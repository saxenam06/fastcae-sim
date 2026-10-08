"""The example contracts: each is accepted, current with its generator, and true to its sources."""

import importlib.util
import json
from pathlib import Path

import pytest

from zenryx.contract.canonical import freeze, spec_hash
from zenryx.contract.model import HousingDesignSpec
from zenryx.contract.validate import load_and_validate, validate

DATA = Path(__file__).parent.parent / "data" / "contracts"
NAMES = [
    "ivanov2018_posed.json",
    "hofstetter2018_posed.json",
    "agri_ev_gearbox_posed.json",
    "textbook_two_bearing_derived.json",
]


def generator():
    spec = importlib.util.spec_from_file_location("make_examples", DATA / "make_examples.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", NAMES)
def test_each_example_is_accepted(name):
    spec, refusals = load_and_validate(DATA / name)
    assert refusals == [], [r.model_dump() for r in refusals]
    assert spec is not None


@pytest.mark.parametrize("name", NAMES)
def test_each_example_is_current_with_its_generator(name):
    on_disk = json.loads((DATA / name).read_text(encoding="utf-8"))
    built = generator().EXAMPLES[name]()
    assert on_disk == built, f"{name} is stale: run checks/data/contracts/make_examples.py"


def test_a_derived_example_freezes_to_a_valid_task():
    spec, _ = load_and_validate(DATA / "textbook_two_bearing_derived.json")
    frozen = freeze(spec)
    assert validate(frozen) == []
    assert frozen.frozen_hash == spec_hash(frozen)


@pytest.mark.parametrize(
    "name",
    ["ivanov2018_posed.json", "hofstetter2018_posed.json", "agri_ev_gearbox_posed.json"],
)
def test_a_posed_example_cannot_be_frozen_before_it_is_derived(name):
    spec, _ = load_and_validate(DATA / name)
    rules = {r.rule for r in validate(freeze(spec))}
    assert rules == {"stage.derived_needs_physics"}


def test_ivanov_carries_its_gear_train_as_published():
    spec, _ = load_and_validate(DATA / "ivanov2018_posed.json")
    req = spec.requirement
    assert req.total_ratio.value.value == 7.184
    s1, s2 = req.stages
    assert (s1.z_pinion.value, s1.z_gear.value, s2.z_pinion.value, s2.z_gear.value) == (
        25,
        51,
        23,
        81,
    )
    assert (s1.centre_distance.value.value, s2.centre_distance.value.value) == (83, 125)
    assert s1.helix_angle.provenance.kind == "published"
    # Stage 2's helix angle is garbled in the copy read: recovered, so listed as an assumption.
    assert s2.helix_angle.provenance.assumption_id == "A7"
    # The packaging is the user's input, proposed and listed until the engineer sets it.
    assert req.input_output_offset.provenance.assumption_id == "A9"
    assert spec.manufacturing.process == "sand_casting"


def test_hofstetter_carries_table_2_as_published():
    spec, _ = load_and_validate(DATA / "hofstetter2018_posed.json")
    req = spec.requirement
    assert req.input_output_offset.value.to_canonical() == (165.0, "mm")
    assert req.total_ratio.value.value == 9.32
    nominal = [t for t in req.torques if t.kind == "nominal"][0]
    assert nominal.torque.value.to_canonical() == (366000.0, "N*mm")
    assert nominal.torque.provenance.kind == "published"
    assert "Table 2" in nominal.torque.provenance.citation
    assert [b.designation.value for b in req.bearings] == [
        "6206",
        "NU205-E",
        "32010",
        "32010",
        "6012",
        "6011",
    ]


def test_every_assumption_in_an_example_is_listed_and_labelled():
    for name in NAMES:
        data = json.loads((DATA / name).read_text(encoding="utf-8"))
        spec = HousingDesignSpec.model_validate(data)
        assert all(a.why for a in spec.assumptions)


def test_examples_hold_nothing_from_grc():
    for name in NAMES:
        text = (DATA / name).read_text(encoding="utf-8").lower()
        assert "grc" not in text
        assert "nrel" not in text


def test_breaking_an_example_is_refused():
    data = json.loads((DATA / "agri_ev_gearbox_posed.json").read_text(encoding="utf-8"))
    data["requirement"]["stages"][0]["z_gear"]["value"] = 50
    spec, refusals = load_and_validate(data)
    assert {"consistency.ratio", "consistency.centre_distance"} <= {r.rule for r in refusals}
