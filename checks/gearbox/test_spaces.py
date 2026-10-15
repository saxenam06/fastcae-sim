"""The fixed volumes, the shell and the spaces (GBX-5, `zenryx.domains.gearbox.spaces`), and their
exact solids (`volumes`): one description for the Contract page and the optimiser's voxels."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.spaces import Hypothesis, spaces
from zenryx.domains.gearbox.volumes import volumes, whole
from zenryx.geometry.plan import outline_of_circles, perimeter, spaced
from zenryx.geometry.solids import fuse

CONTRACT = Path(__file__).parents[1] / "data" / "contracts" / "ev_reducer_posed.json"


@pytest.fixture(scope="module")
def spec():
    spec, refusals = load_and_validate(CONTRACT)
    assert spec is not None, refusals
    return spec


@pytest.fixture(scope="module")
def chain(spec):
    return complete_chain(spec)


@pytest.fixture(scope="module")
def sp(spec, chain):
    return spaces(spec, chain)


def _inside(poly, x, y) -> bool:
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def test_the_split_lies_midway_between_the_stages(sp, chain):
    gears = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear"]
    first = max(p.z_max for p in gears if p.name.startswith("s1 "))
    second = min(p.z_min for p in gears if p.name.startswith("s2 "))
    assert sp.split_z == pytest.approx((first + second) / 2)
    assert first < sp.split_z < second


def test_the_inside_runs_every_room_to_the_split(sp):
    """A cup per half: each piece ends at the split, and every room is covered on its side(s)."""
    for c in sp.inside:
        assert sp.split_z in (c.z0, c.z1), c.name
    for room in sp.rooms:
        halves = [c for c in sp.inside if c.name == room.name and c.radius == room.radius]
        low = [c for c in halves if c.z1 == sp.split_z]
        high = [c for c in halves if c.z0 == sp.split_z]
        assert bool(low) == (room.z0 < sp.split_z) and bool(high) == (room.z1 > sp.split_z)
        if low:
            assert low[0].z0 == room.z0
        if high:
            assert high[0].z1 == room.z1


def test_each_seal_sits_on_the_shaft_at_its_own_end(sp, spec, chain):
    """The seal's bore is the bearing's bore at that end plus twice the section (A16): the input
    leaves at its 6309 end (45 mm), not on its least bore (25 mm, at the other end)."""
    section = spec.requirement.shaft_layout.seal_section.value.value
    seals = {c.name: c for c in sp.exits if " seal " in c.name}
    assert set(seals) == {"input seal -z", "output seal -z", "output seal +z"}
    for name, c in seals.items():
        shaft, _, side = name.split(" ")
        bore = chain.bearings[(shaft, side)].bearing.d
        assert c.radius == pytest.approx(bore / 2 + section)
    assert seals["input seal -z"].radius == pytest.approx(32.5)


def test_the_bolts_stand_evenly_at_most_the_pitch_apart(sp, spec):
    joint = spec.manufacturing.joint
    pitch = joint.max_pitch.value.value
    n = len(sp.bolts)
    assert n == max(4, math.ceil(perimeter(sp.bolt_line) / pitch))
    assert perimeter(sp.bolt_line) / n <= pitch
    for b in sp.bolts:
        assert b.radius == pytest.approx(joint.boss_diameter.value.value / 2)
        assert (b.z0, b.z1) == pytest.approx((sp.split_z - 8.0, sp.split_z + 8.0))


def test_the_split_flange_is_a_sealing_land_round_the_inside(spec, chain, sp):
    """The halves meet on a flange the contract fixes (A26; the engineer, 10 Oct 23:47): a land the
    rules' width out from every room seen along the shafts, the flange's depth each side of the
    split. Drawn, the land holds no room and reaches every bolt's boss."""
    joint = spec.manufacturing.joint
    land, t_f = joint.land_width.value.value, joint.flange_thickness.value.value
    assert len(sp.flange) == len(sp.rooms)
    for f, r in zip(sp.flange, sp.rooms, strict=True):
        assert f.centre == r.centre and f.radius == pytest.approx(r.radius + land)
        assert (f.z0, f.z1) == pytest.approx((sp.split_z - t_f, sp.split_z + t_f))
    circles = [(r.centre, r.radius) for r in sp.rooms]
    assert [(c.centre, c.radius) for c in sp.flange_inside] == circles
    space = volumes(spec, chain)
    drawn = space.split.solid
    rooms = fuse([whole(c) for c in sp.flange_inside])
    assert drawn.intersect(rooms).Volume() < 1.0  # mm³: the land holds no room
    assert drawn.Volume() > 0.0
    for b in sp.bolts:
        assert drawn.intersect(whole(b)).Volume() > 1.0, b.name  # every boss stands on the land


def _area(poly) -> float:
    n = len(poly)
    return 0.5 * sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(n))


def test_the_outline_of_circles_follows_their_union():
    """Two overlapping circles: the outline runs round both, anticlockwise, every point on one of
    them and inside neither, and it encloses their union's area (the lens counted once)."""
    r1, r2, d = 50.0, 30.0, 60.0
    poly = outline_of_circles([(0.0, 0.0, r1), (d, 0.0, r2)], step_deg=0.5)
    for x, y in poly:
        on = [abs(math.hypot(x - cx, y) - r) < 1e-6 for cx, r in ((0.0, r1), (d, r2))]
        assert any(on)
        assert math.hypot(x, y) > r1 - 1e-6 and math.hypot(x - d, y) > r2 - 1e-6
    a1 = math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    lens = r1 * r1 * (a1 - math.sin(2 * a1) / 2) + r2 * r2 * (a2 - math.sin(2 * a2) / 2)
    union = math.pi * (r1 * r1 + r2 * r2) - lens
    assert _area(poly) == pytest.approx(union, rel=2e-4)
    # One circle is its own outline; a circle inside another adds nothing.
    alone = outline_of_circles([(0.0, 0.0, 10.0), (2.0, 0.0, 3.0)])
    assert _area(alone) == pytest.approx(math.pi * 100.0, rel=1e-3)


def test_spaced_points_are_evenly_round_an_outline():
    square = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    points = spaced(square, 10.0)
    assert len(points) == 4
    assert points[0] == pytest.approx((5.0, 0.0))
    assert points[2] == pytest.approx((5.0, 10.0))


def test_the_packaging_space_holds_the_mounts(sp):
    """The housing must reach its mounts, so the packaging hull holds their bosses (two of the
    first loop's three stood outside the parts' hull)."""
    for m in sp.mounts:
        for k in range(16):
            a = 2 * math.pi * k / 16
            x = m.centre[0] + 0.999 * m.radius * math.cos(a)
            y = m.centre[1] + 0.999 * m.radius * math.sin(a)
            assert _inside(sp.outline, x, y), m.name


def test_every_brackets_room_clears_the_housing(sp):
    """Each mount's lug stands past the split flange's edge, so the vehicle's bracket and bolt
    (its room beyond both faces, as far as the boss is long) touch neither the shell nor the flange.
    The first loop's places, kept from before the contract had a shell and a flange, put mount-2's
    room 11 mm into the wall and mount-3's 16.5 mm into the flange (10 October 20:45)."""
    for b in sp.brackets:
        for k in range(48):  # the room's rim, in plan
            a = 2 * math.pi * k / 48
            x, y = b.centre[0] + b.radius * math.cos(a), b.centre[1] + b.radius * math.sin(a)
            assert not _inside(sp.joint_outline, x, y), b.name
        for s in sp.shell:
            if s.z1 > b.z0 and s.z0 < b.z1:
                apart = math.hypot(b.centre[0] - s.centre[0], b.centre[1] - s.centre[1])
                assert apart - s.radius - b.radius > 0.0, (b.name, s.name)


def test_the_hypothesis_never_thins_the_wall_under_the_contracts_least(spec, chain):
    assert spaces(spec, chain, Hypothesis(wall=5.0)).wall == 5.0
    with pytest.raises(ValueError, match="least wall"):
        spaces(spec, chain, Hypothesis(wall=3.0))
    with pytest.raises(ValueError, match="split"):
        spaces(spec, chain, Hypothesis(split="at_the_motor"))


def test_the_design_space_meets_no_element(spec, chain):
    """The packaging less the shell's outside, the exits, the mounts and their brackets' rooms and
    the bolts: none of them overlaps it."""
    space = volumes(spec, chain)
    sp = space.spaces
    elements = fuse([whole(c) for c in sp.shell + sp.keep_out])
    assert space.design.solid.intersect(elements).Volume() < 1.0  # mm³
    assert (
        space.design.solid.Volume()
        < space.packaging.solid.Volume() - elements.intersect(space.packaging.solid).Volume() + 1.0
    )
