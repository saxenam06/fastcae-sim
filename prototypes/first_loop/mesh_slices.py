"""PROTOTYPE (LOP-30) - A drawn half's mesh cut across the pull at several heights, zoomed to a window in plan, with the layout's bores, bolts
and mounts drawn: to see what lies at a place FE's mesher refuses."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design, half = sys.argv[1], sys.argv[2]
zs = [float(v) for v in sys.argv[3].split(",")]
box = [float(v) for v in sys.argv[4].split(",")]
png = sys.argv[5]
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
m = trimesh.load(OUT / f"{design}_{half}.ply")
fig, axes = plt.subplots(1, len(zs), figsize=(7 * len(zs), 7))
for ax, z in zip(np.atleast_1d(axes), zs, strict=True):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is not None:
        for ent in sec.discrete:
            ax.plot(ent[:, 0], ent[:, 1], "k-", lw=0.8)
    for b in lay["bearings"]:
        ax.add_patch(plt.Circle(b["axis"][:2], 0.5 * float(b["D"]), fill=False, ec="#2b6cb0", lw=1.0))
    for bb in lay["bolts"]:
        ax.add_patch(plt.Circle(bb[:2], 0.5 * float(lay["settings"]["bolt_boss"]), fill=False, ec="#c05621", lw=1.0))
        ax.add_patch(plt.Circle(bb[:2], 8.0, fill=False, ec="#c05621", lw=0.6, ls="--"))
    ax.set_xlim(box[0], box[1])
    ax.set_ylim(box[2], box[3])
    ax.set_aspect("equal")
    ax.set_title(f"{design} {half}: the cut at z {z:g}", fontsize=11, loc="left")
fig.savefig(OUT / png, dpi=80, bbox_inches="tight")
print(OUT / png)
