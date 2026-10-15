"""The least walls and the protected interfaces as signed distances in the drawing's field, and the
run's metal beyond its least walls (moved from `prototypes/first_loop/exact_walls.py`:
`_seal_seat_mm`, `_height_min`, `extra_placed`, `_capped`, `_density`, `ramp`, `round_inter`,
`round_union`, `least_sdf`, `interface_sdf`; LOP-33). The final recipe protects the interfaces
without the bearings' towers (`--no-towers`): the towers' part is not here.

Every signed distance is in mm, negative inside the metal.
"""

from __future__ import annotations

import numpy as np

from zenryx.domains.gearbox.housing import cup as cupmod
from zenryx.domains.gearbox.housing.columns import height_columns

EDGE = 0.5  # mm, the density's step across a face (0.5 exactly on it)


def seal_seat_mm(spec) -> float:
    """Each sealed exit's seat behind its bearing (the contract's)."""
    from zenryx.domains.gearbox.forces import value_in

    return value_in(spec.requirement.shaft_layout.behind_bearing_sealed, "mm")


def extra_placed(z) -> np.ndarray:
    """The run's placed metal (its free voxels at 0.5 or more) beyond each column's least height, on
    its own grid (`z`, the run's field): the least walls are drawn exact instead, and the drawing
    fills each column from the split to its last metal, so a member stands on the wall below it."""
    n = z["n"].astype(int)
    elem, free_e, frozen = z["elem"], z["free_e"], z["frozen"].astype(bool)
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, _, _ = height_columns(kind, n, int(z["k_split"]), elem, free_e)
    placed = np.asarray(z["phys"]) >= 0.5
    if "height_min" not in z:
        raise ValueError(
            "the run saves no least heights (`height_min`): not a run of the final recipe"
        )
    need = np.asarray(z["height_min"], float)[elem[free_e]]
    n_cols = int(col.max()) + 1
    tmin = np.zeros(n_cols)
    np.maximum.at(tmin, col, need)
    least = np.ceil(tmin[col] - 1e-6)  # each free voxel's column's least wall, in whole voxels
    keep = placed & (pos >= least)
    out = np.zeros(int(np.prod(n)), bool)
    out[elem[free_e]] = keep
    return out.reshape(n)


def capped(X, Y, Z, axis, r: float, z_lo: float, z_hi: float) -> np.ndarray:
    """The signed distance to a cylinder along z of radius r from z_lo to z_hi."""
    dr = np.hypot(X - axis[0], Y - axis[1]) - r
    dz = np.maximum(z_lo - Z, Z - z_hi)
    return np.hypot(np.maximum(dr, 0.0), np.maximum(dz, 0.0)) + np.minimum(np.maximum(dr, dz), 0.0)


def density(sdf: np.ndarray) -> np.ndarray:
    return (0.5 - 0.5 * np.tanh(sdf / EDGE)).astype(np.float32)


def ramp(sdf: np.ndarray, width: float) -> np.ndarray:
    """A face's density for the contour: 0.5 on the face, linear over `width` mm either side, so
    marching cubes on cells `width` mm apart puts a plane face where it is."""
    return np.clip(0.5 - sdf / (2.0 * width), 0.0, 1.0).astype(np.float32)


def round_inter(a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    """Two solids' common part, the edge where their faces meet rounded to radius r: a member's side
    and its free end give its rounded free edge."""
    return np.minimum(-r, np.maximum(a, b)) + np.hypot(
        np.maximum(r + a, 0.0), np.maximum(r + b, 0.0)
    )


def round_union(a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    """Two solids joined with a fillet of radius r where their faces meet: the members and the exact
    parts give the members' filleted roots."""
    return np.maximum(r, np.minimum(a, b)) - np.hypot(
        np.maximum(r - a, 0.0), np.maximum(r - b, 0.0)
    )


def least_sdf(
    X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str, seat: float
) -> np.ndarray:
    """The half's least walls at their true faces: the cup's outside at the least wall (with the
    plate over the other half's opening), the sealing land and the seals' seats (`seat` mm deep)."""
    wall = float(layout["settings"]["wall"])
    lower = half == "motor_side"
    other = "cover" if lower else "motor_side"
    cup_d = np.full(X.shape, np.inf, np.float32)
    plan_d = np.full(X.shape[:2], np.inf, np.float32)
    for which in (half, other):
        for p in cupmod.pieces(all_rooms, z_split, which):
            far = p["far"] if which == half else z_split
            z_lo, z_hi = sorted((far, z_split))
            cup_d = np.minimum(
                cup_d, capped(X, Y, Z, p["axis"], p["r"], z_lo, z_hi).astype(np.float32)
            )
            ring = np.hypot(X[:, :, 0] - p["axis"][0], Y[:, :, 0] - p["axis"][1]) - p["r"]
            plan_d = np.minimum(plan_d, ring.astype(np.float32))
    sdf = cup_d - wall
    fl = layout["flange"]
    # the band round the inside, outside it
    band = np.maximum(plan_d - float(fl["land_width"]), -plan_d)
    sdf = np.minimum(
        sdf, np.maximum(band[:, :, None], np.abs(Z - z_split) - float(fl["thickness"]))
    )
    for e in layout.get("exits") or []:
        if e["kind"] != "seal" or (e["z"][1] <= z_split) != lower:
            continue
        inner = e["z"][1] if lower else e["z"][0]
        z_lo, z_hi = (inner, inner + seat) if lower else (inner - seat, inner)
        sdf = np.minimum(sdf, capped(X, Y, Z, e["centre"], e["radius"] + wall, z_lo, z_hi))
    return sdf.astype(np.float32)


def interface_sdf(X, Y, Z, layout: dict, z_split: float, half: str) -> np.ndarray:
    """The half's protected interfaces at their true faces: the sealing land, the bolts' bosses and,
    in the motor side, the mounts' lugs (no bearings' towers: the final recipe's `--no-towers`)."""
    s = layout["settings"]
    lower = half == "motor_side"
    fl = layout["flange"]
    t_f = float(fl["thickness"])
    z_lo, z_hi = (z_split - t_f, z_split) if lower else (z_split, z_split + t_f)
    X0, Y0 = X[:, :, 0], Y[:, :, 0]
    d_out = np.min(
        [np.hypot(X0 - c["centre"][0], Y0 - c["centre"][1]) - c["radius"] for c in fl["outer"]],
        axis=0,
    )
    d_in = np.min(
        [np.hypot(X0 - c["centre"][0], Y0 - c["centre"][1]) - c["radius"] for c in fl["inner"]],
        axis=0,
    )
    sdf = np.maximum(np.maximum(d_out, -d_in)[:, :, None], np.maximum(z_lo - Z, Z - z_hi))
    for c in layout["bolts"]:
        sdf = np.minimum(sdf, capped(X, Y, Z, c, float(s["bolt_boss"]) / 2, z_lo, z_hi))
    if lower:
        for m in layout["mounts"]:
            sdf = np.minimum(
                sdf,
                capped(X, Y, Z, m["centre"], float(s["mount_diameter"]) / 2, m["z"][0], m["z"][1]),
            )
    return sdf.astype(np.float32)
