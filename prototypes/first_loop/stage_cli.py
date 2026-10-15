"""PROTOTYPE (LOP-33, PLT-12) - one stage of the final workflow by itself, for a RunPod worker (the engineer, 15 October: the GPU
for the optimisation alone). `stage_cli.py optimise <spec.json>` runs the optimisation as `engines.py` does and prints, on its last
line, `STAGE_RESULT <json>`: the exit code, the run's stem, its settling note and the files it wrote in data/first_loop/. It goes
when the optimiser is in `src/zenryx`.

    spec.json: {"design": ..., "budget": 7.73, "voxel": 4, "args": [...]}   (the recipe's settings come in the environment)"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engines import PrototypeEngines  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"


def main() -> int:
    stage, spec_path = sys.argv[1], Path(sys.argv[2])
    if stage != "optimise":
        raise SystemExit(f"stage_cli.py runs the optimisation alone, not {stage!r}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    design = spec["design"]
    before = {p.name: p.stat().st_mtime for p in OUT.iterdir()} if OUT.exists() else {}
    log = OUT / f"optimise_{design}.log"
    code, run, settled = PrototypeEngines(OUT, guard=False).optimise(design, float(spec["budget"]), float(spec["voxel"]), list(spec["args"]),
                                                                    os.environ, log)  # fmt: skip
    written = sorted(p.name for p in OUT.iterdir() if before.get(p.name) != p.stat().st_mtime and (bool(run) and p.name.startswith(run) or p == log))
    print("STAGE_RESULT " + json.dumps({"exit": code, "run": run, "settled": settled, "files": written}))
    return code


if __name__ == "__main__":
    sys.exit(main())
