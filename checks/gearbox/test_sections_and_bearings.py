"""GBX-3: the shaft sections and the bearing selection, and the round of steps 5 to 8.

Checked against the closed forms they rest on (the rating life, the equivalent loads, the
distortion-energy diameter, a simply supported beam's slope), and on the EV reducer: the round
settles, and every seat either has a bearing that lasts the contract's life or says why none does.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.bearings import (
    Bearing,
    catalogue,
    equivalent_load,
    life_hours,
    select,
)
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import GearLoad
from zenryx.domains.gearbox.loads import SeatLoad
from zenryx.domains.gearbox.shafts import _moments_along, _slope_vectors, _slopes, _strength

CONTRACT = Path(__file__).parents[1] / "data" / "contracts" / "ev_reducer_posed.json"


def _bearing(kind="deep_groove_ball", c=32500.0, c0=19000.0, e=None, y=None):
    return Bearing("x", kind, 40.0, 80.0, 18.0, c, c0, e, y, None, False, "test")


def test_the_rating_life_follows_the_catalogue_formula():
    # A ball bearing at half its rating: (C/P)^3 = 8 million revolutions; at 1,000 rpm, 133.3 h.
    ball = _bearing()
    assert life_hours(ball, 16250.0, 1000.0) == pytest.approx(8e6 / 60000.0)
    # A roller bearing's exponent is 10/3.
    roller = _bearing("cylindrical_roller")
    assert life_hours(roller, 16250.0, 1000.0) == pytest.approx(2 ** (10 / 3) * 1e6 / 60000.0)


def test_the_equivalent_load_follows_the_catalogue_rules():
    ball = _bearing()
    assert equivalent_load(ball, 5000.0, 500.0) == pytest.approx(5000.0)  # Fa/Fr under e
    # Fa/C0 = 532/19000 = 0.028: e 0.22, Y 1.99 (Shigley Table 11-1); Fa/Fr = 0.53 > e.
    assert equivalent_load(ball, 1000.0, 532.0) == pytest.approx(0.56 * 1000 + 1.99 * 532)
    tapered = _bearing("tapered_roller", 61600.0, 68000.0, e=0.37, y=1.6)
    assert equivalent_load(tapered, 5000.0, 1000.0) == pytest.approx(5000.0)
    assert equivalent_load(tapered, 5000.0, 4000.0) == pytest.approx(0.4 * 5000 + 1.6 * 4000)
    assert equivalent_load(_bearing("cylindrical_roller"), 5000.0, 4000.0) == 5000.0


def test_the_selection_takes_the_smallest_bearing_that_fits_and_lasts():
    choice = select("deep_groove_ball", 30.0, 3000.0, 0.0, 3000.0, 944.0)
    assert choice.bearing.d >= 30.0 and choice.life >= 944.0
    lasting = [
        b
        for b in catalogue()
        if b.type == "deep_groove_ball"
        and b.d >= 30.0
        and life_hours(b, equivalent_load(b, 3000.0, 0.0), 3000.0) >= 944.0
    ]
    assert min(b.D for b in lasting) == choice.bearing.D


def test_a_seat_no_bearing_serves_is_refused_with_its_loads():
    with pytest.raises(ValueError, match="no deep_groove_ball bearing"):
        select("deep_groove_ball", 30.0, 400_000.0, 0.0, 3000.0, 944.0)


def test_the_strength_diameter_is_the_distortion_energy_one():
    # Shigley Ch. 7: d = (32 n / (pi Sy) sqrt(M^2 + 0.75 T^2))^(1/3).
    n, sy, m, t = 2.0, 590.0, 200_000.0, 150_000.0
    expected = (32 * n / (math.pi * sy) * math.sqrt(m**2 + 0.75 * t**2)) ** (1 / 3)
    assert _strength(n, sy, m, t) == pytest.approx(expected)


def test_the_slope_of_a_centrally_loaded_beam():
    """A point load P at the middle of a simply supported span L: the slope at each support is
    P·L²/(16·E·I)."""
    p, span, ei = 1000.0, 120.0, 210_000.0 * math.pi * 30.0**4 / 64
    load = GearLoad("s", "gear", (0.0, 0.0), (0.0, 0.0), (p, 0.0, 0.0), (0.0, 0.0, 0.0))
    support = SeatLoad("s", "-z", 0.0, (p / 2, 0.0, 0.0), p / 2, 0.0)
    points = [span * i / 399 for i in range(400)]
    moments = _moments_along(points, 0.0, span, support, [(load, span / 2)])
    slopes = _slopes(0.0, span, moments, ei)
    assert slopes[0] == pytest.approx(p * span**2 / (16 * ei), rel=2e-3)
    assert slopes[-1] == pytest.approx(p * span**2 / (16 * ei), rel=2e-3)
    # As vectors: the shaft bows towards the load (+x), so at the -z support its axis leans
    # towards +x going along +z, and at the +z support back towards -x.
    lean = _slope_vectors(0.0, span, moments, ei)
    assert lean[0][0] == pytest.approx(p * span**2 / (16 * ei), rel=2e-3)
    assert lean[-1][0] == pytest.approx(-p * span**2 / (16 * ei), rel=2e-3)
    assert lean[0][1] == pytest.approx(0.0, abs=1e-12)


def test_the_chain_keeps_each_bearings_lean_per_case(chain):
    """Every shaft's section carries, for every load case, the shaft's lean at both bearings, and
    the worst lean's size is the worst slope the stiffening loop measured."""
    for s in chain.sections:
        assert set(s.lean_at_bearing) == {c.name for c in chain.forces}
        for side in ("-z", "+z"):
            worst = max(math.hypot(*v[side]) for v in s.lean_at_bearing.values())
            assert worst == pytest.approx(s.slope_at_bearing[side], rel=1e-9)


@pytest.fixture(scope="module")
def chain():
    spec, refusals = load_and_validate(CONTRACT)
    assert refusals == []
    return complete_chain(spec)


def test_the_round_settles(chain):
    assert 1 < chain.passes <= 8


def test_every_seat_has_a_bearing_that_lasts_or_says_why_not(chain):
    seats = {(s.shaft, s.side) for s in chain.loads[0].seats}
    assert seats == set(chain.bearings) | set(chain.refused)
    for choice in chain.bearings.values():
        assert choice.life >= 944.0
        assert choice.bearing.d >= choice.bore_needed - 1e-9
    for why in chain.refused.values():
        assert "lasts 944 h" in why


def test_the_layout_uses_the_selected_bearings(chain):
    for (shaft, side), choice in chain.bearings.items():
        part = chain.layout.stack(shaft).bearing(side)
        assert part.width == pytest.approx(choice.bearing.width)
        assert part.diameter == pytest.approx(choice.bearing.D)


def test_the_differentials_hubs_set_the_output_bores(chain):
    output = next(s for s in chain.sections if s.shaft == "output")
    assert output.bore_needed == {"-z": 45.0, "+z": 45.0}
    for side in ("-z", "+z"):
        if ("output", side) in chain.bearings:
            assert chain.bearings[("output", side)].bearing.d >= 45.0
