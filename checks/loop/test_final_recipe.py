"""The final workflow's recipe (LOP-31): one versioned file of the agreed settings, which
`zenryx.workflow` runs (LOP-33). Read as data, so nothing here imports the prototypes."""

import json
from pathlib import Path

from zenryx.workflow.recipe import FINAL, load_recipe

ROOT = Path(__file__).resolve().parents[2]
LOOP = ROOT / "prototypes" / "first_loop"
KNOWN = {
    "recipe",
    "version",
    "agreed",
    "contract",
    "design",
    "budget_kg",
    "voxel_mm",
    "optimiser_args",
    "env",
}


def recipe() -> dict:
    return json.loads(FINAL.read_text(encoding="utf-8"))


def test_its_keys_are_the_known_ones() -> None:
    assert set(recipe()) == KNOWN


def test_it_loads_and_names_a_contract_that_exists() -> None:
    r, sha = load_recipe(FINAL, ROOT)
    assert (ROOT / r.contract).exists() and len(sha) == 16


def test_its_environment_holds_only_the_loops_settings() -> None:
    env = recipe()["env"]
    assert env
    assert all(k.startswith(("LOOP_", "GUARD_")) for k in env)
    assert all(isinstance(v, str) for v in env.values())


def test_its_optimiser_arguments_are_words() -> None:
    args = recipe()["optimiser_args"]
    assert args and all(isinstance(a, str) for a in args)
    assert "--least-width" in args


def test_every_stage_its_engines_run_is_in_src() -> None:
    from zenryx.workflow.stage import STAGES

    assert set(STAGES) == {
        "layout",
        "optimise",
        "draw",
        "oiltight",
        "fe",
        "castable",
        "records",
        "process",
    }


def test_its_numbers() -> None:
    r = recipe()
    assert r["version"] >= 1
    assert 0 < r["budget_kg"] < 20
    assert r["voxel_mm"] in (4, 6, 10)
