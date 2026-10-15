"""The Contract page's result (PLT-8, GBX-5): the elements of the product's contract, the agent's
hypothesis and what the optimiser is given, bundled for the UI."""

from __future__ import annotations

import base64

import pytest

from zenryx.api import volumes


@pytest.fixture(scope="module")
def payload() -> dict:
    return volumes.build()


def test_the_committed_copy_is_current(payload):
    """web/src/records/volumes.json is what the UI bundles; rewrite it after a contract changes."""
    assert volumes.OUT.read_text(encoding="utf-8") == volumes.text(payload), (
        "stale: run uv run python -m zenryx.api.volumes"
    )


def test_three_groups_each_from_those_above(payload):
    """The contract, what the agent decides, what the optimiser is given (the engineer, 14:00)."""
    assert [g["id"] for g in payload["groups"]] == ["contract", "hypothesis", "given"]
    by_group = {}
    for layer in payload["layers"]:
        by_group.setdefault(layer["group"], []).append(layer["id"])
    assert by_group == {
        "contract": ["gear", "shaft", "bearing", "carrier", "mount", "packaging"],
        "hypothesis": ["split", "shell", "bolt"],
        "given": ["design_space"],
    }
    labels = [r["label"] for r in payload["hypothesis"]]
    assert labels == ["Split", "Inside", "Wall", "Flange", "Bolts"]


def test_every_solid_is_in_one_layer(payload):
    faces = sorted(f for layer in payload["layers"] for f in layer["faces"])
    assert faces == list(range(payload["faces"]))
    for layer in payload["layers"]:
        for key in layer["ghosts"]:
            assert key in payload["meshes"], (layer["id"], key)


def test_the_design_space_is_the_packaging_less_every_element(payload):
    litres = {layer["id"]: layer["litres"] for layer in payload["layers"]}
    kept = litres["gear"] + litres["carrier"] + litres["shell"] + litres["mount"] + litres["bolt"]
    assert 0 < litres["design_space"] < litres["packaging"] - kept


def test_each_mesh_is_fcmesh03(payload):
    for name, text in payload["meshes"].items():
        assert base64.b64decode(text)[:8] == b"FCMESH03", name
