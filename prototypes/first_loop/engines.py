"""PROTOTYPE (LOP-33) - the final workflow's heavy stages as `zenryx.workflow.flow.Engines`: each runs
the prototype's own script, with the arguments `propose.py` gave it, so a design made through
`zenryx.workflow` is the one `propose.py` made. A stage leaves this file when it is ported into
`src/zenryx` with a check that it gives the prototype's result (the grade already has).

The memory guard (`memory_guard.py`) watches the design's processes from the first heavy stage
(`campaign_run.sh` did the same around `propose.py`); `close()` waits for it."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from hostenv import python_exe  # noqa: E402

LOOP = "prototypes/first_loop"


class PrototypeEngines:
    def __init__(self, out: Path, guard: bool = True, root: Path = ROOT, py: str = ""):
        self.out, self.py, self.use_guard, self.root = out, py or python_exe(), guard, root
        self._guard: subprocess.Popen | None = None
        self._marker = ""

    def _run(self, args: list[str], env: Mapping[str, str], log: Path) -> int:
        with log.open("w", encoding="utf-8") as fh:
            return subprocess.call([self.py, *args], cwd=self.root, env=dict(env), stdout=fh, stderr=subprocess.STDOUT)

    def _start_guard(self, design: str, env: Mapping[str, str]) -> None:
        if not self.use_guard or self._guard is not None:
            return
        self._marker = design
        self._guard = subprocess.Popen(
            [self.py, f"{LOOP}/memory_guard.py", design, "--floor-mb", env.get("GUARD_FLOOR", "900"),
             "--strikes", env.get("GUARD_STRIKES", "3"), "--most", "1.5"],
            cwd=self.root, env=dict(env), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # fmt: skip

    def close(self) -> str:
        """Waits for the guard; what it did, if it stopped the run."""
        if self._guard is not None:
            self._guard.wait()
        stopped = self.out / f"memory_guard_{self._marker}.stopped"
        return f"STOPPED by the memory guard: {stopped.read_text().strip()}" if self._marker and stopped.exists() else ""

    def layout(self, env: Mapping[str, str], log: Path) -> int:
        code = self._run([f"{LOOP}/contract_layout.py"], env, log)
        if code == 0:
            self._run([f"{LOOP}/setup_export.py"], env, log.with_name("final_setup.log"))
        return code

    def optimise(self, design: str, budget: float, voxel: float, args: list[str], env: Mapping[str, str], log: Path) -> tuple[int, str, str]:
        self._start_guard(design, env)
        tag = design.replace("outcome_", "")
        cmd = [f"{LOOP}/topo_free.py", f"{budget:g}", f"{voxel:g}", "200", "--objective", "compliance_tilt", "--beds",
               "--cases", "peak drive", "--route", "split", "--settle", "0.02", "--every", "25", "--beta-most", "32", "--fast",
               "--max-member", "12", "--tag", tag, *args]  # fmt: skip  (propose.py's defaults; the recipe's arguments win)
        code = self._run(cmd, env, log)
        text = log.read_text(encoding="utf-8", errors="replace")
        line = next((ln for ln in text.splitlines() if "done in" in ln), "")
        run = line.rsplit("; ", 1)[-1].strip() if line else ""
        settled = next((ln.split("] ", 1)[1] for ln in text.splitlines() if "settled at" in ln and "] " in ln), "")
        return code, run, settled

    def draw(self, run: str, design: str, env: Mapping[str, str], log: Path) -> int:
        self._start_guard(design, env)
        return self._run([f"{LOOP}/outcome_cad.py", run, design, "skin", "mesh"], env, log)

    def oiltight(self, design: str, env: Mapping[str, str], log: Path) -> int:
        return self._run([f"{LOOP}/oiltight.py", design], env, log)

    def judge(self, design: str, env: Mapping[str, str], fe_log: Path, cast_log: Path) -> tuple[int, int]:
        """FE and castability at once (the GPU's and the CPU's), or one after the other with LOOP_CAST_AFTER=1."""
        with fe_log.open("w", encoding="utf-8") as f1, cast_log.open("w", encoding="utf-8") as f2:
            fe = subprocess.Popen([self.py, f"{LOOP}/fe.py", design, "8.0"], cwd=self.root, env=dict(env), stdout=f1, stderr=subprocess.STDOUT)
            if env.get("LOOP_CAST_AFTER", "0") != "0":
                fe.wait()
            cast = subprocess.Popen([self.py, f"{LOOP}/castable.py", design], cwd=self.root, env=dict(env), stdout=f2, stderr=subprocess.STDOUT)
            return fe.wait(), cast.wait()

    def records(self, design: str, run: str, env: Mapping[str, str], out: Path) -> None:
        for name, args in (("view", ["view_export.py", design]), ("look", ["look.py", design]),
                           ("view_organic", ["view_export.py", f"{design}_organic"]), ("run_view", ["topo_export.py", run]),
                           ("names", ["names.py"])):  # fmt: skip
            self._run([f"{LOOP}/{args[0]}", *args[1:]], env, out / f"{name}_{design}.log")
        if (out / f"{design}_cover.ply").exists():  # each half's face along the pull (campaign_run.sh did it after the flow)
            self._run([f"{LOOP}/look.py", design, "face"], env, out / f"look_face_{design}.log")

    def process(self, design: str, env: Mapping[str, str], log: Path) -> None:
        self._run([f"{LOOP}/process_export.py", design], env, log)


if os.environ.get("LOOP_ENGINES_SELFTEST"):  # the protocol's methods all present (a typo would only show on the laptop)
    from zenryx.workflow.flow import Engines  # noqa: E402

    missing = [m for m in ("layout", "optimise", "draw", "oiltight", "judge", "records", "process") if not callable(getattr(PrototypeEngines, m, None))]
    assert not missing and Engines, missing
