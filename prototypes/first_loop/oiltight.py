"""PROTOTYPE (LOP-27) - is a drawn housing oil-tight? The empty start's gate (the engineer, 12 October
20:22: "Do an empty start"): with no fixed shell, the walls are the optimiser's own metal, held
closed by each column's least height (`topo_free.least_heights`); this checks the drawing kept them.

Both halves (the design record's meshes) are filled on one grid along the pull (`mesh_route.
occupancy`), the split on a cell face; every exit's seal bore counts as closed (the seal and its
shaft fill it); the inside (the cup's rooms, `outcome_cad.rooms_mask`, both halves) is flood-filled
through every empty cell, six neighbours. A leak is the inside reaching the grid's edge. Where it
leaks: the shortest path's middle, from the inside's and the outside's geodesic distances.

Run: .venv/Scripts/python.exe prototypes/first_loop/oiltight.py <design> [cell_mm] [--open x,y,z]
     (--open: a cube of 2 cells emptied there first, to check that a hole is found)
Writes data/first_loop/oiltight_<design>.json; prints TIGHT or LEAK and where.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import cup as cupmod  # noqa: E402
import mesh_route as mr  # noqa: E402
import shell as convex  # noqa: E402
from outcome_cad import OUT, rooms_mask  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

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


def check(design: str, cell: float = CELL, opened: tuple[float, float, float] | None = None) -> dict:
    from scipy.ndimage import label

    t0 = time.time()
    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    z_split = float(rec["z"]["split"])
    meshes = {}
    for half, name in rec["files"].items():
        ply = OUT / name.replace(".stl", ".ply")
        import trimesh

        meshes[half] = trimesh.load(str(ply if ply.exists() else OUT / name), process=True)
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
            print(f"{half}: {int(np.sum(odd))} columns crossed its surface an odd number of times (left as found)")
    xs, ys, zs = (lo[i] + cell * (np.arange(shape[i]) + 0.5) for i in range(3))
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    sealed = np.zeros(tuple(shape), bool)
    for e in rec.get("exits") or []:
        if e["kind"] == "seal":  # the seal and its shaft close the bore
            sealed |= (np.hypot(X - e["centre"][0], Y - e["centre"][1]) < e["radius"] + cell) & (Z >= e["z"][0] - cell) & (Z <= e["z"][1] + cell)
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    grid = {"n": shape, "lo": lo, "h": cell}
    inside = rooms_mask(grid, all_rooms, z_split, "motor_side") | rooms_mask(grid, all_rooms, z_split, "cover")
    if opened is not None:  # a hole made on purpose, to check the check
        near = (np.abs(X - opened[0]) <= cell) & (np.abs(Y - opened[1]) <= cell) & (np.abs(Z - opened[2]) <= cell)
        metal &= ~near
    free = ~metal & ~sealed
    seed = inside & free
    labels, _ = label(free)
    inside_labels = np.unique(labels[seed])
    inside_labels = inside_labels[inside_labels > 0]
    edge = np.zeros(tuple(shape), bool)
    edge[[0, -1], :, :] = edge[:, [0, -1], :] = edge[:, :, [0, -1]] = True
    outside_labels = np.unique(labels[edge & free])
    leaking = np.intersect1d(inside_labels, outside_labels)
    out = {"design": design, "cell_mm": cell, "tight": bool(len(leaking) == 0), "inside_cells": int(seed.sum()),
           "metal_cm3": float(metal.sum()) * cell**3 / 1e3, "opened": list(opened) if opened else None}  # fmt: skip
    if len(leaking):
        region = np.isin(labels, leaking)
        d_in = _geodesic(seed, region)
        d_out = _geodesic(edge & region, region)
        both = (d_in >= 0) & (d_out >= 0)
        total = np.where(both, d_in + d_out, np.iinfo(np.int32).max)
        best = int(total.min())
        # the shortest way out's cells, and where it leaves the inside: its first cells outside the rooms (the hole's
        # inner face; the path's middle lay beyond the hole, on its way to the grid's edge)
        on_path = both & (total <= best)
        past = on_path & ~inside
        first = past & (d_in == d_in[past].min()) if past.any() else on_path
        pts = np.column_stack([X[first], Y[first], Z[first]])
        out.update(leak_at_mm=[round(float(v), 1) for v in pts.mean(axis=0)], path_mm=best * cell, path_cells=int(on_path.sum()))
    out["seconds"] = round(time.time() - t0, 1)
    (OUT / f"oiltight_{design}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    word = "TIGHT" if out["tight"] else f"LEAK at {out['leak_at_mm']} mm (the shortest way out {out['path_mm']:.0f} mm)"
    print(f"{design}: {word}; inside {out['inside_cells']:,} cells of {cell:g} mm, metal {out['metal_cm3']:.0f} cm3, {out['seconds']:.0f} s")
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    hole = None
    if "--open" in sys.argv:
        hole = tuple(float(v) for v in sys.argv[sys.argv.index("--open") + 1].split(","))
        args = [a for a in args if a != sys.argv[sys.argv.index("--open") + 1]]
    result = check(args[0], float(args[1]) if len(args) > 1 else CELL, hole)
    sys.exit(0 if result["tight"] or hole is not None else 1)
