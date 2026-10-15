"""PROTOTYPE (LOP) - grade every design the loop judged, against the contract's pass lines.

For each data/first_loop/fe_<stem>.json:
- each seat's tilt against its bearing type's limit with the 25 % model margin (the contract's
  limits; the margin applied as FE value <= 0.75 x limit, as proposed on the Physics page). The
  tilt graded is the seat's against its shaft's line through its two seats' centres: the housing's
  share of the bearing's misalignment (LOP-6). The seat's own rotation, which a rigid turn of the
  whole housing would also show, is reported beside it;
- the worst seat displacement against the reference housing's bearing beds (52 µm in peak drive:
  the design to beat);
- in peak drive alone (`GRADED_CASES`, the engineer's one load case);
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
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))
REFERENCE = {"mass_kg": 7.732, "peak drive": 52.2, "peak reverse": 138.0}  # µm, the example's
FIRST_MODE_HZ = 500.0  # (LOP-29) the housing's first mode at least this (the engineer, 14 October 01:17)
# The load cases graded: peak drive alone (the engineer, 10 October 14:54, and again 11 October
# 00:46: "only one load case, drive... we won't have reverse in the checks"). FE may solve more.
GRADED_CASES = ("peak drive",)


def shaft_tilt_mrad(out: dict, shaft: str, seat: dict, shaft_lean=(0.0, 0.0)) -> float:
    """A seat's tilt against its shaft's axis at the bearing, in mrad: the bearing's misalignment.

    The seat's axis turns to (theta_y, -theta_x, 1). The shaft's chord through its two seats'
    centres leans by (du_x, du_y) / span, du the +z seat's displacement less the -z seat's; the
    shaft's own bending adds `shaft_lean` (dx/dz, dy/dz) against that chord at the bearing, from
    the load tool (the engineer, 9 October 09:57: the two add, no split by rule). A rigid turn of
    the whole housing moves the seat and the chord alike.
    """
    a, b = out["seats"][f"{shaft} -z"], out["seats"][f"{shaft} +z"]
    span = out["shafts"][shaft]["span_mm"]
    dx, dy = (b["u"][0] - a["u"][0]) / span, (b["u"][1] - a["u"][1]) / span
    tx, ty = seat["theta"][0], seat["theta"][1]
    return 1000 * math.hypot(ty - dx - shaft_lean[0], -tx - dy - shaft_lean[1])


def main() -> None:
    spec, _ = load_and_validate(CONTRACT)
    margin = value_in(spec.limits.model_margin, "1")
    limits = {t.bearing_type: 1000 * value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
    types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
    # The shafts' own leans at their bearings, per case, from the load tool's sections.
    leans = {s.shaft: s.lean_at_bearing for s in complete_chain(spec).sections}
    grades = []
    for path in sorted(OUT.glob("fe_*.json")):
        fe = json.loads(path.read_text(encoding="utf-8"))
        stem = fe["stem"]
        # An FE result older than its design's build judged a CAD since replaced (a failed run
        # leaves the last one behind: Avtec's, 20:43); it is not graded.
        build = OUT / f"{stem}.json"
        if build.exists() and build.stat().st_mtime > path.stat().st_mtime:
            print(f"{stem}: its FE result is older than its build; not graded")
            continue
        row = {"stem": stem, "mass_kg": fe["mass_kg"], "lines": {}}
        worst_ratio, worst_own, worst_housing = 0.0, 0.0, 0.0
        for case, out in fe["cases"].items():
            if case not in GRADED_CASES:
                continue
            for seat, v in out["seats"].items():
                shaft, side = seat.split()
                line = (1 - margin) * limits[types[(shaft, side)]]
                lean = leans[shaft].get(case, {}).get(side, (0.0, 0.0))
                worst_ratio = max(worst_ratio, shaft_tilt_mrad(out, shaft, v, lean) / line)
                worst_housing = max(worst_housing, shaft_tilt_mrad(out, shaft, v) / line)
                worst_own = max(worst_own, v["tilt_mrad"] / line)
            disp = max(1000 * v["displacement_mm"] for v in out["seats"].values())
            row["lines"][f"displacement, {case}"] = {
                "value_um": disp,
                "to_beat_um": REFERENCE[case],
                "pass": disp <= REFERENCE[case],
            }
        row["lines"]["misalignment (worst seat against its line)"] = {
            "ratio": worst_ratio,
            "pass": worst_ratio <= 1.0,
        }
        row["housing_only_ratio"] = worst_housing
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
        row["first_mode_hz"] = (fe.get("modes_hz") or [None])[0]
        row["lines"]["first mode"] = {"hz": row["first_mode_hz"], "at_least_hz": FIRST_MODE_HZ,
                                       "pass": row["first_mode_hz"] is not None and row["first_mode_hz"] >= FIRST_MODE_HZ}
        row["pass"] = all(v["pass"] for v in row["lines"].values())
        grades.append(row)
    (OUT / "grades.json").write_text(json.dumps(grades, indent=1), encoding="utf-8")
    print(
        f"{'design':22s} {'kg':>6s} {'drive µm':>9s} {'rev µm':>8s} {'own':>6s} {'housing':>7s} {'+shaft':>6s} {'mode1':>6s}  orders  verdict"
    )
    for g in grades:
        d = g["lines"]["displacement, peak drive"]["value_um"]
        r = g["lines"].get("displacement, peak reverse", {}).get("value_um", float("nan"))
        t = g["lines"]["misalignment (worst seat against its line)"]["ratio"]
        o = "clash" if g["lines"]["orders"]["clashes"] else "clear"
        print(
            f"{g['stem']:22s} {g['mass_kg']:6.2f} {d:9.0f} {r:8.0f} {g['seat_own_tilt_ratio']:6.2f} {g['housing_only_ratio']:7.2f} {t:6.2f} {g['first_mode_hz'] or 0:6.0f}  {o:6s}  {'PASS' if g['pass'] else 'fail'}"
        )


if __name__ == "__main__":
    main()
