"""PROTOTYPE (LOP-19) - checks the GPU stiffness and its kept factor (`fast_factor.GpuStiffness`)
against the CPU assembly and `fe.SingleFactor` that `topo.Voxels.analyse` used: the same answers
to the load cases and to an adjoint's right-hand side, for one density and then another (the
refactorisation path), and how long each takes.

Run: .venv/Scripts/python.exe prototypes/first_loop/fast_factor_check.py [voxel mm]
     (10 mm by default: light enough to run beside an optimisation; 6 mm for the timing)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from fast_factor import GpuStiffness  # noqa: E402
from fe import SingleFactor  # noqa: E402
from topo_free import build_free  # noqa: E402


def old_factor(vox, e_scale):
    t0 = time.time()
    vals = (e_scale[:, None] * vox.ke.ravel()[None, :]).ravel()
    k = sp.coo_matrix((vals, (vox.rows, vox.cols)), shape=(vox.n_dof, vox.n_dof)).tocsr()
    kff = k[vox.free][:, vox.free]
    t1 = time.time()
    f = SingleFactor(kff)
    return f, t1 - t0, time.time() - t1


def main(h: float = 10.0) -> int:
    model = build_free(h, layout="contract", skin=4.0, cavity="cup", penalty_ramp=0, route="split")
    model["cases"] = ("peak drive",)
    vox = topo.Voxels(model)
    rng = np.random.default_rng(7)
    t0 = time.time()
    gpu = GpuStiffness(vox.rows, vox.cols, vox.n_dof, vox.free, vox.ke)
    print(f"{h:g} mm: {len(vox.elem):,} elements, {len(vox.free):,} unknowns, {gpu.nnz:,} stiffness entries; the pattern found in {time.time() - t0:.1f} s")
    worst = 0.0
    for trial in range(2):
        dens = np.where(vox.frozen, 1.0, rng.uniform(0.05, 1.0, len(vox.elem)))
        e_scale = vox.stiff_e * (topo.E_MIN + dens**topo.PENAL * (1 - topo.E_MIN))
        rhs = [vox.rhs[:, 0], rng.normal(size=len(vox.free))]  # the load case, and an adjoint-like right-hand side
        f_old, a_old, t_old = old_factor(vox, e_scale)
        x_old = [f_old.solve(r)[0] for r in rhs]
        f_old.close()
        t0 = time.time()
        f_new = gpu.factor(e_scale)
        t_new = time.time() - t0
        t1 = time.time()
        x_new = [f_new.solve(r)[0] for r in rhs]
        t_solve = time.time() - t1
        diffs = [float(np.abs(a - b).max() / max(np.abs(a).max(), 1e-300)) for a, b in zip(x_old, x_new, strict=True)]
        worst = max(worst, *diffs)
        print(f"density {trial + 1}: the CPU's assembly {a_old:.2f} s + factor {t_old:.2f} s; the GPU's assembly {f_new.assemble_s:.2f} s + "
              f"factor {f_new.factor_s:.2f} s ({t_new:.2f} s in all, {f_new.kind}), its two solves {t_solve:.2f} s; "
              f"the answers differ by {diffs[0]:.1e} and {diffs[1]:.1e} of their size")  # fmt: skip
    gpu.close()
    ok = worst < 1e-8
    print("the same answers" if ok else "the answers DIFFER")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 10.0))
