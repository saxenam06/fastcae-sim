"""PROTOTYPE (LOP-30) - Close-ups of a design's two halves: each half's plan cut into four quadrants, each rendered from an oblique camera
looking at its side walls, to see the side members (jagged fins, spikes)."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design = sys.argv[1] if len(sys.argv) > 1 else "baseline2_spl2"
fig, axes = plt.subplots(2, 4, figsize=(28, 13))
for r, half in enumerate(("cover", "motor_side")):
    m = pv.read(OUT / f"{design}_{half}.ply")
    x0, x1, y0, y1, z0, z1 = m.bounds
    xm, ym = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    quads = [(x0, xm, y0, ym, (-1, -1)), (xm, x1, y0, ym, (1, -1)), (x0, xm, ym, y1, (-1, 1)), (xm, x1, ym, y1, (1, 1))]
    for c, (a0, a1, b0, b1, (sx, sy)) in enumerate(quads):
        part = m.clip_box(bounds=(a0 - 1, a1 + 1, b0 - 1, b1 + 1, z0 - 1, z1 + 1), invert=False)
        cen = np.array([0.5 * (a0 + a1), 0.5 * (b0 + b1), 0.5 * (z0 + z1)])
        up = 1.0 if half == "cover" else -1.0  # look from the half's outside
        cam = cen + np.array([sx * 160.0, sy * 160.0, up * 170.0])
        pl = pv.Plotter(off_screen=True, window_size=(900, 760))
        pl.set_background("white")
        pl.add_mesh(part, color="#cfcfcf", smooth_shading=False, specular=0.3, ambient=0.3)
        pl.camera_position = [tuple(cam), tuple(cen), (0, 0, up)]
        img = pl.screenshot(return_img=True)
        pl.close()
        axes[r, c].imshow(img[20:-20, 20:-20])
        axes[r, c].set_axis_off()
        axes[r, c].set_title(f"{half}: x {a0:.0f}..{a1:.0f}, y {b0:.0f}..{b1:.0f}", fontsize=11, loc="left")
fig.tight_layout()
path = OUT / f"closeups_{design}.png"
fig.savefig(path, dpi=70, bbox_inches="tight")
print(path)
