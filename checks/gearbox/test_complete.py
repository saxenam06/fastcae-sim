"""GBX-4: completing a posed contract with the load tool's results, then freezing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from zenryx.contract.canonical import freeze, spec_hash
from zenryx.contract.validate import load_and_validate, validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.complete import complete, seat_name

CONTRACT = Path(__file__).parents[1] / "data" / "contracts" / "ev_reducer_posed.json"


@pytest.fixture(scope="module")
def posed():
    spec, refusals = load_and_validate(CONTRACT)
    assert refusals == []
    return spec


@pytest.fixture(scope="module")
def same_hand(posed):
    """The EV reducer with stage 2's pinion right-handed, so the intermediate shaft's two gears
    share a hand and their thrusts partly cancel (a variant, not the contract)."""
    req = posed.requirement
    s2 = req.stages[1]
    hand = s2.helix_hand_pinion.model_copy(update={"value": "right"})
    s2 = s2.model_copy(update={"helix_hand_pinion": hand})
    return posed.model_copy(
        update={"requirement": req.model_copy(update={"stages": [req.stages[0], s2]})}
    )


def test_the_contract_as_given_is_completed_or_says_which_seat_stops_it(posed):
    chain = complete_chain(posed)
    if chain.refused:
        with pytest.raises(ValueError, match="cannot be completed: intermediate:zpos"):
            complete(posed, chain)
    else:
        assert validate(complete(posed, chain)) == []


def test_a_completed_contract_is_accepted_and_freezes(same_hand):
    done = complete(same_hand)
    assert done.stage == "completed"
    assert validate(done) == []
    frozen = freeze(done)
    assert validate(frozen) == []
    assert frozen.frozen_hash == spec_hash(frozen)


def test_every_calculated_value_carries_the_tools_stamp(same_hand):
    done = complete(same_hand)
    stamp = done.interfaces.seats[0].centre.provenance
    assert stamp.tool == "zenryx.domains.gearbox.complete" and stamp.input_hash == spec_hash(
        same_hand
    )
    for case in done.physics.load_cases:
        for load in case.seat_loads:
            assert load.force.stamped()


def test_the_seats_are_the_selected_bearings_where_the_layout_puts_them(same_hand):
    chain = complete_chain(same_hand)
    done = complete(same_hand, chain)
    seats = {s.name: s for s in done.interfaces.seats}
    assert len(seats) == 6
    for (shaft, side), choice in chain.bearings.items():
        seat = seats[seat_name(shaft, side)]
        assert seat.diameter.value.value == pytest.approx(choice.bearing.D)
        assert seat.width.value.value == pytest.approx(choice.bearing.width)
        assert seat.bearing.value == choice.bearing.designation
        assert seat.bearing_type == choice.bearing.type
        x, y = chain.layout.stack(shaft).axis
        assert seat.centre.value.values == pytest.approx(
            (x, y, chain.layout.stack(shaft).bearing(side).centre)
        )


def test_each_load_case_carries_every_seats_force(same_hand):
    done = complete(same_hand)
    assert [c.name for c in done.physics.load_cases] == [
        "peak_drive",
        "peak_reverse",
        "peak_regeneration",
    ]
    for case in done.physics.load_cases:
        assert {s.seat for s in case.seat_loads} == {s.name for s in done.interfaces.seats}
        total = [sum(s.force.value.values[k] for s in case.seat_loads) for k in range(3)]
        assert total == pytest.approx([0.0, 0.0, 0.0], abs=1e-3)


def test_the_mesh_orders_are_the_pinions_teeth(same_hand):
    done = complete(same_hand)
    assert [(o.stage, o.shaft, o.order.value.value) for o in done.physics.mesh_orders] == [
        ("s1", "input", 25.0),
        ("s2", "intermediate", 23.0),
    ]


def test_only_a_posed_contract_is_completed(same_hand):
    with pytest.raises(ValueError, match="only a posed contract"):
        complete(complete(same_hand))
