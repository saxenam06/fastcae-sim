"""A close look at part of a drawn half (LOP-34; a prototype): `closeup.py <design> <half>
<x0,x1,y0,y1> [<azimuth deg> <elevation deg>] [--folder=<dir>]` renders the half's mesh inside the
plan box from the given direction; `data/rib_housing/closeup_<design>_<half>.png`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "rib_housing"


def main() -> None:
    import pyvista as pv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", OUT))
    design, half = args[0], args[1]
    x0, x1, y0, y1 = (float(v) for v in args[2].split(","))
    az = float(args[3]) if len(args) > 3 else 30.0
    el = float(args[4]) if len(args) > 4 else 25.0
    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    mesh = pv.read(str(folder / info["files"][half]))
    mesh = mesh.clip_box([x0, x1, y0, y1, -1e4, 1e4], invert=False).extract_surface()
    mesh = mesh.compute_normals(split_vertices=True, feature_angle=30.0)
    pv.OFF_SCREEN = True
    pl = pv.Plotter(window_size=(1400, 1000), off_screen=True)
    pl.add_mesh(mesh, color=(0.80, 0.82, 0.85), smooth_shading=True)
    pl.set_background("white")
    c = np.asarray(mesh.center)
    a, e = np.radians(az), np.radians(el)
    d = 2.2 * max(x1 - x0, y1 - y0)
    pl.camera_position = [tuple(c + d * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])),
                          tuple(c), (0, 0, 1)]
    pl.add_text(f"{design} {half}: x {x0:g}..{x1:g}, y {y0:g}..{y1:g}", font_size=12, color="black")
    path = folder / f"closeup_{design}_{half}.png"
    pl.screenshot(str(path))
    print(path)


if __name__ == "__main__":
    main()
