"""cuDSS's direct solver as nvmath exposes it, on the CPU, for the checks only: Intel's PARDISO
(`pypardiso`, which factors in double: a stand-in for tracing and parity on a machine without a
card, never the product's factor) when it is installed, else SciPy's SuperLU (fine for small
models only).

The solver keeps a reference to its matrix, as cuDSS does: the optimiser writes new values into the
matrix in place and factorises again (`fast_factor.GpuStiffness.factor`). The callers refine every
answer to double by conjugate gradients with the factor as their preconditioner, so a stand-in
factor changes the steps taken, not the answer within its tolerance."""

from __future__ import annotations

import enum

import numpy as np
import scipy.sparse as sp


class DirectSolverMatrixType(enum.Enum):
    GENERAL = 0
    SYMMETRIC = 1
    SPD = 2


class HybridMemoryModeOptions:
    def __init__(self, **kwargs):
        self.options = kwargs


class ExecutionCUDA:
    def __init__(self, **kwargs):
        self.options = kwargs


class DirectSolver:
    def __init__(self, a, b, options=None, execution=None):
        self.a, self.b = a, b
        self._solve = None

    def plan(self) -> None:
        pass

    def factorize(self) -> None:
        a = sp.csr_matrix(self.a)
        # PARDISO keeps a factor's memory until told: one refactorised in place lets the last go
        self.free()
        try:
            import pypardiso

            solver = self._pardiso = pypardiso.PyPardisoSolver()
            a64 = a.astype(np.float64)
            a64.sort_indices()
            solver.factorize(a64)
            self._solve = lambda b: solver.solve(a64, np.asarray(b, np.float64))
        except ImportError:
            from scipy.sparse.linalg import splu

            lu = splu(sp.csc_matrix(a), permc_spec="MMD_AT_PLUS_A")
            self._solve = lambda b: lu.solve(np.asarray(b, lu.L.dtype))

    def reset_operands(self, a=None, b=None) -> None:
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b

    def solve(self):
        b = np.asarray(self.b)
        x = self._solve(b.reshape(b.shape[0], -1))
        return np.asfortranarray(np.asarray(x, np.float32).reshape(b.shape))

    def free(self) -> None:
        self._solve = None
        if getattr(self, "_pardiso", None) is not None:
            self._pardiso.free_memory(everything=True)
            self._pardiso = None
