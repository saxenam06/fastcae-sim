"""PROTOTYPE (LOP) - pictures of the housing's halves, every face coloured by its role.

Run: uv run python prototypes/first_loop/picture.py [stem]      (default stem: shell)
Reads data/first_loop/<stem>_<half>.brep and <stem>.json; writes data/first_loop/<stem>.png.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
import pyvista as pv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "data" / "first_loop"
COLOURS = {
    "wall": (0.78, 0.79, 0.80),
    "seat": (0.20, 0.45, 0.85),
    "bolt": (0.90, 0.55, 0.15),
    "mount": (0.85, 0.20, 0.20),
    "motor": (0.55, 0.30, 0.65),
    "split": (0.20, 0.65, 0.40),
    "rib": (0.95, 0.80, 0.25),
}


def mesh_of(shape: cq.Shape, names: dict[str, str]) -> pv.PolyData:
    points, faces, colours = [], [], []
    base = 0
    for k, face in enumerate(shape.Faces()):
        verts, tris = face.tessellate(0.3, 0.4)
        if not tris:
            continue
        role = names.get(str(k), "wall").split(":")[0]
        points.extend((v.x, v.y, v.z) for v in verts)
        for a, b, c in tris:
            faces.extend((3, a + base, b + base, c + base))
            colours.append(COLOURS.get(role, COLOURS["wall"]))
        base += len(verts)
    mesh = pv.PolyData(np.asarray(points), np.asarray(faces))
    mesh.cell_data["rgb"] = (np.asarray(colours) * 255).astype(np.uint8)
    return mesh


def main(stem: str = "shell") -> None:
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(1, 3), window_size=(1800, 640), off_screen=True)
    halves = {}
    for half in ("motor_side", "cover"):
        shape = cq.Shape.importBrep(str(OUT / f"{stem}_{half}.brep"))
        halves[half] = mesh_of(shape, info["faces"][half])
    gap = 40.0
    views = (
        ("both halves, apart", None),
        ("motor side, from the split", "motor_side"),
        ("cover, from the split", "cover"),
    )
    for i, (title, only) in enumerate(views):
        plotter.subplot(0, i)
        for half, mesh in halves.items():
            if only and half != only:
                continue
            shown = mesh.copy()
            if only is None and half == "cover":
                shown.translate((0, 0, gap), inplace=True)
            plotter.add_mesh(shown, scalars="rgb", rgb=True, smooth_shading=False)
        plotter.add_text(title, font_size=10)
        if only == "motor_side":
            plotter.view_vector((0.0, 0.0, 1.0), viewup=(0.0, -1.0, 0.0))
        elif only == "cover":
            plotter.view_vector((0.0, 0.0, -1.0), viewup=(0.0, -1.0, 0.0))
        else:
            plotter.view_vector((0.6, -0.5, 0.8), viewup=(0.0, -1.0, 0.0))
    mass = info["mass_kg"]
    plotter.subplot(0, 0)
    plotter.add_text(
        f"\n\n{mass['total']:.2f} kg  (seats blue, flange bolts orange, mounts red, motor purple)",
        font_size=8,
    )
    plotter.screenshot(str(OUT / f"{stem}.png"))
    print("wrote", OUT / f"{stem}.png")


if __name__ == "__main__":
    main(*sys.argv[1:])
