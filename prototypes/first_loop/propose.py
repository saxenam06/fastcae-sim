"""PROTOTYPE (LOP-20) - one design proposal end to end, in minutes (the engineer's first goal, 11 October
01:26: "the final design proposal from this end-to-end pipeline within a few minutes, so that the agent
can evaluate and decide... or try different variations").

The flow (flow B, "the mesh route"; `docs/features/loop/2026-10-11-record-night.md`):
1. the optimisation, one run: the stiffness the objective, every seat's tilt and bearing bed held,
   peak drive, one design, MMA's dual, stopping once settled (`topo_free.py`);
2. the drawing by the mesh route: the members by marching cubes, every boolean manifold3d's
   (`outcome_cad.py <run> <design> skin mesh`);
3. FE (TetGen's tets, cuDSS TET10, the modes) beside castability (the rays on the mesh), at once;
4. the grade, the pictures, the UI's records.

Each stage's name, method, time and outputs go into `data/first_loop/flow_<design>.json`, which the
Designs page draws as the flow's tabs (LOP-21; every flow tried keeps its own).

Run: .venv/Scripts/python.exe prototypes/first_loop/propose.py <design> [--budget 7.73] [--voxel 6]
       [--run <an existing run's stem: skip the optimisation>] [-- extra topo_free.py arguments]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"
sys.path.insert(0, str(HERE))
from hostenv import python_exe  # noqa: E402

PY = python_exe()  # the venv's python, on the laptop or a Linux GPU worker (PLT-12)
FEASIBLE = 1.10  # the most a run's metal-or-air check may read of its own lines (tilt and beds) and still be drawn

FLOW_D = {
    "id": "D",
    "name": "Parametric CAD",
    "words": "Production's features from a recipe (bosses, bridges, ribs on the flow's lines, spokes, fins, gussets, arms), filleted; exact B-rep and STEP; FE on its filled body",
}
FLOW = {
    "id": "B",
    "name": "The mesh route",
    "words": "The optimisation in one run; the drawing's booleans on watertight meshes (manifold3d); FE's tets straight from them (TetGen); castability beside FE",
}
FLOW_E = {  # LOP-27 (the engineer, 12 October 20:22: "Do an empty start"); a run with `--empty`
    "id": "E",
    "name": "The empty start",
    "words": "No fixed shell: the walls, bosses, ribs and brackets one field the optimiser sizes, oil-tight by each column's least height; "
             "drawn as one body from that field, exact only where machined; the oil-tight gate beside the drawing; FE, castability, the grade as flow B",
}  # fmt: skip


def step(name: str, args: list[str], log: Path) -> tuple[float, int]:
    t = time.time()
    with log.open("w", encoding="utf-8") as fh:
        code = subprocess.call([PY, *args], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return time.time() - t, code


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--budget", type=float, default=7.73)
    ap.add_argument("--voxel", type=float, default=6.0)
    ap.add_argument("--run", default="")
    ap.add_argument("--drawing", choices=("mesh", "ribs", "param"), default="mesh",
                    help="flow B's mesh route, flow C's ribbed CAD (ribbed_cad.py), or flow D's parametric CAD (param_cad.py)")  # fmt: skip
    ap.add_argument("--recipe", default="", help="flow D: the recipe to build from (else one made from the run's layout)")
    ap.add_argument("--drawn", action="store_true", help="the design is drawn already: judge it (FE, castability, the grade, the records)")
    ap.add_argument("--strengthen", default="", help="SHAFT,SIDE,REACH,RAISE (e.g. intermediate,-z,60,6): the ribbed CAD's move on a failing seat")
    ap.add_argument("extra", nargs="*")
    a = ap.parse_args()
    d = a.design
    t_all = time.time()
    steps = []
    global FLOW
    if a.drawing == "ribs":
        from process_export import FLOW_C

        FLOW = FLOW_C
    if a.drawing == "param":
        FLOW = FLOW_D

    run = a.run
    if not run:
        tag = d.replace("outcome_", "")
        args = ["prototypes/first_loop/topo_free.py", f"{a.budget:g}", f"{a.voxel:g}", "200", "--objective", "compliance_tilt", "--beds",
                "--cases", "peak drive", "--route", "split", "--settle", "0.02", "--every", "25", "--beta-most", "32", "--fast",
                "--max-member", "12", "--tag", tag, *a.extra]  # fmt: skip
        seconds, code = step("optimise", args, OUT / f"optimise_{d}.log")
        text = (OUT / f"optimise_{d}.log").read_text(encoding="utf-8", errors="replace")
        line = next((ln for ln in text.splitlines() if "done in" in ln), "")
        run = line.rsplit("; ", 1)[-1].strip() if line else ""
        settled = next((ln.split("] ", 1)[1] for ln in text.splitlines() if "settled at" in ln), "")
        steps.append({"id": "optimise", "label": "Optimisation", "method": "stiffness, every bearing's tilt and bed held; one run, GCMMA with MMA's dual",
                      "seconds": round(seconds, 1), "ok": code == 0 and bool(run), "outputs": [run], "note": settled})  # fmt: skip
        if code or not run:
            return finish(d, steps, t_all, "the optimisation failed")
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    # A failed optimisation stops the proposal, nothing invested after it (the engineer's rule): its
    # metal-or-air check missing its own lines by more than 10 % (11 October 08:05: outcome_env12's
    # 12 mm corridors left two mounts loose, 7.1 x the tilt line and 372 x the beds, and the drawing
    # and FE ran on regardless)
    binary = rec.get("binary") or {}
    missed = max([binary.get("worst") or 0.0, *(binary.get("beds") or {}).values()], default=0.0)
    if not a.run and missed > FEASIBLE:
        steps[-1].update(ok=False, note=f"its metal-or-air check misses its lines: {missed:.2f} x")
        return finish(d, steps, t_all, f"the optimisation failed: its metal-or-air check reads {missed:.2f} x its lines")
    if a.run:  # an existing run reused: its own time, so the flow's tabs show what it cost
        steps.append({"id": "optimise", "label": "Optimisation", "method": "an existing run, reused: stiffness, every bearing's tilt and bed held; one run, GCMMA with MMA's dual",
                      "seconds": round(float(rec.get("seconds") or 0), 1), "ok": True, "outputs": [run], "note": "reused"})  # fmt: skip
    empty = bool(rec.get("empty"))
    if empty:  # LOP-27: the empty start's flow
        FLOW = FLOW_E
    held = ("nothing fixed but the seats' rings, the mounts and the bolts' bosses; the walls the optimiser's, oil-tight by each column's least height" if empty
            else "the contract's wall, flange, bosses and mounts held fixed")  # fmt: skip
    note = f"{rec.get('frozen_kg', 0):.2f} kg fixed, {rec.get('budget_kg', 0) - rec.get('frozen_kg', 0):.2f} kg to place"
    if empty and rec.get("least_kg"):
        note += f", the walls' least {rec['least_kg']:.2f} kg of it"
    steps.insert(0, {"id": "setup", "label": "Set-up", "method": f"{rec.get('voxel_mm', 6):g} mm voxels; {held}",
                     "seconds": 0.0, "ok": True, "note": note, "outputs": [run]})  # fmt: skip

    if a.drawing == "param":  # flow D: production's features from a recipe, as exact parametric CAD (`param_cad.py`)
        if a.drawn and (OUT / f"{d}.json").exists():
            seconds, code = float(json.loads((OUT / f"{d}.json").read_text(encoding="utf-8")).get("seconds") or 0.0), 0
        else:
            seconds, code = step("draw", ["prototypes/first_loop/param_cad.py", run, d, *(["--recipe", a.recipe] if a.recipe else [])], OUT / f"build_{d}.log")
        steps.append({"id": "draw", "label": "Drawing", "method": "OCC: the contract's exact shell, its rims filleted; bosses, bridges, ribs on the flow's lines, spokes, fins, "
                      "gussets, arms from the recipe, each a full-round rib or a plate, fused pairwise; the roots filleted; every exact cut",
                      "seconds": round(seconds, 1), "ok": code == 0, "outputs": [f"{d}_motor_side.step", f"{d}_cover.step", f"{d}_recipe.json"]})  # fmt: skip
    elif a.drawing == "ribs":  # flow C: the field read and drawn as exact CAD (`ribbed_cad.py`)
        seat = a.strengthen.split(",") if a.strengthen else []
        extra = ["--strengthen", *seat] if seat else []
        seconds, code = step("draw", ["prototypes/first_loop/ribbed_cad.py", run, d, *extra], OUT / f"build_{d}.log")
        steps.append({"id": "reading", "label": "Reading", "method": "the field in plan: deep members as ribs along their centre-lines, shallow ones as pads, each under the envelope over the members' ends"
                      + (f"; the {seat[0]} {seat[1]} seat strengthened (ribs within {seat[2]} mm at 12 mm, raised {seat[3]} mm)" if seat else ""),
                      "seconds": None, "of": "body", "ok": code == 0})  # fmt: skip
        steps.append({"id": "draw", "label": "Drawing", "method": "OCC: each rib a plate topped by the envelope along it; posts, struts into the mounts, flat-topped pads; fused pairwise onto the exact shell; every exact cut",
                      "seconds": round(seconds, 1), "ok": code == 0})  # fmt: skip
    else:
        seconds, code = step("draw", ["prototypes/first_loop/outcome_cad.py", run, d, "skin", "mesh"], OUT / f"build_{d}.log")
        method = ("the whole housing by marching cubes from its one field (no exact shell); the inside, bores, exits and holes cut exact: manifold3d's booleans" if empty
                  else "the members by marching cubes; the exact shell, the cuts: manifold3d's booleans")  # fmt: skip
        if empty and os.environ.get("LOOP_EXACT_WALLS", "0") != "0":  # LOP-27: `exact_walls.py`
            method += "; the least walls drawn from the exact inside, smooth, in the same field as the optimiser's metal"
        if os.environ.get("LOOP_KEEP_CUBES", "1") != "0":  # LOP-29: `outcome_cad.cube_fidelity`
            method += "; every metal cube the optimiser placed kept whole, each checked inside the drawing before FE"
        faithful = float((os.environ.get("LOOP_FAITHFUL", "0") or "0").split(":")[0])
        if faithful > 0:  # LOP-27: `mesh_route.faithful`
            method += f"; smoothed faithfully (Ježek et al. 2025): the distance at the {faithful:g} mm voxels' centres interpolated by Gaussians, the volume kept"
        steps.append({"id": "draw", "label": "Drawing", "method": method,
                      "seconds": round(seconds, 1), "ok": code == 0, "outputs": [f"{d}_motor_side.stl", f"{d}_cover.stl"]})  # fmt: skip
        if empty and code == 0:  # the oil-tight gate (`oiltight.py`): the walls are the field's, so the drawing must keep them closed
            step("oiltight", ["prototypes/first_loop/oiltight.py", d], OUT / f"oiltight_{d}.log")
            gate = OUT / f"oiltight_{d}.json"
            if gate.exists():
                g = json.loads(gate.read_text(encoding="utf-8"))
                steps[-1]["note"] = "oil-tight" if g["tight"] else f"LEAKS at {g['leak_at_mm']} mm"
    if code:
        return finish(d, steps, t_all, "the drawing failed")
    drawn = json.loads((OUT / f"{d}.json").read_text(encoding="utf-8")) if (OUT / f"{d}.json").exists() else {}
    if drawn.get("mounts_layout") is not None and len(drawn.get("mounts") or []) < len(drawn["mounts_layout"]):
        # LOP-27 (12 October 23:40): a drawing that loses a mount is not the design's to judge. The surface keeps its largest
        # piece, so a mount whose arm thinned to one voxel was dropped silently, and FE held case3_web_5.5kg on two mounts
        # (119.8 um, a first mode of 114 Hz) where the optimiser's model, on three, passed
        lost = sorted({m["name"] for m in drawn["mounts_layout"]} - {m["name"] for m in drawn.get("mounts") or []})
        steps[-1].update(ok=False, note=f"the drawing lost {', '.join(lost)}: not judged")
        return finish(d, steps, t_all, f"the drawing lost {', '.join(lost)} (try LOOP_MEMBER_LEVEL=0.4)")

    # FE and castability at once: the GPU's and the CPU's; one after the other with LOOP_CAST_AFTER=1 (13 October 22:45: with
    # 2.6 GB of memory free, the two side by side had dipped to 0.5 GB)
    t = time.time()
    with (OUT / f"fe_{d}.log").open("w", encoding="utf-8") as f1, (OUT / f"castable_{d}.log").open("w", encoding="utf-8") as f2:
        fe = subprocess.Popen([PY, "prototypes/first_loop/fe.py", d, "8.0"], cwd=ROOT, stdout=f1, stderr=subprocess.STDOUT)
        if os.environ.get("LOOP_CAST_AFTER", "0") != "0":
            fe.wait()
        cast = subprocess.Popen([PY, "prototypes/first_loop/castable.py", d], cwd=ROOT, stdout=f2, stderr=subprocess.STDOUT)
        fe_code, cast_code = fe.wait(), cast.wait()
    both = time.time() - t
    fe_text = (OUT / f"fe_{d}.log").read_text(encoding="utf-8", errors="replace")
    fe_method = "the CAD's parts filled on a 1.5 mm grid, the machined faces exact; " if a.drawing in ("ribs", "param") else ""
    steps.append({"id": "fe", "label": "FE", "method": fe_method + "TetGen's tets from the mesh, cuDSS TET10, peak drive and 12 modes", "seconds": round(both, 1),
                  "ok": fe_code == 0, "note": next((ln.split("] ", 1)[1] for ln in fe_text.splitlines() if "in all" in ln), "")})  # fmt: skip
    steps.append({"id": "castable", "label": "Castability", "method": "rays along the pull and into the metal, on the " + ("B-rep" if a.drawing in ("ribs", "param") else "mesh"),
                  "seconds": round(both, 1), "ok": cast_code == 0, "note": "beside FE"})  # fmt: skip
    if fe_code == 0:
        seconds, code = step("grade", ["prototypes/first_loop/grade.py"], OUT / f"grade_{d}.log")
        steps.append({"id": "grade", "label": "Grade", "method": "every line of the contract, peak drive", "seconds": round(seconds, 1), "ok": code == 0})
    # the Designs page's records: the design, its organic body, its run (the Optimisation tab and the
    # flow's Optimisation step), the names; the flow's tabs follow in finish()
    for name, args in (("view", ["prototypes/first_loop/view_export.py", d]), ("look", ["prototypes/first_loop/look.py", d]),
                       ("view_organic", ["prototypes/first_loop/view_export.py", f"{d}_organic"]),
                       ("run_view", ["prototypes/first_loop/topo_export.py", run]), ("names", ["prototypes/first_loop/names.py"])):  # fmt: skip
        step(name, args, OUT / f"{name}_{d}.log")
    return finish(d, steps, t_all, "")


def finish(design: str, steps: list[dict], t0: float, failed: str) -> None:
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))} if (OUT / "grades.json").exists() else {}
    record = {"design": design, "flow": FLOW, "steps": steps, "seconds": round(time.time() - t0, 1), "failed": failed or None, "grade": grades.get(design)}
    (OUT / f"flow_{design}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    if (OUT / f"{design}.json").exists():  # the flow's tabs on the Designs page (LOP-21), once a drawing exists
        step("process", ["prototypes/first_loop/process_export.py", design], OUT / f"process_{design}.log")
    print(f"{design}: {'FAILED, ' + failed if failed else 'proposed'} in {record['seconds']:.0f} s; " + ", ".join(f"{s['label']} {s['seconds']:.0f} s" for s in steps if s.get('seconds') is not None))


if __name__ == "__main__":
    sys.exit(main())
