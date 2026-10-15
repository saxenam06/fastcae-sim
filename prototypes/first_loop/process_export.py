"""PROTOTYPE (LOP-21) - a design's process for the Designs page: its flow's steps, each with its name,
its method, its time, the view the page draws for it and its card, and FE's surface with its fields.

The engineer, 11 October 02:08: "every type of end-to-end flow you try on the UI, so that I can see
each process with its own tabs... the tab names may differ as the approach changes". So each design
carries its flow: flow B (the mesh route) from `propose.py`'s `flow_<design>.json`; flow A (the CAD
route, the OCC drawing) from the night's record and logs (`FLOW_A`).

Writes web/src/records/process/<design>.json (the steps) and <design>_fe.json (FE's outer surface,
each TET10 face split into four on its mid-side nodes, with each node's displacement in peak drive
(µm), its von Mises stress (MPa, `fastcae_fe.nodal_stress`, checked by `stress_check.py`) and its
displacement vector for the deformed shape). Both git-ignored, as the designs' records are.

Run: .venv/Scripts/python.exe prototypes/first_loop/process_export.py <design> [<design> ...]
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from fastcae_fe import nodal_stress  # noqa: E402

OUT = ROOT / "data" / "first_loop"
TARGET = ROOT / "web" / "src" / "records" / "process"
VIEW = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])  # the pages' turn: (x, y, z) -> (x, z, -y)
YOUNG, POISSON = 69_000.0, 0.33  # MPa: the contract's EN AC-42100 T6, as fe.py's

FLOW_A = {
    "id": "A",
    "name": "The CAD route",
    "words": "The optimisation in two stages; the drawing in OCC right after it (the smoothed field sewn into a B-rep, fused with the exact shell, cut exact one boolean at a time, healed); FE from the B-rep (gmsh); castability on the B-rep",
}


def b64(a: np.ndarray, dtype) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype=dtype).tobytes()).decode("ascii")


def seconds_in(log: Path, pattern: str) -> float | None:
    if not log.exists():
        return None
    m = re.search(pattern, log.read_text(encoding="utf-8", errors="replace"))
    return float(m.group(1)) if m else None


def span_of(log: Path) -> float | None:
    """The time between a log's first and last stamped lines (h:m:s)."""
    if not log.exists():
        return None
    stamps = re.findall(r"^\[(\d\d):(\d\d):(\d\d)\]", log.read_text(encoding="utf-8", errors="replace"), re.M)
    if len(stamps) < 2:
        return None
    t = [int(h) * 3600 + int(m) * 60 + int(s) for h, m, s in stamps]
    return float((t[-1] - t[0]) % 86400)


def fe_surface(design: str) -> dict | None:
    """FE's outer surface and its fields from fe_<design>.npz."""
    path = OUT / f"fe_{design}.npz"
    if not path.exists():
        return None
    z = np.load(path)
    positions, triangles, groups, values_u, values_vm, vectors = [], [], [], [], [], []
    base = 0
    for g, half in enumerate(("motor_side", "cover")):
        nodes = z[f"{half}_nodes"]
        tets = z[f"{half}_tets"].astype(np.int64)
        off = int(z[f"{half}_offset"])
        u = z["u"][off : off + 3 * len(nodes), 0].reshape(-1, 3)  # peak drive
        _, vm = nodal_stress(nodes, tets, np.full(len(tets), YOUNG), np.full(len(tets), POISSON), u, len(nodes))
        # the outer faces: corner triangles held by one tet
        faces_local = np.array([[0, 1, 2], [0, 1, 3], [1, 2, 3], [0, 2, 3]])
        mids = {(0, 1): 4, (1, 2): 5, (0, 2): 6, (0, 3): 7, (1, 3): 8, (2, 3): 9}
        tri = tets[:, faces_local].reshape(-1, 3)
        key = np.sort(tri, axis=1)
        _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        outer = np.nonzero(counts[inverse.ravel()] == 1)[0]
        tet_of, face_of = outer // 4, outer % 4
        # each outer face as its corner triangle, turned outward (split into four on its mid-side
        # nodes the page's file was 16-19 MB a design; the contours read the same at a quarter)
        del mids
        tri_out = tets[tet_of[:, None], faces_local[face_of]]
        centre = nodes[tets[tet_of, :4]].mean(axis=1)
        p = nodes[tri_out]
        normal = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        inward = np.einsum("ij,ij->i", normal, p.mean(axis=1) - centre) < 0
        tri_out[inward] = tri_out[inward][:, [1, 0, 2]]
        out_tris = tri_out
        used, local = np.unique(out_tris, return_inverse=True)
        positions.append(nodes[used] @ VIEW.T)
        triangles.append(local.reshape(-1, 3) + base)
        groups.append(np.full(len(out_tris), g, np.uint16))
        values_u.append(1000.0 * np.linalg.norm(u[used], axis=1))
        values_vm.append(vm[used])
        vectors.append(u[used] @ VIEW.T)
        base += len(used)
    pos = np.vstack(positions)
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    rec = json.loads((OUT / f"fe_{design}.json").read_text(encoding="utf-8"))
    return {
        "schema": 1,
        "design": design,
        "skin": {"positions": b64(pos, "<f4"), "triangles": b64(np.vstack(triangles), "<u4"), "groups": b64(np.concatenate(groups), "<u2"),
                 "nodes": b64(np.arange(len(pos)), "<u4"), "groupNames": ["Housing: motor side", "Housing: cover"]},  # fmt: skip
        "fields": {
            "displacement": {"unit": "µm", "label": "Displacement, peak drive", "values": b64(np.concatenate(values_u), "<f4")},
            "von Mises": {"unit": "MPa", "label": "von Mises stress, peak drive", "values": b64(np.concatenate(values_vm), "<f4")},
        },
        "vectors": b64(np.vstack(vectors), "<f4"),
        "bbox": [float(v) for v in (*lo, *hi)],
        "mesh": {"unknowns": rec.get("unknowns"), "modes_hz": rec.get("modes_hz"), "clashes": rec.get("order_clashes")},
    }


FLOW_C = {
    "id": "C",
    "name": "The ribbed CAD",
    "words": "The optimisation in one run (flow B's); its field read in plan as a designer reads it (deep members as ribs along their centre-lines, shallow ones as pads, each under the envelope over their ends); drawn as exact CAD (B-rep) on the contract's exact shell, pockets down to its 4 mm wall; FE on the CAD filled on a 1.5 mm grid with its machined faces exact; castability on the B-rep",
}


def flow_c(design: str, info: dict) -> list[dict]:
    """Flow C's stages (`ribbed_cad.py`): the optimisation (its run's own time), the reading and the
    drawing (the drawing's record), FE and castability (their logs)."""
    run = info.get("outcome_of", "")
    rec_run = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")) if (OUT / f"{run}.json").exists() else {}
    fe_log = OUT / f"fe_{design}.log"
    return [
        {"id": "optimise", "label": "Optimisation", "method": "flow B's run: stiffness, every bearing's tilt and bed held; one run, GCMMA with MMA's dual",
         "seconds": rec_run.get("seconds"), "ok": True, "outputs": [run]},
        {"id": "reading", "label": "Reading", "method": "the field in plan: deep members (18 mm or more proud) as ribs along their centre-lines, 6-12 mm as their area over their length; shallow ones as pads; each under the envelope over the members' ends",
         "seconds": None, "of": "body", "ok": True},
        {"id": "draw", "label": "Drawing", "method": "OCC: each rib a plate topped by the envelope along it, drawn where 3 mm or more proud, kept 1.5 mm off every cylinder; posts, struts into the mounts, flat-topped pads; fused pairwise onto the exact shell; every exact cut",
         "seconds": info.get("seconds"), "ok": True},
        {"id": "fe", "label": "FE", "method": "the CAD's parts filled on a 1.5 mm grid, contoured, the machined faces cut exact (manifold3d); TetGen's tets, cuDSS TET10, peak drive and 12 modes",
         "seconds": seconds_in(fe_log, r"; (\d+) s in all"), "ok": True, "note": next((ln.split("] ", 1)[1] for ln in fe_log.read_text(encoding="utf-8", errors="replace").splitlines() if "unknowns (" in ln), "") if fe_log.exists() else ""},
        {"id": "castable", "label": "Castability", "method": "rays along the pull and into the metal, on the B-rep", "seconds": span_of(OUT / f"castable_{design}.log"), "ok": True},
        {"id": "grade", "label": "Grade", "method": "every line of the contract, peak drive", "seconds": None, "ok": True},
    ]  # fmt: skip


def flow_of(design: str, info: dict) -> tuple[dict, list[dict]]:
    """The design's flow and its stages' times: propose.py's record (flow B), the ribbed drawing's
    (flow C), or flow A from the logs."""
    path = OUT / f"flow_{design}.json"
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        return rec["flow"], rec["steps"]
    if info.get("drawing") == "ribs":
        return FLOW_C, flow_c(design, info)
    run = info.get("outcome_of", "")
    rec_run = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")) if (OUT / f"{run}.json").exists() else {}
    start = rec_run.get("start")
    steps = []
    if start:
        steps.append({"id": "optimise_stiff", "label": "Optimisation: stiffness", "method": "the stiffness alone, GCMMA (interior-point subproblem)",
                      "seconds": seconds_in(OUT / "run_flange_stiff.log", r"done in (\d+) s"), "ok": True, "outputs": [start]})  # fmt: skip
        steps.append({"id": "optimise", "label": "Optimisation: tilt held", "method": "from the stiff design, every bearing's tilt held",
                      "seconds": seconds_in(OUT / "run_flange_tilt.log", r"done in (\d+) s"), "ok": True, "outputs": [run]})  # fmt: skip
    else:
        steps.append({"id": "optimise", "label": "Optimisation", "method": "GCMMA", "seconds": rec_run.get("seconds"), "ok": True, "outputs": [run]})
    steps.append({"id": "draw", "label": "Drawing (OCC)", "method": "the field smoothed and remeshed, sewn into a B-rep, fused with the exact shell, cut exact one boolean at a time, healed",
                  "seconds": span_of(OUT / f"build_{design}.log"), "ok": True})  # fmt: skip
    steps.append({"id": "castable", "label": "Castability", "method": "rays along the pull and into the metal, on the B-rep", "seconds": span_of(OUT / f"castable_{design}.log"), "ok": True})
    steps.append({"id": "fe", "label": "FE", "method": "gmsh from the B-rep, cuDSS TET10, peak drive and 12 modes",
                  "seconds": seconds_in(OUT / f"fe_{design}.log", r"; (\d+) s in all"), "ok": True,
                  "note": f"meshed in {seconds_in(OUT / f'fe_{design}.log', r'meshed in (\d+) s'):.0f} s"})  # fmt: skip
    steps.append({"id": "grade", "label": "Grade", "method": "every line of the contract, peak drive", "seconds": None, "ok": True})
    return FLOW_A, steps


def run_record(run: str) -> dict:
    path = OUT / f"{run}.json"
    return json.loads(path.read_text(encoding="utf-8")) if run and path.exists() else {}


def optimise_card(run: str) -> list[list[str]]:
    """A run's numbers, from its metal-or-air check (`binary`)."""
    rec_run = run_record(run)
    binary = rec_run.get("binary") or {}
    return [["Compliance", f"{binary.get('value', 0):.1f} N·mm"], ["Worst tilt", f"{binary.get('worst', 0):.3f} × its line"],
            ["Worst bed", f"{binary['bed_worst']:.2f} × 52.2 µm" if binary.get("bed_worst") is not None else "not held"],
            ["Placed", f"{binary.get('mass_kg', 0):.2f} kg"], ["Iterations", str(len(rec_run.get("history", [])))]]  # fmt: skip


def grade_rows(design: str) -> dict:
    """The grade's lines (grade.py, peak drive) with their limits and verdicts, and castability's."""
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))} if (OUT / "grades.json").exists() else {}
    g = grades.get(design)
    if not g:
        return {"rows": [], "verdict": None}
    lines = g["lines"]
    beds, tilt = lines["displacement, peak drive"], lines["misalignment (worst seat against its line)"]
    orders, mass = lines["orders"], lines["mass"]
    rows = [
        ["Bearing beds, peak drive", f"{beds['value_um']:.1f} µm", f"≤ {beds['to_beat_um']:.1f} µm, the reference's", beds["pass"]],
        ["Worst tilt, against its line", f"{tilt['ratio']:.2f} ×", "≤ 1 × (the shaft's lean included)", tilt["pass"]],
        ["Modes against the mesh orders", f"first {g.get('first_mode_hz') or 0:.0f} Hz" + (f"; {'; '.join(orders['clashes'])}" if orders["clashes"] else ""),
         "no mode within 3 % of an order", orders["pass"]],
        ["Mass", f"{mass['kg']:.2f} kg", f"≤ {mass['to_beat_kg']:.2f} kg, the reference's", mass["pass"]],
    ]  # fmt: skip
    cast = OUT / f"castable_{design}.json"
    if cast.exists():
        halves = json.loads(cast.read_text(encoding="utf-8"))["halves"]
        ok = all(h.get("pull_rule") == "PASS" and h.get("least_wall_rule") == "PASS" for h in halves)
        rows.append(["Castability (castable.py)", "; ".join(f"{h['half'].replace('_', ' ')} undercut {100 * h['undercut_share']:.1f} %, {h['thinner_than_least_wall_cm2']:.0f} cm² under 4 mm" for h in halves),
                     "no undercut along the pull, no wall under 4 mm", ok])  # fmt: skip
    return {"rows": rows, "verdict": bool(g.get("pass")) and all(r[3] for r in rows)}


def cards(design: str, info: dict) -> dict:
    """The numbers each step's card shows."""
    run = info.get("outcome_of", "")
    rec_run = run_record(run)
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))} if (OUT / "grades.json").exists() else {}
    g = grades.get(design) or {}
    lines = g.get("lines", {})
    cast = OUT / f"castable_{design}.json"
    halves = json.loads(cast.read_text(encoding="utf-8"))["halves"] if cast.exists() else []
    s = info["settings"]
    out = {
        "contract": [["Least wall", f"{s['wall']:g} mm"], ["Split flange", f"{s['flange_thickness']:g} mm each half"],
                     ["Sealing land", f"{s.get('land_width', 10):g} mm round the inside"], ["Bolts", f"{len(info.get('bolts', []))}, Ø{s['bolt_boss']:g} bosses"],
                     ["Load case", "peak drive"], ["Mass to beat", "7.73 kg"]],  # fmt: skip
        "setup": [["Voxels", f"{rec_run.get('voxel_mm', 6):g} mm"], ["Fixed", f"{rec_run.get('frozen_kg', 0):.2f} kg"],
                  ["To place", f"{rec_run.get('budget_kg', 0) - rec_run.get('frozen_kg', 0):.2f} kg"], ["Route", "cast from the split"],
                  ["Greatest member", f"{(rec_run.get('max_member') or {}).get('mm', '-')} mm"]],  # fmt: skip
        "draw": [["Mass", f"{info['mass_kg']['total']:.2f} kg"], ["Motor side", f"{info['mass_kg']['motor_side']:.2f} kg"],
                 ["Cover", f"{info['mass_kg']['cover']:.2f} kg"], ["Bolts joining", f"{len(info.get('bolts', []))} of 13"]],  # fmt: skip
        "castable": [[f"{h['half'].replace('_', ' ')}", f"undercut {100 * h['undercut_share']:.1f} %, {h['thinner_than_least_wall_cm2']:.0f} cm² under 4 mm"] for h in halves],
        "fe": [["Beds, drive", f"{lines.get('displacement, peak drive', {}).get('value_um', 0):.1f} µm (≤ 52.2)"],
               ["Worst tilt", f"{lines.get('misalignment (worst seat against its line)', {}).get('ratio', 0):.2f} × its line"],
               ["First mode", f"{g.get('first_mode_hz') or 0:.0f} Hz"], ["Clashes", ", ".join(lines.get("orders", {}).get("clashes", [])) or "none"],
               ["Mass", f"{g.get('mass_kg', 0):.2f} kg (≤ 7.73)"], ["Verdict", "PASS" if g.get("pass") else "fail"]],  # fmt: skip
    }
    return out


def export(design: str) -> None:
    info = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    flow, run_steps = flow_of(design, info)
    c = cards(design, info)
    run = info.get("outcome_of", "")
    steps = [
        {"id": "contract", "label": "Contract", "method": "the contract's elements, from zenryx's spaces", "view": {"kind": "volumes"}, "card": c["contract"]},
        {"id": "setup", "label": "Set-up", "method": "the optimiser's voxels: fixed, kept out, free", "view": {"kind": "volumes", "voxels": True}, "card": c["setup"]},
    ]
    # A stage drawn as two tabs (the drawing: its body, then the design; FE: its mesh, then its
    # results) carries its time on the first alone, so the tabs add up to the flow's time; a stage
    # run beside another says so ("beside": the other's id) in place of a time of its own.
    for s_ in run_steps:
        sid = s_["id"]
        if sid.startswith("optimise"):
            out_run = (s_.get("outputs") or [run])[0]
            steps.append({**s_, "view": {"kind": "field", "run": out_run}, "card": optimise_card(out_run)})
        elif sid == "draw":
            steps.append({**s_, "label": s_["label"] + ": the body", "id": "body", "view": {"kind": "design", "stem": f"{design}_organic"},
                          "card": [["Note", "the inside still solid: cut in the next tab"]]})  # fmt: skip
            steps.append({**s_, "label": "Machined" if flow["id"] in ("B", "E") else "CAD", "id": "machined", "seconds": None, "of": "body",
                          "view": {"kind": "design", "stem": design}, "card": c["draw"]})  # fmt: skip
        elif sid == "fe":
            steps.append({**s_, "label": "FE mesh", "id": "fe_mesh", "view": {"kind": "fe", "field": None}, "card": [["Note", s_.get("note", "")]]})
            steps.append({**s_, "label": "Results", "id": "results", "seconds": None, "of": "fe_mesh", "view": {"kind": "fe", "field": "displacement"}, "card": c["fe"]})
        elif sid == "castable":
            beside = {"seconds": None, "beside": "fe_mesh"} if s_.get("note") == "beside FE" else {}
            steps.append({**s_, **beside, "view": {"kind": "design", "stem": design}, "card": c["castable"]})
        elif sid == "grade":
            steps.append({**s_, "view": {"kind": "grade", **grade_rows(design)}, "card": []})
        elif sid == "reading":  # the field read in plan (`ribbed_cad.plan_picture`), shown as it is
            picture = OUT / (info.get("picture") or f"{design}_ribs.png")
            TARGET.mkdir(parents=True, exist_ok=True)
            if picture.exists():
                shutil.copyfile(picture, TARGET / f"{design}_reading.png")
            rb = info.get("ribbed") or {}
            ribs = info.get("ribs") or []
            card = [[f"Ribs, {h.replace('_', ' ')}", f"{n}, {sum(r['length'] for r in ribs if r['half'] == h) / 10:.0f} cm of centre-line"] for h, n in (rb.get("ribs") or {}).items()]
            card += [[f"Pads, {h.replace('_', ' ')}", str(n)] for h, n in (rb.get("pads") or {}).items()]
            card += [["Thickness", f"{min((r['width'] for r in ribs), default=0):g}-{max((r['width'] for r in ribs), default=0):g} mm"],
                     ["Struts into mounts", ", ".join(t["mount"] for t in rb.get("ties") or []) or "none"]]  # fmt: skip
            steps.append({**s_, "view": {"kind": "image", "src": f"{design}_reading.png"}, "card": card})
        elif sid == "setup":
            continue
        else:
            steps.append({**s_, "view": {"kind": "none"}, "card": []})
    total = sum(float(s_.get("seconds") or 0) for s_ in run_steps if s_.get("note") != "beside FE")  # a step run beside another counts once
    TARGET.mkdir(parents=True, exist_ok=True)
    record = {"schema": 1, "design": design, "flow": flow, "steps": steps, "seconds": round(total, 1)}
    (TARGET / f"{design}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    fe = fe_surface(design)
    if fe is not None:
        (TARGET / f"{design}_fe.json").write_text(json.dumps(fe), encoding="utf-8")
    print(f"{design}: flow {flow['id']} ({flow['name']}), {len(steps)} steps, {total:.0f} s; FE surface {'written' if fe else 'none'}")


if __name__ == "__main__":
    for d in sys.argv[1:]:
        export(d)
