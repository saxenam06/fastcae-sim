"""PROTOTYPE (LOP-31, LOP-33) - the final workflow, end to end, from the contract to a judged smooth design on the Designs tab
(the engineer, 15 October 14:26: "with changes in the contract or upstream changes the optimization runs with the final workflow
and I see final smooth designs in the Designs tab"). The workflow is `zenryx.workflow` (the recipe, the stages, the gates, the
grade, the state); this script gives it the prototype's engines for the heavy stages (`engines.py`: the optimiser, the drawing,
FE, castability, the pictures and records) and prints the outcome.

1. the contract and the recipe (`src/zenryx/workflow/recipes/final.json`) fingerprinted; the last run's in
   `data/first_loop/final_state.json`;
2. the layout rebuilt from the contract when the contract changed (`contract_layout.py`, then `setup_export.py`);
3. the optimisation, the smooth drawing, the oil-tight gate, FE beside castability, the grade and the UI's records, under the
   memory guard;
4. the outcome recorded in the state file and printed.

Nothing runs when neither the contract nor the recipe changed since the last run (`--force` to run anyway). It needs a GPU
(the optimiser's and FE's cuDSS factors): about 25 minutes with the optimisation, 10 without.

    run_final.py [--recipe <json>] [--run <optimisation stem>] [--design <name>] [--force] [--dry-run]

`--run` reuses an optimisation and only draws and judges it (a drawing recipe changed); `--dry-run` prints what would run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from engines import PrototypeEngines  # noqa: E402

from zenryx.workflow.recipe import FINAL  # noqa: E402
from zenryx.workflow.run import OUT, run_final  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="The final workflow, end to end (LOP-31, LOP-33).")
    ap.add_argument("--recipe", default=str(FINAL))
    ap.add_argument("--run", default="", help="an optimisation's stem to draw and judge again, no new optimisation")
    ap.add_argument("--design", default="", help="the design's name (by default the recipe's, the date and time)")
    ap.add_argument("--force", action="store_true", help="run though neither the contract nor the recipe changed")
    ap.add_argument("--dry-run", action="store_true", help="print what would run")
    a = ap.parse_args()
    engines = PrototypeEngines(OUT)
    try:
        result = run_final(engines, recipe_path=Path(a.recipe), run=a.run, design=a.design, force=a.force, dry_run=a.dry_run)
    finally:
        stopped = engines.close()
    if "up_to_date" in result:
        s = result["up_to_date"]
        print(f"up to date: {s.get('design')} ({s.get('verdict')}), made {s.get('time')}; --force to run again")
    elif "dry_run" in result:
        print("would run: " + "; ".join(result["dry_run"]))
    else:
        print(f"{result['design']}: {result['verdict']}; {json.dumps(result['numbers'])}")
        print("the Designs tab shows it at the top (refresh the page)")
    if stopped:
        print(stopped)


if __name__ == "__main__":
    main()
