"""Entries: every value carries its provenance, authority and kind (spec §3)."""

import pytest
from pydantic import ValidationError

from zenryx.contract.entry import Entry, Provenance
from zenryx.contract.units import Quantity


def q(text):
    return Quantity.parse(text)


PUBLISHED = Provenance(kind="published", citation="Hofstetter et al. 2018, Table 2")
STAMP = Provenance(
    kind="derived", tool="frontend", tool_version="0.1", input_hash="sha256:" + "0" * 64
)


def test_published_entry_needs_a_citation():
    with pytest.raises(ValidationError, match="citation"):
        Provenance(kind="published")
    entry = Entry(
        value=q("366 N·m"), provenance=PUBLISHED, authority="engineer_locked", kind="hard"
    )
    assert entry.value == q("366 N·m")


def test_standard_and_measured_need_a_citation():
    with pytest.raises(ValidationError, match="citation"):
        Provenance(kind="standard")
    with pytest.raises(ValidationError, match="citation"):
        Provenance(kind="measured")


def test_derived_needs_its_stamp():
    with pytest.raises(ValidationError, match="tool"):
        Provenance(kind="derived", tool="frontend")
    entry = Entry(value=q("5.07 kN"), provenance=STAMP, authority="engineer_locked", kind="derived")
    assert entry.stamped()


def test_assumption_needs_its_id():
    with pytest.raises(ValidationError, match="assumption_id"):
        Provenance(kind="assumption")
    assert Provenance(kind="assumption", assumption_id="A1").assumption_id == "A1"


def test_engineer_needs_who_and_when():
    with pytest.raises(ValidationError, match="who"):
        Provenance(kind="engineer")
    Provenance(kind="engineer", who="the engineer", when="2026-10-08 02:02")


def test_derived_kind_and_derived_provenance_go_together():
    with pytest.raises(ValidationError, match="derived"):
        Entry(value=q("1 kN"), provenance=PUBLISHED, authority="engineer_locked", kind="derived")
    with pytest.raises(ValidationError, match="derived"):
        Entry(value=q("1 kN"), provenance=STAMP, authority="engineer_locked", kind="hard")


def test_agent_bounded_needs_bounds_inside_its_range():
    with pytest.raises(ValidationError, match="bounds"):
        Entry(value=q("10 mm"), provenance=PUBLISHED, authority="agent_bounded", kind="soft")
    Entry(
        value=q("10 mm"),
        provenance=PUBLISHED,
        authority="agent_bounded",
        kind="soft",
        bounds=(q("5 mm"), q("20 mm")),
    )
    with pytest.raises(ValidationError, match="outside its bounds"):
        Entry(
            value=q("30 mm"),
            provenance=PUBLISHED,
            authority="agent_bounded",
            kind="soft",
            bounds=(q("5 mm"), q("20 mm")),
        )


def test_an_extra_field_is_refused():
    with pytest.raises(ValidationError, match="Extra inputs"):
        Entry(
            value=q("10 mm"),
            provenance=PUBLISHED,
            authority="engineer_locked",
            kind="hard",
            result="smuggled answer",
        )


def test_text_values_are_allowed_for_choices():
    entry = Entry(value="20MnCr5", provenance=PUBLISHED, authority="engineer_locked", kind="hard")
    assert entry.value == "20MnCr5"
