"""PROTOTYPE (LOP-16) - `mma.py` checked on analytic problems before it drives the voxels.

1. Svanberg's cantilever (1987): minimise 0.0624 sum(x) subject to sum(C_j / x_j^3) <= 1,
   C = (61, 37, 19, 7, 1), 1 <= x <= 10. Its optimum has a closed form: x_j = k C_j^(1/4) with
   k^3 = sum(C_j^(1/4)), f = 1.33996.
2. The 2007 notes' toy problem: minimise x1² + x2² + x3² subject to two spheres of radius 3,
   0 <= x <= 5, from (4, 3, 2); against scipy's SLSQP.
3. A bound (min-max) problem shaped like the voxels' one: 12 convex, decreasing "misalignments"
   h_k(x) = sum_j w_kj / (x_j + 0.05), each most sensitive to its own region of the variables,
   and a mass sum(x) <= 0.3 n; minimise z subject to h_k <= z and the mass, with MMA's z (a0 = 1,
   a_k = 1). Against SLSQP on the same epigraph form; the history of z must fall and settle, not
   alternate between two worst constraints.
4. The subproblem's cost at the voxels' size: n = 72,617 variables, 13 constraints.

Run: .venv/Scripts/python.exe prototypes/first_loop/mma_check.py   (prints PASS or FAIL per check)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mma import MMA, solve_subproblem  # noqa: E402

RESULTS = []


def verdict(name: str, ok: bool, text: str) -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {text}")


def cantilever() -> None:
    c = np.array([61.0, 37.0, 19.0, 7.0, 1.0])
    k = np.sum(c**0.25) ** (1 / 3)
    x_star, f_star = k * c**0.25, 0.0624 * k * np.sum(c**0.25)
    opt = MMA(5, 1, 1.0, 10.0)
    x = np.full(5, 5.0)
    for it in range(1, 101):  # noqa: B007 (the count is read after the loop)
        g = np.array([np.sum(c / x**3) - 1.0])
        dg = (-3.0 * c / x**4)[None, :]
        x_new = opt.update(x, 0.0624 * x.sum(), np.full(5, 0.0624), g, dg)
        if np.abs(x_new - x).max() < 1e-7:
            x = x_new
            break
        x = x_new
    f = 0.0624 * x.sum()
    g = np.sum(c / x**3) - 1.0
    ok = abs(f - f_star) < 1e-5 and g < 1e-6 and np.abs(x - x_star).max() < 1e-3
    verdict("cantilever", ok, f"f {f:.6f} against {f_star:.6f}, constraint {g:+.1e}, x {np.round(x, 4).tolist()} against {np.round(x_star, 4).tolist()}, {it} iterations")


def toy() -> None:
    def f0(x):
        return float(x @ x)

    def cons(x):
        return np.array([(x[0] - 5) ** 2 + (x[1] - 2) ** 2 + (x[2] - 1) ** 2 - 9, (x[0] - 3) ** 2 + (x[1] - 4) ** 2 + (x[2] - 3) ** 2 - 9])

    def dcons(x):
        return np.array([[2 * (x[0] - 5), 2 * (x[1] - 2), 2 * (x[2] - 1)], [2 * (x[0] - 3), 2 * (x[1] - 4), 2 * (x[2] - 3)]])

    opt = MMA(3, 2, 0.0, 5.0)
    x = np.array([4.0, 3.0, 2.0])
    for it in range(1, 201):  # noqa: B007 (the count is read after the loop)
        x_new = opt.update(x, f0(x), 2 * x, cons(x), dcons(x))
        if np.abs(x_new - x).max() < 1e-8:
            x = x_new
            break
        x = x_new
    ref = minimize(f0, np.array([4.0, 3.0, 2.0]), jac=lambda v: 2 * v, method="SLSQP", bounds=[(0, 5)] * 3,
                   constraints=[{"type": "ineq", "fun": lambda v: -cons(v), "jac": lambda v: -dcons(v)}], tol=1e-12)  # fmt: skip
    ok = abs(f0(x) - ref.fun) < 1e-6 and cons(x).max() < 1e-6 and np.abs(x - ref.x).max() < 1e-4
    verdict("toy", ok, f"x {np.round(x, 5).tolist()} (SLSQP {np.round(ref.x, 5).tolist()}), f {f0(x):.6f} against {ref.fun:.6f}, {it} iterations")


def bound_problem() -> None:
    n, m_h = 60, 12
    rng = np.random.default_rng(7)
    j = np.arange(n)
    centres = np.linspace(4, n - 5, m_h) + rng.uniform(-2, 2, m_h)
    w = np.exp(-(((j[None, :] - centres[:, None]) / 6.0) ** 2)) + 0.02 * rng.uniform(size=(m_h, n))
    w *= rng.uniform(0.6, 1.4, size=(m_h, 1))
    budget = 0.3 * n

    def h(x):
        return w @ (1.0 / (x + 0.05))

    def dh(x):
        return -w / (x + 0.05) ** 2

    # MMA: constraints h_k - z <= 0 (a_k = 1) and sum(x)/budget - 1 <= 0 (a = 0); f0 = 0, a0 = 1.
    a = np.r_[np.ones(m_h), 0.0]
    opt = MMA(n, m_h + 1, 0.0, 1.0, a0=1.0, a=a, c=np.full(m_h + 1, 1000.0), d=np.ones(m_h + 1))
    x = np.full(n, 0.3)
    zs, worst_idx = [], []
    for it in range(1, 301):  # noqa: B007 (the count is read after the loop)
        f = np.r_[h(x), x.sum() / budget - 1.0]
        df = np.vstack([dh(x), np.full((1, n), 1.0 / budget)])
        x_new = opt.update(x, 0.0, np.zeros(n), f, df, move=0.2)
        zs.append(float(h(x).max()))
        worst_idx.append(int(np.argmax(h(x))))
        if np.abs(x_new - x).max() < 1e-7:
            x = x_new
            break
        x = x_new
    value = float(h(x).max())
    # SLSQP on the epigraph: variables (x, t), minimise t subject to t >= h_k(x), sum(x) <= budget.
    def obj(v):
        return v[-1]

    def jac(v):
        g = np.zeros(n + 1)
        g[-1] = 1.0
        return g

    cons = [
        {"type": "ineq", "fun": lambda v: v[-1] - h(v[:-1]), "jac": lambda v: np.hstack([-dh(v[:-1]), np.ones((m_h, 1))])},
        {"type": "ineq", "fun": lambda v: np.array([budget - v[:-1].sum()]), "jac": lambda v: np.r_[-np.ones(n), 0.0][None, :]},
    ]
    start = np.r_[np.full(n, 0.3), h(np.full(n, 0.3)).max()]
    ref = minimize(obj, start, jac=jac, method="SLSQP", bounds=[(0, 1)] * n + [(0, None)], constraints=cons, options={"maxiter": 2000, "ftol": 1e-14})
    active = int(np.sum(h(x) > value * (1 - 1e-4)))
    # Settled: the step fell below 1e-7 before the 300th iteration, and the last five values of
    # the worst constraint agree to 1e-6 (an alternation would keep two values apart).
    tail = np.array(zs[-5:])
    settled = it < 300 and np.ptp(tail) < 1e-6 * value
    ref_value = float(h(ref.x[:-1]).max())  # SLSQP's point judged as MMA's is: its worst h
    ok = abs(value - ref_value) < 1e-5 * ref_value and x.sum() <= budget * (1 + 1e-6) and settled
    verdict("bound (min-max)", ok, f"max h {value:.6f} (SLSQP {ref_value:.6f}, '{ref.message}'), {active} of {m_h} constraints active at the optimum, mass {x.sum() / budget:.6f} of the budget, {it} iterations; "
            f"worst h over the first 8: {[round(v, 4) for v in zs[:8]]}; the last 5 vary by {np.ptp(tail):.1e}")  # fmt: skip
    print(f"      (the worst constraint's index over the iterations: {worst_idx})")


def gcmma_run(opt: MMA, x, funcs, move: float, most: int = 300, inner_most: int = 15, promise: float | None = None):
    """GCMMA's loop: propose, check the promise at the proposal (one evaluation), tighten while it
    is broken (`promise` None: GCMMA's own test; a tolerance: the bound's weaker one, see
    `MMA._broken`); returns the point, the iterations, the inner iterations and the
    constraints' values at each accepted point. `funcs(x)` returns (f0, df0, f, df)."""
    f0, df0, f, df = funcs(x)
    worst, inners = [], 0
    for it in range(1, most + 1):  # noqa: B007 (the count is read after the loop)
        x_new = opt.propose(x, f0, df0, f, df, move=move)
        for _ in range(inner_most):
            f0_new, _, f_new, _ = funcs(x_new)
            if opt.conservative(f0_new, f_new, promise):
                break
            x_new = opt.tighten(f0_new, f_new, promise)
            inners += 1
        done = np.abs(x_new - x).max() < 1e-7
        x = x_new
        f0, df0, f, df = funcs(x)
        worst.append(f)
        if done:
            break
    return x, it, inners, worst


def gcmma_checks() -> None:
    # 1. the cantilever, by GCMMA
    c = np.array([61.0, 37.0, 19.0, 7.0, 1.0])
    k = np.sum(c**0.25) ** (1 / 3)
    f_star = 0.0624 * k * np.sum(c**0.25)

    def beam(x):
        return 0.0624 * x.sum(), np.full(5, 0.0624), np.array([np.sum(c / x**3) - 1.0]), (-3.0 * c / x**4)[None, :]

    x, it, inners, _ = gcmma_run(MMA(5, 1, 1.0, 10.0), np.full(5, 5.0), beam, move=0.5)
    f = 0.0624 * x.sum()
    verdict("cantilever by GCMMA", abs(f - f_star) < 1e-5 and np.sum(c / x**3) - 1 < 1e-6, f"f {f:.6f} against {f_star:.6f}, {it} iterations, {inners} inner")

    # 2. a misalignment-like bound problem: each "seat" the length of a 2-vector, both parts
    # signed sums of compliance-like terms 1/(x_j + 0.05), so its gradient takes both signs, as a
    # seat's misalignment does; the worst of 12 under a mass budget.
    n, m_h = 60, 12
    rng = np.random.default_rng(5)
    a1 = rng.normal(size=(m_h, n)) * 0.2 + np.exp(-((np.arange(n)[None, :] - np.linspace(5, n - 6, m_h)[:, None]) / 5.0) ** 2)
    a2 = rng.normal(size=(m_h, n)) * 0.2
    t1, t2 = rng.uniform(1.0, 3.0, m_h), rng.uniform(-1.0, 1.0, m_h)
    budget = 0.3 * n

    def seats(x):
        cc = 1.0 / (x + 0.05)
        v1, v2 = a1 @ cc - t1, a2 @ cc - t2
        hh = np.hypot(v1, v2)
        dc = -1.0 / (x + 0.05) ** 2
        dh = (v1[:, None] * a1 + v2[:, None] * a2) * dc[None, :] / np.maximum(hh, 1e-12)[:, None]
        return hh, dh

    def funcs(x):
        hh, dh = seats(x)
        return 0.0, np.zeros(n), np.r_[hh, x.sum() / budget - 1.0], np.vstack([dh, np.full((1, n), 1.0 / budget)])

    a = np.r_[np.ones(m_h), 0.0]
    results = {}
    for name in ("MMA", "GCMMA", "GCMMA, the bound's test", "GCMMA, the bound's test, carried"):
        opt = MMA(n, m_h + 1, 0.0, 1.0, a0=1.0, a=a, c=np.full(m_h + 1, 1000.0), d=np.ones(m_h + 1), carry=0.1 if "carried" in name else 0.0)
        x = np.full(n, 0.3)
        if name == "MMA":
            hist = []
            for it in range(1, 301):  # noqa: B007 (the count is read after the loop)
                _, _, f, df = funcs(x)
                x_new = opt.update(x, 0.0, np.zeros(n), f, df, move=0.2)
                done = np.abs(x_new - x).max() < 1e-7
                x = x_new
                hist.append(funcs(x)[2])
                if done:
                    break
            inners = 0
        else:
            x, it, inners, hist = gcmma_run(opt, x, funcs, move=0.2, promise=None if name == "GCMMA" else 1e-4)
        worst = np.array([h[:m_h].max() for h in hist])
        feasible = np.array([h[m_h] <= 1e-6 for h in hist])
        rises = int(np.sum((np.diff(worst) > 1e-9 * worst[0]) & feasible[1:] & feasible[:-1]))
        results[name] = (float(seats(x)[0].max()), it, inners, rises, worst)
    ref = minimize(lambda v: v[-1], np.r_[np.full(n, 0.3), seats(np.full(n, 0.3))[0].max()], jac=lambda v: np.r_[np.zeros(n), 1.0], method="SLSQP",
                   bounds=[(0, 1)] * n + [(0, None)], options={"maxiter": 3000, "ftol": 1e-14},
                   constraints=[{"type": "ineq", "fun": lambda v: v[-1] - seats(v[:-1])[0], "jac": lambda v: np.hstack([-seats(v[:-1])[1], np.ones((m_h, 1))])},
                                {"type": "ineq", "fun": lambda v: np.array([budget - v[:-1].sum()]), "jac": lambda v: np.r_[-np.ones(n), 0.0][None, :]}])  # fmt: skip
    ref_value = float(seats(ref.x[:-1])[0].max())
    g_value, g_it, g_inner, g_rises, g_worst = results["GCMMA"]
    b_value, b_it, b_inner, b_rises, b_worst = results["GCMMA, the bound's test"]
    m_value, m_it, _, m_rises, m_worst = results["MMA"]
    ok = g_rises == 0 and g_it < 300 and g_value <= ref_value * (1 + 1e-3)
    verdict("misalignment-like bound by GCMMA", ok, f"worst {g_value:.6f} after {g_it} iterations ({g_inner} inner), rises while feasible {g_rises}; "
            f"plain MMA {m_value:.6f} after {m_it} iterations, rises {m_rises}; SLSQP {ref_value:.6f}")  # fmt: skip
    ok = b_rises == 0 and b_it < 300 and b_value <= ref_value * (1 + 1e-3)
    verdict("the same by GCMMA with the bound's test", ok, f"worst {b_value:.6f} after {b_it} iterations ({b_inner} inner), rises while feasible {b_rises}")
    c_value, c_it, c_inner, c_rises, _ = results["GCMMA, the bound's test, carried"]
    ok = c_rises == 0 and c_it < 300 and c_value <= ref_value * (1 + 1e-3)
    verdict("the same, the convexity carried (topo.py's)", ok, f"worst {c_value:.6f} after {c_it} iterations ({c_inner} inner), rises while feasible {c_rises}")
    print(f"      the worst over the first 10 iterations, MMA:            {np.round(m_worst[:10], 4).tolist()}")
    print(f"      the worst over the first 10 iterations, GCMMA:          {np.round(g_worst[:10], 4).tolist()}")
    print(f"      the worst over the first 10 iterations, the bound's test: {np.round(b_worst[:10], 4).tolist()}")


def cost_at_size() -> None:
    n, m = 72_617, 13
    rng = np.random.default_rng(3)
    x = rng.uniform(0.0, 1.0, n)
    low, upp = x - 0.5, x + 0.5
    alpha, beta = np.maximum(0.0, x - 0.2), np.minimum(1.0, x + 0.2)
    df = rng.normal(size=(m, n)) * 1e-4
    ux2, xl2 = (upp - x) ** 2, (x - low) ** 2
    pp = (1.001 * np.maximum(df, 0) + 0.001 * np.maximum(-df, 0) + 1e-5) * ux2
    qq = (0.001 * np.maximum(df, 0) + 1.001 * np.maximum(-df, 0) + 1e-5) * xl2
    f = rng.uniform(0.5, 1.0, m)
    b = pp @ (1 / (upp - x)) + qq @ (1 / (x - low)) - f
    p0 = 1e-5 * ux2
    q0 = 1e-5 * xl2
    a = np.r_[np.ones(m - 1), 0.0]
    t0 = time.time()
    _, info = solve_subproblem(low, upp, alpha, beta, p0, q0, pp, qq, 1.0, a, b, np.full(m, 1000.0), np.ones(m))
    dt = time.time() - t0
    verdict("subproblem at the voxels' size", dt < 10.0, f"n {n:,}, m {m}: {dt:.2f} s, {info['newton_steps']} Newton steps")


if __name__ == "__main__":
    cantilever()
    toy()
    bound_problem()
    gcmma_checks()
    cost_at_size()
    print("all PASS" if all(RESULTS) else "SOME FAILED")
    sys.exit(0 if all(RESULTS) else 1)
