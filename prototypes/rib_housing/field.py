"""The rib-direction field over the housing's design columns (LOP-34; a prototype).

The toy's field (`prototypes/rib_field/toy.py`, `Field`) carried to the product's columns: each
column group (a half's run of columns along the pull, `housing.column_groups`) has two rib families
at right angles, each with a thickness share and a height share as cubic B-splines on `KNOT` mm
knots over the group's plan box, and the directions a smooth B-spline turn from where the strains
first put them (`align`). A free cube's stiffness is its families' laminates (thin plates along the
pull running along theta in plan), each times its share of its column's rib height; a column's
height runs from its base (the split or the wall the column stands on) outward, as the product's
height field does.

fastcae's rules (`prototypes/rib_field/rules.py`, the method §7) hold per group, the toy's anchors
replaced by the housing's: the hard points (each bearing's bore and its 4 mm ring, each bolt's boss,
each mount's lug, of the group's half) and the group's own outline (where its columns end: the
design space's edge). Thickness by place: thick at a hard point, thin away.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rib_field"))

import model as toymodel  # noqa: E402
import rules  # noqa: E402
import toy  # noqa: E402

toy.TALL = 5.0  # fastcae's tallest_ratio, as the toy's --fastcae
KNOT = 16.0  # mm
SPACING = 24.0  # mm: between the ribs' centres when drawn
THETA_SMOOTH = 8.0  # mm: the start's directions smoothed over this
ERSATZ = 1e-4


def basis_1d(x, length, knot):
    return toy.bspline_1d(x, length, knot), toy.bspline_1d_deriv(x, length, knot)


def bspline_group(xy, lo, hi, knot):
    """The tensor-product cubic B-spline basis over a plan box at the points, and its derivatives."""
    lx, ly = hi[0] - lo[0] + knot, hi[1] - lo[1] + knot
    bx, dx = basis_1d(xy[:, 0] - lo[0] + knot / 2, lx, knot)
    by, dy = basis_1d(xy[:, 1] - lo[1] + knot / 2, ly, knot)
    n = len(xy)
    b = sp.csr_matrix(np.einsum("pi,pj->pij", bx, by).reshape(n, -1))
    bxm = sp.csr_matrix(np.einsum("pi,pj->pij", dx, by).reshape(n, -1))
    bym = sp.csr_matrix(np.einsum("pi,pj->pij", bx, dy).reshape(n, -1))
    return b, bxm, bym, (lx, ly)


def hard_points(info: dict, half: str) -> list[tuple[float, float, float]]:
    """(x, y, radius) in plan of the hard points of a half: each bearing's bore with its 4 mm ring,
    each bolt's boss, each of the half's mounts' lugs."""
    s = info["settings"]
    split = info["z"]["split"]
    below = half == "motor_side"
    out = []
    for b in info["bearings"]:
        if (0.5 * (b["z"][0] + b["z"][1]) < split) == below:
            out.append((b["axis"][0], b["axis"][1], b["D"] / 2 + s["wall"]))
    for c in info["bolts"]:
        out.append((c[0], c[1], s["bolt_boss"] / 2))
    for m in info["mounts"]:
        if (0.5 * (m["z"][0] + m["z"][1]) < split) == below:
            out.append((m["centre"][0], m["centre"][1], s["mount_diameter"] / 2))
    return out


def hard_distance(xy, pts):
    best = np.full(len(xy), np.inf)
    grad = np.zeros((len(xy), 2))
    for cx, cy, r in pts:
        dx, dy = xy[:, 0] - cx, xy[:, 1] - cy
        rr = np.maximum(np.hypot(dx, dy), 1e-9)
        d = rr - r
        nearer = d < best
        best = np.where(nearer, d, best)
        grad[nearer] = np.stack([dx / rr, dy / rr], axis=1)[nearer]
    return best, grad


class Group:
    """One group's field, with every attribute `rules.transport` reads."""

    def __init__(self, g: dict, info: dict, col_len_mm: np.ndarray, a: float, offset: int):
        self.name, self.half = g["name"], g["half"]
        self.cols, self.xy = g["cols"], g["xy"]
        self.ij = g["ij"] - g["ij"].min(axis=0)
        self.B, self.Bx, self.By, _ = bspline_group(self.xy, g["lo"], g["hi"], KNOT)
        self.n = self.B.shape[1]
        self.families, self.turns, self.fastcae = 2, True, True
        self.offset = offset  # this group's first variable in the whole design vector
        self.size = 5 * self.n
        self.a = a
        pts = hard_points(info, self.half)
        d_hard, g_hard = hard_distance(self.xy, pts)
        s_, ds = rules.smoothstep(d_hard / rules.T_TAPER)
        self.tcap = rules.T_FAR + (rules.T_NEAR - rules.T_FAR) * (1.0 - s_)
        self.tcap_grad = (-(rules.T_NEAR - rules.T_FAR) * ds / rules.T_TAPER)[:, None] * g_hard
        self.rho_most = self.tcap / SPACING
        self.hcap = col_len_mm[self.cols]
        # the group's outline: the distance from each column to the nearest cell outside the group
        nx, ny = self.ij.max(axis=0) + 3
        mask = np.zeros((nx, ny), bool)
        mask[self.ij[:, 0] + 1, self.ij[:, 1] + 1] = True
        d_edge_grid = distance_transform_edt(mask) * a
        d_edge = d_edge_grid[self.ij[:, 0] + 1, self.ij[:, 1] + 1] - 0.5 * a
        d_any = np.minimum(d_hard, d_edge)
        self.w_end = rules.smoothstep((d_any - rules.END_REACH) / rules.END_REACH)[0]
        # each column's nearest anchor's normal: the hard point's radius, or the outline's gradient
        gy_, gx_ = np.gradient(d_edge_grid.T)[0].T, np.gradient(d_edge_grid.T)[1].T
        ex = gx_[self.ij[:, 0] + 1, self.ij[:, 1] + 1]
        ey = gy_[self.ij[:, 0] + 1, self.ij[:, 1] + 1]
        self.normal = np.where(d_hard <= d_edge, np.arctan2(g_hard[:, 1], g_hard[:, 0]), np.arctan2(ey, ex))
        self.theta0 = np.zeros(len(self.cols))
        self.theta0_grad = np.zeros((len(self.cols), 2))
        self.theta = self.theta0.copy()

    def x_of(self, x):
        return x[self.offset : self.offset + self.size]

    def set_theta(self, xg):
        self.theta = self.theta0 + np.pi * (self.B @ xg[4 * self.n :] - 0.5)

    def columns(self, xg) -> list[dict]:
        out = []
        for k in range(2):
            xr = xg[2 * k * self.n : (2 * k + 1) * self.n]
            xh = xg[(2 * k + 1) * self.n : (2 * k + 2) * self.n]
            rho = self.rho_most * (self.B @ xr)
            r = self.B @ xh
            cap, dcap = toy.smin(self.hcap, toy.TALL * SPACING * rho)
            out.append({"rho": rho, "r": r, "h": r * cap, "cap": cap,
                        "dh_drho": r * dcap * toy.TALL * SPACING})
        return out


class HousingField:
    """Every group's field, the free cubes' stiffness from the design vector, and the chain back."""

    def __init__(self, vox, groups: list[dict], c_local: np.ndarray, c_iso: np.ndarray):
        info = vox.model["info"]
        hh = vox.height
        self.vox, self.a = vox, float(vox.model["h"])
        self.col, self.pos = hh["col"], hh["pos"]  # each free cube's column and its place in it
        n_cols = hh["n_cols"]
        col_len = np.zeros(n_cols)
        np.maximum.at(col_len, self.col, self.pos + 1.0)
        self.col_len_mm = col_len * self.a
        self.groups, off = [], 0
        for g in groups:
            grp = Group(g, info, self.col_len_mm, self.a, off)
            self.groups.append(grp)
            off += grp.size
        self.size = off
        self.group_of_col = np.zeros(n_cols, int)
        self.local_of_col = np.zeros(n_cols, int)
        for i, grp in enumerate(self.groups):
            self.group_of_col[grp.cols] = i
            self.local_of_col[grp.cols] = np.arange(len(grp.cols))
        self.c_local, self.c_iso = c_local, c_iso
        self.density = float(vox.density)

    def start(self, value: float = 0.6) -> np.ndarray:
        x = np.full(self.size, value)
        for grp in self.groups:  # the turns start at none
            x[grp.offset + 4 * grp.n : grp.offset + 5 * grp.n] = 0.5
        return x

    def per_column(self, x) -> dict:
        """Every column's families (rho, height, ...) and direction, from the design vector."""
        n_cols = len(self.col_len_mm)
        theta = np.zeros(n_cols)
        fam = [{k: np.zeros(n_cols) for k in ("rho", "r", "h", "cap", "dh_drho")} for _ in range(2)]
        for grp in self.groups:
            xg = grp.x_of(x)
            grp.set_theta(xg)
            theta[grp.cols] = grp.theta
            for k, f in enumerate(grp.columns(xg)):
                for key in fam[k]:
                    fam[k][key][grp.cols] = f[key]
        return {"theta": theta, "fam": fam}

    def stiffness(self, x) -> tuple[np.ndarray, dict]:
        pc = self.per_column(x)
        col, pos, a = self.col, self.pos, self.a
        c = np.broadcast_to(ERSATZ * self.c_iso, (len(col), 6, 6)).copy()
        for k, f in enumerate(pc["fam"]):
            z0 = pos * a
            h = f["h"][col]
            g = np.clip((h - z0) / a, 0.0, 1.0)
            dg = np.where((h > z0) & (h < z0 + a), 1.0 / a, 0.0)
            crib, dcrib = toymodel.rib_tensor(pc["theta"][col] + k * np.pi / 2, self.c_local)
            c += (g * f["rho"][col])[:, None, None] * crib
            f.update(g=g, dg=dg, crib=crib, dcrib=dcrib)
        return c, pc

    def mass(self, pc) -> float:
        a3 = self.a**3
        return sum(float((f["g"] * f["rho"][self.col]).sum()) for f in pc["fam"]) * a3 * self.density

    def back(self, pc, d_c: np.ndarray | None = None, mass: bool = False) -> np.ndarray:
        """The derivatives by the design vector of one function, given its derivative by every free
        cube's 6 x 6 stiffness `d_c` (rib cubes, 6, 6), or of the mass."""
        col, n_cols = self.col, len(self.col_len_mm)
        d_rho, d_r = [], []
        d_th = np.zeros(n_cols)
        a3 = self.a**3 * self.density
        for f in pc["fam"]:
            rho = f["rho"][col]
            via_rho = f["g"] + rho * f["dg"] * f["dh_drho"][col]
            via_r = rho * f["dg"] * f["cap"][col]
            if mass:
                e_rib = np.full(len(col), a3)
            else:
                e_rib = np.einsum("epq,epq->e", d_c, f["crib"])
                d_th += np.bincount(col, np.einsum("epq,epq->e", d_c, f["dcrib"]) * f["g"] * rho, n_cols)
            d_rho.append(np.bincount(col, e_rib * via_rho, n_cols))
            d_r.append(np.bincount(col, e_rib * via_r, n_cols))
        out = np.zeros(self.size)
        for grp in self.groups:
            cl, bt, n = grp.cols, grp.B.T, grp.n
            o = grp.offset
            for k in range(2):
                out[o + 2 * k * n : o + (2 * k + 1) * n] = bt @ (grp.rho_most * d_rho[k][cl])
                out[o + (2 * k + 1) * n : o + (2 * k + 2) * n] = bt @ d_r[k][cl]
            out[o + 4 * n : o + 5 * n] = np.pi * (bt @ d_th[cl])
        return out

    def align(self, energy_free: np.ndarray, pc) -> None:
        """Each column's start direction: the one in which a rib takes the most energy under the
        strains at the start, smoothed over `THETA_SMOOTH` mm as a doubled angle within its group."""
        angles = np.radians(np.arange(0, 180, 5.0))
        col, n_cols = self.col, len(self.col_len_mm)
        tot = np.zeros((n_cols, len(angles)))
        for k, f in enumerate(pc["fam"]):
            crib, _ = toymodel.rib_tensor(angles + k * np.pi / 2, self.c_local)
            w = np.maximum(f["g"], 0.25)
            np.add.at(tot, col, np.einsum("epq,mpq->em", energy_free, crib) * w[:, None])
        best = angles[np.argmax(tot, axis=1)]
        strength = tot.max(axis=1) - tot.min(axis=1)
        v = strength[:, None] * np.stack([np.cos(2 * best), np.sin(2 * best)], axis=1)
        for grp in self.groups:
            nx, ny = grp.ij.max(axis=0) + 1
            gv = np.zeros((2, nx, ny))
            m = np.zeros((nx, ny))
            gv[:, grp.ij[:, 0], grp.ij[:, 1]] = v[grp.cols].T
            m[grp.ij[:, 0], grp.ij[:, 1]] = 1.0
            sig = THETA_SMOOTH / self.a
            sm = np.stack([gaussian_filter(gv[i], sig, mode="nearest") for i in range(2)])
            wm = gaussian_filter(m, sig, mode="nearest")
            tv = (sm / np.maximum(wm, 1e-9))[:, grp.ij[:, 0], grp.ij[:, 1]].T
            grp.theta0 = 0.5 * np.arctan2(tv[:, 1], tv[:, 0])
            grp.theta = grp.theta0.copy()
            grp.theta0_grad = rules.theta_gradient(grp.theta0, grp.ij, self.a)

    def rules(self, x) -> list[tuple[str, float, np.ndarray, float]]:
        """Every group's fastcae rules: (name, G, dG/dx over the whole vector, the measure)."""
        out = []
        for grp in self.groups:
            xg = grp.x_of(x)
            grp.set_theta(xg)
            for key, (g, dg, meas) in rules.transport(grp, xg).items():
                full = np.zeros(self.size)
                full[grp.offset : grp.offset + grp.size] = dg
                out.append((f"{grp.name}:{key}", g, full, meas))
        return out
