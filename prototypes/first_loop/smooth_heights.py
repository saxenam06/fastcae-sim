"""A height-field run drawn from its own continuous heights (LOP-23, 11 October 16:00; the engineer,
15:44-15:56: "we need some continuous space on which we can do optimisation"; "creative but
physically optimal designs with smooth shapes... nice fillets... continuous"). The published
smoothings (nTop's smooth body over an implicit, Ježek et al. 2025's signed distance and radial
basis functions, INTES's smoothed hull) all smooth the optimiser's own field before drawing it.

A height-field run (`topo_free.py --height-field <mm>`) holds one continuous variable a column: the
metal's height from the split or the wall under it, smoothed over the plan. Its voxels are those
heights rounded to whole voxels. This drawing goes back to the heights themselves:
- the run's columns are rebuilt from its record (`topo.height_columns`, the same plan filter);
- each column's height off its base is taken from the run's design variables;
- the heights are interpolated cubically onto a 1 mm plan grid (no voxel steps, in plan or in
  height), and kept where at least MIN_HEIGHT mm.

`members_field` puts them on the mesh route's 2 mm grid as each column's metal from the split out
to the smooth top, where the root fillets (`outcome_cad.ROOT_FILLET`), kept-clear spaces, exact
shell and cuts apply as for any drawing (`outcome_cad.build_mesh` with LOOP_CLEAN_MEMBERS=heights).
FE judges it.

Run alone, it pictures a run's heights as voxels and as drawn: `smooth_heights.py <run> [label]`."""

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
FINE_PLAN = 1.0  # mm, the plan grid the heights are drawn on
MIN_HEIGHT = 4.0  # mm: lower than this off its base, a column holds no member (at 2 mm, paper-thin flaps folded the coarsened surface)
ISLAND = 300.0  # mm², the smallest member kept in plan


def column_heights(run: str) -> dict:
    """The run's columns and each one's continuous height off its base (mm), per half: a plan map
    on the run's voxel grid (zero where the column holds no member's variable)."""
    import topo
    import topo_free as tf

    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    hf = rec.get("height_field")
    if not hf:
        raise ValueError(f"{run}: not a height-field run (its record has no `height_field`)")
    z = np.load(OUT / f"{run}.npz")
    h = float(z["h"])
    skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
    model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                          route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                          height_field=hf["radius_mm"], space=rec.get("space") or "")  # fmt: skip
    kind, n = model["kind"], model["n"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    if len(free_e) != len(z["free_e"]):
        raise ValueError(f"{run}: the rebuilt model has {len(free_e):,} free voxels, the run {len(z['free_e']):,}")
    col, pos, pts, layer = topo.height_columns(kind, n, model["k_split"], elem, free_e)
    radius = float(hf["radius_mm"]) / h
    plan = np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]])
    tree = cKDTree(plan)
    pp = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    n_cols = len(pts)
    fmat = (sp.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(n_cols, n_cols)).tocsr() + sp.eye(n_cols) * radius).tocsr()
    fs = np.asarray(fmat.sum(axis=1)).ravel()
    mmat, n_design = (sp.diags(1.0 / fs) @ fmat).tocsr(), n_cols
    if rec.get("height_features"):  # LOP-24: a region's columns from its features' parameters (`topo.feature_map`)
        mmat, n_design, _ = topo.feature_map(rec["height_features"], model["info"], pts, layer, model["lo"], h, fmat, n_cols)
    if rec.get("height_volumes"):  # LOP-24: the design space divided into volumes (`topo.volume_map`)
        mmat, n_design, _ = topo.volume_map(rec["height_volumes"], fmat, n_cols)
    length = float(pos.max() + 1.0)
    x = np.asarray(z["x"], float)
    if len(x) != n_design:
        raise ValueError(f"{run}: {len(x):,} design variables, the model {n_design:,}")
    t = (mmat @ x) * length * h  # mm off each column's base
    out = {"h": h, "lo": model["lo"], "n": n}
    for half, base in (("motor_side", 0), ("cover", 10_000)):
        m4 = np.zeros((n[0], n[1]))
        sel = layer == base + 1  # each column's run from the split or its wall (its first)
        ii, jj = pts[sel, 0].astype(int), pts[sel, 1].astype(int)
        m4[ii, jj] = t[sel]
        out[half] = m4
    return out


def smooth_plan(m4: np.ndarray, h: float) -> np.ndarray:
    """The heights (mm, on the run's h grid) interpolated cubically onto the FINE_PLAN grid, kept
    where at least MIN_HEIGHT; a column without a member's variable counts as zero."""
    s = h / FINE_PLAN
    grid = ndi.zoom(m4, s, order=3, mode="nearest", grid_mode=True)
    keep = grid >= MIN_HEIGHT
    lab, k = ndi.label(keep)
    if k:
        areas = ndi.sum(keep, lab, index=np.arange(1, k + 1)) * FINE_PLAN**2
        keep = np.r_[False, areas >= ISLAND][lab]
    return np.where(keep, grid, 0.0)


def members_field(run: str, p: dict, half: str, bury: float, fine: float) -> tuple[np.ndarray, dict]:
    """The smooth heights on the mesh route's grid (`outcome_cad.skin_parts`'s `p`): each column's
    metal from the split out to its top, the top the exact shell's outer face plus the height."""
    ch = column_heights(run)
    plan = smooth_plan(ch[half], ch["h"])
    s = int(round(fine / FINE_PLAN))
    n_f = p["n_f"]
    grid = np.zeros((n_f[0] * s, n_f[1] * s))
    a, b = min(grid.shape[0], plan.shape[0]), min(grid.shape[1], plan.shape[1])
    grid[:a, :b] = plan[:a, :b]
    m_f = grid.reshape(n_f[0], s, n_f[1], s).mean(axis=(1, 3))
    fixed, ks = p["fixed"], p["ks"]
    kk = np.arange(n_f[2])[None, None, :]
    if half == "motor_side":
        lowest = np.where(fixed, kk, n_f[2]).min(axis=2)
        d_fixed = np.where(lowest < n_f[2], ks - lowest, 0)
    else:
        highest = np.where(fixed, kk, -1).max(axis=2)
        d_fixed = np.where(highest >= 0, highest - ks + 1, 0)
    under = np.where(d_fixed > 0, int(round(bury / fine)), 0)
    top = np.where(m_f >= MIN_HEIGHT, d_fixed + under + np.rint(m_f / fine), 0).astype(int)
    # the continuous depths, for the height-field drawing (`outcome_cad.height_field`, LOOP_HEIGHT_FIELD=1)
    p["depth_cont"] = np.where(m_f >= MIN_HEIGHT, d_fixed + under + m_f / fine, 0.0)
    if half == "motor_side":
        members = (kk >= ks - top[..., None]) & (kk < ks)
    else:
        members = (kk >= ks) & (kk < ks + top[..., None])
    stats = {"volume_cm3": float(plan.sum() * FINE_PLAN**2 / 1000.0), "columns_mm2": float((plan > 0).sum() * FINE_PLAN**2)}
    return members.astype(np.float32), stats


def picture(run: str, label: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ch = column_heights(run)
    fig, axes = plt.subplots(2, 2, figsize=(12, 11), dpi=120)
    for row, half in enumerate(("motor_side", "cover")):
        m4 = ch[half]
        vox = np.round(m4 / ch["h"]) * ch["h"]
        for col, (img, title) in enumerate(((vox, "as voxels (4 mm steps)"), (smooth_plan(m4, ch["h"]), "its continuous heights, 1 mm"))):
            ax = axes[row, col]
            ax.imshow(np.where(img > 0, img, np.nan).T, origin="lower", cmap="viridis", vmin=0, vmax=28, interpolation="nearest")
            ax.set_title(f"{half.replace('_', ' ')}: {title}", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle(f"{label}: the members' height off the shell", fontsize=12)
    path = OUT / f"smooth_heights_{label}.png"
    fig.savefig(path)
    return path


if __name__ == "__main__":
    print(picture(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "run"))
