"""Units: every quantity in a contract carries a unit from a fixed list (spec §5).

A value is kept as it was written (366 N·m stays 366 N·m), and converted on read to the canonical
set the tools use: mm, N, N*mm, s, MPa, t/mm3, rad, rad/s, Hz, W, kg and the dimensionless 1.
Common spellings of the same unit (Nm, N*m, um, kg/m3) are accepted through one alias table;
anything else is refused with the list of allowed units.
"""

from __future__ import annotations

import math
import re

from pydantic import BaseModel, ConfigDict, field_validator

# unit as written -> (canonical unit, factor to the canonical unit)
UNITS: dict[str, tuple[str, float]] = {
    "mm": ("mm", 1.0),
    "m": ("mm", 1000.0),
    "µm": ("mm", 1e-3),
    "N": ("N", 1.0),
    "kN": ("N", 1e3),
    "N·m": ("N*mm", 1e3),
    "N·mm": ("N*mm", 1.0),
    "rpm": ("rad/s", 2.0 * math.pi / 60.0),
    "rad/s": ("rad/s", 1.0),
    "MPa": ("MPa", 1.0),
    "GPa": ("MPa", 1e3),
    "kg/m³": ("t/mm3", 1e-12),
    "g/cm³": ("t/mm3", 1e-9),
    "kg": ("kg", 1.0),
    "g": ("kg", 1e-3),
    "rad": ("rad", 1.0),
    "mrad": ("rad", 1e-3),
    "deg": ("rad", math.pi / 180.0),
    "s": ("s", 1.0),
    "h": ("s", 3600.0),
    "Hz": ("Hz", 1.0),
    "W": ("W", 1.0),
    "kW": ("W", 1e3),
    "1/K": ("1/K", 1.0),
    "µm/(m·K)": ("1/K", 1e-6),
    "%": ("1", 0.01),
    "1": ("1", 1.0),
}

# other spellings -> the unit as listed above
ALIASES: dict[str, str] = {
    "Nm": "N·m",
    "N*m": "N·m",
    "N.m": "N·m",
    "N m": "N·m",
    "N-m": "N·m",
    "Nmm": "N·mm",
    "N*mm": "N·mm",
    "N.mm": "N·mm",
    "N mm": "N·mm",
    "um": "µm",
    "micron": "µm",
    "kg/m3": "kg/m³",
    "kg/m^3": "kg/m³",
    "g/cm3": "g/cm³",
    "g/cm^3": "g/cm³",
    "1/min": "rpm",
    "min^-1": "rpm",
    "rev/min": "rpm",
    "°": "deg",
    "degree": "deg",
    "degrees": "deg",
    "percent": "%",
    "1/°C": "1/K",
    "µm/(m·°C)": "µm/(m·K)",
    "um/(m.K)": "µm/(m·K)",
    "um/(m*K)": "µm/(m·K)",
    "µm/m/K": "µm/(m·K)",
    "um/m/K": "µm/(m·K)",
}

# characters that look alike: the micro sign and the Greek mu; the middle dot and the dot operator
_LOOKALIKES = str.maketrans({"μ": "µ", "⋅": "·", "∙": "·"})


class UnitError(ValueError):
    """A value has no unit, or a unit outside the list."""


def _allowed() -> str:
    return ", ".join(UNITS)


def normalise_unit(unit: str) -> str:
    """The unit as listed in UNITS, from any accepted spelling; UnitError otherwise."""
    text = " ".join(unit.strip().translate(_LOOKALIKES).split())
    if not text:
        raise UnitError(f"a value needs a unit; allowed units: {_allowed()}")
    if text in UNITS:
        return text
    if text in ALIASES:
        return ALIASES[text]
    raise UnitError(f"unit {unit!r} is not in the list; allowed units: {_allowed()}")


_NUMBER = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")


class Quantity(BaseModel):
    """A scalar with its unit, kept as written."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float
    unit: str

    @field_validator("unit")
    @classmethod
    def _known_unit(cls, unit: str) -> str:
        return normalise_unit(unit)

    @field_validator("value")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("a quantity must be a finite number")
        return value

    @classmethod
    def parse(cls, text: str) -> Quantity:
        """'366 N·m' -> Quantity(366, 'N·m'). A bare number is refused: it needs a unit."""
        match = _NUMBER.match(text)
        if match is None:
            raise UnitError(f"{text!r} is not a number followed by a unit")
        number, unit = match.groups()
        if not unit:
            raise UnitError(f"{text!r}: a value needs a unit; allowed units: {_allowed()}")
        return cls(value=float(number), unit=normalise_unit(unit))

    def to_canonical(self) -> tuple[float, str]:
        canonical, factor = UNITS[self.unit]
        return self.value * factor, canonical


class Vector(BaseModel):
    """Three components with one unit, in the contract's frame."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    values: tuple[float, float, float]
    unit: str

    @field_validator("unit")
    @classmethod
    def _known_unit(cls, unit: str) -> str:
        return normalise_unit(unit)

    @field_validator("values")
    @classmethod
    def _finite(cls, values: tuple[float, float, float]) -> tuple[float, float, float]:
        if not all(math.isfinite(v) for v in values):
            raise ValueError("a vector's components must be finite numbers")
        return values

    def to_canonical(self) -> tuple[tuple[float, float, float], str]:
        canonical, factor = UNITS[self.unit]
        x, y, z = (v * factor for v in self.values)
        return (x, y, z), canonical
