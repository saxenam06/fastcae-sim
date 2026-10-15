"""PROTOTYPE (LOP-30) - One window of a drawn half, flat-shaded (each triangle's own normal) beside smooth-shaded (vertex normals averaged): are
a face's stripes its geometry or its triangles' shading?

    shade_compare.py <design> <half> <x0,x1,y0,y1> <out png> [dir x,y,z]
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design, half = sys.argv[1], sys.argv[2]
x0, x1, y0, y1 = (float(v) for v in sys.argv[3].split(","))
png = sys.argv[4]
d = np.asarray([float(v) for v in sys.argv[5].split(",")], float) if len(sys.argv) > 5 else np.array([1.0, -1.0, 0.8])
m = pv.read(OUT / f"{design}_{half}.ply")
z0, z1 = m.bounds[4], m.bounds[5]
part = m.clip_box(bounds=(x0, x1, y0, y1, z0 - 1, z1 + 1), invert=False).extract_surface()
cen = np.array([0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)])
up = 1.0 if half == "cover" else -1.0
cam = cen + 1.1 * max(x1 - x0, y1 - y0) * np.array([d[0], d[1], up * d[2]])
fig, axes = plt.subplots(1, 2, figsize=(18, 8))
for ax, smooth in zip(axes, (False, True), strict=True):
    pl = pv.Plotter(off_screen=True, window_size=(1000, 860))
    pl.set_background("white")
    mesh = part.compute_normals(split_vertices=False, feature_angle=60.0) if smooth else part
    pl.add_mesh(mesh, color="#cfcfcf", smooth_shading=smooth, specular=0.3, ambient=0.3)
    pl.camera_position = [tuple(cam), tuple(cen), (0, 0, up)]
    ax.imshow(pl.screenshot(return_img=True)[10:-10, 10:-10])
    pl.close()
    ax.set_axis_off()
    ax.set_title(f"{design} {half}: {'smooth shading (vertex normals)' if smooth else 'flat shading (each triangle)'}", loc="left")
fig.tight_layout()
fig.savefig(OUT / png, dpi=60, bbox_inches="tight")
print(OUT / png)
