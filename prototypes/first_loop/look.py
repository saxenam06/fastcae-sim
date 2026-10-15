"""PROTOTYPE (LOP-9) - a design as the trade's pictures show a housing: shaded metal with its CAD
edges, each half from outside and the two together, so that it can be set beside the engineer's
reference pictures (Ivanov's Fig. 71, the production units).

Run: uv run python prototypes/first_loop/look.py <stem>
Reads data/first_loop/<stem>_<half>.brep and <stem>.json; writes data/first_loop/look_<stem>.png.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
import pyvista as pv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"
METAL = (0.80, 0.82, 0.85)
EDGE = (0.15, 0.16, 0.18)


def surface(shape: cq.Shape) -> pv.PolyData:
    points, faces, base = [], [], 0
    for face in shape.Faces():
        verts, tris = face.tessellate(0.15, 0.2)
        points.extend((v.x, v.y, v.z) for v in verts)
        for a, b, c in tris:
            faces.extend((3, a + base, b + base, c + base))
        base += len(verts)
    return pv.PolyData(np.asarray(points), np.asarray(faces)).compute_normals(split_vertices=True, feature_angle=30.0)


def edges(shape: cq.Shape) -> pv.PolyData:
    """The B-rep's edges as polylines; the seams of round faces left out."""
    lines = []
    for e in shape.Edges():
        try:
            pts = [e.positionAt(t) for t in np.linspace(0.0, 1.0, 24 if e.geomType() != "LINE" else 2)]
        except Exception:  # noqa: BLE001 - a degenerate edge draws nothing
            continue
        lines.append(np.array([(p.x, p.y, p.z) for p in pts]))
    blocks = [pv.lines_from_points(l) for l in lines if len(l) >= 2]
    return blocks[0].merge(blocks[1:]) if blocks else pv.PolyData()


def main(stem: str, face: bool = False) -> None:
    """The four views (`look_<stem>.png`); with `face`, each half's outside seen nearly along the
    pull, as the production photos show a housing's end faces (`look_face_<stem>.png`, LOP-23)."""
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    files = {} if info.get("brep") else (info.get("files") or {})  # a B-rep drawing (ribbed_cad.py) is judged and shown as its CAD; FE reads its own mesh
    if files:  # drawn by the mesh route (11 October): its watertight meshes, their feature edges
        import mesh_route as mr

        surf = {}
        for h in ("motor_side", "cover"):
            mesh = mr.load(OUT / files[h])
            try:
                v, f = mr.coarse(mesh, 2.5)
            except RuntimeError:  # a surface whose coarsening crosses itself is pictured as drawn (FE refuses it on its own)
                v, f = np.asarray(mesh.vertices), np.asarray(mesh.faces)
            # normals split at creases, as the B-rep's: shaded smooth across a flat face's fan of
            # triangles, a plane end wall looked like a cone (11 October 09:05)
            surf[h] = pv.PolyData(v, np.hstack([np.full((len(f), 1), 3), f]).ravel()).compute_normals(split_vertices=True, feature_angle=30.0)
        edge = {h: s.extract_feature_edges(feature_angle=35.0, boundary_edges=True, non_manifold_edges=False, manifold_edges=False) for h, s in surf.items()}
    else:
        halves = {h: cq.Shape.importBrep(str(OUT / f"{stem}_{h}.brep")) for h in ("motor_side", "cover")}
        surf = {h: surface(s) for h, s in halves.items()}
        # An optimiser's outcome drawn as CAD (outcome_cad.py) is thousands of facets: its B-rep
        # edges would be a wire mesh. Its feature edges (the machined faces and bores against the
        # cast skin) are drawn instead, as an organic casting's drawing shows them.
        edge = {
            h: edges(s) if len(s.Faces()) < 2000 else surf[h].clean().extract_feature_edges(feature_angle=35.0, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
            for h, s in halves.items()
        }  # fmt: skip
    pv.OFF_SCREEN = True
    mass = info["mass_kg"]
    if face:
        plotter = pv.Plotter(shape=(1, 2), window_size=(2000, 1000), off_screen=True)
        views = (
            ("cover", (0.12, -0.2, 1.0), f"{stem}: the cover's outside, nearly along the pull ({mass['cover']:.2f} kg)"),
            ("motor_side", (0.12, -0.2, -1.0), f"the motor side's outside ({mass['motor_side']:.2f} kg; the whole {mass['total']:.2f})"),
        )
    else:
        plotter = pv.Plotter(shape=(2, 2), window_size=(1800, 1500), off_screen=True)
        views = (
            ("cover", (0.35, -0.55, 0.75), f"the cover, from outside ({mass['cover']:.2f} kg)"),
            ("motor_side", (-0.35, -0.55, -0.75), f"the motor side, from outside ({mass['motor_side']:.2f} kg)"),
            ("both", (0.75, -0.35, 0.55), f"{stem}: {mass['total']:.2f} kg (the reference 7.73)"),
            ("both", (-0.7, 0.45, -0.55), "from the motor's side"),
        )
    for k, (which, view, title) in enumerate(views):
        plotter.subplot(*((0, k) if face else (k // 2, k % 2)))
        for h in (("motor_side", "cover") if which == "both" else (which,)):
            plotter.add_mesh(surf[h], color=METAL, smooth_shading=True, specular=0.35, specular_power=20, ambient=0.25, diffuse=0.75)
            plotter.add_mesh(edge[h], color=EDGE, line_width=1.2)
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        plotter.add_text(title, font_size=11)
    name = f"look_face_{stem}.png" if face else f"look_{stem}.png"
    plotter.screenshot(str(OUT / name))
    plotter.close()
    print(name)


if __name__ == "__main__":
    main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "face")
