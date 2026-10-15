"""cuDSS's direct solver as nvmath exposes it, on the CPU by SciPy's SuperLU, for the checks only.

The solver keeps a reference to its matrix, as cuDSS does: the optimiser writes new values into the
matrix in place and factorises again (`fast_factor.GpuStiffness.factor`). The factor is taken in the
matrix's own precision (single, as on the card); the callers refine every answer to double by
conjugate gradients, so a stand-in factor changes the steps taken, not the answer within its
tolerance."""

from __future__ import annotations

import enum

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import splu


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
        self._lu = None

    def plan(self) -> None:
        pass

    def factorize(self) -> None:
        a = sp.csc_matrix(self.a)
        self._lu = splu(a, permc_spec="MMD_AT_PLUS_A")

    def reset_operands(self, a=None, b=None) -> None:
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b

    def solve(self):
        b = np.asarray(self.b)
        x = self._lu.solve(b.astype(self._lu.L.dtype))
        return np.asfortranarray(x.reshape(b.shape))

    def free(self) -> None:
        self._lu = None
