"""GBX-2: the layout along each shaft, its clearances, and the seat loads.

The layout is checked against its stack rules and the clearance rule with an injected fault; the
loads against a textbook worked example (the axial force's moment, JTEKT eq. 5-29), against
statics on every shaft, and against what the housing as a whole must hold.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from zenryx.contract.units import Quantity
from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.forces import case_forces, mesh_forces
from zenryx.domains.gearbox.layout import place
from zenryx.domains.gearbox.loads import FIRST_GUESS_Y, seat_loads, shaft_seats

CONTRACT = Path(__file__).parents[1] / "data" / "contracts" / "ev_reducer_posed.json"
DEG = math.pi / 180
GUESS = {
    (s, side): (20.0, 80.0) for s in ("input", "intermediate", "output") for side in ("-z", "+z")
}


@pytest.fixture(scope="module")
def spec():
    spec, refusals = load_and_validate(CONTRACT)
    assert refusals == []
    return spec


@pytest.fixture(scope="module")
def layout(spec):
    return place(spec, GUESS)


def _with_layout(spec, **changes):
    req = spec.requirement
    gaps = req.shaft_layout
    for field, value in changes.items():
        entry = getattr(gaps, field)
        gaps = gaps.model_copy(update={field: entry.model_copy(update={"value": value})})
    return spec.model_copy(update={"requirement": req.model_copy(update={"shaft_layout": gaps})})


def test_the_second_mesh_plane_sits_the_gear_to_gear_gap_beyond_the_first(layout):
    # Stage 1 on the motor side (A22): the shared shaft's two gears 12.7 mm apart (A15).
    planes = dict(layout.planes)
    assert planes["s1"] == 0.0
    assert planes["s2"] == pytest.approx(15.5 / 2 + 12.7 + 25.625 / 2)


def test_a_plain_shaft_stacks_the_gap_and_the_bearing_beyond_its_gears(layout):
    stack = layout.stack("input")
    low, high = stack.bearing("-z"), stack.bearing("+z")
    assert low.z_max == pytest.approx(-16.5 / 2 - 12.7)
    assert high.z_min == pytest.approx(16.5 / 2 + 12.7)
    assert low.width == pytest.approx(20.0)


def test_the_space_behind_a_bearing_depends_on_its_end(layout):
    # The input leaves the housing at -z (a seal, 11 mm), its +z bore is closed (6.35 mm).
    stack = layout.stack("input")
    assert stack.ends[0] == pytest.approx(stack.bearing("-z").z_min - 11.0)
    assert stack.ends[1] == pytest.approx(stack.bearing("+z").z_max - 0.0 + 6.35)


def test_the_differential_sets_the_output_bearings_apart(layout):
    stack = layout.stack("output")
    low, high = stack.bearing("-z"), stack.bearing("+z")
    assert high.centre - low.centre == pytest.approx(96.0)
    gear = next(p for p in stack.parts if p.kind == "gear")
    assert high.z_min - gear.z_max == pytest.approx(12.7)  # the gear beside its +z bearing
    body = next(p for p in stack.parts if p.kind == "carrier")
    assert (body.z_min, body.z_max) == pytest.approx((low.z_max, gear.z_min))
    assert body.diameter == pytest.approx(105.0)


def test_parts_that_overlap_end_on_clear_each_other_along_the_shafts(layout):
    pair = next(c for c in layout.clearances if {c.a, c.b} == {"s1 gear", "s2 gear"})
    assert pair.overlap == pytest.approx(31.4, abs=0.05)
    assert pair.gap == pytest.approx(12.7 + (25.625 - 22.25) / 2)
    assert pair.ok and layout.breaches == ()


def test_a_layout_that_breaks_the_least_clearance_is_reported(spec):
    # An injected fault: the shared shaft's two gears 0.5 mm apart leave the stage-1 gear 2.19 mm
    # from the output gear, under the 3 mm least clearance (A18).
    tight = place(_with_layout(spec, gear_to_gear=Quantity(value=0.5, unit="mm")), GUESS)
    breaches = {frozenset((c.a, c.b)): c for c in tight.breaches}
    pair = breaches[frozenset(("s1 gear", "s2 gear"))]
    assert pair.gap == pytest.approx(0.5 + (25.625 - 22.25) / 2)
    assert pair.least == pytest.approx(3.0)


def test_a_carrier_too_short_for_its_gear_is_refused(spec):
    req = spec.requirement
    gaps = req.shaft_layout
    carrier = gaps.carriers[0]
    short = carrier.model_copy(
        update={
            "bearing_spacing": carrier.bearing_spacing.model_copy(
                update={"value": Quantity(value=40, unit="mm")}
            )
        }
    )
    changed = spec.model_copy(
        update={
            "requirement": req.model_copy(
                update={"shaft_layout": gaps.model_copy(update={"carriers": [short]})}
            )
        }
    )
    with pytest.raises(ValueError, match="no room for its body"):
        place(changed, GUESS)


def test_the_textbook_example_is_reproduced():
    """GHE §6.2's worked example (on JTEKT eq. 5-29): a 60 mm helical pinion centred between two
    bearings 120 mm apart, 300 N·m, alpha_n 20 deg, beta 25 deg. Each seat takes half of Ft; in the
    radial plane Fr/2 ∓ (d/2)·Fa/L; the locating bearing takes Fa."""
    beta = 25 * DEG
    mn = 60 * math.cos(beta) / 20
    mesh = mesh_forces(
        "s1", (20, 40), mn, 20 * DEG, beta, (0.0, 0.0), "right", 300e3, ((0, 0), (90, 0)),
        ("pinion", "wheel"),
    )  # fmt: skip
    ft = 2 * 300e3 / 60.0
    fr = ft * math.tan(20 * DEG) / math.cos(beta)
    fa = ft * math.tan(beta)
    roles = {"-z": ("deep_groove_ball", "floating"), "+z": ("deep_groove_ball", "locating")}
    a, b = shaft_seats("pinion", [(mesh.pinion, 60.0)], (0.0, 120.0), roles)
    assert abs(a.force[1]) == pytest.approx(ft / 2) and abs(b.force[1]) == pytest.approx(ft / 2)
    assert sorted([abs(a.force[0]), abs(b.force[0])]) == pytest.approx(
        [0.5 * fr - 30 * fa / 120, 0.5 * fr + 30 * fa / 120]
    )
    assert (a.axial, abs(b.axial)) == pytest.approx((0.0, fa))


def test_every_shaft_balances(spec, layout):
    cases = case_forces(spec)
    planes = dict(layout.planes)
    for case, loads in zip(cases, seat_loads(spec, layout, cases), strict=True):
        for stack in layout.shafts:
            gear_loads = [
                (g, planes[m.stage])
                for m in case.meshes
                for g in (m.pinion, m.gear)
                if g.shaft == stack.shaft
            ]
            low, high = loads.seat(stack.shaft, "-z"), loads.seat(stack.shaft, "+z")
            # The bearings push the shaft with the opposite of what the seats take.
            for k in range(3):
                total = sum(g.force[k] for g, _ in gear_loads) - low.force[k] - high.force[k]
                assert total == pytest.approx(0.0, abs=1e-6)
            # Moments in the two planes about the -z support.
            mx = my = 0.0
            for g, z in gear_loads:
                lever = z - low.z
                mx += g.moment[0] - lever * g.force[1]
                my += g.moment[1] + lever * g.force[0]
            lever = high.z - low.z
            mx -= -lever * high.force[1]
            my -= lever * high.force[0]
            assert (mx, my) == pytest.approx((0.0, 0.0), abs=1e-3)


def test_the_housing_holds_the_output_torque_at_its_mounts(spec, layout):
    """The seats' forces cancel; with the motor's reaction they twist the housing by -i·T_in about
    z, which the mounts must hold."""
    cases = case_forces(spec)
    ratio = (51 / 25) * (81 / 23)
    for case, loads in zip(cases, seat_loads(spec, layout, cases), strict=True):
        total = [sum(s.force[k] for s in loads.seats) for k in range(3)]
        assert total == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)
        twist = loads.motor_torque
        for s in loads.seats:
            x, y = layout.stack(s.shaft).axis
            twist += x * s.force[1] - y * s.force[0]
        assert twist == pytest.approx(-ratio * case.input_torque, rel=1e-9)


def test_the_tapered_pair_carries_its_induced_forces(spec, layout):
    drive = {c.name: c for c in seat_loads(spec, layout, case_forces(spec))}["peak drive"]
    low, high = drive.seat("intermediate", "-z"), drive.seat("intermediate", "+z")
    induced = 0.5 * low.radial / FIRST_GUESS_Y
    assert low.axial == pytest.approx(-induced)
    thrust = 3243.2 + 6489.9  # both of the shaft's axial forces push towards +z in drive
    assert high.axial == pytest.approx(induced + thrust, abs=0.2)


def test_a_locating_bearing_takes_all_the_thrust(spec, layout):
    drive = {c.name: c for c in seat_loads(spec, layout, case_forces(spec))}["peak drive"]
    assert drive.seat("input", "-z").axial == pytest.approx(-3243.2, abs=0.05)
    assert drive.seat("input", "+z").axial == 0.0


def test_reverse_and_regeneration_load_the_seats_alike(spec, layout):
    loads = {c.name: c for c in seat_loads(spec, layout, case_forces(spec))}
    for a, b in zip(loads["peak reverse"].seats, loads["peak regeneration"].seats, strict=True):
        assert a.force == pytest.approx(b.force)
