"""Does PARDISO's out-of-core factor work here (LOP-34; a prototype)? `ooc_probe.py [n per side]
[core MB]`: a 3D Laplacian (n^3 unknowns, SPD) factored by the symmetric indefinite factor with
iparm 60 = 1 (in core when it fits under MKL_PARDISO_OOC_MAX_CORE_SIZE, else out of core), its
solve against the in-core factor's, and PARDISO's own memory report (iparm 15-17, KB)."""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import scipy.sparse as sp


def laplacian(n: int) -> sp.csr_matrix:
    one = sp.diags([-np.ones(n - 1), 2.0 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1])
    eye = sp.identity(n)
    return (sp.kron(sp.kron(one, eye), eye) + sp.kron(sp.kron(eye, one), eye) + sp.kron(sp.kron(eye, eye), one)
            + 1e-3 * sp.identity(n**3)).tocsr()


def solve(a, b, ooc: bool):
    import pypardiso

    up = sp.triu(a, format="csr")
    up.sort_indices()
    s = pypardiso.PyPardisoSolver(mtype=-2)
    if ooc:
        # PARDISO reads iparm only when iparm(1) = 1: then its symmetric indefinite defaults are
        # given by hand (nested dissection, pivots perturbed 1e-8, Bunch-Kaufman) and the factor
        # put out of core
        for i, v in ((1, 1), (2, 2), (10, 8), (18, -1), (21, 1), (60, 2)):
            s.set_iparm(i, v)
    t0 = time.time()
    s.factorize(up)
    x = s.solve(up, b)
    mem = {k: int(s.get_iparm(k)) for k in (15, 16, 17)}
    s.free_memory(everything=True)
    return x, time.time() - t0, mem


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    os.environ.setdefault("MKL_PARDISO_OOC_MAX_CORE_SIZE", sys.argv[2] if len(sys.argv) > 2 else "200")
    os.environ.setdefault("MKL_PARDISO_OOC_PATH", os.path.join(os.getcwd(), "pardiso_ooc"))
    a = laplacian(n)
    b = np.random.default_rng(0).standard_normal((a.shape[0], 2))
    x0, t0, m0 = solve(a, b, ooc=False)
    print(f"{a.shape[0]:,} unknowns; in core {t0:.1f} s, memory (KB) {m0}", flush=True)
    x1, t1, m1 = solve(a, b, ooc=True)
    print(f"out of core under {os.environ['MKL_PARDISO_OOC_MAX_CORE_SIZE']} MB: {t1:.1f} s, memory (KB) {m1}; "
          f"relative difference {np.abs(x1 - x0).max() / np.abs(x0).max():.2e}")


if __name__ == "__main__":
    main()
