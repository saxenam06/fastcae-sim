"""A drawn design as the trade's pictures show a housing (moved from
`prototypes/first_loop/look.py`: `main`, the mesh route's branch; LOP-33): shaded metal with its
feature edges, each half from outside and the two together (`look_<design>.png`), or each half's
outside nearly along the pull, as the production photos show end faces (`look_face_<design>.png`).
Needs a display (Xvfb on a Linux worker) for VTK's offscreen rendering."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from zenryx.domains.gearbox.housing import mesh as mr

METAL = (0.80, 0.82, 0.85)
EDGE = (0.15, 0.16, 0.18)
PICTURE_EDGE = 2.5  # mm: the pictured surface's triangles


def look(design: str, out: Path, face: bool = False) -> Path:
    import pyvista as pv

    info = json.loads((out / f"{design}.json").read_text(encoding="utf-8"))
    surf = {}
    for h in ("motor_side", "cover"):
        mesh = mr.load(out / info["files"][h])
        try:
            v, f = mr.coarse(mesh, PICTURE_EDGE)
        # a surface whose coarsening crosses itself is pictured as drawn (FE refuses it on its own)
        except RuntimeError:
            v, f = np.asarray(mesh.vertices), np.asarray(mesh.faces)
        # normals split at creases: shaded smooth across a flat face's fan of triangles, a plane end
        # wall looked like a cone
        surf[h] = pv.PolyData(v, np.hstack([np.full((len(f), 1), 3), f]).ravel()).compute_normals(
            split_vertices=True, feature_angle=30.0
        )
    edge = {
        h: s.extract_feature_edges(
            feature_angle=35.0, boundary_edges=True, non_manifold_edges=False, manifold_edges=False
        )
        for h, s in surf.items()
    }
    pv.OFF_SCREEN = True
    mass = info["mass_kg"]
    if face:
        plotter = pv.Plotter(shape=(1, 2), window_size=(2000, 1000), off_screen=True)
        views = (
            (
                "cover",
                (0.12, -0.2, 1.0),
                f"{design}: the cover's outside, nearly along the pull ({mass['cover']:.2f} kg)",
            ),
            (
                "motor_side",
                (0.12, -0.2, -1.0),
                f"the motor side's outside ({mass['motor_side']:.2f} kg; the whole "
                f"{mass['total']:.2f})",
            ),
        )
    else:
        plotter = pv.Plotter(shape=(2, 2), window_size=(1800, 1500), off_screen=True)
        views = (
            ("cover", (0.35, -0.55, 0.75), f"the cover, from outside ({mass['cover']:.2f} kg)"),
            (
                "motor_side",
                (-0.35, -0.55, -0.75),
                f"the motor side, from outside ({mass['motor_side']:.2f} kg)",
            ),
            ("both", (0.75, -0.35, 0.55), f"{design}: {mass['total']:.2f} kg (the reference 7.73)"),
            ("both", (-0.7, 0.45, -0.55), "from the motor's side"),
        )
    for k, (which, view, title) in enumerate(views):
        plotter.subplot(*((0, k) if face else (k // 2, k % 2)))
        for h in ("motor_side", "cover") if which == "both" else (which,):
            plotter.add_mesh(
                surf[h],
                color=METAL,
                smooth_shading=True,
                specular=0.35,
                specular_power=20,
                ambient=0.25,
                diffuse=0.75,
            )
            plotter.add_mesh(edge[h], color=EDGE, line_width=1.2)
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        plotter.add_text(title, font_size=11)
    path = out / (f"look_face_{design}.png" if face else f"look_{design}.png")
    plotter.screenshot(str(path))
    plotter.close()
    return path
