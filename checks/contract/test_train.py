"""The gear train's ratio, speeds, mesh frequencies and axis angle (zenryx.contract.train)."""

import pytest

from zenryx.contract.train import mesh_frequency, ratio, shaft_speeds, stage_angle

IVANOV = [(25, 51), (23, 81)]


def test_the_ratio_is_the_product_of_the_stages():
    assert ratio(IVANOV) == pytest.approx(7.184348, abs=1e-6)


def test_each_shaft_turns_at_the_input_speed_over_the_ratio_so_far():
    speeds = shaft_speeds(6000, IVANOV)
    assert speeds[1] == pytest.approx(6000 * 25 / 51)
    assert speeds[2] == pytest.approx(835.15, abs=0.01)  # Ivanov 2018 gives 835.19 rpm


def test_a_mesh_frequency_is_teeth_times_shaft_speed():
    assert mesh_frequency(25, 6000) == pytest.approx(2500.0)
    # Stage 2 at the 6,000 rpm cruise: the frequency Ivanov's first mode sits on (1,127 Hz).
    assert mesh_frequency(23, 6000 * 25 / 51) == pytest.approx(1127.45, abs=0.01)


@pytest.mark.parametrize(
    ("offset", "angle"),
    [(165.0, 103.12), (208.0, 180.0), (42.0, 0.0), (130.0, 74.30)],
)
def test_the_stage_angle_follows_from_the_offset(offset, angle):
    assert stage_angle(83.0, 125.0, offset) == pytest.approx(angle, abs=0.01)


@pytest.mark.parametrize("offset", [41.0, 208.5])
def test_an_offset_out_of_reach_is_refused(offset):
    with pytest.raises(ValueError, match="cannot reach"):
        stage_angle(83.0, 125.0, offset)
