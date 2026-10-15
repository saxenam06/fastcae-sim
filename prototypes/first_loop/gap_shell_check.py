"""PROTOTYPE (LOP-30) - The least gap read against the shell (`gap_shell`, 15 October 05:05): on spl8's own set-up and final field, the sizes
constraint with and without it (the slot share it finds), and its derivative against central differences.

    gap_shell_check.py <run stem> <spec json> [eps]
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import topo  # noqa: E402
from topo_free import build_free  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run, spec_path = sys.argv[1], sys.argv[2]
eps = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-5
rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
z = np.load(OUT / f"{run}.npz")


def voxels(gap_shell: bool):
    model = build_free(float(rec["voxel_mm"]), band=rec["band_mm"], flange=bool(rec["flange"]), mount_reach=rec["mount_reach"],
                       height_field=float(rec["height_field"]["radius_mm"]), empty=bool(rec["empty"]), protect=bool(rec["protect"]),
                       flange_whole=bool(rec.get("flange_whole", True)), drawing_clear=bool(rec.get("drawing_clear")),
                       couplings=rec.get("couplings", "glue"), shell_fixed=bool(rec.get("shell_fixed")), towers=bool(rec.get("towers", True)),
                       route=rec.get("route", "cast"), cavity=rec.get("cavity", "cup"))  # fmt: skip
    model["least_height_mm"], model["least_width_mm"] = rec.get("least_height_mm"), rec.get("least_width_mm")
    model["spline"] = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    model["spline"]["gap_shell"] = gap_shell
    t0 = time.time()
    vox = topo.Voxels(model)
    print(f"gap_shell={gap_shell}: set up in {time.time() - t0:.0f} s; closing blocks {len(vox.spline['close']['blocks'])}, "
          f"points in none {int(vox.spline['alone_close'].sum())} of {len(vox.spline['alone_close'])}", flush=True)
    return vox


x = np.asarray(z["x"], float)
beta = float(z["beta"]) if "beta" in z.files else 16.0
print(f"x {len(x)}, beta {beta:g}", flush=True)
v0 = voxels(False)
g0, d0, s0 = v0.spline_sizes(x, beta)
print(f"without: the thin share {s0[0]:.5f}, the narrow-gap share {s0[1]:.5f}", flush=True)
del v0
v1 = voxels(True)
g1, d1, s1 = v1.spline_sizes(x, beta)
print(f"with the shell: the thin share {s1[0]:.5f}, the narrow-gap share {s1[1]:.5f}", flush=True)
rng = np.random.default_rng(3)
n_phi = v1.spline["n_phi"]
for t_ in range(4):
    d = np.zeros(len(x))
    idx = rng.choice(n_phi, size=200, replace=False)
    d[idx] = rng.standard_normal(200)
    gp, _, _ = v1.spline_sizes(x + eps * d, beta)
    gm, _, _ = v1.spline_sizes(x - eps * d, beta)
    fd = (gp - gm) / (2 * eps)
    an = d1 @ d
    print(f"direction {t_}: central differences {fd}, the derivative {an}, relative error "
          f"{np.abs(fd - an) / np.maximum(np.abs(fd), 1e-12)}", flush=True)
