"""A height-field run's columns, drawn as smooth members (moved from `prototypes/first_loop/`:
`topo.height_columns`; `outcome_cad.voxel_cols_as_spline`, `_bilateral`, `fill_diagonals` and
`spline_members_pts` on the final recipe's path; LOP-33).

The run's own columns and heights, no new optimisation: each column's height is its cubes' densities
summed along it; the outline in plan is where a column holds metal, blurred among the columns of its
half, layer and family and read at its middle; each member's free end smoothed edge-preservingly
(the bilateral filter); the free edges rounded.
"""

from __future__ import annotations

import math

import numpy as np

PLAN_SUB = (
    0.5  # mm: the plan grid on which the members' true distance from their outline is measured
)
SUB_Q = 2  # points a column in each plan direction (each cube's points h / 4 off its centre)
TOP_SHARP = 2.0  # the free end's soft-plus sharpness past each node's own level


def height_columns(
    kind: np.ndarray, n: np.ndarray, k_split: int, elem: np.ndarray, free_e: np.ndarray
):
    """The height field's columns: each run of modelled voxels along the pull in each half (from the
    split, or from the wall it stands on, outward), and each free voxel's place in its run's free
    voxels counted from the run's start nearest the split. Returns (each free voxel's column, its
    place, each column's plan cell (i, j), each column's layer: its half and its run's index)."""
    grid = np.asarray(kind).reshape(tuple(n))
    col_key = np.full(int(np.prod(n)), -1, np.int64)
    place = np.full(int(np.prod(n)), -1, np.int64)
    flat = np.arange(int(np.prod(n))).reshape(tuple(n))
    for half, sl, flip in ((0, slice(0, k_split), True), (1, slice(k_split, n[2]), False)):
        a = grid[:, :, sl]
        idx = flat[:, :, sl]
        if flip:  # the motor side: from the split downward
            a, idx = a[:, :, ::-1], idx[:, :, ::-1]
        mod, fre = a >= 0, a == 0
        prev = np.concatenate([np.zeros(a.shape[:2] + (1,), bool), mod[:, :, :-1]], axis=2)
        start = mod & ~prev
        run = np.cumsum(start, axis=2)
        fcum = np.cumsum(fre, axis=2)
        base = np.maximum.accumulate(np.where(start, fcum - fre, -1), axis=2)
        pos = fcum - base - 1
        ii, jj = np.meshgrid(np.arange(n[0]), np.arange(n[1]), indexing="ij")
        key = (
            (half * 10_000 + np.broadcast_to(run, a.shape)) * 100_000 + ii[:, :, None]
        ) * 100_000 + jj[:, :, None]
        sel = fre
        col_key[idx[sel]] = key[sel]
        place[idx[sel]] = pos[sel]
    flat_free = elem[free_e]
    keys, col = np.unique(col_key[flat_free], return_inverse=True)
    ci, cj = (keys // 100_000) % 100_000, keys % 100_000
    layer = keys // (100_000 * 100_000)
    return col, place[flat_free].astype(float), np.column_stack([ci, cj]).astype(float), layer


def run_columns(z, sigma_mm: float, round_mm: float) -> dict:
    """The run's field (`z`) as columns to draw: each column's half, plan cell, base, family (on the
    split or on a wall), height `t` and free end `E` on one scale from the split, and its points'
    outline field `sub_phi` (the outline blurred over `sigma_mm` among its half's, layer's and
    family's columns, read at 0.5). A column holds metal from half a cube."""
    from scipy.ndimage import gaussian_filter

    n = np.asarray(z["n"], int)
    elem, frozen, free_e = z["elem"], z["frozen"].astype(bool), z["free_e"]
    k_split, h = int(z["k_split"]), float(z["h"])
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, pts, layer = height_columns(kind, n, k_split, elem, free_e)
    n_cols = len(pts)
    kz = elem[free_e] % int(n[2])
    base = np.full(n_cols, -1, np.int64)
    base[col[pos == 0]] = kz[pos == 0]
    half = (np.asarray(layer, np.int64) // 10_000).astype(np.int8)
    ii, jj = pts[:, 0].astype(int), pts[:, 1].astype(int)
    grid = kind.reshape(tuple(n))
    off = np.concatenate(
        [np.zeros(tuple(n[:2]) + (1,), np.int64), np.cumsum(grid < 0, axis=2)], axis=2
    )
    k0 = np.where(half == 1, k_split, base + 1)
    k1 = np.where(half == 1, base, k_split)
    on_split = (off[ii, jj, np.maximum(k1, k0)] - off[ii, jj, k0]) == 0
    t = np.bincount(
        col, weights=np.asarray(z["phys"], float), minlength=n_cols
    )  # voxels of metal a column
    metal = t >= 0.5
    # each plan cell's stack of columns in the drawing's order (from the split outward)
    lay_of = np.zeros(n_cols, np.int64)
    for hf_ in (0, 1):
        sel = np.flatnonzero(half == hf_)
        seen: dict = {}
        for k in sel[np.argsort(-base[sel] if hf_ == 0 else base[sel], kind="stable")]:
            key = (ii[k], jj[k])
            lay_of[k] = seen.get(key, 0)
            seen[key] = lay_of[k] + 1
    q = SUB_Q
    sa, sb = (v.ravel() for v in np.meshgrid(np.arange(q), np.arange(q), indexing="ij"))
    sub_col = np.repeat(np.arange(n_cols), q * q)
    sub_ij = np.column_stack(
        [q * ii[sub_col] + np.tile(sa, n_cols), q * jj[sub_col] + np.tile(sb, n_cols)]
    )
    sub_phi = np.zeros(len(sub_col))
    sig = sigma_mm / (h / q)
    shape = (q * int(n[0]), q * int(n[1]))
    for key in {(int(a), int(b), bool(c)) for a, b, c in zip(half, lay_of, on_split, strict=True)}:
        mine = (half == key[0]) & (lay_of == key[1]) & (on_split == key[2])
        pts_m = mine[sub_col]
        present = np.zeros(shape)
        filled = np.zeros(shape)
        present[sub_ij[pts_m, 0], sub_ij[pts_m, 1]] = 1.0
        filled[sub_ij[pts_m, 0], sub_ij[pts_m, 1]] = metal[sub_col[pts_m]].astype(float)
        num, den = gaussian_filter(filled, sig), gaussian_filter(present, sig)
        at = (sub_ij[pts_m, 0], sub_ij[pts_m, 1])
        sub_phi[pts_m] = num[at] / np.maximum(den[at], 1e-9) - 0.5
    o_base = np.where(half == 0, (k_split - 1) - base, base - k_split).astype(float)
    return {
        "ij": pts.astype(np.int32),
        "half": half,
        "base": base.astype(np.int32),
        "on_split": on_split,
        "E": np.where(metal, o_base + t, np.nan).astype(np.float32),
        "sub_ij": sub_ij.astype(np.int32),
        "sub_col": sub_col.astype(np.int32),
        "sub_phi": sub_phi.astype(np.float32),
        "round_mm": float(round_mm),
        "least_island_mm2": float(h * h),
        "holding": int(metal.sum()),
        "columns": int(n_cols),
    }


def bilateral(z: np.ndarray, mask: np.ndarray, sig_s: float, sig_r: float) -> np.ndarray:
    """A plan grid's heights `z` smoothed over `sig_s` nodes among the `mask` nodes, each neighbour
    weighed down by how far its height differs (Gaussian over `sig_r`): the bilateral filter (Tomasi
    & Manduchi 1998)."""
    r = int(np.ceil(2.0 * sig_s))
    nx, ny = z.shape
    zp = np.pad(np.where(mask, z, 0.0), r)
    mp = np.pad(mask.astype(float), r)
    num = np.zeros(z.shape)
    den = np.zeros(z.shape)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            d2 = dx * dx + dy * dy
            if d2 > r * r:
                continue
            zs = zp[r + dx : r + dx + nx, r + dy : r + dy + ny]
            w = mp[r + dx : r + dx + nx, r + dy : r + dy + ny] * math.exp(
                -0.5 * d2 / (sig_s * sig_s)
            )
            w = w * np.exp(-0.5 * ((zs - z) / sig_r) ** 2)
            num += w * zs
            den += w
    return np.where(den > 1e-12, num / np.maximum(den, 1e-12), z)


def fill_diagonals(metal: np.ndarray, most: int = 12) -> np.ndarray:
    """The cells made metal where two metal cells touch only along an edge or at a corner, one cell
    a contact, until none is left (a corner-only contact in the members' outline became a line two
    sheets touch along, which TetGen refuses). A 2D mask is passed as (n, m, 1)."""
    m = np.asarray(metal, bool).copy()
    for _ in range(most):
        changed = 0
        for a0, a1 in ((0, 1), (0, 2), (1, 2)):
            b = np.moveaxis(m, (a0, a1), (0, 1))  # a view: writing it writes m
            p00, p11, p10, p01 = b[:-1, :-1], b[1:, 1:], b[1:, :-1], b[:-1, 1:]
            d1 = p00 & p11 & ~p10 & ~p01
            d2 = p10 & p01 & ~p00 & ~p11
            changed += int(d1.sum()) + int(d2.sum())
            p10 |= d1  # one cell of each contact: the square closed
            p00 |= d2
        # a body diagonal: two cells sharing a corner only, the six others of their cube air
        for s0, s1, s2 in ((0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)):
            sl = [slice(None, -1), slice(1, None)]
            c_a = m[sl[s0], sl[s1], sl[s2]]
            c_b = m[sl[1 - s0], sl[1 - s1], sl[1 - s2]]
            cube = np.zeros(c_a.shape, np.int32)
            for i in (0, 1):
                for j in (0, 1):
                    for k in (0, 1):
                        cube += m[sl[i], sl[j], sl[k]]
            lone = c_a & c_b & (cube == 2)
            changed += int(lone.sum())
            m[sl[1 - s0], sl[s1], sl[s2]] |= (
                lone  # a cell beside the first, sharing a face with each
            )
        if not changed:
            break
    return m


def members_sdf(
    cols: dict,
    half: str,
    f: dict,
    xs,
    ys,
    zs,
    footprint: np.ndarray,
    smooth_mm: float,
    smooth_range: float,
) -> np.ndarray:
    """The half's members as a signed distance (mm, positive outside), layer by layer: in plan the
    true distance from the members' outline (its points read cubic on a `PLAN_SUB` grid); the free
    end each family's `E` read cubic between the columns, past the node's own level by a soft plus,
    smoothed over `smooth_mm` keeping steps over `smooth_range` (the bilateral filter); the two
    joined with the free edge rounded (`round_mm`). The families part on the cup's outline
    (`footprint`) on the first layer, a node falling back to its own column's family where its
    parted family has no column on its layer."""
    from scipy.ndimage import distance_transform_edt, label, map_coordinates

    from zenryx.domains.gearbox.housing.walls import round_inter

    h, lo, n = float(f["h"]), np.asarray(f["lo"], float), [int(v) for v in f["n"]]
    ks = int(f["k_split"])
    lower = half == "motor_side"
    sel = np.flatnonzero(cols["half"] == (0 if lower else 1))
    ij, base, fam = cols["ij"][sel].astype(int), cols["base"][sel], cols["on_split"][sel]
    e_col = cols["E"][sel]
    rnd = float(cols["round_mm"])
    q = SUB_Q
    step = h / q
    sub_of = {int(c): k for k, c in enumerate(sel)}
    sub_keep = np.array([int(c) in sub_of for c in cols["sub_col"]])
    sub_ij, sub_phi = cols["sub_ij"][sub_keep].astype(int), cols["sub_phi"][sub_keep]
    sub_k = np.array([sub_of[int(c)] for c in cols["sub_col"][sub_keep]], np.int64)
    order = np.argsort(-base) if lower else np.argsort(base)
    layer = np.zeros(len(sel), np.int64)
    seen: dict = {}
    for k in order:
        key = (int(ij[k, 0]), int(ij[k, 1]))
        layer[k] = seen.get(key, 0)
        seen[key] = layer[k] + 1

    def carried(a: np.ndarray) -> np.ndarray:
        if np.isnan(a).all():
            return np.zeros_like(a)
        _, (ia, ja) = distance_transform_edt(np.isnan(a), return_indices=True)
        return a[ia, ja]

    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    CI, CJ = np.meshgrid(
        (xs - lo[0]) / h - 0.5, (ys - lo[1]) / h - 0.5, indexing="ij"
    )  # in columns
    cell_i = np.clip(np.floor(CI + 0.5).astype(int), 0, n[0] - 1)
    cell_j = np.clip(np.floor(CJ + 0.5).astype(int), 0, n[1] - 1)
    n_sub = (q * n[0], q * n[1])
    ss = PLAN_SUB
    m_s = (int(np.ceil(n[0] * h / ss)), int(np.ceil(n[1] * h / ss)))
    xs_s, ys_s = lo[0] + ss * (np.arange(m_s[0]) + 0.5), lo[1] + ss * (np.arange(m_s[1]) + 0.5)
    SI, SJ = np.meshgrid(
        (xs_s - lo[0]) / step - 0.5, (ys_s - lo[1]) / step - 0.5, indexing="ij"
    )  # in points
    own_si = np.clip(np.floor(SI + 0.5).astype(int), 0, n_sub[0] - 1)
    own_sj = np.clip(np.floor(SJ + 0.5).astype(int), 0, n_sub[1] - 1)
    NI, NJ = np.meshgrid(
        (xs - lo[0]) / ss - 0.5, (ys - lo[1]) / ss - 0.5, indexing="ij"
    )  # on the plan grid
    zz = np.asarray(zs)[None, None, :]
    dx = float(xs[1] - xs[0]) if len(xs) > 1 else 1.0
    dy = float(ys[1] - ys[0]) if len(ys) > 1 else 1.0
    sig = smooth_mm / dx if len(xs) > 1 else 1.0
    out = np.full((len(xs), len(ys), zz.shape[2]), np.inf, np.float32)
    for lay in range(int(layer.max()) + 1 if len(layer) else 0):
        mine = layer == lay
        grid_base = np.full(n[:2], -1, np.int64)
        grid_fam = np.zeros(n[:2], np.int8)
        grid_v = {
            True: np.full(n[:2], np.nan),
            False: np.full(n[:2], np.nan),
        }  # each family's E, by column
        for k in np.flatnonzero(mine):
            i_, j_ = ij[k]
            grid_base[i_, j_], grid_fam[i_, j_] = base[k], 1 if fam[k] else 2
            grid_v[bool(fam[k])][i_, j_] = e_col[k]
        pts_l = mine[sub_k]
        phi_g = np.full(n_sub, np.nan)
        phi_g[sub_ij[pts_l, 0], sub_ij[pts_l, 1]] = sub_phi[pts_l]
        has_g = np.isfinite(phi_g)
        # the true distance from the outline (mm, positive inside), the outline a cubic curve
        # through the points
        phi_s = map_coordinates(carried(phi_g), [SI, SJ], order=3, mode="nearest")
        inside = (phi_s > 0.0) & has_g[own_si, own_sj]
        inside = fill_diagonals(inside[:, :, None])[
            :, :, 0
        ]  # no corner-only contact in the outline
        lab, n_lab = label(inside)  # specks of outline smaller than a column dropped
        if n_lab:
            size = np.bincount(lab.ravel(), minlength=n_lab + 1) * ss * ss
            inside &= size[lab] >= float(cols["least_island_mm2"])
        d_in = distance_transform_edt(inside) * ss
        d_out = distance_transform_edt(~inside) * ss
        a_s = np.where(inside, d_in - 0.5 * ss, -(d_out - 0.5 * ss))
        a_f = map_coordinates(a_s, [NI, NJ], order=1, mode="nearest")
        own_fam = grid_fam[cell_i, cell_j]
        fam_f = np.where(own_fam > 0, np.where(footprint, 2, 1), 0) if lay == 0 else own_fam
        present = {1: bool((grid_fam == 1).any()), 2: bool((grid_fam == 2).any())}
        fam_f = np.where(((fam_f == 1) & present[1]) | ((fam_f == 2) & present[2]), fam_f, own_fam)
        base_by = {}
        for code_ in (1, 2):
            gb = np.where(grid_fam == code_, grid_base.astype(float), np.nan)
            base_by[code_] = np.rint(carried(gb)).astype(np.int64)[cell_i, cell_j]
        base_f = np.where(fam_f == 1, base_by[1], base_by[2])
        v_f = np.where(
            fam_f == 1,
            map_coordinates(carried(grid_v[True]), [CI, CJ], order=3, mode="nearest"),
            map_coordinates(carried(grid_v[False]), [CI, CJ], order=3, mode="nearest"),
        )
        o_base_f = ((ks - 1) - base_f) if lower else (base_f - ks)
        t_f = (
            np.logaddexp(0.0, TOP_SHARP * (v_f - o_base_f)) / TOP_SHARP
        )  # the height past the node's own level
        out_plan = -np.where(fam_f > 0, a_f, -np.inf)[:, :, None]
        face2 = lo[2] + h * (base_f + 1) if lower else lo[2] + h * base_f
        z_end = face2 - h * t_f if lower else face2 + h * t_f  # each node's free end (mm)
        # each member's free end smoothed in plan within the member and its family, steps kept
        z_s = z_end.copy()
        for code_ in (1, 2):
            m_ = ((fam_f == code_) & (a_f > -2.0 * smooth_mm)).astype(float)
            if m_.any():
                z_s = np.where(m_ > 0, bilateral(z_end, m_ > 0, sig, smooth_range), z_s)
        z_end = z_s
        face = face2[:, :, None]
        zdist = (z_end[:, :, None] - zz) if lower else (zz - z_end[:, :, None])
        # the distance to a sloped top: the height over the slope's secant, so the contour's ramp
        # spans a cell
        gx_, gy_ = np.gradient(z_end, dx, dy)
        zdist = zdist / np.sqrt(1.0 + gx_ * gx_ + gy_ * gy_)[:, :, None]
        f_l = round_inter(out_plan, zdist, rnd)
        if lay:  # a run past another: from its own first voxel
            f_l = np.maximum(f_l, (zz - face) if lower else (face - zz))
        out = np.minimum(out, f_l.astype(np.float32))
    return out
