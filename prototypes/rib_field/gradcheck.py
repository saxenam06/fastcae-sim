"""The toy's derivatives against central differences (LOP-34): the field's compliance and mass by a
few of its rho and height variables and by a few columns' directions, and the free columns'
compliance by a few heights. `python prototypes/rib_field/gradcheck.py [voxel mm]`."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402


def check(name, f, x, grad, picks, step):
    """Central differences at `step` and ten and a hundred times it, the closest kept: the
    compliance is strongly curved in some variables (truncation shrinks with the step squared)
    and flat in others (round-off grows as the step shrinks)."""
    worst = 0.0
    for k in picks:
        best = None
        for h in (step, 10 * step, 100 * step):
            xp, xm = x.copy(), x.copy()
            xp[k] += h
            xm[k] -= h
            fd = (f(xp) - f(xm)) / (2 * h)
            err = abs(fd - grad[k]) / max(abs(fd), abs(grad[k]), 1e-12)
            if best is None or err < best[0]:
                best = (err, fd, h)
        err, fd, h = best
        worst = max(worst, err)
        print(f"{name}[{k}]: analytic {grad[k]: .8e}, central {fd: .8e} (step {h:g}), relative {err:.2e}")
    return worst


def main() -> None:
    a = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
    s = toy.build(a)
    rng = np.random.default_rng(0)
    worst = 0.0
    # the field, at a random state with random directions
    fld = toy.Field(s)
    fld.theta = rng.uniform(0, np.pi, s.n_cols)
    x = np.r_[rng.uniform(0.2, 0.8, fld.n), rng.uniform(0.2, 0.8, fld.n)]
    c, cc = fld.stiffness(x)
    r = toy.solve(s, c)
    g = fld.gradients(cc, r["energy"])

    def comp(xx):
        return toy.solve(s, fld.stiffness(xx)[0])["compliance"]

    def mass(xx):
        return fld.mass(fld.stiffness(xx)[1])

    busy = np.argsort(-np.abs(g["dc"]))
    picks = list(busy[:3]) + list(busy[fld.n // 2 : fld.n // 2 + 1])
    picks += [k for k in busy if k >= fld.n][:3]
    worst = max(worst, check("field compliance", comp, x, g["dc"], picks, 1e-6))
    worst = max(worst, check("field mass", mass, x, g["dm"], picks, 1e-6))

    th0 = fld.theta.copy()

    def comp_th(th):
        fld.theta = th
        out = toy.solve(s, fld.stiffness(x)[0])["compliance"]
        fld.theta = th0
        return out

    picks = list(np.argsort(-np.abs(g["dc_dtheta"]))[:4])
    worst = max(worst, check("field compliance by theta", comp_th, th0, g["dc_dtheta"], picks, 1e-6))
    # the free columns
    cols = toy.Columns(s)
    cols.p = 3.0
    xc = rng.uniform(0.2, 0.8, cols.n)
    c, cc = cols.stiffness(xc)
    r = toy.solve(s, c)
    g = cols.gradients(cc, r["energy"])

    def comp_c(xx):
        return toy.solve(s, cols.stiffness(xx)[0])["compliance"]

    picks = list(np.argsort(-np.abs(g["dc"]))[:4])
    worst = max(worst, check("columns compliance", comp_c, xc, g["dc"], picks, 1e-6))
    print(f"worst relative difference {worst:.2e}")


if __name__ == "__main__":
    main()
