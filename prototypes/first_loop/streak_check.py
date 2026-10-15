"""PROTOTYPE (LOP-30) - Are a drawn member's vertical streaks in its geometry? Cut the half across the pull, take the section's outline in a
window, and measure how far it wanders from its own smoothed copy (the outline's high-frequency part), with a zoomed picture.

    streak_check.py <design> <half> <z> <x0,x1,y0,y1> <out png>
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from scipy.ndimage import gaussian_filter1d  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design, half, z = sys.argv[1], sys.argv[2], float(sys.argv[3])
x0, x1, y0, y1 = (float(v) for v in sys.argv[4].split(","))
png = sys.argv[5]
m = trimesh.load(OUT / f"{design}_{half}.ply")
sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
fig, ax = plt.subplots(figsize=(9, 9))
devs = []
for ent in sec.discrete:
    inside = (ent[:, 0] >= x0) & (ent[:, 0] <= x1) & (ent[:, 1] >= y0) & (ent[:, 1] <= y1)
    if inside.sum() < 20:
        continue
    seg = np.diff(ent, axis=0)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    if s[-1] < 10:
        continue
    t = np.arange(0.0, s[-1], 0.1)
    p = np.column_stack([np.interp(t, s, ent[:, 0]), np.interp(t, s, ent[:, 1])])
    sm = np.column_stack([gaussian_filter1d(p[:, 0], 20, mode="wrap"), gaussian_filter1d(p[:, 1], 20, mode="wrap")])  # 2 mm
    d = np.hypot(*(p - sm).T)
    keep = (p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
    devs.append(d[keep])
    ax.plot(p[:, 0], p[:, 1], "k-", lw=0.6)
    ax.plot(sm[:, 0], sm[:, 1], "r-", lw=0.4)
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
ax.set_aspect("equal")
dd = np.concatenate(devs) if devs else np.zeros(1)
ax.set_title(f"{design} {half} at z {z:g}: the outline (black) and its 2 mm smoothed copy (red); wander rms {np.sqrt((dd**2).mean()):.2f} mm, "
             f"most {dd.max():.2f} mm", fontsize=9, loc="left")
fig.savefig(OUT / png, dpi=90, bbox_inches="tight")
print(OUT / png, f"rms {np.sqrt((dd**2).mean()):.3f} mm, 95 % {np.percentile(dd, 95):.3f}, most {dd.max():.3f}")
