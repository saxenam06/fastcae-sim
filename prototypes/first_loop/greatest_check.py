"""PROTOTYPE (LOP-20) - a check of the greatest member (`topo.greatest_share`): its derivative
against central differences (9.8e-7 on 10 October), the ball's entries (each voxel once), and its
measure on slabs and ribs of known thickness, i.e. what the 0.6 limit lets through (a 12 mm wall
0.58, an 18 mm one 0.75, at 6 mm voxels).

Run: .venv/Scripts/python.exe prototypes/first_loop/greatest_check.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import topo  # noqa: E402

rng = np.random.default_rng(7)
grid = np.stack(np.meshgrid(np.arange(14), np.arange(12), np.arange(9), indexing="ij"), axis=-1).reshape(-1, 3)
keep = rng.random(len(grid)) > 0.25  # free voxels with gaps, as round the cavity
ijk = grid[keep]
radius = 12.0 / 0.849 / 6.0  # 12 mm at 6 mm voxels: 2.36 voxels
ball, cells = topo.local_ball(ijk, radius)
diag = ball.diagonal()
print(f"{len(ijk)} free voxels, ball radius {radius:.2f} voxels holds {cells} cells; diagonal all 1: {bool(np.all(diag == 1))}, entries all 1: {bool(np.all(ball.data == 1))}")

rho = rng.uniform(0.05, 0.95, len(ijk))
g, dg, m = topo.greatest_share(ball, cells, rho, 0.6)
worst = 0.0
for j in rng.choice(len(ijk), 25, replace=False):
    eps = 1e-6
    up, dn = rho.copy(), rho.copy()
    up[j] += eps
    dn[j] -= eps
    fd = (topo.greatest_share(ball, cells, up, 0.6)[0] - topo.greatest_share(ball, cells, dn, 0.6)[0]) / (2 * eps)
    worst = max(worst, abs(fd - dg[j]) / max(abs(fd), 1e-12))
print(f"G {g:.5f}, M {m:.5f}; the derivative against central differences, 25 voxels: worst relative error {worst:.2e}")

# Slabs of t voxels through a block of free voxels: the measure M that the limit 0.6 reads.
big = np.stack(np.meshgrid(np.arange(30), np.arange(30), np.arange(30), indexing="ij"), axis=-1).reshape(-1, 3)
bb, bc = topo.local_ball(big, radius)
for t in (1, 2, 3, 4, 6):
    slab = ((big[:, 2] >= 15 - t // 2) & (big[:, 2] < 15 - t // 2 + t)).astype(float)
    print(f"a slab {t} voxels ({6 * t} mm) thick: M = {topo.greatest_share(bb, bc, slab, 0.6)[2]:.3f}")
for t in (1, 2, 3):
    rib = ((big[:, 0] >= 15 - t // 2) & (big[:, 0] < 15 - t // 2 + t) & (big[:, 2] >= 10) & (big[:, 2] < 14)).astype(float)
    print(f"a rib {t} voxels thick, 4 high: M = {topo.greatest_share(bb, bc, rib, 0.6)[2]:.3f}")
