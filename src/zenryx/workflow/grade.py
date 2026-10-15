"""Every graded line of the contract against a design's FE result (LOP-33; from the prototype's
`prototypes/first_loop/grade.py`, which now calls this).

For each FE result (`fe_<stem>.json`):
- each seat's tilt against its bearing type's limit less the model margin (the contract's limits).
  The tilt graded is the seat's against its shaft's line through its two seats' centres, the
  shaft's own lean at the bearing added (the load tool's): the bearing's misalignment. The seat's
  own rotation, which a rigid turn of the whole housing would also show, and the housing's share
  without the shaft's lean are reported beside it;
- the worst seat's displacement against the reference housing's worst bearing bed;
- in peak drive alone (`GRADED_CASES`, the engineer's one load case);
- the modes against the gear orders (FE's clashes);
- the first mode against `FIRST_MODE_HZ`;
- the mass against the reference housing's.
A design passes only if every line passes.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from zenryx.contract.model import HousingDesignSpec
from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in

# The design to beat: the reference housing's mass (kg) and worst bearing-bed displacement (µm) by
# case, from the contract's published references (`check_references` holds them to it).
REFERENCE = {"mass_kg": 7.732, "peak drive": 52.2, "peak reverse": 138.0}
FIRST_MODE_HZ = 500.0  # (LOP-29) the housing's first mode at least this (the engineer, 14 October)
# Peak drive alone (the engineer, 10 October 14:54 and 11 October 00:46). FE may solve more.
GRADED_CASES = ("peak drive",)
MISALIGNMENT = "misalignment (worst seat against its line)"


@dataclass(frozen=True)
class Lines:
    """What the contract fixes for the grade: each seat's tilt line (mrad) and each shaft's lean."""

    tilt_line: dict[tuple[str, str], float]
    leans: dict[str, dict]


def lines_of(spec: HousingDesignSpec) -> Lines:
    margin = value_in(spec.limits.model_margin, "1")
    limits = {t.bearing_type: 1000 * value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
    line = {
        (b.shaft, b.side.value): (1 - margin) * limits[b.type]
        for b in spec.requirement.shaft_layout.bearings
    }
    leans = {s.shaft: s.lean_at_bearing for s in complete_chain(spec).sections}
    return Lines(line, leans)


def shaft_tilt_mrad(out: dict, shaft: str, seat: dict, shaft_lean=(0.0, 0.0)) -> float:
    """A seat's tilt against its shaft's axis at the bearing, in mrad: the bearing's misalignment.

    The seat's axis turns to (theta_y, -theta_x, 1). The shaft's chord through its two seats'
    centres leans by (du_x, du_y) / span, du the +z seat's displacement less the -z seat's; the
    shaft's own bending adds `shaft_lean` (dx/dz, dy/dz) against that chord at the bearing (the
    engineer, 9 October 09:57: the two add). A rigid turn of the housing moves seat and chord alike.
    """
    a, b = out["seats"][f"{shaft} -z"], out["seats"][f"{shaft} +z"]
    span = out["shafts"][shaft]["span_mm"]
    dx, dy = (b["u"][0] - a["u"][0]) / span, (b["u"][1] - a["u"][1]) / span
    tx, ty = seat["theta"][0], seat["theta"][1]
    return 1000 * math.hypot(ty - dx - shaft_lean[0], -tx - dy - shaft_lean[1])


def grade(fe: dict, lines: Lines) -> dict:
    """One design's grade from its FE result."""
    row: dict = {"stem": fe["stem"], "mass_kg": fe["mass_kg"], "lines": {}}
    worst_ratio, worst_own, worst_housing = 0.0, 0.0, 0.0
    for case, out in fe["cases"].items():
        if case not in GRADED_CASES:
            continue
        for seat, v in out["seats"].items():
            shaft, side = seat.split()
            line = lines.tilt_line[(shaft, side)]
            lean = lines.leans[shaft].get(case, {}).get(side, (0.0, 0.0))
            worst_ratio = max(worst_ratio, shaft_tilt_mrad(out, shaft, v, lean) / line)
            worst_housing = max(worst_housing, shaft_tilt_mrad(out, shaft, v) / line)
            worst_own = max(worst_own, v["tilt_mrad"] / line)
        disp = max(1000 * v["displacement_mm"] for v in out["seats"].values())
        row["lines"][f"displacement, {case}"] = {
            "value_um": disp,
            "to_beat_um": REFERENCE[case],
            "pass": disp <= REFERENCE[case],
        }
    row["lines"][MISALIGNMENT] = {"ratio": worst_ratio, "pass": worst_ratio <= 1.0}
    row["housing_only_ratio"] = worst_housing
    row["seat_own_tilt_ratio"] = worst_own
    clashes = fe.get("order_clashes", [])
    row["lines"]["orders"] = {"clashes": clashes, "pass": not clashes}
    row["lines"]["mass"] = {
        "kg": fe["mass_kg"],
        "to_beat_kg": REFERENCE["mass_kg"],
        "pass": fe["mass_kg"] <= REFERENCE["mass_kg"],
    }
    row["first_mode_hz"] = (fe.get("modes_hz") or [None])[0]
    first = row["first_mode_hz"]
    row["lines"]["first mode"] = {
        "hz": first,
        "at_least_hz": FIRST_MODE_HZ,
        "pass": first is not None and first >= FIRST_MODE_HZ,
    }
    row["pass"] = all(v["pass"] for v in row["lines"].values())
    return row


def grade_all(out: Path, contract: Path) -> tuple[list[dict], list[str]]:
    """Every FE result in `out` graded, written to `out/grades.json`; and the stems not graded.

    An FE result older than its design's build judged a drawing since replaced (a failed run
    leaves the last one behind), so it is not graded.
    """
    spec, refusals = load_and_validate(contract)
    if spec is None:
        raise ValueError(f"{contract.name} does not load: {refusals}")
    lines = lines_of(spec)
    grades, stale = [], []
    for path in sorted(out.glob("fe_*.json")):
        fe = json.loads(path.read_text(encoding="utf-8"))
        build = out / f"{fe['stem']}.json"
        if build.exists() and build.stat().st_mtime > path.stat().st_mtime:
            stale.append(fe["stem"])
            continue
        grades.append(grade(fe, lines))
    (out / "grades.json").write_text(json.dumps(grades, indent=1), encoding="utf-8")
    return grades, stale


def table(grades: list[dict], stale: list[str] = ()) -> str:
    """The grades as a table, one design a row (and the FE results not graded)."""
    rows = [f"{s}: its FE result is older than its build; not graded" for s in stale]
    rows.append(
        f"{'design':22s} {'kg':>6s} {'drive µm':>9s} {'rev µm':>8s} {'own':>6s} {'housing':>7s} "
        f"{'+shaft':>6s} {'mode1':>6s}  orders  verdict"
    )
    for g in grades:
        d = g["lines"]["displacement, peak drive"]["value_um"]
        r = g["lines"].get("displacement, peak reverse", {}).get("value_um", float("nan"))
        t = g["lines"][MISALIGNMENT]["ratio"]
        o = "clash" if g["lines"]["orders"]["clashes"] else "clear"
        rows.append(
            f"{g['stem']:22s} {g['mass_kg']:6.2f} {d:9.0f} {r:8.0f} "
            f"{g['seat_own_tilt_ratio']:6.2f} {g['housing_only_ratio']:7.2f} {t:6.2f} "
            f"{g['first_mode_hz'] or 0:6.0f}  {o:6s}  {'PASS' if g['pass'] else 'fail'}"
        )
    return "\n".join(rows) + "\n"


def check_references(spec: HousingDesignSpec) -> list[str]:
    """Where `REFERENCE` disagrees with the contract's published references (empty: it agrees)."""
    found: dict[str, float] = {}
    for r in spec.references:
        if r.quantity == "housing mass":
            found["mass_kg"] = float(r.value.split()[0])
        if r.quantity.startswith("bearing-bed displacement"):
            for part in r.value.replace(" mm", "").split(";"):
                name, values = part.strip().split(" ", 1)
                case = {"forward": "peak drive", "reverse": "peak reverse"}[name]
                found[case] = 1000 * max(float(v) for v in values.split(","))
    return [
        f"{k}: {REFERENCE[k]} here, {found.get(k)} in the contract"
        for k in REFERENCE
        if found.get(k) is None or not math.isclose(found[k], REFERENCE[k], rel_tol=1e-9)
    ]
