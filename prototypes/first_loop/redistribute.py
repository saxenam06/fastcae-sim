"""Generator C's "redistribute" move (LOP-25, approach 2; the engineer's plan, `zenryx_new_plan.md` §4C: "Remove
material from an overfilled region and allow the search to place material elsewhere, while preserving required
performance"). From a height-field run: each half's metal in plan; where it is broad (its distance to the metal's
edge at least half of `--width` mm), the region is overfilled: those columns, grown by `--grow` mm, are taken out
of the design space (every free voxel in them), each mount's and each bore's own room kept
(`topo_free.space_mask`). The next run must carry the load another way.

    redistribute.py <run> --label <label> [--width 40] [--grow 8]

Writes data/first_loop/<label>.npz (mask: the free cells left; for `topo_free.py --space <label>.npz`) and
<label>.png (each half in plan: the run's metal, the overfilled patch taken out)."""

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions as rg  # noqa: E402
import smooth_heights as shh  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"


def main(run: str, label: str, width: float, grow: float) -> dict:
    ctx = rg.context(run)
    n, lo, h, ks, kind = ctx["n"], ctx["lo"], ctx["h"], ctx["ks"], ctx["kind"]
    maps = shh.column_heights(run)
    free = (kind == 0).reshape(n)
    mask = free.copy()
    out = {}
    pics = {}
    for half, sl in (("motor_side", slice(0, ks)), ("cover", slice(ks, None))):
        t = np.asarray(maps[half], float)
        foot = t >= 4.0
        edt = ndi.distance_transform_edt(foot) * h
        core = edt >= 0.5 * width
        patch = ndi.binary_dilation(core, iterations=max(1, int(round((0.5 * width + grow) / h)))) & foot if core.any() else core
        mask[:, :, sl] &= ~patch[:, :, None]
        out[half] = {"patch_cells": int(patch.sum()), "metal_in_patch": float(t[patch].sum() / max(t[foot].sum(), 1e-9))}
        pics[half] = (t, patch)
        print(f"{half}: the overfilled patch {patch.sum() * h * h / 100:.0f} cm² in plan, {100 * out[half]['metal_in_patch']:.0f} % of the half's metal")
    np.savez_compressed(OUT / f"{label}.npz", mask=mask, lo=lo, n=np.asarray(n), h=h)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for ax, half in zip(axes, ("motor_side", "cover")):
        t, patch = pics[half]
        ex = [lo[0], lo[0] + h * t.shape[0], lo[1], lo[1] + h * t.shape[1]]
        ax.imshow(np.where(t >= 4.0, t, np.nan).T, origin="lower", extent=ex, cmap="Blues", interpolation="nearest")
        ax.contour(lo[0] + h * (np.arange(t.shape[0]) + 0.5), lo[1] + h * (np.arange(t.shape[1]) + 0.5), patch.T.astype(float), [0.5], colors="r")
        ax.set_aspect("equal")
        ax.set_title(f"{half}: the run's metal (blue), the overfilled patch taken out (red)", fontsize=9)
    fig.savefig(OUT / f"{label}.png", dpi=100, bbox_inches="tight")
    print(OUT / f"{label}.png")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("--label", required=True)
    ap.add_argument("--width", type=float, default=40.0, help="mm: metal at least this broad is overfilled")
    ap.add_argument("--grow", type=float, default=8.0, help="mm the patch is grown by")
    a = ap.parse_args()
    main(a.run, a.label, a.width, a.grow)
