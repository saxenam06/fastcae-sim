"""The voxel model's reduced stiffness T' K T assembled on the GPU into a pattern found once, and
its single-precision factor refactorised in place: cuDSS planned once per model (moved from
`prototypes/first_loop/fast_factor.py`: `GpuStiffness` and `GpuFactor`, the rigid couplings' path;
LOP-19, LOP-29, LOP-33).

The voxels never change, only their stiffness scales, so the reduced matrix's pattern never changes
either: it is found once, each analysis scatters the elements' values into it on the card, scales
them to a unit diagonal, writes them into the solver's matrix in place and refactorises. An element
whose unknowns are all uncoupled keeps its entries, each at its own reduced unknown; an element
touching a coupled or held node has its matrix reduced once, T_e' k_e T_e, and scaled by its
stiffness each time. The factor keeps `factor.SingleFactor`'s rules: single precision on purpose,
Cholesky first and LDL^T where its rounding breaks a pivot, every answer refined to double by
conjugate gradients with the factor as their preconditioner. One factor is open at a time per model.
"""

from __future__ import annotations

import time

import numpy as np

from zenryx.physics.factor import REFINE_MOST, REFINE_TOL
from zenryx.physics.tet10 import mtlayer


class GpuStiffness:
    """The reduced stiffness of a voxel model on the card: its pattern, found once from every
    element's unknowns (`dof`, 24 each) and the couplings' transform `T`, and one cuDSS solver
    planned on it."""

    def __init__(self, ke: np.ndarray, T, dof: np.ndarray):
        import cupy as cp
        import cupyx.scipy.sparse as csp

        t0 = time.time()
        self.cp = cp
        self.ke = cp.asarray(np.asarray(ke, float).ravel())  # (576,)
        key = self._reduced_pattern(np.asarray(dof), T, np.asarray(ke, float))
        n_free = T.shape[1]
        unique, slot = np.unique(key, return_inverse=True)
        self.nnz = len(unique)
        row_of = (unique // n_free).astype(np.int32)
        col_of = (unique % n_free).astype(np.int32)
        indptr = np.zeros(n_free + 1, dtype=np.int32)
        np.add.at(indptr, row_of.astype(np.int64) + 1, 1)
        indptr = np.cumsum(indptr).astype(np.int32)
        diag = np.flatnonzero(row_of == col_of)
        if len(diag) != n_free:
            raise RuntimeError(
                f"the stiffness pattern has {len(diag):,} diagonal entries for {n_free:,} unknowns"
            )
        self.n = n_free
        # the untouched elements' slots first (element by element, 576 each), then the reduced
        # matrices'
        n_unt = len(self.untouched) * self.ke.size
        self.slot_t = cp.asarray(slot[n_unt:].astype(np.int32))
        self.untouched_d = cp.asarray(self.untouched)
        self.slot = cp.asarray(slot[:n_unt].astype(np.int32))
        self.row_of = cp.asarray(row_of)
        self.indices = cp.asarray(col_of)
        self.indptr = cp.asarray(indptr)
        self.diag = cp.asarray(diag.astype(np.int32))
        # K in double for the refinement's products, and S K S in single for the factor: the same
        # pattern, values written in place by `factor`
        self.k = csp.csr_matrix(
            (cp.zeros(self.nnz), self.indices, self.indptr), shape=(n_free, n_free)
        )
        self.a = csp.csr_matrix(
            (cp.zeros(self.nnz, dtype=cp.float32), self.indices, self.indptr),
            shape=(n_free, n_free),
        )
        self.b = cp.asfortranarray(cp.zeros((n_free, 1), dtype=cp.float32))
        self.scale = cp.ones(n_free)
        self.solver = None
        self.kind = None
        self.pattern_s = time.time() - t0

    def _reduced_pattern(self, dof: np.ndarray, T, ke: np.ndarray) -> np.ndarray:
        """The reduced entries' keys (row * n_q + col; the untouched elements' 576 each first, then
        every touched element's reduced matrix), and the touched elements' reduced matrices
        (`t_vals`, their elements `t_elem`)."""
        cp = self.cp
        T = T.tocsr()
        n_q = T.shape[1]
        ones = np.diff(T.indptr) == 1
        identity = np.zeros(T.shape[0], bool)
        identity[ones] = T.data[T.indptr[:-1][ones]] == 1.0
        to_q = np.full(T.shape[0], -1, dtype=np.int64)
        to_q[identity] = T.indices[T.indptr[:-1][identity]]
        whole = identity[dof].all(axis=1)
        self.untouched = np.flatnonzero(whole)
        touched = np.flatnonzero(~whole)
        qd = to_q[dof[self.untouched]]  # (n_unt, 24)
        keys = [(qd[:, :, None] * n_q + qd[:, None, :]).reshape(-1)]
        t_vals, t_elem = [], []
        for e in touched:
            te = T[dof[e]]  # (24, n_q), a few columns
            cols_e = np.unique(te.indices).astype(np.int64)  # int32 indices times n_q overflow
            dense = te[:, cols_e].toarray()
            kr = dense.T @ ke @ dense
            keys.append((cols_e[:, None] * n_q + cols_e[None, :]).reshape(-1))
            t_vals.append(kr.reshape(-1))
            t_elem.append(np.full(kr.size, e))
        self.t_vals = cp.asarray(np.concatenate(t_vals)) if t_vals else cp.zeros(0)
        self.t_elem = (
            cp.asarray(np.concatenate(t_elem).astype(np.int64))
            if t_elem
            else cp.zeros(0, dtype=cp.int64)
        )
        return np.concatenate(keys)

    def _plan(self, kind: str) -> None:
        from nvmath.sparse.advanced import (
            DirectSolver,
            DirectSolverMatrixType,
            ExecutionCUDA,
            HybridMemoryModeOptions,
        )

        if self.solver is not None:
            self.solver.free()
        execution = ExecutionCUDA(
            hybrid_memory_mode_options=HybridMemoryModeOptions(hybrid_memory_mode=True)
        )
        options = {
            "sparse_system_type": getattr(DirectSolverMatrixType, kind),
            "multithreading_lib": mtlayer(),
        }
        self.solver = DirectSolver(self.a, self.b, options=options, execution=execution)
        self.solver.plan()
        self.kind = kind

    def factor(self, e_scale) -> GpuFactor:
        """The stiffness at the elements' scales `e_scale` (n_elem,), assembled and factorised on
        the card. Returns its factor (valid until the next call)."""
        cp = self.cp
        t0 = time.time()
        es = cp.asarray(e_scale, dtype=cp.float64)
        if not bool(cp.all(cp.isfinite(es))) or float(es.min()) <= 0.0:
            # handed a stiffness like this, cuDSS's factorize never returned (11 October 21:22)
            bad = int((~cp.isfinite(es)).sum())
            raise RuntimeError(
                f"the elements' scales are not all finite and positive: {bad} not finite, "
                f"the least {float(cp.nanmin(es)):.3e}"
            )
        data = cp.zeros(self.nnz + 1)
        vals = (es[self.untouched_d][:, None] * self.ke[None, :]).ravel()
        cp.add.at(data, self.slot, vals)
        cp.add.at(data, self.slot_t, es[self.t_elem] * self.t_vals)
        del vals
        self.k.data[...] = data[: self.nnz]
        del data
        diag = self.k.data[self.diag]
        if not bool(cp.all(cp.isfinite(diag))) or float(diag.min()) <= 0.0:
            raise RuntimeError(
                "the stiffness's diagonal is not all finite and positive: "
                f"the least {float(cp.nanmin(diag)):.3e}"
            )
        self.scale = 1.0 / cp.sqrt(diag)
        self.a.data[...] = (
            self.k.data * self.scale[self.row_of] * self.scale[self.indices]
        ).astype(cp.float32)
        cp.cuda.Device().synchronize()
        assembled = time.time() - t0
        t1 = time.time()
        kinds = ("SYMMETRIC",) if self.kind == "SYMMETRIC" else ("SPD", "SYMMETRIC")
        for kind in kinds:
            if self.kind != kind:
                self._plan(kind)
            self.solver.factorize()
            cp.cuda.Device().synchronize()
            probe = self._backsolve(cp.ones(self.n))
            if bool(cp.all(cp.isfinite(probe))):
                return GpuFactor(self, assembled, time.time() - t1)
        raise RuntimeError("every single-precision factor broke down: the stiffness is singular")

    def _backsolve(self, r):
        """K^-1 r by the scaled single factor, on the card: S (S K S)^-1 S r."""
        cp = self.cp
        self.b[:, 0] = (self.scale * r).astype(cp.float32)
        self.solver.reset_operands(b=self.b)
        return self.scale * self.solver.solve().reshape(-1).astype(cp.float64)

    def close(self) -> None:
        if self.solver is not None:
            self.solver.free()
            self.solver = None


class GpuFactor:
    """An analysis's factor (`GpuStiffness.factor`): `factor.SingleFactor`'s `solve` and `close`."""

    def __init__(self, owner: GpuStiffness, assemble_s: float, factor_s: float):
        self.owner = owner
        self.assemble_s = assemble_s
        self.factor_s = factor_s
        self.kind = owner.kind

    def solve(self, f, tol: float = REFINE_TOL, most: int = REFINE_MOST):
        """k x = f, refined to the relative residual `tol` in at most `most` conjugate-gradient
        steps. Returns (x, steps, residual) with x a NumPy array."""
        o = self.owner
        cp = o.cp
        b = cp.asarray(np.asarray(f, dtype=np.float64).reshape(-1))
        scale = max(float(cp.linalg.norm(b)), 1e-300)
        x = o._backsolve(b)
        r = b - o.k @ x
        steps = 0
        if float(cp.linalg.norm(r)) > tol * scale:
            z = o._backsolve(r)
            p = z.copy()
            rz = float(r @ z)
            while steps < most:
                kp = o.k @ p
                alpha = rz / float(p @ kp)
                x = x + alpha * p
                r = r - alpha * kp
                steps += 1
                if float(cp.linalg.norm(r)) <= tol * scale:
                    break
                z = o._backsolve(r)
                rz_new = float(r @ z)
                p = z + (rz_new / rz) * p
                rz = rz_new
        residual = float(cp.linalg.norm(r)) / scale
        # SingleFactor's acceptance: within a hundred times the tolerance (its GMRES fallback is
        # for sliver meshes; a voxel model has none)
        if not np.isfinite(residual) or residual > 100 * tol:
            raise RuntimeError(
                f"the refinement stopped at a relative residual of {residual:.1e} after {steps} "
                "steps"
            )
        return cp.asnumpy(x), steps, residual

    def close(self) -> None:
        """Nothing to free: the solver is the model's, refactorised by the next analysis."""
