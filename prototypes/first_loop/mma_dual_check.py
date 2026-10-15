"""PROTOTYPE (LOP-20) - `mma_dual.solve_subproblem` against `mma.solve_subproblem` (the primal-dual
method) on subproblems shaped like the loop's: 79,484 variables; m = 2 (the mass and the greatest
member), 8 (and six seats' tilts) and 14 (and six bearing beds); the coefficients built as
`mma.MMA._solve` builds them, at a first iteration and at a later one with tight asymptotes. Both
solve the same convex subproblem, so their points must agree; the dual's should be no worse
(its objective no higher, its constraints met as well) and much faster.

Run: .venv/Scripts/python.exe prototypes/first_loop/mma_dual_check.py   (on the CPU: LOOP_FAST unset)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.pop("LOOP_FAST", None)

import mma  # noqa: E402
import mma_dual  # noqa: E402


def subproblem(rng, n: int, m: int, late: bool):
    """The arguments `mma.MMA._solve` hands a solver, for gradients like the loop's."""
    x = rng.uniform(0.05, 0.95, n)
    span = np.ones(n)
    reach = 0.05 if late else 0.5  # the asymptotes: wide at first, tight later
    low, upp = x - reach * span, x + reach * span
    move = 0.2 / np.sqrt(8.0 if late else 1.0)
    alpha = np.maximum.reduce([np.zeros(n), low + 0.1 * (x - low), x - move])
    beta = np.minimum.reduce([np.ones(n), upp - 0.1 * (upp - x), x + move])
    df0 = -rng.exponential(1.0, n) * 10.0 / n  # compliance: every voxel's metal stiffens
    df = np.empty((m, n))
    f = np.empty(m)
    df[0] = 1.0 / (0.06 * n)  # the mass, at its budget
    f[0] = rng.uniform(-0.01, 0.01)
    if m > 1:
        df[1] = rng.exponential(1.0, n) / n * (rng.random(n) < 0.3)  # the greatest member, where metal gathers
        f[1] = rng.uniform(-0.02, 0.01)
    for i in range(2, m):  # seats' tilts and beds: both signs, gathered near the seats
        near = rng.random(n) < 0.05
        df[i] = rng.normal(0.0, 1.0, n) * near * 50.0 / n
        f[i] = rng.uniform(-0.3, 0.05)
    ux1, xl1 = upp - x, x - low
    ux2, xl2 = ux1 * ux1, xl1 * xl1
    raa0 = max(1e-6, 0.1 / n * float(np.abs(df0) @ span))
    raa = np.maximum(1e-6, 0.1 / n * (np.abs(df) @ span))
    p0 = (1.001 * np.maximum(df0, 0) + 0.001 * np.maximum(-df0, 0) + raa0 / span) * ux2
    q0 = (0.001 * np.maximum(df0, 0) + 1.001 * np.maximum(-df0, 0) + raa0 / span) * xl2
    tiny = raa.reshape(-1, 1) / span[None, :]
    pp = (1.001 * np.maximum(df, 0) + 0.001 * np.maximum(-df, 0) + tiny) * ux2
    qq = (0.001 * np.maximum(df, 0) + 1.001 * np.maximum(-df, 0) + tiny) * xl2
    r = f - (pp @ (1.0 / ux1) + qq @ (1.0 / xl1))
    return low, upp, alpha, beta, p0, q0, pp, qq, 1.0, np.zeros(m), -r, np.full(m, 1000.0), np.ones(m)


def measures(x, args):
    low, upp, alpha, beta, p0, q0, pp, qq, a0, a, b, c, d = args
    obj = float(p0 @ (1.0 / (upp - x)) + q0 @ (1.0 / (x - low)))
    cons = pp @ (1.0 / (upp - x)) + qq @ (1.0 / (x - low)) - b
    return obj, cons


def main() -> None:
    rng = np.random.default_rng(11)
    n = 79_484
    worst = 0.0
    print(f"{'m':>3s} {'late':>5s} {'primal-dual s':>13s} {'dual s':>7s} {'steps':>5s} {'max |dx|':>9s} {'objective pd':>13s} {'dual':>13s} {'worst g pd':>10s} {'dual':>10s}")
    for m in (2, 8, 14):
        for late in (False, True):
            args = subproblem(rng, n, m, late)
            t = time.time()
            x_pd, info_pd = mma.solve_subproblem(*args)
            t_pd = time.time() - t
            t = time.time()
            x_du, info_du = mma_dual.solve_subproblem(*args)
            t_du = time.time() - t
            dx = float(np.abs(x_pd - x_du).max())
            o_pd, g_pd = measures(x_pd, args)
            o_du, g_du = measures(x_du, args)
            worst = max(worst, dx)
            print(f"{m:3d} {str(late):>5s} {t_pd:13.3f} {t_du:7.3f} {info_du['newton_steps']:5d} {dx:9.2e} {o_pd:13.6f} {o_du:13.6f} "
                  f"{float((g_pd - info_pd['y']).max()):10.2e} {float((g_du - info_du['y']).max()):10.2e}")
    print(f"largest difference in x: {worst:.2e}  ({'agree' if worst < 1e-4 else 'DISAGREE'})")


if __name__ == "__main__":
    main()
