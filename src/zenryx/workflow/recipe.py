"""The final workflow's recipe (LOP-31): one versioned file of the agreed settings.

A setting changes only through the recipe, with a new version and the engineer's word (14 October
12:35: "ask me before including new settings"). Its environment holds only the loop's settings
(`LOOP_*`, `GUARD_*`); its optimiser arguments are passed on as they are.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FINAL = HERE / "recipes" / "final.json"


class Recipe(BaseModel):
    """The agreed settings of one workflow, and the contract they are run on."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    recipe: str = Field(min_length=1)
    version: int = Field(ge=1)
    agreed: str = Field(min_length=1)
    contract: str = Field(min_length=1)
    design: str = Field(min_length=1)
    budget_kg: float = Field(gt=0, lt=20)
    voxel_mm: float = Field(gt=0)
    optimiser_args: list[str] = Field(min_length=1)
    env: dict[str, str] = Field(min_length=1)

    @field_validator("env")
    @classmethod
    def _loop_settings_only(cls, env: dict[str, str]) -> dict[str, str]:
        bad = [k for k in env if not k.startswith(("LOOP_", "GUARD_"))]
        if bad:
            raise ValueError(f"the environment holds only LOOP_ and GUARD_ settings, not {bad}")
        return env

    def contract_path(self, root: Path = ROOT) -> Path:
        return root / self.contract


def fingerprint(data: bytes) -> str:
    """A file's fingerprint: the first 16 hex digits of its sha256."""
    return hashlib.sha256(data).hexdigest()[:16]


def load_recipe(path: Path = FINAL, root: Path = ROOT) -> tuple[Recipe, str]:
    """The recipe, checked, and its fingerprint. Refuses a recipe whose contract is missing."""
    data = path.read_bytes()
    recipe = Recipe.model_validate_json(data)
    if not recipe.contract_path(root).exists():
        raise ValueError(f"{path}: no contract at {recipe.contract}")
    return recipe, fingerprint(data)
