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


def draw_field(run: dict, a: float = toy.A, step: float = FINE) -> dict:
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
    active = plate & ~reg["solid"]
    z = np.where(plate, toy.WALL, 0.0)
    out = {"theta": theta, "px": px, "py": py, "regions": reg, "step": step}
    for k in range(int(run.get("families", 1))):
        xr, xh = x[2 * k * n : (2 * k + 1) * n], x[(2 * k + 1) * n : (2 * k + 2) * n]
        rho = (toy.T_MOST / toy.SPACING) * (basis @ xr)
        cap, _ = toy.smin(toy.BAND, toy.TALL * toy.SPACING * rho)
        h = ((basis @ xh) * cap).reshape(px.shape)
        rho = rho.reshape(px.shape)
        phase, amp = stripes(theta + k * np.pi / 2, plate, toy.SPACING, step)
        rib = (np.cos(phase) >= np.cos(np.pi * np.clip(rho, 0, 1))) & active
        rib &= (rho * toy.SPACING >= T_LEAST) & (h >= H_LEAST)
        z = np.where(rib, np.maximum(z, toy.WALL + h), z)
        out.update({f"rib{k}": rib, f"rho{k}": rho, f"h{k}": h, f"phase{k}": phase, f"amp{k}": amp})
    z = np.where(reg["solid"], toy.WALL + toy.BAND, z)
    out["z"] = z
    return out


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
    z = np.where(reg["solid"], toy.WALL + toy.BAND, z)
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
