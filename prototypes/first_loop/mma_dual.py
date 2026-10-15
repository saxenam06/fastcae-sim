"""PROTOTYPE (LOP-20) - MMA's subproblem by its dual (Svanberg 1987, "The method of moving asymptotes",
section 4), for the plain problem, the one the compliance loops pose: no a_i, so MMA's extra
variable z is zero at the optimum (a0 > 0 and z enters nothing else), and with the m multipliers
fixed the subproblem falls apart into one closed-form problem a variable.

`mma.solve_subproblem` (the notes' primal-dual interior-point method) took about 1.3 s a
subproblem at 79,484 variables on the GPU (11 October 00:57: 3.9 s of a 5.8 s iteration, the
finite-element solves 0.5 s): some hundred Newton steps, each a few dozen passes over the variables
and ten transfers back from the card. The dual has m unknowns, here 2 to 14:

    W(lam) = min over alpha <= x <= beta, y >= 0 of
             sum_j (P_j / (u_j - x_j) + Q_j / (x_j - l_j)) - lam'b + sum_i (c_i y_i + d_i y_i^2/2 - lam_i y_i),
    P = p0 + pp' lam,  Q = q0 + qq' lam  (both >= 0: lam >= 0, every coefficient >= 0),

whose minimiser is explicit: x_j = (l_j sqrt(P_j) + u_j sqrt(Q_j)) / (sqrt(P_j) + sqrt(Q_j)), cut to
[alpha_j, beta_j] (the function is convex in x_j between the asymptotes), and y_i = max(0, (lam_i -
c_i) / d_i). W is concave; its gradient is each constraint's value at x(lam) less y and b, and its
Hessian -G diag(1/D) G' over the variables inside their bounds (G the constraints' slopes, D the
Lagrangian's curvature in x), less 1/d_i where y_i > 0. A projected Newton ascent on lam >= 0 with
backtracking takes some ten steps, each a few passes over the variables.

`solve_subproblem` takes and returns what `mma.solve_subproblem` does. A problem with some a_i not
zero (a bound problem, `topo.py`'s `misalignment_bound`) goes to the primal-dual method. On the GPU
(LOOP_FAST, at least `mma.GPU_LEAST` variables) the passes run in CuPy. `mma_dual_check.py` checks
it against the primal-dual method on the loop's own subproblems.
"""

from __future__ import annotations

import numpy as np

TOL = 1e-9  # the projected gradient's largest entry at the end, relative to 1 + |b_i|
MOST = 200  # Newton steps at most


def solve_subproblem(low, upp, alpha, beta, p0, q0, pp, qq, a0, a, b, c, d, epsimin=1e-7):
    """MMA's subproblem (`mma.solve_subproblem`'s arguments and result) by its dual."""
    import mma

    a_h = np.asarray(a, float)
    if np.any(a_h != 0.0) or float(a0) <= 0.0:
        return mma.solve_subproblem(low, upp, alpha, beta, p0, q0, pp, qq, a0, a, b, c, d, epsimin)
    n, m = len(low), len(b)
    on_gpu = mma.fast() and n >= mma.GPU_LEAST
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
        w = float(host(xp.sum(p_ * inv_u + q_ * inv_l))) - float(lam @ b_h) + float(np.sum(c_h * y_ + 0.5 * d_h * y_ * y_ - lam * y_))
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
    for steps in range(1, MOST + 1):
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
    x_ = parts[0]
    y_ = parts[5]
    return host(x_), {"z": 0.0, "y": np.asarray(y_, float), "lam": lam, "newton_steps": steps}
