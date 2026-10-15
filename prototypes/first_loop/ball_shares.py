"""PROTOTYPE (LOP-28) - where a run's metal bunches: the greatest member's ball shares (`topo.local_ball`,
`topo.greatest_share`) on a run's final field, read at 16 and 12 mm. For each: the p-means at p 12, 40 and 80 (what the
rule would read), the metal voxels' shares at the 50/90/99/99.9th percentiles and their worst, how many balls hold over
0.6 and 0.7, and where the 2000 worst stand in plan (20 mm cells, with their z range). 13 October 03:41: on `final9` the
rule at p 12 read 0.566 while 238 balls held over 0.7, all at the junctions.

Run: .venv/Scripts/python.exe prototypes/first_loop/ball_shares.py <run stem> [<run stem> ...]"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OUT = HERE.parents[1] / "data" / "first_loop"


def main(stems: list[str]) -> None:
    import topo

    for stem in stems:
        z = np.load(OUT / f"{stem}.npz")
        ijk = z["ijk"][z["free_e"]]
        rho = z["phys"]
        h = float(z["h"])
        lo = z["lo"]
        print(stem, f"{len(rho):,} free voxels, metal {rho.sum():,.0f}")
        for mm in (16.0, 12.0):
            radius = mm / 0.849 / h
            ball, cells = topo.local_ball(ijk, radius)
            share = (ball @ rho) / cells
            on = rho > 0.5
            s_on = share[on]
            pm = {p: (np.sum(rho * share**p) / np.sum(rho)) ** (1 / p) for p in (12, 40, 80)}
            q = np.percentile(s_on, [50, 90, 99, 99.9])
            print(f"  {mm:g} mm (R {radius:.2f} vox, {cells} cells): p-means " + ", ".join(f"p{p} {v:.3f}" for p, v in pm.items())
                  + f"; metal voxels' shares 50/90/99/99.9 % {q.round(3).tolist()}, max {s_on.max():.3f}; "
                  f"over 0.6: {int((s_on > 0.6).sum())}, over 0.7: {int((s_on > 0.7).sum())}")  # fmt: skip
            worst = np.argsort(-share * on)[:2000]
            xyz = lo[None, :] + h * (ijk[worst] + 0.5)
            cell = np.round(xyz[:, :2] / 20.0).astype(int)
            keys, counts = np.unique(cell, axis=0, return_counts=True)
            spots = []
            for t in np.argsort(-counts)[:8]:
                zs = xyz[np.all(cell == keys[t], axis=1), 2]
                spots.append(f"({20 * keys[t][0]}, {20 * keys[t][1]}): {counts[t]}, z {zs.min():.0f}..{zs.max():.0f}")
            print("    where the 2000 worst balls stand (20 mm cells, x y mm: count, z range): " + "; ".join(spots))


if __name__ == "__main__":
    main(sys.argv[1:])
