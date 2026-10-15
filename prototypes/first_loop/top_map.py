"""PROTOTYPE (LOP-32) - A height-field run's members' free ends in plan, each half and family: the visible top's height above
the split (mm) per column holding metal, with the members' skeleton (`member_fair`) over it, masked points grey: where the
tops rise and fall, along members or across webs and junctions.

    top_map.py <run stem> <out png> [x0,x1,y0,y1]
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import member_fair as mf  # noqa: E402

run, png = sys.argv[1], sys.argv[2]
box = [float(v) for v in sys.argv[3].split(",")] if len(sys.argv) > 3 else None
cols, t, lo, h = mf.from_run(run)
fr = mf.Frame(cols, t, lo, h)
E = h * (cols["o_base"] + t)
metal = t >= 0.5
xy = lo[:2] + h * (cols["ij"] + 0.5)
fig, axes = plt.subplots(2, 2, figsize=(22, 20))
for r_, hf in enumerate((1, 0)):
    for c_, fam in enumerate((False, True)):
        ax = axes[r_, c_]
        sel = metal & (cols["half"] == hf) & (cols["on_split"] == fam)
        if box:
            sel &= (xy[:, 0] >= box[0]) & (xy[:, 0] <= box[1]) & (xy[:, 1] >= box[2]) & (xy[:, 1] <= box[3])
        sc = ax.scatter(xy[sel, 0], xy[sel, 1], c=E[sel], s=60 if box else 14, marker="s", cmap="viridis", lw=0)
        fig.colorbar(sc, ax=ax, shrink=0.7, label="the free end from the split (mm)")
        mine = np.array([g[0] == hf and bool(g[2]) == fam for g in fr.group], bool) if fr.n_pts else np.zeros(0, bool)
        if box:
            mine &= (fr.xy[:, 0] >= box[0]) & (fr.xy[:, 0] <= box[1]) & (fr.xy[:, 1] >= box[2]) & (fr.xy[:, 1] <= box[3])
        ax.plot(fr.xy[mine & ~fr.masked, 0], fr.xy[mine & ~fr.masked, 1], "r.", ms=3)
        ax.plot(fr.xy[mine & fr.masked, 0], fr.xy[mine & fr.masked, 1], ".", c="#888888", ms=3)
        ax.set_aspect("equal")
        ax.set_title(f"{['motor side', 'cover'][hf]}, {'on the split' if fam else 'on a wall'}: each column's top (red: the "
                     "skeleton's points the rules read, grey: masked)", fontsize=11, loc="left")
fig.tight_layout()
fig.savefig(Path(HERE.parents[1] / "data" / "first_loop" / png), dpi=55)
print(HERE.parents[1] / "data" / "first_loop" / png)
