"""PROTOTYPE (LOP-19) - MMA's subproblem on the GPU: `mma.solve_subproblem`, the same primal-dual
interior-point method step for step (Svanberg's notes, section 5), its arithmetic over the n
variables done by CuPy instead of NumPy.

Why: on 76,000 voxels the NumPy version took 4.9-8.0 s of an iteration's 15-19 s (LOP-18's log,
10 October 15:00), every Newton step some 25 passes over the variables, every pass a few tenths of
a millisecond, up to 8 barrier levels of steps, and GCMMA solving it up to three times an
iteration. The same passes on the card cost microseconds each. The Newton system reduced to the m
multipliers and z is (m + 1) square, so it is solved on the CPU; only the reductions that decide a
step (the residual's norm and worst entry, the longest feasible step) come back, one transfer each.

`solve_subproblem` takes and returns NumPy arrays, as `mma.solve_subproblem` does, so `mma.MMA`
can call either (`mma.SUBPROBLEM`). `mma_gpu_check.py` checks that both give the same point.
"""

from __future__ import annotations

import numpy as np


def solve_subproblem(low, upp, alpha, beta, p0, q0, pp, qq, a0, a, b, c, d, epsimin=1e-7):
    """`mma.solve_subproblem` on the GPU: the same arguments (NumPy arrays), the same result."""
    import cupy as cp

    n, m = len(low), len(b)
    if m >= n:  # the x-and-z reduction is for many constraints: leave it to NumPy
        from mma import solve_subproblem as on_cpu

        return on_cpu(low, upp, alpha, beta, p0, q0, pp, qq, a0, a, b, c, d, epsimin)
    g = cp.asarray
    low, upp, alpha, beta = g(low), g(upp), g(alpha), g(beta)
    p0, q0, pp, qq = g(p0), g(q0), g(pp), g(qq)
    a_h = np.asarray(a, float)  # the m-sized data, on both sides
    b, c, d, a = g(b), g(c), g(d), g(a_h)
    a0 = float(a0)

    x = 0.5 * (alpha + beta)
    y = cp.ones(m)
    z = 1.0
    lam = cp.ones(m)
    xsi = cp.maximum(1.0 / (x - alpha), 1.0)
    eta = cp.maximum(1.0 / (beta - x), 1.0)
    mu = cp.maximum(cp.ones(m), 0.5 * c)
    zet = 1.0
    s = cp.ones(m)
    epsi = 1.0
    steps = 0

    def residual(x, y, z, lam, xsi, eta, mu, zet, s, epsi):
        """The relaxed KKT residual's 2-norm and largest entry (`mma.solve_subproblem`'s)."""
        ux1, xl1 = upp - x, x - low
        plam = p0 + pp.T @ lam
        qlam = q0 + qq.T @ lam
        gvec = pp @ (1.0 / ux1) + qq @ (1.0 / xl1)
        dpsidx = plam / ux1**2 - qlam / xl1**2
        parts = [
            dpsidx - xsi + eta,  # stationarity in x
            c + d * y - mu - lam,  # in y
            gvec - a * z - y + s - b,  # the constraints with their slacks
            xsi * (x - alpha) - epsi,  # complementarity, relaxed
            eta * (beta - x) - epsi,
            mu * y - epsi,
            lam * s - epsi,
        ]
        sums = cp.stack([cp.sum(p * p) for p in parts])
        tops = cp.stack([cp.max(cp.abs(p)) for p in parts])
        sums_h, tops_h = cp.asnumpy(sums), cp.asnumpy(tops)
        in_z = float(a0 - zet - float(a_h @ cp.asnumpy(lam)))  # in z
        relax_z = zet * z - epsi
        norm = float(np.sqrt(sums_h.sum() + in_z**2 + relax_z**2))
        worst = float(max(tops_h.max(), abs(in_z), abs(relax_z)))
        return norm, worst

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
            delz = a0 - float(a_h @ cp.asnumpy(lam)) - epsi / z
            dellam = gvec - a * z - y - b + epsi / lam
            diagx = 2.0 * (plam / (ux2 * ux1) + qlam / (xl2 * xl1)) + xsi / (x - alpha) + eta / (beta - x)
            diagy = d + mu / y
            diaglamyi = s / lam + 1.0 / diagy
            blam = dellam + dely / diagy - gg @ (delx / diagx)
            big = np.empty((m + 1, m + 1))
            big[:m, :m] = cp.asnumpy((gg / diagx) @ gg.T + cp.diag(diaglamyi))
            big[:m, m] = a_h
            big[m, :m] = a_h
            big[m, m] = -zet / z
            sol = np.linalg.solve(big, np.concatenate([cp.asnumpy(blam), [delz]]))
            dlam, dz = cp.asarray(sol[:m]), float(sol[m])
            dx = -delx / diagx - (gg.T @ dlam) / diagx
            dy = -dely / diagy + dlam / diagy
            dxsi = -xsi + epsi / (x - alpha) - (xsi * dx) / (x - alpha)
            deta = -eta + epsi / (beta - x) + (eta * dx) / (beta - x)
            dmu = -mu + epsi / y - (mu * dy) / y
            dzet = -zet + epsi / z - zet * dz / z
            ds = -s + epsi / lam - (s * dlam) / lam
            # The longest step that keeps every positive variable positive and x inside its
            # bounds, by a margin of 1 % (the same rule as on the CPU).
            ratios = cp.stack(
                [
                    cp.max(-1.01 * dy / y),
                    cp.max(-1.01 * dlam / lam),
                    cp.max(-1.01 * dxsi / xsi),
                    cp.max(-1.01 * deta / eta),
                    cp.max(-1.01 * dmu / mu),
                    cp.max(-1.01 * ds / s),
                    cp.max(-1.01 * dx / (x - alpha)),
                    cp.max(1.01 * dx / (beta - x)),
                ]
            )
            most = max(float(cp.asnumpy(ratios).max()), -1.01 * dz / z, -1.01 * dzet / zet, 1.0)
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
    return cp.asnumpy(x), {"z": float(z), "y": cp.asnumpy(y), "lam": cp.asnumpy(lam), "newton_steps": steps}
