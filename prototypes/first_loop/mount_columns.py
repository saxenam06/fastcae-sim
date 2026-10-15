"""PROTOTYPE (LOP-30) - Round each mount: the voxel run's columns as the smooth drawing reads them (`outcome_cad.voxel_cols_as_spline`), how many
hold metal, how many of those the blurred outline drops (every point below its middle), and their heights; a plan picture
of the metal columns, dropped ones red, with the blurred outline's zero line.

    mount_columns.py <run stem> <sigma mm> <out png>
"""

import json
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
import outcome_cad as oc  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run, sigma, png = sys.argv[1], float(sys.argv[2]), sys.argv[3]
spl = oc.voxel_cols_as_spline(run, sigma, 3.0)
z = np.load(OUT / f"{run}.npz")
h, lo = float(z["h"]), np.asarray(z["lo"], float)
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
ij, half, t = spl["ij"].astype(int), spl["half"], spl["t"]
xy = lo[:2] + h * (ij + 0.5)
metal = np.isfinite(t)
sub_col, sub_phi = spl["sub_col"], spl["sub_phi"]
best = np.full(len(t), -np.inf)
np.maximum.at(best, sub_col, sub_phi)
dropped = metal & (best <= 0)
fig, axes = plt.subplots(1, 3, figsize=(24, 8))
for ax, m in zip(axes, lay["mounts"], strict=True):
    c = np.asarray(m["centre"], float)
    near = (np.hypot(xy[:, 0] - c[0], xy[:, 1] - c[1]) < 40) & (half == 0)
    print(f"{m['name']}: {int((near & metal).sum())} metal columns within 40 mm, {int((near & dropped).sum())} dropped by the blur; "
          f"heights (mm) of the dropped: {np.round(h * t[near & dropped], 0).tolist()[:20]}")
    sel = near & metal
    ax.scatter(xy[sel & ~dropped, 0], xy[sel & ~dropped, 1], s=60, c=h * t[sel & ~dropped], cmap="viridis", marker="s", vmin=0, vmax=80)
    ax.scatter(xy[sel & dropped, 0], xy[sel & dropped, 1], s=60, c="red", marker="s")
    ax.add_patch(plt.Circle(c, 18.0, fill=False, ec="k", lw=1.5))
    for k in np.flatnonzero(sel):
        ax.annotate(f"{h * t[k]:.0f}", xy[k], fontsize=6, ha="center", va="center", color="w")
    ax.set_xlim(c[0] - 42, c[0] + 42)
    ax.set_ylim(c[1] - 42, c[1] + 42)
    ax.set_aspect("equal")
    ax.set_title(f"{m['name']}: metal columns (height off their base, mm), red = dropped by the {sigma:g} mm blur", fontsize=10, loc="left")
fig.tight_layout()
fig.savefig(OUT / png, dpi=70)
print(OUT / png)
