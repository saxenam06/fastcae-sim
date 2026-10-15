"""The final workflow's recipe (LOP-31): one versioned file of the agreed settings, which
`run_final.py` runs. Read as data, so nothing here imports the prototypes."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOOP = ROOT / "prototypes" / "first_loop"
RECIPE = LOOP / "recipes" / "final.json"
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
    return json.loads(RECIPE.read_text(encoding="utf-8"))


def test_its_keys_are_the_known_ones() -> None:
    assert set(recipe()) == KNOWN


def test_it_names_a_contract_that_exists() -> None:
    assert (ROOT / recipe()["contract"]).exists()


def test_its_environment_holds_only_the_loops_settings() -> None:
    env = recipe()["env"]
    assert env
    assert all(k.startswith(("LOOP_", "GUARD_")) for k in env)
    assert all(isinstance(v, str) for v in env.values())


def test_its_optimiser_arguments_are_words() -> None:
    args = recipe()["optimiser_args"]
    assert args and all(isinstance(a, str) for a in args)
    assert "--least-width" in args


def test_the_scripts_it_runs_exist() -> None:
    for name in (
        "run_final.py",
        "campaign_run.sh",
        "propose.py",
        "contract_layout.py",
        "setup_export.py",
    ):
        assert (LOOP / name).exists(), name


def test_its_numbers() -> None:
    r = recipe()
    assert r["version"] >= 1
    assert 0 < r["budget_kg"] < 20
    assert r["voxel_mm"] in (4, 6, 10)
