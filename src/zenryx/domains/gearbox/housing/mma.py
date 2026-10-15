"""Svanberg's globally convergent method of moving asymptotes (GCMMA), for the plain problem the
least-mass loop poses (moved from `prototypes/first_loop/mma.py`: `MMA` without `update` and
`restart`, and `mma_dual.py`: `solve_subproblem`; LOP-16, LOP-20, LOP-33).

The problem (K. Svanberg, "MMA and GCMMA - two methods for nonlinear optimization", KTH, 2007,
section 1): minimise f0(x) subject to f_i(x) <= 0, xmin <= x <= xmax, with MMA's extra variables y_i
(c_i y_i + d_i y_i^2 / 2, large c_i: zero at a feasible optimum) and z (a_i = 0: zero). Each
iteration replaces every f_i by a convex separable approximation from its value and gradient,

    f_i ~ r_i + sum_j ( p_ij / (u_j - x_j) + q_ij / (x_j - l_j) ),

between moving asymptotes l < x < u, which move apart while a variable keeps going one way and close
in when it oscillates. GCMMA (section 4) checks each proposal: one evaluation of the functions
there, and where an approximation fell below its function, a larger convexity term for that
approximation and the subproblem again from the same point, so a step keeps its promise.

The subproblem is solved by its dual (Svanberg 1987, section 4): with no a_i, the m multipliers
fixed, it falls apart into one closed-form problem a variable, x_j = (l_j sqrt(P_j) + u_j sqrt(Q_j))
/ (sqrt(P_j) + sqrt(Q_j)) cut to [alpha_j, beta_j]; the dual is concave, and a projected Newton
ascent on lam >= 0 with backtracking takes some ten steps. On the GPU from `GPU_LEAST` variables.
"""

from __future__ import annotations

import numpy as np

GPU_LEAST = 30_000  # variables: below this the card's launches cost more than NumPy's passes
TOL = 1e-9  # the dual's projected gradient's largest entry at the end, relative to 1 + |b_i|
MOST = 200  # the dual's Newton steps at most


class MMA:
    """The method's state between iterations: the asymptotes and the two previous points. n
    variables, m constraints; `xmin`, `xmax` scalars or (n,) arrays; a0, a, c, d as in the problem
    (a must be zero: the plain problem). `asyinit`, `asyincr`, `asydecr` and `albefa` are the notes'
    0.5, 1.2, 0.7 and 0.1; `carry` the share of the last iteration's convexity terms the next one
    starts from. Step by `propose`, then `conservative` and `tighten` until it is."""

    def __init__(
        self,
        n: int,
        m: int,
        xmin,
        xmax,
        a0: float = 1.0,
        a=None,
        c=None,
        d=None,
        asyinit: float = 0.5,
        asyincr: float = 1.2,
        asydecr: float = 0.7,
        albefa: float = 0.1,
        epsimin: float = 1e-7,
        raa_least: float = 1e-6,
        carry: float = 0.0,
    ) -> None:
        self.n, self.m = n, m
        self.xmin = np.broadcast_to(np.asarray(xmin, float), (n,)).copy()
        self.xmax = np.broadcast_to(np.asarray(xmax, float), (n,)).copy()
        self.a0 = float(a0)
        self.a = np.zeros(m) if a is None else np.asarray(a, float).copy()
        if np.any(self.a) or self.a0 <= 0.0:
            raise ValueError("the dual solves the plain problem only: a = 0, a0 > 0")
        self.c = np.full(m, 1000.0) if c is None else np.asarray(c, float).copy()
        self.d = np.ones(m) if d is None else np.asarray(d, float).copy()
        self.asyinit, self.asyincr, self.asydecr = asyinit, asyincr, asydecr
        self.albefa, self.epsimin, self.raa_least = albefa, epsimin, raa_least
        self.carry = carry
        self.span = np.maximum(self.xmax - self.xmin, 1e-5)
        self.iteration = 0
        self.xold1 = self.xold2 = None
        self.low = self.upp = None
        self.last = {}  # the last subproblem's z, y, multipliers, Newton steps and approximations
        self._step = None  # the iteration under way (its point, data and convexity terms)

    def _asymptotes(self, x):
        """The asymptotes (section 3): wide at first, then opened while each variable keeps going
        one way and closed in when it turns back."""
        span = self.xmax - self.xmin
        if self.iteration <= 2 or self.xold2 is None:
            return x - self.asyinit * span, x + self.asyinit * span
        trend = (x - self.xold1) * (self.xold1 - self.xold2)
        gamma = np.ones(self.n)
        gamma[trend > 0] = self.asyincr
        gamma[trend < 0] = self.asydecr
        low = np.clip(x - gamma * (self.xold1 - self.low), x - 10.0 * span, x - 0.01 * span)
        upp = np.clip(x + gamma * (self.upp - self.xold1), x + 0.01 * span, x + 10.0 * span)
        return low, upp

    def _begin(self, x, f0, df0, f, df, move):
        """An iteration's fixed parts: the asymptotes, the subproblem's bounds (inside the
        asymptotes, the move limit and the box), the data; the history moves on."""
        x = np.asarray(x, float)
        df0 = np.broadcast_to(np.asarray(df0, float), (self.n,))
        f = np.asarray(f, float).reshape(self.m)
        df = np.asarray(df, float).reshape(self.m, self.n)
        self.iteration += 1
        low, upp = self._asymptotes(x)
        span = self.xmax - self.xmin
        alpha = np.maximum.reduce([self.xmin, low + self.albefa * (x - low), x - move * span])
        beta = np.minimum.reduce([self.xmax, upp - self.albefa * (upp - x), x + move * span])
        self.xold2, self.xold1 = self.xold1, x.copy()
        self.low, self.upp = low, upp
        return {
            "x": x,
            "f0": float(f0),
            "df0": df0,
            "f": f,
            "df": df,
            "low": low,
            "upp": upp,
            "alpha": alpha,
            "beta": beta,
        }

    def _solve(self, step, raa0: float, raa) -> np.ndarray:
        """The subproblem at the iteration's point with the convexity terms raa0, raa (m,); keeps
        the approximations' values at its optimum (`last["f0app"]`, `last["fapp"]`)."""
        x, low, upp = step["x"], step["low"], step["upp"]
        ux1, xl1 = upp - x, x - low
        ux2, xl2 = ux1 * ux1, xl1 * xl1
        df0, df = step["df0"], step["df"]
        p0 = (1.001 * np.maximum(df0, 0) + 0.001 * np.maximum(-df0, 0) + raa0 / self.span) * ux2
        q0 = (0.001 * np.maximum(df0, 0) + 1.001 * np.maximum(-df0, 0) + raa0 / self.span) * xl2
        tiny = np.asarray(raa, float).reshape(-1, 1) / self.span[None, :]
        pp = (1.001 * np.maximum(df, 0) + 0.001 * np.maximum(-df, 0) + tiny) * ux2
        qq = (0.001 * np.maximum(df, 0) + 1.001 * np.maximum(-df, 0) + tiny) * xl2
        r0 = step["f0"] - float(p0 @ (1.0 / ux1) + q0 @ (1.0 / xl1))
        r = step["f"] - (pp @ (1.0 / ux1) + qq @ (1.0 / xl1))
        x_new, info = solve_subproblem(
            low, upp, step["alpha"], step["beta"], p0, q0, pp, qq, -r, self.c, self.d
        )
        u_new, l_new = 1.0 / (upp - x_new), 1.0 / (x_new - low)
        info["f0app"] = r0 + float(p0 @ u_new + q0 @ l_new)
        info["fapp"] = r + pp @ u_new + qq @ l_new
        step["x_new"] = x_new
        self.last = info
        return x_new

    def propose(self, x, f0: float, df0, f, df, move: float = 0.5) -> np.ndarray:
        """GCMMA's iteration from x: f0 and df0 (n,) the objective and its gradient, f (m,) and df
        (m, n) the constraints and theirs, `move` the step limit as a share of xmax - xmin; the
        first proposal. Its convexity terms are a tenth of each function's mean gradient size (at
        least `raa_least`), or `carry` of where the last iteration's ended if that is more."""
        last = self._step
        step = self._begin(x, f0, df0, f, df, move)
        step["raa0"] = max(self.raa_least, 0.1 / self.n * float(np.abs(step["df0"]) @ self.span))
        step["raa"] = np.maximum(self.raa_least, 0.1 / self.n * (np.abs(step["df"]) @ self.span))
        if self.carry and last is not None:
            step["raa0"] = max(step["raa0"], self.carry * last["raa0"])
            step["raa"] = np.maximum(step["raa"], self.carry * last["raa"])
        step["inner"] = 0
        self._step = step
        return self._solve(step, step["raa0"], step["raa"])

    def _broken(self, f0_new: float, f_new, promise: float):
        """Which approximations broke the last proposal's terms: (objective, constraints (m,)). The
        true functions must meet the subproblem's own constraints with its z and y, f_i - a_i z
        - y_i <= `promise`, and the objective keep to its approximation within `promise`."""
        info = self.last
        f_new = np.asarray(f_new, float).reshape(self.m)
        return f0_new > info["f0app"] + promise, f_new - self.a * info["z"] - info["y"] > promise

    def conservative(self, f0_new: float, f_new, promise: float) -> bool:
        """Whether the last proposal keeps its promise at the functions' values there."""
        obj, cons = self._broken(f0_new, f_new, promise)
        return not obj and not bool(np.any(cons))

    def tighten(self, f0_new: float, f_new, promise: float) -> np.ndarray:
        """GCMMA's inner iteration: raise the convexity term of every approximation that broke the
        proposal's terms, by enough to have covered its shortfall there (times 1.1, at most
        tenfold), and solve again from the same point. Returns the new proposal."""
        step, info = self._step, self.last
        f_new = np.asarray(f_new, float).reshape(self.m)
        x, x_new, low, upp = step["x"], step["x_new"], step["low"], step["upp"]
        # d(x_new): how much a unit of raa adds to an approximation at x_new (the notes' d_k)
        dist = float(
            np.sum((x_new - x) ** 2 * (upp - low) / ((upp - x_new) * (x_new - low) * self.span))
        )
        dist = max(dist, 1e-12)
        obj, cons = self._broken(f0_new, f_new, promise)
        short0 = max(f0_new - info["f0app"], 0.0)
        if obj:
            step["raa0"] = min(1.1 * (step["raa0"] + short0 / dist), 10.0 * step["raa0"])
        short = np.maximum(f_new - info["fapp"], 0.0)
        grown = np.minimum(1.1 * (step["raa"] + short / dist), 10.0 * step["raa"])
        step["raa"] = np.where(cons, grown, step["raa"])
        step["inner"] += 1
        return self._solve(step, step["raa0"], step["raa"])


def solve_subproblem(low, upp, alpha, beta, p0, q0, pp, qq, b, c, d):
    """MMA's subproblem with no a_i, by its dual: the subproblem's optimum x and {"z": 0, "y",
    "lam", "newton_steps"}."""
    n, m = len(low), len(b)
    on_gpu = n >= GPU_LEAST
    if on_gpu:
        import cupy as xp
    else:
        xp = np
    g = xp.asarray
    low, upp, alpha, beta, p0, q0, pp, qq = (g(v) for v in (low, upp, alpha, beta, p0, q0, pp, qq))
    b_h, c_h, d_h = (np.asarray(v, float) for v in (b, c, d))
    host = (lambda v: xp.asnumpy(v)) if on_gpu else (lambda v: np.asarray(v))

    def primal(lam):
        """x(lam), and the parts the dual's value, gradient and Hessian need."""
        lam_d = g(lam)
        p_ = p0 + lam_d @ pp
        q_ = q0 + lam_d @ qq
        sp_, sq_ = xp.sqrt(p_), xp.sqrt(q_)
        x_ = (low * sp_ + upp * sq_) / (sp_ + sq_ + 1e-300)
        x_ = xp.minimum(xp.maximum(x_, alpha), beta)
        ux, xl = upp - x_, x_ - low
        return x_, p_, q_, ux, xl

    def value_and_gradient(lam):
        x_, p_, q_, ux, xl = primal(lam)
        y_ = np.maximum(0.0, (lam - c_h) / d_h)
        inv_u, inv_l = 1.0 / ux, 1.0 / xl
        cons = host(pp @ inv_u + qq @ inv_l)  # each constraint's approximation at x(lam)
        w = (
            float(host(xp.sum(p_ * inv_u + q_ * inv_l)))
            - float(lam @ b_h)
            + float(np.sum(c_h * y_ + 0.5 * d_h * y_ * y_ - lam * y_))
        )
        return w, cons - y_ - b_h, (x_, p_, q_, ux, xl, y_)

    def hessian(parts, lam):
        x_, p_, q_, ux, xl, y_ = parts
        inside = (x_ > alpha) & (x_ < beta)
        gg = pp / (ux * ux) - qq / (xl * xl)  # (m, n): the constraints' slopes in x
        curv = 2.0 * p_ / (ux * ux * ux) + 2.0 * q_ / (xl * xl * xl)
        weight = xp.where(inside, 1.0 / curv, 0.0)
        h_ = -host((gg * weight) @ gg.T)
        h_ -= np.diag(np.where(lam > c_h, 1.0 / d_h, 0.0))
        return h_

    lam = np.zeros(m)
    w, grad, parts = value_and_gradient(lam)
    steps = 0
    scale = 1.0 + np.abs(b_h)
    for steps in range(1, MOST + 1):  # noqa: B007 (read after the loop)
        held = (lam <= 0.0) & (grad < 0.0)  # at the bound and pushed into it: stays at zero
        free = ~held
        if not free.any() or np.max(np.abs(grad[free]) / scale[free]) <= TOL:
            break
        h_ = hessian(parts, lam)
        hf = h_[np.ix_(free, free)]
        reg = 1e-14 * max(1.0, float(np.max(np.abs(np.diag(hf))))) if hf.size else 0.0
        try:
            step_f = np.linalg.solve(hf - reg * np.eye(len(hf)), -grad[free])
        except np.linalg.LinAlgError:
            step_f = np.linalg.lstsq(hf - reg * np.eye(len(hf)), -grad[free], rcond=None)[0]
        direction = np.zeros(m)
        direction[free] = step_f
        if float(direction @ grad) <= 0.0:  # not an ascent (a flat or broken Hessian): the gradient
            direction = np.where(free, grad, 0.0)
        t, taken = 1.0, False
        for _ in range(60):  # backtracking on the dual's value (Armijo, projected)
            trial = np.maximum(0.0, lam + t * direction)
            w_t, grad_t, parts_t = value_and_gradient(trial)
            if w_t >= w + 1e-4 * float(grad @ (trial - lam)):
                taken = True
                break
            t *= 0.5
        if not taken:
            break
        lam, w, grad, parts = trial, w_t, grad_t, parts_t
    return host(parts[0]), {
        "z": 0.0,
        "y": np.asarray(parts[5], float),
        "lam": lam,
        "newton_steps": steps,
    }
