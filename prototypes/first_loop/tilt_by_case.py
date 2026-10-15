"""PROTOTYPE (LOP-20) - a design's graded worst tilt split by load case, with grade.py's own
functions: each case's three worst seats against their lines, with the shaft's lean and the
housing alone. The grade keeps only the worst of both cases; this showed, on 10 October 17:00, that
the designs optimised on peak drive alone fail only in peak reverse.

Run: .venv/Scripts/python.exe prototypes/first_loop/tilt_by_case.py <design stem> [<design stem> ...]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402

spec, _ = grade.load_and_validate(grade.CONTRACT)
margin = grade.value_in(spec.limits.model_margin, "1")
limits = {t.bearing_type: 1000 * grade.value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
leans = {s.shaft: s.lean_at_bearing for s in grade.complete_chain(spec).sections}
for stem in sys.argv[1:]:
    fe = json.loads((grade.OUT / f"fe_{stem}.json").read_text(encoding="utf-8"))
    for case, out in fe["cases"].items():
        rows = []
        for seat, v in out["seats"].items():
            shaft, side = seat.split()
            line = (1 - margin) * limits[types[(shaft, side)]]
            lean = leans[shaft].get(case, {}).get(side, (0.0, 0.0))
            rows.append((grade.shaft_tilt_mrad(out, shaft, v, lean) / line, grade.shaft_tilt_mrad(out, shaft, v) / line, seat))
        rows.sort(reverse=True)
        top = ", ".join(f"{s} {r:.2f} (housing {h:.2f})" for r, h, s in rows[:3])
        print(f"{stem:26s} {case:13s} worst: {top}")
