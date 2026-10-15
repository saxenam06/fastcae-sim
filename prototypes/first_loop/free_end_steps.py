"""PROTOTYPE (LOP-30) - the steps in a drawn design's free ends, the acceptance gate of the engineer's reviews (14 October
23:13: "no step over 2 mm in a free end"). Each half's drawing filled on a 1 mm grid; along its pull the outermost metal
in each plan cell is the free end where a member stands there (at least 3 mm proud of its column's level, the run's
`spl_base`); between neighbouring member cells of one family (on the split or on a wall), both at least `--edge` mm inside
the member's outline (the round's fall at the edge is the section rule's, not a step), a rise of more than 2 mm in 1 mm
is a step. Prints each half's steps (cells, the largest) and pictures the free ends with the steps marked.

    free_end_steps.py <design> [--run <run stem>] [--edge 5] [--step 2]

The run is the design's own (its flow record names it) unless given.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "first_loop"
sys.path.insert(0, str(HERE))


def run_of(design: str) -> str:
    flow = json.loads((OUT / f"flow_{design}.json").read_text(encoding="utf-8"))
    step = next(s_ for s_ in flow["steps"] if s_.get("id") == "optimise")
    return step["outputs"][0]


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from scipy.ndimage import distance_transform_edt

    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--run", default="")
    ap.add_argument("--edge", type=float, default=5.0)
    ap.add_argument("--step", type=float, default=2.0)
    a = ap.parse_args()
    run = a.run or run_of(a.design)
    z = np.load(OUT / f"{run}.npz")
    if "spl_base" not in z.files:
        raise SystemExit(f"{run} is not a spline run: no columns' levels saved")
    lo, h = np.asarray(z["lo"], float), float(z["h"])
    ij, half_c, base, fam = z["spl_ij"].astype(int), z["spl_half"].astype(int), z["spl_base"].astype(int), z["spl_on_split"].astype(bool)
    n_xy = (int(z["n"][0]), int(z["n"][1]))
    fig, axes = plt.subplots(1, 2, figsize=(20, 9))
    summary = {}
    for ax, (hf, half) in zip(axes, ((0, "motor_side"), (1, "cover")), strict=True):
        lower = hf == 0
        # each plan cell's outermost column (the farthest from the split): its level's face and its family
        face = np.full(n_xy, np.nan)
        fam_g = np.zeros(n_xy, np.int8)
        sel = np.flatnonzero(half_c == hf)
        order = sel[np.argsort(-base[sel])] if lower else sel[np.argsort(base[sel])]  # the outermost written last
        for k in order:
            i_, j_ = ij[k]
            face[i_, j_] = lo[2] + (base[k] + 1) * h if lower else lo[2] + base[k] * h
            fam_g[i_, j_] = 1 if fam[k] else 2
        m = trimesh.load(OUT / f"{a.design}_{half}.ply")
        g = 1.0
        b_lo, b_hi = m.bounds
        vx = m.voxelized(pitch=g).fill()
        pts = vx.points
        xs = np.arange(b_lo[0] + 0.5 * g, b_hi[0], g)
        ys = np.arange(b_lo[1] + 0.5 * g, b_hi[1], g)
        ii = np.floor((pts[:, 0] - b_lo[0]) / g).astype(int)
        jj = np.floor((pts[:, 1] - b_lo[1]) / g).astype(int)
        ok = (ii >= 0) & (ii < len(xs)) & (jj >= 0) & (jj < len(ys))
        if lower:
            end_v = np.full((len(xs), len(ys)), np.inf)
            np.minimum.at(end_v, (ii[ok], jj[ok]), pts[ok, 2])
        else:
            end_v = np.full((len(xs), len(ys)), -np.inf)
            np.maximum.at(end_v, (ii[ok], jj[ok]), pts[ok, 2])
        end = np.where(np.isfinite(end_v), end_v, np.nan)
        # the run's column under each 1 mm cell
        ci = np.clip(np.floor((xs - lo[0]) / h).astype(int), 0, n_xy[0] - 1)
        cj = np.clip(np.floor((ys - lo[1]) / h).astype(int), 0, n_xy[1] - 1)
        face_c = face[ci[:, None], cj[None, :]]
        fam_c = fam_g[ci[:, None], cj[None, :]]
        proud = (face_c - end) if lower else (end - face_c)
        member = np.isfinite(proud) & (proud >= 3.0) & (fam_c > 0)
        steps_all = []
        mark = np.zeros(member.shape, bool)
        for f_ in (1, 2):
            mf = member & (fam_c == f_)
            inner = distance_transform_edt(mf) * g >= a.edge
            for axis in (0, 1):
                e1 = np.take(end, np.arange(end.shape[axis] - 1), axis=axis)
                e2 = np.take(end, np.arange(1, end.shape[axis]), axis=axis)
                i1 = np.take(inner, np.arange(inner.shape[axis] - 1), axis=axis)
                i2 = np.take(inner, np.arange(1, inner.shape[axis]), axis=axis)
                both = i1 & i2
                d = np.abs(e2 - e1)
                hit = both & (d > a.step)
                steps_all.append(d[hit])
                idx = np.argwhere(hit)
                mark[tuple(idx.T)] = True
        st = np.concatenate(steps_all) if steps_all else np.zeros(0)
        n_inner = int(sum((distance_transform_edt(member & (fam_c == f_)) * g >= a.edge).sum() for f_ in (1, 2)))
        summary[half] = {"member_cells": int(member.sum()), "inner_cells": n_inner, "steps": int(len(st)),
                         "largest_mm": float(st.max()) if len(st) else 0.0, "share": float(len(st)) / max(n_inner, 1)}  # fmt: skip
        print(f"{a.design} {half}: {int(member.sum()):,} member cells of 1 mm ({n_inner:,} at least {a.edge:g} mm inside); "
              f"{len(st):,} rises over {a.step:g} mm in 1 mm ({100.0 * len(st) / max(n_inner, 1):.2f} %), the largest {summary[half]['largest_mm']:.1f} mm")  # fmt: skip
        hm = np.where(member, proud, np.nan)
        im = ax.imshow(hm.T, origin="lower", extent=(xs[0] - 0.5, xs[-1] + 0.5, ys[0] - 0.5, ys[-1] + 0.5), cmap="viridis")
        if mark.any():
            mi = np.argwhere(mark)
            ax.plot(xs[mi[:, 0]], ys[mi[:, 1]], "r.", ms=2.0)
        ax.set_aspect("equal")
        ax.set_title(f"{a.design} {half}: members' height off their level (mm); red, a rise over {a.step:g} mm in 1 mm "
                     f"({summary[half]['steps']:,}, the largest {summary[half]['largest_mm']:.1f} mm)", fontsize=10, loc="left")  # fmt: skip
        fig.colorbar(im, ax=ax, shrink=0.7)
    png = OUT / f"steps_{a.design}.png"
    fig.savefig(png, dpi=80, bbox_inches="tight")
    (OUT / f"steps_{a.design}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(png)


if __name__ == "__main__":
    main()
