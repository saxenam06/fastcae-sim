"""The Designs page's records of a design made by the final workflow (moved from the prototypes'
`view_export.py`, `topo_export.py`, `process_export.py` and `names.py`, only what a mesh-route
design of flow E needs; LOP-33):

- `design`: the design's two halves (their meshes, coarsened for the page, shaded smooth with sharp
  creases) and the contract's parts, one mesh whose face id is the part's index, with its mass,
  castability and grade (`designs/<design>.json`; the organic body before its cuts as
  `<design>_organic`);
- `run`: the optimisation's voxels (frozen, placed, grey) with the contract's parts, its settings
  and history (`optimisations/<run>.json`);
- `process`: the design's flow, a tab a step, each with its card (`process/<design>.json`), and FE's
  outer surface with the displacement and von Mises stress in peak drive
  (`process/<design>_fe.json`);
- `index`: the design's and its run's names and summaries in each folder's `_index.json`, newest
  first. Entries made by other tools are kept as they are.

The folders are git-ignored: the designs live in data/.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import numpy as np

from zenryx.api.mesh import encode, face_smoothed_normals
from zenryx.api.volumes import VIEW
from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import mesh as mr
from zenryx.domains.gearbox.volumes import volumes
from zenryx.physics.tet10 import nodal_von_mises
from zenryx.workflow.grade import CASE, MISALIGNMENT, REFERENCE

COLOURS = {
    "motor_side": (0.74, 0.77, 0.82),
    "cover": (0.70, 0.80, 0.74),
    "gear": (0.86, 0.58, 0.22),
    "shaft": (0.42, 0.44, 0.50),
    "bearing": (0.22, 0.48, 0.80),
    "carrier": (0.58, 0.36, 0.64),
    "mount": (0.15, 0.58, 0.62),
    "bolt": (0.92, 0.76, 0.20),
}
GROUP = {
    "motor_side": "housing",
    "cover": "housing",
    "gear": "gears",
    "shaft": "shafts",
    "bearing": "bearings",
    "carrier": "differential",
    "mount": "mounts",
    "bolt": "bolts",
}
HALVES = (("motor_side", "Housing: motor side"), ("cover", "Housing: cover"))
PAGE_EDGE = 3.0  # mm: a half's triangles on the page
# degrees: normals split where two triangles meet at more (the bores, the split face, the rims stay
# sharp)
CREASE = 40.0
PLACED, GREY = 0.5, 0.2  # a run's voxel densities shown as placed and as grey
TONES = {"frozen": (0.74, 0.77, 0.82), "placed": (0.18, 0.60, 0.42), "grey": (0.70, 0.86, 0.75)}
DRAWN = "the mesh route"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _write(path: Path, payload: dict, compact: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, separators=(",", ":")) if compact else json.dumps(payload, indent=1)
    path.write_text(body, encoding="utf-8")
    return path


def _grades(out: Path) -> dict:
    graded = out / "grades.json"
    return (
        {g["stem"]: g for g in json.loads(graded.read_text(encoding="utf-8"))}
        if graded.exists()
        else {}
    )


def tessellated(shapes, tolerance=0.25, angular=0.3):
    """Every shape's triangles, its index as the face id; each shape meshed first to an absolute
    chord (CadQuery's own tessellation is relative to a face's size, coarse on large walls)."""
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
    return (
        np.asarray(verts, float).reshape(-1, 3),
        np.asarray(tris, np.int64).reshape(-1, 3),
        np.asarray(owner, np.int64),
        np.asarray(faces, np.int64),
    )


def _parts(contract: Path, skip=("mount", "bolt")) -> list:
    spec, _ = load_and_validate(contract)
    return [v for v in volumes(spec, complete_chain(spec)).parts if v.role not in skip]


def design(stem: str, out: Path, records: Path, contract: Path) -> Path:
    """`designs/<stem>.json`: both halves (their meshes) and the contract's parts (the housing's own
    mesh holds its mounts and bolts' bosses)."""
    import pyvista as pv

    info = _json(out / f"{stem}.json")
    parts = [
        {"id": half, "label": label, "kind": half, "group": "housing"} for half, label in HALVES
    ]
    context = _parts(contract)
    parts += [
        {"id": f"{v.role}{k}", "label": v.name, "kind": v.role, "group": GROUP.get(v.role, v.role)}
        for k, v in enumerate(context)
    ]
    for p in parts:
        p["colour"] = list(COLOURS[p["kind"]])
    vertices, triangles, owner, faces = tessellated([v.solid for v in context])
    vertices = vertices @ VIEW.T
    normals = (
        face_smoothed_normals(vertices, triangles, faces) if len(triangles) else np.zeros((0, 3))
    )
    # the halves first, each triangle its own face (for picking), shaded smooth with their normals
    # split at creases: shaded triangle by triangle, a coarsened field mesh's long triangles on its
    # tall faces showed as stripes (15 October)
    meshed = [mr.coarse(mr.load(out / info["files"][half]), PAGE_EDGE) for half, _ in HALVES]
    owner = owner + len(meshed)
    faces = faces + sum(len(t) for _, t in meshed)
    mv, mt, mo, mf, mn, base, face0 = [], [], [], [], [], 0, 0
    for i, (v, t) in enumerate(meshed):
        pd = pv.PolyData(
            np.asarray(v, float) @ VIEW.T, np.hstack([np.full((len(t), 1), 3), t]).ravel()
        )
        pd = pd.compute_normals(
            point_normals=True,
            cell_normals=False,
            split_vertices=True,
            feature_angle=CREASE,
            consistent_normals=False,
            auto_orient_normals=False,
        )
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
    normals = np.vstack([*mn, normals])
    mesh = base64.b64encode(encode(vertices, triangles, owner, normals=normals)).decode("ascii")
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    # only results made after the design's latest drawing: an older one judged a drawing since
    # replaced
    built = (out / f"{stem}.json").stat().st_mtime
    cast = out / f"castable_{stem}.json"
    castable = _json(cast)["halves"] if cast.exists() and cast.stat().st_mtime >= built else None
    fe = out / f"fe_{stem}.json"
    grade = _grades(out).get(stem) if fe.exists() and fe.stat().st_mtime >= built else None
    payload = {
        "schema": 1,
        "stem": stem,
        "recipe": info.get("recipe"),
        "mass_kg": info["mass_kg"],
        "parts": parts,
        "mesh": mesh,
        "bbox": [round(float(v), 3) for v in (*lo, *hi)],
        "faces": len(context),
        "castable": [
            {
                "half": h["half"],
                "undercut_cm2": h["undercut_cm2"],
                "closed_voids": h["closed_voids"],
                "thin_cm2": h["thinner_than_least_wall_cm2"],
            }
            for h in castable
        ]
        if castable
        else None,
        "grade": {
            "drive_um": grade["lines"]["displacement, peak drive"]["value_um"],
            "misalignment": grade["lines"][MISALIGNMENT]["ratio"],
            "first_mode_hz": grade.get("first_mode_hz"),
            "clashes": grade["lines"]["orders"]["clashes"],
        }
        if grade
        else None,
    }
    return _write(records / "designs" / f"{stem}.json", payload)


def voxel_faces(mask: np.ndarray, lo: np.ndarray, h: float):
    """The boundary of a voxel set: every face between a voxel in the set and one outside it, two
    triangles each, with its outward normal per corner. Returns (vertices, triangles, normals)."""
    padded = np.pad(mask, 1)
    verts, tris, norms = [], [], []
    base = 0
    for axis in range(3):
        u, v = [a for a in range(3) if a != axis]
        for sign in (-1, 1):
            face = (padded & ~np.roll(padded, -sign, axis=axis))[1:-1, 1:-1, 1:-1]
            idx = np.argwhere(face).astype(float)
            if not len(idx):
                continue
            idx[:, axis] += 1.0 if sign > 0 else 0.0
            corners = []
            for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                c = idx.copy()
                c[:, u] += du
                c[:, v] += dv
                corners.append(c)
            pts = np.stack(corners, axis=1).reshape(-1, 3) * h + lo
            q = len(idx)
            a, b, c_, d = (np.arange(q) * 4 + k for k in range(4))
            # (u, v) turns about +axis when (u, v, axis) is cyclic; the face must face along
            # sign·axis
            ccw = (u, v, axis) in ((0, 1, 2), (1, 2, 0), (2, 0, 1))
            first, second = (
                ((a, b, c_), (a, c_, d)) if ccw == (sign > 0) else ((a, c_, b), (a, d, c_))
            )
            tri = np.concatenate([np.stack(first, 1), np.stack(second, 1)]) + base
            nrm = np.zeros(3)
            nrm[axis] = sign
            verts.append(pts)
            tris.append(tri)
            norms.append(np.tile(nrm, (3 * len(tri), 1)))
            base += len(pts)
    if not verts:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3))
    return np.concatenate(verts), np.concatenate(tris), np.concatenate(norms)


def run(stem: str, out: Path, records: Path, contract: Path) -> Path:
    """`optimisations/<stem>.json`: the run's voxels as surfaces (frozen, placed, grey) with the
    contract's parts."""
    rec = _json(out / f"{stem}.json")
    z = np.load(out / f"{stem}.npz")
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    elem, frozen, free_e, phys = z["elem"], z["frozen"].astype(bool), z["free_e"], z["phys"]
    grid = {k: np.zeros(int(np.prod(n)), bool) for k in TONES}
    grid["frozen"][elem[frozen]] = True
    grid["placed"][elem[free_e[phys > PLACED]]] = True
    grid["grey"][elem[free_e[(phys > GREY) & (phys <= PLACED)]]] = True
    labels = {
        "frozen": "Frozen: the skin and the interfaces",
        "placed": f"Material placed (density > {PLACED})",
        "grey": f"Grey zone ({GREY}-{PLACED})",
    }
    parts, verts, tris, norms, owner = [], [], [], [], []
    base = 0
    for key in TONES:
        vv, tt, nn = voxel_faces(grid[key].reshape(n), lo, h)
        parts.append(
            {"id": key, "label": labels[key], "kind": key, "group": key, "colour": list(TONES[key])}
        )
        verts.append(vv)
        tris.append(tt + base)
        norms.append(nn)
        owner.append(np.full(len(tt), len(parts) - 1))
        base += len(vv)
    context = _parts(contract, skip=())
    pv_, pt, owner_parts, faces = tessellated([v.solid for v in context])
    parts += [
        {
            "id": f"{v.role}{k}",
            "label": v.name,
            "kind": v.role,
            "group": GROUP.get(v.role, v.role),
            "colour": list(COLOURS[v.role]),
        }
        for k, v in enumerate(context)
    ]
    verts.append(pv_)
    tris.append(pt + base)
    norms.append(face_smoothed_normals(pv_, pt, faces))
    owner.append(owner_parts + len(TONES))
    vertices = np.concatenate(verts) @ VIEW.T
    triangles = np.concatenate(tris)
    mesh = base64.b64encode(
        encode(vertices, triangles, np.concatenate(owner), normals=np.concatenate(norms) @ VIEW.T)
    ).decode("ascii")
    lo_v, hi_v = vertices.min(axis=0), vertices.max(axis=0)
    spec, _ = load_and_validate(contract)
    voxel_kg = h**3 * value_in(spec.manufacturing.material.density, "t/mm3") * 1e3
    history = rec.get("history", [])
    last = history[-1] if history else {}
    payload = {
        "schema": 1,
        "stem": stem,
        "title": "From the interfaces",
        "run": {
            "objective": rec.get("objective"),
            "budget_kg": rec.get("budget_kg"),
            "frozen_kg": rec.get("frozen_kg"),
            "placed_kg": round(float(grid["placed"].sum() * voxel_kg), 2),
            "grey_kg": round(float(grid["grey"].sum() * voxel_kg), 2),
            "voxel_mm": h,
            "iterations": len(history),
            "unknowns": rec.get("unknowns"),
            "seconds": round(float(rec.get("seconds", 0.0))),
            "element": rec.get("element"),
            "factor": rec.get("factor"),
            "casting": rec.get("casting"),
            "worst_ratio": last.get("worst_ratio"),
            "worst_seat": last.get("worst_seat"),
            "converged": bool(history) and history[-1].get("change", 1.0) < 0.01,
        },
        "history": [
            {"it": e["iteration"], "objective": e.get("objective"), "worst": e.get("worst_ratio")}
            for e in history
        ],
        "parts": parts,
        "mesh": mesh,
        "bbox": [round(float(v), 3) for v in (*lo_v, *hi_v)],
        "faces": len(parts),
    }
    return _write(records / "optimisations" / f"{stem}.json", payload)


def _b64(a: np.ndarray, dtype) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype=dtype).tobytes()).decode("ascii")


def fe_surface(design_: str, out: Path, contract: Path) -> dict | None:
    """FE's outer surface (each outer TET10 face as its corner triangle, turned outward) and its
    fields in peak drive."""
    path = out / f"fe_{design_}.npz"
    if not path.exists():
        return None
    spec, _ = load_and_validate(contract)
    material = spec.manufacturing.material
    young, poisson = value_in(material.youngs_modulus, "MPa"), value_in(material.poisson_ratio, "1")
    z = np.load(path)
    positions, triangles, groups, values_u, values_vm, vectors = [], [], [], [], [], []
    base = 0
    faces_local = np.array([[0, 1, 2], [0, 1, 3], [1, 2, 3], [0, 2, 3]])
    for g, half in enumerate(("motor_side", "cover")):
        nodes = z[f"{half}_nodes"]
        tets = z[f"{half}_tets"].astype(np.int64)
        off = int(z[f"{half}_offset"])
        u = z["u"][off : off + 3 * len(nodes), 0].reshape(-1, 3)  # peak drive
        vm = nodal_von_mises(nodes, tets, young, poisson, u)
        tri = tets[:, faces_local].reshape(-1, 3)
        _, inverse, counts = np.unique(
            np.sort(tri, axis=1), axis=0, return_inverse=True, return_counts=True
        )
        outer = np.nonzero(counts[inverse.ravel()] == 1)[0]
        tet_of, face_of = outer // 4, outer % 4
        tri_out = tets[tet_of[:, None], faces_local[face_of]]
        centre = nodes[tets[tet_of, :4]].mean(axis=1)
        p = nodes[tri_out]
        inward = (
            np.einsum(
                "ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), p.mean(axis=1) - centre
            )
            < 0
        )
        tri_out[inward] = tri_out[inward][:, [1, 0, 2]]
        used, local = np.unique(tri_out, return_inverse=True)
        positions.append(nodes[used] @ VIEW.T)
        triangles.append(local.reshape(-1, 3) + base)
        groups.append(np.full(len(tri_out), g, np.uint16))
        values_u.append(1000.0 * np.linalg.norm(u[used], axis=1))
        values_vm.append(vm[used])
        vectors.append(u[used] @ VIEW.T)
        base += len(used)
    pos = np.vstack(positions)
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    rec = _json(out / f"fe_{design_}.json")
    return {
        "schema": 1,
        "design": design_,
        "skin": {
            "positions": _b64(pos, "<f4"),
            "triangles": _b64(np.vstack(triangles), "<u4"),
            "groups": _b64(np.concatenate(groups), "<u2"),
            "nodes": _b64(np.arange(len(pos)), "<u4"),
            "groupNames": [label for _, label in HALVES],
        },
        "fields": {
            "displacement": {
                "unit": "µm",
                "label": "Displacement, peak drive",
                "values": _b64(np.concatenate(values_u), "<f4"),
            },
            "von Mises": {
                "unit": "MPa",
                "label": "von Mises stress, peak drive",
                "values": _b64(np.concatenate(values_vm), "<f4"),
            },
        },
        "vectors": _b64(np.vstack(vectors), "<f4"),
        "bbox": [float(v) for v in (*lo, *hi)],
        "mesh": {
            "unknowns": rec.get("unknowns"),
            "modes_hz": rec.get("modes_hz"),
            "clashes": rec.get("order_clashes"),
        },
    }


def _optimise_card(rec_run: dict) -> list[list[str]]:
    """A run's numbers, from its metal-or-air check (`binary`)."""
    binary = rec_run.get("binary") or {}
    return [
        ["Compliance", f"{binary.get('value', 0):.1f} N·mm"],
        ["Worst tilt", f"{binary.get('worst', 0):.3f} × its line"],
        [
            "Worst bed",
            f"{binary['bed_worst']:.2f} × {REFERENCE[CASE]:g} µm"
            if binary.get("bed_worst") is not None
            else "not held",
        ],
        ["Placed", f"{binary.get('mass_kg', 0):.2f} kg"],
        ["Iterations", str(len(rec_run.get("history", [])))],
    ]


def _grade_rows(g: dict | None, halves: list[dict]) -> dict:
    """The grade's lines with their limits and verdicts, and castability's."""
    if not g:
        return {"rows": [], "verdict": None}
    lines = g["lines"]
    beds, tilt = (
        lines["displacement, peak drive"],
        lines[MISALIGNMENT],
    )
    orders, mass = lines["orders"], lines["mass"]
    rows = [
        [
            "Bearing beds, peak drive",
            f"{beds['value_um']:.1f} µm",
            f"≤ {beds['to_beat_um']:.1f} µm, the reference's",
            beds["pass"],
        ],
        [
            "Worst tilt, against its line",
            f"{tilt['ratio']:.2f} ×",
            "≤ 1 × (the shaft's lean included)",
            tilt["pass"],
        ],
        [
            "Modes against the mesh orders",
            f"first {g.get('first_mode_hz') or 0:.0f} Hz"
            + (f"; {'; '.join(orders['clashes'])}" if orders["clashes"] else ""),
            "no mode within 3 % of an order",
            orders["pass"],
        ],
        [
            "Mass",
            f"{mass['kg']:.2f} kg",
            f"≤ {mass['to_beat_kg']:.2f} kg, the reference's",
            mass["pass"],
        ],
    ]
    if halves:
        ok = all(
            h.get("pull_rule") == "PASS" and h.get("least_wall_rule") == "PASS" for h in halves
        )
        rows.append(
            [
                "Castability",
                "; ".join(
                    f"{h['half'].replace('_', ' ')} undercut {100 * h['undercut_share']:.1f} %, "
                    f"{h['thinner_than_least_wall_cm2']:.0f} cm² under 4 mm"
                    for h in halves
                ),
                "no undercut along the pull, no wall under 4 mm",
                ok,
            ]
        )
    return {"rows": rows, "verdict": bool(g.get("pass")) and all(r[3] for r in rows)}


def process(design_: str, out: Path, records: Path, contract: Path) -> Path:
    """`process/<design>.json` from the flow's record (`flow_<design>.json`), and
    `process/<design>_fe.json`."""
    info = _json(out / f"{design_}.json")
    flow_rec = _json(out / f"flow_{design_}.json")
    flow, run_steps = flow_rec["flow"], flow_rec["steps"]
    rec_run = _json(out / f"{info.get('outcome_of', '')}.json")
    g = _grades(out).get(design_) or {}
    lines = g.get("lines", {})
    halves = _json(out / f"castable_{design_}.json").get("halves", [])
    s = info["settings"]
    beds_to_beat, mass_to_beat = REFERENCE[CASE], REFERENCE["mass_kg"]
    layout_bolts = len(_json(out / "contract.json").get("bolts", []))
    card = {
        "contract": [
            ["Least wall", f"{s['wall']:g} mm"],
            ["Split flange", f"{s['flange_thickness']:g} mm each half"],
            ["Sealing land", f"{s['land_width']:g} mm round the inside"],
            ["Bolts", f"{len(info.get('bolts', []))}, Ø{s['bolt_boss']:g} bosses"],
            ["Load case", "peak drive"],
            ["Mass to beat", f"{mass_to_beat:.2f} kg"],
        ],
        "setup": [
            ["Voxels", f"{rec_run.get('voxel_mm', 0):g} mm"],
            ["Fixed", f"{rec_run.get('frozen_kg', 0):.2f} kg"],
            ["To place", f"{rec_run.get('budget_kg', 0) - rec_run.get('frozen_kg', 0):.2f} kg"],
            ["Route", "cast from the split"],
            ["Greatest member", f"{(rec_run.get('max_member') or {}).get('mm', '-')} mm"],
        ],
        "draw": [
            ["Mass", f"{info['mass_kg']['total']:.2f} kg"],
            ["Motor side", f"{info['mass_kg']['motor_side']:.2f} kg"],
            ["Cover", f"{info['mass_kg']['cover']:.2f} kg"],
            ["Bolts joining", f"{len(info.get('bolts', []))} of {layout_bolts}"],
        ],
        "castable": [
            [
                h["half"].replace("_", " "),
                f"undercut {100 * h['undercut_share']:.1f} %, "
                f"{h['thinner_than_least_wall_cm2']:.0f} cm² under 4 mm",
            ]
            for h in halves
        ],
        "fe": [
            [
                "Beds, drive",
                f"{lines.get('displacement, peak drive', {}).get('value_um', 0):.1f} µm (≤ "
                f"{beds_to_beat:g})",
            ],
            ["Worst tilt", f"{lines.get(MISALIGNMENT, {}).get('ratio', 0):.2f} × its line"],
            ["First mode", f"{g.get('first_mode_hz') or 0:.0f} Hz"],
            ["Clashes", ", ".join(lines.get("orders", {}).get("clashes", [])) or "none"],
            ["Mass", f"{g.get('mass_kg', 0):.2f} kg (≤ {mass_to_beat:.2f})"],
            ["Verdict", "PASS" if g.get("pass") else "fail"],
        ],
    }
    steps = [
        {
            "id": "contract",
            "label": "Contract",
            "method": "the contract's elements, from zenryx's spaces",
            "view": {"kind": "volumes"},
            "card": card["contract"],
        },
        {
            "id": "setup",
            "label": "Set-up",
            "method": "the optimiser's voxels: fixed, kept out, free",
            "view": {"kind": "volumes", "voxels": True},
            "card": card["setup"],
        },
    ]
    # A stage drawn as two tabs (the drawing: its body, then the design; FE: its mesh, then its
    # results) carries its time on the first alone, so the tabs add up to the flow's time; a stage
    # run beside another says so ("beside": its id).
    for s_ in run_steps:
        sid = s_["id"]
        if sid == "optimise":
            out_run = (s_.get("outputs") or [info.get("outcome_of", "")])[0]
            steps.append(
                {
                    **s_,
                    "view": {"kind": "field", "run": out_run},
                    "card": _optimise_card(_json(out / f"{out_run}.json")),
                }
            )
        elif sid == "draw":
            steps.append(
                {
                    **s_,
                    "label": s_["label"] + ": the body",
                    "id": "body",
                    "view": {"kind": "design", "stem": f"{design_}_organic"},
                    "card": [["Note", "the inside still solid: cut in the next tab"]],
                }
            )
            steps.append(
                {
                    **s_,
                    "label": "Machined",
                    "id": "machined",
                    "seconds": None,
                    "of": "body",
                    "view": {"kind": "design", "stem": design_},
                    "card": card["draw"],
                }
            )
        elif sid == "fe":
            steps.append(
                {
                    **s_,
                    "label": "FE mesh",
                    "id": "fe_mesh",
                    "view": {"kind": "fe", "field": None},
                    "card": [["Note", s_.get("note", "")]],
                }
            )
            steps.append(
                {
                    **s_,
                    "label": "Results",
                    "id": "results",
                    "seconds": None,
                    "of": "fe_mesh",
                    "view": {"kind": "fe", "field": "displacement"},
                    "card": card["fe"],
                }
            )
        elif sid == "castable":
            beside = {"seconds": None, "beside": "fe_mesh"} if s_.get("note") == "beside FE" else {}
            steps.append(
                {
                    **s_,
                    **beside,
                    "view": {"kind": "design", "stem": design_},
                    "card": card["castable"],
                }
            )
        elif sid == "grade":
            steps.append(
                {**s_, "view": {"kind": "grade", **_grade_rows(g or None, halves)}, "card": []}
            )
        elif sid != "setup":
            steps.append({**s_, "view": {"kind": "none"}, "card": []})
    total = sum(
        float(s_.get("seconds") or 0) for s_ in run_steps if s_.get("note") != "beside FE"
    )  # a step run beside another counts once
    path = _write(
        records / "process" / f"{design_}.json",
        {"schema": 1, "design": design_, "flow": flow, "steps": steps, "seconds": round(total, 1)},
        compact=False,
    )
    fe = fe_surface(design_, out, contract)
    if fe is not None:
        _write(records / "process" / f"{design_}_fe.json", fe)
    return path


def run_title(rec_run: dict) -> str:
    """A final run's name: what it holds, its budget, its method."""
    what = (
        "Least metal, tilt and beds held"
        if rec_run.get("objective") == "mass_tilt"
        else str(rec_run.get("objective"))
    )
    return f"{what} · {rec_run.get('budget_kg', 0):g} kg · GCMMA"


def _summary(design_: str, rec_run: dict, info: dict, out: Path) -> dict:
    """The design's row in the Designs page's comparison: the optimiser's budget, its fixed and
    placed metal, the drawing's mass, FE's beds, worst tilt and first mode (the grade's), and
    castability."""
    row = {
        "cad_kg": (info.get("mass_kg") or {}).get("total"),
        "budget_kg": rec_run.get("budget_kg"),
        "fixed_kg": rec_run.get("frozen_kg"),
        "placed_kg": (rec_run.get("binary") or {}).get("mass_kg"),
    }
    g = _grades(out).get(design_)
    if g:
        lines = g["lines"]
        drive = lines["displacement, peak drive"]
        tilt, orders, mass = (
            lines[MISALIGNMENT],
            lines["orders"],
            lines["mass"],
        )
        row.update(
            drive_um=drive["value_um"],
            tilt=tilt["ratio"],
            mode_hz=g.get("first_mode_hz"),
            clashes=len(orders["clashes"]),
            passes={
                "beds": drive["pass"],
                "tilt": tilt["pass"],
                "mode": orders["pass"],
                "mass": mass["pass"],
            },
            to_beat={"kg": mass["to_beat_kg"], "drive_um": drive["to_beat_um"]},
        )
    halves = _json(out / f"castable_{design_}.json").get("halves")
    if halves:
        row["castable"] = all(
            h.get("pull_rule") == "PASS" and h.get("least_wall_rule") == "PASS" for h in halves
        )
        row["undercut"] = max(h.get("undercut_share", 0.0) for h in halves)
    return row


def index(design_: str, out: Path, records: Path) -> None:
    """The design's, its organic body's and its run's entries in the folders' `_index.json`, newest
    first; the other entries kept as they are."""
    info = _json(out / f"{design_}.json")
    run_ = info.get("outcome_of", "")
    rec_run = _json(out / f"{run_}.json")
    title = run_title(rec_run)
    t_run = (out / f"{run_}.json").stat().st_mtime
    t_design = (out / f"{design_}.json").stat().st_mtime
    entries = {
        "optimisations": {run_: {"title": title, "method": "GCMMA", "time": t_run}},
        "designs": {
            f"{design_}_organic": {
                "title": f"{title} · organic shape",
                "source": "optimisation",
                "run": run_,
                "time": t_design,
                "summary": None,
            },
            design_: {
                "title": f"{title} · mesh",
                "source": "optimisation",
                "run": run_,
                "time": t_design,
                "summary": _summary(design_, rec_run, info, out),
            },
        },
    }
    for folder, new in entries.items():
        path = records / folder / "_index.json"
        current = _json(path)
        current.update(new)
        _write(path, dict(sorted(current.items(), key=lambda kv: -kv[1]["time"])), compact=False)


def write_all(design_: str, out: Path, records: Path, contract: Path) -> None:
    """Every record of a design the final workflow made: its view, its body's, its run's, the names;
    then its process."""
    info = _json(out / f"{design_}.json")
    design(design_, out, records, contract)
    design(f"{design_}_organic", out, records, contract)
    run(info["outcome_of"], out, records, contract)
    index(design_, out, records)
