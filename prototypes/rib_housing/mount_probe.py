"""Are the mounts' lugs joined to the body in a state's own field? (LOP-34; a prototype)
`mount_probe.py <label> [voxel mm]`: each cube metal where its solid share or its ribs' share is at
least `LEVEL`, the frozen cubes metal; each half's largest face-joined piece; each mount's lug cubes
in it or not, and the solid zone's metal in its corridor."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import label

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drawrib  # noqa: E402

LEVEL = 0.5


def main() -> None:
    label_ = sys.argv[1]
    voxel = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    vox, model, hf, x = drawrib.rebuild(label_, voxel)
    cols = drawrib.columns_of(vox, hf, x)
    pc = cols["pc"]
    s = pc["solid"]["g"]
    ribs = pc["u"] * sum(f["g"] * f["rho"][hf.col] for f in pc["fam"])
    n = tuple(int(v) for v in model["n"])
    h, lo = float(model["h"]), np.asarray(model["lo"], float)
    info = model["info"]
    split = info["z"]["split"]
    for name, share in (("solid", s), ("solid or ribs", s + ribs)):
        metal = np.zeros(int(np.prod(n)), bool)
        metal[vox.elem[vox.frozen]] = True
        metal[vox.elem[vox.free_e]] = share >= LEVEL
        metal = metal.reshape(n)
        ks = int(model["k_split"])
        lab_all = np.zeros(n, int)
        for _off, sl in ((0, np.s_[:, :, :ks]), (10**6, np.s_[:, :, ks:])):
            lab, k = label(metal[sl])
            if k:
                sizes = np.bincount(lab.ravel())
                sizes[0] = 0
                big = int(np.argmax(sizes))
                lab_all[sl] = np.where(lab == big, 1, np.where(lab > 0, 2, 0))
        for mt in info["mounts"]:
            cx, cy = mt["centre"]
            ii = np.arange(n[0]) * h + lo[0] + h / 2
            jj = np.arange(n[1]) * h + lo[1] + h / 2
            kk = np.arange(n[2]) * h + lo[2] + h / 2
            X, Y, Z = np.meshgrid(ii, jj, kk, indexing="ij")
            lug = (np.hypot(X - cx, Y - cy) <= info["settings"]["mount_diameter"] / 2) & (mt["z"][0] <= Z) & (mt["z"][1] >= Z)
            lug &= metal
            state = np.bincount(lab_all[lug].ravel(), minlength=3)
            print(f"{name}: {mt['name']} (z {mt['z'][0]:.0f}..{mt['z'][1]:.0f}, split {split:.0f}): "
                  f"{state[1]} lug cubes in the body, {state[2]} in a loose piece, {state[0]} not metal")
    # the corridor's solid metal by mount
    xyz = lo + (vox.ijk[vox.free_e] + 0.5) * h
    for mt in info["mounts"]:
        near = np.hypot(xyz[:, 0] - mt["centre"][0], xyz[:, 1] - mt["centre"][1]) < 60
        print(f"{mt['name']}: solid within 60 mm in plan {float((s * near).sum()) * h**3 * vox.density:.3f} kg, "
              f"ribs {float((ribs * near).sum()) * h**3 * vox.density:.3f} kg")


if __name__ == "__main__":
    main()
