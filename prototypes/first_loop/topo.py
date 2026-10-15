"""PROTOTYPE (LOP-3) - not product code: topology optimisation outside a frozen shell.

A voxel model of the packaging space (the contract's volumes) with:
- **frozen solid:** the shell built before (convex or lobed form), from the same construction rules,
  voxel by voxel: its walls and end walls, bosses, flange lips, mounts, the motor flange;
- **kept clear:** the gears' cavity, the bores and the shafts, and the room the outside needs: the
  motor beyond the motor-side face, the half-shafts beyond the output's faces, a tool's access to
  every flange bolt and mount;
- **free (the design space):** the rest of the packaging space, outside the shell.
The loads are LOP-2's: each seat's force over its bore's nodes, the motor's reaction on its ring;
the mounts' holes are held. SIMP (p = 3), a density filter (radius 1.5 voxels), optimality
criteria under a mass budget. Each iteration is solved by `fe.py`'s scaled single-precision
factor, its answers refined in double (LOP-3's runs used a double factor, against the rule; fixed
for LOP-16, 22:05). The element is the hexahedron with Wilson's incompatible modes (`hex_wilson`).

The objective (the agent's formulation choice):
- `compliance`: the two cases' compliance (the usual first run);
- `tilt`: a smooth maximum (p-norm, p = 6) of every seat's tilt over its line (0.75 x the
  contract's limit for its bearing type) in both cases: the measure the contract binds on. Its
  gradient by one adjoint solve per iteration on the same factor;
- `misalignment`: the same p-norm of the grade's measure (each seat against its shaft's chord,
  plus the shaft's lean);
- `misalignment_bound`: the grade's measure as a bound problem solved by GCMMA (`mma.py`):
  minimise z subject to every seat's misalignment ratio in both cases <= z, and the mass.
The first three are updated by optimality criteria, the last by GCMMA (`solve_model` says why).
`Voxels` holds the finite elements and the design chain (filter, projection, casting filter)
with its exact derivative, which `topo_gradcheck.py` checks against finite differences.
The result is a hypothesis: the CAD, meshed and solved, is the judge (fastcae's lesson).

Run: uv run python prototypes/first_loop/topo.py <shell_stem> <objective> <budget_kg> [voxel_mm]
     [iterations]   (e.g. lobed tilt 1.0 6 40; outputs data/first_loop/topo_<...>.npz/.json/.png)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import hull_of_circles  # noqa: E402

OUT = ROOT / "data" / "first_loop"
# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))
YOUNG, POISSON, DENSITY = 69_000.0, 0.33, 2.6e-6  # MPa, -, kg/mm³
PENAL, E_MIN, FILTER, P_NORM = 3.0, 1e-6, 1.5, 6.0
# The bound formulation's adjoint solves are refined to this relative residual, the answers to
# fe.py's 1e-10: the halves joined only at the bolts on a grey start left one adjoint at 7e-8
# after 436 steps (LOP-16, 10 October 00:27), which a gradient can carry.
ADJOINT_TOL = 1e-8
# GCMMA's most inner iterations (each one more solve, no adjoints) before a step is taken anyway,
# and its test: a step is taken when every ratio there stays within PROMISE of the subproblem's
# bound (the ratios scaled so the worst is 10: 1e-4 of the worst), the mass within its budget.
# GCMMA's own test (every approximation above its function) took 2-5 inner iterations an
# iteration at 10 mm, mostly for seats far below the worst (`mma.MMA._broken`). At 6 mm and
# beta 4 an iteration with 5 took 104 s, 81 s of it in the subproblems, and the run averaged
# 73 s an iteration (10 October 03:33): 2 keeps a 200-iteration run to the night.
INNER_MOST = int(os.environ.get("LOOP_INNER", "2"))  # LOP-19: LOOP_INNER=0 takes MMA's first proposal (one analysis an iteration)
PROMISE = 1e-3
# (LOP-29, the engineer 13 October 17:45-19:24: "modes far from the gear orders - you can keep in optimization"; "we need to
# bring this in") the model's natural frequencies inside the optimisation: below MODE_LOW a voxel's mass falls as rho^6
# (Pedersen 2000), so a near-empty voxel has no local mode of its own; MODE_COUNT modes are read each analysis.
MODE_LOW = 0.1
# (LOP-29, 14 October 04:05) metal joined to nothing takes this share of its mass in the modes: the drawing drops it, and its
# near-free modes (27-331 Hz, FE's first 547-786) filled the modes read, so the gaps and the floor missed the real ones
LOOSE_MASS = float(os.environ.get("LOOP_LOOSE_MASS", "1e-6"))
# (LOP-29, the engineer 14 October 15:37: "Ok") and, with the modes read, this share of its stiffness: a stiff piece hanging
# on near-empty cubes carries nothing (the same tilt and modes) but leaves the stiffness nearly singular for the single
# factor (`baseline2_lw8`, iteration 120: a 22-cube piece, a random vector refined to 1e-10 in 16 steps with it, 4 without;
# at iteration 128 past the 60 allowed, in the modes' solve). `LOOP_LOOSE_STIFF=1` the old way.
LOOSE_STIFF = float(os.environ.get("LOOP_LOOSE_STIFF", "1e-6"))
# (LOP-30, the engineer 14 October 17:27: the optimiser in spline space) the outline field's coefficients span this many mm
# each side of zero, and its Heaviside's sharpness is SPLINE_SHARP per mm times the projection's (0.25 at the start: a soft
# field the optimiser can shape; 4 at the last sharpness 16: the outline within a quarter of a mm)
SPLINE_RANGE = 8.0
SPLINE_SHARP = 0.25
MODE_COUNT = int(os.environ.get("LOOP_MODE_COUNT", "14"))


def mode_mass(dens: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(LOP-29) Each element's share of its voxel's mass for the modes, and its slope by the density: the density itself,
    and below MODE_LOW MODE_LOW (rho / MODE_LOW)^6 (Pedersen 2000), continuous with its slope at MODE_LOW only in value."""
    r = np.maximum(dens, 0.0) / MODE_LOW
    low = dens < MODE_LOW
    return np.where(low, MODE_LOW * r**6, dens), np.where(low, 6.0 * r**5, 1.0)


def gear_orders(model: dict) -> dict:
    """(LOP-29) The gear orders the modes are kept from, by the contract's own chain, as `fe.py` computes them: each stage's
    mesh frequency at the rated speed (its pinion's teeth times its shaft's turns a second), Hz."""
    spec, chain = model["spec"], model["chain"]
    speeds = chain.speeds
    return {s.name: int(s.z_pinion.value) * speeds[s.pinion_shaft] / 60.0 for s in spec.requirement.stages}


def mode_gaps(hz: np.ndarray, d_hz: np.ndarray, orders: dict, margin: float, floor: float = 0.0,
              floor_margin: float = 0.0) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """(LOP-29) The gap round each gear order as constraints (at most 0 when held): the highest mode below the order at
    most (1 - margin) of it, the lowest above at least (1 + margin) of it; two a order, in the orders' order. A side no
    computed mode stands on (every mode above the order, or every one below it) is held (-1, no slope). Returns the values,
    their derivatives by the element densities and a note of which mode each read. With `floor` (Hz, LOP-29, the engineer 14
    October 01:17: 500), FLOOR_MODES more, last: each of the lowest FLOOR_MODES modes at least `floor` (1 + `floor_margin`),
    so a cluster of modes is raised together (one at a time, the lowest jumped 300-570 Hz between iterations)."""
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
    if floor > 0:
        lo_f = floor * (1.0 + floor_margin)
        order = np.argsort(hz)
        for j in range(FLOOR_MODES):
            if j < len(order):
                i = int(order[j])
                g.append(1.0 - hz[i] / lo_f)
                rows.append(-d_hz[i] / lo_f)
                notes.append(f"mode {j + 1} {hz[i]:.0f} Hz at least {lo_f:.0f}")
            else:
                g.append(-1.0)
                rows.append(np.zeros(d_hz.shape[1]))
                notes.append(f"mode {j + 1}: not read")
    return np.asarray(g, float), np.vstack(rows), notes
MEMBER_P = 12.0  # the greatest member's p-mean: near the worst ball's share, and smooth
# (LOP-29, 14 October 02:05) with the modes held the sharpness rises by this a step, and only while every mode limit holds:
# a doubling (2 to 4) cut a lug loose at once, beyond the reach of a sharp field's gradients
BETA_STEP_MODES = 2.0**0.5
# (LOP-29, 14 October 02:25) the first mode's floor held on each of the lowest this many modes
FLOOR_MODES = 6
# (LOP-29) `modes_tilt`: the lowest FLOOR_MODES modes' smooth minimum (KS, sharpness KS_RHO over MODE_REF Hz) raised
MODE_REF = 500.0
KS_RHO = 20.0
# When a run has settled (11 October; `solve_model`'s sharpening): the objective within a share of
# itself over a window of iterations at one sharpness. SETTLE_BETA moves on to the next sharpness,
# SETTLE_STOP ends the run at the last, the budget spent to within MASS_SPENT.
SETTLE_WINDOW, SETTLE_BETA, SETTLE_STOP, MASS_SPENT = 5, 0.005, 0.002, 0.005


def _flat(history: list[dict], window: int, share: float) -> bool:
    """The objective (each row's `bound`) moved less than `share` of itself over the last `window`
    rows."""
    if len(history) < window:
        return False
    f = [float(row["bound"]) for row in history[-window:]]
    return max(f) - min(f) <= share * abs(f[-1])


def local_ball(ijk, radius: float):
    """The free voxels' ball neighbourhoods for the greatest member: a sparse 0/1 matrix (each
    voxel, every free voxel within `radius` voxels of it, itself included) and the number of grid
    cells a whole ball holds, so that a ball reaching past the free voxels (into the cavity, the
    skin or outside) counts that part as empty."""
    from scipy.spatial import cKDTree

    tree = cKDTree(np.asarray(ijk, float))
    pairs = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    n = len(ijk)
    ball = sp.coo_matrix((np.ones(len(pairs.data)), (pairs.row, pairs.col)), shape=(n, n)).tocsr()
    # Each pair once and each voxel in its own ball, whether or not the distance matrix lists the
    # zero distances (it does: adding the identity counted every voxel twice).
    ball = ((ball + sp.eye(n, format="csr")) > 0).astype(float).tocsr()
    r = int(math.floor(radius))
    o = np.arange(-r, r + 1)
    cells = int(((o[:, None, None] ** 2 + o[None, :, None] ** 2 + o[None, None, :] ** 2) <= radius**2).sum())
    return ball, cells


def greatest_share(ball, cells: int, rho, alpha: float, p: float | None = None, fixed: np.ndarray | None = None,
                   floor: float | None = None):  # fmt: skip
    """The greatest member's constraint at the free voxels' densities `rho`: G = M / alpha - 1,
    M the density-weighted p-mean of each voxel's ball share (the metal's own balls, so the empty
    space round a sparse design dilutes nothing), with dG / d rho and M itself. `p` (MEMBER_P by
    default) sets how near the worst ball the mean reads: at 12 a few knots of solid metal where
    members cross passed beside thinner metal (12 October 15:23, sections of 28 mm); at 40 one
    knot of 100 voxels at 0.8 among 30,000 at 0.55 reads 0.69 and is held. `fixed` (LOP-30, the engineer 14 October 23:01:
    the lump rule counting the sealing land and the bolts' bosses) adds each ball's fixed metal, a constant. With `floor`
    (15 October 03:45) it is held so it can be met: each ball's placed metal against what its fixed metal leaves of alpha,
    never less than `floor` (counted outright, the land's balls read 0.70 with nothing placed and `spl4`'s members came
    off the split); away from fixed metal the rule as before."""
    p = MEMBER_P if p is None else float(p)
    scale = None
    if floor is not None and fixed is not None:
        scale = alpha / np.maximum(alpha - fixed / cells, float(floor))
        share = (ball @ rho) / cells * scale
    else:
        share = (ball @ rho + (0.0 if fixed is None else fixed)) / cells
    a = float(np.sum(rho * share**p))
    b = float(np.sum(rho))
    if a <= 0.0 or b <= 0.0:
        return -1.0, np.zeros_like(rho), 0.0
    m = (a / b) ** (1.0 / p)
    d_a = share**p + p * (ball.T @ (rho * share ** (p - 1.0) * (1.0 if scale is None else scale))) / cells
    d_m = (m / p) * (d_a / a - 1.0 / b)
    return m / alpha - 1.0, d_m / alpha, m


# The members' plan rule (LOP-23, 11 October 14:50; the engineer, 14:42: "increase the minimum gap,
# so that whatever pattern comes out comes out clean"). The casting filter makes each half's metal a
# height over its plan, so its members are walls along the pull, and their widths and the gaps
# between them are the plan's. Each column's presence P = 1 - exp(-H / PLAN_TAU), H its voxels of
# placed metal, is grown by a p-mean (PLAN_Q) over a disc of half the gap; members closer than the
# gap then merge, and the grown presence's greatest share in a disc of (width + gap) / 0.96 is held
# at most PLAN_ALPHA (`greatest_share`). Calibrated on synthetic plans at 4 mm voxels
# (`scratchpad/plan_rule_calibrate.py`), width 8 mm and gap 10 mm at 0.5: one rib 4 or 8 mm wide
# passes (0.33, 0.45), 12 mm fails (0.56); two 4 mm ribs pass 16 mm apart (0.36) and fail 12 mm
# apart (0.54); two 8 mm ribs pass 20 mm apart (0.45) and fail 16 mm apart (0.53); every crossing
# lattice (0.63-0.94) and a 24 mm pad (0.80) fail. With the gap at 16 mm, the gaps that pass are
# 24 mm (4 mm ribs) and 32 mm (8 mm ribs). The frozen skin, flange and mounts are not counted.
PLAN_TAU, PLAN_Q, PLAN_ALPHA = 0.5, 8.0, 0.5


def _disc(pts: np.ndarray, radius: float):
    """Each plan column's neighbours within `radius` voxels (itself included) as a sparse 0/1
    matrix, and the cells a whole disc holds."""
    from scipy.spatial import cKDTree

    tree = cKDTree(pts)
    pairs = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    n = len(pts)
    m = sp.coo_matrix((np.ones(len(pairs.data)), (pairs.row, pairs.col)), shape=(n, n)).tocsr()
    m = ((m + sp.eye(n, format="csr")) > 0).astype(float).tocsr()
    r = int(math.floor(radius))
    o = np.arange(-r, r + 1)
    return m, int(((o[:, None] ** 2 + o[None, :] ** 2) <= radius**2).sum())


def plan_rule(ijk_free: np.ndarray, k_split: int, h: float, width_mm: float, gap_mm: float) -> dict:
    """The members' plan rule's fixed parts: the free voxels' columns, each half its own (C, columns
    by free voxels), the discs of the growth (D) and of the share (W)."""
    ijk = np.asarray(ijk_free, int)
    half = (ijk[:, 2] >= k_split).astype(np.int64)
    key = (half * 1_000_003 + ijk[:, 0]) * 1_000_003 + ijk[:, 1]
    cols, col_of = np.unique(key, return_inverse=True)
    c_mat = sp.csr_matrix((np.ones(len(col_of)), (col_of, np.arange(len(col_of)))), shape=(len(cols), len(col_of)))
    ci = (cols // 1_000_003) % 1_000_003
    cj = cols % 1_000_003
    ch = cols // (1_000_003 * 1_000_003)
    pts = np.column_stack([ci + 10_000.0 * ch, cj]).astype(float)  # the halves far apart: no disc spans both
    d_mat, n_d = _disc(pts, gap_mm / 2.0 / h)
    w_mat, n_w = _disc(pts, (width_mm + gap_mm) / 0.96 / h)
    return {"C": c_mat, "D": d_mat, "n_d": n_d, "W": w_mat, "n_w": n_w, "columns": len(cols)}


def perimeter_pairs(height: dict, n_free: int) -> dict:
    """The height field's outline in plan (LOP-26, 12 October 14:46: dashes and worms have many ends and a long outline;
    a limit on it, as Haber, Jog & Bendsøe 1996 limit the perimeter, leaves fewer, longer, continuous members): every
    pair of plan-neighbouring columns of one layer, each column by its base voxel (the free voxel at its start: a column
    holds metal when its base does). The outline is h times the sum over pairs of the smoothed |difference| of their bases'
    densities; a column next to frozen metal or outside the field pays nothing there, so a member ending on a boss or the
    shell costs no outline."""
    col, pos, pts, layer = height["col"], height["pos"], height["pts"], height["layer"]
    base = np.full(int(col.max()) + 1, -1, np.int64)
    first = np.flatnonzero(pos == 0)
    base[col[first]] = first
    key = {(int(layer[c]), int(pts[c, 0]), int(pts[c, 1])): c for c in range(len(pts)) if base[c] >= 0}
    a, b = [], []
    for (lay, i, j), c in key.items():
        for di, dj in ((1, 0), (0, 1)):
            c2 = key.get((lay, i + di, j + dj))
            if c2 is not None:
                a.append(base[c])
                b.append(base[c2])
    return {"a": np.asarray(a, np.int64), "b": np.asarray(b, np.int64), "n_free": n_free, "pairs": len(a)}


def perimeter_value(pairs: dict, rho_free: np.ndarray, h: float, limit_mm: float, eps: float = 0.05):
    """The outline constraint at the free voxels' densities: G = P / limit - 1, P the outline in mm, with dG / d rho and P."""
    d = rho_free[pairs["a"]] - rho_free[pairs["b"]]
    s = np.sqrt(d * d + eps * eps)
    p = h * float(np.sum(s - eps))
    grad = np.zeros(pairs["n_free"])
    np.add.at(grad, pairs["a"], h * d / s)
    np.add.at(grad, pairs["b"], -h * d / s)
    return p / limit_mm - 1.0, grad / limit_mm, p


# The semantic rules (LOP-28; the engineer, 13 October 00:03-00:21, with a reviewer's notes: "the optimiser understands
# structural performance, but it does not understand which shapes should remain geometrically calm"): each region of the
# design space its own rule. A broad panel may slope and change its thickness but must not ripple: the bending of the
# columns' continuous heights, s_xx² + s_yy² + 2 s_xy² (the full second derivative: a plane costs nothing, a saddle does,
# which the Laplacian alone would miss), its weighted mean over the region at most a bound (`bending_operator`,
# `bending_value`). A bracket keeps its job: the metal round each mount at least a floor (`solve_model`'s `brackets`).
BEND_SOFT = 4.0  # 1/voxel: a column's height read through a soft cap at its own length (a height past it places no metal)


def bending_operator(height: dict, ijk_free: np.ndarray, weights: np.ndarray) -> dict:
    """The second differences of the columns' heights at every column some region weighs whose eight plan neighbours stand
    in its layer on its own base (its first free voxel's level, so no room's edge, ring or step is read as bending): s_xx,
    s_yy and s_xy as sparse rows over the columns, in voxels of height per voxel of plan squared; each region's weights at
    those centres. `weights` is (regions, columns), each row in [0, 1] with its fade."""
    pts = np.asarray(height["pts"]).astype(np.int64)
    layer = np.asarray(height["layer"], np.int64)
    col, pos = height["col"], height["pos"]
    n_cols = int(height["n_cols"])
    k0 = np.full(n_cols, -1, np.int64)
    first = pos == 0
    k0[col[first]] = np.asarray(ijk_free)[first, 2]
    code = (layer * 100_000 + pts[:, 0]) * 100_000 + pts[:, 1]
    order = np.argsort(code)
    code_sorted = code[order]

    def neighbour(di: int, dj: int):
        want = (layer * 100_000 + pts[:, 0] + di) * 100_000 + pts[:, 1] + dj
        k = np.clip(np.searchsorted(code_sorted, want), 0, n_cols - 1)
        found = code_sorted[k] == want
        idx = np.where(found, order[k], -1)
        return idx, found & (k0[np.maximum(idx, 0)] == k0)

    near = {(di, dj): neighbour(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0)}
    weights = np.atleast_2d(np.asarray(weights, float))
    valid = np.all([ok for _, ok in near.values()], axis=0) & (weights.max(axis=0) > 0) & (k0 >= 0)
    c = np.flatnonzero(valid)
    r = np.arange(len(c))

    def rows(entries) -> sp.csr_matrix:
        ii, jj, vv = [], [], []
        for (di, dj), v in entries:
            ii.append(r)
            jj.append(c if (di, dj) == (0, 0) else near[(di, dj)][0][c])
            vv.append(np.full(len(c), v))
        return sp.csr_matrix((np.concatenate(vv), (np.concatenate(ii), np.concatenate(jj))), shape=(len(c), n_cols))

    w = weights[:, c]
    return {"dxx": rows((((1, 0), 1.0), ((0, 0), -2.0), ((-1, 0), 1.0))), "dyy": rows((((0, 1), 1.0), ((0, 0), -2.0), ((0, -1), 1.0))),
            "dxy": rows((((1, 1), 0.25), ((1, -1), -0.25), ((-1, 1), -0.25), ((-1, -1), 0.25))), "w": w,
            "wsum": np.maximum(w.sum(axis=1), 1e-12), "centres": c, "length": np.bincount(col, minlength=n_cols).astype(float)}  # fmt: skip


def bending_value(op: dict, t: np.ndarray, kinds=None):
    """Each region's weighted mean bending at the columns' heights t (voxels), and dB/dt (regions, columns). Each height is
    read through a soft cap at its column's length (`BEND_SOFT`), so the bending is the drawn surface's. Two kinds:
    - 0, **the bending:** B = sum w (s_xx² + s_yy² + 2 s_xy²) / sum w, in voxels^-2 (a curvature in 1/mm is s / h): a calm
      patch, sloping freely, with no ribs, steps or ripples;
    - 1, **the double curvature** (LOP-28, 13 October 00:27): B = sum w (s_xx s_yy - s_xy²)² / sum w, in voxels^-4, the
      Hessian's determinant (the surface's Gaussian curvature while its slopes are small) squared: zero on every surface
      that curves one way at a time (planes, slopes, straight and curved ribs, round collars: what production castings are
      built from), large on bumps, dents, saddles and wrinkles (what makes a field look organic)."""
    kinds = np.zeros(len(op["wsum"]), int) if kinds is None else np.asarray(kinds, int)
    z = BEND_SOFT * (op["length"] - t)
    t_eff = op["length"] - np.logaddexp(0.0, z) / BEND_SOFT
    d_eff = 1.0 / (1.0 + np.exp(-z))  # d t_eff / d t
    sxx, syy, sxy = op["dxx"] @ t_eff, op["dyy"] @ t_eff, op["dxy"] @ t_eff
    det = sxx * syy - sxy * sxy
    w, wsum = op["w"], op["wsum"]
    b, rows = np.zeros(len(wsum)), []
    for k in range(len(wsum)):
        if kinds[k] == 1:
            b[k] = float(w[k] @ (det * det)) / wsum[k]
            wd = w[k] * det
            rows.append((2.0 / wsum[k]) * (op["dxx"].T @ (wd * syy) + op["dyy"].T @ (wd * sxx) - 2.0 * (op["dxy"].T @ (wd * sxy))))
        else:
            b[k] = float(w[k] @ (sxx * sxx + syy * syy + 2.0 * sxy * sxy)) / wsum[k]
            rows.append((2.0 / wsum[k]) * (op["dxx"].T @ (w[k] * sxx) + op["dyy"].T @ (w[k] * syy) + 2.0 * (op["dxy"].T @ (w[k] * sxy))))
    return b, np.vstack(rows) * d_eff[None, :]


def bending_rms(b: np.ndarray, kinds, h: float) -> np.ndarray:
    """A region's measure as a curvature in 1/m: the bending's RMS, or the double curvature's RMS taken to the quarter power."""
    kinds = np.asarray(kinds, int)
    return np.where(kinds == 1, np.maximum(b, 0.0) ** 0.25, np.sqrt(np.maximum(b, 0.0))) * 1000.0 / h


def bending_bound(rms_per_m, kinds, h: float) -> np.ndarray:
    """The bounds on B (voxel units) from curvatures in 1/m: (r h / 1000)² for the bending, to the fourth for the double curvature."""
    r = np.asarray(rms_per_m, float) * h / 1000.0
    return np.where(np.asarray(kinds, int) == 1, r**4, r**2)


def plan_share(rule: dict, rho_free: np.ndarray, alpha: float = PLAN_ALPHA):
    """The plan rule's constraint at the free voxels' densities: G = M / alpha - 1, M the grown
    presence's greatest share; with dG / d rho_free and M. With `rule["mask"]` (LOP-28, the empty start) only the masked
    voxels count: the metal beyond each wall's least height, so a bare wall is no member."""
    mask = rule.get("mask")
    if mask is not None:
        g, grad, m = plan_share({k: v for k, v in rule.items() if k != "mask"}, rho_free * mask, alpha)
        return g, grad * mask, m
    hgt = rule["C"] @ rho_free
    e = np.exp(-hgt / PLAN_TAU)
    p = 1.0 - e
    a = (rule["D"] @ p**PLAN_Q) / rule["n_d"]
    grown = np.maximum(a, 1e-300) ** (1.0 / PLAN_Q)
    g, d_grown, m = greatest_share(rule["W"], rule["n_w"], grown, alpha)
    d_a = d_grown * (1.0 / PLAN_Q) * np.maximum(a, 1e-300) ** (1.0 / PLAN_Q - 1.0)
    d_p = (rule["D"].T @ (d_a / rule["n_d"])) * PLAN_Q * p ** (PLAN_Q - 1.0)
    d_h = d_p * e / PLAN_TAU
    return g, rule["C"].T @ d_h, m


def feature_map(feat: dict, info: dict, pts: np.ndarray, layer: np.ndarray, lo, h: float, fmat, n_cols: int):
    """The height field's map M with one region given to features (LOP-24, the bore experiment): `feat` =
    {"half": "motor_side" | "cover", "bore": <shaft>, "radius": <mm from its axis>, "features": [
    {"name", "kind": "ring", "r_in", "r_out"} | {"name", "kind": "rib", "angle" (degrees) | "to" [x, y], "r0", "r1", "width"}
    | {"name", "kind": "sector", "r_in", "r_out", "a0", "a1"}, ...]} in mm round the bore's axis. The region: that half's
    columns within `radius` of the axis and nearer its boss's edge than any other bore's of the half. A region column
    covered by a feature (the first in the list that covers it) takes its height from the feature's
    parameters (a ring and a sector one, a rib two, root and tip, linear along it); one covered by none
    holds no metal; every other column is free, the plan filter mixing free columns only. A feature
    marked `"free": true` is a design-space volume instead: its columns stay free, each its own
    variable (the design space iterated in regular volumes inside the region). Returns (M,
    the design variables' count, the features' record: each one's parameters' indices and columns)."""
    side = "+z" if feat["half"] == "cover" else "-z"
    in_half = (layer // 10000) == (1 if feat["half"] == "cover" else 0)
    bores = [b for b in info["bearings"] if b["side"] == side]
    me = next(b for b in bores if b["shaft"] == feat["bore"])
    cx = lo[0] + h * (pts[:, 0] + 0.5)
    cy = lo[1] + h * (pts[:, 1] + 0.5)
    ax, ay = me["axis"]
    r = np.hypot(cx - ax, cy - ay)
    ang = np.degrees(np.arctan2(cy - ay, cx - ax))
    nearest = np.ones(n_cols, dtype=bool)
    for b in bores:  # nearer this boss's edge than any other's: a larger neighbour keeps its own boss
        if b is not me:
            nearest &= r - me["boss_r"] <= np.hypot(cx - b["axis"][0], cy - b["axis"][1]) - b["boss_r"]
    region = in_half & (r <= float(feat["radius"])) & nearest
    owner = np.full(n_cols, -1)
    opened = np.zeros(n_cols, dtype=bool)  # the region's free volumes: a design space inside it ("free": true)
    w_rows, w_cols, w_vals = [], [], []
    record, n_par = [], 0
    for k, f in enumerate(feat["features"]):
        params = []
        if f["kind"] in ("ring", "sector"):
            cov = region & (r >= f["r_in"]) & (r <= f["r_out"])
            if f["kind"] == "sector":
                d = (ang - f["a0"]) % 360.0
                cov &= d <= (f["a1"] - f["a0"]) % 360.0
            cov &= owner < 0
            idx = np.flatnonzero(cov)
            if not f.get("free"):
                w_rows += idx.tolist(); w_cols += [n_par] * len(idx); w_vals += [1.0] * len(idx)
                params = [n_par]
                n_par += 1
        elif f["kind"] == "rib":
            a = np.radians(f["angle"]) if "angle" in f else np.arctan2(f["to"][1] - ay, f["to"][0] - ax)
            u = np.array([np.cos(a), np.sin(a)])
            s = ((cx - ax) * u[0] + (cy - ay) * u[1] - f["r0"]) / max(f["r1"] - f["r0"], 1e-9)
            off = np.abs(-(cx - ax) * u[1] + (cy - ay) * u[0])
            cov = region & (s >= 0.0) & (s <= 1.0) & (off <= 0.5 * f["width"]) & (owner < 0)
            idx = np.flatnonzero(cov)
            if not f.get("free"):
                sv = np.clip(s[idx], 0.0, 1.0)
                w_rows += idx.tolist() * 2; w_cols += [n_par] * len(idx) + [n_par + 1] * len(idx)
                w_vals += (1.0 - sv).tolist() + sv.tolist()
                params = [n_par, n_par + 1]
                n_par += 2
        else:
            raise ValueError(f"feature kind {f['kind']!r}: ring, rib or sector")
        owner[idx] = k
        if f.get("free"):  # a free volume: each of its columns its own variable, as outside the region
            opened[idx] = True
        record.append({"name": f["name"], "kind": f["kind"], "params": params, "columns": len(idx), "free": bool(f.get("free"))})
    free = np.flatnonzero(~region | opened)
    ff = fmat[free][:, free].tocsr()
    fs_f = np.asarray(ff.sum(axis=1)).ravel()
    ffn = (sp.diags(1.0 / fs_f) @ ff).tocoo()
    n_free = len(free)
    rows = np.concatenate([free[ffn.row], np.asarray(w_rows, dtype=np.int64)])
    cols = np.concatenate([ffn.col, n_free + np.asarray(w_cols, dtype=np.int64)])
    vals = np.concatenate([ffn.data, np.asarray(w_vals, float)])
    m = sp.csr_matrix((vals, (rows, cols)), shape=(n_cols, n_free + n_par))
    for rec in record:
        rec["params"] = [n_free + p for p in rec["params"]]
    say(f"features round the {feat['bore']} bore ({feat['half']}): {int(region.sum()):,} columns in the region, "
        f"{int(((owner >= 0) & ~opened).sum()):,} under {sum(not x['free'] for x in record)} features ({n_par} parameters), "
        f"{int(opened.sum()):,} in {sum(x['free'] for x in record)} free volumes, the rest of the region empty; "
        f"{n_free:,} free columns in all")  # fmt: skip
    return m, n_free + n_par, {"spec": feat, "features": record, "n_free": n_free, "owner": owner, "region": region}


def volume_map(path: str, fmat, n_cols: int):
    """The height field's map M with the design space divided into volumes (LOP-24, approach 1 as the engineer
    meant it, 12 October 01:23-01:34: the design space sectioned cleanly, each section given a form of its own
    so that metal cannot smear across it): every column in a volume (`<path>`: `vol_of_col`, -1 for a column
    left free; `law` a volume, 0 one height for the whole volume, 1 a height linear along it, from a root to a
    tip; `s_of_col`, a column's place along its volume, 0 to 1) takes its height from the volume's parameters;
    a free column stays its own variable, the plan filter mixing free columns only. Returns (M, the design
    variables' count, the record)."""
    p = Path(path)
    p = p if p.is_absolute() or p.exists() else OUT / p
    z = np.load(p)
    vol, law, s = np.asarray(z["vol_of_col"], np.int64), np.asarray(z["law"], np.int64), np.asarray(z["s_of_col"], float)
    if len(vol) != n_cols:
        raise ValueError(f"{p.name}: {len(vol):,} columns, the model {n_cols:,}")
    count = np.where(law == 1, 2, 1)
    first = np.r_[0, np.cumsum(count)[:-1]]
    n_par = int(count.sum())
    # -1 a free column; -2 a column held empty (no metal: a form with nothing else, 12 October 02:27: with only -1 the
    # columns no rib or ring covered stayed free, and the optimiser painted them)
    free = np.flatnonzero(vol == -1)
    n_free = len(free)
    rows, cols, vals = [], [], []
    if n_free:
        ff = fmat[free][:, free].tocsr()
        ffn = (sp.diags(1.0 / np.asarray(ff.sum(axis=1)).ravel()) @ ff).tocoo()
        rows, cols, vals = [free[ffn.row]], [ffn.col], [ffn.data]
    on = np.flatnonzero(vol >= 0)
    v = vol[on]
    const = law[v] == 0
    rows += [on[const], on[~const], on[~const]]
    cols += [n_free + first[v[const]], n_free + first[v[~const]], n_free + first[v[~const]] + 1]
    vals += [np.ones(int(const.sum())), 1.0 - s[on[~const]], s[on[~const]]]
    m = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n_cols, n_free + n_par))
    say(f"the design space in {len(law)} volumes ({int((law == 1).sum())} with a root and a tip height): {len(on):,} columns, "
        f"{n_par} parameters; {n_free:,} columns free, {int((vol == -2).sum()):,} held empty")  # fmt: skip
    return m, n_free + n_par, {"volumes": int(len(law)), "params": n_par, "n_free": n_free, "vol_of_col": vol, "first": first}


def height_columns(kind: np.ndarray, n: np.ndarray, k_split: int, elem: np.ndarray, free_e: np.ndarray):
    """The height field's columns (LOP-23, 11 October 15:50): each run of modelled voxels along the
    pull in each half (from the split, or from the wall it stands on, outward), and each free
    voxel's place in its run's free voxels counted from the run's start nearest the split. Returns
    (each free voxel's column, its place, each column's plan cell (i, j), each column's layer: its
    half and its run's index, so the plan filter mixes only columns of one layer)."""
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
        key = ((half * 10_000 + np.broadcast_to(run, a.shape)) * 100_000 + ii[:, :, None]) * 100_000 + jj[:, :, None]
        sel = fre
        col_key[idx[sel]] = key[sel]
        place[idx[sel]] = pos[sel]
    flat_free = elem[free_e]
    keys, col = np.unique(col_key[flat_free], return_inverse=True)
    ci, cj = (keys // 100_000) % 100_000, keys % 100_000
    layer = keys // (100_000 * 100_000)
    return col, place[flat_free].astype(float), np.column_stack([ci, cj]).astype(float), layer


def least_width_blocks(pts: np.ndarray, layer: np.ndarray, base: np.ndarray, w: int, disc: bool = False,
                       solid: set | None = None) -> dict:
    """(LOP-29, 14 October; the engineer, 13:42: "lets try a") The least member width in plan's blocks: every w x w square
    of columns standing on one level of one half (their first free voxel at one place along the pull, so their heights
    are measured from one base). The fixed parts are no columns, so they count toward no member's width. Returns each
    block's columns (`blocks`, n_blocks x its size), each column's blocks (`member`, n_cols x its size, -1 where none) and
    how many columns lie in no block (`alone`: they can hold no member). With `disc` (LOP-30, 14 October 23:20) each block
    is the disc w across inscribed in the square, so a member at 45 degrees needs the same width as one along an axis (a
    square needs it √2 wider there).

    With `solid` (LOP-30, 15 October 05:05; for the least gap), a set of (half, i, j) places of fixed metal: a block may
    hold such places where its level has no column, each one virtual column, index n_cols (`virtual`), which the caller
    gives the metal's value; `member` then has a last row for it, with no blocks. So a slot between a member and the shell
    closes as one between two members does. Every block holding at least one column is found, whatever lies at its
    corner."""
    half = np.asarray(layer, np.int64) // 10_000
    ii, jj = np.asarray(pts[:, 0], np.int64), np.asarray(pts[:, 1], np.int64)
    base = np.asarray(base, np.int64)
    key = {(int(a), int(b), int(c), int(d)): k for k, (a, b, c, d) in enumerate(zip(half, base, ii, jj, strict=True))}
    if len(key) != len(ii):
        raise ValueError("two columns on one level share a plan cell")
    mid = 0.5 * (w - 1)
    offsets = [(a, b) for a in range(w) for b in range(w) if not disc or (a - mid) ** 2 + (b - mid) ** 2 <= (0.5 * w) ** 2]
    found = []
    n_cols = len(ii)
    if solid is None:
        for c in range(n_cols):  # each block named by its corner column
            cols = [key.get((int(half[c]), int(base[c]), int(ii[c]) + a, int(jj[c]) + b)) for a, b in offsets]
            if all(k is not None for k in cols):
                found.append(cols)
    else:
        corners = {(int(half[c]), int(base[c]), int(ii[c]) - a, int(jj[c]) - b) for c in range(n_cols) for a in range(w) for b in range(w)}
        for hf_, lv_, ci_, cj_ in sorted(corners):
            cols = []
            for a, b in offsets:
                k = key.get((hf_, lv_, ci_ + a, cj_ + b))
                if k is None and (hf_, ci_ + a, cj_ + b) in solid:
                    k = n_cols
                if k is None:
                    break
                cols.append(k)
            if len(cols) == len(offsets) and min(cols) < n_cols:
                found.append(cols)
    q = len(offsets)
    blocks = np.asarray(found, np.int64).reshape(-1, q)
    member = np.full((n_cols + (solid is not None), q), -1, np.int64)
    fill = np.zeros(n_cols, np.int64)
    for bi, cols in enumerate(blocks):
        for k in cols:
            if k < n_cols:
                member[k, fill[k]] = bi
                fill[k] += 1
    out = {"blocks": blocks, "member": member, "w": int(w), "alone": int((fill == 0).sum())}
    if solid is not None:
        out["virtual"] = n_cols
    return out


def open_heights(op: dict, t0: np.ndarray, k: float):
    """(LOP-29) The columns' heights opened to the least width in plan (`least_width_blocks`): each block's soft minimum
    of its columns' heights, then each column's soft maximum over the blocks it is in (Sigmund 2007's opening: erode,
    then dilate), both by log-sum-exp at sharpness k a voxel. Where a block's columns are level, a column keeps its
    height exactly; a member narrower than a block weighs nothing; a column in no block holds nothing. Returns the
    opened heights and their Jacobian by t0 (sparse; each row sums to 1)."""
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
    a_mat = sp.csr_matrix((a.ravel(), (np.repeat(np.arange(len(blocks)), q), blocks.ravel())), shape=(len(blocks), n_cols))
    return t_open, (s_mat @ a_mat).tocsr()


def _open_bias(op: dict, k: float) -> np.ndarray:
    """(LOP-30) The soft opening's shortfall on a level field (`open_heights`): a block's soft minimum reads log(q) / k
    under its level and a point's soft maximum log(n) / k over its blocks', so a point in n < q blocks (the design
    space's edges) reads log(q / n) / k low. Added back, a level field opens to itself everywhere."""
    nb = (op["member"] >= 0).sum(axis=1)
    q = op["blocks"].shape[1]
    return np.where(nb > 0, np.log(q / np.maximum(nb, 1)) / k, 0.0)


def _rowwise_kron(a, b, n_b: int) -> sp.csr_matrix:
    """Each row's outer product of two sparse matrices' rows (the same rows), flattened as a's column x n_b + b's."""
    a, b = sp.csr_matrix(a), sp.csr_matrix(b)
    na, nb = np.diff(a.indptr), np.diff(b.indptr)
    rows_a = np.repeat(np.arange(a.shape[0]), na)
    reps = nb[rows_a]
    ia = np.repeat(np.arange(a.nnz), reps)
    within = np.arange(len(ia)) - np.repeat(np.cumsum(reps) - reps, reps)
    ib = np.repeat(b.indptr[rows_a], reps) + within
    return sp.csr_matrix((a.data[ia] * b.data[ib], (rows_a[ia], a.indices[ia] * n_b + b.indices[ib])), shape=(a.shape[0], a.shape[1] * n_b))


def bspline_basis(xy: np.ndarray, spacing: float, derivs: bool = False) -> dict:
    """(LOP-30) The tensor-product cubic B-spline basis of a uniform knot grid `spacing` mm apart over the plan points `xy`
    (mm): each point reads 16 coefficients, with weights that are a partition of unity (coefficients in [0, 1] give
    values in [0, 1]). Returns the points x coefficients matrix (`B`, only the coefficients some point reads), and the
    grid (`origin`, `shape`, `kept`: each kept coefficient's index in the full grid) to evaluate the field anywhere. With
    `derivs`, the field's slopes along x and y too (`Dx`, `Dy`, per mm; on uniform knots d B3_i / dx = (B2_i - B2_i+1) /
    spacing), on the same kept coefficients."""
    from scipy.interpolate import BSpline

    xy = np.asarray(xy, float)
    origin = xy.min(axis=0)
    mats, dmats, shape, knots = [], [], [], []
    for a in range(2):
        m = max(1, int(np.ceil((xy[:, a].max() - origin[a]) / spacing + 1e-9)))
        t = origin[a] + spacing * np.arange(-3, m + 4)
        xa = np.clip(xy[:, a], t[3], t[m + 3])
        mats.append(BSpline.design_matrix(xa, t, 3).tocsr())
        if derivs:
            d2 = BSpline.design_matrix(xa, t, 2).tocsc()
            dmats.append(((d2[:, :-1] - d2[:, 1:]) / spacing).tocsr())
        shape.append(m + 3)
        knots.append(t)
    bx, by = mats
    full = _rowwise_kron(bx, by, shape[1])  # each point's row: the outer product of its two axes' rows
    kept = np.flatnonzero(np.asarray((full != 0).sum(axis=0)).ravel())
    out = {"B": full[:, kept].tocsr(), "origin": origin, "spacing": float(spacing), "shape": tuple(shape), "kept": kept,
           "knots": knots}  # fmt: skip
    if derivs:  # a coefficient no point reads is no design variable: the field is the kept ones' sum, and so its slope
        out["Dx"] = _rowwise_kron(dmats[0], by, shape[1])[:, kept].tocsr()
        out["Dy"] = _rowwise_kron(bx, dmats[1], shape[1])[:, kept].tocsr()
    return out


SPLINE_SUB = 2  # (LOP-30, 14 October 19:15) the outline field read at SPLINE_SUB x SPLINE_SUB points a cube, h / SPLINE_SUB apart
SPLINE_OUTLINE_SOFT = 1.0  # mm of the outline field over which its length's soft edge rises (`Voxels.spline_outline`)
SPLINE_SIZES_BETA = 8.0  # (LOP-30) the least sharpness at which the least width and gap are measured (`Voxels.spline_sizes`)
CAP_FREE = 1.0e3  # (LOP-30) the section window's cap (voxels) where it does not apply: far above any column
LEVEL_SMOOTH_MM = 8.0  # (LOP-30) the radius over which the window's caps' reference level is smoothed (`spline_setup`)
# (LOP-30, the engineer 14 October 20:34: "Start with A", the section rule) the outline field's distance inside its zero
# line is its value over its slope, the slope floored at this (per mm) where the field is flat; and below this share of
# the round's radius from the outline the round continues as its tangent, so its slope stays finite (`section_drop`)
SPLINE_SLOPE_FLOOR = 0.1
SPLINE_ROUND_TIP = 1.0 / 16.0
# (LOP-30, the engineer 14 October 22:43-23:01: production-quality members in the field) the smooth top's least member
# (a column holds at least the least member: `least + softplus(E - level - least)`) and the section window's smooth
# minimum, their sharpness a voxel; the round's distance inside the outline as a soft minimum of the distances to the
# points outside it on the same level (`spline_setup`'s `dist`), over this many mm and within this radius
TOP_SHARP = 2.0
CAP_SHARP = 2.0
DIST_EPS = 0.5
DIST_R = 6.0


def section_drop(a: np.ndarray, r: float):
    """(LOP-30, the section rule) How far a member's free end stands back (mm) at a point `a` mm inside its outline: a
    quarter circle of radius r, nothing from r inside, r at the outline, which rounds the edge where the member's side
    meets its free end (the top of a rib on a wall, the far edge of an arm hanging from the split). Below r / 16 inside
    it continues as its tangent (the circle's slope is infinite at the side). Returns the drop and its slope by a."""
    a0 = SPLINE_ROUND_TIP * r
    ab = np.clip(a, a0, r)
    root = np.sqrt(ab * (2.0 * r - ab))
    drop = r - root
    slope = -(r - ab) / root
    low = a < a0
    return np.where(low, drop + slope * (a - a0), drop), np.where(a >= r, 0.0, slope)


def spline_setup(spec: dict, kind: np.ndarray, n, k_split: int, pts: np.ndarray, layer: np.ndarray, base: np.ndarray,
                 lo, h: float, least_vox: float, least_width_mm: float, col_len: np.ndarray | None = None,
                 window_free: np.ndarray | None = None, window_bosses: np.ndarray | None = None, bosses_wall_only: bool = False) -> dict:  # fmt: skip
    """(LOP-30) The spline map's fields over the height field's columns: per half an outline field (`spec["phi_mm"]`
    knots) and two height fields (`spec["h_mm"]` knots), one for the columns standing on the split (every voxel from the
    split to their first free one modelled: the flange's, the mounts' and the side walls' members) and one for those
    standing on a wall past the inside (the end walls' members), whose bases differ by the inside's depth.

    The outline field is read at SPLINE_SUB x SPLINE_SUB points in each cube, h / SPLINE_SUB apart (the drawing's own
    grid): a cube's share in plan is the share of its points where the field is positive, so the optimiser and the
    drawing see one smooth outline (read at the cubes' centres alone, a member the smooth outline drew 4 mm wide counted
    as two whole cubes, 8 mm: baseline2_spl's blades). On those points the field is closed to the least gap
    (`spec["gap_mm"]`: no hole or slot narrower) and opened to the least width (no metal narrower), each over blocks of
    points on one level (`least_width_blocks`); the outline's length is read on them too (`Voxels.spline_outline`). Each
    column reads the height fields at its centre. With the section rule (`spec["round_mm"]`, the engineer 14 October
    20:34) each point's member stands back at its free end by `section_drop` of its distance inside the outline, so a
    member's free edges are rounded; the outline's slopes at the points (`Dx`, `Dy`) give that distance."""
    grid = np.asarray(kind).reshape(tuple(n))
    half = np.asarray(layer, np.int64) // 10_000
    ii, jj = pts[:, 0].astype(int), pts[:, 1].astype(int)
    off = np.concatenate([np.zeros(tuple(n[:2]) + (1,), np.int64), np.cumsum(grid < 0, axis=2)], axis=2)  # unmodelled below k
    k0 = np.where(half == 1, k_split, base + 1)
    k1 = np.where(half == 1, base, k_split)
    on_split = (off[ii, jj, np.maximum(k1, k0)] - off[ii, jj, k0]) == 0
    xy = np.asarray(lo, float)[:2] + h * (pts + 0.5)
    q = SPLINE_SUB
    sa, sb = (v.ravel() for v in np.meshgrid(np.arange(q), np.arange(q), indexing="ij"))
    sub_col = np.repeat(np.arange(len(pts)), q * q)
    sub_ij = np.column_stack([q * ii[sub_col] + np.tile(sa, len(pts)), q * jj[sub_col] + np.tile(sb, len(pts))])
    sub_xy = np.asarray(lo, float)[:2] + (h / q) * (sub_ij + 0.5)
    sub_half, sub_layer, sub_base = half[sub_col], np.asarray(layer)[sub_col], base[sub_col]
    # (LOP-30, 15 October 00:18; the engineer: "Ok" to fixing it) with one smooth top (F1) a member's free end is one
    # surface across its columns' levels, so its plan rules (the least width and gap, the window, the round's distance, the
    # outline's neighbours) see it whole across the steps of the walls, the seats' rings and the land: the points grouped
    # by their run along the pull and their family, not by their level. By level, a strip of one level under 8 mm wide (a
    # seat's 4 mm ring) held no metal and cut every rib reaching the boss (`level_strips_probe.py`: 3,237 such points
    # against 2,009, the rings gone)
    if spec.get("top"):
        sub_lev = (np.asarray(layer, np.int64) % 10_000)[sub_col] * 2 + on_split[sub_col].astype(np.int64)
    else:
        sub_lev = sub_base
    avg = sp.csr_matrix((np.full(len(sub_col), 1.0 / (q * q)), (sub_col, np.arange(len(sub_col)))), shape=(len(pts), len(sub_col)))
    fields, b_phi, b_h, d_phi_x, d_phi_y = [], [], [], [], []
    n_phi = n_h = 0
    rnd = float(spec.get("round_mm") or 0.0)  # the section rule's round (`section_drop`): the outline's slopes are needed
    for hf_ in (0, 1):
        sel_s = np.flatnonzero(sub_half == hf_)
        if not len(sel_s):
            continue
        basis = bspline_basis(sub_xy[sel_s], float(spec["phi_mm"]), derivs=rnd > 0)
        fields.append({"kind": "outline", "half": hf_, "offset": n_phi, "rows": sel_s, **{k: basis[k] for k in ("origin", "spacing", "shape", "kept")}})
        b_phi.append((sel_s, basis["B"], n_phi))
        if rnd > 0:
            d_phi_x.append((sel_s, basis["Dx"], n_phi))
            d_phi_y.append((sel_s, basis["Dy"], n_phi))
        n_phi += basis["B"].shape[1]
        for fam, mask in (("split", on_split), ("wall", ~on_split)):
            sel_f = np.flatnonzero((half == hf_) & mask)
            if not len(sel_f):
                continue
            basis = bspline_basis(xy[sel_f], float(spec["h_mm"]))
            fields.append({"kind": "height", "half": hf_, "family": fam, "offset": n_h, "rows": sel_f,
                           **{k: basis[k] for k in ("origin", "spacing", "shape", "kept")}})  # fmt: skip
            b_h.append((sel_f, basis["B"], n_h))
            n_h += basis["B"].shape[1]

    def assemble(parts: list, n_coef: int, n_rows: int) -> sp.csr_matrix:
        r_, c_, v_ = [], [], []
        for sel, b, offset in parts:
            coo = b.tocoo()
            r_.append(sel[coo.row])
            c_.append(coo.col + offset)
            v_.append(coo.data)
        return sp.csr_matrix((np.concatenate(v_), (np.concatenate(r_), np.concatenate(c_))), shape=(n_rows, n_coef))

    # each point's neighbours along +x and +y on its own level (none: -1), for the outline's length
    key = {(int(sub_half[s]), int(sub_lev[s]), int(sub_ij[s, 0]), int(sub_ij[s, 1])): s for s in range(len(sub_col))}
    nb_x = np.array([key.get((int(sub_half[s]), int(sub_lev[s]), int(sub_ij[s, 0]) + 1, int(sub_ij[s, 1])), -1) for s in range(len(sub_col))])
    nb_y = np.array([key.get((int(sub_half[s]), int(sub_lev[s]), int(sub_ij[s, 0]), int(sub_ij[s, 1]) + 1), -1) for s in range(len(sub_col))])
    out = {"B_phi": assemble(b_phi, n_phi, len(sub_col)), "B_h": assemble(b_h, n_h, len(pts)), "n_phi": n_phi, "n_h": n_h,
           "n_design": n_phi + n_h, "range": SPLINE_RANGE, "least": float(least_vox), "fields": fields, "on_split": on_split,
           "half": half, "base": base, "avg": avg, "sub_ij": sub_ij, "sub_col": sub_col, "sub_half": sub_half, "nb_x": nb_x,
           "nb_y": nb_y, "q": q, "h": float(h), "open": None, "close": None, "alone": np.zeros(len(sub_col), bool),
           "spec": dict(spec), "round": rnd, "Dx": None, "Dy": None, "P": None}  # fmt: skip
    if rnd > 0:  # the outline field's slopes at the points, per mm, for its distance inside (`Voxels._spline_dens`)
        out["Dx"], out["Dy"] = assemble(d_phi_x, n_phi, len(sub_col)), assemble(d_phi_y, n_phi, len(sub_col))
    if least_width_mm > 0:
        w = int(round(least_width_mm / (h / q)))
        if w < 2:
            raise ValueError(f"the least width {least_width_mm:g} mm is under two {h / q:g} mm points: nothing to open")
        out["open"] = least_width_blocks(sub_ij, sub_layer, sub_lev, w, disc=bool(spec.get("disc")))
        out["alone"] = (out["open"]["member"] < 0).all(axis=1)
    gap_mm = float(spec.get("gap_mm") or 0.0)
    if gap_mm > 0:
        w = int(round(gap_mm / (h / q)))
        if w < 2:
            raise ValueError(f"the least gap {gap_mm:g} mm is under two {h / q:g} mm points: nothing to close")
        solid = None
        if spec.get("gap_shell"):
            # (LOP-30, 15 October 05:05) the least gap read against the shell too: each half's fixed metal in plan (its
            # cubes frozen anywhere along the pull, at the points' spacing) is metal to the closing where a level has no
            # point, so no slot narrower than the gap opens between a member and the walls, the land, the bosses or the
            # lugs (`spl8f6`'s side walls: thin curtains standing 2-5 mm off the wall, a slot no sand fills)
            frozen = grid == 1
            solid = set()
            for hf_, fz in ((0, frozen[:, :, :k_split].any(axis=2)), (1, frozen[:, :, k_split:].any(axis=2))):
                for ci_, cj_ in zip(*np.nonzero(fz), strict=True):
                    for a_ in range(q):
                        for b_ in range(q):
                            solid.add((hf_, int(q * ci_ + a_), int(q * cj_ + b_)))
        if solid is None and out["open"] is not None and out["open"]["w"] == w:
            out["close"] = out["open"]
        else:
            out["close"] = least_width_blocks(sub_ij, sub_layer, sub_lev, w, disc=bool(spec.get("disc")), solid=solid)
    out["pts_path"] = bool(spec.get("top") or spec.get("window") or spec.get("dist") or spec.get("sizes"))
    out["top"] = out["window"] = out["dist"] = None
    # (LOP-30, 14 October 23:35) the least width and gap as constraints on the raw field (`Voxels.spline_sizes`), each at
    # most this share of the metal; the openings on the points then only measure, the geometry stays the smooth field
    out["sizes"] = float(spec["sizes"]) if spec.get("sizes") else None
    out["alone_close"] = (out["close"]["member"][: len(sub_col)] < 0).all(axis=1) if out["close"] is not None else None
    if out["close"] is not None and out["close"].get("virtual") is not None:
        if not out["sizes"]:
            raise ValueError("the least gap against the shell (gap_shell) is read as a constraint only (--sizes)")
        # a point whose every block holds the shell lies in a slot of the shell itself (between the wall and the land, a
        # boss at the design space's edge), where no member is to blame: no gap measured there. A slot between a member and
        # the wall keeps blocks on the member's side that miss the wall, so it is still read
        mem_ = out["close"]["member"][: len(sub_col)]
        has_v = (out["close"]["blocks"] == out["close"]["virtual"]).any(axis=1)
        shell_only = np.where(mem_ >= 0, has_v[np.maximum(mem_, 0)], True).all(axis=1) & (mem_ >= 0).any(axis=1)
        out["alone_close"] = out["alone_close"] | shell_only
    if spec.get("top"):
        # (LOP-30, F1; the engineer 14 October 23:01) one smooth top: each family's height field is its members' free end
        # itself, voxels out from the split (`o_base` a column's starting level on that scale), so a member's free end no
        # longer steps where its columns' starting levels do (the land's and the shell's cubes, the rooms' end walls)
        if col_len is None:
            raise ValueError("the smooth top needs each column's length")
        o_base = np.where(half == 0, (k_split - 1) - base, base - k_split).astype(float)
        e_lo, e_span = np.zeros(len(pts)), np.ones(len(pts))
        for hf_ in (0, 1):
            for mask in (on_split, ~on_split):
                sel = (half == hf_) & mask
                if sel.any():
                    lo_ = float(o_base[sel].min() + least_vox)
                    hi_ = float((o_base[sel] + np.asarray(col_len, float)[sel]).max())
                    e_lo[sel], e_span[sel] = lo_, max(hi_ - lo_, 1.0)
        out["top"] = {"o_base": o_base, "E_lo": e_lo, "E_span": e_span}
    win = spec.get("window")
    if win:
        # (LOP-30, F2) the section window: a member's height (above its level) at most caps_mm[0] where it is narrower
        # than widths_mm[0], caps_mm[k] where it is at least widths_mm[k-1] wide: the field opened again at each width
        widths, caps = [float(v) for v in win["widths_mm"]], [float(v) for v in win["caps_mm"]]
        if len(caps) != len(widths) + 1:
            raise ValueError("the section window needs one cap more than its widths")
        blocks = [least_width_blocks(sub_ij, sub_layer, sub_lev, int(round(wd / (h / q))), disc=bool(spec.get("disc"))) for wd in widths]
        out["window"] = {"open": blocks, "alone": [(b_["member"] < 0).all(axis=1) for b_ in blocks], "caps_vox": np.asarray(caps) / h,
                         "widths_mm": widths}  # fmt: skip
        # (15 October 01:55; the engineer, 01:48: rules as guides, a production look) the members hanging from the split
        # (the side walls' gussets, production's "from the flange's bolt bosses into the body") their own caps
        # (`caps_split_mm`, one per width as `caps_mm`): a thin gusset may run deep, a wide one stays low; `spl5d`'s deep
        # side members near the seats had carried its beds, and capped like the end walls' ribs the beds stalled at 1.6 x
        caps_split = win.get("caps_split_mm")
        if caps_split is not None:
            if len(caps_split) != len(caps):
                raise ValueError("the side walls' caps need one a width class, as the window's")
            out["window"]["caps_split_vox"] = np.asarray([float(c_) for c_ in caps_split]) / h
        out["window"]["split_pts"] = on_split[sub_col]
        # the columns the window leaves their full height (the mounts' brackets and the bearings' bosses, `Voxels`), by point;
        # with `bosses_wall_only` a boss's only on its wall (the columns hanging from the split stay capped)
        free_c = np.zeros(len(pts), bool) if window_free is None else np.asarray(window_free, bool).copy()
        if window_bosses is not None:
            free_c |= np.asarray(window_bosses, bool) & (~on_split if bosses_wall_only else True)
        out["window"]["free"] = free_c[sub_col] if free_c.any() else None
        out["window"]["free_cols"] = int(free_c.sum())
        # (15 October 01:21; the engineer: "Yes" to the production settings) with one smooth top the caps are measured from
        # each family's level smoothed over LEVEL_SMOOTH_MM, not from each column's own: a capped member's free end then runs
        # smooth over the wall's steps (the land's edge, a seat's ring) instead of copying them (`spl5d_it80`'s terraces).
        # Each column's cap is raised by its smoothed level less its own (voxels)
        lift = np.zeros(len(pts))
        if out["top"] is not None:
            o_b = out["top"]["o_base"]
            grp = (np.asarray(layer, np.int64) % 10_000) * 2 + on_split.astype(np.int64)
            ckey = {(int(half[c]), int(grp[c]), int(ii[c]), int(jj[c])): c for c in range(len(pts))}
            r_c = int(math.ceil(LEVEL_SMOOTH_MM / h))
            sig2 = 2.0 * (0.5 * LEVEL_SMOOTH_MM) ** 2
            offs = [(a, b, math.exp(-(a * a + b * b) * h * h / sig2)) for a in range(-r_c, r_c + 1) for b in range(-r_c, r_c + 1)
                    if (a * a + b * b) * h * h <= LEVEL_SMOOTH_MM**2]  # fmt: skip
            for c in range(len(pts)):
                num = den = 0.0
                for a, b, w_ in offs:
                    k = ckey.get((int(half[c]), int(grp[c]), int(ii[c]) + a, int(jj[c]) + b))
                    if k is not None:
                        num += w_ * o_b[k]
                        den += w_
                lift[c] = num / den - o_b[c]
        out["window"]["lift"] = lift
    if spec.get("dist") == "soft":
        # (LOP-30) the round's distance inside the outline: a soft minimum of the distances to the points outside it on the
        # same level, within DIST_R (the field over its slope jumped from point to point: 25 % of neighbours inside
        # `spl2`'s outline more than 4 mm apart)
        step = h / q
        r_pts = int(np.ceil(DIST_R / step))
        offs = [(a, b) for a in range(-r_pts, r_pts + 1) for b in range(-r_pts, r_pts + 1) if (a * a + b * b) * step * step <= DIST_R**2]
        pp, qq_, dd = [], [], []
        for s_ in range(len(sub_col)):
            hk, bk, ik, jk = int(sub_half[s_]), int(sub_lev[s_]), int(sub_ij[s_, 0]), int(sub_ij[s_, 1])
            for a, b in offs:
                t_ = key.get((hk, bk, ik + a, jk + b))
                if t_ is not None:
                    pp.append(s_)
                    qq_.append(t_)
                    dd.append(step * math.hypot(a, b))
        pp, qq_, dd = np.asarray(pp, np.int64), np.asarray(qq_, np.int64), np.asarray(dd)
        out["dist"] = {"p": pp, "q": qq_, "w": np.exp(-dd / DIST_EPS), "eps": DIST_EPS, "floor": math.exp(-DIST_R / DIST_EPS), "d0": 0.5 * step}
    # (LOP-30, F3) the fields' bending (P-spline: Eilers & Marx 1996): each field's second differences along x and y over
    # its kept control points, the squared sum over the spacing squared (about the integral of the squared curvature)
    ops = []
    for fd in fields:
        shape_, kept_ = fd["shape"], np.asarray(fd["kept"], np.int64)
        local = np.full(shape_[0] * shape_[1], -1, np.int64)
        local[kept_] = np.arange(len(kept_))
        rows, cols, vals = [], [], []
        r_ = 0
        for k_loc, g_ in enumerate(kept_):
            ix, iy = divmod(int(g_), shape_[1])
            for dx_, dy_ in ((1, 0), (0, 1)):
                a_, b_ = (ix - dx_, iy - dy_), (ix + dx_, iy + dy_)
                if not (0 <= a_[0] < shape_[0] and 0 <= a_[1] < shape_[1] and 0 <= b_[0] < shape_[0] and 0 <= b_[1] < shape_[1]):
                    continue
                la, lb = local[a_[0] * shape_[1] + a_[1]], local[b_[0] * shape_[1] + b_[1]]
                if la < 0 or lb < 0:
                    continue
                rows += [r_, r_, r_]
                cols += [int(la), k_loc, int(lb)]
                vals += [1.0, -2.0, 1.0]
                r_ += 1
        d2 = sp.csr_matrix((vals, (rows, cols)), shape=(r_, len(kept_)))
        start = fd["offset"] + (0 if fd["kind"] == "outline" else n_phi)
        ops.append({"kind": fd["kind"], "half": fd["half"], "family": fd.get("family"), "D2": d2, "start": start,
                    "n": len(kept_), "spacing": float(fd["spacing"])})  # fmt: skip
    out["bend_ops"] = ops
    return out


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


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


def _d_matrix() -> np.ndarray:
    lam = YOUNG * POISSON / ((1 + POISSON) * (1 - 2 * POISSON))
    mu = YOUNG / (2 * (1 + POISSON))
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


def hex_wilson(h: float) -> np.ndarray:
    """A cube's 24x24 stiffness with Wilson's incompatible modes (1 - xi², 1 - eta², 1 - zeta² for
    each component) condensed out; 2x2x2 Gauss. The plain hexahedron locks in bending: a
    cantilever of 6 mm cubes one element thick reads 0.626 of beam theory's deflection (two thick,
    0.856), this one 0.985 (0.981) (LOP-16, 22:00). On a cube the Jacobian is constant, so
    Taylor's correction is not needed and the patch test holds."""
    d = _d_matrix()
    corners = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)], float) * 2 - 1
    g = 1 / math.sqrt(3)
    k = np.zeros((33, 33))
    for gx in (-g, g):
        for gy in (-g, g):
            for gz in (-g, g):
                dn = np.array([[xi * (1 + yi * gy) * (1 + zi * gz), yi * (1 + xi * gx) * (1 + zi * gz), zi * (1 + xi * gx) * (1 + yi * gy)] for xi, yi, zi in corners])
                dn *= 0.125 * (2 / h)
                dp = np.diag([-2 * gx, -2 * gy, -2 * gz]) * (2 / h)
                b = np.hstack([_b_of(dn), _b_of(dp)])
                k += b.T @ d @ b * (h / 2) ** 3
    kuu, kua, kaa = k[:24, :24], k[:24, 24:], k[24:, 24:]
    return kuu - kua @ np.linalg.solve(kaa, kua.T)


def hex_stiffness(h: float) -> np.ndarray:
    """An 8-node hexahedron's 24x24 stiffness, a cube of side h, 2x2x2 Gauss points (LOP-3's
    element; it locks in bending, see `hex_wilson`)."""
    lam = YOUNG * POISSON / ((1 + POISSON) * (1 - 2 * POISSON))
    mu = YOUNG / (2 * (1 + POISSON))
    d = np.zeros((6, 6))
    d[:3, :3] = lam
    d[np.arange(3), np.arange(3)] += 2 * mu
    d[np.arange(3, 6), np.arange(3, 6)] = mu
    corners = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)], float) * 2 - 1
    g = 1 / math.sqrt(3)
    ke = np.zeros((24, 24))
    for gx in (-g, g):
        for gy in (-g, g):
            for gz in (-g, g):
                dn = np.zeros((8, 3))
                for a, (xi, yi, zi) in enumerate(corners):
                    dn[a] = [
                        xi * (1 + yi * gy) * (1 + zi * gz),
                        yi * (1 + xi * gx) * (1 + zi * gz),
                        zi * (1 + xi * gx) * (1 + yi * gy),
                    ]
                dn *= 0.125 * (2 / h)
                b = np.zeros((6, 24))
                for a in range(8):
                    gxa, gya, gza = dn[a]
                    b[0, 3 * a] = gxa
                    b[1, 3 * a + 1] = gya
                    b[2, 3 * a + 2] = gza
                    b[3, 3 * a], b[3, 3 * a + 1] = gya, gxa
                    b[4, 3 * a + 1], b[4, 3 * a + 2] = gza, gya
                    b[5, 3 * a], b[5, 3 * a + 2] = gza, gxa
                ke += b.T @ d @ b * (h / 2) ** 3
    return ke


def build_model(stem: str, h: float):
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(CONTRACT)
    chain = complete_chain(spec)
    s = info["settings"]
    z_lo, z_hi, z_split = info["z"]["lo"], info["z"]["hi"], info["z"]["split"]
    end = s.get("end_wall", s["wall"])
    clearance = 40.0
    pods = info.get("pods") or [
        {
            "shaft": None,
            "outer": info["outer_outline"],
            "inner": info["inner_outline"],
            "z": (z_lo, z_hi),
        }
    ]
    points = [pt for p in pods for pt in p["outer"]]
    pack = np.asarray(hull_of_circles([(x, y, clearance) for x, y in points[::3]], segments=24))
    lo = np.array([pack[:, 0].min(), pack[:, 1].min(), z_lo - clearance])
    hi = np.array([pack[:, 0].max(), pack[:, 1].max(), z_hi + clearance])
    n = np.ceil((hi - lo) / h).astype(int)
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    zc = lo[2] + h * (np.arange(n[2]) + 0.5)
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing="ij")
    x, y, z = X.ravel(), Y.ravel(), Z.ravel()

    def rho(c):
        return np.hypot(x - c[0], y - c[1])

    in_pack = inside(pack, x, y) & (z >= lo[2]) & (z <= hi[2])
    in_outer = np.zeros(x.shape, dtype=bool)
    in_cavity = np.zeros(x.shape, dtype=bool)
    # A voxel is wall where it touches the wall, not only where its centre falls in it: a wall
    # thinner than a voxel would otherwise break into pieces. So the outer test takes any of a
    # voxel's four corners (end view) and the cavity test all four, and the cavity stops half a
    # voxel short of each end wall.
    half = h / 2
    corners = [(x + dx, y + dy) for dx in (-half, half) for dy in (-half, half)]
    for p in pods:
        z0, z1 = p["z"]
        out_any = np.zeros(x.shape, dtype=bool)
        in_all = np.ones(x.shape, dtype=bool)
        for cx_, cy_ in corners:
            out_any |= inside(p["outer"], cx_, cy_)
            in_all &= inside(p["inner"], cx_, cy_)
        in_outer |= out_any & (z >= z0 - half) & (z <= z1 + half)
        in_cavity |= in_all & (z - half > z0 + end) & (z + half < z1 - end)
    pod_z = {p["shaft"]: p["z"] for p in pods}
    shell = in_outer & ~in_cavity
    bosses = np.zeros(x.shape, dtype=bool)
    hard = np.zeros(x.shape, dtype=bool)
    for b in info["bearings"]:
        r = rho(b["axis"])
        z0, z1 = b["z"]
        plo, phi = pod_z.get(b["shaft"], (z_lo, z_hi))
        if b["side"] == "-z":
            bosses |= (r <= b["D"] / 2 + s["boss"]) & (z >= plo) & (z <= z1)
            hard |= (r < b["D"] / 2 - s["shoulder"]) & (z > plo + end) & (z < z0)
        else:
            bosses |= (r <= b["D"] / 2 + s["boss"]) & (z >= z0) & (z <= phi)
            hard |= (r < b["D"] / 2 - s["shoulder"]) & (z > z1) & (z < phi - end)
        hard |= (r < b["D"] / 2) & (z >= z0) & (z <= z1)
        if b["sealed"]:
            hard |= (r < b["d"] / 2 + s["seal_radial"]) & ((z < z0) if b["side"] == "-z" else (z > z1))
    shell |= bosses
    clear = in_cavity & ~bosses
    for p in pods:  # the flange lips at the split
        lip = hull_of_circles([(xx, yy, s["flange_width"]) for xx, yy in p["outer"][::3]], segments=24)
        shell |= inside(lip, x, y) & (np.abs(z - z_split) <= s["flange_thickness"])
    for m in info["mounts"]:
        r = rho(m["centre"])
        shell |= (r <= s["mount_diameter"] / 2) & (z >= m["z"][0]) & (z <= m["z"][1])
        clear |= (r < s["mount_diameter"] / 2 + 4) & ((z < m["z"][0]) | (z > m["z"][1]))
    inp = next(b["axis"] for b in info["bearings"] if b["shaft"] == "input")
    out_axis = next(b["axis"] for b in info["bearings"] if b["shaft"] == "output")
    ring_in, ring_out = s["motor_ring"]
    z_motor = info["z"].get("motor", z_lo)
    r_in = rho(inp)
    t_ring = s["motor_ring_thickness"]
    shell |= (r_in >= ring_in / 2) & (r_in <= ring_out / 2) & (z >= z_motor - t_ring) & (z <= z_motor)
    if info.get("pods"):  # the lobed form's flange plate for the motor
        shell |= (r_in <= ring_out / 2) & (z >= z_motor) & (z <= z_motor + end)
    clear |= (r_in < ring_out / 2 + 15) & (z < z_motor - t_ring)  # the motor
    clear |= (rho(out_axis) < 45) & ((z < z_lo) | (z > z_hi))  # the half-shafts' joints
    for c in info["bolts"]:
        clear |= (rho(c) < 11) & (np.abs(z - z_split) > s["flange_thickness"]) & (np.abs(z - z_split) < 45)
    clear |= hard
    shell &= ~hard
    design = in_pack & ~shell & ~clear
    kind = np.full(x.shape, -1, dtype=np.int8)  # -1 not modelled, 0 design, 1 frozen
    kind[design] = 0
    kind[shell] = 1
    return {"info": info, "spec": spec, "chain": chain, "h": h, "lo": lo, "n": n, "kind": kind,
            "inp": inp, "z_motor": z_motor}  # fmt: skip


def rotation_rows(xyz: np.ndarray, ids: np.ndarray, n_dof: int) -> sp.csr_matrix:
    """(3, n_dof): a node set's best-fit rotation (RBE3, uniform weights), as fe.py reads it."""
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


def released_at_split(node_key, corner, ijk, lo, h, n_grid: int, joint: dict):
    """The halves joined only at the bolts: every node of the split's layer that an element above
    the split uses gets a copy of its own, except within a bolt boss's footprint (within
    `joint["radius"]` of one of `joint["bolts"]`, in plan), where the two halves go on sharing it.
    Elsewhere the halves touch without a bond, as `fe.py` joins them only at the bolts. Nothing
    stops them passing through each other either (a linear model has no contact), so the joint
    face's compression is not counted: this joint is the softer bound, the glued one the stiffer.
    `corner` is every element's eight corners' grid indices, `node_key` their node keys; a copy's
    key is its node's plus `n_grid`. Returns the new keys and a note of what stayed tied."""
    ks = joint["k_split"]
    above = np.repeat(ijk[:, 2] >= ks, 8)
    on_split = corner[:, 2] == ks
    px, py = lo[0] + h * corner[:, 0], lo[1] + h * corner[:, 1]
    bolt_of = np.full(len(corner), -1)
    for i, (bx, by) in enumerate(joint["bolts"]):
        bolt_of[(bolt_of < 0) & (np.hypot(px - bx, py - by) <= joint["radius"])] = i
    shared = np.intersect1d(node_key[on_split & above], node_key[on_split & ~above])
    tied = on_split & (bolt_of >= 0) & np.isin(node_key, shared)
    released = on_split & above & (bolt_of < 0)
    note = (f"the halves joined only at {len(np.unique(bolt_of[tied]))} of the layout's {len(joint['bolts'])} bolts: "
            f"{len(np.unique(node_key[tied]))} of the split's {len(shared)} shared nodes kept")  # fmt: skip
    return np.where(released, node_key + n_grid, node_key), note


class Voxels:
    """The voxel model as finite elements, and the chain from the design variables to the
    elements' densities with its exact derivative. Built once a run; `solve_model` iterates on
    it, `topo_gradcheck.py` checks its derivatives against finite differences.

    - **Elements:** every modelled voxel (`kind` >= 0) a hexahedron with Wilson's incompatible
      modes (`hex_wilson`). `model["stiffness"]`, where given, scales a voxel's stiffness (the
      skin modelled as the contract's least wall, `topo_free.py`). The halves are glued at the
      split, or joined only at the bolts when `model["joint"]` says so (`released_at_split`).
    - **Loads and supports (LOP-2's):** each seat's force over its bore's nodes, the motor's
      torque on its ring; the mounts' holes held.
    - **Measures:** every seat's own rotation and its misalignment against its shaft's chord plus
      the shaft's lean, over its line (`grade.py`'s), in both cases.
    - **The chain:** x (one variable per free voxel) -> the density filter (radius `FILTER`
      voxels) -> the projection (`model["projection"]`, at sharpness beta) -> the casting filter
      (`model["cast"]`, frozen voxels metal) -> the densities. The stiffness reads them by SIMP
      (penalty 3, or the ramp's), the mass by their sum over the free voxels. `back` takes derivatives with respect
      to the densities back to x through the same chain. It reads the casting filter at its last
      forward pass, so it must follow `physical` at the same x and beta."""

    def __init__(self, model):
        h, n, lo, kind = model["h"], model["n"], model["lo"], model["kind"]
        info, chain, spec = model["info"], model["chain"], model["spec"]
        self.model, self.h = model, h
        self.elem = elem = np.flatnonzero(kind >= 0)
        self.frozen = frozen = kind[elem] == 1
        self.ijk = ijk = np.stack(np.unravel_index(elem, n), axis=1)
        self.grid_n, self.k_split_ = np.asarray(n, int), int(model.get("k_split") or 0)  # (LOP-29) for the loose metal
        offsets = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)])
        corner = (ijk[:, None, :] + offsets[None, :, :]).reshape(-1, 3)
        n_grid = int(np.prod(n + 1))
        node_key = np.ravel_multi_index(corner.T, n + 1)
        self.joint_note = "the halves glued at the split"
        # (LOP-29) FE's rigid couplings (`model["couplings"]` "kinematic"): the halves released everywhere, each bolt's holes then
        # one rigid body; else the halves share their nodes over each bolt's boss ("glue", every run before 13 October 23:00)
        self.kinematic = (os.environ.get("LOOP_MODEL_COUPLING") or model.get("couplings") or "glue") == "kinematic"  # the variable: a check's
        if model.get("joint"):
            joint = {**model["joint"], "radius": -1.0} if self.kinematic else model["joint"]
            node_key, self.joint_note = released_at_split(node_key, corner, ijk, lo, h, n_grid, joint)
        used, inverse = np.unique(node_key, return_inverse=True)
        conn = inverse.reshape(-1, 8)
        xyz = lo + h * np.stack(np.unravel_index(used % n_grid, n + 1), axis=1)
        n_nodes = len(used)
        self.n_dof = n_dof = 3 * n_nodes
        self.xyz = xyz  # the nodes' coordinates, mm (a copy above the split shares its node's)
        stiff = model.get("stiffness")
        self.stiff_e = np.ones(len(elem)) if stiff is None else np.asarray(stiff, float)[elem]
        mass_share = model.get("mass_share")
        self.mass_share_e = np.ones(len(elem)) if mass_share is None else np.asarray(mass_share, float)[elem]
        self.mode_count = int(model["modes"].get("count", MODE_COUNT)) if model.get("modes") else 0  # LOP-29: modes each analysis
        say(f"voxels {h:g} mm: {len(elem):,} elements ({frozen.sum():,} frozen, {(~frozen).sum():,} free), {n_dof:,} unknowns; {self.joint_note}")
        self.ke = hex_wilson(h)
        self.dof = dof = (3 * conn[:, :, None] + np.arange(3)[None, None, :]).reshape(-1, 24)
        self.rows = np.repeat(dof, 24, axis=1).ravel().astype(np.int32)
        self.cols = np.tile(dof, (1, 24)).ravel().astype(np.int32)

        s = info["settings"]
        # The load cases: both peaks unless the model names its own (the engineer, 10 October 14:54:
        # "first only one load case", peak drive).
        wanted = tuple(model.get("cases") or ("peak drive", "peak reverse"))
        self.cases = cases = [c for c in chain.loads if c.name in wanted]
        if len(cases) != len(wanted):
            raise ValueError(f"load cases {wanted}: the chain has {[c.name for c in chain.loads]}")
        self.n_cases = len(cases)
        f = np.zeros((n_dof, self.n_cases))
        seat_ids = {}
        # A seat's nodes are the frozen voxels' own: a node held only by near-empty design voxels
        # would swing freely and read as a tilt.
        on_shell = np.zeros(n_nodes, dtype=bool)
        on_shell[np.unique(conn[frozen])] = True
        for b in info["bearings"]:
            r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
            ids = np.flatnonzero(on_shell & (np.abs(r - b["D"] / 2) <= 0.75 * h) & (xyz[:, 2] >= b["z"][0] - 0.5 * h) & (xyz[:, 2] <= b["z"][1] + 0.5 * h))
            assert len(ids) > 8, (b["shaft"], b["side"], len(ids))
            seat_ids[(b["shaft"], b["side"])] = ids
        seat_force = {}  # (LOP-29, rigid couplings) each seat's force by case, applied at its bearing's centre
        for j, case in enumerate(cases):
            for seat in case.seats:
                ids = seat_ids[(seat.shaft, seat.side)]
                if self.kinematic:
                    seat_force.setdefault((seat.shaft, seat.side), np.zeros((3, self.n_cases)))[:, j] += np.asarray(seat.force, float)
                    continue
                for k in range(3):
                    f[3 * ids + k, j] += seat.force[k] / len(ids)
            # A flanged motor's reaction, on its ring's face. The contract's layout has no flange
            # (the engineer, 10 October 13:21: the vehicle holds the motor): no ring, no torque.
            self.ring_ids = np.zeros(0, dtype=int)
            if "motor_ring" not in s:
                continue
            r_vec = xyz[:, :2] - np.asarray(model["inp"])
            r_len = np.hypot(r_vec[:, 0], r_vec[:, 1])
            ring_in, ring_out = s["motor_ring"]
            ids = np.flatnonzero((r_len >= ring_in / 2) & (r_len <= ring_out / 2) & (xyz[:, 2] <= model["z_motor"] - s["motor_ring_thickness"] + 0.5 * h))
            self.ring_ids = ids  # the motor ring's face, where its torque acts
            tau = case.motor_torque
            denom = (r_len[ids] ** 2).sum()
            f[3 * ids, j] += -tau * r_vec[ids, 1] / denom
            f[3 * ids + 1, j] += tau * r_vec[ids, 0] / denom
        if self.kinematic:
            # (LOP-29) FE's couplings (`couplings.py`): a seat's surface (its nodes on the model's boundary) rigid with its bearing's
            # centre; each bolt's hole through both flanges (the nodes on its boundary within half a voxel of the hole) one rigid body
            # at its point on the split; each mount's hole (the lug's core within the hole's radius and a quarter voxel) held
            import couplings as cpl

            boundary = np.bincount(conn.ravel(), minlength=n_nodes) < 8
            groups = []
            # a node two seats reach (bores closer than a voxel or two) goes to the seat whose surface it lies nearer
            gap = {}
            for key, ids in seat_ids.items():
                b = next(b_ for b_ in info["bearings"] if (b_["shaft"], b_["side"]) == key)
                gap[key] = np.abs(np.hypot(xyz[ids, 0] - b["axis"][0], xyz[ids, 1] - b["axis"][1]) - b["D"] / 2)
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
                groups.append({"nodes": ids, "ref": (*b["axis"], 0.5 * (b["z"][0] + b["z"][1])), "name": f"the {key[0]} {key[1]} seat", "seat": key})
            z_s = float(info["z"]["split"])
            t_f = float((info.get("flange") or {}).get("thickness", s["flange_thickness"]))
            n_bolts = 0
            for c in info["bolts"]:
                r = np.hypot(xyz[:, 0] - c[0], xyz[:, 1] - c[1])
                ids = np.flatnonzero(boundary & (r <= s["bolt_hole"] / 2 + 0.5 * h) & (np.abs(xyz[:, 2] - z_s) <= t_f + 1e-6))
                if len(ids) >= 6:
                    groups.append({"nodes": ids, "ref": (c[0], c[1], z_s), "name": f"bolt {n_bolts + 1}"})
                    n_bolts += 1
            held = []
            for m in info["mounts"]:
                r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
                ids = np.flatnonzero((r <= s["mount_hole"] / 2 + 0.25 * h) & (xyz[:, 2] >= m["z"][0] - 1e-6) & (xyz[:, 2] <= m["z"][1] + 1e-6))
                groups.append({"nodes": ids, "fixed": True, "name": m["name"]})
                held.append(ids)
            self.held = np.unique(np.concatenate(held))
            self.coupling_groups = groups  # (`couplings_view.py --model` pictures them)
            T, tinfo = cpl.rigid_transform(xyz, groups)
            rigid = cpl.check_rigid(T, xyz, groups, tinfo)
            if rigid > 1e-9:
                raise RuntimeError(f"the rigid couplings' transform is not rigid: {rigid:.1e}")
            self.T, self.n_q, self.free = T, tinfo["n_q"], None
            rhs = np.asarray(T.T @ f)
            for g, grp in enumerate(groups):
                if grp.get("seat") in seat_force:
                    rhs[tinfo["ref_col"][g] : tinfo["ref_col"][g] + 3] += seat_force[grp["seat"]]
            self.rhs = rhs
            self.joint_note += f"; rigid couplings: {len(seat_ids)} seats, {n_bolts} bolts through both halves, {len(held)} mounts held"
            say(f"rigid couplings (FE's): {len(seat_ids)} seats with their bearings' centres, {n_bolts} bolts each one rigid body, "
                f"{len(held)} mounts' holes held; {self.n_q:,} unknowns remain")  # fmt: skip
        else:
            held = []
            for m in info["mounts"]:
                r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
                held.append(np.flatnonzero((r <= s["mount_hole"] / 2 + 0.75 * h) & (xyz[:, 2] >= m["z"][0]) & (xyz[:, 2] <= m["z"][1])))
            self.held = held = np.unique(np.concatenate(held))
            fixed = np.zeros(n_dof, dtype=bool)
            for k in range(3):
                fixed[3 * held + k] = True
            self.free = free = np.flatnonzero(~fixed)
            self.T = sp.csr_matrix((np.ones(len(free)), (free, np.arange(len(free)))), shape=(n_dof, len(free)))
            self.n_q = len(free)
            self.rhs = f[free]
        # The seats' rotation rows and lines (rad), for the tilt objective and the record; for the
        # misalignment, each seat's two rows against its shaft's chord, and the shaft's leans.
        limits = {t.bearing_type: value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
        margin = value_in(spec.limits.model_margin, "1")
        # The optimiser's factor of safety (`model["safety"]`, LOP-24; the engineer, 11 October 20:04): every
        # tilt and bed held at most 1/safety of its line, covering the model's own optimism (FE read thin
        # members 11-30 % softer at 4 mm); the grade judges the true lines
        safety = float(model.get("safety") or 1.0)
        safety_beds = float(model.get("safety_beds") or safety)  # the beds' own factor (LOP-24), else the tilt's
        types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
        centre_z = {(b["shaft"], b["side"]): 0.5 * (b["z"][0] + b["z"][1]) for b in info["bearings"]}

        def moved(ids):
            """(3, free): the mean displacement of a node set."""
            rr_, cc_, vv_ = [], [], []
            for k_ in range(3):
                rr_ += [k_] * len(ids)
                cc_ += list(3 * ids + k_)
                vv_ += [1.0 / len(ids)] * len(ids)
            return (sp.csr_matrix((vv_, (rr_, cc_)), shape=(3, n_dof)) @ self.T).tocsr()

        self.seats = []
        for key, ids in seat_ids.items():
            rr = (rotation_rows(xyz, ids, n_dof) @ self.T).tocsr()
            shaft, side = key
            a_, b_ = moved(seat_ids[(shaft, "-z")]), moved(seat_ids[(shaft, "+z")])
            span = abs(centre_z[(shaft, "+z")] - centre_z[(shaft, "-z")])
            # grade.py: hypot(theta_y - dx - lean_x, -theta_x - dy - lean_y), dx = (u+z - u-z)_x / span
            l1 = (rr[1] - (b_[0] - a_[0]) / span).tocsr()
            l2 = (-rr[0] - (b_[1] - a_[1]) / span).tocsr()
            # a seat's own factor (LOP-28, `model["safety_seats"]`, "<shaft> <side>": factor): learned from FE, where the model
            # flatters one seat more than the rest (the cover's input seat, 1.26-1.30 x in three drawings of 13 October)
            f_seat = float((model.get("safety_seats") or {}).get(f"{shaft} {side}", safety))
            self.seats.append((key, rr, (1 - margin) * limits[types[key]] / f_seat, l1, l2))
        leans = {sec.shaft: sec.lean_at_bearing for sec in chain.sections}
        self.lean_of = {(key, c): leans[key[0]].get(case.name, {}).get(key[1], (0.0, 0.0)) for key in seat_ids for c, case in enumerate(cases)}
        # Every seat in every case, in this order: the bound formulation's constraints.
        self.keys = [(key, c) for key, *_ in self.seats for c in range(len(cases))]
        # The bearing beds (the grade's displacement line; LOP-20, 11 October): each seat's
        # displacement, the mean of its nodes' (fe.py's `displacement_mm`), at most the design to
        # beat's in each case `model["beds_mm"]` names (mm, by case); a constraint of
        # `compliance_tilt`. A floating core meets the relative tilt; it cannot meet the beds.
        beds_mm = model.get("beds_mm") or {}
        self.bed_line = [beds_mm[case.name] / safety_beds if beds_mm.get(case.name) else None for case in cases]
        self.bed_rows = {key: moved(ids) for key, ids in seat_ids.items()}
        self.bed_keys = [(key, c) for key in seat_ids for c, line in enumerate(self.bed_line) if line]

        self.free_e = free_e = np.flatnonzero(~frozen)
        from scipy.spatial import cKDTree

        tree = cKDTree(ijk[free_e].astype(float))
        pairs = tree.sparse_distance_matrix(tree, FILTER, output_type="coo_matrix")
        w = np.maximum(0.0, FILTER - pairs.data)
        hmat = sp.coo_matrix((w, (pairs.row, pairs.col)), shape=(len(free_e), len(free_e))).tocsr()
        self.hmat = (hmat + sp.eye(len(free_e)) * FILTER).tocsr()
        groups = model.get("groups")
        if groups is not None:
            # The rib filter (LOP-23, `topo_free.build_free(..., rib_filter=True)`): a grouped voxel's
            # filtered density is its group's mean (one piece of the rib network at one height off
            # the shell), so each piece stands at one height; the others keep the cone filter.
            g = np.asarray(groups)[elem[free_e]]
            grouped = g >= 0
            _, member = np.unique(g[grouped], return_inverse=True)
            ind = sp.csr_matrix((np.ones(int(grouped.sum())), (member, np.flatnonzero(grouped))), shape=(int(member.max()) + 1, len(free_e)))
            keep = sp.diags((~grouped).astype(float))
            self.hmat = (keep @ self.hmat + ind.T @ ind).tocsr()
            say(f"the rib filter: {int(grouped.sum()):,} of {len(free_e):,} free voxels in {ind.shape[0]:,} groups")
        self.hs = np.asarray(self.hmat.sum(axis=1)).ravel()
        self.cast = model.get("cast")
        # A projection (`model["projection"]`: its threshold and the iterations at which its
        # sharpness doubles, from 1) drives the filtered field to solid and void: without it 54 %
        # of the free run's metal stayed grey at 100 iterations (LOP-16 run 1), which no mould
        # casts.
        self.projection = model.get("projection")
        self.mass_rows = np.zeros(len(elem))
        self.mass_rows[free_e] = 1.0  # the mass (in voxels) reads the free voxels' densities
        # The height field (LOP-23, 11 October 15:50; the engineer, 15:44: "we need some continuous
        # space on which we can do optimisation"): one design variable a column of each half, the
        # metal's height there from the split or the wall it stands on, smoothed over the plan by a
        # cone of `radius_mm`, so the members are continuous ridges and webs of one surface and each
        # column is one run from the split: castable by construction (no casting filter).
        self.height = None
        self.spline = None  # (LOP-30) the spline map, with the height field
        self.features = None
        self.n_design = len(free_e)
        hf = model.get("height_field")
        if hf:
            col, pos, pts, layer = height_columns(kind, n, model["k_split"], elem, free_e)
            n_cols = len(pts)
            radius = float(hf["radius_mm"]) / h
            plan = np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]])
            ptree = cKDTree(plan)
            pp = ptree.sparse_distance_matrix(ptree, radius, output_type="coo_matrix")
            fmat = sp.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(n_cols, n_cols)).tocsr()
            fmat = (fmat + sp.eye(n_cols) * radius).tocsr()
            cmat = sp.csr_matrix((np.ones(len(col)), (col, np.arange(len(col)))), shape=(n_cols, len(col)))
            fs = np.asarray(fmat.sum(axis=1)).ravel()
            mmat = (sp.diags(1.0 / fs) @ fmat).tocsr()  # the design variables to the columns' heights (as shares of L)
            self.n_design = n_cols
            feat = model.get("height_features")
            if feat:  # LOP-24: a region's columns from a few features' parameters
                mmat, self.n_design, self.features = feature_map(feat, model["info"], pts, layer, model["lo"], h, fmat, n_cols)
            if model.get("height_volumes"):  # LOP-24: the design space divided into volumes, each its own form (`volume_map`)
                mmat, self.n_design, self.features = volume_map(model["height_volumes"], fmat, n_cols)
            parts_map = None
            if model.get("parts"):  # LOP-26, Refine: every column's height production's parts' (`parts.PartsMap`), nothing else
                import parts as parts_mod

                parts_map = parts_mod.PartsMap(model["parts"], np.asarray(model["lo"], float)[:2] + h * (pts + 0.5), layer)
                self.n_design = parts_map.n_vars
                say(f"production's parts: {len(parts_map.members)} members and {len(parts_map.rings)} rings, {parts_map.n_vars} variables "
                    "(their nodes' places and their sizes); a column no part covers holds nothing")  # fmt: skip
            # LOP-27, the empty start (`topo_free.least_heights`): each wall's column its least height (voxels), under the optimiser's own
            tmin = None
            if model.get("height_min") is not None:
                tmin = np.zeros(n_cols)
                np.maximum.at(tmin, col, np.asarray(model["height_min"], float)[elem[free_e]])
                say(f"the empty start: {int((tmin > 0).sum()):,} of {n_cols:,} columns are walls, each at least its least height "
                    f"(median {np.median(tmin[tmin > 0]) * h:.1f} mm, most {tmin.max() * h:.1f} mm)")  # fmt: skip
            self.height = {"col": col, "pos": pos, "M": mmat, "C": cmat, "wall_gate": float(model.get("wall_gate_mm") or 0.0) / h,
                           "L": float(pos.max() + 1.0), "n_cols": n_cols, "radius_mm": float(hf["radius_mm"]),
                           "least": 0.0 if parts_map is not None else float(model.get("least_height_mm") or 0.0) / h,  # parts gate their own heights
                           "parts": parts_map, "h": h, "pts": pts, "layer": layer, "tmin": tmin}  # fmt: skip
            if self.height["least"]:
                say(f"the least member: a column under {model['least_height_mm']:g} mm holds nothing (no paint, LOP-25)")
            least_w = float(model.get("least_width_mm") or 0.0)
            spl = model.get("spline")
            base = None
            if least_w > 0 or spl:  # each column's first free voxel's place along the pull: its level
                if parts_map is not None or feat or model.get("height_volumes"):
                    raise ValueError("the least width and the spline map are the plain height field's (no features, volumes or parts)")
                kz = elem[free_e] % int(n[2])
                base = np.full(n_cols, -1, np.int64)
                first_ = pos == 0
                base[col[first_]] = kz[first_]
                if (base < 0).any():
                    raise ValueError("a column without its first free voxel")
            if spl:  # LOP-30 (the engineer, 14 October 17:27): smooth B-spline fields as the design variables (`spline_setup`)
                # (14 October 23:58) the mounts' reach discs (`topo_free.build_free`): the brackets' columns, whose depth the
                # lugs' places set, keep their full height under the section window (capped at 32 mm, mount-3's lug could
                # not be reached at all: `lug_reach_probe.py`)
                in_disc = np.zeros(n_cols, bool)
                col_xy = np.asarray(model["lo"], float)[:2] + h * (pts + 0.5)
                col_half = np.asarray(layer) // 10_000
                free_w = (spl.get("window") or {}).get("free", ["mounts"])
                if "mounts" in free_w:
                    for d_ in model.get("mount_discs") or []:
                        in_disc |= (col_half == d_["half"]) & (np.hypot(*(col_xy - np.asarray(d_["centre"])).T) <= d_["reach_mm"])
                in_boss = np.zeros(n_cols, bool)
                if "bosses" in free_w:  # (15 October 00:45, the engineer: "Lift height cap only") each bearing's boss tall, as
                    # castability's section check leaves it out (within 0.625 D + 5 mm of its axis); the lump rule holds there.
                    # Only the columns standing on a wall (`spline_setup`): the boss stands on its bearing's wall, and the
                    # columns hanging from the split inside the circle had hung 40-80 mm down the side walls as thin fins
                    # (the engineer, 01:24: "why such regions are too noisy and like edgy and staircasy")
                    for b_ in model["info"]["bearings"]:
                        hf_b = 1 if str(b_["side"]).startswith("+") else 0
                        in_boss |= (col_half == hf_b) & (np.hypot(*(col_xy - np.asarray(b_["axis"][:2], float)).T) <= 0.625 * float(b_["D"]) + 5.0)
                self.spline = spline_setup(spl, kind, n, int(model["k_split"]), pts, layer, base, model["lo"], h,
                                           float(model.get("least_height_mm") or 0.0) / h, least_w,
                                           col_len=np.bincount(col, minlength=n_cols), window_free=in_disc, window_bosses=in_boss,
                                           bosses_wall_only=bool((spl.get("window") or {}).get("bosses_wall_only", False)))  # fmt: skip
                self.n_design = self.spline["n_design"]
                sp_ = self.spline
                if sp_["top"] is not None:
                    say("the smooth top (F1): each family's height field its members' free end, one surface out from the split")
                if sp_["window"] is not None:
                    w_ = sp_["window"]
                    say("the section window (F2): a member at most " + ", ".join(
                        f"{c_ * h:g} mm tall" + (f" where under {w_['widths_mm'][0]:g} mm wide" if i_ == 0 else f" where at least {w_['widths_mm'][i_ - 1]:g} mm wide")
                        for i_, c_ in enumerate(w_["caps_vox"])) + (" (discs)" if spl.get("disc") else "")
                        + (f"; {' and '.join({'mounts': 'the mounts reach discs', 'bosses': 'the bearings bosses'}.get(s_, s_) for s_ in (spl.get('window') or {}).get('free', ['mounts']))}"
                           f" ({w_['free_cols']:,} columns) keep their full height" if w_["free"] is not None else ""))  # fmt: skip
                if sp_["dist"] is not None:
                    say(f"the round's distance inside the outline: a soft minimum over {DIST_R:g} mm ({len(sp_['dist']['p']):,} pairs of points)")
                say(f"the spline map: an outline field ({spl['phi_mm']:g} mm knots, {sp_['n_phi']:,} coefficients) and two height fields "
                    f"({spl['h_mm']:g} mm knots, {sp_['n_h']:,}), per half; {int(sp_['on_split'].sum()):,} columns on the split, "
                    f"{int((~sp_['on_split']).sum()):,} on a wall; every member at least {sp_['least'] * h:g} mm proud; the outline read "
                    f"at {sp_['q']} x {sp_['q']} points a cube ({len(sp_['sub_col']):,})"
                    + (f"; closed to a {float(spl.get('gap_mm') or 0):g} mm least gap" if sp_["close"] is not None else "")
                    + (f"; opened to {least_w:g} mm ({len(sp_['open']['blocks']):,} blocks, {int(sp_['alone'].sum()):,} points in none)"
                       if sp_["open"] is not None else ""))  # fmt: skip
            elif least_w > 0:  # LOP-29 (the engineer, 14 October 13:42): the least member width in plan (`open_heights`)
                w = int(round(least_w / h))
                if w < 2:
                    raise ValueError(f"the least width {least_w:g} mm is under two {h:g} mm cubes: nothing to open")
                self.height["open"] = least_width_blocks(pts, layer, base, w)
                op = self.height["open"]
                say(f"the least member width in plan: {least_w:g} mm ({w} cubes); a column's height counts only up to what the "
                    f"fullest {w} x {w} block of columns on its level reaches ({len(op['blocks']):,} blocks; {op['alone']:,} of "
                    f"{n_cols:,} columns in none, holding nothing)")  # fmt: skip
            say(f"the height field: {n_cols:,} columns, each a height from the split or its wall, smoothed over {hf['radius_mm']:g} mm in plan; "
                f"at most {self.height['L']:.0f} voxels high; {len(free_e):,} free voxels")  # fmt: skip

    def _t0(self, x, beta: float):
        """The columns' heights (voxels) before the least member's gate: the plan filter's of the design variables, or the
        parts' (LOP-26); opened to the least width in plan when it is set (LOP-29, `open_heights`, its sharpness the
        projection's, as the least member's gate), with that opening's Jacobian (else None)."""
        hh = self.height
        t0 = hh["parts"].heights(x) / hh["h"] if hh.get("parts") is not None else (hh["M"] @ x) * hh["L"]
        if hh.get("open") is None:
            return t0, None
        return open_heights(hh["open"], t0, max(beta, 2.0))

    def column_heights(self, x, beta: float):
        """Each column's continuous height (voxels from its base) and its slope by the plan filter's output (M x) L: the
        height `_height_dens` steps each voxel on (LOP-28: the bending limit reads it). The height field's, not the parts'.
        With the least width (LOP-29) the slope is by the opened heights, which the bending's chain does not take."""
        if self.spline is not None:
            raise ValueError("the columns' heights of the spline map (LOP-30) are its height fields': `spline_columns`")
        hh = self.height
        t0, _ = self._t0(x, beta)
        if hh.get("least"):
            s = np.tanh(max(beta, 2.0) * (t0 - hh["least"]))
            g = 0.5 * (1.0 + s)
            slope, t = g + t0 * 0.5 * max(beta, 2.0) * (1.0 - s * s), t0 * g
        else:
            slope, t = np.ones_like(t0), t0
        tmin = hh.get("tmin")
        if tmin is not None:
            wall = tmin > 0
            extra, d_extra = self._wall_extra(t0, beta)
            t, slope = np.where(wall, tmin + extra, t), np.where(wall, d_extra, slope)
        return t, slope

    def _wall_extra(self, t0, beta: float):
        """(LOP-28) The metal a wall's column holds beyond its least height, and its slope by t0: t0 itself, or with
        `model["wall_gate_mm"]` (production's plain walls, the engineer 13 October 01:54: "the walls between the ribs are not
        curvy") counted only once it passes the gate, a smooth step sharpened with the projection, so a wall is either
        bare at its least or carries a member at least that tall: no paint thickening it."""
        gate = self.height.get("wall_gate")
        if not gate:
            return t0, np.ones_like(t0)
        s = np.tanh(max(beta, 2.0) * (t0 - gate))
        g = 0.5 * (1.0 + s)
        return t0 * g, g + t0 * 0.5 * max(beta, 2.0) * (1.0 - s * s)

    def _spline_dens(self, x, beta: float):
        """(LOP-30) The spline map's free densities: each column's share in plan, the outline field at its points (closed to
        the least gap, opened to the least width, through a Heaviside sharpened with the projection), times each voxel's
        step on the column's height (its height field at its centre, at least the least member); with the section rule,
        each point's own step on the column's height less its round's drop (`section_drop`), the voxel the mean of its
        points' shares times steps. With what `back` needs."""
        sp_, hh = self.spline, self.height
        x = np.asarray(x, float)
        coef = sp_["range"] * (2.0 * x[: sp_["n_phi"]] - 1.0)
        phi = sp_["B_phi"] @ coef  # at each cube's points
        k_ = max(beta, 2.0)
        jac_c = jac_o = None
        if sp_["sizes"] is not None:  # (LOP-30) the raw field is the geometry; the least width and gap are constraints
            if sp_["open"] is not None:  # a point in no least-width disc holds nothing, as the opening gave it
                phi = np.where(sp_["alone"], -sp_["range"], phi)
            b_phi = SPLINE_SHARP * beta
            th = np.tanh(b_phi * phi)
            u_s = 0.5 * (1.0 + th)
            return self._spline_pts(x, beta, phi, u_s, 0.5 * b_phi * (1.0 - th * th), sp_["avg"] @ u_s, None, None)
        if sp_["close"] is not None:  # the least gap: closed, -open(-phi), its slope J_open(-phi)
            phi_c, jac_c = open_heights(sp_["close"], -phi, k_)
            phi = -phi_c
        if sp_["open"] is not None:  # the least width
            phi, jac_o = open_heights(sp_["open"], phi, k_)
            phi = np.where(sp_["alone"], -sp_["range"], phi)
        b_phi = SPLINE_SHARP * beta
        th = np.tanh(b_phi * phi)
        u_s = 0.5 * (1.0 + th)
        du_s = 0.5 * b_phi * (1.0 - th * th)
        u = sp_["avg"] @ u_s  # each column's share in plan: its points' mean
        if sp_["pts_path"]:  # (LOP-30, F1-F2 and the soft distance) each point's own height (`_spline_pts`)
            return self._spline_pts(x, beta, phi, u_s, du_s, u, jac_o, jac_c)
        t = sp_["least"] + (hh["L"] - sp_["least"]) * (sp_["B_h"] @ x[sp_["n_phi"] :])
        if sp_["round"]:
            # the section rule: each point's member stands back at its free end by the round's drop at its distance inside
            # the outline (the field over its slope), and a cube's density is its points' mean of their metal in it
            if sp_["P"] is None:  # each free voxel's column's points
                qq = sp_["q"] ** 2
                sp_["P"] = hh["col"][:, None] * qq + np.arange(qq)[None, :]
            P = sp_["P"]
            gx, gy = sp_["Dx"] @ coef, sp_["Dy"] @ coef
            g = np.sqrt(gx * gx + gy * gy + SPLINE_SLOPE_FLOOR**2)
            a = phi / g
            drop, d_drop = section_drop(a, sp_["round"])
            s = np.tanh(beta * (t[hh["col"]][:, None] - drop[P] / hh["h"] - hh["pos"][:, None] - 0.5))
            big_s = 0.5 * (1.0 + s)
            return (u_s[P] * big_s).mean(axis=1), {"phi": phi, "u": u, "u_s": u_s, "du_s": du_s, "t": t, "S": big_s,
                                                   "dS": 0.5 * beta * (1.0 - s * s), "a": a, "g": g, "gx": gx, "gy": gy,
                                                   "d_drop": d_drop, "jac_o": jac_o, "jac_c": jac_c}  # fmt: skip
        s = np.tanh(beta * (t[hh["col"]] - hh["pos"] - 0.5))
        step = 0.5 * (1.0 + s)
        uc = u[hh["col"]]
        return uc * step, {"phi": phi, "u": u, "du_s": du_s, "t": t, "step": step, "uc": uc,
                           "dstep": 0.5 * beta * (1.0 - s * s), "jac_o": jac_o, "jac_c": jac_c}  # fmt: skip

    def _spline_pts(self, x, beta: float, phi, u_s, du_s, u, jac_o, jac_c):
        """(LOP-30; the engineer, 14 October 22:43-23:01: production-quality members, "smooth nice but shaped by the
        optimiser") Each point's own height, a cube's density its points' mean of their plan share times their metal in it:
        - F1, the smooth top: each family's height field the members' free end, out from the split (`E`), the column's
          height its distance past the column's own level, at least the least member (a softplus);
        - F2, the section window: the height at most the window's cap for how wide the member is there (the outline
          field opened again at each width, through a Heaviside), by a smooth minimum;
        - the section rule's round: less `section_drop` of the point's distance inside the outline, a soft minimum of
          its distances to the points outside it on its level."""
        sp_, hh = self.spline, self.height
        b_phi = SPLINE_SHARP * beta
        k_ = max(beta, 2.0)
        bh = sp_["B_h"] @ x[sp_["n_phi"] :]
        tp = sp_["top"]
        e_top = dt = None
        if tp is not None:
            e_top = tp["E_lo"] + tp["E_span"] * bh
            zt = e_top - tp["o_base"] - sp_["least"]
            t = sp_["least"] + np.logaddexp(0.0, TOP_SHARP * zt) / TOP_SHARP
            dt = 0.5 * (1.0 + np.tanh(0.5 * TOP_SHARP * zt))
        else:
            t = sp_["least"] + (hh["L"] - sp_["least"]) * bh
        big_t = t[sp_["sub_col"]]
        win, wide, cap, d_cap = sp_["window"], [], None, None
        if win is not None:
            cv = win["caps_vox"]
            cs = win.get("caps_split_vox")  # the side walls' gussets' own caps (`spline_setup`), by point
            sp_pts = win["split_pts"]
            cap = np.full(len(big_t), cv[0]) if cs is None else np.where(sp_pts, cs[0], cv[0])
            for k_w, (blk, alone_w) in enumerate(zip(win["open"], win["alone"], strict=True)):
                pw, jw = open_heights(blk, phi, k_)
                pw = np.where(alone_w, -sp_["range"], pw)
                thw = np.tanh(b_phi * pw)
                step_cap = (cv[k_w + 1] - cv[k_w]) if cs is None else np.where(sp_pts, cs[k_w + 1] - cs[k_w], cv[k_w + 1] - cv[k_w])
                cap = cap + step_cap * 0.5 * (1.0 + thw)
                wide.append({"jac": jw, "di": 0.5 * b_phi * (1.0 - thw * thw), "alone": alone_w, "dcap": step_cap})
            cap = cap + win["lift"][sp_["sub_col"]]  # measured from the smoothed level (`spline_setup`)
            if win["free"] is not None:  # the mounts' brackets: no cap (the smooth minimum then reads the height itself)
                cap = np.where(win["free"], CAP_FREE, cap)
            m_ = np.minimum(big_t, cap)
            ea, eb = np.exp(-CAP_SHARP * (big_t - m_)), np.exp(-CAP_SHARP * (cap - m_))
            t_m = m_ - np.log(ea + eb) / CAP_SHARP
            d_t, d_cap = ea / (ea + eb), eb / (ea + eb)
        else:
            t_m, d_t = big_t, np.ones_like(big_t)
        a = drop = d_drop = s_dist = None
        if sp_["round"]:
            ds = sp_["dist"]
            if ds is None:
                raise ValueError("the section rule on each point's own height reads its soft distance (`dist`)")
            s_dist = np.bincount(ds["p"], weights=(1.0 - u_s[ds["q"]]) * ds["w"], minlength=len(u_s)) + ds["floor"]
            a = -ds["eps"] * np.log(s_dist) - ds["d0"]
            drop, d_drop = section_drop(a, sp_["round"])
            t_p = t_m - drop / hh["h"]
        else:
            t_p = t_m
        if sp_["P"] is None:  # each free voxel's column's points
            qq = sp_["q"] ** 2
            sp_["P"] = hh["col"][:, None] * qq + np.arange(qq)[None, :]
            sp_["Csub"] = sp.csr_matrix((np.ones(len(sp_["sub_col"])), (sp_["sub_col"], np.arange(len(sp_["sub_col"])))),
                                        shape=(len(t), len(sp_["sub_col"])))  # fmt: skip
        P = sp_["P"]
        s = np.tanh(beta * (t_p[P] - hh["pos"][:, None] - 0.5))
        big_s = 0.5 * (1.0 + s)
        return (u_s[P] * big_s).mean(axis=1), {"pts": True, "phi": phi, "u": u, "u_s": u_s, "du_s": du_s, "t": t, "dt": dt,
                                               "E": e_top, "cap": cap, "d_t": d_t, "d_cap": d_cap, "wide": wide, "a": a,
                                               "drop": drop, "d_drop": d_drop, "s_dist": s_dist, "T": t_p, "S": big_s,
                                               "dS": 0.5 * beta * (1.0 - s * s), "jac_o": jac_o, "jac_c": jac_c}  # fmt: skip

    def _spline_back_pts(self, d: np.ndarray, c_: dict) -> np.ndarray:
        """(LOP-30) `back` through `_spline_pts`: the derivatives of the rows `d` (rows x free voxels) by the design
        variables (rows x n_design)."""
        sp_, hh = self.spline, self.height
        P = sp_["P"]
        qq = P.shape[1]
        n_pts, n_free = len(c_["u_s"]), d.shape[1]
        vox = np.repeat(np.arange(n_free), qq)
        w = c_["u_s"][P] * c_["dS"] / qq  # a voxel's density by its points' heights (voxels)
        g_us = np.asarray(sp.csr_matrix(((c_["S"] / qq).ravel(), (P.ravel(), vox)), shape=(n_pts, n_free)) @ d.T)
        g_tp = np.asarray(sp.csr_matrix((w.ravel(), (P.ravel(), vox)), shape=(n_pts, n_free)) @ d.T)
        g_phi = np.zeros_like(g_us)
        if c_["drop"] is not None:  # the round: by each point's distance inside, which reads its neighbours' shares
            ds = sp_["dist"]
            g_a = (-g_tp / hh["h"]) * c_["d_drop"][:, None]
            coef_pq = ds["eps"] * ds["w"] / c_["s_dist"][ds["p"]]  # d a_p / d u_q
            g_us = g_us + np.asarray(sp.csr_matrix((coef_pq, (ds["q"], ds["p"])), shape=(n_pts, n_pts)) @ g_a)
        g_t = g_tp * c_["d_t"][:, None]
        if c_["cap"] is not None:  # the window: by its caps, through each width's opening
            g_cap = g_tp * c_["d_cap"][:, None]
            for wd in c_["wide"]:
                g_pw = g_cap * (wd["dcap"] * wd["di"])[:, None]
                g_pw[wd["alone"]] = 0.0
                g_phi = g_phi + np.asarray(wd["jac"].T @ g_pw)
        g_phi = g_phi + g_us * c_["du_s"][:, None]
        g_col = np.asarray(sp_["Csub"] @ g_t)  # by each column's height (voxels)
        if sp_["top"] is not None:
            g_xh = np.asarray(sp_["B_h"].T @ (g_col * (sp_["top"]["E_span"] * c_["dt"])[:, None]))
        else:
            g_xh = (hh["L"] - sp_["least"]) * np.asarray(sp_["B_h"].T @ g_col)
        return np.vstack([self._spline_phi_back(g_phi, c_), g_xh]).T

    def spline_sizes(self, x, beta: float):
        """(LOP-30; 14 October 23:35: the openings on the 2 mm points made the smooth outline blocky, `raw_vs_opened.png`)
        The least width and the least gap as constraints on the raw field (the geometry): the metal thinner than the least
        width (the field's share inside less the opened field's) and the gaps narrower than the least gap (the closed
        field's share less the field's), each at most `spec["sizes"]` of the metal's share. Returns G (2), dG / dx (2 x
        n_design) and the two shares."""
        sp_ = self.spline
        x = np.asarray(x, float)
        coef = sp_["range"] * (2.0 * x[: sp_["n_phi"]] - 1.0)
        phi = sp_["B_phi"] @ coef
        # read at a sharpness of at least SPLINE_SIZES_BETA, so that it judges the line the drawing draws: at the first
        # iterations' soft field a level field's edge read 7-14 % thin and narrow (`sizes_probe.py`, 14 October 23:40)
        beta_s = max(beta, SPLINE_SIZES_BETA)
        k_ = beta_s
        b_phi = SPLINE_SHARP * beta_s

        def heav(v):
            th_ = np.tanh(b_phi * v)
            return 0.5 * (1.0 + th_), 0.5 * b_phi * (1.0 - th_ * th_)

        alone = sp_["alone"] if sp_["open"] is not None else None
        if alone is not None:  # a point in no least-width disc holds nothing (`_spline_dens`): neither thin nor a gap
            phi = np.where(alone, -sp_["range"], phi)
        u, du = heav(phi)
        if alone is not None:
            du = np.where(alone, 0.0, du)
        m_ = float(u.sum())
        rows = []
        vals = []
        share = float(sp_["sizes"])
        if sp_["open"] is not None:
            po, jo = open_heights(sp_["open"], phi, k_)
            po = np.where(sp_["alone"], -sp_["range"], po + _open_bias(sp_["open"], k_))
            uo, duo = heav(po)
            duo = np.where(sp_["alone"], 0.0, duo)
            v_w = float((u - uo).sum())
            d_vw = du - np.asarray(jo.T @ duo)
            vals.append(v_w / m_)
            rows.append((d_vw * m_ - v_w * du) / (share * m_ * m_))
        if sp_["close"] is not None:
            n_s = len(phi)
            if sp_["close"].get("virtual") is not None:  # the shell's places, metal to the closing (`least_width_blocks`)
                pc, jc = open_heights(sp_["close"], np.append(-phi, -sp_["range"]), k_)
                pc, jc = pc[:n_s], jc[:n_s, :n_s]
            else:
                pc, jc = open_heights(sp_["close"], -phi, k_)
            uc, duc = heav(-(pc + _open_bias(sp_["close"], k_)[:n_s]))
            alone_c = sp_["alone_close"]
            uc = np.where(alone_c, u, uc)  # a point in no closing block: no gap measured there
            duc = np.where(alone_c, 0.0, duc)
            v_g = float((uc - u).sum())
            d_vg = np.asarray(jc.T @ duc) - np.where(alone_c, 0.0, du)
            vals.append(v_g / m_)
            rows.append((d_vg * m_ - v_g * du) / (share * m_ * m_))
        g = np.asarray(vals) / share - 1.0
        d_x = np.zeros((len(rows), len(x)))
        for i_, r_ in enumerate(rows):
            d_x[i_, : sp_["n_phi"]] = 2.0 * sp_["range"] * np.asarray(sp_["B_phi"].T @ r_)
        return g, d_x, np.asarray(vals)

    def spline_bending(self, x):
        """(LOP-30, F3) Each field's bending (`spline_setup`'s `bend_ops`): the squared second differences of its control
        points in mm over its spacing squared, and their derivatives by x (fields x n_design)."""
        sp_, hh = self.spline, self.height
        x = np.asarray(x, float)
        vals, grads = [], np.zeros((len(sp_["bend_ops"]), len(x)))
        for i_, op in enumerate(sp_["bend_ops"]):
            xs_ = x[op["start"] : op["start"] + op["n"]]
            if op["kind"] == "outline":
                unit = 2.0 * sp_["range"]
            elif sp_["top"] is not None:  # the free end's span is one a field (its family and half)
                unit = float(sp_["top"]["E_span"][self._height_rows(op)[0]]) * hh["h"]
            else:
                unit = (hh["L"] - sp_["least"]) * hh["h"]
            r2 = op["D2"] @ (unit * xs_)
            vals.append(float(r2 @ r2) / op["spacing"] ** 2)
            grads[i_, op["start"] : op["start"] + op["n"]] = 2.0 * unit * np.asarray(op["D2"].T @ r2) / op["spacing"] ** 2
        return np.asarray(vals), grads

    def _height_rows(self, op: dict) -> np.ndarray:
        """The columns a height field's operator serves (its field's rows)."""
        fd = next(f_ for f_ in self.spline["fields"] if f_["kind"] == "height" and f_["half"] == op["half"] and f_["family"] == op["family"])
        return np.asarray(fd["rows"], np.int64)

    def _spline_phi_back(self, g_phi: np.ndarray, c_: dict) -> np.ndarray:
        """(LOP-30) A derivative by the outline field's opened values at the points (points x rows) taken back to its
        coefficients' design variables: through the opening, the closing and the basis."""
        sp_ = self.spline
        if c_["jac_o"] is None and sp_["sizes"] is not None and sp_["open"] is not None:  # a masked point is no coefficient's
            g_phi = np.where(sp_["alone"][:, None], 0.0, g_phi)
        if c_["jac_o"] is not None:
            g_phi = np.asarray(c_["jac_o"].T @ g_phi)
        if c_["jac_c"] is not None:
            g_phi = np.asarray(c_["jac_c"].T @ g_phi)
        return 2.0 * sp_["range"] * np.asarray(sp_["B_phi"].T @ g_phi)

    def spline_outline(self, x, beta: float, limit_mm: float):
        """(LOP-30, the engineer 14 October 19:04: calm members) The members' outline in plan, its length (mm) on the
        smooth outline: the opened field read through a soft edge (SPLINE_OUTLINE_SOFT mm), its slope's magnitude summed
        over the points (h / SPLINE_SUB apart, with their +x and +y neighbours on one level: a member meeting a wall, a
        boss or a level's edge pays nothing there). Returns G = length / limit - 1, dG / dx and the length."""
        sp_ = self.spline
        _, c_ = self._spline_dens(x, beta)
        th = np.tanh(c_["phi"] / SPLINE_OUTLINE_SOFT)
        us = 0.5 * (1.0 + th)
        dus = 0.5 * (1.0 - th * th) / SPLINE_OUTLINE_SOFT
        nx, ny = sp_["nb_x"], sp_["nb_y"]
        hx, hy = nx >= 0, ny >= 0
        dx = np.where(hx, us[np.where(hx, nx, 0)] - us, 0.0)
        dy = np.where(hy, us[np.where(hy, ny, 0)] - us, 0.0)
        delta = 1e-3
        mag = np.sqrt(dx * dx + dy * dy + delta * delta)
        step_mm = sp_["h"] / sp_["q"]
        length = step_mm * float(np.sum(mag - delta))
        g_us = -(dx + dy) / mag
        np.add.at(g_us, nx[hx], (dx / mag)[hx])
        np.add.at(g_us, ny[hy], (dy / mag)[hy])
        g_phi = (step_mm * g_us * dus)[:, None]
        g_x = np.r_[self._spline_phi_back(g_phi, c_)[:, 0], np.zeros(sp_["n_h"])]
        return length / limit_mm - 1.0, g_x / limit_mm, length

    def spline_columns(self, x, beta: float) -> dict:
        """(LOP-30) What the drawing reads of a spline run: each column's plan cell, half, level (its first free voxel along
        the pull), family (on the split or on a wall), its outline field (opened, mm) and its height (voxels)."""
        sp_, hh = self.spline, self.height
        _, c_ = self._spline_dens(x, beta)
        out = {"ij": hh["pts"].astype(np.int32), "half": sp_["half"].astype(np.int8), "base": sp_["base"].astype(np.int32),
               "on_split": sp_["on_split"], "t": c_["t"].astype(np.float32), "u": c_["u"].astype(np.float32),
               "sub_ij": sp_["sub_ij"].astype(np.int32), "sub_col": sp_["sub_col"].astype(np.int32),
               "sub_phi": c_["phi"].astype(np.float32), "sub_q": np.int32(sp_["q"])}  # fmt: skip
        if sp_["round"]:  # the section rule: each point's distance inside the outline (mm) and the round's radius
            out.update({"sub_a": c_["a"].astype(np.float32), "round_mm": np.float32(sp_["round"])})
        if c_.get("pts"):  # (LOP-30, F1-F2) what the drawing needs to draw each point's own height as the model does
            out.update({"pts_path": np.int8(1), "least": np.float32(sp_["least"]), "top_sharp": np.float32(TOP_SHARP),
                        "cap_sharp": np.float32(CAP_SHARP)})  # fmt: skip
            if c_["E"] is not None:
                out.update({"E": c_["E"].astype(np.float32), "o_base": sp_["top"]["o_base"].astype(np.float32)})
            if c_["cap"] is not None:
                out["sub_cap"] = c_["cap"].astype(np.float32)  # voxels
        return out

    def _height_dens(self, x, beta: float):
        """The height field's free densities, their slope by the columns' heights (voxels; the opened heights with the
        least width) and the least width's opening's Jacobian (None without it)."""
        hh = self.height
        # the columns' heights (voxels): the plan filter's of the design variables, or the parts' (LOP-26), opened to the
        # least width in plan (LOP-29)
        t0, jac = self._t0(x, beta)
        if hh.get("least"):
            # the least member (LOP-25, approach 2; the engineer, 12 October 09:54): a column's height counts only once it
            # passes `least`, a smooth step sharpened with the projection, so a thin layer of paint holds nothing and
            # costs nothing, and the metal goes where it makes members
            s = np.tanh(max(beta, 2.0) * (t0 - hh["least"]))
            g = 0.5 * (1.0 + s)
            slope = g + t0 * 0.5 * max(beta, 2.0) * (1.0 - s * s)
            t = t0 * g
        else:
            slope = np.ones_like(t0)
            t = t0
        tmin = hh.get("tmin")
        if tmin is not None:
            # the empty start (LOP-27): a wall's column stands at least its least height (the oil-tightness) and the
            # optimiser's own on top, not gated unless the walls are held plain (LOP-28, `_wall_extra`)
            wall = tmin > 0
            extra, d_extra = self._wall_extra(t0, beta)
            t = np.where(wall, tmin + extra, t)
            slope = np.where(wall, d_extra, slope)
        th = np.tanh(beta * (t[hh["col"]] - hh["pos"] - 0.5))
        return 0.5 * (1.0 + th), 0.5 * beta * (1.0 - th * th) * slope[hh["col"]], jac

    def project(self, rho, beta: float, eta: float | None = None):
        """The projection of filtered densities at sharpness beta and threshold eta (by default
        the projection's own): (projected, its slope)."""
        if not self.projection:
            return rho, np.ones_like(rho)
        eta = self.projection["eta"] if eta is None else eta
        den = math.tanh(beta * eta) + math.tanh(beta * (1.0 - eta))
        t = np.tanh(beta * (rho - eta))
        return (math.tanh(beta * eta) + t) / den, beta * (1.0 - t * t) / den

    def physical(self, x, beta: float, eta: float | None = None) -> np.ndarray:
        """The element densities a design vector gives: filtered, projected (at threshold eta, by
        default the projection's own) if a projection is set, then cast if a casting filter is set
        (frozen voxels 1)."""
        dens = np.ones(len(self.elem))
        if self.spline is not None:  # (LOP-30) the spline map, on the height field's columns
            dens[self.free_e] = self._spline_dens(x, beta)[0]
            return dens
        if self.height is not None:  # the height field: castable by construction
            dens[self.free_e] = self._height_dens(x, beta)[0]
            return dens
        dens[self.free_e] = self.project((self.hmat @ x) / self.hs, beta, eta)[0]
        return self.cast[0](dens) if self.cast else dens

    def back(self, d_dens, x, beta: float, eta: float | None = None) -> np.ndarray:
        """Derivatives with respect to the densities (one row per function, or one vector) taken
        back to the design variables: through the casting filter's backward pass (at its last
        forward, which must be `physical(x, beta, eta)`), the projection's slope and the filter's
        transpose. A frozen voxel's density is 1 whatever x is, so its entries carry nothing and
        are dropped."""
        rows = np.atleast_2d(d_dens)
        if self.spline is not None:  # (LOP-30) through each voxel's plan share and step, then the fields' bases
            sp_, hh = self.spline, self.height
            _, c_ = self._spline_dens(x, beta)
            d = np.where(self.frozen[None, :], 0.0, rows)[:, self.free_e]
            if c_.get("pts"):  # (LOP-30, F1-F2 and the soft distance)
                out = self._spline_back_pts(d, c_)
                return out if np.ndim(d_dens) == 2 else out[0]
            if sp_["round"]:  # the section rule: through each point's share and drop, its distance inside, the slopes
                P = sp_["P"]
                qq = P.shape[1]
                n_pts, n_free = len(c_["u_s"]), d.shape[1]
                vox = np.repeat(np.arange(n_free), qq)
                w = c_["u_s"][P] * c_["dS"] / qq  # a voxel's density by its points' free ends (voxels)
                g_t = np.asarray(hh["C"] @ (d * w.sum(axis=1)[None, :]).T)  # by each column's height (voxels)
                g_us = np.asarray(sp.csr_matrix(((c_["S"] / qq).ravel(), (P.ravel(), vox)), shape=(n_pts, n_free)) @ d.T)
                g_drop = -np.asarray(sp.csr_matrix((w.ravel(), (P.ravel(), vox)), shape=(n_pts, n_free)) @ d.T) / hh["h"]
                g_a = g_drop * c_["d_drop"][:, None]  # by each point's distance inside
                g_phi = g_us * c_["du_s"][:, None] + g_a / c_["g"][:, None]
                k_ = -(c_["phi"] / c_["g"] ** 3)[:, None] * g_a  # the distance's slope by the field's slopes
                g_slopes = np.asarray(sp_["Dx"].T @ (k_ * c_["gx"][:, None]) + sp_["Dy"].T @ (k_ * c_["gy"][:, None]))
                g_x_phi = self._spline_phi_back(g_phi, c_) + 2.0 * sp_["range"] * g_slopes
                out = np.vstack([g_x_phi, (hh["L"] - sp_["least"]) * np.asarray(sp_["B_h"].T @ g_t)]).T
                return out if np.ndim(d_dens) == 2 else out[0]
            g_u = np.asarray(hh["C"] @ (d * c_["step"][None, :]).T)  # by each column's plan share (columns x rows)
            g_t = np.asarray(hh["C"] @ (d * (c_["uc"] * c_["dstep"])[None, :]).T)  # by each column's height (voxels)
            g_phi = np.asarray(sp_["avg"].T @ g_u) * c_["du_s"][:, None]  # by each point's opened field
            out = np.vstack([self._spline_phi_back(g_phi, c_), (hh["L"] - sp_["least"]) * np.asarray(sp_["B_h"].T @ g_t)]).T
            return out if np.ndim(d_dens) == 2 else out[0]
        if self.height is not None:  # through each voxel's step on its column's height, then the plan filter
            hh = self.height
            _, slope, jac = self._height_dens(x, beta)
            d = np.where(self.frozen[None, :], 0.0, rows)[:, self.free_e] * slope[None, :]
            if hh.get("parts") is not None:  # through the parts' map (LOP-26): d height (voxels) / dx = J / h
                g = np.asarray(hh["C"] @ d.T).T / hh["h"]
                out = np.asarray(hh["parts"].jacobian(x).T @ g.T).T
                return out if np.ndim(d_dens) == 2 else out[0]
            g = np.asarray(hh["C"] @ d.T).T
            if jac is not None:  # through the least width's opening (LOP-29): by the heights before it
                g = np.asarray(jac.T @ g.T).T
            g = g * hh["L"]
            out = np.asarray(hh["M"].T @ g.T).T
            return out if np.ndim(d_dens) == 2 else out[0]
        slope = self.project((self.hmat @ x) / self.hs, beta, eta)[1]
        # every row at once (LOP-20, 11 October): the casting filter's backward over the stacked
        # rows, then the filter's transpose on them as one matrix
        d = np.where(self.frozen[None, :], 0.0, rows)
        d = self.cast[1](d) if self.cast else d
        out = np.asarray(self.hmat.T @ (d[:, self.free_e] * (slope / self.hs)[None, :]).T).T
        return out if np.ndim(d_dens) == 2 else out[0]

    def analyse(self, dens, objective: str, penal: float = PENAL, adjoints: bool = True) -> dict:
        """One finite-element solve at the densities `dens` (the modelled elements', in `elem`
        order), SIMP's penalty `penal`: both load cases on one single-precision factor
        (`fe.SingleFactor`, refined in double to 1e-10), every seat's ratio to its line, and the
        derivatives the objective needs, with respect to the densities, by adjoint solves on the
        same factor (refined to `ADJOINT_TOL`: a gradient needs fewer digits than the answer):
        - `compliance`: both cases' compliance (no adjoint: it is self-adjoint);
        - `tilt`, `misalignment`: the p-norm (P_NORM) of all the ratios, one adjoint a case;
        - `misalignment_bound`: every ratio's own derivative, one adjoint per seat and case (12).
        Returns the ratios, the value and its derivative (or each ratio's), the displacements and
        the time each part took. With `adjoints=False` it stops after the answers and keeps the
        factor: `finish` then takes the derivatives on it (a trial point GCMMA accepts), `release`
        frees it (one it refuses). One factor is open at a time."""
        from fe import SingleFactor

        t0 = time.time()
        clock = {}
        e_scale = self.stiff_e * (E_MIN + dens**penal * (1 - E_MIN))
        # (LOP-29) with the modes read, metal joined to nothing takes LOOSE_STIFF of its stiffness (as LOOSE_MASS of its
        # mass): it carries nothing, and hanging on near-empty cubes it leaves the single factor nearly singular
        loose = self.loose(dens) if (self.mode_count and LOOSE_STIFF < 1.0) else None
        k_share = np.where(loose, LOOSE_STIFF, 1.0) if (loose is not None and loose.any()) else None
        if k_share is not None:
            e_scale = e_scale * k_share
        if os.environ.get("LOOP_FAST", "0") != "0":
            # LOP-19: the stiffness assembled on the GPU into the pattern found once, its factor
            # refactorised in place (`fast_factor.py`; the same answers as below to 5e-11)
            if getattr(self, "_gpu", None) is None:
                from fast_factor import GpuStiffness

                self._gpu = (GpuStiffness(self.rows, self.cols, self.n_dof, None, self.ke, T=self.T, dof=self.dof) if self.kinematic
                             else GpuStiffness(self.rows, self.cols, self.n_dof, self.free, self.ke))  # fmt: skip
            factor = self._gpu.factor(e_scale)
            clock["assemble"], clock["factor"] = factor.assemble_s, factor.factor_s
        else:
            vals = (e_scale[:, None] * self.ke.ravel()[None, :]).ravel()
            k = sp.coo_matrix((vals, (self.rows, self.cols)), shape=(self.n_dof, self.n_dof)).tocsr()
            del vals
            kff = (self.T.T @ k @ self.T).tocsr() if self.kinematic else k[self.free][:, self.free]
            del k
            clock["assemble"] = time.time() - t0
            t1 = time.time()
            factor = SingleFactor(kff)
            clock["factor"] = time.time() - t1
        steps = []
        try:
            t1 = time.time()
            sols = [factor.solve(self.rhs[:, c]) for c in range(self.n_cases)]
            uf = np.column_stack([s_[0] for s_ in sols])
            steps += [s_[1] for s_ in sols]
            clock["solves"] = time.time() - t1
            ratios, total = {}, 0.0
            grad = np.zeros_like(uf)
            adjoint_rhs = {}
            for key, rr, line, l1, l2 in self.seats:
                for c in range(self.n_cases):
                    # the misalignment (grade.py's) for these objectives, and read beside compliance
                    if objective in ("misalignment", "misalignment_bound", "compliance", "compliance_bound"):
                        lx, ly = self.lean_of[(key, c)]
                        v1, v2 = float((l1 @ uf[:, c])[0]) - lx, float((l2 @ uf[:, c])[0]) - ly
                        rows_ = (l1, l2)
                    else:
                        th = rr @ uf[:, c]
                        v1, v2 = float(th[0]), float(th[1])
                        rows_ = (rr[0], rr[1])
                    tilt = math.hypot(v1, v2)
                    ratio = tilt / line
                    ratios[(key, c)] = ratio
                    if tilt > 0:
                        # d ratio / du = (v1 dv1/du + v2 dv2/du) / (tilt line)
                        d_ratio = (v1 * rows_[0].toarray().ravel() + v2 * rows_[1].toarray().ravel()) / (tilt * line)
                    else:
                        d_ratio = np.zeros(self.n_q)
                    if objective in ("misalignment_bound", "compliance_bound"):
                        adjoint_rhs[(key, c)] = d_ratio
                    elif objective in ("tilt", "misalignment"):
                        total += ratio**P_NORM
                        # d(ratio^p)/du = p ratio^(p-1) d ratio / du
                        grad[:, c] += P_NORM * ratio ** (P_NORM - 1) * d_ratio
            beds, bed_rhs = {}, {}
            if objective == "compliance_bound":
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
        out = {"ratios": ratios, "u": u, "clock": clock, "steps": steps, "objective": objective,
               "beds": beds, "bed_vector": np.array([beds[kc] for kc in self.bed_keys]) if beds else np.zeros(0), "_bed_rhs": bed_rhs,
               "_factor": factor, "_grad": grad, "_adjoint_rhs": adjoint_rhs, "_dens": dens, "_penal": penal, "_t0": t0,
               "_k_share": k_share, "loose_stiff_voxels": int(loose.sum()) if loose is not None else 0}  # fmt: skip
        if objective == "misalignment_bound":
            out["ratio_vector"] = np.array([ratios[kc] for kc in self.keys])
            out["value"] = float(out["ratio_vector"].max())
        elif objective in ("tilt", "misalignment"):
            out["value"] = total ** (1.0 / P_NORM)
            out["ratio_vector"] = np.array([ratios[kc] for kc in self.keys])
        else:
            out["value"] = float(sum(self.rhs[:, c] @ uf[:, c] for c in range(self.n_cases)))  # f'u = sum of e u'k_e u
            out["ratio_vector"] = np.array([ratios[kc] for kc in self.keys])  # the seats' misalignment, read beside
        clock["total"] = time.time() - t0
        return self.finish(out) if adjoints else out

    def with_modes(self, out: dict) -> dict:
        """(LOP-29) The modes on an analysis's kept factor, once (`_modes`): called at the point a step takes (`finish`)
        and at the binary check, never at a trial GCMMA may refuse (12 s an eigen-solve at 4 mm)."""
        if self.mode_count and "modes_hz" not in out and out.get("_factor") is not None:
            try:
                self._modes(out)
            except BaseException:
                self.release(out)
                raise
        return out

    def _modes(self, out: dict) -> None:
        """(LOP-29) The model's first `mode_count` natural frequencies (Hz) at an analysis's densities, on its kept factor, and
        each one's derivative by the element densities, into `out` ("modes_hz", "d_modes_hz"). Shift-invert Lanczos about zero
        as `fe.modes` (scipy's eigsh reads the stiffness only through the factor); the housing's own mass lumped at the
        voxels' corners, as FE's modes are the housing's alone; near-empty voxels' mass taken down (`mode_mass`). A mode's
        slope by an element's density: its mass-normalised shape's strain energy there times the stiffness's slope, less its
        eigenvalue times its kinetic share there times the mass's slope."""
        from scipy.sparse.linalg import LinearOperator, eigsh

        t1 = time.time()
        factor, dens, penal = out["_factor"], out["_dens"], out["_penal"]
        mi, dmi = mode_mass(dens)
        loose = self.loose(dens)  # (LOP-29) metal joined to nothing, the drawing's to drop: its mass taken down
        if LOOSE_MASS < 1.0 and loose.any():
            mi, dmi = np.where(loose, LOOSE_MASS * mi, mi), np.where(loose, LOOSE_MASS * dmi, dmi)
        out["loose_voxels"] = int(loose.sum())
        unit = DENSITY * self.h**3 * self.mass_share_e
        m_dof = np.zeros(self.n_dof)
        np.add.at(m_dof, self.dof, np.repeat((unit * mi / 8.0)[:, None], 24, axis=1))
        m_red = (self.T.T @ sp.diags(m_dof) @ self.T).tocsr()  # the housing's lumped mass, reduced (a rigid set's at its centre)
        n = self.n_q
        tol = float(os.environ.get("LOOP_MODE_TOL", "1e-5"))  # the derivative check tightens it (1e-10)
        op = LinearOperator((n, n), matvec=lambda v: factor.solve(np.asarray(v, float).ravel(), tol=min(1e-7, 0.1 * tol))[0], dtype=np.float64)
        a_shape = LinearOperator((n, n), matvec=lambda v: v, dtype=np.float64)  # not read in shift-invert mode
        v0 = getattr(self, "_mode_start", None)  # the last step's modes summed: Lanczos starts near them
        lam, vec = eigsh(a_shape, k=self.mode_count, M=m_red, sigma=0.0, OPinv=op, which="LM", tol=tol,
                         v0=v0 if v0 is not None and len(v0) == n else None)  # fmt: skip
        self._mode_start = vec.sum(axis=1)
        order = np.argsort(lam)
        lam, vec = np.maximum(lam[order], 0.0), vec[:, order]
        hz = np.sqrt(lam * 1000.0) / (2.0 * math.pi)  # N/mm over kg: 1000 /s² a unit
        d_k = self.stiff_e * penal * dens ** (penal - 1) * (1 - E_MIN)
        if out.get("_k_share") is not None:  # (LOP-29) metal joined to nothing: its stiffness's share, as `analyse` took it
            d_k = d_k * out["_k_share"]
        d_m = unit * dmi / 8.0
        full = np.zeros(self.n_dof)
        d_hz = np.zeros((len(hz), len(self.elem)))
        for i in range(len(hz)):
            phi = vec[:, i] / math.sqrt(float(vec[:, i] @ (m_red @ vec[:, i])))
            full = np.asarray(self.T @ phi).ravel()
            pe = full[self.dof]
            strain = np.einsum("ej,jk,ek->e", pe, self.ke, pe)
            kinetic = (pe * pe).sum(axis=1)
            d_hz[i] = 1000.0 * (d_k * strain - lam[i] * d_m * kinetic) / (8.0 * math.pi**2 * max(float(hz[i]), 1e-9))
        d_hz[:, self.frozen] = 0.0
        out["modes_hz"], out["d_modes_hz"] = hz, d_hz
        out["clock"]["modes"] = time.time() - t1

    def loose(self, dens: np.ndarray) -> np.ndarray:
        """(LOP-29) Each element joined to nothing: in its half, metal (a density of 0.5 or more, or fixed) face-joined to
        no other than its own piece, the half's largest piece of metal its body; the voids between count as no join."""
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
        # (LOP-30, 14 October 19:07) a fixed part is never loose: a mount's lug is held at its hole and drawn whatever joins it;
        # counted loose, a lug the optimiser left unjoined lost its mass and stiffness, the mount vanished from the model and
        # dropping it cost nothing (`baseline2_spl` lost mount-3 and sat on two mounts at 370 Hz)
        return on & ~joined[tuple(self.ijk.T)] & ~self.frozen

    def release(self, out: dict) -> None:
        """Free a kept factor (a trial point refused)."""
        factor = out.pop("_factor", None)
        if factor is not None:
            factor.close()

    def finish(self, out: dict) -> dict:
        """The derivatives of an analysis kept with `adjoints=False`, by adjoint solves on its
        factor, which is then freed."""
        self.with_modes(out)  # LOP-29: the point taken: its modes, while its factor is open
        factor = out["_factor"]
        objective, dens, penal = out["objective"], out["_dens"], out["_penal"]
        clock, steps = out["clock"], out["steps"]
        try:
            t1 = time.time()
            if objective in ("misalignment_bound", "compliance_bound"):
                lam = {}
                for kc, rhs in out["_adjoint_rhs"].items():
                    sol, n_steps, _ = factor.solve(rhs, tol=ADJOINT_TOL)
                    lam[kc] = sol
                    steps.append(n_steps)
                lam_bed = {}
                for kc, rhs in out.get("_bed_rhs", {}).items():
                    sol, n_steps, _ = factor.solve(rhs, tol=ADJOINT_TOL)
                    lam_bed[kc] = sol
                    steps.append(n_steps)
            elif objective in ("tilt", "misalignment"):
                grad = out["_grad"]
                lam = np.column_stack([factor.solve(grad[:, c])[0] if np.any(grad[:, c]) else np.zeros(self.n_q) for c in range(self.n_cases)])
            clock["adjoints"] = time.time() - t1
        finally:
            self.release(out)
        d_e = self.stiff_e * penal * dens ** (penal - 1) * (1 - E_MIN)  # d stiffness scale / d density
        if out.get("_k_share") is not None:  # (LOP-29) metal joined to nothing: its stiffness's share, held at this point
            d_e = d_e * out["_k_share"]
        ue = out["u"][self.dof]  # (elements, 24, cases)
        if objective in ("misalignment_bound", "compliance_bound"):
            d_ratios = np.empty((len(self.keys), len(self.elem)))
            for i, kc in enumerate(self.keys):
                full = np.asarray(self.T @ lam[kc]).ravel()
                le = full[self.dof]
                # d ratio / d density_e = -d_e lambda_e' k_e u_e (the case's u)
                d_ratios[i] = -d_e * np.einsum("ei,ei->e", le @ self.ke, ue[:, :, kc[1]])
            out["d_ratios"] = d_ratios
            if lam_bed:
                d_beds = np.empty((len(self.bed_keys), len(self.elem)))
                for i, kc in enumerate(self.bed_keys):
                    full = np.asarray(self.T @ lam_bed[kc]).ravel()
                    d_beds[i] = -d_e * np.einsum("ei,ei->e", full[self.dof] @ self.ke, ue[:, :, kc[1]])
                out["d_beds"] = d_beds
        if objective == "misalignment_bound":
            pass
        elif objective in ("tilt", "misalignment"):
            lf = np.asarray(self.T @ lam).reshape(self.n_dof, self.n_cases)
            le = lf[self.dof]
            mixed = np.einsum("eic,ij,ejc->e", le, self.ke, ue)  # lambda' k_e u, summed over the cases
            out["d_value"] = -d_e * mixed
        else:
            energy = np.einsum("eic,ij,ejc->e", ue, self.ke, ue)
            out["d_value"] = -d_e * energy
        for key in ("_grad", "_adjoint_rhs", "_bed_rhs", "_dens"):
            out.pop(key, None)
        clock["total"] = time.time() - out.pop("_t0")
        return out


def _uniform_start(vox: Voxels, target: float, beta: float) -> np.ndarray:
    """The uniform design whose densities, after the filter, the projection and the casting
    filter, weigh the budget (in voxels): a feasible start for MMA."""
    lo_v, hi_v = 0.0, 1.0
    for _ in range(40):
        mid = 0.5 * (lo_v + hi_v)
        if vox.physical(np.full(vox.n_design, mid), beta)[vox.free_e].sum() > target:
            hi_v = mid
        else:
            lo_v = mid
    return np.full(vox.n_design, lo_v)


def solve_model(model, budget_kg: float, iterations: int, objective: str, start=None, beta0: float = 1.0,
                first: int = 1, on_iteration=None):  # fmt: skip
    """SIMP over the model's free voxels under a mass budget (kg of free voxels), on `Voxels`.
    Each iteration is solved by `fe.py`'s scaled single-precision factor with its answers refined
    in double (the rule: single precision on purpose; LOP-3's double factor broke it).
    Objectives:
    - `compliance`: both cases' compliance;
    - `tilt`: a p-norm of every seat's own rotation over its line (LOP-3's);
    - `misalignment`: a p-norm of every seat's misalignment over its line, as `grade.py` reads it:
      the seat against its shaft's chord through its two seats' centres, plus the shaft's own lean
      at the bearing from the load tool. Its gradient by one adjoint solve a case.
    These three are updated by optimality criteria (OC) with a damping exponent and move limits.
    On the misalignment that never settled: OC drops every positive sensitivity, and the p-norm
    (p = 6) follows whichever seat is worst, so with two seats near the worst each step swung the
    field toward the other one (runs 2 and 3 alternated 0.159 <-> 0.196, the step at its limit).
    - `misalignment_bound`: the bound formulation, solved by GCMMA (`mma.py`): minimise z subject
      to every seat's ratio in every case <= z (12 constraints) and the mass <= the budget. Each
      ratio keeps its own gradient (12 adjoint solves an iteration on the same factor), so a step
      weighs every seat near the worst at once. Plain MMA did not settle here (6 mm, 10
      October 00:31): its approximations promised ratios below zero (z = 0 in 4 of 10
      subproblems), the steps overshot, the worst swung 2.3 <-> 4.0 and the mass 3.7 <-> 5.2 kg.
      GCMMA checks each proposal by one more solve there (no adjoints) and, where an
      approximation fell below its ratio, makes it more convex and solves again (at most
      `INNER_MOST` times); a step taken keeps its promise, so the worst falls while the mass
      holds. The adjoints are taken on the factor of the point accepted. Every iteration the
      ratios are scaled so that the worst is 10, for MMA's constants (c = 1000); the scale does not
      move the subproblem's optimum. The move limit is `projection["mma_move"]` / sqrt(beta), so
      it shrinks as the projection sharpens, where the same step in x moves the densities
      further. It starts from the uniform field that weighs the budget.
      With `projection["robust"]` (a threshold's shift, d), the robust formulation (Wang,
      Lazarov & Sigmund 2011): the same filtered field projected three times, eroded (eta + d),
      nominal (eta) and dilated (eta - d), and every seat's ratio in every case bounded in all
      three (36 constraints); the mass is the nominal's. Without it the bound loop leaned on grey
      voxels: split 7.73's field read 0.087 × its line, the same field as metal or air 4.1-6.3
      (cut at 0.3-0.7; `voxel_vs_fe.py`, 10 October 05:24), for a seat's tilt is a difference
      between its two ends, and partly stiff voxels balanced the two. Each realisation is one
      more factor and its own 12 adjoints, one factor open at a time; a try GCMMA may refuse is
      solved without adjoints and freed at once, the last try with them. With
      `projection["robust_p"]`, each seat and case's three ratios are one constraint, their
      p-norm (12 constraints, not 36), which keeps MMA's subproblem well posed as they converge.
    Every bound run ends with the binary check: the nominal field at 0.5, all metal or air, read
    by the same model (`binary` in the result).
    `model["penalty_ramp"]` (iterations), when given, raises SIMP's penalty from 1 to 3 in steps
    of 0.5 over the first so many iterations (the usual continuation; each step is a new problem,
    which the bound loop reads afresh). It is there for the conditioning: on the
    grey start the casting filter leaves each column's last voxel at the split its thinnest
    (about 0.06, so E ~ 2e-4 at p = 3), and a cover joined only at the bolts hangs on those voxels
    alone; at p = 1 they start 300 times stiffer, and the single factor refines.
    `model["cast"]`, when given, is a casting filter (forward, backward) applied to the projected
    densities: the mass and the stiffness both read its output. `start` (design variables),
    `beta0` and `first` (the first iteration's number, for the projection's schedule) resume a
    run, else the start is uniform, beta 1 and the count 1. `on_iteration(it, x, beta)`, when
    given, is called after each iteration with the next one's design and sharpness (a
    checkpoint)."""
    from mma import MMA

    vox = Voxels(model)
    h = model["h"]
    free_e, frozen, elem = vox.free_e, vox.frozen, vox.elem
    projection = vox.projection
    beta = [float(beta0)]
    target = budget_kg / DENSITY / h**3
    bound = objective == "misalignment_bound"
    # LOP-19 (the engineer, 10 October 15:14: "only one solve for one load case"): one weighted
    # measure of every seat's misalignment, the p-norm (P_NORM) of the ratios over their lines, by
    # GCMMA under the mass: one forward and one adjoint solve a case and realisation.
    # `compliance_gcmma` (the engineer, 10 October 16:11, the papers' first objective): the same loop
    # with the realisations' compliance (f'u) as the objective, its gradient from the forward solve
    # alone (compliance is self-adjoint): one solve a case and realisation.
    # `compliance_tilt` (the engineer, 10 October 22:11: "yes", to every bearing's tilt held under its
    # line beside the stiffness): the compliance as the objective, as `compliance_gcmma`, and every
    # seat's misalignment in every case a constraint, at most its line, each seat and case's
    # realisations one constraint (`robust_p`); one adjoint a seat and case on each factor.
    pnorm = objective in ("misalignment_pnorm", "compliance_gcmma", "compliance_tilt", "mass_tilt", "modes_tilt")
    tilted = objective in ("compliance_tilt", "mass_tilt", "modes_tilt")
    maxmode = objective == "modes_tilt"  # (LOP-29) the lowest modes raised, the budget a ceiling
    if maxmode and not model.get("modes"):
        raise ValueError("modes_tilt raises the model's modes: give --modes (the orders' gaps) so they are read")
    # `mass_tilt` (LOP-24; the engineer, 11 October 20:04, on the thick paint): the least metal that
    # holds every seat's tilt and bed (with the factor of safety, `model["safety"]`), the budget only a
    # ceiling. Under `compliance_tilt` the whole budget is spent: once the lines are met the rest of the
    # metal goes where it lowers the compliance a little, spread over the shell.
    least = objective == "mass_tilt"
    analysed = {"misalignment_pnorm": "misalignment", "compliance_gcmma": "compliance", "compliance_tilt": "compliance_bound",
                "mass_tilt": "compliance_bound", "modes_tilt": "compliance_bound"}.get(objective, objective)
    complied = analysed in ("compliance", "compliance_bound")
    # LOP-20 (the engineer, 10 October 18:21: "realistic shapes, taking loads optimally"): the
    # greatest member, a casting rule as a constraint, so the metal forms ribs and walls, never
    # lumps. Within a ball of `radius_vox` voxels round each free voxel the placed metal's share is
    # at most `alpha` (Guest 2009's maximum length scale, as Wu, Aage, Westermann & Sigmund 2018's
    # local volume constraint), aggregated by `greatest_share` and taken on the dilated design, so
    # that every realisation keeps it. A slab of thickness t fills (3/4)(t/R) - (t/R)^3/16 of a
    # ball it crosses: 0.6 at t = 0.85 R. The frozen skin, seats and mounts are not counted.
    greatest = model.get("max_member")
    share_ball, share_cells = None, 0
    if greatest:
        if not pnorm:
            raise ValueError("the greatest member is a constraint of the p-norm and compliance loops")
        share_ball, share_cells = local_ball(vox.ijk[free_e], greatest["radius_vox"])
        say(f"the greatest member: {greatest['mm']:g} mm, a ball of {greatest['radius_vox']:.2f} voxels ({share_cells} cells) at most {greatest['alpha']:g} metal")
    share_fixed = None
    if greatest and greatest.get("fixed_mm"):
        # (LOP-30, the engineer 14 October 23:01) the lump rule counting the fixed metal at the split (the sealing land, the
        # bolts' bosses, within `fixed_mm` of the split), as castability counts it: a member hanging from the split had
        # thickened the land into blocks of 21-26 mm (`baseline2_spl3`, `lump_where.py`) the rule never saw
        from scipy.spatial import cKDTree

        band = np.flatnonzero(vox.frozen & (np.abs(vox.ijk[:, 2] + 0.5 - model["k_split"]) <= float(greatest["fixed_mm"]) / h))
        share_fixed = np.asarray(cKDTree(vox.ijk[band].astype(float)).query_ball_point(vox.ijk[free_e].astype(float), r=greatest["radius_vox"],
                                                                                        return_length=True), float)  # fmt: skip
        say(f"the lump rule counts the fixed metal within {greatest['fixed_mm']:g} mm of the split ({len(band):,} cubes: the land, the bolts' bosses)"
            + (f"; each ball's placed metal at most what the fixed leaves of {greatest['alpha']:g}, never under {greatest['floor']:g}"
               if greatest.get("floor") else ""))  # fmt: skip

    def share_of(dens_all):
        return greatest_share(share_ball, share_cells, dens_all[free_e], greatest["alpha"], greatest.get("p"), fixed=share_fixed,
                              floor=greatest.get("floor"))  # fmt: skip

    # The members' plan rule (LOP-23, `plan_rule`): at most a width wide and a gap apart, in plan
    plan = model.get("plan_rule")
    plan_fixed, plan_alpha = None, PLAN_ALPHA
    if plan:
        if not pnorm:
            raise ValueError("the members' plan rule is a constraint of the p-norm and compliance loops")
        plan_alpha = float(plan.get("alpha", PLAN_ALPHA))
        plan_fixed = plan_rule(vox.ijk[free_e], model["k_split"], h, plan["width_mm"], plan["gap_mm"])
        if vox.height is not None and vox.height.get("tmin") is not None:  # LOP-28: the empty start's walls are no members
            hh_ = vox.height
            plan_fixed["mask"] = (hh_["pos"] >= np.ceil(hh_["tmin"][hh_["col"]] - 1e-6)).astype(float)
        say(f"the members' plan rule: {plan['width_mm']:g} mm wide at most, grown by half a {plan['gap_mm']:g} mm gap, "
            f"the grown presence's share at most {plan_alpha:g}; {plan_fixed['columns']:,} columns")

    def plan_of(dens_all):
        return plan_share(plan_fixed, dens_all[free_e], plan_alpha)

    # The members' outline in plan (LOP-26, `perimeter_pairs`): at most `model["perimeter"]["mm"]`, so that the metal forms
    # fewer, longer, continuous members, not dashes or worms
    perim = model.get("perimeter")
    perim_pairs = None
    if perim:
        if vox.height is None:
            raise ValueError("the outline's limit is the height field's (--height-field)")
        perim_pairs = perimeter_pairs(vox.height, len(free_e))
        say(f"the outline in plan at most {perim['mm']:g} mm ({perim_pairs['pairs']:,} neighbouring columns)")

    def perim_of(dens_all):
        return perimeter_value(perim_pairs, dens_all[free_e], h, float(perim["mm"]))

    # The semantic rules (LOP-28, `bending_operator`): each marked region's mean bending at most its bound (`model["bending"]`:
    # the regions' weights a column, their bounds as an RMS curvature in 1/m), and each bracket's metal at least its floor
    # (`model["brackets"]`: each free voxel's bracket or -1, each bracket's floor in voxels), on the one design of the p-norm
    # and compliance loops
    bend = model.get("bending")
    bend_op, bend_lim = None, None
    if bend:
        if vox.height is None or vox.height.get("parts") is not None:
            raise ValueError("the bending limit is the height field's (--height-field), not the parts'")
        if vox.height.get("open") is not None or vox.spline is not None:
            raise ValueError("the bending limit with the least width (LOP-29) or the spline map (LOP-30) is not built")
        bend_op = bending_operator(vox.height, vox.ijk[free_e], np.asarray(bend["weights"], float))
        bend_kinds = np.asarray(bend.get("kinds", np.zeros(len(bend["rms_per_m"]))), int)
        bend_lim = bending_bound(bend["rms_per_m"], bend_kinds, h)
        say("the bending limits: " + "; ".join(f"{nm} ({'double curvature' if k_ == 1 else 'bending'}) at most {r_:g} 1/m ({int((w_ > 0).sum()):,} centres)"
                                               for nm, k_, r_, w_ in zip(bend["names"], bend_kinds, bend["rms_per_m"], bend_op["w"], strict=True)))  # fmt: skip

    def bend_of(x_at):
        """The bending constraints at x: B / bound - 1, their derivatives by x, and each region's measure (1/m)."""
        t_at, slope = vox.column_heights(x_at, beta[0])
        b_, d_t = bending_value(bend_op, t_at, bend_kinds)
        hh_ = vox.height
        d_x = np.asarray(hh_["M"].T @ (d_t * (slope * hh_["L"])[None, :]).T).T
        return b_ / bend_lim - 1.0, d_x / bend_lim[:, None], bending_rms(b_, bend_kinds, h)

    # (LOP-30, the engineer 14 October 19:04-19:06: calm members) the members' outline's length on the smooth outline
    # (`Voxels.spline_outline`), at most `model["spline"]["outline_mm"]`: a function of x itself, as the bending
    out_mm = float((model.get("spline") or {}).get("outline_mm") or 0.0) if vox.spline is not None else 0.0
    if out_mm > 0:
        say(f"the members' outline at most {out_mm:g} mm long (the smooth outline, read on its points)")

    def outline_of(x_at):
        """The outline's constraint at x: length / limit - 1, its derivative by x (one row), and the length (mm)."""
        g_o, d_o, length_ = vox.spline_outline(x_at, beta[0], out_mm)
        return np.r_[g_o], d_o[None, :], length_

    # (LOP-30, F3; the engineer 14 October 23:01) each field's bending at most its limit (`model["spline"]["bend"]`: by
    # "outline<half>", "split<half>", "wall<half>"), after the outline's length: functions of x itself
    sb_spec = (model.get("spline") or {}).get("bend") if vox.spline is not None else None
    sb_idx, sb_lim = [], None
    if sb_spec:
        for i_, op in enumerate(vox.spline["bend_ops"]):
            key_ = f"{'outline' if op['kind'] == 'outline' else op['family']}{op['half']}"
            if key_ in sb_spec:
                sb_idx.append(i_)
        sb_lim = np.array([float(sb_spec[f"{'outline' if vox.spline['bend_ops'][i_]['kind'] == 'outline' else vox.spline['bend_ops'][i_]['family']}{vox.spline['bend_ops'][i_]['half']}"])
                           for i_ in sb_idx])  # fmt: skip
        say("the fields' bending (F3) at most: " + ", ".join(
            f"{vox.spline['bend_ops'][i_]['kind']} {vox.spline['bend_ops'][i_].get('family') or ''} half {vox.spline['bend_ops'][i_]['half']} {l_:.4g}"
            for i_, l_ in zip(sb_idx, sb_lim, strict=True)))  # fmt: skip

    def sbend_of(x_at):
        """The fields' bending constraints at x: B / limit - 1, their derivatives by x, and the bendings."""
        v_, d_ = vox.spline_bending(x_at)
        v_, d_ = v_[sb_idx], d_[sb_idx]
        return v_ / sb_lim - 1.0, d_ / sb_lim[:, None], v_

    # (LOP-30, 14 October 23:35) the least width and gap as constraints on the raw field (`Voxels.spline_sizes`), last
    n_sizes = 0
    if vox.spline is not None and vox.spline["sizes"] is not None:
        n_sizes = int(vox.spline["open"] is not None) + int(vox.spline["close"] is not None)
        say(f"the least width and gap held as constraints on the smooth field: each at most {vox.spline['sizes']:g} of the metal")

    def sizes_of(x_at):
        return vox.spline_sizes(x_at, beta[0])

    brk = model.get("brackets")
    brk_rows, brk_least, brk_of_vox = None, None, None
    if brk:
        brk_of_vox = np.asarray(brk["of"], np.int64)
        if len(brk_of_vox) != len(free_e):
            raise ValueError(f"the brackets' map has {len(brk_of_vox):,} free voxels, the model {len(free_e):,}")
        brk_least = np.asarray(brk["least_vox"], float)
        brk_rows = np.zeros((len(brk_least), len(elem)))
        for k_, least_k in enumerate(brk_least):
            brk_rows[k_, free_e[brk_of_vox == k_]] = -1.0 / least_k
        say("each bracket's metal at least: " + ", ".join(f"{nm} {lv * h**3 / 1000:.1f} cm³" for nm, lv in zip(brk["names"], brk_least, strict=True)))

    # (LOP-29) the modes held clear of the gear orders (`model["modes"]`: the margin each side), read on each analysis's
    # factor (`Voxels._modes`), as constraints after the brackets' floors (`mode_gaps`)
    mode_orders, mode_margin, mode_floor, floor_margin = None, 0.0, 0.0, 0.0
    if model.get("modes"):
        mode_orders, mode_margin = gear_orders(model), float(model["modes"]["margin"])
        mode_floor = float(model["modes"].get("first") or 0.0)  # (LOP-29) the first mode's least, Hz
        floor_margin = float(model["modes"].get("first_margin") or 0.0)  # its own margin (14 October: none by default)
        say("the modes held clear of the gear orders: " + ", ".join(f"{nm} {f_:.0f} Hz ± {100 * mode_margin:g} %" for nm, f_ in mode_orders.items())
            + (f"; the lowest {FLOOR_MODES} modes each at least {mode_floor:.0f} Hz, held at {mode_floor * (1 + floor_margin):.0f}" if mode_floor > 0 else "")
            + f"; {vox.mode_count} modes read each analysis")  # fmt: skip

    def modes_of(state):
        return mode_gaps(state["modes_hz"], state["d_modes_hz"], mode_orders, mode_margin, mode_floor, floor_margin)

    def brk_of(dens_all):
        """The brackets' constraints at the densities: 1 - metal / floor, and each bracket's metal (cm³)."""
        metal = np.array([dens_all[free_e][brk_of_vox == k_].sum() for k_ in range(len(brk_least))])
        return 1.0 - metal / brk_least, metal * h**3 / 1000.0

    if start is not None:
        x = np.clip(np.asarray(start, float), 0.0, 1.0)
        if len(x) != vox.n_design:
            raise ValueError(f"the start has {len(x):,} design variables, the model {vox.n_design:,}")
    elif bound or pnorm:
        x = _uniform_start(vox, target, beta[0])
    else:
        x = np.full(vox.n_design, min(0.5, target / len(free_e)))
    # (LOP-32, the engineer 15 October 16:10: "Reward. add rules") the members' fairing rules (`member_fair`), a stage from a
    # converged run: on a temporary skeleton of the members, rebuilt every `every` iterations from the current heights, each
    # measure's local worst case (a KS aggregate of its points over its limit) at most 0, the limits tightened from the
    # start's own worst to their targets over `over` iterations. The topology frozen: a column farther than `band` cubes from
    # the start's metal (in its half, level and family) holds nothing, so no member is born elsewhere and none is traded for
    # three new ones
    fair = model.get("fair")
    fair_names, fair_st = (), {}
    if fair:
        if vox.height is None or vox.spline is not None or vox.height.get("parts") is not None or vox.features is not None:
            raise ValueError("the fairing rules are the plain height field's (--height-field): not the spline map's, features' or parts'")
        import member_fair as mf
        from scipy import ndimage as ndi

        fair_names = tuple(nm for nm, v_ in fair["targets"].items() if v_)
        fair_cols = mf.column_info(model["kind"], model["n"], int(model["k_split"]), elem, free_e)
        t_s, _ = vox.column_heights(x, beta[0])
        band_c = float(fair.get("band") or 0.0)
        if band_c > 0:
            allowed = np.zeros(fair_cols["n_cols"], bool)
            # in plan over the whole half, every column holding half a cube or more counted: frozen level by level and family by
            # family from columns of a cube or more, the first try (`lw8_fair1`, 15 October 16:31) held out two one-cube columns
            # joining mount-3's lug to its arm, and the beds read 1.35 x from the start
            for hf_ in (0, 1):
                idx = np.flatnonzero(fair_cols["half"] == hf_)
                ij_ = fair_cols["ij"][idx]
                met = t_s[idx] >= 0.5
                if not met.any():
                    continue
                o_ = ij_.min(axis=0)
                grid_ = np.zeros(tuple(ij_.max(axis=0) - o_ + 1), bool)
                grid_[ij_[met, 0] - o_[0], ij_[met, 1] - o_[1]] = True
                allowed[idx] = ndi.distance_transform_edt(~grid_)[ij_[:, 0] - o_[0], ij_[:, 1] - o_[1]] <= band_c
            vox.height["M"] = (sp.diags(allowed.astype(float)) @ vox.height["M"]).tocsr()  # a column outside reads no height
            say(f"the topology frozen: {int(allowed.sum()):,} of {len(allowed):,} columns, those within {band_c:g} cubes in plan of the "
                "start's metal in their half, may hold metal")  # fmt: skip
            t_s, _ = vox.column_heights(x, beta[0])
        fair_st["frame"] = mf.Frame(fair_cols, t_s, model["lo"], h)
        raw_ = fair_st["frame"].raw(t_s)
        fair_st["start"] = {nm: 1.05 * float(np.abs(raw_[nm]).max()) if len(raw_[nm]) else 1.0 for nm in fair_names}
        fair_st["it"] = first
        fr_ = fair_st["frame"]
        say(f"the fairing rules: {len(fr_.branches)} branches on the members' skeleton, {fr_.n_pts:,} points ({len(fr_.at):,} taken, "
            "junctions, ends, stubs and webs masked); each measure's worst from the start's to its target over "
            f"{int(fair['over'])} iterations, the skeleton rebuilt every {int(fair['every'])}: "
            + ", ".join(f"{nm} {fair_st['start'][nm] / 1.05:.3f} -> {min(float(fair['targets'][nm]), fair_st['start'][nm]):.3f}"
                        for nm in fair_names))  # fmt: skip

    def fair_limits() -> dict:
        frac = min(1.0, max(0.0, (fair_st["it"] - first) / max(1.0, float(fair["over"]))))
        out_ = {}
        for nm in fair_names:
            l0 = max(fair_st["start"][nm], 1e-9)
            out_[nm] = l0 * (min(float(fair["targets"][nm]), l0) / l0) ** frac
        return out_

    def fair_of(x_at):
        """The fairing constraints at x: each measure's KS over its limit less 1, their derivatives by x (through the least
        member's gate, the least width's opening and the plan filter), and each measure's worst point and limit."""
        t_at, slope = vox.column_heights(x_at, beta[0])
        _, jac = vox._t0(x_at, beta[0])
        lims = fair_limits()
        vals = fair_st["frame"].values(t_at, lims, float(fair.get("rho") or KS_RHO), fair_names)
        hh_ = vox.height
        g_, rows_, worst_ = [], [], {}
        for nm in fair_names:
            g_k, d_t, v_k = vals[nm]
            d0 = d_t * slope
            if jac is not None:
                d0 = np.asarray(jac.T @ d0).ravel()
            rows_.append(np.asarray(hh_["M"].T @ (d0 * hh_["L"])).ravel())
            g_.append(g_k)
            worst_[nm] = (float(v_k.max()) if len(v_k) else 0.0, float(lims[nm]))
        return np.asarray(g_, float), np.vstack(rows_), worst_

    say(f"{objective} objective; {len(vox.held)} nodes held at the mounts; {len(vox.seats)} seats watched; budget {budget_kg:.3f} kg of free voxels")
    ramp = model.get("penalty_ramp") or 0
    # (LOP-30, 15 October 01:21; the engineer: "Yes" to 4 mm ribs) a spline run's densities are shares of real geometry
    # (its points in plan, its heights along the pull), so a cube half filled by a 4 mm rib is half as stiff, not an
    # eighth: SIMP's penalty 1 (`model["penal_most"]`). With 3, a 4 mm rib straddling two cubes read 4 x too soft, so the
    # optimiser would lay ribs along the grid
    pen_most = float(model.get("penal_most") or PENAL)

    def penalty_at(it: int) -> float:
        """SIMP's penalty at iteration `it`: from 1 to 3 in steps of 0.5 over the ramp (each
        step makes a new problem, so few of them), then 3 (or the run's `penal_most`)."""
        return pen_most if ramp <= 0 else min(pen_most, 1.0 + 0.5 * math.floor(4.0 * (it - 1) / ramp))

    def grey_of(dens_free):
        return float(((dens_free > 0.1) & (dens_free < 0.9)).sum() / max(1, (dens_free > 0.1).sum()))

    def named(rat):
        return {f"{k[0][0]} {k[0][1]} case {k[1]}": v for k, v in rat.items()}

    history = []
    ratios = {}
    realisations, binary = None, None
    if bound or pnorm:
        robust = projection.get("robust") if projection else None
        eta0 = projection["eta"] if projection else None
        etas = [eta0 + robust, eta0, eta0 - robust] if robust else [eta0]
        names = ["eroded", "nominal", "dilated"] if robust else ["nominal"]
        nom = names.index("nominal")
        # With `projection["robust_p"]`, each seat and case's realisations are one constraint, their
        # p-norm (at p 16 at most 7 % over their worst, on the safe side). As the three converge,
        # their 36 constraints come in near-duplicate threes, MMA's dual system turns nearly
        # singular, and its subproblems slowed from 11 s an iteration to 77 s by iteration 25
        # (robust split 7.73, 10 October 06:06).
        robust_p = projection.get("robust_p") if robust else None
        if least and robust:
            raise ValueError("the least-mass objective runs one design: no robust formulation with it")
        n_tilt = (len(vox.keys) if robust_p or not robust else len(etas) * len(vox.keys)) if tilted else 0
        # the bearing beds beside the tilt (`model["beds_mm"]`), on the nominal design
        beds_on = tilted and bool(vox.bed_keys)
        n_beds = len(vox.bed_keys) if beds_on else 0
        if plan_fixed is not None and robust:
            raise ValueError("the members' plan rule is held on the nominal design alone: no robust formulation with it")
        if perim_pairs is not None and (robust or not pnorm):
            raise ValueError("the outline's limit is held on one design of the p-norm and compliance loops: no robust formulation with it")
        if (bend_op is not None or brk_rows is not None or mode_orders is not None) and (robust or not pnorm):
            raise ValueError("the semantic rules and the modes are held on one design of the p-norm and compliance loops: no robust formulation with them")
        n_brk = len(brk_least) if brk_rows is not None else 0
        n_bend = len(bend_lim) if bend_op is not None else 0
        if out_mm > 0 and (robust or not pnorm):
            raise ValueError("the outline's length (LOP-30) is held on one design of the p-norm and compliance loops: no robust formulation with it")
        n_bend += 1 if out_mm > 0 else 0  # the outline's length after the bending: both functions of x itself
        if sb_idx and (robust or not pnorm):
            raise ValueError("the fields' bending (LOP-30) is held on one design of the p-norm and compliance loops")
        n_bend += len(sb_idx)  # the fields' bending (F3)
        if n_sizes and (robust or not pnorm):
            raise ValueError("the least width and gap as constraints (LOP-30) are held on one design of the p-norm and compliance loops")
        n_bend += n_sizes  # the least width and gap last
        if fair_names and (robust or not pnorm):
            raise ValueError("the fairing rules (LOP-32) are held on one design of the p-norm and compliance loops")
        n_bend += len(fair_names)  # (LOP-32) the fairing rules after them
        n_modes =2 * len(mode_orders) + (FLOOR_MODES if mode_floor > 0 else 0) if mode_orders is not None else 0
        first_mode = 1 + (share_ball is not None) + (plan_fixed is not None) + (perim_pairs is not None) + n_tilt + n_beds + n_brk
        mode_rows = slice(first_mode, first_mode + n_modes)
        m = (1 + (share_ball is not None) + (plan_fixed is not None) + (perim_pairs is not None) + n_tilt + n_beds + n_brk + n_modes + n_bend) if pnorm else (len(vox.keys) if robust_p else len(etas) * len(vox.keys)) + 1
        dil = len(etas) - 1  # the dilated realisation (the nominal without the robust formulation)
        # GCMMA's convexity terms carried a tenth over between iterations: the seats' gradients
        # gather on the voxels round them, so the notes' start (a tenth of the mean gradient)
        # left 5 inner iterations in most iterations at 6 mm (10 October 01:00).
        a_mma = np.zeros(m) if pnorm else np.r_[np.ones(m - 1), 0.0]  # the bound's z enters the seats' constraints only
        opt = MMA(vox.n_design, m, 0.0, 1.0, a0=1.0, a=a_mma, c=np.full(m, 1000.0), d=np.ones(m), carry=0.1)
        mma_move = projection.get("mma_move", 0.2) if projection else 0.2

        def realised(x_at, penal_at: float, with_adjoints: bool) -> list[dict]:
            """Each realisation's analysis at x_at, with its densities (`dens`). One factor is
            open at a time: a robust analysis without adjoints is freed at once, its answers kept."""
            outs = []
            if not np.all(np.isfinite(x_at)):  # LOP-24: a design with NaN handed to the factoriser hung it
                raise RuntimeError(f"the design variables are not all finite: {int((~np.isfinite(x_at)).sum())} of {len(x_at)}")
            for eta in etas:
                d_ = vox.physical(x_at, beta[0], eta)
                if not np.all(np.isfinite(d_)):
                    raise RuntimeError(f"the densities are not all finite: {int((~np.isfinite(d_)).sum())} of {len(d_)}")
                o_ = vox.analyse(d_, analysed, penal_at, adjoints=with_adjoints)
                if robust and not with_adjoints:
                    vox.release(o_)
                o_["dens"] = d_
                outs.append(o_)
            return outs

        def all_ratios(outs: list[dict]) -> np.ndarray:
            return np.concatenate([o_["ratio_vector"] for o_ in outs])

        def constraints(outs: list[dict]):
            """The constraints' values and, with `robust_p`, the weights of each realisation's
            ratio in its seat and case's p-norm (d norm / d ratio); without it every ratio."""
            if not robust_p:
                return all_ratios(outs), None
            rr_ = np.vstack([o_["ratio_vector"] for o_ in outs])  # (realisations, seats and cases)
            norm = (rr_**robust_p).sum(axis=0) ** (1.0 / robust_p)
            return norm, (rr_ / norm[None, :]) ** (robust_p - 1)

        states, state_settings = None, None
        since = 0  # iterations at the current sharpness
        for it in range(first, iterations + 1):
            t0 = time.time()
            penal = penalty_at(it)
            factors = 0
            if fair_names:  # (LOP-32) the limits' schedule, and the skeleton rebuilt from the current heights every so often
                fair_st["it"] = it
                if it > first and (it - first) % int(fair["every"]) == 0:
                    t_now, _ = vox.column_heights(x, beta[0])
                    fair_st["frame"] = mf.Frame(fair_cols, t_now, model["lo"], h)
            if states is None or state_settings != (beta[0], penal):
                # The problem changed (the start, a sharper projection, a higher penalty): the
                # point's ratios and gradients afresh.
                states = realised(x, penal, True)
                state_settings = (beta[0], penal)
                factors += len(etas)
                say(f"it {it:3d}: beta {beta[0]:g}, p {penal:.2f}: the point read afresh, worst {all_ratios(states).max():.4f}x its line (voxel model"
                    + (", " + ", ".join(f"{nm} {s_['ratio_vector'].max():.4f}" for nm, s_ in zip(names, states, strict=True)) if robust else "")
                    + f"), mass {states[nom]['dens'][free_e].sum() * DENSITY * h**3:.3f} kg")  # fmt: skip
            # The current point's functions (the ratios scaled so the worst is 10, and the mass)
            # and their gradients. `back` reads the casting filter at its last forward pass, so
            # each realisation's forward is taken again just before its own backward.
            f0, df0 = 0.0, np.zeros(len(x))
            if pnorm and len(etas) == 1:
                # One design (no robust formulation): every function is read at the same point, so
                # all their derivatives go back to x in one pass (LOP-20, 11 October): the objective,
                # the mass, the greatest member, every seat's tilt and bed, in that order (as below).
                s_ = states[0]
                if least:  # the objective: the metal's share of the ceiling, scaled to 10
                    scale = 10.0
                    f0 = scale * float(s_["dens"][free_e].sum()) / target
                    rows_d = [scale * vox.mass_rows[None, :] / target, vox.mass_rows[None, :] / target]
                elif maxmode:  # (LOP-29) 10 x MODE_REF over the lowest modes' smooth minimum (KS)
                    hz_, dhz_ = np.asarray(s_["modes_hz"], float), np.asarray(s_["d_modes_hz"], float)
                    low_ = np.argsort(hz_)[:FLOOR_MODES]
                    w_ = np.exp(-KS_RHO * (hz_[low_] - hz_[low_].min()) / MODE_REF)
                    ks_hz = float(hz_[low_].min() - MODE_REF / KS_RHO * np.log(w_.sum()))
                    d_ks = ((w_ / w_.sum())[:, None] * dhz_[low_]).sum(axis=0)
                    scale = 10.0
                    f0 = scale * MODE_REF / ks_hz
                    rows_d = [(-scale * MODE_REF / ks_hz**2) * d_ks[None, :], vox.mass_rows[None, :] / target]
                else:
                    p_all = float(s_["value"])
                    scale = 10.0 / max(p_all, 1e-12)
                    f0 = scale * p_all
                    outer = scale if complied else scale * p_all ** (1.0 - P_NORM) / P_NORM
                    rows_d = [outer * s_["d_value"][None, :], vox.mass_rows[None, :] / target]
                g = [s_["dens"][free_e].sum() / target - 1.0]
                if share_ball is not None:
                    g_s, d_s, _ = share_of(s_["dens"])
                    d_all = np.zeros(len(elem))
                    d_all[free_e] = d_s
                    rows_d.append(d_all[None, :])
                    g.append(g_s)
                if plan_fixed is not None:  # the members' plan rule, after the greatest member (as below)
                    g_p, d_p, _ = plan_of(s_["dens"])
                    d_all = np.zeros(len(elem))
                    d_all[free_e] = d_p
                    rows_d.append(d_all[None, :])
                    g.append(g_p)
                if perim_pairs is not None:  # the outline in plan, after the plan rule (as below)
                    g_q, d_q, _ = perim_of(s_["dens"])
                    d_all = np.zeros(len(elem))
                    d_all[free_e] = d_q
                    rows_d.append(d_all[None, :])
                    g.append(g_q)
                if tilted:
                    rows_d.append(s_["d_ratios"])
                    g.extend(s_["ratio_vector"] - 1.0)
                if beds_on:
                    rows_d.append(s_["d_beds"])
                    g.extend(s_["bed_vector"] - 1.0)
                if brk_rows is not None:  # the brackets' floors (LOP-28), after the beds
                    rows_d.append(brk_rows)
                    g.extend(brk_of(s_["dens"])[0])
                if mode_orders is not None:  # the gap round each gear order (LOP-29), after the floors
                    g_m, d_gm, _ = modes_of(s_)
                    rows_d.append(d_gm)
                    g.extend(g_m)
                vox.physical(x, beta[0], etas[0])
                back_all = vox.back(np.vstack(rows_d), x, beta[0], etas[0])
                df0, dg, g = back_all[0], back_all[1:], np.asarray(g, float)
                if bend_op is not None:  # the bending limits (LOP-28), last: functions of x itself, not of the densities
                    g_b, dg_b, _ = bend_of(x)
                    g, dg = np.r_[g, g_b], np.vstack([dg, dg_b])
                if out_mm > 0:  # (LOP-30) the outline's length, after them
                    g_o, dg_o, _ = outline_of(x)
                    g, dg = np.r_[g, g_o], np.vstack([dg, dg_o])
                if sb_idx:  # (LOP-30, F3) the fields' bending
                    g_sb, dg_sb, _ = sbend_of(x)
                    g, dg = np.r_[g, g_sb], np.vstack([dg, dg_sb])
                if n_sizes:  # (LOP-30) the least width and gap
                    g_sz, dg_sz, _ = sizes_of(x)
                    g, dg = np.r_[g, g_sz], np.vstack([dg, dg_sz])
                if fair_names:  # (LOP-32) the fairing rules, last
                    g_f, dg_f, _ = fair_of(x)
                    g, dg = np.r_[g, g_f], np.vstack([dg, dg_f])
            elif pnorm:
                # The objective: the p-norm of every ratio in every realisation, scaled to 10 (the
                # scale moves no optimum); each realisation's d_value is d(sum of ratio^p)/d dens,
                # so d(norm) = norm^(1-p) / p times their sum, taken back realisation by realisation.
                p_all = sum(s_["value"] ** P_NORM for s_ in states) ** (1.0 / P_NORM)
                scale = 10.0 / max(p_all, 1e-12)
                f0 = scale * p_all
                for eta, s_ in zip(etas, states, strict=True):
                    vox.physical(x, beta[0], eta)
                    if complied:  # d_value is d(compliance)/d dens: d(norm) = (c / norm)^(p-1) of it
                        outer = scale * (s_["value"] / p_all) ** (P_NORM - 1.0)
                    else:  # d_value is d(sum of ratio^p)/d dens: d(norm) = norm^(1-p) / p of it
                        outer = scale * p_all ** (1.0 - P_NORM) / P_NORM
                    df0 = df0 + vox.back(outer * s_["d_value"], x, beta[0], eta)
                vox.physical(x, beta[0], etas[nom])
                g = np.r_[states[nom]["dens"][free_e].sum() / target - 1.0]
                dg = vox.back(vox.mass_rows[None, :] / target, x, beta[0], etas[nom])
                if share_ball is not None:  # the greatest member, on the dilated design
                    g_s, d_s, _ = share_of(states[dil]["dens"])
                    d_all = np.zeros(len(elem))
                    d_all[free_e] = d_s
                    vox.physical(x, beta[0], etas[dil])
                    g = np.r_[g, g_s]
                    dg = np.vstack([dg, vox.back(d_all, x, beta[0], etas[dil])])
                if tilted:  # every seat and case's misalignment at most its line
                    values, weights = constraints(states)
                    g = np.r_[g, values - 1.0]
                    rows = []
                    for k_, (eta, s_) in enumerate(zip(etas, states, strict=True)):
                        vox.physical(x, beta[0], eta)
                        part = vox.back(s_["d_ratios"] if weights is None else weights[k_][:, None] * s_["d_ratios"], x, beta[0], eta)
                        if weights is None or not rows:
                            rows.append(part)
                        else:
                            rows[0] = rows[0] + part  # the realisations' p-norm: their sum
                    dg = np.vstack([dg, *rows])
                if beds_on:  # every seat's bearing bed at most the design to beat's
                    vox.physical(x, beta[0], etas[nom])
                    g = np.r_[g, states[nom]["bed_vector"] - 1.0]
                    dg = np.vstack([dg, vox.back(states[nom]["d_beds"], x, beta[0], etas[nom])])
            else:
                values, weights = constraints(states)
                scale = 10.0 / max(float(values.max()), 1e-12)
                g = np.r_[scale * values, states[nom]["dens"][free_e].sum() / target - 1.0]
                rows = []
                for k_, (eta, s_) in enumerate(zip(etas, states, strict=True)):
                    vox.physical(x, beta[0], eta)
                    d_ = scale * (s_["d_ratios"] if weights is None else weights[k_][:, None] * s_["d_ratios"])
                    part = vox.back(d_, x, beta[0], eta)
                    if weights is None or not rows:
                        rows.append(part)
                    else:
                        rows[0] = rows[0] + part  # the p-norm's derivative: its realisations' sum
                vox.physical(x, beta[0], etas[nom])
                rows.append(vox.back(vox.mass_rows[None, :] / target, x, beta[0], etas[nom]))
                dg = np.vstack(rows)
            move = mma_move / math.sqrt(beta[0])
            t1 = time.time()
            x_new = opt.propose(x, f0, df0, g, dg, move=move)
            t_mma = time.time() - t1
            # GCMMA: the proposal's promise checked by one solve there; while an approximation
            # fell below its ratio, that approximation is made more convex and the step re-solved.
            inner = 0
            while True:
                last_try = inner >= INNER_MOST
                trials = realised(x_new, penal, bool(robust) and last_try)  # the last robust try is taken: its adjoints at once
                factors += len(etas)
                mass_new = trials[nom]["dens"][free_e].sum() / target - 1.0
                if pnorm:
                    if maxmode:  # predicted from the step's slope (no eigen-solve at a trial, as the gaps)
                        f0_new = f0 + float(df0 @ (x_new - x))
                    else:
                        f0_new = scale * (mass_new + 1.0) if least else scale * sum(t_["value"] ** P_NORM for t_ in trials) ** (1.0 / P_NORM)
                    g_new = np.r_[mass_new] if share_ball is None else np.r_[mass_new, share_of(trials[dil]["dens"])[0]]
                    if plan_fixed is not None:
                        g_new = np.r_[g_new, plan_of(trials[nom]["dens"])[0]]
                    if perim_pairs is not None:
                        g_new = np.r_[g_new, perim_of(trials[nom]["dens"])[0]]
                    if tilted:
                        g_new = np.r_[g_new, constraints(trials)[0] - 1.0]
                    if beds_on:
                        g_new = np.r_[g_new, trials[nom]["bed_vector"] - 1.0]
                    if brk_rows is not None:
                        g_new = np.r_[g_new, brk_of(trials[nom]["dens"])[0]]
                    if mode_orders is not None:  # predicted from the step's gaps and their slopes (no eigen-solve at a trial)
                        g_new = np.r_[g_new, g[mode_rows] + dg[mode_rows] @ (x_new - x)]
                    if bend_op is not None:
                        g_new = np.r_[g_new, bend_of(x_new)[0]]
                    if out_mm > 0:
                        g_new = np.r_[g_new, outline_of(x_new)[0]]
                    if sb_idx:
                        g_new = np.r_[g_new, sbend_of(x_new)[0]]
                    if n_sizes:
                        g_new = np.r_[g_new, sizes_of(x_new)[0]]
                    if fair_names:
                        g_new = np.r_[g_new, fair_of(x_new)[0]]
                else:
                    f0_new = 0.0
                    g_new = np.r_[scale * constraints(trials)[0], mass_new]
                kept = opt.conservative(f0_new, g_new, promise=PROMISE)
                if kept or last_try:
                    break
                for t_ in trials:
                    vox.release(t_)
                t1 = time.time()
                x_new = opt.tighten(f0_new, g_new, promise=PROMISE)
                t_mma += time.time() - t1
                inner += 1
            if not robust:
                trials = [vox.finish(trials[0])]  # the adjoints at the point taken, on its factor
            elif not last_try:
                trials = realised(x_new, penal, True)  # taken before the last try: its adjoints afresh
                factors += len(etas)
            change = float(np.abs(x_new - x).max())
            x, states = x_new, trials
            r = all_ratios(states)
            ratios = states[nom]["ratios"]
            w_name, w_state = max(zip(names, states, strict=True), key=lambda p: float(p[1]["ratio_vector"].max()))
            worst = max(w_state["ratios"].items(), key=lambda kv: kv[1])
            value = worst[1]
            worst_seat = f"{worst[0][0][0]} {worst[0][0][1]} case {worst[0][1]}" + (f", {w_name}" if robust else "")
            free_now = states[nom]["dens"][free_e]
            grey = grey_of(free_now)
            clock = states[nom]["clock"]
            # the bound z, or with the p-norm the objective itself, in the ratios' own units
            if least:  # the objective itself: the metal placed, kg
                z_bound = float(free_now.sum()) * DENSITY * h**3
            elif maxmode:  # the lowest modes' smooth minimum, Hz
                hz_now = np.sort(np.asarray(states[nom]["modes_hz"], float))[:FLOOR_MODES]
                z_bound = float(hz_now.min() - MODE_REF / KS_RHO * np.log(np.exp(-KS_RHO * (hz_now - hz_now.min()) / MODE_REF).sum()))
            else:
                z_bound = sum(s_["value"] ** P_NORM for s_ in states) ** (1.0 / P_NORM) if pnorm else opt.last["z"] / scale
            active = int(np.sum(r >= 0.98 * r.max()))
            share_now = share_of(states[dil]["dens"])[2] if share_ball is not None else None
            plan_now = plan_of(states[nom]["dens"])[2] if plan_fixed is not None else None
            perim_now = perim_of(states[nom]["dens"])[2] if perim_pairs is not None else None
            bend_g, bend_now = bend_of(x)[0::2] if bend_op is not None else (None, None)
            out_now = outline_of(x)[2] if out_mm > 0 else None
            sb_now = sbend_of(x)[2] / sb_lim if sb_idx else None
            sz_now = sizes_of(x)[2] if n_sizes else None
            fair_g, _, fair_now = fair_of(x) if fair_names else (None, None, None)
            brk_g, brk_now = brk_of(states[nom]["dens"]) if brk_rows is not None else (None, None)
            modes_g, modes_note = modes_of(states[nom])[0::2] if mode_orders is not None else (None, None)
            row = {"iteration": it, "objective": value, "change": change, "worst_ratio": worst[1], "greatest_share": share_now, "plan_share": plan_now,
                   "outline_mm": perim_now if perim_now is not None else out_now,
                   "bending_rms_per_m": None if bend_now is None else [float(v_) for v_ in bend_now],
                   "bracket_cm3": None if brk_now is None else [float(v_) for v_ in brk_now],
                   "modes_hz": None if mode_orders is None else [round(float(v_), 1) for v_ in states[nom]["modes_hz"]],
                   "mode_gaps": None if modes_g is None else [float(v_) for v_ in modes_g],
                   "fair": None if fair_now is None else {nm: [round(w_, 5), round(l_, 5)] for nm, (w_, l_) in fair_now.items()},
                   "worst_seat": worst_seat, "beta": beta[0], "penalty": penal,
                   "grey_share": grey, "seconds": time.time() - t0, "mass_kg": float(free_now.sum()) * DENSITY * h**3,
                   "move": move, "ratios": named(ratios), "bound": z_bound, "active": active, "inner": inner,
                   "conservative": bool(kept), "factors": factors, "mma_seconds": t_mma, "newton_steps": opt.last["newton_steps"],
                   "clock": {k: round(v, 3) for k, v in clock.items()}, "solve_steps": states[nom]["steps"]}  # fmt: skip
            if robust:
                row["worst_by"] = {nm: float(s_["ratio_vector"].max()) for nm, s_ in zip(names, states, strict=True)}
            if beds_on:
                row["bed_worst"] = float(states[nom]["bed_vector"].max())
            label = "metal placed (kg)" if least else ("the lowest modes' smooth minimum (Hz)" if maxmode else ("compliance (N mm)" if complied else ("p-norm" if pnorm else "bound")))
            say(f"it {it:3d}: worst {worst[1]:.4f}x its line at {worst_seat} (voxel model), {label} {z_bound:.4f}, "
                + (f"the worst bed {row['bed_worst']:.4f}x the design to beat's; " if beds_on else "")
                + (", ".join(f"{nm} {v_:.4f}" for nm, v_ in row["worst_by"].items()) + "; " if robust else "")
                + (f"greatest member's share {share_now:.3f} (at most {greatest['alpha']:g}); " if share_ball is not None else "")
                + (f"plan share {plan_now:.3f} (at most {plan_alpha:g}); " if plan_fixed is not None else "")
                + (f"the outline {perim_now:.0f} mm (at most {perim['mm']:g}); " if perim_pairs is not None else "")
                + ("bending " + ", ".join(f"{v_:.0f}/{r_:g}" for v_, r_ in zip(bend_now, bend["rms_per_m"], strict=True)) + " 1/m; " if bend_op is not None else "")
                + (f"the outline {out_now:.0f} mm (at most {out_mm:g}); " if out_mm > 0 else "")
                + ("bending of its limits " + ", ".join(f"{v_:.2f}" for v_ in sb_now) + "; " if sb_idx else "")
                + ("thin / narrow-gap share " + ", ".join(f"{v_:.4f}" for v_ in sz_now) + f" (at most {vox.spline['sizes']:g}); " if n_sizes else "")
                + ("fairing (worst / limit) " + ", ".join(f"{nm} {w_:.3f}/{l_:.3f}" for nm, (w_, l_) in fair_now.items()) + "; " if fair_names else "")
                + ("brackets " + ", ".join(f"{v_:.1f}/{lv * h**3 / 1000:.1f}" for v_, lv in zip(brk_now, brk_least, strict=True)) + " cm³; " if brk_rows is not None else "")
                + ("modes " + ", ".join(f"{v_:.0f}" for v_ in states[nom]["modes_hz"][:10]) + " Hz, gaps "
                   + ", ".join(f"{v_:+.3f}" for v_ in modes_g) + f" (modes {clock.get('modes', 0.0):.1f} s); " if mode_orders is not None else "")
                + f"{active} within 2 % of it, mass {row['mass_kg']:.3f} kg, change {change:.3f} (move {move:.3f}), beta {beta[0]:g}, p {penal:.2f}, grey {grey:.2f}; "
                f"{inner} inner{'' if kept else ' (not yet conservative, taken)'}, {factors} factors, {row['seconds']:.1f} s "
                f"(the nominal's last: factor {clock['factor']:.1f}, 2 solves {clock['solves']:.1f}, 12 adjoints {clock.get('adjoints', 0.0):.1f}; MMA {t_mma:.1f})")  # fmt: skip
            history.append(row)
            since += 1
            sharpest = not projection or beta[0] >= projection["beta_most"]
            # The sharpness doubles every `every` iterations; with `settle` (LOP-19, one run instead
            # of stages) as soon as the design settles at it (a step under `settle`, or the result
            # flat: the objective within SETTLE_BETA of itself over SETTLE_WINDOW iterations; at
            # least 5 iterations at this sharpness and the full penalty), at most `every` after the
            # last. At the last sharpness the run stops when no voxel moves (a step under 0.01) or,
            # the budget spent and the greatest member held, the result is flat within SETTLE_STOP
            # (the engineer, 11 October 00:51: "stop the run if the result is not changing enough";
            # a few voxels flickering kept the runs going to their last iteration).
            settle = projection.get("settle") if projection else None
            here = history[-since:] if since else []
            flat_beta = since >= SETTLE_WINDOW and _flat(here, SETTLE_WINDOW, SETTLE_BETA)
            flat_stop = since >= SETTLE_WINDOW and _flat(here, SETTLE_WINDOW, SETTLE_STOP)
            spent = least or float(free_now.sum()) / target - 1.0 >= -MASS_SPENT  # the least-mass objective spends no budget
            held = (share_now is None or share_now <= greatest["alpha"] + 0.005) and (plan_now is None or plan_now <= plan_alpha + 0.005) and (
                perim_now is None or perim_now <= 1.005 * float(perim["mm"])) and (bend_g is None or float(bend_g.max()) <= 0.01) and (
                brk_g is None or float(brk_g.max()) <= 0.005) and (modes_g is None or float(modes_g.max()) <= 0.005) and (
                fair_g is None or float(fair_g.max()) <= 0.01)
            modes_ok = modes_g is None or float(modes_g.max()) <= 0.005  # (LOP-29) every mode limit held at this sharpness
            due = (since >= projection["every"] or (since >= 5 and (change < settle or flat_beta) and penal >= pen_most and modes_ok)) if settle else (projection and it % projection["every"] == 0)
            if projection and due and not sharpest:
                if modes_g is not None and not modes_ok:
                    say(f"the sharpness raised at iteration {it} with a mode limit still broken ({float(modes_g.max()):+.3f}): "
                        f"{projection['every']} iterations at beta {beta[0]:g}")
                beta[0] = min(beta[0] * (BETA_STEP_MODES if modes_g is not None else 2.0), float(projection["beta_most"]))
                if beta[0] > float(projection["beta_most"]) * 0.999:
                    beta[0] = float(projection["beta_most"])
                since = 0
            elif it > 10 and sharpest and penal >= pen_most and (not fair_names or it - first >= int(fair["over"]) + 5) and (
                    change < 0.01 or (flat_stop and spent and held)):  # fmt: skip
                say(f"settled at iteration {it}: " + (f"no voxel moves more than {change:.3f}" if change < 0.01 else
                    f"the result within {100 * SETTLE_STOP:g} % of itself over the last {SETTLE_WINDOW} iterations at beta {beta[0]:g}"))  # fmt: skip
                break
            if on_iteration:
                # (15 October 02:28) the iteration's record too: the run keeps its last state that held every line
                # (`topo_free`'s `<stem>_held.npz`); `spl8` met every line from iteration 5 to 128, then the last
                # sharpening (22.6 -> 32) pinched a thin link off and its checkpoint kept only the broken state
                on_iteration(it, x, beta[0], history[-1] if history else None)
    else:
        for it in range(first, iterations + 1):
            t0 = time.time()
            penal = penalty_at(it)
            dens = vox.physical(x, beta[0])
            result = vox.analyse(dens, objective, penal)
            ratios, value = result["ratios"], result["value"]
            dcf, dv = vox.back(np.vstack([result["d_value"], vox.mass_rows]), x, beta[0])
            lo_l, hi_l = 1e-30, 1e30
            damping = projection.get("damping", 0.5) if projection else 0.5
            move = projection["move_late"] if projection and beta[0] >= projection["beta_most"] else 0.2
            while hi_l / lo_l > 1 + 1e-4:
                mid = math.sqrt(lo_l * hi_l)
                cand = np.clip(x * (np.maximum(-dcf, 0) / (mid * np.maximum(dv, 1e-12))) ** damping, np.maximum(0.001, x - move), np.minimum(1.0, x + move))
                if vox.physical(cand, beta[0])[free_e].sum() > target:
                    lo_l = mid
                else:
                    hi_l = mid
            change = float(np.abs(cand - x).max())
            x = cand
            worst = max(ratios.items(), key=lambda kv: kv[1])
            free_now = dens[free_e]
            grey = grey_of(free_now)
            row = {"iteration": it, "objective": value, "change": change, "worst_ratio": worst[1],
                   "worst_seat": f"{worst[0][0][0]} {worst[0][0][1]} case {worst[0][1]}", "beta": beta[0], "penalty": penal,
                   "grey_share": grey, "seconds": time.time() - t0, "mass_kg": float(free_now.sum()) * DENSITY * h**3,
                   "move": move, "ratios": named(ratios), "clock": {k: round(v, 3) for k, v in result["clock"].items()},
                   "solve_steps": result["steps"]}  # fmt: skip
            say(f"it {it:3d}: {objective} {value:,.4g}, change {change:.3f}, worst {worst[1]:.2f}x its line at {worst[0][0][0]} {worst[0][0][1]} case {worst[0][1]} (voxel model), beta {beta[0]:g}, p {penal:.2f}, grey {grey:.2f}, {time.time() - t0:.1f} s")
            history.append(row)
            sharpest = not projection or beta[0] >= projection["beta_most"]
            if projection and it % projection["every"] == 0 and not sharpest:
                beta[0] *= 2.0
            elif it > 10 and change < 0.01 and sharpest and penal >= pen_most:
                break
            if on_iteration:
                on_iteration(it, x, beta[0])
    phys = vox.physical(x, beta[0])[free_e]
    if bound or pnorm:
        if robust:
            realisations = {nm: named(s_["ratios"]) for nm, s_ in zip(names, states, strict=True)}
        # The binary check: the nominal field at 0.5, all metal or air, read by the same model. (LOP-30) With shares of real
        # geometry (`penal_most` 1) the shares themselves: rounding a cube half filled by a 4 mm rib to all or nothing
        # would double the rib or delete it
        dens_bin = np.ones(len(elem))
        shares = pen_most < PENAL and vox.spline is not None
        dens_bin[free_e] = phys if shares else (phys >= 0.5).astype(float)
        b_ = vox.with_modes(vox.analyse(dens_bin, analysed, pen_most if shares else PENAL, adjoints=False))
        vox.release(b_)
        binary = {"worst": float(b_["ratio_vector"].max()), "ratios": named(b_["ratios"]), "metal_voxels": int((phys >= 0.5).sum()),
                  "mass_kg": float(phys.sum() if shares else (phys >= 0.5).sum()) * DENSITY * h**3, "value": float(b_["value"]),
                  "shares": bool(shares),
                  "greatest_share": share_of(dens_bin)[2] if share_ball is not None else None,
                  "plan_share": plan_of(dens_bin)[2] if plan_fixed is not None else None,
                  "outline_mm": perim_of(dens_bin)[2] if perim_pairs is not None else None,
                  "beds": named(b_.get("beds") or {}), "bed_worst": float(b_["bed_vector"].max()) if len(b_.get("bed_vector", [])) else None,
                  "modes_hz": [round(float(v_), 1) for v_ in b_["modes_hz"]] if "modes_hz" in b_ else None,
                  "mode_gaps": [float(v_) for v_ in modes_of(b_)[0]] if mode_orders is not None else None}  # fmt: skip
        say(("the shares check: the field's geometric shares, half a cube half as stiff," if shares else "the binary check: the nominal field at 0.5, all metal or air,")
            + f" reads {binary['worst']:.4f}x its line (voxel model), {binary['mass_kg']:.3f} kg placed"
            + (f", compliance {binary['value']:.1f} N mm" if complied else "")
            + (f", the worst bed {binary['bed_worst']:.4f}x the design to beat's" if binary["bed_worst"] is not None else "")
            + (f", the greatest member's share {binary['greatest_share']:.3f}" if share_ball is not None else "")
            + (f", the plan share {binary['plan_share']:.3f}" if plan_fixed is not None else "")
            + (f", the outline {binary['outline_mm']:.0f} mm" if perim_pairs is not None else "")
            + (", modes " + ", ".join(f"{v_:.0f}" for v_ in binary["modes_hz"][:10]) + " Hz, gaps " + ", ".join(f"{v_:+.3f}" for v_ in binary["mode_gaps"])
               if binary["mode_gaps"] is not None else ""))  # fmt: skip
    fair_out = None
    if fair_names:  # (LOP-32) the measures on the start's skeleton and on the end's, rebuilt
        t_end, _ = vox.column_heights(x, beta[0])
        frame_end = mf.Frame(fair_cols, t_end, model["lo"], h)
        fair_out = {"targets": {nm: float(fair["targets"][nm]) for nm in fair_names}, "start": {nm: v_ / 1.05 for nm, v_ in fair_st["start"].items()},
                    "end": mf.summary(frame_end, t_end), "settings": {k: fair[k] for k in ("every", "over", "band", "rho") if k in fair}}  # fmt: skip
        say("the fairing rules at the end (worst, from the start's): " + ", ".join(
            f"{nm} {fair_out['end'][nm]['max']:.3f} (p95 {fair_out['end'][nm]['p95']:.3f}) from {fair_out['start'][nm]:.3f}" for nm in fair_names))  # fmt: skip
    return {"phys": phys, "x": x, "free_e": free_e, "elem": elem, "frozen": frozen, "ijk": vox.ijk, "history": history, "n_dof": vox.n_dof,
            "ratios": named(ratios), "joint": vox.joint_note, "beta": beta[0], "realisations": realisations, "binary": binary,
            "spline_cols": vox.spline_columns(x, beta[0]) if vox.spline is not None else None, "fair": fair_out}  # fmt: skip


def picture(model, result, path: Path, title: str):
    import pyvista as pv

    h, lo = model["h"], model["lo"]
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(1, 2), window_size=(1600, 700), off_screen=True)

    def blocks(mask_e):
        ijk = result["ijk"][mask_e]
        if len(ijk) == 0:
            return None
        grid = pv.ImageData(dimensions=tuple(model["n"] + 1), spacing=(h, h, h), origin=tuple(lo))
        flags = np.zeros(model["n"], dtype=np.uint8)
        flags[tuple(ijk.T)] = 1
        grid.cell_data["on"] = flags.ravel(order="F")
        return grid.threshold(0.5, scalars="on").extract_surface(algorithm="dataset_surface")

    shell = blocks(result["frozen"])
    solid = np.zeros(len(result["elem"]), dtype=bool)
    solid[result["free_e"][result["phys"] > 0.5]] = True
    added = blocks(solid)
    for col, view in enumerate(((0.6, -0.5, 0.8), (-0.6, -0.5, -0.8))):
        plotter.subplot(0, col)
        if shell is not None:
            plotter.add_mesh(shell, color=(0.75, 0.76, 0.78), opacity=0.35)
        if added is not None:
            plotter.add_mesh(added, color=(0.90, 0.55, 0.15))
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        side = "the cover's side" if col == 0 else "the motor's side"
        plotter.add_text(f"{title}: material added (orange, density > 0.5), seen from {side}", font_size=9)
    plotter.screenshot(str(path))


def main(shell: str, objective: str, budget: float, h: float = 6.0, iterations: int = 40) -> None:
    t0 = time.time()
    model = build_model(shell, h)
    result = solve_model(model, budget, iterations, objective)
    stem = f"topo_{shell}_{objective}_{budget:g}kg_{h:g}mm"
    np.savez_compressed(OUT / f"{stem}.npz", phys=result["phys"], x=result["x"], free_e=result["free_e"], elem=result["elem"], frozen=result["frozen"], ijk=result["ijk"], lo=model["lo"], n=model["n"], h=h)
    (OUT / f"{stem}.json").write_text(json.dumps({"shell": shell, "objective": objective, "budget_kg": budget, "voxel_mm": h, "history": result["history"], "unknowns": result["n_dof"], "seconds": time.time() - t0}, indent=1), encoding="utf-8")
    picture(model, result, OUT / f"{stem}.png", f"{shell}, {objective}, {budget:g} kg")
    say(f"done in {time.time() - t0:.0f} s; {stem}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], float(a[2]), float(a[3]) if len(a) > 3 else 6.0, int(a[4]) if len(a) > 4 else 40)
