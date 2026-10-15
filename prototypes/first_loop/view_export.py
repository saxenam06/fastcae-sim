"""PROTOTYPE (PLT-9) - a design for the Designs page's 3D view: both halves and every part inside.

The housing's halves (their BREPs), and the contract's parts (gears, shafts, bearings, the
differential's case, from `zenryx.domains.gearbox.volumes`) with the motor's envelope (A25's
Ø204 body against the motor face), all in one mesh whose face id is the part's index. Each part
gets its own colour, and the design's recipe, mass, castability and grade ride along. The viewer
paints the parts, hides them, and draws any part below full opacity see-through.

Run: uv run python prototypes/first_loop/view_export.py <stem> [<stem> ...]
Writes web/src/records/designs/<stem>.json (git ignores the folder: the designs live in data/).
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import shell as convex  # noqa: E402
from zenryx.api.mesh import encode, face_smoothed_normals  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.volumes import volumes  # noqa: E402
from zenryx.geometry.solids import cylinder  # noqa: E402

OUT = ROOT / "data" / "first_loop"
WEB = ROOT / "web" / "src" / "records" / "designs"
# As the Contract page's volumes: the shafts horizontal, the output low: (x, y, z) -> (x, z, -y).
VIEW = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
COLOURS = {
    "motor_side": (0.74, 0.77, 0.82),
    "cover": (0.70, 0.80, 0.74),
    "gear": (0.86, 0.58, 0.22),
    "shaft": (0.42, 0.44, 0.50),
    "bearing": (0.22, 0.48, 0.80),
    "carrier": (0.58, 0.36, 0.64),
    "motor": (0.72, 0.30, 0.28),
    "mount": (0.15, 0.58, 0.62),
    "bolt": (0.92, 0.76, 0.20),
}
GROUP = {"motor_side": "housing", "cover": "housing", "gear": "gears", "shaft": "shafts", "bearing": "bearings", "carrier": "differential", "motor": "motor",
         "mount": "mounts", "bolt": "bolts"}  # fmt: skip


def tessellated(shapes, tolerance=0.25, angular=0.3):
    """Every shape's triangles, its index as the face id. Each shape is meshed first to an
    absolute chord: CadQuery's own tessellation is relative to a face's size, coarse on large walls
    (the pitfall castable.py met)."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh

    verts, tris, owner, faces = [], [], [], []
    base, face_count = 0, 0
    for index, shape in enumerate(shapes):
        BRepMesh_IncrementalMesh(shape.wrapped, tolerance, False, angular, True)
        for face in shape.Faces():
            points, tri = face.tessellate(tolerance, angular)
            if not tri:
                continue
            verts.extend((p.x, p.y, p.z) for p in points)
            tris.extend((a + base, b + base, c + base) for a, b, c in tri)
            owner.extend([index] * len(tri))
            faces.extend([face_count] * len(tri))
            base += len(points)
            face_count += 1
    return np.asarray(verts, float).reshape(-1, 3), np.asarray(tris, np.int64).reshape(-1, 3), np.asarray(owner, np.int64), np.asarray(faces, np.int64)


def export(stem: str) -> Path:
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    space = volumes(spec, chain)
    parts, shapes, meshed = [], [], []
    files = {} if info.get("brep") else (info.get("files") or {})  # a B-rep drawing (ribbed_cad.py) is judged and shown as its CAD; FE reads its own mesh
    for half, label in (("motor_side", "Housing: motor side"), ("cover", "Housing: cover")):
        if half in files:  # drawn by the mesh route (11 October): its mesh, coarsened for the page
            import mesh_route as mr

            meshed.append(mr.coarse(mr.load(OUT / files[half]), 3.0))
        else:
            shapes.append(cq.Shape.importBrep(str(OUT / f"{stem}_{half}.brep")))
        parts.append({"id": half, "label": label, "kind": half, "group": "housing"})
    for k, v in enumerate(space.parts):
        if v.role in ("mount", "bolt"):  # the housing's own CAD holds its mounts and bolts' bosses
            continue
        shapes.append(v.solid)
        parts.append({"id": f"{v.role}{k}", "label": v.name, "kind": v.role, "group": GROUP.get(v.role, v.role)})
    # The motor's envelope only for a design with a flange (the contract's has none: the vehicle
    # holds the motor, the engineer, 10 October 13:21).
    if "motor_ring_thickness" in info["settings"] and info["z"].get("motor") is not None:
        axis_in = next(b["axis"] for b in info["bearings"] if b["shaft"] == "input")
        z_motor = info["z"]["motor"] - info["settings"]["motor_ring_thickness"]
        shapes.append(cylinder(tuple(axis_in), z_motor - 180.0, z_motor, 204.0))
        parts.append({"id": "motor", "label": "Motor (its envelope, A25)", "kind": "motor", "group": "motor"})
    for p in parts:
        p["colour"] = list(COLOURS[p["kind"]])

    vertices, triangles, owner, faces = tessellated(shapes)
    vertices = vertices @ VIEW.T
    normals = face_smoothed_normals(vertices, triangles, faces) if len(triangles) else np.zeros((0, 3))
    if meshed:  # the meshed halves are parts 0 and 1: their triangles first, each its own face (for picking)
        # (15 October 14:15; the engineer, 13:49: "remove this vertical edgy stretchy shapes") their shading smooth, the
        # vertices split where two triangles meet at more than 40 degrees (the bores, the split face, the rims stay sharp):
        # shaded triangle by triangle, a coarsened field mesh's long triangles on its tall faces showed as stripes
        import pyvista as pv

        owner = owner + len(meshed)
        faces = faces + sum(len(t) for _, t in meshed)
        mv, mt, mo, mf, mn, base, face0 = [], [], [], [], [], 0, 0
        for i, (v, t) in enumerate(meshed):
            pd = pv.PolyData(np.asarray(v, float) @ VIEW.T, np.hstack([np.full((len(t), 1), 3), t]).ravel())
            pd = pd.compute_normals(point_normals=True, cell_normals=False, split_vertices=True, feature_angle=40.0,
                                    consistent_normals=False, auto_orient_normals=False)  # fmt: skip
            v2, t2 = np.asarray(pd.points, float), pd.faces.reshape(-1, 4)[:, 1:].astype(np.int64)
            mv.append(v2)
            mt.append(t2 + base)
            mo.append(np.full(len(t2), i, np.int64))
            mf.append(face0 + np.arange(len(t2), dtype=np.int64))
            mn.append(np.asarray(pd.point_data["Normals"], float)[t2.ravel()])
            base += len(v2)
            face0 += len(t2)
        vertices = np.vstack([*mv, vertices])
        triangles = np.vstack([*mt, triangles + base])
        owner = np.concatenate([*mo, owner])
        faces = np.concatenate([*mf, faces])
        normals = np.vstack([*mn, normals])
    mesh = base64.b64encode(encode(vertices, triangles, owner, normals=normals)).decode("ascii")
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)

    # Only results made after the design's latest build: an older one judged a CAD since replaced.
    built = (OUT / f"{stem}.json").stat().st_mtime
    cast = OUT / f"castable_{stem}.json"
    castable = json.loads(cast.read_text(encoding="utf-8"))["halves"] if cast.exists() and cast.stat().st_mtime >= built else None
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))} if (OUT / "grades.json").exists() else {}
    fe = OUT / f"fe_{stem}.json"
    grade = grades.get(stem) if fe.exists() and fe.stat().st_mtime >= built else None
    payload = {
        "schema": 1,
        "stem": stem,
        "recipe": info.get("recipe"),
        "mass_kg": info["mass_kg"],
        "parts": parts,
        "mesh": mesh,
        "bbox": [round(float(v), 3) for v in (*lo, *hi)],
        "faces": len(shapes),
        "castable": [
            {"half": h["half"], "undercut_cm2": h["undercut_cm2"], "closed_voids": h["closed_voids"], "thin_cm2": h["thinner_than_least_wall_cm2"]}
            for h in castable
        ] if castable else None,
        "grade": {
            "drive_um": grade["lines"]["displacement, peak drive"]["value_um"],  # peak drive alone is graded (grade.GRADED_CASES)
            "misalignment": grade["lines"]["misalignment (worst seat against its line)"]["ratio"],
            "first_mode_hz": grade.get("first_mode_hz"),
            "clashes": grade["lines"]["orders"]["clashes"],
        } if grade else None,
    }  # fmt: skip
    WEB.mkdir(parents=True, exist_ok=True)
    path = WEB / f"{stem}.json"
    body = json.dumps(payload, separators=(",", ":"))
    path.write_text(body, encoding="utf-8")
    print(f"{path.name}: {len(triangles):,} triangles, {len(body) / 1e6:.1f} MB")
    return path


if __name__ == "__main__":
    import names  # every design's name and kind, for the Designs page (names.py)

    for s in sys.argv[1:]:
        export(s)
    names.write_indexes()
