"""PROTOTYPE (LOP-30) - A quick look at the plan fairing before any drawing: each half's first level, the metal columns (grey), the plain outline
(the columns' own distance's zero, black) and the faired one (red).

    fair_preview.py <run stem> <along>[:<iso>[:<protect>]] <out png>
"""

import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("LOOP_EXACT_WALLS", "1")
os.environ["LOOP_VOXEL_FAIR"] = sys.argv[2]
import outcome_cad as oc  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run, png = sys.argv[1], sys.argv[3]
z = np.load(OUT / f"{run}.npz")
h, lo = float(z["h"]), np.asarray(z["lo"], float)
spl = oc.voxel_cols_as_spline(run, 3.0, 3.0)
ss = oc.SPLINE_PLAN_SUB
fig, axes = plt.subplots(1, 2, figsize=(26, 13))
for ax, hf in zip(axes, (0, 1), strict=True):
    grid = spl["plan_sdf"][(hf, 0)]
    xs = lo[0] + ss * (np.arange(grid.shape[0]) + 0.5)
    ys = lo[1] + ss * (np.arange(grid.shape[1]) + 0.5)
    # the first level's own columns (each plan cell's nearest run to the split, as the drawing orders them)
    base = spl["base"].astype(int)
    first = np.zeros(len(base), bool)
    seen = set()
    order = np.argsort(-base if hf == 0 else base, kind="stable")
    for k in order:
        if spl["half"][k] != hf:
            continue
        key = (int(spl["ij"][k, 0]), int(spl["ij"][k, 1]))
        if key not in seen:
            first[k] = True
            seen.add(key)
    sel = (spl["half"] == hf) & np.isfinite(spl["t"]) & first
    ij = spl["ij"][sel]
    met = np.zeros(grid.shape, bool)
    r = int(round(h / ss))
    for i, j in ij:
        met[i * r : (i + 1) * r, j * r : (j + 1) * r] = True
    ax.imshow(np.where(met, 0.8, 1.0).T, origin="lower", extent=(xs[0], xs[-1], ys[0], ys[-1]), cmap="gray", vmin=0, vmax=1)
    import voxel_fair as vf

    plain = vf.signed_distance(met, ss)
    ax.contour(xs, ys, plain.T, levels=[0.0], colors="k", linewidths=0.5)
    ax.contour(xs, ys, grid.T, levels=[0.0], colors="r", linewidths=0.8)
    ax.set_aspect("equal")
    ax.set_title(f"{'motor side' if hf == 0 else 'cover'}, first level: metal columns grey, their outline black, faired red", loc="left")
fig.tight_layout()
fig.savefig(OUT / png, dpi=60)
print(OUT / png)
