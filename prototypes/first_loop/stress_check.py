"""PROTOTYPE (LOP-21) - `fastcae_fe.nodal_stress` (copied from fastcae-v1) checked on a case with a known
answer: a block of TET10 under a uniform uniaxial strain (u = (eps x, 0, 0)), whose stress is
uniform: sxx = (lambda + 2 mu) eps, syy = szz = lambda eps, no shear, von Mises |sxx - syy| = 2 mu eps.
Every node must read it to rounding. Prints PASS or FAIL.

Run: .venv/Scripts/python.exe prototypes/first_loop/stress_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastcae_fe import nodal_stress, quadratic  # noqa: E402


def block(n: int = 3, size: float = 10.0):
    """A cube of n^3 cells, each cut into six tets (TET4), then made TET10."""
    g = np.linspace(0.0, size, n + 1)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    nodes = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

    def at(i, j, k):
        return (i * (n + 1) + j) * (n + 1) + k

    tets = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                c = [at(i + a, j + b, k + d) for a in (0, 1) for b in (0, 1) for d in (0, 1)]
                # the cube's corners 0..7 (binary a b d); six tets round the diagonal 0-7
                for t in ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7)):
                    tets.append([c[v] for v in t])
    tets = np.asarray(tets)
    # positive volumes
    p = nodes[tets]
    vol = np.einsum("ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), p[:, 3] - p[:, 0])
    tets[vol < 0] = tets[vol < 0][:, [1, 0, 2, 3]]
    return quadratic(nodes, tets)


def main() -> bool:
    young, nu, eps = 69_000.0, 0.33, 1e-4
    nodes, tets = block()
    u = np.zeros_like(nodes)
    u[:, 0] = eps * nodes[:, 0]
    stress, vm = nodal_stress(nodes, tets, np.full(len(tets), young), np.full(len(tets), nu), u, len(nodes))
    lam = young * nu / ((1 + nu) * (1 - 2 * nu))
    mu = young / (2 * (1 + nu))
    want = np.array([(lam + 2 * mu) * eps, lam * eps, lam * eps, 0.0, 0.0, 0.0])
    err = float(np.abs(stress - want).max() / abs(want[0]))
    vm_err = float(np.abs(vm - 2 * mu * eps).max() / (2 * mu * eps))
    ok = err < 1e-9 and vm_err < 1e-9
    print(f"{'PASS' if ok else 'FAIL'}: {len(tets)} TET10; the stress's worst relative error {err:.1e}, von Mises' {vm_err:.1e} "
          f"(sxx {want[0]:.4f} MPa, von Mises {2 * mu * eps:.4f} MPa)")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
