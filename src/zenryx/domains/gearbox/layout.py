"""The layout along each shaft, and the clearances it leaves (GBX-2, the chain's step 5).

The layout is gap-driven (the engineer, 9 October 00:06): the gaps are the inputs, and the
positions follow by a stack of widths and gaps from a datum (Shigley §18-4 and Fig. 18-2;
Maciejczyk & Zdziennicki Ch. 3; docs/research/2026-10-08-bearing-positions.md).

- **The datum** is the first stage's mesh plane, z = 0. A mesh's two gears share their plane (the
  middle of their faces). On the shaft two stages share, the second stage's gear sits the
  gear-to-gear gap beyond the first, on the side `first_stage_side` leaves.
- **A plain shaft** stacks outwards from its gears: the bearing-to-gear gap, the bearing, then the
  space behind the bearing (the wall of a closed bore, or a seal and its seat where the shaft
  leaves the housing).
- **A shaft whose gear rides on a carrier** (a differential case) takes its bearings from the
  carrier: the gear sits the bearing-to-gear gap beside the bearing at one end, and the other
  bearing is the carrier's spacing away. The carrier's body fills the room between them.
- **The clearances are calculated, never assumed** (the engineer, 01:06): every two parts on
  different shafts whose circles overlap seen along the shafts must clear each other along them by
  the least axial clearance. A pair that does not is reported with its shortfall.

The bearings' widths and outside diameters come from their selection (GBX-3), so the layout goes
round with it: at first they are a guess.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from zenryx.contract.involute import mesh_geometry
from zenryx.contract.model import HousingDesignSpec
from zenryx.domains.gearbox.forces import Point, shaft_axes, stage_data, value_in

TOOL = "zenryx.domains.gearbox.layout"
VERSION = "0.1.0"

SIGN = {"-z": -1.0, "+z": 1.0}


@dataclass(frozen=True)
class Part:
    """One part on a shaft, as a cylinder along it (mm): a gear (its tip Ø), a bearing (its
    outside Ø) or a carrier's body (its Ø)."""

    name: str
    kind: str
    shaft: str
    diameter: float
    z_min: float
    z_max: float

    @property
    def centre(self) -> float:
        return (self.z_min + self.z_max) / 2

    @property
    def width(self) -> float:
        return self.z_max - self.z_min


@dataclass(frozen=True)
class ShaftStack:
    """A shaft's parts along z, and the housing's inner faces behind its two bearings (mm)."""

    shaft: str
    axis: Point
    parts: tuple[Part, ...]
    ends: tuple[float, float]

    def bearing(self, side: str) -> Part:
        return next(p for p in self.parts if p.kind == "bearing" and p.name.endswith(side))


@dataclass(frozen=True)
class Clearance:
    """Two parts on different shafts that overlap seen along the shafts (by `overlap` mm), and the
    gap between them along the shafts against the least it must be."""

    a: str
    b: str
    overlap: float
    gap: float
    least: float

    @property
    def ok(self) -> bool:
        return self.gap >= self.least - 1e-9


@dataclass(frozen=True)
class Layout:
    planes: tuple[tuple[str, float], ...]
    shafts: tuple[ShaftStack, ...]
    clearances: tuple[Clearance, ...]

    def stack(self, shaft: str) -> ShaftStack:
        return next(s for s in self.shafts if s.shaft == shaft)

    @property
    def breaches(self) -> tuple[Clearance, ...]:
        return tuple(c for c in self.clearances if not c.ok)


def _mm(entry, default: float | None = None) -> float:
    if entry is None:
        if default is None:
            raise ValueError("a length the layout needs is missing")
        return default
    return value_in(entry, "mm")


def place(
    spec: HousingDesignSpec,
    bearings: dict[tuple[str, str], tuple[float, float]],
) -> Layout:
    """The layout of a contract's gear train. `bearings` gives each bearing's (width, outside Ø),
    keyed by (shaft, side), as the selection (or a first guess) has them."""
    req = spec.requirement
    gaps = req.shaft_layout
    if gaps is None:
        raise ValueError("the layout needs the contract's shaft_layout")
    stages = req.stages
    data = [stage_data(s) for s in stages]
    geometry = [
        mesh_geometry(
            d["z"][0],
            d["z"][1],
            d["normal_module"],
            d["pressure_angle"],
            d["helix_angle"],
            *d["shifts"],
        )
        for d in data
    ]
    widths = {}
    for s in stages:
        widths[(s.name, "pinion")] = value_in(s.face_width_pinion, "mm")
        widths[(s.name, "gear")] = value_in(s.face_width_gear, "mm")
    g_bg = _mm(gaps.bearing_to_gear)
    g_gg = _mm(gaps.gear_to_gear, g_bg)
    behind = _mm(gaps.behind_bearing)
    behind_sealed = _mm(gaps.behind_bearing_sealed, behind)
    sealed = {(e.shaft, e.side.value) for e in gaps.sealed_ends}
    least = _mm(gaps.min_axial_clearance, 0.0)

    # The mesh planes: the first stage at the datum, the second beside it on the shared shaft.
    planes = {stages[0].name: 0.0}
    if len(stages) == 2:
        first_side = gaps.first_stage_side.value if gaps.first_stage_side is not None else "-z"
        step = widths[(stages[0].name, "gear")] / 2 + g_gg + widths[(stages[1].name, "pinion")] / 2
        planes[stages[1].name] = -SIGN[first_side] * step
    elif len(stages) > 2:
        raise NotImplementedError("trains of more than two stages need more layout inputs")

    axes = shaft_axes(spec)
    gears: dict[str, list[Part]] = {}
    for s, g in zip(stages, geometry, strict=True):
        for member, shaft, tip in (
            ("pinion", s.pinion_shaft, g.tip_diameters[0]),
            ("gear", s.gear_shaft, g.tip_diameters[1]),
        ):
            b = widths[(s.name, member)]
            z = planes[s.name]
            gears.setdefault(shaft, []).append(
                Part(f"{s.name} {member}", "gear", shaft, tip, z - b / 2, z + b / 2)
            )

    carriers = {c.shaft: c for c in gaps.carriers}
    stacks = []
    for shaft, on in gears.items():
        on = sorted(on, key=lambda p: p.z_min)
        parts = list(on)

        def bearing(side: str, centre: float, shaft: str = shaft) -> Part:
            if (shaft, side) not in bearings:
                raise ValueError(f"no width is known for the {side} bearing of {shaft}")
            width, outside = bearings[(shaft, side)]
            return Part(
                f"{shaft} bearing {side}",
                "bearing",
                shaft,
                outside,
                centre - width / 2,
                centre + width / 2,
            )

        if shaft in carriers:
            carrier = carriers[shaft]
            if len(on) != 1:
                raise ValueError(f"a carrier on {shaft} holds one gear, not {len(on)}")
            gear = on[0]
            beside = carrier.gear_beside.value
            s = SIGN[beside]
            other = "-z" if beside == "+z" else "+z"
            w_beside = bearings[(shaft, beside)][0]
            edge = gear.z_max if s > 0 else gear.z_min
            near = bearing(beside, edge + s * (g_bg + w_beside / 2))
            far = bearing(other, near.centre - s * _mm(carrier.bearing_spacing))
            body_from = far.z_max if s > 0 else far.z_min
            body_to = gear.z_min if s > 0 else gear.z_max
            if (body_to - body_from) * s <= 0:
                raise ValueError(
                    f"the {carrier.name} on {shaft}: its bearing spacing leaves no room for its "
                    "body beside the gear"
                )
            parts.append(
                Part(
                    carrier.name,
                    "carrier",
                    shaft,
                    _mm(carrier.diameter),
                    min(body_from, body_to),
                    max(body_from, body_to),
                )
            )
            parts += [near, far]
        else:
            low = bearing("-z", on[0].z_min - g_bg - bearings.get((shaft, "-z"), (0, 0))[0] / 2)
            high = bearing("+z", on[-1].z_max + g_bg + bearings.get((shaft, "+z"), (0, 0))[0] / 2)
            parts += [low, high]
        low_b = next(p for p in parts if p.name == f"{shaft} bearing -z")
        high_b = next(p for p in parts if p.name == f"{shaft} bearing +z")
        ends = (
            low_b.z_min - (behind_sealed if (shaft, "-z") in sealed else behind),
            high_b.z_max + (behind_sealed if (shaft, "+z") in sealed else behind),
        )
        stacks.append(
            ShaftStack(shaft, axes[shaft], tuple(sorted(parts, key=lambda p: p.z_min)), ends)
        )

    meshing = {(f"{s.name} pinion", f"{s.name} gear") for s in stages}
    found = []
    every = [(stack, p) for stack in stacks for p in stack.parts]
    for i, (sa, a) in enumerate(every):
        for sb, b in every[i + 1 :]:
            if sa.shaft == sb.shaft or (a.name, b.name) in meshing or (b.name, a.name) in meshing:
                continue
            overlap = a.diameter / 2 + b.diameter / 2 - math.dist(sa.axis, sb.axis)
            if overlap <= 0:
                continue
            gap = max(b.z_min - a.z_max, a.z_min - b.z_max)
            found.append(Clearance(a.name, b.name, overlap, gap, least))
    return Layout(tuple(planes.items()), tuple(stacks), tuple(found))
