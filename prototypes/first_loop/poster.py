"""PROTOTYPE (LOP) - one design on one picture: the housing from both sides, every face coloured by
its role, and two sections through the shafts' axes coloured by the FE's displacement, so that the
structure inside the walls (a cored double wall, a lattice, the bosses) shows with what it does.

Run: uv run python prototypes/first_loop/poster.py <stem>
Reads data/first_loop/<stem>.json, <stem>_<half>.brep, fe_<stem>.json and .npz, and grades.json;
writes data/first_loop/poster_<stem>.png.
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

from picture import mesh_of  # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"
GAP = 0.0  # the halves shown assembled


def volume_grids(field, case: int):
    """Each half's TET mesh as a pyvista grid, its displacement magnitude (µm) on the nodes."""
    grids = []
    for half in ("motor_side", "cover"):
        nodes = field[f"{half}_nodes"]
        tets = field[f"{half}_tets"][:, :4]
        off = int(field[f"{half}_offset"])
        u = field["u"][off : off + 3 * len(nodes), case].reshape(-1, 3)
        cells = np.hstack([np.full((len(tets), 1), 4), tets]).ravel()
        grid = pv.UnstructuredGrid(cells, np.full(len(tets), pv.CellType.TETRA), nodes)
        grid.point_data["um"] = 1000 * np.linalg.norm(u, axis=1)
        grids.append(grid)
    return grids


def section(plotter, grids, a, b, title, top):
    """The housing cut by the plane through the shaft axes at `a` and `b` (both along z), the far
    side kept, coloured by displacement."""
    d = np.array([b[0] - a[0], b[1] - a[1], 0.0])
    normal = np.cross(d / np.linalg.norm(d), (0.0, 0.0, 1.0))
    origin = (a[0], a[1], 0.0)
    for grid in grids:
        cut = grid.clip(normal=normal, origin=origin, invert=False)
        plotter.add_mesh(cut, scalars="um", cmap="turbo", clim=(0, top), show_scalar_bar=False, show_edges=False)
    plotter.add_text(title, font_size=9)
    # looking at the cut face, along the plane's normal, z to the right
    plotter.view_vector(tuple(-normal), viewup=(0.0, 0.0, 1.0))
    plotter.camera.azimuth = 0


def main(stem: str) -> None:
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    fe = json.loads((OUT / f"fe_{stem}.json").read_text(encoding="utf-8"))
    field = np.load(OUT / f"fe_{stem}.npz")
    grade = next(g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8")) if g["stem"] == stem)
    axes = {b["shaft"]: b["axis"] for b in info["bearings"]}
    cases = list(fe["cases"])

    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(2, 2), window_size=(1800, 1500), off_screen=True)
    halves = {h: mesh_of(cq.Shape.importBrep(str(OUT / f"{stem}_{h}.brep")), info["faces"][h]) for h in ("motor_side", "cover")}

    plotter.subplot(0, 0)
    for mesh in halves.values():
        plotter.add_mesh(mesh, scalars="rgb", rgb=True, smooth_shading=False)
    plotter.view_vector((0.55, -0.45, 0.75), viewup=(0.0, -1.0, 0.0))
    plotter.add_text("the cover's side", font_size=11)

    plotter.subplot(0, 1)
    for mesh in halves.values():
        plotter.add_mesh(mesh, scalars="rgb", rgb=True, smooth_shading=False)
    plotter.view_vector((-0.55, -0.45, -0.75), viewup=(0.0, -1.0, 0.0))
    plotter.add_text("the motor's side (motor flange purple, mounts red)", font_size=11)

    drive = volume_grids(field, cases.index("peak drive"))
    reverse = volume_grids(field, cases.index("peak reverse"))
    top = max(float(g.point_data["um"].max()) for g in drive + reverse)

    plotter.subplot(1, 0)
    section(plotter, drive, axes["intermediate"], axes["output"],
            "section through the intermediate and output shafts: peak drive, µm", top)  # fmt: skip
    plotter.add_scalar_bar("µm", vertical=False, position_x=0.25, position_y=0.04, width=0.5, n_labels=5)

    plotter.subplot(1, 1)
    section(plotter, reverse, axes["input"], axes["intermediate"],
            "section through the input and intermediate shafts: peak reverse, µm", top)  # fmt: skip

    lines = grade["lines"]
    d, r = lines["displacement, peak drive"]["value_um"], lines["displacement, peak reverse"]["value_um"]
    mis = lines["misalignment (worst seat against its line)"]["ratio"]
    clash = "none" if not lines["orders"]["clashes"] else "; ".join(lines["orders"]["clashes"])
    plotter.subplot(0, 0)
    plotter.add_text(
        f"\n\n{stem}: {fe['mass_kg']:.2f} kg (the reference 7.73)\n"
        f"bearing beds {d:.0f} / {r:.0f} µm, drive / reverse (the reference 52 / 138)\n"
        f"worst misalignment {mis:.2f} of its line (must reach 1), with the shaft's own bend\n"
        f"first mode {fe['modes_hz'][0]:.0f} Hz; order clashes: {clash}",
        font_size=9,
    )
    path = OUT / f"poster_{stem}.png"
    plotter.screenshot(str(path))
    print("wrote", path)


if __name__ == "__main__":
    main(sys.argv[1])
