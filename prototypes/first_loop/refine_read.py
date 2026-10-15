"""PROTOTYPE (LOP-26, step B of Refine; the engineer, 12 October 11:01-11:16: "yes build") - a free run's members
read as production's parts (docs/features/loop/2026-10-12-primitive-library.md §3.3), for `parts.py`'s map and
`topo_free.py --parts`.

The free run is a height field with the least member (`LOOP_LEAST_MEMBER`), so its metal is members, not paint.
Each column's metal (mm off its base, the run's own densities) is read per half on the first run of columns
(over the end walls, and beside the side walls from the split):
- **tied first:** every seat's boss, a solid ring round its axis out to where the metal round it thins (half the
  ring's columns under the least height), at most the handbook's 1.25·D + 10 mm across, its height the
  metal's; a seat whose columns run far past the band (a seat on a tube) gets a tower's height range;
- **free next:** the rest of the metal over the end walls and beside the side walls apart, thinned to its
  skeleton (`skeleton_members`), twigs under `--prune` mm pruned, each branch cut into straight runs (`--tol`).
  Each run is a member `--width` mm wide between two nodes; an end at a boss's rim is a node sliding round it, at
  a bolt or a mount fixed there, at the outline sliding along it, else free (a junction, or a loose end);
- **broad metal** (the metal about a run wider than `--broad` mm) becomes parallel members `--pitch` mm apart,
  never one wide part;
- every member's root and tip heights are the metal's at its ends, at least the least height plus 1 mm, each
  within its columns' own room; its family is what its ends join (a link joins two bosses; a tie a boss and a
  bolt or a mount; a spoke a boss and the outline; an arm a mount; a rim or a belt runs along the outline; a fin
  stands beside a side wall; else a rib).
The parts are checked against the free run: the metal they hold at their start (each column the tallest part,
the least height's gate) against the run's, and the share of the run's metal within 6 mm of a part.

    refine_read.py <free run> --label <label> [--width 8] [--prune 12] [--tol 4] [--broad 16] [--pitch 12]

Writes data/first_loop/<label>.json (the parts, `parts.py`'s format, with the checks) and <label>.png (each half in
plan: the run's metal under the parts, coloured by family, and the parts' own metal at their start)."""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parts as pm  # noqa: E402
import regions as rg  # noqa: E402
import topo  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"
BOSS_REACH = 44.0  # mm past the bore a boss's metal is looked for
NODE_MERGE = 6.0  # mm: ends closer than this are one node
SNAP_BOSS, SNAP_BOLT, SNAP_MOUNT, SNAP_EDGE = 8.0, 14.0, 34.0, 6.0  # mm: an end this near a boss's rim, a bolt, a mount (its eye 18 + 16), the outline
ANGLE_MERGE = math.radians(8.0)  # ends at one boss's rim this close in angle are one node
FREE_REACH, KNOT_REACH = 15.0, 12.0  # mm a free node moves (an end, an interior knot)
GRID_PITCH = 28.0  # mm between a grid's nodes (with 8 mm members, the 20 mm gap of 12 October 12:43)
WHEEL_TURN = math.radians(10.0)  # how far a wheel's spokes may turn together, either way
CIRCLE_RANGE, EDGE_RANGE = math.radians(20.0), 20.0  # a sliding node's range either way
FAMILY_COLOUR = {"boss": "#7f3b08", "tower": "#b35806", "seal boss": "#fdb863", "ring rib": "#e08214", "link": "#d62728", "tie": "#1f77b4", "spoke": "#2ca02c",
                 "arm": "#9467bd", "rim": "#8c564b", "belt": "#e377c2", "fin": "#17becf", "gusset": "#bcbd22", "rib": "#3949ab",
                 "grid": "#e6550d", "curved rib": "#31a354", "web": "#6a51a3"}  # fmt: skip


def outline_polyline(discs: list, step: float = 1.0) -> np.ndarray:
    """The boundary of a union of discs (a half's rooms' outsides), a closed polyline in mm, counter-clockwise."""
    from skimage.measure import approximate_polygon, find_contours

    ax = np.array([d[0] for d in discs], float)
    rr = np.array([d[1] for d in discs], float)
    x0, x1 = (ax[:, 0] - rr).min() - 4.0, (ax[:, 0] + rr).max() + 4.0
    y0, y1 = (ax[:, 1] - rr).min() - 4.0, (ax[:, 1] + rr).max() + 4.0
    gx, gy = np.arange(x0, x1, step), np.arange(y0, y1, step)
    px, py = np.meshgrid(gx, gy, indexing="ij")
    inside = np.zeros(px.shape, bool)
    for (cx, cy), r in zip(ax, rr, strict=True):
        inside |= np.hypot(px - cx, py - cy) <= r
    contour = max(find_contours(inside.astype(float), 0.5), key=len)
    poly = approximate_polygon(contour, tolerance=0.4)
    pts = np.column_stack([x0 + step * poly[:, 0], y0 + step * poly[:, 1]])
    if np.hypot(*(pts[0] - pts[-1])) < 1e-6:
        pts = pts[:-1]
    area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    return pts if area > 0 else pts[::-1]


def nearest_on(poly: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """The arc length (mm) of the point of a closed polyline nearest p, and its distance."""
    q = np.vstack([poly, poly[:1]])
    seg = np.diff(q, axis=0)
    l2 = np.maximum((seg**2).sum(axis=1), 1e-12)
    t = np.clip(((p[None, :] - q[:-1]) * seg).sum(axis=1) / l2, 0.0, 1.0)
    foot = q[:-1] + t[:, None] * seg
    d = np.hypot(*(foot - p[None, :]).T)
    i = int(np.argmin(d))
    cum = np.concatenate([[0.0], np.cumsum(np.sqrt(l2))])
    return float(cum[i] + t[i] * math.sqrt(l2[i])), float(d[i])


def read(run: str, label: str, width: float = 8.0, prune_mm: float = 12.0, tol_mm: float = 4.0, broad: float = 16.0,
         pitch: float = 12.0, rich: bool = False) -> dict:  # fmt: skip
    from scipy.ndimage import binary_opening, distance_transform_edt, label as cc_label
    from skimage.measure import approximate_polygon
    from skimage.morphology import skeletonize

    import section_forms as sfm
    import skeleton_members as sk

    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    least = float(rec.get("least_height_mm") or 8.0)
    band = float(rec.get("band_mm") or 24.0)
    ctx = rg.context(run)
    model, kind, h, lo = ctx["model"], ctx["kind"], ctx["h"], ctx["lo"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, _, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    z = np.load(OUT / f"{run}.npz")
    phys = np.asarray(z["phys"], float)
    dens = phys if len(phys) == len(z["free_e"]) else phys[z["free_e"]]
    metal_col = np.bincount(col, weights=dens * h, minlength=len(pts))  # mm of metal a column, off its base
    room_col = np.bincount(col, minlength=len(pts)) * h  # mm: the column's own free run (its room)
    centres = lo[:2] + h * (pts + 0.5)
    n0, n1 = int(model["n"][0]), int(model["n"][1])
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    discs = sfm.outline_pieces()
    spec = {"run": run, "h": h, "least_mm": least, "band_mm": band, "width_mm": width, "edges": {}, "nodes": [], "members": [], "rings": [], "grids": {}, "rich": rich}
    checks = {}
    elsewhere = float(metal_col[~np.isin(layer, list(pm.LAYER.values()))].sum() * h * h / 1e3)
    if elsewhere > 1.0:
        checks["metal in other runs, cm3 (not read)"] = round(elsewhere, 1)
    for half, lay_id in pm.LAYER.items():
        lower = half == "motor_side"
        on = np.flatnonzero(layer == lay_id)
        ii, jj = pts[on, 0].astype(int), pts[on, 1].astype(int)
        hmap, room = np.zeros((n0, n1)), np.zeros((n0, n1))
        hmap[ii, jj], room[ii, jj] = metal_col[on], room_col[on]
        gx = lo[0] + h * (np.arange(n0) + 0.5)
        gy = lo[1] + h * (np.arange(n1) + 0.5)
        px, py = np.meshgrid(gx, gy, indexing="ij")
        own = discs[half]
        inside = np.zeros((n0, n1), bool)
        for ax_, r_ in own:
            inside |= np.hypot(px - ax_[0], py - ax_[1]) <= r_
        edge = outline_polyline(own)
        spec["edges"][half] = edge.tolist()
        along = pm.PartsMap({"nodes": [], "edges": {half: edge.tolist()}}, np.zeros((0, 2)), np.zeros(0))._along  # (name, s) -> point, tangent
        solid = hmap >= least
        taken = np.zeros((n0, n1), bool)
        bosses = []

        def annulus(c: np.ndarray, r_in: float, r_most: float, family: str, extra: dict) -> float | None:
            """A ring from r_in out to where the run's metal round it thins (half its 4 mm band's columns under the least
            height), at most r_most; its height the metal's; None where the run holds no metal next to r_in."""
            nonlocal taken
            rho = np.hypot(px - c[0], py - c[1])
            r_out, first = None, True
            for r in np.arange(r_in, r_most, 4.0):
                band_cells = (rho >= r) & (rho < r + 4.0) & (room > 0)
                if band_cells.sum() < 3:
                    continue
                if solid[band_cells].mean() >= 0.5:
                    r_out = r + 4.0
                elif first and solid[band_cells].mean() < 0.3:
                    return None
                else:
                    break
                first = False
            r_out = float(np.clip(r_out if r_out is not None else r_in + 6.0, r_in + 6.0, r_most))
            within = (rho >= r_in) & (rho <= r_out) & (room > 0)
            hs = hmap[within & solid]
            h0 = float(np.median(hs)) if len(hs) else least + 2.0
            h_top = float(np.percentile(room[within], 90)) if within.any() else band
            fam = "tower" if family == "boss" and h_top > band + 8.0 else family
            spec["rings"].append({"family": fam, "half": half, "kind": "annulus", "centre": c.tolist(), "r_in": r_in, "r": r_out,
                                  "r_range": [r_in + 4.0, r_most + 4.0], "h": float(np.clip(h0, least + 1.0, max(h_top, least + 2.0))),
                                  "h_range": [0.0, max(h_top, least + 2.0)], **extra})  # fmt: skip
            taken |= (rho >= r_in - 2.0) & (rho <= r_out + 2.0)
            return r_out

        # every seat's boss, a ring from its bore out, never wider than the handbook's boss (12 October 11:30: read out to
        # where the metal thins, the lumps round the seats became solid pads up to 70 mm across, lumps by another name; the
        # lump's metal past the boss, and over the bearing, becomes members)
        for b in lay["bearings"]:
            if (b["side"] == "-z") != lower:
                continue
            c = np.asarray(b["axis"], float)
            r_bore = 0.5 * float(b["D"])
            r_out = annulus(c, r_bore, 0.625 * float(b["D"]) + 5.0, "boss", {"shaft": b["shaft"]})
            bosses.append((c, r_out if r_out is not None else r_bore + 6.0))
            if r_out is None:  # the boss stays, at its least, for the members to end on
                annulus_least = {"family": "boss", "half": half, "kind": "annulus", "centre": c.tolist(), "r_in": r_bore, "r": r_bore + 6.0,
                                 "r_range": [r_bore + 4.0, 0.625 * float(b["D"]) + 9.0], "h": least + 1.0, "h_range": [0.0, band], "shaft": b["shaft"]}  # fmt: skip
                spec["rings"].append(annulus_least)
        # a seal's boss round every shaft's exit through this half's end walls
        z_split = float(lay["z"]["split"])
        for e in lay.get("exits") or []:
            if (float(e["z"][1]) <= z_split) != lower:
                continue
            annulus(np.asarray(e["centre"], float), float(e["radius"]), float(e["radius"]) + 12.0, "seal boss", {"exit": e["name"]})
        # the free members, over the end walls and beside the side walls apart
        bolts = [np.asarray(p, float) for p in lay["bolts"]]
        mounts = [np.asarray(m["centre"], float) for m in lay["mounts"] if (m.get("pod", "motor_side") == "motor_side") == lower]
        node_of = []  # (half, kind, data) of every node made here, to merge
        base = len(spec["nodes"])

        def node(p: np.ndarray, interior: bool, region: str) -> int:
            """The node an end or a knot at p takes: snapped to a boss's rim, a bolt, a mount or the outline, else free;
            ends merged with a node already there."""
            for k, (kind_, data) in enumerate(node_of):
                if kind_ == "circle" and data["boss"] is not None and not interior:
                    c_, r_ = data["centre"], data["r"]
                    ang = math.atan2(p[1] - c_[1], p[0] - c_[0])
                    if abs(np.hypot(*(p - c_)) - r_) <= SNAP_BOSS + 2.0 and abs((ang - data["angle"] + math.pi) % (2 * math.pi) - math.pi) <= ANGLE_MERGE:
                        return base + k
                elif kind_ in ("fixed", "free", "edge") and not interior and np.hypot(*(p - data["at"])) <= NODE_MERGE:
                    return base + k
            if not interior:
                for bi, (c_, r_) in enumerate(bosses):
                    if np.hypot(*(p - c_)) <= r_ + SNAP_BOSS:
                        ang = math.atan2(p[1] - c_[1], p[0] - c_[0])
                        at = c_ + r_ * np.array([math.cos(ang), math.sin(ang)])
                        node_of.append(("circle", {"boss": bi, "centre": c_, "r": r_, "angle": ang, "at": at}))
                        spec["nodes"].append({"kind": "circle", "half": half, "centre": c_.tolist(), "r": r_, "angle": ang,
                                              "range": [ang - CIRCLE_RANGE, ang + CIRCLE_RANGE], "on": f"boss {bi}"})  # fmt: skip
                        return len(spec["nodes"]) - 1
                for what, points, reach in (("mount", mounts, SNAP_MOUNT), ("bolt", bolts, SNAP_BOLT)):
                    for q in points:
                        if np.hypot(*(p - q)) <= reach:
                            for k, (kind_, data) in enumerate(node_of):  # one node a hard point
                                if kind_ == "fixed" and np.hypot(*(data["at"] - q)) < 1e-6:
                                    return base + k
                            node_of.append(("fixed", {"at": q, "boss": None, "what": what}))
                            spec["nodes"].append({"kind": "fixed", "half": half, "xy": q.tolist(), "on": what})
                            return len(spec["nodes"]) - 1
                s_, d_ = nearest_on(edge, p)
                if d_ <= SNAP_EDGE:
                    at = along(half, s_)[0]
                    node_of.append(("edge", {"at": at, "boss": None}))
                    spec["nodes"].append({"kind": "edge", "half": half, "edge": half, "s": s_, "range": [s_ - EDGE_RANGE, s_ + EDGE_RANGE], "on": "outline"})
                    return len(spec["nodes"]) - 1
            node_of.append(("free", {"at": p, "boss": None}))
            spec["nodes"].append({"kind": "free", "half": half, "xy0": p.tolist(), "reach": KNOT_REACH if interior else FREE_REACH,
                                  "on": "knot" if interior else region})  # fmt: skip
            return len(spec["nodes"]) - 1

        def region_at(p: np.ndarray) -> str:
            i_ = int(np.clip(np.rint((p[0] - lo[0]) / h - 0.5), 0, n0 - 1))
            j_ = int(np.clip(np.rint((p[1] - lo[1]) / h - 0.5), 0, n1 - 1))
            return "end walls" if inside[i_, j_] else "side walls"

        def cells_on(a: np.ndarray, b: np.ndarray, k: int = 25):
            s_ = np.linspace(0.0, 1.0, k)
            line = a[None, :] + s_[:, None] * (b - a)[None, :]
            return (np.clip(np.rint((line[:, 0] - lo[0]) / h - 0.5).astype(int), 0, n0 - 1),
                    np.clip(np.rint((line[:, 1] - lo[1]) / h - 0.5).astype(int), 0, n1 - 1))  # fmt: skip

        def parallel(xy: np.ndarray, wide: float, family: str | None, region: str | None) -> None:
            """Members along a polyline: one, or parallel ones `pitch` apart where the metal about it is broad."""
            count = 1 if wide <= broad else int(min(3, max(2, round(wide / pitch))))
            d_all = xy[-1] - xy[0]
            nrm = np.array([-d_all[1], d_all[0]]) / max(np.hypot(*d_all), 1e-9)
            offsets = [0.0] if count == 1 else list((np.arange(count) - 0.5 * (count - 1)) * min(pitch, wide / count))
            for off in offsets:
                pts_xy = xy + off * nrm[None, :]
                ids = [node(p, interior=0 < k < len(pts_xy) - 1, region=region or region_at(p)) for k, p in enumerate(pts_xy)]
                for a, b in zip(ids[:-1], ids[1:], strict=True):
                    if a != b:
                        mid = 0.5 * (pts_xy[0] + pts_xy[-1])
                        spec["members"].append({"family": family, "half": half, "a": a, "b": b, "width": width, "region": region or region_at(mid)})

        gridded = np.zeros((n0, n1), bool)

        def run_height(ci, cj) -> tuple[float, float]:
            """The run's metal height along cells (the median where it holds metal) and their room (90th percentile)."""
            hv, rv = hmap[ci, cj], room[ci, cj]
            good = hv >= least
            top = max(float(np.percentile(rv[rv > 0], 90)) if (rv > 0).any() else band, least + 2.0)
            return float(np.clip(np.median(hv[good]) if good.any() else least + 2.0, least + 1.0, top)), top

        def arc_of(xy: np.ndarray, ci, cj) -> bool:
            """A branch that bends steadily (four knots or more, every turn one way, 30° or more in all, a circle within 4 mm
            of every knot, its radius 30-400 mm) as a curved rib: an arc of one height whose radius the optimiser sizes."""
            if len(xy) < 4:
                return False
            seg = np.diff(xy, axis=0)
            heading = np.arctan2(seg[:, 1], seg[:, 0])
            turns = (np.diff(heading) + math.pi) % (2.0 * math.pi) - math.pi
            if not (np.all(turns > 0) or np.all(turns < 0)) or abs(float(turns.sum())) < math.radians(30.0):
                return False
            fit = np.linalg.lstsq(np.column_stack([xy, np.ones(len(xy))]), -(xy**2).sum(axis=1), rcond=None)[0]  # x²+y²+Dx+Ey+F = 0
            c_ = -0.5 * fit[:2]
            r_fit = math.sqrt(max(float(c_ @ c_ - fit[2]), 0.0))
            if not 30.0 <= r_fit <= 400.0 or float(np.abs(np.hypot(*(xy - c_).T) - r_fit).max()) > 4.0:
                return False
            angs = np.arctan2(xy[:, 1] - c_[1], xy[:, 0] - c_[0])
            a0, a1 = (float(angs[0]), float(angs[-1])) if turns.sum() > 0 else (float(angs[-1]), float(angs[0]))  # counter-clockwise
            # production's curved ribs: a ring rib's arc round a boss, or a gently curved rib (90° at most); a long arc round
            # nothing is no production form (12 October 13:08: 196° and 229° arcs centred in the open)
            round_boss = any(np.hypot(*(c_ - cb)) <= 15.0 for cb, _ in bosses)
            if not round_boss and (a1 - a0) % (2.0 * math.pi) > math.radians(90.0):
                return False
            h0, top = run_height(ci, cj)
            spec["rings"].append({"family": "curved rib", "half": half, "kind": "arc", "centre": c_.tolist(), "r": r_fit,
                                  "r_range": [r_fit - 8.0, r_fit + 8.0], "width": width, "a0": a0, "a1": a1, "h": h0, "h_range": [0.0, top]})  # fmt: skip
            return True

        def grid_patch(xy: np.ndarray, wide: float, foot_: np.ndarray) -> None:
            """Broad metal about a branch (the footprint within half its width of it) as a triangular grid of members
            `GRID_PITCH` apart along the branch: one frame, shifted, turned and stretched as one, so the grid stays regular."""
            nonlocal gridded
            seg_d = np.full(px.shape, np.inf)
            for p0, p1 in zip(xy[:-1], xy[1:], strict=True):
                ab = p1 - p0
                t_ = np.clip(((px - p0[0]) * ab[0] + (py - p0[1]) * ab[1]) / max(float(ab @ ab), 1e-9), 0.0, 1.0)
                seg_d = np.minimum(seg_d, np.hypot(px - (p0[0] + t_ * ab[0]), py - (p0[1] + t_ * ab[1])))
            region = foot_ & (seg_d <= 0.5 * wide + 4.0)
            if region.sum() < 12:
                parallel(xy, wide, None, None)
                return
            gridded |= region
            cells_ = np.argwhere(region)
            xy_c = lo[:2][None, :] + h * (cells_ + 0.5)
            u0 = math.atan2(*(xy[-1] - xy[0])[::-1])
            e1, e2 = np.array([math.cos(u0), math.sin(u0)]), np.array([math.cos(u0 + math.pi / 3), math.sin(u0 + math.pi / 3)])
            origin = xy_c.mean(axis=0)
            ij = np.linalg.solve(np.column_stack([e1, e2]) * GRID_PITCH, (xy_c - origin).T).T
            key = f"{half} grid {len(spec['grids'])}"
            spec["grids"][key] = {"origin": origin.tolist(), "angle": u0, "pitch": GRID_PITCH, "shift": 6.0, "turn": 0.1, "stretch": 0.15}
            from scipy.spatial import cKDTree as _tree

            near = _tree(xy_c)
            ids = {}
            for i_ in range(int(np.floor(ij[:, 0].min())) - 1, int(np.ceil(ij[:, 0].max())) + 2):
                for j_ in range(int(np.floor(ij[:, 1].min())) - 1, int(np.ceil(ij[:, 1].max())) + 2):
                    p = origin + GRID_PITCH * (i_ * e1 + j_ * e2)
                    if near.query(p)[0] <= 4.0:  # a node on the broad metal
                        ids[(i_, j_)] = len(spec["nodes"])
                        spec["nodes"].append({"kind": "lattice", "half": half, "grid": key, "i": i_, "j": j_, "on": "grid"})
            for (i_, j_), a in ids.items():
                for di, dj in ((1, 0), (0, 1), (-1, 1)):  # a triangle's three edges, each once
                    b = ids.get((i_ + di, j_ + dj))
                    if b is not None:
                        mid = 0.5 * (place_any(spec["nodes"][a]) + place_any(spec["nodes"][b]))
                        spec["members"].append({"family": "grid", "half": half, "a": a, "b": b, "width": width, "region": region_at(mid)})

        def place_any(nd: dict) -> np.ndarray:
            if nd["kind"] == "lattice":
                g = spec["grids"][nd["grid"]]
                u0 = float(g["angle"])
                e1, e2 = np.array([math.cos(u0), math.sin(u0)]), np.array([math.cos(u0 + math.pi / 3), math.sin(u0 + math.pi / 3)])
                return np.asarray(g["origin"], float) + float(g["pitch"]) * (nd["i"] * e1 + nd["j"] * e2)
            if nd["kind"] in ("circle", "spoke"):
                return np.asarray(nd["centre"]) + nd["r"] * np.array([math.cos(nd["angle"]), math.sin(nd["angle"])])
            if nd["kind"] == "edge":
                return along(half, nd["s"])[0]
            return np.asarray(nd["xy" if nd["kind"] == "fixed" else "xy0"], float)

        def wheels(place) -> None:
            """A boss's radial spokes (four or more members from its rim, within 25° of radial) made one wheel: evenly
            spaced, each its own length, turning together (one shared variable); a rim ring where they end at one radius."""
            for bi, (c_, r_) in enumerate(bosses):
                found = []
                for k_m, m in enumerate(spec["members"]):
                    if m["half"] != half:
                        continue
                    for e_in, e_out in ((m["a"], m["b"]), (m["b"], m["a"])):
                        nd_in = spec["nodes"][e_in]
                        p_in = place(nd_in)
                        # an end on the boss's rim, or a radial rib's inner end within 20 mm of it (12 October 13:08: the
                        # cover's spokes stopped short of its output boss and were taken for plain ribs)
                        on_it = (nd_in["kind"] == "circle" and nd_in.get("on") == f"boss {bi}") or (
                            nd_in["kind"] == "free" and float(np.hypot(*(p_in - c_))) <= r_ + 25.0)
                        if on_it:
                            p_out = place(spec["nodes"][e_out])
                            seg = p_out - p_in
                            radial = (p_in - c_) / max(float(np.hypot(*(p_in - c_))), 1e-9)
                            # ending at another boss it is a link, not a spoke (12 October 13:12: the ribs between two bosses
                            # were read as a fan of one, with a rim through bare wall)
                            at_other = any(np.hypot(*(p_out - cb)) <= rb + 25.0 for bj, (cb, rb) in enumerate(bosses) if bj != bi)
                            if not at_other and np.hypot(*seg) > 8.0 and float(np.hypot(*(p_out - c_))) > float(np.hypot(*(p_in - c_))) and \
                                    float(seg @ radial) / float(np.hypot(*seg)) >= math.cos(math.radians(35.0)):
                                found.append((k_m, math.atan2(p_in[1] - c_[1], p_in[0] - c_[0]), float(np.hypot(*(p_out - c_)))))
                            break
                if len(found) < 4:
                    continue
                found.sort(key=lambda t_: t_[1])
                n = len(found)
                angles = np.array([a for _, a, _ in found])
                gaps = np.diff(np.r_[angles, angles[0] + 2.0 * math.pi])
                full = bool(gaps.max() < 0.5 * math.pi)
                if full:  # all round: a full wheel, its turn the spokes' circular mean
                    phi = math.atan2(*np.mean([[math.sin(a - 2.0 * math.pi * k / n), math.cos(a - 2.0 * math.pi * k / n)]
                                                for k, a in enumerate(angles)], axis=0))  # fmt: skip
                    thetas = [phi + 2.0 * math.pi * k / n for k in range(n)]
                else:  # a fan: evenly over the spokes' own arc, its widest gap left open
                    k0 = int(np.argmax(gaps)) + 1
                    order = [(k0 + k) % n for k in range(n)]
                    first, last = angles[order[0]], angles[order[-1]]
                    span = (last - first) % (2.0 * math.pi)
                    thetas = [None] * n
                    for k, idx_ in enumerate(order):
                        thetas[idx_] = first + span * k / max(n - 1, 1)
                key = f"{half} wheel {bi}"
                drop = {k_m for k_m, _, _ in found}
                radii = []
                for (k_m, _, rad_out), th in zip(found, thetas, strict=True):
                    a = len(spec["nodes"])
                    spec["nodes"].append({"kind": "spoke", "half": half, "centre": c_.tolist(), "r": r_, "angle": th, "turn": WHEEL_TURN,
                                          "share": key, "on": f"boss {bi}"})  # fmt: skip
                    spec["nodes"].append({"kind": "spoke", "half": half, "centre": c_.tolist(), "r": rad_out, "angle": th, "turn": WHEEL_TURN,
                                          "share": key, "on": "wheel"})  # fmt: skip
                    spec["members"].append({"family": "spoke", "half": half, "a": a, "b": a + 1, "width": width, "region": "end walls"})
                    radii.append(rad_out)
                spec["members"] = [m for k_m, m in enumerate(spec["members"]) if k_m not in drop]
                rim = float(np.median(radii))
                rho = np.hypot(px - c_[0], py - c_[1])
                on_rim = (np.abs(rho - rim) <= 0.5 * width) & (room > 0)
                # a full wheel's spokes ending on one circle the run filled at least 40 % of: production's rim
                if full and n >= 5 and float(np.std(radii)) < 8.0 and on_rim.any() and float(solid[on_rim].mean()) >= 0.4:
                    cells_ = np.argwhere(on_rim)
                    h0, top = run_height(cells_[:, 0], cells_[:, 1])
                    spec["rings"].append({"family": "ring rib", "half": half, "kind": "band", "centre": c_.tolist(), "r": rim,
                                          "r_range": [rim - 8.0, rim + 8.0], "width": width, "h": h0, "h_range": [0.0, top]})  # fmt: skip

        # a link between every two seats of the half along their line of centres, where the run's metal runs along it
        # (production's boss to boss: the gears' separating force)
        edt_all = distance_transform_edt(solid) * h
        for i_ in range(len(bosses)):
            for j_ in range(i_ + 1, len(bosses)):
                (ca, ra), (cb, rb) = bosses[i_], bosses[j_]
                d = cb - ca
                length = float(np.hypot(*d))
                if length <= ra + rb + 6.0:
                    continue
                u = d / length
                pa, pb = ca + ra * u, cb - rb * u
                fi, fj = cells_on(pa, pb)
                if solid[fi, fj].mean() < 0.5:
                    continue
                wide = float(np.median(2.0 * edt_all[fi, fj][solid[fi, fj]]))
                parallel(np.vstack([pa, pb]), wide, "link", "end walls")
                ab = pb - pa
                t_ = np.clip(((px - pa[0]) * ab[0] + (py - pa[1]) * ab[1]) / max(float(ab @ ab), 1e-9), 0.0, 1.0)
                taken |= np.hypot(px - (pa[0] + t_ * ab[0]), py - (pa[1] + t_ * ab[1])) <= 0.5 * max(wide, width) + 2.0
        # the rest of the half's metal, over the end walls and beside the side walls at once (a member crossing the wall's
        # line stays one), thinned to its skeleton
        foot = solid & ~taken
        foot = binary_opening(foot, np.ones((2, 2), bool)) | (foot & (hmap >= least + 4.0))
        lab, n_lab = cc_label(foot, np.ones((3, 3), int))
        for k in range(1, n_lab + 1):
            if (lab == k).sum() < 3:
                foot[lab == k] = False
        if foot.sum() >= 4:
            edt = distance_transform_edt(foot) * h
            skel = sk.prune(skeletonize(foot), prune_mm / h)
            branches, _ = sk.skeleton_graph(skel)
            for br in branches:
                cells = np.asarray(br, float)
                if len(cells) < 2:
                    continue
                poly = approximate_polygon(cells, tolerance=tol_mm / h)
                xy = lo[:2][None, :] + h * (poly + 0.5)
                if np.hypot(*(xy[-1] - xy[0])) < 6.0 and len(xy) <= 2:
                    continue
                # the metal's width along the branch: twice its distance to the footprint's edge
                ci = np.clip(cells[:, 0].astype(int), 0, n0 - 1)
                cj = np.clip(cells[:, 1].astype(int), 0, n1 - 1)
                wide = float(np.median(2.0 * edt[ci, cj]))
                if rich and gridded[int(np.median(ci)), int(np.median(cj))]:
                    continue  # its metal is already a grid's
                if rich and arc_of(xy, ci, cj):
                    continue
                if rich and wide > 2.0 * broad:  # broad metal as a grid, never one wide part
                    grid_patch(xy, wide, foot)
                    continue
                parallel(xy, wide, None, None)

        def place(nd: dict) -> np.ndarray:
            if nd["kind"] == "fixed":
                return np.asarray(nd["xy"], float)
            if nd["kind"] in ("circle", "spoke"):
                return np.asarray(nd["centre"]) + nd["r"] * np.array([math.cos(nd["angle"]), math.sin(nd["angle"])])
            if nd["kind"] == "edge":
                return along(half, nd["s"])[0]
            if nd["kind"] == "lattice":
                g = spec["grids"][nd["grid"]]
                u0 = float(g["angle"])
                e1, e2 = np.array([math.cos(u0), math.sin(u0)]), np.array([math.cos(u0 + math.pi / 3), math.sin(u0 + math.pi / 3)])
                return np.asarray(g["origin"], float) + float(g["pitch"]) * (nd["i"] * e1 + nd["j"] * e2)
            return np.asarray(nd["xy0"], float)

        if rich:
            wheels(place)

        # a member shorter than 6 mm is none (both ends snapped to one hard point)
        spec["members"] = [m for m in spec["members"] if m["half"] != half or np.hypot(*(place(spec["nodes"][m["b"]]) - place(spec["nodes"][m["a"]]))) >= 6.0]
        # every mount held: where no member reaches a mount, an arm from it to the nearest point of the outline (a mount
        # nothing reaches leaves the housing hanging on nothing: the mounts are where it is held)
        for q in mounts:
            reached = any(m["half"] == half and any(spec["nodes"][e].get("on") == "mount" and np.hypot(*(place(spec["nodes"][e]) - q)) < 1.0
                                                    for e in (m["a"], m["b"])) for m in spec["members"])  # fmt: skip
            if reached:
                continue
            s_, _ = nearest_on(edge, q)
            p_edge = along(half, s_)[0]
            parallel(np.vstack([q, p_edge]), width, "arm", "side walls")
        # every member's start heights and room, and its family
        at = {k: place(spec["nodes"][k]) for k in range(base, len(spec["nodes"]))}
        for m in spec["members"]:
            if m["half"] != half or "h" in m:
                continue
            a, b = at[m["a"]], at[m["b"]]
            s_ = np.linspace(0.0, 1.0, 13)
            line = a[None, :] + s_[:, None] * (b - a)[None, :]
            fi = np.clip(np.rint((line[:, 0] - lo[0]) / h - 0.5).astype(int), 0, n0 - 1)
            fj = np.clip(np.rint((line[:, 1] - lo[1]) / h - 0.5).astype(int), 0, n1 - 1)
            hv, rv = hmap[fi, fj], room[fi, fj]
            good = hv >= least

            def end_height(sel):
                v = hv[sel & good]
                if len(v):
                    return float(np.median(v))
                v = hv[good]
                return float(np.median(v)) if len(v) else least + 2.0

            top = float(np.percentile(rv[rv > 0], 90)) if (rv > 0).any() else band
            top = max(top, least + 2.0)
            m["h"] = [float(np.clip(end_height(s_ <= 0.34), least + 1.0, top)), float(np.clip(end_height(s_ >= 0.66), least + 1.0, top))]
            m["h_range"] = [0.0, top]
            at_mount = [k for k, nd in ((0, spec["nodes"][m["a"]]), (1, spec["nodes"][m["b"]])) if nd.get("on") == "mount"]
            if at_mount:  # an arm reaches its mount's eye: off the split down past the eye's far face, within its columns' room
                eye = next(mm for mm in lay["mounts"] if np.hypot(*(np.asarray(mm["centre"]) - at[m["a"] if at_mount[0] == 0 else m["b"]])) < 1.0)
                depth = (z_split - float(eye["z"][0])) if lower else (float(eye["z"][1]) - z_split)
                top = max(float(rv.max()) if len(rv) else band, least + 2.0)
                m["h_range"] = [0.0, top]
                m["h"] = [float(np.clip(max(v, depth + 2.0), least + 1.0, top)) for v in m["h"]]
            ka, kb = spec["nodes"][m["a"]], spec["nodes"][m["b"]]
            ends = {ka.get("on"), kb.get("on")}
            on_boss = [e for e in (ka.get("on"), kb.get("on")) if e and e.startswith("boss")]
            if "mount" in ends:
                fam = "arm"
            elif len(on_boss) == 2 and on_boss[0] != on_boss[1]:
                fam = "link"
            elif on_boss and "bolt" in ends:
                fam = "tie"
            elif on_boss and "outline" in ends:
                fam = "spoke"
            elif m["region"] == "side walls":
                u = (b - a) / max(np.hypot(*(b - a)), 1e-9)
                s_mid, _ = nearest_on(edge, 0.5 * (a + b))
                t_edge = along(half, s_mid)[1]
                fam = "gusset" if "bolt" in ends else ("belt" if abs(float(u @ t_edge)) > 0.7 else "fin")
            elif ends == {"outline"}:
                fam = "rim"
            elif on_boss:
                fam = "spoke"
            else:
                fam = "rib"
            m["family"] = m["family"] or fam
    # the checks: the parts' metal at their start against the run's
    pmap = pm.PartsMap(spec, centres, layer)
    x0 = pmap.start()
    hp = pmap.heights(x0)
    hp = np.minimum(hp, room_col)  # the parts gate their own heights (`parts.GATE`)
    for half, lay_id in pm.LAYER.items():
        on = layer == lay_id
        run_m, parts_m = float(metal_col[on].sum()), float(hp[on].sum())
        ii, jj = pts[on, 0].astype(int), pts[on, 1].astype(int)
        covered = np.zeros((n0, n1), bool)
        covered[ii[hp[on] > 0], jj[hp[on] > 0]] = True
        near = distance_transform_edt(~covered) * h <= 6.0
        run_near = float(metal_col[on][near[ii, jj]].sum())
        checks[half] = {"run metal cm3": round(run_m * h * h / 1e3, 1), "parts metal cm3": round(parts_m * h * h / 1e3, 1),
                        "mass ratio": round(parts_m / max(run_m, 1e-9), 3), "run metal within 6 mm of a part": round(run_near / max(run_m, 1e-9), 3),
                        "overlap": round(float(np.minimum(metal_col[on], hp[on]).sum()) / max(run_m, 1e-9), 3),
                        "members": sum(1 for m in spec["members"] if m["half"] == half), "rings": sum(1 for r in spec["rings"] if r["half"] == half),
                        "nodes": dict(zip(*np.unique([n["kind"] for n in spec["nodes"] if n["half"] == half], return_counts=True), strict=True))}  # fmt: skip
        checks[half]["nodes"] = {k: int(v) for k, v in checks[half]["nodes"].items()}
    fams = {}
    for m in spec["members"]:
        fams[m["family"]] = fams.get(m["family"], 0) + 1
    for r in spec["rings"]:
        fams[r["family"]] = fams.get(r["family"], 0) + 1
    checks["families"] = fams
    checks["variables"] = pmap.n_vars
    spec["checks"] = checks
    for m in spec["members"]:
        m.pop("region", None)
    (OUT / f"{label}.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    picture(label, spec, pmap, x0, metal_col, hp, pts, layer, lo, h, n0, n1)
    return spec


def picture(label, spec, pmap, x0, metal_col, hp, pts, layer, lo, h, n0, n1) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Circle, Patch, Wedge

    prm = pmap.params(x0)
    fig, axes = plt.subplots(2, 2, figsize=(17, 15))
    extent = [lo[0], lo[0] + n0 * h, lo[1], lo[1] + n1 * h]
    top = float(spec["band_mm"])
    for c_, (half, lay_id) in enumerate(pm.LAYER.items()):
        on = layer == lay_id
        ii, jj = pts[on, 0].astype(int), pts[on, 1].astype(int)
        for r_, (vals, title) in enumerate(((metal_col, "the free run's metal (mm off its base) under the parts"), (hp, "the parts' own metal at their start"))):
            ax = axes[r_, c_]
            m = np.full((n0, n1), np.nan)
            m[ii, jj] = vals[on]
            m[(m <= 0)] = np.nan
            im = ax.imshow(m.T, origin="lower", extent=extent, cmap="Greys" if r_ == 0 else "viridis", vmin=0, vmax=top, alpha=0.75 if r_ == 0 else 1.0)
            edge = np.asarray(spec["edges"][half])
            ax.plot(*np.vstack([edge, edge[:1]]).T, color="#999999", lw=0.8)
            if r_ == 0:
                polys, colours = [], []
                for mb in prm["members"]:
                    if mb["half"] != half:
                        continue
                    a, b = np.asarray(mb["ends"][0]), np.asarray(mb["ends"][1])
                    u = (b - a) / max(np.hypot(*(b - a)), 1e-9)
                    n_ = np.array([-u[1], u[0]]) * 0.5 * mb["width"]
                    polys.append([a + n_, b + n_, b - n_, a - n_])
                    colours.append(FAMILY_COLOUR.get(mb["family"], "#555555"))
                ax.add_collection(PolyCollection(polys, facecolors=colours, edgecolors="none", alpha=0.85))
                for rg_ in prm["rings"]:
                    if rg_["half"] != half:
                        continue
                    colour = FAMILY_COLOUR.get(rg_["family"], "#7f3b08")
                    if rg_["kind"] == "band":
                        ax.add_patch(Wedge(rg_["centre"], rg_["r"] + 0.5 * rg_["width"], 0, 360, width=rg_["width"], color=colour, alpha=0.6))
                    elif rg_["kind"] == "annulus":
                        ax.add_patch(Wedge(rg_["centre"], rg_["r"], 0, 360, width=rg_["r"] - rg_["r_in"], color=colour, alpha=0.6, lw=0))
                    elif rg_["kind"] == "arc":
                        ax.add_patch(Wedge(rg_["centre"], rg_["r"] + 0.5 * rg_["width"], math.degrees(rg_["a0"]), math.degrees(rg_["a1"]),
                                           width=rg_["width"], color=colour, alpha=0.8, lw=0))  # fmt: skip
                    elif rg_["kind"] == "web":
                        from matplotlib.patches import Polygon as _poly

                        g_ = np.linspace(-200.0, 200.0, 201)
                        gx_, gy_ = np.meshgrid(g_ + 0.5 * (rg_["centre"][0] + rg_["centre2"][0]), g_ + 0.5 * (rg_["centre"][1] + rg_["centre2"][1]))
                        sd_ = pm.uneven_capsule(np.column_stack([gx_.ravel(), gy_.ravel()]), np.asarray(rg_["centre"]), np.asarray(rg_["centre2"]),
                                                rg_["r1"], rg_["r2"]).reshape(gx_.shape)  # fmt: skip
                        ax.contourf(gx_, gy_, sd_, levels=[-1e9, 0.0], colors=[colour], alpha=0.4)
                        del _poly
                    else:
                        ax.add_patch(Circle(rg_["centre"], rg_["r"], color=colour, alpha=0.35, lw=0))
                        ax.add_patch(Circle(rg_["centre"], rg_["r"], fill=False, color=colour, lw=1.5))
                marks = {"fixed": ("s", "#000000"), "circle": ("^", "#7f3b08"), "edge": ("D", "#8c564b"), "free": ("o", "#ff7f0e"),
                         "spoke": ("v", "#2ca02c"), "lattice": (".", "#e6550d")}  # fmt: skip
                for nd in prm["nodes"]:
                    if nd["half"] != half:
                        continue
                    mk, col_ = marks.get(nd["kind"], ("o", "#ff7f0e"))
                    if nd["kind"] == "free" and nd.get("on") == "knot":
                        continue
                    ax.plot(*nd["at"], mk, color=col_, ms=4)
            ax.set_title(f"{label}, {half.replace('_', ' ')}: {title}", fontsize=10)
            ax.set_aspect("equal")
            fig.colorbar(im, ax=ax, shrink=0.6, label="mm")
    used = sorted({m["family"] for m in spec["members"]} | {r["family"] for r in spec["rings"]})
    handles = [Patch(color=FAMILY_COLOUR.get(f, "#555555"), label=f) for f in used]
    handles += [plt.Line2D([], [], marker=mk, color=c_, ls="", label=f"node: {k}") for k, (mk, c_) in
                {"fixed": ("s", "#000000"), "circle": ("^", "#7f3b08"), "edge": ("D", "#8c564b"), "free": ("o", "#ff7f0e")}.items()]  # fmt: skip
    fig.legend(handles=handles, loc="lower center", ncol=8, fontsize=10)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    target = OUT / f"{label}.png"
    fig.savefig(target, dpi=80)
    print(target)
    return target


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("--label", required=True)
    ap.add_argument("--width", type=float, default=8.0)
    ap.add_argument("--prune", type=float, default=12.0)
    ap.add_argument("--tol", type=float, default=4.0)
    ap.add_argument("--broad", type=float, default=16.0)
    ap.add_argument("--pitch", type=float, default=12.0)
    ap.add_argument("--rich", action="store_true", help="the richer library: wheels, grids, curved ribs (12 October 12:51)")
    a = ap.parse_args()
    out = read(a.run, a.label, a.width, a.prune, a.tol, a.broad, a.pitch, a.rich)
    print(json.dumps(out["checks"], indent=1))
