"""The rib rules held while the field is found (LOP-34; a prototype; the engineer, 16 October: "do
step 1 and 2").

- **Thickness by place** (`thickness_cap`): the thickest rib allowed at a point tapers from `T_NEAR`
  at the edge of the bearing's boss, a bolt's boss or the lug to `T_FAR` at `T_TAPER` mm from the
  nearest (a smooth step), as production's ribs thicken where the load gathers.
- **Ends on walls and bosses** (`transport`): along each rib, away from the hard points and the
  plate's edge (the side walls of a housing), its thickness and its height stay nearly constant: the
  root mean square of their slopes along the rib's own direction at most `LIMIT_T` and `LIMIT_H`
  (mm a mm), so a rib can start or stop only within `END_REACH` of a boss, a bolt, the lug or the
  edge. Two GCMMA constraints, with their derivatives by every variable (the thickness's and the
  height's B-splines and the directions' turn).

The values are the toy's, not the product's: the product's take the engineer's word.
"""

from __future__ import annotations

import numpy as np

import toy

T_NEAR, T_FAR, T_TAPER = 12.0, 6.0, 30.0  # mm
END_REACH = 12.0  # mm
LIMIT_T = 0.03  # mm of thickness a mm along a rib, root mean square
LIMIT_H = 0.08  # mm of height a mm along a rib, root mean square


def hard_points() -> list[tuple[tuple[float, float], float]]:
    return [(toy.BORE, toy.R_BOSS), (toy.LUG, toy.R_LUG)] + [(b, toy.R_BOLT) for b in toy.BOLTS]


def hard_distance(xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The distance from each point to the nearest hard point's edge, and its gradient."""
    best = np.full(len(xy), np.inf)
    grad = np.zeros((len(xy), 2))
    for (cx, cy), r in hard_points():
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


def end_weight(xy: np.ndarray) -> np.ndarray:
    """0 within `END_REACH` of a hard point's edge or the plate's edge (a rib may end there), rising
    smoothly to 1 at twice that."""
    d = np.minimum(hard_distance(xy)[0], edge_distance(xy))
    return smoothstep((d - END_REACH) / END_REACH)[0]


def smin2(a: float, b: np.ndarray, k: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`toy.smin` with its first and second derivatives by b."""
    m = np.minimum(a, b)
    ea, eb = np.exp(-k * (a - m)), np.exp(-k * (b - m))
    sig = eb / (ea + eb)
    return m - np.log(ea + eb) / k, sig, -k * sig * (1 - sig)


def transport(fld, x: np.ndarray) -> dict:
    """The rules on the field at x: each family's thickness and height slopes along its ribs. Returns
    the two constraints (G <= 0), their gradients by x, and the slopes' root mean squares."""
    n, B, Bx, By = fld.n, fld.B, fld.Bx, fld.By
    w = fld.w_end
    tcap, tg = fld.tcap, fld.tcap_grad
    sums = {"T": 0.0, "H": 0.0}
    grads = {"T": np.zeros_like(x), "H": np.zeros_like(x)}
    dth = {"T": np.zeros(len(w)), "H": np.zeros(len(w))}
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
        r, rx, ry = B @ xh, Bx @ xh, By @ xh
        c, c1, c2 = smin2(toy.BAND, toy.TALL * t, toy.SMIN)
        c1, c2 = c1 * toy.TALL, c2 * toy.TALL**2  # by t
        tr = tx * rx + ty * ry
        e = c * tr + r * c1 * d  # the height's slope along the rib
        sums["T"] += float((w * d * d).sum())
        sums["H"] += float((w * e * e).sum())
        # by the thickness's variables: d is linear in them
        gd = 2 * w * d
        grads["T"][sl_r] += B.T @ ((tx * tg[:, 0] + ty * tg[:, 1]) * gd) + Bx.T @ (tcap * tx * gd)
        grads["T"][sl_r] += By.T @ (tcap * ty * gd)
        ge = 2 * w * e
        de_dt = c1 * tr + r * c2 * d
        de_dd = r * c1
        grads["H"][sl_r] += B.T @ (tcap * de_dt * ge)
        grads["H"][sl_r] += B.T @ ((tx * tg[:, 0] + ty * tg[:, 1]) * de_dd * ge)
        grads["H"][sl_r] += Bx.T @ (tcap * tx * de_dd * ge) + By.T @ (tcap * ty * de_dd * ge)
        grads["H"][sl_h] += Bx.T @ (c * tx * ge) + By.T @ (c * ty * ge) + B.T @ (c1 * d * ge)
        # by the direction
        dd_dth = -ty * tx_ + tx * ty_
        dth["T"] += gd * dd_dth
        dth["H"] += ge * (c * (-ty * rx + tx * ry) + r * c1 * dd_dth)
    total_w = float(w.sum()) * fld.families
    out = {}
    for key, limit in (("T", LIMIT_T), ("H", LIMIT_H)):
        rms = np.sqrt(sums[key] / total_w)
        scale = 1.0 / (2.0 * max(rms, 1e-12) * total_w * limit)
        g = grads[key] * scale
        if fld.turns:
            g[2 * n * fld.families :] += np.pi * (B.T @ (dth[key] * scale))
        out[key] = (rms / limit - 1.0, g, rms)
    return out
