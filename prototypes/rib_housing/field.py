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
ARM_MOST = 0.95  # an arm's floor at most this share of a column (`arm_floor`)


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


def solid_zone(vox) -> np.ndarray:
    """Each free cube: may it hold solid metal? Within a bearing's handbook boss (0.625 D + 5 mm of
    its axis, the product's own boss zone) in its half, or in a mount's corridor (the product's set-up:
    within the mount's reach of the shell plus the band, at the mount's height and the band's past it,
    to the split): production's bosses and brackets (16 October: ribs alone left the beds 15-20 x
    their lines; the reference meets them with solid bosses and arms)."""
    m = vox.model
    info, s = m["info"], m["info"]["settings"]
    h, lo = float(m["h"]), np.asarray(m["lo"], float)
    ijk = vox.ijk[vox.free_e]
    xyz = lo + (ijk + 0.5) * h
    split = info["z"]["split"]
    band = 24.0
    zone = np.zeros(len(xyz), bool)
    below = xyz[:, 2] < split
    for b in info["bearings"]:
        b_below = 0.5 * (b["z"][0] + b["z"][1]) < split
        r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
        zone |= (r < 0.625 * b["D"] + 5.0) & (below == b_below)
    fixed_xyz = lo + (vox.ijk[vox.frozen] + 0.5) * h
    for mt in info["mounts"]:
        cx, cy = mt["centre"]
        d_fixed = np.hypot(fixed_xyz[:, 0] - cx, fixed_xyz[:, 1] - cy)
        shell = d_fixed[d_fixed > s["mount_diameter"] / 2 + h]  # the shell nearest, past the lug
        reach = float(shell.min()) + band if len(shell) else band
        z_lo, z_hi = mt["z"][0] - band, mt["z"][1] + band
        z_lo, z_hi = (z_lo, max(z_hi, split)) if mt["z"][1] <= split else (min(z_lo, split), z_hi)
        zone |= (np.hypot(xyz[:, 0] - cx, xyz[:, 1] - cy) <= reach) & (xyz[:, 2] >= z_lo) & (xyz[:, 2] <= z_hi)
    return zone


def zone_discs(vox) -> list[dict]:
    """The solid zones' discs in plan, exactly (`solid_zone`'s): each bearing's boss and each mount's
    corridor, with their half ("motor_side" or "cover")."""
    m = vox.model
    info, s = m["info"], m["info"]["settings"]
    h, lo = float(m["h"]), np.asarray(m["lo"], float)
    split = info["z"]["split"]
    out = []
    for b in info["bearings"]:
        below = 0.5 * (b["z"][0] + b["z"][1]) < split
        out.append({"half": "motor_side" if below else "cover", "centre": list(b["axis"]),
                    "r": 0.625 * b["D"] + 5.0, "kind": "boss"})
    fixed_xyz = lo + (vox.ijk[vox.frozen] + 0.5) * h
    for mt in info["mounts"]:
        cx, cy = mt["centre"]
        d_fixed = np.hypot(fixed_xyz[:, 0] - cx, fixed_xyz[:, 1] - cy)
        shell = d_fixed[d_fixed > s["mount_diameter"] / 2 + h]
        reach = float(shell.min()) + 24.0 if len(shell) else 24.0
        out.append({"half": "motor_side" if mt["z"][1] <= split else "cover", "centre": [cx, cy], "r": reach,
                    "kind": "mount"})
    return out


def arm_floor(hf, vox) -> tuple[np.ndarray, list[dict]]:
    """Each mount's least arm (16 October, a prototype rule for the engineer to agree): the solid
    columns within the lug's diameter (and the plan filter's 6 mm) of the straight line from the lug
    to the nearest fixed metal past it, held deep enough to reach the lug's far face. Without it the
    optimiser joined mount-1 by 6 cubes (`t5`): one held mount carries the housing under the one load
    case, and this run holds no modes (the baseline's modes are what joined its lugs). Returns the
    design vector's lower bounds and, per mount, the arm's columns and least metal."""
    m = vox.model
    info, s = m["info"], m["info"]["settings"]
    h, lo = float(m["h"]), np.asarray(m["lo"], float)
    split = info["z"]["split"]
    xmin = np.zeros(hf.size)
    fixed_xyz = lo + (vox.ijk[vox.frozen] + 0.5) * h
    n_cols = len(hf.col_len_mm)
    col_xy = np.zeros((n_cols, 2))
    col_half = np.zeros(n_cols, bool)  # True: the motor side
    for grp in hf.groups:
        col_xy[grp.cols] = grp.xy
        col_half[grp.cols] = grp.half == "motor_side"
    ijk = vox.ijk[vox.free_e]
    first = hf.pos == 0
    base = np.full(n_cols, -1, np.int64)
    base[hf.col[first]] = ijk[first, 2]
    zone_len = np.zeros(n_cols)
    np.maximum.at(zone_len, hf.col[hf.in_zone], (hf.pos[hf.in_zone] + 1.0) * hf.a)
    report = []
    r_lug = s["mount_diameter"] / 2
    for mt in info["mounts"]:
        below = mt["z"][1] <= split
        c = np.asarray(mt["centre"], float)
        d = np.hypot(fixed_xyz[:, 0] - c[0], fixed_xyz[:, 1] - c[1])
        beyond = (d > r_lug + h) & ((fixed_xyz[:, 2] < split) == below)
        p = fixed_xyz[beyond][np.argmin(d[beyond]), :2]
        seg = p - c
        t = np.clip(((col_xy - c) @ seg) / max(seg @ seg, 1e-9), 0.0, 1.0)
        off = np.hypot(*(col_xy - (c + t[:, None] * seg)).T)
        on = np.isin(np.arange(n_cols), hf.zcols) & (off <= r_lug + 6.0) & (col_half == below)
        face = lo[2] + h * (base + 1) if below else lo[2] + h * base
        need = (face - mt["z"][0]) if below else (mt["z"][1] - face)
        need = np.minimum(np.maximum(need, 0.0), zone_len)
        cols = np.flatnonzero(on & (need > 0))
        k = hf.zone_of_col[cols]
        # under the upper bound: a variable with xmin = xmax gives MMA asymptotes no span (`h2`'s
        # first try slid to nothing)
        xmin[hf.n_rib + k] = np.minimum(ARM_MOST, need[cols] / hf.col_len_mm[cols])
        kg = float((need[cols] * h * h).sum()) * vox.density
        report.append({"mount": mt["name"], "to": p.tolist(), "columns": int(len(cols)), "kg": kg})
    return xmin, report


class HousingField:
    """Every group's field, the free cubes' stiffness from the design vector, and the chain back.
    Beside the ribs, the solid zones (`solid_zone`: bosses and brackets) hold today's free columns:
    one height a column of solid metal, filtered over the plan, SIMP on each cube's share."""

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
        # the solid zones' columns: a variable each, the plan filter a cone of 6 mm within a group
        self.in_zone = solid_zone(vox)
        zcols = np.unique(self.col[self.in_zone])
        self.zcols = zcols
        self.n_rib = self.size
        self.size = self.n_rib + len(zcols)
        xy = np.zeros((n_cols, 2))
        lay = np.zeros(n_cols, int)
        for i, grp in enumerate(self.groups):
            xy[grp.cols] = grp.xy
            lay[grp.cols] = i
        from scipy.spatial import cKDTree

        pts = np.column_stack([xy[zcols, 0] + 1e6 * lay[zcols], xy[zcols, 1]])
        tree = cKDTree(pts)
        pp = tree.sparse_distance_matrix(tree, 6.0, output_type="coo_matrix")
        wmat = sp.coo_matrix((np.maximum(0.0, 6.0 - pp.data), (pp.row, pp.col)), shape=(len(zcols),) * 2).tocsr()
        wmat = (wmat + sp.eye(len(zcols)) * 6.0).tocsr()
        self.W = (sp.diags(1.0 / np.asarray(wmat.sum(axis=1)).ravel()) @ wmat).tocsr()
        self.zone_of_col = np.full(n_cols, -1)
        self.zone_of_col[zcols] = np.arange(len(zcols))
        self.penal = 1.0

    def start(self, value: float = 0.6, solid: float = 0.3) -> np.ndarray:
        x = np.full(self.size, value)
        for grp in self.groups:  # the turns start at none
            x[grp.offset + 4 * grp.n : grp.offset + 5 * grp.n] = 0.5
        x[self.n_rib :] = solid
        return x

    def solid(self, x) -> dict:
        """The solid zones' cubes' shares of their columns' heights."""
        hs = self.col_len_mm[self.zcols] * (self.W @ x[self.n_rib :])
        zc = self.zone_of_col[self.col]
        on = self.in_zone & (zc >= 0)
        z0 = self.pos * self.a
        h = np.where(on, hs[np.maximum(zc, 0)], 0.0)
        g = np.where(on, np.clip((h - z0) / self.a, 0.0, 1.0), 0.0)
        dg = np.where(on & (h > z0) & (h < z0 + self.a), 1.0 / self.a, 0.0)
        return {"g": g, "dg": dg, "zc": zc, "on": on, "hs": hs}

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
        """Each free cube's stiffness: the solid share s of it isotropic (SIMP), the rest (1 - s) its
        ribs' laminates, so a cube is never more than full."""
        pc = self.per_column(x)
        col, pos, a = self.col, self.pos, self.a
        so = self.solid(x)
        u = 1.0 - so["g"]
        c = np.broadcast_to(ERSATZ * self.c_iso, (len(col), 6, 6)).copy()
        for k, f in enumerate(pc["fam"]):
            z0 = pos * a
            h = f["h"][col]
            g = np.clip((h - z0) / a, 0.0, 1.0)
            dg = np.where((h > z0) & (h < z0 + a), 1.0 / a, 0.0)
            crib, dcrib = toymodel.rib_tensor(pc["theta"][col] + k * np.pi / 2, self.c_local)
            c += (u * g * f["rho"][col])[:, None, None] * crib
            f.update(g=g, dg=dg, crib=crib, dcrib=dcrib)
        c += (so["g"] ** self.penal)[:, None, None] * self.c_iso
        pc["solid"], pc["u"] = so, u
        return c, pc

    def mass(self, pc) -> float:
        return sum(self.masses(pc))

    def masses(self, pc) -> tuple[float, float]:
        """(the ribs' kg, the solid zones' kg)."""
        a3 = self.a**3 * self.density
        return (sum(float((pc["u"] * f["g"] * f["rho"][self.col]).sum()) for f in pc["fam"]) * a3,
                float(pc["solid"]["g"].sum()) * a3)

    def back(self, pc, d_c: np.ndarray | None = None, mass: bool = False) -> np.ndarray:
        """The derivatives by the design vector of one function, given its derivative by every free
        cube's 6 x 6 stiffness `d_c` (rib cubes, 6, 6), or of the mass."""
        col, n_cols = self.col, len(self.col_len_mm)
        d_rho, d_r = [], []
        d_th = np.zeros(n_cols)
        a3 = self.a**3 * self.density
        u = pc["u"]
        e_u = np.zeros(len(col))  # the function's derivative by each cube's rib share (1 - s)
        for f in pc["fam"]:
            rho = f["rho"][col]
            via_rho = f["g"] + rho * f["dg"] * f["dh_drho"][col]
            via_r = rho * f["dg"] * f["cap"][col]
            if mass:
                e_rib = np.full(len(col), a3)
            else:
                e_rib = np.einsum("epq,epq->e", d_c, f["crib"])
                d_th += np.bincount(col, np.einsum("epq,epq->e", d_c, f["dcrib"]) * f["g"] * rho * u, n_cols)
            e_u += e_rib * f["g"] * rho
            d_rho.append(np.bincount(col, e_rib * u * via_rho, n_cols))
            d_r.append(np.bincount(col, e_rib * u * via_r, n_cols))
        out = np.zeros(self.size)
        for grp in self.groups:
            cl, bt, n = grp.cols, grp.B.T, grp.n
            o = grp.offset
            for k in range(2):
                out[o + 2 * k * n : o + (2 * k + 1) * n] = bt @ (grp.rho_most * d_rho[k][cl])
                out[o + (2 * k + 1) * n : o + (2 * k + 2) * n] = bt @ d_r[k][cl]
            out[o + 4 * n : o + 5 * n] = np.pi * (bt @ d_th[cl])
        # the solid zones: d / d g = (p g^(p-1)) (d_c : C_iso), or the mass's a^3 density
        so = pc["solid"]
        if mass:
            e_g = np.full(len(col), a3)
        else:
            e_g = np.einsum("epq,pq->e", d_c, self.c_iso) * self.penal * np.maximum(so["g"], 1e-12) ** (self.penal - 1)
        e_g = e_g - e_u  # the ribs' share gives way to the solid's
        dh = np.bincount(np.maximum(so["zc"], 0), np.where(so["on"], e_g * so["dg"], 0.0), len(self.zcols))
        out[self.n_rib :] = self.W.T @ (dh * self.col_len_mm[self.zcols])
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
