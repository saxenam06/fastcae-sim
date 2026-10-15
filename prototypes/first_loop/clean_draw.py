"""PROTOTYPE (LOP-25, the plan's generator B done properly; the engineer, 12 October 15:49-15:57: "we still see such
irregular shapes", "yes" to cleaning the members after the run): a member-like free run (the least member, the greatest
member read near its worst ball: `p40_free`) read as clean members, its layout kept:
- each half's metal (off its base, the run's own densities) thinned to its skeleton, twigs under `PRUNE` mm pruned;
- each branch resampled every `KNOT` mm, its path averaged over `SMOOTH` knots (its ends kept), and drawn straight where
  it lies within `STRAIGHT` mm of its chord;
- along it, its width (twice the metal's distance to its edge, within the thickness rules' 8-16 mm) and its height (the
  column's metal at each knot) averaged the same way, so its section changes gently and its top is fair;
- each seat's boss a ring, from the bore out to where the metal round it thins (at most the trade's 1.25·D + 10 across),
  at the metal's median height.
`implicit_draw.members_body` draws them on the exact, filleted shell as one smooth body (every joint filleted by the smooth
union), and `outcome_cad.build_mesh` cuts it exact (LOOP_CLEAN=1).

    clean_draw.py <run>      prints what it reads and pictures it (data/first_loop/clean_<run tag>.png)"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parts as pm  # noqa: E402
import regions as rg  # noqa: E402
import topo  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"
KNOT = 4.0  # mm between a branch's knots
SMOOTH = 5  # knots a path, a width and a height are averaged over
STRAIGHT = 3.0  # mm: a branch within this of its chord is drawn straight
PRUNE = 12.0  # mm: shorter twigs are pruned
WIDTH = (8.0, 16.0)  # mm: a member's width, within the thickness rules
CRUMB = 10  # cells: a footprint piece smaller than this is a loose crumb, dropped
SHORT = 12.0  # mm: a curved branch shorter than this is a twig, dropped
EXTEND = 6.0  # mm each end runs on, into what it meets
_CACHE = {}


def _average(v: np.ndarray, k: int) -> np.ndarray:
    """A moving average over k knots along a branch (each end its own value), for paths (n, 2) or values (n,)."""
    if len(v) <= 2 or k <= 1:
        return v
    half = k // 2
    pad = np.concatenate([np.repeat(v[:1], half, axis=0), v, np.repeat(v[-1:], half, axis=0)], axis=0)
    out = np.stack([pad[i : i + len(v)] for i in range(2 * half + 1)]).mean(axis=0)
    out[0], out[-1] = v[0], v[-1]
    return out


def read(run: str) -> dict:
    """The run's clean members and bosses, per half (cached)."""
    if run in _CACHE:
        return _CACHE[run]
    from scipy.ndimage import binary_opening, distance_transform_edt
    from scipy.ndimage import label as cc_label
    from skimage.morphology import skeletonize

    import skeleton_members as sk

    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    least = float(rec.get("least_height_mm") or 8.0)
    ctx = rg.context(run)
    model, kind, h, lo = ctx["model"], ctx["kind"], ctx["h"], ctx["lo"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, _, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    z = np.load(OUT / f"{run}.npz")
    phys = np.asarray(z["phys"], float)
    dens = phys if len(phys) == len(z["free_e"]) else phys[z["free_e"]]
    metal_col = np.bincount(col, weights=dens * h, minlength=len(pts))
    n0, n1 = int(model["n"][0]), int(model["n"][1])
    gx, gy = lo[0] + h * (np.arange(n0) + 0.5), lo[1] + h * (np.arange(n1) + 0.5)
    px, py = np.meshgrid(gx, gy, indexing="ij")
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    out = {"run": run, "h": h, "lo": lo, "n": (n0, n1), "least_mm": least, "halves": {}}
    for half, lay_id in pm.LAYER.items():
        on = layer == lay_id
        hmap = np.zeros((n0, n1))
        hmap[pts[on, 0].astype(int), pts[on, 1].astype(int)] = metal_col[on]
        solid = hmap >= least
        rings, taken = [], np.zeros((n0, n1), bool)
        for b in lay["bearings"]:
            if (b["side"] == "+z") != (half == "cover"):
                continue
            c = np.asarray(b["axis"], float)
            r_in, most = 0.5 * float(b["D"]), 0.625 * float(b["D"]) + 5.0
            rho = np.hypot(px - c[0], py - c[1])
            r_out = None
            for r in np.arange(r_in, most, 4.0):
                band = (rho >= r) & (rho < r + 4.0) & (hmap > 0)
                if band.sum() >= 3 and solid[band].mean() >= 0.5:
                    r_out = r + 4.0
                elif band.sum() >= 3:
                    break
            if r_out is None:
                continue
            r_out = min(r_out, most)
            within = (rho >= r_in) & (rho <= r_out) & solid
            if within.sum() < 3:
                continue
            rings.append({"centre": c.tolist(), "r_in": r_in, "r": r_out, "h": float(np.median(hmap[within]))})
            taken |= (rho >= r_in - 2.0) & (rho <= r_out + 2.0)
        foot = solid & ~taken
        foot = binary_opening(foot, np.ones((2, 2), bool)) | (foot & (hmap >= least + 4.0))
        lab, n_lab = cc_label(foot, np.ones((3, 3), int))
        for k in range(1, n_lab + 1):
            if (lab == k).sum() < CRUMB:  # a loose crumb of metal, no member
                foot[lab == k] = False
        edt = distance_transform_edt(foot) * h
        skel = sk.prune(skeletonize(foot), PRUNE / h)
        branches, _ = sk.skeleton_graph(skel)
        members = []
        for br in branches:
            cells = np.asarray(br, float)
            if len(cells) < 2:
                continue
            xy = lo[:2][None, :] + h * (cells + 0.5)
            seg = np.hypot(*np.diff(xy, axis=0).T)
            arc = np.concatenate([[0.0], np.cumsum(seg)])
            if arc[-1] < 8.0:
                continue
            s_k = np.linspace(0.0, arc[-1], max(2, int(round(arc[-1] / KNOT)) + 1))
            ci, cj = cells[:, 0].astype(int), cells[:, 1].astype(int)
            w_c = np.clip(2.0 * edt[ci, cj], *WIDTH)
            h_c = hmap[ci, cj]
            h_c = np.where(h_c >= least, h_c, np.nan)
            if np.isnan(h_c).all():
                continue
            good = ~np.isnan(h_c)
            h_c = np.interp(arc, arc[good], h_c[good])
            xy_k = np.column_stack([np.interp(s_k, arc, xy[:, 0]), np.interp(s_k, arc, xy[:, 1])])
            w_k = _average(np.interp(s_k, arc, w_c), SMOOTH)
            h_k = _average(np.interp(s_k, arc, h_c), SMOOTH)
            chord = xy_k[-1] - xy_k[0]
            length = float(np.hypot(*chord))
            off = np.abs((xy_k[:, 0] - xy_k[0, 0]) * chord[1] - (xy_k[:, 1] - xy_k[0, 1]) * chord[0]) / max(length, 1e-9)
            straight = bool(off.max() <= STRAIGHT)
            if straight:  # nearly straight: drawn straight
                t_ = np.linspace(0.0, 1.0, len(xy_k))
                xy_k = xy_k[0][None, :] + t_[:, None] * chord[None, :]
            else:
                xy_k = _average(xy_k, SMOOTH)
            if length < SHORT and not straight:
                continue
            # each end carried EXTEND mm on along its own direction, so that the member runs into the member, the boss
            # or the wall it meets (12 October 16:05: drawn to the skeleton's ends, joints were left open by a few mm)
            for end, nxt in ((0, 1), (-1, -2)):
                d_ = xy_k[end] - xy_k[nxt]
                d_ = d_ / max(float(np.hypot(*d_)), 1e-9)
                tip = xy_k[end] + EXTEND * d_
                if end == 0:
                    xy_k, w_k, h_k = np.vstack([tip, xy_k]), np.r_[w_k[0], w_k], np.r_[h_k[0], h_k]
                else:
                    xy_k, w_k, h_k = np.vstack([xy_k, tip]), np.r_[w_k, w_k[-1]], np.r_[h_k, h_k[-1]]
            members.append({"xy": xy_k.tolist(), "w": w_k.tolist(), "h": h_k.tolist(), "straight": straight})
        out["halves"][half] = {"rings": rings, "members": members}
    _CACHE[run] = out
    return out


def picture(run: str, data: dict) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Wedge

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    norm = plt.Normalize(0.0, 30.0)
    cmap = matplotlib.colormaps["viridis"]
    for ax, (half, d) in zip(axes, data["halves"].items(), strict=True):
        polys, cols = [], []
        for m in d["members"]:
            xy, w, hh = np.asarray(m["xy"]), np.asarray(m["w"]), np.asarray(m["h"])
            for k in range(len(xy) - 1):
                u = xy[k + 1] - xy[k]
                nrm = np.array([-u[1], u[0]]) / max(np.hypot(*u), 1e-9)
                a_, b_ = 0.5 * w[k] * nrm, 0.5 * w[k + 1] * nrm
                polys.append([xy[k] + a_, xy[k + 1] + b_, xy[k + 1] - b_, xy[k] - a_])
                cols.append(cmap(norm(0.5 * (hh[k] + hh[k + 1]))))
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="none"))
        for r in d["rings"]:
            ax.add_patch(Wedge(r["centre"], r["r"], 0, 360, width=r["r"] - r["r_in"], color=cmap(norm(r["h"])), alpha=0.9))
        n_str = sum(m["straight"] for m in d["members"])
        ax.set_title(f"{half.replace('_', ' ')}: {len(d['members'])} clean members ({n_str} straight), {len(d['rings'])} bosses", fontsize=10)
        ax.set_aspect("equal")
        ax.autoscale_view()
    fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, shrink=0.7, label="height off the base, mm")
    tag = run.split("drive_")[-1].split("_hf")[0]
    target = OUT / f"clean_{tag}.png"
    fig.savefig(target, dpi=80, bbox_inches="tight")
    return target


if __name__ == "__main__":
    data = read(sys.argv[1])
    for half, d in data["halves"].items():
        print(half, len(d["members"]), "members", sum(m["straight"] for m in d["members"]), "straight", len(d["rings"]), "bosses")
    print(picture(sys.argv[1], data))
