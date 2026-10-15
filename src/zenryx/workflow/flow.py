"""One design's flow, from its optimisation to its judged design and the Designs tab's records
(LOP-33; the final workflow's route of `prototypes/first_loop/propose.py`, flows B and E).

The stages, in order:
1. the optimisation (or an existing run reused);
2. the gate: a run whose metal-or-air check misses its own lines by more than `FEASIBLE` stops
   the flow, nothing invested after it;
3. the drawing (the mesh route), then the oil-tight gate for an empty start;
4. the gate: a drawing that holds fewer mounts than the layout is not judged;
5. FE beside castability;
6. the grade (`zenryx.workflow.grade`), when FE ran;
7. the Designs tab's records and the pictures.
Each stage's time, outcome and note go into the flow's record, `flow_<design>.json`, the format the
Designs tab's process view reads (`process_export.py`).

The heavy stages are an `Engines`; the files between them (a run's record `<run>.json`, a drawing's
`<design>.json`, the gate's `oiltight_<design>.json`) are the stages' contract.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol

from zenryx.workflow import grade as grading

FEASIBLE = 1.10  # the most a run's metal-or-air check may read of its own lines and be drawn

FLOW_B = {
    "id": "B",
    "name": "The mesh route",
    "words": "The optimisation in one run; the drawing's booleans on watertight meshes "
    "(manifold3d); FE's tets straight from them (TetGen); castability beside FE",
}
FLOW_E = {  # LOP-27 (the engineer, 12 October 20:22: "Do an empty start"); a run with `--empty`
    "id": "E",
    "name": "The empty start",
    "words": "No fixed shell: the walls, bosses, ribs and brackets one field the optimiser sizes, "
    "oil-tight by each column's least height; drawn as one body from that field, exact only where "
    "machined; the oil-tight gate beside the drawing; FE, castability, the grade as flow B",
}


class Engines(Protocol):
    """The heavy stages. Each writes its files into the flow's folder and its output to `log`."""

    def layout(self, env: Mapping[str, str], log: Path) -> int:
        """The layout record from the contract, and the UI's view of the set-up; its exit code."""

    def optimise(
        self,
        design: str,
        budget: float,
        voxel: float,
        args: list[str],
        env: Mapping[str, str],
        log: Path,
    ) -> tuple[int, str, str]:
        """One optimisation: its exit code, its run's stem ('' if none) and its settling note."""

    def draw(self, run: str, design: str, env: Mapping[str, str], log: Path) -> int:
        """The design drawn from the run's field: `<design>.json` and each half's mesh."""

    def oiltight(self, design: str, env: Mapping[str, str], log: Path) -> int:
        """The oil-tight gate: `oiltight_<design>.json`."""

    def judge(
        self, design: str, env: Mapping[str, str], fe_log: Path, cast_log: Path
    ) -> tuple[int, int]:
        """FE (`fe_<design>.json`) beside castability: their exit codes."""

    def records(self, design: str, run: str, env: Mapping[str, str], out: Path) -> None:
        """The Designs tab's records and the pictures (failures are not the design's)."""

    def process(self, design: str, env: Mapping[str, str], log: Path) -> None:
        """The flow's tabs on the Designs tab, from `flow_<design>.json`."""


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _timed(fn: Callable[[], object]) -> tuple[float, object]:
    t = time.time()
    result = fn()
    return round(time.time() - t, 1), result


def _line(log: Path, marker: str) -> str:
    """The text after "] " of the first line of `log` holding `marker`, or ''."""
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    hit = next((ln for ln in text.splitlines() if marker in ln), "")
    return hit.split("] ", 1)[1] if "] " in hit else ""


def draw_method(empty: bool, env: Mapping[str, str]) -> str:
    """The drawing's method in words, from the settings it ran with."""
    if empty:
        method = (
            "the whole housing by marching cubes from its one field (no exact shell); the inside, "
            "bores, exits and holes cut exact: manifold3d's booleans"
        )
    else:
        method = "the members by marching cubes; the exact shell, the cuts: manifold3d's booleans"
    if empty and env.get("LOOP_EXACT_WALLS", "0") != "0":
        method += (
            "; the least walls drawn from the exact inside, smooth, in the same field as the "
            "optimiser's metal"
        )
    if env.get("LOOP_KEEP_CUBES", "1") != "0":
        method += (
            "; every metal cube the optimiser placed kept whole, each checked inside the drawing "
            "before FE"
        )
    faithful = float((env.get("LOOP_FAITHFUL", "0") or "0").split(":")[0])
    if faithful > 0:
        method += (
            f"; smoothed faithfully (Ježek et al. 2025): the distance at the {faithful:g} mm "
            "voxels' centres interpolated by Gaussians, the volume kept"
        )
    return method


def propose(
    design: str,
    *,
    budget: float,
    voxel: float,
    args: list[str],
    engines: Engines,
    out: Path,
    contract: Path,
    env: Mapping[str, str],
    run: str = "",
) -> dict:
    """One design's flow; its record (also written to `out/flow_<design>.json`)."""
    d, t_all, steps, flow = design, time.time(), [], FLOW_B

    def finish(failed: str) -> dict:
        grades = {g["stem"]: g for g in json.loads(_read_text(out / "grades.json") or "[]")}
        record = {
            "design": d,
            "flow": flow,
            "steps": steps,
            "seconds": round(time.time() - t_all, 1),
            "failed": failed or None,
            "grade": grades.get(d),
        }
        (out / f"flow_{d}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
        if (out / f"{d}.json").exists():
            engines.process(d, env, out / f"process_{d}.log")
        return record

    if not run:
        log = out / f"optimise_{d}.log"
        seconds, (code, run, settled) = _timed(
            lambda: engines.optimise(d, budget, voxel, args, env, log)
        )
        steps.append(
            {
                "id": "optimise",
                "label": "Optimisation",
                "method": "stiffness, every bearing's tilt and bed held; "
                "one run, GCMMA with MMA's dual",
                "seconds": seconds,
                "ok": code == 0 and bool(run),
                "outputs": [run],
                "note": settled,
            }
        )
        if code or not run:
            return finish("the optimisation failed")
        rec = _read(out / f"{run}.json")
        binary = rec.get("binary") or {}
        missed = max(
            [binary.get("worst") or 0.0, *(binary.get("beds") or {}).values()], default=0.0
        )
        if missed > FEASIBLE:
            steps[-1].update(
                ok=False, note=f"its metal-or-air check misses its lines: {missed:.2f} x"
            )
            return finish(
                f"the optimisation failed: its metal-or-air check reads {missed:.2f} x its lines"
            )
    else:
        rec = _read(out / f"{run}.json")
        steps.append(
            {
                "id": "optimise",
                "label": "Optimisation",
                "method": "an existing run, reused: stiffness, every bearing's tilt and bed held; "
                "one run, GCMMA with MMA's dual",
                "seconds": round(float(rec.get("seconds") or 0), 1),
                "ok": True,
                "outputs": [run],
                "note": "reused",
            }
        )
    empty = bool(rec.get("empty"))
    if empty:
        flow = FLOW_E
    held = (
        "nothing fixed but the seats' rings, the mounts and the bolts' bosses; the walls the "
        "optimiser's, oil-tight by each column's least height"
        if empty
        else "the contract's wall, flange, bosses and mounts held fixed"
    )
    frozen, budget_kg = rec.get("frozen_kg", 0), rec.get("budget_kg", 0)
    note = f"{frozen:.2f} kg fixed, {budget_kg - frozen:.2f} kg to place"
    if empty and rec.get("least_kg"):
        note += f", the walls' least {rec['least_kg']:.2f} kg of it"
    steps.insert(
        0,
        {
            "id": "setup",
            "label": "Set-up",
            "method": f"{rec.get('voxel_mm', 6):g} mm voxels; {held}",
            "seconds": 0.0,
            "ok": True,
            "note": note,
            "outputs": [run],
        },
    )

    seconds, code = _timed(lambda: engines.draw(run, d, env, out / f"build_{d}.log"))
    steps.append(
        {
            "id": "draw",
            "label": "Drawing",
            "method": draw_method(empty, env),
            "seconds": seconds,
            "ok": code == 0,
            "outputs": [f"{d}_motor_side.stl", f"{d}_cover.stl"],
        }
    )
    if empty and code == 0:
        engines.oiltight(d, env, out / f"oiltight_{d}.log")
        gate = _read(out / f"oiltight_{d}.json")
        if gate:
            steps[-1]["note"] = (
                "oil-tight" if gate["tight"] else f"LEAKS at {gate['leak_at_mm']} mm"
            )
    if code:
        return finish("the drawing failed")
    drawn = _read(out / f"{d}.json")
    layout_mounts = drawn.get("mounts_layout")
    if layout_mounts is not None and len(drawn.get("mounts") or []) < len(layout_mounts):
        # LOP-27: a drawing that loses a mount is not the design's to judge (a thin arm read at
        # 0.5 can part from its lug, and FE then holds the housing on fewer mounts)
        kept = {m["name"] for m in drawn.get("mounts") or []}
        lost = ", ".join(sorted({m["name"] for m in layout_mounts} - kept))
        steps[-1].update(ok=False, note=f"the drawing lost {lost}: not judged")
        return finish(f"the drawing lost {lost} (try LOOP_MEMBER_LEVEL=0.4)")

    fe_log, cast_log = out / f"fe_{d}.log", out / f"castable_{d}.log"
    both, (fe_code, cast_code) = _timed(lambda: engines.judge(d, env, fe_log, cast_log))
    steps.append(
        {
            "id": "fe",
            "label": "FE",
            "method": "TetGen's tets from the mesh, cuDSS TET10, peak drive and 12 modes",
            "seconds": both,
            "ok": fe_code == 0,
            "note": _line(fe_log, "in all"),
        }
    )
    steps.append(
        {
            "id": "castable",
            "label": "Castability",
            "method": "rays along the pull and into the metal, on the mesh",
            "seconds": both,
            "ok": cast_code == 0,
            "note": "beside FE",
        }
    )
    if fe_code == 0:

        def graded() -> int:
            try:
                grades, stale = grading.grade_all(out, contract)
            except Exception as e:  # a grade that fails is the flow's step, not a crash
                (out / f"grade_{d}.log").write_text(f"the grade failed: {e}\n", encoding="utf-8")
                return 1
            (out / f"grade_{d}.log").write_text(grading.table(grades, stale), encoding="utf-8")
            return 0

        seconds, code = _timed(graded)
        steps.append(
            {
                "id": "grade",
                "label": "Grade",
                "method": "every line of the contract, peak drive",
                "seconds": seconds,
                "ok": code == 0,
            }
        )
    engines.records(d, run, env, out)
    return finish("")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""
