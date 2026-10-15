"""PROTOTYPE (LOP-17) - the casting filter's derivative against central differences, CPU only.

`topo_free.casting_filter`, plain (each column filled between metal) and anchored (filled from the
split out to the last metal, the route "split"), on a small grid with a split, a room and a
kept-clear voxel breaking the runs, and frozen voxels; J = w · rho~(rho) for random w. The
backward pass must give dJ/drho within finite-difference noise. Also checks the anchored filter's
meaning: every column of each half one piece from where its run starts nearest the split.

Run: .venv/Scripts/python.exe prototypes/first_loop/cast_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from topo_free import casting_filter  # noqa: E402


def check(anchored: bool, seed: int = 1) -> float:
    rng = np.random.default_rng(seed)
    n = np.array([3, 2, 12])
    k_split = 6
    kind = np.zeros(tuple(n), dtype=np.int8)
    kind[0, 0, 2] = -1  # a room breaks the motor side's run
    kind[1, 1, 9] = -1  # a kept-clear voxel in the cover
    kind[2, 1, 4] = 1  # frozen
    kind[2, 0, 10] = 1
    kind = kind.ravel()
    forward, backward = casting_filter(kind, n, k_split, anchored=anchored)
    m = int((kind >= 0).sum())
    rho = rng.uniform(0.05, 0.95, m)
    w = rng.normal(size=m)
    forward(rho)
    grad = backward(w)
    eps = 1e-6
    fd = np.zeros(m)
    for i in range(m):
        up, dn = rho.copy(), rho.copy()
        up[i] += eps
        dn[i] -= eps
        fd[i] = (w @ forward(up) - w @ forward(dn)) / (2 * eps)
    forward(rho)  # the backward pass reads the last forward's densities
    free = kind[kind >= 0] == 0
    err = float(np.max(np.abs(grad[free] - fd[free])) / max(np.max(np.abs(fd[free])), 1e-12))
    return err


def meaning() -> bool:
    """Anchored, a single metal voxel far out in a column fills the column from the split to it."""
    n = np.array([1, 1, 12])
    k_split = 6
    kind = np.zeros(12, dtype=np.int8)
    forward, _ = casting_filter(kind, n, k_split, anchored=True)
    rho = np.full(12, 1e-6)
    rho[10] = 1.0 - 1e-9  # metal in the cover, four voxels past the split
    rho[1] = 1.0 - 1e-9  # metal in the motor side, five voxels below it
    out = forward(rho)
    cover_ok = bool(np.all(out[6:11] > 0.99) and out[11] < 0.01)
    motor_ok = bool(np.all(out[1:6] > 0.99) and out[0] < 0.01)
    return cover_ok and motor_ok


if __name__ == "__main__":
    for anchored in (False, True):
        e = check(anchored)
        print(f"{'anchored' if anchored else 'plain'}: worst relative error of the derivative {e:.2e}")
    print("anchored fills from the split out:", meaning())
