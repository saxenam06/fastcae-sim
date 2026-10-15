"""PROTOTYPE (LOP-30) - The optimiser's metal cubes round a mount's lug that a smooth drawing lost: each one's place, its column (metal, height,
base, family, layer) as the smooth drawing reads it, the outline field at its points, and how far it is from the lug's
kept-clear rooms.

    lug_probe.py <run stem> <design> <mount name> [sigma]
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("LOOP_EXACT_WALLS", "1")
import outcome_cad as oc  # noqa: E402
import topo  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run, design, mount = sys.argv[1:4]
sigma = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
z = np.load(OUT / f"{run}.npz")
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
m = next(m_ for m_ in lay["mounts"] if m_["name"] == mount)
c = np.asarray(m["centre"], float)
h, lo, n = float(z["h"]), np.asarray(z["lo"], float), np.asarray(z["n"], int)
elem, frozen, free_e, phys = z["elem"], z["frozen"].astype(bool), z["free_e"], np.asarray(z["phys"], float)
kind = np.full(int(np.prod(n)), -1, np.int8)
kind[elem] = 0
kind[elem[frozen]] = 1
col, pos, pts, layer = topo.height_columns(kind, n, int(z["k_split"]), elem, free_e)
spl = oc.voxel_cols_as_spline(run, sigma, 3.0)
ijk = np.column_stack(np.unravel_index(elem[free_e], tuple(n)))
xyz = lo + h * (ijk + 0.5)
near = (np.hypot(xyz[:, 0] - c[0], xyz[:, 1] - c[1]) < 26) & (phys >= 0.5)
surf = pv.read(OUT / f"{design}_motor_side.ply")
sel = np.flatnonzero(near)
inside = np.asarray(pv.PolyData(xyz[sel]).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)["SelectedPoints"]).astype(bool)
print(f"{mount} at {c}, its lug z {m['z']}; the split at {lay['z']['split']}; {len(sel)} metal cubes within 26 mm, {int((~inside).sum())} lost")
best = np.full(len(spl["t"]), -np.inf)
np.maximum.at(best, spl["sub_col"], spl["sub_phi"])
for k, ok in zip(sel, inside, strict=True):
    cc = col[k]
    print(f"  {'kept' if ok else 'LOST'} cube at ({xyz[k, 0]:.0f}, {xyz[k, 1]:.0f}, {xyz[k, 2]:.1f}) r {np.hypot(*(xyz[k, :2] - c)):.1f}: "
          f"density {phys[k]:.2f}, column {cc}: t {spl['t'][cc]:.2f} vox, base {spl['base'][cc]}, split family {bool(spl['on_split'][cc])}, "
          f"layer {int(layer[cc]) % 10_000}, outline best {best[cc]:+.2f}, place along it {int(pos[k])}")
