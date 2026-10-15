"""The rib rules held while the field is found (LOP-34; a prototype; the engineer, 16 October: "do
step 1 and 2", then "implement fastcae rules as applicable for this model ... we still should be
able to reveal various ribs, patterns, tapered ribs and brackets").

fastcae's rules (`fastcae-v1:src/fastcae/generate/rules.py`, `src/fastcae/rules/member.py`), read
for a field of ribs:

- **thinnest / thickest** -> **thickness by place** (`thickness_cap`): the thickest rib allowed
  tapers from `T_NEAR` at the edge of a boss, a bolt's boss or the lug to `T_FAR` at `T_TAPER` mm
  (a smooth step), as production's ribs thicken where the load gathers; under `T_LEAST` a rib is not
  drawn (`draw.py`).
- **tallest_ratio** -> a rib stands at most `TALL` times its thickness (`toy.TALL`).
- **never above the wall or boss each end grips, flush_mm under its top** -> **the height by place**
  (`height_cap`): within `END_REACH` of a hard point a rib stands at most `FLUSH` under that point's
  top (the bolts' bosses `toy.H_BOLT` tall), rising smoothly to the band past twice that; so ribs
  taper down to a low boss.
- **least_end_mm** (twice the root fillet) -> a rib under `H_LEAST` tall is not drawn.
- **ends glued to walls** -> **the end rule** (`"T"`): along each rib, away from the hard points and
  the plate's edge (a housing's side walls), its thickness stays nearly constant (root mean square of
  its slope along the rib at most `LIMIT_T`), so a rib starts and stops only within `END_REACH` of
  a boss, a bolt, the lug or the edge.
- **no cliffs, tapers allowed** -> **the slope rule** (`"H"`): the height's slope along each rib,
  read near its worst (a p-norm, p `P_NORM`, weighted by the rib's amount) at most `LIMIT_H`: tops
  slope and taper but never step.
- **arrive_deg** (60 degrees) -> **the arrival rule** (`"A"`): within `END_REACH` of a hard point
  or the edge, ribs run along its normal (spokes, ends arriving square) or along its face (rings),
  never in between: sin^2(2 u) of the angle u between the rib and the normal over 0.75 (30-60
  degrees) penalised, weighted by the ribs' amount. Two families at right angles share the angle,
  so a spoke family carries a ring family.
- **bend_mm** -> **the bend rule** (`"K"`): the rib lines' curvature (the rate the direction turns
  along a rib) read near its worst (p-norm, weighted by amount) at most 1 / `R_BEND`.
- **sand_mm, cross_deg** -> by construction: one spacing between ribs, the two families at 90.
- **shortest_ratio** -> the drawing's gate (`draw.L_LEAST`), with pieces touching nothing dropped.
- **draft_deg, tip_mm, fillet_root_mm, fillet_edge_mm** -> the drawing (`draw.implicit`): drafted
  faces, rounded tops and root fillets from a smooth implicit field.

Each rule G <= 0 is a GCMMA constraint, with its derivatives by every variable (each family's
thickness and height B-splines and the directions' turn); `gradcheck.py --rules` checks them. The
values are the toy's, scaled from fastcae's (25 mm ribs) to ours: the product's take the engineer's
word.
"""

from __future__ import annotations

import numpy as np

import toy

T_NEAR, T_FAR, T_TAPER = 12.0, 6.0, 30.0  # mm
T_LEAST = 3.0  # mm: a thinner rib is not drawn
H_LEAST = 8.0  # mm: a lower rib is not drawn (twice our 4 mm root fillet; LOOP_LEAST_MEMBER)
END_REACH = 12.0  # mm
FLUSH = 3.0  # mm under a hard point's top
LIMIT_T = 0.03  # mm of thickness a mm along a rib, root mean square
LIMIT_H = 0.5  # mm of height a mm along a rib, near the worst (p-norm)
LIMIT_A = 0.02  # the mean obliqueness of the ribs near a hard point or the edge
R_BEND = 30.0  # mm: the tightest a rib line bends, near the worst (p-norm `P_BEND`), away from the anchors
P_BEND = 4.0  # (16 October: at p 8 over every point the start's convergence at the bosses ruled it
# infeasible and the optimiser emptied the ribs, toy run f4)
P_NORM = 8.0
ARRIVE_SHARP = 8.0  # the obliqueness penalty's softplus sharpness


def hard_points() -> list[tuple[tuple[float, float], float, float]]:
    """(centre, radius, top above the wall) of each hard point."""
    return (
        [(toy.BORE, toy.R_BOSS, toy.BAND), (toy.LUG, toy.R_LUG, toy.BAND)]
        + [(b, toy.R_BOLT, toy.H_BOLT) for b in toy.BOLTS]
    )


def hard_distance(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The distance from each point to the nearest hard point's edge, and its gradient."""
    best = np.full(len(xy), np.inf)
    grad = np.zeros((len(xy), 2))
    for (cx, cy), r, _ in hard_points():
        dx, dy = xy[:, 0] - cx, xy[:, 1] - cy
        rr = np.maximum(np.hypot(dx, dy), 1e-9)
        d = rr - r
        nearer = d < best
        best = np.where(nearer, d, best)
        grad[nearer] = np.stack([dx / rr, dy / rr], axis=1)[nearer]
    return best, grad


def edge_distance(xy: np.ndarray) -> np.ndarray:
    return np.minimum.reduce([xy[:, 0], toy.LX - xy[:, 0], xy[:, 1], toy.LY - xy[:, 1]])


def smoothstep(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u), 6 * u * (1 - u)


def thickness_cap(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The thickest rib allowed at each point (mm) and its gradient (mm a mm)."""
    d, grad = hard_distance(xy)
    s, ds = smoothstep(d / T_TAPER)
    cap = T_FAR + (T_NEAR - T_FAR) * (1.0 - s)
    return cap, (-(T_NEAR - T_FAR) * ds / T_TAPER)[:, None] * grad


def height_cap(xy: np.ndarray) -> np.ndarray:
    """The tallest a rib may stand at each point (mm above the wall): `FLUSH` under the top of each
    hard point within `END_REACH` of its edge, rising smoothly to the band at twice that."""
    cap = np.full(len(xy), toy.BAND)
    for (cx, cy), r, top in hard_points():
        d = np.hypot(xy[:, 0] - cx, xy[:, 1] - cy) - r
        s, _ = smoothstep((d - END_REACH) / END_REACH)
        cap = np.minimum(cap, toy.BAND - (toy.BAND - (top - FLUSH)) * (1.0 - s))
    return cap


def end_weight(xy: np.ndarray) -> np.ndarray:
    """0 within `END_REACH` of a hard point's edge or the plate's edge (a rib may end there), rising
    smoothly to 1 at twice that."""
    d = np.minimum(hard_distance(xy)[0], edge_distance(xy))
    return smoothstep((d - END_REACH) / END_REACH)[0]


def anchor_normal(xy: np.ndarray) -> np.ndarray:
    """The angle of the normal of the nearest anchor (a hard point's radius, or the edge's
    normal)."""
    d, grad = hard_distance(xy)
    e = edge_distance(xy)
    ang = np.arctan2(grad[:, 1], grad[:, 0])
    near_x = np.minimum(xy[:, 0], toy.LX - xy[:, 0]) <= np.minimum(xy[:, 1], toy.LY - xy[:, 1])
    edge_ang = np.where(near_x, 0.0, np.pi / 2)
    return np.where(e < d, edge_ang, ang)


def theta_gradient(theta: np.ndarray, ij: np.ndarray, a: float) -> np.ndarray:
    """(n, 2): the gradient of a line field theta given on the columns (i, j), by central
    differences where both neighbours exist (one-sided otherwise), each difference taken modulo pi."""
    nx, ny = ij[:, 0].max() + 1, ij[:, 1].max() + 1
    grid = np.full((nx + 2, ny + 2), np.nan)
    grid[ij[:, 0] + 1, ij[:, 1] + 1] = theta
    out = np.zeros((len(theta), 2))
    for axis, (di, dj) in enumerate(((1, 0), (0, 1))):
        c = grid[ij[:, 0] + 1, ij[:, 1] + 1]
        p = grid[ij[:, 0] + 1 + di, ij[:, 1] + 1 + dj]
        m = grid[ij[:, 0] + 1 - di, ij[:, 1] + 1 - dj]

        def wrap(u):
            return np.angle(np.exp(2j * u)) / 2

        fwd, bwd = wrap(p - c), wrap(c - m)
        both = ~np.isnan(p) & ~np.isnan(m)
        g = np.where(both, 0.5 * (fwd + bwd), np.where(~np.isnan(p), fwd, np.where(~np.isnan(m), bwd, 0.0)))
        out[:, axis] = np.nan_to_num(g) / a
    return out


def smin2(a, b: np.ndarray, k: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`toy.smin` with its first and second derivatives by b."""
    m = np.minimum(a, b)
    ea, eb = np.exp(-k * (a - m)), np.exp(-k * (b - m))
    sig = eb / (ea + eb)
    return m - np.log(ea + eb) / k, sig, -k * sig * (1 - sig)


def _pnorm(values: np.ndarray, weights: np.ndarray, p: float):
    """(sum w |v|^p / sum w)^(1/p), its derivative by v and by w."""
    av = np.abs(values) + 1e-30
    s = float((weights * av**p).sum())
    w = float(weights.sum()) + 1e-30
    if s <= 1e-300:  # nothing weighed (a group wholly within reach of its anchors)
        return 0.0, np.zeros_like(values), np.zeros_like(weights)
    m = (s / w) ** (1.0 / p)
    dv = m / s * weights * av ** (p - 1) * np.sign(values)
    dw = (m / p) * (av**p / s - 1.0 / w)
    return m, dv, dw


def transport(fld, x: np.ndarray) -> dict:
    """The rules on the field at x. Returns, per rule ("T", "H", and with `fld.fastcae` "A", "K"),
    (G <= 0, dG/dx, the measure)."""
    n, B, Bx, By = fld.n, fld.B, fld.Bx, fld.By
    w = fld.w_end
    tcap, tg = fld.tcap, fld.tcap_grad
    fams = []
    for k in range(fld.families):
        th = fld.theta + k * np.pi / 2
        tx, ty = np.cos(th), np.sin(th)
        sl_r = slice(2 * k * n, (2 * k + 1) * n)
        sl_h = slice((2 * k + 1) * n, (2 * k + 2) * n)
        xr, xh = x[sl_r], x[sl_h]
        a, ax, ay = B @ xr, Bx @ xr, By @ xr
        t = tcap * a
        tx_, ty_ = tg[:, 0] * a + tcap * ax, tg[:, 1] * a + tcap * ay
        d = tx * tx_ + ty * ty_  # the thickness's slope along the rib
        # the end rule reads the rib's share of its local cap: a rib keeps it along its run, so it
        # tapers with the cap from a thick root (16 October: read on the thickness itself, the cap's
        # taper broke the rule wherever a rib ran from a boss, and the toy's f5 placed half its budget)
        ds = T_FAR * (tx * ax + ty * ay)
        r, rx, ry = B @ xh, Bx @ xh, By @ xh
        c, c1, c2 = smin2(fld.hcap, toy.TALL * t, toy.SMIN)
        c1, c2 = c1 * toy.TALL, c2 * toy.TALL**2  # by t
        tr = tx * rx + ty * ry
        e = c * tr + r * c1 * d  # the height's slope along the rib
        fams.append(dict(tx=tx, ty=ty, sl_r=sl_r, sl_h=sl_h, a=a, ax=ax, ay=ay, ds=ds, tx_=tx_, ty_=ty_, d=d, r=r,
                         rx=rx, ry=ry, c=c, c1=c1, c2=c2, tr=tr, e=e))

    def back(gd_list, ge_list, ga_list=None, gs_list=None):
        """The gradient by x of a function with these derivatives by each family's d, e (and a,
        the thickness share), and by theta."""
        g = np.zeros_like(x)
        gth = np.zeros(len(w))
        for f, gd, ge, ga, gs in zip(fams, gd_list, ge_list, ga_list or [None] * len(fams),
                                     gs_list or [None] * len(fams), strict=True):
            if gs is not None:  # the share's slope: T_FAR (tx ax + ty ay)
                g[f["sl_r"]] += T_FAR * (Bx.T @ (f["tx"] * gs) + By.T @ (f["ty"] * gs))
                gth += gs * T_FAR * (-f["ty"] * f["ax"] + f["tx"] * f["ay"])
            tx, ty, sl_r, sl_h = f["tx"], f["ty"], f["sl_r"], f["sl_h"]
            m_coef = tx * tg[:, 0] + ty * tg[:, 1]
            # d = m_coef a + tcap (tx ax + ty ay): linear in the thickness's variables
            gd_total = gd + ge * f["r"] * f["c1"]  # e depends on d through r c1 d
            g[sl_r] += B.T @ (m_coef * gd_total) + Bx.T @ (tcap * tx * gd_total)
            g[sl_r] += By.T @ (tcap * ty * gd_total)
            de_dt = f["c1"] * f["tr"] + f["r"] * f["c2"] * f["d"]
            g[sl_r] += B.T @ (tcap * de_dt * ge)
            if ga is not None:
                g[sl_r] += B.T @ ga
            g[sl_h] += Bx.T @ (f["c"] * tx * ge) + By.T @ (f["c"] * ty * ge)
            g[sl_h] += B.T @ (f["c1"] * f["d"] * ge)
            dd_dth = -ty * f["tx_"] + tx * f["ty_"]
            gth += gd_total * dd_dth + ge * f["c"] * (-ty * f["rx"] + tx * f["ry"])
        return g, gth

    def finish(g, gth, extra_th=None):
        if fld.turns:
            if extra_th is not None:
                gth = gth + extra_th
            g[2 * n * fld.families :] += np.pi * (B.T @ gth)
        return g

    out = {}
    total_w = float(w.sum()) * fld.families + 1e-30
    # "T": the thickness constant along the ribs away from the anchors (root mean square)
    sd = sum(float((w * f["ds"] ** 2).sum()) for f in fams)
    rms = np.sqrt(sd / total_w)
    scale = 1.0 / (2.0 * max(rms, 1e-12) * total_w * LIMIT_T)
    g, gth = back([np.zeros_like(w) for _ in fams], [np.zeros_like(w) for _ in fams], None,
                  [2 * w * f["ds"] * scale for f in fams])
    out["T"] = (rms / LIMIT_T - 1.0, finish(g, gth), rms)
    if not fld.fastcae:
        # the height constant along the ribs too (root mean square), as before the fastcae rules
        se = sum(float((w * f["e"] ** 2).sum()) for f in fams)
        rms = np.sqrt(se / total_w)
        scale = 1.0 / (2.0 * max(rms, 1e-12) * total_w * 0.08)
        g, gth = back([np.zeros_like(w) for _ in fams], [2 * w * f["e"] * scale for f in fams])
        out["H"] = (rms / 0.08 - 1.0, finish(g, gth), rms)
        return out
    # "H": the height's slope near its worst, weighted by the rib's amount (tapers, no cliffs)
    vals = np.concatenate([f["e"] for f in fams])
    wts = np.concatenate([f["a"] + 1e-3 for f in fams])
    m, dv, dw = _pnorm(vals, wts, P_NORM)
    k_ = len(w)
    g, gth = back(
        [np.zeros_like(w) for _ in fams],
        [dv[i * k_ : (i + 1) * k_] / LIMIT_H for i in range(len(fams))],
        [dw[i * k_ : (i + 1) * k_] / LIMIT_H for i in range(len(fams))],
    )
    out["H"] = (m / LIMIT_H - 1.0, finish(g, gth), m)
    # "A": ribs near an anchor radial or round it, never oblique
    near = 1.0 - w
    u = fld.theta - fld.normal
    s2 = np.sin(2 * u) ** 2
    pp = (s2 - 0.75) / 0.25
    q = np.logaddexp(0.0, ARRIVE_SHARP * pp) / ARRIVE_SHARP
    dq = 1.0 / (1.0 + np.exp(-ARRIVE_SHARP * pp)) * (2 * np.sin(4 * u) / 0.25)
    amount = sum(f["a"] for f in fams)
    wn = float(near.sum()) + 1e-30
    mean = float((near * amount * q).sum()) / wn
    g = np.zeros_like(x)
    for f in fams:
        g[f["sl_r"]] += B.T @ (near * q / wn / LIMIT_A)
    g = finish(g, np.zeros(len(w)), near * amount * dq / wn / LIMIT_A)
    out["A"] = (mean / LIMIT_A - 1.0, g, mean)
    # "K": the rib lines' curvature near its worst, weighted by the rib's amount
    y = x[2 * n * fld.families :] if fld.turns else np.zeros(n)
    thx = fld.theta0_grad[:, 0] + np.pi * (Bx @ y)
    thy = fld.theta0_grad[:, 1] + np.pi * (By @ y)
    kap = np.concatenate([f["tx"] * thx + f["ty"] * thy for f in fams])
    wts = np.concatenate([w * (f["a"] + 1e-3) for f in fams])  # away from the anchors
    m, dv, dw = _pnorm(kap, wts, P_BEND)
    lim = 1.0 / R_BEND
    g = np.zeros_like(x)
    gth = np.zeros(len(w))
    gthx = np.zeros(len(w))
    gthy = np.zeros(len(w))
    for i, f in enumerate(fams):
        dvi, dwi = dv[i * k_ : (i + 1) * k_] / lim, dw[i * k_ : (i + 1) * k_] / lim
        g[f["sl_r"]] += B.T @ (dwi * w)
        gth += dvi * (-f["ty"] * thx + f["tx"] * thy)
        gthx += dvi * f["tx"]
        gthy += dvi * f["ty"]
    if fld.turns:
        g[2 * n * fld.families :] += np.pi * (B.T @ gth + Bx.T @ gthx + By.T @ gthy)
    out["K"] = (m / lim - 1.0, g, m)
    return out
