"""The voxel model as finite elements, and the chain from the design variables to the elements'
densities with its exact derivative (moved from `prototypes/first_loop/topo.py`: `Voxels`,
`hex_wilson`, `rotation_rows`, `released_at_split`, `least_width_blocks`, `open_heights`,
`mode_mass`, `gear_orders`, `mode_gaps`, `local_ball`, `greatest_share`; only the final recipe's
path; LOP-16 to LOP-29, LOP-33).

- **Elements:** every modelled voxel a cube with Wilson's incompatible modes (`hex_wilson`). The
  halves are released at the split; FE's rigid couplings join them: each seat's surface rigid with
  its bearing's centre, where its load acts; each bolt's hole through both flanges one rigid body at
  its point on the split; each mount's hole held (`physics.couplings`, eliminated exactly: u = T q).
- **Measures:** every seat's misalignment against its shaft's chord plus the shaft's lean, over its
  line (the grade's), at most 1/safety of it; every seat's bed (its nodes' mean displacement) at
  most the design to beat's, over the safety; the first `MODE_COUNT` modes and their slopes.
- **The chain (the height field):** one design variable a column of each half; the plan filter (a
  cone of the height field's radius over the columns of one layer); the least member width in plan
  (`open_heights`: a column's height counts only up to what the fullest block of columns on its
  level reaches); the least member (a column under it holds nothing, a smooth step sharpened with
  the projection); each voxel's density a smooth step on its column's height (at sharpness beta).
  The stiffness reads the densities by SIMP, the mass by their sum over the free voxels.
"""

from __future__ import annotations

import math
import time

import numpy as np
import scipy.sparse as sp

from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import say
from zenryx.domains.gearbox.housing.setup import height_columns
from zenryx.physics import couplings as cpl

PENAL, E_MIN = 3.0, 1e-6
# the adjoint solves are refined to this relative residual, the answers to 1e-10: a gradient
# needs fewer digits than the answer
ADJOINT_TOL = 1e-8
# below MODE_LOW a voxel's mass falls as rho^6 (Pedersen 2000), so a near-empty voxel has no local
# mode of its own; MODE_COUNT modes are read each analysis, to MODE_TOL
MODE_LOW = 0.1
MODE_COUNT = 14
MODE_TOL = 1e-5
# metal joined to nothing takes this share of its mass in the modes (the drawing drops it, and its
# near-free modes filled the modes read) and of its stiffness (hanging on near-empty cubes it left
# the single factor nearly singular)
LOOSE_MASS = 1e-6
LOOSE_STIFF = 1e-6
# the first mode's floor held on each of the lowest this many modes
FLOOR_MODES = 6
MEMBER_P = 12.0  # the greatest member's p-mean by default


def _d_matrix(young: float, poisson: float) -> np.ndarray:
    lam = young * poisson / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    d = np.zeros((6, 6))
    d[:3, :3] = lam
    d[np.arange(3), np.arange(3)] += 2 * mu
    d[np.arange(3, 6), np.arange(3, 6)] = mu
    return d


def _b_of(grads: np.ndarray) -> np.ndarray:
    """The 6 x 3m strain matrix of m shape functions' gradients (m, 3)."""
    b = np.zeros((6, 3 * len(grads)))
    for a, (gx, gy, gz) in enumerate(grads):
        b[0, 3 * a], b[1, 3 * a + 1], b[2, 3 * a + 2] = gx, gy, gz
        b[3, 3 * a], b[3, 3 * a + 1] = gy, gx
        b[4, 3 * a + 1], b[4, 3 * a + 2] = gz, gy
        b[5, 3 * a], b[5, 3 * a + 2] = gz, gx
    return b


def hex_wilson(h: float, young: float, poisson: float) -> np.ndarray:
    """A cube's 24x24 stiffness with Wilson's incompatible modes (1 - xi², 1 - eta², 1 - zeta² for
    each component) condensed out; 2x2x2 Gauss. The plain hexahedron locks in bending: a cantilever
    of 6 mm cubes one element thick reads 0.626 of beam theory's deflection, this one 0.985. On a
    cube the Jacobian is constant, so Taylor's correction is not needed."""
    d = _d_matrix(young, poisson)
    corners = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)], float) * 2 - 1
    g = 1 / math.sqrt(3)
    k = np.zeros((33, 33))
    for gx in (-g, g):
        for gy in (-g, g):
            for gz in (-g, g):
                dn = np.array(
                    [
                        [
                            xi * (1 + yi * gy) * (1 + zi * gz),
                            yi * (1 + xi * gx) * (1 + zi * gz),
                            zi * (1 + xi * gx) * (1 + yi * gy),
                        ]
                        for xi, yi, zi in corners
                    ]
                )
                dn *= 0.125 * (2 / h)
                dp = np.diag([-2 * gx, -2 * gy, -2 * gz]) * (2 / h)
                b = np.hstack([_b_of(dn), _b_of(dp)])
                k += b.T @ d @ b * (h / 2) ** 3
    kuu, kua, kaa = k[:24, :24], k[:24, 24:], k[24:, 24:]
    return kuu - kua @ np.linalg.solve(kaa, kua.T)


def rotation_rows(xyz: np.ndarray, ids: np.ndarray, n_dof: int) -> sp.csr_matrix:
    """(3, n_dof): a node set's best-fit rotation (RBE3, uniform weights), as FE reads it."""
    p = xyz[ids]
    r = p - p.mean(axis=0)
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    a_inv = np.linalg.inv(a)
    skew = np.zeros((len(ids), 3, 3))
    skew[:, 0, 1], skew[:, 0, 2] = -r[:, 2], r[:, 1]
    skew[:, 1, 0], skew[:, 1, 2] = r[:, 2], -r[:, 0]
    skew[:, 2, 0], skew[:, 2, 1] = -r[:, 1], r[:, 0]
    rot = np.einsum("ab,nbc->nac", a_inv, skew)
    rows, cols, vals = [], [], []
    for a_ in range(3):
        for c_ in range(3):
            rows += [a_] * len(ids)
            cols += list(3 * ids + c_)
            vals += list(rot[:, a_, c_])
    return sp.csr_matrix((vals, (rows, cols)), shape=(3, n_dof))


def released_at_split(node_key, corner, ijk, k_split: int, n_grid: int):
    """The halves released at the split: every node of the split's layer that an element above the
    split uses gets a copy of its own (its key plus `n_grid`); the rigid couplings join them at the
    bolts. `corner` is every element's eight corners' grid indices, `node_key` their node keys."""
    above = np.repeat(ijk[:, 2] >= k_split, 8)
    released = (corner[:, 2] == k_split) & above
    return np.where(released, node_key + n_grid, node_key)


def least_width_blocks(pts: np.ndarray, layer: np.ndarray, base: np.ndarray, w: int) -> dict:
    """The least member width in plan's blocks (the engineer, 14 October 13:42): every w x w square
    of columns standing on one level of one half (their first free voxel at one place along the
    pull, so their heights are measured from one base). Returns each block's columns (`blocks`),
    each column's blocks (`member`, -1 where none) and how many columns lie in no block
    (`alone`)."""
    half = np.asarray(layer, np.int64) // 10_000
    ii, jj = np.asarray(pts[:, 0], np.int64), np.asarray(pts[:, 1], np.int64)
    base = np.asarray(base, np.int64)
    key = {
        (int(a), int(b), int(c), int(d)): k
        for k, (a, b, c, d) in enumerate(zip(half, base, ii, jj, strict=True))
    }
    if len(key) != len(ii):
        raise ValueError("two columns on one level share a plan cell")
    offsets = [(a, b) for a in range(w) for b in range(w)]
    found = []
    n_cols = len(ii)
    for c in range(n_cols):  # each block named by its corner column
        cols = [
            key.get((int(half[c]), int(base[c]), int(ii[c]) + a, int(jj[c]) + b))
            for a, b in offsets
        ]
        if all(k is not None for k in cols):
            found.append(cols)
    q = len(offsets)
    blocks = np.asarray(found, np.int64).reshape(-1, q)
    member = np.full((n_cols, q), -1, np.int64)
    fill = np.zeros(n_cols, np.int64)
    for bi, cols in enumerate(blocks):
        for k in cols:
            member[k, fill[k]] = bi
            fill[k] += 1
    return {"blocks": blocks, "member": member, "w": int(w), "alone": int((fill == 0).sum())}


def open_heights(op: dict, t0: np.ndarray, k: float):
    """The columns' heights opened to the least width in plan: each block's soft minimum of its
    columns' heights, then each column's soft maximum over the blocks it is in (Sigmund 2007's
    opening: erode, then dilate), both by log-sum-exp at sharpness k a voxel. A member narrower than
    a block weighs nothing; a column in no block holds nothing. Returns the opened heights and their
    Jacobian by t0 (sparse; each row sums to 1)."""
    blocks, member = op["blocks"], op["member"]
    n_cols = len(t0)
    if len(blocks) == 0:
        return np.zeros(n_cols), sp.csr_matrix((n_cols, n_cols))
    tb = t0[blocks]
    m = tb.min(axis=1, keepdims=True)
    ea = np.exp(-k * (tb - m))
    sa = ea.sum(axis=1, keepdims=True)
    e = m[:, 0] - np.log(sa[:, 0]) / k  # each block's soft minimum (at most its lowest column)
    a = ea / sa  # its slope by each of its columns' heights
    has = member >= 0
    eb = np.where(has, e[np.where(has, member, 0)], -np.inf)
    top = eb.max(axis=1)
    ok = np.isfinite(top)
    top0 = np.where(ok, top, 0.0)
    es = np.where(has, np.exp(k * (np.where(has, eb, 0.0) - top0[:, None])), 0.0)
    ss = np.where(ok, es.sum(axis=1), 1.0)
    t_open = np.where(ok, top0 + np.log(ss) / k, 0.0)
    s = es / ss[:, None]  # each column's slope by its blocks' minima
    rows = np.repeat(np.arange(n_cols), member.shape[1])[has.ravel()]
    s_mat = sp.csr_matrix((s[has], (rows, member[has])), shape=(n_cols, len(blocks)))
    q = blocks.shape[1]
    a_mat = sp.csr_matrix(
        (a.ravel(), (np.repeat(np.arange(len(blocks)), q), blocks.ravel())),
        shape=(len(blocks), n_cols),
    )
    return t_open, (s_mat @ a_mat).tocsr()


def mode_mass(dens: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Each element's share of its voxel's mass for the modes, and its slope by the density: the
    density itself, and below MODE_LOW MODE_LOW (rho / MODE_LOW)^6 (Pedersen 2000)."""
    r = np.maximum(dens, 0.0) / MODE_LOW
    low = dens < MODE_LOW
    return np.where(low, MODE_LOW * r**6, dens), np.where(low, 6.0 * r**5, 1.0)


def gear_orders(spec, chain) -> dict:
    """The gear orders the modes are kept from, as FE computes them: each stage's mesh frequency at
    the rated speed (its pinion's teeth times its shaft's turns a second), Hz."""
    return {
        s.name: int(s.z_pinion.value) * chain.speeds[s.pinion_shaft] / 60.0
        for s in spec.requirement.stages
    }


def mode_gaps(
    hz: np.ndarray, d_hz: np.ndarray, orders: dict, margin: float, floor: float
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """The gap round each gear order as constraints (at most 0 when held): the highest mode below
    the order at most (1 - margin) of it, the lowest above at least (1 + margin) of it; two an
    order, in the orders' order. A side no computed mode stands on is held (-1, no slope). Then
    FLOOR_MODES more: each of the lowest FLOOR_MODES modes at least `floor` (Hz), so a cluster of
    modes is raised together. Returns the values, their derivatives by the element densities and a
    note of which mode each read."""
    g, rows, notes = [], [], []
    for name, f_o in orders.items():
        below, above = np.flatnonzero(hz < f_o), np.flatnonzero(hz >= f_o)
        lo_ = f_o * (1.0 - margin)
        hi_ = f_o * (1.0 + margin)
        if len(below):
            i = below[np.argmax(hz[below])]
            g.append(hz[i] / lo_ - 1.0)
            rows.append(d_hz[i] / lo_)
            notes.append(f"{name}: mode {i + 1} {hz[i]:.0f} Hz at most {lo_:.0f}")
        else:
            g.append(-1.0)
            rows.append(np.zeros(d_hz.shape[1]))
            notes.append(f"{name}: no mode below")
        if len(above):
            i = above[np.argmin(hz[above])]
            g.append(1.0 - hz[i] / hi_)
            rows.append(-d_hz[i] / hi_)
            notes.append(f"{name}: mode {i + 1} {hz[i]:.0f} Hz at least {hi_:.0f}")
        else:
            g.append(-1.0)
            rows.append(np.zeros(d_hz.shape[1]))
            notes.append(f"{name}: no mode above in the {len(hz)} read")
    order = np.argsort(hz)
    for j in range(FLOOR_MODES):
        if j < len(order):
            i = int(order[j])
            g.append(1.0 - hz[i] / floor)
            rows.append(-d_hz[i] / floor)
            notes.append(f"mode {j + 1} {hz[i]:.0f} Hz at least {floor:.0f}")
        else:
            g.append(-1.0)
            rows.append(np.zeros(d_hz.shape[1]))
            notes.append(f"mode {j + 1}: not read")
    return np.asarray(g, float), np.vstack(rows), notes


def local_ball(ijk, radius: float):
    """The free voxels' ball neighbourhoods for the greatest member: a sparse 0/1 matrix (each
    voxel, every free voxel within `radius` voxels of it, itself included) and the number of grid
    cells a whole ball holds, so that a ball reaching past the free voxels counts that part as
    empty."""
    from scipy.spatial import cKDTree

    tree = cKDTree(np.asarray(ijk, float))
    pairs = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    n = len(ijk)
    ball = sp.coo_matrix((np.ones(len(pairs.data)), (pairs.row, pairs.col)), shape=(n, n)).tocsr()
    ball = ((ball + sp.eye(n, format="csr")) > 0).astype(float).tocsr()
    r = int(math.floor(radius))
    o = np.arange(-r, r + 1)
    cells = int(
        ((o[:, None, None] ** 2 + o[None, :, None] ** 2 + o[None, None, :] ** 2) <= radius**2).sum()
    )
    return ball, cells


def greatest_share(ball, cells: int, rho, alpha: float, p: float):
    """The greatest member's constraint at the free voxels' densities `rho` (Guest 2009's maximum
    length scale, as Wu, Aage, Westermann & Sigmund 2018's local volume constraint): G = M / alpha -
    1, M the density-weighted p-mean of each voxel's ball share, with dG / d rho and M itself. `p`
    sets how near the worst ball the mean reads (at 40 one knot of 100 voxels at 0.8 among 30,000 at
    0.55 reads 0.69 and is held)."""
    share = (ball @ rho) / cells
    a = float(np.sum(rho * share**p))
    b = float(np.sum(rho))
    if a <= 0.0 or b <= 0.0:
        return -1.0, np.zeros_like(rho), 0.0
    m = (a / b) ** (1.0 / p)
    d_a = share**p + p * (ball.T @ (rho * share ** (p - 1.0))) / cells
    d_m = (m / p) * (d_a / a - 1.0 / b)
    return m / alpha - 1.0, d_m / alpha, m


class Voxels:
    """The voxel model (`setup.build`'s), its analysis and the chain from the design variables to
    the densities. `model` also carries `cases`, `safety`, `beds_mm`, `least_height_mm`,
    `least_width_mm`."""

    def __init__(self, model):
        h, n, lo, kind = model["h"], model["n"], model["lo"], model["kind"]
        info, chain, spec = model["info"], model["chain"], model["spec"]
        material = spec.manufacturing.material
        self.model, self.h = model, h
        self.density = float(model["density"])
        self.elem = elem = np.flatnonzero(kind >= 0)
        self.frozen = frozen = kind[elem] == 1
        self.ijk = ijk = np.stack(np.unravel_index(elem, n), axis=1)
        self.grid_n, self.k_split_ = np.asarray(n, int), int(model["k_split"])
        offsets = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)])
        corner = (ijk[:, None, :] + offsets[None, :, :]).reshape(-1, 3)
        n_grid = int(np.prod(n + 1))
        node_key = released_at_split(
            np.ravel_multi_index(corner.T, n + 1), corner, ijk, int(model["k_split"]), n_grid
        )
        used, inverse = np.unique(node_key, return_inverse=True)
        conn = inverse.reshape(-1, 8)
        xyz = lo + h * np.stack(np.unravel_index(used % n_grid, n + 1), axis=1)
        n_nodes = len(used)
        self.n_dof = n_dof = 3 * n_nodes
        self.xyz = xyz  # the nodes' coordinates, mm (a copy above the split shares its node's)
        self.mode_count = MODE_COUNT
        say(
            f"voxels {h:g} mm: {len(elem):,} elements ({frozen.sum():,} frozen, "
            f"{(~frozen).sum():,} free), {n_dof:,} unknowns; "
            "the halves released at the split"
        )
        self.ke = hex_wilson(
            h, value_in(material.youngs_modulus, "MPa"), value_in(material.poisson_ratio, "1")
        )
        self.dof = (3 * conn[:, :, None] + np.arange(3)[None, None, :]).reshape(-1, 24)

        s = info["settings"]
        wanted = tuple(model["cases"])
        self.cases = cases = [c for c in chain.loads if c.name in wanted]
        if len(cases) != len(wanted):
            raise ValueError(f"load cases {wanted}: the chain has {[c.name for c in chain.loads]}")
        self.n_cases = len(cases)
        # A seat's nodes are the frozen voxels' own: a node held only by near-empty design voxels
        # would swing freely and read as a tilt.
        seat_ids = {}
        on_shell = np.zeros(n_nodes, dtype=bool)
        on_shell[np.unique(conn[frozen])] = True
        for b in info["bearings"]:
            r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
            ids = np.flatnonzero(
                on_shell
                & (np.abs(r - b["D"] / 2) <= 0.75 * h)
                & (xyz[:, 2] >= b["z"][0] - 0.5 * h)
                & (xyz[:, 2] <= b["z"][1] + 0.5 * h)
            )
            assert len(ids) > 8, (b["shaft"], b["side"], len(ids))
            seat_ids[(b["shaft"], b["side"])] = ids
        seat_force = {}  # each seat's force by case, applied at its bearing's centre
        for j, case in enumerate(cases):
            for seat in case.seats:
                seat_force.setdefault((seat.shaft, seat.side), np.zeros((3, self.n_cases)))[
                    :, j
                ] += np.asarray(seat.force, float)
        # FE's couplings: a seat's surface (its nodes on the model's boundary) rigid with its
        # bearing's centre; each bolt's hole through both flanges (the nodes on its boundary within
        # half a voxel of the hole) one rigid body at its point on the split; each mount's hole (the
        # lug's core within the hole's radius and a quarter voxel) held
        boundary = np.bincount(conn.ravel(), minlength=n_nodes) < 8
        groups = []
        # a node two seats reach (bores closer than a voxel or two) goes to the seat whose surface
        # it lies nearer
        gap = {}
        for key, ids in seat_ids.items():
            b = next(b_ for b_ in info["bearings"] if (b_["shaft"], b_["side"]) == key)
            gap[key] = np.abs(
                np.hypot(xyz[ids, 0] - b["axis"][0], xyz[ids, 1] - b["axis"][1]) - b["D"] / 2
            )
        nearest = {}
        for key, ids in seat_ids.items():
            for i_, d_ in zip(ids, gap[key], strict=True):
                if i_ not in nearest or d_ < nearest[i_][1]:
                    nearest[i_] = (key, d_)
        for key, ids in list(seat_ids.items()):
            ids = np.array([i_ for i_ in ids if nearest[i_][0] == key], dtype=np.int64)
            ids = ids[boundary[ids]]
            assert len(ids) > 8, (key, len(ids))
            seat_ids[key] = ids
            b = next(b_ for b_ in info["bearings"] if (b_["shaft"], b_["side"]) == key)
            groups.append(
                {
                    "nodes": ids,
                    "ref": (*b["axis"], 0.5 * (b["z"][0] + b["z"][1])),
                    "name": f"the {key[0]} {key[1]} seat",
                    "seat": key,
                }
            )
        z_s = float(info["z"]["split"])
        t_f = float(info["flange"]["thickness"])
        n_bolts = 0
        for c in info["bolts"]:
            r = np.hypot(xyz[:, 0] - c[0], xyz[:, 1] - c[1])
            ids = np.flatnonzero(
                boundary
                & (r <= s["bolt_hole"] / 2 + 0.5 * h)
                & (np.abs(xyz[:, 2] - z_s) <= t_f + 1e-6)
            )
            if len(ids) >= 6:
                groups.append(
                    {"nodes": ids, "ref": (c[0], c[1], z_s), "name": f"bolt {n_bolts + 1}"}
                )
                n_bolts += 1
        held = []
        for m in info["mounts"]:
            r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
            ids = np.flatnonzero(
                (r <= s["mount_hole"] / 2 + 0.25 * h)
                & (xyz[:, 2] >= m["z"][0] - 1e-6)
                & (xyz[:, 2] <= m["z"][1] + 1e-6)
            )
            groups.append({"nodes": ids, "fixed": True, "name": m["name"]})
            held.append(ids)
        self.held = np.unique(np.concatenate(held))
        T, tinfo = cpl.rigid_transform(xyz, groups)
        rigid = cpl.check_rigid(T, xyz, groups, tinfo)
        if rigid > 1e-9:
            raise RuntimeError(f"the rigid couplings' transform is not rigid: {rigid:.1e}")
        self.T, self.n_q = T, tinfo["n_q"]
        rhs = np.zeros((self.n_q, self.n_cases))
        for g, grp in enumerate(groups):
            if grp.get("seat") in seat_force:
                rhs[tinfo["ref_col"][g] : tinfo["ref_col"][g] + 3] += seat_force[grp["seat"]]
        self.rhs = rhs
        self.joint_note = (
            f"the halves released at the split; rigid couplings: {len(seat_ids)} seats, "
            f"{n_bolts} bolts through both halves, {len(held)} mounts held"
        )
        say(
            f"rigid couplings (FE's): {len(seat_ids)} seats with their bearings' centres, "
            f"{n_bolts} bolts each one rigid body, "
            f"{len(held)} mounts' holes held; {self.n_q:,} unknowns remain"
        )
        # Each seat's misalignment against its shaft's chord plus the shaft's lean (the grade's),
        # and its line (rad), at most 1/safety of it: the factor of safety covers the model's own
        # optimism
        limits = {t.bearing_type: value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
        margin = value_in(spec.limits.model_margin, "1")
        safety = float(model["safety"])
        types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
        centre_z = {
            (b["shaft"], b["side"]): 0.5 * (b["z"][0] + b["z"][1]) for b in info["bearings"]
        }

        def moved(ids):
            """(3, n_q): the mean displacement of a node set."""
            rr_, cc_, vv_ = [], [], []
            for k_ in range(3):
                rr_ += [k_] * len(ids)
                cc_ += list(3 * ids + k_)
                vv_ += [1.0 / len(ids)] * len(ids)
            return (sp.csr_matrix((vv_, (rr_, cc_)), shape=(3, n_dof)) @ self.T).tocsr()

        self.seats = []
        for key in seat_ids:
            shaft, side = key
            a_, b_ = moved(seat_ids[(shaft, "-z")]), moved(seat_ids[(shaft, "+z")])
            rr = (rotation_rows(xyz, seat_ids[key], n_dof) @ self.T).tocsr()
            span = abs(centre_z[(shaft, "+z")] - centre_z[(shaft, "-z")])
            # hypot(theta_y - dx - lean_x, -theta_x - dy - lean_y), dx = (u+z - u-z)_x / span
            l1 = (rr[1] - (b_[0] - a_[0]) / span).tocsr()
            l2 = (-rr[0] - (b_[1] - a_[1]) / span).tocsr()
            self.seats.append((key, (1 - margin) * limits[types[key]] / safety, l1, l2))
        leans = {sec.shaft: sec.lean_at_bearing for sec in chain.sections}
        self.lean_of = {
            (key, c): leans[key[0]].get(case.name, {}).get(key[1], (0.0, 0.0))
            for key in seat_ids
            for c, case in enumerate(cases)
        }
        # every seat in every case, in this order: the constraints
        self.keys = [(key, c) for key, *_ in self.seats for c in range(len(cases))]
        # The bearing beds (the grade's displacement line): each seat's displacement, the mean of
        # its nodes', at most the design to beat's over the safety in each case `beds_mm` names
        beds_mm = model["beds_mm"]
        self.bed_line = [
            beds_mm[case.name] / safety if beds_mm.get(case.name) else None for case in cases
        ]
        self.bed_rows = {key: moved(ids) for key, ids in seat_ids.items()}
        self.bed_keys = [
            (key, c) for key in seat_ids for c, line in enumerate(self.bed_line) if line
        ]

        self.free_e = free_e = np.flatnonzero(~frozen)
        self.mass_rows = np.zeros(len(elem))
        self.mass_rows[free_e] = 1.0  # the mass (in voxels) reads the free voxels' densities
        # The height field (the engineer, 11 October 15:44: "we need some continuous space on which
        # we can do optimisation"): one design variable a column of each half, the metal's height
        # there from the split or the wall it stands on, smoothed over the plan by a cone of the
        # field's radius, so the members are continuous ridges and webs: castable by construction
        from scipy.spatial import cKDTree

        col, pos, pts, layer = height_columns(kind, n, model["k_split"], elem, free_e)
        n_cols = len(pts)
        radius = float(model["height_field_mm"]) / h
        plan = np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]])
        ptree = cKDTree(plan)
        pp = ptree.sparse_distance_matrix(ptree, radius, output_type="coo_matrix")
        fmat = sp.coo_matrix(
            (np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(n_cols, n_cols)
        ).tocsr()
        fmat = (fmat + sp.eye(n_cols) * radius).tocsr()
        cmat = sp.csr_matrix(
            (np.ones(len(col)), (col, np.arange(len(col)))), shape=(n_cols, len(col))
        )
        fs = np.asarray(fmat.sum(axis=1)).ravel()
        mmat = (
            sp.diags(1.0 / fs) @ fmat
        ).tocsr()  # the design variables to the columns' heights (as shares of L)
        self.n_design = n_cols
        self.height = {
            "col": col,
            "pos": pos,
            "M": mmat,
            "C": cmat,
            "L": float(pos.max() + 1.0),
            "n_cols": n_cols,
            "least": float(model["least_height_mm"]) / h,
            "h": h,
        }
        say(f"the least member: a column under {model['least_height_mm']:g} mm holds nothing")
        # the least member width in plan (the engineer, 14 October 13:42): each column's first free
        # voxel's place along the pull is its level
        kz = elem[free_e] % int(n[2])
        base = np.full(n_cols, -1, np.int64)
        first_ = pos == 0
        base[col[first_]] = kz[first_]
        if (base < 0).any():
            raise ValueError("a column without its first free voxel")
        least_w = float(model["least_width_mm"])
        w = int(round(least_w / h))
        if w < 2:
            raise ValueError(
                f"the least width {least_w:g} mm is under two {h:g} mm cubes: nothing to open"
            )
        op = self.height["open"] = least_width_blocks(pts, layer, base, w)
        say(
            f"the least member width in plan: {least_w:g} mm ({w} cubes); a column's height counts "
            "only up to what the "
            f"fullest {w} x {w} block of columns on its level reaches ({len(op['blocks']):,} "
            f"blocks; {op['alone']:,} of "
            f"{n_cols:,} columns in none, holding nothing)"
        )
        say(
            f"the height field: {n_cols:,} columns, each a height from the split or its wall, "
            "smoothed over "
            f"{model['height_field_mm']:g} mm in plan; at most {self.height['L']:.0f} voxels high; "
            f"{len(free_e):,} free voxels"
        )
        self._gpu = None

    def _height_dens(self, x, beta: float):
        """The free densities, their slope by the columns' opened heights (voxels), and the least
        width's opening's Jacobian."""
        hh = self.height
        # the columns' heights (voxels): the plan filter's of the design variables, opened to the
        # least width in plan
        t0, jac = open_heights(hh["open"], (hh["M"] @ x) * hh["L"], max(beta, 2.0))
        # the least member (the engineer, 12 October 09:54): a column's height counts only once it
        # passes `least`, a smooth step sharpened with the projection, so a thin layer of paint
        # holds nothing and costs nothing
        s = np.tanh(max(beta, 2.0) * (t0 - hh["least"]))
        g = 0.5 * (1.0 + s)
        slope = g + t0 * 0.5 * max(beta, 2.0) * (1.0 - s * s)
        t = t0 * g
        th = np.tanh(beta * (t[hh["col"]] - hh["pos"] - 0.5))
        return 0.5 * (1.0 + th), 0.5 * beta * (1.0 - th * th) * slope[hh["col"]], jac

    def physical(self, x, beta: float) -> np.ndarray:
        """The element densities a design vector gives (frozen voxels 1)."""
        dens = np.ones(len(self.elem))
        dens[self.free_e] = self._height_dens(x, beta)[0]
        return dens

    def back(self, d_dens, x, beta: float) -> np.ndarray:
        """Derivatives with respect to the densities (one row per function, or one vector) taken
        back to the design variables: through each voxel's step on its column's height, the least
        width's opening and the plan filter. A frozen voxel's entries carry nothing."""
        rows = np.atleast_2d(d_dens)
        hh = self.height
        _, slope, jac = self._height_dens(x, beta)
        d = np.where(self.frozen[None, :], 0.0, rows)[:, self.free_e] * slope[None, :]
        g = np.asarray(hh["C"] @ d.T).T
        g = np.asarray(jac.T @ g.T).T * hh["L"]
        out = np.asarray(hh["M"].T @ g.T).T
        return out if np.ndim(d_dens) == 2 else out[0]

    def analyse(self, dens, penal: float = PENAL, adjoints: bool = True) -> dict:
        """One finite-element solve at the densities `dens` (the modelled elements', in `elem`
        order), SIMP's penalty `penal`: every case on one single-precision factor (refined in double
        to 1e-10), every seat's ratio to its line and its bed. With `adjoints` the derivatives by
        the densities (`finish`); without, the factor is kept: `finish` then takes the derivatives
        on it (a trial point GCMMA accepts), `release` frees it (one it refuses)."""
        from zenryx.physics.fast_factor import GpuStiffness

        t0 = time.time()
        clock = {}
        e_scale = E_MIN + dens**penal * (1 - E_MIN)
        # metal joined to nothing takes LOOSE_STIFF of its stiffness: it carries nothing, and
        # hanging on near-empty cubes it leaves the single factor nearly singular
        loose = self.loose(dens)
        k_share = np.where(loose, LOOSE_STIFF, 1.0) if loose.any() else None
        if k_share is not None:
            e_scale = e_scale * k_share
        # the stiffness assembled on the GPU into the pattern found once, its factor refactorised in
        # place
        if self._gpu is None:
            self._gpu = GpuStiffness(self.ke, self.T, self.dof)
        factor = self._gpu.factor(e_scale)
        clock["assemble"], clock["factor"] = factor.assemble_s, factor.factor_s
        steps = []
        try:
            t1 = time.time()
            sols = [factor.solve(self.rhs[:, c]) for c in range(self.n_cases)]
            uf = np.column_stack([s_[0] for s_ in sols])
            steps += [s_[1] for s_ in sols]
            clock["solves"] = time.time() - t1
            ratios, adjoint_rhs = {}, {}
            for key, line, l1, l2 in self.seats:
                for c in range(self.n_cases):
                    lx, ly = self.lean_of[(key, c)]
                    v1, v2 = float((l1 @ uf[:, c])[0]) - lx, float((l2 @ uf[:, c])[0]) - ly
                    tilt = math.hypot(v1, v2)
                    ratios[(key, c)] = tilt / line
                    # d ratio / du = (v1 dv1/du + v2 dv2/du) / (tilt line)
                    adjoint_rhs[(key, c)] = (
                        (v1 * l1.toarray().ravel() + v2 * l2.toarray().ravel()) / (tilt * line)
                        if tilt > 0
                        else np.zeros(self.n_q)
                    )
            beds, bed_rhs = {}, {}
            for key, c in self.bed_keys:  # each seat's bed over its line, and d(it)/du
                mv = self.bed_rows[key]
                moved_by = np.asarray(mv @ uf[:, c]).ravel()
                size = float(np.linalg.norm(moved_by))
                line = self.bed_line[c]
                beds[(key, c)] = size / line
                bed_rhs[(key, c)] = np.asarray(mv.T @ moved_by).ravel() / (max(size, 1e-30) * line)
        except BaseException:
            factor.close()
            raise
        u = np.asarray(self.T @ uf).reshape(self.n_dof, self.n_cases)
        out = {
            "ratios": ratios,
            "u": u,
            "clock": clock,
            "steps": steps,
            "beds": beds,
            "bed_vector": np.array([beds[kc] for kc in self.bed_keys]) if beds else np.zeros(0),
            "_bed_rhs": bed_rhs,
            "_factor": factor,
            "_adjoint_rhs": adjoint_rhs,
            "_dens": dens,
            "_penal": penal,
            "_t0": t0,
            "_k_share": k_share,
            "loose_stiff_voxels": int(loose.sum()),
            "value": float(
                sum(self.rhs[:, c] @ uf[:, c] for c in range(self.n_cases))
            ),  # the compliance f'u
            "ratio_vector": np.array([ratios[kc] for kc in self.keys]),
        }
        clock["total"] = time.time() - t0
        return self.finish(out) if adjoints else out

    def with_modes(self, out: dict) -> dict:
        """The modes on an analysis's kept factor, once (`_modes`): at the point a step takes
        (`finish`) and at the binary check, never at a trial GCMMA may refuse."""
        if "modes_hz" not in out and out.get("_factor") is not None:
            try:
                self._modes(out)
            except BaseException:
                self.release(out)
                raise
        return out

    def _modes(self, out: dict) -> None:
        """The model's first `mode_count` natural frequencies (Hz) at an analysis's densities, on
        its kept factor, and each one's derivative by the element densities (`modes_hz`,
        `d_modes_hz`). Shift-invert Lanczos about zero (scipy's eigsh reads the stiffness only
        through the factor); the housing's own mass lumped at the voxels' corners; near-empty
        voxels' mass taken down (`mode_mass`). A mode's slope by an element's density: its
        mass-normalised shape's strain energy there times the stiffness's slope, less its eigenvalue
        times its kinetic share there times the mass's slope."""
        from scipy.sparse.linalg import LinearOperator, eigsh

        t1 = time.time()
        factor, dens, penal = out["_factor"], out["_dens"], out["_penal"]
        mi, dmi = mode_mass(dens)
        loose = self.loose(
            dens
        )  # metal joined to nothing, the drawing's to drop: its mass taken down
        if loose.any():
            mi, dmi = np.where(loose, LOOSE_MASS * mi, mi), np.where(loose, LOOSE_MASS * dmi, dmi)
        out["loose_voxels"] = int(loose.sum())
        unit = self.density * self.h**3
        m_dof = np.zeros(self.n_dof)
        np.add.at(m_dof, self.dof, np.repeat((unit * mi / 8.0)[:, None], 24, axis=1))
        m_red = (self.T.T @ sp.diags(m_dof) @ self.T).tocsr()  # the housing's lumped mass, reduced
        n = self.n_q
        op = LinearOperator(
            (n, n),
            matvec=lambda v: factor.solve(
                np.asarray(v, float).ravel(), tol=min(1e-7, 0.1 * MODE_TOL)
            )[0],
            dtype=np.float64,
        )
        a_shape = LinearOperator(
            (n, n), matvec=lambda v: v, dtype=np.float64
        )  # not read in shift-invert mode
        v0 = getattr(
            self, "_mode_start", None
        )  # the last step's modes summed: Lanczos starts near them
        lam, vec = eigsh(
            a_shape,
            k=self.mode_count,
            M=m_red,
            sigma=0.0,
            OPinv=op,
            which="LM",
            tol=MODE_TOL,
            v0=v0 if v0 is not None and len(v0) == n else None,
        )
        self._mode_start = vec.sum(axis=1)
        order = np.argsort(lam)
        lam, vec = np.maximum(lam[order], 0.0), vec[:, order]
        hz = np.sqrt(lam * 1000.0) / (2.0 * math.pi)  # N/mm over kg: 1000 /s² a unit
        d_k = penal * dens ** (penal - 1) * (1 - E_MIN)
        if (
            out.get("_k_share") is not None
        ):  # metal joined to nothing: its stiffness's share, as `analyse` took it
            d_k = d_k * out["_k_share"]
        d_m = unit * dmi / 8.0
        d_hz = np.zeros((len(hz), len(self.elem)))
        for i in range(len(hz)):
            phi = vec[:, i] / math.sqrt(float(vec[:, i] @ (m_red @ vec[:, i])))
            pe = np.asarray(self.T @ phi).ravel()[self.dof]
            strain = np.einsum("ej,jk,ek->e", pe, self.ke, pe)
            kinetic = (pe * pe).sum(axis=1)
            d_hz[i] = (
                1000.0
                * (d_k * strain - lam[i] * d_m * kinetic)
                / (8.0 * math.pi**2 * max(float(hz[i]), 1e-9))
            )
        d_hz[:, self.frozen] = 0.0
        out["modes_hz"], out["d_modes_hz"] = hz, d_hz
        out["clock"]["modes"] = time.time() - t1

    def loose(self, dens: np.ndarray) -> np.ndarray:
        """Each element joined to nothing: in its half, metal (a density of 0.5 or more, or fixed)
        face-joined to no other than its own piece, the half's largest piece of metal its body. A
        fixed part is never loose."""
        from scipy.ndimage import label

        metal = np.zeros(tuple(self.grid_n), bool)
        on = (np.asarray(dens) >= 0.5) | self.frozen
        metal[tuple(self.ijk[on].T)] = True
        joined = np.zeros(metal.shape, bool)
        ks = self.k_split_ if 0 < self.k_split_ < metal.shape[2] else metal.shape[2]
        for sl in (np.s_[:, :, :ks], np.s_[:, :, ks:]):
            lab, k = label(metal[sl])
            if k:
                sizes = np.bincount(lab.ravel())
                sizes[0] = 0
                joined[sl] = lab == int(np.argmax(sizes))
        return on & ~joined[tuple(self.ijk.T)] & ~self.frozen

    def release(self, out: dict) -> None:
        """Free a kept factor (a trial point refused)."""
        factor = out.pop("_factor", None)
        if factor is not None:
            factor.close()

    def finish(self, out: dict) -> dict:
        """The derivatives of an analysis kept with `adjoints=False`, by adjoint solves on its
        factor, which is then freed: every seat's ratio and bed by the densities."""
        self.with_modes(out)  # the point taken: its modes, while its factor is open
        factor = out["_factor"]
        dens, penal = out["_dens"], out["_penal"]
        clock, steps = out["clock"], out["steps"]
        try:
            t1 = time.time()
            lam = {}
            for kc, rhs in out["_adjoint_rhs"].items():
                sol, n_steps, _ = factor.solve(rhs, tol=ADJOINT_TOL)
                lam[kc] = sol
                steps.append(n_steps)
            lam_bed = {}
            for kc, rhs in out["_bed_rhs"].items():
                sol, n_steps, _ = factor.solve(rhs, tol=ADJOINT_TOL)
                lam_bed[kc] = sol
                steps.append(n_steps)
            clock["adjoints"] = time.time() - t1
        finally:
            self.release(out)
        d_e = penal * dens ** (penal - 1) * (1 - E_MIN)  # d stiffness scale / d density
        if (
            out.get("_k_share") is not None
        ):  # metal joined to nothing: its stiffness's share, held at this point
            d_e = d_e * out["_k_share"]
        ue = out["u"][self.dof]  # (elements, 24, cases)
        d_ratios = np.empty((len(self.keys), len(self.elem)))
        for i, kc in enumerate(self.keys):
            le = np.asarray(self.T @ lam[kc]).ravel()[self.dof]
            # d ratio / d density_e = -d_e lambda_e' k_e u_e (the case's u)
            d_ratios[i] = -d_e * np.einsum("ei,ei->e", le @ self.ke, ue[:, :, kc[1]])
        out["d_ratios"] = d_ratios
        d_beds = np.empty((len(self.bed_keys), len(self.elem)))
        for i, kc in enumerate(self.bed_keys):
            full = np.asarray(self.T @ lam_bed[kc]).ravel()
            d_beds[i] = -d_e * np.einsum("ei,ei->e", full[self.dof] @ self.ke, ue[:, :, kc[1]])
        out["d_beds"] = d_beds
        for key in ("_adjoint_rhs", "_bed_rhs", "_dens"):
            out.pop(key, None)
        clock["total"] = time.time() - out.pop("_t0")
        return out
