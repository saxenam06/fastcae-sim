"""fastcae's rib rules on the housing's walls (LOP-34, the restart; a prototype): the toy's two that
the plan names (`prototypes/rib_field/rules.py`, after `fastcae-v1:src/fastcae/generate/rules.py`),
read along each rib on its wall.

- **The end rule** (`"T"`): a rib's thickness share stays nearly constant along it, away from the
  hard points and the design space's edge on the wall: the root mean square of `T_FAR` times the
  share's slope along the rib (its direction t on the wall) at most `LIMIT_T` mm a mm, so a rib
  starts and stops only within `END_REACH` of a boss, a bolt, a lug or the edge.
- **The slope rule** (`"H"`): the rib's height's slope along it, read near its worst (a p-norm,
  weighted by how live the rib is), at most `LIMIT_H`: tops taper, never step.

Both are read once a wall point (the cubes of the first layer on the wall) and per half, as G <= 0
with their derivatives by every variable (each family's thickness and height B-splines and the
turn); `gradcheck.py --rules` checks them.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rib_field"))
import rules as toyrules  # noqa: E402
import toy  # noqa: E402
import wallfield as wfm  # noqa: E402

END_REACH = toyrules.END_REACH  # 12 mm
LIMIT_T = toyrules.LIMIT_T  # 0.03 mm of thickness a mm along a rib
LIMIT_H = toyrules.LIMIT_H  # 0.5 mm of height a mm along a rib
P_NORM = toyrules.P_NORM


def prepare(wf) -> dict:
    """Each cube's weights in the rules and the thickness cap's gradient where it is read. The rules
    read the first layer's cubes (under one cube off the wall) over the end walls. The edge of the
    design space on an end wall (a rim among them): a first-layer foot with no foot of any end-wall
    cube of its half an edge's length away along +-e1 or +-e2 (the first layer alone is patchy on
    the curved walls: half its feet read as edges)."""
    cm, a = wf.cm, wf.a
    n = wf.n_cubes
    # on the end walls only: a side wall's fin is one section down its wall by construction
    first = (cm["d"] < a) & wf.across
    edge = np.zeros(n, bool)
    edge_dist = np.full(n, np.inf)
    for lower in (True, False):
        half = np.flatnonzero(cm["lower"] == lower)
        sel = np.flatnonzero(first & (cm["lower"] == lower))
        feet = cm["foot"][sel]
        tree = cKDTree(cm["foot"][half[wf.across[half]]])  # the end walls' (a rim is an edge)
        miss = np.zeros(len(sel), bool)
        for e in (cm["e1"][sel], cm["e2"][sel]):
            for sg in (1.0, -1.0):
                dd, _ = tree.query(feet + sg * a * e)
                miss |= dd > 0.75 * a
        edge[sel] = miss
        if miss.any():
            edge_dist[half], _ = cKDTree(feet[miss]).query(cm["foot"][half])
    dist = np.minimum(wf.hard_dist, edge_dist)
    w_end, _ = wfm.smoothstep((dist - END_REACH) / END_REACH)
    eps = 0.25
    grad = np.zeros((n, 3))
    for k in range(3):
        dp = np.zeros(3)
        dp[k] = eps
        grad[:, k] = (wf.thickness_cap(wf.read_at + dp)[0] - wf.thickness_cap(wf.read_at - dp)[0]) / (2 * eps)
    return {"first": first.astype(float), "edge": edge, "edge_dist": edge_dist, "w_end": w_end, "tcap_grad": grad}


def rules(wf, x: np.ndarray, prep: dict) -> list[tuple[str, float, np.ndarray, float]]:
    """(name, G <= 0, dG/dx, the measure) for each half's end rule and slope rule."""
    cm = wf.cm
    out = []
    for hf in wf.halves:
        rows, B = hf["rows"], hf["B"]
        bs = (hf["Bx"], hf["By"], hf["Bz"])
        nb, o = hf["nb"], hf["off"]
        theta = wf.theta0[rows] + math.pi * (B @ wf.field_x(x, hf, 4) - 0.5)
        e1, e2, nn = cm["e1"][rows], cm["e2"][rows], cm["n"][rows]
        first = prep["first"][rows]
        w = prep["w_end"][rows] * first
        tcap, gcap = wf.tcap[rows], prep["tcap_grad"][rows]
        fams = []
        for k in range(2):
            th = theta + k * math.pi / 2
            t = np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2
            m = np.cross(nn, t)
            xs, xr = wf.field_x(x, hf, 2 * k), wf.field_x(x, hf, 2 * k + 1)
            sig, r = B @ xs, B @ xr
            gs = np.stack([M @ xs for M in bs], axis=1)
            gr = np.stack([M @ xr for M in bs], axis=1)
            thk = sig * tcap
            gthk = tcap[:, None] * gs + sig[:, None] * gcap
            c, c1, c2 = toyrules.smin2(wfm.H_MOST, wfm.TALL * thk, toy.SMIN)
            c1, c2 = c1 * wfm.TALL, c2 * wfm.TALL**2  # by the thickness
            f = {"t": t, "sl_s": slice(o + 2 * k * nb, o + (2 * k + 1) * nb),
                 "sl_r": slice(o + (2 * k + 1) * nb, o + (2 * k + 2) * nb),
                 "St": (gs * t).sum(1), "Sm": (gs * m).sum(1), "Rt": (gr * t).sum(1), "Rm": (gr * m).sum(1),
                 "D": (gthk * t).sum(1), "Dm": (gthk * m).sum(1), "Gt": (gcap * t).sum(1),
                 "r": r, "c": c, "c1": c1, "c2": c2}
            f["ds"] = wfm.T_FAR * f["St"]
            f["e"] = c * f["Rt"] + r * c1 * f["D"]
            live, dlive = wfm.smoothstep((thk - wfm.T_MIN) / wfm.T_RAMP)
            f["wk"] = first * (live + 1e-3)
            f["dwk"] = first * dlive / wfm.T_RAMP * tcap  # by sigma
            fams.append(f)
        sl_tau = slice(o + 4 * nb, o + 5 * nb)
        # "T": the thickness share constant along the ribs, away from the anchors
        W = 2.0 * float(w.sum()) + 1e-30
        rms = math.sqrt(sum(float((w * f["ds"] ** 2).sum()) for f in fams) / W)
        g = np.zeros(wf.size)
        gth = np.zeros(len(rows))
        for f in fams:
            gsd = w * f["ds"] / (max(rms, 1e-12) * W * LIMIT_T)
            g[f["sl_s"]] += wfm.T_FAR * sum(M.T @ (f["t"][:, ax] * gsd) for ax, M in enumerate(bs))
            gth += gsd * wfm.T_FAR * f["Sm"]
        g[sl_tau] += math.pi * (B.T @ gth)
        out.append((f"{hf['half']}:T", rms / LIMIT_T - 1.0, g, rms))
        # "H": the height's slope along the ribs near its worst
        vals = np.concatenate([f["e"] for f in fams])
        wts = np.concatenate([f["wk"] for f in fams])
        mh, dv, dw = toyrules._pnorm(vals, wts, P_NORM)
        g = np.zeros(wf.size)
        gth = np.zeros(len(rows))
        nr = len(rows)
        for k, f in enumerate(fams):
            ge, gw = dv[k * nr: (k + 1) * nr] / LIMIT_H, dw[k * nr: (k + 1) * nr] / LIMIT_H
            tt = f["t"]
            g[f["sl_r"]] += sum(M.T @ (f["c"] * tt[:, ax] * ge) for ax, M in enumerate(bs))
            g[f["sl_r"]] += B.T @ (f["c1"] * f["D"] * ge)
            per = ge * (tcap * f["c1"] * f["Rt"] + f["r"] * f["c2"] * tcap * f["D"] + f["r"] * f["c1"] * f["Gt"])
            g[f["sl_s"]] += B.T @ (per + gw * f["dwk"])
            g[f["sl_s"]] += sum(M.T @ (ge * f["r"] * f["c1"] * tcap * tt[:, ax]) for ax, M in enumerate(bs))
            gth += ge * (f["c"] * f["Rm"] + f["r"] * f["c1"] * f["Dm"])
        g[sl_tau] += math.pi * (B.T @ gth)
        out.append((f"{hf['half']}:H", mh / LIMIT_H - 1.0, g, mh))
    return out
