"""What differs between the engineer's Windows laptop and a Linux worker (moved from
`prototypes/first_loop/hostenv.py`: `kill_tree`, `available_mb`; LOP-33): ending a process with its
children (on Windows a venv's python.exe is a launcher with a child, so ending the launcher alone
leaves it), and the memory a run may still take (in a container, its cgroup's limit, not the
host's)."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from pathlib import Path

WINDOWS = os.name == "nt"


def _cgroup_free_mb() -> float | None:
    for limit, used in (
        ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),  # cgroup v2
        (
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
            "/sys/fs/cgroup/memory/memory.usage_in_bytes",
        ),
    ):
        try:
            lim = Path(limit).read_text().strip()
            if lim == "max" or int(lim) > 1 << 60:
                return None
            return (int(lim) - int(Path(used).read_text().strip())) / 2**20
        except (OSError, ValueError):
            continue
    return None


def available_mb() -> float:
    """The memory still available (MB): Windows' own (GlobalMemoryStatusEx); elsewhere the least of
    /proc/meminfo's MemAvailable and what the container's cgroup still allows."""
    if WINDOWS:
        import ctypes

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

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


def _children(pid: int) -> list[int]:
    try:
        out = subprocess.run(
            ["ps", "-o", "pid=", "--ppid", str(pid)], capture_output=True, text=True, timeout=20
        )
        return [int(v) for v in out.stdout.split() if v.strip().isdigit()]
    except Exception:
        return []


def kill_tree(pid: int) -> None:
    """The process and every descendant: `taskkill /F /T` on Windows, SIGKILL elsewhere."""
    if WINDOWS:
        subprocess.call(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    todo, seen = [pid], []
    while todo:  # the tree first, so no child is re-parented before it is found
        p = todo.pop()
        seen.append(p)
        todo += _children(p)
    for p in reversed(seen):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(p, signal.SIGKILL)
