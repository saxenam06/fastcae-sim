"""Synthetic FE results and engines for the workflow's checks: no GPU, no data/."""

from __future__ import annotations

import json
import random
from pathlib import Path

SEATS = [(s, side) for s in ("input", "intermediate", "output") for side in ("-z", "+z")]
SPANS = {"input": 120.0, "intermediate": 150.0, "output": 170.0}


def fe_result(
    stem: str,
    *,
    seed: int = 0,
    scale: float = 1.0,
    mass_kg: float = 5.0,
    modes_hz: tuple[float, ...] = (700.0, 900.0),
    clashes: tuple = (),
    rigid_turn: float = 0.0,
) -> dict:
    """An FE result in fe.py's format: each seat's displacement, rotation and own tilt by case.

    `rigid_turn` (rad about y) turns the whole housing rigidly on top: every seat's x moves with its
    z and every seat rotates alike, which the misalignment graded must not see."""
    rnd = random.Random(seed)
    cases = {}
    for case in ("peak drive", "peak reverse"):
        seats = {}
        for shaft, side in SEATS:
            z = (-1 if side == "-z" else 1) * SPANS[shaft] / 2
            u = [
                scale * rnd.uniform(-0.02, 0.02) + rigid_turn * z,
                scale * rnd.uniform(-0.02, 0.02),
                0.0,
            ]
            theta = [
                scale * rnd.uniform(-2e-4, 2e-4),
                scale * rnd.uniform(-2e-4, 2e-4) + rigid_turn,
                0.0,
            ]
            seats[f"{shaft} {side}"] = {
                "u": u,
                "theta": theta,
                "tilt_mrad": 1000 * (theta[0] ** 2 + theta[1] ** 2) ** 0.5,
                "displacement_mm": (u[0] ** 2 + u[1] ** 2 + u[2] ** 2) ** 0.5,
            }
        cases[case] = {"seats": seats, "shafts": {s: {"span_mm": SPANS[s]} for s in SPANS}}
    return {
        "stem": stem,
        "mass_kg": mass_kg,
        "cases": cases,
        "order_clashes": list(clashes),
        "modes_hz": list(modes_hz),
    }


def write(out: Path, name: str, data: dict) -> Path:
    path = out / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path
