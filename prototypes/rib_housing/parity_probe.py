"""The rib model against the product's on the reference's own field (LOP-34; a prototype): the run
`baseline2_lw8` (ref/lop33) read by the product's model (`Voxels.analyse`, its densities by SIMP on
the product's element) and by `RibModel` with every free cube isotropic at the same SIMP stiffness
(plain hexahedra): their tilts and beds over the lines should agree within the elements' difference.
`parity_probe.py`."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import housing  # noqa: E402
import ribmodel  # noqa: E402

REF = housing.ROOT / "ref" / "lop33"


def main() -> None:
    vox, _ = housing.product_model(4.0)
    stem = next(p.stem for p in REF.glob("topofree_*baseline2_lw8*_sf1.5.npz"))
    z = np.load(REF / f"{stem}.npz")
    print("npz keys", sorted(z.keys()))
    phys = np.asarray(z["phys"], float)
    dens = np.ones(len(vox.elem))
    if len(phys) == len(vox.elem):
        dens = phys
    else:
        dens[vox.free_e] = phys
    binary = (dens >= 0.5).astype(float)
    binary[vox.frozen] = 1.0
    out_p = vox.analyse(binary, penal=3.0, adjoints=False)
    vox.release(out_p)
    print("product: tilts", np.round(out_p["ratio_vector"], 3), "beds", np.round(out_p["bed_vector"], 3))
    rm = ribmodel.RibModel(vox)
    e_scale = 1e-6 + binary[vox.free_e] ** 3 * (1 - 1e-6)
    c = e_scale[:, None, None] * rm.c_iso[None]
    out_r = rm.analyse(c, adjoints=False)
    print("rib model (isotropic): tilts", np.round(out_r["ratios"], 3), "beds", np.round(out_r["beds"], 3))
    print("placed kg", float(binary[vox.free_e].sum()) * 4.0**3 * vox.density)


if __name__ == "__main__":
    main()
