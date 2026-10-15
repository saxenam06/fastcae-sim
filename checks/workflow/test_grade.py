"""The grade ported into zenryx (LOP-33): its lines, and its targets held to the contract."""

import json
import math
import os
import time

import pytest
from fixtures import fe_result, write

from zenryx.contract.validate import load_and_validate
from zenryx.workflow import grade as g
from zenryx.workflow.recipe import ROOT

CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"


@pytest.fixture(scope="module")
def lines():
    spec, _ = load_and_validate(CONTRACT)
    return g.lines_of(spec)


def test_the_targets_are_the_contracts_references() -> None:
    spec, _ = load_and_validate(CONTRACT)
    assert g.check_references(spec) == []


def test_a_rigid_turn_of_the_housing_is_no_misalignment(lines) -> None:
    still = g.grade(fe_result("a", seed=3), lines)
    turned = g.grade(fe_result("a", seed=3, rigid_turn=2e-3), lines)
    m = g.MISALIGNMENT
    assert math.isclose(turned["lines"][m]["ratio"], still["lines"][m]["ratio"], rel_tol=1e-9)


def test_the_shafts_lean_is_added(lines) -> None:
    row = g.grade(fe_result("a", seed=1, scale=0.0), lines)  # the housing does not move
    assert row["lines"][g.MISALIGNMENT]["ratio"] > 0.0  # the shafts' own bending alone


def test_each_line_passes_and_fails_on_its_own(lines) -> None:
    good = g.grade(fe_result("a", scale=0.01), lines)
    assert good["pass"], good["lines"]
    assert good["lines"]["displacement, peak drive"]["to_beat_um"] == 52.2
    assert "displacement, peak reverse" not in good["lines"]  # peak drive alone is graded
    for kwargs, line in (
        ({"mass_kg": 8.0}, "mass"),
        ({"modes_hz": (450.0, 900.0)}, "first mode"),
        ({"modes_hz": ()}, "first mode"),
        ({"clashes": ({"mode": 3, "order": "s1"},)}, "orders"),
    ):
        row = g.grade(fe_result("a", scale=0.01, **kwargs), lines)
        failed = [k for k, v in row["lines"].items() if not v["pass"]]
        assert failed == [line], (kwargs, failed)
        assert not row["pass"]
    soft = g.grade(fe_result("a", scale=50.0), lines)
    assert not soft["lines"]["displacement, peak drive"]["pass"]
    assert not soft["lines"][g.MISALIGNMENT]["pass"]


def test_grade_all_skips_a_result_older_than_its_build(tmp_path) -> None:
    write(tmp_path, "new.json", {})  # built, then judged: graded
    write(tmp_path, "fe_old.json", fe_result("old"))
    write(tmp_path, "fe_new.json", fe_result("new"))
    earlier = time.time() - 10
    os.utime(tmp_path / "new.json", (earlier, earlier))
    build = write(tmp_path, "old.json", {})
    later = time.time() + 10
    os.utime(build, (later, later))
    grades, stale = g.grade_all(tmp_path, CONTRACT)
    assert [r["stem"] for r in grades] == ["new"]
    assert stale == ["old"]
    assert json.loads((tmp_path / "grades.json").read_text()) == grades
    assert "PASS" in g.table(grades, stale) or "fail" in g.table(grades, stale)
