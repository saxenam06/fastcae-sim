"""The CPU stand-in's direct solver with a symmetric factor (LOP-34; a prototype, for this folder's
judge only): `checks/support/gpu_on_cpu`'s `DirectSolver` factorises with PARDISO's general LU
(`pypardiso`'s default, matrix type 11), which keeps both triangles; FE's matrices (the reduced
stiffness, the shifted K - sigma M of the modes) are symmetric, so the symmetric indefinite factor
(type -2, Bunch-Kaufman pivoting) on the upper triangle holds about half the memory. Double
precision, as the stand-in's. `use()` patches the stand-in in place; `check()` compares both
factors' solves on a symmetric indefinite matrix."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def _factorize(self) -> None:
    import pypardiso

    a = sp.csr_matrix(self.a)
    self.free()
    up = sp.triu(a.astype(np.float64), format="csr")
    up.sort_indices()
    solver = self._pardiso = pypardiso.PyPardisoSolver(mtype=-2)
    solver.factorize(up)
    self._solve = lambda b: solver.solve(up, np.asarray(b, np.float64))


def use() -> None:
    from nvmath.sparse.advanced import DirectSolver

    DirectSolver.factorize = _factorize


def check(n: int = 3000) -> float:
    """The relative difference between the symmetric factor's solve and scipy's on a random symmetric
    indefinite sparse matrix with a full diagonal."""
    from scipy.sparse.linalg import spsolve

    import pypardiso

    rng = np.random.default_rng(0)
    m = sp.random(n, n, density=3.0 / n, random_state=1, format="csr")
    a = (m + m.T + sp.diags(rng.uniform(-2.0, 4.0, n))).tocsr()
    b = rng.standard_normal((n, 3))
    up = sp.triu(a, format="csr")
    up.sort_indices()
    s = pypardiso.PyPardisoSolver(mtype=-2)
    s.factorize(up)
    x = s.solve(up, b)
    ref = np.column_stack([spsolve(a.tocsc(), b[:, k]) for k in range(3)])
    return float(np.abs(x - ref).max() / np.abs(ref).max())


if __name__ == "__main__":
    print(f"the symmetric factor against scipy's solve: {check():.2e}")
