"""What a gear train gives before any shaft is laid out: its ratio, its shafts' speeds, its mesh
frequencies, and the angle its three axes make in the plane.

    ratio            the product of the stages' tooth ratios (gear teeth over pinion teeth)
    shaft speeds     each shaft's speed from the input's, stage by stage
    mesh frequency   a mesh's tooth-passing frequency: teeth x the speed of their shaft / 60
    stage angle      the angle at the intermediate shaft between its centre lines to the input and
                     to the output, from the two centre distances and the input-output offset: the
                     law of cosines on the triangle the three axes make
    axis positions   the three shafts' centres in the plane: the intermediate at the origin, the
                     input along -x, the output at the stage angle
    end-view overlap how far two round parts cover the same ground seen along the shafts: their
                     radii's sum less the distance between their centres. Parts on different
                     shafts that overlap must clear each other along the shafts instead

The offset is the packaging input: the vehicle fixes it, and the angle follows from it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

# The same slack the validator allows an offset at the triangle's limits (consistency.offset).
_REACH = 1e-6


def ratio(teeth: Sequence[tuple[int, int]]) -> float:
    """The train's ratio from each stage's (pinion teeth, gear teeth)."""
    return math.prod(z_gear / z_pinion for z_pinion, z_gear in teeth)


def shaft_speeds(input_rpm: float, teeth: Sequence[tuple[int, int]]) -> list[float]:
    """The speed of the input and of each shaft after it, in rev/min."""
    speeds = [input_rpm]
    for z_pinion, z_gear in teeth:
        speeds.append(speeds[-1] * z_pinion / z_gear)
    return speeds


def mesh_frequency(teeth: int, rpm: float) -> float:
    """A mesh's tooth-passing frequency in Hz, from one gear's teeth and its own shaft's speed."""
    return teeth * rpm / 60.0


def stage_angle(a1: float, a2: float, offset: float) -> float:
    """The angle at the intermediate shaft, in degrees, for centre distances a1 and a2 and an
    input-output offset. An offset the two centre distances cannot reach is refused."""
    if not abs(a1 - a2) - _REACH <= offset <= a1 + a2 + _REACH:
        raise ValueError(
            f"centre distances of {a1:g} and {a2:g} mm cannot reach an offset of {offset:g} mm "
            f"(it must lie between {abs(a1 - a2):g} and {a1 + a2:g})"
        )
    cosine = (a1 * a1 + a2 * a2 - offset * offset) / (2.0 * a1 * a2)
    return math.degrees(math.acos(min(1.0, max(-1.0, cosine))))


Point = tuple[float, float]


def axis_positions(a1: float, a2: float, offset: float) -> tuple[Point, Point, Point]:
    """The input's, the intermediate's and the output's centres in the plane, in mm: the
    intermediate at the origin, the input along -x, the output where the offset puts it."""
    angle = math.radians(stage_angle(a1, a2, offset))
    output = (a2 * math.cos(math.pi - angle), a2 * math.sin(math.pi - angle))
    return (-a1, 0.0), (0.0, 0.0), output


def end_view_overlap(r1: float, c1: Point, r2: float, c2: Point) -> float:
    """How far two round parts of radii r1 and r2, centred at c1 and c2, cover the same ground
    seen along the shafts; positive means they overlap, negative is the room between them."""
    return r1 + r2 - math.dist(c1, c2)
