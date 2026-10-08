"""Bearing selection (GBX-3, the chain's step 8).

**The rating life** (the catalogue method; Shigley Ch. 11; ISO 281 is the standard, paid, so only
its public formula is used): L10 = (C / P)^p million revolutions, p = 3 for ball bearings and
10/3 for roller bearings, in hours L10h = L10 · 10^6 / (60 n).

**The equivalent load** P = X·Fr + Y·Fa, as the catalogue gives it:
- a deep-groove ball bearing: P = Fr while Fa/Fr <= e, else 0.56·Fr + Y·Fa, with e and Y read off
  the ratio Fa/C0 (Shigley Table 11-1);
- a tapered roller bearing: P = Fr while Fa/Fr <= e, else 0.4·Fr + Y·Fa, with the bearing's own
  e and Y;
- a cylindrical roller bearing (NU, floating): P = Fr.

**The choice** (the engineer, 9 October 00:50: the life of 944 h at the drive case; bearings from a
maker's public catalogue, cited): of the arrangement's type, the bore at least what the shaft needs,
the life at least the contract's at the drive case and the rated speed; of those, the smallest
outside diameter, then the narrowest.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

CATALOGUE = Path(__file__).parent / "data" / "bearings.json"

# Shigley Table 11-1 (from the makers' tables): Fa/C0 against e and the Y of 0.56·Fr + Y·Fa.
BALL_E_Y = (
    (0.014, 0.19, 2.30),
    (0.021, 0.21, 2.15),
    (0.028, 0.22, 1.99),
    (0.042, 0.24, 1.85),
    (0.056, 0.26, 1.71),
    (0.070, 0.27, 1.63),
    (0.084, 0.28, 1.55),
    (0.110, 0.30, 1.45),
    (0.17, 0.34, 1.31),
    (0.28, 0.38, 1.15),
    (0.42, 0.42, 1.04),
    (0.56, 0.44, 1.00),
)


@dataclass(frozen=True)
class Bearing:
    """A catalogue bearing (mm, N). For a tapered roller bearing, width is its total width T and
    a its load centre's distance as the catalogue measures it."""

    designation: str
    type: str
    d: float
    D: float
    width: float
    C: float
    C0: float
    e: float | None
    Y: float | None
    a: float | None
    checked: bool
    source: str


@cache
def catalogue() -> tuple[Bearing, ...]:
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    rows = []
    for r in data["rows"]:
        rows.append(
            Bearing(
                designation=r["designation"],
                type=r["type"],
                d=float(r["d"]),
                D=float(r["D"]),
                width=float(r["width"]),
                C=1000.0 * float(r["C"]),
                C0=1000.0 * float(r["C0"]),
                e=r.get("e"),
                Y=r.get("Y"),
                a=r.get("a"),
                checked=bool(r.get("checked")),
                source=r.get("source", data["source"]),
            )
        )
    return tuple(rows)


def _ball_e_y(ratio: float) -> tuple[float, float]:
    """e and Y for a deep-groove ball bearing at Fa/C0, interpolated in Shigley Table 11-1."""
    table = BALL_E_Y
    if ratio <= table[0][0]:
        return table[0][1], table[0][2]
    for (r0, e0, y0), (r1, e1, y1) in zip(table, table[1:], strict=False):
        if ratio <= r1:
            t = (ratio - r0) / (r1 - r0)
            return e0 + t * (e1 - e0), y0 + t * (y1 - y0)
    return table[-1][1], table[-1][2]


def equivalent_load(bearing: Bearing, fr: float, fa: float) -> float:
    """P (N) from the radial and axial loads the bearing carries (N)."""
    fa = abs(fa)
    if bearing.type == "cylindrical_roller":
        return fr
    if bearing.type == "deep_groove_ball":
        e, y = _ball_e_y(fa / bearing.C0)
        return fr if fr > 0 and fa / fr <= e else 0.56 * fr + y * fa
    if bearing.type == "tapered_roller":
        if bearing.e is None or bearing.Y is None:
            raise ValueError(f"{bearing.designation}: a tapered bearing needs its e and Y")
        return fr if fr > 0 and fa / fr <= bearing.e else 0.4 * fr + bearing.Y * fa
    raise ValueError(f"no load rule for a {bearing.type} bearing")


def life_hours(bearing: Bearing, load: float, rpm: float) -> float:
    """The basic rating life L10h (h) at an equivalent load (N) and a speed (rev/min)."""
    if load <= 0:
        return float("inf")
    p = 3.0 if bearing.type == "deep_groove_ball" else 10.0 / 3.0
    return (bearing.C / load) ** p * 1e6 / (60.0 * rpm)


@dataclass(frozen=True)
class Choice:
    """A seat's selected bearing, with the life it gives and what it was chosen against."""

    bearing: Bearing
    load: float
    life: float
    bore_needed: float


def select(kind: str, bore_needed: float, fr: float, fa: float, rpm: float, hours: float) -> Choice:
    """The smallest bearing of a type whose bore fits the shaft and whose life at the drive case
    reaches the contract's. Refused (ValueError) where the catalogue holds none."""
    fitting = []
    for b in catalogue():
        if b.type != kind or b.d < bore_needed - 1e-9:
            continue
        load = equivalent_load(b, fr, fa)
        life = life_hours(b, load, rpm)
        if life >= hours:
            fitting.append(Choice(b, load, life, bore_needed))
    if not fitting:
        raise ValueError(
            f"no {kind} bearing in the catalogue with a bore of at least {bore_needed:.1f} mm "
            f"lasts {hours:.0f} h at Fr {fr:.0f} N, Fa {abs(fa):.0f} N and {rpm:.0f} rpm"
        )
    return min(fitting, key=lambda c: (c.bearing.D, c.bearing.width, c.bearing.d))
