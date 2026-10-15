"""What joins each mount's lug in a state's field, and does the drawing reach it (LOP-34; a
prototype): `lug_probe.py <label> [voxel mm]`. For each lug, the free cubes beside its fixed cubes
holding solid (share >= 0.5): their columns' group, base, place, the column's solid height and how far
its zone reaches; each such cube's centre against the drawn free end."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drawrib  # noqa: E402


def main() -> None:
    label_ = sys.argv[1]
    voxel = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    vox, model, hf, x = drawrib.rebuild(label_, voxel)
    cols = drawrib.columns_of(vox, hf, x)
    s = cols["pc"]["solid"]["g"]
    n = np.asarray(model["n"], int)
    h, lo = float(model["h"]), np.asarray(model["lo"], float)
    info = model["info"]
    ks = int(model["k_split"])
    zsp = lo[2] + h * ks
    ijk_all = vox.ijk
    flat = lambda ijk: (ijk[:, 0] * n[1] + ijk[:, 1]) * n[2] + ijk[:, 2]  # noqa: E731
    free_of = np.full(int(np.prod(n)), -1)
    free_of[vox.elem[vox.free_e]] = np.arange(len(vox.free_e))
    frozen_flat = set(vox.elem[vox.frozen].tolist())
    for mt in info["mounts"]:
        cx, cy = mt["centre"]
        c = lo + (ijk_all + 0.5) * h
        lug = (np.hypot(c[:, 0] - cx, c[:, 1] - cy) <= info["settings"]["mount_diameter"] / 2) & (
            c[:, 2] >= mt["z"][0]) & (c[:, 2] <= mt["z"][1])
        lug_ijk = ijk_all[lug & vox.frozen]
        nb = []
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            q = lug_ijk + np.asarray(d)
            ok = np.all((q >= 0) & (q < n), axis=1)
            nb.append(q[ok])
        nb = np.unique(np.concatenate(nb), axis=0)
        fl = flat(nb)
        fi = free_of[fl]
        fi = fi[fi >= 0]
        held = fi[s[fi] >= 0.5]
        print(f"{mt['name']}: {len(lug_ijk)} lug cubes; {len(fi)} free neighbours, {len(held)} solid (>= 0.5); "
              f"{int(sum(f in frozen_flat for f in fl))} frozen neighbours")
        for e in held[:12]:
            col = hf.col[e]
            g = cols["group"][col]
            zc = lo[2] + (vox.ijk[vox.free_e[e], 2] + 0.5) * h
            base = cols["base"][col]
            o_base = h * ((ks - 1) - base) if zc < zsp else h * (base - ks)
            hs = min(cols["hs"][col], cols["zone_len"][col])
            z_end = zsp - (o_base + hs) if zc < zsp else zsp + o_base + hs
            print(f"   cube z {zc:6.1f}: column {col} group {g} (run {cols['run_of_group'][g]}), base k {base}, "
                  f"place {int(hf.pos[e])}, solid {s[e]:.2f}, height {cols['hs'][col]:.1f} (zone {cols['zone_len'][col]:.1f}) "
                  f"-> drawn to z {z_end:.1f}")


if __name__ == "__main__":
    main()
