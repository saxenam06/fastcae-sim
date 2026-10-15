"""The final workflow's stages, gates, record and state (LOP-33), on fake engines.

No GPU, no data/."""

import json
from pathlib import Path

import pytest
from fixtures import fe_result, write

from zenryx.workflow import flow, run
from zenryx.workflow.recipe import FINAL, ROOT, Recipe, load_recipe

CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
MOUNTS = [{"name": f"mount-{i}"} for i in (1, 2, 3)]


class FakeEngines:
    """Writes each stage's files as the prototype's scripts do; `fail` names a stage that fails."""

    def __init__(
        self, out: Path, *, fail: str = "", missed: float = 0.9, mounts: int = 3, empty=True
    ):
        self.out, self.fail, self.missed, self.mounts, self.empty = out, fail, missed, mounts, empty
        self.calls: list[str] = []

    def layout(self, env, log):
        self.calls.append("layout")
        return 1 if self.fail == "layout" else 0

    def optimise(self, design, budget, voxel, args, env, log):
        self.calls.append("optimise")
        self.args = (budget, voxel, list(args), env.get("LOOP_VOXEL_SMOOTH"))
        if self.fail == "optimise":
            return 1, "", ""
        rec = {"binary": {"worst": self.missed, "beds": {"a": 0.5}}, "empty": self.empty}
        rec.update({"frozen_kg": 3.5, "budget_kg": 7.73, "voxel_mm": voxel, "least_kg": 1.0})
        write(self.out, f"run_{design}.json", rec)
        return 0, f"run_{design}", "settled at 120"

    def draw(self, run, design, env, log):
        self.calls.append("draw")
        if self.fail == "draw":
            return 1
        drawn = {"mounts_layout": MOUNTS, "mounts": MOUNTS[: self.mounts]}
        write(self.out, f"{design}.json", drawn)
        return 0

    def oiltight(self, design, env, log):
        self.calls.append("oiltight")
        write(self.out, f"oiltight_{design}.json", {"tight": True})
        return 0

    def judge(self, design, env, fe_log, cast_log):
        self.calls.append("judge")
        fe_log.write_text("[00:01] FE in all 42 s\n", encoding="utf-8")
        if self.fail == "fe":
            return 1, 0
        write(self.out, f"fe_{design}.json", fe_result(design, scale=0.01))
        return 0, 0

    def records(self, design, run, env, out):
        self.calls.append("records")

    def process(self, design, env, log):
        self.calls.append("process")


def propose(tmp_path, engines, run_stem=""):
    return flow.propose(
        "d1",
        budget=7.73,
        voxel=4,
        args=["--least-width", "8"],
        engines=engines,
        out=tmp_path,
        contract=CONTRACT,
        env={"LOOP_EXACT_WALLS": "1"},
        run=run_stem,
    )


def test_the_whole_flow_in_order(tmp_path) -> None:
    e = FakeEngines(tmp_path)
    rec = propose(tmp_path, e)
    assert e.calls == ["optimise", "draw", "oiltight", "judge", "records", "process"]
    assert [s["id"] for s in rec["steps"]] == [
        "setup",
        "optimise",
        "draw",
        "fe",
        "castable",
        "grade",
    ]
    assert rec["flow"]["id"] == "E" and rec["failed"] is None
    assert rec["grade"]["stem"] == "d1" and rec["grade"]["pass"]
    assert rec["steps"][2]["note"] == "oil-tight"
    assert "least walls drawn from the exact inside" in rec["steps"][2]["method"]
    assert rec["steps"][3]["note"] == "FE in all 42 s"
    assert json.loads((tmp_path / "flow_d1.json").read_text()) == rec
    assert (tmp_path / "grade_d1.log").read_text().strip()


def test_a_failed_optimisation_stops_the_flow(tmp_path) -> None:
    e = FakeEngines(tmp_path, fail="optimise")
    rec = propose(tmp_path, e)
    assert e.calls == ["optimise"] and rec["failed"] == "the optimisation failed"


def test_a_run_missing_its_lines_is_not_drawn(tmp_path) -> None:
    e = FakeEngines(tmp_path, missed=1.2)
    rec = propose(tmp_path, e)
    assert e.calls == ["optimise"]
    assert "1.20 x its lines" in rec["failed"] and not rec["steps"][-1]["ok"]


def test_a_reused_run_skips_the_gate_and_the_optimiser(tmp_path) -> None:
    e = FakeEngines(tmp_path, missed=1.2)
    write(tmp_path, "old_run.json", {"binary": {"worst": 1.5}, "seconds": 600, "voxel_mm": 4})
    rec = propose(tmp_path, e, run_stem="old_run")
    assert "optimise" not in e.calls and rec["failed"] is None
    assert rec["steps"][1]["note"] == "reused" and rec["steps"][1]["seconds"] == 600
    assert rec["flow"]["id"] == "B" and "oiltight" not in e.calls


def test_a_drawing_that_loses_a_mount_is_not_judged(tmp_path) -> None:
    e = FakeEngines(tmp_path, mounts=2)
    rec = propose(tmp_path, e)
    assert "judge" not in e.calls and "mount-3" in rec["failed"]


def test_a_failed_drawing_or_fe(tmp_path) -> None:
    e = FakeEngines(tmp_path, fail="draw")
    assert propose(tmp_path, e)["failed"] == "the drawing failed"
    e = FakeEngines(tmp_path / "x", fail="fe")
    (tmp_path / "x").mkdir()
    rec = propose(tmp_path / "x", e)
    assert rec["failed"] is None and "grade" not in [s["id"] for s in rec["steps"]]
    assert rec["grade"] is None


def test_the_recipe_is_read_and_checked() -> None:
    recipe, sha = load_recipe(FINAL)
    assert recipe.version >= 1 and len(sha) == 16 and "--least-width" in recipe.optimiser_args
    bad = recipe.model_dump() | {"env": {"PATH": "/x"}}
    with pytest.raises(ValueError):
        Recipe.model_validate(bad)


def test_run_final_runs_once_then_is_up_to_date(tmp_path) -> None:
    e = FakeEngines(tmp_path)
    first = run.run_final(e, out=tmp_path, design="d1", env={})
    assert e.calls[0] == "layout" and first["verdict"] == "passes every line"
    assert first["numbers"]["mass_kg"] == 5.0 and first["run"] == "run_d1"
    assert e.args[2] == load_recipe(FINAL)[0].optimiser_args and e.args[3] == "3"
    again = FakeEngines(tmp_path)
    assert "up_to_date" in run.run_final(again, out=tmp_path, env={}) and again.calls == []
    assert run.run_final(again, out=tmp_path, dry_run=True, force=True, env={})["dry_run"][0] == (
        "the optimisation"
    )
    redraw = FakeEngines(tmp_path)
    run.run_final(redraw, out=tmp_path, run="run_d1", design="d2", env={})
    assert redraw.calls[:2] == ["draw", "oiltight"]  # the layout is current: not rebuilt


def test_run_final_stops_when_the_layout_fails(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="layout failed"):
        run.run_final(FakeEngines(tmp_path, fail="layout"), out=tmp_path, env={})
