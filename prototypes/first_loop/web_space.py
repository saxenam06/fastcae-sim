"""PROTOTYPE (LOP-25; the engineer, 15:23-15:27: "how to prevent such lumps"): the design space with room for a flat
plate between the bearings. Between two seats of a half the optimiser needs the most metal, and with every member at
most 12 mm thick it bundled bars there, which crossed and merged into knots. Here, over the hull of every two of a half's
seats' bosses (their discs at the trade's boss radius, 1.25·D + 10) less the bosses themselves, the free cells are kept
only within `--cap` mm of their column's base: a web at most that thick, strong but thin everywhere (production's web
between the bosses). Everywhere else the space is as before.

    web_space.py <run> --label <label> [--cap 12]

The run gives the model (its grid and columns: `regions.context`). Writes data/first_loop/<label>.npz (a cell mask, for
`topo_free.py --space <label>.npz`) and <label>.png (each half's web areas in plan)."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parts as pm  # noqa: E402
import regions as rg  # noqa: E402
import topo  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"


def main(run: str, label: str, cap: float) -> dict:
    ctx = rg.context(run)
    model, kind, h, lo = ctx["model"], ctx["kind"], ctx["h"], ctx["lo"]
    n = tuple(int(v) for v in model["n"])
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    ii, jj, _ = np.unravel_index(elem[free_e], n)
    xy = np.column_stack([lo[0] + h * (ii + 0.5), lo[1] + h * (jj + 0.5)])
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    web = np.zeros(len(free_e), bool)
    areas = {}
    for half, base in (("motor_side", 1), ("cover", 10_001)):
        seats = [b for b in lay["bearings"] if (b["side"] == "+z") == (half == "cover")]
        on = layer[col] == base
        here = np.zeros(len(free_e), bool)
        for i in range(len(seats)):
            for j in range(i + 1, len(seats)):
                a, b = np.asarray(seats[i]["axis"], float), np.asarray(seats[j]["axis"], float)
                ra, rb = 0.625 * float(seats[i]["D"]) + 5.0, 0.625 * float(seats[j]["D"]) + 5.0
                hull = pm.uneven_capsule(xy, a, b, ra, rb) <= 0.0
                outside = (np.hypot(*(xy - a).T) > ra) & (np.hypot(*(xy - b).T) > rb)
                here |= on & hull & outside
        web |= here
        areas[half] = int(len(np.unique(col[here])))
    cut = web & (pos * h >= cap)
    mask = np.ones(int(np.prod(n)), bool)
    mask[elem[free_e[cut]]] = False
    np.savez_compressed(OUT / f"{label}.npz", mask=mask.reshape(n), lo=np.asarray(lo), n=np.asarray(n), h=h)
    out = {"label": label, "cap_mm": cap, "web_columns": areas, "cells_removed": int(cut.sum()), "free_cells": int(len(free_e))}
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, (half, base) in zip(axes, (("motor_side", 1), ("cover", 10_001)), strict=True):
        m = np.zeros(n[:2])
        sel = (layer[col] == base) & web
        m[ii[sel], jj[sel]] = 1.0
        allc = np.zeros(n[:2])
        allc[ii[layer[col] == base], jj[layer[col] == base]] = 1.0
        ax.imshow((allc + m).T, origin="lower", extent=[lo[0], lo[0] + n[0] * h, lo[1], lo[1] + n[1] * h], cmap="Greys", vmin=0, vmax=2.5)
        ax.set_title(f"{label}, {half.replace('_', ' ')}: the web areas (dark), at most {cap:g} mm off the wall", fontsize=9)
        ax.set_aspect("equal")
    fig.savefig(OUT / f"{label}.png", dpi=80, bbox_inches="tight")
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("--label", required=True)
    ap.add_argument("--cap", type=float, default=12.0)
    a = ap.parse_args()
    main(a.run, a.label, a.cap)
