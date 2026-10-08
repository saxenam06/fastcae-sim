"""Involute gear geometry the contract's validator needs: the working centre distance.

For a helical pair with normal module mn, normal pressure angle alpha_n, helix angle beta and
profile-shift coefficients x1, x2 (the standard involute relations, as in DIN 3960 and ISO 21771):

    alpha_t       = atan(tan(alpha_n) / cos(beta))                transverse pressure angle
    inv(alpha_w)  = inv(alpha_t) + 2 (x1 + x2) tan(alpha_n) / (z1 + z2)
    a             = mn (z1 + z2) / (2 cos(beta)) * cos(alpha_t) / cos(alpha_w)
"""

from __future__ import annotations

import math


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
    alpha_t = math.atan(math.tan(pressure_angle) / math.cos(helix_angle))
    inv_w = inv(alpha_t) + 2.0 * (x1 + x2) * math.tan(pressure_angle) / (z1 + z2)
    alpha_w = inv_inverse(inv_w, guess=alpha_t)
    reference = normal_module * (z1 + z2) / (2.0 * math.cos(helix_angle))
    return reference * math.cos(alpha_t) / math.cos(alpha_w)
