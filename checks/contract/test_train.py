"""The gear train's ratio, speeds, mesh frequencies, axis angle and positions, and what overlaps
seen along the shafts (zenryx.contract.train)."""

import math

import pytest

from zenryx.contract.train import (
    axis_positions,
    end_view_overlap,
    mesh_frequency,
    ratio,
    shaft_speeds,
    stage_angle,
)

IVANOV = [(25, 51), (23, 81)]


def test_the_ratio_is_the_product_of_the_stages():
    assert ratio(IVANOV) == pytest.approx(7.184348, abs=1e-6)


def test_the_teeth_give_the_papers_ratios():
    # The papers verify the tool once, here, and not in every contract (the engineer, 8 Oct).
    # Ivanov 2018 states 7.184; Son et al. 2020 states 12.37 for Kim et al.'s gear train.
    assert ratio(IVANOV) == pytest.approx(7.184, rel=1e-3)
    assert ratio([(14, 46), (21, 79)]) == pytest.approx(12.37, rel=1e-3)


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


def test_the_axes_sit_at_their_centre_distances_and_the_offset():
    inp, mid, out = axis_positions(82.917, 125.037, 165.0)
    assert mid == (0.0, 0.0) and inp[1] == 0.0
    assert math.dist(inp, mid) == pytest.approx(82.917)
    assert math.dist(mid, out) == pytest.approx(125.037)
    assert math.dist(inp, out) == pytest.approx(165.0)


def test_ivanovs_stage_1_wheel_and_output_wheel_overlap_seen_along_the_shafts():
    # Tip diameters about 114.76 and 198.17 mm, the shafts 125.0 mm apart: 31 mm of overlap.
    _, mid, out = axis_positions(82.917, 125.037, 165.0)
    assert end_view_overlap(114.76 / 2, mid, 198.17 / 2, out) == pytest.approx(31.4, abs=0.1)
    # Two parts with room between them come out negative: the room.
    assert end_view_overlap(10.0, (0.0, 0.0), 10.0, (30.0, 0.0)) == pytest.approx(-10.0)
