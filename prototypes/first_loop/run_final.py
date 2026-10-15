"""PROTOTYPE (LOP-31) - the final workflow, end to end, from the contract to a judged smooth design on the Designs tab (the
engineer, 15 October 14:26: "with changes in the contract or upstream changes the optimization runs with the final workflow
and I see final smooth designs in the Designs tab"). Its settings are one versioned recipe (`recipes/final.json`); this
script only runs them:

1. the contract and the recipe fingerprinted (sha256); the last run's are in `data/first_loop/final_state.json`;
2. the layout rebuilt from the contract when the contract changed (`contract_layout.py`, then `setup_export.py`);
3. the optimisation, the smooth drawing, FE, castability, oil-tightness, the grade and the UI's records, by `campaign_run.sh`
   (`propose.py` under the memory guard) with the recipe's arguments and environment;
4. the outcome recorded in the state file and printed.

Nothing runs when neither the contract nor the recipe changed since the last run (`--force` to run anyway). It needs the
laptop's GPU (the optimiser's and FE's cuDSS factors): about 25 minutes with the optimisation, 10 without.

    run_final.py [--recipe recipes/final.json] [--run <optimisation stem>] [--design <name>] [--force] [--dry-run]

`--run` reuses an optimisation and only draws and judges it (a drawing recipe changed); `--dry-run` prints what would run."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"
STATE = OUT / "final_state.json"
KNOWN = {"recipe", "version", "agreed", "contract", "design", "budget_kg", "voxel_mm", "optimiser_args", "env"}


def load_recipe(path: Path) -> dict:
    """The recipe, checked: its keys known, its environment only the loop's settings, its contract present."""
    r = json.loads(path.read_text(encoding="utf-8"))
    unknown = set(r) - KNOWN
    missing = KNOWN - set(r)
    if unknown or missing:
        raise SystemExit(f"{path}: unknown keys {sorted(unknown)}, missing {sorted(missing)}")
    bad = [k for k in r["env"] if not (k.startswith("LOOP_") or k.startswith("GUARD_"))]
    if bad:
        raise SystemExit(f"{path}: the environment holds only LOOP_ and GUARD_ settings, not {bad}")
    if not (ROOT / r["contract"]).exists():
        raise SystemExit(f"{path}: no contract at {r['contract']}")
    return r


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def run(cmd: list[str], env: dict, dry: bool, log: Path | None = None) -> int:
    """One stage, its output to `log` (or the console); its exit code."""
    print(f"[{datetime.datetime.now():%H:%M:%S}] " + " ".join(cmd), flush=True)
    if dry:
        return 0
    if log is None:
        return subprocess.run(cmd, cwd=ROOT, env=env).returncode
    with open(log, "w", encoding="utf-8") as f:
        return subprocess.run(cmd, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT).returncode


def main() -> None:
    ap = argparse.ArgumentParser(description="The final workflow, end to end (LOP-31).")
    ap.add_argument("--recipe", default=str(HERE / "recipes" / "final.json"))
    ap.add_argument("--run", default="", help="an optimisation's stem to draw and judge again, no new optimisation")
    ap.add_argument("--design", default="", help="the design's name (by default the recipe's, the date and time)")
    ap.add_argument("--force", action="store_true", help="run though neither the contract nor the recipe changed")
    ap.add_argument("--dry-run", action="store_true", help="print what would run")
    a = ap.parse_args()
    recipe_path = Path(a.recipe)
    recipe = load_recipe(recipe_path)
    contract_sha = sha((ROOT / recipe["contract"]).read_bytes())
    recipe_sha = sha(recipe_path.read_bytes())
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    print(f"the recipe {recipe['recipe']} v{recipe['version']} ({recipe_sha}); the contract {recipe['contract']} ({contract_sha})")
    if not a.force and not a.run and state.get("contract_sha") == contract_sha and state.get("recipe_sha") == recipe_sha:
        print(f"up to date: {state.get('design')} ({state.get('verdict')}), made {state.get('time')}; --force to run again")
        return
    py = sys.executable
    env = dict(os.environ)
    env.update({k: str(v) for k, v in recipe["env"].items()})
    OUT.mkdir(parents=True, exist_ok=True)
    if state.get("layout_contract_sha") != contract_sha:  # the layout from the contract, and the UI's view of the set-up
        if run([py, "prototypes/first_loop/contract_layout.py"], env, a.dry_run, OUT / "final_layout.log"):
            raise SystemExit(f"the layout failed: {OUT / 'final_layout.log'}")
        run([py, "prototypes/first_loop/setup_export.py"], env, a.dry_run, OUT / "final_setup.log")
    design = a.design or f"{recipe['design']}_{datetime.datetime.now():%m%d_%H%M}"
    cmd = ["bash", "prototypes/first_loop/campaign_run.sh", design, "--budget", str(recipe["budget_kg"]), "--voxel", str(recipe["voxel_mm"])]
    cmd += ["--run", a.run] if a.run else ["--", *recipe["optimiser_args"]]
    code = run(cmd, env, a.dry_run)
    if a.dry_run:
        return
    flow_path = OUT / f"flow_{design}.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8")) if flow_path.exists() else {}
    grade = flow.get("grade") or {}
    verdict = "failed: " + str(flow["failed"]) if flow.get("failed") else ("passes every line" if grade.get("pass") else "judged, fails a line")
    lines = grade.get("lines") or {}
    numbers = {
        "mass_kg": grade.get("mass_kg"),
        "worst_seat_um": (lines.get("displacement, peak drive") or {}).get("value_um"),
        "tilt": (lines.get("misalignment (worst seat against its line)") or {}).get("ratio"),
        "first_mode_hz": grade.get("first_mode_hz"),
        "clashes": (lines.get("orders") or {}).get("clashes"),
    }
    run_stem = next((s.get("outputs", [None])[0] for s in flow.get("steps", []) if s.get("id") == "optimise"), a.run or None)
    STATE.write_text(json.dumps({"contract_sha": contract_sha, "recipe_sha": recipe_sha, "layout_contract_sha": contract_sha,
                                 "recipe": recipe["recipe"], "version": recipe["version"], "design": design, "run": run_stem,
                                 "verdict": verdict, "numbers": numbers, "exit": code,
                                 "time": f"{datetime.datetime.now():%Y-%m-%d %H:%M}"}, indent=1), encoding="utf-8")  # fmt: skip
    print(f"{design}: {verdict}; {json.dumps(numbers)}")
    print("the Designs tab shows it at the top (refresh the page)")


if __name__ == "__main__":
    main()
