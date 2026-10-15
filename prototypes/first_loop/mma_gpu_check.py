"""PROTOTYPE (LOP-19) - checks MMA's subproblem on the GPU (`mma_gpu.solve_subproblem`) against the
NumPy one (`mma.solve_subproblem`): the same point, the same Newton steps, and how long each takes,
on a subproblem of the voxel optimisation's size (76,249 variables; 6 seats' bounds and the mass,
as LOP-18's peak-drive run has; and 13, as a run with both cases).

Run: .venv/Scripts/python.exe prototypes/first_loop/mma_gpu_check.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mma  # noqa: E402
import mma_gpu  # noqa: E402


def subproblem(n: int, m: int, seed: int) -> tuple:
    """An MMA subproblem as the voxel optimisation builds one: x in [0, 1], the asymptotes at
    x -+ 0.5, the move limit 0.2; seats' gradients of both signs gathered on a few thousand
    voxels each, the mass's positive and even; a bound problem (a = 1 on the seats)."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.0, 1.0, n)
    span = np.ones(n)
    low, upp = x - 0.5 * span, x + 0.5 * span
    alpha = np.maximum.reduce([np.zeros(n), low + 0.1 * (x - low), x - 0.2])
    beta = np.minimum.reduce([np.ones(n), upp - 0.1 * (upp - x), x + 0.2])
    df = np.zeros((m, n))
    for i in range(m - 1):
        near = rng.choice(n, min(4000, n // 2), replace=False)
        df[i, near] = rng.normal(0.0, 1e-3, near.size)
    df[m - 1] = 1.0 / n
    f = np.r_[rng.uniform(0.3, 0.6, m - 1), 0.01]
    ux1, xl1 = upp - x, x - low
    ux2, xl2 = ux1**2, xl1**2
    raa = np.full(m, 1e-6)
    tiny = raa[:, None] / span[None, :]
    pp = (1.001 * np.maximum(df, 0) + 0.001 * np.maximum(-df, 0) + tiny) * ux2
    qq = (0.001 * np.maximum(df, 0) + 1.001 * np.maximum(-df, 0) + tiny) * xl2
    p0 = (1e-6 / span) * ux2
    q0 = (1e-6 / span) * xl2
    r = f - (pp @ (1.0 / ux1) + qq @ (1.0 / xl1))
    a = np.r_[np.ones(m - 1), 0.0]
    return low, upp, alpha, beta, p0, q0, pp, qq, 1.0, a, -r, np.full(m, 1000.0), np.ones(m)


def main() -> int:
    worst = 0.0
    for m in (7, 13):
        args = subproblem(76_249, m, seed=m)
        mma_gpu.solve_subproblem(*subproblem(2_000, m, seed=1))  # warm the card (CuPy's kernels)
        t0 = time.time()
        x_cpu, info_cpu = mma.solve_subproblem(*args)
        t_cpu = time.time() - t0
        t0 = time.time()
        x_gpu, info_gpu = mma_gpu.solve_subproblem(*args)
        t_gpu = time.time() - t0
        diff = float(np.abs(x_cpu - x_gpu).max())
        worst = max(worst, diff)
        print(f"m = {m:2d}: NumPy {t_cpu:6.2f} s ({info_cpu['newton_steps']} Newton steps), CuPy {t_gpu:5.2f} s "
              f"({info_gpu['newton_steps']}); the points differ by {diff:.2e}, z {info_cpu['z']:.6f} / {info_gpu['z']:.6f}")  # fmt: skip
    ok = worst < 1e-8
    print("the same point" if ok else "the points DIFFER")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
