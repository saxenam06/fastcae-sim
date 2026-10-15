"""PROTOTYPE (LOP-32) - The members' fairing rules (the engineer, 15 October 16:10: "Reward. add rules"; with an outside review:
a topology-frozen fairing stage, local rules measured on a temporary skeleton, never on one global integral).

A height-field run's members are read on a temporary skeleton, the frame: per half, level and family (the drawing's groups),
the columns holding metal are rastered at 1 mm, thinned to their skeleton, cut into branches between ends and junctions,
each branch smoothed along itself and sampled every 2 mm with its tangent, normal and half-width. Junctions, member ends,
short stubs and broad webs are masked. On the frame, three local measures along each member, as functions of the columns'
heights t (voxels) with their derivatives:

- **the top's bend** (1/mm): the second difference of the free end (its distance from the split, the visible top) over
  8 mm each side; a straight taper costs nothing, a rise and fall does;
- **the top's slope**: its first difference;
- **the width's change**: the first difference of the member's width, its normal transect's metal (each column's
  indicator, a soft step at half the least member, interpolated bilinearly along the transect).

Each measure is aggregated by a KS function (a smooth maximum) over the unmasked points: a local worst case, so one ugly
member cannot hide among calm ones (the bending rule of 13 October halved a global integral and changed nothing seen).
`topo.solve_model` holds each at most its limit (`model["fair"]`), the frame rebuilt every few iterations from the current
heights; the frame never becomes the geometry.

    member_fair.py <run stem> [--out <png>]   the frame and the measures on a run, pictured (no optimisation)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy import ndimage

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "first_loop"

FINE = 1.0  # mm: the plan raster the skeleton is read on
DS = 2.0  # mm: the frame's points along a member
STENCIL = 4  # points: each difference taken over STENCIL * DS each side (8 mm)
SMOOTH = 3.0  # mm: a skeleton branch smoothed along itself before its tangents are read
METAL = 1.0  # voxels: a column holds metal from this height (half the least member of 8 mm)
EDGE = 0.35  # voxels: the width's indicator's soft edge round METAL
SPUR = 8.0  # mm: twigs shorter than this (or 1.5 widths at their junction) are pruned from the skeleton
JUNCTION = 1.5  # widths round a junction masked (at least LEAST_MASK)
END = 1.0  # widths from a member's free end masked (at least LEAST_MASK)
LEAST_MASK = 6.0  # mm
STUB = 3.0  # widths: a shorter branch is masked whole (at least 16 mm)
BROAD = 24.0  # mm: wider than this, a web, not a member: masked
MARGIN = 4.0  # mm: a width's transect runs this far past the frame's half-width
ABS_EPS = 1e-3  # the smooth absolute value's floor (the measures' units)
MEASURES = ("top_bend", "top_slope", "width_change")
UNITS = {"top_bend": "1/mm", "top_slope": "", "width_change": ""}
_NB = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def column_info(kind: np.ndarray, n, k_split: int, elem: np.ndarray, free_e: np.ndarray) -> dict:
    """Each height-field column's plan cell, half, base, family (on the split or on a wall) and level (its place in its plan
    cell's stack, from the split out), as `outcome_cad.voxel_cols_as_spline` reads them, and its base's distance from the
    split (voxels): a column's free end is `o_base + t` voxels out from the split."""
    import topo

    n = np.asarray(n, int)
    col, pos, pts, layer = topo.height_columns(kind, n, k_split, elem, free_e)
    n_cols = len(pts)
    kz = elem[free_e] % int(n[2])
    base = np.full(n_cols, -1, np.int64)
    base[col[pos == 0]] = kz[pos == 0]
    half = (np.asarray(layer, np.int64) // 10_000).astype(np.int8)
    ii, jj = pts[:, 0].astype(int), pts[:, 1].astype(int)
    grid = kind.reshape(tuple(n))
    off = np.concatenate([np.zeros(tuple(n[:2]) + (1,), np.int64), np.cumsum(grid < 0, axis=2)], axis=2)
    k0 = np.where(half == 1, k_split, base + 1)
    k1 = np.where(half == 1, base, k_split)
    on_split = (off[ii, jj, np.maximum(k1, k0)] - off[ii, jj, k0]) == 0
    lay = np.zeros(n_cols, np.int64)
    for hf_ in (0, 1):
        sel = np.flatnonzero(half == hf_)
        seen: dict = {}
        for k in sel[np.argsort(-base[sel] if hf_ == 0 else base[sel], kind="stable")]:
            key = (ii[k], jj[k])
            lay[k] = seen.get(key, 0)
            seen[key] = lay[k] + 1
    o_base = np.where(half == 0, (k_split - 1) - base, base - k_split).astype(float)
    group = {}
    for k, key in enumerate(zip(half.tolist(), lay.tolist(), on_split.tolist(), strict=True)):
        group.setdefault(key, []).append(k)
    return {"col": col, "pos": pos, "ij": np.column_stack([ii, jj]), "half": half, "base": base, "on_split": on_split, "lay": lay,
            "o_base": o_base, "groups": {k: np.asarray(v, np.int64) for k, v in group.items()}, "n_cols": n_cols}  # fmt: skip


def indicator(t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A column's metal as a soft step at METAL voxels, and its slope by the height."""
    th = np.tanh((t - METAL) / EDGE)
    return 0.5 * (1.0 + th), 0.5 * (1.0 - th * th) / EDGE


def _skeleton(mask: np.ndarray) -> np.ndarray:
    from skimage.morphology import skeletonize, thin

    return thin(skeletonize(mask))


def _trace(sk: np.ndarray):
    """A one-pixel skeleton's branches: each an ordered list of pixels from a node to a node (a node: a cluster of pixels
    with other than two neighbours), and each node's pixels; a closed loop is one branch from and to the same pixel."""
    H, W = sk.shape
    cnt = ndimage.convolve(sk.astype(np.int16), np.ones((3, 3), np.int16), mode="constant") - sk.astype(np.int16)
    cnt = np.where(sk, cnt, 0)
    node = sk & (cnt != 2)
    lab, n_lab = ndimage.label(node, structure=np.ones((3, 3), int))
    visited = np.zeros_like(sk, dtype=bool)

    def nbrs(p):
        i, j = p
        return [(i + a, j + b) for a, b in _NB if 0 <= i + a < H and 0 <= j + b < W and sk[i + a, j + b]]

    paths = []
    for p in map(tuple, np.argwhere(node)):
        for q in nbrs(p):
            if node[q]:
                if lab[q] != lab[p] and lab[p] < lab[q]:  # two node clusters touching: a branch of two pixels
                    paths.append([p, q])
                continue
            if visited[q]:
                continue
            path, prev, cur = [p, q], p, q
            visited[q] = True
            while True:
                nxt = [r for r in nbrs(cur) if r != prev and r not in path[-3:]]
                at_node = [r for r in nxt if node[r]]
                if at_node:
                    path.append(at_node[0])
                    break
                nxt = [r for r in nxt if not visited[r]]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                visited[cur] = True
                path.append(cur)
            paths.append(path)
    for p in map(tuple, np.argwhere(sk & ~node & ~visited)):  # loops with no node
        if visited[p]:
            continue
        path, prev, cur = [p], None, p
        visited[p] = True
        while True:
            nxt = [r for r in nbrs(cur) if r != prev and not visited[r]]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            visited[cur] = True
            path.append(cur)
        path.append(p)
        paths.append(path)
    return paths, lab, n_lab


def _graph(mask: np.ndarray, edt: np.ndarray):
    """The skeleton's branches after pruning spurs and joining through nodes of two: (paths, ends of each path as node ids
    or -1, each node's degree and centre)."""
    sk = _skeleton(mask)
    for _round in range(4):
        paths, lab, n_lab = _trace(sk)
        ends = [(int(lab[p[0]]) - 1 if lab[p[0]] else -1, int(lab[p[-1]]) - 1 if lab[p[-1]] else -1) for p in paths]
        deg = np.zeros(max(n_lab, 1), int)
        for a, b in ends:
            for e in (a, b):
                if e >= 0:
                    deg[e] += 1
        cut = False
        for p, (a, b) in zip(paths, ends, strict=True):
            if a < 0 or b < 0:
                continue
            spur_end = (deg[a] == 1 and deg[b] >= 3) or (deg[b] == 1 and deg[a] >= 3)
            if not spur_end:
                continue
            junction = p[-1] if deg[b] >= 3 else p[0]
            limit = max(SPUR, 1.5 * 2.0 * float(edt[junction]))
            if len(p) * FINE < limit:
                for q in p:
                    if lab[q] == 0 or deg[lab[q] - 1] == 1:  # the twig's own pixels and its end, never the junction
                        sk[q] = False
                cut = True
        if not cut:
            break
    paths, lab, n_lab = _trace(sk)
    ends = [(int(lab[p[0]]) - 1 if lab[p[0]] else -1, int(lab[p[-1]]) - 1 if lab[p[-1]] else -1) for p in paths]
    deg = np.zeros(max(n_lab, 1), int)
    for a, b in ends:
        for e in (a, b):
            if e >= 0:
                deg[e] += 1
    # a node of degree two joins its two branches into one (a corner the thinning read as a node)
    changed = True
    while changed:
        changed = False
        for nd in np.flatnonzero(deg == 2):
            at = [k for k, (a, b) in enumerate(ends) if a == nd or b == nd]
            if len(at) != 2 or at[0] == at[1]:
                continue
            k1, k2 = at
            p1 = paths[k1] if ends[k1][1] == nd else paths[k1][::-1]
            e1 = ends[k1][0] if ends[k1][1] == nd else ends[k1][1]
            p2 = paths[k2] if ends[k2][0] == nd else paths[k2][::-1]
            e2 = ends[k2][1] if ends[k2][0] == nd else ends[k2][0]
            paths[k1], ends[k1] = p1 + p2[1:], (e1, e2)
            del paths[k2], ends[k2]
            deg[nd] = 0
            changed = True
            break
    centres = ndimage.center_of_mass(np.ones_like(lab), lab, range(1, n_lab + 1)) if n_lab else []
    return paths, ends, deg, np.asarray(centres, float).reshape(-1, 2)


class Frame:
    """The temporary skeleton of a height-field design's members and the measures' operators on its columns.

    `cols` is `column_info`'s; `t` each column's height (voxels); `lo` the grid's corner (mm), `h` the cube (mm)."""

    def __init__(self, cols: dict, t: np.ndarray, lo, h: float, skip: tuple = ()):
        self.h, self.cols = float(h), cols
        lo = np.asarray(lo, float)
        n_cols = cols["n_cols"]
        cx = lo[0] + h * (cols["ij"][:, 0] + 0.5)
        cy = lo[1] + h * (cols["ij"][:, 1] + 0.5)
        self.cxy = np.column_stack([cx, cy])
        metal = t >= METAL
        r = int(round(h / FINE))
        pts, tang, norm, half_w, mask, branch, gkey = [], [], [], [], [], [], []
        rows_a, cols_a, vals_a = [], [], []  # the free end's sampling: frame point x column
        rows_r, cols_r, vals_r = [], [], []  # the width's transect: frame point x column
        self.branches = []
        n_pt = 0
        for key, idx in cols["groups"].items():
            if key in skip:
                continue
            mine = idx[metal[idx]]
            if len(mine) < 3:
                continue
            ij = cols["ij"][idx]
            i0, j0 = ij.min(axis=0) - 3
            i1, j1 = ij.max(axis=0) + 4
            shape = (int(i1 - i0), int(j1 - j0))
            cell = -np.ones(shape, np.int64)  # each plan cell's column of this group
            cell[ij[:, 0] - i0, ij[:, 1] - j0] = idx
            met = np.zeros(shape, bool)
            met[cols["ij"][mine, 0] - i0, cols["ij"][mine, 1] - j0] = True
            fine = np.kron(met, np.ones((r, r), bool))
            fine = ndimage.gaussian_filter(fine.astype(float), 1.0 / FINE) >= 0.5
            edt = ndimage.distance_transform_edt(fine) * FINE
            paths, ends, deg, centres = _graph(fine, edt)
            ox, oy = lo[0] + h * i0, lo[1] + h * j0  # the fine raster's corner, mm
            junctions = [ox + (centres[k, 0] + 0.5) * FINE for k in np.flatnonzero(deg >= 3)]
            junctions = np.column_stack([junctions, [oy + (centres[k, 1] + 0.5) * FINE for k in np.flatnonzero(deg >= 3)]]) if junctions else np.zeros((0, 2))
            free_ends = set(np.flatnonzero(deg == 1).tolist())
            widths_all = []
            prepared = []
            for p, (ea, eb) in zip(paths, ends, strict=True):
                if len(p) < 3:
                    continue
                pix = np.asarray(p, float)
                xy = np.column_stack([ox + (pix[:, 0] + 0.5) * FINE, oy + (pix[:, 1] + 0.5) * FINE])
                a_pix = np.array([edt[q] for q in p])
                seg = np.hypot(*np.diff(xy, axis=0).T)
                s = np.r_[0.0, np.cumsum(seg)]
                length = float(s[-1])
                if length < DS * 2:
                    continue
                sm = np.column_stack([ndimage.gaussian_filter1d(xy[:, k], SMOOTH / FINE, mode="nearest") for k in (0, 1)])
                s_new = np.arange(0.5 * (length % DS), length + 1e-9, DS)
                c = np.column_stack([np.interp(s_new, s, sm[:, 0]), np.interp(s_new, s, sm[:, 1])])
                a = np.interp(s_new, s, a_pix)
                prepared.append((c, a, s_new, length, ea in free_ends, eb in free_ends))
                widths_all.append(2.0 * a)
            med_w = float(np.median(np.concatenate(widths_all))) if widths_all else 8.0
            for c, a, s_new, length, end_a, end_b in prepared:
                if len(c) < 3:
                    continue
                g = np.gradient(c, axis=0)
                g /= np.maximum(np.hypot(g[:, 0], g[:, 1]), 1e-9)[:, None]
                nrm = np.column_stack([-g[:, 1], g[:, 0]])
                w = 2.0 * a
                masked = np.zeros(len(c), bool)
                if length < max(STUB * med_w, 16.0):
                    masked[:] = True
                if len(junctions):
                    d_j = np.min(np.hypot(c[:, None, 0] - junctions[None, :, 0], c[:, None, 1] - junctions[None, :, 1]), axis=1)
                    masked |= d_j <= np.maximum(JUNCTION * w, LEAST_MASK)
                if end_a:
                    masked |= s_new <= np.maximum(END * w, LEAST_MASK)
                if end_b:
                    masked |= (length - s_new) <= np.maximum(END * w, LEAST_MASK)
                masked |= w > BROAD
                b_id = len(self.branches)
                self.branches.append({"group": key, "first": n_pt, "count": len(c), "length_mm": length})
                for k in range(len(c)):
                    # the free end's sample: the group's metal columns within the half-width (at least 0.6 of a cube)
                    rho = max(float(a[k]), 0.6 * h)
                    d = np.hypot(cx[mine] - c[k, 0], cy[mine] - c[k, 1])
                    near = d <= rho
                    if not near.any():
                        if d.min() <= a[k] + h:
                            near = d == d.min()
                        else:
                            masked[k] = True
                            near = d == d.min()
                    wt = np.exp(-0.5 * (d[near] / (rho / 1.5)) ** 2)
                    wt /= wt.sum()
                    rows_a += [n_pt + k] * int(near.sum())
                    cols_a += mine[near].tolist()
                    vals_a += wt.tolist()
                    # the width's transect: the columns' indicator, bilinear between their centres, across the member
                    half = float(a[k]) + MARGIN
                    s_t = np.arange(-half, half + 1e-9, 1.0)
                    px = c[k, 0] + s_t * nrm[k, 0]
                    py = c[k, 1] + s_t * nrm[k, 1]
                    fi = (px - lo[0]) / h - 0.5 - i0
                    fj = (py - lo[1]) / h - 0.5 - j0
                    a0 = np.floor(fi).astype(int)
                    b0 = np.floor(fj).astype(int)
                    u = fi - a0
                    v = fj - b0
                    acc: dict = {}
                    for da, db, wv in ((0, 0, (1 - u) * (1 - v)), (1, 0, u * (1 - v)), (0, 1, (1 - u) * v), (1, 1, u * v)):
                        aa, bb = a0 + da, b0 + db
                        ok = (aa >= 0) & (aa < shape[0]) & (bb >= 0) & (bb < shape[1])
                        cc = np.where(ok, cell[np.clip(aa, 0, shape[0] - 1), np.clip(bb, 0, shape[1] - 1)], -1)
                        for col_k, wv_k in zip(cc[cc >= 0].tolist(), wv[cc >= 0].tolist(), strict=True):
                            acc[col_k] = acc.get(col_k, 0.0) + wv_k * 1.0  # mm of transect per sample
                    rows_r += [n_pt + k] * len(acc)
                    cols_r += list(acc.keys())
                    vals_r += list(acc.values())
                pts.append(c)
                tang.append(g)
                norm.append(nrm)
                half_w.append(a)
                mask.append(masked)
                branch += [b_id] * len(c)
                gkey += [key] * len(c)
                n_pt += len(c)
        self.n_pts = n_pt
        self.xy = np.vstack(pts) if pts else np.zeros((0, 2))
        self.tangent = np.vstack(tang) if tang else np.zeros((0, 2))
        self.normal = np.vstack(norm) if norm else np.zeros((0, 2))
        self.half_w = np.concatenate(half_w) if half_w else np.zeros(0)
        self.masked = np.concatenate(mask) if mask else np.zeros(0, bool)
        self.branch = np.asarray(branch, np.int64)
        self.group = gkey
        self.A = sp.csr_matrix((vals_a, (rows_a, cols_a)), shape=(n_pt, n_cols))
        self.R = sp.csr_matrix((vals_r, (rows_r, cols_r)), shape=(n_pt, n_cols))
        # the differences along each branch: a point and its neighbours STENCIL points away, all three unmasked
        m = STENCIL
        i_c, i_m, i_p = [], [], []
        for b in self.branches:
            f, k = b["first"], b["count"]
            for q in range(f + m, f + k - m):
                if not (self.masked[q] or self.masked[q - m] or self.masked[q + m]):
                    i_c.append(q)
                    i_m.append(q - m)
                    i_p.append(q + m)
        self.at = np.asarray(i_c, np.int64)
        n_at = len(i_c)
        L = m * DS
        rr = np.arange(n_at)
        D2 = sp.csr_matrix((np.r_[np.full(n_at, 1.0), np.full(n_at, -2.0), np.full(n_at, 1.0)] / L**2,
                            (np.r_[rr, rr, rr], np.r_[i_p, i_c, i_m])), shape=(n_at, n_pt))  # fmt: skip
        D1 = sp.csr_matrix((np.r_[np.full(n_at, 1.0), np.full(n_at, -1.0)] / (2.0 * L), (np.r_[rr, rr], np.r_[i_p, i_m])), shape=(n_at, n_pt))
        self.ops = {"top_bend": ((D2 @ self.A).tocsr(), "E"), "top_slope": ((D1 @ self.A).tocsr(), "E"),
                    "width_change": ((D1 @ self.R).tocsr(), "U")}  # fmt: skip

    def raw(self, t: np.ndarray) -> dict:
        """Each measure's signed value at every point it is taken at (`at`), and the per-column fields it reads."""
        E = self.h * (self.cols["o_base"] + t)
        U, _ = indicator(t)
        return {name: np.asarray(op @ (E if what == "E" else U)).ravel() for name, (op, what) in self.ops.items()}

    def values(self, t: np.ndarray, limits: dict, rho: float, names=MEASURES):
        """Each measure's constraint: the KS aggregate (a smooth maximum at sharpness `rho`) of its points' absolute values
        over its limit, less 1: (1/rho) log sum exp(rho (v / limit - 1)), at most 0 when every point is within its limit
        (a few hundredths conservative where several are near it); its gradient by the columns' heights (voxels); and its
        points' absolute values. A measure taken at no point reads -1."""
        E = self.h * (self.cols["o_base"] + t)
        U, dU = indicator(t)
        out = {}
        for name in names:
            op, what = self.ops[name]
            if op.shape[0] == 0:
                out[name] = (-1.0, np.zeros_like(t), np.zeros(0))
                continue
            z = np.asarray(op @ (E if what == "E" else U)).ravel()
            v = np.sqrt(z * z + ABS_EPS**2)
            lim = float(limits[name])
            y = rho * (v / lim - 1.0)
            y_max = float(y.max())
            e = np.exp(y - y_max)
            g_val = (y_max + np.log(e.sum())) / rho
            wgt = (e / e.sum()) * (z / v) / lim  # d g / d z
            grad = np.asarray(op.T @ wgt).ravel() * (self.h if what == "E" else dU)
            out[name] = (float(g_val), grad, v)
        return out


def from_run(run: str):
    """A run's columns, heights (its cubes' densities summed: the metal it holds) and grid, for the CLI."""
    z = np.load(OUT / f"{run}.npz")
    n = np.asarray(z["n"], int)
    elem, frozen, free_e = z["elem"], z["frozen"].astype(bool), z["free_e"]
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    cols = column_info(kind, n, int(z["k_split"]), elem, free_e)
    t = np.bincount(cols["col"], weights=np.asarray(z["phys"], float), minlength=cols["n_cols"])
    return cols, t, np.asarray(z["lo"], float), float(z["h"])


def summary(frame: Frame, t: np.ndarray) -> dict:
    raw = frame.raw(t)
    out = {"points": int(frame.n_pts), "unmasked": int((~frame.masked).sum()), "taken": int(len(frame.at)), "branches": len(frame.branches)}
    for name, v in raw.items():
        a = np.abs(v)
        out[name] = {"p50": float(np.percentile(a, 50)) if len(a) else 0.0, "p95": float(np.percentile(a, 95)) if len(a) else 0.0,
                     "max": float(a.max()) if len(a) else 0.0, "units": UNITS[name]}  # fmt: skip
    return out


def picture(frame: Frame, t: np.ndarray, cols: dict, png: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raw = frame.raw(t)
    bend = np.full(frame.n_pts, np.nan)
    bend[frame.at] = np.abs(raw["top_bend"])
    wch = np.full(frame.n_pts, np.nan)
    wch[frame.at] = np.abs(raw["width_change"])
    fig = plt.figure(figsize=(26, 19))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.25, 1.25, 1.0])
    metal = t >= METAL
    for hf_ in (0, 1):
        for c_, (field, label, vmax) in enumerate(((bend, "the top's bend |d2E/ds2| (1/mm)", 0.15), (wch, "the width's change |dw/ds|", 0.6))):
            ax = fig.add_subplot(gs[hf_, 2 * c_ : 2 * c_ + 2])
            sel = (cols["half"] == hf_) & metal
            ax.scatter(frame.cxy[sel, 0], frame.cxy[sel, 1], s=9, marker="s", c="#d9d4cc", lw=0)
            mine = np.array([g[0] == hf_ for g in frame.group], bool) if frame.n_pts else np.zeros(0, bool)
            ax.scatter(frame.xy[mine & frame.masked, 0], frame.xy[mine & frame.masked, 1], s=3, c="#9a9a9a", lw=0)
            ok = mine & ~np.isnan(field)
            sc = ax.scatter(frame.xy[ok, 0], frame.xy[ok, 1], s=7, c=field[ok], cmap="inferno_r", vmin=0, vmax=vmax, lw=0)
            fig.colorbar(sc, ax=ax, shrink=0.7, label=label)
            ax.set_aspect("equal")
            ax.set_title(f"{['motor side', 'cover'][hf_]}: {label} along each member (grey: masked, beige: the columns holding metal)", fontsize=11, loc="left")
    # the worst branches' profiles: the free end and the width along the member
    E = frame.h * (cols["o_base"] + t)
    U, _ = indicator(t)
    e_s = np.asarray(frame.A @ E).ravel()
    w_s = np.asarray(frame.R @ U).ravel()
    worst = {}
    for k_, q in zip(frame.at, np.abs(raw["top_bend"]), strict=True):
        b = int(frame.branch[k_])
        worst[b] = max(worst.get(b, 0.0), float(q))
    order = sorted(worst, key=lambda b: -worst[b])[:4]
    for c_, b in enumerate(order):
        ax = fig.add_subplot(gs[2, c_])
        br = frame.branches[b]
        sl = slice(br["first"], br["first"] + br["count"])
        s_ = DS * np.arange(br["count"])
        ax.plot(s_, e_s[sl], "-", c="tab:red", label="free end from the split (mm)")
        ax.plot(s_, w_s[sl], "-", c="tab:blue", label="width (mm)")
        mk = frame.masked[sl]
        ax.plot(s_[mk], e_s[sl][mk], "o", ms=3, c="#999999", label="masked")
        hf_, lay_, fam_ = br["group"]
        ax.set_title(f"branch {b}: {['motor side', 'cover'][hf_]}, level {lay_}, {'on the split' if fam_ else 'on a wall'}; worst bend {worst[b]:.3f}/mm", fontsize=10, loc="left")
        ax.set_xlabel("along the member (mm)")
        ax.legend(fontsize=8)
    fig.suptitle(title, fontsize=14, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(png, dpi=55)
    plt.close(fig)


def check(frame: Frame, t: np.ndarray, limits: dict, rho: float = 20.0, count: int = 12, step: float = 1e-4, seed: int = 1) -> float:
    """The measures' derivatives by the columns' heights against central differences, at the columns each reads most;
    returns the worst relative error."""
    rng = np.random.default_rng(seed)
    base = frame.values(t, limits, rho)
    worst = 0.0
    for name in MEASURES:
        g = base[name][1]
        cand = np.flatnonzero(np.abs(g) > 1e-6 * max(np.abs(g).max(), 1e-30))
        if len(cand) == 0:
            continue
        pick = rng.choice(cand, size=min(count, len(cand)), replace=False)
        for k in pick:
            tp, tm = t.copy(), t.copy()
            tp[k] += step
            tm[k] -= step
            fd = (frame.values(tp, limits, rho, (name,))[name][0] - frame.values(tm, limits, rho, (name,))[name][0]) / (2 * step)
            err = abs(fd - g[k]) / max(abs(fd), abs(g[k]), 1e-12)
            worst = max(worst, err)
        print(f"{name}: {len(pick)} columns, the worst relative error so far {worst:.2e}")
    return worst


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The members' frame and fairing measures on a run (LOP-32).")
    ap.add_argument("run")
    ap.add_argument("--out", default="")
    ap.add_argument("--check", action="store_true", help="the measures' derivatives against central differences")
    a = ap.parse_args()
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    sys.path.insert(0, str(HERE))
    cols_, t_, lo_, h_ = from_run(a.run)
    fr = Frame(cols_, t_, lo_, h_)
    rep = summary(fr, t_)
    print(json.dumps(rep, indent=1))
    if a.check:
        lim_ = {nm: 0.5 * rep[nm]["max"] for nm in MEASURES}
        print(f"the derivatives' worst relative error: {check(fr, t_, lim_):.2e}")
    png = OUT / (a.out or f"member_fair_{a.run[:40]}.png")
    picture(fr, t_, cols_, png, f"{a.run[:80]}...: the members' frame and the fairing measures")
    print(png)
