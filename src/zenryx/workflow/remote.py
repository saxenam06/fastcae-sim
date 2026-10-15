"""The optimisation on RunPod's GPU, everything else where the workflow runs (PLT-12; the engineer,
15 October: "we need GPU only for optimisation as of now ... for FEM local GPU is sufficient").

`RemoteOptimise` wraps the local `Engines`: every stage runs locally but the optimisation, which
goes to the RunPod endpoint by its two APIs alone:
1. the layout record the optimiser reads (`contract.json`) is uploaded to the network volume
   (RunPod's S3-compatible storage API);
2. a job starts on the endpoint (RunPod's job API): the worker checks out the same commit, runs the
   optimisation, and lists the files it wrote;
3. those files (the run's record, its field, its log) come back to the local folder; the drawing
   and FE carry on from them.

Settings come from the environment, or a `.env` file at the repository's root (never in git):
- `ZENRYX_OPTIMISE_ON`: `runpod` (the default) or `local`;
- `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`: the job API;
- `RUNPOD_VOLUME_ID`, `RUNPOD_DATACENTER`, and `RUNPOD_S3_KEY`/`RUNPOD_S3_SECRET` (or AWS_*): the
  network volume's storage API;
- `ZENRYX_REF`: the commit the worker runs (by default this checkout's HEAD; it must be pushed).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from zenryx.workflow.flow import Engines
from zenryx.workflow.recipe import ROOT

API = "https://api.runpod.ai/v2"
DONE = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}
VOLUME_ROOT = "fastcae-sim"  # the worker's checkout on the volume (`deploy/runpod/handler.py`)


def read_env_file(path: Path = ROOT / ".env") -> dict[str, str]:
    """KEY=value lines of a `.env` file (comments and blank lines skipped); {} if there is none."""
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


@dataclass(frozen=True)
class Settings:
    optimise_on: str
    api_key: str
    endpoint: str
    volume: str
    datacenter: str
    s3_key: str
    s3_secret: str
    ref: str

    @classmethod
    def load(cls, env: Mapping[str, str] | None = None) -> Settings:
        e = {**read_env_file(), **(os.environ if env is None else env)}
        return cls(
            optimise_on=e.get("ZENRYX_OPTIMISE_ON", "runpod").lower(),
            api_key=e.get("RUNPOD_API_KEY", ""),
            endpoint=e.get("RUNPOD_ENDPOINT_ID", ""),
            volume=e.get("RUNPOD_VOLUME_ID", ""),
            datacenter=e.get("RUNPOD_DATACENTER", ""),
            s3_key=e.get("RUNPOD_S3_KEY", e.get("AWS_ACCESS_KEY_ID", "")),
            s3_secret=e.get("RUNPOD_S3_SECRET", e.get("AWS_SECRET_ACCESS_KEY", "")),
            ref=e.get("ZENRYX_REF", ""),
        )

    def missing(self) -> list[str]:
        """The settings the RunPod route needs that are not set."""
        need = {
            "RUNPOD_API_KEY": self.api_key,
            "RUNPOD_ENDPOINT_ID": self.endpoint,
            "RUNPOD_VOLUME_ID": self.volume,
            "RUNPOD_DATACENTER": self.datacenter,
            "RUNPOD_S3_KEY": self.s3_key,
            "RUNPOD_S3_SECRET": self.s3_secret,
        }
        return [k for k, v in need.items() if not v]


class Jobs:
    """RunPod's job API for one endpoint."""

    def __init__(self, api_key: str, endpoint: str):
        self.api_key, self.endpoint = api_key, endpoint

    def call(self, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(
            f"{API}/{self.endpoint}/{path}",
            method="POST" if body is not None else "GET",
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                raise RuntimeError(
                    f"RunPod {path}: HTTP {e.code} {e.read().decode()[:500]}"
                ) from None
            except (urllib.error.URLError, TimeoutError):
                time.sleep(2 ** (attempt + 1))
        raise RuntimeError(f"RunPod {path}: no answer")

    def start(self, job_input: dict) -> str:
        return self.call("run", {"input": job_input})["id"]

    def status(self, job: str) -> dict:
        return self.call(f"status/{job}")

    def cancel(self, job: str) -> None:
        self.call(f"cancel/{job}", {})

    def wait(
        self,
        job: str,
        progress: Callable[[dict], None] = lambda _s: None,
        every: float = 15.0,
        stop: Callable[[], bool] = lambda: False,
    ) -> dict:
        while True:
            s = self.status(job)
            progress(s)
            if s.get("status") in DONE:
                return s
            if stop():
                self.cancel(job)
                raise RuntimeError(f"cancelled: RunPod job {job}")
            time.sleep(every)


class Volume:
    """The network volume through RunPod's S3-compatible storage API."""

    def __init__(self, s: Settings):
        import boto3

        self.bucket = s.volume
        self.s3 = boto3.client(
            "s3",
            region_name=s.datacenter,
            endpoint_url=f"https://s3api-{s.datacenter.lower()}.runpod.io",
            aws_access_key_id=s.s3_key,
            aws_secret_access_key=s.s3_secret,
        )

    def upload(self, local: Path, key: str) -> None:
        self.s3.upload_file(str(local), self.bucket, key)

    def download(self, key: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        self.s3.download_file(self.bucket, key, str(local))


def head_commit(root: Path = ROOT) -> str:
    """This checkout's commit: the worker runs the same code."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


class RemoteOptimise:
    """`Engines` with the optimisation on RunPod and every other stage the local engines'."""

    def __init__(self, local: Engines, settings: Settings, out: Path):
        missing = settings.missing()
        if missing:
            raise RuntimeError(
                "the optimisation on RunPod needs " + ", ".join(missing) + " (in .env); "
                "or set ZENRYX_OPTIMISE_ON=local"
            )
        self.local, self.s, self.out = local, settings, out
        self.jobs = Jobs(settings.api_key, settings.endpoint)
        self.volume = Volume(settings)
        self.job: str | None = None
        self.cancelled = False
        self.last: dict = {}

    def __getattr__(self, name: str):  # every stage but the optimisation is the local engines'
        return getattr(self.local, name)

    def cancel(self) -> None:
        self.cancelled = True
        if hasattr(self.local, "cancel"):
            self.local.cancel()

    def optimise(
        self,
        design: str,
        budget: float,
        voxel: float,
        args: list[str],
        env: Mapping[str, str],
        log: Path,
    ) -> tuple[int, str, str]:
        base = f"{VOLUME_ROOT}/data/first_loop"
        self.volume.upload(self.out / "contract.json", f"{base}/contract.json")
        job_input = {
            "ref": self.s.ref or head_commit(),
            "mode": "optimise",
            "design": design,
            "budget": budget,
            "voxel": voxel,
            "args": list(args),
            "env": {k: v for k, v in env.items() if k.startswith(("LOOP_", "GUARD_"))},
        }
        self.job = self.jobs.start(job_input)
        with log.open("w", encoding="utf-8") as fh:
            fh.write(
                f"RunPod job {self.job} on endpoint {self.s.endpoint}: {json.dumps(job_input)}\n"
            )

            def progress(s: dict) -> None:
                if s.get("output") and s.get("status") not in DONE:
                    fh.write(f"[{time.strftime('%H:%M:%S')}] {json.dumps(s['output'])}\n")
                    fh.flush()

            status = self.jobs.wait(self.job, progress, stop=lambda: self.cancelled)
        out = status.get("output") or {}
        self.last = {"job": self.job, "status": status.get("status"), **out}
        if status.get("status") != "COMPLETED" or "error" in out:
            with log.open("a", encoding="utf-8") as fh:
                fh.write(f"the RunPod job ended {status.get('status')}: {json.dumps(out)[:2000]}\n")
            return 1, "", ""
        worker_log = log.with_name(f"{log.stem}_worker.log")
        for name in out.get("files", []):
            local = worker_log if name == f"optimise_{design}.log" else self.out / name
            self.volume.download(f"{base}/{name}", local)
        with log.open("a", encoding="utf-8") as fh:  # the worker's own log after the job's
            if worker_log.exists():
                fh.write(worker_log.read_text(encoding="utf-8", errors="replace"))
            fh.write(
                f"RunPod: {out.get('minutes')} min on {out.get('gpu', {}).get('name')}, "
                f"peak {out.get('gpu', {}).get('peak_mb')} MB\n"
            )
        return int(out.get("exit", 1)), out.get("run", ""), out.get("settled", "")


def engines_for(local: Engines, out: Path, settings: Settings | None = None) -> Engines:
    """The engines the workflow runs with: the optimisation on RunPod unless set to local."""
    s = settings or Settings.load()
    if s.optimise_on == "local":
        return local
    if s.optimise_on != "runpod":
        raise ValueError(f"ZENRYX_OPTIMISE_ON is 'runpod' or 'local', not {s.optimise_on!r}")
    return RemoteOptimise(local, s, out)
