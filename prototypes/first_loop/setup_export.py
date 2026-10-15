"""PROTOTYPE (LOP-17, GBX-5) - what the optimiser is given, for the Contract page's 3D view.

The voxel model's own masks (`topo_free.build_free` on the contract's layout, `contract_layout.py`,
which zenryx's `spaces` writes) as layers of cell faces, drawn by the renderer's voxel layers in
place of the exact volumes when the page's switch says so. Each layer is the boundary of a mask: a
cell face wherever a cell of the mask meets one outside it. So the page shows exactly what the
optimiser holds fixed, keeps out of and may fill, at its own 6 mm voxels, element by element: each
layer names the chip (the element) it belongs to (the engineer, 10 October 13:47-14:00: the
elements are the keep-out volumes; one shell; three groups).

Writes web/src/records/setup.json (git-ignored, as the Designs page's records are):
{schema, source, voxel_mm, grid: {size, shape, origin}, layers: [{id, chip, label, colour, alpha,
faces (base64 little-endian uint32: cell << 3 | direction, the renderer's packing), cells, litres,
note}], hypothesis: [{label, value}] (the run's own choices: the route, the mass budget)}.

Run after contract_layout.py: .venv/Scripts/python.exe prototypes/first_loop/setup_export.py [voxel mm]
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from topo import inside  # noqa: E402
from topo_free import build_free  # noqa: E402

TARGET = ROOT / "web" / "src" / "records" / "setup.json"


def faces_of(mask: np.ndarray) -> np.ndarray:
    """Every boundary face of a mask on the grid: (cell << 3) | direction, direction = axis * 2 +
    (0 toward +axis, 1 toward -axis), the renderer's packing (`VOXEL_VERTEX_SHADER`)."""
    n = mask.shape
    codes = []
    cell = np.arange(int(np.prod(n)), dtype=np.uint64).reshape(n)
    for axis in range(3):
        for side, direction in ((1, axis * 2), (-1, axis * 2 + 1)):
            neighbour = np.zeros_like(mask)
            src = [slice(None)] * 3
            dst = [slice(None)] * 3
            if side > 0:
                dst[axis], src[axis] = slice(0, n[axis] - 1), slice(1, n[axis])
            else:
                dst[axis], src[axis] = slice(1, n[axis]), slice(0, n[axis] - 1)
            neighbour[tuple(dst)] = mask[tuple(src)]
            on = mask & ~neighbour
            codes.append((cell[on] << np.uint64(3)) | np.uint64(direction))
    return np.concatenate(codes).astype(np.uint32)


def turned(mask: np.ndarray) -> np.ndarray:
    """A mask in the viewer's frame: the Contract page turns the picture (x, y, z) -> (x, z, -y)
    (`zenryx.api.volumes.VIEW`), which takes cells to cells: the grid's axes swapped and one
    flipped. The cell (i, j, k) goes to (i, k, n_y - 1 - j)."""
    return np.ascontiguousarray(np.transpose(mask, (0, 2, 1))[:, :, ::-1])


def main(h: float = 6.0, budget: float = 7.73, route: str = "split") -> Path:
    model = build_free(h, layout="contract", band=None, joint="bolts", skin=4.0, cavity="cup", penalty_ramp=0, route=route, flange=True)
    n = tuple(int(v) for v in model["n"])
    m = {k: turned(np.asarray(v).reshape(n)) for k, v in model["masks"].items()}
    ks = int(model["k_split"])
    # The split's cells where the halves meet: the inside out to the bolts' bosses (the contract's
    # joint outline), a layer whose lower faces (toward the viewer's -y) lie in the split plane.
    lo = np.asarray(model["lo"], float)
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    gx, gy = np.meshgrid(xc, yc, indexing="ij")
    joint = inside(np.asarray(model["info"]["joint_outline"]), gx.ravel(), gy.ravel()).reshape(n[0], n[1])
    plan = np.zeros(n, bool)
    plan[:, :, ks] = joint  # in the model's frame (i, j, k), then turned as the masks are
    split = turned(plan) & m["pack"]
    split_faces = np.array([c for c in faces_of(split) if c & 7 == 3], dtype=np.uint32)  # their -y faces only
    skin = model["skin"]
    # Each voxel layer under the chip of the element it stands for (the Contract page's ids, as
    # zenryx.api.volumes writes them), in that element's colour, and by kind (metal held fixed,
    # kept out, free, a plane): (id, chip, kind, label, colour, alpha, mask or faces, note).
    rows = [
        ("shaft_exits", "shaft", "kept_out", "Exits", (0.45, 0.47, 0.52), 0.22, m["clear_exits"],
         "kept out: each seal's bore, 1 mm into the housing, and the half-shafts' joints"),
        ("mounts", "mount", "fixed", "Mounts", (0.15, 0.58, 0.62), 1.0, m["mounts"], "held fixed, solid"),
        ("brackets", "mount", "kept_out", "Brackets", (0.15, 0.58, 0.62), 0.22, m["clear_brackets"],
         "kept out: the vehicle's bracket and bolt beyond each mount's faces"),
        ("split_plane", "split", "plane", "Split", (0.60, 0.30, 0.85), 0.55, split_faces,
         "the voxel faces in the split plane, where the halves meet"),
        ("shell_wall", "shell", "fixed", "Wall", (0.70, 0.72, 0.76), 0.40, m["wall"] | m["seats"],
         f"held fixed: a voxel round the inside standing for the {skin['wall_mm']:g} mm wall (its mass x{skin['mass_share']:.2f}, "
         f"stiffness x{skin['stiffness_share']:.2f}), whole round each bearing's bore"),
        ("flange", "split", "fixed", "Flange", (0.60, 0.30, 0.85), 1.0, m["flange"],
         f"held fixed: the split flange, its sealing land round the inside and the bolts' bosses on it, each voxel at the share "
         f"of it they fill ({skin['flange']['kg']:.2f} kg); the halves are joined only at the bosses"),
        ("design", "design_space", "free", "Free", (0.18, 0.62, 0.42), 0.12, m["design"], "where the optimiser may place metal"),
    ]  # fmt: skip
    layers = []
    for lid, chip, kind, label, colour, alpha, mask_or_faces, note in rows:
        if mask_or_faces.dtype == bool:
            faces = faces_of(mask_or_faces)
            cells = int(mask_or_faces.sum())
        else:
            faces, cells = mask_or_faces, 0
        layers.append({"id": lid, "chip": chip, "kind": kind, "label": label, "colour": colour, "alpha": alpha, "cells": cells,
                       "litres": round(cells * h**3 / 1e6, 3), "note": note,
                       "faces": base64.b64encode(faces.astype("<u4").tobytes()).decode("ascii")})  # fmt: skip
        print(f"{lid:12s} {chip:13s} {kind:9s} {cells:7,} cells, {len(faces):7,} faces, {cells * h**3 / 1e6:6.2f} L")
    centre0 = lo + h / 2  # the centre of cell (0, 0, 0), in the contract's frame
    origin = [centre0[0], centre0[2], -(centre0[1] + (n[1] - 1) * h)]  # the turned grid's first cell, in the viewer's
    routes = {"split": "a two-part sand mould parting at the split", "cast": "a two-part mould, its parting free", "free": "additive: no mould"}
    hypothesis = [
        {"label": "Route", "value": routes[route]},
        {"label": "Budget", "value": f"{budget:g} kg, the reference housing's mass"},
    ]
    record = {"schema": 2, "source": "topo_free.build_free on the contract's layout (contract_layout.py, from zenryx's spaces)",
              "voxel_mm": h, "grid": {"size": h, "shape": [n[0], n[2], n[1]], "origin": origin}, "layers": layers,
              "hypothesis": hypothesis}  # fmt: skip
    TARGET.write_text(json.dumps(record), encoding="utf-8")
    print(f"{TARGET.relative_to(ROOT)}: {TARGET.stat().st_size / 1e6:.1f} MB")
    return TARGET


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 6.0)
