"""PROTOTYPE (LOP-29) - a drawn wall's real thickness: rays along z through a design's drawn half at points round one seat
(50 mm off its axis each way, and one between), each giving the drawn metal's extent, beside the optimiser's own voxels in
that column (metal #, fixed F, not modelled r). It showed `lop29_keep`'s floor of the motor side's intermediate gear room
drawn 4.9 mm thick where the optimiser had one 4 mm cube, and `lop29_exact`'s 4.0 mm (13 October 20:40-20:52).

Run: .venv/Scripts/python.exe prototypes/first_loop/wall_rays.py <design> "<shaft> <side>" """

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "first_loop"


def main(design: str, seat: str) -> None:
    import pyvista as pv

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{rec['outcome_of']}.npz")
    n, lo, h, ks = z["n"].astype(int), np.asarray(z["lo"], float), float(z["h"]), int(z["k_split"])
    z_split = lo[2] + h * ks
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    shaft, side = seat.split()
    b = next(x for x in lay["bearings"] if x["shaft"] == shaft and x["side"] == side)
    mesh = pv.read(str(OUT / rec["files"]["motor_side" if side == "-z" else "cover"])).triangulate().clean()
    phys = np.zeros(int(np.prod(n)))
    phys[z["elem"][z["free_e"]]] = np.asarray(z["phys"], float)
    kind = np.full(int(np.prod(n)), "r", object)
    kind[z["elem"]] = "."
    kind[z["elem"][z["frozen"].astype(bool)]] = "F"
    ax = np.asarray(b["axis"], float)
    lower = side == "-z"
    for dx, dy in ((50, 0), (-50, 0), (0, 50), (0, -50), (45, 20)):
        x0, y0 = ax[0] + dx, ax[1] + dy
        z_a, z_b = (lo[2] - 5.0, z_split) if lower else (z_split, lo[2] + h * n[2] + 5.0)
        pts, _ = mesh.ray_trace([x0, y0, z_a], [x0, y0, z_b])
        zs = np.sort(np.asarray(pts)[:, 2]) if len(pts) else np.array([])
        runs = [(float(zs[m]), float(zs[m + 1])) for m in range(0, len(zs) - 1, 2)]
        i, j = int((x0 - lo[0]) // h), int((y0 - lo[1]) // h)
        col = []
        for k in range(n[2]):
            c = lo[2] + h * (k + 0.5)
            if (c > z_split) if lower else (c < z_split):
                continue
            idx = np.ravel_multi_index((i, j, k), n)
            mark = "F" if kind[idx] == "F" else ("#" if kind[idx] == "." and phys[idx] >= 0.5 else kind[idx])
            col.append(f"{c:.1f}{mark}")
        print(f"({dx:+d}, {dy:+d}) mm off the axis: drawn " + (", ".join(f"{a:.1f} to {c:.1f} ({c - a:.1f} mm)" for a, c in runs) or "nothing"))
        print("   the optimiser's voxels (centre z; # metal, F fixed, . free and empty, r not modelled): " + " ".join(col))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
