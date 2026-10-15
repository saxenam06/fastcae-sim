"""PROTOTYPE (LOP-31) - What stands round each mount's lug and its bracket's kept-clear rooms: the optimiser's placed cubes
(density 0.5 or more) within reach of the lug, sorted into the cap (over a room's far end, inside its circle), the side
(beside the room or the lug) and the rest; for each, whether the drawn half holds its centre. The picture, one row a mount:
the optimiser's cubes (placed orange, fixed grey) and the drawing, from the same camera, the rooms as blue glass.

    mount_cap.py <run stem> <design> <out png> [half=motor_side]
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
half = sys.argv[4] if len(sys.argv) > 4 else "motor_side"
z = np.load(OUT / f"{run}.npz")
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
h, lo, n = float(z["h"]), np.asarray(z["lo"], float), np.asarray(z["n"], int)
elem, frozen, phys = z["elem"], z["frozen"].astype(bool), np.asarray(z["phys"], float)
free = elem[~frozen]
pl_ijk = np.column_stack(np.unravel_index(free[phys >= 0.5], tuple(n)))
placed = lo + h * (pl_ijk + 0.5)
fx_ijk = np.column_stack(np.unravel_index(elem[frozen], tuple(n)))
fixed = lo + h * (fx_ijk + 0.5)
surf = pv.read(OUT / f"{design}_{half}.ply")
rooms = {b["name"]: b for b in lay["brackets"]}
z_split = float(lay["z"]["split"])
REACH = 44.0  # mm round the lug's axis


def cubes(pts: np.ndarray, colour: str) -> pv.PolyData | None:
    if len(pts) == 0:
        return None
    return pv.PolyData(pts).glyph(geom=pv.Cube(x_length=h * 0.96, y_length=h * 0.96, z_length=h * 0.96), scale=False, orient=False)


fig, axes = plt.subplots(len(lay["mounts"]), 2, figsize=(18, 8 * len(lay["mounts"])), squeeze=False)
report = {}
for r, m in enumerate(lay["mounts"]):
    c = np.asarray(m["centre"], float)
    mine = [b for b in lay["brackets"] if b["name"].startswith(m["name"] + " ")]
    rb = max(float(b["radius"]) for b in mine)
    zr0 = min(float(b["z"][0]) for b in mine)
    zr1 = max(float(b["z"][1]) for b in mine)
    rad = np.hypot(placed[:, 0] - c[0], placed[:, 1] - c[1])
    near = rad < REACH
    pts, rr = placed[near], rad[near]
    kept = np.asarray(pv.PolyData(pts).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)["SelectedPoints"]).astype(bool) if len(pts) else np.zeros(0, bool)
    cap = (rr <= rb + 0.5 * h) & ((pts[:, 2] > zr1) | (pts[:, 2] < zr0))
    side = ~cap & (pts[:, 2] >= zr0) & (pts[:, 2] <= zr1)
    rest = ~cap & ~side
    rep = {}
    for name, sel in (("cap", cap), ("side", side), ("rest", rest)):
        layers = sorted({round(float(v), 2) for v in pts[sel, 2]})
        rep[name] = {"cubes": int(sel.sum()), "kept": int((sel & kept).sum()), "lost": int((sel & ~kept).sum()), "z": layers[:12]}
    report[m["name"]] = {"lug_z": m["z"], "rooms_z": [zr0, zr1], "room_r": rb, **rep}
    # the picture: field left, drawing right, the same camera from outside the half, low over the lug
    box = (c[0] - REACH - 6, c[0] + REACH + 6, c[1] - REACH - 6, c[1] + REACH + 6, lay["z"]["lo"] - 1, z_split + 1)
    part = surf.clip_box(bounds=box, invert=False)
    fnear = np.hypot(fixed[:, 0] - c[0], fixed[:, 1] - c[1]) < REACH
    cen = np.array([c[0], c[1], 0.5 * (lay["z"]["lo"] + z_split)])
    radial = c / max(np.hypot(*c), 1e-9)
    cam = cen + 150.0 * np.array([radial[0] * 0.8 + 0.35, radial[1] * 0.8 - 0.35, -0.55])
    for col, what in enumerate(("field", "drawing")):
        pl = pv.Plotter(off_screen=True, window_size=(1100, 950))
        pl.set_background("white")
        if what == "field":
            fm = cubes(fixed[fnear], "#9a9a9a")
            if fm is not None:
                pl.add_mesh(fm, color="#a8a8a8", opacity=1.0)
            for sel, colour in ((cap, "#d62728"), (side, "#ff9f40"), (rest, "#f2c27a")):
                pm = cubes(pts[sel], colour)
                if pm is not None:
                    pl.add_mesh(pm, color=colour)
        else:
            pl.add_mesh(part, color="#cfcfcf", smooth_shading=True, specular=0.3, ambient=0.3)
            lost = cubes(pts[cap & ~kept], "#d62728")
            if lost is not None:
                pl.add_mesh(lost, color="#d62728", opacity=0.55)
        for b in mine:
            cyl = pv.Cylinder(center=(c[0], c[1], 0.5 * (b["z"][0] + b["z"][1])), direction=(0, 0, 1), radius=float(b["radius"]), height=float(b["z"][1]) - float(b["z"][0]), resolution=60)
            pl.add_mesh(cyl, color="#3a7bd5", opacity=0.22)
        pl.camera_position = [tuple(cam), tuple(cen), (0, 0, -1)]
        img = pl.screenshot(return_img=True)
        pl.close()
        ax = axes[r, col]
        ax.imshow(img[10:-10, 10:-10])
        ax.set_axis_off()
        rp = report[m["name"]]
        if what == "field":
            ax.set_title(f"{m['name']}: the optimiser's cubes (red: over the room's end, {rp['cap']['cubes']}; orange: beside it, {rp['side']['cubes']}); blue: the bracket's rooms", fontsize=12, loc="left")
        else:
            ax.set_title(f"{m['name']}: the drawing (red glass: the cap's cubes it lost, {rp['cap']['lost']} of {rp['cap']['cubes']})", fontsize=12, loc="left")
fig.tight_layout()
fig.savefig(OUT / png, dpi=60, bbox_inches="tight")
print(json.dumps(report, indent=1))
print(OUT / png)
