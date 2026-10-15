"""The fixed volumes a completed gear train and the contract give the housing, its shell, and the
spaces they leave (GBX-5). One description: `volumes` draws it exactly (PLT-8, the Contract page)
and the loop's optimiser samples it as voxels (`prototypes/first_loop/topo_free.py`), so the two
show the same set-up.

The fixed volumes are what the design space keeps out of (the engineer, 10 October 13:47). Each
is made of cylinders along the shafts (an axis in plan, a radius, a z range, and an inner radius
for a ring):
- **gears**, each its tip Ø over its face width;
- **shafts**, each at its least bore between its end faces, and where it leaves the housing its
  exit: the seal's bore (the shaft's Ø at that end, its bearing's bore, plus twice the seal's
  section, fitted from outside) and the room of what it joins beyond the end face (a half-shaft's
  joint), both from the end face to the packaging space's end;
- **bearing bores**, each bearing's outside Ø over its width;
- **the differential**, the carrier's case;
- **mounts**, each mount pad's boss with its bolt's hole, and the room of the vehicle's bracket
  and bolt beyond both faces;
- **bolts** at the split: round the rooms seen along the shafts, following their outline through
  the waists between them (not their hull, which left bosses off the flange), the process's joint
  offset outside the least wall, evenly at most its pitch apart, each a boss through the flange
  (`manufacturing.joint`, the process's rules);
- **the split flange**, where the halves meet (the same rules): a sealing land round the inside,
  the land's width out from the rooms seen along the shafts (both halves' openings), the flange's
  depth on each side of the split; the bolts' bosses stand on it.

**The shell** is one uniform least wall (the manufacturing profile's `min_wall`) round the inside.
The inside is every part's room (each gear and the carrier grown by the least radial and axial
clearances, A19 and A18; each bearing's room; each shaft at its least bore) run from its far end in
its half to the split, because the parts go in from the split: a cup per half, as a cast half is.
The halves meet at **the split plane**, square to the shafts.

The split's place, the inside's form, the wall (never under the contract's least) and the bolts'
pattern are a design's choices, an agent's hypothesis (the engineer, 10 October 13:52-14:00), given
as a `Hypothesis`; its defaults are the first loop's: the split between the stages (midway between
the first stage's gears and the second's), one cup per half, the least wall, the bolts evenly round
the inside at the process's most pitch.

The spaces: **the packaging space** (the hull of every part's circle grown by the installation
clearance, A3, and of the mounts' bosses, which the housing must reach, over the stacks' length
grown by the clearance) and **the design space**: the packaging space less the fixed volumes and
the shell, where the optimiser may add metal.

Shapes only, as numbers: no CAD kernel here (`volumes` builds the solids).
"""

from __future__ import annotations

from dataclasses import dataclass

from zenryx.contract.model import HousingDesignSpec
from zenryx.domains.gearbox.chain import Chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.geometry.plan import Point, hull_of_circles, outline_of_circles, spaced

TOOL = "zenryx.domains.gearbox.spaces"
VERSION = "0.1.0"

PLACES = ("between_stages",)


@dataclass(frozen=True)
class Cylinder:
    """A cylinder along the shafts: its axis in plan, its radius, its z range, and an inner
    radius for a ring (0: a full cylinder)."""

    name: str
    centre: Point
    radius: float
    z0: float
    z1: float
    inner: float = 0.0


@dataclass(frozen=True)
class Hypothesis:
    """What a design decides before the optimiser places metal: an agent's choices (the engineer,
    10 October 13:52-14:00), these defaults the first loop's. Where the halves meet; the inside's
    form; the shell's wall, never under the contract's least wall (None: the least wall); the
    bolts' pattern under the process's rules."""

    split: str = "between_stages"
    inside: str = "cup"  # one cup per half, every part's room run to the split
    wall: float | None = None
    bolts: str = "even"  # evenly round the inside, at the process's most pitch

    def check(self) -> None:
        if self.split not in PLACES:
            raise ValueError(f"the split's place {self.split!r}: one of {', '.join(PLACES)}")
        if self.inside != "cup":
            raise ValueError(f"the inside's form {self.inside!r}: 'cup' is the only one yet")
        if self.bolts != "even":
            raise ValueError(f"the bolts' pattern {self.bolts!r}: 'even' is the only one yet")


@dataclass(frozen=True)
class Spaces:
    """The fixed volumes, the shell and the spaces, every length in mm in the contract's frame."""

    gears: list[Cylinder]
    shafts: list[Cylinder]  # each shaft between its end faces
    exits: list[Cylinder]  # where shafts leave: the seals' bores, and the rooms beyond
    bearings: list[Cylinder]  # each bearing: its outside Ø over its width, its bore inside
    carriers: list[Cylinder]
    mounts: list[Cylinder]  # each boss, with its bolt's hole
    brackets: list[Cylinder]  # the vehicle's bracket and bolt beyond each mount's faces
    bolts: list[Cylinder]  # each bolt's boss through the flange, with its hole
    flange: list[Cylinder]  # each room's circle grown by the land, the flange's depth each side
    rooms: list[Cylinder]  # every part's room inside, with its clearances
    inside: list[Cylinder]  # each room run from its far end in its half to the split
    wall: float  # the shell's least wall
    split_z: float
    bolt_line: list[Point]
    joint_outline: list[Point]  # where the halves meet: the inside out to the bolts' bosses
    outline: list[Point]  # the packaging space, seen along the shafts
    z_range: tuple[float, float]  # the packaging space along the shafts

    @property
    def shell(self) -> list[Cylinder]:
        """The inside grown by the least wall, every way: the shell's outside, as cylinders whose
        union, less the inside, is the wall."""
        t = self.wall
        return [Cylinder(c.name, c.centre, c.radius + t, c.z0 - t, c.z1 + t) for c in self.inside]

    @property
    def flange_inside(self) -> list[Cylinder]:
        """The inside over the flange's depth: every room's circle, both halves' openings at the
        split. The flange's cylinders less these are the sealing land."""
        if not self.flange:
            return []
        z0, z1 = self.flange[0].z0, self.flange[0].z1
        return [Cylinder(c.name, c.centre, c.radius, z0, z1) for c in self.rooms]

    @property
    def keep_out(self) -> list[Cylinder]:
        """What the design space keeps out of, besides the shell: the exits, the mounts and their
        brackets' rooms, the bolts and the split flange (the parts lie inside the shell)."""
        held = self.mounts + self.bolts + self.flange
        whole = [Cylinder(c.name, c.centre, c.radius, c.z0, c.z1) for c in held]
        return self.exits + whole + self.brackets


def _mm(entry, default: float = 0.0) -> float:
    return default if entry is None else value_in(entry, "mm")


def split_height(spec: HousingDesignSpec, chain: Chain, place: str = "between_stages") -> float:
    """Where the halves meet along the shafts: for "between_stages", midway between the first
    stage's gears and the second's."""
    if place not in PLACES:
        raise ValueError(f"the split's place {place!r}: one of {', '.join(PLACES)}")
    stages = spec.requirement.stages
    if len(stages) != 2:
        raise ValueError("the split between the stages needs two stages")
    gears = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear"]

    def of(stage):
        return [p for p in gears if p.name.startswith(f"{stage.name} ")]

    first, second = of(stages[0]), of(stages[1])
    if max(p.z_max for p in first) <= min(p.z_min for p in second):
        return (max(p.z_max for p in first) + min(p.z_min for p in second)) / 2
    return (min(p.z_min for p in first) + max(p.z_max for p in second)) / 2


def spaces(spec: HousingDesignSpec, chain: Chain, hypothesis: Hypothesis | None = None) -> Spaces:
    """Every fixed volume, the shell and the spaces, for a design's hypothesis (the first loop's
    defaults when none is given)."""
    hypothesis = hypothesis or Hypothesis()
    hypothesis.check()
    req = spec.requirement
    gaps = req.shaft_layout
    radial = _mm(gaps.min_radial_clearance)
    axial = _mm(gaps.min_axial_clearance)
    section = _mm(gaps.seal_section)
    space = req.installation_space
    clearance = _mm(space.clearance) if space.kind == "layout_envelope" else 0.0
    least = value_in(spec.manufacturing.min_wall, "mm")
    wall = least if hypothesis.wall is None else hypothesis.wall
    if wall < least - 1e-9:
        raise ValueError(f"a wall of {wall:g} mm is under the contract's least wall, {least:g} mm")
    sealed = {(e.shaft, e.side.value): e for e in gaps.sealed_ends}

    gears, shafts, bearings, carriers, rooms, circles = [], [], [], [], [], []
    bore_at: dict[tuple[str, str], float] = {}
    for stack in chain.layout.shafts:
        (x, y), shaft = stack.axis, stack.shaft
        for p in stack.parts:
            if p.kind in ("gear", "carrier"):
                body = Cylinder(p.name, (x, y), p.diameter / 2, p.z_min, p.z_max)
                (gears if p.kind == "gear" else carriers).append(body)
                r = p.diameter / 2 + radial
                rooms.append(Cylinder(p.name, (x, y), r, p.z_min - axial, p.z_max + axial))
                circles.append((x, y, r))
            elif p.kind == "bearing":
                side = p.name.rsplit(" ", 1)[-1]
                choice = chain.bearings.get((shaft, side))
                bore = choice.bearing.d if choice else 0.5 * p.diameter
                bore_at[(shaft, side)] = bore
                r = p.diameter / 2
                bearings.append(Cylinder(p.name, (x, y), r, p.z_min, p.z_max, bore / 2))
                rooms.append(Cylinder(p.name, (x, y), r, p.z_min, p.z_max))
                circles.append((x, y, p.diameter / 2))
        bores = [v for (s, _), v in bore_at.items() if s == shaft]
        d = min(bores) if bores else next(s.diameter for s in chain.sections if s.shaft == shaft)
        shafts.append(Cylinder(f"{shaft} shaft", (x, y), d / 2, *stack.ends))
        rooms.append(Cylinder(f"{shaft} shaft", (x, y), d / 2, *stack.ends))

    # The mounts: the housing must reach them, so the packaging space holds their bosses.
    mounts, reach = [], []
    for m in req.mounts:
        (mx, my, mz), _ = m.centre.value.to_canonical()
        normal = m.normal.value.values
        if abs(abs(normal[2]) - 1.0) > 1e-6:
            raise ValueError(f"mount {m.name}: only a bolt along the shafts is drawn yet")
        r, half = _mm(m.diameter) / 2, _mm(m.length) / 2
        mounts.append(Cylinder(m.name, (mx, my), r, mz - half, mz + half, _mm(m.hole_diameter) / 2))
        reach.append((mx, my, r))

    outline = hull_of_circles([(cx, cy, r + clearance) for cx, cy, r in circles] + reach)
    low = min(s.ends[0] for s in chain.layout.shafts) - clearance
    high = max(s.ends[1] for s in chain.layout.shafts) + clearance

    # Where a shaft leaves: the seal's bore on the shaft at that end (its bearing's bore there),
    # and what it joins beyond the end face.
    exits = []
    for stack in chain.layout.shafts:
        (x, y), shaft = stack.axis, stack.shaft
        for side, z_end in (("-z", stack.ends[0]), ("+z", stack.ends[1])):
            end = sealed.get((shaft, side))
            if end is None:
                continue
            z0, z1 = (low, z_end) if side == "-z" else (z_end, high)
            seal = bore_at[(shaft, side)] / 2 + section
            exits.append(Cylinder(f"{shaft} seal {side}", (x, y), seal, z0, z1))
            if end.room is not None:
                exits.append(Cylinder(f"{shaft} joint {side}", (x, y), _mm(end.room) / 2, z0, z1))

    split_z = split_height(spec, chain, hypothesis.split)
    inside = []
    for c in rooms:
        if c.z0 < split_z:
            inside.append(Cylinder(c.name, c.centre, c.radius, c.z0, split_z))
        if c.z1 > split_z:
            inside.append(Cylinder(c.name, c.centre, c.radius, split_z, c.z1))

    # Each room as tall as its mount beyond each face, no higher (the engineer, 13 October
    # 20:31: "Keep clear is just the mount height and not any higher"); up to the packaging's
    # end, the room over each lug had kept a column through the whole housing clear
    brackets = []
    for m, boss in zip(req.mounts, mounts, strict=True):
        if m.bracket_room is not None:
            rb = _mm(m.bracket_room) / 2
            tall = boss.z1 - boss.z0
            below, above = f"{m.name} bracket -z", f"{m.name} bracket +z"
            brackets.append(Cylinder(below, boss.centre, rb, boss.z0 - tall, boss.z0))
            brackets.append(Cylinder(above, boss.centre, rb, boss.z1, boss.z1 + tall))

    bolts, bolt_line, flange = [], [], []
    joint = spec.manufacturing.joint
    joint_outline = hull_of_circles([(cx, cy, r + wall) for cx, cy, r in circles])
    if joint is not None:
        # The bolts' axes the rules' offset outside the least wall all round, through the waists
        # between the rooms too: on their hull, a waist's bolt stood clear of the flange.
        offset = wall + _mm(joint.bolt_offset)
        bolt_line = outline_of_circles([(cx, cy, r + offset) for cx, cy, r in circles])
        reach_out = offset + _mm(joint.boss_diameter) / 2
        joint_outline = outline_of_circles([(cx, cy, r + reach_out) for cx, cy, r in circles])
        t_f = _mm(joint.flange_thickness)
        land = _mm(joint.land_width)
        flange = [
            Cylinder(f"{c.name} land", c.centre, c.radius + land, split_z - t_f, split_z + t_f)
            for c in rooms
        ]
        for k, (bx, by) in enumerate(spaced(bolt_line, _mm(joint.max_pitch))):
            bolts.append(
                Cylinder(
                    f"bolt {k + 1}",
                    (bx, by),
                    _mm(joint.boss_diameter) / 2,
                    split_z - t_f,
                    split_z + t_f,
                    _mm(joint.hole_diameter) / 2,
                )
            )

    return Spaces(
        gears=gears,
        shafts=shafts,
        exits=exits,
        bearings=bearings,
        carriers=carriers,
        mounts=mounts,
        brackets=brackets,
        bolts=bolts,
        flange=flange,
        rooms=rooms,
        inside=inside,
        wall=wall,
        split_z=split_z,
        bolt_line=bolt_line,
        joint_outline=joint_outline,
        outline=outline,
        z_range=(low, high),
    )
