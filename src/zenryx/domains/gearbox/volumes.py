"""The volumes a completed gear train fixes, and the design space they leave for the housing
(PLT-8, the contract's result; LOP-1 builds the housing in it).

- **The parts**, each a cylinder along its shaft: each gear (its tip Ø over its face width), each
  shaft (its least bore, through its housing faces and out where it leaves), each bearing (a ring,
  its outside and bore Ø over its width), the differential's case.
- **The packaging space:** the convex hull, seen along the shafts, of every part's circle grown by
  the installation space's clearance (A3), over the housing's length grown by the same.
- **What the housing keeps clear of:** each gear and the carrier grown by the least radial
  clearance to the wall (A19) and the least axial clearance (A18); each shaft; each bearing's own
  room (its seat is housing).
- **The design space:** the packaging space less what the housing keeps clear of: where housing
  material may go.
"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from zenryx.contract.model import HousingDesignSpec
from zenryx.domains.gearbox.chain import Chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.geometry.solids import cylinder, fuse, hull_of_circles, prism, ring

TOOL = "zenryx.domains.gearbox.volumes"
VERSION = "0.1.0"

OUTSIDE = 30.0  # how far a shaft is drawn beyond a housing face it leaves through, mm


@dataclass(frozen=True)
class Volume:
    name: str
    role: str
    solid: cq.Shape


@dataclass(frozen=True)
class Space:
    """The parts, the packaging space, what the housing keeps clear of, and the design space."""

    parts: list[Volume]
    packaging: Volume
    keep_out: Volume
    design: Volume
    outline: list[tuple[float, float]]
    z_range: tuple[float, float]


def _mm(entry, default: float = 0.0) -> float:
    return default if entry is None else value_in(entry, "mm")


def volumes(spec: HousingDesignSpec, chain: Chain) -> Space:
    req = spec.requirement
    gaps = req.shaft_layout
    radial = _mm(gaps.min_radial_clearance)
    axial = _mm(gaps.min_axial_clearance)
    space = req.installation_space
    clearance = _mm(space.clearance) if space.kind == "layout_envelope" else 0.0
    sealed = {(e.shaft, e.side.value) for e in gaps.sealed_ends}
    sections = {s.shaft: s for s in chain.sections}

    parts: list[Volume] = []
    keep: list[cq.Shape] = []
    circles: list[tuple[float, float, float]] = []
    for stack in chain.layout.shafts:
        (x, y), shaft = stack.axis, stack.shaft
        bores = []
        for p in stack.parts:
            if p.kind == "gear":
                parts.append(Volume(p.name, "gear", cylinder((x, y), p.z_min, p.z_max, p.diameter)))
                keep.append(
                    cylinder((x, y), p.z_min - axial, p.z_max + axial, p.diameter + 2 * radial)
                )
                circles.append((x, y, p.diameter / 2 + radial))
            elif p.kind == "carrier":
                parts.append(
                    Volume(p.name, "carrier", cylinder((x, y), p.z_min, p.z_max, p.diameter))
                )
                keep.append(
                    cylinder((x, y), p.z_min - axial, p.z_max + axial, p.diameter + 2 * radial)
                )
                circles.append((x, y, p.diameter / 2 + radial))
            elif p.kind == "bearing":
                side = p.name.rsplit(" ", 1)[-1]
                choice = chain.bearings.get((shaft, side))
                bore = choice.bearing.d if choice else 0.5 * p.diameter
                bores.append(bore)
                parts.append(
                    Volume(p.name, "bearing", ring((x, y), p.z_min, p.z_max, p.diameter, bore))
                )
                keep.append(cylinder((x, y), p.z_min, p.z_max, p.diameter))
                circles.append((x, y, p.diameter / 2))
        d = min(bores) if bores else sections[shaft].diameter
        z0 = stack.ends[0] - (OUTSIDE if (shaft, "-z") in sealed else 0.0)
        z1 = stack.ends[1] + (OUTSIDE if (shaft, "+z") in sealed else 0.0)
        parts.append(Volume(f"{shaft} shaft", "shaft", cylinder((x, y), z0, z1, d)))
        keep.append(cylinder((x, y), z0 - 1.0, z1 + 1.0, d))

    outline = hull_of_circles([(cx, cy, r + clearance) for cx, cy, r in circles])
    low = min(s.ends[0] for s in chain.layout.shafts) - clearance
    high = max(s.ends[1] for s in chain.layout.shafts) + clearance
    packaging = prism(outline, low, high)
    keep_out = fuse(keep)
    design = packaging.cut(keep_out).clean()
    return Space(
        parts=parts,
        packaging=Volume("packaging space", "packaging", packaging),
        keep_out=Volume("kept clear", "keep_out", keep_out),
        design=Volume("design space", "design_space", design),
        outline=outline,
        z_range=(low, high),
    )
