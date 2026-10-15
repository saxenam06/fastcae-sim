"""PROTOTYPE (LOP-30) - Where a smooth drawing lost the optimiser's metal: each placed cube (the run's metal beyond its fixed set, density 0.5 or
more) whose centre lies outside the drawn half, in plan, coloured by its depth from the split, with the mounts and bores.

    lost_cubes.py <run stem> <design> <out png>
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run, design, png = sys.argv[1:4]
z = np.load(OUT / f"{run}.npz")
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
h, lo = float(z["h"]), np.asarray(z["lo"], float)
elem, frozen, phys = z["elem"], z["frozen"].astype(bool), np.asarray(z["phys"], float)
n = np.asarray(z["n"], int)
free = elem[~frozen]
ijk = np.column_stack(np.unravel_index(free[phys >= 0.5], tuple(n)))
xyz = lo + h * (ijk + 0.5)
z_split = float(lay["z"]["split"])
fig, axes = plt.subplots(1, 2, figsize=(22, 11))
summary = {}
for ax, half in zip(axes, ("motor_side", "cover"), strict=True):
    mine = xyz[:, 2] < z_split if half == "motor_side" else xyz[:, 2] >= z_split
    pts = xyz[mine]
    surf = pv.read(OUT / f"{design}_{half}.ply")
    inside = np.asarray(pv.PolyData(pts).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)["SelectedPoints"]).astype(bool)
    lost = pts[~inside]
    summary[half] = (int(len(pts)), int(len(lost)))
    ax.scatter(pts[inside, 0], pts[inside, 1], s=4, c="#bbbbbb", lw=0)
    sc = ax.scatter(lost[:, 0], lost[:, 1], s=10, c=np.abs(lost[:, 2] - z_split), cmap="plasma", lw=0)
    for b in lay["bearings"]:
        ax.add_patch(plt.Circle(b["axis"][:2], 0.5 * float(b["D"]), fill=False, ec="#2b6cb0", lw=1.0))
    for m in lay["mounts"]:
        c = m.get("centre") or m.get("axis")
        ax.add_patch(plt.Circle(c[:2], 18.0, fill=False, ec="#c53030", lw=1.5))
        ax.annotate(m.get("name", ""), c[:2], fontsize=10, color="#c53030")
    ax.set_aspect("equal")
    ax.set_title(f"{design} {half}: {len(lost)} of {len(pts)} placed cubes outside the drawing (coloured by depth off the split, mm)",
                 fontsize=10, loc="left")
    fig.colorbar(sc, ax=ax, shrink=0.6)
fig.tight_layout()
fig.savefig(OUT / png, dpi=70)
print(OUT / png, summary)
