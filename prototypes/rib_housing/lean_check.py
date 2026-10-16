"""The product's `SingleFactor` with this folder's lean constructor (`symfactor.use()`) against
scipy's solve on a 3D Laplacian (LOP-34; a prototype check): `lean_check.py [n per side]`. Run with
the GPU stand-ins and `src` on the path."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

sys.path.insert(0, str(Path(__file__).resolve().parent))
import symfactor  # noqa: E402


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    symfactor.use()
    from zenryx.physics.factor import SingleFactor

    one = sp.diags([-np.ones(n - 1), 2.0 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1])
    eye = sp.identity(n)
    k = (sp.kron(sp.kron(one, eye), eye) + sp.kron(sp.kron(eye, one), eye) + sp.kron(sp.kron(eye, eye), one)
         + 0.01 * sp.identity(n**3)).tocsr()
    k = (sp.diags(np.linspace(1.0, 1e4, n**3)) @ k @ sp.diags(np.linspace(1.0, 1e4, n**3))).tocsr()  # decades apart
    f = np.random.default_rng(0).standard_normal(n**3)
    fac = SingleFactor(k)
    x, steps, res = fac.solve(f)
    ref = spsolve(k.tocsc(), f)
    fac.close()
    print(f"{n**3:,} unknowns: kind {fac.kind}, {steps} refining steps, residual {res:.1e}, "
          f"against scipy {np.abs(x - ref).max() / np.abs(ref).max():.1e}")


if __name__ == "__main__":
    main()
