"""The API the UI's Run button calls (PLT-5).

The engineer, 15 October: "I already need a run button on the UI on the contract page".
FastAPI on port 8030 (zenryx's own; the UI proxies `/api` to it).

- `GET  /api/workflow`: the recipe, the contract's fingerprint against the last run's (has the
  contract changed since?), the last run's outcome, and the run going now if any;
- `POST /api/runs`: start the final workflow (`zenryx.workflow.run.run_final`); one run at a time;
- `GET  /api/runs`, `GET /api/runs/{id}`: each run's state, its stages so far, its log's tail;
- `POST /api/runs/{id}/cancel`: stop it (the stage running is ended, nothing after it starts).

Each run's state is a file, `data/runs/<id>.json`, so the list survives a restart of the server.
The workflow's heavy stages are the `Engines` the server is given (`create_app`); where the
optimisation runs is `zenryx.workflow.remote`'s setting. Run it without `--reload` (CLAUDE.md).
"""

from __future__ import annotations

import datetime
import json
import threading
import traceback
import uuid
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from zenryx.workflow import run as workflow
from zenryx.workflow.flow import Engines
from zenryx.workflow.recipe import FINAL, ROOT, fingerprint, load_recipe

PORT = 8030
STAGES = ["layout", "optimise", "draw", "oiltight", "judge", "grade", "records"]
LOG_TAIL = 40


class RunRequest(BaseModel):
    force: bool = False  # run though neither the contract nor the recipe changed
    run: str = ""  # an existing optimisation's stem: draw and judge it again
    design: str = ""  # the design's name (by default the recipe's, the date and time)


class Cancelled(RuntimeError):
    pass


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def create_app(
    make_engines: Callable[[Path], Engines],
    out: Path = workflow.OUT,
    runs_dir: Path | None = None,
    recipe_path: Path = FINAL,
) -> FastAPI:
    """The API, its runs' heavy stages made by `make_engines(out)` for each run."""
    runs_dir = runs_dir or out.parent / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="zenryx", docs_url="/api/docs", openapi_url="/api/openapi.json")
    lock = threading.Lock()
    live: dict[str, dict] = {}  # the run going now: its state and its engines

    def path(run_id: str) -> Path:
        return runs_dir / f"{run_id}.json"

    def save(state: dict) -> None:
        path(state["id"]).write_text(json.dumps(state, indent=1), encoding="utf-8")

    def load(run_id: str) -> dict:
        p = path(run_id)
        if not p.exists():
            raise HTTPException(404, f"no run {run_id}")
        return json.loads(p.read_text(encoding="utf-8"))

    def log_tail(state: dict) -> list[str]:
        stage = state.get("stage")
        name = {
            "layout": "final_layout.log",
            "optimise": f"optimise_{state.get('design')}.log",
            "draw": f"build_{state.get('design')}.log",
            "oiltight": f"oiltight_{state.get('design')}.log",
            "judge": f"fe_{state.get('design')}.log",
        }.get(stage or "")
        p = out / name if name else None
        if not p or not p.exists():
            return []
        return p.read_text(encoding="utf-8", errors="replace").splitlines()[-LOG_TAIL:]

    def go(state: dict, req: RunRequest, engines: Engines) -> None:
        def on_stage(stage: str) -> None:
            if state.get("cancel"):
                raise Cancelled("cancelled")
            now = _now()
            if state["stages"] and "ended" not in state["stages"][-1]:
                state["stages"][-1]["ended"] = now
            state["stages"].append({"stage": stage, "started": now})
            state["stage"] = stage
            save(state)

        try:
            result = workflow.run_final(
                engines,
                recipe_path=recipe_path,
                out=out,
                run=req.run,
                design=state["design"],
                force=True,  # the button asks for a run: `/api/workflow` says whether one is due
                on_stage=on_stage,
            )
            state.update(status="done", result=result)
        except Cancelled:
            state.update(status="cancelled")
        except Exception as e:  # the run's failure, kept for the UI
            state.update(
                status="cancelled" if state.get("cancel") else "failed",
                error=f"{type(e).__name__}: {e}",
                trace=traceback.format_exc()[-4000:],
            )
        finally:
            if state["stages"] and "ended" not in state["stages"][-1]:
                state["stages"][-1]["ended"] = _now()
            state["ended"] = _now()
            state["stage"] = None
            save(state)
            with lock:
                live.clear()

    @app.get("/api/workflow")
    def workflow_state() -> dict:
        recipe, recipe_sha = load_recipe(recipe_path)
        contract_sha = fingerprint(recipe.contract_path().read_bytes())
        st = out / workflow.STATE
        last = json.loads(st.read_text(encoding="utf-8")) if st.exists() else None
        return {
            "recipe": {"name": recipe.recipe, "version": recipe.version, "sha": recipe_sha},
            "contract": {"path": recipe.contract, "sha": contract_sha},
            "last": last,
            "changed": {
                "contract": last is None or last.get("contract_sha") != contract_sha,
                "recipe": last is None or last.get("recipe_sha") != recipe_sha,
            },
            "running": live.get("state", {}).get("id"),
        }

    @app.post("/api/runs", status_code=202)
    def start(req: RunRequest) -> dict:
        with lock:
            if live:
                raise HTTPException(409, f"a run is going: {live['state']['id']}")
            recipe, _ = load_recipe(recipe_path)
            design = req.design or f"{recipe.design}_{datetime.datetime.now():%m%d_%H%M}"
            state = {
                "id": uuid.uuid4().hex[:12],
                "design": design,
                "reuse": req.run or None,
                "status": "running",
                "started": _now(),
                "stage": None,
                "stages": [],
            }
            engines = make_engines(out)
            live.update(state=state, engines=engines)
            save(state)
        threading.Thread(target=go, args=(state, req, engines), daemon=True).start()
        return state

    @app.get("/api/runs")
    def runs() -> list[dict]:
        states = [json.loads(p.read_text(encoding="utf-8")) for p in runs_dir.glob("*.json")]
        return sorted(states, key=lambda s: s.get("started", ""), reverse=True)

    @app.get("/api/runs/{run_id}")
    def one(run_id: str) -> dict:
        state = live["state"] if live.get("state", {}).get("id") == run_id else load(run_id)
        return {**state, "log": log_tail(state), "stages_all": STAGES}

    @app.post("/api/runs/{run_id}/cancel")
    def cancel(run_id: str) -> dict:
        with lock:
            if live.get("state", {}).get("id") != run_id:
                raise HTTPException(409, f"run {run_id} is not going")
            live["state"]["cancel"] = True
            engines = live["engines"]
        if hasattr(engines, "cancel"):
            engines.cancel()  # the stage running is ended; on_stage stops the next
        return {"id": run_id, "cancel": True}

    return app


def serve(
    make_engines: Callable[[Path], Engines], host: str = "127.0.0.1", port: int = PORT
) -> None:
    """The API on this machine (no `--reload`: on Windows it signals every process on the
    console)."""
    import uvicorn

    uvicorn.run(create_app(make_engines), host=host, port=port, log_level="info")


def main() -> None:
    """`python -m zenryx.api.server`: the API the Run button calls, on port 8030, its runs' stages
    `zenryx.workflow.run.engines` (every stage here; the optimisation on RunPod only if `.env` says
    `ZENRYX_OPTIMISE_ON=runpod`). A server: start it only on the engineer's word."""
    serve(lambda out: workflow.engines(out))


__all__ = ["create_app", "serve", "main", "ROOT"]


if __name__ == "__main__":
    main()
