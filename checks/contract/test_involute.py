"""Involute geometry of a shifted helical pair: the pressure angles, the diameters, and the working
centre distance the validator checks."""

import math

import pytest

from zenryx.contract.involute import inv, inv_inverse, mesh_geometry, working_centre_distance

# Ivanov 2018's two stages: teeth, normal module (mm), profile shifts; alpha_n 18 deg, beta 30 deg.
IVANOV = [
    (25, 51, 1.85, 0.43672, 0.57199922),
    (23, 81, 2.05, 0.431143, 0.56857692),
]
ALPHA_N, BETA = math.radians(18), math.radians(30)


def _ivanov(stage: int):
    z1, z2, mn, x1, x2 = IVANOV[stage]
    return mesh_geometry(z1, z2, mn, ALPHA_N, BETA, x1, x2)


def test_inv_and_its_inverse():
    alpha = math.radians(20)
    assert inv(alpha) == pytest.approx(math.tan(alpha) - alpha)
    assert inv_inverse(inv(alpha)) == pytest.approx(alpha, abs=1e-12)


def test_unshifted_pair_sits_at_the_reference_centre_distance():
    # mn 2, z 25/65, beta 20 deg: a = mn (z1 + z2) / (2 cos beta)
    a = working_centre_distance(25, 65, 2.0, math.radians(20), math.radians(20), 0.0, 0.0)
    assert a == pytest.approx(2.0 * 90 / (2 * math.cos(math.radians(20))), rel=1e-12)


def test_an_unshifted_pair_runs_on_its_reference_circles():
    g = mesh_geometry(25, 65, 2.0, math.radians(20), math.radians(20), 0.0, 0.0)
    assert g.working_pressure_angle == pytest.approx(g.transverse_pressure_angle, abs=1e-12)
    assert g.working_pitch_diameters == pytest.approx(g.reference_diameters, rel=1e-12)


def test_a_shifted_pair_matches_the_hand_calculation():
    # z 14/46, mn 1.75, alpha_n 20, beta 25, x 0.2 / -0.7299: worked by hand to 56.94 mm
    a = working_centre_distance(14, 46, 1.75, math.radians(20), math.radians(25), 0.2, -0.7299)
    assert a == pytest.approx(56.94, abs=0.02)


def test_ivanovs_stages_run_at_their_published_centre_distances():
    # Ivanov 2018 gives 83 and 125 mm; the validator allows 0.1 mm.
    assert _ivanov(0).working_centre_distance == pytest.approx(83.0, abs=0.1)
    assert _ivanov(1).working_centre_distance == pytest.approx(125.0, abs=0.1)


def test_the_working_pressure_angle_solves_the_involute_relation():
    for stage, (z1, z2, _, x1, x2) in enumerate(IVANOV):
        g = _ivanov(stage)
        assert math.tan(g.transverse_pressure_angle) == pytest.approx(
            math.tan(ALPHA_N) / math.cos(BETA), rel=1e-12
        )
        assert inv(g.working_pressure_angle) - inv(g.transverse_pressure_angle) == pytest.approx(
            2 * (x1 + x2) * math.tan(ALPHA_N) / (z1 + z2), rel=1e-12
        )
    # The values the contract page shows.
    assert round(math.degrees(_ivanov(0).transverse_pressure_angle), 3) == 20.565
    assert round(math.degrees(_ivanov(0).working_pressure_angle), 3) == 23.566
    assert round(math.degrees(_ivanov(1).working_pressure_angle), 3) == 22.824


def test_the_diameters_hold_together():
    for stage, (z1, z2, mn, _, _) in enumerate(IVANOV):
        g = _ivanov(stage)
        (d1, d2), (db1, db2), (dw1, dw2) = (
            g.reference_diameters,
            g.base_diameters,
            g.working_pitch_diameters,
        )
        assert (d1, d2) == pytest.approx((z1 * mn / math.cos(BETA), z2 * mn / math.cos(BETA)))
        # One base circle per gear: it is the reference circle's and the working circle's.
        assert db1 == pytest.approx(d1 * math.cos(g.transverse_pressure_angle), rel=1e-12)
        assert db1 == pytest.approx(dw1 * math.cos(g.working_pressure_angle), rel=1e-12)
        assert db2 == pytest.approx(dw2 * math.cos(g.working_pressure_angle), rel=1e-12)
        # The working circles touch at the pitch point and keep the tooth ratio.
        assert dw1 + dw2 == pytest.approx(2 * g.working_centre_distance, rel=1e-12)
        assert dw2 / dw1 == pytest.approx(z2 / z1, rel=1e-12)


def test_the_centre_distance_function_is_the_geometrys():
    z1, z2, mn, x1, x2 = IVANOV[1]
    assert working_centre_distance(z1, z2, mn, ALPHA_N, BETA, x1, x2) == (
        mesh_geometry(z1, z2, mn, ALPHA_N, BETA, x1, x2).working_centre_distance
    )
