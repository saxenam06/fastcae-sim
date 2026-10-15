"""PROTOTYPE (LOP-30) - A spline run's members at a saved state, seen along the pull: each half's members shaded as a relief by how far their
free end stands from the split (the model's own point heights, after the window's cap and the round; the drawing reads
the same fields), the design space light grey, the bearings' bores and the mounts outlined. A light look at a running
optimisation: no drawing, no FE.

    relief_view.py <state npz (x, beta)> <record run stem for the set-up> <spline spec json> <out png> <title>
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import topo  # noqa: E402
from topo_free import build_free  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
state, run, spec_path, png, title = sys.argv[1:6]
rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
z = np.load(state)
model = build_free(float(rec["voxel_mm"]), band=rec["band_mm"], flange=bool(rec["flange"]), mount_reach=rec["mount_reach"],
                   height_field=float(rec["height_field"]["radius_mm"]), empty=bool(rec["empty"]), protect=bool(rec["protect"]),
                   flange_whole=bool(rec.get("flange_whole", True)), drawing_clear=bool(rec.get("drawing_clear")),
                   couplings=rec.get("couplings", "glue"), shell_fixed=bool(rec.get("shell_fixed")), towers=bool(rec.get("towers", True)),
                   route=rec.get("route", "cast"), cavity=rec.get("cavity", "cup"))  # fmt: skip
model["least_height_mm"], model["least_width_mm"] = rec.get("least_height_mm"), rec.get("least_width_mm")
model["spline"] = json.loads(Path(spec_path).read_text(encoding="utf-8"))
vox = topo.Voxels(model)
sp_ = vox.spline
x, beta = np.asarray(z["x"], float), float(z["beta"])
h, lo = float(model["h"]), np.asarray(model["lo"], float)
k_split = int(model["k_split"])
z_split = lo[2] + h * k_split
_, c_ = vox._spline_dens(x, beta)
phi, t_p = c_["phi"], c_["T"]
sub_col = sp_["sub_col"]
base = sp_["base"][sub_col]
half = sp_["sub_half"]
lower = half == 0
face = np.where(lower, lo[2] + h * (base + 1), lo[2] + h * base)
z_end = np.where(lower, face - h * t_p, face + h * t_p)
reach = np.abs(z_end - z_split)  # the free end's distance from the split (mm)
metal = (phi > 0) & (t_p * h > 1.0)
ij = sp_["sub_ij"]
n_sub = (int(ij[:, 0].max()) + 1, int(ij[:, 1].max()) + 1)
step = h / sp_["q"]
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
ls = LightSource(azdeg=315, altdeg=40)
fig, axes = plt.subplots(1, 2, figsize=(22, 10.5))
for ax, (hf, name) in zip(axes, ((0, "motor side (seen from below)"), (1, "cover (seen from above)")), strict=True):
    sel = half == hf
    space = np.zeros(n_sub, bool)
    space[ij[sel, 0], ij[sel, 1]] = True
    g = np.full(n_sub, np.nan)
    m_ = sel & metal
    # the outermost metal point at each plan point (a run past a room stands farther out)
    order = np.argsort(reach[m_])
    idx = np.flatnonzero(m_)[order]
    g[ij[idx, 0], ij[idx, 1]] = reach[idx]
    if hf == 0:  # seen from below: mirror x so the view is as from outside
        g, space = g[::-1, :], space[::-1, :]
    ext = (lo[0], lo[0] + n_sub[0] * step, lo[1], lo[1] + n_sub[1] * step)
    if hf == 0:
        ext = (-ext[1], -ext[0], ext[2], ext[3])
    ax.imshow(np.where(space, 0.85, np.nan).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
    filled = np.where(np.isfinite(g), g, np.nanmin(g) if np.isfinite(g).any() else 0.0)
    rgb = ls.shade(filled.T, cmap=plt.get_cmap("copper"), vert_exag=0.6, blend_mode="soft", vmin=0, vmax=np.nanpercentile(g, 99))
    rgba = np.concatenate([rgb[..., :3], np.isfinite(g).T[..., None].astype(float)], axis=2)
    ax.imshow(rgba, origin="lower", extent=ext, interpolation="bilinear")
    for b in lay["bearings"]:
        if (1 if str(b["side"]).startswith("+") else 0) != hf:
            continue
        cx = -b["axis"][0] if hf == 0 else b["axis"][0]
        ax.add_patch(plt.Circle((cx, b["axis"][1]), 0.5 * float(b["D"]), fill=False, ec="#2b6cb0", lw=1.2))
    for m in lay["mounts"]:
        if hf != (0 if m["z"][1] <= z_split else 1):
            continue
        cx = -m["centre"][0] if hf == 0 else m["centre"][0]
        ax.add_patch(plt.Circle((cx, m["centre"][1]), 0.5 * float(lay["settings"]["mount_diameter"]), fill=False, ec="#c53030", lw=1.2))
    ax.set_aspect("equal")
    ax.set_title(f"{name}: the members, shaded by how far they stand from the split", fontsize=12, loc="left")
    ax.set_xticks([])
    ax.set_yticks([])
fig.suptitle(title, fontsize=13, x=0.01, ha="left")
fig.savefig(png, dpi=75, bbox_inches="tight")
print(png)
