"""The snapshot the web UI reads (zenryx.api.snapshot, PLT-4)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from zenryx.api import snapshot
from zenryx.contract.canonical import spec_hash
from zenryx.contract.validate import load_and_validate

VALIDATE = Path(snapshot.__file__).parents[1] / "contract" / "validate.py"


@pytest.fixture(scope="module")
def payload() -> dict:
    return snapshot.build()


EXAMPLES = snapshot.ROOT / "checks" / "data" / "contracts"


@pytest.fixture(scope="module")
def every_example() -> dict:
    """All four example contracts, to check the snapshot's code on more than the main one."""
    files = [
        EXAMPLES / name
        for name in (
            "ivanov2018_posed.json",
            "hofstetter2018_posed.json",
            "agri_ev_gearbox_posed.json",
            "textbook_two_bearing_derived.json",
        )
    ]
    return snapshot.build(files)


def test_the_product_shows_one_contract_the_first(payload):
    assert [c["id"] for c in payload["contracts"]] == ["ivanov2018-l1"]


def test_a_contract_carries_its_hash_stage_and_verdict(every_example):
    for contract in every_example["contracts"]:
        spec, refusals = load_and_validate(snapshot.ROOT / contract["file"])
        assert contract["hash"] == spec_hash(spec)
        assert contract["stage"] == spec.stage
        assert contract["refusals"] == [r.model_dump() for r in refusals]


def test_only_the_derived_contract_is_ready_to_freeze(every_example):
    ready = {c["id"]: c["freeze"]["ready"] for c in every_example["contracts"]}
    assert ready == {
        "ivanov2018-l1": False,
        "hofstetter2018-l1-hpdc": False,
        "kim2024-agricultural-utv-l1-hpdc": False,
        "textbook-two-bearing": True,
    }
    posed = next(c for c in every_example["contracts"] if c["id"] == "ivanov2018-l1")
    assert {r["rule"] for r in posed["freeze"]["refusals"]} == {"stage.derived_needs_physics"}


def test_the_page_shows_ivanovs_gear_train_with_short_sources(payload):
    page = payload["contracts"][0]["page"]
    train = next(g for g in page["inputs"] if g["group"] == "Gear train")
    assert train["table"]["columns"] == ["Stage 1", "Stage 2"]
    teeth = next(r for r in train["table"]["rows"] if r["label"].startswith("Teeth"))
    assert [c["value"] for c in teeth["cells"]] == ["25 / 51", "23 / 81"]
    assert {c["source"] for c in teeth["cells"]} == {"Ivanov 2018"}
    widths = next(r for r in train["table"]["rows"] if r["label"].startswith("Face width"))
    assert widths["cells"][0]["value"] == "16.5 / 15.5 mm"
    helix = next(r for r in train["table"]["rows"] if r["label"] == "Helix angle")
    assert [c["source"] for c in helix["cells"]] == ["Ivanov 2018", "assumed"]


def test_the_page_computes_what_zenryx_can_and_names_the_rest(payload):
    calcs = {c["quantity"]: c for c in payload["contracts"][0]["page"]["calculations"]}
    assert calcs["Gear mesh check"]["status"] == "computed"
    assert "✗" not in calcs["Gear mesh check"]["result"]
    assert calcs["Shaft angle"]["result"].startswith("103.1°")
    assert "1,127 Hz" in calcs["Mesh frequencies"]["result"]
    for planned in ("Gear forces", "Bearing loads", "Bearing sizes"):
        assert calcs[planned]["status"] == "planned"
        assert calcs[planned]["method"] and calcs[planned]["by"]


def test_the_page_points_out_a_published_mode_on_a_mesh_frequency(payload):
    beat = payload["contracts"][0]["page"]["to_beat"]
    modes = next(b for b in beat if "mode" in b["quantity"])
    assert "fails order separation" in modes["note"]


def test_every_entry_is_in_words_with_its_provenance(every_example):
    for contract in every_example["contracts"]:
        raw = json.loads(contract["json"])
        for entry in contract["entries"]:
            assert entry["layer"] in snapshot.LAYERS
            assert entry["label"] and entry["group"] and entry["value"]
            assert entry["provenance"]["kind"] in {
                "published",
                "standard",
                "measured",
                "derived",
                "assumption",
                "engineer",
            }
            assert _at(raw, entry["path"]) is not None, entry["path"]


def test_a_torque_reads_by_its_kind_direction_and_shaft(every_example):
    contracts = every_example["contracts"]
    hofstetter = next(c for c in contracts if c["id"] == "hofstetter2018-l1-hpdc")
    torque = next(e for e in hofstetter["entries"] if e["path"] == "requirement.torques[0].torque")
    assert torque["label"] == "torque · nominal drive, input shaft"
    assert torque["value"] == "366 N·m"
    assert torque["canonical"] == "366000 N*mm"
    ratio = next(e for e in hofstetter["entries"] if e["path"] == "requirement.total_ratio")
    assert ratio["value"] == "9.32"


@pytest.mark.parametrize(
    ("number", "text"),
    [
        (3398400.0, "3398400"),  # 944 h in seconds: no exponent
        (277.50735, "277.507"),  # 2650 rpm in rad/s: six significant digits
        (0.3135, "0.3135"),
        (366000.0, "366000"),
        (2.66e-09, "2.66e-09"),  # a density in t/mm3 keeps its exponent
        (0.0, "0"),
        (-12.5, "-12.5"),
    ],
)
def test_numbers_read_as_an_engineer_writes_them(number, text):
    assert snapshot._num(number) == text


def test_the_records_are_empty_until_the_agent_and_judge_exist(payload):
    assert payload["records"] == {
        "campaigns": [],
        "episodes": [],
        "candidates": [],
        "evaluations": [],
        "decisions": [],
        "choices": [],
        "pairs": [],
        "snapshot_tasks": [],
        "preference_pairs": [],
    }


def test_every_validator_rule_has_its_words(payload):
    named = set(re.findall(r'rule="([a-z_.]+)"', VALIDATE.read_text(encoding="utf-8")))
    assert named
    assert {r["id"] for r in payload["rules"]} == named


def test_it_is_deterministic(payload):
    assert snapshot.text(snapshot.build()) == snapshot.text(payload)


def test_the_committed_copy_is_current(payload):
    """web/src/records/snapshot.json is what the UI bundles; rewrite it after a contract changes."""
    assert snapshot.OUT.read_text(encoding="utf-8") == snapshot.text(payload), (
        "stale: run uv run python -m zenryx.api.snapshot"
    )


def _at(node, path: str):
    for part in re.findall(r"[^.\[\]]+", path):
        node = node[int(part)] if isinstance(node, list) else node.get(part)
        if node is None:
            return None
    return node
