"""Involute gear geometry: what a shifted helical pair runs with.

For a helical pair with teeth z1, z2, normal module mn, normal pressure angle alpha_n, helix angle
beta and profile-shift coefficients x1, x2 (the standard involute relations, as in DIN 3960 and
ISO 21771):

    alpha_t       = atan(tan(alpha_n) / cos(beta))                transverse pressure angle
    inv(alpha_w)  = inv(alpha_t) + 2 (x1 + x2) tan(alpha_n) / (z1 + z2)
                                                                  working pressure angle
    d             = z mn / cos(beta)                              reference diameter
    db            = d cos(alpha_t)                                base diameter
    dw            = db / cos(alpha_w)                             working pitch diameter
    a             = (dw1 + dw2) / 2                               working centre distance

The validator checks a contract's given centre distance against a; the contract page shows the
rest; the load tool (GBX-1) takes the forces at the working pitch circle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def inv(alpha: float) -> float:
    """The involute function, tan(alpha) - alpha, in radians."""
    return math.tan(alpha) - alpha


def inv_inverse(value: float, guess: float = 0.35) -> float:
    """The angle whose involute is value (Newton's method; d inv/d alpha = tan^2(alpha))."""
    if value < 0:
        raise ValueError("the involute of a pressure angle is never negative")
    alpha = guess
    for _ in range(60):
        step = (inv(alpha) - value) / (math.tan(alpha) ** 2)
        alpha -= step
        alpha = min(max(alpha, 1e-6), math.pi / 2 - 1e-6)
        if abs(step) < 1e-15:
            return alpha
    raise ArithmeticError("the inverse involute did not converge")


@dataclass(frozen=True)
class MeshGeometry:
    """A helical pair's geometry: angles in radians, lengths in the module's unit, each pair of
    diameters pinion first."""

    transverse_pressure_angle: float
    working_pressure_angle: float
    reference_diameters: tuple[float, float]
    base_diameters: tuple[float, float]
    working_pitch_diameters: tuple[float, float]
    working_centre_distance: float


def mesh_geometry(
    z1: int,
    z2: int,
    normal_module: float,
    pressure_angle: float,
    helix_angle: float,
    x1: float,
    x2: float,
) -> MeshGeometry:
    """The pressure angles and diameters a pair of involute helical gears runs with."""
    alpha_t = math.atan(math.tan(pressure_angle) / math.cos(helix_angle))
    inv_w = inv(alpha_t) + 2.0 * (x1 + x2) * math.tan(pressure_angle) / (z1 + z2)
    alpha_w = inv_inverse(inv_w, guess=alpha_t)
    d1, d2 = (z * normal_module / math.cos(helix_angle) for z in (z1, z2))
    db1, db2 = d1 * math.cos(alpha_t), d2 * math.cos(alpha_t)
    dw1, dw2 = db1 / math.cos(alpha_w), db2 / math.cos(alpha_w)
    return MeshGeometry(
        transverse_pressure_angle=alpha_t,
        working_pressure_angle=alpha_w,
        reference_diameters=(d1, d2),
        base_diameters=(db1, db2),
        working_pitch_diameters=(dw1, dw2),
        working_centre_distance=(dw1 + dw2) / 2.0,
    )


def working_centre_distance(
    z1: int,
    z2: int,
    normal_module: float,
    pressure_angle: float,
    helix_angle: float,
    x1: float,
    x2: float,
) -> float:
    """The centre distance a pair of involute helical gears runs at, in the module's unit."""
    geometry = mesh_geometry(z1, z2, normal_module, pressure_angle, helix_angle, x1, x2)
    return geometry.working_centre_distance
