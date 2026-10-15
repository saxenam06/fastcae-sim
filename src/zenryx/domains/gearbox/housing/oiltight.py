"""Is the drawn housing oil-tight? (moved from `prototypes/first_loop/oiltight.py`: `check`,
`_geodesic`; LOP-33). The empty start's walls are the optimiser's own metal; this checks the drawing
kept them closed. Both halves are filled on one grid along the pull (`mesh.occupancy`), the split on
a cell face; every exit's seal bore counts as closed (the seal and its shaft fill it); the inside
(the cup's rooms, both halves) is flood-filled through every empty cell, six neighbours. A leak is
the inside reaching the grid's edge; where it leaks is where the shortest way out leaves the inside.
Writes `oiltight_<design>.json`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import cup as cupmod
from zenryx.domains.gearbox.housing import mesh as mr
from zenryx.domains.gearbox.housing.draw import rooms_mask

CELL = 2.0  # mm, the grid's cell: a 4 mm wall is two cells


def _geodesic(seed: np.ndarray, free: np.ndarray, most: int = 2000) -> np.ndarray:
    """Each free cell's distance in cells from the seed through free cells (6 neighbours), -1 where
    unreached: a breadth-first sweep by dilation."""
    from scipy.ndimage import binary_dilation, generate_binary_structure

    six = generate_binary_structure(3, 1)
    dist = np.full(free.shape, -1, np.int32)
    front = seed & free
    dist[front] = 0
    reached = front.copy()
    for step in range(1, most):
        grown = binary_dilation(front, structure=six) & free & ~reached
        if not grown.any():
            break
        dist[grown] = step
        reached |= grown
        front = grown
    return dist


def check(design: str, out: Path, contract: Path, cell: float = CELL) -> dict:
    import trimesh
    from scipy.ndimage import label

    t0 = time.time()
    rec = json.loads((out / f"{design}.json").read_text(encoding="utf-8"))
    z_split = float(rec["z"]["split"])
    meshes = {}
    for half, name in rec["files"].items():
        ply = out / name.replace(".stl", ".ply")
        meshes[half] = trimesh.load(str(ply if ply.exists() else out / name), process=True)
    lo, shape = mr.grid_over(list(meshes.values()), cell, pad=3)
    lo = np.asarray(lo, float).copy()
    lo[2] = z_split - cell * np.ceil((z_split - lo[2]) / cell)  # the split on a cell face
    shape = np.asarray(shape, int).copy()
    shape[2] += 2
    metal = np.zeros(tuple(shape), bool)
    for half, tm in meshes.items():
        cells, _, odd = mr.occupancy(tm, cell, lo, shape)
        metal |= cells
        if np.any(odd):
            print(
                f"{half}: {int(np.sum(odd))} columns crossed its surface an odd number of times "
                "(left as found)"
            )
    xs, ys, zs = (lo[i] + cell * (np.arange(shape[i]) + 0.5) for i in range(3))
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    sealed = np.zeros(tuple(shape), bool)
    for e in rec.get("exits") or []:
        if e["kind"] == "seal":  # the seal and its shaft close the bore
            sealed |= (
                (np.hypot(gx - e["centre"][0], gy - e["centre"][1]) < e["radius"] + cell)
                & (gz >= e["z"][0] - cell)
                & (gz <= e["z"][1] + cell)
            )
    spec, _ = load_and_validate(contract)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(
        chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm")
    )
    grid = {"n": shape, "lo": lo, "h": cell}
    inside = rooms_mask(grid, all_rooms, z_split, "motor_side") | rooms_mask(
        grid, all_rooms, z_split, "cover"
    )
    free = ~metal & ~sealed
    seed = inside & free
    labels, _ = label(free)
    inside_labels = np.unique(labels[seed])
    inside_labels = inside_labels[inside_labels > 0]
    edge = np.zeros(tuple(shape), bool)
    edge[[0, -1], :, :] = edge[:, [0, -1], :] = edge[:, :, [0, -1]] = True
    outside_labels = np.unique(labels[edge & free])
    leaking = np.intersect1d(inside_labels, outside_labels)
    result = {
        "design": design,
        "cell_mm": cell,
        "tight": bool(len(leaking) == 0),
        "inside_cells": int(seed.sum()),
        "metal_cm3": float(metal.sum()) * cell**3 / 1e3,
        "opened": None,
    }
    if len(leaking):
        region = np.isin(labels, leaking)
        d_in = _geodesic(seed, region)
        d_out = _geodesic(edge & region, region)
        both = (d_in >= 0) & (d_out >= 0)
        total = np.where(both, d_in + d_out, np.iinfo(np.int32).max)
        best = int(total.min())
        # the shortest way out's cells, and where it leaves the inside: its first cells outside the
        # rooms
        on_path = both & (total <= best)
        past = on_path & ~inside
        first = past & (d_in == d_in[past].min()) if past.any() else on_path
        pts = np.column_stack([gx[first], gy[first], gz[first]])
        result.update(
            leak_at_mm=[round(float(v), 1) for v in pts.mean(axis=0)],
            path_mm=best * cell,
            path_cells=int(on_path.sum()),
        )
    result["seconds"] = round(time.time() - t0, 1)
    (out / f"oiltight_{design}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    word = (
        "TIGHT"
        if result["tight"]
        else f"LEAK at {result['leak_at_mm']} mm (the shortest way out {result['path_mm']:.0f} mm)"
    )
    print(
        f"{design}: {word}; inside {result['inside_cells']:,} cells of {cell:g} mm, metal "
        f"{result['metal_cm3']:.0f} cm3, {result['seconds']:.0f} s"
    )
    return result
