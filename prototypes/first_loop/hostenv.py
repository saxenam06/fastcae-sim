"""PROTOTYPE (PLT-12) - what differs between the engineer's Windows laptop and a Linux GPU worker (RunPod serverless,
15 October): the venv's python, ending a process with its children, and the memory a run may still take. Every caller
behaves on the laptop exactly as before; on Linux the same calls work without PowerShell or taskkill.

- `python_exe()`: `LOOP_PY` if set, else the venv's own (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python`
  elsewhere), else this interpreter.
- `kill_tree(pid)`: `taskkill /F /T` on Windows; on Linux the process and every descendant, by SIGKILL.
- `available_mb()`: Windows' GlobalMemoryStatusEx; on Linux the least of /proc/meminfo's MemAvailable and what the
  container's cgroup still allows (a container's /proc/meminfo shows the host's memory, not its own limit).
- `python_holders(marker, skip)`: the python processes whose command line holds the marker."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WINDOWS = os.name == "nt"


def python_exe() -> str:
    if os.environ.get("LOOP_PY"):
        return os.environ["LOOP_PY"]
    for p in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if p.exists():
            return str(p)
    return sys.executable


def _children(pid: int) -> list[int]:
    try:
        out = subprocess.run(["ps", "-o", "pid=", "--ppid", str(pid)], capture_output=True, text=True, timeout=20)
        return [int(v) for v in out.stdout.split() if v.strip().isdigit()]
    except Exception:
        return []


def kill_tree(pid: int) -> None:
    if WINDOWS:
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    todo, seen = [pid], []
    while todo:  # the tree first, so no child is re-parented before it is found
        p = todo.pop()
        seen.append(p)
        todo += _children(p)
    for p in reversed(seen):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(p, signal.SIGKILL)


def _cgroup_free_mb() -> float | None:
    for limit, used in (("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),  # cgroup v2
                        ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes")):  # fmt: skip
        try:
            lim = Path(limit).read_text().strip()
            if lim == "max" or int(lim) > 1 << 60:
                return None
            return (int(lim) - int(Path(used).read_text().strip())) / 2**20
        except (OSError, ValueError):
            continue
    return None


def available_mb() -> float:
    if WINDOWS:
        import ctypes

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]  # fmt: skip

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return status.ullAvailPhys / 2**20
    avail = float("inf")
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                avail = int(line.split()[1]) / 1024
    except OSError:
        pass
    cg = _cgroup_free_mb()
    return min(avail, cg) if cg is not None else avail


def python_holders(marker: str, skip: tuple[str, ...] = ()) -> list[int]:
    if WINDOWS:
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*" + marker.replace("'", "''") + "*'"
              + "".join(f" -and $_.CommandLine -notlike '*{s}*'" for s in skip) + " } | ForEach-Object { $_.ProcessId }")  # fmt: skip
        try:
            out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60)
            return [int(v) for v in out.stdout.split() if v.strip().isdigit()]
        except Exception:
            return []
    pids = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit() or int(d.name) == os.getpid():
            continue
        try:
            cmd = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if "python" in cmd.split(" ", 1)[0] and marker in cmd and not any(s in cmd for s in skip):
            pids.append(int(d.name))
    return pids
