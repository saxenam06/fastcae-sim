"""PROTOTYPE (LOP-28) - the optimiser's own model's natural frequencies for a finished run, beside FE's for its drawn design:
whether the model can hold a mode's margin from the gear orders (the grade's clash line; the evening's lesson 7: a mode lands
in the stage-1 order's band by chance, since the modes are not in the optimiser).

The run's model rebuilt as it ran (`topo_free.build_free` with its record's settings), its densities at the run's last
sharpness, its stiffness as `topo.Voxels.analyse` assembles it (SIMP at p 3) and a lumped mass with the low densities'
mass taken down (Pedersen 2000: rho for rho > 0.1, rho^6 scaled to meet it below, so a near-empty voxel has no local mode),
the mounts held; Lanczos in shift-invert about zero with the model's single factor (as `fe.modes`). Prints both spectra.

Run: .venv/Scripts/python.exe prototypes/first_loop/model_modes.py <run> [<design>] [--count 12]"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402

OUT = topo.OUT
LOW = 0.1  # below it a voxel's mass falls as rho^6 (Pedersen 2000)


def mass_of(dens: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Each element's mass share and its derivative by its density."""
    low = dens < LOW
    m = np.where(low, LOW * (np.maximum(dens, 0.0) / LOW) ** 6, dens)
    dm = np.where(low, 6.0 * (np.maximum(dens, 0.0) / LOW) ** 5, 1.0)
    return m, dm


def model_modes(vox: topo.Voxels, dens: np.ndarray, count: int = 12, penal: float = topo.PENAL, vectors: bool = False):
    """The model's first `count` natural frequencies (Hz) at the densities, with the mode shapes on the free unknowns."""
    from fe import SingleFactor
    from scipy.sparse.linalg import LinearOperator, eigsh

    e_scale = vox.stiff_e * (topo.E_MIN + dens**penal * (1 - topo.E_MIN))
    vals = (e_scale[:, None] * vox.ke.ravel()[None, :]).ravel()
    k = sp.coo_matrix((vals, (vox.rows, vox.cols)), shape=(vox.n_dof, vox.n_dof)).tocsr()
    kff = k[vox.free][:, vox.free].tocsr()
    del k, vals
    m_e = topo.DENSITY * vox.h**3 * mass_of(dens)[0]
    nodes = vox.dof[:, 0::3] // 3
    m_node = np.zeros(vox.n_dof // 3)
    np.add.at(m_node, nodes, (m_e / 8.0)[:, None])
    m_dof = np.repeat(m_node, 3)[vox.free]
    mff = sp.diags(m_dof).tocsr()
    factor = SingleFactor(kff)
    try:
        op = LinearOperator(kff.shape, matvec=lambda v: factor.solve(np.asarray(v, float).ravel())[0], dtype=float)
        lam, vec = eigsh(kff, k=count, M=mff, sigma=0.0, OPinv=op, which="LM", tol=1e-6)
    finally:
        factor.close()
    order = np.argsort(lam)
    hz = np.sqrt(np.maximum(lam[order], 0.0) * 1000.0) / (2 * np.pi)  # N/mm over kg: 1000 /s² per unit
    return (hz, vec[:, order]) if vectors else hz


def main(run: str, design: str | None, count: int) -> None:
    from topo_free import build_free

    t0 = time.time()
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    h = float(z["h"])
    model = build_free(h, band=rec.get("band_mm"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "disc",
                       route=rec.get("route") or "cast", cavity=rec.get("cavity") or "cup", penalty_ramp=rec.get("penalty_ramp") or 0,
                       height_field=(rec.get("height_field") or {}).get("radius_mm"), empty=bool(rec.get("empty")))  # fmt: skip
    model["cases"] = tuple(rec.get("cases") or ("peak drive",))
    if rec.get("height_volumes"):
        model["height_volumes"] = rec["height_volumes"]
    vox = topo.Voxels(model)
    if len(z["x"]) != vox.n_design:
        raise ValueError(f"{run}: {len(z['x'])} variables, the rebuilt model {vox.n_design}")
    dens = vox.physical(np.asarray(z["x"], float), float(z["beta"]))
    hz = model_modes(vox, dens, count)
    print(f"the model's modes ({run[-60:]}): " + ", ".join(f"{v:.0f}" for v in hz) + f" Hz; {time.time() - t0:.0f} s")
    if design:
        fe = json.loads((OUT / f"fe_{design}.json").read_text(encoding="utf-8"))
        print(f"FE's modes ({design}):          " + ", ".join(f"{v:.0f}" for v in fe["modes_hz"][:count]) + " Hz")
        n = min(len(hz), len(fe["modes_hz"]))
        print("model / FE:  " + ", ".join(f"{a / b:.2f}" for a, b in zip(hz[:n], fe["modes_hz"][:n], strict=True)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The optimiser's model's modes against FE's (LOP-28).")
    ap.add_argument("run")
    ap.add_argument("design", nargs="?", default=None)
    ap.add_argument("--count", type=int, default=12)
    a = ap.parse_args()
    main(a.run, a.design, a.count)
