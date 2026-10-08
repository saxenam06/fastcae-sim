"""GBX-1: the forces and moments at each gear mesh (zenryx.domains.gearbox.forces).

Checked on a ladder: the textbook form at zero shift; exact invariants (equal and opposite forces,
the torque given back, every shaft balanced); the hand rule for thrust; a published worked
example; and the product contract's own numbers.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from zenryx.contract.involute import inv, inv_inverse, mesh_geometry
from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.forces import case_forces, mesh_forces

CONTRACT = Path(__file__).parents[1] / "data" / "contracts" / "ev_reducer_posed.json"
DEG = math.pi / 180


def _pair(torque, hand="right", shifts=(0.0, 0.0), z=(20, 60), mn=2.0, alpha=20, beta=15):
    a = mesh_geometry(z[0], z[1], mn, alpha * DEG, beta * DEG, *shifts).working_centre_distance
    return mesh_forces("s", z, mn, alpha * DEG, beta * DEG, shifts, hand, torque, ((0, 0), (a, 0)))


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def test_at_zero_shift_it_is_the_textbook_form():
    """Shigley Ch. 13: Ft = 2T/d, Fr = Ft tan(alpha_n) / cos(beta), Fa = Ft tan(beta)."""
    torque, z, mn, alpha, beta = 100_000.0, (20, 60), 2.0, 20 * DEG, 15 * DEG
    m = _pair(torque)
    d1 = z[0] * mn / math.cos(beta)
    ft = 2 * torque / d1
    assert m.tangential == pytest.approx(ft, rel=1e-12)
    assert m.radial == pytest.approx(ft * math.tan(alpha) / math.cos(beta), rel=1e-12)
    assert m.axial == pytest.approx(ft * math.tan(beta), rel=1e-12)


def test_a_published_worked_example_is_reproduced():
    """drivetrainhub, notebooks-gears, "Chapter 1 - Force Analysis" (figures credited to Maitra,
    Handbook of Gear Design): z 15/45, mn 2.5 mm, alpha_n 20 deg, beta 20 deg, a 80 mm, T 100 N·m
    give Ft 5000.0 N, Fr 1971.1 N at alpha_tw 21.515 deg, and Fa 1819.9 N as Ft tan(beta).
    https://github.com/drivetrainhub/notebooks-gears (strength/Chapter 1 - Force Analysis.ipynb)

    The 80 mm is reached by profile shift; only its sum sets the working angle, so it is solved
    from the centre distance. The axial force here follows the base helix (Ft tan(beta_w)): the
    notebook's Ft tan(beta) is the reference-helix convention, 0.2 % lower for this pair."""
    z, mn, alpha, beta, a = (15, 45), 2.5, 20 * DEG, 20 * DEG, 80.0
    alpha_t = math.atan(math.tan(alpha) / math.cos(beta))
    a0 = (z[0] + z[1]) * mn / (2 * math.cos(beta))
    alpha_wt = math.acos(a0 * math.cos(alpha_t) / a)
    shift = (inv(alpha_wt) - inv(alpha_t)) * (z[0] + z[1]) / (2 * math.tan(alpha))
    assert inv_inverse(inv(alpha_t) + 2 * shift * math.tan(alpha) / sum(z)) == pytest.approx(
        alpha_wt
    )
    m = mesh_forces("s", z, mn, alpha, beta, (shift / 2, shift / 2), "right", 100_000.0,
                    ((0, 0), (a, 0)))  # fmt: skip
    assert math.degrees(alpha_wt) == pytest.approx(21.515, abs=5e-4)
    assert m.tangential == pytest.approx(5000.0, abs=0.05)
    assert m.radial == pytest.approx(1971.1, abs=0.05)
    assert m.tangential * math.tan(beta) == pytest.approx(1819.9, abs=0.05)
    dw, d = 2 * a * z[0] / sum(z), z[0] * mn / math.cos(beta)
    assert m.axial == pytest.approx(m.tangential * math.tan(beta) * dw / d, rel=1e-12)
    assert m.axial / (m.tangential * math.tan(beta)) - 1 == pytest.approx(0.0023, abs=1e-4)


def test_the_two_gears_feel_equal_and_opposite_forces():
    m = _pair(150_000.0, shifts=(0.4, 0.6))
    assert all(p == pytest.approx(-g) for p, g in zip(m.pinion.force, m.gear.force, strict=True))
    assert m.pinion.point == m.gear.point
    # The force's size is the normal tooth force: its three parts at right angles.
    whole = math.sqrt(m.tangential**2 + m.radial**2 + m.axial**2)
    assert _norm(m.pinion.force) == pytest.approx(whole)


def test_the_tangential_force_gives_back_each_gears_torque():
    torque = 150_000.0
    m = _pair(torque, shifts=(0.43672, 0.57199922), z=(25, 51), mn=1.85, alpha=18, beta=30)
    assert m.pinion.moment[2] == pytest.approx(-torque)  # the mesh resists what drives it
    assert m.gear.moment[2] == pytest.approx(-torque * 51 / 25)  # it turns the gear the other way
    rw1 = math.dist(m.pinion.centre, m.pinion.point)
    assert m.tangential * rw1 == pytest.approx(torque)


def test_the_radial_force_pushes_the_two_gears_apart():
    for torque in (150_000.0, -150_000.0):
        m = _pair(torque, shifts=(0.4, 0.6))
        # The pinion's axis is at the origin, the gear's along +x.
        assert m.pinion.force[0] == pytest.approx(-m.radial)
        assert m.gear.force[0] == pytest.approx(m.radial)


def test_the_hand_rule_for_thrust():
    """Curl the fingers of the driver's own hand in its sense of rotation; the thumb gives the
    driver's thrust (e.g. KHK, Gear Technical Reference, on the thrust of helical gears). A
    positive torque turns the driving pinion anticlockwise seen from +z."""
    assert _pair(150_000.0, hand="right").pinion.force[2] > 0
    assert _pair(150_000.0, hand="left").pinion.force[2] < 0
    assert _pair(-150_000.0, hand="right").pinion.force[2] < 0
    assert _pair(-150_000.0, hand="left").pinion.force[2] > 0


def test_the_axial_force_has_its_moment_about_the_gears_centre():
    m = _pair(150_000.0, shifts=(0.4, 0.6))
    rw1 = math.dist(m.pinion.centre, m.pinion.point)
    rw2 = math.dist(m.gear.centre, m.gear.point)
    assert math.hypot(m.pinion.moment[0], m.pinion.moment[1]) == pytest.approx(m.axial * rw1)
    assert math.hypot(m.gear.moment[0], m.gear.moment[1]) == pytest.approx(m.axial * rw2)


def test_axes_that_do_not_sit_at_the_working_distance_are_refused():
    with pytest.raises(ValueError, match="working centre distance"):
        mesh_forces("s", (20, 60), 2.0, 20 * DEG, 15 * DEG, (0, 0), "right", 1e5, ((0, 0), (90, 0)))


@pytest.fixture(scope="module")
def cases():
    spec, refusals = load_and_validate(CONTRACT)
    assert refusals == []
    return {c.name: c for c in case_forces(spec)}


def test_the_ev_reducer_has_one_case_per_torque(cases):
    assert list(cases) == ["peak drive", "peak reverse", "peak regeneration"]


def test_the_ev_reducers_forces(cases):
    """At 150 N·m, as the load tool's plan worked them (§1; prototypes/helical_forces)."""
    s1, s2 = cases["peak drive"].meshes
    assert (s1.tangential, s1.radial, s1.axial) == pytest.approx((5499.4, 2398.7, 3243.2), abs=0.05)
    assert (s2.tangential, s2.radial, s2.axial) == pytest.approx(
        (11066.0, 4657.1, 6489.9), abs=0.05
    )
    assert s2.pinion_torque == pytest.approx(-150_000.0 * 51 / 25)


def test_every_shaft_passes_its_torque_on(cases):
    """Steady state: on the intermediate shaft, the torque the first mesh puts in, the second
    takes out; the output's is the input's times the ratio, in the same sense."""
    for case in cases.values():
        s1, s2 = case.meshes
        assert s1.gear.moment[2] + s2.pinion.moment[2] == pytest.approx(0.0, abs=1e-6)
        torques = dict(case.shaft_torques)
        assert torques["output"] == pytest.approx(case.input_torque * (51 / 25) * (81 / 23))


def test_reverse_and_regeneration_load_the_teeth_alike(cases):
    reverse, regen = cases["peak reverse"], cases["peak regeneration"]
    for a, b in zip(reverse.meshes, regen.meshes, strict=True):
        assert a.pinion.force == pytest.approx(b.pinion.force)
    # Against drive: the tangential and axial parts reverse, the radial part does not.
    drive = cases["peak drive"]
    for d, r in zip(drive.meshes, reverse.meshes, strict=True):
        assert r.pinion.force[2] == pytest.approx(-d.pinion.force[2])
        assert r.pinion.moment[2] == pytest.approx(-d.pinion.moment[2])
        assert r.radial == pytest.approx(d.radial)


def test_the_forward_rotation_mirrors_the_directions_not_the_sizes():
    spec, _ = load_and_validate(CONTRACT)
    req = spec.requirement
    turned = req.forward_rotation.model_copy(update={"value": "-z"})
    flipped = spec.model_copy(
        update={"requirement": req.model_copy(update={"forward_rotation": turned})}
    )
    a = {c.name: c for c in case_forces(spec)}["peak drive"]
    b = {c.name: c for c in case_forces(flipped)}["peak drive"]
    for ma, mb in zip(a.meshes, b.meshes, strict=True):
        assert (mb.tangential, mb.radial, mb.axial) == pytest.approx(
            (ma.tangential, ma.radial, ma.axial)
        )
        assert mb.pinion.force[2] == pytest.approx(-ma.pinion.force[2])
