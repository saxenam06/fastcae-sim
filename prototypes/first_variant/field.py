"""PROTOTYPE - not product code, not the judge.

Plan Part C, Task 10: the shell and the structure as signed distance fields on a voxel grid
(1.5 mm voxels, 2.0 mm if memory requires) over the installation space (the layout's envelope
grown by 20 mm, assumption A3). Negative inside, positive outside, in mm.

1. Keep-outs: each gear's tip cylinder + 5 mm radial and 3 mm axial clearance; each shaft between
   its seats (bearing bore + 3 mm); the bearings' own volumes; the shaft passages through the
   back-wall shoulders; each bolt's hole and the room for its head above the boss.
2. Cavity: the gears' keep-outs swept to the split face, so the core of the die can be drawn out
   along -z, and closed by a flat back at the keep-outs' far end. Its outline is the smooth union
   of the keep-out discs (necks rounded with 15 mm, prototype choice).
3. Shell: the band g <= f <= g + t (g = 5, t = 5 mm) outside the cavity, with f = C - delta(z) and
   delta = (z_wall_in - z) tan 2 deg: the offset grows toward the split face, so the cavity is
   widest at the opening and every side wall, inside and out, leans inward along the pull
   direction +z (A7) by 2 deg. Closed at the back wall, cut open at z = 0. A sealing lip runs round
   the split face.
4. Structure: plates (drafted, 6-8 mm) joined by a smooth union (blend 6 mm): webs from each
   back-wall seat ring to the mount pad, bridges input-intermediate and intermediate-output, and
   radial ribs from each seat ring to the shell (gussets under the motor flange at the input).
   Copies of the core's features, 0.3 mm undersize, are blended in so the members meet them with
   fillets, and the blend is capped at each ring and boss top so it never rises through the
   core's exact faces. The members are clipped to the installation space (the design domain);
   everything is clipped to stay out of the keep-outs and the cavity.
5. Reported checks, not enforced (applied to the joined housing by join.py with the functions
   here): wall-thickness map (distance transform), draft map, enclosed voids (flood fill).

write_outline() runs first: it gives core.py the shell's outline at the split face and the bolt
boss points along it (outline.json).
"""

from __future__ import annotations

import json
import math
import sys
import time

import numpy as np
import params as P
from layout import angle_deg, free_memory_mb, load_layout, outline_d2, peak_memory_mb, smin
from scipy import ndimage
from skimage import measure

# ================================================================== the outline (for the core)


def write_outline(layout=None):
    """The shell's outline at the split face (z = 0) and the bolt boss points along it."""
    layout = layout or load_layout()
    h = 0.25
    lo, hi = layout.space_lo - 40.0, layout.space_hi + 40.0  # bosses may leave the A3 box
    xs = np.arange(lo[0], hi[0] + h, h)
    ys = np.arange(lo[1], hi[1] + h, h)
    d2 = outline_d2(layout, xs[:, None], ys[None, :])
    d0 = float(layout.delta(0.0))
    g, t = P.SHELL_GAP, P.SHELL_WALL
    levels = {
        "cavity_inner": g + d0,
        "wall_outer": g + t + d0,
        "lip_outer": g + t + P.LIP_WIDTH + d0,
        "boss_centres": layout.boss_level_f() + d0,
    }
    curves = {}
    for name, lev in levels.items():
        cs = measure.find_contours(d2, lev)
        c = max(cs, key=len)
        xy = np.c_[xs[0] + c[:, 0] * h, ys[0] + c[:, 1] * h]
        if np.linalg.norm(xy[0] - xy[-1]) > 1e-6:
            raise RuntimeError(f"outline {name} is not closed")
        curves[name] = xy

    xy = curves["boss_centres"]
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    s = np.r_[0.0, np.cumsum(seg)]
    perimeter = float(s[-1])
    n = math.ceil(perimeter / P.BOSS_MAX_PITCH)
    s0 = s[int(np.argmax(xy[:, 0]))]  # one boss at the +x end
    targets = (s0 + perimeter * np.arange(n) / n) % perimeter
    bosses = np.c_[np.interp(targets, s, xy[:, 0]), np.interp(targets, s, xy[:, 1])]
    chords = np.linalg.norm(bosses - np.roll(bosses, -1, axis=0), axis=1)

    out = {
        "PROTOTYPE": "plan Part C, Task 10 (outline for Task 9); not product code",
        "z": 0.0,
        "levels_f_plus_draft": {k: round(v, 4) for k, v in levels.items()},
        "draft_offset_at_split": round(d0, 4),
        "boss_perimeter": round(perimeter, 2),
        "boss_count": n,
        "boss_pitch_along_outline": round(perimeter / n, 2),
        "boss_max_chord": round(float(chords.max()), 2),
        "bosses": [[round(float(a), 3), round(float(b), 3)] for a, b in bosses],
        "curves": {
            k: [[round(float(a), 2), round(float(b), 2)] for a, b in v[::4]]
            for k, v in curves.items()
        },
        "provenance": {"boss pitch <= 80 mm, d18, 5 mm beyond the wall": P.PROTO},
    }
    path = P.OUT / "outline.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(
        f"outline.json -> {path}: {n} bolt bosses, {perimeter / n:.1f} mm apart along the "
        f"outline (max chord {chords.max():.1f} mm)"
    )
    return out


# ================================================================== the grid and primitives


class Grid:
    def __init__(self, lo, hi, h):
        self.h = float(h)
        self.lo = np.asarray(lo, dtype=np.float64)
        self.n = tuple(int(math.ceil((hi[i] - lo[i]) / h)) + 1 for i in range(3))
        self.ax = [
            (self.lo[i] + self.h * np.arange(self.n[i])).astype(np.float32) for i in range(3)
        ]

    def coords(self, sl=None):
        sl = sl or (slice(None),) * 3
        return (
            self.ax[0][sl[0]][:, None, None],
            self.ax[1][sl[1]][None, :, None],
            self.ax[2][sl[2]][None, None, :],
        )

    def sub(self, lo, hi):
        sl = []
        for i in range(3):
            i0 = int(max(0, math.floor((lo[i] - self.lo[i]) / self.h)))
            i1 = int(min(self.n[i], math.ceil((hi[i] - self.lo[i]) / self.h) + 1))
            sl.append(slice(i0, max(i0, i1)))
        return tuple(sl)


def capped_cylinder(rho, z, r, z0, z1):
    a = rho - np.float32(r)
    b = np.abs(z - np.float32(0.5 * (z0 + z1))) - np.float32(0.5 * (z1 - z0))
    return (
        np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0)
    ).astype(np.float32)


def box_sdf(x, y, z, lo, hi):
    d = np.maximum(np.float32(lo[0]) - x, x - np.float32(hi[0]))
    d = np.maximum(d, np.maximum(np.float32(lo[1]) - y, y - np.float32(hi[1])))
    return np.maximum(d, np.maximum(np.float32(lo[2]) - z, z - np.float32(hi[2])))


def cavity_f(layout, grid):
    """f = C - delta(z): C is the distance to the drawable, flat-backed keep-out prism."""
    x, y, z = grid.coords()
    d2 = outline_d2(layout, x, y).astype(np.float32)  # (nx, ny, 1)
    b = z - np.float32(layout.z_keepout_top)  # (1, 1, nz)
    both = (d2 > 0) & (b > 0)
    c = np.where(both, np.sqrt(d2 * d2 + b * b), np.maximum(d2, b))
    del both
    c -= layout.delta(z).astype(np.float32)
    return c.astype(np.float32, copy=False)


# ================================================================== members


def pick_angles(existing, n, min_sep=35.0):
    """Rib directions spread away from the members already at a ring (greedy max-min)."""
    cand = np.arange(0.0, 360.0, 1.0)
    chosen = []
    for _ in range(n):
        ref = np.array(list(existing) + chosen)
        if ref.size == 0:
            chosen.append(90.0)
            continue
        diff = np.abs((cand[:, None] - ref[None, :] + 180.0) % 360.0 - 180.0).min(axis=1)
        i = int(np.argmax(diff))
        if diff[i] < min_sep:
            break
        chosen.append(float(cand[i]))
    return chosen


def define_members(layout):
    """Plates in vertical planes: origin (x, y), horizontal direction u, a convex polygon in
    (s, z) with s along u, thickness t at the back wall's outer face (tapering with the draft),
    and an optional standoff: the plate stays within that distance of the shell's outer face."""
    rings = layout.back_by
    z_wo = layout.z_wall_out
    pad_xy = np.array([layout.pad_face_x, 0.0])
    members = []

    def add(kind, name, a_xy, u, poly, t, standoff=None):
        members.append(
            {
                "kind": kind,
                "name": name,
                "origin": [float(a_xy[0]), float(a_xy[1])],
                "u": [float(u[0]), float(u[1])],
                "poly": [[float(p[0]), float(p[1])] for p in poly],
                "t": float(t),
                "z_ref": float(z_wo),
                "standoff": None if standoff is None else float(standoff),
            }
        )

    for a, b in (("input", "intermediate"), ("intermediate", "output")):
        A, B = rings[a], rings[b]
        v = np.array([B.cx - A.cx, B.cy - A.cy])
        ln = float(np.linalg.norm(v))
        add(
            "bridge",
            f"bridge {a}-{b}",
            (A.cx, A.cy),
            v / ln,
            [(0.0, z_wo - 3.0), (ln, z_wo - 3.0), (ln, B.ring_top - 2.0), (0.0, A.ring_top - 2.0)],
            P.BRIDGE_THICKNESS,
        )

    for sh in ("input", "intermediate", "output"):
        A = rings[sh]
        v = pad_xy - np.array([A.cx, A.cy])
        u = v / np.linalg.norm(v)
        s_end = (layout.pad_face_x - 2.0 - A.cx) / u[0]
        z_lo = layout.pad_z[1] - 3.0
        z_hi = z_wo + P.WEB_STANDOFF + 10.0
        lean = (z_hi - z_lo) * math.tan(math.radians(3.0))  # the web's end face is drafted
        add(
            "web",
            f"web {sh} ring to mount pad",
            (A.cx, A.cy),
            u,
            [(0.0, z_lo), (s_end, z_lo), (s_end - lean, z_hi), (0.0, z_hi)],
            P.WEB_THICKNESS,
            standoff=P.WEB_STANDOFF,
        )

    lines = [
        (np.array(m["origin"]), np.array(m["u"]), max(p[0] for p in m["poly"])) for m in members
    ]
    for sh, A in rings.items():
        existing = []
        for o, u, s_max in lines:
            rel = np.array([A.cx, A.cy]) - o
            s_par = float(rel @ u)
            dist = abs(-rel[0] * u[1] + rel[1] * u[0])
            r = A.r_ring_top
            if dist < r and -r <= s_par <= s_max + r:
                if s_max - s_par > r:
                    existing.append(angle_deg(u))
                if s_par > r:
                    existing.append(angle_deg(-u))
        for ang in pick_angles(existing, P.RIBS_PER_RING):
            u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            r_i = A.r_ring_top - 2.0
            if sh == "input":  # gussets carrying the motor flange's overhang to the shell
                r_fo = layout.flange_r_out - 1.0
                z_fb = layout.z_flange_bottom + 1.0
                z_top = layout.z_flange - 4.0
                poly = [(r_i, z_fb - (r_fo - r_i)), (r_fo, z_fb), (r_fo, z_top), (r_i, z_top)]
                add(
                    "rib",
                    f"rib input ring {ang:.0f} deg (flange gusset)",
                    (A.cx, A.cy),
                    u,
                    poly,
                    P.RIB_THICKNESS,
                )
            else:
                poly = [
                    (r_i, z_wo - 3.0),
                    (r_i + P.RIB_LENGTH + 2.0, z_wo - 3.0),
                    (r_i, A.ring_top - 2.0),
                ]
                add(
                    "rib",
                    f"rib {sh} ring {ang:.0f} deg",
                    (A.cx, A.cy),
                    u,
                    poly,
                    P.RIB_THICKNESS,
                    standoff=A.ring_top - z_wo,
                )
    return members


def plate_sdf(grid, f, m):
    ox, oy = m["origin"]
    ux, uy = m["u"]
    poly = np.asarray(m["poly"], dtype=np.float64)
    t0, zref, tan = m["t"], m["z_ref"], P.tan_draft()
    s_lo, s_hi = poly[:, 0].min(), poly[:, 0].max()
    z_lo, z_hi = poly[:, 1].min(), poly[:, 1].max()
    ht_max = 0.5 * t0 + max(0.0, zref - z_lo) * tan
    corners = np.array(
        [
            [ox + s * ux - w * uy, oy + s * uy + w * ux]
            for s in (s_lo, s_hi)
            for w in (-ht_max, ht_max)
        ]
    )
    pad = P.MEMBER_BLEND + 2 * grid.h
    sl = grid.sub(
        (corners[:, 0].min() - pad, corners[:, 1].min() - pad, z_lo - pad),
        (corners[:, 0].max() + pad, corners[:, 1].max() + pad, z_hi + pad),
    )
    x, y, z = grid.coords(sl)
    dx, dy = x - np.float32(ox), y - np.float32(oy)
    s = dx * np.float32(ux) + dy * np.float32(uy)
    w = -dx * np.float32(uy) + dy * np.float32(ux)
    ht = np.maximum(
        np.float32(0.5 * t0) - (z - np.float32(zref)) * np.float32(tan), np.float32(0.75)
    )
    d = np.abs(w) - ht
    n = len(poly)
    for i in range(n):
        s0, z0 = poly[i]
        s1, z1 = poly[(i + 1) % n]
        ds, dz = s1 - s0, z1 - z0
        ln = math.hypot(ds, dz)
        nx_, nz_ = dz / ln, -ds / ln  # outward normal of a CCW polygon's edge
        d = np.maximum(
            d, np.float32(nx_) * (s - np.float32(s0)) + np.float32(nz_) * (z - np.float32(z0))
        )
    if m.get("standoff") is not None:
        d = np.maximum(d, f[sl] - np.float32(P.SHELL_GAP + P.SHELL_WALL + m["standoff"]))
    return sl, d.astype(np.float32, copy=False)


def proxies(layout, grid, bosses):
    """Field copies of the core's features (0.3 mm undersize), for the blends."""
    pu, tan = P.PROXY_UNDERSIZE, P.tan_draft()
    pad = P.MEMBER_BLEND + 2 * grid.h
    out = []
    for s in layout.back:
        R = float(s.r_ring(s.z0)) + pad
        sl = grid.sub((s.cx - R, s.cy - R, s.z0 - pad), (s.cx + R, s.cy + R, s.ring_top + pad))
        x, y, z = grid.coords(sl)
        rho = np.hypot(x - np.float32(s.cx), y - np.float32(s.cy))
        d = np.maximum(
            rho - (s.r_ring(z).astype(np.float32) - np.float32(pu)),
            np.maximum(np.float32(s.z0) - z, z - np.float32(s.ring_top - pu)),
        )
        out.append((f"seat ring {s.shaft}", sl, d.astype(np.float32)))

    cx, cy = layout.flange_c
    zb, zf = layout.z_flange_bottom, layout.z_flange
    R = layout.flange_r_out + pad
    sl = grid.sub((cx - R, cy - R, zb - pad), (cx + R, cy + R, zf + pad))
    x, y, z = grid.coords(sl)
    rho = np.hypot(x - np.float32(cx), y - np.float32(cy))
    r_o = np.float32(layout.flange_r_out) - (z - np.float32(zb)) * np.float32(tan)
    r_i = np.float32(layout.flange_r_spigot - P.FLANGE_POCKET_UNDERSIZE) - (
        np.float32(zf) - z
    ) * np.float32(tan)
    d = np.maximum(
        np.maximum(rho - (r_o - np.float32(pu)), (r_i + np.float32(pu)) - rho),
        np.maximum(np.float32(zb) - z, z - np.float32(zf - pu)),
    )
    out.append(("motor flange ring", sl, d.astype(np.float32)))

    x0, x1 = layout.pad_face_x - 25.0, layout.pad_face_x - pu
    z0, z1 = layout.pad_z
    hy0 = layout.pad_half_y
    sl = grid.sub((x0 - pad, -hy0 - pad, z0 - pad), (x1 + pad, hy0 + pad, z1 + pad))
    x, y, z = grid.coords(sl)
    hy = layout.pad_half_y_at(z).astype(np.float32) - np.float32(pu)
    d = np.maximum(np.maximum(np.float32(x0) - x, x - np.float32(x1)), np.abs(y) - hy)
    d = np.maximum(d, np.maximum(np.float32(z0 + pu) - z, z - np.float32(z1 - pu)))
    out.append(("mount pad", sl, d.astype(np.float32)))

    rb = P.BOSS_DIAMETER / 2
    for bx, by in bosses:
        sl = grid.sub(
            (bx - rb - pad, by - rb - pad, -1.0 - pad),
            (bx + rb + pad, by + rb + pad, P.BOSS_HEIGHT + pad),
        )
        x, y, z = grid.coords(sl)
        rho = np.hypot(x - np.float32(bx), y - np.float32(by))
        r = np.float32(rb) - np.maximum(z, 0) * np.float32(tan) - np.float32(pu)
        d = np.maximum(
            rho - r, np.maximum(np.float32(-1.0) - z, z - np.float32(P.BOSS_HEIGHT - pu))
        )
        out.append(("bolt boss", sl, d.astype(np.float32)))
    return out


def keepouts(layout, grid, bosses=()):
    x, y, z = grid.coords()
    k = np.full(grid.n, 1e3, dtype=np.float32)
    for bx, by in bosses:  # the bolt's hole and the head's room above the boss top
        rho = np.hypot(x - np.float32(bx), y - np.float32(by))
        k = np.minimum(k, capped_cylinder(rho, z, P.BOSS_HOLE / 2 + 0.5, -2.0, P.BOSS_HEIGHT + 0.5))
        # the head's room widens upward with the draft, so the faces it cuts stay drawable
        z0 = P.BOSS_HEIGHT - P.PROXY_UNDERSIZE
        r_head = np.float32(P.BOLT_HEAD_CLEARANCE_R) + np.maximum(
            z - np.float32(z0), 0
        ) * np.float32(P.tan_draft())
        head = np.maximum(
            rho - r_head, np.maximum(np.float32(z0) - z, z - np.float32(P.BOSS_HEIGHT + 45.0))
        )
        k = np.minimum(k, head.astype(np.float32))
    for g in layout.gears:
        rho = np.hypot(x - np.float32(g.cx), y - np.float32(g.cy))
        k = np.minimum(k, capped_cylinder(rho, z, g.r_keepout, *g.z_keepout))
    for shaft, (cx, cy) in layout.axes.items():
        a, b = layout.cover_by[shaft], layout.back_by[shaft]
        r = (max(a.d, b.d) + P.SHAFT_DIAMETER_EXTRA) / 2
        rho = np.hypot(x - np.float32(cx), y - np.float32(cy))
        k = np.minimum(k, capped_cylinder(rho, z, r, 0.5 * (a.z0 + a.z1), 0.5 * (b.z0 + b.z1)))
    for s in layout.seats:
        rho = np.hypot(x - np.float32(s.cx), y - np.float32(s.cy))
        k = np.minimum(k, capped_cylinder(rho, z, s.D / 2, s.z0, s.z1))
        if s.side == "back" and s.through:
            k = np.minimum(k, capped_cylinder(rho, z, s.r_shoulder_hole, s.z1 - 0.5, s.z1 + 200.0))
    return k


# ================================================================== the field


def grid_for(layout, h):
    top = max(max(s.ring_top for s in layout.back), layout.z_flange) + 3.0
    m = 15.0 + 3 * h  # the split flange's bosses reach past the A3 box; the grid holds them
    lo = [layout.space_lo[0] - m, layout.space_lo[1] - m, -1.0 - 4 * h]
    hi = [layout.space_hi[0] + m, layout.space_hi[1] + m, top + 4 * h]
    return Grid(lo, hi, h)


def estimate_mb(layout, h):
    n = np.prod(grid_for(layout, h).n)
    return float(n * 4 * 16 / 2**20 + 300.0)  # about 16 float32 grids live at once + overhead


def build_field(layout, bosses, h):
    grid = grid_for(layout, h)
    g, t, k = P.SHELL_GAP, P.SHELL_WALL, P.MEMBER_BLEND
    f = cavity_f(layout, grid)
    _, _, z = grid.coords()

    shell = np.maximum(np.float32(g) - f, f - np.float32(g + t))
    lip = np.maximum(
        np.maximum(np.float32(g) - f, f - np.float32(g + t + P.LIP_WIDTH)),
        z - np.float32(P.LIP_HEIGHT),
    )
    S = smin(shell, lip, k).astype(np.float32)
    del shell, lip

    members = define_members(layout)
    M = np.full(grid.n, 50.0, dtype=np.float32)
    for m in members:
        sl, d = plate_sdf(grid, f, m)
        M[sl] = smin(M[sl], d, k)
    x, y, z = grid.coords()
    M = np.maximum(M, box_sdf(x, y, z, layout.space_lo, layout.space_hi))  # the design domain
    S = smin(S, M, k).astype(np.float32)
    del M

    prox = proxies(layout, grid, bosses)
    for _, sl, d in prox:
        S[sl] = smin(S[sl], d, k)

    # The smooth union bulges up to k/4 where a member's top meets a ring's top; cap the
    # field at each seat ring's top within the ring and its blend radius (but not inside the
    # motor-flange ring, which stands higher) and at each boss top within the boss.
    pu = P.PROXY_UNDERSIZE
    x, y, z = grid.coords()
    fcx, fcy = layout.flange_c
    r_in = layout.flange_r_spigot - P.FLANGE_POCKET_UNDERSIZE - 1.0
    r_out = layout.flange_r_out + 1.0
    in_flange = np.abs(
        np.hypot(x - np.float32(fcx), y - np.float32(fcy)) - np.float32(0.5 * (r_in + r_out))
    ) - np.float32(0.5 * (r_out - r_in))
    for s in layout.back:
        rho = np.hypot(x - np.float32(s.cx), y - np.float32(s.cy))
        allowed = np.minimum(
            np.minimum(z - np.float32(s.ring_top - pu), np.float32(s.r_ring_top + k) - rho),
            in_flange,
        )
        S = np.maximum(S, allowed)
    rb = P.BOSS_DIAMETER / 2 + 0.5
    for bx, by in bosses:
        sl = grid.sub(
            (bx - rb - 2, by - rb - 2, P.BOSS_HEIGHT - 3.0),
            (bx + rb + 2, by + rb + 2, P.BOSS_HEIGHT + 12.0),
        )
        xs, ys, zs = grid.coords(sl)
        rho = np.hypot(xs - np.float32(bx), ys - np.float32(by))
        S[sl] = np.maximum(
            S[sl], np.minimum(zs - np.float32(P.BOSS_HEIGHT - pu), np.float32(rb) - rho)
        )

    K = keepouts(layout, grid, bosses)
    S = np.maximum(S, np.float32(g) - f)  # nothing inside the cavity
    S = np.maximum(S, -K)  # nothing in a keep-out
    S_normals = S.astype(np.float32, copy=True)  # the cast surfaces' field, before the split cut
    S = np.maximum(S, np.float32(-1.0) - z)  # cut 1 mm below the split face; join.py faces it
    return (grid, S.astype(np.float32, copy=False), S_normals, f, K, members, [p[0] for p in prox])


def marching_cubes(grid, S):
    """Closed triangle mesh of {S < 0} (the grid is padded so the surface closes)."""
    import trimesh

    Sn = S.copy()
    Sn[np.abs(Sn) < 1e-5] = 1e-5  # no field value exactly at the level: no degenerate triangles
    Sp = np.pad(Sn, 1, mode="constant", constant_values=10.0)
    del Sn
    h = grid.h
    v, fc, _, _ = measure.marching_cubes(
        Sp, level=0.0, spacing=(h, h, h), method="lewiner", allow_degenerate=True
    )
    v = v + (grid.lo - h)
    tm = trimesh.Trimesh(v, fc, process=True)
    if tm.volume < 0:
        tm.invert()
    return tm


# ================================================================== reported checks


def voxelize_mesh(V, F, lo, pitch, shape, chunk=150000):
    """Occupancy of a closed mesh by ray parity along +z through each voxel column centre.
    Voxel (i, j, k) has its centre at lo + (i + 0.5, j + 0.5, k + 0.5) * pitch; pick lo off
    the mesh's own grid so no column passes exactly through a vertex or an edge."""
    nx, ny, nz = shape
    V = np.asarray(V, dtype=np.float64)
    F = np.asarray(F, dtype=np.int64)
    T = np.zeros((nx, ny, nz + 1), dtype=np.uint8)
    for c0 in range(0, len(F), chunk):
        tri = V[F[c0 : c0 + chunk]]
        x = (tri[:, :, 0] - lo[0]) / pitch - 0.5
        y = (tri[:, :, 1] - lo[1]) / pitch - 0.5
        i0 = np.clip(np.ceil(x.min(1)), 0, nx).astype(np.int64)
        i1 = np.clip(np.floor(x.max(1)), -1, nx - 1).astype(np.int64)
        j0 = np.clip(np.ceil(y.min(1)), 0, ny).astype(np.int64)
        j1 = np.clip(np.floor(y.max(1)), -1, ny - 1).astype(np.int64)
        ni = np.maximum(i1 - i0 + 1, 0)
        nj = np.maximum(j1 - j0 + 1, 0)
        cnt = ni * nj
        keep = np.nonzero(cnt > 0)[0]
        if keep.size == 0:
            continue
        cnt_k = cnt[keep]
        tid = np.repeat(keep, cnt_k)
        start = np.repeat(np.cumsum(cnt_k) - cnt_k, cnt_k)
        off = np.arange(tid.size) - start
        ii = i0[tid] + off // nj[tid]
        jj = j0[tid] + off % nj[tid]
        px, py = ii.astype(np.float64), jj.astype(np.float64)
        x0, x1, x2 = x[tid, 0], x[tid, 1], x[tid, 2]
        y0, y1, y2 = y[tid, 0], y[tid, 1], y[tid, 2]
        det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        ok = det != 0
        det = np.where(ok, det, 1.0)
        l0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / det
        l1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / det
        l2 = 1.0 - l0 - l1
        inside = ok & (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        zz = l0 * tri[tid, 0, 2] + l1 * tri[tid, 1, 2] + l2 * tri[tid, 2, 2]
        kk = np.ceil((zz - lo[2]) / pitch - 0.5).astype(np.int64)
        sel = inside & (kk <= nz)
        kk = np.clip(kk[sel], 0, nz)
        np.bitwise_xor.at(T, (ii[sel], jj[sel], kk), 1)
    occ = np.bitwise_xor.accumulate(T[:, :, :nz], axis=2).astype(bool)
    return occ


def local_thickness(occ, pitch):
    """Local thickness (mm): the diameter of the largest ball inside the solid that holds the
    voxel (Hildebrand and Ruegsegger), from the distance transform in radius bins."""
    D = ndimage.distance_transform_edt(occ).astype(np.float32) * np.float32(pitch)
    r_in = D - np.float32(0.5 * pitch)
    del D
    radii = np.r_[np.arange(0.75, 4.01, 0.25), np.arange(4.5, 8.01, 0.5), np.arange(9, 16, 1.0)]
    lt = np.zeros(occ.shape, dtype=np.float32)
    rmax = float(r_in.max())
    for r in radii[::-1]:
        if r > rmax:
            continue
        seeds = r_in >= np.float32(r)
        dist = ndimage.distance_transform_edt(~seeds).astype(np.float32) * np.float32(pitch)
        hit = (dist <= np.float32(r)) & occ & (lt == 0)
        lt[hit] = 2.0 * r
        del seeds, dist, hit
    rest = occ & (lt == 0)
    lt[rest] = np.maximum(2.0 * r_in[rest], pitch)
    return lt


def sample_inside(vol, lo, pitch, pts, normals, depths=(0.5, 1.0, 1.5, 2.0)):
    """Largest value of vol found just inside each surface point (along -normal). A point
    whose samples all miss the voxel solid (a face narrower than a voxel, a sharp edge) takes
    the largest value among the voxels within one voxel of it."""
    best = np.zeros(len(pts), dtype=np.float32)
    shape = np.array(vol.shape)

    def at(q, v_src):
        idx = np.floor((q - lo) / pitch).astype(np.int64)
        ok = np.all((idx >= 0) & (idx < shape), axis=1)
        v = np.zeros(len(q), dtype=np.float32)
        v[ok] = v_src[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
        return v

    for dpt in depths:
        best = np.maximum(best, at(pts - normals * (dpt * pitch), vol))
    miss = best == 0
    if miss.any():
        near = ndimage.grey_dilation(vol, size=(3, 3, 3))
        best[miss] = at(pts[miss], near)
    return best


def enclosed_voids(occ, pitch):
    """Air pockets not connected to the grid's boundary (flood fill from outside)."""
    lab, n = ndimage.label(~occ)
    if n == 0:
        return {"count": 0, "volume_mm3": 0.0}
    border = np.unique(
        np.r_[
            lab[0].ravel(),
            lab[-1].ravel(),
            lab[:, 0].ravel(),
            lab[:, -1].ravel(),
            lab[:, :, 0].ravel(),
            lab[:, :, -1].ravel(),
        ]
    )
    sizes = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    border_set = set(border.tolist())
    voids = [i for i in range(1, n + 1) if i not in border_set]
    vol = float(sum(sizes[i - 1] for i in voids) * pitch**3)
    return {
        "count": len(voids),
        "volume_mm3": round(vol, 2),
        "largest_mm3": round(float(max([sizes[i - 1] for i in voids], default=0) * pitch**3), 2),
    }


def draft_angles_deg(normals, pull=(0.0, 0.0, 1.0)):
    """Angle between each face and the pull direction, in degrees (90 = flat to the pull)."""
    n = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    return np.degrees(np.arcsin(np.clip(np.abs(n @ np.asarray(pull)), 0.0, 1.0)))


def field_gradient_at(S, lo, h, pts):
    """Unit gradient of the field (the smooth outward normal) at points, trilinear."""
    g = np.gradient(S, h)
    coords = ((np.asarray(pts) - lo) / h).T
    out = np.stack(
        [ndimage.map_coordinates(gi, coords, order=1, mode="nearest") for gi in g], axis=1
    )
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


# ================================================================== main


def main():
    t0 = time.time()
    layout = load_layout()
    outline = json.loads((P.OUT / "outline.json").read_text(encoding="utf-8"))
    free = free_memory_mb()
    h = P.VOXEL
    need = estimate_mb(layout, h)
    budget = 4000.0 if free is None else min(4000.0, 0.7 * free)
    if need > budget:
        h = P.VOXEL_FALLBACK
        need = estimate_mb(layout, h)
    print(f"field: free memory {free:.0f} MB; estimated need {need:.0f} MB at {h} mm voxels")
    if need > budget:
        raise MemoryError("even the 2.0 mm grid would exceed the memory budget")

    grid, S, S_normals, f, K, members, proxy_names = build_field(layout, outline["bosses"], h)
    t_field = time.time() - t0
    print(
        f"  grid {grid.n} = {np.prod(grid.n) / 1e6:.2f} M voxels at {h} mm; "
        f"{len(members)} members; built in {t_field:.1f} s"
    )

    tm = marching_cubes(grid, S)
    print(
        f"  marching cubes: {len(tm.faces)} triangles, watertight {tm.is_watertight}, "
        f"volume {tm.volume / 1e3:.1f} cm3"
    )
    voids = enclosed_voids(S < 0, h)
    np.savez_compressed(P.OUT / "field.npz", S=S, S_normals=S_normals, lo=grid.lo, h=grid.h)
    del S_normals
    np.savez(
        P.OUT / "field_mesh.npz",
        vertices=tm.vertices.astype(np.float64),
        faces=tm.faces.astype(np.int32),
    )
    tm.export(P.OUT / "field.stl")
    report = {
        "PROTOTYPE": "plan Part C, Task 10; not product code, not the judge",
        "voxel_mm": h,
        "grid_shape": list(grid.n),
        "grid_lo": grid.lo.tolist(),
        "free_memory_mb_before": None if free is None else round(free),
        "estimated_need_mb": round(need),
        "peak_memory_mb": peak_memory_mb(),
        "time_s": round(time.time() - t0, 1),
        "field_mesh": {
            "triangles": int(len(tm.faces)),
            "watertight": bool(tm.is_watertight),
            "volume_mm3": round(float(tm.volume), 1),
        },
        "field_enclosed_voids": voids,
        "members": members,
        "proxies": proxy_names,
        "shell": {
            "gap": P.SHELL_GAP,
            "wall": P.SHELL_WALL,
            "draft_deg": P.DRAFT_DEG,
            "lip": [P.LIP_WIDTH, P.LIP_HEIGHT],
        },
        "provenance": P.PROVENANCE,
    }
    (P.OUT / "field.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(
        f"  field.npz, field_mesh.npz, field.stl, field.json -> {P.OUT}; "
        f"voids in the field solid: {voids['count']}; peak memory "
        f"{report['peak_memory_mb']:.0f} MB; {report['time_s']} s"
    )
    return report


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "outline":
        write_outline()
    else:
        main()
