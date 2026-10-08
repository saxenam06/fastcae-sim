"""The validator: accepts a sound contract, refuses each fault with its rule (spec §7)."""

from builders import (
    assumed,
    clone,
    derived,
    gear_train_posed,
    minimal_posed,
    published,
    qty,
    two_bearing_derived,
    vec,
)

from zenryx.contract.canonical import freeze
from zenryx.contract.model import HousingDesignSpec
from zenryx.contract.validate import load_and_validate, validate


def rules(data):
    spec, refusals = load_and_validate(data)
    return {r.rule for r in refusals}


def test_minimal_posed_contract_is_accepted():
    assert rules(minimal_posed()) == set()


def test_a_gear_train_contract_is_accepted():
    assert rules(gear_train_posed()) == set()


def test_a_derived_contract_is_accepted():
    assert rules(two_bearing_derived()) == set()


def test_a_schema_fault_comes_back_as_a_refusal():
    data = minimal_posed()
    data["requirement"]["torques"][0]["torque"]["value"] = {"value": 366}
    spec, refusals = load_and_validate(data)
    assert spec is None
    assert refusals and all(r.rule == "schema" for r in refusals)
    assert any("torque" in r.entry for r in refusals)


def test_an_assumption_must_be_listed():
    data = minimal_posed()
    data["requirement"]["installation_space"]["clearance"] = assumed(qty(20, "mm"), "A9")
    assert "provenance.assumption_listed" in rules(data)


def test_a_value_in_the_wrong_dimension_is_refused():
    data = minimal_posed()
    data["requirement"]["torques"][0]["torque"] = published(qty(366, "mm"))
    assert "consistency.dimension" in rules(data)


def test_stage_rules():
    # a posed contract carries no physics cases yet
    data = two_bearing_derived()
    data["stage"] = "posed"
    assert "stage.posed" in rules(data)
    # a derived contract needs interfaces and physics
    data = two_bearing_derived()
    del data["physics"]
    assert "stage.derived_needs_physics" in rules(data)
    # physics values are derived by their tool, never typed
    data = two_bearing_derived()
    data["physics"]["load_cases"][0]["seat_loads"][0]["force"] = published(vec(0, 5000, 0, "N"))
    assert "stage.physics_is_derived" in rules(data)


def test_a_frozen_contract_carries_its_own_hash():
    spec = HousingDesignSpec.model_validate(two_bearing_derived())
    frozen = freeze(spec)
    assert validate(frozen) == []
    tampered = frozen.model_copy(update={"frozen_hash": "sha256:" + "f" * 64})
    assert {r.rule for r in validate(tampered)} == {"stage.frozen_hash"}
    unfrozen = spec.model_copy(update={"frozen_hash": frozen.frozen_hash})
    assert "stage.frozen_hash" in {r.rule for r in validate(unfrozen)}


def test_the_stages_must_give_the_total_ratio():
    data = gear_train_posed()
    data["requirement"]["stages"][1]["z_gear"]["value"] = 90
    assert "consistency.ratio" in rules(data)


def test_each_centre_distance_must_follow_from_its_gears():
    data = gear_train_posed()
    data["requirement"]["stages"][0]["centre_distance"] = published(qty(60, "mm"))
    assert "consistency.centre_distance" in rules(data)


def test_the_two_stages_must_reach_the_offset():
    data = gear_train_posed()
    data["requirement"]["input_output_offset"] = published(qty(200, "mm"))
    assert "consistency.offset" in rules(data)


def test_a_seat_must_lie_inside_the_installation_space():
    data = two_bearing_derived()
    data["interfaces"]["seats"][1]["centre"] = derived(vec(0, 0, 500, "mm"))
    assert "consistency.seat_inside_space" in rules(data)


def test_power_and_torque_must_agree():
    data = gear_train_posed()
    data["requirement"]["torques"][0]["torque"] = published(qty(40, "N·m"))
    assert "consistency.power" in rules(data)


def test_interface_names_are_unique():
    data = two_bearing_derived()
    data["interfaces"]["seats"][1]["name"] = data["interfaces"]["seats"][0]["name"]
    assert "consistency.unique_names" in rules(data)


def test_a_seat_load_names_an_existing_seat():
    data = two_bearing_derived()
    data["physics"]["load_cases"][0]["seat_loads"][0]["seat"] = "nowhere"
    assert "consistency.seat_reference" in rules(data)


def test_an_axis_is_a_unit_vector():
    data = two_bearing_derived()
    data["interfaces"]["seats"][0]["axis"] = derived(vec(0, 0, 2, "1"))
    assert "consistency.unit_vector" in rules(data)


def test_a_bearing_must_fit_its_seat():
    data = two_bearing_derived()
    data["requirement"]["bearings"][0]["outer_diameter"] = published(qty(72, "mm"))
    assert "consistency.bearing_seat" in rules(data)


def test_a_position_must_be_a_vector():
    data = two_bearing_derived()
    data["interfaces"]["seats"][0]["centre"] = derived(qty(0, "mm"))
    assert "consistency.shape" in rules(data)


def test_a_box_corner_given_as_a_number_is_refused_not_a_crash():
    data = two_bearing_derived()
    data["requirement"]["installation_space"]["box_min"] = published(qty(-100, "mm"))
    assert "consistency.shape" in rules(data)


def test_a_scalar_must_not_be_a_vector():
    data = minimal_posed()
    data["requirement"]["input_output_offset"] = published(vec(165, 0, 0, "mm"))
    assert "consistency.shape" in rules(data)


def test_every_bearing_type_has_a_tilt_limit():
    data = two_bearing_derived()
    data["requirement"]["bearings"][0]["type"] = "spherical_roller"
    assert "consistency.tilt_limit" in rules(data)


def test_refusals_name_the_entry():
    data = gear_train_posed()
    data["requirement"]["stages"][0]["centre_distance"] = published(qty(60, "mm"))
    spec, refusals = load_and_validate(data)
    found = [r for r in refusals if r.rule == "consistency.centre_distance"]
    assert found and found[0].entry == "requirement.stages[0].centre_distance"
    assert "mm" in found[0].reason


def test_clone_keeps_builders_independent():
    a = minimal_posed()
    b = clone(a)
    b["task"]["id"] = "other"
    assert a["task"]["id"] == "test-minimal"
