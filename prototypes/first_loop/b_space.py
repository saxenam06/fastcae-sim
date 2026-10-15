"""PROTOTYPE (LOP-25, approach 2: generator B then C; the engineer, 12 October 09:53: "after C when we again optimise,
the B members are kept right?") - a drawn design's members as the next optimisation's design space: each half's
mesh filled on the run's own voxel grid (a cell is the member's when its centre lies inside the mesh), grown by
`--grow` cells so the optimiser can thicken them, and written as a space mask (`regions.py`'s format: mask, lo, n,
h) for `topo_free.py --space <label>.npz`. With the least member (`LOOP_LEAST_MEMBER`) the optimiser then keeps,
resizes or drops each of B's members, and can grow new metal only within them.

    b_space.py <run> <design> --label <label> [--grow 1]

Writes data/first_loop/<label>.npz and <label>.png (each half's mask in plan)."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions as rg  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"


def main(run: str, design: str, label: str, grow: int) -> None:
    import trimesh
    from scipy.ndimage import binary_dilation, generate_binary_structure

    ctx = rg.context(run)
    lo, h, n = np.asarray(ctx["lo"], float), float(ctx["h"]), np.asarray(ctx["model"]["n"], int)
    import mesh_route as mr

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    mask = np.zeros(tuple(int(v) for v in n), bool)
    for half, name in (rec.get("files") or {}).items():
        path = OUT / name
        ply = path.with_suffix(".ply")
        tm = trimesh.load(str(ply if ply.exists() else path), process=False)
        # filled column by column on the run's own grid (trimesh's `contains` needs rtree, not installed)
        cells, _, odd = mr.occupancy(tm, h, lo, tuple(int(v) for v in n))
        mask |= cells
        print(f"{half}: {int(cells.sum()):,} cells inside the members' mesh" + (f" ({odd} odd columns)" if odd else ""))
    if grow > 0:
        mask = binary_dilation(mask, generate_binary_structure(3, 1), iterations=grow)
    np.savez_compressed(OUT / f"{label}.npz", mask=mask, lo=lo, n=n, h=h)
    print(f"{label}: {int(mask.sum()):,} cells ({grow} grown) -> {OUT / f'{label}.npz'}")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    k_split = int(ctx["model"]["k_split"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, (name, sl) in zip(axes, (("motor side", slice(0, k_split)), ("cover", slice(k_split, int(n[2]))))):
        ax.imshow(mask[:, :, sl].sum(axis=2).T * h, origin="lower", extent=[lo[0], lo[0] + n[0] * h, lo[1], lo[1] + n[1] * h], cmap="viridis")
        ax.set_title(f"{label}, {name}: B's members as the design space (mm along the pull)", fontsize=9)
        ax.set_aspect("equal")
    fig.savefig(OUT / f"{label}.png", dpi=90, bbox_inches="tight")
    print(OUT / f"{label}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("design")
    ap.add_argument("--label", required=True)
    ap.add_argument("--grow", type=int, default=1)
    a = ap.parse_args()
    main(a.run, a.design, a.label, a.grow)
