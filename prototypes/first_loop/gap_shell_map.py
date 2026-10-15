"""PROTOTYPE (LOP-30) - Where the least gap read against the shell finds slots on a run's field: each half's points in plan, the shell's fixed
metal grey, the members black, the narrow gaps the closing finds red (with the shell) and orange (without, members alone).

    gap_shell_map.py <run stem> <spec json> <out png>
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import topo  # noqa: E402
from topo_free import build_free  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
run, spec_path, png = sys.argv[1:4]
rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
z = np.load(OUT / f"{run}.npz")
x = np.asarray(z["x"], float)
beta = max(float(z["beta"]) if "beta" in z.files else 16.0, topo.SPLINE_SIZES_BETA)


def gaps(gap_shell: bool):
    model = build_free(float(rec["voxel_mm"]), band=rec["band_mm"], flange=bool(rec["flange"]), mount_reach=rec["mount_reach"],
                       height_field=float(rec["height_field"]["radius_mm"]), empty=bool(rec["empty"]), protect=bool(rec["protect"]),
                       flange_whole=bool(rec.get("flange_whole", True)), drawing_clear=bool(rec.get("drawing_clear")),
                       couplings=rec.get("couplings", "glue"), shell_fixed=bool(rec.get("shell_fixed")), towers=bool(rec.get("towers", True)),
                       route=rec.get("route", "cast"), cavity=rec.get("cavity", "cup"))  # fmt: skip
    model["least_height_mm"], model["least_width_mm"] = rec.get("least_height_mm"), rec.get("least_width_mm")
    model["spline"] = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    model["spline"]["gap_shell"] = gap_shell
    vox = topo.Voxels(model)
    sp_ = vox.spline
    coef = sp_["range"] * (2.0 * x[: sp_["n_phi"]] - 1.0)
    phi = sp_["B_phi"] @ coef
    if sp_["open"] is not None:
        phi = np.where(sp_["alone"], -sp_["range"], phi)
    k_ = beta
    n_s = len(phi)
    if sp_["close"].get("virtual") is not None:
        pc, _ = topo.open_heights(sp_["close"], np.append(-phi, -sp_["range"]), k_)
        pc = pc[:n_s]
    else:
        pc, _ = topo.open_heights(sp_["close"], -phi, k_)
    closed = -(pc + topo._open_bias(sp_["close"], k_)[:n_s])
    gap = (closed > 0) & (phi <= 0) & ~sp_["alone_close"]
    print(f"gap_shell={gap_shell}: points in no block or in the shell's own slots {int(sp_['alone_close'].sum())}; "
          f"narrow-gap points {int(gap.sum())}; the share {vox.spline_sizes(x, beta)[2]}", flush=True)
    grid = np.asarray(model["kind"]).reshape(tuple(model["n"]))
    return sp_, phi, gap, grid, model


sp1, phi, gap1, grid, model = gaps(True)
_, _, gap0, _, _ = gaps(False)
ij, half, q, h = sp1["sub_ij"], sp1["sub_half"], sp1["q"], float(model["h"])
lo = np.asarray(model["lo"], float)
k_split = int(model["k_split"])
fig, axes = plt.subplots(1, 2, figsize=(22, 11))
for ax, hf in zip(axes, (0, 1), strict=True):
    fz = (grid == 1)[:, :, :k_split].any(axis=2) if hf == 0 else (grid == 1)[:, :, k_split:].any(axis=2)
    ci, cj = np.nonzero(fz)
    ax.scatter(lo[0] + h * (ci + 0.5), lo[1] + h * (cj + 0.5), s=3, c="#cccccc", marker="s", lw=0)
    sel = half == hf
    xy = lo[:2] + (h / q) * (ij + 0.5)
    m = sel & (phi > 0)
    ax.scatter(xy[m, 0], xy[m, 1], s=1.2, c="k", lw=0)
    g0 = sel & gap0
    g1 = sel & gap1 & ~gap0
    ax.scatter(xy[g0, 0], xy[g0, 1], s=2.0, c="orange", lw=0)
    ax.scatter(xy[g1, 0], xy[g1, 1], s=2.0, c="red", lw=0)
    ax.set_aspect("equal")
    ax.set_title(f"{'motor side' if hf == 0 else 'cover'}: members black, fixed metal in plan grey; narrow gaps among "
                 f"members orange ({int(g0.sum())} points), against the shell too red ({int(g1.sum())})", fontsize=10, loc="left")
fig.tight_layout()
fig.savefig(OUT / png, dpi=70)
print(OUT / png)
