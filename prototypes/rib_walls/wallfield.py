"""The rib field on the housing's walls, with its production features (LOP-34, the restart; a
prototype). The settings are the engineer's of 16 October (~10:25 IST): ribs 8-12 mm thick, 40 mm
apart, up to 24 mm tall, two families at right angles; a ring boss round each bearing's seat and
two gusset webs from each mount's lug to the wall, sized by the optimiser.

Every free cube stands on a wall (`surface.map_cubes`: its distance out `d`, the wall's normal `n`,
a tangent frame `e1`, `e2`). Per half, each family k has a thickness share sigma_k and a height share
r_k, and the half has a turn tau: cubic B-splines in space (`KNOT` mm), read at each cube's foot on
the wall. Family 0 runs at theta = theta0 + pi (tau - 1/2) in the wall's tangent plane, family 1 at
theta + 90 degrees; theta0 is where the strains first put the ribs (`align`). A rib family's metal:

- thickness t = sigma x T_cap (T_NEAR at a hard point to T_FAR away, `T_TAPER` mm), its share of the
  cube rho = t / SPACING; under T_MIN a rib carries nothing, all of it from T_MIN + T_RAMP;
- height h = r x min(H_MOST, TALL x t) off the wall, the cube's share of it g (its span along n);
- stiffness: a plate along t and n, nothing across it (the toy's laminate) turned into the cube's
  frame (`frame_rotation`).

On a face along the pull (a side wall) only family 0 stands, along the pull, its thickness and height
read at the split above its foot: a fin of one section from the flange down its wall, as production's
side-wall ribs, castable in the two-part mould (a rib across the pull there, or one whose height
changed down the wall, would be an undercut). On the end walls (and the plate under the other half's
opening) both families and their turn are free: drawn along the pull from the wall, any direction
casts.

The features, each a solid share v of the cube, joined as a union (s = 1 - prod(1 - v)): a ring boss
round each bearing (its outer radius, and its height past the bearing's outer end and the wall),
standing on whatever wall lies under it (a cap on the bore's end wall, a collar down a tall tube),
and per mount two webs from the lug to the wall, from its far end to the split (thickness, at least
`WEB_LEAST`, and spread). A cube is s x solid + (1 - s) x its ribs, its mass likewise. Every
share is a smooth step over the cube (C1), so the derivatives hold across the cubes' edges.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rib_field"))
import toy  # noqa: E402

SPACING = 40.0  # mm between a family's ribs
T_MIN, T_RAMP = 8.0, 2.0  # mm: under T_MIN a rib carries nothing, all of it from T_MIN + T_RAMP
T_NEAR, T_FAR, T_TAPER = 12.0, 10.0, 30.0  # mm: the thickest rib at a hard point, away, over
H_MOST = 24.0  # mm: the tallest rib (the recipe's band)
TALL = 5.0  # a rib at most this many times its thickness tall (fastcae's tallest_ratio)
KNOT = 16.0  # mm
ERSATZ = 1e-4
BOSS_GROW = (6.0, 30.0)  # mm: a ring boss's outer radius past the bore, least and range
BOSS_TALL = (2.0, 22.0)  # mm: its height past the bearing's outer end and the wall, least and range
WEB_LEAST, WEB_MOST = 8.0, 16.0  # mm: a bracket web's thickness
WEB_SPREAD = (math.radians(10.0), math.radians(50.0))  # each web's angle off the lug-wall line
PAIRS = [(0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)]  # the product's Voigt order


def frame_rotation(R: np.ndarray, dR: np.ndarray | None = None):
    """(n, 6, 6) T with local strains = T global strains (engineering shears, the product's order),
    the local axes the columns of R (n, 3, 3); and its derivative given dR."""
    n = len(R)
    T = np.zeros((n, 6, 6))
    dT = None if dR is None else np.zeros((n, 6, 6))
    for row, (i, j) in enumerate(PAIRS):
        f = 1.0 if i == j else 2.0
        for col, (a, b) in enumerate(PAIRS):
            if a == b:
                T[:, row, col] = f * R[:, a, i] * R[:, a, j]
                if dR is not None:
                    dT[:, row, col] = f * (dR[:, a, i] * R[:, a, j] + R[:, a, i] * dR[:, a, j])
            else:
                T[:, row, col] = 0.5 * f * (R[:, a, i] * R[:, b, j] + R[:, b, i] * R[:, a, j])
                if dR is not None:
                    dT[:, row, col] = 0.5 * f * (dR[:, a, i] * R[:, b, j] + R[:, a, i] * dR[:, b, j]
                                                 + dR[:, b, i] * R[:, a, j] + R[:, b, i] * dR[:, a, j])
    return T, dT


def rib_tensor(theta: np.ndarray, e1: np.ndarray, e2: np.ndarray, n: np.ndarray, local: np.ndarray):
    """(n, 6, 6): a rib running at theta in each cube's tangent frame (a plate along t and n), and
    its derivative by theta (dt = m, dm = -t)."""
    c, s = np.cos(theta)[:, None], np.sin(theta)[:, None]
    t = c * e1 + s * e2
    m = np.cross(n, t)
    R = np.stack([t, m, n], axis=2)
    dR = np.stack([m, -t, np.zeros_like(n)], axis=2)
    T, dT = frame_rotation(R, dR)
    C = np.einsum("nqp,qr,nrs->nps", T, local, T)
    dC = np.einsum("nqp,qr,nrs->nps", dT, local, T)
    return C, dC + dC.transpose(0, 2, 1)


def bspline3(p: np.ndarray, lo: np.ndarray, hi: np.ndarray, knot: float, used: np.ndarray | None = None):
    """The cubic B-spline basis in space at points p (clipped into [lo, hi]), and its derivatives by
    x, y, z (sparse), its columns those any point uses (or `used`, to read a field at other points);
    and the columns kept."""
    p = np.clip(p, lo, hi)
    mats = []
    for ax in range(3):
        L = hi[ax] - lo[ax] + knot
        u = p[:, ax] - lo[ax] + knot / 2
        mats.append((toy.bspline_1d(u, L, knot), toy.bspline_1d_deriv(u, L, knot)))
    nb = [m[0].shape[1] for m in mats]
    rows, cols, v, vx, vy, vz = [], [], [], [], [], []
    idx = [np.argsort(-m[0], axis=1)[:, :4] for m in mats]  # each point's four live splines an axis
    npts = len(p)
    ar = np.arange(npts)
    for a in range(4):
        for b in range(4):
            for c in range(4):
                i, j, k = idx[0][:, a], idx[1][:, b], idx[2][:, c]
                bx, by, bz = mats[0][0][ar, i], mats[1][0][ar, j], mats[2][0][ar, k]
                dx, dy, dz = mats[0][1][ar, i], mats[1][1][ar, j], mats[2][1][ar, k]
                rows.append(ar)
                cols.append((i * nb[1] + j) * nb[2] + k)
                v.append(bx * by * bz)
                vx.append(dx * by * bz)
                vy.append(bx * dy * bz)
                vz.append(bx * by * dz)
    shape = (npts, nb[0] * nb[1] * nb[2])
    r, cc = np.concatenate(rows), np.concatenate(cols)
    out = [sp.csr_matrix((np.concatenate(w), (r, cc)), shape=shape) for w in (v, vx, vy, vz)]
    if used is None:
        used = np.unique(out[0].indices)
    return [m[:, used].tocsr() for m in out], used


def smoothstep(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u), 6 * u * (1 - u)


def share(x, width: float):
    """A cube's share of a span ending at x (mm past the cube's centre): a smooth step over `width`
    (C1; its integral the linear share's), and its derivative by x."""
    s, ds = smoothstep((x + 0.5 * width) / width)
    return s, ds / width


class WallField:
    """Every free cube's ribs and features from the design vector, and the chain back."""

    def __init__(self, vox, cm: dict, layout: dict, c_local: np.ndarray, c_iso: np.ndarray, all_rooms):
        import surface

        self.vox, self.cm, self.layout = vox, cm, layout
        self.surface = surface
        self.a = float(vox.model["h"])
        self.density = float(vox.density)
        self.c_local, self.c_iso = c_local, c_iso
        self.n_cubes = len(cm["d"])
        s = layout["settings"]
        split = float(layout["z"]["split"])
        self.split = split
        foot = cm["foot"]
        # on a face along the pull (a side wall) a rib runs along the pull (theta 0) and only family 0:
        # a rib across the pull there, or one whose height changed down the wall, would be an undercut
        # for the two-part mould; its thickness and height are read at the split, so each is a fin of
        # one section from the flange down its wall, as production's side-wall ribs
        self.across = cm["across"].astype(bool)
        self.along = ~self.across
        self.read_at = foot.copy()
        self.read_at[self.along, 2] = split
        # the fields: per half, five B-spline fields (sigma0, r0, sigma1, r1, tau)
        self.halves = []
        off = 0
        for half, sel in (("motor_side", cm["lower"]), ("cover", ~cm["lower"])):
            rows = np.flatnonzero(sel)
            p = self.read_at[rows]
            lo_b, hi_b = p.min(axis=0), p.max(axis=0)
            (B, Bx, By, Bz), used = bspline3(p, lo_b, hi_b, KNOT)
            nb = B.shape[1]
            self.halves.append({"half": half, "rows": rows, "B": B, "Bx": Bx, "By": By, "Bz": Bz,
                                "nb": nb, "off": off, "lo": lo_b, "hi": hi_b, "used": used})
            off += 5 * nb
        self.n_field = off
        # thickness by place: T_NEAR at a hard point (each bearing's seat, bolt's boss, mount's lug)
        self.hard = []
        for b in layout["bearings"]:
            self.hard.append((b["axis"], b["D"] / 2 + s["wall"], b["z"]))
        t_f = float(layout["flange"]["thickness"])
        for c in layout["bolts"]:
            self.hard.append((c, s["bolt_boss"] / 2, (split - t_f, split + t_f)))
        for mt in layout["mounts"]:
            self.hard.append((mt["centre"], s["mount_diameter"] / 2, mt["z"]))
        self.tcap, self.hard_dist = self.thickness_cap(self.read_at)
        # the ring bosses: one per bearing, a round boss on its axis, standing on whatever wall lies under
        # it in its half (or hanging from the split) up to its height past the bearing's outer end and
        # the wall: a cap on a bore's own end wall, a collar down a tall tube to the wall below (16
        # October: capped only, the seats at the cover's tall tubes' far ends kept 1.6 x their bed
        # line); castable along the pull by construction
        self.bosses = []
        wall = float(s["wall"])
        for b in layout["bearings"]:
            below = 0.5 * (b["z"][0] + b["z"][1]) < split
            z_out = min(b["z"]) - wall if below else max(b["z"]) + wall  # the bearing's outer end's face
            reach = BOSS_TALL[0] + BOSS_TALL[1] + self.a
            zc = cm["centre"][:, 2]
            r_all = np.hypot(cm["centre"][:, 0] - b["axis"][0], cm["centre"][:, 1] - b["axis"][1])
            on = np.flatnonzero((cm["lower"] == below) & (r_all < b["D"] / 2 + BOSS_GROW[0] + BOSS_GROW[1] + self.a)
                                & ((zc >= z_out - reach) if below else (zc <= z_out + reach)))
            # how far each cube stands out past the bearing's end (mm, toward the outside)
            past = (z_out - zc[on]) if below else (zc[on] - z_out)
            self.bosses.append({"name": f"{b['shaft']} {b['side']}", "cubes": on, "r": r_all[on], "r0": b["D"] / 2,
                                "past": past, "z_out": z_out, "axis": list(b["axis"]),
                                "half": "motor_side" if below else "cover"})
        # the brackets: two webs per mount from the lug to the wall, up to the split. Each mount's
        # spread is kept to the angles whose ray at the lug's mid-height meets the wall (4 degrees in):
        # past them a web would run beside the wall or into nothing (mounts 2 and 3 stand 105 mm off
        # the wall, and their rays miss it past 20 degrees). A web runs to the wall itself (the free
        # cubes end there), at most as far as the farthest such ray, so no reach enters its share.
        self.webs = []
        for mt in layout["mounts"]:
            cxy = np.asarray(mt["centre"], float)
            zmid = 0.5 * (mt["z"][0] + mt["z"][1])
            half = "motor_side" if mt["z"][1] <= split else "cover"
            angles = np.radians(np.arange(0, 360, 1.0))
            reach = np.array([self._ray(cxy, zmid, a_, half, all_rooms) for a_ in angles])
            phi0 = float(angles[np.argmin(reach)])  # the way to the wall: the nearest
            off = np.abs(np.angle(np.exp(1j * (angles - phi0))))
            missed = off[reach >= 399.0]
            most_off = (float(missed.min()) if len(missed) else math.pi) - math.radians(4.0)
            span = float(np.clip(most_off, WEB_SPREAD[0] + math.radians(2.0), WEB_SPREAD[0] + WEB_SPREAD[1]))
            span -= WEB_SPREAD[0]
            l_cap = float(reach[off <= WEB_SPREAD[0] + span + math.radians(1.0)].max()) + 2.0
            # from the lug's far end to the split, joining the flange (production's gusseted lug, the
            # engineer's LOOP_LUG_WEBS of 13 October; over the lug's height alone the webs were the
            # beds' strongest lever at their thickest, and the bosses grew to drums instead); the
            # bracket's kept-clear room over the lug holds no free cube
            z_lo, z_hi = (mt["z"][0], split) if half == "motor_side" else (split, mt["z"][1])
            in_z = np.flatnonzero((cm["centre"][:, 2] >= z_lo) & (cm["centre"][:, 2] <= z_hi)
                                  & (cm["lower"] == (half == "motor_side"))
                                  & (np.hypot(cm["centre"][:, 0] - cxy[0], cm["centre"][:, 1] - cxy[1])
                                     < l_cap + 2.0 * self.a))
            self.webs.append({"name": mt["name"], "centre": cxy, "zmid": zmid, "half": half, "phi0": phi0,
                              "z_span": (float(z_lo), float(z_hi)),
                              "span": span, "l_cap": l_cap, "reach0": float(reach.min()),
                              "r_lug": s["mount_diameter"] / 2, "cubes": in_z, "all_rooms": all_rooms})
        self.size = self.n_field + 2 * len(self.bosses) + 2 * len(self.webs)
        self.theta0 = np.zeros(self.n_cubes)

    def thickness_cap(self, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The thickest rib at points p (T_NEAR at a hard point to T_FAR at T_TAPER mm off), and the
        distance to the nearest hard point (a cylinder segment)."""
        dist = np.full(len(p), np.inf)
        for axis, r, (z0, z1) in self.hard:
            dr = np.maximum(np.hypot(p[:, 0] - axis[0], p[:, 1] - axis[1]) - r, 0.0)
            dz = np.maximum(np.maximum(z0 - p[:, 2], p[:, 2] - z1), 0.0)
            dist = np.minimum(dist, np.hypot(dr, dz))
        st, _ = smoothstep(dist / T_TAPER)
        return T_FAR + (T_NEAR - T_FAR) * (1.0 - st), dist

    def _ray(self, cxy, z, ang, half, all_rooms) -> float:
        """How far from the lug's axis, at angle ang in plan, a ray first meets the shell (mm): marched,
        then bisected to 1e-7 mm, so the reach is smooth in the angle."""
        u = np.array([math.cos(ang), math.sin(ang)])

        def sdf(t):
            p = np.array([[cxy[0] + t * u[0], cxy[1] + t * u[1], z]])
            return float(self.surface.shell_sdf(p, self.layout, all_rooms, half)[0])

        prev, tpar = 0.0, 0.0
        for _ in range(2000):
            d = sdf(tpar)
            if d <= 0.0:
                break
            prev = tpar
            tpar += max(d, 0.25)
            if tpar > 400:
                return 400.0
        lo, hi = prev, tpar
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if sdf(mid) > 0.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    # ---- the field read anywhere (the drawing)
    def values_at(self, x, half: str, p: np.ndarray) -> list[np.ndarray]:
        """The half's five fields (sigma0, r0, sigma1, r1, tau) at read points p (n, 3)."""
        hf = next(h for h in self.halves if h["half"] == half)
        (B, *_), _ = bspline3(p, hf["lo"], hf["hi"], KNOT, used=hf["used"])
        return [B @ self.field_x(x, hf, k) for k in range(5)]

    def theta0_at(self, half: str, p: np.ndarray, reach: float | None = None) -> np.ndarray:
        """The start directions of the half's end-wall cubes read at points p on the end walls: their
        doubled angles weighed by a Gaussian over their feet (half width a cube), the nearest's
        where none lies within `reach` (2 cubes)."""
        from scipy.spatial import cKDTree

        reach = reach or 2.0 * self.a
        sel = np.flatnonzero(self.across & (self.cm["lower"] == (half == "motor_side")))
        feet = self.cm["foot"][sel]
        v = np.stack([np.cos(2 * self.theta0[sel]), np.sin(2 * self.theta0[sel])], axis=1)
        tree = cKDTree(feet)
        acc = np.zeros((len(p), 2))
        for i, nb in enumerate(tree.query_ball_point(p, reach)):
            if nb:
                w = np.exp(-0.5 * (np.linalg.norm(feet[nb] - p[i], axis=1) / (0.5 * self.a)) ** 2)
                acc[i] = w @ v[nb]
        empty = np.linalg.norm(acc, axis=1) < 1e-12
        if empty.any():
            _, j = tree.query(p[empty])
            acc[empty] = v[j]
        return 0.5 * np.arctan2(acc[:, 1], acc[:, 0])

    # ---- the design vector's parts
    def field_x(self, x, hf, k):
        return x[hf["off"] + k * hf["nb"]: hf["off"] + (k + 1) * hf["nb"]]

    def boss_x(self, x, i):
        o = self.n_field + 2 * i
        return x[o], x[o + 1]

    def web_x(self, x, i):
        o = self.n_field + 2 * len(self.bosses) + 2 * i
        return x[o], x[o + 1]

    def start(self, sigma: float = 0.85, r: float = 0.5, boss: float = 0.3, web: float = 0.5) -> np.ndarray:
        x = np.zeros(self.size)
        for hf in self.halves:
            for k, v in enumerate((sigma, r, sigma, r, 0.5)):
                x[hf["off"] + k * hf["nb"]: hf["off"] + (k + 1) * hf["nb"]] = v
        x[self.n_field: self.n_field + 2 * len(self.bosses)] = boss
        x[self.n_field + 2 * len(self.bosses):] = web
        return x

    def lower_bounds(self) -> np.ndarray:
        lo = np.zeros(self.size)
        for i in range(len(self.webs)):  # each web at least WEB_LEAST thick (the lug never hangs loose)
            lo[self.n_field + 2 * len(self.bosses) + 2 * i] = (WEB_LEAST - 0.0) / WEB_MOST
        return lo

    # ---- per cube
    def per_cube(self, x) -> dict:
        n = self.n_cubes
        cm, a = self.cm, self.a
        out = {"fam": [], "theta": np.zeros(n)}
        sig = [np.zeros(n), np.zeros(n)]
        rr = [np.zeros(n), np.zeros(n)]
        tau = np.zeros(n)
        for hf in self.halves:
            rows, B = hf["rows"], hf["B"]
            sig[0][rows] = B @ self.field_x(x, hf, 0)
            rr[0][rows] = B @ self.field_x(x, hf, 1)
            sig[1][rows] = B @ self.field_x(x, hf, 2)
            rr[1][rows] = B @ self.field_x(x, hf, 3)
            tau[rows] = B @ self.field_x(x, hf, 4)
        theta = np.where(self.across, self.theta0 + math.pi * (tau - 0.5), 0.0)  # along the pull on a side wall
        out["theta"], out["sig"], out["r"], out["tau"] = theta, sig, rr, tau
        for k in range(2):
            t = sig[k] * self.tcap  # mm
            rho_raw = t / SPACING
            s_, ds_ = smoothstep((t - T_MIN) / T_RAMP)
            on = 1.0 if k == 0 else self.across  # family 1 only on faces across the pull
            rho = rho_raw * s_ * on
            drho_dt = (s_ + t * ds_ / T_RAMP) / SPACING * on  # d rho / d thickness
            cap, dcap = toy.smin(H_MOST, TALL * t)
            h = rr[k] * cap
            g, dg = share(h - cm["d"], a)  # the cube's share of a rib h tall, the cube at d
            C, dC = rib_tensor(theta + k * math.pi / 2, cm["e1"], cm["e2"], cm["n"], self.c_local)
            out["fam"].append({"t": t, "rho": rho, "drho_dt": drho_dt, "h": h, "cap": cap,
                               "dh_dt": rr[k] * dcap * TALL, "g": g, "dg": dg, "C": C, "dC": dC})
        # the features' solid share: their union, 1 - prod(1 - v)
        feats = []
        for i, bs in enumerate(self.bosses):
            xr, xh = self.boss_x(x, i)
            Rb = bs["r0"] + BOSS_GROW[0] + BOSS_GROW[1] * xr
            hb = BOSS_TALL[0] + BOSS_TALL[1] * xh
            gr, dgr = share(Rb - bs["r"], a)
            gh, dgh = share(hb - bs["past"], a)
            feats.append({"kind": "boss", "i": i, "cubes": bs["cubes"], "v": gr * gh,
                          "d0": dgr * gh * BOSS_GROW[1], "d1": gr * dgh * BOSS_TALL[1]})
        for i, wb in enumerate(self.webs):
            xt, xa = self.web_x(x, i)
            tw = WEB_MOST * xt
            alpha = WEB_SPREAD[0] + wb["span"] * xa
            cubes = wb["cubes"]
            p = cm["centre"][cubes, :2] - wb["centre"]
            for sgn in (1.0, -1.0):
                psi = wb["phi0"] + sgn * alpha
                u = np.array([math.cos(psi), math.sin(psi)])
                along = p @ u
                cross = p[:, 0] * u[1] - p[:, 1] * u[0]  # d along / d psi = -cross
                # across the web: within half its thickness of its line; along it: from the lug on
                gw, dgw = share(0.5 * tw - np.abs(cross), a)
                g1, dg1 = share(along - (wb["r_lug"] - 2.0), a)
                g2, dg2 = share(wb["l_cap"] - along, a)
                gl = g1 * g2
                dgl = (dg1 * g2 - g1 * dg2) * (-cross)
                dgw_dpsi = -dgw * np.sign(cross) * along
                feats.append({"kind": "web", "i": i, "cubes": cubes, "v": gw * gl,
                              "d0": dgw * 0.5 * WEB_MOST * gl,
                              "d1": (dgw_dpsi * gl + gw * dgl) * sgn * wb["span"]})
        ones = np.zeros(n, int)
        p_excl = np.ones(n)
        for ft in feats:
            full = ft["v"] >= 1.0
            np.add.at(ones, ft["cubes"][full], 1)
            np.multiply.at(p_excl, ft["cubes"][~full], 1.0 - ft["v"][~full])
        s = 1.0 - np.where(ones == 0, p_excl, 0.0)
        for ft in feats:  # each feature's d s / d v: the product of the others' (1 - v)
            c, v = ft["cubes"], ft["v"]
            ft["others"] = np.where(v < 1.0, np.where(ones[c] == 0, p_excl[c] / np.maximum(1.0 - v, 1e-300), 0.0),
                                    np.where(ones[c] == 1, p_excl[c], 0.0))
        out["s"], out["feats"] = s, feats
        return out

    def stiffness(self, x):
        pc = self.per_cube(x)
        u = 1.0 - pc["s"]
        c = np.broadcast_to(ERSATZ * self.c_iso, (self.n_cubes, 6, 6)).copy()
        for f in pc["fam"]:
            c += (u * f["g"] * f["rho"])[:, None, None] * f["C"]
        c += pc["s"][:, None, None] * self.c_iso
        pc["u"] = u
        return c, pc

    def masses(self, pc) -> tuple[float, float]:
        a3 = self.a**3 * self.density
        ribs = sum(float((pc["u"] * f["g"] * f["rho"]).sum()) for f in pc["fam"]) * a3
        return ribs, float(pc["s"].sum()) * a3

    def mass(self, pc) -> float:
        return sum(self.masses(pc))

    def back(self, pc, d_c=None, mass: bool = False) -> np.ndarray:
        """The derivative by the design vector of a function given its derivative by every free cube's
        6 x 6 stiffness `d_c`, or of the mass."""
        n = self.n_cubes
        a3 = self.a**3 * self.density
        u = pc["u"]
        d_sig, d_r = [], []
        d_theta = np.zeros(n)
        e_s = np.zeros(n)  # by the solid share
        for f in pc["fam"]:
            e = np.full(n, a3) if mass else np.einsum("epq,epq->e", d_c, f["C"])
            if not mass:
                d_theta += u * f["g"] * f["rho"] * np.einsum("epq,epq->e", d_c, f["dC"])
            e_s -= e * f["g"] * f["rho"]
            # by the thickness (mm): through rho and through the height's cap
            d_t = u * e * (f["g"] * f["drho_dt"] + f["rho"] * f["dg"] * f["dh_dt"])
            d_sig.append(d_t * self.tcap)
            d_r.append(u * e * f["rho"] * f["dg"] * f["cap"])
        e_s += np.full(n, a3) if mass else np.einsum("epq,pq->e", d_c, self.c_iso)
        g = np.zeros(self.size)
        for hf in self.halves:
            rows, bt, nb, o = hf["rows"], hf["B"].T, hf["nb"], hf["off"]
            g[o: o + nb] = bt @ d_sig[0][rows]
            g[o + nb: o + 2 * nb] = bt @ d_r[0][rows]
            g[o + 2 * nb: o + 3 * nb] = bt @ d_sig[1][rows]
            g[o + 3 * nb: o + 4 * nb] = bt @ d_r[1][rows]
            g[o + 4 * nb: o + 5 * nb] = math.pi * (bt @ (d_theta * self.across)[rows])
        for ft in pc["feats"]:
            base = self.n_field + (2 * ft["i"] if ft["kind"] == "boss" else 2 * len(self.bosses) + 2 * ft["i"])
            es = e_s[ft["cubes"]] * ft["others"]
            g[base] += float(es @ ft["d0"])
            g[base + 1] += float(es @ ft["d1"])
        return g

    def align(self, energy, pc, smooth_mm: float = 12.0) -> None:
        """Each cube's start direction: where a rib takes the most of the first analysis's strain
        energy, as a doubled angle in its frame, averaged over its neighbours within `smooth_mm` on
        faces of its own kind (across the pull, or along it)."""
        from scipy.spatial import cKDTree

        n = self.n_cubes
        cm = self.cm
        angles = np.radians(np.arange(0.0, 180.0, 7.5))
        tot = np.zeros((n, len(angles)))
        w = np.maximum(sum(f["g"] for f in pc["fam"]), 0.25)
        for ia, ang in enumerate(angles):
            for k in range(2):
                C, _ = rib_tensor(np.full(n, ang + k * math.pi / 2), cm["e1"], cm["e2"], cm["n"], self.c_local)
                tot[:, ia] += np.einsum("epq,epq->e", energy, C) * w
        best = angles[np.argmax(tot, axis=1)]
        strength = tot.max(axis=1) - tot.min(axis=1)
        v = strength[:, None] * np.stack([np.cos(2 * best), np.sin(2 * best)], axis=1)
        sm = np.zeros_like(v)
        for kind in (True, False):
            for lower in (True, False):
                sel = np.flatnonzero((cm["across"] == kind) & (cm["lower"] == lower))
                if not len(sel):
                    continue
                tree = cKDTree(cm["foot"][sel])
                pairs = tree.sparse_distance_matrix(tree, smooth_mm, output_type="coo_matrix")
                wmat = sp.coo_matrix((np.exp(-0.5 * (pairs.data / (0.5 * smooth_mm)) ** 2), (pairs.row, pairs.col)),
                                     shape=(len(sel), len(sel))).tocsr()
                wmat = wmat + sp.eye(len(sel))
                sm[sel] = wmat @ v[sel]
        self.theta0 = np.where(self.across, 0.5 * np.arctan2(sm[:, 1], sm[:, 0]), 0.0)
