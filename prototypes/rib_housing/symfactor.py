"""The CPU stand-in's direct solver as the product's own factor (LOP-34; a prototype, for this
folder's judge only).

`checks/support/gpu_on_cpu`'s `DirectSolver` factorises with PARDISO's general LU in double
(`pypardiso`'s default, matrix type 11): both triangles, eight bytes an entry. The product's
`SingleFactor` factorises its (diagonally scaled, float32) stiffness in single precision on the GPU
(cuDSS) and refines every answer to double by conjugate gradients on K itself. `use()` makes the
stand-in do the same on the CPU: PARDISO's symmetric indefinite factor (type -2, Bunch-Kaufman
pivoting) of the upper triangle **in single precision** (`iparm(28) = 1`, MKL called directly: pypardiso
passes only double), a quarter of the general double LU's memory; the refinement is the product's.
The FE matrices it sees are symmetric (the reduced stiffness; the modes' Lanczos only solves with
it). It also gives SciPy's CSR the `.get()` FE's assembly asks of CuPy's sparse matrices.
`check()` compares the single factor's solve with scipy's on a 3D Laplacian.

(16 October: the symmetric double factor of the reference's 2.0 M-unknown mesh ran the container's
15 GB out; PARDISO's out-of-core mode would not open its files here, error -10.)
"""

from __future__ import annotations

import ctypes
import time

import numpy as np
import scipy.sparse as sp

MEMORY_REPORT: list[dict] = []  # each factor's PARDISO memory report (KB) and times


class SingleSym:
    """PARDISO's single-precision symmetric indefinite factor of a symmetric matrix's upper
    triangle, kept for any number of solves."""

    def __init__(self, a: sp.spmatrix):
        import pypardiso

        self.lib = pypardiso.PyPardisoSolver().libmkl  # pypardiso's own search for mkl_rt
        up = sp.triu(sp.csr_matrix(a), format="csr").astype(np.float32)
        up.sort_indices()
        self.n = up.shape[0]
        self.data = np.ascontiguousarray(up.data, np.float32)
        self.ia = np.ascontiguousarray(up.indptr, np.int32)
        self.ja = np.ascontiguousarray(up.indices, np.int32)
        self.pt = np.zeros(64, np.int64)
        self.iparm = np.zeros(64, np.int32)
        # 1-based as PARDISO's manual: user values, nested dissection, pivots perturbed 1e-8,
        # report the factor's size, Bunch-Kaufman pivoting, single precision, zero-based indices
        for i, v in ((1, 1), (2, 2), (8, 2), (10, 8), (18, -1), (21, 1), (28, 1), (35, 1)):
            self.iparm[i - 1] = v
        t0 = time.time()
        self._call(11, np.zeros((1, self.n), np.float32))
        predicted = {k: int(self.iparm[k - 1]) for k in (15, 16, 17)}
        t1 = time.time()
        self._call(22, np.zeros((1, self.n), np.float32))
        MEMORY_REPORT.append({"n": self.n, "kb": predicted, "factor_nnz": int(self.iparm[17]),
                              "analysis_s": t1 - t0, "factor_s": time.time() - t1})

    def _call(self, phase: int, b: np.ndarray) -> np.ndarray:
        b = np.ascontiguousarray(b, np.float32)  # (nrhs, n): each right-hand side contiguous
        x = np.zeros_like(b)
        err = ctypes.c_int32(0)
        i32 = ctypes.POINTER(ctypes.c_int32)
        f32 = ctypes.POINTER(ctypes.c_float)
        self.lib.pardiso(
            self.pt.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
            ctypes.byref(ctypes.c_int32(1)),
            ctypes.byref(ctypes.c_int32(1)),
            ctypes.byref(ctypes.c_int32(-2)),
            ctypes.byref(ctypes.c_int32(phase)),
            ctypes.byref(ctypes.c_int32(self.n)),
            self.data.ctypes.data_as(f32),
            self.ia.ctypes.data_as(i32),
            self.ja.ctypes.data_as(i32),
            np.zeros(1, np.int32).ctypes.data_as(i32),
            ctypes.byref(ctypes.c_int32(b.shape[0])),
            self.iparm.ctypes.data_as(i32),
            ctypes.byref(ctypes.c_int32(0)),
            b.ctypes.data_as(f32),
            x.ctypes.data_as(f32),
            ctypes.byref(err),
        )
        if err.value != 0:
            raise RuntimeError(f"PARDISO's single factor failed in phase {phase}: error {err.value}")
        return x

    def solve(self, b: np.ndarray) -> np.ndarray:
        """x for (n,) or (n, nrhs) right-hand sides, in single precision."""
        b2 = np.asarray(b).reshape(self.n, -1)
        return self._call(33, b2.T).T

    def free_memory(self, everything: bool = True) -> None:  # noqa: ARG002 (pypardiso's signature)
        if self.pt.any():
            self._call(-1, np.zeros((1, self.n), np.float32))
            self.pt[:] = 0


def _factorize(self) -> None:
    self.free()
    solver = self._pardiso = SingleSym(self.a)
    self._solve = solver.solve


def use() -> None:
    from nvmath.sparse.advanced import DirectSolver

    DirectSolver.factorize = _factorize
    # the stand-in's sparse matrices are SciPy's, already on the host: FE's assembly
    # (`zenryx.physics.tet10.stiffness(..., gpu=True)`) asks them for CuPy's `.get()`
    if not hasattr(sp.csr_matrix, "get"):
        sp.csr_matrix.get = lambda self: self


def check(n: int = 40) -> float:
    """The single factor's solve against scipy's on a 3D Laplacian (n^3 unknowns), relative."""
    from scipy.sparse.linalg import spsolve

    one = sp.diags([-np.ones(n - 1), 2.0 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1])
    eye = sp.identity(n)
    a = (sp.kron(sp.kron(one, eye), eye) + sp.kron(sp.kron(eye, one), eye)
         + sp.kron(sp.kron(eye, eye), one) + 0.1 * sp.identity(n**3)).tocsr()
    b = np.random.default_rng(0).standard_normal((a.shape[0], 2))
    s = SingleSym(a)
    x = s.solve(b)
    s.free_memory()
    ref = np.column_stack([spsolve(a.tocsc(), b[:, k]) for k in range(2)])
    print(f"the report: {MEMORY_REPORT[-1]}")
    return float(np.abs(x - ref).max() / np.abs(ref).max())


if __name__ == "__main__":
    print(f"the single symmetric factor against scipy's solve: {check():.2e}")
