"""Send a heavy run to the RunPod serverless worker and wait for it (PLT-12). Standard library only: run it with any
python 3.10+, on the laptop or in a cloud session.

Needs RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in the environment (never in git; `.env` is ignored).

    submit.py final [--ref product/end-to-end] [--recipe <path>] [--run <stem>] [--design <name>] [--force] [--no-wait]
    submit.py script <name under prototypes/first_loop> [args ...] [--ref ...] [--no-wait]
    submit.py status <job id>        # where a job stands (its last progress line, or its result)
    submit.py cancel <job id>
    submit.py health                 # the endpoint's workers and queue

The code run is what is on GitHub at --ref: commit and push first. A job's files stay on the network volume;
`sync.sh pull <pattern>` fetches them into data/ and web/src/records/."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.runpod.ai/v2"
DONE = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}


def call(path: str, body: dict | None = None) -> dict:
    key, endpoint = os.environ.get("RUNPOD_API_KEY"), os.environ.get("RUNPOD_ENDPOINT_ID")
    if not key or not endpoint:
        raise SystemExit("set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID")
    req = urllib.request.Request(f"{API}/{endpoint}/{path}", method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})  # fmt: skip
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}") from None
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** (attempt + 1))
    raise SystemExit(f"{path}: no answer from RunPod")


def wait(job_id: str, every: float = 30) -> dict:
    last = None
    while True:
        s = call(f"status/{job_id}")
        state = s.get("status")
        line = json.dumps(s.get("output")) if state not in DONE and s.get("output") else state
        if line != last:
            print(f"[{time.strftime('%H:%M:%S')}] {line}", flush=True)
            last = line
        if state in DONE:
            return s
        time.sleep(every)


def report(s: dict) -> None:
    out = s.get("output") or {}
    if s.get("status") != "COMPLETED" or "error" in out:
        print(json.dumps(s, indent=1))
        sys.exit(1)
    print("\n".join(out.get("tail", [])[-20:]))
    print(json.dumps({k: out.get(k) for k in ("exit", "commit", "minutes", "gpu", "final_state", "log")}, indent=1))
    print(f"{len(out.get('written', []))} files written; fetch them: bash deploy/runpod/sync.sh pull <pattern>")
    if s.get("executionTime"):
        print(f"billed GPU time about {s['executionTime'] / 1000 / 60:.1f} min (plus the worker's start)")
    sys.exit(out.get("exit") or 0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the loop's heavy work on the RunPod worker (PLT-12).")
    sub = ap.add_subparsers(dest="what", required=True)
    f = sub.add_parser("final", help="the final workflow (python -m zenryx.workflow.run) on the worker")
    f.add_argument("--recipe", default="")
    f.add_argument("--run", default="")
    f.add_argument("--design", default="")
    f.add_argument("--force", action="store_true")
    sc = sub.add_parser("script", help="one script under prototypes/first_loop/")
    sc.add_argument("script")
    sc.add_argument("args", nargs=argparse.REMAINDER)
    for p in (f, sc):
        p.add_argument("--ref", default="product/end-to-end")
        p.add_argument("--env", action="append", default=[], help="LOOP_X=value, for this job only")
        p.add_argument("--no-wait", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("job")
    ca = sub.add_parser("cancel")
    ca.add_argument("job")
    sub.add_parser("health")
    a = ap.parse_args()

    if a.what == "health":
        print(json.dumps(call("health"), indent=1))
        return
    if a.what == "cancel":
        print(json.dumps(call(f"cancel/{a.job}", {}), indent=1))
        return
    if a.what == "status":
        s = call(f"status/{a.job}")
        report(s) if s.get("status") in DONE else print(json.dumps(s, indent=1))
        return
    inp: dict = {"ref": a.ref, "mode": a.what, "env": dict(kv.split("=", 1) for kv in a.env)}
    if a.what == "final":
        inp.update({k: v for k, v in {"recipe": a.recipe, "run": a.run, "design": a.design, "force": a.force}.items() if v})
    else:
        inp.update({"script": a.script, "args": a.args})
    job = call("run", {"input": inp})
    print(f"job {job['id']} ({job.get('status')}): {json.dumps(inp)}")
    if a.no_wait:
        print(f"later: python deploy/runpod/submit.py status {job['id']}")
        return
    report(wait(job["id"]))


if __name__ == "__main__":
    main()
