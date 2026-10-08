"""Involute geometry the validator uses: the working centre distance of a shifted helical pair."""

import math

import pytest

from zenryx.contract.involute import inv, inv_inverse, working_centre_distance


def test_inv_and_its_inverse():
    alpha = math.radians(20)
    assert inv(alpha) == pytest.approx(math.tan(alpha) - alpha)
    assert inv_inverse(inv(alpha)) == pytest.approx(alpha, abs=1e-12)


def test_unshifted_pair_sits_at_the_reference_centre_distance():
    # mn 2, z 25/65, beta 20 deg: a = mn (z1 + z2) / (2 cos beta)
    a = working_centre_distance(25, 65, 2.0, math.radians(20), math.radians(20), 0.0, 0.0)
    assert a == pytest.approx(2.0 * 90 / (2 * math.cos(math.radians(20))), rel=1e-12)


def test_a_shifted_pair_matches_the_hand_calculation():
    # z 14/46, mn 1.75, alpha_n 20, beta 25, x 0.2 / -0.7299: worked by hand to 56.94 mm
    a = working_centre_distance(14, 46, 1.75, math.radians(20), math.radians(25), 0.2, -0.7299)
    assert a == pytest.approx(56.94, abs=0.02)
