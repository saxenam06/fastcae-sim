"""PROTOTYPE (LOP-22) - an optimiser's field drawn as a designer draws a cast housing, in exact CAD:
the night of 11 October's second goal (the engineer, 00:20 and 01:26-01:38, after SEW's published
steps: "fit a smooth outer envelope over our members, trimmed by the flange plane and the end
faces; use our exact 4 mm wall as the pocket floors; use the members' centre-lines as rib paths,
each rib running from the wall up to the envelope, at most 12 mm thick; leave pockets between").

The field read in plan, half by half (it is cast along the pull from the split, so each column of
voxels holds one run of the metal the optimiser placed; `topo_free.py`'s route "split"):
1. **its members, two kinds:** where a column's placed metal stands `DEEP` or more past the frozen
   metal under it (the wall, the flange's land) or past the split, a deep rib or a web; where less,
   a pad, the wall thickened over an area. Read on a `FINE` grid, each 6 mm column its 3 × 3 cells,
   closed over a cell and blurred over one, so a diagonal of voxels that touch at their corners
   reads as one member (a blur over the coarse columns merged neighbouring members into blobs);
2. **the envelopes:** one smooth surface over the deep members' outer ends and one over the
   shallow ones' (on the columns' grid: the gaps filled from the nearest, smoothed over
   `ENVELOPE_SIGMA` voxels);
3. **the ribs:** the deep members' centre-lines (the plan skeleton's branches, small holes filled,
   spurs under `SPUR` cut), each one smooth spline, one thickness its members' own area over its
   length (`RIB`: 6 to 12 mm); each a plate topped by a ruled surface following the envelope along
   it, drawn only where it stands `RIB_LEAST` or more off the shell beneath (`base_of`), its free
   ends carried into what they meet, its sides kept `KEEP_OFF` off every upright cylinder of the
   shell and the cuts and joined to the shell's metal within `SLOT` (`keep_off`); a round post
   where branches meet, `POST` wider than its widest rib and `POST_PROUD` past its highest; a
   strut squarely into each mount the members reach (`mount_ties`);
4. **the pads:** the shallow members' outlines as polygons, flat-topped at their envelope's
   median, off the shell's face levels beneath;
5. **the pockets** are what is left between: down to the exact wall (`outcome_cad.exact_shell`:
   the contract's 4 mm wall, the split flange's land, the bolts' bosses, the mounts);
6. **every exact cut** (`exact_cuts`, as the mesh route makes them: the exits, the brackets'
   rooms, the bolts' sockets and holes, the inside, the bearings' bores and their paths in, the
   mounts' holes).
Exact B-rep, OCC's booleans a pair at a time, each checked by its volume (`union`), so it is the
CAD itself: `<stem>_<half>.brep` and `.step`, the record as `outcome_cad.py`'s B-rep drawings
write it, its body before the exact cuts as `<stem>_organic`, the reading in plan
(`<stem>_ribs.png`). FE reads its own mesh beside it (`mesh_body`: the parts filled on a 1.5 mm grid,
contoured, cut exact; the record's `files`); castability and the pictures read the B-rep (`brep`).
`--strengthen <shaft> <side> <reach mm> <raise mm>`: a design agent's move on a failing seat
(`STRENGTHEN`).

Run: .venv/Scripts/python.exe prototypes/first_loop/ribbed_cad.py <run stem> <design stem> [--strengthen ...]
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import cup as cupmod  # noqa: E402
import field_body as fb  # noqa: E402  (closed outlines as splines)
import grammar  # noqa: E402  (spline_strip, strip, say, OUT)
import outcome_cad as oc  # noqa: E402  (exact_shell, SOCKET, layout_of)
import shell as convex  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import cylinder  # noqa: E402

OUT = grammar.OUT
say = grammar.say
FINE = 2.0  # mm, the plan's grid: each 6 mm column its 3 x 3 cells
DEEP = 18.0  # mm, a column's placed metal this far past the frozen metal (or the split) is a rib's; less, a pad's
# LOOP_RIB_DEEP (mm) for a field within a height envelope (LOP-23, `topo_free.py --band`): its
# members stand at most the band proud, so at 18 mm nearly all of them would read as pads
DEEP = float(os.environ.get("LOOP_RIB_DEEP", DEEP))
RIB = (6.0, 12.0)  # mm, a rib's least and greatest thickness (12: the run's greatest member)
SPUR = 10.0  # mm, a branch of the centre-lines this short with a free end is cut
SMOOTH = 1.5  # mm, a rib's spline off its centre-line's cells (rms)
ENVELOPE_SIGMA = 0.5  # voxels, the envelopes' smoothing (1.0 lowered the tall members' tops, 04:50)
PAD_LEAST = 2.0  # cm², a pad's least area: smaller ones belong to the rib beside them
POST = 2.0  # mm, a post at a node is this much wider than the widest rib there
EXTEND = 3.0  # mm, a rib's free end carried on this far past half its thickness, into what its member meets
PAST_SPLIT = 2.0  # mm, the ribs and pads begin this far past the split's plane, and the half is cut flat there after
TIE_REACH = 12.0  # mm past a mount's boss: deep members this close to it are tied into it by a strut
HOLE_LEAST = 6.0  # cm², a gap in the deep members smaller than this is filled before their centre-lines are read (it ringed a node with a rib, 03:17)
# mm, FE's mesh's chord error: each part tessellated this finely and joined exactly (`mesh_body`);
# FE's coarsening keeps itself from folding the bare walls between the ribs (`mesh_route.coarse`).
# Tessellated at 0.3 mm the parts crossed themselves at the B-rep's slivers (03:55)
MESH_CHORD = 0.05
FE_VOXEL, FE_BLUR = 1.5, 1.0  # mm and cells: FE's body filled on this grid and contoured after this blur (`mesh_body`)
RIB_LEAST = 3.0  # mm, a rib is drawn only where its top stands this far off the shell under it
KEEP_OFF = 1.5  # mm, a rib's side, a post's rim and a pad's outline kept this far off any upright cylinder of the shell and the cuts
SLOT = 4.0  # mm, a gap of air narrower than this (the least wall) between a rib and the shell's metal is closed: the rib joins the metal
RUN_ON = 3.0  # mm, a rib's top surface run past its ends
POST_PROUD = 1.0  # mm, a post's top past the highest rib it joins
# A field within a height envelope (LOP-23, `topo_free.py --band`; its record's `band_mm`) is read by
# width, not depth: every member stands at most the band proud, so the depth rule read nearly all of
# it as ribs, and where the three wheels meet, webs 30 mm and more wide and up to 66 mm along the
# pull were drawn as one rib 12 mm thick, 25-30 mm off them: the CAD held half the optimiser's metal
# (outcome_cnet24_6.3kg, 11 October 10:35: 649 of 1,297 cm3). Members wider than `BROAD` (what a
# disc of that diameter fits in) are pads, drawn as terraces at the field's own column ends
# (`terraces`); the narrow rest are ribs along their centre-lines.
BROAD = 16.0  # mm
# a rib's least and greatest thickness within a height envelope: production's 0.8-1.0 x the wall
# outside (`docs/research/2026-10-09-production-housings-against-ours.md` §5.4), no thinner than
# the contract's 4 mm least wall (the engineer, 10:54: "we should use that only in that range")
RIB_BAND = (4.0, 5.0)
STRUT = 10.0  # mm, a strut into a mount at least: a lug, about 2·δ thick round its hole (§5.4), not a rib


def columns(run: str, half: str) -> dict:
    """The half's columns of placed metal: which hold it, its outer end along the pull, and how far
    it stands past the frozen metal under it (the wall, the land) or, with none, past the split."""
    z = np.load(OUT / f"{run}.npz")
    n, lo, h, ks = z["n"].astype(int), z["lo"].astype(float), float(z["h"]), int(z["k_split"])
    placed = np.zeros(int(np.prod(n)), bool)
    frozen = np.zeros(int(np.prod(n)), bool)
    placed[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    frozen[z["elem"][z["frozen"].astype(bool)]] = True
    placed, frozen = placed.reshape(n), frozen.reshape(n)
    placed &= ~frozen
    k = np.arange(n[2])[None, None, :]
    lower = half == "motor_side"
    side = (k < ks) if lower else (k >= ks)
    sel, fz = placed & side, frozen & side
    col = sel.any(axis=2)
    z_split = lo[2] + h * ks
    if lower:
        outer = np.where(col, lo[2] + h * np.where(sel, k, n[2]).min(axis=2), np.nan)
        base = np.where(fz.any(axis=2), lo[2] + h * np.where(fz, k, n[2]).min(axis=2), z_split)
        proud = base - outer
    else:
        outer = np.where(col, lo[2] + h * (np.where(sel, k, -1).max(axis=2) + 1), np.nan)
        base = np.where(fz.any(axis=2), lo[2] + h * (np.where(fz, k, -1).max(axis=2) + 1), z_split)
        proud = outer - base
    xs = lo[0] + h * (np.arange(n[0]) + 0.5)
    ys = lo[1] + h * (np.arange(n[1]) + 0.5)
    return {"col": col, "outer": outer, "proud": np.where(col, proud, np.nan), "xs": xs, "ys": ys, "h": h, "lo": lo, "z_split": z_split,
            "placed_kg": float(sel.sum()) * h**3}  # fmt: skip


def fine(mask6: np.ndarray, c: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A columns' mask on the `FINE` grid: each column its cells, closed over a cell (a diagonal of
    columns touching at their corners joins) and blurred over one, read at a half."""
    from scipy.ndimage import binary_closing, gaussian_filter

    r = int(round(c["h"] / FINE))
    m = np.kron(mask6.astype(np.uint8), np.ones((r, r), np.uint8)).astype(bool)
    m = binary_closing(np.pad(m, 2), structure=np.ones((3, 3), bool))[2:-2, 2:-2]
    m = gaussian_filter(m.astype(float), 1.0) >= 0.5
    xs = c["lo"][0] + FINE * (np.arange(m.shape[0]) + 0.5)
    ys = c["lo"][1] + FINE * (np.arange(m.shape[1]) + 0.5)
    return m, xs, ys


def centre_lines(mask: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> tuple[list[dict], list[dict]]:
    """The mask's plan skeleton as branches between nodes (a junction or a free end): each branch
    its cells in order, in mm, and the mask's half-width along it; spurs under `SPUR` cut."""
    from scipy.ndimage import distance_transform_edt, label
    from skimage.morphology import remove_small_holes, skeletonize

    mask = remove_small_holes(mask, max_size=int(HOLE_LEAST * 100.0 / FINE**2))
    dist = distance_transform_edt(mask) * FINE
    sk = skeletonize(mask)
    offsets = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0)]

    def neighbours(p, cells):
        return [(p[0] + di, p[1] + dj) for di, dj in offsets if (p[0] + di, p[1] + dj) in cells]

    cells = set(zip(*np.nonzero(sk), strict=True))
    for _ in range(3):  # spurs cut, then the branches traced again
        deg = {p: len(neighbours(p, cells)) for p in cells}
        junction = np.zeros(sk.shape, bool)
        for p, d in deg.items():
            if d >= 3:
                junction[p] = True
        lab, count = label(junction, structure=np.ones((3, 3), bool))
        node_of = {p: int(lab[p]) for p in cells if lab[p]}
        nodes = {i: [] for i in range(1, count + 1)}
        for p, i in node_of.items():
            nodes[i].append(p)
        free = [p for p, d in deg.items() if d <= 1]
        for p in free:
            count += 1
            node_of[p] = count
            nodes[count] = [p]
        branches, seen = [], set()
        for i, members in nodes.items():
            for p in members:
                for q in neighbours(p, cells):
                    if node_of.get(q) == i or (p, q) in seen:
                        continue
                    chain = [p, q]
                    seen.add((p, q))
                    prev, cur = p, q
                    while cur not in node_of:
                        nxt = [r for r in neighbours(cur, cells) if r != prev and r not in chain[-3:]]
                        if not nxt:
                            break
                        prev, cur = cur, nxt[0]
                        chain.append(cur)
                    seen.add((chain[-1], chain[-2]))
                    branches.append({"cells": chain, "ends": (i, node_of.get(chain[-1]))})
        # closed loops without a node (a ring round a bearing): traced from any cell
        loose = cells - {c_ for b in branches for c_ in b["cells"]} - set(node_of)
        while loose:
            start = next(iter(loose))
            chain, prev, cur = [start], None, start
            while True:
                nxt = [r for r in neighbours(cur, cells) if r != prev and r in loose and r not in chain]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                chain.append(cur)
            loose -= set(chain)
            if len(chain) > 3:
                branches.append({"cells": chain + [start], "ends": (None, None)})
        spurs = set()
        for b in branches:
            length = FINE * len(b["cells"])
            free_end = any(e is not None and len(nodes[e]) == 1 and e > len(nodes) - len(free) for e in b["ends"])
            if free_end and length < SPUR:
                spurs.update(c_ for c_ in b["cells"] if node_of.get(c_) is None or len(nodes[node_of[c_]]) == 1)
        if not spurs:
            break
        cells -= spurs
    out_branches, out_nodes = [], []
    for b in branches:
        ij = np.array(b["cells"], float)
        pts = np.column_stack([xs[0] + FINE * ij[:, 0], ys[0] + FINE * ij[:, 1]])
        half_w = np.array([dist[c_] for c_ in b["cells"]])
        out_branches.append({"points": pts, "half_width": half_w, "ends": b["ends"]})
    # each member cell the nearest branch's: a branch's own metal in plan, its area, from which its
    # rib's thickness is drawn (`rib_plates`: area over length). Drawn at the median half-width
    # along its centre-line, the cover's ribs were 6-8 mm where its members averaged 12 (150 cm2
    # over 124 cm), and the drawing came out 0.5 kg under the optimiser's metal, its tilt 1.13 x (04:50)
    if out_branches:
        from scipy.spatial import cKDTree

        owner = np.concatenate([np.full(len(b_["points"]), k) for k, b_ in enumerate(out_branches)])
        tree = cKDTree(np.vstack([b_["points"] for b_ in out_branches]))
        ci, cj = np.nonzero(mask)
        _, at = tree.query(np.column_stack([xs[0] + FINE * ci, ys[0] + FINE * cj]))
        area = np.bincount(owner[at], minlength=len(out_branches)) * FINE**2
        for k, b_ in enumerate(out_branches):
            b_["area"] = float(area[k])
    for i, members in nodes.items():
        ij = np.array(members, float).mean(axis=0)
        out_nodes.append({"id": i, "at": (float(xs[0] + FINE * ij[0]), float(ys[0] + FINE * ij[1])), "junction": len(members) > 1 or i <= count - len(free)})
    return out_branches, out_nodes


def smooth_path(points: np.ndarray) -> np.ndarray:
    """A branch's cells as one smooth spline through them (`SMOOTH` off them, rms), its two ends
    kept where they are, resampled about every 6 mm."""
    from scipy.interpolate import splev, splprep

    keep = np.concatenate([[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-6])
    pts = points[keep]
    length = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    if len(pts) < 4 or length < 8.0:
        return np.vstack([pts[0], pts[-1]])
    tck, _ = splprep(pts.T, s=len(pts) * SMOOTH**2, k=3)
    m = max(3, int(math.ceil(length / 6.0)) + 1)
    out = np.column_stack(splev(np.linspace(0.0, 1.0, m), tck))
    out[0], out[-1] = pts[0], pts[-1]
    return out


def envelope(c: dict, mask6: np.ndarray) -> np.ndarray:
    """One smooth surface over the outer ends of the columns in `mask6`, on the columns' grid: the
    gaps filled from the nearest, smoothed over `ENVELOPE_SIGMA` voxels. Each rib's top follows
    it along its path (`rib_plates`), each pad's top is its median (`pad_plates`); one B-spline of
    it over the whole half, its slab cutting every rib, grazed the shell's faces (03:25-03:41)."""
    from scipy.ndimage import distance_transform_edt, gaussian_filter

    height = np.where(mask6, c["outer"], np.nan)
    _, (ii, jj) = distance_transform_edt(~mask6, return_indices=True)
    return gaussian_filter(height[ii, jj], ENVELOPE_SIGMA)


def base_of(layout: dict, all_rooms: list[dict], half: str):
    """The half's exact shell's outer end along the pull over each point in plan, z (what a rib
    stands on): a room's end wall (its far end and the wall), the plate over the other half's
    opening, the split flange's land and the bolts' bosses, a mount's end, else the split."""
    s = layout["settings"]
    z_split, wall, t_f = layout["z"]["split"], s["wall"], s["flange_thickness"]
    lower = half == "motor_side"
    out = -1.0 if lower else 1.0
    pick = np.minimum if lower else np.maximum
    discs = [(p["axis"], p["r"] + wall, p["far"] + out * wall) for p in cupmod.pieces(all_rooms, z_split, half)]
    discs += [(p["axis"], p["r"] + wall, z_split + out * wall) for p in cupmod.pieces(all_rooms, z_split, "cover" if lower else "motor_side")]
    discs += [(c_["centre"], c_["radius"], z_split + out * t_f) for c_ in layout["flange"]["outer"]]
    discs += [(c_, s["bolt_boss"] / 2, z_split + out * t_f) for c_ in layout["bolts"]]
    discs += [(m["centre"], s["mount_diameter"] / 2, m["z"][0]) for m in layout["mounts"]] if lower else []

    def base(p: np.ndarray) -> np.ndarray:
        z = np.full(len(p), z_split)
        for centre, r, end in discs:
            inside = np.hypot(p[:, 0] - centre[0], p[:, 1] - centre[1]) <= r
            z = np.where(inside, pick(z, end), z)
        return z

    return base


def circles_of(layout: dict, all_rooms: list[dict], half: str) -> list[tuple[np.ndarray, float, bool]]:
    """Every upright cylinder of the half's exact shell and its exact cuts, in plan (centre,
    radius, whether metal is inside it): a rib's side, a post and a pad's outline are kept
    `KEEP_OFF` off each (CLAUDE.md's sliver rule: run along a cylinder, they left faces
    0.002-0.08 mm wide, 03:25-03:41), and close to the shell's metal they join it (`keep_off`)."""
    s = layout["settings"]
    z_split, wall = layout["z"]["split"], s["wall"]
    lower = half == "motor_side"
    metal, air = [], []
    for p in cupmod.pieces(all_rooms, z_split, half):
        metal.append((p["axis"], p["r"] + wall))
        air += [(p["axis"], p["r"]), (p["axis"], p["r"] - cupmod.STOCK)]
    metal += [(p["axis"], p["r"] + wall) for p in cupmod.pieces(all_rooms, z_split, "cover" if lower else "motor_side")]
    metal += [(c_["centre"], c_["radius"]) for c_ in layout["flange"]["outer"]]
    air += [(c_["centre"], c_["radius"]) for c_ in layout["flange"]["inner"]]
    for c_ in layout["bolts"]:
        metal.append((c_, s["bolt_boss"] / 2))
        air += [(c_, oc.SOCKET[0] / 2), (c_, s["bolt_hole"] / 2)]
    centre_of = {m["name"]: m["centre"] for m in layout["mounts"]}
    for m in layout["mounts"]:
        (metal if lower else air).append((m["centre"], s["mount_diameter"] / 2))
        air.append((m["centre"], s["mount_hole"] / 2))
    for b in layout.get("brackets") or []:
        air.append((b.get("centre") or centre_of[b["name"].split(" bracket")[0]], b["radius"]))
    air += [(e["centre"], e["radius"]) for e in layout.get("exits") or []]
    for b in layout["bearings"]:
        air += [(b["axis"], b["D"] / 2), (b["axis"], (b["D"] + 1.0) / 2)]
    return [(np.asarray(c_, float), float(r), True) for c_, r in metal] + [(np.asarray(c_, float), float(r), False) for c_, r in air]


def keep_off(points: np.ndarray, half_width: float, circles: list, tangent: np.ndarray | None = None) -> np.ndarray:
    """Points (a rib's centre-line, its sides `half_width` either side; a post's centre, its rim
    `half_width` out; an outline, 0) moved along each circle's radius so that no side runs within
    `KEEP_OFF` of the circle: where a side lies inside that band, the point is moved until the side
    stands `KEEP_OFF` off, on the side it was; and where a side stands outside the shell's metal by
    less than `SLOT`, it is moved into the metal by `KEEP_OFF`: kept off it, it left slots of air a
    millimetre or two wide beside the walls, which no sand fills and which forced TetGen's tets
    small (386,000 in the cover against flow B's 77,000, 04:27). A rib crossing a circle squarely
    is left as it is (`tangent` given: only where it runs along the circle, within 25°)."""
    p = points.copy()
    for centre, r, solid in circles:
        d_vec = p - centre
        d = np.linalg.norm(d_vec, axis=1)
        u = d_vec / np.maximum(d, 1e-9)[:, None]
        along = np.ones(len(p), bool) if tangent is None else np.abs(np.einsum("ij,ij->i", tangent, u)) < math.sin(math.radians(25.0))
        for side in ((-half_width, half_width) if half_width > 0 else (0.0,)):
            gap = d + side - r  # the side's distance off the circle, signed
            slot = solid & (side <= 0) & (gap >= 0) & (gap < SLOT)  # a narrow slot of air between the side and the metal
            near = along & (d > 1e-6) & (slot | (np.abs(gap) < KEEP_OFF))
            if near.any():
                move = np.where(slot, -KEEP_OFF - gap, np.where(gap >= 0, KEEP_OFF - gap, -KEEP_OFF - gap))
                p[near] += u[near] * move[near, None]
                d_vec = p - centre
                d = np.linalg.norm(d_vec, axis=1)
                u = d_vec / np.maximum(d, 1e-9)[:, None]
    return p


def sample(grid: np.ndarray, c: dict, p: np.ndarray) -> np.ndarray:
    """A grid over the columns (`c`'s xs, ys) read at points in plan, bilinear."""
    from scipy.ndimage import map_coordinates

    return map_coordinates(grid, [(p[:, 0] - c["xs"][0]) / c["h"], (p[:, 1] - c["ys"][0]) / c["h"]], order=1, mode="nearest")


def refair(p: np.ndarray, rms: float = 0.4) -> np.ndarray:
    """Points refaired by a smoothing spline through them (`rms` mm off them), their ends kept."""
    from scipy.interpolate import splev, splprep

    if len(p) < 4:
        return p
    keep = np.concatenate([[True], np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-6])
    q = p[keep]
    if len(q) < 4:
        return p
    tck, u = splprep(q.T, s=len(q) * rms**2, k=3)
    out = np.column_stack(splev(u, tck))
    out[0], out[-1] = q[0], q[-1]
    return out if len(out) == len(p) else p


def tangents(p: np.ndarray) -> np.ndarray:
    t = np.gradient(p, axis=0)
    return t / np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]


def plate(path: np.ndarray, top: np.ndarray, w: float, z0: float, z1: float, out: float) -> cq.Shape:
    """A rib: a plate `w` thick along the path in plan, from z0 to z1, its top one ruled surface
    through the heights `top` along it (square across the rib), run `RUN_ON` past both ends so
    that no face of the cut lies in the plate's ends."""
    t0 = (path[0] - path[1]) / max(float(np.linalg.norm(path[0] - path[1])), 1e-9)
    t1 = (path[-1] - path[-2]) / max(float(np.linalg.norm(path[-1] - path[-2])), 1e-9)
    ext = np.vstack([path[0] + t0 * RUN_ON, path, path[-1] + t1 * RUN_ON])
    zt = np.concatenate([[top[0]], top, [top[-1]]])
    n = tangents(ext)[:, ::-1] * np.array([-1.0, 1.0])
    reach = w / 2 + 2.0
    left = [cq.Vector(float(x), float(y), float(z)) for (x, y), z in zip(ext + n * reach, zt, strict=True)]
    right = [cq.Vector(float(x), float(y), float(z)) for (x, y), z in zip(ext - n * reach, zt, strict=True)]
    roof = cq.Face.makeRuledSurface(cq.Edge.makeSpline(left), cq.Edge.makeSpline(right))
    span = float(np.max(np.abs(zt - (z0 if out > 0 else z1)))) + 10.0
    slab = cq.Solid.extrudeLinear(roof, cq.Vector(0.0, 0.0, -out * span))
    prism = grammar.spline_strip(path, w, z0, z1) if len(path) > 2 else grammar.strip(path[0], path[-1], w, z0, z1)[0]
    return prism.intersect(slab)


# A design agent's move on a failing seat (`--strengthen <shaft> <side> <reach mm> <raise mm>`; 11
# October 05:30: flow C's intermediate -z seat tilted 1.20 x its line, flow B's organic members there
# 0.70 x): every rib within the reach of the seat's axis, in its half, drawn at the greatest thickness
# and raised, every pad there raised. Set by `build`: {shaft, side, axis, near, raise, cap, out}.
STRENGTHEN: dict | None = None


def strengthened(out: float) -> bool:
    """Whether the strengthening applies in the half drawn outward along `out`."""
    return STRENGTHEN is not None and STRENGTHEN["out"] == out


def rib_plates(branches: list[dict], nodes: list[dict], c: dict, top_grid: np.ndarray, base, circles: list, z0: float, z1: float,
               out: float) -> tuple[list[cq.Shape], list[dict]]:  # fmt: skip
    """Each branch a plate of its own thickness along its spline (`plate`), its top on the
    envelope along it, drawn only where it stands `RIB_LEAST` or more off the shell under it
    (lower, its top grazed the shell's faces: slivers at the land's top and the end walls',
    03:25-03:41); its free ends carried on `EXTEND` past half its thickness (a centre-line stops
    that short of what its member meets: the wall, a mount's boss, 03:26); its sides kept off the
    shell's and the cuts' cylinders (`keep_off`). A round post where branches meet, `POST` wider
    than the widest rib there, topped `POST_PROUD` past the highest of them (level with one, their
    tops met in a sliver)."""
    junctions = {nd["id"] for nd in nodes if nd["junction"]}
    solids, ribs, at_node = [], [], {}
    for b in branches:
        length_b = float(np.linalg.norm(np.diff(b["points"], axis=0), axis=1).sum())
        w = float(np.clip(b.get("area", 0.0) / max(length_b, FINE), *RIB)) if b.get("area") else float(np.clip(2 * np.median(b["half_width"]), *RIB))
        w = round(w * 2) / 2
        if strengthened(out) and float(np.min(np.linalg.norm(b["points"] - STRENGTHEN["axis"], axis=1))) <= STRENGTHEN["near"]:
            w = RIB[1]  # a rib round the seat strengthened: the greatest thickness
        path = smooth_path(b["points"])
        for end, e in zip((0, -1), b["ends"], strict=True):
            if e in junctions:
                continue
            tip, back = path[end], path[1 if end == 0 else -2]
            t = (tip - back) / max(float(np.linalg.norm(tip - back)), 1e-9)
            path = np.vstack([tip + t * (w / 2 + EXTEND), path]) if end == 0 else np.vstack([path, tip + t * (w / 2 + EXTEND)])
        # the path at about 3 mm, kept off the cylinders, its height off the shell under it
        length = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
        s_ = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
        m = max(2, int(math.ceil(length / 3.0)) + 1)
        fine_path = np.column_stack([np.interp(np.linspace(0, length, m), s_, path[:, k]) for k in (0, 1)])
        fine_path = keep_off(fine_path, w / 2, circles, tangents(fine_path))
        env = sample(top_grid, c, fine_path)
        under = base(fine_path)
        high = out * (env - under) >= RIB_LEAST
        # each run of the path standing high enough is a rib of its own
        edges = np.flatnonzero(np.diff(np.concatenate([[0], high.astype(int), [0]])))
        for a, z_ in zip(edges[::2], edges[1::2], strict=True):
            piece = fine_path[a:z_]
            if len(piece) < 2 or float(np.linalg.norm(np.diff(piece, axis=0), axis=1).sum()) < SPUR:
                continue
            top = np.convolve(np.pad(env[a:z_], 2, mode="edge"), np.ones(5) / 5, mode="valid")  # fair along it, over 15 mm
            top = under[a:z_] + out * np.maximum(out * (top - under[a:z_]), RIB_LEAST)
            if strengthened(out):  # raised round the seat, falling off over 20 mm, never past the half's farthest member
                d = np.linalg.norm(fine_path[a:z_] - STRENGTHEN["axis"], axis=1)
                lift = STRENGTHEN["raise"] * np.clip((STRENGTHEN["near"] - d) / 20.0, 0.0, 1.0)
                top = top + out * lift
                top = np.minimum(top, STRENGTHEN["cap"]) if out > 0 else np.maximum(top, STRENGTHEN["cap"])
            # drawn through every second point (6 mm), refaired a little: the keep-off moves left
            # kinks, and the strip's offset splines looped there (11 of 29 ribs refused, 04:15)
            pick_ = np.unique(np.concatenate([np.arange(0, len(piece), 2), [len(piece) - 1]]))
            piece, top = refair(piece[pick_]), top[pick_]
            try:
                solid = plate(piece, top, w, z0, z1, out)
                if not solid.isValid() or solid.Volume() <= 0:
                    raise ValueError("not valid")
            except Exception as e:  # noqa: BLE001 - a rib OCC refuses is left out, said
                say(f"  a rib of {len(piece)} points refused ({e})")
                continue
            solids.append(solid)
            ribs.append({"points": [[round(float(x), 2), round(float(y), 2)] for x, y in piece[:: max(1, len(piece) // 12)]], "width": w,
                         "length": float(np.linalg.norm(np.diff(piece, axis=0), axis=1).sum()), "top": [round(float(top.min()), 1), round(float(top.max()), 1)]})  # fmt: skip
            for end, e in ((0, b["ends"][0]), (-1, b["ends"][1])):
                if e in junctions and ((end == 0 and a == 0) or (end == -1 and z_ == len(fine_path))):
                    at_node.setdefault(e, []).append((w, float(top[end])))
    pick = max if out > 0 else min
    for nd in nodes:
        if nd["id"] not in at_node:
            continue
        w_most = max(w for w, _ in at_node[nd["id"]])
        d_post = w_most + POST
        centre = keep_off(np.asarray([nd["at"]], float), d_post / 2, circles)[0]
        z_top = pick(z for _, z in at_node[nd["id"]]) + out * POST_PROUD
        solids.append(cylinder(tuple(centre), *(sorted((z0, z_top)) if out > 0 else sorted((z_top, z1))), d_post))
    return solids, ribs


def mount_ties(ribs: list[dict], deep: np.ndarray, xs: np.ndarray, ys: np.ndarray, layout: dict, circles: list, z_split: float) -> tuple[list[cq.Shape], list[dict]]:
    """A strut squarely into each mount the deep members reach (cells within `TIE_REACH` of its
    boss): straight from the nearest point of a rib's spline to the mount's centre, that rib's
    thickness, the mount's height (from its far end to the split), with a post where it leaves the
    rib. The members meet a mount at its side, and their centre-line runs half their thickness
    off it: mount-3's ring rib only grazed its boss, and the boss was dropped with the loose
    pieces (03:38)."""
    r_m = layout["settings"]["mount_diameter"] / 2
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    solids, ties = [], []
    for m in layout["mounts"]:
        c = np.asarray(m["centre"], float)
        if not (deep & (np.hypot(X - c[0], Y - c[1]) <= r_m + TIE_REACH)).any() or not ribs:
            continue
        d, p, w = min(((float(np.linalg.norm(np.asarray(q) - c)), tuple(q), r["width"]) for r in ribs for q in r["points"]), key=lambda t: t[0])
        if d > r_m + TIE_REACH + 12.0:
            continue
        w = max(w, STRUT)  # a lug, not a rib
        z0, z1 = m["z"][0], z_split + PAST_SPLIT
        p = tuple(keep_off(np.asarray([p], float), (w + POST) / 2, circles)[0])
        solids.append(grammar.strip(p, tuple(c), w, z0, z1)[0])
        solids.append(cylinder(p, z0, z1, w + POST))
        ties.append({"mount": m["name"], "from": [round(p[0], 2), round(p[1], 2)], "width": w, "length": d})
    return solids, ties


def simplified(loop: np.ndarray, tol: float = 0.6) -> np.ndarray:
    """A closed polygon with the points it can lose within `tol` mm dropped (Ramer-Douglas-Peucker,
    on the loop cut at its two farthest points), at least 8 kept."""

    def rdp(p: np.ndarray) -> np.ndarray:
        if len(p) < 3:
            return p
        a, b = p[0], p[-1]
        d = b - a
        norm = float(np.hypot(*d))
        dist = np.hypot(*(p - a).T) if norm < 1e-12 else np.abs(d[0] * (p[:, 1] - a[1]) - d[1] * (p[:, 0] - a[0])) / norm
        i = int(np.argmax(dist))
        if dist[i] <= tol:
            return np.vstack([a, b])
        return np.vstack([rdp(p[: i + 1])[:-1], rdp(p[i:])])

    if len(loop) < 8:
        return loop
    j = int(np.argmax(np.hypot(*(loop - loop[0]).T)))
    out = np.vstack([rdp(np.vstack([loop[: j + 1]]))[:-1], rdp(np.vstack([loop[j:], loop[:1]]))[:-1]])
    return out if len(out) >= 8 else loop


def crosses(loop: np.ndarray) -> bool:
    """Whether a closed polygon's edges cross one another (beyond neighbours)."""
    a, b = loop, np.roll(loop, -1, axis=0)
    n = len(loop)
    for i in range(n):
        p, r = a[i], b[i] - a[i]
        q, s = a[i + 2 :], b[i + 2 :] - a[i + 2 :]
        if i == 0:
            q, s = q[:-1], s[:-1]  # the last edge shares the first's start
        if not len(q):
            continue
        rxs = r[0] * s[:, 1] - r[1] * s[:, 0]
        qp = q - p
        ok = np.abs(rxs) > 1e-12
        t = np.where(ok, (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / np.where(ok, rxs, 1.0), -1.0)
        u = np.where(ok, (qp[:, 0] * r[1] - qp[:, 1] * r[0]) / np.where(ok, rxs, 1.0), -1.0)
        if np.any(ok & (t > 1e-9) & (t < 1 - 1e-9) & (u > 1e-9) & (u < 1 - 1e-9)):
            return True
    return False


def pad_plates(mask: np.ndarray, xs: np.ndarray, ys: np.ndarray, c: dict, top_grid: np.ndarray, base, circles: list, z0: float, z1: float,
               out: float, level: float | None = None) -> list[cq.Shape]:  # fmt: skip
    """The pads: each smoothed outline (with its holes), kept off the cylinders (`keep_off`), a
    prism up to one flat top, the median of its envelope, at least `RIB_LEAST` off the shell
    under it and `KEEP_OFF` off any of the shell's faces beneath it (one envelope over all of
    them grazed the land's top and the end walls', 03:25-03:41). With `level`, every pad's top is
    there (a terrace, `terraces`). An outline that the resampling or the keep-off made cross itself
    is taken as traced (left out, the cover's 43 cm2 pad was lost, 09:13)."""
    from matplotlib.path import Path as Polygon
    from scipy.ndimage import gaussian_filter

    def area_of(loop: np.ndarray) -> float:
        return 0.5 * abs(float(np.dot(loop[:, 0], np.roll(loop[:, 1], 1)) - np.dot(loop[:, 1], np.roll(loop[:, 0], 1))))

    X, Y = np.meshgrid(xs, ys, indexing="ij")
    plan = np.column_stack([X.ravel(), Y.ravel()])
    solids = []
    # the outlines as traced (they never cross themselves), simplified below where that stays so:
    # resampled at 4 mm they cut across narrow necks, and a boss's 89 cm2 terrace was left out (11:38)
    for outer, holes in fb.loops(gaussian_filter(mask.astype(float), 1.0), xs, ys, 0.5, step=None):
        area = area_of(outer)
        if area < PAD_LEAST * 100.0:
            continue
        kept_outer = keep_off(outer, 0.0, circles)
        kept_holes = [keep_off(hl, 0.0, circles) for hl in holes]
        if not crosses(kept_outer) and not any(crosses(hl) for hl in kept_holes):
            outer, holes = kept_outer, kept_holes
        # fewer points where the outline runs straight (each point a face of the prism: the cover's
        # terraces made a half of 7,756 faces whose cuts took minutes, 10:44), never so it crosses
        simple = [simplified(loop) for loop in [outer, *holes]]
        if not any(crosses(loop) for loop in simple):
            outer, holes = simple[0], simple[1:]
        inside = Polygon(outer).contains_points(plan).reshape(X.shape) & mask
        if not inside.any():
            continue
        pts = np.column_stack([X[inside], Y[inside]])
        under = base(pts)
        if level is None:
            rise = float(np.median(out * (sample(top_grid, c, pts) - under)))
        else:  # a terrace is kept where any of it stands proud: one over a room's end wall and the land beside it (two bases) was judged by the deeper and dropped (11:35)
            rise = float(np.max(out * (level - under)))
        if rise < RIB_LEAST:
            continue
        z_top = float(np.median(under)) + out * rise if level is None else float(level)
        if strengthened(out) and float(np.min(np.linalg.norm(pts - STRENGTHEN["axis"], axis=1))) <= STRENGTHEN["near"]:
            z_top += out * STRENGTHEN["raise"]  # a pad round the strengthened seat raised
            z_top = min(z_top, STRENGTHEN["cap"]) if out > 0 else max(z_top, STRENGTHEN["cap"])
        for level in np.unique(np.round(under, 2)):  # never level with a face of the shell beneath it
            if abs(z_top - level) < KEEP_OFF:
                z_top = level + (KEEP_OFF if z_top >= level else -KEEP_OFF)
        lo, hi = (z0, z_top) if out > 0 else (z_top, z1)

        def ring(loop: np.ndarray, lo: float = lo) -> cq.Wire:
            return cq.Wire.makePolygon([cq.Vector(float(x), float(y), lo) for x, y in loop], close=True)

        # Each outline a polygon (the contour's points, about 4 mm apart), not a spline through
        # them: the spline crossed itself at narrow necks, and the cover's 34 cm2 pad over its
        # output lobe's end wall was left out, its seat's tilt then 1.30 x its line (04:41)
        try:
            face = cq.Face.makeFromWires(ring(outer), [ring(hl) for hl in holes])
            solid = cq.Solid.extrudeLinear(face, cq.Vector(0.0, 0.0, hi - lo))
        except Exception:  # noqa: BLE001 - an outline OCC refuses is left out, said
            say(f"  a pad's outline of {len(outer)} points refused")
            continue
        expected = (area_of(outer) - sum(area_of(hl) for hl in holes)) * (hi - lo)
        if not solid.isValid() or abs(solid.Volume() - expected) > 0.02 * expected:
            say(f"  a pad of {area / 100:.1f} cm2 left out: its outline crosses itself (valid {solid.isValid()}, {solid.Volume() / 1e3:.1f} cm3 against {expected / 1e3:.1f})")
            continue
        solids.append(solid)
    return solids


RING_STEP = 4.0  # mm: a boss's annuli whose ends lie within this of each other are one ring (`boss_rings`)
RING_COVER = 0.6  # an annulus is a ring's when the field's metal goes round this share of it


def boss_rings(pieces: list[dict], c: dict, metal: np.ndarray, base, z0: float, z1: float, out: float) -> tuple[list[cq.Shape], dict]:
    """Each bore's boss as concentric exact rings, as a designer draws one: of the network's annuli
    round the bore (`rib_network`'s, a voxel wide), those the field's metal goes `RING_COVER` of the
    way round, kept where any of their columns stands `RIB_LEAST` proud of its own base, and grouped
    outward while each next annulus's end (its columns' median) lies within `RING_STEP` of the last;
    each group one ring from its end to the split, flat-topped, 0.5 mm past its radii either side so
    that no two rings' faces coincide. Returns the rings and {"rings": records, "pieces": the indices
    of the annuli drawn}; the others are drawn as arc plates (`network_parts`)."""
    h, xs, ys = c["h"], c["xs"], c["ys"]
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    by_bore: dict[tuple[float, float], list] = {}
    for k, p in enumerate(pieces):
        if p["shape"][0] != "annulus":
            continue
        _, cx, cy, r0, r1 = p["shape"]
        own = p["own"] & metal
        mine = int(p["mask"].sum())
        if not own.any() or mine == 0 or own.sum() < RING_COVER * mine:
            continue
        end = float(np.median(c["outer"][own]))
        pts = np.column_stack([X[own], Y[own]])
        if float(np.max(out * (end - base(pts)))) < RIB_LEAST:
            continue
        by_bore.setdefault((float(cx), float(cy)), []).append((float(r0), float(r1), end, k))
    solids, rings, done = [], [], set()
    for (cx, cy), anns in by_bore.items():
        anns.sort()
        groups: list[list] = []
        for a in anns:
            last = groups[-1][-1] if groups else None
            if last is not None and a[0] <= last[1] + 1e-6 and abs(a[2] - last[2]) <= RING_STEP:
                groups[-1].append(a)
            else:
                groups.append([a])
        for g in groups:
            r_in, r_out = g[0][0], g[-1][1]
            end = float(np.median([a[2] for a in g]))
            lo_, hi_ = (z0, end) if out > 0 else (end, z1)
            ring = cylinder((cx, cy), lo_, hi_, 2 * (r_out + 0.5))
            if r_in > 0.6:
                ring = ring.cut(cylinder((cx, cy), lo_ - 1.0, hi_ + 1.0, 2 * (r_in - 0.5)))
            if not ring.isValid() or ring.Volume() <= 0:
                continue
            solids.append(ring)
            rings.append({"centre": [round(cx, 1), round(cy, 1)], "r": [round(r_in, 1), round(r_out, 1)], "top": [round(end, 1), round(end, 1)],
                          "width": round(r_out - r_in, 1), "length": float(np.pi * (r_in + r_out)),
                          "points": [[round(cx + 0.5 * (r_in + r_out) * math.cos(t_), 2), round(cy + 0.5 * (r_in + r_out) * math.sin(t_), 2)] for t_ in np.linspace(0, 2 * np.pi, 13)]})  # fmt: skip
            done.update(a[3] for a in g)
    return solids, {"rings": rings, "pieces": done}


def network_parts(net: dict, half: str, c: dict, base, circles: list, z0: float, z1: float, out: float, layout: dict) -> tuple[list[cq.Shape], list[dict], list[dict]]:
    """A run optimised on production's rib network (`topo_free.py --ribs`) drawn from the network's own
    pieces, not read back from its voxels (LOP-23, 11 October 11:30): every piece the optimiser put
    metal on (`network_draw.pieces`, each column of metal one piece's) is one exact feature. A spoke,
    a link, a gusset, a fin or a ridge's square is a plate along its own straight line, a ring's arc a
    plate along the arc, `RIB` thick, over the stretch its metal covers, its top on the field's column
    ends along it (the nearest of its own columns, faired over 15 mm), at least `RIB_LEAST` proud of
    the shell under it; a boss's annulus a flat-topped ring where its metal goes most of the way round,
    else a plate along its arc. Read through skeletons and contours, the 4 mm network field lost 1.9
    kg of its 7.0 and two mounts (11:23). Every mount gets a strut to the shell (`network_struts`).
    Returns the solids, the ribs (for the record) and the struts."""
    from scipy.ndimage import distance_transform_edt

    h, xs, ys = c["h"], c["xs"], c["ys"]
    metal = c["col"] & (np.nan_to_num(c["proud"]) >= RIB_LEAST)
    solids, ribs = [], []
    # Each bore's boss as concentric exact rings (`boss_rings`): the annuli the field filled most of
    # the way round, grouped while their ends stay within `RING_STEP` of each other, each group one
    # flat-topped ring; the rest drawn as arc plates below. One ring an annulus at its columns' median
    # end, judged by the median of two bases (its room's end wall and the land beside it), was dropped
    # (outcome_prodc24_4mm_7.0kg, 11:35: beds 326 µm); as terraces at 4 mm voxels, the deeper ones
    # eroded away (11:51: the motor side kept 216 of 780 cm3)
    ring_solids, ring_done = boss_rings(net[half], c, metal, base, z0, z1, out)
    solids += ring_solids
    ribs += [{"kind": "boss ring", **r_} for r_ in ring_done["rings"]]
    for k_, p in enumerate(net[half]):
        own = p["own"] & metal
        if not own.any() or k_ in ring_done["pieces"]:
            continue
        kind = p["shape"][0]
        ii, jj = np.nonzero(own)
        pts = np.column_stack([xs[ii], ys[jj]])
        # each point in plan takes its nearest own column's end
        _, (ni, nj) = distance_transform_edt(~own, return_indices=True)
        ends = c["outer"][ni, nj]
        near = distance_transform_edt(~own) * h <= 0.75 * h

        def column_end(q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            gi = np.clip(np.round((q[:, 0] - xs[0]) / h).astype(int), 0, own.shape[0] - 1)
            gj = np.clip(np.round((q[:, 1] - ys[0]) / h).astype(int), 0, own.shape[1] - 1)
            return ends[gi, gj], near[gi, gj]

        if kind == "annulus":  # an annulus the field filled only partly (the rest are `boss_rings`): a plate along the arc its metal covers
            _, cx, cy, r0, r1 = p["shape"]
            ang = np.sort(np.mod(np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx), 2 * np.pi))
            gaps = np.diff(np.concatenate([ang, [ang[0] + 2 * np.pi]]))
            k = int(np.argmax(gaps))  # the arc its metal covers: from after the widest gap round to it
            a_start, span = ang[(k + 1) % len(ang)], 2 * np.pi - float(gaps[k])
            rr, w = 0.5 * (r0 + r1), (r1 - r0) + 1.0
            m = max(3, int(math.ceil(rr * span / 3.0)) + 1)
            a_s = a_start + np.linspace(-0.5 * h / max(rr, h), span + 0.5 * h / max(rr, h), m)
            path = np.column_stack([cx + rr * np.cos(a_s), cy + rr * np.sin(a_s)])
        elif kind == "arc":
            _, cx, cy, rr, a0, a1 = p["shape"]
            ang = np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx)
            lo_a, hi_a = float(ang.min()) - 0.5 * h / rr, float(ang.max()) + 0.5 * h / rr
            m = max(3, int(math.ceil(rr * (hi_a - lo_a) / 3.0)) + 1)
            a_s = np.linspace(lo_a, hi_a, m)
            path, w = np.column_stack([cx + rr * np.cos(a_s), cy + rr * np.sin(a_s)]), None
        else:
            if kind == "segment":
                a, b = np.asarray(p["shape"][1], float), np.asarray(p["shape"][2], float)
            else:  # a square of cells: the straight line through them
                ctr = pts.mean(axis=0)
                if len(pts) < 2:
                    continue
                _, _, vt = np.linalg.svd(pts - ctr, full_matrices=False)
                s_ = (pts - ctr) @ vt[0]
                a, b = ctr + s_.min() * vt[0], ctr + s_.max() * vt[0]
            d = b - a
            length = float(np.hypot(*d))
            if length < 1e-6:
                continue
            u = d / length
            t = (pts - a) @ u  # the stretch its own metal covers along the line
            t0, t1 = float(t.min()) - 0.5 * h, float(t.max()) + 0.5 * h
            m = max(2, int(math.ceil((t1 - t0) / 3.0)) + 1)
            path, w = a + np.linspace(t0, t1, m)[:, None] * u, None
        if w is None:  # a rib: its own metal's area over its length, within production's range
            run_len = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()) + 1e-9
            w = float(np.clip(own.sum() * h * h / run_len, *RIB))
            w = round(w * 2) / 2
        path = keep_off(path, w / 2, circles, tangents(path))
        env, covered = column_end(path)
        under = base(path)
        high = covered & (out * (env - under) >= RIB_LEAST)
        edges = np.flatnonzero(np.diff(np.concatenate([[0], high.astype(int), [0]])))
        for s0, s1 in zip(edges[::2], edges[1::2], strict=True):
            piece = path[s0:s1]
            if len(piece) < 2 or float(np.linalg.norm(np.diff(piece, axis=0), axis=1).sum()) < 2.0 * h:
                continue
            top = np.convolve(np.pad(env[s0:s1], 2, mode="edge"), np.ones(5) / 5, mode="valid")
            top = under[s0:s1] + out * np.maximum(out * (top - under[s0:s1]), RIB_LEAST)
            pick_ = np.unique(np.concatenate([np.arange(0, len(piece), 2), [len(piece) - 1]]))
            piece, top = refair(piece[pick_]), top[pick_]
            try:
                solid = plate(piece, top, w, z0, z1, out)
                if not solid.isValid() or solid.Volume() <= 0:
                    raise ValueError("not valid")
            except Exception as e:  # noqa: BLE001 - a piece OCC refuses is left out, said
                say(f"  a {kind} of {len(piece)} points refused ({e})")
                continue
            solids.append(solid)
            ribs.append({"kind": kind, "points": [[round(float(x), 2), round(float(y), 2)] for x, y in piece[:: max(1, len(piece) // 12)]], "width": w,
                         "length": float(np.linalg.norm(np.diff(piece, axis=0), axis=1).sum()), "top": [round(float(top.min()), 1), round(float(top.max()), 1)]})  # fmt: skip
    return solids, ribs, []


def network_struts(layout: dict, all_rooms: list[dict], half: str, circles: list, z_split: float) -> tuple[list[cq.Shape], list[dict]]:
    """A strut from each mount to the shell (the motor side's: the mounts are its): straight from the
    mount's centre to the nearest point of the half's outside in plan (the rooms' discs grown by the
    wall), 3 mm into it, `STRUT` thick, from the mount's far end to past the split, and a post where
    it meets the wall. Only where ribs reached a mount had one been drawn (`mount_ties`), and two of
    three mounts came off (11:23)."""
    if half != "motor_side":
        return [], []
    wall = layout["settings"]["wall"]
    discs = [(np.asarray(p["axis"], float), p["r"] + wall) for p in cupmod.pieces(all_rooms, z_split, half)]
    solids, ties = [], []
    for m in layout["mounts"]:
        c = np.asarray(m["centre"], float)
        best = None
        for centre, r in discs:
            v = c - centre
            dist = float(np.hypot(*v))
            if dist < 1e-6:
                continue
            q = centre + v / dist * (r - 3.0)  # 3 mm into the wall
            if best is None or dist - r < best[0]:
                best = (dist - r, q)
        if best is None:
            continue
        q = tuple(keep_off(np.asarray([best[1]], float), (STRUT + POST) / 2, circles)[0])
        z0, z1 = m["z"][0], z_split + PAST_SPLIT
        solids.append(grammar.strip(q, tuple(c), STRUT, z0, z1)[0])
        solids.append(cylinder(q, z0, z1, STRUT + POST))
        ties.append({"mount": m["name"], "from": [round(q[0], 2), round(q[1], 2)], "width": STRUT, "length": round(best[0] + 3.0, 1)})
    return solids, ties


def by_width(c: dict) -> tuple[np.ndarray, np.ndarray]:
    """A field within a height envelope read by width (`BROAD`): its columns of placed metal standing
    `RIB_LEAST` or more proud split into the broad ones (in a member wider than `BROAD`: what a disc
    of that diameter, rolled through the member in plan, covers) and the narrow rest. Returns the
    two column masks (broad, narrow)."""
    from scipy.ndimage import binary_opening

    every = c["col"] & (np.nan_to_num(c["proud"]) >= RIB_LEAST)
    m, _, _ = fine(every, c)
    r = int(round(BROAD / 2 / FINE))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    broad_fine = binary_opening(m, structure=(xx**2 + yy**2) <= r * r)
    k = int(round(c["h"] / FINE))
    nx, ny = every.shape
    share = broad_fine[: nx * k, : ny * k].reshape(nx, k, ny, k).mean(axis=(1, 3))
    broad = every & (share >= 0.5)
    return broad, every & ~broad


def terraces(broad: np.ndarray, c: dict, base, circles: list, z0: float, z1: float, out: float) -> list[cq.Shape]:
    """The broad members as nested terraces at the field's own column ends: for each end the field's
    columns reach (`outer`, a voxel's face), the broad columns reaching it or farther, as pads with
    their top there (`pad_plates`). Each column then stands as far as the optimiser's metal in it,
    and the nested outlines need not meet: a deeper terrace stands a cell (`FINE`) inside the
    shallower one's outline. Traced from the same columns their outlines met along shared edges,
    and OCC's fuse of a deeper terrace came out invalid: seven left out, the half's body once lost
    (929 + 298 cm3 fused to 233, 10:40)."""
    from scipy.ndimage import binary_erosion

    solids = []
    ends = np.unique(np.round(c["outer"][broad], 3))
    for k, end in enumerate(sorted(ends, key=lambda e: out * e)):  # the nearest first
        reach = broad & (out * (c["outer"] - end) >= -1e-6)
        if not reach.any():
            continue
        mask, xs2, ys2 = fine(reach, c)
        if k:
            mask = binary_erosion(mask, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
        solids += pad_plates(mask, xs2, ys2, c, None, base, circles, z0, z1, out, level=float(end))
    return solids


def plan_picture(stem: str, reading: dict, layout: dict) -> Path:
    """Each half's reading in plan: the field's columns (how far they stand proud), the ribs drawn
    (their thickness), the pads' outlines, the inside's outline at the split and the mounts."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from matplotlib.patches import Polygon as Patch

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    for ax, half in zip(axes, ("cover", "motor_side"), strict=True):
        r = reading[half]
        c = r["columns"]
        ext = [c["xs"][0] - c["h"] / 2, c["xs"][-1] + c["h"] / 2, c["ys"][0] - c["h"] / 2, c["ys"][-1] + c["h"] / 2]
        im = ax.imshow(c["proud"].T, origin="lower", extent=ext, cmap="Greys", alpha=0.55, vmin=0, vmax=100)
        for ring in layout["flange"]["inner"]:
            ax.add_patch(Circle(ring["centre"], ring["radius"], fill=False, ec="0.35", lw=0.6, ls="--"))
        for m in layout["mounts"]:
            ax.add_patch(Circle(m["centre"], layout["settings"]["mount_diameter"] / 2, fill=False, ec="tab:green", lw=1.5))
            ax.annotate(m["name"], m["centre"], color="tab:green", fontsize=8, ha="center", va="center")
        for rib in r["ribs"]:
            p = np.asarray(rib["points"], float)
            if p.ndim != 2 or len(p) < 2:  # the bosses' terraces: no line of their own
                continue
            ax.plot(p[:, 0], p[:, 1], "-", color="tab:red", lw=max(rib["width"], 1.0) / 3.0, solid_capstyle="round", alpha=0.85)
        for outline in r["pad_outlines"]:
            ax.add_patch(Patch(outline, closed=True, fill=False, ec="tab:blue", lw=1.2))
        ax.set_title(f"{half}: {len(r['ribs'])} ribs (red, line width ∝ thickness), {len(r['pad_outlines'])} pads (blue)\nover the field's columns (grey: mm proud)")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, shrink=0.7, label="mm the placed metal stands proud")
    path = OUT / f"{stem}_ribs.png"
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)
    return path


def mesh_body(pieces: list[cq.Shape], layout: dict, all_rooms: list[dict], half: str):
    """FE's mesh of a half, as the mesh route makes its (`outcome_cad.build_mesh`): the half's
    parts (the exact shell, each rib, post, strut and pad, unjoined) each tessellated to
    `MESH_CHORD` and filled on one grid of `FE_VOXEL` (`mesh_route.occupancy`), their surface
    contoured (no feature under a cell survives), then cut flat at the split and by the same exact
    cuts by manifold3d. The B-rep's exact parts met in faces 0.002 mm wide: tessellated, they
    crossed themselves once coarsened (03:43), and TetGen could not mesh them even kept (04:15);
    joined by manifold3d first, two ribs meeting along an edge were not a manifold (04:31)."""
    import manifold3d as mf
    import mesh_route as mr

    lower = half == "motor_side"
    meshes = [mr.tessellated(p, MESH_CHORD) for p in pieces]
    lo, shape = mr.grid_over(meshes, FE_VOXEL)
    cells = np.zeros(tuple(shape), bool)
    odd = 0
    for m in meshes:
        c_, _, o = mr.occupancy(m, FE_VOXEL, lo, shape)
        cells |= c_
        odd += o
    body = mr.from_trimesh(mr.contour(cells, lo, FE_VOXEL, FE_BLUR, 0.5))
    say(f"{half}: FE's body on a {FE_VOXEL:g} mm grid, {mr.volume_of(body) / 1e3:.0f} cm3 (its cells {cells.sum() * FE_VOXEL**3 / 1e3:.0f})"
        + (f" ({odd} odd columns)" if odd else ""))  # fmt: skip
    body = body ^ mr.half_space(layout["z"]["split"], keep_below=lower)
    body = body - mf.Manifold.batch_boolean([mr.from_shape(t, MESH_CHORD) for _, t in exact_cuts(layout, all_rooms, half)], mf.OpType.Add)
    body, dropped = mr.largest(body)
    if dropped:
        say(f"{half}: FE's mesh, {dropped / 1e3:.1f} cm3 of loose pieces dropped")
    return body


def union(shapes: list[cq.Shape], name: str) -> cq.Shape:
    """One solid from many, fused a pair at a time, each fuse checked by its volume: at least the
    larger part's, at most the two parts' sum. OCC's fuse of several at once lost a half's body and
    called it valid (03:21)."""
    # the largest first: begun from a small faulty part, every fuse after it was refused (04:15)
    parts = sorted((s_ for s_ in shapes if s_.isValid() and s_.Volume() > 0), key=lambda x: -x.Volume())
    if len(parts) < len(shapes):
        say(f"  {name}: {len(shapes) - len(parts)} part(s) not valid, left out")

    def fused(a: cq.Shape, b: cq.Shape) -> tuple[cq.Shape | None, float]:
        v_a, v_b = a.Volume(), b.Volume()
        out = a.fuse(b)
        v = out.Volume()
        # OCC's volumes of spline-sided solids are good to about half a per cent: a 1 mm3 tolerance
        # refused two parts apart, the mounts' struts (03:28), and 0.2 % the pads (03:31)
        tol = 1e-2 * (v_a + v_b)
        return (out if out.isValid() and max(v_a, v_b) - tol <= v <= v_a + v_b + tol else None), v

    # A pairwise tree, so that every operand stays small: fused one by one onto a growing body, the
    # cover's 77 ribs and terraces took 8.5 minutes (11:38-11:47). A part refused where it was paired
    # is tried once more against the whole at the end.
    level, refused = parts, []
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level) - 1, 2):
            out, _ = fused(level[i], level[i + 1])
            if out is None:
                nxt.append(level[i])
                refused.append(level[i + 1])
            else:
                nxt.append(out)
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    body = level[0]
    for s_ in refused:
        out, v = fused(body, s_)
        if out is None:
            say(f"  {name}: the fuse of a part gave {v / 1e3:.1f} cm3 from {body.Volume() / 1e3:.1f} and {s_.Volume() / 1e3:.1f}: left out")
            continue
        body = out
    return body


def thin_faces(shape: cq.Shape, below: float = 0.5) -> list[tuple[float, tuple[float, float, float], str]]:
    """The faces narrower than `below` mm (2·area/perimeter, CLAUDE.md's sliver rule): their width,
    their centre and their kind, narrowest first."""
    out = []
    for face in shape.Faces():
        per = sum(e.Length() for e in face.Edges())
        if per > 0 and 2.0 * face.Area() / per < below:
            c_ = face.Center()
            out.append((2.0 * face.Area() / per, (round(c_.x, 1), round(c_.y, 1), round(c_.z, 1)), face.geomType()))
    return sorted(out)


def exact_cuts(layout: dict, all_rooms: list[dict], half: str) -> list[tuple[str, cq.Shape]]:
    """Every exact cut of a half, named, as the mesh route makes them (`outcome_cad.build_mesh`):
    the exits, the vehicle's brackets beyond each mount, each bolt's head seat with a hex key's
    room and its hole, the inside, each bearing's bore and its path in from the split, the
    mounts' holes."""
    s = layout["settings"]
    z_split, wall, draft = layout["z"]["split"], s["wall"], s.get("draft", 0.0)
    t_f = s["flange_thickness"]
    lower = half == "motor_side"
    brackets = {b["name"]: b for b in layout.get("brackets", [])}
    cuts = []
    for e in layout.get("exits") or []:
        ez0, ez1 = e["z"]
        if (ez1 <= z_split) == lower:
            cuts.append((f"exit {e.get('name', '')}", cylinder(e["centre"], ez0 - 1.0, ez1 + 1e-3, 2 * e["radius"]) if lower else cylinder(e["centre"], ez0 - 1e-3, ez1 + 1.0, 2 * e["radius"])))
    for m in layout["mounts"]:  # the vehicle's bracket and bolt beyond both faces
        d_b = 2 * brackets[f"{m['name']} bracket -z"]["radius"]
        cuts += [(f"{m['name']} bracket -z", cylinder(m["centre"], m["z"][0] - 600.0, m["z"][0], d_b)),
                 (f"{m['name']} bracket +z", cylinder(m["centre"], m["z"][1], m["z"][1] + 600.0, d_b))]  # fmt: skip
    d_s, h_s = oc.SOCKET
    for i, cb in enumerate(layout["bolts"]):  # each bolt's head seat and a hex key's room, and its hole
        cuts.append((f"bolt {i} socket", cylinder(cb, z_split - t_f - h_s, z_split - t_f, d_s) if lower else cylinder(cb, z_split + t_f, z_split + t_f + h_s, d_s)))
        cuts.append((f"bolt {i} hole", cylinder(cb, z_split - t_f - 1.0, z_split + t_f + 1.0, s["bolt_hole"])))
    cuts.append(("the inside", cupmod.cup(all_rooms, z_split, half, wall, draft)[1]))
    for b in layout["bearings"]:
        if (b["side"] == "-z") != lower:
            continue
        bz0, bz1 = b["z"]
        cuts.append((f"{b.get('name', 'bearing')} bore", cylinder(b["axis"], bz0, bz1, b["D"])))
        cuts.append((f"{b.get('name', 'bearing')} path in", cylinder(b["axis"], *sorted((bz1 if lower else bz0, z_split)), b["D"] + 1.0)))
    for m in layout["mounts"] if lower else []:
        cuts.append((f"{m['name']} hole", cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"])))
    return cuts


def build(run: str, stem: str) -> dict:
    t0 = time.time()
    layout = json.loads((OUT / f"{oc.layout_of(run)}.json").read_text(encoding="utf-8"))
    if not layout.get("flange"):
        raise ValueError("the ribbed drawing draws the contract's layout of 11 October (its `flange`)")
    s = layout["settings"]
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial, axial = value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm")
    z_split, wall, draft = layout["z"]["split"], s["wall"], s.get("draft", 0.0)
    bearings, bolts, mounts = layout["bearings"], layout["bolts"], layout["mounts"]
    all_rooms = cupmod.rooms(chain, radial, axial)
    halves, organic, reading, meshes, held = {}, {}, {}, {}, list(mounts)
    band = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")).get("band_mm")  # read by width within a height envelope
    global RIB
    RIB = RIB_BAND if band else (6.0, 12.0)  # production's thickness within a height envelope
    import network_draw

    # a run on production's rib network is drawn from its own pieces (`network_parts`)
    net = network_draw.pieces(run, force=True) if json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")).get("ribs") else None

    for half in os.environ.get("RIBBED_HALVES", "motor_side cover").split():  # one alone while it is debugged
        t1 = time.time()
        lower = half == "motor_side"
        out = -1.0 if lower else 1.0
        c = columns(run, half)
        global STRENGTHEN
        STRENGTHEN = None
        if STRENGTHEN_ASKED and (STRENGTHEN_ASKED["side"] == "-z") == lower:
            seat = next(b for b in bearings if b["shaft"] == STRENGTHEN_ASKED["shaft"] and b["side"] == STRENGTHEN_ASKED["side"])
            cap = float(np.nanmin(c["outer"])) if lower else float(np.nanmax(c["outer"]))
            STRENGTHEN = {**STRENGTHEN_ASKED, "axis": np.asarray(seat["axis"], float), "cap": cap, "out": out}
            say(f"{half}: the ribs within {STRENGTHEN['near']:g} mm of the {seat['shaft']} {seat['side']} seat at {RIB[1]:g} mm, raised {STRENGTHEN['raise']:g} mm (to z {cap:.1f} at most)")
        if band:  # within a height envelope: by width, the broad members terraces, the narrow ribs
            pad6, deep6 = by_width(c)
        else:
            deep6 = c["col"] & (c["proud"] >= DEEP)
            pad6 = c["col"] & ~deep6
        deep, xs2, ys2 = fine(deep6, c)
        pad, _, _ = fine(pad6, c)
        branches, nodes = centre_lines(deep, xs2, ys2)
        # the ribs and pads begin `PAST_SPLIT` past the split's plane and the half is cut flat there
        # after: begun on it, their feet lay in the shell's joint face, and OCC's fuse of the three
        # lost the half (185 of 3,700 cm3, 03:21); begun 1 mm short of it, the feet left slivers
        # where they crossed the land's edge (0.008-0.05 mm, 03:25)
        z_far = float(np.nanmax(np.abs(c["outer"] - z_split))) + 10.0
        z0, z1 = (z_split - z_far, z_split + PAST_SPLIT) if lower else (z_split - PAST_SPLIT, z_split + z_far)
        top_rib, top_pad = envelope(c, deep6), envelope(c, pad6)
        base, circles = base_of(layout, all_rooms, half), circles_of(layout, all_rooms, half)
        ties = []
        if net is not None:  # a run on the network: drawn from its own pieces (`network_parts`)
            rib_parts, ribs, _ = network_parts(net, half, c, base, circles, z0, z1, out, layout)
            strut_parts, ties = network_struts(layout, all_rooms, half, circles, z_split)
            rib_parts += strut_parts
            pads = []
            if lower:
                say(f"{half}: struts into the mounts: " + (", ".join(f"{t['mount']} ({t['length']:.0f} mm, {t['width']:g} thick)" for t in ties) or "none"))
        else:
            rib_parts, ribs = rib_plates(branches, nodes, c, top_rib, base, circles, z0, z1, out)
            if lower:  # the mounts are the motor side's (`outcome_cad.exact_shell`)
                tie_parts, ties = mount_ties(ribs, deep, xs2, ys2, layout, circles, z_split)
                rib_parts += tie_parts
                say(f"{half}: struts into the mounts: " + (", ".join(f"{t['mount']} ({t['length']:.0f} mm, {t['width']:g} thick)" for t in ties) or "none"))
            pads = terraces(pad6, c, base, circles, z0, z1, out) if band else pad_plates(pad, xs2, ys2, c, top_pad, base, circles, z0, z1, out)
        say(f"{half}: {deep6.sum()} {'narrow' if band else 'deep'} columns, {pad6.sum()} {'broad' if band else 'shallow'}; {len(ribs)} ribs ({sum(r['length'] for r in ribs) / 10:.0f} cm of centre-line, "
            f"thickness {min((r['width'] for r in ribs), default=0):g}-{max((r['width'] for r in ribs), default=0):g} mm), {len(pads)} pads")  # fmt: skip
        body = oc.exact_shell(layout, all_rooms, z_split, half, wall, draft)
        v_shell = body.Volume()
        pieces = [body] + rib_parts + pads  # the parts unjoined, as FE's mesh fills them (`mesh_body`)
        if rib_parts:
            ribs_solid = union(rib_parts, f"{half}'s ribs")
            say(f"{half}: the ribs, each topped by the envelope along it, {ribs_solid.Volume() / 1e3:.0f} cm3, valid {ribs_solid.isValid()}")
            body = union([body, ribs_solid], f"{half}'s shell and ribs")
        if pads:
            pads_solid = union(pads, f"{half}'s pads")
            say(f"{half}: the pads, flat-topped, {pads_solid.Volume() / 1e3:.0f} cm3, valid {pads_solid.isValid()}")
            body = union([body, pads_solid], f"{half}'s shell, ribs and pads")
        meshes[half] = mesh_body(pieces, layout, all_rooms, half)
        beyond = cq.Solid.makeBox(4000.0, 4000.0, 1000.0, cq.Vector(-2000.0, -2000.0, z_split if lower else z_split - 1000.0))
        body = body.cut(beyond)  # cut flat at the split: the joint's face one plane
        say(f"{half}: the shell {v_shell / 1e3:.0f} cm3, with the ribs and pads {body.Volume() / 1e3:.0f} cm3 (solid through the inside), valid {body.isValid()}")
        organic[half] = body
        for name, tool in exact_cuts(layout, all_rooms, half):
            cut = body.cut(tool)
            lost = body.Volume() - cut.Volume()
            if not cut.isValid() or lost > 0.05 * body.Volume() and name != "the inside":
                say(f"{half}: the cut '{name}' took {lost / 1e3:.0f} of {body.Volume() / 1e3:.0f} cm3, valid {cut.isValid()}")
            body = cut
        tidy = body.clean()  # faces of one surface merged, kept only if it changed nothing else
        if tidy.isValid() and abs(tidy.Volume() - body.Volume()) < 1.0:
            body = tidy
        thin = thin_faces(body)
        if thin:
            say(f"{half}: {len(thin)} faces under 0.5 mm wide, the narrowest: " + "; ".join(f"{w:.3f} mm {k} at {c_}" for w, c_, k in thin[:6]))
        solids = sorted(body.Solids(), key=lambda x: x.Volume(), reverse=True)
        if len(solids) > 1:
            say(f"{half}: {len(solids) - 1} loose pieces dropped, {sum(x.Volume() for x in solids[1:]) / 1e3:.1f} cm3")
        # (no heal: FE meshes its own body, `mesh_body`, never this B-rep, and the heal was refused in
        # both halves while it took a minute or more of a half's drawing, 11 October 10:44)
        body = solids[0]
        if lower:
            held = []
            for m in mounts:
                ring = cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]).cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
                if body.intersect(ring).Volume() > 0.6 * ring.Volume():
                    held.append(m)
        halves[half] = body
        outlines = [o for o, _ in fb.loops(pad.astype(float), xs2, ys2, 0.5)]
        reading[half] = {"columns": c, "ribs": ribs, "pad_outlines": outlines, "top_rib": top_rib, "top_pad": top_pad, "ties": ties, "pads_drawn": len(pads)}
        say(f"{half}: drawn in {time.time() - t1:.0f} s: {len(body.Faces())} faces, {body.Volume() / 1e3:.0f} cm3, valid {body.isValid()}")
    if os.environ.get("RIBBED_HALVES"):
        return {}
    picture = plan_picture(stem, reading, layout)
    if len(held) < len(mounts):
        say(f"{stem}: the body holds {len(held)} of the layout's {len(mounts)} mounts")
    names = {half: convex._name_faces(shape, bearings, bolts, mounts, [], z_split, s, []) for half, shape in halves.items()}
    import mesh_route as mr

    files = {}
    for half, shape in halves.items():
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{stem}_{half}.step"))
        shape.exportBrep(str(OUT / f"{stem}_{half}.brep"))
        # FE's mesh (`mesh_body`), which FE (TetGen's tets), castability and the pictures read as
        # the mesh route's meshes (`files`): gmsh's mesher of the B-rep stops at a face under 0.5 mm
        tm = mr.to_trimesh(meshes[half])
        tm.export(str(OUT / f"{stem}_{half}.stl"))
        tm.export(str(OUT / f"{stem}_{half}.ply"))
        files[half] = f"{stem}_{half}.stl"
        say(f"{half}: FE's mesh, {len(tm.faces):,} triangles, watertight {tm.is_watertight}, {tm.volume / 1e3:.0f} cm3 (the B-rep {shape.Volume() / 1e3:.0f})")
    mass = {half: shape.Volume() * s["density"] for half, shape in halves.items()}
    record = {**layout, "stem": stem, "form": "outcome", "drawing": "ribs", "route": "brep", "skin_bosses": False,
              "ribbed": {"deep_mm": DEEP, "rib_mm": list(RIB), "spur_mm": SPUR, "smooth_mm": SMOOTH, "envelope_sigma_voxels": ENVELOPE_SIGMA,
                         "read": "the network's pieces" if net is not None else "by width" if band else "by depth", "broad_mm": BROAD if band else None,
                         "ribs": {h_: len(r["ribs"]) for h_, r in reading.items()}, "pads": {h_: r["pads_drawn"] for h_, r in reading.items()}, "ties": [t for r in reading.values() for t in r["ties"]]},
              "outcome_of": run, "ribs": [{"half": h_, **rb} for h_, r in reading.items() for rb in r["ribs"]], "bolts": bolts, "mounts": held,
              "mounts_layout": mounts, "mass_kg": {**mass, "total": sum(mass.values())},
              "faces": {half: {str(k): v for k, v in nm.items()} for half, nm in names.items()}, "seconds": time.time() - t0,
              "picture": picture.name, "files": files, "brep": {half: f"{stem}_{half}.brep" for half in halves},
              "strengthened": STRENGTHEN_ASKED}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1, default=list), encoding="utf-8")
    files_o = {}
    for half, shape in organic.items():
        shape.exportBrep(str(OUT / f"{stem}_organic_{half}.brep"))
        mr.tessellated(shape, 0.1).export(str(OUT / f"{stem}_organic_{half}.stl"))  # a picture: closed, not a manifold
        files_o[half] = f"{stem}_organic_{half}.stl"
    mass_o = {half: shape.Volume() * s["density"] for half, shape in organic.items()}
    shown = {**record, "stem": f"{stem}_organic", "form": "organic", "organic_of": stem, "mass_kg": {**mass_o, "total": sum(mass_o.values())},
             "files": files_o, "brep": {half: f"{stem}_organic_{half}.brep" for half in organic}}  # fmt: skip
    (OUT / f"{stem}_organic.json").write_text(json.dumps(shown, indent=1, default=list), encoding="utf-8")
    say(f"{stem}: {record['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f}); "
        f"{len(held)} of {len(mounts)} mounts held; drawn in {record['seconds']:.0f} s; the reading: {picture.name}")  # fmt: skip
    return record


STRENGTHEN_ASKED: dict | None = None  # from `--strengthen <shaft> <side> <reach mm> <raise mm>`

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--strengthen" in args:
        i = args.index("--strengthen")
        shaft, side, near, lift = args[i + 1 : i + 5]
        STRENGTHEN_ASKED = {"shaft": shaft, "side": side, "near": float(near), "raise": float(lift)}
        args = args[:i] + args[i + 5 :]
    build(args[0], args[1])
