"""PROTOTYPE (LOP-33) - the parity check of the final workflow's move into `src/zenryx/workflow`: the old route's
records against the new one's, on stub stages, with no GPU and no data/.

1. **The grade:** `grade.py` as it was before the move (git c3f9fb7) against `zenryx.workflow.grade.grade_all`, on 40
   synthetic FE results (rigid turns, clashes, light and heavy, soft and stiff): identical grades.
2. **The flow:** `propose.py` as it was (c3f9fb7, run through `campaign_run.sh`'s route) against
   `zenryx.workflow.flow.propose` with the prototype's engines (`engines.py`), both on a copy of the tree whose stage
   scripts are stubs that write each stage's files: identical flow records (times aside) in 10 cases (a new run, a
   reused one, the feasibility gate, a lost mount, a leak, a failed optimisation, drawing or FE, flow B and E).

Run: .venv/Scripts/python.exe prototypes/first_loop/workflow_parity.py   (needs the git history back to c3f9fb7)"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BEFORE = "c3f9fb7"  # the last commit before the move (LOP-33)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "checks" / "workflow"))
sys.path.insert(0, str(HERE))

from engines import PrototypeEngines  # noqa: E402
from fixtures import fe_result, write  # noqa: E402

from zenryx.workflow import flow  # noqa: E402
from zenryx.workflow.grade import grade_all  # noqa: E402

CONTRACT = REPO / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
ENV = {"LOOP_EXACT_WALLS": "1", "LOOP_FAITHFUL": "2"}
STAGES = ("topo_free", "outcome_cad", "oiltight", "fe", "castable", "grade", "view_export", "look", "topo_export", "names", "process_export")
STUB = """import json, os, sys
from pathlib import Path
OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
name, a, case = Path(__file__).stem, sys.argv[1:], json.loads(os.environ["STUB_CASE"])
def w(n, d): (OUT / n).write_text(json.dumps(d))
if name == "topo_free":
    if case.get("fail") == "optimise": sys.exit(1)
    run = "run_" + a[a.index("--tag") + 1]
    w(run + ".json", {"binary": {"worst": case.get("missed", 0.9), "beds": {"a": 0.5}}, "empty": case.get("empty", True),
                      "frozen_kg": 3.5, "budget_kg": 7.73, "voxel_mm": float(a[1]), "least_kg": 1.0, "argv": a})
    print("[00:00] settled at 120"); print("[00:01] done in 1 s; " + run)
elif name == "outcome_cad":
    if case.get("fail") == "draw": sys.exit(1)
    m = [{"name": "mount-%d" % i} for i in (1, 2, 3)]
    w(a[1] + ".json", {"mounts_layout": m, "mounts": m[: case.get("mounts", 3)]})
elif name == "oiltight":
    w("oiltight_" + a[0] + ".json", {"tight": case.get("tight", True), "leak_at_mm": [1, 2, 3]})
elif name == "fe":
    print("[00:02] FE in all 42 s")
    if case.get("fail") == "fe": sys.exit(1)
    sys.path.insert(0, CHECKS)
    from fixtures import fe_result
    w("fe_" + a[0] + ".json", fe_result(a[0], scale=0.01))
elif name == "grade":
    sys.path.insert(0, SRC)
    from zenryx.workflow.grade import grade_all
    grade_all(OUT, Path(CONTRACT))
"""
CASES = [{}, {"empty": False}, {"missed": 1.3}, {"mounts": 2}, {"fail": "fe"}, {"fail": "draw"}, {"fail": "optimise"},
         {"tight": False}, {"reuse": True}, {"reuse": True, "missed": 1.5}]  # fmt: skip


def old_file(path: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{BEFORE}:{path}"], capture_output=True, text=True, check=True).stdout


def grades() -> str:
    designs = [fe_result(f"d{i}", seed=i, scale=[0.01, 0.3, 1, 3, 30][i % 5], mass_kg=4 + (i % 7) * 0.7, modes_hz=(400 + 15 * i, 900),
                         clashes=({"mode": 2},) if i % 6 == 0 else (), rigid_turn=1e-3 * (i % 3)) for i in range(40)]  # fmt: skip
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        for out in (a, b):
            for d in designs:
                write(Path(out), f"fe_{d['stem']}.json", d)
        code = old_file("prototypes/first_loop/grade.py").replace('OUT = ROOT / "data" / "first_loop"', f"OUT = Path({a!r})")
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(code, "grade.py@" + BEFORE, "exec"), {"__name__": "__main__", "__file__": str(HERE / "grade.py")})
        old = json.loads((Path(a) / "grades.json").read_text())
        new, _ = grade_all(Path(b), CONTRACT)
    assert old == new and len(new) == 40, "the grades differ"
    return f"the grade: {len(new)} designs, identical ({sum(r['pass'] for r in new)} pass)"


def tree(case: dict, tmp: Path, py: Path) -> Path:
    root = Path(tempfile.mkdtemp(prefix="parity_", dir=tmp))
    loop = root / "prototypes" / "first_loop"
    loop.mkdir(parents=True)
    (root / "data" / "first_loop").mkdir(parents=True)
    (loop / "propose.py").write_text(old_file("prototypes/first_loop/propose.py"))
    stub = f"CHECKS, SRC, CONTRACT = {str(REPO / 'checks' / 'workflow')!r}, {str(REPO / 'src')!r}, {str(CONTRACT)!r}\n" + STUB
    for n in STAGES:
        (loop / f"{n}.py").write_text(stub)
    if case.get("reuse"):
        write(root / "data" / "first_loop", "old_run.json", {"binary": {"worst": case.get("missed", 0.9)}, "seconds": 600, "voxel_mm": 4,
                                                            "empty": True, "frozen_kg": 3, "budget_kg": 7})  # fmt: skip
    (root / ".venv" / "Scripts").mkdir(parents=True)  # propose.py@c3f9fb7 calls the venv's python by this path
    w = root / ".venv" / "Scripts" / "python.exe"
    w.write_text(f'#!/bin/sh\nexec {py} "$@"\n')
    w.chmod(0o755)
    return root


def strip(rec: dict) -> dict:
    rec = json.loads(json.dumps(rec))
    rec.pop("seconds")
    for s in rec["steps"]:
        if s.get("seconds") is not None and s.get("note") != "reused":
            s["seconds"] = "t"
    return rec


def flows() -> str:
    py = Path(sys.executable)
    with tempfile.TemporaryDirectory() as tmp:
        for case in CASES:
            a, b = tree(case, Path(tmp), py), tree(case, Path(tmp), py)
            env = {**os.environ, **ENV, "STUB_CASE": json.dumps(case)}
            run = "old_run" if case.get("reuse") else ""
            argv = ["--run", run] if run else ["--", "--least-width", "8"]
            subprocess.run([str(py), "prototypes/first_loop/propose.py", "d1", "--budget", "7.73", "--voxel", "4", *argv],
                           cwd=a, env=env, check=True, capture_output=True)  # fmt: skip
            old = json.loads((a / "data" / "first_loop" / "flow_d1.json").read_text())
            engines = PrototypeEngines(b / "data" / "first_loop", guard=False, root=b, py=str(py))
            new = flow.propose("d1", budget=7.73, voxel=4, args=["--least-width", "8"], engines=engines, out=b / "data" / "first_loop",
                               contract=CONTRACT, env=env, run=run)  # fmt: skip
            assert strip(old) == strip(new), f"the flow records differ in case {case}"
            if not run and not case.get("fail"):  # the optimiser was called with the same arguments
                argv_old = json.loads((a / "data" / "first_loop" / "run_d1.json").read_text())["argv"]
                argv_new = json.loads((b / "data" / "first_loop" / "run_d1.json").read_text())["argv"]
                assert argv_old == argv_new, (argv_old, argv_new)
            shutil.rmtree(a), shutil.rmtree(b)
    return f"the flow: {len(CASES)} cases, identical records and optimiser arguments"


if __name__ == "__main__":
    print("PARITY: " + grades())
    print("PARITY: " + flows())
