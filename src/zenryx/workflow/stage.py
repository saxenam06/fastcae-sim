"""One stage of the final workflow by itself, in its own process (LOP-33): the engines start each
stage this way, so a stage's memory goes back when it ends and a stage can be stopped by its process
tree; a RunPod worker runs the optimisation the same way.

    python -m zenryx.workflow.stage <stage> --out <folder> --contract <contract.json> [--design
    <name>] [--run <stem>]
        [--budget <kg> --voxel <mm> -- <the recipe's optimiser arguments>]

The stages: `layout`, `optimise`, `draw`, `oiltight`, `fe`, `castable`, `records`, `process`. The
recipe's settings come in the environment. The last line printed is `STAGE_RESULT <json>`: the exit
code and what the stage made (for `optimise`, the run's stem, its settling note and the files it
wrote).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

from zenryx.workflow.recipe import ROOT

RECORDS = ROOT / "web" / "src" / "records"


def _optimise(a: argparse.Namespace, rest: list[str]) -> dict:
    from zenryx.domains.gearbox.housing import optimise

    before = {p.name: p.stat().st_mtime for p in a.out.iterdir()}
    stem, settled = optimise.run(a.design, a.budget, a.voxel, rest, a.out, a.contract, os.environ)
    written = sorted(
        p.name
        for p in a.out.iterdir()
        if p.name.startswith(stem) and before.get(p.name) != p.stat().st_mtime
    )
    return {"run": stem, "settled": settled, "files": written}


def _draw(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.domains.gearbox.housing.draw import DrawSettings, draw

    draw(a.run, a.design, a.out, a.contract, DrawSettings.from_env(os.environ))
    return {}


def _oiltight(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.domains.gearbox.housing.oiltight import check

    return {"tight": check(a.design, a.out, a.contract)["tight"]}


def _fe(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.domains.gearbox.housing.fe import judge

    judge(a.design, a.out, a.contract)
    return {}


def _castable(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.domains.gearbox.housing.castable import castability

    castability(a.design, a.out, a.contract)
    return {}


def _records(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.api import records
    from zenryx.domains.gearbox.housing.look import look

    records.write_all(a.design, a.out, a.records, a.contract)
    look(a.design, a.out)
    look(a.design, a.out, face=True)
    return {}


def _process(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.api import records

    records.process(a.design, a.out, a.records, a.contract)
    return {}


def _layout(a: argparse.Namespace, _rest: list[str]) -> dict:
    from zenryx.domains.gearbox.housing.layout import write

    write(a.contract, a.out)
    return {}


STAGES = {
    "layout": _layout,
    "optimise": _optimise,
    "draw": _draw,
    "oiltight": _oiltight,
    "fe": _fe,
    "castable": _castable,
    "records": _records,
    "process": _process,
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    rest = argv[argv.index("--") + 1 :] if "--" in argv else []
    argv = argv[: argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description="One stage of the final workflow (zenryx.workflow).")
    ap.add_argument("stage", choices=sorted(STAGES))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--records", type=Path, default=RECORDS)
    ap.add_argument("--design", default="")
    ap.add_argument("--run", default="")
    ap.add_argument("--budget", type=float, default=0.0)
    ap.add_argument("--voxel", type=float, default=0.0)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    try:
        result = {"exit": 0, **STAGES[a.stage](a, rest)}
    except Exception as e:  # the stage's failure, said on its log; the flow decides what follows
        traceback.print_exc()
        result = {"exit": 1, "error": f"{type(e).__name__}: {e}"}
    sys.stdout.flush()
    print("STAGE_RESULT " + json.dumps(result), flush=True)
    return int(result["exit"])


if __name__ == "__main__":
    sys.exit(main())
