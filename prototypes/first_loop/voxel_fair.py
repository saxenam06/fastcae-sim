"""PROTOTYPE (LOP-30) - a voxel run's members faired in plan, no new optimisation (the engineer, 15 October 13:49: "straighten
the features, align them more properly, remove this vertical edgy stretchy shapes"). Each group of columns (a half, a
level, a family) as a signed distance in plan on a fine grid (mm, positive inside the metal):

1. the metal columns' union, its distance on the fine grid (each column's square exact, no point staircase);
2. smoothed a little the same way in every direction (`iso_mm`): the columns' 4 mm steps go;
3. smoothed along each member's own direction (`along_mm`), read from the metal's structure tensor (the direction in which
   the metal does not change), as much as the metal there is line-like (its coherence): a member's wobbles along its length
   straighten without its width thinning (Weickert's coherence-enhancing smoothing, on the distance);
4. held within `band_mm` of the columns' own outline either way: the outline straightens within that band and moves no
   further, so no member parts from the wall or boss it stands against, thins away, or grows where there was no metal.

The drawing (`outcome_cad.spline_members_pts`) then reads the plan distance directly: no binary outline and no distance of a
binary outline, whose 0.5 mm steps, pushed along the pull, were vertical streaks down every tall face (0.3 mm rms,
`baseline2_lw8_smooth`)."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates


def signed_distance(mask: np.ndarray, cell: float) -> np.ndarray:
    """A plan mask's signed distance (mm, positive inside), each cell's centre to the nearest cell of the other kind, less
    half a cell, so the zero lies on the cells' boundary."""
    if not mask.any():
        return np.full(mask.shape, -1e3)
    d_in = distance_transform_edt(mask) * cell
    d_out = distance_transform_edt(~mask) * cell
    return np.where(mask, d_in - 0.5 * cell, -(d_out - 0.5 * cell))


def orientation(mask: np.ndarray, cell: float, grad_mm: float = 1.0, rho_mm: float = 3.0):
    """Each cell's member direction (unit vector along which the metal does not change) and its coherence (0 isotropic, 1
    line-like), from the structure tensor of the mask smoothed over `grad_mm`, averaged over `rho_mm`."""
    u = gaussian_filter(mask.astype(float), grad_mm / cell)
    gy, gx = np.gradient(u)  # axis 0 = x index, axis 1 = y index: gx along axis 1
    gi, gj = gy, gx  # the gradient along the grid's first (i) and second (j) axes
    jii = gaussian_filter(gi * gi, rho_mm / cell)
    jij = gaussian_filter(gi * gj, rho_mm / cell)
    jjj = gaussian_filter(gj * gj, rho_mm / cell)
    tr = jii + jjj
    disc = np.sqrt(np.maximum((jii - jjj) ** 2 + 4.0 * jij * jij, 0.0))
    coherence = np.where(tr > 1e-12, (disc / np.maximum(tr, 1e-12)) ** 2, 0.0)
    # the dominant eigenvector (across the member): angle 0.5 atan2(2 jij, jii - jjj); the member runs at right angles to it
    theta = 0.5 * np.arctan2(2.0 * jij, jii - jjj)
    ti, tj = -np.sin(theta), np.cos(theta)
    return ti, tj, coherence


def orientation_of_field(f: np.ndarray, cell: float, grad_mm: float = 1.5, rho_mm: float = 4.0):
    """As `orientation`, for a height field: each cell's direction along its contour (no change of height), and how
    line-like the field is there (a cliff's edge: 1; a flat top: 0)."""
    u = gaussian_filter(f, grad_mm / cell)
    gi, gj = np.gradient(u)
    jii = gaussian_filter(gi * gi, rho_mm / cell)
    jij = gaussian_filter(gi * gj, rho_mm / cell)
    jjj = gaussian_filter(gj * gj, rho_mm / cell)
    tr = jii + jjj
    disc = np.sqrt(np.maximum((jii - jjj) ** 2 + 4.0 * jij * jij, 0.0))
    coherence = np.where(tr > 1e-12, (disc / np.maximum(tr, 1e-12)) ** 2, 0.0)
    theta = 0.5 * np.arctan2(2.0 * jij, jii - jjj)
    return -np.sin(theta), np.cos(theta), coherence


def fair_tops(z: np.ndarray, mask: np.ndarray, cell: float, along_mm: float) -> np.ndarray:
    """(15 October 14:20) The members' free ends smoothed along their own contours over `along_mm` (where they are
    line-like: a cliff between a tall column and a short one), so a cliff keeps its height while the line it runs along
    straightens: kept sharp but placed by the 4 mm columns, a cliff's face was corrugated down its height. Only within
    `mask`; elsewhere unchanged."""
    ti, tj, coh = orientation_of_field(z, cell)
    z_al = along_smooth(z, ti, tj, cell, along_mm)
    return np.where(mask, coh * z_al + (1.0 - coh) * z, z)


def along_smooth(f: np.ndarray, ti: np.ndarray, tj: np.ndarray, cell: float, along_mm: float) -> np.ndarray:
    """`f` averaged along each cell's own direction (a line integral, Gaussian weights over `along_mm`), read linearly."""
    step = max(cell, 0.5)
    k_most = int(np.ceil(2.0 * along_mm / step))
    ii, jj = np.meshgrid(np.arange(f.shape[0], dtype=float), np.arange(f.shape[1], dtype=float), indexing="ij")
    num = np.zeros(f.shape)
    den = 0.0
    for k in range(-k_most, k_most + 1):
        w = float(np.exp(-0.5 * (k * step / along_mm) ** 2))
        off = k * step / cell
        num += w * map_coordinates(f, [ii + off * ti, jj + off * tj], order=1, mode="nearest")
        den += w
    return num / den


def fair_group(metal: np.ndarray, cell: float, iso_mm: float, along_mm: float, band_mm: float) -> np.ndarray:
    """One group's faired plan distance (mm, positive inside) on the fine grid of `cell` mm, `metal` its metal columns'
    cells: smoothed every way and along each member, then held within `band_mm` of the columns' own outline either way,
    so the 4 mm steps and the wobbles straighten while no member parts from a wall, thins away or grows where there was no
    metal. (Tried, 15 October 13:55: held unchanged near the fixed metal instead; every end wall is fixed metal under its
    members, so nothing moved.)"""
    d = signed_distance(metal, cell)
    d_iso = gaussian_filter(d, iso_mm / cell) if iso_mm > 0 else d
    if along_mm > 0:
        # the direction read over 6 mm: over 3 mm a staircase's own steps set it, the sampling ran out of a narrow member
        # sideways and cut slits through it (`fair_preview_8.png`)
        ti, tj, coh = orientation(metal, cell, rho_mm=6.0)
        d_al = along_smooth(d_iso, ti, tj, cell, along_mm)
        d_fair = coh * d_al + (1.0 - coh) * d_iso
    else:
        d_fair = d_iso
    out = np.clip(d_fair, d - band_mm, d + band_mm)
    # no gap opened inside the metal: a place more than 2 mm inside the columns stays metal (a member 4 mm wide, one column,
    # may still straighten: it weighs nothing in the model)
    return np.where(d > 2.0, np.maximum(out, 0.25), out)
