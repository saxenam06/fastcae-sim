"""The final workflow, end to end (LOP-31, LOP-33): the contract and the recipe fingerprinted; the
layout rebuilt from the contract when the contract changed; one design's flow (`flow.propose`); the
outcome kept in the state file (`final_state.json`). Nothing runs when neither the contract nor the
recipe changed since the last run, unless forced or given an existing optimisation to redraw.
"""

from __future__ import annotations

import datetime
import json
import os
from collections.abc import Mapping
from pathlib import Path

from zenryx.workflow import flow as flows
from zenryx.workflow.grade import MISALIGNMENT
from zenryx.workflow.recipe import FINAL, ROOT, fingerprint, load_recipe

OUT = ROOT / "data" / "first_loop"
STATE = "final_state.json"


def stages(recipe_run: str, layout: bool) -> list[str]:
    """The stages a run will take, in order."""
    named = ["the layout from the contract"] if layout else []
    named.append(f"the optimisation {recipe_run} reused" if recipe_run else "the optimisation")
    return named + [
        "the drawing",
        "the oil-tight gate (an empty start)",
        "FE beside castability",
        "the grade",
        "the Designs tab's records",
    ]


def numbers(record: dict) -> dict:
    """The outcome's headline numbers from a flow's record."""
    grade = record.get("grade") or {}
    lines = grade.get("lines") or {}
    return {
        "mass_kg": grade.get("mass_kg"),
        "worst_seat_um": (lines.get("displacement, peak drive") or {}).get("value_um"),
        "tilt": (lines.get(MISALIGNMENT) or {}).get("ratio"),
        "first_mode_hz": grade.get("first_mode_hz"),
        "clashes": (lines.get("orders") or {}).get("clashes"),
    }


def verdict(record: dict) -> str:
    if record.get("failed"):
        return f"failed: {record['failed']}"
    return (
        "passes every line" if (record.get("grade") or {}).get("pass") else "judged, fails a line"
    )


def run_final(
    engines: flows.Engines,
    *,
    recipe_path: Path = FINAL,
    out: Path = OUT,
    root: Path = ROOT,
    run: str = "",
    design: str = "",
    force: bool = False,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    now: datetime.datetime | None = None,
) -> dict:
    """Run the workflow if the contract or the recipe changed (or `force`, or `run` to redraw).

    Returns what happened: `{"up_to_date": state}`, `{"dry_run": stages}`, or the new state.
    """
    recipe, recipe_sha = load_recipe(recipe_path, root)
    contract = recipe.contract_path(root)
    contract_sha = fingerprint(contract.read_bytes())
    state_path = out / STATE
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    same = state.get("contract_sha") == contract_sha and state.get("recipe_sha") == recipe_sha
    if same and not force and not run:
        return {"up_to_date": state}
    layout = state.get("layout_contract_sha") != contract_sha
    if dry_run:
        return {"dry_run": stages(run, layout)}
    full_env = {**(os.environ if env is None else env), **recipe.env}
    out.mkdir(parents=True, exist_ok=True)
    if layout and engines.layout(full_env, out / "final_layout.log"):
        raise RuntimeError(f"the layout failed: {out / 'final_layout.log'}")
    now = now or datetime.datetime.now()
    name = design or f"{recipe.design}_{now:%m%d_%H%M}"
    record = flows.propose(
        name,
        budget=recipe.budget_kg,
        voxel=recipe.voxel_mm,
        args=list(recipe.optimiser_args),
        engines=engines,
        out=out,
        contract=contract,
        env=full_env,
        run=run,
    )
    run_stem = next(
        (
            s["outputs"][0]
            for s in record["steps"]
            if s.get("id") == "optimise" and s.get("outputs")
        ),
        run or None,
    )
    new = {
        "contract_sha": contract_sha,
        "recipe_sha": recipe_sha,
        "layout_contract_sha": contract_sha,
        "recipe": recipe.recipe,
        "version": recipe.version,
        "design": name,
        "run": run_stem,
        "verdict": verdict(record),
        "numbers": numbers(record),
        "time": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
    }
    state_path.write_text(json.dumps(new, indent=1), encoding="utf-8")
    return new
