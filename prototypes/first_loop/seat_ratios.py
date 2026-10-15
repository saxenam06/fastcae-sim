"""PROTOTYPE (LOP-28) - each seat's misalignment against its line, as `grade.py` reads the worst (the seat against its
shaft's chord, plus the shaft's own lean), for one or more designs, beside the optimiser's own reading of the same seats at
its run's end (the binary check's nominal ratios times the run's factors of safety, so both are against the true line):
which seat governs, and how much the model flatters each (13 October 01:58: the cover's input seat's own factor of 1.4 moved
its tilt 8 %, but the worst ratio stayed 1.04).

Run: .venv/Scripts/python.exe prototypes/first_loop/seat_ratios.py <design> [<design> ...]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import grade  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

OUT = grade.OUT


def main(designs: list[str]) -> None:
    spec, _ = load_and_validate(grade.CONTRACT)
    margin = value_in(spec.limits.model_margin, "1")
    limits = {t.bearing_type: 1000 * value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
    types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
    leans = {s.shaft: s.lean_at_bearing for s in complete_chain(spec).sections}
    for d in designs:
        fe = json.loads((OUT / f"fe_{d}.json").read_text(encoding="utf-8"))
        rec = json.loads((OUT / f"{d}.json").read_text(encoding="utf-8"))
        run = json.loads((OUT / f"{rec['outcome_of']}.json").read_text(encoding="utf-8"))
        safety = float(run.get("safety") or 1.0)
        seat_f = run.get("safety_seats") or {}
        model = (run.get("history") or [{}])[-1].get("ratios", {})
        print(f"{d}:")
        for case, out in fe["cases"].items():
            if case not in grade.GRADED_CASES:
                continue
            for seat, v in out["seats"].items():
                shaft, side = seat.split()
                line = (1 - margin) * limits[types[(shaft, side)]]
                lean = leans[shaft].get(case, {}).get(side, (0.0, 0.0))
                ratio = grade.shaft_tilt_mrad(out, shaft, v, lean) / line
                key = next((k for k in model if k.startswith(f"{shaft} {side}")), None)
                m_ratio = model[key] / float(seat_f.get(seat, safety)) if key else float("nan")
                print(f"   {seat:16s} FE {ratio:6.3f} x its line; the model {m_ratio:6.3f} (FE / model {ratio / m_ratio if m_ratio == m_ratio and m_ratio > 0 else float('nan'):5.2f})")


if __name__ == "__main__":
    main(sys.argv[1:])
