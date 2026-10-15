"""The housing's set-up for the rib-direction field (LOP-34; a prototype: nothing in `src/` imports
it; outputs in `data/rib_housing/`).

Everything here is the product's own, called as the final recipe calls it
(`src/zenryx/workflow/recipes/final.json`): the layout record from the contract
(`housing.layout.write`), the voxel model (`housing.setup.build`, `housing.voxels.Voxels`: 4 mm
cubes, the fixed shell and interfaces, the design space as columns along the pull, the rigid
couplings, the peak drive, every seat's tilt and bed measure with its line at 1/1.5). What changes
is only how the free cubes are filled (`model.py`, `field.py`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "data" / "rib_housing"
CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
RECIPE = ROOT / "src" / "zenryx" / "workflow" / "recipes" / "final.json"


def recipe() -> dict:
    return json.loads(RECIPE.read_text(encoding="utf-8"))


def layout(out: Path = OUT) -> dict:
    """The layout record from the contract, by the product's own stage (written once)."""
    from zenryx.domains.gearbox.housing import layout as lay

    out.mkdir(parents=True, exist_ok=True)
    path = out / "contract.json"
    if not path.exists():
        lay.write(CONTRACT, out)
    return json.loads(path.read_text(encoding="utf-8"))


def product_model(voxel: float | None = None, out: Path = OUT):
    """The product's voxel model, built as `housing.optimise.run` builds it with the final recipe's
    arguments. Returns (Voxels, the model dict)."""
    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.housing import optimise as opt
    from zenryx.domains.gearbox.housing.setup import build
    from zenryx.domains.gearbox.housing.voxels import Voxels
    from zenryx.workflow.grade import GRADED_CASES, REFERENCE

    rec = recipe()
    voxel = float(voxel or rec["voxel_mm"])
    a = opt.parse(rec["optimiser_args"])
    env = rec["env"]
    spec, refusals = load_and_validate(CONTRACT)
    if spec is None:
        raise ValueError(refusals)
    lay = layout(out)
    model = build(lay, spec, voxel, a.band, a.height_field)
    model.update(
        cases=opt.CASES,
        safety=a.safety,
        least_height_mm=float(env["LOOP_LEAST_MEMBER"]),
        least_width_mm=a.least_width,
        beds_mm={c: REFERENCE[c] / 1000.0 for c in opt.CASES if c in GRADED_CASES},
        modes={"margin": a.modes, "count": 14, "first": a.first_mode, "first_margin": 0.0},
        max_member={"mm": a.max_member, "alpha": opt.MEMBER_ALPHA,
                    "radius_vox": a.max_member / 0.849 / voxel, "p": float(env["LOOP_MEMBER_P"])},
    )
    model["budget_kg"] = float(rec["budget_kg"])
    return Voxels(model), model


def column_groups(vox) -> list[dict]:
    """The design columns grouped by the product's layer (a half and the run along the pull that the
    column belongs to), each group's columns, their plan centres (mm) and its plan box."""
    from zenryx.domains.gearbox.housing.setup import height_columns

    m = vox.model
    col, pos, pts, layer = height_columns(m["kind"], np.asarray(m["n"]), m["k_split"], vox.elem, vox.free_e)
    lo, h = np.asarray(m["lo"], float), float(m["h"])
    xy = lo[:2] + (pts + 0.5) * h
    groups = []
    for lay in np.unique(layer):
        cols = np.flatnonzero(layer == lay)
        half = "cover" if lay // 10_000 else "motor_side"
        groups.append(
            {
                "name": f"{half}_run{int(lay % 10_000)}",
                "layer": int(lay),
                "half": half,
                "cols": cols,
                "xy": xy[cols],
                "ij": pts[cols].astype(int),
                "lo": xy[cols].min(axis=0),
                "hi": xy[cols].max(axis=0),
            }
        )
    return groups
