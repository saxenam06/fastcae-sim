"""The RunPod serverless worker (PLT-12; the engineer, 15 October: the GPU paid only while an optimisation runs, a 16 GB card
so the voxels can go finer than the laptop's 4 mm).

A job is one heavy run on the GPU. The worker keeps a checkout of this repository on the endpoint's network volume
(`/runpod-volume/fastcae-sim`), so `data/` (every run, field, mesh and judgement) and the UI's generated records
(`web/src/records/`) persist between jobs, exactly as on the laptop; each job first moves the checkout to the git ref it
names (ignored files are kept). The Python environment is the image's (`/opt/venv`, built from `uv.lock`); a job whose
`uv.lock` differs from the image's is refused, since its dependencies would be wrong: rebuild the image.

Input (`job["input"]`):
    {"ref": "product/end-to-end",           # a branch, tag or commit on GitHub (default: the branch)
     "mode": "final" | "script",           # default "final"
     # mode "final": prototypes/first_loop/run_final.py with these
     "recipe": "prototypes/first_loop/recipes/final.json", "run": "<stem>", "design": "<name>", "force": false,
     # mode "script": one script under prototypes/first_loop/ (.py or .sh) with its arguments
     "script": "model_vs_fe.py", "args": ["baseline2_lw8_smooth"],
     "env": {"LOOP_...": "..."}}           # extra LOOP_/GUARD_ settings for this job only (a check, never the baseline)

Output: the exit code, the log's tail, `final_state.json` (mode "final"), the GPU's peak memory and the files written
under `data/first_loop/` and `web/src/records/` during the job (to fetch with `sync.sh pull`).

One job at a time: set the endpoint's max workers to 1 (the checkout and `data/` are shared); a lock file on the volume
refuses a second job beside a first."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import runpod

VOLUME = Path(os.environ.get("ZENRYX_VOLUME", "/runpod-volume"))
WORK = VOLUME / "fastcae-sim"
REPO = os.environ.get("ZENRYX_REPO", "github.com/saxenam06/fastcae-sim.git")
DEFAULT_REF = os.environ.get("ZENRYX_REF", "product/end-to-end")
VENV = Path(os.environ.get("ZENRYX_VENV", "/opt/venv"))
LOCK_SHA = Path("/opt/uv.lock.sha256")
LOCK = VOLUME / "zenryx.lock"
STALE_LOCK_S = 8 * 3600
TAIL = 60


def sh(cmd: list[str], cwd: Path | None = None, extra: list[str] | None = None) -> str:
    """A short command, its output; raises with it on failure. `extra` are arguments kept out of the error (a token)."""
    p = subprocess.run((cmd[:1] + (extra or []) + cmd[1:]), cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd)}: {(p.stdout + p.stderr).strip()[-2000:]}")
    return p.stdout.strip()


def git_auth() -> list[str]:
    """git's options for a private repository: the token as a header for this call, never written into .git/config."""
    tok = os.environ.get("GITHUB_TOKEN", "")
    if not tok:
        return []
    basic = base64.b64encode(f"x-access-token:{tok}".encode()).decode()
    return ["-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {basic}"]


def checkout(ref: str) -> str:
    """The volume's checkout moved to `ref`; its commit."""
    url = f"https://{REPO}"
    if not (WORK / ".git").exists():
        WORK.parent.mkdir(parents=True, exist_ok=True)
        sh(["git", "clone", "--no-checkout", url, str(WORK)], extra=git_auth())
    sh(["git", "fetch", "--depth", "50", "origin", ref], cwd=WORK, extra=git_auth())
    sh(["git", "checkout", "--force", "--detach", "FETCH_HEAD"], cwd=WORK)
    venv_link = WORK / ".venv"
    if not venv_link.exists():
        venv_link.symlink_to(VENV)
    return sh(["git", "rev-parse", "--short", "HEAD"], cwd=WORK)


def check_lock() -> None:
    want = LOCK_SHA.read_text().strip() if LOCK_SHA.exists() else ""
    have = hashlib.sha256((WORK / "uv.lock").read_bytes()).hexdigest()
    if want and want != have:
        raise RuntimeError("uv.lock at this ref differs from the image's: rebuild the worker image (deploy/runpod/README.md)")


def take_lock(job_id: str) -> None:
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime > STALE_LOCK_S:
        LOCK.unlink()
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(f"another job holds the volume ({LOCK.read_text().strip()}); set max workers to 1") from None
    os.write(fd, f"{job_id} {time.strftime('%Y-%m-%d %H:%M:%S')}".encode())
    os.close(fd)


class GpuPeak(threading.Thread):
    """The GPU's memory in use, sampled every few seconds: the peak tells how fine the voxels may go on this card."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.peak_mb, self.total_mb, self.name, self.stop = 0.0, None, None, threading.Event()

    def run(self) -> None:
        while not self.stop.is_set():
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]  # fmt: skip
                name, used, total = (v.strip() for v in out.split(","))
                self.name, self.total_mb, self.peak_mb = name, float(total), max(self.peak_mb, float(used))
            except Exception:
                pass
            self.stop.wait(5)


def snapshot(roots: list[Path]) -> dict[str, float]:
    out = {}
    for r in roots:
        if r.exists():
            for p in r.rglob("*"):
                if p.is_file():
                    out[str(p.relative_to(WORK))] = p.stat().st_mtime
    return out


def start_display() -> dict:
    """A virtual display for the pictures (pyvista, gmsh): the worker has no screen."""
    if os.environ.get("DISPLAY") or not shutil.which("Xvfb"):
        return {}
    subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return {"DISPLAY": ":99"}


def command(inp: dict) -> list[str]:
    py = str(VENV / "bin" / "python")
    mode = inp.get("mode", "final")
    if mode == "final":
        cmd = [py, "-u", "prototypes/first_loop/run_final.py"]
        if inp.get("recipe"):
            cmd += ["--recipe", str(inp["recipe"])]
        if inp.get("run"):
            cmd += ["--run", str(inp["run"])]
        if inp.get("design"):
            cmd += ["--design", str(inp["design"])]
        if inp.get("force"):
            cmd.append("--force")
        return cmd
    if mode == "script":
        name = str(inp.get("script", ""))
        path = (WORK / "prototypes" / "first_loop" / name).resolve()
        if path.parent != (WORK / "prototypes" / "first_loop").resolve() or path.suffix not in (".py", ".sh") or not path.exists():
            raise RuntimeError(f"no script prototypes/first_loop/{name}")
        args = [str(a) for a in inp.get("args", [])]
        return (["bash", str(path)] if path.suffix == ".sh" else [py, "-u", str(path)]) + args
    raise RuntimeError(f"unknown mode {mode!r}: 'final' or 'script'")


def handler(job: dict) -> dict:
    inp = job.get("input") or {}
    t0 = time.time()
    bad = [k for k in inp.get("env", {}) if not (k.startswith("LOOP_") or k.startswith("GUARD_"))]
    if bad:
        return {"error": f"env holds only LOOP_ and GUARD_ settings, not {bad}"}
    try:
        take_lock(job["id"])
    except RuntimeError as e:
        return {"error": str(e)}
    gpu = GpuPeak()
    gpu.start()
    try:
        commit = checkout(str(inp.get("ref") or DEFAULT_REF))
        check_lock()
        out_dir = WORK / "data" / "first_loop"
        out_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)  # the run needs no access to GitHub
        env.update({"LOOP_PY": str(VENV / "bin" / "python"), "PYTHONPATH": str(WORK / "src"), "PYTHONUNBUFFERED": "1", "MPLBACKEND": "Agg"})
        env.update(start_display())
        env.update({k: str(v) for k, v in inp.get("env", {}).items()})
        cmd = command(inp)
        roots = [out_dir, WORK / "web" / "src" / "records"]
        before = snapshot(roots)
        log = out_dir / f"runpod_{job['id']}.log"
        with log.open("w", encoding="utf-8") as fh:
            fh.write(f"commit {commit}; {' '.join(cmd)}\n")
            fh.flush()
            proc = subprocess.Popen(cmd, cwd=WORK, env=env, stdout=fh, stderr=subprocess.STDOUT)
            while proc.poll() is None:
                time.sleep(30)
                last = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()][-1:]
                runpod.serverless.progress_update(job, {"minutes": round((time.time() - t0) / 60, 1), "gpu_peak_mb": gpu.peak_mb, "last": last})
        after = snapshot(roots)
        written = sorted(p for p, m in after.items() if before.get(p) != m)
        state = out_dir / "final_state.json"
        return {
            "exit": proc.returncode,
            "commit": commit,
            "command": cmd,
            "minutes": round((time.time() - t0) / 60, 1),
            "gpu": {"name": gpu.name, "total_mb": gpu.total_mb, "peak_mb": gpu.peak_mb},
            "final_state": json.loads(state.read_text(encoding="utf-8")) if inp.get("mode", "final") == "final" and state.exists() else None,
            "log": str(log.relative_to(WORK)),
            "tail": log.read_text(encoding="utf-8", errors="replace").splitlines()[-TAIL:],
            "written": written,
        }
    except Exception as e:  # a refusal or a setup failure, reported as the job's error
        return {"error": str(e), "minutes": round((time.time() - t0) / 60, 1)}
    finally:
        gpu.stop.set()
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
