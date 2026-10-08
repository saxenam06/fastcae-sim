"""The layers of the contract load, and refuse what does not belong (spec §4)."""

import pytest
from builders import clone, minimal_posed, qty, standard
from pydantic import ValidationError

from zenryx.contract.model import HousingDesignSpec


def test_a_minimal_posed_contract_loads():
    spec = HousingDesignSpec.model_validate(minimal_posed())
    assert spec.stage == "posed"
    assert spec.requirement.style == "package"
    assert spec.interfaces is None
    assert spec.physics is None


def test_a_torque_names_its_shaft():
    data = clone(minimal_posed())
    data["requirement"]["torques"][0]["shaft"] = ""
    with pytest.raises(ValidationError, match="shaft"):
        HousingDesignSpec.model_validate(data)


def test_a_torque_states_its_kind():
    data = clone(minimal_posed())
    del data["requirement"]["torques"][0]["kind"]
    with pytest.raises(ValidationError, match="kind"):
        HousingDesignSpec.model_validate(data)


def test_a_gear_train_contract_needs_its_stages():
    data = clone(minimal_posed())
    data["requirement"]["style"] = "gear_train"
    with pytest.raises(ValidationError, match="gear_train"):
        HousingDesignSpec.model_validate(data)


def test_a_package_contract_needs_the_offset():
    data = clone(minimal_posed())
    del data["requirement"]["input_output_offset"]
    with pytest.raises(ValidationError, match="offset"):
        HousingDesignSpec.model_validate(data)


def test_a_box_space_needs_its_corners():
    data = clone(minimal_posed())
    data["requirement"]["installation_space"] = {"kind": "box"}
    with pytest.raises(ValidationError, match="box"):
        HousingDesignSpec.model_validate(data)


def test_die_casting_needs_pull_directions_and_draft():
    data = clone(minimal_posed())
    data["manufacturing"]["pull_directions"] = []
    with pytest.raises(ValidationError, match="pull"):
        HousingDesignSpec.model_validate(data)


def test_an_answer_at_the_root_is_refused():
    data = clone(minimal_posed())
    data["best_design"] = "housing_v3.step"
    with pytest.raises(ValidationError, match="Extra inputs"):
        HousingDesignSpec.model_validate(data)


def test_a_bare_number_is_not_a_value():
    data = clone(minimal_posed())
    data["requirement"]["total_ratio"]["value"] = 9.32
    with pytest.raises(ValidationError):
        HousingDesignSpec.model_validate(data)


def test_only_schema_version_0_1():
    data = clone(minimal_posed())
    data["schema_version"] = "0.2"
    with pytest.raises(ValidationError, match="schema_version"):
        HousingDesignSpec.model_validate(data)


def test_tilt_limits_name_a_bearing_type():
    data = clone(minimal_posed())
    data["limits"]["bearing_tilt"].append(
        {"bearing_type": "wobbly", "limit": standard(qty(1, "mrad"), "x")}
    )
    with pytest.raises(ValidationError, match="bearing_type"):
        HousingDesignSpec.model_validate(data)
