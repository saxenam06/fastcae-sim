"""PROTOTYPE (LOP-16) - not product code: Svanberg's method of moving asymptotes (MMA) and its
globally convergent form (GCMMA).

The problem MMA solves (K. Svanberg, "MMA and GCMMA - two methods for nonlinear optimization",
KTH, 2007, section 1):

    minimise    f0(x) + a0 z + sum_i (c_i y_i + d_i y_i^2 / 2)
    subject to  f_i(x) - a_i z - y_i <= 0,   i = 1..m
                xmin_j <= x_j <= xmax_j,  y_i >= 0,  z >= 0.

z and y are extra variables. With a_i = 0 and large c_i the y_i are zero at a feasible optimum
and the problem is the plain one, min f0 subject to f_i <= 0. With f0 = 0, a0 = 1 and a_i = 1 on
some constraints it is a bound (min-max) problem: min z subject to f_i(x) <= z, which is how the
voxel optimisation minimises its worst seat (`topo.py`'s `misalignment_bound`). Every constraint
then keeps its own approximation and its own multiplier, so the step weighs every seat near the
worst at once instead of chasing whichever was worst last time.

Each iteration replaces every f_i by a convex separable approximation built from its value and
gradient at the current point,

    f_i ~ r_i + sum_j ( p_ij / (u_j - x_j) + q_ij / (x_j - l_j) ),

between moving asymptotes l < x < u (section 3 of the notes): they move apart while a variable
keeps going one way and close in when it oscillates, which is what damps a flip-flop. The
subproblem is solved by the notes' primal-dual interior-point method (section 5): Newton steps on
the relaxed KKT conditions with the barrier epsilon cut tenfold from 1 to 1e-7, the Newton
system reduced to the m multipliers and z (m is small, n is the voxels). The plain problem (no
a_i, as the compliance loops pose it) goes to its dual instead (`mma_dual.py`, since 11 October):
one unknown a constraint and every x_j in closed form, the exact optimum in a tenth of the time.

GCMMA (section 4) keeps MMA's subproblem but checks each proposal: one evaluation of the
functions there, and where an approximation fell below its function, a larger convexity term for
that approximation and the subproblem again from the same point, until every approximation lies
above its function at the proposal. Then the step keeps its promise. The voxel optimisation uses
it: plain MMA's approximations of the seats' misalignments, whose gradients take both signs,
promised more than the steps brought (`topo.solve_model`).

Written from the notes' formulas for this repository: numpy only, no other dependency. Checked
on analytic problems by `mma_check.py`.
"""

from __future__ import annotations

import os

import numpy as np


GPU_LEAST = 30_000  # variables: below this the card's launches cost more than NumPy's passes


def fast() -> bool:
    """Whether the subproblem runs on the GPU (`mma_gpu.py`, the same steps): the environment's
    LOOP_FAST, read at each call (LOP-19), for a problem of at least GPU_LEAST variables. On 76,000
    the card took 0.37 s to NumPy's 1.08; on a few thousand its fixed cost a step would lose."""
    return os.environ.get("LOOP_FAST", "0") != "0"


class MMA:
    """The method's state between iterations: the asymptotes and the two previous points.

    n variables, m constraints; `xmin`, `xmax` scalars or (n,) arrays. a0, a, c, d as in the
    problem above (defaults: a0 = 1, a = 0, c = 1000, d = 1, the notes' plain problem). `asyinit`,
    `asyincr`, `asydecr` and `albefa` are the notes' 0.5, 1.2, 0.7 and 0.1; `carry` (GCMMA,
    default 0, the notes' rule) the share of the last iteration's convexity terms the next one
    starts from.

    Two ways to step:
    - `update`: MMA, one subproblem per iteration, every approximation given the fixed small
      convexity term `raa0` (1e-5);
    - `propose`, then `conservative` and `tighten` until it is: GCMMA (section 4 of the notes).
      MMA's approximations need not lie above the functions they stand for, so a step can promise
      more than it brings and the next one undo it. GCMMA checks the promise at the proposed point
      (one evaluation of the functions, no gradients) and, where an approximation fell below its
      function, raises that approximation's convexity term and solves again from the same point:
      the step shrinks only where it was too bold. Its convexity terms start each iteration at a
      tenth of the gradients' mean size, so it does not depend on how the functions are scaled."""

    def __init__(self, n: int, m: int, xmin, xmax, a0: float = 1.0, a=None, c=None, d=None,
                 asyinit: float = 0.5, asyincr: float = 1.2, asydecr: float = 0.7,
                 albefa: float = 0.1, raa0: float = 1e-5, epsimin: float = 1e-7,
                 raa_least: float = 1e-6, carry: float = 0.0) -> None:  # fmt: skip
        self.n, self.m = n, m
        self.xmin = np.broadcast_to(np.asarray(xmin, float), (n,)).copy()
        self.xmax = np.broadcast_to(np.asarray(xmax, float), (n,)).copy()
        self.a0 = float(a0)
        self.a = np.zeros(m) if a is None else np.asarray(a, float).copy()
        self.c = np.full(m, 1000.0) if c is None else np.asarray(c, float).copy()
        self.d = np.ones(m) if d is None else np.asarray(d, float).copy()
        self.asyinit, self.asyincr, self.asydecr = asyinit, asyincr, asydecr
        self.albefa, self.raa0, self.epsimin, self.raa_least = albefa, raa0, epsimin, raa_least
        self.carry = carry  # GCMMA: the share of the last iteration's convexity terms the next starts from
        self.span = np.maximum(self.xmax - self.xmin, 1e-5)
        self.iteration = 0
        self.xold1 = self.xold2 = None
        self.low = self.upp = None
        self.last = {}  # the last subproblem's z, y, multipliers, Newton steps and approximations
        self._step = None  # GCMMA: the iteration under way (its point, data and convexity terms)

    def restart(self) -> None:
        """Forget the history: the next step sets the asymptotes afresh (after the problem itself
        changed, e.g. a projection sharpened)."""
        self.iteration = 0
        self.xold1 = self.xold2 = None

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
        return {"x": x, "f0": float(f0), "df0": df0, "f": f, "df": df, "low": low, "upp": upp, "alpha": alpha, "beta": beta}

    def _solve(self, step, raa0: float, raa) -> np.ndarray:
        """The subproblem at the iteration's point with the convexity terms raa0, raa (m,); keeps
        the approximations' values at its optimum (`last["f0app"]`, `last["fapp"]`)."""
        x, low, upp = step["x"], step["low"], step["upp"]
        ux1, xl1 = upp - x, x - low
        ux2, xl2 = ux1 * ux1, xl1 * xl1
        df0, df = step["df0"], step["df"]
        # The approximations' coefficients (section 3; GCMMA's raa in place of MMA's fixed one).
        p0 = (1.001 * np.maximum(df0, 0) + 0.001 * np.maximum(-df0, 0) + raa0 / self.span) * ux2
        q0 = (0.001 * np.maximum(df0, 0) + 1.001 * np.maximum(-df0, 0) + raa0 / self.span) * xl2
        tiny = np.asarray(raa, float).reshape(-1, 1) / self.span[None, :]
        pp = (1.001 * np.maximum(df, 0) + 0.001 * np.maximum(-df, 0) + tiny) * ux2
        qq = (0.001 * np.maximum(df, 0) + 1.001 * np.maximum(-df, 0) + tiny) * xl2
        r0 = step["f0"] - float(p0 @ (1.0 / ux1) + q0 @ (1.0 / xl1))
        r = step["f"] - (pp @ (1.0 / ux1) + qq @ (1.0 / xl1))
        solve = solve_subproblem
        if not np.any(self.a) and os.environ.get("LOOP_MMA", "dual") == "dual":
            # The plain problem (no a_i: z drops out) by its dual (`mma_dual.py`, LOP-20, 11 October):
            # the exact optimum, where the interior-point method stops 1e-7 short, in a tenth of the
            # time (`mma_dual_check.py`); LOOP_MMA=primal-dual keeps the notes' method
            from mma_dual import solve_subproblem as solve
        elif fast() and self.n >= GPU_LEAST:
            from mma_gpu import solve_subproblem as solve
        x_new, info = solve(low, upp, step["alpha"], step["beta"], p0, q0, pp, qq, self.a0, self.a, -r, self.c, self.d, self.epsimin)
        u_new, l_new = 1.0 / (upp - x_new), 1.0 / (x_new - low)
        info["f0app"] = r0 + float(p0 @ u_new + q0 @ l_new)
        info["fapp"] = r + pp @ u_new + qq @ l_new
        step["x_new"] = x_new
        self.last = info
        return x_new

    def update(self, x, f0: float, df0, f, df, move: float = 0.5) -> np.ndarray:
        """One MMA iteration from x: f0 and df0 (n,) the objective and its gradient, f (m,) and
        df (m, n) the constraints and theirs, `move` the step limit as a share of xmax - xmin.
        Returns the subproblem's optimum, the next point."""
        step = self._begin(x, f0, df0, f, df, move)
        return self._solve(step, self.raa0, np.full(self.m, self.raa0))

    def propose(self, x, f0: float, df0, f, df, move: float = 0.5) -> np.ndarray:
        """GCMMA's iteration from x (the arguments as `update`'s): the first proposal. Its
        convexity terms are a tenth of each function's mean gradient size (the notes' start, at
        least `raa_least`), or a tenth of where the last iteration's ended if that is more (with
        `carry`): where the gradients gather on a few variables, as a seat's do on the voxels
        round it, their mean is far below the convexity the step needs, and each inner iteration
        may raise a term only tenfold. Evaluate the functions there and ask `conservative`;
        while not, `tighten`."""
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

    def _broken(self, f0_new: float, f_new, promise: float | None):
        """Which approximations broke the last proposal's terms: (objective, constraints (m,)).
        With `promise` None, GCMMA's own test: an approximation below its function there (to
        `epsimin`). With a tolerance, the weaker test that is enough for a bound problem: the true
        functions meet the subproblem's own constraints with its z and y, f_i - a_i z - y_i <=
        `promise` (an inactive constraint may be underestimated as long as it stays below the
        bound), and the objective keeps to its approximation within `promise`. Then the true
        point achieves the subproblem's value: the bound falls."""
        info = self.last
        f_new = np.asarray(f_new, float).reshape(self.m)
        if promise is None:
            return f0_new > info["f0app"] + self.epsimin, f_new > info["fapp"] + self.epsimin
        return f0_new > info["f0app"] + promise, f_new - self.a * info["z"] - info["y"] > promise

    def conservative(self, f0_new: float, f_new, promise: float | None = None) -> bool:
        """Whether the last proposal keeps its promise at the functions' values there (`_broken`
        says by which test): then the step may be taken."""
        obj, cons = self._broken(f0_new, f_new, promise)
        return not obj and not bool(np.any(cons))

    def tighten(self, f0_new: float, f_new, promise: float | None = None) -> np.ndarray:
        """GCMMA's inner iteration: raise the convexity term of every approximation that broke
        the proposal's terms (`_broken`), by enough to have covered its shortfall there (times
        1.1, at most tenfold), and solve again from the same point. Returns the new proposal."""
        step, info = self._step, self.last
        f_new = np.asarray(f_new, float).reshape(self.m)
        x, x_new, low, upp = step["x"], step["x_new"], step["low"], step["upp"]
        # d(x_new): how much a unit of raa adds to an approximation at x_new (the notes' d_k).
        dist = float(np.sum((x_new - x) ** 2 * (upp - low) / ((upp - x_new) * (x_new - low) * self.span)))
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


def solve_subproblem(low, upp, alpha, beta, p0, q0, pp, qq, a0, a, b, c, d, epsimin=1e-7):
    """The MMA subproblem by the notes' primal-dual interior-point method (section 5):

        min  sum_j (p0_j/(u_j - x_j) + q0_j/(x_j - l_j)) + a0 z + sum_i (c_i y_i + d_i y_i^2/2)
        s.t. sum_j (pp_ij/(u_j - x_j) + qq_ij/(x_j - l_j)) - a_i z - y_i <= b_i,
             alpha <= x <= beta, y >= 0, z >= 0.

    Newton steps on the KKT conditions relaxed by epsilon (every complementarity product equal to
    epsilon), epsilon cut tenfold from 1 to `epsimin`; each step kept inside the positive
    variables' bounds and halved until the residual falls. The Newton system is reduced to the m
    multipliers and z when m < n, else to x and z. Returns (x, info)."""
    n, m = len(low), len(b)
    x = 0.5 * (alpha + beta)
    y = np.ones(m)
    z = 1.0
    lam = np.ones(m)
    xsi = np.maximum(1.0 / (x - alpha), 1.0)
    eta = np.maximum(1.0 / (beta - x), 1.0)
    mu = np.maximum(np.ones(m), 0.5 * c)
    zet = 1.0
    s = np.ones(m)
    epsi = 1.0
    steps = 0

    def residual(x, y, z, lam, xsi, eta, mu, zet, s, epsi):
        ux1, xl1 = upp - x, x - low
        plam = p0 + pp.T @ lam
        qlam = q0 + qq.T @ lam
        gvec = pp @ (1.0 / ux1) + qq @ (1.0 / xl1)
        dpsidx = plam / ux1**2 - qlam / xl1**2
        parts = [
            dpsidx - xsi + eta,  # stationarity in x
            c + d * y - mu - lam,  # in y
            [a0 - zet - a @ lam],  # in z
            gvec - a * z - y + s - b,  # the constraints with their slacks
            xsi * (x - alpha) - epsi,  # complementarity, relaxed
            eta * (beta - x) - epsi,
            mu * y - epsi,
            [zet * z - epsi],
            lam * s - epsi,
        ]
        r = np.concatenate([np.asarray(p, float).ravel() for p in parts])
        return float(np.sqrt(r @ r)), float(np.abs(r).max())

    while epsi > epsimin:
        norm, worst = residual(x, y, z, lam, xsi, eta, mu, zet, s, epsi)
        inner = 0
        while worst > 0.9 * epsi and inner < 200:
            inner += 1
            steps += 1
            ux1, xl1 = upp - x, x - low
            ux2, xl2 = ux1 * ux1, xl1 * xl1
            plam = p0 + pp.T @ lam
            qlam = q0 + qq.T @ lam
            gvec = pp @ (1.0 / ux1) + qq @ (1.0 / xl1)
            gg = pp / ux2 - qq / xl2  # (m, n): the constraints' gradients in x
            dpsidx = plam / ux2 - qlam / xl2
            delx = dpsidx - epsi / (x - alpha) + epsi / (beta - x)
            dely = c + d * y - lam - epsi / y
            delz = a0 - a @ lam - epsi / z
            dellam = gvec - a * z - y - b + epsi / lam
            diagx = 2.0 * (plam / (ux2 * ux1) + qlam / (xl2 * xl1)) + xsi / (x - alpha) + eta / (beta - x)
            diagy = d + mu / y
            diaglamyi = s / lam + 1.0 / diagy
            if m < n:
                blam = dellam + dely / diagy - gg @ (delx / diagx)
                big = np.empty((m + 1, m + 1))
                big[:m, :m] = (gg / diagx) @ gg.T + np.diag(diaglamyi)
                big[:m, m] = a
                big[m, :m] = a
                big[m, m] = -zet / z
                sol = np.linalg.solve(big, np.concatenate([blam, [delz]]))
                dlam, dz = sol[:m], sol[m]
                dx = -delx / diagx - (gg.T @ dlam) / diagx
            else:
                dellamyi = dellam + dely / diagy
                axx = np.diag(diagx) + (gg.T / diaglamyi) @ gg
                azz = zet / z + a @ (a / diaglamyi)
                axz = -gg.T @ (a / diaglamyi)
                bx = delx + gg.T @ (dellamyi / diaglamyi)
                bz = delz - a @ (dellamyi / diaglamyi)
                big = np.empty((n + 1, n + 1))
                big[:n, :n] = axx
                big[:n, n] = axz
                big[n, :n] = axz
                big[n, n] = azz
                sol = np.linalg.solve(big, -np.concatenate([bx, [bz]]))
                dx, dz = sol[:n], sol[n]
                dlam = (gg @ dx) / diaglamyi - dz * (a / diaglamyi) + dellamyi / diaglamyi
            dy = -dely / diagy + dlam / diagy
            dxsi = -xsi + epsi / (x - alpha) - (xsi * dx) / (x - alpha)
            deta = -eta + epsi / (beta - x) + (eta * dx) / (beta - x)
            dmu = -mu + epsi / y - (mu * dy) / y
            dzet = -zet + epsi / z - zet * dz / z
            ds = -s + epsi / lam - (s * dlam) / lam
            # The longest step that keeps every positive variable positive and x inside its
            # bounds, by a margin of 1 %.
            positive = np.concatenate([y, [z], lam, xsi, eta, mu, [zet], s])
            dpositive = np.concatenate([dy, [dz], dlam, dxsi, deta, dmu, [dzet], ds])
            most = max(
                float(np.max(-1.01 * dpositive / positive)),
                float(np.max(-1.01 * dx / (x - alpha))),
                float(np.max(1.01 * dx / (beta - x))),
                1.0,
            )
            step = 1.0 / most
            old = (x, y, z, lam, xsi, eta, mu, zet, s)
            for _ in range(50):  # halved until the residual falls
                trial = (old[0] + step * dx, old[1] + step * dy, old[2] + step * dz, old[3] + step * dlam,
                         old[4] + step * dxsi, old[5] + step * deta, old[6] + step * dmu,
                         old[7] + step * dzet, old[8] + step * ds)  # fmt: skip
                new_norm, new_worst = residual(*trial, epsi)
                if new_norm < norm:
                    break
                step /= 2.0
            x, y, z, lam, xsi, eta, mu, zet, s = trial
            norm, worst = new_norm, new_worst
        epsi *= 0.1
    return x, {"z": float(z), "y": y, "lam": lam, "newton_steps": steps}
