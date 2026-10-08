"""Canonical serialisation and the hash: the same content always gives the same hash (spec §6)."""

from builders import clone, minimal_posed

from zenryx.contract.canonical import canonical_json, freeze, spec_hash
from zenryx.contract.model import HousingDesignSpec


def load(data):
    return HousingDesignSpec.model_validate(data)


def test_key_order_does_not_change_the_hash():
    data = minimal_posed()
    reordered = dict(reversed(list(clone(data).items())))
    assert spec_hash(load(data)) == spec_hash(load(reordered))


def test_a_round_trip_through_json_keeps_the_hash():
    spec = load(minimal_posed())
    again = HousingDesignSpec.model_validate_json(spec.model_dump_json())
    assert spec_hash(again) == spec_hash(spec)


def test_any_changed_value_changes_the_hash():
    data = minimal_posed()
    changed = clone(data)
    changed["requirement"]["torques"][0]["torque"]["value"]["value"] = 367
    assert spec_hash(load(data)) != spec_hash(load(changed))


def test_the_same_quantity_in_another_unit_has_the_same_hash():
    data = minimal_posed()
    other = clone(data)
    other["requirement"]["torques"][0]["torque"]["value"] = {"value": 366000, "unit": "N·mm"}
    assert spec_hash(load(data)) == spec_hash(load(other))


def test_conversion_noise_does_not_change_the_hash():
    data = minimal_posed()
    other = clone(data)
    card = other["manufacturing"]["material"]
    card["youngs_modulus"]["value"] = {"value": 70930, "unit": "MPa"}
    assert spec_hash(load(data)) == spec_hash(load(other))


def test_freezing_stamps_the_stage_and_the_hash():
    spec = load(minimal_posed())
    frozen = freeze(spec)
    assert frozen.stage == "frozen"
    assert frozen.frozen_hash == spec_hash(frozen)
    assert frozen.frozen_hash.startswith("sha256:")


def test_the_hash_does_not_include_itself():
    frozen = freeze(load(minimal_posed()))
    assert "frozen_hash" not in canonical_json(frozen)
