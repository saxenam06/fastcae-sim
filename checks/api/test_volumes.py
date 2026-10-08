"""The Contract page's result (PLT-8): the volumes of the product's contract, bundled for the UI."""

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


def test_every_part_is_in_one_layer(payload):
    solid = [layer for layer in payload["layers"] if layer["draw"] == "solid"]
    faces = sorted(f for layer in solid for f in layer["faces"])
    assert faces == list(range(payload["faces"]))
    assert [layer["id"] for layer in payload["layers"]] == [
        "gear",
        "shaft",
        "bearing",
        "carrier",
        "packaging",
        "design_space",
    ]


def test_the_design_space_is_the_packaging_less_what_is_kept_clear(payload):
    litres = {layer["id"]: layer["litres"] for layer in payload["layers"]}
    parts = litres["gear"] + litres["carrier"]
    assert 0 < litres["design_space"] < litres["packaging"] - parts


def test_each_mesh_is_fcmesh03(payload):
    for name, text in payload["meshes"].items():
        assert base64.b64decode(text)[:8] == b"FCMESH03", name
