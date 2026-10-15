"""The optimiser's voxel model of the housing, as the final recipe sets it up (moved from
`prototypes/first_loop/topo_free.py`: `build_free`, `least_heights`, `hanging`, and from `topo.py`:
`inside`, `height_columns`; only the final recipe's set-up; LOP-27 to LOP-29, LOP-33).

The set-up (the engineer, 12 October 20:22 to 14 October 00:26): the empty start with the shell
fixed and the interfaces protected, no bearing towers. Each voxel is not modelled (-1), free (0) or
fixed (1):
- **fixed:** the 4 mm shell (every cube the least walls make metal, each column's least height
  rounded to whole cubes, `least_heights`), the split flange's sealing land and the bolts' bosses on
  it (A26, whole cubes: a cube whose centre lies in the flange is the flange's), and the mounts
  (A20); the optimiser only adds on top of them;
- **kept clear:** each shaft's way out (a seal's bore 1 mm into the housing, a half-shaft's joint),
  each mount's bracket room, each bolt's hole and its head's socket, every one the drawing's 2 mm
  wider (one description for the optimiser and the drawing);
- **free:** the rest of the packaging space outside the inside, within the band of the shell (the
  height envelope), and round each mount everything within reach of the shell at the mount's height
  and the band's past it, to the split (each column one run from the split).
The voxels are laid so that the split is a voxel face. Each half's free voxels make the height
field's columns (`height_columns`): one variable a column, castable by construction.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, generate_binary_structure

from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import say

KEEP_MARGIN = 2.0  # mm: the drawing's margin round a kept-clear space
PROJECTION = {
    "eta": 0.5,
    "every": 40,
    "beta_most": 16.0,
    "move_late": 0.05,
    "damping": 0.3,
    "mma_move": 0.2,
}


def inside(polygon, x, y):
    """Point-in-polygon (even-odd), vectorised over x, y."""
    poly = np.asarray(polygon)
    xs, ys = poly[:, 0], poly[:, 1]
    xs2, ys2 = np.roll(xs, -1), np.roll(ys, -1)
    result = np.zeros(x.shape, dtype=bool)
    for x1, y1, x2, y2 in zip(xs, ys, xs2, ys2, strict=True):
        cond = (y1 > y) != (y2 > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xin = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        result ^= cond & (x < xin)
    return result


def height_columns(
    kind: np.ndarray, n: np.ndarray, k_split: int, elem: np.ndarray, free_e: np.ndarray
):
    """The height field's columns: each run of modelled voxels along the pull in each half (from the
    split, or from the wall it stands on, outward), and each free voxel's place in its run's free
    voxels counted from the run's start nearest the split. Returns (each free voxel's column, its
    place, each column's plan cell (i, j), each column's layer: its half and its run's index, so the
    plan filter mixes only columns of one layer)."""
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


def least_heights(
    kind: np.ndarray,
    rooms: np.ndarray,
    n: np.ndarray,
    k_split: int,
    h: float,
    lo: np.ndarray,
    info: dict,
    spec,
) -> tuple[np.ndarray, np.ndarray]:
    """The housing's least walls (LOP-27): each run's least height along the pull, in its own free
    voxels, given to each of the run's free voxels (0: none), and each free voxel's share of metal
    that least height alone puts there.

    A run is a column's stretch of modelled voxels in one half, from the split outward (as
    `height_columns` reads them). It stands on a room when the voxel before its first, toward the
    split, is the inside's; at the split when it starts on the split's layer. Its least height above
    the split (mm) is the most of:
    - the end wall: its room's depth and the least wall, on a room;
    - the side wall: the deepest room of the half within a voxel of it in plan (8 neighbours), and
      the least wall, where that room is deeper than its own base;
    - the plate over the other half's wider opening: the least wall, at the split where the other
      half's inside reaches the split and its own does not;
    - the sealing land (A26): the flange's depth, at the split within the land's width of the
      inside, outside it;
    - a seal's seat (A16): the seal's length behind its bearing, on a room within the least wall and
      a voxel of a sealed exit's bore, in the exit's half.
    Less its base (the room's depth, or 0 at the split), less the frozen voxels within it wherever
    they stand, in the run's free voxels' own count."""
    from scipy.ndimage import distance_transform_edt, maximum_filter

    wall = value_in(spec.manufacturing.min_wall, "mm")
    t_f, land_w = float(info["flange"]["thickness"]), float(info["flange"]["land_width"])
    seat = value_in(spec.requirement.shaft_layout.behind_bearing_sealed, "mm")
    z_s = float(info["z"]["split"])
    grid, room = kind.reshape(tuple(n)), rooms.reshape(tuple(n))
    need = np.zeros(tuple(n))
    fill = np.zeros(tuple(n))
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    px, py = np.meshgrid(xc, yc, indexing="ij")
    own = {0: room[:, :, k_split - 1], 1: room[:, :, k_split]}  # each half's inside at the split
    inside_u = own[0] | own[1]
    off_u = (
        distance_transform_edt(~inside_u) * h
    )  # each cell's distance in plan from the inside at the split, mm
    for half in (0, 1):
        ks = (
            np.arange(k_split - 1, -1, -1) if half == 0 else np.arange(k_split, n[2])
        )  # from the split outward
        g, r = grid[:, :, ks], room[:, :, ks]
        depth = np.where(
            own[half], r.sum(axis=2) * h, 0.0
        )  # each column's rooms from the split, mm
        beside = maximum_filter(
            depth, size=3, mode="constant", cval=0.0
        )  # the deepest room within a voxel in plan
        plate = inside_u & ~own[half]
        land = ~inside_u & (off_u <= land_w + 1e-6)
        seal_ring = np.zeros(depth.shape, dtype=bool)
        for e in info.get("exits") or []:
            if e["kind"] != "seal" or (e["z"][1] <= z_s) != (half == 0):
                continue
            seal_ring |= (
                np.hypot(px - e["centre"][0], py - e["centre"][1]) <= e["radius"] + wall + h
            )
        for i, j in zip(*np.nonzero((g >= 0).any(axis=2)), strict=True):
            col, rc = g[i, j], r[i, j]
            k, top = 0, len(col)
            while k < top:
                if col[k] < 0:
                    k += 1
                    continue
                end = k
                while end < top and col[end] >= 0:
                    end += 1
                on_room = k > 0 and rc[k - 1]
                base = depth[i, j] if on_room else 0.0
                above = 0.0  # the least height above the split, mm
                if on_room:
                    above = base + wall
                    if seal_ring[i, j]:
                        above = max(above, base + seat)
                if beside[i, j] > base:
                    above = max(above, beside[i, j] + wall)
                if k == 0:  # at the split
                    if plate[i, j]:
                        above = max(above, wall)
                    if land[i, j]:
                        above = max(above, t_f)
                if (k == 0 or on_room) and above > base:
                    # each free voxel filled by the share of it the span covers, by its own offset
                    # from the run's start, frozen voxels counted wherever they stand
                    span = (above - base) / h
                    free_here = np.flatnonzero(col[k:end] == 0) + k
                    share = np.clip(span - (free_here - k), 0.0, 1.0)
                    need[i, j, ks[free_here]] = float(share.sum())
                    fill[i, j, ks[free_here]] = share
                k = end
    return need.ravel(), fill.ravel()


def hanging(
    kind: np.ndarray, n: np.ndarray, lo: np.ndarray, h: float, tie: dict, anchor: np.ndarray
) -> np.ndarray:
    """The modelled voxels not joined face to face to the supported body (`anchor`, the mounts'
    voxels): two voxels are joined when they share a face, and across the split only where a face's
    four corners all lie within a bolt boss's footprint (`tie`: k_split, bolts, radius). A voxel
    joined by an edge or a corner at most is a hinge, and the stiffness is singular there. Returns a
    flat mask."""
    from scipy.ndimage import label

    modelled = (kind >= 0).reshape(n)
    six = generate_binary_structure(3, 1)
    ks = tie["k_split"]
    lower, upper = modelled.copy(), modelled.copy()
    lower[:, :, ks:] = False
    upper[:, :, :ks] = False
    lab_lo, n_lo = label(lower, structure=six)
    lab_up, n_up = label(upper, structure=six)
    labels = lab_lo + np.where(lab_up > 0, lab_up + n_lo, 0)
    ni, nj = np.meshgrid(np.arange(n[0] + 1), np.arange(n[1] + 1), indexing="ij")
    px, py = lo[0] + h * ni, lo[1] + h * nj
    tied = np.zeros(ni.shape, dtype=bool)
    for bx, by in tie["bolts"]:
        tied |= np.hypot(px - bx, py - by) <= tie["radius"]
    face = tied[:-1, :-1] & tied[1:, :-1] & tied[:-1, 1:] & tied[1:, 1:]
    across = face & modelled[:, :, ks - 1] & modelled[:, :, ks]
    parent = np.arange(n_lo + n_up + 1)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in zip(labels[:, :, ks - 1][across], labels[:, :, ks][across], strict=True):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    root = np.array([find(i) for i in range(len(parent))])
    comp = root[labels]
    anchored = np.unique(comp[anchor.reshape(n) & modelled])
    anchored = anchored[anchored != root[0]]
    return (modelled & ~np.isin(comp, anchored)).ravel()


def build(layout: dict, spec, h: float, band: float, height_field: float) -> dict:
    """The voxel model at voxel size h (mm) on the layout record (`layout.record`): `kind` per
    voxel, the joint, the frozen mass, the least walls' mass, the height field's smoothing radius
    (`height_field` mm) and the band (mm)."""
    info = layout
    chain = complete_chain(spec)
    s = info["settings"]
    density = float(s["density"])  # kg/mm³
    gaps = spec.requirement.shaft_layout
    radial = value_in(gaps.min_radial_clearance, "mm")
    axial = value_in(gaps.min_axial_clearance, "mm")
    outline = np.asarray(info["outline"])
    low, high = info["z_range"]
    lo = np.array([outline[:, 0].min(), outline[:, 1].min(), low])
    hi = np.array([outline[:, 0].max(), outline[:, 1].max(), high])
    z_s = info["z"]["split"]
    lo[2] = z_s - h * np.ceil((z_s - low) / h - 1e-9)  # the split on a voxel face
    n = np.ceil((hi - lo) / h).astype(int)
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    zc = lo[2] + h * (np.arange(n[2]) + 0.5)
    gx, gy, gz = np.meshgrid(xc, yc, zc, indexing="ij")
    x, y, z = gx.ravel(), gy.ravel(), gz.ravel()
    in_pack = inside(outline, x, y)
    # the halves as the voxels split them: the cover's from layer k_split up, the motor side's below
    k_split = int(round((z_s - lo[2]) / h))
    k_of = np.broadcast_to(np.arange(n[2])[None, None, :], tuple(n)).ravel()
    cover = k_of >= k_split

    # every part's room: (axis x, axis y, radius, z from, z to)
    parts = []
    for stack in chain.layout.shafts:
        (ax, ay), shaft = stack.axis, stack.shaft
        least = []
        for p in stack.parts:
            if p.kind in ("gear", "carrier"):
                parts.append((ax, ay, p.diameter / 2 + radial, p.z_min - axial, p.z_max + axial))
            elif p.kind == "bearing":
                parts.append((ax, ay, p.diameter / 2, p.z_min, p.z_max))
                choice = chain.bearings.get((shaft, p.name.rsplit(" ", 1)[-1]))
                least.append(choice.bearing.d if choice else 0.5 * p.diameter)
        parts.append(
            (ax, ay, min(least) / 2, stack.ends[0], stack.ends[1])
        )  # the shaft, through its end walls
    # each shaft's way out: a seal's bore, taken 1 mm into the housing, and a half-shaft's joint
    # beyond the end face
    clear = np.zeros(x.shape, dtype=bool)
    for e in info["exits"]:
        into = 1.0 if e["kind"] == "seal" else 0.0
        clear |= (
            (np.hypot(x - e["centre"][0], y - e["centre"][1]) < e["radius"] + KEEP_MARGIN)
            & (z > e["z"][0] - into)
            & (z < e["z"][1] + into)
        )
    # The inside: a cup per half, each room's footprint from its far end in the half to the split. A
    # voxel is inside when most of it is, in plan (5 of 3 x 3 points).
    votes = np.zeros(x.shape, dtype=np.int8)
    for dx in (-h / 3, 0.0, h / 3):
        for dy in (-h / 3, 0.0, h / 3):
            hit = np.zeros(x.shape, dtype=bool)
            for ax, ay, radius, z0, z1 in parts:
                hit |= (np.hypot(x + dx - ax, y + dy - ay) < radius) & np.where(
                    cover, z < z1, z > z0
                )
            votes += hit
    rooms = votes >= 5
    grown = binary_dilation(rooms.reshape(n), structure=generate_binary_structure(3, 1)).ravel()
    skin = grown & ~rooms

    # the mounts (A20), and the vehicle's bracket and bolt beyond each mount's faces
    mounts = np.zeros(x.shape, dtype=bool)
    for m in info["mounts"]:
        mounts |= (
            (np.hypot(x - m["centre"][0], y - m["centre"][1]) <= s["mount_diameter"] / 2)
            & (z >= m["z"][0])
            & (z <= m["z"][1])
        )
    for b in info["brackets"]:
        clear |= (
            (np.hypot(x - b["centre"][0], y - b["centre"][1]) < b["radius"] + KEEP_MARGIN)
            & (z > b["z"][0])
            & (z < b["z"][1])
        )
    # The split flange: its sealing land and the bolts' bosses on it, whole cubes (the engineer, 13
    # October 18:38-18:42): a cube whose centre lies in the flange is the flange's
    fl = info["flange"]
    t_f = fl["thickness"]
    outer = np.asarray([(*c["centre"], c["radius"]) for c in fl["outer"]])
    inner = np.asarray([(*c["centre"], c["radius"]) for c in fl["inner"]])
    bolt_xy = np.asarray(info["bolts"], float)
    r_boss, r_hole = s["bolt_boss"] / 2, s["bolt_hole"] / 2
    idx = np.nonzero(in_pack & (np.abs(z - z_s) < t_f + h))[0]
    px, py = x[idx], y[idx]
    d_out = (
        np.hypot(px[:, None] - outer[None, :, 0], py[:, None] - outer[None, :, 1])
        - outer[None, :, 2]
    ).min(axis=1)
    d_in = (
        np.hypot(px[:, None] - inner[None, :, 0], py[:, None] - inner[None, :, 1])
        - inner[None, :, 2]
    ).min(axis=1)
    r_b = np.hypot(px[:, None] - bolt_xy[None, :, 0], py[:, None] - bolt_xy[None, :, 1]).min(axis=1)
    plan = ((d_out <= 0.0) & (d_in >= 0.0)) | ((r_b <= r_boss) & (r_b >= r_hole))
    flange_cells = np.zeros(x.shape, dtype=bool)
    flange_cells[idx] = plan & (np.abs(z[idx] - z_s) <= t_f)
    flange_cells &= ~rooms
    # each bolt's hole through the flange and its head's socket beyond each flange face, void, as
    # the drawing cuts and keeps them
    d_s, h_s = s["bolt_socket"]
    holes = np.zeros(x.shape, dtype=bool)
    for bx, by in info["bolts"]:
        r_b = np.hypot(x - bx, y - by)
        holes |= (r_b < r_hole) & (np.abs(z - z_s) <= t_f)
        beyond = np.where(
            cover,
            (z > z_s + t_f) & (z <= z_s + t_f + h_s),
            (z < z_s - t_f) & (z >= z_s - t_f - h_s),
        )
        holes |= (r_b < d_s / 2 + KEEP_MARGIN) & beyond
    clear |= holes
    flange_cells &= ~holes
    frozen = (mounts | flange_cells) & in_pack & ~clear
    design = in_pack & ~rooms & ~clear & ~frozen
    # The height envelope (11 October): metal only within the band of the shell, and round each
    # mount everything within reach of the shell at the mount's height and the band's past it, to
    # the split
    from scipy.ndimage import distance_transform_edt

    near = distance_transform_edt(~skin.reshape(n)).ravel() * h <= band
    corridor = np.zeros(x.shape, dtype=bool)
    sx, sy = x[skin], y[skin]
    for m in info["mounts"]:
        cx_, cy_ = m["centre"]
        j = int(np.argmin((sx - cx_) ** 2 + (sy - cy_) ** 2))
        reach_m = float(np.hypot(sx[j] - cx_, sy[j] - cy_)) + band
        z_lo, z_hi = m["z"][0] - band, m["z"][1] + band
        z_lo, z_hi = (z_lo, max(z_hi, z_s)) if m["z"][1] <= z_s else (min(z_lo, z_s), z_hi)
        corridor |= (np.hypot(x - cx_, y - cy_) <= reach_m) & (z >= z_lo) & (z <= z_hi)
    design &= near | corridor
    kind = np.full(x.shape, -1, dtype=np.int8)
    kind[design] = 0
    kind[frozen] = 1
    tie = {"k_split": k_split, "bolts": [tuple(b) for b in info["bolts"]], "radius": r_boss}
    # nothing left hanging: free voxels joined to the supported body by an edge or a corner at most
    # are left out of the model; a frozen one would be a fault in the set-up, and stops it
    loose = hanging(kind, n, lo, h, tie, mounts & (kind >= 0))
    if np.any(loose & (kind == 1)):
        raise RuntimeError(
            f"{int((loose & (kind == 1)).sum())} frozen voxels hang by an edge or a corner: the "
            "set-up is faulty"
        )
    kind[loose] = -1
    height_min, least_fill = least_heights(kind, rooms, n, k_split, h, lo, info, spec)
    # the 4 mm shell protected: every cube the least walls make metal (each column's least height
    # rounded to whole cubes, as the projection rounds it) frozen whole
    elem_ = np.flatnonzero(kind >= 0)
    free_e_ = np.flatnonzero(kind[elem_] == 0)
    col_, pos_, _, _ = height_columns(kind, n, k_split, elem_, free_e_)
    tmin_ = np.zeros(int(col_.max()) + 1)
    np.maximum.at(tmin_, col_, np.asarray(height_min, float)[elem_[free_e_]])
    shell = elem_[free_e_][pos_ + 0.5 < tmin_[col_]]
    kind[shell] = 1
    frozen[shell] = True
    frozen_kg = float(frozen.sum()) * h**3 * density
    least_kg = float(least_fill.sum()) * h**3 * density
    say(
        f"the 4 mm shell protected: {len(shell):,} cubes of the least walls frozen whole; the "
        "optimiser adds on top of it"
    )
    say(
        "the empty start with the shell fixed: the 4 mm shell, the sealing land and the bolts' "
        "bosses, the mounts "
        f"({frozen_kg:.2f} kg fixed); the walls' least metal about {least_kg:.2f} kg, inside the "
        "shell"
    )
    in_flange = frozen & flange_cells
    say(
        f"model {n.tolist()} voxels of {h:g} mm: {frozen.sum():,} frozen ({frozen_kg:.2f} kg: "
        f"mounts {mounts.sum():,}, the split "
        f"flange {int(in_flange.sum()):,}), {int((kind == 0).sum()):,} free"
        + (f"; {int(loose.sum())} free voxels hanging by an edge left out" if loose.any() else "")
    )
    return {
        "info": info,
        "spec": spec,
        "chain": chain,
        "h": h,
        "lo": lo,
        "n": n,
        "kind": kind,
        "k_split": k_split,
        "density": density,
        "joint": tie,
        "frozen_kg": frozen_kg,
        "least_kg": least_kg,
        "band": band,
        "height_field_mm": float(height_field),
        "height_min": np.zeros_like(height_min),
        "left_out": int(loose.sum()),
        "flange_kg": float(in_flange.sum()) * h**3 * density,
    }
