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
    "ev_reducer_posed.json",
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
    ["ev_reducer_posed.json", "hofstetter2018_posed.json", "agri_ev_gearbox_posed.json"],
)
def test_a_posed_example_cannot_be_frozen_before_it_is_derived(name):
    spec, _ = load_and_validate(DATA / name)
    rules = {r.rule for r in validate(freeze(spec))}
    assert rules == {"stage.derived_needs_physics"}


def test_the_ev_reducer_carries_the_engineers_requirements():
    spec, _ = load_and_validate(DATA / "ev_reducer_posed.json")
    req = spec.requirement
    s1, s2 = req.stages
    assert (s1.z_pinion.value, s1.z_gear.value, s2.z_pinion.value, s2.z_gear.value) == (
        25,
        51,
        23,
        81,
    )
    # The gear data fix the ratio and the centre distances, so the contract states neither; a
    # paper's 7.184 and 83 / 125 mm verify the involute code (test_involute.py).
    assert req.total_ratio is None and req.ratio_tolerance is None
    assert s1.centre_distance is None and s2.centre_distance is None
    # The requirements are the engineer's; the helix angles are 30 deg on both stages (23:23).
    assert {s.helix_angle.provenance.kind for s in (s1, s2)} == {"engineer"}
    assert s2.helix_angle.value.to_canonical()[0] == pytest.approx(0.5235987756)
    # The packaging and the process were decided for the first loop (the engineer, 9 Oct 02:12).
    assert req.input_output_offset.provenance.kind == "engineer"
    assert req.input_output_offset.value.to_canonical() == (165.0, "mm")
    assert [a.id for a in spec.assumptions] == [
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
        "A8",
        "A11",
        "A12",
        "A13",
        "A14",
        "A15",
        "A16",
        "A17",
        "A18",
        "A19",
        "A21",
    ]
    # The input's sense of rotation sets the forces' directions (GBX-1); not given, so assumed.
    assert req.forward_rotation.provenance.assumption_id == "A21"
    # The layout's inputs are its gaps (the engineer, 9 Oct 00:06), assumed from Shigley's sketch.
    gaps = req.shaft_layout
    assert gaps.bearing_to_gear.value.to_canonical() == (12.7, "mm")
    assert gaps.behind_bearing.value.to_canonical() == (6.35, "mm")
    assert [e.provenance.assumption_id for e in (gaps.bearing_to_gear, gaps.behind_bearing)] == [
        "A13",
        "A14",
    ]
    assert gaps.gear_to_gear.provenance.assumption_id == "A15"
    # Behind a bearing where its shaft leaves: a seal and its seat; which ends leave (01:06).
    assert gaps.behind_bearing_sealed.value.to_canonical() == (11.0, "mm")
    assert [(e.shaft, e.side.value) for e in gaps.sealed_ends] == [
        ("input", "-z"),
        ("output", "-z"),
        ("output", "+z"),
    ]
    assert gaps.min_axial_clearance.provenance.assumption_id == "A18"
    assert gaps.min_radial_clearance.value.to_canonical() == (8.25, "mm")
    # One order-check speed, the duty's rated 6,000 rpm, named rather than copied.
    assert spec.limits.order_check_at.value == "rated"
    assert spec.limits.order_check_at.provenance.kind == "engineer"
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
    # Restating the paper's centre distance and ratio beside the full gear data: both redundant.
    data = json.loads((DATA / "agri_ev_gearbox_posed.json").read_text(encoding="utf-8"))
    req = data["requirement"]
    module = req["stages"][0]["normal_module"]  # a published entry of Table 1, as a template
    req["stages"][0]["centre_distance"] = {**module, "value": {"value": 57, "unit": "mm"}}
    req["total_ratio"] = {**module, "value": {"value": 12.37, "unit": "1"}}
    spec, refusals = load_and_validate(data)
    found = {(r.rule, r.entry) for r in refusals}
    assert found == {
        ("consistency.redundant", "requirement.stages[0].centre_distance"),
        ("consistency.redundant", "requirement.total_ratio"),
    }
