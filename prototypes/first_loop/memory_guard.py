"""PROTOTYPE (LOP-28) - a guard for an unattended campaign: while a run is going, read the machine's available memory and
the GPU's every few seconds, write them to a log, and if the available memory stays under a floor, end every python
process whose command line holds the run's marker, by its tree (the machine blue-screened twice on 2 October with heavy
GPU and memory work at once; the engineer left the campaign running on 13 October 00:16).

The available memory is Windows' own (GlobalMemoryStatusEx, through ctypes: no psutil in the venv); the processes are
found by their command lines (Win32_Process, through PowerShell) and ended with `taskkill /F /T`. On a Linux GPU worker
(RunPod, PLT-12) the same through `hostenv.py`: /proc and the container's cgroup, the tree ended by SIGKILL.

Run: .venv/Scripts/python.exe prototypes/first_loop/memory_guard.py <marker> [--floor-mb 900] [--every 5] [--strikes 3]
     It ends by itself when no process holds the marker any more (after it has seen one), or after --most hours."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from hostenv import available_mb, kill_tree, python_holders

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"


def gpu_mb() -> float | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
        return float(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


def holders(marker: str) -> list[int]:
    """The python processes whose command line holds the marker (not this guard, nor `run_final.py`, which only orchestrates:
    given `--design <marker>` it held the marker itself and its flow waited on it for ever, 15 October 15:00)."""
    return python_holders(marker, skip=("memory_guard", "run_final"))


def main(marker: str, floor_mb: float, every: float, strikes: int, most_hours: float) -> None:
    log = OUT / f"memory_guard_{marker}.log"
    seen, low, t0 = False, 0, time.time()
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%H:%M:%S')} guarding '{marker}': floor {floor_mb:.0f} MB, {strikes} strikes, every {every:g} s\n")
        while time.time() - t0 < most_hours * 3600:
            pids = holders(marker)
            seen = seen or bool(pids)
            if seen and not pids:
                fh.write(f"{time.strftime('%H:%M:%S')} no process holds the marker: done\n")
                return
            avail, gpu = available_mb(), gpu_mb()
            fh.write(json.dumps({"t": time.strftime("%H:%M:%S"), "available_mb": round(avail), "gpu_mb": gpu, "pids": pids}) + "\n")
            fh.flush()
            low = low + 1 if avail < floor_mb else 0
            if low >= strikes and pids:
                for pid in pids:
                    kill_tree(pid)
                fh.write(f"{time.strftime('%H:%M:%S')} the available memory stayed under {floor_mb:.0f} MB: ended {pids}\n")
                (OUT / f"memory_guard_{marker}.stopped").write_text(f"{time.strftime('%H:%M:%S')} {avail:.0f} MB available\n", encoding="utf-8")
                return
            time.sleep(every)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Stop a run whose machine runs out of memory (LOP-28).")
    ap.add_argument("marker")
    ap.add_argument("--floor-mb", type=float, default=900.0)
    ap.add_argument("--every", type=float, default=5.0)
    ap.add_argument("--strikes", type=int, default=3)
    ap.add_argument("--most", type=float, default=2.0, help="hours at most")
    a = ap.parse_args()
    main(a.marker, a.floor_mb, a.every, a.strikes, a.most)
