"""The members drawn clean (LOP-23, 11 October 14:45; the engineer, 14:36-14:38: "still very lumpy";
"we have skipped the CAD build but not the quality of design"). The optimiser decides where metal
goes; the drawing decides how each member looks.

Each half's members are read from the run's field as a plan map of their height off the shell. The
field is a height map over its plan: the casting filter makes each column one run from the split or
the wall (`interval_census.py`). They are drawn again on a 1 mm plan grid:
- tiny islands (under ISLAND mm²) dropped, every other member kept;
- broad parts (BROAD_R mm or more from their edge: webs and pads) as pads, their tops the field's
  heights smoothed, their edges rounded (EDGE_R);
- the rest as ribs along their centre-lines (the skeleton, spurs under SPUR mm pruned), each of a
  production width (WIDTHS, the nearest to its own width smoothed along it) and the field's height
  smoothed along it, with a fully rounded top.

`members_field` puts them back on the mesh route's 2 mm grid as each column's metal from the split
out to the clean top, where the root fillets, kept-clear spaces, exact shell and cuts apply as for
any drawing (`outcome_cad.build_mesh` with LOOP_CLEAN_MEMBERS=1). FE judges the result.

Run alone, it pictures a run's members before and after: `clean_members.py <run> [label]`."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
FINE_PLAN = 1.0  # mm, the plan grid the members are drawn on
ISLAND = 150.0  # mm², the smallest member kept
BROAD_R = 7.0  # mm: a member at least twice this wide is a pad or a web
SPUR = 6.0  # mm, the shortest free end of a centre-line kept
WIDTHS = (5.0, 6.5, 8.0, 10.0, 12.0)  # mm, the ribs' widths (production's 4-5 mm, up to the members' rule)
EDGE_R = 3.0  # mm, a pad's edge rounding
SMOOTH_W, SMOOTH_H = 4.0, 6.0  # mm, the smoothing of each rib's width and height along it


def field_plan(run: str) -> dict:
    z = np.load(OUT / f"{run}.npz")
    n = z["n"].astype(int)
    placed = np.zeros(int(np.prod(n)), bool)
    placed[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    return {"h": float(z["h"]), "lo": z["lo"].astype(float), "n": n, "ks": int(z["k_split"]), "placed": placed.reshape(tuple(n))}


def heights(fp: dict, half: str) -> np.ndarray:
    """mm of placed metal in each column of the half: its members' height off the shell (or, beside
    the cup, their depth from the split)."""
    sl = slice(0, fp["ks"]) if half == "motor_side" else slice(fp["ks"], fp["n"][2])
    return fp["placed"][:, :, sl].sum(axis=2) * fp["h"]


def _disk(r: float) -> np.ndarray:
    k = int(np.ceil(r))
    i, j = np.mgrid[-k : k + 1, -k : k + 1]
    return (i * i + j * j) <= r * r


def _prune(skel: np.ndarray, length: float) -> np.ndarray:
    """The skeleton less every free end shorter than `length` cells that runs into a junction (or
    stands alone): walked from each end pixel while the path has no branch."""
    skel = skel.copy()
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    kernel = np.ones((3, 3), int)
    kernel[1, 1] = 0
    for _ in range(2):
        deg = ndi.convolve(skel.astype(int), kernel, mode="constant") * skel
        for e in np.argwhere(deg == 1):
            path, cur = [tuple(e)], tuple(e)
            while len(path) <= length:
                nxt = [(cur[0] + a, cur[1] + b) for a, b in nb
                       if 0 <= cur[0] + a < skel.shape[0] and 0 <= cur[1] + b < skel.shape[1]
                       and skel[cur[0] + a, cur[1] + b] and (cur[0] + a, cur[1] + b) not in path]  # fmt: skip
                if len(nxt) != 1 or deg[nxt[0]] >= 3:
                    break
                cur = nxt[0]
                path.append(cur)
            if len(path) <= length:
                for q in path:
                    skel[q] = False
    return skel


def clean_plan(m4: np.ndarray, h: float) -> tuple[np.ndarray, dict]:
    """A half's members' heights (mm, on the field's h grid) drawn clean on the FINE_PLAN grid:
    (the clean heights, a summary)."""
    from skimage.morphology import skeletonize

    s = int(round(h / FINE_PLAN))
    present = m4 >= 0.5 * h
    mask = ndi.zoom(ndi.gaussian_filter(present.astype(float), 0.7), s, order=1) >= 0.5
    m1 = np.kron(m4, np.ones((s, s)))[: mask.shape[0], : mask.shape[1]]
    lab, k = ndi.label(mask)
    areas = ndi.sum(mask, lab, index=np.arange(1, k + 1)) * FINE_PLAN**2 if k else np.zeros(0)
    keep = np.r_[False, areas >= ISLAND]
    dropped = float(areas[areas < ISLAND].sum()) if k else 0.0
    mask = keep[lab]
    dt = ndi.distance_transform_edt(mask) * FINE_PLAN
    broad = ndi.binary_opening(mask, structure=_disk(BROAD_R / FINE_PLAN))
    narrow = mask & ~broad
    skel = _prune(skeletonize(narrow), SPUR / FINE_PLAN)

    def along(values: np.ndarray, where: np.ndarray, sigma: float) -> np.ndarray:
        num = ndi.gaussian_filter(np.where(where, values, 0.0), sigma / FINE_PLAN)
        den = ndi.gaussian_filter(where.astype(float), sigma / FINE_PLAN)
        return np.where(den > 1e-6, num / np.maximum(den, 1e-12), 0.0)

    w = along(2.0 * dt, skel, SMOOTH_W)
    tall = ndi.maximum_filter(m1, size=3)
    hgt = along(tall, skel, SMOOTH_H)
    widths = np.asarray(WIDTHS)
    cls = np.abs(w[..., None] - widths[None, None, :]).argmin(axis=-1)
    rib = np.full(mask.shape, -1e9)
    for c, wc in enumerate(widths):
        sel = skel & (cls == c)
        if not sel.any():
            continue
        r = wc / 2.0 / FINE_PLAN
        kk = int(np.ceil(r))
        i, j = np.mgrid[-kk : kk + 1, -kk : kk + 1]
        d = np.hypot(i, j)
        foot = d <= r
        top = np.where(foot, (np.sqrt(np.maximum(r * r - d * d, 0.0)) - r) * FINE_PLAN, 0.0)  # the fully rounded top
        rib = np.maximum(rib, ndi.grey_dilation(np.where(sel, hgt, -1e9), footprint=foot, structure=top))
    pad_top = along(m1, broad, SMOOTH_W)
    dtb = ndi.distance_transform_edt(broad) * FINE_PLAN
    edge = np.where(dtb < EDGE_R, EDGE_R - np.sqrt(np.maximum(EDGE_R**2 - (EDGE_R - dtb) ** 2, 0.0)), 0.0)
    pad = np.where(broad, pad_top - edge, -1e9)
    clean = np.maximum(np.maximum(rib, pad), 0.0)
    clean[clean < 1.0] = 0.0
    stats = {"ribs_mm": float(skel.sum() * FINE_PLAN), "pads_cm2": float(broad.sum() * FINE_PLAN**2 / 100.0),
             "islands_dropped_cm2": dropped / 100.0,
             "widths": {f"{wc:g}": float((skel & (cls == c)).sum() * FINE_PLAN) for c, wc in enumerate(widths)},
             "volume_cm3_before": float(m4.sum() * h * h / 1000.0), "volume_cm3_after": float(clean.sum() * FINE_PLAN**2 / 1000.0)}  # fmt: skip
    return clean, stats


def members_field(run: str, p: dict, half: str, bury: float, fine: float) -> tuple[np.ndarray, dict]:
    """The clean members on the mesh route's grid (`outcome_cad.skin_parts`'s `p`, cells of `fine`
    mm): each column's metal from the split out to its clean top, the top the exact shell's outer
    face (the grid's fixed parts stand `bury` under it) plus the clean height."""
    fp = field_plan(run)
    clean, stats = clean_plan(heights(fp, half), fp["h"])
    s = int(round(fine / FINE_PLAN))
    n_f = p["n_f"]
    grid = np.zeros((n_f[0] * s, n_f[1] * s))
    a, b = min(grid.shape[0], clean.shape[0]), min(grid.shape[1], clean.shape[1])
    grid[:a, :b] = clean[:a, :b]
    m_f = grid.reshape(n_f[0], s, n_f[1], s).max(axis=(1, 3))
    fixed, ks = p["fixed"], p["ks"]
    kk = np.arange(n_f[2])[None, None, :]
    if half == "motor_side":
        lowest = np.where(fixed, kk, n_f[2]).min(axis=2)
        d_fixed = np.where(lowest < n_f[2], ks - lowest, 0)
    else:
        highest = np.where(fixed, kk, -1).max(axis=2)
        d_fixed = np.where(highest >= 0, highest - ks + 1, 0)
    under = np.where(d_fixed > 0, int(round(bury / fine)), 0)
    top = np.where(m_f > 0.0, d_fixed + under + np.rint(m_f / fine), 0).astype(int)
    if half == "motor_side":
        members = (kk >= ks - top[..., None]) & (kk < ks)
    else:
        members = (kk >= ks) & (kk < ks + top[..., None])
    return members.astype(np.float32), stats


def picture(run: str, label: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fp = field_plan(run)
    fig, axes = plt.subplots(2, 2, figsize=(12, 11), dpi=120)
    summary = {}
    for row, half in enumerate(("motor_side", "cover")):
        m4 = heights(fp, half)
        clean, stats = clean_plan(m4, fp["h"])
        summary[half] = stats
        for col, (img, title) in enumerate(((m4, "as optimised (4 mm voxels)"), (clean, "drawn clean (1 mm)"))):
            ax = axes[row, col]
            ax.imshow(np.where(img > 0, img, np.nan).T, origin="lower", cmap="viridis", vmin=0, vmax=28, interpolation="nearest")
            ax.set_title(f"{half.replace('_', ' ')}: {title}", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle(f"{label}: the members' height off the shell, before and after", fontsize=12)
    path = OUT / f"clean_members_{label}.png"
    fig.savefig(path)
    print(json.dumps(summary, indent=1))
    return path


if __name__ == "__main__":
    print(picture(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "run"))
