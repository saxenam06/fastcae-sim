"""The final workflow's stages run here, each in its own process (`python -m
zenryx.workflow.stage`), its output in its log (LOP-33). They replace the prototypes' scripts
(`prototypes/first_loop/engines.py`) with the code moved into `zenryx`, each stage checked against
the prototype's result (`prototypes/first_loop/housing_parity.py`).

A memory guard watches each heavy stage: if the available memory stays under the recipe's floor
(`GUARD_FLOOR` MB) for `GUARD_STRIKES` reads 5 s apart, the stage is ended by its tree and
`memory_guard_<design>.stopped` says so (the laptop blue-screened twice on 2 October with heavy GPU
and memory work at once). `cancel()` ends the running stage and refuses any after it (the API's
cancel).
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path

from zenryx.host import available_mb, kill_tree
from zenryx.workflow.recipe import ROOT

GUARD_EVERY = 5.0  # s between the guard's reads


class LocalEngines:
    def __init__(
        self,
        out: Path,
        contract: Path,
        records: Path | None = None,
        guard: bool = True,
        py: str = "",
    ):
        self.out, self.contract, self.py, self.use_guard = (
            out,
            contract,
            py or sys.executable,
            guard,
        )
        self.records = records or ROOT / "web" / "src" / "records"
        self._running: list[subprocess.Popen] = []
        self._stopped = ""
        self._design = ""
        self.cancelled = False

    # --- running a stage
    # ---------------------------------------------------------------------------------------------

    def _args(self, stage: str, design: str = "", run: str = "") -> list[str]:
        return [
            self.py,
            "-m",
            "zenryx.workflow.stage",
            stage,
            "--out",
            str(self.out),
            "--contract",
            str(self.contract),
            "--records",
            str(self.records),
            "--design",
            design,
            "--run",
            run,
        ]

    def _start(self, args: list[str], env: Mapping[str, str], fh) -> subprocess.Popen:
        if self.cancelled:
            raise RuntimeError("cancelled")
        proc = subprocess.Popen(args, cwd=ROOT, env=dict(env), stdout=fh, stderr=subprocess.STDOUT)
        self._running.append(proc)
        return proc

    def _watch(self, proc: subprocess.Popen, env: Mapping[str, str]) -> None:
        """The memory guard of one stage's process (a thread)."""
        floor, strikes = float(env.get("GUARD_FLOOR", "900")), int(env.get("GUARD_STRIKES", "3"))
        log = self.out / f"memory_guard_{self._design}.log"
        low = 0
        with log.open("a", encoding="utf-8") as fh:
            while proc.poll() is None:
                avail = available_mb()
                fh.write(
                    json.dumps(
                        {
                            "t": time.strftime("%H:%M:%S"),
                            "available_mb": round(avail),
                            "pid": proc.pid,
                        }
                    )
                    + "\n"
                )
                fh.flush()
                low = low + 1 if avail < floor else 0
                if low >= strikes:
                    kill_tree(proc.pid)
                    self._stopped = f"{time.strftime('%H:%M:%S')} {avail:.0f} MB available"
                    (self.out / f"memory_guard_{self._design}.stopped").write_text(
                        self._stopped + "\n", encoding="utf-8"
                    )
                    fh.write(
                        f"{time.strftime('%H:%M:%S')} the available memory stayed under "
                        f"{floor:.0f} MB: ended {proc.pid}\n"
                    )
                    return
                time.sleep(GUARD_EVERY)

    def _wait(self, proc: subprocess.Popen, env: Mapping[str, str], guarded: bool) -> int:
        watcher = (
            threading.Thread(target=self._watch, args=(proc, env), daemon=True)
            if guarded and self.use_guard
            else None
        )
        if watcher:
            watcher.start()
        code = proc.wait()
        if watcher:
            watcher.join()
        self._running.remove(proc)
        return code

    def _run(self, args: list[str], env: Mapping[str, str], log: Path, guarded: bool = True) -> int:
        with log.open("w", encoding="utf-8") as fh:
            return self._wait(self._start(args, env, fh), env, guarded)

    @staticmethod
    def _result(log: Path) -> dict:
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        line = next(
            (ln for ln in reversed(text.splitlines()) if ln.startswith("STAGE_RESULT ")), ""
        )
        return json.loads(line.split(" ", 1)[1]) if line else {}

    def cancel(self) -> None:
        """Ends the stage running (each process by its tree) and refuses any stage after it."""
        self.cancelled = True
        for proc in list(self._running):
            kill_tree(proc.pid)

    def close(self) -> str:
        """What the memory guard did, if it stopped a stage."""
        return f"STOPPED by the memory guard: {self._stopped}" if self._stopped else ""

    # --- the stages (`zenryx.workflow.flow.Engines`)
    # --------------------------------------------------------------------

    def layout(self, env: Mapping[str, str], log: Path) -> int:
        return self._run(self._args("layout"), env, log, guarded=False)

    def optimise(
        self,
        design: str,
        budget: float,
        voxel: float,
        args: list[str],
        env: Mapping[str, str],
        log: Path,
    ) -> tuple[int, str, str]:
        self._design = design
        code = self._run(
            [
                *self._args("optimise", design),
                "--budget",
                f"{budget:g}",
                "--voxel",
                f"{voxel:g}",
                "--",
                *args,
            ],
            env,
            log,
        )
        r = self._result(log)
        return code, r.get("run", ""), r.get("settled", "")

    def draw(self, run: str, design: str, env: Mapping[str, str], log: Path) -> int:
        self._design = design
        return self._run(self._args("draw", design, run), env, log)

    def oiltight(self, design: str, env: Mapping[str, str], log: Path) -> int:
        return self._run(self._args("oiltight", design), env, log)

    def judge(
        self, design: str, env: Mapping[str, str], fe_log: Path, cast_log: Path
    ) -> tuple[int, int]:
        """FE and castability at once (the GPU's and the CPU's), or one after the other with
        LOOP_CAST_AFTER=1."""
        with fe_log.open("w", encoding="utf-8") as f1, cast_log.open("w", encoding="utf-8") as f2:
            fe = self._start(self._args("fe", design), env, f1)
            if env.get("LOOP_CAST_AFTER", "0") != "0":
                fe_code = self._wait(fe, env, True)
                return fe_code, self._wait(
                    self._start(self._args("castable", design), env, f2), env, True
                )
            cast = self._start(self._args("castable", design), env, f2)
            return self._wait(fe, env, True), self._wait(cast, env, False)

    def records(self, design: str, run: str, env: Mapping[str, str], out: Path) -> None:
        self._run(
            self._args("records", design, run), env, out / f"records_{design}.log", guarded=False
        )

    def process(self, design: str, env: Mapping[str, str], log: Path) -> None:
        self._run(self._args("process", design), env, log, guarded=False)
