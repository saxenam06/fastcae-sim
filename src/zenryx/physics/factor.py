"""The single-precision factor of a symmetric positive definite stiffness, refined to double, and
the modes it gives (moved from `prototypes/first_loop/fe.py`: `SingleFactor`, `modes`, `GMRES_MOST`;
fastcae-v1's REFINE_TOL and REFINE_MOST; LOP-33). FE and the optimiser's binary check both use it.

A cuDSS factor (nvmath) in single precision on purpose: the factor must fit the card (the engineer,
3 October). There is no double factor and no fallback to one (CLAUDE.md).
"""

from __future__ import annotations

import math
import time

import numpy as np
import scipy.sparse as sp

from zenryx.physics.tet10 import mtlayer, release

REFINE_TOL = 1.0e-10  # the relative residual the refined answer reaches, as a double factor's does
REFINE_MOST = (
    60  # the most refining steps; a stiffness the single factor cannot precondition this well fails
)
GMRES_MOST = 480  # the most GMRES steps after conjugate gradients stall (8 restarts of 60)


class SingleFactor:
    """A cuDSS factor of a symmetric positive definite stiffness in single precision, kept for as
    many right-hand sides as the judgement needs (the load cases, then the modes' Lanczos
    iterations); each answer refined to double by conjugate gradients with the factor as their
    preconditioner. A stiffness this factor cannot precondition fails."""

    def __init__(self, k: sp.csr_matrix):
        import cupy as cp
        import cupyx.scipy.sparse as csp
        from nvmath.sparse.advanced import (
            DirectSolver,
            DirectSolverMatrixType,
            ExecutionCUDA,
            HybridMemoryModeOptions,
        )

        self.k = k
        self.cp = cp
        self.kind = None
        # The stiffness scaled by its diagonal (S K S, S = diag(K)^-1/2) before it is factored:
        # a sliver element or a stiff rib makes K's entries span many decades, which a single-
        # precision factor rounds away; scaled, every diagonal entry is 1 and the factor is a
        # far better preconditioner. The refinement still works on K itself, in double.
        self.scale = 1.0 / np.sqrt(k.diagonal())
        scaled = sp.diags(self.scale) @ k @ sp.diags(self.scale)
        release()
        self.a = csp.csr_matrix(scaled.astype(np.float32))
        self.b = cp.asfortranarray(cp.zeros((k.shape[0], 1), dtype=np.float32))
        execution = ExecutionCUDA(
            hybrid_memory_mode_options=HybridMemoryModeOptions(hybrid_memory_mode=True)
        )
        # Cholesky first; where its single-precision rounding breaks a pivot, LDL^T with pivoting,
        # still in single precision.
        for kind in ("SPD", "SYMMETRIC"):
            options = {
                "sparse_system_type": getattr(DirectSolverMatrixType, kind),
                "multithreading_lib": mtlayer(),
            }
            self.solver = DirectSolver(self.a, self.b, options=options, execution=execution)
            t0 = time.time()
            self.solver.plan()
            self.solver.factorize()
            cp.cuda.Device().synchronize()
            self.factor_s = time.time() - t0
            probe = self.backsolve(np.ones(k.shape[0]))
            if np.all(np.isfinite(probe)):
                self.kind = kind
                break
            self.solver.free()
        if self.kind is None:
            self.close()
            raise RuntimeError(
                "every single-precision factor broke down: the stiffness is singular"
            )

    def backsolve(self, r: np.ndarray) -> np.ndarray:
        """K^-1 r by the scaled single factor: S (S K S)^-1 S r."""
        cp = self.cp
        rs = self.scale * np.asarray(r, dtype=np.float64).reshape(-1)
        self.solver.reset_operands(
            b=cp.asfortranarray(cp.asarray(rs.reshape(-1, 1), dtype=np.float32))
        )
        return self.scale * cp.asnumpy(self.solver.solve()).astype(np.float64).reshape(-1)

    def solve(self, f: np.ndarray, tol: float = REFINE_TOL, most: int = REFINE_MOST):
        """k x = f for one right-hand side, refined to the relative residual `tol` in at most `most`
        conjugate-gradient steps. Returns (x, steps, residual); raises when it does not get
        there."""
        b = np.asarray(f, dtype=np.float64).reshape(-1)
        scale = max(float(np.linalg.norm(b)), 1e-300)
        x = self.backsolve(b)
        r = b - self.k @ x
        steps = 0
        if float(np.linalg.norm(r)) > tol * scale:
            z = self.backsolve(r)
            p = z.copy()
            rz = float(r @ z)
            while steps < most:
                kp = self.k @ p
                alpha = rz / float(p @ kp)
                x = x + alpha * p
                r = r - alpha * kp
                steps += 1
                if float(np.linalg.norm(r)) <= tol * scale:
                    break
                z = self.backsolve(r)
                rz_new = float(r @ z)
                p = z + (rz_new / rz) * p
                rz = rz_new
        residual = float(np.linalg.norm(r)) / scale
        if not np.isfinite(residual) or residual > 100 * tol:
            # Conjugate gradients stall when the single factor, on a mesh with many slivers, is
            # no longer quite positive definite. GMRES takes any preconditioner: the same single
            # factor, restarted every 60 steps; the answer is still judged by K x = f in double.
            from scipy.sparse.linalg import LinearOperator, gmres

            n = self.k.shape[0]
            m = LinearOperator((n, n), matvec=self.backsolve, dtype=np.float64)
            start = x if np.all(np.isfinite(x)) else self.backsolve(b)
            count = [0]

            def tick(_):
                count[0] += 1

            x, _ = gmres(
                self.k,
                b,
                x0=start,
                M=m,
                rtol=tol,
                atol=0.0,
                restart=60,
                maxiter=GMRES_MOST // 60,
                callback=tick,
                callback_type="pr_norm",
            )
            residual = float(np.linalg.norm(b - self.k @ x)) / scale
            steps += count[0]
        if not np.isfinite(residual) or residual > 100 * tol:
            raise RuntimeError(
                f"the single-precision factor did not refine: residual {residual:.1e} after "
                f"{steps} steps"
            )
        return x, steps, residual

    def close(self) -> None:
        if getattr(self, "solver", None) is not None:
            self.solver.free()
            self.solver = None
        self.a = self.b = None
        release()


def modes(k_red: sp.csr_matrix, m_red: sp.csr_matrix, factor: SingleFactor, count: int = 12):
    """The housing's first natural frequencies (Hz) as held, and the modes' reduced vectors in the
    same order, mass-normalised: Lanczos in shift-invert about zero (scipy's eigsh) on the reduced
    stiffness and mass, every inner solve by the single factor refined to 1e-7 (the frequencies need
    no more)."""
    from scipy.sparse.linalg import LinearOperator, eigsh

    n = k_red.shape[0]
    op = LinearOperator(
        (n, n), matvec=lambda v: factor.solve(v, tol=1e-7, most=REFINE_MOST)[0], dtype=np.float64
    )
    values, vecs = eigsh(
        k_red, k=count, M=m_red, sigma=0.0, OPinv=op, which="LM", tol=1e-6, return_eigenvectors=True
    )
    order = np.argsort(values)
    return [float(np.sqrt(max(v, 0.0)) / (2 * math.pi)) for v in values[order]], vecs[:, order]
