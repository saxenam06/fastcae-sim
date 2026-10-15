"""PROTOTYPE (LOP-30) - the section rule seen on the housing: `spline_example.py`'s bracket (two legs from the motor side's
side wall to mount-1's lug) and rib (across the end wall between two bearings' bosses), drawn from the same smooth fields
without the section rule and with it (`LOOP_EXAMPLE_SECTION=4:4`), each cropped round the member and seen from the same
camera. Run both examples first.

    section_compare.py [--out section_compare.png]

Writes the picture into data/first_loop.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"


def shot(mesh, bounds, camera, size=(900, 760)):
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    pl.add_mesh(mesh.clip_box(bounds=bounds, invert=False), color="#cfcfcf", smooth_shading=True, specular=0.35, ambient=0.3)
    pl.camera_position = camera
    img = pl.screenshot(return_img=True)
    pl.close()
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="section_compare.png")
    a = ap.parse_args()
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    m1 = next(m for m in layout["mounts"] if m["name"] == "mount-1")
    c_m = np.asarray(m1["centre"], float)[:2]
    ends = np.array([[-111.5, -46.4], [-137.3, -3.7]])  # spline_example.py's legs' ends at the side wall
    pts = np.vstack([c_m, ends])
    (bx0, by0), (bx1, by1) = pts.min(axis=0) - 26.0, pts.max(axis=0) + 26.0
    brs = [b for b in layout["bearings"] if b["side"] == "-z"][:2]
    ca, cb = (np.asarray(b["axis"], float)[:2] for b in brs)
    ua = (cb - ca) / np.linalg.norm(cb - ca)
    ra, rb = (float(b.get("boss_r") or 30.0) for b in brs)
    r_a, r_b = ca + ua * ra, cb - ua * rb
    (rx0, ry0), (rx1, ry1) = np.minimum(r_a, r_b) - 34.0, np.maximum(r_a, r_b) + 34.0
    views = {
        "bracket": ((bx0, bx1, by0, by1, -95.0, 16.0), np.r_[0.5 * (bx0 + bx1), 0.5 * (by0 + by1), -45.0], np.array([-40.0, -175.0, -150.0])),
        "rib": ((rx0, rx1, ry0, ry1, -75.0, -25.0), np.r_[0.5 * (r_a + r_b), -48.0], np.array([-55.0, -105.0, -120.0])),
    }
    fig, axes = plt.subplots(2, 2, figsize=(16, 13.5))
    for i, (name, (bounds, focal, off)) in enumerate(views.items()):
        for j, (design, label) in enumerate((("spline_example", "without the section rule"), ("spline_example_sec", "with it: round 4, fillet 4"))):
            mesh = pv.read(OUT / f"{design}_motor_side.ply")
            img = shot(mesh, bounds, [tuple(focal + off), tuple(focal), (0, 0, -1)])
            axes[i, j].imshow(img[20:-20, 20:-20])
            axes[i, j].set_axis_off()
            axes[i, j].set_title(f"The {name}, {label}", fontsize=13, loc="left")
    fig.suptitle("The same fields drawn without and with the section rule (the motor side from outside, cropped round the member)",
                 fontsize=14, y=0.995)  # fmt: skip
    fig.tight_layout()
    path = OUT / a.out
    fig.savefig(path, dpi=80, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
