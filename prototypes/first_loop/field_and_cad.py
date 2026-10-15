"""PROTOTYPE (LOP-17) - an optimisation's field and the CAD drawn from it, from the same cameras:
the field's voxels above (the frozen ones grey, the metal it placed orange), the CAD below
(`outcome_cad.py`'s organic body with its exact interfaces), so that each lump of the field can be
followed into the casting.

Run: .venv/Scripts/python.exe prototypes/first_loop/field_and_cad.py <run stem> <design stem>
Reads data/first_loop/<run>.npz and .json, <design>_<half>.brep (or the mesh route's meshes, its
record's `files`) and <design>.json, and grades.json when it holds the design; writes
data/first_loop/field_and_cad_<design>.png.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
import pyvista as pv

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from look import EDGE, METAL, surface  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"
PLACED = (0.80, 0.45, 0.15)  # the metal the optimiser placed, as topo.py's pictures colour it
FROZEN = (0.72, 0.74, 0.77)
VIEWS = (  # look.py's cameras
    ("cover", (0.35, -0.55, 0.75), "the cover, from outside"),
    ("motor_side", (-0.35, -0.55, -0.75), "the motor side, from outside"),
    ("both", (0.75, -0.35, 0.55), "both halves"),
)


def voxels(z, mask: np.ndarray) -> pv.PolyData:
    """The outer surface of the voxels in `mask` (a grid of the run's shape)."""
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    grid = pv.ImageData(dimensions=tuple(n + 1), spacing=(h, h, h), origin=tuple(lo))
    grid.cell_data["on"] = mask.ravel(order="F").astype(np.uint8)
    solid = grid.threshold(0.5, scalars="on")
    return solid.extract_surface() if solid.n_cells else pv.PolyData()


def main(run: str, design: str) -> Path:
    z = np.load(OUT / f"{run}.npz")
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    info = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    n, ks = z["n"].astype(int), int(z["k_split"])
    frozen = np.zeros(int(np.prod(n)), bool)
    placed = np.zeros(int(np.prod(n)), bool)
    frozen[z["elem"][z["frozen"].astype(bool)]] = True
    placed[z["elem"][z["free_e"]]] = np.asarray(z["phys"]) >= 0.5
    frozen, placed = frozen.reshape(n), placed.reshape(n) & ~frozen.reshape(n)
    k = np.arange(n[2])[None, None, :]
    side = {"motor_side": k < ks, "cover": k >= ks, "both": np.ones_like(k, bool)}
    files = {} if info.get("brep") else (info.get("files") or {})  # a B-rep drawing (ribbed_cad.py) is judged and shown as its CAD; FE reads its own mesh
    if files:  # drawn by the mesh route (11 October): its watertight meshes, as look.py reads them
        import mesh_route as mr

        surf = {}
        for h in ("motor_side", "cover"):
            v, f = mr.coarse(mr.load(OUT / files[h]), 2.5)
            surf[h] = pv.PolyData(v, np.hstack([np.full((len(f), 1), 3), f]).ravel())
    else:
        surf = {h: surface(cq.Shape.importBrep(str(OUT / f"{design}_{h}.brep"))) for h in ("motor_side", "cover")}
    edge = {h: surf[h].clean().extract_feature_edges(feature_angle=35.0, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
            for h in surf}  # fmt: skip
    binary = (rec.get("binary") or {}).get("worst")
    grade = next((g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8")) if g.get("stem") == design), None)
    ratio = grade["lines"]["misalignment (worst seat against its line)"]["ratio"] if grade else None
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(2, len(VIEWS)), window_size=(2400, 1500), off_screen=True)
    for col, (which, view, label) in enumerate(VIEWS):
        names = ("motor_side", "cover") if which == "both" else (which,)
        bounds = np.array([surf[h].bounds for h in names])
        box = (bounds[:, 0].min(), bounds[:, 1].max(), bounds[:, 2].min(), bounds[:, 3].max(), bounds[:, 4].min(), bounds[:, 5].max())
        plotter.subplot(0, col)
        for mask, colour in ((frozen, FROZEN), (placed, PLACED)):
            mesh = voxels(z, mask & side[which])
            if mesh.n_cells:
                plotter.add_mesh(mesh, color=colour, ambient=0.3, diffuse=0.75)
        title = f"the optimiser's field: {label}"
        if col == 0:
            title += f"\n{rec['budget_kg']:g} kg; as metal or air {binary:.2f} x its line" if binary else ""
        plotter.add_text(title, font_size=10)
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        plotter.reset_camera(bounds=box)
        plotter.subplot(1, col)
        for h in names:
            plotter.add_mesh(surf[h], color=METAL, smooth_shading=True, specular=0.35, specular_power=20, ambient=0.25, diffuse=0.75)
            plotter.add_mesh(edge[h], color=EDGE, line_width=1.2)
        title = f"its CAD ({design}): {label}"
        if col == 0:
            title += f"\n{info['mass_kg']['total']:.2f} kg" + (f"; FE +shaft {ratio:.2f} x its line" if ratio else "")
        plotter.add_text(title, font_size=10)
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        plotter.reset_camera(bounds=box)
    path = OUT / f"field_and_cad_{design}.png"
    plotter.screenshot(str(path))
    plotter.close()
    print(path.name)
    return path


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
