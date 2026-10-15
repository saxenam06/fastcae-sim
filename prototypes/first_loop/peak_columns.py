"""PROTOTYPE (LOP-30) - The voxel run's columns standing far above every neighbour on their level (the sticks): each one's place, height, its
neighbours' tallest, and how many columns of its own height stand together (1: a single 4 mm column).

    peak_columns.py <run stem> [rise mm]
"""

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("LOOP_EXACT_WALLS", "1")
import outcome_cad as oc  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run = sys.argv[1]
rise = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
z = np.load(OUT / f"{run}.npz")
h, lo = float(z["h"]), np.asarray(z["lo"], float)
spl = oc.voxel_cols_as_spline(run, 2.0, 3.0)
ij, half, base, fam, t = spl["ij"].astype(int), spl["half"], spl["base"], spl["on_split"], np.nan_to_num(spl["t"], nan=0.0)
key = {(int(half[k]), int(base[k]) if False else 0, int(ij[k, 0]), int(ij[k, 1]), bool(fam[k])): k for k in range(len(t))}
by = {}
for k in range(len(t)):
    by.setdefault((int(half[k]), bool(fam[k]), int(ij[k, 0]), int(ij[k, 1])), []).append(k)
found = 0
for k in np.argsort(-t):
    if t[k] * h < 20:
        break
    hf, fm, i, j = int(half[k]), bool(fam[k]), int(ij[k, 0]), int(ij[k, 1])
    nb = [t[c] for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0) for c in by.get((hf, fm, i + di, j + dj), [])]
    top_nb = max(nb) if nb else 0.0
    if (t[k] - top_nb) * h >= rise:
        found += 1
        x, y = lo[:2] + h * (np.array([i, j]) + 0.5)
        print(f"{'cover' if hf else 'motor side'} {'split' if fm else 'wall'} column at ({x:.0f}, {y:.0f}): {t[k] * h:.0f} mm, "
              f"its tallest neighbour {top_nb * h:.0f} mm")
print(f"{found} columns stand {rise:g} mm or more above every neighbour")
