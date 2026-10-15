"""Ribs drawn from the rib-direction field (LOP-34; a prototype): the de-homogenisation.

On a fine plan grid (`FINE` mm) the directions, the amount and the heights are read from the run;
a stripe pattern is found whose stripes follow the directions `SPACING` mm apart: the phase of a
complex field psi, each grid edge asking psi to turn by the spacing's rate across the ribs (and to be
mirrored where the line field's representative flips), the smallest eigenvector of that energy
(as Knöppel, Crane, Pinkall & Schröder's stripe patterns, 2015), so ribs end and branch where the
directions converge. A point is a rib's where cos(phase) >= cos(pi rho): each rib rho x SPACING
thick, centred on the phase's zero. The ribs stand h above the wall; a rib under `T_LEAST` thick or
`H_LEAST` tall is not drawn. The free columns are drawn as the run left them (each column its
height). Both become a height map, then a watertight mesh (marching cubes on `FINE` cells).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.sparse.linalg import eigsh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402

FINE = 0.5  # mm
T_LEAST = 2.5  # mm: a thinner rib is not drawn
H_LEAST = 3.0  # mm: a lower rib is not drawn


def fine_grid(step: float = FINE) -> tuple[np.ndarray, np.ndarray]:
    x = np.arange(step / 2, toy.LX, step)
    y = np.arange(step / 2, toy.LY, step)
    return np.meshgrid(x, y, indexing="ij")


def regions(px: np.ndarray, py: np.ndarray) -> dict:
    """The fixed parts on the fine grid, exactly: the bore, the boss, the bolts' and the lug's."""
    d = np.hypot(px - toy.BORE[0], py - toy.BORE[1])
    bolt = np.zeros(px.shape, bool)
    for b in toy.BOLTS:
        bolt |= np.hypot(px - b[0], py - b[1]) < toy.R_BOLT
    lug = np.hypot(px - toy.LUG[0], py - toy.LUG[1]) < toy.R_LUG
    hole = d < toy.R_BORE
    boss = (d >= toy.R_BORE) & (d < toy.R_BOSS)
    return {"hole": hole, "boss": boss, "bolt": bolt, "lug": lug, "solid": boss | bolt | lug}


def on_columns(values: np.ndarray, cols_ij: np.ndarray, px, py, a: float, sigma_mm: float = 4.0):
    """A per-column quantity read at the fine points: put on the column grid, the empty columns
    filled by a normalised Gaussian, then interpolated bilinearly."""
    nx, ny = int(round(toy.LX / a)), int(round(toy.LY / a))
    vals = np.atleast_2d(values.T).T if values.ndim == 1 else values
    out = []
    mask = np.zeros((nx, ny))
    mask[cols_ij[:, 0], cols_ij[:, 1]] = 1.0
    wm = gaussian_filter(mask, sigma_mm / a, mode="nearest")
    for k in range(vals.shape[1]):
        g = np.zeros((nx, ny))
        g[cols_ij[:, 0], cols_ij[:, 1]] = vals[:, k]
        filled = np.where(mask > 0, g, gaussian_filter(g, sigma_mm / a, mode="nearest") / np.maximum(wm, 1e-9))
        coords = np.stack([px / a - 0.5, py / a - 0.5])
        out.append(map_coordinates(filled, coords, order=1, mode="nearest"))
    return out[0] if values.ndim == 1 else np.stack(out, axis=-1)


def stripes(theta: np.ndarray, active: np.ndarray, spacing: float, step: float) -> tuple:
    """The stripe pattern's phase and amplitude on the grid (`theta` the ribs' direction at each
    point; `active` the points to solve on)."""
    shape = theta.shape
    idx = np.full(shape, -1)
    idx[active] = np.arange(active.sum())
    n_pts = int(active.sum())
    nrm = np.stack([-np.sin(theta), np.cos(theta)], axis=-1)
    omega = 2 * np.pi / spacing
    rows, cols, vals = [], [], []

    def add(r, c, v):
        rows.append(r)
        cols.append(c)
        vals.append(v)

    for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
        sl_p = (slice(0, shape[0] - di), slice(max(0, -dj), shape[1] - max(0, dj)))
        sl_q = (slice(di, shape[0]), slice(max(0, dj), shape[1] - max(0, -dj)))
        both = active[sl_p] & active[sl_q]
        p, q = idx[sl_p][both], idx[sl_q][both]
        npv, nqv = nrm[sl_p][both], nrm[sl_q][both]
        s = np.sign((npv * nqv).sum(axis=1))
        s[s == 0] = 1.0
        navg = npv + s[:, None] * nqv
        navg /= np.maximum(np.linalg.norm(navg, axis=1, keepdims=True), 1e-12)
        w = omega * (navg[:, 0] * di * step + navg[:, 1] * dj * step)
        wt = 1.0 / np.hypot(di, dj)  # the diagonals count less
        c, sn = np.cos(w), np.sin(w)
        # A: psi_q ~ A psi_p, as a 2 x 2 real map (a rotation, or a rotation then a mirror)
        a00, a01 = c, -sn
        a10, a11 = np.where(s > 0, sn, -sn), np.where(s > 0, c, -c)
        amat = np.stack([np.stack([a00, a01], -1), np.stack([a10, a11], -1)], -2)
        for i in range(2):
            add(2 * p + i, 2 * p + i, np.full(len(p), wt))
            add(2 * q + i, 2 * q + i, np.full(len(p), wt))
            for j in range(2):
                add(2 * q + i, 2 * p + j, -wt * amat[:, i, j])
                add(2 * p + j, 2 * q + i, -wt * amat[:, i, j])
    lmat = sp.coo_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(2 * n_pts, 2 * n_pts),
    ).tocsc()
    _, vec = eigsh(lmat, k=1, sigma=-1e-4, which="LM")
    psi = vec[0::2, 0] + 1j * vec[1::2, 0]
    phase = np.zeros(shape)
    amp = np.zeros(shape)
    phase[active] = np.angle(psi)
    amp[active] = np.abs(psi) / np.abs(psi).mean()
    return phase, amp


def draw_field(run: dict, a: float = toy.A, step: float = FINE, gate: bool = False) -> dict:
    """The field's ribs as a height map (mm above the wall's underside), with its parts."""
    px, py = fine_grid(step)
    reg = regions(px, py)
    plate = ~reg["hole"]
    cols_ij = run["cols_ij"]
    # the directions as doubled angles, read at the fine points
    v = np.stack([np.cos(2 * run["theta"]), np.sin(2 * run["theta"])], axis=1)
    vf = on_columns(v, cols_ij, px, py, a)
    theta = 0.5 * np.arctan2(vf[..., 1], vf[..., 0])
    basis = toy.bspline_2d(px.ravel(), py.ravel(), toy.KNOT)
    n = basis.shape[1]
    x = run["x"]
    spacing = float(run.get("spacing", toy.SPACING))
    if bool(run.get("by_place", False)):
        import rules

        tcap = rules.thickness_cap(np.stack([px.ravel(), py.ravel()], axis=1))[0]
    else:
        tcap = np.full(px.size, float(run.get("t_most", toy.T_MOST)))
    fastcae = bool(run.get("fastcae", False))
    tall = float(run.get("tall", toy.TALL))
    if fastcae:
        import rules

        assert abs(float(run["h_bolt"]) - toy.H_BOLT) < 1e-9, "draw with --fastcae (the bolts' height)"
        hcap = rules.height_cap(np.stack([px.ravel(), py.ravel()], axis=1))
        t_least, h_least = rules.T_LEAST, rules.H_LEAST
    else:
        hcap, t_least, h_least = toy.BAND, T_LEAST, H_LEAST
    active = plate & ~reg["solid"]
    out = {"theta": theta, "px": px, "py": py, "regions": reg, "step": step}
    ribs = np.zeros(px.shape, bool)
    ztop = np.zeros(px.shape)
    for k in range(int(run.get("families", 1))):
        xr, xh = x[2 * k * n : (2 * k + 1) * n], x[(2 * k + 1) * n : (2 * k + 2) * n]
        rho = (tcap / spacing) * (basis @ xr)
        cap, _ = toy.smin(hcap, tall * spacing * rho)
        h = ((basis @ xh) * cap).reshape(px.shape)
        rho = rho.reshape(px.shape)
        phase, amp = stripes(theta + k * np.pi / 2, plate, spacing, step)
        rib = (np.cos(phase) >= np.cos(np.pi * np.clip(rho, 0, 1))) & active
        rib &= (rho * spacing >= t_least) & (h >= h_least)
        out[f"drawn{k}"] = (rho * spacing >= t_least) & (h >= h_least) & active
        ribs |= rib
        ztop = np.where(rib, np.maximum(ztop, h), ztop)
        out.update({f"rib{k}": rib, f"rho{k}": rho, f"h{k}": h, f"phase{k}": phase, f"amp{k}": amp})
    out["census_before"] = census(ribs, reg, step)
    if gate:
        ribs, out["gate"] = gated(ribs, reg, step)
        out["census"] = census(ribs, reg, step)
    else:
        out["census"] = out["census_before"]
    z = np.where(plate, toy.WALL, 0.0)
    z = np.where(ribs, toy.WALL + ztop, z)
    z = solids_top(z, reg)
    out["z"] = z
    out["ribs"] = ribs
    out["spacing"] = spacing
    return out


def solids_top(z: np.ndarray, reg: dict) -> np.ndarray:
    """The fixed parts' tops on a height map: the boss and the lug the band's, a bolt's boss its own."""
    z = np.where(reg["boss"] | reg["lug"], toy.WALL + toy.BAND, z)
    return np.where(reg["bolt"], toy.WALL + toy.H_BOLT, z)


L_LEAST = 20.0  # mm: a shorter rib is not drawn (the drawing's gate)
TOUCH = 1.5  # mm: a rib this near a hard point or the plate's edge is held by it
FREE_END = 3.0  # mm: a rib's end farther than this from a hard point, the edge or another rib is free


def anchors(reg: dict, step: float) -> np.ndarray:
    """What a rib may end on: the hard points (bosses, bolts, lug) grown by `TOUCH`, and the plate's
    edge band."""
    from scipy.ndimage import binary_dilation

    k = max(1, int(round(TOUCH / step)))
    held = binary_dilation(reg["solid"], iterations=k)
    held[:k, :] = held[-k:, :] = True
    held[:, :k] = held[:, -k:] = True
    return held


def gated(ribs: np.ndarray, reg: dict, step: float) -> tuple[np.ndarray, dict]:
    """The drawing's gate: each connected piece of rib kept only if it touches a hard point or the
    edge, and is at least `L_LEAST` long (its extent along its own main axis)."""
    from scipy.ndimage import label

    held = anchors(reg, step)
    lab, count = label(ribs, structure=np.ones((3, 3)))
    keep = np.zeros(count + 1, bool)
    dropped = {"loose": 0, "short": 0, "area_mm2": 0.0}
    for i in range(1, count + 1):
        ij = np.argwhere(lab == i).astype(float) * step
        touches = bool(held[lab == i].any())
        if len(ij) > 2:
            c = ij - ij.mean(axis=0)
            axis = np.linalg.svd(c, full_matrices=False)[2][0]
            length = float(np.ptp(c @ axis)) + step
        else:
            length = step
        if not touches:
            dropped["loose"] += 1
        elif length < L_LEAST:
            dropped["short"] += 1
        else:
            keep[i] = True
            continue
        dropped["area_mm2"] += len(ij) * step * step
    return keep[lab], dropped


def census(ribs: np.ndarray, reg: dict, step: float) -> dict:
    """The drawn ribs' free ends (their skeleton's end points farther than `FREE_END` from a hard
    point or the edge) and their length."""
    from scipy.ndimage import convolve, distance_transform_edt
    from skimage.morphology import skeletonize

    sk = skeletonize(ribs)
    nb = convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    ends = sk & (nb == 1)
    far = distance_transform_edt(~anchors(reg, step)) * step > FREE_END
    length_m = float(sk.sum()) * step / 1000.0
    free = int((ends & far).sum())
    return {"free_ends": free, "rib_length_m": round(length_m, 3),
            "free_ends_per_m": round(free / max(length_m, 1e-9), 1)}


def draw_columns(run: dict, a: float = toy.A, step: float = FINE) -> dict:
    """The free columns as the run left them: each column its height."""
    px, py = fine_grid(step)
    reg = regions(px, py)
    plate = ~reg["hole"]
    nx, ny = int(round(toy.LX / a)), int(round(toy.LY / a))
    hg = np.zeros((nx, ny))
    hg[run["cols_ij"][:, 0], run["cols_ij"][:, 1]] = run["h"]
    i = np.clip((px / a).astype(int), 0, nx - 1)
    j = np.clip((py / a).astype(int), 0, ny - 1)
    h = hg[i, j]
    z = np.where(plate, toy.WALL + h, 0.0)
    z = solids_top(z, reg)
    return {"z": z, "h": h, "px": px, "py": py, "regions": reg, "step": step}


def mesh(z: np.ndarray, step: float = FINE):
    """The height map's solid as a watertight mesh (marching cubes on `step` cells)."""
    from zenryx.domains.gearbox.housing import mesh as mr

    top = toy.WALL + toy.BAND
    nz = int(round(top / step))
    zc = (np.arange(nz) + 0.5) * step
    vol = (zc[None, None, :] < z[:, :, None]).astype(np.float32)
    return mr.contour(vol, np.zeros(3), step)


def mass_kg(z: np.ndarray, step: float = FINE) -> float:
    """The height map's metal over the wall and the fixed parts' share is left in: the whole."""
    _, _, density = toy.material()
    return float(z.sum() * step * step * density)


DRAFT_DEG = 1.0  # fastcae's draft_deg: each rib face leans in toward its top
R_TOP = 2.0  # mm: a rib's top edges rounded (fastcae's fillet_edge_mm, scaled)
R_ROOT = 3.0  # mm: a rib's roots filleted on the wall and the hard points (fillet_root_mm, scaled)


def _smin(a, b, k):
    """A polynomial smooth minimum (Quilez): min(a, b) rounded over k."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _smax(a, b, k):
    return -_smin(-a, -b, k)


def implicit(d: dict, step: float):
    """The field's drawing as a smooth solid: f > 0 inside, on a grid of `step` mm; the wall, the
    fixed parts, and each family's ribs (half as thick as drawn at the wall less the draft's lean
    above it, to the rib's own height) with their top edges rounded (`R_TOP`) and their roots
    filleted (`R_ROOT`). The ribs' side faces come from the stripes' phase: a point lies
    |phase| spacing / 2 pi from its rib's middle. Returns (f, the grid's lower corner)."""
    px, py, reg = d["px"], d["py"], d["regions"]
    s = d["spacing"]
    top = toy.WALL + toy.BAND
    nz = int(np.ceil(top / step)) + 1
    z = ((np.arange(nz) + 0.5) * step)[None, None, :]
    big = 1e3
    r_bore = np.hypot(px - toy.BORE[0], py - toy.BORE[1])
    plate = np.minimum.reduce([px, toy.LX - px, py, toy.LY - py, r_bore - toy.R_BORE])[..., None]
    floor = np.minimum(z, 1e9)
    wall = np.minimum(np.minimum(plate, toy.WALL - z), floor)
    hard = np.minimum.reduce(
        [toy.R_BOSS - r_bore, r_bore - toy.R_BORE, np.full_like(px, big)]
    )[..., None]
    hard = np.minimum(np.minimum(hard, top - z), floor)
    lug = (toy.R_LUG - np.hypot(px - toy.LUG[0], py - toy.LUG[1]))[..., None]
    hard = np.maximum(hard, np.minimum(np.minimum(lug, top - z), floor))
    for b in toy.BOLTS:
        rb = (toy.R_BOLT - np.hypot(px - b[0], py - b[1]))[..., None]
        hard = np.maximum(hard, np.minimum(np.minimum(rb, toy.WALL + toy.H_BOLT - z), floor))
    from scipy.ndimage import binary_dilation

    kept = binary_dilation(d["ribs"], iterations=max(1, int(round(R_ROOT / step))))
    lean = np.tan(np.radians(DRAFT_DEG))
    ribs = np.full(px.shape + (nz,), -big)
    k = 0
    while f"phase{k}" in d:
        valid = (d[f"drawn{k}"] & kept)[..., None]
        half = (d[f"rho{k}"] * s / 2.0)[..., None] - np.maximum(z - toy.WALL, 0.0) * lean
        side = half - (np.abs(d[f"phase{k}"]) * s / (2 * np.pi))[..., None]
        cap = (toy.WALL + d[f"h{k}"])[..., None] - z
        rib = _smin(side, cap, R_TOP)
        rib = np.minimum(np.minimum(rib, plate), floor)
        ribs = np.maximum(ribs, np.where(valid, rib, -big))
        k += 1
    body = _smax(wall, ribs, R_ROOT)
    body = _smax(body, hard, R_ROOT)
    return body, np.zeros(3)


def mesh_implicit(f: np.ndarray, step: float):
    """The smooth solid's surface (marching cubes at 0, the grid padded with air), its largest
    watertight piece."""
    import trimesh
    from skimage.measure import marching_cubes

    field = np.pad(f.astype(float), 2, constant_values=-1.0)
    verts, faces, _, _ = marching_cubes(field, level=0.0, spacing=(step, step, step))
    verts += -2 * step + 0.5 * step
    tm = trimesh.Trimesh(verts, faces[:, ::-1], process=True)
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    if tm.volume < 0:
        tm.invert()
    return tm

