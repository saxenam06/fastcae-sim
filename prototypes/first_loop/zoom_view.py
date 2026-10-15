"""PROTOTYPE (LOP-30) - One window of a design's half rendered close from several cameras: to see what a torn-looking member really is.

    zoom_view.py <out png> <half> <x0,x1,y0,y1> <design>[,<design>...]
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
png, half = sys.argv[1], sys.argv[2]
x0, x1, y0, y1 = (float(v) for v in sys.argv[3].split(","))
designs = sys.argv[4].split(",")
dirs = [(1.0, -1.0, 0.8), (-1.0, -1.0, 0.8), (1.0, 1.0, 1.4)]
fig, axes = plt.subplots(len(designs), len(dirs), figsize=(8 * len(dirs), 7 * len(designs)), squeeze=False)
for r, design in enumerate(designs):
    m = pv.read(OUT / f"{design}_{half}.ply")
    z0, z1 = m.bounds[4], m.bounds[5]
    part = m.clip_box(bounds=(x0, x1, y0, y1, z0 - 1, z1 + 1), invert=False)
    cen = np.array([0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)])
    up = 1.0 if half == "cover" else -1.0
    for c, (sx, sy, sz) in enumerate(dirs):
        cam = cen + 1.1 * max(x1 - x0, y1 - y0) * np.array([sx, sy, up * sz])
        pl = pv.Plotter(off_screen=True, window_size=(1000, 860))
        pl.set_background("white")
        pl.add_mesh(part, color="#cfcfcf", smooth_shading=False, specular=0.3, ambient=0.3, show_edges=False)
        pl.camera_position = [tuple(cam), tuple(cen), (0, 0, up)]
        img = pl.screenshot(return_img=True)
        pl.close()
        axes[r, c].imshow(img[10:-10, 10:-10])
        axes[r, c].set_axis_off()
        axes[r, c].set_title(f"{design} {half}: x {x0:g}..{x1:g}, y {y0:g}..{y1:g}", fontsize=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / png, dpi=60, bbox_inches="tight")
print(OUT / png)
