"""PROTOTYPE (LOP-27) - where a design's outer surface bends, and whose bending it is: the optimiser's, its voxels' or
the drawing's (the engineer, 13 October 00:03: "how do we penalise the rate of change of surface around the
semantically important regions... so that it doesnt wrinkle things there"; a reviewer's note: first establish whether
the wrinkles are in the design field or are introduced when it is drawn).

For each design, on its run's own 4 mm column grid and for each half, three outer surfaces, each as the top's
distance from the split:
- **the optimiser's surface:** each column's continuous height, t = its least height + (M x) L (`topo.Voxels`
  height mode: the design variables through the plan filter, or the volumes' map), on the column's base (the face its
  run starts from: the split, a room's far face or a frozen ring);
- **the voxels:** the sum of the column's voxel densities (what the stiffness sees: at the run's last sharpness each
  voxel is metal or air, so this is t rounded to whole 4 mm voxels);
- **the drawing:** the drawn mesh's outermost surface along the pull at the column centres (vertical rays).
And for each, the bending: the second differences s_xx, s_yy, s_xy and sqrt(s_xx² + s_yy² + 2 s_xy²) (the reviewer's
measure), taken only where every point of the stencil is a first-run column on the same base, so no room's edge or ring
step counts. Prints its median and 90th percentile by half and by kind of column (over a room, beside the rooms); writes
data/first_loop/roughness_<first design>.png (rows the designs; per half the three maps), one log colour scale.

Measured (13 October 00:20, the baseline and cases 2 and 3): the drawing bends less than the optimiser's surface, never
more; the voxels bend as the optimiser's surface does. The wrinkles are the optimiser's own; the drawing adds the 4 mm
staircase of whole voxels. A rib's sides bend most of all, so a bending penalty must be off where ribs are wanted.

Run: .venv/Scripts/python.exe prototypes/first_loop/roughness.py <design> [<design> ...]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import exact_walls  # noqa: E402
import topo  # noqa: E402
import trimesh  # noqa: E402

OUT = topo.OUT
SCALE = (10.0, 3000.0)  # 1/m, the maps' log scale (a flat panel shows at its foot)


def tops(run: str) -> dict:
    """The run's first-run columns: plan cell, half, base (mm from the split), and the optimiser's and the voxels' tops."""
    z = np.load(OUT / f"{run}.npz")
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    n, lo, h, ks = z["n"].astype(int), z["lo"].astype(float), float(z["h"]), int(z["k_split"])
    elem, free_e, frozen = z["elem"], z["free_e"], z["frozen"].astype(bool)
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, pts, layer = topo.height_columns(kind, n, ks, elem, free_e)
    n_cols = len(pts)
    voxels = np.bincount(col, weights=np.asarray(z["phys"], float), minlength=n_cols)
    # the optimiser's continuous heights, as topo.Voxels builds them
    radius = float(rec["height_field"]["radius_mm"]) / h
    plan = np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]])
    tree = cKDTree(plan)
    pp = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    fmat = sp.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(n_cols, n_cols)).tocsr()
    fmat = (fmat + sp.eye(n_cols) * radius).tocsr()
    if rec.get("height_volumes"):
        mmat = topo.volume_map(rec["height_volumes"], fmat, n_cols)[0]
    else:
        mmat = (sp.diags(1.0 / np.asarray(fmat.sum(axis=1)).ravel()) @ fmat).tocsr()
    t = (mmat @ np.asarray(z["x"], float)) * float(pos.max() + 1.0)
    if rec.get("empty"):
        tmin = np.zeros(n_cols)
        np.maximum.at(tmin, col, exact_walls._height_min(run, z)[elem[free_e]])
        t = np.where(tmin > 0, tmin + t, t)
    k = np.unravel_index(elem[free_e], tuple(n))[2]
    first = pos == 0
    k0 = np.zeros(n_cols, int)
    k0[col[first]] = k[first]
    half = layer // 10_000  # 0 the motor side (downward from the split), 1 the cover
    z_split = lo[2] + h * ks
    z_base = np.where(half == 1, lo[2] + h * k0, lo[2] + h * (k0 + 1))
    base = np.abs(z_base - z_split)
    # each first-run column's top as the drawing must take it (13 October 00:50): its height counted over its own free
    # voxels, any frozen voxels between them passed over (a seat's ring sits inside its column), and the run's frozen
    # voxels beyond its top kept; base + h t lost the cover's output seat's ring (empty1h_5.5kg: 315 µm)
    top_true = np.full(n_cols, np.nan)
    code = (layer * 100_000 + pts[:, 0].astype(np.int64)) * 100_000 + pts[:, 1].astype(np.int64)
    look = dict(zip(code.tolist(), range(n_cols), strict=True))
    grid = kind.reshape(tuple(n))
    for hv, sl, flip in ((0, slice(0, ks), True), (1, slice(ks, int(n[2])), False)):
        a = grid[:, :, sl][:, :, ::-1] if flip else grid[:, :, sl]
        mod = a >= 0
        prev = np.concatenate([np.zeros(a.shape[:2] + (1,), bool), mod[:, :, :-1]], axis=2)
        run1 = mod & (np.cumsum(mod & ~prev, axis=2) == 1)
        frz = (a == 1) & run1
        u_ax = np.arange(a.shape[2])
        frozen_u = np.where(frz.any(axis=2), np.where(frz, u_ax[None, None, :], -1).max(axis=2) + 1, 0)
        fi, fj, fu = np.nonzero((a == 0) & run1)
        starts = np.flatnonzero(np.r_[True, (fi[1:] != fi[:-1]) | (fj[1:] != fj[:-1])])
        ends = np.r_[starts[1:], len(fi)]
        for s0, s1 in zip(starts, ends, strict=True):
            c = look.get(((hv * 10_000 + 1) * 100_000 + int(fi[s0])) * 100_000 + int(fj[s0]))
            if c is None:
                continue
            us, tc = fu[s0:s1], float(t[c])
            p_ = int(np.floor(tc))
            top_u = us[-1] + 1.0 if p_ >= len(us) else us[p_] + (tc - p_)
            top_true[c] = h * max(top_u, frozen_u[fi[s0], fj[s0]])
    return {"pts": pts.astype(int), "half": half, "run": layer % 10_000, "base": base, "optimiser": base + h * t, "voxels": base + h * voxels,
            "n": n, "lo": lo, "h": h, "z_split": z_split, "t": t, "top_true": top_true,
            "height": {"col": col, "pos": pos, "pts": pts, "layer": layer, "n_cols": n_cols},
            "ijk_free": np.column_stack(np.unravel_index(elem[free_e], tuple(n))), "phys": np.asarray(z["phys"], float)}  # fmt: skip


def mesh_tops(mesh: trimesh.Trimesh, xs: np.ndarray, ys: np.ndarray, z_split: float, upward: bool) -> np.ndarray:
    """The mesh's outermost surface along the pull at the plan points (xs[i], ys[j]): distance from the split, nan where missed."""
    tri = mesh.triangles
    x0, y0, h = xs[0], ys[0], xs[1] - xs[0]
    out = np.full((len(xs), len(ys)), -np.inf)
    lo_i = np.ceil((tri[:, :, 0].min(axis=1) - x0) / h).astype(int)
    hi_i = np.floor((tri[:, :, 0].max(axis=1) - x0) / h).astype(int)
    lo_j = np.ceil((tri[:, :, 1].min(axis=1) - y0) / h).astype(int)
    hi_j = np.floor((tri[:, :, 1].max(axis=1) - y0) / h).astype(int)
    span = int(max((hi_i - lo_i).max(), (hi_j - lo_j).max(), 0)) + 1
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok_det = np.abs(det) > 1e-12
    for di in range(span):
        for dj in range(span):
            i, j = lo_i + di, lo_j + dj
            m = ok_det & (i <= hi_i) & (j <= hi_j) & (i >= 0) & (j >= 0) & (i < len(xs)) & (j < len(ys))
            if not m.any():
                continue
            px, py = x0 + h * i[m], y0 + h * j[m]
            am, bm, cm, dm = a[m], b[m], c[m], det[m]
            l1 = ((bm[:, 1] - cm[:, 1]) * (px - cm[:, 0]) + (cm[:, 0] - bm[:, 0]) * (py - cm[:, 1])) / dm
            l2 = ((cm[:, 1] - am[:, 1]) * (px - cm[:, 0]) + (am[:, 0] - cm[:, 0]) * (py - cm[:, 1])) / dm
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            zz = l1 * am[:, 2] + l2 * bm[:, 2] + l3 * cm[:, 2]
            d = (zz - z_split) if upward else (z_split - zz)
            np.maximum.at(out, (i[m][inside], j[m][inside]), d[inside])
    return np.where(np.isfinite(out), out, np.nan)


def bending(top: np.ndarray, base: np.ndarray, h: float) -> np.ndarray:
    """sqrt(s_xx² + s_yy² + 2 s_xy²) in 1/m where the whole stencil is present on one base; nan elsewhere."""
    nx, ny = top.shape
    p = np.pad(top, 1, constant_values=np.nan)
    q = np.pad(base, 1, constant_values=np.nan)
    c = (slice(1, nx + 1), slice(1, ny + 1))

    def sh(a, di, dj):
        return a[1 + di : nx + 1 + di, 1 + dj : ny + 1 + dj]

    ok = np.all([np.abs(sh(q, di, dj) - q[c]) < 0.5 * h for di in (-1, 0, 1) for dj in (-1, 0, 1)], axis=0)
    sxx = (sh(p, 1, 0) - 2 * p[c] + sh(p, -1, 0)) / h**2
    syy = (sh(p, 0, 1) - 2 * p[c] + sh(p, 0, -1)) / h**2
    sxy = (sh(p, 1, 1) - sh(p, 1, -1) - sh(p, -1, 1) + sh(p, -1, -1)) / (4 * h**2)
    e = np.sqrt(sxx**2 + syy**2 + 2 * sxy**2) * 1000.0
    return np.where(ok & np.isfinite(e), e, np.nan)


def main(designs: list[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    kinds = ("optimiser", "voxels", "drawing")
    fig, axes = plt.subplots(len(designs), 6, figsize=(30, 5.0 * len(designs)), squeeze=False)
    im = None
    for r, design in enumerate(designs):
        rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
        f = tops(rec["outcome_of"])
        n, lo, h = f["n"], f["lo"], f["h"]
        xs, ys = lo[0] + h * (np.arange(n[0]) + 0.5), lo[1] + h * (np.arange(n[1]) + 0.5)
        for c, (half_name, hv) in enumerate((("cover", 1), ("motor_side", 0))):
            sel = (f["half"] == hv) & (f["run"] == 1)
            pi, pj = f["pts"][sel, 0], f["pts"][sel, 1]
            base = np.full((n[0], n[1]), np.nan)
            base[pi, pj] = f["base"][sel]
            surf = {}
            for kname in ("optimiser", "voxels"):
                s = np.full((n[0], n[1]), np.nan)
                s[pi, pj] = f[kname][sel]
                surf[kname] = s
            mesh = trimesh.load(str(OUT / f"{design}_{half_name}.ply"), process=True)
            surf["drawing"] = np.where(np.isfinite(base), mesh_tops(mesh, xs, ys, f["z_split"], upward=hv == 1), np.nan)
            room = base > 0.5 * h
            for k, kname in enumerate(kinds):
                b = bending(surf[kname], base, h)
                parts = []
                for where, m in (("over a room", room), ("beside", ~room & np.isfinite(base))):
                    v = b[m & np.isfinite(b)]
                    if v.size:
                        parts.append(f"{where} median {np.median(v):6.1f}, 90 % {np.percentile(v, 90):6.1f}")
                print(f"{design:22s} {half_name:10s} {kname:9s} " + "; ".join(parts) + " (1/m)")
                ax = axes[r, 3 * c + k]
                shown = np.where(np.isfinite(b), np.maximum(b, SCALE[0]), np.nan)
                im = ax.imshow(shown.T, origin="lower", extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap="magma", norm=LogNorm(*SCALE))
                for bb in layout["bearings"]:
                    if bb["side"] == ("+z" if hv == 1 else "-z"):
                        ax.add_patch(plt.Circle(bb["axis"], bb["D"] / 2, fill=False, color="c", lw=0.8))
                ax.set_title(f"{design}: {half_name.replace('_', ' ')}, {kname}", fontsize=10)
                ax.set_aspect("equal")
    fig.colorbar(im, ax=axes, shrink=0.5, label="bending of the outer surface (1/m): sqrt(s_xx² + s_yy² + 2 s_xy²)")
    path = OUT / f"roughness_{designs[0]}.png"
    fig.savefig(path, dpi=55, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main(sys.argv[1:])
