"""Every graded line of the contract against a design's FE result (LOP-33; from the prototype's
`prototypes/first_loop/grade.py`, which now calls this).

For each FE result (`fe_<stem>.json`), in peak drive alone (the engineer's one load case):
- each seat's misalignment against its bearing type's limit less the model margin (the contract's
  limits): the seat's tilt against its shaft's line through its two seats' centres, the shaft's own
  lean at the bearing added (the load tool's);
- the worst seat's displacement against the reference housing's worst bearing bed;
- the modes against the gear orders (FE's clashes), and the first mode against `FIRST_MODE_HZ`;
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

# The design to beat: the reference housing's mass (kg) and worst bearing-bed displacement in peak
# drive (µm), from the contract's published references (`check_references` holds them to it).
REFERENCE = {"mass_kg": 7.732, "peak drive": 52.2}
FIRST_MODE_HZ = 500.0  # (LOP-29) the housing's first mode at least this (the engineer, 14 October)
CASE = "peak drive"  # the one load case graded (the engineer, 10 and 11 October)
GRADED_CASES = (CASE,)
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
    out = fe["cases"][CASE]
    worst = 0.0
    for seat, v in out["seats"].items():
        shaft, side = seat.split()
        lean = lines.leans[shaft].get(CASE, {}).get(side, (0.0, 0.0))
        worst = max(worst, shaft_tilt_mrad(out, shaft, v, lean) / lines.tilt_line[(shaft, side)])
    disp = max(1000 * v["displacement_mm"] for v in out["seats"].values())
    clashes = fe.get("order_clashes", [])
    first = (fe.get("modes_hz") or [None])[0]
    row = {
        "stem": fe["stem"],
        "mass_kg": fe["mass_kg"],
        "lines": {
            f"displacement, {CASE}": {
                "value_um": disp,
                "to_beat_um": REFERENCE[CASE],
                "pass": disp <= REFERENCE[CASE],
            },
            MISALIGNMENT: {"ratio": worst, "pass": worst <= 1.0},
            "orders": {"clashes": clashes, "pass": not clashes},
            "mass": {
                "kg": fe["mass_kg"],
                "to_beat_kg": REFERENCE["mass_kg"],
                "pass": fe["mass_kg"] <= REFERENCE["mass_kg"],
            },
            "first mode": {
                "hz": first,
                "at_least_hz": FIRST_MODE_HZ,
                "pass": first is not None and first >= FIRST_MODE_HZ,
            },
        },
        "first_mode_hz": first,
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
        f"{'design':22s} {'kg':>6s} {'drive µm':>9s} {'tilt':>6s} {'mode1':>6s}  orders  verdict"
    )
    for g in grades:
        d = g["lines"][f"displacement, {CASE}"]["value_um"]
        t = g["lines"][MISALIGNMENT]["ratio"]
        o = "clash" if g["lines"]["orders"]["clashes"] else "clear"
        rows.append(
            f"{g['stem']:22s} {g['mass_kg']:6.2f} {d:9.0f} {t:6.2f} "
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
            forward = r.value.replace(" mm", "").split(";")[0].strip()
            assert forward.startswith("forward ")
            found[CASE] = 1000 * max(float(v) for v in forward.split(" ", 1)[1].split(","))
    return [
        f"{k}: {REFERENCE[k]} here, {found.get(k)} in the contract"
        for k in REFERENCE
        if found.get(k) is None or not math.isclose(found[k], REFERENCE[k], rel_tol=1e-9)
    ]
