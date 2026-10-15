"""Production features drawn as one smooth solid (LOP-24/25; the engineer, 12 October 01:52-01:54: "a housing which
looks like a production [one]... nice ribs, nice patterns... the 4 mm shell should also have fillets"; judged
against the production photos: smooth filleted shells, thin tall ribs of one thickness, round bosses, lugs).

The optimiser chose where each member goes and how stiff it must be (a run on `topo.volume_map`'s volumes:
`section_forms.py`'s ribs along the flow's lines, each a strip `w` wide with a root and a tip height, the bosses'
rings, each section's thickness). The drawing keeps each member's stiffness and gives it a production form:
- **a rib** becomes the tallest thin rib of the same bending stiffness about its base (`w t³ = t_p h_p³`, `t_p`
  the production thickness, `--rib`), at most its column's own room (the band), thicker only where the room caps
  it; its sides along the pull, its top fully rounded;
- **a boss** a ring prism from the seat out to its boss radius at the optimiser's height, its edges rounded;
- **a section's thickness** a plate over its columns, where the optimiser gave it one;
- **the shell** the contract's own: each room's cup a cylinder grown by the wall past its end (`cup.pieces`), the
  plate over the other half's wider opening, the split flange's land and the bolts' bosses, the mounts; each
  rounded at its convex edges (`--round`, at most the wall, so the 4 mm wall stays 4 mm).
Everything is one signed distance field, joined by smooth unions (a fillet of about `--fillet` mm at every
junction: rib roots, rings, lugs, the lobes' meets), contoured at zero on a `--grid` mm grid. `outcome_cad.build_mesh`
then cuts it exact as any drawing (the inside, the bores, the exits, the holes, the split): LOOP_IMPLICIT=
"rib:fillet:round:grid", e.g. "6:4:3:1.25"."""

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE.parents[1] / "data" / "first_loop"
BURY = 2.0  # mm a feature runs into the wall it stands on
# mm: a member the optimiser left lower is not drawn (3 since 12 October 04:08: 1.5 mm layers' rounded edges left
# lips 0.16 mm thin, and TetGen hung on the cover of `prod14_asis`; under 3 mm it is no feature, the wall's own)
LEAST_H = float(os.environ.get("LOOP_LEAST_H", "3.0"))
BOSS_LEAST = 5.0  # mm: every bore's boss at least this high
PIECE = 6.0  # mm: a rib drawn in pieces this long, each spanning its own columns
R_TOP = 1.5  # mm: a rib's top edges rounded this much, plate-like (production's), its roots filleted by the union
K_SHELL = 6.0  # mm, the fillet where the shell's lobes meet
BURY_DEEP = 6.0  # mm the wall's thickening runs into it (the exact cuts take off what reaches the inside)
PLAN_SIGMA = 1.6  # mm: the thickening's outline, the columns' squares rounded
TOP_SIGMA = 2.0  # mm: its top and foot, the columns' steps softened
FEATURE_REACH = 34.0  # mm the field reaches past the shell's own box: the band (24) and the features' rounding
CLEAR_GAP = 2.0  # mm the features stop short of every kept-clear space (`cleared`)
MOUNT_HELD = 20_000.0  # mm³: the drawn metal about a mount's lug that holds it without a bracket of its own
FIT_FORMS = os.environ.get("LOOP_FORM_FIT", "0") == "1"  # each end wall's form drawn flat / planar / straight (`form_tops`)
# each form's exact outline (`form_shape`): off, as it spread the metal (`prod12_asis` 8.12 kg, the tilt 1.06 ×)
EXACT_FORMS = os.environ.get("LOOP_EXACT_FORMS", "0") == "1"
FORM_SIGMA = 2.0  # mm: a form's top smoothed this much (its own heights, the optimiser's; 3.5 lowered the peaks)
WEB_T = 8.0  # mm: a mount's bracket, two webs this thick from its lug to the shell (production's gusseted lug)
BRACKET = os.environ.get("LOOP_BRACKET", "web")  # "web": the two webs; "bar": one arm 0.7 of the lug's diameter wide
PANEL_RIBS = os.environ.get("LOOP_PANEL_RIBS", "0") == "1"  # production's ribs on the end walls' bare panels (`panel_ribs`)
PANEL_REACH, PANEL_STEP = 6.0, 30.0  # mm from metal a panel's; degrees apart
PANEL_T = float(os.environ.get("LOOP_PANEL_T", "6"))  # mm thick (fastcae's rib rule: 5)
BAR_W = float(os.environ.get("LOOP_BAR_W", "0.7"))  # a bar bracket's width, of the lug's diameter
PANEL_H = float(os.environ.get("LOOP_PANEL_H", "10"))  # mm high off the wall
PANEL_RING = os.environ.get("LOOP_PANEL_RING", "0") == "1"  # a ring rib across each boss's spokes at their middle
FORM_VOXELS = os.environ.get("LOOP_FORM_VOXELS", "1") == "1"  # a form's free columns in the model's whole voxels
# mm: the solid opened by this (the least thickness twice it); off: on the grid's distance transform the surface came
# out bumpy at the grid's scale, every decimation crossed itself and FE's mesh ran to 4.4 M unknowns (`prod17_asis`)
OPEN_R = float(os.environ.get("LOOP_OPEN_R", "0"))
SOCKET = (16.0, 25.0)  # mm: `outcome_cad.SOCKET`, the room over a bolt's head


def smin(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """A smooth minimum of two distance fields (polynomial): their union, filleted over about k."""
    if k <= 0:
        return np.minimum(a, b)
    hh = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - hh) + a * hh - k * hh * (1.0 - hh)


def box_sdf(d_plan: np.ndarray, d_z: np.ndarray, rr: float) -> np.ndarray:
    """A 2.5D solid's distance from its plan distance and its z distance (both of the solid shrunk by rr),
    rounded by rr."""
    return np.hypot(np.maximum(d_plan, 0.0), np.maximum(d_z, 0.0)) + np.minimum(np.maximum(d_plan, d_z), 0.0) - rr


class Field:
    """The half's distance field on a grid; each primitive evaluated on its own box only."""

    def __init__(self, lo: np.ndarray, hi: np.ndarray, g: float):
        self.lo, self.g = np.asarray(lo, float), float(g)
        self.n = np.maximum(np.ceil((np.asarray(hi) - self.lo) / g).astype(int) + 1, 2)
        self.f = np.full(tuple(self.n), 1e3, np.float32)

    def axes(self, b_lo, b_hi):
        i0 = np.clip(np.floor((np.asarray(b_lo) - self.lo) / self.g).astype(int), 0, self.n - 1)
        i1 = np.clip(np.ceil((np.asarray(b_hi) - self.lo) / self.g).astype(int) + 1, 1, self.n)
        if np.any(i1 <= i0):
            return None
        xs = [self.lo[k] + self.g * np.arange(i0[k], i1[k]) for k in range(3)]
        return (slice(i0[0], i1[0]), slice(i0[1], i1[1]), slice(i0[2], i1[2])), np.meshgrid(*xs, indexing="ij")

    def add(self, b_lo, b_hi, sdf_of, k: float) -> None:
        got = self.axes(np.asarray(b_lo) - k - 2.0, np.asarray(b_hi) + k + 2.0)
        if got is None:
            return
        sl, (X, Y, Z) = got
        self.f[sl] = smin(self.f[sl], sdf_of(X, Y, Z).astype(np.float32), k)


def cylinder(c, r: float, z0: float, z1: float, rr: float):
    def f(X, Y, Z):
        d_p = np.hypot(X - c[0], Y - c[1]) - (r - rr)
        d_z = np.maximum(z0 + rr - Z, Z - (z1 - rr))
        return box_sdf(d_p, d_z, rr)

    return f, (c[0] - r, c[1] - r, z0), (c[0] + r, c[1] + r, z1)


def ring(c, r_in: float, r_out: float, z0: float, z1: float, rr: float):
    def f(X, Y, Z):
        rho = np.hypot(X - c[0], Y - c[1])
        d_p = np.abs(rho - 0.5 * (r_in + r_out)) - (0.5 * (r_out - r_in) - rr)
        d_z = np.maximum(z0 + rr - Z, Z - (z1 - rr))
        return box_sdf(d_p, d_z, rr)

    return f, (c[0] - r_out, c[1] - r_out, z0), (c[0] + r_out, c[1] + r_out, z1)


def rib(a, b, half_t: float, z_lo0: float, z_lo1: float, z_hi0: float, z_hi1: float, rr: float):
    """A rib along the plan segment a-b, its z interval linear along it, rounded by rr (rr = half_t: a round top)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    l2 = max(float(ab @ ab), 1e-9)

    def f(X, Y, Z):
        s = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / l2, 0.0, 1.0)
        d_p = np.hypot(X - (a[0] + s * ab[0]), Y - (a[1] + s * ab[1])) - (half_t - rr)
        zlo = z_lo0 + s * (z_lo1 - z_lo0)
        zhi = z_hi0 + s * (z_hi1 - z_hi0)
        d_z = np.maximum(zlo + rr - Z, Z - (zhi - rr))
        return box_sdf(d_p, d_z, rr)

    lo = (min(a[0], b[0]) - half_t, min(a[1], b[1]) - half_t, min(z_lo0, z_lo1))
    hi = (max(a[0], b[0]) + half_t, max(a[1], b[1]) + half_t, max(z_hi0, z_hi1))
    return f, lo, hi


def web_plate(c1, r1: float, c2, r2: float, z0: float, z1: float, rr: float, hole_at=None, hole_r: float = 0.0):
    """A web: a plate over the hull of two discs (two bosses), z0 to z1, a round hole through it, rounded by rr."""
    import parts as pm

    c1, c2 = np.asarray(c1, float), np.asarray(c2, float)

    def f(X, Y, Z):
        plan = np.column_stack([X.ravel(), Y.ravel()])
        d_p = pm.uneven_capsule(plan, c1, c2, max(r1 - rr, 0.5), max(r2 - rr, 0.5)).reshape(X.shape)
        if hole_r > 0.0:
            d_p = np.maximum(d_p, (hole_r + rr) - np.hypot(X - hole_at[0], Y - hole_at[1]))
        d_z = np.maximum(z0 + rr - Z, Z - (z1 - rr))
        return box_sdf(d_p, d_z, rr)

    lo = (min(c1[0] - r1, c2[0] - r2), min(c1[1] - r1, c2[1] - r2), z0)
    hi = (max(c1[0] + r1, c2[0] + r2), max(c1[1] + r1, c2[1] + r2), z1)
    return f, lo, hi


def arc_rib(c, r: float, width: float, a0: float, a1: float, z0: float, z1: float, rr: float):
    """A rib along a circle's arc from a0 to a1 (radians, counter-clockwise), `width` wide, z0 to z1, its ends round."""
    c = np.asarray(c, float)
    span = float(np.mod(a1 - a0, 2.0 * np.pi))
    e0 = c + r * np.array([np.cos(a0), np.sin(a0)])
    e1 = c + r * np.array([np.cos(a1), np.sin(a1)])

    def f(X, Y, Z):
        rho = np.hypot(X - c[0], Y - c[1])
        within = np.mod(np.arctan2(Y - c[1], X - c[0]) - a0, 2.0 * np.pi) <= span
        d_end = np.minimum(np.hypot(X - e0[0], Y - e0[1]), np.hypot(X - e1[0], Y - e1[1]))
        d_p = np.where(within, np.abs(rho - r), d_end) - (0.5 * width - rr)
        d_z = np.maximum(z0 + rr - Z, Z - (z1 - rr))
        return box_sdf(d_p, d_z, rr)

    reach = r + 0.5 * width
    return f, (c[0] - reach, c[1] - reach, z0), (c[0] + reach, c[1] + reach, z1)


def variable_rib(pts_xy: np.ndarray, half_ts: np.ndarray, z_lo: np.ndarray, z_hi: np.ndarray, rr: float):
    """One rib along a plan polyline whose half-width changes from knot to knot (each piece its two knots' mean) and
    whose z interval is linear between the knots: the pieces joined by a plain minimum, one plate (`polyline_rib`'s
    reason), its top rounded by rr (at most each piece's half-width)."""
    pts_xy = np.asarray(pts_xy, float)
    parts = []
    for k in range(len(pts_xy) - 1):
        ht = 0.5 * (float(half_ts[k]) + float(half_ts[k + 1]))
        parts.append(rib(pts_xy[k], pts_xy[k + 1], ht, z_lo[k], z_lo[k + 1], z_hi[k], z_hi[k + 1], min(rr, ht))[0])

    def f(X, Y, Z):
        out = parts[0](X, Y, Z)
        for g_ in parts[1:]:
            out = np.minimum(out, g_(X, Y, Z))
        return out

    t_most = float(np.max(half_ts))
    lo = (pts_xy[:, 0].min() - t_most, pts_xy[:, 1].min() - t_most, float(np.min(z_lo)))
    hi = (pts_xy[:, 0].max() + t_most, pts_xy[:, 1].max() + t_most, float(np.max(z_hi)))
    return f, lo, hi


def polyline_rib(pts_xy: np.ndarray, half_t: float, z_lo: np.ndarray, z_hi: np.ndarray, rr: float):
    """One rib along a plan polyline, its z interval linear between the knots: the pieces joined by a plain
    minimum, so that the rib is one plate with one top line (12 October 03:05: each 6 mm piece smooth-unioned on
    its own left a bump at every joint, the ribs beaded like sausages)."""
    pts_xy = np.asarray(pts_xy, float)
    parts = [rib(pts_xy[k], pts_xy[k + 1], half_t, z_lo[k], z_lo[k + 1], z_hi[k], z_hi[k + 1], rr)[0] for k in range(len(pts_xy) - 1)]

    def f(X, Y, Z):
        out = parts[0](X, Y, Z)
        for g_ in parts[1:]:
            out = np.minimum(out, g_(X, Y, Z))
        return out

    lo = (pts_xy[:, 0].min() - half_t, pts_xy[:, 1].min() - half_t, float(np.min(z_lo)))
    hi = (pts_xy[:, 0].max() + half_t, pts_xy[:, 1].max() + half_t, float(np.max(z_hi)))
    return f, lo, hi


def land(outer: list, inner: list, z0: float, z1: float, rr: float):
    """The split flange's land: the outer circles' union less the inner circles', a flange thick."""

    def f(X, Y, Z):
        d_o = np.min([np.hypot(X - c["centre"][0], Y - c["centre"][1]) - c["radius"] for c in outer], axis=0)
        d_i = np.min([np.hypot(X - c["centre"][0], Y - c["centre"][1]) - c["radius"] for c in inner], axis=0)
        d_p = np.maximum(d_o, -d_i) + rr
        d_z = np.maximum(z0 + rr - Z, Z - (z1 - rr))
        return box_sdf(d_p, d_z, rr)

    xs = [c["centre"][0] + s * c["radius"] for c in outer for s in (-1, 1)]
    ys = [c["centre"][1] + s * c["radius"] for c in outer for s in (-1, 1)]
    return f, (min(xs), min(ys), z0), (max(xs), max(ys), z1)


def members(run: str) -> dict:
    """The run's volumes with their heights (mm) and their columns' bases and rooms, read from its record."""
    import regions as rg
    import topo

    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    hv = rec["height_volumes"]
    meta = json.loads((OUT / f"{Path(hv).stem.removesuffix('_cols')}.json").read_text(encoding="utf-8"))
    sec = json.loads((OUT / f"{meta['sections']}.json").read_text(encoding="utf-8")) if meta.get("sections") else {"sections": []}
    cols = np.load(OUT / hv)
    vol_of_col, law = np.asarray(cols["vol_of_col"], np.int64), np.asarray(cols["law"], np.int64)
    ctx = rg.context(run)
    model, kind, lo, h = ctx["model"], ctx["kind"], ctx["lo"], ctx["h"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    big_l = float(pos.max() + 1.0)
    x = np.asarray(np.load(OUT / f"{run}.npz")["x"], float)
    n_free = int((vol_of_col == -1).sum())  # -2: held empty
    count = np.where(law == 1, 2, 1)
    first = n_free + np.r_[0, np.cumsum(count)[:-1]]
    # each column's base (the face its first free voxel stands on) and room (its free voxels), mm
    kk = np.unravel_index(elem[free_e], model["n"])[2]
    lower = (layer[col] // 10_000) == 0
    base_vox = np.where(pos == 0)[0]
    base = np.full(len(pts), np.nan)
    base[col[base_vox]] = np.where(lower[base_vox], lo[2] + h * (kk[base_vox] + 1), lo[2] + h * kk[base_vox])
    room = np.bincount(col, minlength=len(pts)) * h
    # every column's height as the optimiser had it (mm): the free columns' own variables mixed by the plan filter
    # among free columns (`topo.volume_map`), each volume's columns from its parameters
    t_all = np.zeros(len(pts))
    if n_free:
        from scipy.spatial import cKDTree
        import scipy.sparse as sp

        radius = float(rec["height_field"]["radius_mm"]) / h
        free = np.flatnonzero(vol_of_col == -1)
        plan = np.column_stack([pts[free, 0] + 1_000_000.0 * layer[free], pts[free, 1]])
        tree = cKDTree(plan)
        pp = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
        ff = (sp.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(n_free, n_free)).tocsr() + sp.eye(n_free) * radius).tocsr()
        ffn = sp.diags(1.0 / np.asarray(ff.sum(axis=1)).ravel()) @ ff
        t_all[free] = (ffn @ x[:n_free]) * big_l * h
    out = []
    for v, item in enumerate(meta["volumes"]):
        mine = np.flatnonzero(vol_of_col == v)
        if not len(mine):
            continue
        hts = [float(x[first[v] + j]) * big_l * h for j in range(count[v])]
        sv = np.asarray(cols["s_of_col"], float)[mine]
        t_all[mine] = hts[0] if law[v] == 0 else (1.0 - sv) * hts[0] + sv * hts[1]
        out.append({**item, "heights_mm": hts, "base_mm": float(np.nanmedian(base[mine])), "room_mm": float(np.median(room[mine])),
                    "cols_s": sv, "cols_base": base[mine], "cols_room": room[mine],
                    "half": item.get("half") or ("cover" if (layer[mine[0]] // 10_000) == 1 else "motor_side"),
                    "cells": pts[mine].astype(int), "section_info": next((s for s in sec["sections"] if s["id"] == item.get("section")), None)})  # fmt: skip
    kind_of_vol = np.array([it["kind"] for it in meta["volumes"]] + ["free", "empty"])
    col_kind = kind_of_vol[np.where(vol_of_col >= 0, vol_of_col, np.where(vol_of_col == -1, len(meta["volumes"]), len(meta["volumes"]) + 1))]
    # the forms' own columns, free (`section_forms.py --free-forms`): each column the form it belongs to
    lay_of = np.asarray(cols["layout_of_col"], np.int64) if "layout_of_col" in cols.files else vol_of_col
    col_form = kind_of_vol[np.where(lay_of >= 0, lay_of, np.where(vol_of_col == -1, len(meta["volumes"]), len(meta["volumes"]) + 1))]
    return {"volumes": out, "lo": lo, "h": h, "meta": meta["volumes"],
            "cols": {"cells": pts[:, :2].astype(int), "layer": layer, "base": base, "room": room, "t": t_all, "kind": col_kind, "form": col_form,
                     "layout": lay_of, "s": np.asarray(cols["s_of_col"], float)}}  # fmt: skip


def quantised(t: np.ndarray, h: float) -> np.ndarray:
    """The metal a column holds in the optimiser's own model: whole voxels, each metal where the height passes its
    middle (the projection at β 32 is a step), so 3 mm is a 4 mm voxel and 1.9 mm nothing."""
    return h * np.rint(np.maximum(np.asarray(t, float), 0.0) / h)


def smax(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """A smooth maximum (an intersection, filleted over about k)."""
    return -smin(-a, -b, k)


def clear_spaces(layout: dict, z_split: float, lower: bool) -> list[tuple]:
    """The kept-clear spaces the exact cuts take out of a half beside its features, as cylinders (centre, radius,
    z0, z1): the shafts' exits, the vehicle's brackets beyond each mount's faces, each bolt's hole and the room over
    its head (`outcome_cad.SOCKET`)."""
    s, t_f = layout["settings"], float(layout["flange"]["thickness"])
    out = [(e["centre"], float(e["radius"]), *map(float, e["z"])) for e in layout.get("exits") or [] if (float(e["z"][1]) <= z_split) == lower]
    out += [(b["centre"], float(b["radius"]), *map(float, b["z"])) for b in layout.get("brackets") or []]
    d_s, h_s = SOCKET
    for c in layout["bolts"]:
        out.append((c, 0.5 * float(s["bolt_hole"]), z_split - t_f - 1.0, z_split + t_f + 1.0))
        out.append((c, 0.5 * d_s, *((z_split - t_f - h_s, z_split - t_f) if lower else (z_split + t_f, z_split + t_f + h_s))))
    return out


def cleared(prim: tuple, spaces: list[tuple]) -> tuple:
    """A feature that stops CLEAR_GAP short of every kept-clear space near it, its edge there rounded: an exact cut
    through a smooth surface leaves it where the two meet at a grazing angle, and the slivers stop FE's mesher
    (`prod7_asis`, 12 October 03:10: 1,243 triangles under 0.05 mm by the mounts' brackets and the bolts' rooms)."""
    f, lo, hi = prim
    near = [c for c in spaces if c[0][0] + c[1] > lo[0] - 4 and c[0][0] - c[1] < hi[0] + 4 and c[0][1] + c[1] > lo[1] - 4
            and c[0][1] - c[1] < hi[1] + 4 and c[3] > lo[2] - 4 and c[2] < hi[2] + 4]  # fmt: skip
    if not near:
        return prim

    def g(X, Y, Z):
        d = f(X, Y, Z)
        for c, r, z0, z1 in near:
            d_c = box_sdf(np.hypot(X - c[0], Y - c[1]) - r, np.maximum(z0 - Z, Z - z1), 0.0)
            d = smax(d, CLEAR_GAP - d_c, 1.0)
        return d

    return g, lo, hi


def panel_ribs(fld: "Field", faces: np.ndarray, lower: bool, metal_xy: np.ndarray, outline, seats: list, rings_r: float,
               reach_mm: float, spacing_deg: float, t: float, height: float) -> list[tuple]:  # fmt: skip
    """Production's ribs on the end walls' bare panels (12 October 06:00; the noise-and-vibration rule that no flat panel
    goes unribbed: the cover's broad bare end wall carried the mode of about 1,150 Hz by the stage-2 order): every point
    of a half's end walls farther than `reach_mm` from any drawn metal is a panel's; from the nearest bore, radial ribs
    every `spacing_deg` that cross a panel run from the boss's rim (the bore plus `rings_r`) to the wall's edge, `t`
    thick, `height` off the wall's exact face, as polyline plates on it. Returns primitives (sdf, lo, hi)."""
    from scipy.ndimage import distance_transform_edt
    from scipy.spatial import cKDTree

    out_dir = -1.0 if lower else 1.0
    xs = fld.lo[0] + fld.g * np.arange(fld.n[0])
    ys = fld.lo[1] + fld.g * np.arange(fld.n[1])
    px, py = np.meshgrid(xs, ys, indexing="ij")
    within = (outline(px, py) < -2.0) & np.isfinite(faces)
    near_metal = np.zeros_like(within)
    if len(metal_xy):
        d, _ = cKDTree(metal_xy).query(np.column_stack([px[within], py[within]]), distance_upper_bound=reach_mm)
        near_metal[within] = np.isfinite(d)
    for b in seats:  # the bores themselves and their bosses are no panel
        near_metal |= np.hypot(px - b["axis"][0], py - b["axis"][1]) < 0.5 * float(b["D"]) + rings_r
    bare = within & ~near_metal
    if bare.sum() < 4:
        return []
    del distance_transform_edt
    out = []
    spokes = {}  # each boss's spokes drawn: their lengths (mm)
    for b in seats:
        c = np.asarray(b["axis"], float)
        r0 = 0.5 * float(b["D"]) + rings_r
        for ang in np.arange(0.0, 360.0, spacing_deg):
            u = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
            ss = np.arange(r0, r0 + 400.0, fld.g)
            pts = c[None, :] + ss[:, None] * u[None, :]
            ii = np.rint((pts[:, 0] - fld.lo[0]) / fld.g).astype(int)
            jj = np.rint((pts[:, 1] - fld.lo[1]) / fld.g).astype(int)
            ok = (ii >= 0) & (ii < fld.n[0]) & (jj >= 0) & (jj < fld.n[1])
            ii, jj = np.where(ok, ii, 0), np.where(ok, jj, 0)
            inside = ok & (outline(pts[:, 0], pts[:, 1]) < -2.0) & np.isfinite(faces[ii, jj])
            if not inside[0]:
                continue
            # the ray from the boss's rim to where it first leaves the wall, kept where most of it crosses bare wall (a
            # panel), at least 20 mm of it, and it ends short of any other bore's boss
            last = int(np.argmin(inside)) if not inside.all() else len(inside)
            seg = slice(0, max(last, 2))
            if last * fld.g < 20.0 or bare[ii[seg], jj[seg]].mean() < 0.6:
                continue
            if any(np.hypot(*(pts[seg][-1] - np.asarray(o["axis"]))) < 0.5 * float(o["D"]) + rings_r for o in seats if o is not b):
                continue
            knots = np.linspace(0, max(last, 2) - 1, max(2, int(np.ceil((max(last, 2) - 1) * fld.g / PIECE)) + 1)).astype(int)
            zf = faces[ii[knots], jj[knots]]
            if not np.all(np.isfinite(zf)):
                continue
            z_lo, z_hi = np.minimum(zf - out_dir * BURY, zf + out_dir * height), np.maximum(zf - out_dir * BURY, zf + out_dir * height)
            out.append(polyline_rib(pts[knots], 0.5 * t, z_lo, z_hi, min(R_TOP, 0.5 * t)))
            spokes.setdefault(id(b), (b, []))[1].append(max(last, 2) * fld.g)
    if PANEL_RING:  # a ring rib across each boss's spokes at their middle, halving the panels between them (production's
        # spoked end faces; the cover's mode by s1's order lived between two spokes, `prod20_asis`, 12 October 06:15)
        for b, lengths in spokes.values():
            if len(lengths) < 3:
                continue
            c = np.asarray(b["axis"], float)
            r = 0.5 * float(b["D"]) + rings_r + 0.5 * float(np.median(lengths))
            th = np.linspace(0.0, 2 * np.pi, max(24, int(2 * np.pi * r / PIECE)) + 1)
            pts = c[None, :] + r * np.column_stack([np.cos(th), np.sin(th)])
            ii = np.clip(np.rint((pts[:, 0] - fld.lo[0]) / fld.g).astype(int), 0, fld.n[0] - 1)
            jj = np.clip(np.rint((pts[:, 1] - fld.lo[1]) / fld.g).astype(int), 0, fld.n[1] - 1)
            ok = (outline(pts[:, 0], pts[:, 1]) < -2.0) & np.isfinite(faces[ii, jj])
            ok &= ~np.array([any(np.hypot(*(p - np.asarray(o["axis"]))) < 0.5 * float(o["D"]) + rings_r for o in seats if o is not b) for p in pts])
            # each run of points on the wall one arc
            k = 0
            while k < len(pts):
                if not ok[k]:
                    k += 1
                    continue
                e = k
                while e + 1 < len(pts) and ok[e + 1]:
                    e += 1
                if e - k >= 2:
                    zf = faces[ii[k : e + 1], jj[k : e + 1]]
                    z_lo = np.minimum(zf - out_dir * BURY, zf + out_dir * height)
                    z_hi = np.maximum(zf - out_dir * BURY, zf + out_dir * height)
                    out.append(polyline_rib(pts[k : e + 1], 0.5 * t, z_lo, z_hi, min(R_TOP, 0.5 * t)))
                k = e + 1
    return out


def form_shape(kind: str, xy: np.ndarray, h: float, item: dict, seats: list):
    """A form's exact outline in plan, as a signed distance (mm, < 0 within), or None for the columns' own: a boss a
    circle round its bore, a rib or a gusset a straight strip as wide as its columns' own area over its length
    (12 October 03:42: the columns' 4 mm squares left the bosses polygons and the ribs jagged)."""
    if kind == "ring":
        c = xy.mean(axis=0)
        ax = min(seats, key=lambda b: np.hypot(*(np.asarray(b["axis"]) - c)))["axis"]
        r = float(np.hypot(*(xy - np.asarray(ax)).T).max()) + 0.5 * h
        return lambda px, py: np.hypot(px - ax[0], py - ax[1]) - r
    if kind in ("rib", "gusset") and "a_mm" in item:
        a, b = np.asarray(item["a_mm"], float), np.asarray(item["b_mm"], float)
        d = b - a
        length = max(float(np.hypot(*d)), h)
        w = max(h, len(xy) * h * h / length)
        # the strip's ends where its columns end: each column's place along the line, its first and last
        sv = ((xy - a) @ d) / float(d @ d)
        a, b = a + float(sv.min()) * d, a + float(sv.max()) * d
        d = b - a

        def f(px, py):
            s_ = np.clip(((px - a[0]) * d[0] + (py - a[1]) * d[1]) / max(float(d @ d), 1e-9), 0.0, 1.0)
            return np.hypot(px - (a[0] + s_ * d[0]), py - (a[1] + s_ * d[1])) - 0.5 * w

        return f
    return None


def thickening(cells: np.ndarray, base: np.ndarray, t: np.ndarray, lo, h: float, out_dir: float, g: float, rr: float,
               outline=None, beside: bool = False, shape=None, top_sigma: float | None = None):  # fmt: skip
    """The wall thickened where the optimiser put metal on it, drawn as one smooth solid (12 October 02:40: the free
    columns' metal, the bosses' rings and the sections' thicknesses, which the post-by-post drawing had left out
    or grooved): each column's metal from BURY_DEEP inside its wall to its height off its base; its outline in plan
    the columns' squares rounded (a Gaussian of PLAN_SIGMA, cut at a half), its top and its foot the columns'
    blurred by TOP_SIGMA, each column's value carried out past the outline so that the edge does not sag; rounded
    by rr. Returns a primitive (sdf, box lo, box hi) or None."""
    from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

    keep = t >= LEAST_H
    if keep.sum() < 2:
        return None
    i0, j0 = cells[keep].min(axis=0) - 3
    i1, j1 = cells[keep].max(axis=0) + 4
    nc = (int(i1 - i0), int(j1 - j0))
    on = np.zeros(nc, bool)
    top = np.zeros(nc)
    foot = np.zeros(nc)
    ci, cj = cells[keep, 0] - i0, cells[keep, 1] - j0
    on[ci, cj] = True
    top[ci, cj] = base[keep] + out_dir * t[keep]
    foot[ci, cj] = base[keep] - out_dir * BURY_DEEP
    _, (ni, nj) = distance_transform_edt(~on, return_indices=True)  # each cell's nearest metal column
    top, foot = top[ni, nj], foot[ni, nj]
    # the fine plan grid (g) over the columns' squares
    x0, y0 = lo[0] + h * i0, lo[1] + h * j0
    nx, ny = int(np.ceil(nc[0] * h / g)), int(np.ceil(nc[1] * h / g))
    fx = (np.arange(nx) + 0.5) * g / h - 0.5  # each fine node in column units (column centres at integers)
    fy = (np.arange(ny) + 0.5) * g / h - 0.5
    gi = np.clip(np.rint(fx).astype(int), 0, nc[0] - 1)
    gj = np.clip(np.rint(fy).astype(int), 0, nc[1] - 1)
    inside = gaussian_filter(on[np.ix_(gi, gj)].astype(float), PLAN_SIGMA / g) >= 0.5
    d_plan = (distance_transform_edt(~inside) - distance_transform_edt(inside)) * g  # < 0 inside, mm
    px, py = np.meshgrid(x0 + (np.arange(nx) + 0.5) * g, y0 + (np.arange(ny) + 0.5) * g, indexing="ij")
    if shape is not None:  # the form's exact outline, no further than half a column past its columns
        d_plan = np.maximum(shape(px, py), d_plan - 0.5 * h)
    if outline is not None:  # the columns' squares against the exact outline (the side walls' outer faces)
        d_out = outline(px, py)
        if beside:  # beside a side wall: carried 3 mm into it near the piece, so no crevice opens between them
            d_plan = np.minimum(d_plan, np.maximum.reduce([d_plan - 6.0, d_out, -d_out - 3.0]))
        else:  # on an end wall: no lip past the side wall's face
            d_plan = np.maximum(d_plan, d_out)
    sig = (top_sigma or TOP_SIGMA) / g
    top_f = gaussian_filter(top[np.ix_(gi, gj)], sig)
    foot_f = gaussian_filter(foot[np.ix_(gi, gj)], sig)
    z_lo, z_hi = np.minimum(top_f, foot_f), np.maximum(top_f, foot_f)

    def f(X, Y, Z):
        u = (X[:, :, 0] - x0) / g - 0.5  # the fine grid's own indices
        v = (Y[:, :, 0] - y0) / g - 0.5
        dp = map_coordinates(d_plan, [u, v], order=1, mode="nearest")[:, :, None]
        zl = map_coordinates(z_lo, [u, v], order=1, mode="nearest")[:, :, None]
        zh = map_coordinates(z_hi, [u, v], order=1, mode="nearest")[:, :, None]
        return box_sdf(dp + rr, np.maximum(zl + rr - Z, Z - (zh - rr)), rr)

    return f, (x0, y0, float(z_lo.min())), (x0 + nx * g, y0 + ny * g, float(z_hi.max()))


def exact_faces(fld: "Field", lower: bool) -> np.ndarray:
    """The shell's outer face along the pull at each plan node of the field (z, mm; NaN where the column holds no
    shell): its outermost metal node, refined to the zero crossing beyond it."""
    metal = fld.f < 0
    nz = fld.n[2]
    anyk = metal.any(axis=2)
    if lower:
        k = np.argmax(metal, axis=2)  # the lowest metal node
        k_out = np.maximum(k - 1, 0)
    else:
        k = nz - 1 - np.argmax(metal[:, :, ::-1], axis=2)  # the highest
        k_out = np.minimum(k + 1, nz - 1)
    ii, jj = np.meshgrid(np.arange(fld.n[0]), np.arange(fld.n[1]), indexing="ij")
    f_in, f_out = fld.f[ii, jj, k].astype(float), fld.f[ii, jj, k_out].astype(float)
    frac = np.clip(-f_in / np.maximum(f_out - f_in, 1e-9), 0.0, 1.0)
    z = fld.lo[2] + fld.g * (k + np.where(lower, -frac, frac))
    return np.where(anyk & (k_out != k), z, np.nan)


def form_tops(kind: str, xy: np.ndarray, s: np.ndarray, base: np.ndarray, t: np.ndarray, out_dir: float) -> np.ndarray:
    """A form's columns' heights as production draws it, its metal kept (12 October 03:32: each column its own height
    left the bosses' and the bridges' tops torn): a boss's face flat, a bridge's top a plane, a rib's or a gusset's top
    a straight line along it; the surface fitted to the optimiser's tops by least squares, then moved along the pull
    until it holds the form's own metal. Returns each column's height off its base (mm)."""
    tops = base + out_dir * t
    if kind in ("rib", "gusset", "belt"):
        a = np.column_stack([np.ones_like(s), s])
    elif kind == "bridge":
        a = np.column_stack([np.ones(len(xy)), xy - xy.mean(axis=0)])
    else:
        a = np.ones((len(xy), 1))
    surf = a @ np.linalg.lstsq(a, tops, rcond=None)[0]
    want = float(t.sum())
    if want <= 0:
        return np.zeros_like(t)

    def held(d):
        return float(np.maximum(0.0, out_dir * (surf + d - base)).sum())

    lo_, hi_ = -100.0, 100.0  # the shift along the pull (mm, outward positive) that gives back the form's metal
    for _ in range(60):
        mid = 0.5 * (lo_ + hi_)
        lo_, hi_ = (mid, hi_) if held(out_dir * mid) < want else (lo_, mid)
    return np.maximum(0.0, out_dir * (surf + out_dir * 0.5 * (lo_ + hi_) - base))


def wall_pieces(cells: np.ndarray, base: np.ndarray, h: float) -> list[np.ndarray]:
    """The columns split into pieces of continuous wall: neighbours in plan whose bases differ by at most a voxel
    belong together (a bearing's pocket standing past its end wall, a lobe's end over another's, the end walls
    over the split are each a piece of their own, so that no blur mixes a top with a foot far below it)."""
    key = {(int(i), int(j)): k for k, (i, j) in enumerate(cells)}
    parent = np.arange(len(cells))

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for k, (i, j) in enumerate(cells):
        for di, dj in ((1, 0), (0, 1)):
            m = key.get((int(i) + di, int(j) + dj))
            if m is not None and abs(base[k] - base[m]) <= 1.1 * h:
                ra, rb = root(k), root(m)
                if ra != rb:
                    parent[ra] = rb
    roots = np.array([root(k) for k in range(len(cells))])
    return [np.flatnonzero(roots == r) for r in np.unique(roots)]


def production_rib(w: float, h: float, room: float, t_p: float) -> tuple[float, float]:
    """The thin rib of the same bending stiffness about its base as a strip w wide and h high (w h³ = t h_p³):
    t_p thick and h_p high, at most `room`; thicker, in 2 mm steps, where the room caps it."""
    h_p = min(room, h * (w / t_p) ** (1.0 / 3.0))
    t = max(t_p, w * (h / max(h_p, 1e-9)) ** 3)
    return 2.0 * np.ceil(t / 2.0), h_p


def half_body(run: str, half: str, layout: dict, all_rooms: list, z_split: float, wall: float, rib_t: float = 6.0,
              k_feat: float = 4.0, rround: float = 3.0, grid: float = 1.25):  # fmt: skip
    """The half's solid (a manifold3d Manifold), before the exact cuts: the shell, its features, one smooth body."""
    import cup as cupmod

    lower = half == "motor_side"
    out_dir = -1.0 if lower else 1.0
    s = layout["settings"]
    fld, faces, prims = shell_field(layout, all_rooms, z_split, wall, half, rround, grid)
    n_shell = len(prims)
    mem = members(run)

    def on_wall(cells: np.ndarray, vox_base: np.ndarray) -> np.ndarray:
        """Each column's base on the exact shell (its outer face at the column's centre), the voxel model's where
        the exact face is missing or more than 1.5 voxels off it (a column at a wall's edge)."""
        cx = mem["lo"][0] + mem["h"] * (cells[:, 0] + 0.5)
        cy = mem["lo"][1] + mem["h"] * (cells[:, 1] + 0.5)
        ix = np.clip(np.rint((cx - fld.lo[0]) / fld.g).astype(int), 0, fld.n[0] - 1)
        iy = np.clip(np.rint((cy - fld.lo[1]) / fld.g).astype(int), 0, fld.n[1] - 1)
        ex = faces[ix, iy]
        ok = np.isfinite(ex) & (np.abs(ex - vox_base) <= 1.5 * mem["h"])
        return np.where(ok, ex, vox_base)

    drawn = {"ribs": 0, "rings": 0, "plates": 0, "brackets": 0}
    ends = []  # the drawn ribs' ends, to see which mounts they reach
    rings_drawn = set()
    for v in mem["volumes"]:
        if v["half"] != half:
            continue
        room = v["room_mm"]
        if v["kind"] in ("rib", "gusset"):  # a gusset: a rib beside a side wall, from the wall out
            v = {**v, "cols_base": on_wall(v["cells"], v["cols_base"])}
            h0, h1 = (min(room, hv) for hv in v["heights_mm"])
            if max(h0, h1) < LEAST_H:
                continue
            w = float(v["width"])
            if v.get("over") == "the side walls" or rib_t <= 0:  # beside a side wall, or no conversion asked: drawn as it is, rounded
                t, hp0, hp1 = w, h0, h1
            else:
                t0, hp0 = production_rib(w, max(h0, 0.0), room, rib_t)
                t1, hp1 = production_rib(w, max(h1, 0.0), room, rib_t)
                t = max(t0, t1)
            ends += [np.asarray(v["a_mm"]), np.asarray(v["b_mm"])]
            # one plate along the rib, its top and its foot given at knots about PIECE mm apart: each knot's the envelope
            # of the columns about it, each column's metal from its own base to its own top (where a rib crosses a
            # bearing's pocket its columns step down the pocket's flank to the end wall, and one base left the flank
            # empty: the cover's seats 3-4 times softer, 12 October 02:23); the top line then smoothed over three knots,
            # the foot kept the deepest of its three (it runs into the wall, the exact cuts take what reaches inside)
            a_mm, b_mm = np.asarray(v["a_mm"], float), np.asarray(v["b_mm"], float)
            length = float(np.hypot(*(b_mm - a_mm)))
            nb = max(1, int(round(length / PIECE)))
            cs, cb, cr = v["cols_s"], v["cols_base"], v["cols_room"]
            knots = np.linspace(0.0, 1.0, nb + 1)
            top_k, foot_k = np.full(nb + 1, np.nan), np.full(nb + 1, np.nan)
            for kk, sk in enumerate(knots):
                near = (np.abs(cs - sk) <= 0.75 / nb) & np.isfinite(cb)
                if not near.any():
                    continue
                hl = np.minimum(cr[near], hp0 + np.clip(cs[near], 0.0, 1.0) * (hp1 - hp0))
                tops, roots = cb[near] + out_dir * hl, cb[near] - out_dir * BURY
                top_k[kk] = tops.max() if out_dir > 0 else tops.min()
                foot_k[kk] = roots.min() if out_dir > 0 else roots.max()
            ok = np.isfinite(top_k)
            if ok.sum() == 0:
                continue
            top_k = np.interp(knots, knots[ok], top_k[ok])
            foot_k = np.interp(knots, knots[ok], foot_k[ok])
            if nb >= 2:
                top_k = np.r_[top_k[0], (top_k[:-2] + top_k[1:-1] + top_k[2:]) / 3.0, top_k[-1]]
                pad = np.r_[foot_k[0], foot_k, foot_k[-1]]
                three = np.stack([pad[:-2], pad[1:-1], pad[2:]])
                foot_k = three.min(axis=0) if out_dir > 0 else three.max(axis=0)
            z_lo, z_hi = np.minimum(top_k, foot_k), np.maximum(top_k, foot_k)
            line = a_mm[None, :] + knots[:, None] * (b_mm - a_mm)[None, :]
            prims.append((*polyline_rib(line, 0.5 * t, z_lo, z_hi, min(R_TOP, 0.5 * t)), k_feat))
            drawn["ribs"] += 1
        elif v["kind"] == "ring" and v.get("section_info"):
            rings_drawn.add(tuple(np.round(v["section_info"]["axis"], 1)))
            drawn["rings"] += 1
    # the wall's thickening: every column's metal that is not a rib's (the free columns', the bosses' rings, the
    # sections' thicknesses), each piece of continuous wall drawn as one smooth solid (`thickening`). Each column
    # holds what the optimiser's model holds (`quantised`); every bore's boss at least BOSS_LEAST high, the seat's
    # machined face needs one whatever the optimiser spent there. A column by column drawing of rounded posts
    # grooved the plates and, the free columns left out, missed most of the cover's seats' stiffness (12 October 02:27).
    cl = mem["cols"]
    first_run = cl["layer"] == (1 if lower else 10_001)
    t_c = np.minimum(np.maximum(cl["t"], 0.0), cl["room"])
    # the free columns as the model's whole voxels (a 3 mm height is a 4 mm voxel); a volume of one height at least
    # that and its own (a flat face either way); a volume whose height runs along it as it runs (smooth, not terraced)
    # (a free column in a form, `--free-forms`: its height as it runs, smooth along the form, not terraced)
    loose = (cl["kind"] == "free") & (cl["form"] == "free")
    # a free column in a form in whole voxels too, as the model holds it (12 October 06:00: drawn as its continuous
    # height, a 2.5 mm column the model holds as a 4 mm voxel came out 2.5 mm, and the light designs lost their tilt)
    loose = loose | ((cl["kind"] == "free") & FORM_VOXELS)
    t_q = np.where(loose, quantised(t_c, mem["h"]), np.where(cl["kind"] == "free", t_c,
                   np.where(np.isin(cl["kind"], ("ring", "rest", "lug", "web")), np.maximum(t_c, quantised(t_c, mem["h"])), t_c)))  # fmt: skip
    t_q = np.minimum(t_q, cl["room"])
    # a column the optimiser gave between half the least height and it is drawn at the least height, not left out: no
    # lip thinner than LEAST_H, and never less metal than the model (left out, the light designs' thin layers lost their
    # stiffness: `prod20_asis` tilt 1.07 ×, 12 October 05:55)
    t_q = np.where((t_q >= 0.5 * LEAST_H) & (t_q < LEAST_H), np.minimum(LEAST_H, cl["room"]), t_q)
    ok_base = first_run & np.isfinite(cl["base"])
    bx = cl["base"].copy()
    bx[ok_base] = on_wall(cl["cells"][ok_base], cl["base"][ok_base])
    # the forms of a free-forms layout (`section_forms.py --free-forms`) as production draws them, each its own metal
    form_of = cl["layout"]
    in_form = ok_base & (cl["kind"] == "free") & (form_of >= 0)
    xy_all = mem["lo"][:2] + mem["h"] * (cl["cells"] + 0.5)
    own = cupmod.pieces(all_rooms, z_split, half)

    def outline(px, py):  # the half's outline in plan: its rooms' outsides (< 0 within)
        return np.min([np.hypot(px - p["axis"][0], py - p["axis"][1]) - (float(p["r"]) + wall) for p in own], axis=0)

    for v in np.unique(form_of[in_form]):
        sel = np.flatnonzero(in_form & (form_of == v))
        kind_v = mem["meta"][int(v)]["kind"]
        # an end wall's form drawn as production draws it; one beside a side wall (a gusset, a rib's part down to a bolt)
        # keeps its own heights, as it stands on the split, not on a wall: a straight top dropped a gusset's root and left
        # its tip on a hairline, and the single factor did not refine (`prod10_asis`, 12 October 03:36)
        # (off by default: the flat faces, planes and straight tops cost the seats a quarter of their stiffness, the
        # optimiser's heights vary where the load asks, `prod11_asis` 52.8 µm where `prod9_asis` read 41.8)
        if FIT_FORMS and (outline(*xy_all[sel].T) < 0).mean() >= 0.5:
            t_q[sel] = np.minimum(form_tops(kind_v, xy_all[sel], cl["s"][sel], bx[sel], t_c[sel], out_dir), cl["room"][sel])
        if kind_v in ("rib", "gusset") and t_q[sel].mean() >= LEAST_H and "a_mm" in mem["meta"][int(v)]:
            ends += [np.asarray(mem["meta"][int(v)]["a_mm"]), np.asarray(mem["meta"][int(v)]["b_mm"])]
    is_ring = (cl["kind"] == "ring") | (in_form & np.isin(cl["form"], ("ring",)))
    t_q = np.where(is_ring, np.maximum(t_q, np.minimum(BOSS_LEAST, cl["room"])), t_q)
    paint = ok_base & np.isin(cl["kind"], ("free", "ring", "rest", "bridge", "web", "belt", "lug")) & (t_q >= LEAST_H)
    other = (~first_run) & ((cl["layer"] // 10_000) == (0 if lower else 1)) & (cl["t"] >= LEAST_H)
    if other.any():
        print(f"{half}: {int(other.sum())} columns' metal in a second run along the pull, not drawn", flush=True)
    idx = np.flatnonzero(paint)
    base_ex = bx[idx]
    cc = cl["cells"][idx]
    within = outline(mem["lo"][0] + mem["h"] * (cc[:, 0] + 0.5), mem["lo"][1] + mem["h"] * (cc[:, 1] + 0.5)) < 0
    # each form its own pieces (its own outline and top, joined to the others by the smooth union's fillet); the rest
    # by continuous wall
    fid = np.where(in_form[idx], form_of[idx], -1)
    seats_here = [b for b in layout["bearings"] if (b["side"] == "-z") == lower]
    for v in np.unique(fid):
        grp = np.flatnonzero(fid == v)
        kind_v = mem["meta"][int(v)]["kind"] if v >= 0 else "free"
        shape = form_shape(kind_v, mem["lo"][:2] + mem["h"] * (cc[grp] + 0.5), mem["h"], mem["meta"][int(v)] if v >= 0 else {}, seats_here) if EXACT_FORMS else None
        for comp in wall_pieces(cc[grp], base_ex[grp], mem["h"]):
            comp = grp[comp]
            got = thickening(cc[comp], base_ex[comp], t_q[idx[comp]], mem["lo"], mem["h"], out_dir, grid, min(R_TOP, 0.5 * mem["h"]),
                             outline=outline, beside=bool(within[comp].mean() < 0.5), shape=shape,
                             top_sigma=FORM_SIGMA if v >= 0 else None)  # fmt: skip
            if got is not None:
                prims.append((*got, k_feat))
                drawn["plates"] += 1
    if PANEL_RIBS:  # production's ribs on the bare panels (`panel_ribs`)
        metal_xy = mem["lo"][:2] + mem["h"] * (cc + 0.5)
        for got in panel_ribs(fld, faces, lower, metal_xy, outline, seats_here, 12.0, PANEL_REACH, PANEL_STEP, PANEL_T, PANEL_H):
            prims.append((*got, k_feat))
            drawn["ribs"] += 1
    if lower:  # every mount its bracket: where no drawn rib reaches its lug, an arm from the lug to the shell's nearest point
        pieces = cupmod.pieces(all_rooms, z_split, half)
        cxy = mem["lo"][:2] + mem["h"] * (cc + 0.5)
        for m in layout["mounts"]:
            c = np.asarray(m["centre"], float)
            r_m = 0.5 * float(s["mount_diameter"])
            # reached when the drawn metal about its lug holds at least MOUNT_HELD (12 October 03:38: a rib's end near
            # the mount was taken for its bracket, and the lug hung on a hairline: the single factor did not refine)
            near = np.hypot(*(cxy - c).T) <= r_m + 16.0
            if float((t_q[idx][near] * mem["h"] ** 2).sum()) >= MOUNT_HELD:
                continue
            best = None
            for p in pieces:  # the nearest point of a room's outside, in plan
                ax = np.asarray(p["axis"], float)
                d = c - ax
                r_out = float(p["r"]) + wall
                q = ax + d / max(np.hypot(*d), 1e-9) * (r_out - 2.0)
                if best is None or np.hypot(*(q - c)) < np.hypot(*(best[0] - c)):
                    best = (q, ax, r_out - 2.0)
            z0, z1 = float(m["z"][0]), float(m["z"][1])
            # production's gusseted lug: two webs from the lug to the shell either side of its nearest point, a
            # triangle with the wall (12 October 03:50; a solid bar 25 mm wide weighed 0.15 kg a mount)
            q, ax, r_s = best
            reach = float(np.hypot(*(q - c)))
            u = (q - ax) / max(np.hypot(*(q - ax)), 1e-9)
            if BRACKET == "bar":
                prims.append((*rib(c, q, 0.5 * BAR_W * float(s["mount_diameter"]), z0, z0, z1, z1, 4.0), 6.0))
            else:
                for sgn in (-1.0, 1.0):
                    th = sgn * max(25.0, 0.6 * reach) / r_s
                    rot = np.array([u[0] * np.cos(th) - u[1] * np.sin(th), u[0] * np.sin(th) + u[1] * np.cos(th)])
                    prims.append((*rib(c, ax + r_s * rot, 0.5 * WEB_T, z0, z0, z1, z1, 2.0), 6.0))
            drawn["brackets"] += 1
    return finish_body(fld, prims[n_shell:], layout, z_split, half, grid, f"{drawn['ribs']} ribs, {drawn['rings']} rings, {drawn['plates']} plates, "
                       f"{drawn['brackets']} brackets; {len(prims)} primitives")  # fmt: skip


def shell_field(layout: dict, all_rooms: list, z_split: float, wall: float, half: str, rround: float, grid: float):
    """The half's exact shell as smooth primitives on its own field: each room's cup (a cylinder grown by the wall past
    its end), the plate over the other half's wider opening, the split flange's land, the bolts' bosses, the mounts;
    rounded at their convex edges (at most the wall). Returns (the field, the shell's outer face along the pull at each
    plan node, the shell's primitives)."""
    import cup as cupmod

    lower = half == "motor_side"
    out_dir = -1.0 if lower else 1.0
    s = layout["settings"]
    fl = layout["flange"]
    t_f = float(fl["thickness"])
    prims = []  # (sdf, box lo, box hi, k)
    for p in cupmod.pieces(all_rooms, z_split, half):  # the cup: each room's outside, the wall round it and past its end
        far = float(p["far"]) + out_dir * wall
        z0, z1 = (far, z_split + 2.0) if lower else (z_split - 2.0, far)
        prims.append((*cylinder(p["axis"], float(p["r"]) + wall, z0, z1, min(rround, wall)), K_SHELL))
    plate = (z_split - wall, z_split + 2.0) if lower else (z_split - 2.0, z_split + wall)
    for p in cupmod.pieces(all_rooms, z_split, "cover" if lower else "motor_side"):  # over the other half's wider opening
        prims.append((*cylinder(p["axis"], float(p["r"]) + wall, *plate, 0.0), K_SHELL))
    zf = (z_split - t_f, z_split + 2.0) if lower else (z_split - 2.0, z_split + t_f)
    prims.append((*land(fl["outer"], fl["inner"], *zf, 2.0), 3.0))
    for c in layout["bolts"]:
        prims.append((*cylinder(c, 0.5 * float(s["bolt_boss"]), *zf, 2.0), 3.0))
    if lower:
        for m in layout["mounts"]:
            prims.append((*cylinder(m["centre"], 0.5 * float(s["mount_diameter"]), m["z"][0], m["z"][1], 2.0), 3.0))
    # the shell first: its outer face along the pull is what every feature stands on (12 October 02:45: on the
    # voxel skin's face, up to a voxel off the exact wall, the thickening drew 7.27 kg where the field drew 5.93)
    lo_b = np.min([p[1] for p in prims], axis=0) - FEATURE_REACH
    hi_b = np.max([p[2] for p in prims], axis=0) + FEATURE_REACH
    fld = Field(lo_b, hi_b, grid)
    for f, b0, b1, k in prims:
        fld.add(b0, b1, f, k)
    return fld, exact_faces(fld, lower), prims


def finish_body(fld: Field, features: list, layout: dict, z_split: float, half: str, grid: float, note: str):
    """The features on the shell's field, each short of the kept-clear spaces (`cleared`), contoured at zero, its
    largest watertight piece decimated without crossing itself: the half's solid (a manifold3d Manifold) before the
    exact cuts."""
    import mesh_route as mr

    lower = half == "motor_side"
    spaces = clear_spaces(layout, z_split, lower)
    for f, b0, b1, k in features:  # the features on the shell's field, each short of the kept-clear spaces
        g_, b0, b1 = cleared((f, b0, b1), spaces)
        fld.add(b0, b1, g_, k)
    import trimesh
    from skimage.measure import marching_cubes

    field = fld.f
    if OPEN_R > 0:  # the least thickness a casting has: the solid opened by OPEN_R (eroded, then grown back), so no lip,
        # sliver or step thinner than twice it is left and every edge is rounded; the coarsened surfaces' slivers where
        # thin layers met stopped TetGen at every rung (`fa6_web`, 12 October 04:40)
        from scipy.ndimage import distance_transform_edt

        inside_d = distance_transform_edt(field < 0.0) * grid
        field = (distance_transform_edt(inside_d <= OPEN_R) * grid - OPEN_R).astype(np.float32)
        del inside_d
    # contoured a hair off zero: flat faces landing on grid planes put exact zeros on the grid, whose degenerate
    # triangles left the contour open (12 October 02:02)
    verts, faces, _, _ = marching_cubes(field, level=0.0137 * grid, spacing=(grid, grid, grid))
    tm = trimesh.Trimesh(verts + fld.lo, faces, process=True)
    if tm.volume < 0:
        tm.invert()
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    # decimated, but never into a surface that crosses itself (marching cubes' never does; the collapse folded one of
    # `fa9_web`'s, and nothing downstream could unfold it, 12 October 04:50): less decimated, or not at all
    # (the whole contour, kept where every decimation crossed, ran FE's mesh past its ceiling: the decimation with the
    # fewest crossings is kept then, `mesh_route.coarse` keeping faces out round them)
    tried = []
    for target in (400_000, 650_000):
        if len(tm.faces) <= target:
            break
        import pymeshlab

        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(tm.vertices, tm.faces))
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target, preservenormal=True, preservetopology=True)
        m = ms.current_mesh()
        dec = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)
        tried.append((len(mr.crossing_centres(dec.vertices, dec.faces)), len(tried), dec))
        if not tried[-1][0]:
            break
    if tried:
        crossed, _, tm = min(tried, key=lambda x: (x[0], x[1]))
        if crossed:
            print(f"{half}: the least crossed decimation kept ({crossed} faces cross)", flush=True)
    print(f"{half}: implicit body: {note} on {tuple(int(v) for v in fld.n)} cells; {len(tm.faces):,} triangles, watertight {tm.is_watertight}", flush=True)
    return mr.from_trimesh(tm)


def column_frame(run: str) -> dict:
    """A run's height-field columns: each one's plan cell, layer, base (the face its first free voxel stands on, mm)
    and room (its free voxels, mm)."""
    import regions as rg
    import topo

    ctx = rg.context(run)
    model, kind, lo, h = ctx["model"], ctx["kind"], ctx["lo"], ctx["h"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    kk = np.unravel_index(elem[free_e], model["n"])[2]
    lower = (layer[col] // 10_000) == 0
    base_vox = np.where(pos == 0)[0]
    base = np.full(len(pts), np.nan)
    base[col[base_vox]] = np.where(lower[base_vox], lo[2] + h * (kk[base_vox] + 1), lo[2] + h * kk[base_vox])
    return {"cells": pts[:, :2].astype(int), "layer": layer, "base": base, "room": np.bincount(col, minlength=len(pts)) * h,
            "lo": lo, "h": h, "n": tuple(int(v) for v in model["n"])}  # fmt: skip


def parts_body(parts_file: str, half: str, layout: dict, all_rooms: list, z_split: float, wall: float, k_feat: float = 4.0,
               rround: float = 3.0, grid: float = 1.25):  # fmt: skip
    """The half's solid drawn from production's parts (LOP-26, Refine: `parts.py`, the optimiser's own parts and sizes):
    every member a plate `width` thick along its two ends, its top from its root height to its tip height off each
    column's base (on the exact shell where the shell is there, else the model's), within the column's room, fully
    rounded at its top's edges (R_TOP), drawn only where it stands at least the least height; every ring a ring prism
    off its columns' base; all of it one smooth body with the exact, filleted shell (`shell_field`, fillets of k_feat at
    every junction), then contoured (`finish_body`); `outcome_cad.build_mesh` cuts it exact (LOOP_PARTS=<file>)."""
    import parts as pm

    lower = half == "motor_side"
    out_dir = -1.0 if lower else 1.0
    path = Path(parts_file)
    path = path if path.is_absolute() or path.exists() else OUT / path
    spec = json.loads(path.read_text(encoding="utf-8"))
    if any("ends" not in m for m in spec["members"]):  # a reading, not yet optimised: its parts at their start
        pmap = pm.PartsMap(spec, np.zeros((0, 2)), np.zeros(0))
        spec = pmap.params(pmap.start())
    least = float(spec.get("least_mm") or 8.0)
    fr = column_frame(spec["run"])
    fld, faces, shell = shell_field(layout, all_rooms, z_split, wall, half, rround, grid)
    lo, h, n = fr["lo"], fr["h"], fr["n"]
    first = fr["layer"] == pm.LAYER[half]
    base_map, room_map = np.full(n[:2], np.nan), np.zeros(n[:2])
    ci, cj = fr["cells"][first, 0], fr["cells"][first, 1]
    base_map[ci, cj], room_map[ci, cj] = fr["base"][first], fr["room"][first]
    # each column's base on the exact shell where the shell is there (within 1.5 voxels of the model's), else the model's
    cx, cy = lo[0] + h * (ci + 0.5), lo[1] + h * (cj + 0.5)
    ix = np.clip(np.rint((cx - fld.lo[0]) / fld.g).astype(int), 0, fld.n[0] - 1)
    iy = np.clip(np.rint((cy - fld.lo[1]) / fld.g).astype(int), 0, fld.n[1] - 1)
    ex = faces[ix, iy]
    ok = np.isfinite(ex) & (np.abs(ex - base_map[ci, cj]) <= 1.5 * h)
    base_map[ci, cj] = np.where(ok, ex, base_map[ci, cj])

    def column_at(p):
        i_ = int(np.clip(np.rint((p[0] - lo[0]) / h - 0.5), 0, n[0] - 1))
        j_ = int(np.clip(np.rint((p[1] - lo[1]) / h - 0.5), 0, n[1] - 1))
        return base_map[i_, j_], room_map[i_, j_]

    feats, drawn = [], {"members": 0, "rings": 0}
    for m in spec["members"]:
        if m["half"] != half:
            continue
        a, b = np.asarray(m["ends"][0], float), np.asarray(m["ends"][1], float)
        length = float(np.hypot(*(b - a)))
        k_n = max(2, int(round(length / PIECE)) + 1)
        s_ = np.linspace(0.0, 1.0, k_n)
        line = a[None, :] + s_[:, None] * (b - a)[None, :]
        hs = m["h"][0] + s_ * (m["h"][1] - m["h"][0])
        got = [column_at(p) for p in line]
        base = np.array([g_[0] for g_ in got])
        room = np.array([g_[1] for g_ in got])
        if np.isfinite(base).sum() == 0:
            continue
        base = np.interp(s_, s_[np.isfinite(base)], base[np.isfinite(base)])  # a knot off the columns (in a boss's bore) takes its neighbours'
        hh = np.minimum(hs, np.where(room > 0, room, hs))
        keep = hh >= least
        # each run of knots where it stands at least the least height, one plate
        runs, cur = [], []
        for k, on in enumerate(keep):
            if on:
                cur.append(k)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        for r_ in runs:
            if len(r_) < 2:
                continue
            top, foot = base[r_] + out_dir * hh[r_], base[r_] - out_dir * BURY
            z_lo, z_hi = np.minimum(top, foot), np.maximum(top, foot)
            half_t = 0.5 * float(m["width"])
            feats.append((*polyline_rib(line[r_], half_t, z_lo, z_hi, min(R_TOP, half_t)), k_feat))
            drawn["members"] += 1
    gx, gy = lo[0] + h * (np.arange(n[0]) + 0.5), lo[1] + h * (np.arange(n[1]) + 0.5)
    px, py = np.meshgrid(gx, gy, indexing="ij")
    for r in spec["rings"]:
        if r["half"] != half or r["h"] < least:
            continue
        c = np.asarray(r["centre"], float)
        rho = np.hypot(px - c[0], py - c[1])
        if r["kind"] == "web":  # a plate over two bosses' hull, a round hole in it
            plan = np.column_stack([px.ravel(), py.ravel()])
            inside_web = pm.uneven_capsule(plan, c, np.asarray(r["centre2"], float), float(r["r1"]), float(r["r2"])).reshape(px.shape) <= 0.0
            cells = inside_web & (np.hypot(px - r["hole_at"][0], py - r["hole_at"][1]) > float(r["hole"])) & np.isfinite(base_map)
        elif r["kind"] == "arc":  # a rib along an arc
            ang = np.mod(np.arctan2(py - c[1], px - c[0]) - float(r["a0"]), 2.0 * np.pi)
            cells = (ang <= np.mod(float(r["a1"]) - float(r["a0"]), 2.0 * np.pi)) & (np.abs(rho - float(r["r"])) <= 0.5 * float(r["width"])) & np.isfinite(base_map)
        else:
            if r["kind"] == "band":
                r_in, r_out = r["r"] - 0.5 * r["width"], r["r"] + 0.5 * r["width"]
            else:
                r_in, r_out = (float(r.get("r_in") or 0.0) if r["kind"] == "annulus" else 0.0), float(r["r"])
            cells = (rho >= r_in) & (rho <= r_out) & np.isfinite(base_map)
        if cells.sum() < 3:
            continue
        b0 = float(np.median(base_map[cells]))
        hh = min(float(r["h"]), float(np.median(room_map[cells])) if (room_map[cells] > 0).any() else float(r["h"]))
        if hh < least:
            continue
        top, foot = b0 + out_dir * hh, b0 - out_dir * BURY
        z0, z1 = min(top, foot), max(top, foot)
        if r["kind"] == "web":
            feats.append((*web_plate(c, float(r["r1"]), np.asarray(r["centre2"], float), float(r["r2"]), z0, z1, R_TOP,
                                     np.asarray(r["hole_at"], float), float(r["hole"])), k_feat))  # fmt: skip
        elif r["kind"] == "arc":
            feats.append((*arc_rib(c, float(r["r"]), float(r["width"]), float(r["a0"]), float(r["a1"]), z0, z1, min(R_TOP, 0.5 * float(r["width"]))), k_feat))
        elif r_in > 0.0:
            feats.append((*ring(c, r_in, r_out, z0, z1, min(R_TOP, 0.5 * (r_out - r_in))), k_feat))
        else:
            feats.append((*cylinder(c, r_out, z0, z1, R_TOP), k_feat))
        drawn["rings"] += 1
    return finish_body(fld, feats, layout, z_split, half, grid, f"{drawn['members']} members, {drawn['rings']} rings (production's parts, {path.name})")


def members_body(run: str, half: str, layout: dict, all_rooms: list, z_split: float, wall: float, k_feat: float = 4.0,
                 rround: float = 3.0, grid: float = 1.25):  # fmt: skip
    """The half's solid drawn from a free run's clean members (LOP-25, the plan's generator B: `clean_draw.read`): each
    member a plate along its smoothed (or straightened) path, its width and its height off each column's base (on the
    exact shell where the shell is there, else the model's) the run's own, gently varying, its top rounded; each boss a
    ring; all of it one smooth body with the exact, filleted shell (`shell_field`; every joint filleted by the smooth
    union of k_feat), then contoured (`finish_body`); `outcome_cad.build_mesh` cuts it exact (LOOP_CLEAN=1)."""
    import clean_draw as cd

    lower = half == "motor_side"
    out_dir = -1.0 if lower else 1.0
    data = cd.read(run)
    least = float(data["least_mm"])
    fr = column_frame(run)
    fld, faces, _ = shell_field(layout, all_rooms, z_split, wall, half, rround, grid)
    lo, h, n = fr["lo"], fr["h"], fr["n"]
    first = fr["layer"] == (1 if lower else 10_001)
    base_map, room_map = np.full(n[:2], np.nan), np.zeros(n[:2])
    ci, cj = fr["cells"][first, 0], fr["cells"][first, 1]
    base_map[ci, cj], room_map[ci, cj] = fr["base"][first], fr["room"][first]
    cx, cy = lo[0] + h * (ci + 0.5), lo[1] + h * (cj + 0.5)
    ix = np.clip(np.rint((cx - fld.lo[0]) / fld.g).astype(int), 0, fld.n[0] - 1)
    iy = np.clip(np.rint((cy - fld.lo[1]) / fld.g).astype(int), 0, fld.n[1] - 1)
    ex = faces[ix, iy]
    ok = np.isfinite(ex) & (np.abs(ex - base_map[ci, cj]) <= 1.5 * h)
    base_map[ci, cj] = np.where(ok, ex, base_map[ci, cj])

    def column_at(p):
        i_ = int(np.clip(np.rint((p[0] - lo[0]) / h - 0.5), 0, n[0] - 1))
        j_ = int(np.clip(np.rint((p[1] - lo[1]) / h - 0.5), 0, n[1] - 1))
        return base_map[i_, j_], room_map[i_, j_]

    feats, drawn = [], {"members": 0, "rings": 0}
    d = data["halves"][half]
    for m in d["members"]:
        xy, w, hh = np.asarray(m["xy"], float), np.asarray(m["w"], float), np.asarray(m["h"], float)
        got = [column_at(p) for p in xy]
        base = np.array([g_[0] for g_ in got])
        room = np.array([g_[1] for g_ in got])
        if np.isfinite(base).sum() == 0:
            continue
        s_ = np.arange(len(xy), dtype=float)
        base = np.interp(s_, s_[np.isfinite(base)], base[np.isfinite(base)])  # a knot off the columns takes its neighbours'
        hh = np.minimum(hh, np.where(room > 0, room, hh))
        hh = np.maximum(hh, least)
        top, foot = base + out_dir * hh, base - out_dir * BURY
        z_lo, z_hi = np.minimum(top, foot), np.maximum(top, foot)
        feats.append((*variable_rib(xy, 0.5 * w, z_lo, z_hi, R_TOP), k_feat))
        drawn["members"] += 1
    gx, gy = lo[0] + h * (np.arange(n[0]) + 0.5), lo[1] + h * (np.arange(n[1]) + 0.5)
    px, py = np.meshgrid(gx, gy, indexing="ij")
    for r in d["rings"]:
        c = np.asarray(r["centre"], float)
        rho = np.hypot(px - c[0], py - c[1])
        cells = (rho >= r["r_in"]) & (rho <= r["r"]) & np.isfinite(base_map)
        if cells.sum() < 3:
            continue
        b0 = float(np.median(base_map[cells]))
        hh = min(float(r["h"]), float(np.median(room_map[cells])) if (room_map[cells] > 0).any() else float(r["h"]))
        top, foot = b0 + out_dir * hh, b0 - out_dir * BURY
        feats.append((*ring(c, float(r["r_in"]), float(r["r"]), min(top, foot), max(top, foot), min(R_TOP, 0.5 * (r["r"] - r["r_in"]))), k_feat))
        drawn["rings"] += 1
    return finish_body(fld, feats, layout, z_split, half, grid, f"{drawn['members']} clean members, {drawn['rings']} bosses (generator B, {run[:40]}…)")
