"""PROTOTYPE (PLT-10) - an optimisation run for the Designs page's Optimisation tab.

The run's voxels as surfaces, one part each:
- what was frozen: the skin and the interfaces of a run from the interfaces (LOP-16), the drawn
  shell of one round a shell (LOP-3);
- the material placed (density over 0.5) and the grey zone (0.2 to 0.5).
With them, the contract's parts (gears, shafts, bearings, the differential's case) and the
motor's envelope, in the designs' record format, so the same viewer shows them. The run's
settings, its objective's history and its worst seats ride along.

Run: uv run python prototypes/first_loop/topo_export.py <run stem> [<run stem> ...]
     (a run stem is data/first_loop/<stem>.npz/.json; with none, every run there)
Writes web/src/records/optimisations/<stem>.json (git ignores the folder: the runs live in data/).
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
from view_export import COLOURS, GROUP, VIEW, tessellated  # noqa: E402
from zenryx.api.mesh import encode  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.volumes import volumes  # noqa: E402
from zenryx.geometry.solids import cylinder  # noqa: E402

OUT = ROOT / "data" / "first_loop"
WEB = ROOT / "web" / "src" / "records" / "optimisations"
DENSITY = 2.6e-6  # kg/mm³, as topo.py
PLACED, GREY = 0.5, 0.2
# green for what the optimiser placed: the gears are orange, the bearings blue (view_export's)
TONES = {"frozen": (0.74, 0.77, 0.82), "placed": (0.18, 0.60, 0.42), "grey": (0.70, 0.86, 0.75)}


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
            # (u, v) turns about +axis when (u, v, axis) is cyclic; the face must face along sign·axis
            ccw = (u, v, axis) in ((0, 1, 2), (1, 2, 0), (2, 0, 1))
            first, second = ((a, b, c_), (a, c_, d)) if ccw == (sign > 0) else ((a, c_, b), (a, d, c_))
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


def export(stem: str) -> Path:
    run = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{stem}.npz")
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    elem, frozen, free_e, phys = z["elem"], z["frozen"].astype(bool), z["free_e"], z["phys"]
    grid = {k: np.zeros(int(np.prod(n)), bool) for k in TONES}
    grid["frozen"][elem[frozen]] = True
    grid["placed"][elem[free_e[phys > PLACED]]] = True
    grid["grey"][elem[free_e[(phys > GREY) & (phys <= PLACED)]]] = True
    free_run = "frozen_kg" in run
    run.setdefault("shell", "shell")  # the first runs were round the convex shell and named none
    run.setdefault("objective", "compliance" if run.get("history") and "compliance" in run["history"][0] else None)
    labels = {
        "frozen": "Frozen: the skin and the interfaces" if free_run else f"Frozen: the shell ({run.get('shell', '')})",
        "placed": f"Material placed (density > {PLACED})",
        "grey": f"Grey zone ({GREY}-{PLACED})",
    }
    parts, verts, tris, norms, owner = [], [], [], [], []
    base = 0
    for key in TONES:
        vv, tt, nn = voxel_faces(grid[key].reshape(n), lo, h)
        parts.append({"id": key, "label": labels[key], "kind": key, "group": key, "colour": list(TONES[key])})
        verts.append(vv)
        tris.append(tt + base)
        norms.append(nn)
        owner.append(np.full(len(tt), len(parts) - 1))
        base += len(vv)

    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    space = volumes(spec, chain)
    shapes = [v.solid for v in space.parts]
    roles = [v for v in space.parts]
    # The motor's envelope only for a run on the generator's layout, which had its flange; the
    # contract's has none (the engineer, 10 October 13:21: the vehicle holds the motor).
    flanged = run.get("layout", "grammar4") == "grammar4"
    if flanged:
        axis_in = next(st.axis for st in chain.layout.shafts if st.shaft == "input")
        z_motor = min(st.ends[0] for st in chain.layout.shafts) - 12.0
        shapes.append(cylinder(tuple(axis_in), z_motor - 180.0, z_motor, 204.0))
    pv, pt, owner_parts, faces = tessellated(shapes)
    from zenryx.api.mesh import face_smoothed_normals

    pn = face_smoothed_normals(pv, pt, faces)
    for k, v in enumerate(roles):
        parts.append({"id": f"{v.role}{k}", "label": v.name, "kind": v.role, "group": GROUP.get(v.role, v.role), "colour": list(COLOURS[v.role])})
    if flanged:
        parts.append({"id": "motor", "label": "Motor (its envelope, A25)", "kind": "motor", "group": "motor", "colour": list(COLOURS["motor"])})
    first_context = len(TONES)
    verts.append(pv)
    tris.append(pt + base)
    norms.append(pn)
    owner.append(owner_parts + first_context)

    vertices = np.concatenate(verts) @ VIEW.T
    triangles = np.concatenate(tris)
    normals = np.concatenate(norms) @ VIEW.T
    face_id = np.concatenate(owner)
    mesh = base64.b64encode(encode(vertices, triangles, face_id, normals=normals)).decode("ascii")
    lo_v, hi_v = vertices.min(axis=0), vertices.max(axis=0)

    history = run.get("history", [])
    last = history[-1] if history else {}
    voxel_kg = h**3 * DENSITY
    payload = {
        "schema": 1,
        "stem": stem,
        "title": "From the interfaces" if free_run else f"Round a frozen shell ({run.get('shell', '')})",
        "run": {
            "objective": run.get("objective"),
            "budget_kg": run.get("budget_kg"),
            "frozen_kg": run.get("frozen_kg"),
            "placed_kg": round(float(grid["placed"].sum() * voxel_kg), 2),
            "grey_kg": round(float(grid["grey"].sum() * voxel_kg), 2),
            "voxel_mm": h,
            "iterations": len(history),
            "unknowns": run.get("unknowns"),
            "seconds": round(float(run.get("seconds", 0.0))),
            "element": run.get("element", "hex8, plain (it locks in bending)"),
            "factor": run.get("factor", "a double factor (against the single-precision rule)"),
            "casting": run.get("casting", "none"),
            "worst_ratio": last.get("worst_ratio", last.get("worst_tilt_ratio")),
            "worst_seat": last.get("worst_seat"),
            "converged": bool(history) and history[-1].get("change", 1.0) < 0.01,
        },
        # the first runs (LOP-3's compliance at 1 and 2 kg) logged their compliance under its own name
        "history": [{"it": e["iteration"], "objective": e.get("objective", e.get("compliance")), "worst": e.get("worst_ratio", e.get("worst_tilt_ratio"))} for e in history],
        "parts": parts,
        "mesh": mesh,
        "bbox": [round(float(v), 3) for v in (*lo_v, *hi_v)],
        "faces": len(parts),
    }
    WEB.mkdir(parents=True, exist_ok=True)
    path = WEB / f"{stem}.json"
    body = json.dumps(payload, separators=(",", ":"))
    path.write_text(body, encoding="utf-8")
    print(f"{path.name}: {len(triangles):,} triangles, {len(body) / 1e6:.1f} MB")
    return path


if __name__ == "__main__":
    import names  # every run's name, for the Optimisation tab (names.py)

    stems = sys.argv[1:] or sorted(p.stem for p in OUT.glob("topo*.npz"))
    for s in stems:
        if (OUT / f"{s}.json").exists():
            export(s)
    names.write_indexes()
