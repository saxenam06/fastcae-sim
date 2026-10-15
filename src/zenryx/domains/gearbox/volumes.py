"""The fixed volumes, the shell and the spaces of `spaces`, drawn as exact solids (PLT-8, the
contract's result; GBX-5). The design space keeps out of every fixed volume and the shell (the
engineer, 10 October 13:47); `spaces` says what each is.

- **The fixed volumes**, solid: the gears, the shafts between their end faces, the bearing bores
  (each bearing as a ring), the differential, the mounts' bosses, the bolts' bosses. Beside them,
  see-through, the room they need where they reach outside: each shaft's exit (its seal's bore
  and a half-shaft's joint) and the vehicle's bracket at each mount.
- **The shell:** the inside (each part's room run to the split) grown by the least wall, less the
  inside and the exits: the wall. **The split flange**, where the halves meet: the sealing land
  round the inside, the flange's depth each side of the split (without joint rules, the split
  plane alone, as a thin slab over the joint's outline).
- **The packaging space**, and **the design space**: the packaging space less the shell's
  outside, the exits, the mounts and their brackets' rooms, the bolts and the split flange.
"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from zenryx.contract.model import HousingDesignSpec
from zenryx.domains.gearbox.chain import Chain
from zenryx.domains.gearbox.spaces import Cylinder, Hypothesis, Spaces, spaces
from zenryx.geometry.solids import cylinder, fuse, prism, ring

TOOL = "zenryx.domains.gearbox.volumes"
VERSION = "0.2.0"

SPLIT_DEPTH = 0.5  # mm: without joint rules, the split plane drawn as a slab this thin


@dataclass(frozen=True)
class Volume:
    name: str
    role: str
    solid: cq.Shape


@dataclass(frozen=True)
class Space:
    """Every element as solids: the fixed volumes (`parts`, each tagged by its role), the rooms
    they need outside (`reach`), the shell's wall, the split flange, and the two spaces."""

    parts: list[Volume]
    reach: list[Volume]
    wall: Volume
    split: Volume
    packaging: Volume
    design: Volume
    spaces: Spaces
    outline: list[tuple[float, float]]
    z_range: tuple[float, float]


def solid(c: Cylinder) -> cq.Shape:
    """A cylinder of `spaces` as a solid: a ring where it has an inner radius."""
    if c.inner > 0:
        return ring(c.centre, c.z0, c.z1, 2 * c.radius, 2 * c.inner)
    return cylinder(c.centre, c.z0, c.z1, 2 * c.radius)


def whole(c: Cylinder) -> cq.Shape:
    """A cylinder of `spaces` with any hole filled: the room it takes."""
    return cylinder(c.centre, c.z0, c.z1, 2 * c.radius)


def volumes(spec: HousingDesignSpec, chain: Chain, hypothesis: Hypothesis | None = None) -> Space:
    sp = spaces(spec, chain, hypothesis)
    parts: list[Volume] = []
    for role, members in (
        ("gear", sp.gears),
        ("shaft", sp.shafts),
        ("bearing", sp.bearings),
        ("carrier", sp.carriers),
        ("mount", sp.mounts),
        ("bolt", sp.bolts),
    ):
        parts += [Volume(c.name, role, solid(c)) for c in members]
    reach = [Volume(c.name, "shaft", whole(c)) for c in sp.exits]
    reach += [Volume(c.name, "mount", whole(c)) for c in sp.brackets]

    low, high = sp.z_range
    packaging = prism(sp.outline, low, high)
    outside = fuse([whole(c) for c in sp.shell])
    inside = fuse([whole(c) for c in sp.inside])
    wall = outside.cut(inside)
    if sp.exits:
        wall = wall.cut(fuse([whole(c) for c in sp.exits]))
    wall = wall.intersect(packaging).clean()
    if sp.flange:
        land = fuse([whole(c) for c in sp.flange]).cut(fuse([whole(c) for c in sp.flange_inside]))
        split = Volume("split flange", "split", land.clean())
    else:
        plane = prism(sp.joint_outline, sp.split_z - SPLIT_DEPTH / 2, sp.split_z + SPLIT_DEPTH / 2)
        split = Volume("split plane", "split", plane)
    keep = [outside] + [whole(c) for c in sp.keep_out]
    design = packaging.cut(fuse(keep)).clean()
    return Space(
        parts=parts,
        reach=reach,
        wall=Volume("the shell's wall", "shell", wall),
        split=split,
        packaging=Volume("packaging space", "packaging", packaging),
        design=Volume("design space", "design_space", design),
        spaces=sp,
        outline=sp.outline,
        z_range=sp.z_range,
    )
