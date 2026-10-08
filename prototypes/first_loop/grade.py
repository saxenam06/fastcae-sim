"""PROTOTYPE (LOP) - grade every design the loop judged, against the contract's pass lines.

For each data/first_loop/fe_<stem>.json:
- each seat's tilt against its bearing type's limit with the 25 % model margin (the contract's
  limits; the margin applied as FE value <= 0.75 x limit, as proposed on the Physics page). The
  tilt graded is the seat's against its shaft's line through its two seats' centres: the housing's
  share of the bearing's misalignment (LOP-6). The seat's own rotation, which a rigid turn of the
  whole housing would also show, is reported beside it;
- the worst seat displacement against the reference housing's bearing beds (52 µm forward, 138 µm
  in reverse: the design to beat);
- the modes against the mesh frequencies at the rated speed (at least 3 % apart);
- the mass against the reference housing's 7.73 kg.
A design passes only if every line passes. Writes data/first_loop/grades.json and prints a table.

Run: uv run python prototypes/first_loop/grade.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "data" / "first_loop"

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))
REFERENCE = {"mass_kg": 7.732, "peak drive": 52.2, "peak reverse": 138.0}  # µm, the example's


def shaft_tilt_mrad(out: dict, shaft: str, seat: dict) -> float:
    """A seat's tilt against its shaft's line through the two seats' centres, in mrad.

    The seat's axis turns to (theta_y, -theta_x, 1); the line to (du_x, du_y, 1) / span, du the
    +z seat's displacement less the -z seat's. A rigid turn of the whole housing moves both alike.
    """
    a, b = out["seats"][f"{shaft} -z"], out["seats"][f"{shaft} +z"]
    span = out["shafts"][shaft]["span_mm"]
    dx, dy = (b["u"][0] - a["u"][0]) / span, (b["u"][1] - a["u"][1]) / span
    tx, ty = seat["theta"][0], seat["theta"][1]
    return 1000 * math.hypot(ty - dx, -tx - dy)


def main() -> None:
    spec, _ = load_and_validate(CONTRACT)
    margin = value_in(spec.limits.model_margin, "1")
    limits = {t.bearing_type: 1000 * value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
    types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
    grades = []
    for path in sorted(OUT.glob("fe_*.json")):
        fe = json.loads(path.read_text(encoding="utf-8"))
        stem = fe["stem"]
        row = {"stem": stem, "mass_kg": fe["mass_kg"], "lines": {}}
        worst_ratio, worst_own = 0.0, 0.0
        for case, out in fe["cases"].items():
            for seat, v in out["seats"].items():
                shaft, side = seat.split()
                line = (1 - margin) * limits[types[(shaft, side)]]
                worst_ratio = max(worst_ratio, shaft_tilt_mrad(out, shaft, v) / line)
                worst_own = max(worst_own, v["tilt_mrad"] / line)
            disp = max(1000 * v["displacement_mm"] for v in out["seats"].values())
            row["lines"][f"displacement, {case}"] = {
                "value_um": disp,
                "to_beat_um": REFERENCE[case],
                "pass": disp <= REFERENCE[case],
            }
        row["lines"]["tilt against the shaft (worst seat against its line)"] = {
            "ratio": worst_ratio,
            "pass": worst_ratio <= 1.0,
        }
        row["seat_own_tilt_ratio"] = worst_own
        row["lines"]["orders"] = {
            "clashes": fe.get("order_clashes", []),
            "pass": not fe.get("order_clashes"),
        }
        row["lines"]["mass"] = {
            "kg": fe["mass_kg"],
            "to_beat_kg": REFERENCE["mass_kg"],
            "pass": fe["mass_kg"] <= REFERENCE["mass_kg"],
        }
        row["pass"] = all(v["pass"] for v in row["lines"].values())
        row["first_mode_hz"] = (fe.get("modes_hz") or [None])[0]
        grades.append(row)
    (OUT / "grades.json").write_text(json.dumps(grades, indent=1), encoding="utf-8")
    print(
        f"{'design':22s} {'kg':>6s} {'drive µm':>9s} {'rev µm':>8s} {'own':>6s} {'shaft':>6s} {'mode1':>6s}  orders  verdict"
    )
    for g in grades:
        d = g["lines"]["displacement, peak drive"]["value_um"]
        r = g["lines"]["displacement, peak reverse"]["value_um"]
        t = g["lines"]["tilt against the shaft (worst seat against its line)"]["ratio"]
        o = "clash" if g["lines"]["orders"]["clashes"] else "clear"
        print(
            f"{g['stem']:22s} {g['mass_kg']:6.2f} {d:9.0f} {r:8.0f} {g['seat_own_tilt_ratio']:6.2f} {t:6.2f} {g['first_mode_hz'] or 0:6.0f}  {o:6s}  {'PASS' if g['pass'] else 'fail'}"
        )


if __name__ == "__main__":
    main()
