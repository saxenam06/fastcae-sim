"""PROTOTYPE (LOP-27) - one junction as one clean form: the map that glues a patch's columns into a single flat web, for
`topo_free.py --height-volumes` (`topo.volume_map`). Case 3 of the junction cases (`junction_cases.sh`; the engineer,
12 October 23:05: "try"): the cover's patch between the intermediate and output bearings, which the empty start's
baseline (`empty1_5.5kg`) fills with a lumpy strap, becomes one web of one thickness; the optimiser still chooses that
thickness and re-optimises everything else, which stays free.

The web's footprint: between two bearings of one half, within the hull of their circles grown `reach` mm past each
bore's radius (a bridge, as `section_forms.py --bridges` lays it), less those circles themselves (each bore's boss
stays free). Only the end wall's columns join it: each standing on a room with the least wall as its least height
(`topo_free.least_heights`), so that one shared height over them gives one flat top; the side walls' and the
pockets' columns, whose least heights differ, stay free.

Writes data/first_loop/<label>_cols.npz (`vol_of_col`: -1 free, 0 the web; `law` [0]: one height; `s_of_col`) and a
picture of the footprint over the baseline's metal (<label>.png).

Run: .venv/Scripts/python.exe prototypes/first_loop/web_form.py <run> <shaft a> <shaft b> [--half cover]
     [--reach 6] [--label junction_web1]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import exact_walls  # noqa: E402
import topo  # noqa: E402

OUT = topo.OUT


def main(run: str, shaft_a: str, shaft_b: str, half: str = "cover", reach: float = 6.0, label: str = "junction_web1") -> Path:
    z = np.load(OUT / f"{run}.npz")
    n, lo, h, ks = z["n"].astype(int), z["lo"].astype(float), float(z["h"]), int(z["k_split"])
    elem, free_e, frozen = z["elem"], z["free_e"], z["frozen"].astype(bool)
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, pts, layer = topo.height_columns(kind, n, ks, elem, free_e)
    n_cols = len(pts)
    need = exact_walls._height_min(run, z)[elem[free_e]]
    tmin = np.zeros(n_cols)
    np.maximum.at(tmin, col, need)
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    wall = float(layout["settings"]["wall"])
    side = "-z" if half == "motor_side" else "+z"
    bores = {b["shaft"]: b for b in layout["bearings"] if b["side"] == side}
    a, b = bores[shaft_a], bores[shaft_b]
    ca, cb = np.asarray(a["axis"], float), np.asarray(b["axis"], float)
    ra, rb = a["D"] / 2 + reach, b["D"] / 2 + reach
    x = lo[0] + h * (pts[:, 0] + 0.5)
    y = lo[1] + h * (pts[:, 1] + 0.5)
    d = cb - ca
    t = np.clip(((x - ca[0]) * d[0] + (y - ca[1]) * d[1]) / float(d @ d), 0.0, 1.0)
    hull = np.hypot(x - (ca[0] + t * d[0]), y - (ca[1] + t * d[1])) <= ra + t * (rb - ra)  # the tapered capsule of the two circles
    bosses = (np.hypot(x - ca[0], y - ca[1]) <= ra) | (np.hypot(x - cb[0], y - cb[1]) <= rb)
    in_half = (layer // 10_000) == (0 if half == "motor_side" else 1)
    first_run = (layer % 10_000) == 1
    end_wall = np.abs(tmin - wall / h) < 1e-6  # standing on a room, the least wall its least height
    web = hull & ~bosses & in_half & first_run & end_wall
    vol = np.where(web, 0, -1).astype(np.int32)
    path = OUT / f"{label}_cols.npz"
    np.savez_compressed(path, vol_of_col=vol, law=np.array([0], np.int64), s_of_col=np.zeros(n_cols), shafts=np.array([shaft_a, shaft_b]),
                        half=half, reach=reach, run=run)  # fmt: skip
    print(f"{label}: {int(web.sum())} of {n_cols:,} columns glued into one web between the {shaft_a} and {shaft_b} bearings ({half}); "
          f"{int((hull & ~bosses & in_half & first_run).sum())} in the bridge, {int((hull & ~bosses & in_half & first_run & ~end_wall).sum())} left free "
          f"(side walls, pockets, plates); {path.name}")  # fmt: skip
    try:  # the footprint over the baseline's metal in plan
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        placed = np.zeros(int(np.prod(n)), bool)
        placed[elem[free_e]] = np.asarray(z["phys"]) >= 0.5
        grid = placed.reshape(n)
        k = np.arange(n[2])
        metal = (grid & ((k >= ks) if half == "cover" else (k < ks))[None, None, :]).sum(axis=2) * h
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.imshow(metal.T, origin="lower", extent=[lo[0], lo[0] + n[0] * h, lo[1], lo[1] + n[1] * h], cmap="Greys", vmax=40)
        ax.scatter(x[web], y[web], s=6, c="tab:orange", label="the web (one height)")
        for bb in (a, b):
            ax.add_patch(plt.Circle(bb["axis"], bb["D"] / 2 + reach, fill=False, color="tab:blue"))
        ax.set_title(f"{label}: the web between the {shaft_a} and {shaft_b} bearings ({half})")
        ax.set_aspect("equal")
        ax.legend()
        fig.savefig(OUT / f"{label}.png", dpi=90, bbox_inches="tight")
    except Exception as e:  # the picture is for checking only
        print(f"(no picture: {e})")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="One junction glued into one flat web (a --height-volumes map).")
    ap.add_argument("run")
    ap.add_argument("shaft_a")
    ap.add_argument("shaft_b")
    ap.add_argument("--half", default="cover", choices=["cover", "motor_side"])
    ap.add_argument("--reach", type=float, default=6.0, help="mm past each bore's radius the bridge's circles reach")
    ap.add_argument("--label", default="junction_web1")
    a = ap.parse_args()
    main(a.run, a.shaft_a, a.shaft_b, a.half, a.reach, a.label)
