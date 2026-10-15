"""The rib-direction field's toy (LOP-34; a prototype): a flat end wall with a bearing's boss, bolts
round its edge and a mount lug, ribs standing on it in a band; two ways of finding the ribs at one
mass, judged alike.

- **the field** (`Field`): at every column, which way the ribs run (theta), how much rib metal (rho,
  their thickness over their spacing) and how tall (h, at most `TALL` times their thickness and the
  band); rho and the height's share are cubic B-splines on `KNOT` mm knots, theta follows the
  strains (each column's direction the one that takes the most energy, `align`), smoothed;
- **the free columns** (`Columns`, today's way): each column one height of solid metal, filtered over
  the plan, SIMP on the cubes' shares.

Both minimise the two load cases' compliance at `BUDGET_KG` of placed metal (optimality criteria).
The set-up (mm, N): the wall `WALL` thick, `LX` x `LY`; the bearing's bore Ø `2 R_BORE` in a boss
Ø `2 R_BOSS` as tall as the band, its seat rigid with the bearing's centre `Z_LOAD` above the wall's
underside, where the loads act; bolt bosses and the lug held. The material is the contract's.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model as mdl  # noqa: E402
from zenryx.domains.gearbox.housing.mma import MMA  # noqa: E402
from zenryx.domains.gearbox.housing.voxels import greatest_share, local_ball  # noqa: E402
from zenryx.physics import couplings as cpl  # noqa: E402

OUT = ROOT / "data" / "rib_field"
CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"

A = 4.0  # mm: the model's cubes
LX, LY = 200.0, 160.0
WALL = 4.0
BAND = 24.0  # mm: the ribs' room above the wall
BORE = (120.0, 90.0)
R_BORE, R_BOSS = 26.0, 36.0
Z_LOAD = 16.0  # mm above the wall's underside: the bearing's centre
BOLTS = [(10, 80), (10, 150), (100, 150), (190, 150), (190, 80), (190, 10), (100, 10)]
R_BOLT = 7.0
FASTCAE = "--fastcae" in sys.argv  # fastcae's rules (`rules.py`), with their set-up
H_BOLT = 12.0 if FASTCAE else BAND  # mm above the wall: the bolts' bosses (a flange's height)
LUG = (26.0, 26.0)
R_LUG = 10.0
CASES = {"drive": (3000.0, 2000.0, 1500.0), "reverse": (-2000.0, 3000.0, 1500.0)}
BUDGET_KG = 0.25  # the ribs' metal (or the columns')

SPACING = float(os.environ.get("RIB_SPACING", 24.0))  # mm: between the ribs' centres when drawn
T_MOST = float(os.environ.get("RIB_T_MOST", 7.0))  # mm: the thickest rib
TALL = 5.0 if FASTCAE else 4.0  # a rib stands at most this many times its thickness (fastcae: 5)
KNOT = 16.0  # mm: the B-splines' knots
SMIN = 1.0  # 1/mm: the smooth minimum's sharpness (under-reads by at most ln 2 / SMIN)
THETA_SMOOTH = 8.0  # mm: the directions smoothed over this
THETA_STEP = np.radians(15.0)  # the most a direction turns in one step
# the free columns' lump rule, our optimiser's (`optimise.py`: --max-member 16, LOOP_MEMBER_P=40)
MAX_MEMBER, MEMBER_ALPHA, MEMBER_P = 16.0, 0.6, 40.0
MOVE = 0.1  # MMA's step limit, a share of each variable's range


def material() -> tuple[float, float, float]:
    """The contract's alloy: Young's modulus (MPa), Poisson's ratio, density (kg/mm3)."""
    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.forces import value_in

    spec, _ = load_and_validate(CONTRACT)
    m = spec.manufacturing.material
    return (
        value_in(m.youngs_modulus, "MPa"),
        value_in(m.poisson_ratio, "1"),
        value_in(m.density, "t/mm3") * 1e3,
    )


def bspline_1d(x: np.ndarray, length: float, knot: float) -> np.ndarray:
    """(len(x), n): uniform cubic B-splines with knots `knot` apart covering [0, length]."""
    n = int(np.ceil(length / knot)) + 3
    centres = (np.arange(n) - 1) * knot
    t = np.abs((x[:, None] - centres[None, :]) / knot)
    out = np.where(t < 1, (4 - 6 * t**2 + 3 * t**3) / 6, np.where(t < 2, (2 - t) ** 3 / 6, 0.0))
    return out


def bspline_1d_deriv(x: np.ndarray, length: float, knot: float) -> np.ndarray:
    """(len(x), n): the derivatives by x of `bspline_1d`'s basis."""
    n = int(np.ceil(length / knot)) + 3
    centres = (np.arange(n) - 1) * knot
    u = (x[:, None] - centres[None, :]) / knot
    a = np.abs(u)
    du = np.where(a < 1, (-12 * u + 9 * u * a) / 6, np.where(a < 2, -np.sign(u) * (2 - a) ** 2 / 2, 0.0))
    return du / knot


def bspline_2d_grad(x: np.ndarray, y: np.ndarray, knot: float) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    """The derivatives by x and by y of `bspline_2d`'s basis at the points."""
    bx, by = bspline_1d(x, LX, knot), bspline_1d(y, LY, knot)
    dx, dy = bspline_1d_deriv(x, LX, knot), bspline_1d_deriv(y, LY, knot)
    return (
        sp.csr_matrix(np.einsum("pi,pj->pij", dx, by).reshape(len(x), -1)),
        sp.csr_matrix(np.einsum("pi,pj->pij", bx, dy).reshape(len(x), -1)),
    )


def bspline_2d(x: np.ndarray, y: np.ndarray, knot: float) -> sp.csr_matrix:
    """(len(x), nx ny): the tensor-product basis at the points (x, y)."""
    bx, by = bspline_1d(x, LX, knot), bspline_1d(y, LY, knot)
    return sp.csr_matrix(np.einsum("pi,pj->pij", bx, by).reshape(len(x), -1))


def smin(a: float, b: np.ndarray, k: float = SMIN) -> tuple[np.ndarray, np.ndarray]:
    """A smooth minimum of a and b, and its derivative by b."""
    m = np.minimum(a, b)
    ea, eb = np.exp(-k * (a - m)), np.exp(-k * (b - m))
    return m - np.log(ea + eb) / k, eb / (ea + eb)


@dataclass
class Setup:
    grid: mdl.Grid
    asm: mdl.Assembler
    kind: np.ndarray  # per active element: 0 wall, 1 solid, 2 design
    col: np.ndarray  # per active element: its design column, or -1
    layer: np.ndarray  # per active element: its layer above the wall (0 the first), or -1
    cols_xy: np.ndarray  # (n columns, 2): each design column's centre in plan
    cols_ij: np.ndarray  # (n columns, 2)
    T: sp.csr_matrix
    tinfo: dict
    f: np.ndarray  # (n_q, cases)
    c_iso: np.ndarray
    c_local: np.ndarray
    density: float
    groups: list = field(default_factory=list)

    @property
    def n_cols(self) -> int:
        return len(self.cols_xy)


def build(a: float = A) -> Setup:
    e, nu, density = material()
    nx, ny = int(round(LX / a)), int(round(LY / a))
    nw, nb = int(round(WALL / a)), int(round(BAND / a))
    grid = mdl.Grid(nx, ny, nw + nb, a)
    cx, cy, cz = grid.centre.T
    d_bore = np.hypot(cx - BORE[0], cy - BORE[1])
    hole = d_bore < R_BORE
    boss = (d_bore >= R_BORE) & (d_bore < R_BOSS)
    bolt = np.zeros_like(hole)
    for b in BOLTS:
        bolt |= np.hypot(cx - b[0], cy - b[1]) < R_BOLT
    lug = np.hypot(cx - LUG[0], cy - LUG[1]) < R_LUG
    hole = hole | (bolt & (cz > WALL + H_BOLT))
    bolt = bolt & ~hole
    active = np.flatnonzero(~hole)
    wall = grid.k < nw
    solid = boss | bolt | lug
    kind = np.where(solid, 1, np.where(wall, 0, 2))[active]
    asm = mdl.Assembler(grid, active)
    # the design columns
    design = kind == 2
    ij = np.stack([grid.i[active], grid.j[active]], axis=1)
    keys = ij[:, 0] + nx * ij[:, 1]
    uniq, inv = np.unique(keys[design], return_inverse=True)
    col = np.full(len(active), -1)
    col[design] = inv
    layer = np.where(design, grid.k[active] - nw, -1)
    cols_ij = np.stack([uniq % nx, uniq // nx], axis=1)
    cols_xy = (cols_ij + 0.5) * a
    # the couplings: the bore's seat rigid with the bearing's centre; the bolts and the lug held
    used = np.unique(grid.nodes_of[active])
    xyz = grid.xyz
    on = np.zeros(len(xyz), bool)
    on[used] = True
    d_node = np.hypot(xyz[:, 0] - BORE[0], xyz[:, 1] - BORE[1])
    seat = np.flatnonzero(on & (d_node < R_BORE + 0.75 * a))
    groups = [{"nodes": seat, "ref": (BORE[0], BORE[1], Z_LOAD), "name": "the bearing's seat"}]
    for k_, b in enumerate(BOLTS):
        ids = np.unique(
            grid.nodes_of[np.flatnonzero((np.hypot(cx - b[0], cy - b[1]) < R_BOLT) & (cz < WALL + H_BOLT))]
        )
        groups.append({"nodes": ids, "fixed": True, "name": f"bolt {k_ + 1}"})
    ids = np.unique(grid.nodes_of[np.flatnonzero(lug)])
    groups.append({"nodes": ids, "fixed": True, "name": "the lug"})
    # nodes no element holds are held too (the bore's middle)
    loose = np.flatnonzero(~on)
    if len(loose):
        groups.append({"nodes": loose, "fixed": True, "name": "unused"})
    tee, tinfo = cpl.rigid_transform(xyz, groups)
    f = np.zeros((tee.shape[1], len(CASES)))
    for c_, force in enumerate(CASES.values()):
        f[tinfo["ref_col"][0] : tinfo["ref_col"][0] + 3, c_] = force
    return Setup(
        grid=grid,
        asm=asm,
        kind=kind,
        col=col,
        layer=layer,
        cols_xy=cols_xy,
        cols_ij=cols_ij,
        T=tee.tocsr(),
        tinfo=tinfo,
        f=f,
        c_iso=mdl.isotropic(e, nu),
        c_local=mdl.rib_local(e, nu),
        density=density,
        groups=groups,
    )


def solve(s: Setup, c: np.ndarray) -> dict:
    """The compliance of both cases, the bearing's tilt, and each element's energy tensor."""
    import pypardiso

    k = s.asm.stiffness(c)
    kr = (s.T.T @ k @ s.T).tocsr()
    kr = (0.5 * (kr + kr.T)).tocsr()
    q = pypardiso.spsolve(kr, s.f)
    q = q.reshape(len(s.f), -1)
    u = s.T @ q
    r = s.tinfo["ref_col"][0]
    tilt = np.hypot(q[r + 3], q[r + 4])  # rad, per case
    comp = float((s.f * q).sum())
    return {"compliance": comp, "tilt": tilt, "u": u, "energy": s.asm.energy(u), "q": q}


def heights_share(h: np.ndarray, layer: np.ndarray, a: float) -> tuple[np.ndarray, np.ndarray]:
    """Each design element's share of its height under its column's rib height h (mm above the wall),
    and the share's derivative by h."""
    z0 = layer * a
    g = np.clip((h - z0) / a, 0.0, 1.0)
    dg = np.where((h > z0) & (h < z0 + a), 1.0 / a, 0.0)
    return g, dg


class Field:
    """The rib-direction field over the design columns: per family (one, or two crossing at right
    angles) its rho and its height's share as B-splines; the first family's direction theta per
    column, the second's theta + 90 degrees. The variables x = [x_rho, x_r] for each family in turn."""

    def __init__(self, s: Setup, knot: float = KNOT, families: int = 1, turns: bool = True):
        """`turns`: the directions are the optimiser's too, theta = theta0 + pi (B y - 1/2), a
        smooth turn of up to 90 degrees either way from where the strains first put them
        (`align`); y the last n variables."""
        self.s = s
        self.turns = turns
        self.theta0 = np.zeros(s.n_cols)
        self.B = bspline_2d(s.cols_xy[:, 0], s.cols_xy[:, 1], knot)
        self.n = self.B.shape[1]
        self.families = families
        self.Bx, self.By = bspline_2d_grad(s.cols_xy[:, 0], s.cols_xy[:, 1], knot)
        self.fastcae = FASTCAE
        self.by_place = "--by-place" in sys.argv or FASTCAE
        self.ruled = "--ends" in sys.argv or FASTCAE
        self.hcap = np.full(s.n_cols, BAND)
        self.theta0_grad = np.zeros((s.n_cols, 2))
        if FASTCAE:
            import rules

            self.hcap = rules.height_cap(s.cols_xy)
            self.normal = rules.anchor_normal(s.cols_xy)
        if self.by_place:
            import rules

            self.tcap, self.tcap_grad = rules.thickness_cap(s.cols_xy)
        else:
            self.tcap, self.tcap_grad = np.full(s.n_cols, T_MOST), np.zeros((s.n_cols, 2))
        self.rho_most = self.tcap / SPACING  # per column
        if self.ruled:
            import rules

            self.w_end = rules.end_weight(s.cols_xy)
        self.theta = np.zeros(s.n_cols)
        self.v = np.zeros((s.n_cols, 2))  # the doubled-angle direction, smoothed
        self.d = s.kind == 2
        self.col, self.lay = s.col[self.d], s.layer[self.d]

    def start(self, value: float = 0.5) -> np.ndarray:
        return np.full(2 * self.n * self.families + (self.n if self.turns else 0), value)

    def set_theta(self, x: np.ndarray) -> None:
        if self.turns and len(x) > 2 * self.n * self.families:
            y = x[2 * self.n * self.families :]
            self.theta = self.theta0 + np.pi * (self.B @ y - 0.5)

    def columns(self, x: np.ndarray) -> list[dict]:
        """Per family: rho, the height and their derivatives per column."""
        out = []
        for k in range(self.families):
            xr = x[2 * k * self.n : (2 * k + 1) * self.n]
            xh = x[(2 * k + 1) * self.n : (2 * k + 2) * self.n]
            rho = self.rho_most * (self.B @ xr)
            r = self.B @ xh
            cap, dcap = smin(self.hcap, TALL * SPACING * rho)
            out.append(
                {"rho": rho, "r": r, "h": r * cap, "cap": cap, "dh_drho": r * dcap * TALL * SPACING}
            )
        return out

    def stiffness(self, x: np.ndarray) -> tuple[np.ndarray, dict]:
        s = self.s
        self.set_theta(x)
        fams = self.columns(x)
        c = np.empty((len(s.kind), 6, 6))
        c[s.kind != 2] = s.c_iso
        col, lay = self.col, self.lay
        cd = np.broadcast_to(mdl.ERSATZ * s.c_iso, (len(col), 6, 6)).copy()
        for k, f in enumerate(fams):
            g, dg = heights_share(f["h"][col], lay, s.grid.a)
            crib, dcrib = mdl.rib_tensor(self.theta[col] + k * np.pi / 2, s.c_local)
            cd += (g * f["rho"][col])[:, None, None] * crib
            f.update(g=g, dg=dg, crib=crib, dcrib=dcrib)
        c[self.d] = cd
        return c, {"fams": fams, "col": col, "d": self.d}

    def mass_x(self, x: np.ndarray) -> float:
        """The mass at x, without the stiffness (the optimality step's bisection)."""
        s, tot = self.s, 0.0
        for f in self.columns(x):
            g, _ = heights_share(f["h"][self.col], self.lay, s.grid.a)
            tot += float((g * f["rho"][self.col]).sum())
        return tot * s.grid.a**3 * s.density

    def mass(self, cc: dict) -> float:
        tot = sum(float((f["g"] * f["rho"][cc["col"]]).sum()) for f in cc["fams"])
        return tot * self.s.grid.a**3 * self.s.density

    def gradients(self, cc: dict, energy: np.ndarray) -> dict:
        """The compliance's and the mass's derivatives by x, and the compliance's by each theta."""
        s, a3 = self.s, self.s.grid.a**3
        col, nc, bt = cc["col"], s.n_cols, self.B.T
        en = energy[cc["d"]]
        dc, dm = [], []
        dc_dth = np.zeros(nc)
        for f in cc["fams"]:
            g, dg = f["g"], f["dg"]
            rho = f["rho"][col]
            e_rib = -np.einsum("epq,epq->e", en, f["crib"])  # d compliance / d (g rho)
            e_th = -np.einsum("epq,epq->e", en, f["dcrib"])
            via_rho = g + rho * dg * f["dh_drho"][col]
            via_r = rho * dg * f["cap"][col]
            dc += [bt @ (self.rho_most * np.bincount(col, e_rib * via_rho, nc)),
                   bt @ np.bincount(col, e_rib * via_r, nc)]
            dm += [(bt @ (self.rho_most * np.bincount(col, via_rho, nc))) * a3 * s.density,
                   (bt @ np.bincount(col, via_r, nc)) * a3 * s.density]
            dc_dth += np.bincount(col, e_th * g * rho, nc)
        if self.turns:
            dc.append(np.pi * (bt @ dc_dth))
            dm.append(np.zeros(self.n))
        return {"dc": np.concatenate(dc), "dm": np.concatenate(dm), "dc_dtheta": dc_dth}

    def align(self, energy: np.ndarray, cc: dict, first: bool = False) -> dict:
        """Each column's direction turned toward the one in which its ribs take the most energy under
        the present strains (for the compliance, the optimum direction of a stiff-along-one-way
        material), smoothed over `THETA_SMOOTH` mm as a doubled angle; returns how far they turned."""
        s = self.s
        angles = np.radians(np.arange(0, 180, 5.0))
        en = energy[cc["d"]]
        tot = np.zeros((s.n_cols, len(angles)))
        for k, f in enumerate(cc["fams"]):
            crib, _ = mdl.rib_tensor(angles + k * np.pi / 2, s.c_local)
            w = np.maximum(f["g"], 0.25) * np.maximum(f["rho"][cc["col"]], 0.02)
            np.add.at(tot, cc["col"], np.einsum("epq,mpq->em", en, crib) * w[:, None])
        best = angles[np.argmax(tot, axis=1)]
        strength = tot.max(axis=1) - tot.min(axis=1)
        v = strength[:, None] * np.stack([np.cos(2 * best), np.sin(2 * best)], axis=1)
        # smoothed on the plan grid
        nx, ny = s.grid.nx, s.grid.ny
        grid_v = np.zeros((2, nx, ny))
        mask = np.zeros((nx, ny))
        grid_v[:, s.cols_ij[:, 0], s.cols_ij[:, 1]] = v.T
        mask[s.cols_ij[:, 0], s.cols_ij[:, 1]] = 1.0
        sig = THETA_SMOOTH / s.grid.a
        sm = np.stack([gaussian_filter(grid_v[k], sig, mode="nearest") for k in range(2)])
        wm = gaussian_filter(mask, sig, mode="nearest")
        target = (sm / np.maximum(wm, 1e-9))[:, s.cols_ij[:, 0], s.cols_ij[:, 1]].T
        t_target = 0.5 * np.arctan2(target[:, 1], target[:, 0])
        if first:
            new = t_target
        else:
            turn = np.angle(np.exp(2j * (t_target - self.theta))) / 2  # within +-90 degrees
            new = self.theta + np.clip(turn, -THETA_STEP, THETA_STEP)
        moved = np.abs(np.angle(np.exp(2j * (new - self.theta))) / 2)
        self.theta = np.mod(new, np.pi)
        self.v = target
        return {"most": float(moved.max()), "median": float(np.median(moved)),
                "share_over_5": float((moved > np.radians(5)).mean())}

    def turn(self, dc_dtheta: np.ndarray, step: float) -> dict:
        """The directions moved down the compliance's gradient, at most `step` radians a column
        (a tanh of the derivative over its median size), then smoothed over `THETA_SMOOTH` mm as a
        doubled angle. The strains' own best direction (`align`) flips ribs that are stiff one way
        only: stiffened along it, the strain moves across it."""
        s = self.s
        scale = np.median(np.abs(dc_dtheta)) + 1e-30
        new = self.theta - step * np.tanh(dc_dtheta / (3.0 * scale))
        v = np.stack([np.cos(2 * new), np.sin(2 * new)], axis=1)
        nx, ny = s.grid.nx, s.grid.ny
        grid_v = np.zeros((2, nx, ny))
        mask = np.zeros((nx, ny))
        grid_v[:, s.cols_ij[:, 0], s.cols_ij[:, 1]] = v.T
        mask[s.cols_ij[:, 0], s.cols_ij[:, 1]] = 1.0
        sig = THETA_SMOOTH / s.grid.a / 2.0
        sm = np.stack([gaussian_filter(grid_v[k], sig, mode="nearest") for k in range(2)])
        wm = gaussian_filter(mask, sig, mode="nearest")
        target = (sm / np.maximum(wm, 1e-9))[:, s.cols_ij[:, 0], s.cols_ij[:, 1]].T
        new = 0.5 * np.arctan2(target[:, 1], target[:, 0])
        moved = np.abs(np.angle(np.exp(2j * (new - self.theta))) / 2)
        self.theta = np.mod(new, np.pi)
        self.v = target
        return {"most": float(moved.max()), "median": float(np.median(moved)),
                "share_over_5": float((moved > np.radians(5)).mean())}


class Columns:
    """Today's way on the toy: one height of solid metal a column, the heights filtered over the plan
    (a cone of `radius` mm), SIMP on each cube's share."""

    def __init__(self, s: Setup, radius: float = 6.0):
        self.s = s
        xy = s.cols_xy
        d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
        w = np.maximum(0.0, radius - d)
        w = w / w.sum(axis=1, keepdims=True)
        self.W = sp.csr_matrix(w)
        self.n = s.n_cols
        self.p = 1.0
        d = s.kind == 2
        ijk = np.stack([s.grid.i, s.grid.j, s.grid.k], axis=1)[s.asm.elements[d]]
        self.ball, self.cells = local_ball(ijk, MAX_MEMBER / 0.849 / s.grid.a)

    def stiffness(self, x: np.ndarray) -> tuple[np.ndarray, dict]:
        s = self.s
        h = BAND * (self.W @ x)
        c = np.empty((len(s.kind), 6, 6))
        c[s.kind != 2] = s.c_iso
        d = s.kind == 2
        col, lay = s.col[d], s.layer[d]
        g, dg = heights_share(h[col], lay, s.grid.a)
        c[d] = (mdl.ERSATZ + (1 - mdl.ERSATZ) * g**self.p)[:, None, None] * s.c_iso
        return c, {"h": h, "g": g, "dg": dg, "col": col, "d": d}

    def mass(self, cc: dict) -> float:
        return float(cc["g"].sum() * self.s.grid.a**3 * self.s.density)

    def lump(self, cc: dict) -> tuple[float, np.ndarray, float]:
        """Our optimiser's greatest member on the cubes' shares (G <= 0, its derivative by x, the
        p-mean share)."""
        g_, dg_m, m = greatest_share(self.ball, self.cells, cc["g"], MEMBER_ALPHA, MEMBER_P)
        dh = np.bincount(cc["col"], dg_m * cc["dg"], self.s.n_cols)
        return g_, BAND * (self.W.T @ dh), m

    def mass_x(self, x: np.ndarray) -> float:
        s = self.s
        d = s.kind == 2
        g, _ = heights_share((BAND * (self.W @ x))[s.col[d]], s.layer[d], s.grid.a)
        return float(g.sum() * s.grid.a**3 * s.density)

    def gradients(self, cc: dict, energy: np.ndarray) -> dict:
        s, a3 = self.s, self.s.grid.a**3
        col, g, dg = cc["col"], cc["g"], cc["dg"]
        en = energy[cc["d"]]
        e_iso = -np.einsum("epq,pq->e", en, s.c_iso)
        de = e_iso * (1 - mdl.ERSATZ) * self.p * np.maximum(g, 1e-9) ** (self.p - 1)
        dc_dh = np.bincount(col, de * dg, s.n_cols)
        dm_dh = np.bincount(col, dg, s.n_cols) * a3 * s.density
        wt = self.W.T
        return {"dc": BAND * (wt @ dc_dh), "dm": BAND * (wt @ dm_dh)}


def oc(x, dc, dm, mass_of, budget, move=0.1, eta=0.5, lo=0.0, hi=1.0):
    """The optimality criteria's step: x scaled by (-dc / (lam dm))^eta within the move limit, lam
    found by bisection so the mass meets the budget."""
    ratio = np.maximum(-dc, 1e-30) / np.maximum(dm, 1e-30)
    l1, l2 = 1e-30, 1e30
    xn = x
    for _ in range(200):
        lam = np.sqrt(l1 * l2)
        xn = np.clip(x * (ratio / lam) ** eta, np.maximum(lo, x - move), np.minimum(hi, x + move))
        if mass_of(xn) > budget:
            l1 = lam
        else:
            l2 = lam
        if l2 / l1 < 1 + 1e-6:
            break
    return xn


def run_field(
    s: Setup, iterations: int = 80, families: int = 1, move: float = MOVE, say=print
) -> tuple[Field, np.ndarray, list]:
    """The directions start where the strains put them (`Field.align`), then move down the
    compliance's gradient (`Field.turn`), the step shrinking when the compliance rose."""
    fld = Field(s, families=families, turns="--turn-steps" not in sys.argv)
    if "--freeze-theta" in sys.argv:
        fld.turns = False
    x = fld.start()
    history = []
    step, last, opt, c0 = THETA_STEP / 3, None, None, 1.0
    for it in range(iterations):
        if it == 0:
            c, cc = fld.stiffness(x)
            turned = fld.align(solve(s, c)["energy"], cc, first=True)
            fld.theta0 = fld.theta.copy()
            if fld.fastcae:
                import rules

                fld.theta0_grad = rules.theta_gradient(fld.theta0, s.cols_ij, s.grid.a)
        before = fld.theta.copy()
        c, cc = fld.stiffness(x)
        r = solve(s, c)
        gr = fld.gradients(cc, r["energy"])
        m = fld.mass(cc)
        if it and fld.turns:
            moved = np.abs(np.angle(np.exp(2j * (fld.theta - before))) / 2)
            turned = {"most": float(moved.max()), "median": float(np.median(moved)),
                      "share_over_5": float((moved > np.radians(5)).mean())}
        if it and not fld.turns and "--freeze-theta" not in sys.argv:
            if last is not None and r["compliance"] > last:
                step = max(step * 0.6, np.radians(0.25))
            else:
                step = min(step * 1.15, THETA_STEP / 3)
            turned = fld.turn(gr["dc_dtheta"], step)
        last = r["compliance"]
        history.append(
            {
                "it": it,
                "compliance": r["compliance"],
                "mass_kg": m,
                "tilt_mrad": (1e3 * r["tilt"]).tolist(),
                "turn_deg": np.degrees(turned["most"]),
                "turn_median_deg": np.degrees(turned["median"]),
                "turning_share": turned["share_over_5"],
            }
        )
        say(
            f"field ({families}) it {it:3d}: compliance {r['compliance']:.2f} N mm, mass {m:.3f} kg, "
            f"tilt {1e3 * r['tilt'].max():.4f} mrad, directions turned at most "
            f"{np.degrees(turned['most']):.1f} deg (median {np.degrees(turned['median']):.2f}, "
            f"{100 * turned['share_over_5']:.0f} % over 5)"
        )
        f, df = [m / BUDGET_KG - 1.0], [gr["dm"] / BUDGET_KG]
        if fld.ruled:
            import rules

            ru = rules.transport(fld, x)
            for key in ru:
                f.append(ru[key][0])
                df.append(ru[key][1])
            history[-1]["rules"] = {key: ru[key][2] for key in ru}
            say("    the rules: " + ", ".join(f"{key} {ru[key][2]:.4f} ({ru[key][0]:+.3f})" for key in ru))
        if opt is None:
            opt, c0 = MMA(len(x), len(f), 0.0, 1.0), r["compliance"]
        x = opt.propose(x, r["compliance"] / c0, gr["dc"] / c0, f, df, move=move)
    return fld, x, history


def run_columns(
    s: Setup, iterations: int = 80, lump: bool = True, move: float = MOVE, say=print
) -> tuple[Columns, np.ndarray, list]:
    """Today's way: MMA on the columns' heights, the mass and (with `lump`) our optimiser's
    greatest member held; SIMP's penalty from 1 to 3."""
    cols = Columns(s)
    x = np.full(cols.n, BUDGET_KG / 2.0)
    history = []
    opt, c0 = None, 1.0
    for it in range(iterations):
        cols.p = min(3.0, 1.0 + it / 20.0)
        c, cc = cols.stiffness(x)
        r = solve(s, c)
        gr = cols.gradients(cc, r["energy"])
        m = cols.mass(cc)
        f, df = [m / BUDGET_KG - 1.0], [gr["dm"] / BUDGET_KG]
        share = None
        if lump:
            g_, dg_, share = cols.lump(cc)
            f.append(g_)
            df.append(dg_)
        history.append(
            {"it": it, "compliance": r["compliance"], "mass_kg": m,
             "tilt_mrad": (1e3 * r["tilt"]).tolist(), "lump_share": share}
        )
        say(
            f"columns it {it:3d}: compliance {r['compliance']:.2f} N mm, mass {m:.3f} kg, tilt "
            f"{1e3 * r['tilt'].max():.4f} mrad (p {cols.p:.2f})"
            + (f", the greatest member's share {share:.3f}" if share is not None else "")
        )
        if opt is None:
            opt, c0 = MMA(len(x), len(f), 0.0, 1.0), r["compliance"]
        x = opt.propose(x, r["compliance"] / c0, gr["dc"] / c0, f, df, move=move)
    return cols, x, history


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    """`toy.py [iterations] [families] [label] [--no-columns]`: the field's run, then the free
    columns' at the same mass; written to `data/rib_field/<label>_field.npz`, `<label>_columns.npz`
    and `<label>_history.json`."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    iterations = int(args[0]) if args else 80
    families = int(args[1]) if len(args) > 1 else 1
    label = args[2] if len(args) > 2 else f"toy{families}"
    a = float(next((v.split("=")[1] for v in sys.argv if v.startswith("--voxel=")), A))
    t0 = time.time()
    s = build(a)
    print(f"set-up: {len(s.kind):,} cubes, {s.n_cols:,} design columns, {s.T.shape[1]:,} unknowns")
    fld, xf, hf = run_field(s, iterations, families)
    fams = fld.columns(xf)
    np.savez_compressed(
        OUT / f"{label}_field.npz",
        x=xf,
        families=families,
        spacing=SPACING,
        t_most=T_MOST,
        by_place=fld.by_place,
        ruled=fld.ruled,
        fastcae=fld.fastcae,
        tall=TALL,
        h_bolt=H_BOLT,
        voxel=a,
        theta=fld.theta,
        v=fld.v,
        rho=np.stack([f["rho"] for f in fams]),
        h=np.stack([f["h"] for f in fams]),
        cols_xy=s.cols_xy,
        cols_ij=s.cols_ij,
    )
    history = {"field": hf, "families": families, "voxel": a}
    if "--no-columns" not in sys.argv:
        cols, xc, hc = run_columns(s, iterations, lump="--no-lump" not in sys.argv)
        _, ccc = cols.stiffness(xc)
        np.savez_compressed(
            OUT / f"{label}_columns.npz", x=xc, h=ccc["h"], voxel=a, cols_xy=s.cols_xy, cols_ij=s.cols_ij
        )
        history["columns"] = hc
    history["seconds"] = time.time() - t0
    (OUT / f"{label}_history.json").write_text(json.dumps(history, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
