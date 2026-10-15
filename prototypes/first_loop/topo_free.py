"""PROTOTYPE (LOP-16) - not product code: the housing from its interfaces, by topology optimisation
on the bearings' misalignment.

Nothing is drawn but what the contract fixes. A voxel model of PLT-8's packaging space (the hull,
seen along the shafts, of every part's circle grown by the installation clearance, over the
stacks' length grown by it) with:
- **the cavity, kept clear:** each half a cup open toward the split, as a cast half is. Every
  part's room (each gear and carrier grown by the least radial and axial clearances, A19 and A18;
  each bearing's room; each shaft at its least bore) is taken in plan and run from its far end in
  the half to the split, and the half's cavity is their union: both stages share one cavity, and
  nothing stands inside it. A sealed end's seal bore and the shafts' exits through the end walls
  are as before. Outside, kept clear: the motor beyond its flange, the half-shafts' joints, the
  mounts' bolts. (`cavity="rooms"` keeps the earlier model: each room its own cylinder, so the
  skin closed every room off and walls stood inside the housing at the split.)
- **frozen:** the cavity's skin, its one-voxel boundary: the oil's boundary (a stiffness
  optimisation alone gives a frame, never a closed housing), holding each bearing's seat. A skin
  voxel stands for the contract's least wall (4 mm) in a voxel 5-6 mm thick: its mass is the
  wall's (scaled by t/h) and its stiffness the wall's in bending (scaled by (t/h)^3), see
  `build_free`; round the bearings' bores it stays whole. Also frozen: the motor's ring (A25) and
  the mounts (A20, where the prototype places them), solid;
- **free:** the rest of the packaging space.

A casting filter keeps every column of each half, along the pull, one interval of metal: it fills
any gap between metal. Whatever the optimiser draws then comes out of a two-part mould split at
the halves' joint. The halves are joined only at the bolts, as `fe.py` joins them (`joint="bolts"`,
the layout's bolt circle; `joint="glued"` shares the whole split plane, the earlier model).

The objective is `topo.py`'s `misalignment_bound`: the grade's measure (every seat's
misalignment over its line, in both cases) as a bound problem solved by GCMMA (`mma.py`), SIMP's
penalty ramped from 1 to 3 over the first 20 iterations; `misalignment` is the earlier p-norm
updated by optimality criteria, which never settled (runs 2 and 3). The budget is the whole
housing's mass; the free voxels get what the frozen ones leave. The result is a hypothesis; the
CAD, meshed and solved, is the judge.

Run: .venv/Scripts/python.exe prototypes/first_loop/topo_free.py [budget_kg] [voxel_mm]
       [iterations] [band_mm] [--objective misalignment_bound|misalignment] [--joint bolts|glued]
       [--skin MM] [--cavity cup|rooms] [--ramp N] [--tag TEXT] [--resume]
     (e.g. 7.73 6 200; outputs data/first_loop/topofree_<...>.npz/.json/.png, and a checkpoint
     every 10 iterations, <stem>_checkpoint.npz, from which --resume carries on)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, generate_binary_structure

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from topo import DENSITY, OUT, inside, say  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.plan import hull_of_circles  # noqa: E402

# The layout record the model takes its mounts, split, bolts and exits from: "contract" (written by
# contract_layout.py from zenryx's `spaces`, no motor flange; since 10 October 14:00) or "grammar4"
# (the generator's placements and motor ring: every earlier run, rebuilt from its record's layout).
LAYOUT = "contract"
FLOOR = 1e-9  # a frozen voxel's (1 - density) in the casting filter's products
# "damping": the OC update's exponent (0.5 is the usual square root); run 2 flipped between two
# worst seats at its end with steps of 0.1, so stage 2 took 0.3 and steps of 0.05 (it still
# flipped: run 3). "mma_move": MMA's step limit at beta 1, divided by sqrt(beta) as the
# projection sharpens (0.05 at beta 16, the OC's late step).
PROJECTION = {"eta": 0.5, "every": 40, "beta_most": 16.0, "move_late": 0.05, "damping": 0.3, "mma_move": 0.2}
# Iterations over which SIMP's penalty rises from 1 to 3 (`topo.solve_model` says why: a cover
# joined only at the bolts hangs on grey voxels at the start, which p = 3 makes too soft for the
# single factor to refine).
PENALTY_RAMP = 20
TRADE_PROUD = 3.0  # mm, a bearing boss's face past its end wall (grammar.py's 0.5·δ; `outcome_cad.PROUD`)
# (LOP-29) a kept-clear space emptied this far past its boundary, as the drawing empties it (`outcome_cad.FINE_MARGIN`), with
# `build_free(..., drawing_clear=True)`; and a bolt head's socket where the layout gives none (`outcome_cad.SOCKET`)
KEEP_MARGIN = 2.0
SOCKET = (16.0, 25.0)
CHECKPOINT_EVERY = 10  # iterations between the run's checkpoints (a resume path for long runs)
HELD_TOL = 1.02  # (LOP-30) a state holds its lines when every tilt and bed is within this of its line (`<stem>_held.npz`)
# The production rib network as the design space (LOP-23, `ribs`): a wheel round each bore, as on
# the cases cast for Nissan's two-stage BEV reducer (Aichi Kikai) and in the Materials 14:3999
# shell: `RIB_SPOKES` spokes from the bore across its own cell, a ring at the boss, a link from
# each bore to the next, a ridge between the cells, and a gusset from each bolt's boss to the wall.
RIB_SPOKES = 16
RIB_HALF = 0.75  # a candidate rib holds the voxels whose centres lie within this many voxels of its line: one voxel wide, two on a diagonal (4-connected)
FIN_PITCH = 24.0  # mm along the inside's outline between the fins up the side walls (the Gaojian housing's fins along the pull)
SEGMENT = 40.0  # mm: under the rib filter, the length of rib that stands at one height (a spoke's, a link's, an arc's, a ridge's square)


def _to_segment(px: np.ndarray, py: np.ndarray, a: tuple, b: tuple) -> np.ndarray:
    """Each point's distance in plan to the segment a-b."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / max(dx * dx + dy * dy, 1e-12), 0.0, 1.0)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def field_lines(stem: str, n: np.ndarray, lo: np.ndarray, h: float, k_split: int, lower: bool) -> np.ndarray:
    """A run's members as lines in plan (LOP-23, `ribs_from`): one half's placed metal (its free
    voxels at 0.5 or more) seen along the pull, its small holes filled, thinned to its centre-lines,
    each line then a candidate rib one voxel wide, two where it steps diagonally (so that its voxels
    share faces). The run must be on the same voxels: it is the interpreted design put back into the
    voxel model and optimised again (the engineer, 9 October 22:51), its load paths beside
    production's wheels."""
    from skimage.morphology import remove_small_holes, skeletonize

    z = np.load(OUT / f"{stem}.npz")
    if not (np.array_equal(z["n"].astype(int), n) and np.allclose(z["lo"], lo) and float(z["h"]) == h):
        raise ValueError(f"{stem}: another model's voxels ({z['n'].tolist()} of {float(z['h']):g} mm), not these")
    placed = np.zeros(int(np.prod(n)), bool)
    placed[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    placed = placed.reshape(tuple(n))
    plan = (placed[:, :, :k_split] if lower else placed[:, :, k_split:]).any(axis=2)
    plan = remove_small_holes(plan, max(1, int(round((3 * h) ** 2 / h**2))))
    lines = skeletonize(plan)
    joined = lines.copy()
    joined[1:, :-1] |= lines[:-1, :-1] & lines[1:, 1:]  # a step to (i+1, j+1) also holds (i+1, j)
    joined[1:, 1:] |= lines[:-1, 1:] & lines[1:, :-1]  # a step from (i, j+1) to (i+1, j) also holds (i+1, j+1)
    return joined


def side_fins(inside: np.ndarray, xc: np.ndarray, yc: np.ndarray, h: float, band: float, parts: bool = False, geometry: bool = False) -> np.ndarray | list:
    """Fins up the side walls (LOP-23): at every `FIN_PITCH` along the half's inside's outline in plan
    (`inside`, its rooms seen along the pull), a line along the outline's outward normal from two
    voxels inside it to the band past it; each a slab along the pull, so a fin up the side wall from
    the flange to the end face, as the production housings' fins stand. The free run's metal off
    the wheels was the side walls' (11 October 08:21: 0.71 kg, from the flange up). With `parts`,
    each fin alone (for the rib filter)."""
    from skimage.measure import find_contours

    X, Y = np.meshgrid(xc, yc, indexing="ij")
    w = RIB_HALF * h
    fins = []
    for c in find_contours(inside.astype(float), 0.5):
        px, py = xc[0] + h * c[:, 0], yc[0] + h * c[:, 1]
        step = np.hypot(np.diff(px), np.diff(py))
        s = np.concatenate([[0.0], np.cumsum(step)])
        if s[-1] < FIN_PITCH:
            continue
        for at in np.arange(0.5 * FIN_PITCH, s[-1], FIN_PITCH):
            i = int(np.clip(np.searchsorted(s, at), 1, len(s) - 1))
            tx, ty = px[i] - px[i - 1], py[i] - py[i - 1]
            norm = np.hypot(tx, ty)
            if norm < 1e-9:
                continue
            nx, ny = ty / norm, -tx / norm
            ix = int(np.clip(round((px[i] + 2 * h * nx - xc[0]) / h), 0, len(xc) - 1))
            iy = int(np.clip(round((py[i] + 2 * h * ny - yc[0]) / h), 0, len(yc) - 1))
            if inside[ix, iy]:  # the normal pointing in: turn it out
                nx, ny = -nx, -ny
            a = (px[i] - 2 * h * nx, py[i] - 2 * h * ny)
            b = (px[i] + (band + h) * nx, py[i] + (band + h) * ny)
            fins.append((_to_segment(X, Y, a, b) <= w, ("segment", a, b)))
    if parts:
        return fins if geometry else [m for m, _ in fins]
    return np.logical_or.reduce([m for m, _ in fins]) if fins else np.zeros(X.shape, bool)


def _tiles(mask: np.ndarray, xc: np.ndarray, yc: np.ndarray) -> list[np.ndarray]:
    """A plan mask cut into `SEGMENT` squares: each square's part of it, where it has any."""
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    tile = np.floor((X - xc[0]) / SEGMENT).astype(int) * 100_000 + np.floor((Y - yc[0]) / SEGMENT).astype(int)
    return [mask & (tile == t) for t in np.unique(tile[mask])]


def space_regions(path: str) -> dict:
    """An iteration's design space (LOP-24, `--space`): {"halves": {"motor_side" | "cover": [{"name": ...,
    "outline": [[x, y], ...], "holes": [[[x, y], ...], ...]}, ...]}}, in mm in plan."""
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        p = OUT / p
    return json.loads(p.read_text(encoding="utf-8"))


def space_mask(path: str, x: np.ndarray, y: np.ndarray, cover: np.ndarray, info: dict | None = None, band: float = 24.0) -> np.ndarray:
    """Each voxel inside one of its half's regions (outline less holes), by its column's centre; and, whatever the
    regions say, each mount's own room (its disc, its radius plus half the band), so that no lug is cut loose.
    A `.npz` (LOP-24, `regions.py`: regions as 3D solids between the hard points) gives the cells themselves."""
    from matplotlib.path import Path as MPath

    if str(path).endswith(".npz"):
        p = Path(path)
        p = p if p.is_absolute() or p.exists() else OUT / p
        out = np.asarray(np.load(p)["mask"], bool).ravel().copy()
        if out.shape != x.shape:
            raise ValueError(f"{p.name}: {out.size:,} cells, the grid {x.size:,}")
    else:
        regions = space_regions(path)["halves"]
        out = np.zeros(x.shape, dtype=bool)
        xy = np.column_stack([x, y])
        for half, sel in (("motor_side", ~cover), ("cover", cover)):
            inside = np.zeros(int(sel.sum()), dtype=bool)
            pts = xy[sel]
            for reg in regions.get(half, []):
                here = MPath(np.asarray(reg["outline"], float)).contains_points(pts)
                for hole in reg.get("holes", []):
                    here &= ~MPath(np.asarray(hole, float)).contains_points(pts)
                inside |= here
            out[sel] = inside
    if info is not None:
        r_m = 0.5 * float(info["settings"].get("mount_diameter", 36.0)) + 0.5 * band
        for m in info.get("mounts", []):
            out |= np.hypot(x - m["centre"][0], y - m["centre"][1]) <= r_m
        for b in info.get("bearings", []):  # each seat's own room on its half: the boss disc
            half = cover if b["side"] == "+z" else ~cover
            out |= half & (np.hypot(x - b["axis"][0], y - b["axis"][1]) <= float(b["boss_r"]))
    return out


def rib_network(info: dict, xc: np.ndarray, yc: np.ndarray, h: float, lower: bool, wall_xy: np.ndarray,
                parts: bool = False, geometry: bool = False) -> np.ndarray | list:  # fmt: skip
    """The production rib network of one half in plan, (len(xc), len(yc)) True where a candidate rib
    stands: every rib a slab along the pull, so whatever height the optimiser gives it within the
    band it comes out of the mould. Round each bore (its bearing in this half): a disc to the
    trade's boss radius (`boss_r`, 1.25·D + 10), `RIB_SPOKES` spokes from the bore across the
    bore's own cell (the plan points nearer its axis than any other, so that spokes of two wheels
    never cross), each phased to point at the nearest other bore, and a ring at the boss; a link
    between each pair of bores; the cells' boundaries as ridges, where the spokes end; and from
    each bolt's boss a gusset to the nearest wall (`wall_xy`, the skin's voxels in plan).

    With `parts`, the network's pieces for the rib filter (`rib_groups`), each at one height: the
    boss's annuli a voxel wide (so that it stays round), the ring's arcs, the spokes' and the links'
    lengths of `SEGMENT`, the ridges by `SEGMENT` squares, each gusset. With `geometry` too, each
    piece as (mask, shape) for drawing it clean (`network_draw.py`): ("annulus", cx, cy, r0, r1),
    ("arc", cx, cy, r, a0, a1), ("segment", (ax, ay), (bx, by)) or ("cells",) for a ridge's square."""
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    w = RIB_HALF * h
    seats = [b for b in info["bearings"] if (b["side"] == "-z") == lower]
    centres = np.asarray([b["axis"] for b in seats], float)
    d_c = np.stack([np.hypot(X - cx, Y - cy) for cx, cy in centres])
    cell = np.argmin(d_c, axis=0)
    prims = []  # (mask, shape)
    reach = float(np.hypot(*(np.ptp(np.asarray(info["outline"], float), axis=0))))
    for i, b in enumerate(seats):
        cx, cy = centres[i]
        mine = cell == i
        disc = (d_c[i] <= b["boss_r"]) & mine  # the boss
        prims += [(disc & (d_c[i] >= r0) & (d_c[i] < r0 + h), ("annulus", cx, cy, r0, min(r0 + h, b["boss_r"]))) for r0 in np.arange(0.0, b["boss_r"] + h, h)]
        ring = (np.abs(d_c[i] - b["boss_r"]) <= w) & mine  # its ring
        arcs = max(1, int(round(2 * np.pi * b["boss_r"] / SEGMENT)))
        q = np.floor((np.arctan2(Y - cy, X - cx) + np.pi) / (2 * np.pi) * arcs).astype(int) % arcs
        prims += [(ring & (q == k), ("arc", cx, cy, b["boss_r"], -np.pi + 2 * np.pi * k / arcs, -np.pi + 2 * np.pi * (k + 1) / arcs)) for k in range(arcs)]
        others = [centres[j] for j in range(len(seats)) if j != i]
        nearest = min(others, key=lambda c: np.hypot(c[0] - cx, c[1] - cy))
        phase = np.arctan2(nearest[1] - cy, nearest[0] - cx)
        for k in range(RIB_SPOKES):
            a = phase + 2 * np.pi * k / RIB_SPOKES
            ux, uy = np.cos(a), np.sin(a)
            tip = (cx + reach * ux, cy + reach * uy)
            spoke = (_to_segment(X, Y, (cx, cy), tip) <= w) & mine
            prims += [(spoke & (d_c[i] >= s0) & (d_c[i] < s0 + SEGMENT), ("segment", (cx + s0 * ux, cy + s0 * uy), (cx + (s0 + SEGMENT) * ux, cy + (s0 + SEGMENT) * uy)))
                      for s0 in np.arange(0.0, reach + SEGMENT, SEGMENT)]  # fmt: skip
        for c in others:  # the links
            link = _to_segment(X, Y, (cx, cy), tuple(c)) <= w
            along = np.hypot(X - cx, Y - cy)
            span = float(np.hypot(c[0] - cx, c[1] - cy))
            ux, uy = (c[0] - cx) / span, (c[1] - cy) / span
            prims += [(link & (along >= s0) & (along < s0 + SEGMENT), ("segment", (cx + s0 * ux, cy + s0 * uy), (cx + min(s0 + SEGMENT, span) * ux, cy + min(s0 + SEGMENT, span) * uy)))
                      for s0 in np.arange(0.0, span + SEGMENT, SEGMENT)]  # fmt: skip
    # the ridges: a plan point next to another cell
    edge = np.zeros(X.shape, bool)
    edge[1:, :] |= cell[1:, :] != cell[:-1, :]
    edge[:-1, :] |= cell[1:, :] != cell[:-1, :]
    edge[:, 1:] |= cell[:, 1:] != cell[:, :-1]
    edge[:, :-1] |= cell[:, 1:] != cell[:, :-1]
    prims += [(t, ("cells",)) for t in _tiles(edge, xc, yc)]
    for bx, by in info["bolts"]:  # the gussets
        j = int(np.argmin((wall_xy[:, 0] - bx) ** 2 + (wall_xy[:, 1] - by) ** 2))
        prims.append((_to_segment(X, Y, (bx, by), tuple(wall_xy[j])) <= w, ("segment", (bx, by), tuple(wall_xy[j]))))
    prims = [p for p in prims if p[0].any()]
    if parts:
        return prims if geometry else [m for m, _ in prims]
    return np.logical_or.reduce([m for m, _ in prims])


def build_free(h: float, layout: str = LAYOUT, band: float | None = None, joint: str = "bolts",
               skin: float | None = None, cavity: str = "cup", penalty_ramp: int = PENALTY_RAMP, route: str = "cast",
               trade: bool = False, flange: bool = False, ribs: bool = False, ribs_from: str = "", fins: bool = False,
               rib_filter: bool = False, mount_reach: str = "corridor", height_field: float | None = None, space: str = "",
               empty: bool = False, protect: bool = False, flange_whole: bool = True, drawing_clear: bool = False,
               couplings: str = "glue", shell_fixed: bool = False, towers: bool = True) -> dict:  # fmt: skip
    """The voxel model at voxel size h (mm): `kind` per voxel (-1 not modelled, 0 free, 1 frozen),
    the casting filter, the projection, the joint, the skin's stiffness factors, the frozen mass
    and a mask of each kind of space (`masks`, for `topo_setup.py`'s pictures).

    - `band` (mm): stage 2's design space, metal only within it of the skin and in corridors to
      the mounts.
    - `joint`: "bolts" (the default) joins the halves only within the bolt bosses' footprints
      (`bolt_boss` across, round each of the layout's bolts) at the split, as `fe.py` does; "glued"
      shares every node of the split plane.
    - `skin` (mm): the wall a skin voxel stands for, by default the contract's least wall. The
      skin is one voxel thick (h, 5-6 mm), the least wall 4 mm, and the voxel size stays. A skin
      voxel's mass is scaled by t/h, the wall's own. Its stiffness is scaled by (t/h)^3: a plate's
      bending stiffness goes as E t^3, so this makes the bare one-voxel layer bend as the 4 mm
      wall does (Wilson's hexahedron bends correctly one element thick, `topo.hex_wilson`). That
      is the mode that matters for the seats: an end wall's bending tilts its bearing (LOP-1). A
      plate's stretching goes as E t, so in its own plane the scaled layer is (t/h)^2 = 0.44 times
      as stiff as the wall (at 6 mm): conservative where the skin acts as a membrane or as the
      flange of a rib the optimiser adds. One scaling cannot match both; the bending one errs on
      the soft side. It is also SIMP's own (p = 3) for a voxel of density t/h. When the voxel is
      no thicker than the wall (h <= t), or `skin` is 0, the skin is the voxel itself, unscaled.
      The skin's voxels round each bearing's bore stay whole (a seat sits in a boss, never in a
      4 mm wall), and the motor's ring and the mounts are solid parts, never scaled.
    - `cavity`: "cup" (the default) or "rooms" (the earlier model), see the module's docstring.
    - `penalty_ramp`: iterations over which SIMP's penalty rises from 1 to 3 (0: 3 throughout,
      as runs 1-3 had).
    - `flange` (the set-up since 11 October; a run's record says `flange`): the contract's split
      flange held fixed as the drawing draws it, its sealing land round the inside and the bolts'
      bosses on it (the layout's `flange`, from `spaces`), the flange's depth each side of the
      split: each voxel at the share of it the flange fills (4 x 4 x 4 points), its mass that share
      and its stiffness the share cubed, SIMP's own (a skin voxel in it keeps at least the wall's
      share). It replaces the bolts' two whole voxel layers (6 mm each side for the rules' 9). And
      the voxels are laid so that the split is a voxel face: at 6 mm the faces had stood 2.7 mm off
      it (17.05 against 14.35), the joint and the flange with them.
    - `ribs` (LOP-23, with `band`): the free voxels only on the production rib network
      (`rib_network`: a wheel round each bore, links, ridges, gussets), each rib a slab along the
      pull standing within the band, and in the mounts' corridors; with `ribs_from` (a run's stem on
      the same voxels) also on that run's members' centre-lines (`field_lines`).
    - `empty` (LOP-27, the empty start; the engineer, 12 October 20:22: "Do an empty start"): no
      fixed shell and no fixed flange land, the walls the optimiser's own metal; fixed only the
      interfaces: each seat's ring (the voxel layer round its bearing, along it, whole), the
      mounts and the bolts' bosses. The skin is still found, for the band and the mounts' reach,
      but it is free. The housing stays oil-tight by each run's least height (`height_min`, in its
      own free voxels; `topo.Voxels` adds it under the height field's own): the contract's least
      wall on a run standing on a room (the end walls) and on a run at the split over the other
      half's room (the plate over its wider opening); the flange's depth in the sealing land round
      the inside at the split (A26); the deepest room beside it and the least wall on the first
      ring round the inside (the side wall), at least the flange's depth; the seal's seat (A16) on
      the first ring round each sealed exit. Needs the height field and the contract's flange."""
    wall_asked = skin  # (the name `skin` is the skin's voxels below)
    if empty and not (height_field and flange):
        raise ValueError("the empty start's least heights are the height field's, on the contract's flange set-up: give height_field and flange")
    if ribs and not band:
        raise ValueError("the rib network is a design space within the band: give `band`")
    if rib_filter and not ribs:
        raise ValueError("the rib filter groups the rib network's pieces: give `ribs`")
    info = json.loads((OUT / f"{layout}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(topo.CONTRACT)
    chain = complete_chain(spec)
    s = info["settings"]
    gaps = spec.requirement.shaft_layout
    radial = value_in(gaps.min_radial_clearance, "mm")
    axial = value_in(gaps.min_axial_clearance, "mm")
    sealed = {(e.shaft, e.side.value) for e in gaps.sealed_ends}
    # The contract's layout (`contract_layout.py`, from zenryx's `spaces`): its packaging space, which
    # holds the mounts, and its exits, brackets and fixed bolt bosses; no motor ring. The generator's
    # (grammar4, every run before 10 October 14:00): the parts' hull alone, as those runs had it.
    from_contract = info.get("form") == "contract"
    if from_contract:
        outline = np.asarray(info["outline"])
        low, high = info["z_range"]
    else:
        clearance = value_in(spec.requirement.installation_space.clearance, "mm")
        circles = [(*st.axis, p.diameter / 2 + (radial if p.kind != "bearing" else 0.0)) for st in chain.layout.shafts for p in st.parts]
        outline = np.asarray(hull_of_circles([(cx, cy, r + clearance) for cx, cy, r in circles]))
        low = min(st.ends[0] for st in chain.layout.shafts) - clearance
        high = max(st.ends[1] for st in chain.layout.shafts) + clearance
    lo = np.array([outline[:, 0].min(), outline[:, 1].min(), low])
    hi = np.array([outline[:, 0].max(), outline[:, 1].max(), high])
    if flange:  # the split on a voxel face: the grid's start moved down by less than a voxel
        z_s = info["z"]["split"]
        lo[2] = z_s - h * np.ceil((z_s - low) / h - 1e-9)
    n = np.ceil((hi - lo) / h).astype(int)
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    zc = lo[2] + h * (np.arange(n[2]) + 0.5)
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing="ij")
    x, y, z = X.ravel(), Y.ravel(), Z.ravel()
    in_pack = inside(outline, x, y)
    # The halves as the voxels split them: the cover's from layer k_split up, the motor side's below.
    k_split = int(round((info["z"]["split"] - lo[2]) / h))
    k_of = np.broadcast_to(np.arange(n[2])[None, None, :], tuple(n)).ravel()
    cover = k_of >= k_split

    # Every part's room: (axis x, axis y, radius, z from, z to).
    parts = []
    clear = np.zeros(x.shape, dtype=bool)
    margin = KEEP_MARGIN if drawing_clear else 0.0  # (LOP-29) the drawing's margin round a kept-clear space
    kept = {"seals": np.zeros(x.shape, dtype=bool), "mount_ends": np.zeros(x.shape, dtype=bool)}  # the kept-clear spaces by kind, for pictures
    for stack in chain.layout.shafts:
        (ax, ay), shaft = stack.axis, stack.shaft
        r = np.hypot(x - ax, y - ay)
        least = []
        for p in stack.parts:
            if p.kind in ("gear", "carrier"):
                parts.append((ax, ay, p.diameter / 2 + radial, p.z_min - axial, p.z_max + axial))
            elif p.kind == "bearing":
                parts.append((ax, ay, p.diameter / 2, p.z_min, p.z_max))
                choice = chain.bearings.get((shaft, p.name.rsplit(" ", 1)[-1]))
                least.append(choice.bearing.d if choice else 0.5 * p.diameter)
        d = min(least)
        parts.append((ax, ay, d / 2, stack.ends[0], stack.ends[1]))  # the shaft, through its end walls
        if from_contract:
            continue
        # A sealed end: the seal's bore through the wall and the shaft out of the housing.
        for side, beyond in (("-z", z < stack.ends[0] + 1.0), ("+z", z > stack.ends[1] - 1.0)):
            if (shaft, side) in sealed:
                seal = (r < d / 2 + s["seal_radial"]) & beyond
                clear |= seal
                kept["seals"] |= seal
    if from_contract:
        # Each shaft's way out (the contract's): a seal's bore, taken 1 mm into the housing as the
        # generator's was, and a half-shaft's joint beyond the end face.
        kept = {"exits": np.zeros(x.shape, dtype=bool), "brackets": np.zeros(x.shape, dtype=bool)}
        for e in info["exits"]:
            into = 1.0 if e["kind"] == "seal" else 0.0
            way = (np.hypot(x - e["centre"][0], y - e["centre"][1]) < e["radius"] + margin) & (z > e["z"][0] - into) & (z < e["z"][1] + into)
            clear |= way
            kept["exits"] |= way
    # The inside: what the oil's boundary encloses. A cup per half: each room's footprint from its
    # far end in the half (its lower end in the motor side's half, its upper end in the cover's)
    # to the split; a room in one half only adds nothing to the other. A voxel is inside when most
    # of it is, in plan (5 of 3 x 3 points): the s1 gear's and the carrier's rooms overlap by
    # 1.3 mm, which no voxel centre found, so the centres' test alone left a wall a voxel thick
    # between them; the 6.9 mm web between the input's and the intermediate's -z bores stays.
    rooms = np.zeros(x.shape, dtype=bool)
    if cavity == "cup":
        votes = np.zeros(x.shape, dtype=np.int8)
        for dx in (-h / 3, 0.0, h / 3):
            for dy in (-h / 3, 0.0, h / 3):
                hit = np.zeros(x.shape, dtype=bool)
                for ax, ay, radius, z0, z1 in parts:
                    hit |= (np.hypot(x + dx - ax, y + dy - ay) < radius) & np.where(cover, z < z1, z > z0)
                votes += hit
        rooms = votes >= 5
    elif cavity == "rooms":
        for ax, ay, radius, z0, z1 in parts:
            rooms |= (np.hypot(x - ax, y - ay) < radius) & (z > z0) & (z < z1)
    else:
        raise ValueError(f"cavity {cavity!r}: 'cup' or 'rooms'")
    grown = binary_dilation(rooms.reshape(n), structure=generate_binary_structure(3, 1)).ravel()
    skin = grown & ~rooms

    # The interfaces: the motor's ring (A25) round the input, under its face, in the generator's
    # layout only (the contract has no flange); the mounts (A20).
    inp = next(st.axis for st in chain.layout.shafts if st.shaft == "input")
    out_axis = next(st.axis for st in chain.layout.shafts if st.shaft == "output")
    out_ends = next(st.ends for st in chain.layout.shafts if st.shaft == "output")
    z_face = min(st.ends[0] for st in chain.layout.shafts)
    r_in = np.hypot(x - inp[0], y - inp[1])
    motor_ring = np.zeros(x.shape, dtype=bool)
    if "motor_ring" in s:
        ring_in, ring_out = s["motor_ring"]
        t_ring = s["motor_ring_thickness"]
        motor_ring = (r_in >= ring_in / 2) & (r_in <= ring_out / 2) & (z >= z_face - t_ring) & (z <= z_face)
    mounts = np.zeros(x.shape, dtype=bool)
    for m in info["mounts"]:
        rm = np.hypot(x - m["centre"][0], y - m["centre"][1])
        mounts |= (rm <= s["mount_diameter"] / 2) & (z >= m["z"][0]) & (z <= m["z"][1])
        if not from_contract:
            ends = (rm < s["mount_diameter"] / 2 + 4) & ((z < m["z"][0]) | (z > m["z"][1]))
            clear |= ends
            kept["mount_ends"] |= ends
    if from_contract:
        for b in info["brackets"]:  # the vehicle's bracket and bolt beyond each mount's faces
            room = (np.hypot(x - b["centre"][0], y - b["centre"][1]) < b["radius"] + margin) & (z > b["z"][0]) & (z < b["z"][1])
            clear |= room
            kept["brackets"] |= room
    else:
        kept["motor"] = (r_in < s["motor_ring"][1] / 2 + 15) & (z < z_face - s["motor_ring_thickness"])  # the motor
        clear |= kept["motor"]
        ro = np.hypot(x - out_axis[0], y - out_axis[1])
        kept["half_shafts"] = (ro < 45) & ((z < out_ends[0]) | (z > out_ends[1]))  # the half-shafts' joints
        clear |= kept["half_shafts"]
    # The bolts' bosses, the two voxel layers at the split round each bolt: metal held fixed in the
    # contract's layout (an element, not design space: the engineer, 10 October 13:47), free in the
    # generator's.
    bosses = np.zeros(x.shape, dtype=bool)
    if s.get("bosses_fixed") and not flange:
        for bx, by in info["bolts"]:
            bosses |= np.hypot(x - bx, y - by) <= s["bolt_boss"] / 2
        bosses &= (k_of == k_split) | (k_of == k_split - 1)
    # The contract's split flange (`flange`): its land and the bolts' bosses, each voxel at the
    # share of it they fill.
    flange_share = np.zeros(x.shape)
    if flange:
        fl = info.get("flange")
        if not from_contract or not fl:
            raise ValueError("the split flange is the contract layout's: run contract_layout.py (11 October)")
        z_s, t_f = info["z"]["split"], fl["thickness"]
        outer = np.asarray([(*c["centre"], c["radius"]) for c in fl["outer"]])
        inner = np.asarray([(*c["centre"], c["radius"]) for c in fl["inner"]])
        bolt_xy = np.asarray(info["bolts"], float)
        r_boss, r_hole = s["bolt_boss"] / 2, s["bolt_hole"] / 2
        idx = np.nonzero(in_pack & (np.abs(z - z_s) < t_f + h))[0]
        # whole cubes (the engineer, 13 October 18:38-18:42): a cube whose centre lies in the flange is the flange's, whole, as
        # the mounts' are; no share. The flange is 8 mm deep (A26 since 18:42), two whole 4 mm cubes each side of the split.
        # A share per cube (the 4 x 4 x 4 samples below) gave its partly filled cubes the cube of their share as stiffness,
        # and they flapped in the model's own modes at 150-330 Hz.
        offs = (np.zeros(1) if flange_whole else ((np.arange(4) + 0.5) / 4 - 0.5)) * h
        filled = np.zeros(len(idx))
        for dx in offs:
            for dy in offs:
                px, py = x[idx] + dx, y[idx] + dy
                d_out = (np.hypot(px[:, None] - outer[None, :, 0], py[:, None] - outer[None, :, 1]) - outer[None, :, 2]).min(axis=1)
                d_in = (np.hypot(px[:, None] - inner[None, :, 0], py[:, None] - inner[None, :, 1]) - inner[None, :, 2]).min(axis=1)
                r_b = np.hypot(px[:, None] - bolt_xy[None, :, 0], py[:, None] - bolt_xy[None, :, 1]).min(axis=1)
                boss = (r_b <= r_boss) & (r_b >= r_hole)
                # the empty start: the land is the field's (its least height); with `protect` (LOP-28) the contract's again
                plan = boss if (empty and not protect) else ((d_out <= 0.0) & (d_in >= 0.0)) | boss
                for dz in offs:
                    filled += plan & (np.abs(z[idx] + dz - z_s) <= t_f)
        flange_share[idx] = filled / offs.size**3
    flange_cells = (flange_share > 0.0) & ~rooms
    # LOP-20 (`trade`): the trade's interfaces frozen as the skin drawing draws them
    # (`outcome_cad.skin_half`), so that the budget is the drawn housing's: each bearing's boss of
    # 1.25·D + 10 mm (grammar.py's, ITMO 2014) from its seat's inner end out past its end wall, the
    # least wall and `TRADE_PROUD` beyond, and the flange's band over the joint's outline, a flange
    # thick each side of the split. On a field that knew neither, the skin drawing came out 3.5 kg
    # past the budget (outcome_skin_6mm_max12: 11.19 kg).
    trade_parts = np.zeros(x.shape, dtype=bool)
    if trade:
        if not from_contract:
            raise ValueError("the trade's interfaces are the contract layout's")
        w_min = value_in(spec.manufacturing.min_wall, "mm")
        for b in info["bearings"]:
            rb = np.hypot(x - b["axis"][0], y - b["axis"][1])
            z0, z1 = b["z"]
            span = (z >= z0 - w_min - TRADE_PROUD) & (z <= z1) if b["side"] == "-z" else (z >= z0) & (z <= z1 + w_min + TRADE_PROUD)
            trade_parts |= (rb <= (1.25 * b["D"] + 10.0) / 2) & span
        trade_parts |= inside(np.asarray(info["joint_outline"]), x, y) & (np.abs(z - info["z"]["split"]) <= s["flange_thickness"])
        trade_parts &= ~rooms
    # Each seat's ring: the voxels within a voxel of its bore, along the bearing. With the shell it is
    # the skin's there, kept whole; the empty start (`empty`) freezes it alone, the seat's interface.
    seat_ring = np.zeros(x.shape, dtype=bool)
    for b in info["bearings"]:
        rb = np.hypot(x - b["axis"][0], y - b["axis"][1])
        seat_ring |= (rb <= b["D"] / 2 + h) & (z >= b["z"][0] - h / 2) & (z <= b["z"][1] + h / 2)
    # (LOP-29, 14 October 00:26) with the shell fixed (`shell_fixed`) no ring of its own: the shell wraps every bearing
    seat_fixed = seat_ring & ~rooms if empty and not shell_fixed else np.zeros(x.shape, dtype=bool)
    # LOP-28, the protected interfaces (the engineer, 13 October 00:50: "prevent the optimiser from deforming surfaces that
    # have a defined engineering purpose... represent the functional geometry as a preserved, non-design base"): each
    # bearing's boss, the layout's cylinder (boss_r, the trade's 1.25 D + 10) along its seat, the voxels wholly inside it
    # (their centres within half a voxel of its face), drawn in the field from its exact shape (`exact_walls.interface_density`); with the sealing land
    # above and the mounts and the bolts' bosses, the run's non-design base
    boss_fixed = np.zeros(x.shape, dtype=bool)
    if protect:
        if not empty:
            raise ValueError("--protect is the empty start's (--empty): with the shell its interfaces are the shell's")
        # each boss a castable tower (13 October 01:40): the layout's cylinder from its seat's outer end, a least wall past it,
        # down to the split (the rooms left empty), as a cast boss stands on its housing and as the drawing fills each column
        # from the split; at its seat's length alone the cylinder overhung open air (prot1_5.5kg: undercut 3.8 / 5.7 %), and
        # clipped to the lobes it shrank to a 4 mm tube wherever a seat stands past its room (prot3f: the cover's input seat
        # 1.26 x its tilt line)
        z_s = info["z"]["split"]
        # (LOP-29, `towers`) the towers left out when asked: the fixed shell keeps the floors calm, the optimiser builds the bosses
        for b in info["bearings"] if towers else []:
            rb = np.hypot(x - b["axis"][0], y - b["axis"][1])
            if b["side"] == "-z":
                span = (z >= b["z"][0] - s["wall"]) & (z < z_s)
            else:
                span = (z >= z_s) & (z <= b["z"][1] + s["wall"])
            # (LOP-29, `drawing_clear`) a cube whose centre lies in the tower is the tower's, whole, as the flange's (the drawing
            # draws the tower to boss_r: the voxels wholly inside it left a ring 2 mm thick the model never counted)
            boss_fixed |= (rb <= float(b["boss_r"]) - (0.0 if drawing_clear else h / 2)) & span
        boss_fixed &= ~rooms
        # (LOP-28, 02:45) production's panel spokes, fixed with the interfaces when asked (`LOOP_PANEL_SPOKES="<pitch>:<t>:<h>"`,
        # `LOOP_SPOKE_HALVES`, default both): radial ribs from each boss across its half's end walls, as `exact_walls.spoke_density`
        # draws them, so the optimiser sizes the rest round them (drawn alone they moved the mode 1.4 % and spoiled the tilt)
        spokes_env = os.environ.get("LOOP_PANEL_SPOKES")
        if spokes_env:
            halves_ = [v.strip() for v in os.environ.get("LOOP_SPOKE_HALVES", "cover,motor_side").split(",") if v.strip()]
            for half_ in halves_:  # the motor side's own spokes with LOOP_PANEL_SPOKES_MOTOR (03:12: they decide mode 8)
                spec_ = os.environ.get("LOOP_PANEL_SPOKES_MOTOR", spokes_env) if half_ == "motor_side" else spokes_env
                pitch, thick, high = (float(v) for v in spec_.split(":"))
                spoke = _spokes(info, rooms, x, y, z, n, z_s, s["wall"], h, pitch, thick, high, [half_])
                boss_fixed |= spoke & ~rooms
                say(f"production's panel spokes fixed ({half_}): every {pitch:g}°, {thick:g} mm thick, {high:g} mm proud; {int(spoke.sum()):,} voxels")
        # (LOP-28, 05:05) production's gusseted lugs, fixed with the interfaces when asked (`LOOP_LUG_WEBS="<thick>:<spread>"`):
        # two webs from each lug to its nearest room's wall, from the lug's far end to the split (`exact_walls.lug_webs`, drawn
        # by `exact_walls.lug_web_density`); the bolts' rooms stay clear (`clear`)
        webs_env = os.environ.get("LOOP_LUG_WEBS")
        if webs_env:
            import cup as cupmod
            import exact_walls

            w_thick, w_spread = (float(v) for v in webs_env.split(":"))
            webs_ = exact_walls.lug_webs(info, cupmod.rooms(chain, radial, axial), z_s, w_thick, w_spread)
            lug_web = np.zeros(x.shape, dtype=bool)
            for w in webs_:
                lug_web |= (exact_walls.seg_plan_dist(x, y, w["from"], w["to"]) <= w["thickness"] / 2) & (z >= w["z"][0]) & (z <= w["z"][1])
            boss_fixed |= lug_web & ~rooms
            say(f"production's gusseted lugs fixed: {len(webs_)} webs, {w_thick:g} mm thick, {w_spread:g} mm apart at the wall; {int(lug_web.sum()):,} voxels")
    if drawing_clear and flange and from_contract:
        # (LOP-29) each bolt's hole through the flange and its head's socket beyond each flange face, void, as the drawing cuts
        # and keeps them (`outcome_cad`: the hole cut exact, the socket emptied FINE_MARGIN wider): the optimiser had filled
        # them, 412 of `lop29_modes`' cubes, metal FE never saw
        z_s, t_f = info["z"]["split"], info["flange"]["thickness"]
        d_s, h_s = s.get("bolt_socket") or SOCKET
        holes = np.zeros(x.shape, dtype=bool)
        for bx, by in info["bolts"]:
            r_b = np.hypot(x - bx, y - by)
            holes |= (r_b < s["bolt_hole"] / 2) & (np.abs(z - z_s) <= t_f)
            beyond = np.where(cover, (z > z_s + t_f) & (z <= z_s + t_f + h_s), (z < z_s - t_f) & (z >= z_s - t_f - h_s))
            holes |= (r_b < d_s / 2 + margin) & beyond
        clear |= holes
        kept["bolts"] = holes
        flange_cells &= ~holes
    frozen = ((motor_ring | mounts | bosses | trade_parts | flange_cells | seat_fixed | boss_fixed) | (skin if not empty else False)) & in_pack & ~clear
    design = in_pack & ~rooms & ~clear & ~frozen
    groups = np.full(x.shape, -1, dtype=np.int64)  # the rib filter's groups (`rib_filter`), -1 for a voxel in none
    mount_discs: list = []  # (LOP-30) each mount's reach disc in plan, with the band's "disc" reach
    if band:
        # Stage 2 (the engineer, 22:51: "start from here and then define some other design
        # space"): metal only within `band` of the skin, where ribs stand, and in a corridor from
        # each mount to the skin. In the whole package run 2 stacked blocks of 78-108 mm, heavy
        # sections no foundry wants; in a band no thicker than a tall rib it must choose ribs.
        # On the contract's layout it is the height envelope (11 October, `--band`): production's
        # ribs stand 10-25 mm off their shell, no higher than the bosses they meet, where the whole
        # packaging let the field stand webs 20-100 mm proud (`docs/research/2026-10-11-production-
        # ev-housings-against-the-ribbed-cad.md`).
        from scipy.ndimage import distance_transform_edt

        off_skin = distance_transform_edt(~(skin | motor_ring).reshape(n)).ravel() * h
        near = off_skin <= band
        corridor = np.zeros(x.shape, dtype=bool)
        sx, sy = x[skin], y[skin]
        for m in info["mounts"]:
            cx_, cy_ = m["centre"]
            j = int(np.argmin((sx - cx_) ** 2 + (sy - cy_) ** 2))
            if mount_reach == "disc":
                # (LOP-30) each disc kept: a mount's bracket region, whose depth the lug's place sets (`topo.spline_setup`'s
                # section window leaves its columns their full height)
                mount_discs.append({"name": m["name"], "centre": [float(cx_), float(cy_)],
                                    "reach_mm": float(np.hypot(sx[j] - cx_, sy[j] - cy_)) + band,
                                    "half": 0 if m["z"][1] <= info["z"]["split"] else 1})  # fmt: skip
                # Everything within reach of the mount, all the way to the shell, at the mount's
                # height and the band's past it (11 October 13:10): the optimiser chooses the arm's
                # path and form. The corridor below, a straight strip as wide as the band from the
                # mount to the nearest wall point, fixed each arm's path (the engineer, 13:08:
                # nothing may constrain the creativity).
                reach_m = float(np.hypot(sx[j] - cx_, sy[j] - cy_)) + band
                z_lo, z_hi = m["z"][0] - band, m["z"][1] + band
                if height_field:
                    # with the height field each column is one run from the split: the region
                    # reaches the split, so a mount's arms hang from the flange as gussets (cut 9 mm
                    # under it, their tops were the undercut faces castability found at z 5.3 mm)
                    z_s = info["z"]["split"]
                    z_lo, z_hi = (z_lo, max(z_hi, z_s)) if m["z"][1] <= z_s else (min(z_lo, z_s), z_hi)
                corridor |= (np.hypot(x - cx_, y - cy_) <= reach_m) & (z >= z_lo) & (z <= z_hi)
                continue
            ax_, ay_ = sx[j], sy[j]
            seg = np.array([ax_ - cx_, ay_ - cy_])
            length2 = max(float(seg @ seg), 1e-9)
            t = np.clip(((x - cx_) * seg[0] + (y - cy_) * seg[1]) / length2, 0.0, 1.0)
            d_plan = np.hypot(x - (cx_ + t * seg[0]), y - (cy_ + t * seg[1]))
            corridor |= (d_plan <= band / 2) & (z >= m["z"][0] - band) & (z <= m["z"][1] + band)
        if ribs:
            # LOP-23: within the band, only the production rib network (`rib_network`), each half
            # its own bores' wheels, and the corridors to the mounts
            net = np.zeros(x.shape, dtype=bool)
            first = 0
            for lower in (True, False):
                half = ~cover if lower else cover
                wall_xy = np.column_stack([x[skin & half], y[skin & half]])
                inside_xy = (rooms & half).reshape(tuple(n)).any(axis=2)
                if rib_filter:
                    # each piece of the network (`parts`) at each height off the shell one group:
                    # the rib filter gives its voxels one density (`topo.Voxels`), so each piece
                    # stands at one height, as production's ribs do
                    prims = rib_network(info, xc, yc, h, lower, wall_xy, parts=True)
                    if ribs_from:
                        prims += _tiles(field_lines(ribs_from, n, lo, h, k_split, lower), xc, yc)
                    if fins:
                        prims += side_fins(inside_xy, xc, yc, h, band, parts=True)
                    label = np.full((n[0], n[1]), -1, dtype=np.int64)
                    for idx, p in enumerate(prims):
                        label[p & (label < 0)] = first + idx
                    first += len(prims)
                    plan = label >= 0
                    lab3 = np.broadcast_to(label[:, :, None], tuple(n)).ravel()
                    level = np.rint(off_skin / h).astype(np.int64)
                    groups = np.where(half & (lab3 >= 0), lab3 * 64 + level, groups)
                else:
                    plan = rib_network(info, xc, yc, h, lower, wall_xy)
                    if ribs_from:  # the load paths a free run found, as lines beside the wheels
                        plan |= field_lines(ribs_from, n, lo, h, k_split, lower)
                    if fins:  # fins up the side walls at a pitch
                        plan |= side_fins(inside_xy, xc, yc, h, band)
                net |= np.broadcast_to(plan[:, :, None], tuple(n)).ravel() & half
            near &= net
        design &= near | corridor
    if space:  # LOP-24: the agent's design space for this iteration, each half's regions in plan
        design &= space_mask(space, x, y, cover, info, band or 24.0)
    kind = np.full(x.shape, -1, dtype=np.int8)
    kind[design] = 0
    kind[frozen] = 1
    r_boss = info["settings"]["bolt_boss"] / 2
    if joint == "bolts":
        tie = {"k_split": k_split, "bolts": [tuple(b) for b in info["bolts"]], "radius": r_boss}
    elif joint == "glued":
        tie = None
    else:
        raise ValueError(f"joint {joint!r}: 'bolts' or 'glued'")
    # Nothing left hanging: a voxel joined to the supported body by an edge or a corner at most
    # is a hinge, a mechanism of no stiffness, and the stiffness is singular there. Releasing the
    # split outside the bolts left a 19-voxel column of free voxels at (160, 59) so (10 October
    # 01:20): the loads never touched it, but some refinements crawled and a random load could not
    # be solved at all. Free voxels so joined are left out of the model; a frozen one would be a
    # fault in the set-up, and stops it.
    loose = hanging(kind, n, lo, h, tie, mounts & (kind >= 0))
    if np.any(loose & (kind == 1)):
        raise RuntimeError(f"{int((loose & (kind == 1)).sum())} frozen voxels hang by an edge or a corner: the set-up is faulty")
    kind[loose] = -1
    design &= ~loose
    height_min, least_fill = least_heights(kind, rooms, n, k_split, h, lo, info, spec) if empty else (None, None)
    shell_voxels = 0
    if shell_fixed:
        # (LOP-29) the 4 mm shell protected: every cube the least walls make metal (each column's least height rounded to
        # whole cubes, as the projection rounds it) frozen whole, so the optimiser only adds on top of it
        if not empty:
            raise ValueError("the protected shell is the empty start's least walls, frozen: give empty")
        elem_ = np.flatnonzero(kind >= 0)
        free_e_ = np.flatnonzero(kind[elem_] == 0)
        col_, pos_, _, _ = topo.height_columns(kind, n, k_split, elem_, free_e_)
        tmin_ = np.zeros(int(col_.max()) + 1)
        np.maximum.at(tmin_, col_, np.asarray(height_min, float)[elem_[free_e_]])
        idx = elem_[free_e_][pos_ + 0.5 < tmin_[col_]]
        kind[idx] = 1
        frozen[idx] = True
        design[idx] = False
        shell_voxels = len(idx)
        height_min = np.zeros_like(height_min)  # nothing left to hold: the shell is fixed

    # The skin's voxels stand for the least wall: mass t/h, stiffness (t/h)^3 (the docstring says
    # why). A bearing's bore is a boss, never a 4 mm wall: the skin's voxels round each seat (within
    # a voxel of its bore, along the bearing) stay whole, else the seat would sit on a soft layer
    # whatever boss the optimiser built round it.
    wall = value_in(spec.manufacturing.min_wall, "mm") if wall_asked is None else float(wall_asked)
    share = wall / h if 0.0 < wall < h else 1.0
    in_flange = frozen & flange_cells
    thin = frozen & skin & ~motor_ring & ~mounts & ~seat_ring & ~bosses & ~trade_parts & ~in_flange
    if empty:  # no skin fixed: nothing stands for the least wall
        thin = np.zeros(x.shape, dtype=bool)
    stiffness = np.ones(x.shape)
    stiffness[thin] = share**3
    mass_share = np.ones(x.shape)  # each fixed voxel's modelled mass, a share of the voxel's
    mass_share[thin] = share
    if flange:
        whole = (skin & seat_ring) | mounts | motor_ring
        if empty:  # the bosses at the share they fill; the seats' rings and the mounts whole
            whole = seat_fixed | mounts | motor_ring
            f = flange_share
        else:
            f = np.where(skin & ~whole, np.maximum(flange_share, share), flange_share)
        f = np.where(whole, 1.0, f)
        mass_share[in_flange] = f[in_flange]
        stiffness[in_flange] = f[in_flange] ** 3
    wall_scale = 1.0
    if flange and info.get("fixed_exact_kg") and not empty:  # the exact fixed metal holds the wall, which the empty start leaves free
        # The fixed voxels weigh what the drawing's exact fixed metal weighs (`contract_layout.py`'s
        # `fixed_exact_kg`): the 6 mm cubes alone counted the wall 0.24 kg light (11 October 00:33),
        # so the drawing came out heavier than the budget. The wall's voxels (the thin skin and the
        # seats' rings) carry the difference, in mass only; their stiffness stays as modelled.
        walls = frozen & ((thin) | (skin & seat_ring & ~mounts & ~motor_ring & ~in_flange))
        target = info["fixed_exact_kg"]["total"] / (h**3 * DENSITY)
        rest = float(mass_share[frozen & ~walls].sum())
        wall_scale = (target - rest) / float(mass_share[walls].sum())
        mass_share[walls] *= wall_scale
    frozen_kg = float(mass_share[frozen].sum()) * h**3 * DENSITY
    skin_note = {"wall_mm": wall if share < 1.0 else h, "mass_share": share, "stiffness_share": share**3, "voxels": int(thin.sum()),
                 "seat_voxels_whole": int((frozen & skin & seat_ring & ~motor_ring & ~mounts).sum())}  # fmt: skip
    if flange:
        skin_note["flange"] = {"voxels": int(in_flange.sum()), "kg": float(mass_share[in_flange].sum()) * h**3 * DENSITY}
        skin_note["wall_mass_scale"] = wall_scale
    if empty:  # no skin stands for a wall (the run's stem says `empty`, not a skin's thickness)
        skin_note.update(wall_mm=0.0, mass_share=1.0, stiffness_share=1.0, empty=True)

    model = {"info": info, "spec": spec, "chain": chain, "h": h, "lo": lo, "n": n, "kind": kind,
             "inp": inp, "z_motor": z_face, "k_split": k_split, "band": band, "cavity": cavity,
             "stiffness": stiffness, "mass_share": mass_share, "skin": skin_note, "flange": flange,
             "mount_discs": mount_discs}  # fmt: skip
    if rib_filter:  # LOP-23: each rib piece's voxels at one height share one density (`topo.Voxels`)
        model["groups"] = np.where(design, groups, -1)
    # The manufacturing route is a design variable (Virostko et al. 2026, generative design of gear
    # bodies: each route a set of constraints, each giving its own outcome): "cast", a two-part
    # mould split at the halves' joint, keeps every column one interval along the pull; "free"
    # (additive) takes no such constraint.
    model["route"] = route
    model["cast"] = casting_filter(kind, n, k_split, anchored=route == "split") if route in ("cast", "split") else None
    if height_field:  # one smooth height a column (`topo.Voxels`): castable by construction, no casting filter
        model["cast"] = None
        model["height_field"] = {"radius_mm": float(height_field)}
    if empty:  # LOP-27: the walls the optimiser's, each run at least its least height (`least_heights`)
        model["empty"] = True
        model["shell_fixed"] = bool(shell_fixed)
        model["towers"] = bool(towers)
        if shell_fixed:
            say(f"the 4 mm shell protected: {shell_voxels:,} cubes of the least walls frozen whole; the optimiser adds on top of it")
        model["height_min"] = height_min
        least_kg = float(least_fill.sum()) * h**3 * DENSITY
        model["least_kg"] = least_kg
        say(("the empty start with the shell fixed: the 4 mm shell, the sealing land and the bolts' bosses, the mounts "
             if shell_fixed else "the empty start: no shell fixed; the seats' rings, the mounts and the bolts' bosses ")
            + f"({frozen_kg:.2f} kg fixed); the walls' least metal about {least_kg:.2f} kg"
            + (", inside the shell" if shell_fixed else ", the optimiser's to place and to grow"))  # fmt: skip
    if protect:  # LOP-28: the protected interfaces, the run's non-design base (drawn exact)
        model["protect"] = True
        say("the protected interfaces: " + (f"the bearings' bosses ({int((boss_fixed & in_pack & ~clear).sum()):,} voxels), " if towers else "no bearing towers, ")
            + f"the sealing land and the "
            f"bolts' bosses ({int(flange_cells.sum()):,}), the mounts ({int(mounts.sum()):,}); {frozen_kg:.2f} kg fixed in all")  # fmt: skip
    # Driven to solid and void: the projection's sharpness doubles every 40 iterations from 1 to
    # 16, then the steps shrink until the field settles (run 1 left 54 % of its metal grey).
    model["projection"] = PROJECTION
    model["penalty_ramp"] = penalty_ramp
    in_boss = np.zeros(x.shape, dtype=bool)
    for bx, by in info["bolts"]:
        in_boss |= np.hypot(x - bx, y - by) <= r_boss
    model["joint"] = tie
    model["joint_kind"] = joint
    model["couplings"] = couplings  # (LOP-29) "kinematic": FE's rigid couplings (`topo.Voxels`, `couplings.py`); "glue" before
    model["frozen_kg"] = frozen_kg
    model["left_out"] = int(loose.sum())
    say(f"model {n.tolist()} voxels of {h:g} mm, the cavity {cavity}: {frozen.sum():,} frozen ({frozen_kg:.2f} kg: skin {skin_note['voxels']:,} "
        f"as a {skin_note['wall_mm']:g} mm wall and {skin_note['seat_voxels_whole']:,} round the seats whole, motor ring {motor_ring.sum():,}, "
        f"mounts {mounts.sum():,}" + (f", the split flange {skin_note['flange']['voxels']:,} at {skin_note['flange']['kg']:.2f} kg" if flange else "")
        + f"), {design.sum():,} free; the halves {joint}" + (f"; {int(loose.sum())} free voxels hanging by an edge left out" if loose.any() else ""))  # fmt: skip
    # every kind of space, for pictures of the set-up (`topo_setup.py`)
    at_split = (k_of == k_split) | (k_of == k_split - 1)
    model["masks"] = {"pack": in_pack, "rooms": rooms, "clear": clear & in_pack, "skin": skin & in_pack & ~clear,
                      "ring": motor_ring & in_pack & ~clear, "mounts": mounts & in_pack & ~clear, "design": design,
                      "trade": trade_parts & in_pack & ~clear, "flange": in_flange,
                      "bolts": in_boss & at_split & (kind >= 0), "bosses": bosses & in_pack & ~clear,
                      "wall": thin, "seats": frozen & skin & seat_ring & ~motor_ring & ~mounts,
                      **{f"clear_{k}": v & in_pack for k, v in kept.items()}}  # fmt: skip
    return model


def _spokes(info: dict, rooms: np.ndarray, x, y, z, n, z_s: float, wall: float, h: float, pitch: float, thick: float, high: float,
            halves: list[str]) -> np.ndarray:  # fmt: skip
    """(LOP-28) Production's panel spokes on the voxel grid, as `exact_walls.spoke_density` draws them: in plan within
    `thick`/2 of a ray every `pitch` degrees from each of the half's bearing bosses (from its boss radius out), on every column
    standing on a room in that half, from the room's far face out a wall and the spoke's height."""
    nn = tuple(int(v) for v in n)
    r3 = rooms.reshape(nn)
    gx, gy = x.reshape(nn)[:, :, 0], y.reshape(nn)[:, :, 0]
    zc = z.reshape(nn)[0, 0, :]
    k_idx = np.arange(nn[2])[None, None, :]
    out = np.zeros(nn, bool)
    for half in halves:
        lower = half == "motor_side"
        rh = r3 & ((zc < z_s) if lower else (zc >= z_s))[None, None, :]
        has = rh.any(axis=2)
        face = np.where(rh, k_idx, nn[2]).min(axis=2) if lower else np.where(rh, k_idx, -1).max(axis=2)
        plan = np.zeros(nn[:2], bool)
        for b in info["bearings"]:
            if (b["side"] == "-z") != lower:
                continue
            dx, dy = gx - b["axis"][0], gy - b["axis"][1]
            r = np.hypot(dx, dy)
            th = np.degrees(np.arctan2(dy, dx)) % pitch
            plan |= (r >= float(b["boss_r"]) - 2.0) & (np.radians(np.minimum(th, pitch - th)) * r <= thick / 2)
        plan &= has
        for step in range(1, int(np.ceil((wall + high) / h)) + 1):
            kk = face - step if lower else face + step
            ok = plan & (kk >= 0) & (kk < nn[2])
            ii, jj = np.nonzero(ok)
            out[ii, jj, kk[ok]] = True
    return out.ravel()


def least_heights(kind: np.ndarray, rooms: np.ndarray, n: np.ndarray, k_split: int, h: float, lo: np.ndarray, info: dict, spec) -> tuple[np.ndarray, np.ndarray]:
    """The empty start's oil-tightness (LOP-27): each run's least height along the pull, in its own
    free voxels, given to each of the run's free voxels (0: none), and each free voxel's share of
    metal that least height alone puts there (for the walls' least mass).

    A run is a column's stretch of modelled voxels in one half, from the split outward (as
    `topo.height_columns` reads them). It stands on a room when the voxel before its first, toward
    the split, is the inside's; at the split when it starts on the split's layer. Its least height
    above the split (mm) is the most of:
    - the end wall: its room's depth and the least wall, on a room;
    - the side wall: the deepest room of the half within a voxel of it in plan (8 neighbours), and
      the least wall, where that room is deeper than its own base: the side of every room, the
      steps between rooms of different depths and the bearings' pockets included;
    - the plate over the other half's wider opening: the least wall, at the split where the other
      half's inside reaches the split and its own does not;
    - the sealing land (A26): the flange's depth, at the split within the land's width of the
      inside, outside it;
    - a seal's seat (A16): the seal's length behind its bearing, on a room within the least wall
      and a voxel of a sealed exit's bore, in the exit's half.
    Less its base (the room's depth, or 0 at the split), less the frozen voxels within it wherever
    they stand (a bolt's boss, a seat's ring), in the run's free voxels' own count."""
    from scipy.ndimage import distance_transform_edt, maximum_filter

    wall = value_in(spec.manufacturing.min_wall, "mm")
    t_f, land_w = float(info["flange"]["thickness"]), float(info["flange"]["land_width"])
    seat = value_in(spec.requirement.shaft_layout.behind_bearing_sealed, "mm")
    z_s = float(info["z"]["split"])
    grid, room = kind.reshape(tuple(n)), rooms.reshape(tuple(n))
    need = np.zeros(tuple(n))
    fill = np.zeros(tuple(n))
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    px, py = np.meshgrid(xc, yc, indexing="ij")
    own = {0: room[:, :, k_split - 1], 1: room[:, :, k_split]}  # each half's inside at the split (every room of the cup runs to it)
    inside_u = own[0] | own[1]
    off_u = distance_transform_edt(~inside_u) * h  # each cell's distance in plan from the inside at the split, mm
    for half in (0, 1):
        ks = np.arange(k_split - 1, -1, -1) if half == 0 else np.arange(k_split, n[2])  # from the split outward
        g, r = grid[:, :, ks], room[:, :, ks]
        depth = np.where(own[half], r.sum(axis=2) * h, 0.0)  # each column's rooms from the split, mm
        beside = maximum_filter(depth, size=3, mode="constant", cval=0.0)  # the deepest room within a voxel in plan
        plate = inside_u & ~own[half]
        land = ~inside_u & (off_u <= land_w + 1e-6)
        seal_ring = np.zeros(depth.shape, dtype=bool)
        for e in info.get("exits") or []:
            if e["kind"] != "seal" or (e["z"][1] <= z_s) != (half == 0):
                continue
            seal_ring |= np.hypot(px - e["centre"][0], py - e["centre"][1]) <= e["radius"] + wall + h
        for i, j in zip(*np.nonzero((g >= 0).any(axis=2)), strict=True):
            col, rc = g[i, j], r[i, j]
            k, top = 0, len(col)
            while k < top:
                if col[k] < 0:
                    k += 1
                    continue
                end = k
                while end < top and col[end] >= 0:
                    end += 1
                on_room = k > 0 and rc[k - 1]
                base = depth[i, j] if on_room else 0.0
                above = 0.0  # the least height above the split, mm
                if on_room:
                    above = base + wall
                    if seal_ring[i, j]:
                        above = max(above, base + seat)
                if beside[i, j] > base:
                    above = max(above, beside[i, j] + wall)
                if k == 0:  # at the split
                    if plate[i, j]:
                        above = max(above, wall)
                    if land[i, j]:
                        above = max(above, t_f)
                if (k == 0 or on_room) and above > base:
                    # (14 October) each free voxel filled by the share of it the span covers, by its own offset from the run's
                    # start, frozen voxels counted wherever they stand: subtracting only the frozen voxels at the start, while
                    # a free voxel's place skips every frozen one, ran a wall on past a seat's ring by the ring's length
                    span = (above - base) / h
                    free_here = np.flatnonzero(col[k:end] == 0) + k
                    share = np.clip(span - (free_here - k), 0.0, 1.0)
                    need[i, j, ks[free_here]] = float(share.sum())
                    fill[i, j, ks[free_here]] = share
                k = end
    return need.ravel(), fill.ravel()


def hanging(kind: np.ndarray, n: np.ndarray, lo: np.ndarray, h: float, tie: dict | None, anchor: np.ndarray) -> np.ndarray:
    """The modelled voxels not joined face to face to the supported body (`anchor`, the mounts'
    voxels): two voxels are joined when they share a face, and across the split only where the
    halves are joined. With `tie` None (glued) every face across the split joins; with the bolted
    joint (`tie`: k_split, bolts, radius) only a face whose four corners all lie within a bolt
    boss's footprint, as `topo.released_at_split` ties them. Returns a flat mask."""
    from scipy.ndimage import label

    modelled = (kind >= 0).reshape(n)
    six = generate_binary_structure(3, 1)
    if tie is None:
        labels, _ = label(modelled, structure=six)
        anchored = np.unique(labels[anchor.reshape(n)])
        return (modelled & ~np.isin(labels, anchored[anchored > 0])).ravel()
    ks = tie["k_split"]
    lower, upper = modelled.copy(), modelled.copy()
    lower[:, :, ks:] = False
    upper[:, :, :ks] = False
    lab_lo, n_lo = label(lower, structure=six)
    lab_up, n_up = label(upper, structure=six)
    labels = lab_lo + np.where(lab_up > 0, lab_up + n_lo, 0)
    # the faces across the split tied whole: all four corner nodes in a bolt boss's footprint
    ni, nj = np.meshgrid(np.arange(n[0] + 1), np.arange(n[1] + 1), indexing="ij")
    px, py = lo[0] + h * ni, lo[1] + h * nj
    tied = np.zeros(ni.shape, dtype=bool)
    for bx, by in tie["bolts"]:
        tied |= np.hypot(px - bx, py - by) <= tie["radius"]
    face = tied[:-1, :-1] & tied[1:, :-1] & tied[:-1, 1:] & tied[1:, 1:]
    across = face & modelled[:, :, ks - 1] & modelled[:, :, ks]
    parent = np.arange(n_lo + n_up + 1)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in zip(labels[:, :, ks - 1][across], labels[:, :, ks][across], strict=True):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    root = np.array([find(i) for i in range(len(parent))])
    comp = root[labels]
    anchored = np.unique(comp[anchor.reshape(n) & modelled])
    anchored = anchored[anchored != root[0]]
    return (modelled & ~np.isin(comp, anchored)).ravel()


def casting_filter(kind: np.ndarray, n: np.ndarray, k_split: int, anchored: bool = False):
    """Each half's columns along the pull filled between metal: rho~ = 1 - (1 - rho)(1 - A B), A
    the chance of metal below in the same run, B above (soft ORs, products of 1 - rho). A run
    breaks at a voxel not modelled (a room, a kept-clear space, outside) and at the split, so no
    fill reaches across a cavity or from one half into the other. Returns (forward, backward) over
    the modelled elements' densities, in `solve_model`'s order (flat index order).

    `anchored`: the fill runs from the run's start nearest the split (the split itself, or the
    cavity a skin stands on) out to the last metal: the factor toward the split is taken as 1 (A in
    the cover, B in the motor side), so a strut never hangs off the split with air under it. A
    two-part mould parted at the halves' joint needs that: drawn as CAD, the gap-filled field of
    run 3 needed 2.6 kg of curtains from its struts down to the split to be cast (10 October 03:06).
    The derivative is the same formula with that factor held at 1."""
    elem = np.flatnonzero(kind >= 0)
    frozen = (kind[elem] == 1)
    modelled = (kind >= 0).reshape(n)
    k_index = np.arange(n[2])[None, None, :]
    # a run starts where the voxel below is not modelled, or at the split
    below = np.concatenate([np.zeros((n[0], n[1], 1), bool), modelled[:, :, :-1]], axis=2)
    starts = modelled & (~below | (k_index == k_split))
    above = np.concatenate([modelled[:, :, 1:], np.zeros((n[0], n[1], 1), bool)], axis=2)
    ends = modelled & (~above | (k_index == k_split - 1))

    # Where each voxel's run starts (forward and reversed): fixed by the model, found once (LOP-20,
    # 11 October: found again in every one of an iteration's 14 backward passes before).
    def run_start(first):
        last = np.maximum.accumulate(np.where(first, k_index, -1), axis=2)
        return np.clip(last, 0, None), last >= 0

    start_at, start_ok = run_start(starts)
    end_at, end_ok = run_start(ends[:, :, ::-1])

    def seg_cumsum(v, at, ok):
        """Inclusive cumulative sums along z (the last axis) restarting at each run's first voxel
        (`at`, `ok` from `run_start`); v may carry leading axes (one row per function)."""
        c = np.cumsum(v, axis=-1)
        padded = np.concatenate([np.zeros(c.shape[:-1] + (1,)), c], axis=-1)
        before = np.take_along_axis(padded, np.broadcast_to(at, c.shape), axis=-1)
        return c - np.where(ok, before, 0.0)

    def rev(a):
        return a[..., ::-1]

    def parts(rho_e):
        grid = np.zeros(int(np.prod(n)))
        r = np.clip(rho_e, 0.0, 1.0 - FLOOR)
        r[frozen] = 1.0 - FLOOR
        grid[elem] = r
        g = grid.reshape(n)
        lg = np.where(modelled, np.log1p(-g), 0.0)
        incl = seg_cumsum(lg, start_at, start_ok)  # log prod over the run up to k, inclusive
        incl_rev = rev(seg_cumsum(rev(lg), end_at, end_ok))  # from k to the run's end, inclusive
        a = 1.0 - np.exp(incl - lg)  # metal strictly below k in its run
        b = 1.0 - np.exp(incl_rev - lg)  # strictly above
        if anchored:
            a = np.where(k_index >= k_split, 1.0, a)  # the cover: from the split up
            b = np.where(k_index < k_split, 1.0, b)  # the motor side: from the split down
        return g, a, b

    def forward(rho_e):
        g, a, b = parts(rho_e)
        out = 1.0 - (1.0 - g) * (1.0 - a * b)
        res = out.ravel()[elem]
        res[frozen] = 1.0
        return res

    _last = [None, None]  # the last forward pass's densities and its parts: the backward pass is taken there

    def backward(dj_e):
        """dJ/drho from dJ/drho~ (both over the modelled elements), at the last forward's rho; for
        one function (n_e,) or many at once (rows, n_e), the forward's parts kept from it."""
        g, a, b = _last[1] if _last[1] is not None else parts(_last[0])
        rows = np.atleast_2d(dj_e)
        gj = np.zeros((len(rows), int(np.prod(n))))
        gj[:, elem] = rows
        gj = gj.reshape((len(rows), *n))
        one = 1.0 - g
        q = np.where(modelled, gj * (one * b * (1.0 - a)), 0.0)  # pulls on metal below k
        r_ = np.where(modelled, gj * (one * a * (1.0 - b)), 0.0)  # pulls on metal above k
        q_after = rev(seg_cumsum(rev(q), end_at, end_ok)) - q  # sum over k' > k in the run
        r_before = seg_cumsum(r_, start_at, start_ok) - r_  # sum over k' < k in the run
        d = gj * (1.0 - a * b) + (q_after + r_before) / one
        res = d.reshape(len(rows), -1)[:, elem]
        res[:, frozen] = 0.0
        return res if np.ndim(dj_e) == 2 else res[0]

    def forward_kept(rho_e):
        _last[0] = np.array(rho_e, dtype=float)
        _last[1] = parts(_last[0])
        g, a, b = _last[1]
        out = 1.0 - (1.0 - g) * (1.0 - a * b)
        res = out.ravel()[elem]
        res[frozen] = 1.0
        return res

    return forward_kept, backward


def full_speed() -> bool:
    """Ask Windows to run this process at full speed, as a foreground program runs, never held to
    the efficiency cores and their low clock as windowless background work (CLAUDE.md's pitfall:
    an overnight run started in the background would otherwise crawl). Whether it was granted;
    nothing off Windows. After fastcae-v1:src/fastcae/runner/__init__.py's `full_speed`, the same
    call (power throttling of execution speed turned off for this process)."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    class _Throttling(ctypes.Structure):
        _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetProcessInformation.restype = wintypes.BOOL
    state = _Throttling(1, 0x1, 0x0)  # version 1; execution speed under our control, not throttled
    power_throttling = 4  # PROCESS_INFORMATION_CLASS.ProcessPowerThrottling
    return bool(kernel.SetProcessInformation(kernel.GetCurrentProcess(), power_throttling, ctypes.byref(state), ctypes.sizeof(state)))


def run_stem(objective: str, budget: float, h: float, band: float | None, cavity: str, joint: str, model: dict, tag: str = "") -> str:
    """A run's file stem: its objective, budget and voxel, then its model's choices. A run on the
    contract's layout says so ("contract"), so it never overwrites a run on the generator's."""
    if model["info"].get("form") == "contract":
        tag = f"contract_{tag}" if tag else "contract"
    if model.get("route", "cast") != "cast":
        tag = f"{model['route']}_{tag}" if tag else model["route"]
    skin = model["skin"]
    return (f"topofree_{objective}_{budget:g}kg_{h:g}mm_projected" + (f"_band{band:g}" if band else "")
            + f"_{cavity}_{joint}" + (f"_skin{skin['wall_mm']:g}" if skin["mass_share"] < 1.0 else "") + (f"_{tag}" if tag else ""))  # fmt: skip


def main(budget: float = 7.73, h: float = 6.0, iterations: int = 200, band: float | None = None,
         objective: str = "misalignment_bound", joint: str = "bolts", skin: float | None = None,
         cavity: str = "cup", tag: str = "", resume: bool = False, ramp: int = PENALTY_RAMP, route: str = "cast",
         robust: float = 0.0, start_from: str = "", beta_start: float = 1.0, robust_p: float = 0.0,
         cases: tuple[str, ...] = (), beta_most: float | None = None, every: int | None = None,
         settle: float | None = None, max_member: float | None = None, trade: bool = False, beds: bool = False,
         ribs: bool = False, ribs_from: str = "", fins: bool = False, rib_filter: bool = False,
         plan_gap: float | None = None, plan_width: float = 8.0, height_field: float | None = None, safety: float = 1.0,
         space: str = "", safety_beds: float | None = None, height_features: str = "", height_volumes: str = "", parts: str = "",
         perimeter: float | None = None, empty: bool = False, bending: str = "", brackets: str = "", protect: bool = False,
         modes: float = 0.0, shell_fixed: bool = False, towers: bool = True, first_mode: float = 0.0,
         first_margin: float = 0.0, least_width: float = 0.0, spline: str = "", least_gap: float = 0.0,
         outline: float = 0.0, section: str = "", top: bool = False, window: str = "", disc: bool = False, soft_dist: bool = False,
         spline_bend: str = "", lump_fixed: float = 0.0, sizes: float = 0.0, window_free: str = "mounts", penal_most: float = 0.0,
         window_split: str = "", lump_floor: float = 0.0, gap_shell: bool = False, fair: str = "") -> None:  # fmt: skip
    """Build the model, optimise it, save the field (`<stem>.npz`: the densities `phys` and the
    design variables `x`), its record (`<stem>.json`) and its picture (`<stem>.png`). Every
    `CHECKPOINT_EVERY` iterations the field so far goes to `<stem>_checkpoint.npz`; `resume`
    carries a stopped run on from there (MMA's asymptotes start afresh).
    - `robust` (a threshold's shift, e.g. 0.2): the robust formulation (`topo.solve_model`), the
      stem tagged `robust<d>`; `robust_p` (e.g. 16): each seat and case's realisations one
      constraint, their p-norm (the stem unchanged, so a run can resume with it).
    - `start_from` (a run's stem): its design variables as the start, at sharpness `beta_start`
      (the same model's voxels; a warm start).
    - `cases`: the load cases by name (default both peaks); one case is said in the stem
      ("drive" for peak drive alone)."""
    t0 = time.time()
    fast = full_speed()
    # The contract's split flange held fixed and the split on a voxel face (11 October), on the
    # contract's layout; every run before had neither (`build_free`'s `flange`).
    flange = LAYOUT == "contract"
    ribs = ribs or bool(ribs_from) or fins or rib_filter
    # Within a band each mount reaches the shell through all its neighbourhood (`mount_reach`
    # "disc"), the run's record says so; runs before 11 October 13:10 had a straight corridor
    mount_reach = "disc"
    model = build_free(h, band=band, joint=joint, skin=skin, cavity=cavity, penalty_ramp=ramp, route=route, trade=trade, flange=flange,
                       ribs=ribs, ribs_from=ribs_from, fins=fins, rib_filter=rib_filter, mount_reach=mount_reach,
                       height_field=height_field, space=space, empty=empty, protect=protect, drawing_clear=True, couplings="kinematic",
                       shell_fixed=shell_fixed, towers=towers)  # fmt: skip
    if empty:  # LOP-27: no fixed shell, the walls the optimiser's (`build_free`'s `empty`)
        tag = f"{tag}_empty" if tag else "empty"
    if shell_fixed:  # LOP-29: the 4 mm shell protected
        tag = f"{tag}_shell"
    if protect and not towers:  # LOP-29: the bearing towers left out of the protected set
        tag = f"{tag}_notowers"
    if protect:  # LOP-28: the bearings' bosses, the sealing land, the bolts' bosses and the mounts a non-design base, drawn exact
        tag = f"{tag}_protect"
    if modes > 0:  # LOP-29: the model's modes held clear of the gear orders, `modes` each side (`topo.mode_gaps`)
        model["modes"] = {"margin": float(modes), "count": topo.MODE_COUNT, "first": float(first_mode), "first_margin": float(first_margin)}
        tag = f"{tag}_modes{100 * modes:g}" + (f"_fm{first_mode:g}" if first_mode > 0 else "") + (f"m{100 * first_margin:g}" if first_mode > 0 and first_margin > 0 else "")
    if space:  # LOP-24: the agent's design space, named after its file
        # cuDSS's SPD factorisation hung four times on a restricted space (11 October 20:51-22:01), never returning;
        # the symmetric, pivoting one ran through (`fast_factor.factor`, LOOP_FACTOR_KIND)
        os.environ.setdefault("LOOP_FACTOR_KIND", "SYMMETRIC")
        tag = f"{tag}_space{Path(space).stem}" if tag else f"space{Path(space).stem}"
    if height_field:  # LOP-23: one smooth height a column (`topo.Voxels`)
        tag = f"{tag}_hf{height_field:g}" if tag else f"hf{height_field:g}"
    model["trade"] = trade
    if ribs:  # the production rib network as the design space (LOP-23), with a free run's lines, with fins, each piece at one height
        word = "ribs" + ("field" if ribs_from else "") + ("fins" if fins else "") + ("uni" if rib_filter else "")
        tag = f"{word}_{tag}" if tag else word
    if trade:  # the trade's bosses and flange frozen (LOP-20)
        tag = f"trade_{tag}" if tag else "trade"
    if cases:
        model["cases"] = tuple(cases)
        if set(cases) != {"peak drive", "peak reverse"}:
            only = "_".join(c.replace("peak ", "") for c in cases)
            tag = f"{only}_{tag}" if tag else only
    # The sharpening's schedule (LOP-19): its last sharpness, its longest stay at one, and with
    # `settle` the doubling as soon as the design settles: one run in place of stages ("single").
    schedule = {k: v for k, v in (("beta_most", beta_most), ("every", every), ("settle", settle)) if v}
    if schedule:
        model["projection"] = dict(model["projection"], **schedule)
    if settle:
        tag = f"{tag}_single" if tag else "single"
    if robust:
        model["projection"] = dict(model["projection"], robust=robust, **({"robust_p": robust_p} if robust_p else {}))
        tag = f"{tag}_robust{robust:g}" if tag else f"robust{robust:g}"
    if max_member:
        # The greatest member (LOP-20; `topo.greatest_share`): a ball of radius R round each free
        # voxel holds at most 0.6 placed metal, which a slab reaches at t = 0.85 R, so R = t / 0.849.
        model["max_member"] = {"mm": max_member, "alpha": 0.6, "radius_vox": max_member / 0.849 / h}
        member_p = float(os.environ.get("LOOP_MEMBER_P", "0") or 0.0)  # LOP-25: the rule read nearer its worst ball (12 October 15:27)
        if member_p > 0:
            model["max_member"]["p"] = member_p
            tag = f"{tag}_p{member_p:g}"
        tag = f"{tag}_max{max_member:g}" if tag else f"max{max_member:g}"
        if lump_fixed > 0:  # LOP-30 (the engineer, 14 October 23:01): the lump rule counting the land and the bolts' bosses
            model["max_member"]["fixed_mm"] = float(lump_fixed)
            tag = f"{tag}f{lump_fixed:g}"
            if lump_floor > 0:  # (15 October 03:45) held so it can be met: each ball's placed metal against what the fixed leaves
                model["max_member"]["floor"] = float(lump_floor)
                tag = f"{tag}u{int(round(100 * lump_floor))}"  # in hundredths: the stem stays under Windows' path limit
    elif lump_fixed > 0:
        raise ValueError("--lump-fixed is the greatest member's (--max-member)")
    if plan_gap:
        # The members' plan rule (LOP-23, `topo.plan_rule`): at most plan_width wide and, grown by half
        # the gap, no two merging; the engineer, 11 October 14:42: "increase the minimum gap"
        model["plan_rule"] = {"width_mm": plan_width, "gap_mm": plan_gap, "alpha": topo.PLAN_ALPHA}
        tag = f"{tag}_plan{plan_width:g}x{plan_gap:g}" if tag else f"plan{plan_width:g}x{plan_gap:g}"
    if flange:
        tag = f"{tag}_flange" if tag else "flange"
    if beds:
        # Every seat's bearing bed at most the design to beat's, in each case graded (LOP-20, 11
        # October): a constraint of `compliance_tilt` beside the tilt. The tilt is relative (a seat
        # against its shaft's line), so a floating core meets it from a grey start; the beds are
        # absolute, so it cannot: the tilt and the stiffness then go in one run, from iteration 1.
        from grade import GRADED_CASES, REFERENCE

        cases_run = tuple(model.get("cases") or ("peak drive", "peak reverse"))
        model["beds_mm"] = {c: REFERENCE[c] / 1000.0 for c in cases_run if c in GRADED_CASES}
        tag = f"{tag}_beds" if tag else "beds"
    if height_features:  # LOP-24, the bore experiment: a region's columns from features' parameters (`topo.feature_map`)
        p = Path(height_features)
        p = p if p.is_absolute() or p.exists() else OUT / p
        model["height_features"] = json.loads(p.read_text(encoding="utf-8"))
        tag = f"{tag}_feat{p.stem}" if tag else f"feat{p.stem}"
    if height_volumes:  # LOP-24: the design space divided into volumes, each its own form (`topo.volume_map`)
        model["height_volumes"] = height_volumes
        tag = f"{tag}_vol{Path(height_volumes).stem}" if tag else f"vol{Path(height_volumes).stem}"
    if perimeter:  # LOP-26: the members' outline in plan at most this (mm; `topo.perimeter_pairs`): no dashes, no worms
        if not height_field:
            raise ValueError("--perimeter needs the height field (--height-field)")
        model["perimeter"] = {"mm": float(perimeter)}
        tag = f"{tag}_per{perimeter:g}" if tag else f"per{perimeter:g}"
    parts_spec = None
    if parts:  # LOP-26, Refine: the design production's parts alone, their places and sizes the variables (`parts.PartsMap`)
        if not height_field:
            raise ValueError("--parts needs the height field (--height-field)")
        p = Path(parts)
        p = p if p.is_absolute() or p.exists() else OUT / p
        parts_spec = json.loads(p.read_text(encoding="utf-8"))
        model["parts"] = parts_spec
        tag = f"{tag}_parts{p.stem}" if tag else f"parts{p.stem}"
    if bending:  # LOP-28, the semantic rules: each marked region's mean bending at most its bound (`topo.bending_operator`)
        if not height_field:
            raise ValueError("--bending needs the height field (--height-field)")
        p = Path(bending)
        p = p if p.is_absolute() or p.exists() else OUT / p
        zb = np.load(p, allow_pickle=False)
        model["bending"] = {"weights": zb["weights"], "rms_per_m": [float(v) for v in zb["rms_per_m"]], "names": [str(v) for v in zb["names"]],
                            "kinds": [int(v) for v in zb["kinds"]] if "kinds" in zb.files else [0] * len(zb["rms_per_m"]), "file": p.name}  # fmt: skip
        tag = f"{tag}_bend{p.stem.removesuffix('_regions')}" if tag else f"bend{p.stem.removesuffix('_regions')}"
    if brackets and brackets.startswith("floors:"):  # LOP-28: each bracket's floor in cm³, its voxels this model's own (`mode_shape.parts`)
        import mode_shape

        floors = [float(v) for v in brackets.split(":", 1)[1].split(",")]
        kind = np.asarray(model["kind"])
        elem = np.flatnonzero(kind >= 0)
        free_flat = elem[kind[elem] == 0]
        ijk = np.stack(np.unravel_index(free_flat, tuple(model["n"])), axis=1)
        xyz = np.asarray(model["lo"], float)[None, :] + h * (ijk + 0.5)
        owner, part_names = mode_shape.parts(xyz, model["info"])
        names = [m["name"] for m in model["info"]["mounts"]]
        of = np.full(len(free_flat), -1, np.int64)
        for k, nm in enumerate(names):
            of[owner == part_names.index(nm)] = k
        least = list(floors)
        # (LOP-28) a bridge's floor too, `LOOP_FLOORS="<half>:<shaft a>:<shaft b>:<cm³>;..."`: the free voxels of the half between
        # two bearings' bosses (the hull of their circles grown 6 mm, less the bosses), at least that much metal: a design move on
        # a mode living there (prot6_least: 2498 Hz, the cover's output and intermediate bores)
        for spec_ in [v for v in os.environ.get("LOOP_FLOORS", "").split(";") if v.strip()]:
            half_, sa, sb, cm3 = spec_.split(":")
            side_ = "+z" if half_ == "cover" else "-z"
            bb = {b["shaft"]: b for b in model["info"]["bearings"] if b["side"] == side_}
            ca, cb = np.asarray(bb[sa]["axis"], float), np.asarray(bb[sb]["axis"], float)
            ra, rb = float(bb[sa]["boss_r"]), float(bb[sb]["boss_r"])
            d_ = cb - ca
            tt = np.clip(((xyz[:, 0] - ca[0]) * d_[0] + (xyz[:, 1] - ca[1]) * d_[1]) / float(d_ @ d_), 0.0, 1.0)
            hull = np.hypot(xyz[:, 0] - (ca[0] + tt * d_[0]), xyz[:, 1] - (ca[1] + tt * d_[1])) <= ra + 6.0 + tt * (rb - ra)
            outside = (np.hypot(xyz[:, 0] - ca[0], xyz[:, 1] - ca[1]) > ra) & (np.hypot(xyz[:, 0] - cb[0], xyz[:, 1] - cb[1]) > rb)
            in_half_ = (xyz[:, 2] >= model["info"]["z"]["split"]) if half_ == "cover" else (xyz[:, 2] < model["info"]["z"]["split"])
            pick = hull & outside & in_half_ & (of < 0)
            of[pick] = len(names)
            names.append(f"{half_} {sa}-{sb} bridge")
            least.append(float(cm3))
            say(f"a floor on the {half_}'s {sa}-{sb} bridge: {int(pick.sum()):,} free voxels, at least {float(cm3):g} cm³")
        # a floor of 0 is no floor (13 October 05:41: `floors:0,0,0` beside a bridge's floor divided by it): its voxels belong to none
        keep_ = [k for k, v in enumerate(least) if v > 0.0]
        remap = np.full(len(least) + 1, -1, np.int64)
        remap[keep_] = np.arange(len(keep_))
        of = remap[np.where(of >= 0, of, len(least))]
        names, least = [names[k] for k in keep_], [least[k] for k in keep_]
        model["brackets"] = {"of": of, "least_vox": np.asarray(least) * 1000.0 / h**3, "names": names, "file": brackets}
        tag = f"{tag}_brk" if tag else "brk"
    elif brackets:  # LOP-28, the semantic rules: each bracket's metal at least its floor
        p = Path(brackets)
        p = p if p.is_absolute() or p.exists() else OUT / p
        zk = np.load(p, allow_pickle=False)
        model["brackets"] = {"of": zk["of"], "least_vox": zk["least_vox"], "names": [str(v) for v in zk["names"]], "file": p.name}
        tag = f"{tag}_brk" if tag else "brk"
    least = float(os.environ.get("LOOP_LEAST_MEMBER", "0") or 0.0)
    if least > 0:  # LOP-25, approach 2: a column under this height (mm) holds nothing: no paint (`topo.Voxels._height_dens`)
        model["least_height_mm"] = least
        tag = f"{tag}_lm{least:g}" if tag else f"lm{least:g}"
    if least_width > 0:  # LOP-29 (the engineer, 14 October 13:42): the least member width in plan (`topo.open_heights`)
        if not model.get("height_field") or model.get("height_features") or model.get("height_volumes") or parts_spec is not None:
            raise ValueError("--least-width is the plain height field's (--height-field; no features, volumes or parts)")
        if model.get("bending"):
            raise ValueError("--least-width with --bending is not built (the bending's chain takes no opening)")
        model["least_width_mm"] = float(least_width)
        tag = f"{tag}_lw{least_width:g}" if tag else f"lw{least_width:g}"
    if spline:  # LOP-30 (the engineer, 14 October 17:27): smooth B-spline outline and height fields as the design variables
        if not model.get("height_field") or model.get("height_features") or model.get("height_volumes") or parts_spec is not None:
            raise ValueError("--spline is the plain height field's (--height-field; no features, volumes or parts)")
        if model.get("bending"):
            raise ValueError("--spline with --bending is not built")
        phi_mm, h_mm = (float(v) for v in spline.split(":"))
        model["spline"] = {"phi_mm": phi_mm, "h_mm": h_mm}
        # the spline map's options in one short tag (e.g. spl6x12g8o3000r4f4: the gap, the outline's limit, the round and the
        # fillet): with one tag each the run's checkpoint path passed Windows' 259 characters (baseline2_spl2, 21:10)
        tag = f"{tag}_spl{phi_mm:g}x{h_mm:g}" if tag else f"spl{phi_mm:g}x{h_mm:g}"
        if least_gap > 0:  # LOP-30 (the engineer, 19:06): no hole or slot narrower, on the smooth outline
            model["spline"]["gap_mm"] = float(least_gap)
            tag = f"{tag}g{least_gap:g}"
        if outline > 0:  # LOP-30 (the engineer, 19:06): the members' outline at most this long, on the smooth outline
            model["spline"]["outline_mm"] = float(outline)
            tag = f"{tag}o{outline:g}"
        if section:  # LOP-30 (the engineer, 20:34: "Start with A"): the members' free edges rounded, their roots filleted
            rnd, fil = (float(v) for v in section.split(":"))
            model["spline"]["round_mm"], model["spline"]["fillet_mm"] = rnd, fil
            tag = f"{tag}r{rnd:g}f{fil:g}"
            say(f"the section rule: every member's free edges rounded to {rnd:g} mm in the optimiser and the drawing "
                f"(`topo.section_drop`), its roots filleted to {fil:g} mm in the drawing")  # fmt: skip
        # LOP-30 (the engineer, 14 October 22:43-23:01: production-quality members, "smooth nice but shaped by optimiser"),
        # each a letter of the spline's tag: T the smooth top (F1), W the section window (F2), D disc openings, S the round's
        # soft distance, B the fields' bending limits (F3)
        if top:
            model["spline"]["top"] = True
            tag = f"{tag}T"
        if window:
            vals_ = [float(v) for v in window.split(":")]
            n_w = (len(vals_) - 1) // 2
            # where the window does not cap (`topo.Voxels`): the mounts' reach discs, and with "bosses" (the engineer, 15
            # October 00:45: "Lift height cap only") the bearings' bosses, the lump rule kept there
            free_ = [s_.strip() for s_ in window_free.split(",") if s_.strip()]
            # "bosses_wall" (the engineer, 15 October 01:24-01:30: no thin fins down the side walls): a boss free only on its
            # bearing's wall, the columns hanging from the split inside its circle capped
            wall_only = "bosses_wall" in free_
            free_ = ["bosses" if s_ == "bosses_wall" else s_ for s_ in free_]
            model["spline"]["window"] = {"widths_mm": vals_[:n_w], "caps_mm": vals_[n_w:], "free": free_, "bosses_wall_only": wall_only}
            if window_split:  # (15 October 01:55) the side walls' gussets' own caps, one per width class (`topo.spline_setup`)
                model["spline"]["window"]["caps_split_mm"] = [float(v) for v in window_split.split(":")]
            tag = f"{tag}W{'b' if 'bosses' in free_ else ''}{'w' if wall_only else ''}{'s' if window_split else ''}"
        if disc:
            model["spline"]["disc"] = True
            tag = f"{tag}D"
        if soft_dist:
            model["spline"]["dist"] = "soft"
            tag = f"{tag}S"
        if spline_bend:
            model["spline"]["bend"] = json.loads(Path(spline_bend).read_text(encoding="utf-8"))
            tag = f"{tag}B{Path(spline_bend).stem.split('_')[-1]}"
        if sizes > 0:  # (14 October 23:35) the least width and gap as constraints on the smooth field (Z)
            model["spline"]["sizes"] = float(sizes)
            tag = f"{tag}Z"
        if gap_shell:  # (15 October 05:05) the least gap read against the shell too (G; `topo.least_width_blocks`' solid)
            if not (least_gap > 0 and sizes > 0):
                raise ValueError("--gap-shell needs --least-gap and --sizes")
            model["spline"]["gap_shell"] = True
            tag = f"{tag}G"
            say(f"the least gap ({least_gap:g} mm) read against the shell too: no slot narrower between a member and the "
                "half's fixed metal (the walls, the land, the bosses, the lugs)")  # fmt: skip
        if penal_most and penal_most != topo.PENAL:  # (15 October 01:21) a half-full cube half as stiff (L: linear shares)
            model["penal_most"] = float(penal_most)
            tag = f"{tag}L{penal_most:g}"
            say(f"SIMP's penalty at most {penal_most:g}: the spline map's densities are shares of real geometry, a cube half "
                "filled by a 4 mm rib half as stiff, wherever the rib sits on the grid")  # fmt: skip
    elif least_gap > 0 or outline > 0 or section or top or window or disc or soft_dist or spline_bend:
        raise ValueError("--least-gap, --outline, --section, --top, --window, --disc, --soft-dist and --spline-bend are the spline map's (--spline)")
    if fair:  # (LOP-32, the engineer 15 October 16:10: "Reward. add rules") the members' fairing rules (`member_fair`), a stage
        # from a converged run (--start): '<top bend 1/mm>:<top slope>:<width change>' targets (0 leaves one out); the skeleton
        # rebuilt every LOOP_FAIR_EVERY iterations, the limits tightened over LOOP_FAIR_OVER, the topology frozen beyond
        # LOOP_FAIR_BAND cubes of the start's metal
        if not height_field or spline:
            raise ValueError("--fair is the plain height field's (--height-field, no --spline)")
        if not start_from and not resume:
            raise ValueError("--fair is a stage from a converged run: give --start <its stem>")
        tb, ts, tw = (float(v) for v in (fair.split(":") + ["0", "0", "0"])[:3])
        model["fair"] = {"targets": {"top_bend": tb, "top_slope": ts, "width_change": tw},
                         "every": int(os.environ.get("LOOP_FAIR_EVERY", "6")), "over": int(os.environ.get("LOOP_FAIR_OVER", "30")),
                         "band": float(os.environ.get("LOOP_FAIR_BAND", "2")), "rho": topo.KS_RHO}  # fmt: skip
        tag = f"{tag}_fair{100 * tb:g}x{10 * ts:g}x{10 * tw:g}"
    if model.get("modes") and topo.LOOSE_STIFF < 1.0:  # LOP-29 (the engineer, 14 October 15:37): `topo.LOOSE_STIFF`
        say(f"metal joined to nothing: {topo.LOOSE_MASS:g} of its mass and {topo.LOOSE_STIFF:g} of its stiffness (it carries "
            "nothing, and hanging on near-empty cubes it leaves the single factor nearly singular)")  # fmt: skip
    if safety and safety != 1.0:  # LOP-24: every tilt and bed held at most 1/safety of its line (`topo.Voxels`)
        model["safety"] = float(safety)
        tag = f"{tag}_sf{safety:g}" if tag else f"sf{safety:g}"
    wall_gate = float(os.environ.get("LOOP_WALL_GATE", "0") or 0.0)  # LOP-28: production's plain walls (`topo.Voxels._wall_extra`), mm
    if wall_gate > 0:
        if not empty:
            raise ValueError("LOOP_WALL_GATE is the empty start's (--empty): the walls' least heights")
        model["wall_gate_mm"] = wall_gate
        tag = f"{tag}_wg{wall_gate:g}"
    seat_factors = os.environ.get("LOOP_SAFETY_SEATS", "")  # LOP-28: "<shaft> <side>=<factor>,...", a seat's own factor of safety
    if seat_factors:
        model["safety_seats"] = {k.strip(): float(v) for k, v in (item.split("=") for item in seat_factors.split(",") if item.strip())}
        tag = f"{tag}_seat" + "".join(f"{k.split()[0][:2]}{k.split()[1][0] if k.split()[1][0] != '+' else 'p'}{v:g}" for k, v in model["safety_seats"].items())
    if safety_beds and safety_beds != (safety or 1.0):  # LOP-24: the beds' own factor of safety
        model["safety_beds"] = float(safety_beds)
        tag = f"{tag}_sfb{safety_beds:g}" if tag else f"sfb{safety_beds:g}"
    free_kg = budget - model["frozen_kg"]
    if empty and model["least_kg"] >= free_kg:
        raise ValueError(f"the empty start's walls need about {model['least_kg']:.2f} kg at least, the budget leaves {free_kg:.2f} kg to place")
    stem = run_stem(objective, budget, h, band, cavity, joint, model, tag)
    say(f"budget {budget:g} kg: {model['frozen_kg']:.2f} frozen, {free_kg:.2f} to place; {stem}{'' if fast else ' (full speed not granted)'}")
    checkpoint = OUT / f"{stem}_checkpoint.npz"
    if len(str(checkpoint)) > 259:  # (14 October 21:10) Windows refuses a longer path: baseline2_spl2 stopped at its first checkpoint
        raise ValueError(f"the run's checkpoint path is {len(str(checkpoint))} characters, past Windows' 259: shorten its tag ({stem})")
    start, beta0, first = None, 1.0, 1
    if resume and checkpoint.exists():
        saved = np.load(checkpoint)
        start, beta0, first = saved["x"], float(saved["beta"]), int(saved["iteration"]) + 1
        say(f"resuming from {checkpoint.name}: iteration {first}, beta {beta0:g}")
    elif start_from:
        saved = np.load(OUT / f"{start_from}.npz")
        # a voxel run has one variable a free voxel; a height-field run one a column, which `topo.Voxels` checks
        if not model.get("height_field") and len(saved["x"]) != int((model["kind"] == 0).sum()):
            raise ValueError(f"{start_from}: {len(saved['x']):,} design variables, the model {int((model['kind'] == 0).sum()):,} free voxels")
        start, beta0 = saved["x"], float(beta_start)
        say(f"starting from {start_from}'s design variables at beta {beta0:g}")
    elif parts_spec is not None:  # the parts where the reading put them, at their read sizes, as sharp as --beta0 says
        import parts as parts_mod

        start, beta0 = parts_mod.PartsMap(parts_spec, np.zeros((0, 2)), np.zeros(0)).start(), float(beta_start)
        say(f"starting from the parts of {Path(parts).name} at beta {beta0:g}")

    held_path = checkpoint.with_name(checkpoint.name.replace("_checkpoint", "_held"))

    def keep(it, x, beta, row=None):
        if it % CHECKPOINT_EVERY == 0:
            np.savez_compressed(checkpoint, x=x, beta=beta, iteration=it)
        # (15 October 02:28) the last state that held every line within HELD_TOL (tilts, beds, the modes' limits), at
        # the sharpest beta so far: a late step that breaks a link no longer costs the design
        if row is not None and float(row.get("worst_ratio") or 9.0) <= HELD_TOL and float(row.get("bed_worst") or 0.0) <= HELD_TOL and (
                not row.get("mode_gaps") or max(row["mode_gaps"]) <= 0.01):  # fmt: skip
            if beta >= keep.best_beta:
                keep.best_beta = beta
                np.savez_compressed(held_path, x=x, beta=beta, iteration=it, worst=float(row["worst_ratio"]), bed=float(row.get("bed_worst") or 0.0))

    keep.best_beta = 0.0

    result = topo.solve_model(model, free_kg, iterations, objective, start=start, beta0=beta0, first=first, on_iteration=keep)
    extra = {"height_min": np.asarray(model["height_min"], np.float32)} if model.get("height_min") is not None else {}  # LOP-27: the least heights, for the drawing
    if result.get("spline_cols"):  # LOP-30: each column's fields, which the drawing draws from (`outcome_cad.spline_members`)
        extra.update({f"spl_{k}": v for k, v in result["spline_cols"].items()})
    np.savez_compressed(OUT / f"{stem}.npz", phys=result["phys"], x=result["x"], free_e=result["free_e"], elem=result["elem"], frozen=result["frozen"],
                        ijk=result["ijk"], lo=model["lo"], n=model["n"], h=h, k_split=model["k_split"], beta=result["beta"], **extra)  # fmt: skip
    record = {"layout": LAYOUT, "objective": objective, "budget_kg": budget, "frozen_kg": model["frozen_kg"], "voxel_mm": h,
              "cavity": cavity, "joint": result["joint"], "skin": model["skin"], "element": "hex8 with Wilson's incompatible modes",
              "factor": "fe.py's single-precision factor, refined", "route": route,
              "casting": {"cast": "each half's columns one interval along the pull",
                          "split": "each half's columns one piece from the joint out to the last metal (anchored)"}.get(route, "none (the additive route)"),
              "projection": model["projection"], "penalty_ramp": ramp, "band_mm": band, "mount_reach": mount_reach if band else None, "start": start_from or None,
              "max_member": model.get("max_member"), "plan_rule": model.get("plan_rule"), "height_field": model.get("height_field"),
              "empty": bool(model.get("empty")), "least_kg": model.get("least_kg"), "protect": bool(model.get("protect")), "shell_fixed": bool(model.get("shell_fixed")), "towers": bool(model.get("towers", True)), "modes": model.get("modes"),
              "safety_seats": model.get("safety_seats"), "wall_gate_mm": model.get("wall_gate_mm"),
              "panel_spokes": {"spec": os.environ["LOOP_PANEL_SPOKES"], "halves": os.environ.get("LOOP_SPOKE_HALVES", "cover,motor_side")}
              if (os.environ.get("LOOP_PANEL_SPOKES") and model.get("protect")) else None,
              "lug_webs": os.environ.get("LOOP_LUG_WEBS") if (os.environ.get("LOOP_LUG_WEBS") and model.get("protect")) else None,
              "trade": model.get("trade", False), "flange": flange, "flange_whole": bool(flange), "drawing_clear": True, "couplings": "kinematic", "beds_mm": model.get("beds_mm"), "safety": model.get("safety", 1.0), "safety_beds": model.get("safety_beds", model.get("safety", 1.0)), "space": space or None,
              "height_features": model.get("height_features"), "height_volumes": model.get("height_volumes"),
              "least_height_mm": model.get("least_height_mm"), "least_width_mm": model.get("least_width_mm"),
              "spline": model.get("spline"), "penal_most": model.get("penal_most"),
              "loose": {"mass": topo.LOOSE_MASS, "stiffness": topo.LOOSE_STIFF} if model.get("modes") else None,
              "resumed_at": first if first > 1 else None,
              "parts": f"{stem}_parts.json" if parts_spec is not None else None,
              "bending": {k: model["bending"][k] for k in ("file", "names", "kinds", "rms_per_m")} if model.get("bending") else None,
              "brackets": {"file": model["brackets"]["file"], "names": model["brackets"]["names"],
                           "least_cm3": [float(v) * h**3 / 1000.0 for v in model["brackets"]["least_vox"]]} if model.get("brackets") else None,
              "parts_read": parts or None, "perimeter_mm": model.get("perimeter", {}).get("mm") if model.get("perimeter") else None,
              "ribs": {"spokes": RIB_SPOKES, "half_width_voxels": RIB_HALF, "from": ribs_from or None,
                       "fin_pitch_mm": FIN_PITCH if fins else None, "one_height_mm": SEGMENT if rib_filter else None} if ribs else None,  # fmt: skip
              "cases": list(model.get("cases") or ("peak drive", "peak reverse")),
              "fast": os.environ.get("LOOP_FAST", "0") != "0",
              "history": result["history"], "ratios": result["ratios"], "realisations": result.get("realisations"),
              "binary": result.get("binary"), "unknowns": result["n_dof"], "seconds": time.time() - t0,
              "fair": result.get("fair")}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    if parts_spec is not None:  # the optimised parts, in mm: what the drawing draws (`implicit_draw.parts_body`, LOOP_PARTS)
        import parts as parts_mod

        done = parts_mod.PartsMap(parts_spec, np.zeros((0, 2)), np.zeros(0)).params(np.asarray(result["x"], float))
        done = dict(done, run=stem, read_from=parts_spec.get("run"), read=parts)
        (OUT / f"{stem}_parts.json").write_text(json.dumps(done, indent=1), encoding="utf-8")
    topo.picture(model, result, OUT / f"{stem}.png", f"from the interfaces, {objective}, {budget:g} kg")
    say(f"done in {time.time() - t0:.0f} s; {stem}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The housing from its interfaces, by topology optimisation (prototype).")
    ap.add_argument("budget", nargs="?", type=float, default=7.73, help="the whole housing's mass, kg (default 7.73)")
    ap.add_argument("voxel", nargs="?", type=float, default=6.0, help="voxel size, mm (default 6)")
    ap.add_argument("iterations", nargs="?", type=int, default=200, help="most iterations (default 200)")
    ap.add_argument("band", nargs="?", type=float, default=None, help="stage 2: metal only within this of the skin, mm")
    ap.add_argument("--band", dest="band_opt", type=float, default=None,
                    help="the height envelope (11 October): metal only within this of the shell, mm, and in a corridor to each mount; "
                         "as the positional band, which argparse cannot take after options")  # fmt: skip
    ap.add_argument("--objective", default="misalignment_bound", choices=["misalignment_bound", "misalignment_pnorm", "compliance_gcmma", "compliance_tilt", "mass_tilt", "modes_tilt", "misalignment"],
                    help="every seat bounded (GCMMA, one adjoint a seat), one p-norm of them (GCMMA, one adjoint a case), "
                         "compliance (GCMMA, no adjoint: the papers' first objective), compliance with every seat's tilt at most its line "
                         "(GCMMA, one adjoint a seat and case; with --robust-p), or the p-norm by OC")  # fmt: skip
    ap.add_argument("--fast", action="store_true", help="the GPU's assembly, kept factor and MMA subproblem (LOP-19; LOOP_FAST=1)")
    ap.add_argument("--joint", default="bolts", choices=["bolts", "glued"], help="halves joined at the bolts only, or glued at the split")
    ap.add_argument("--skin", type=float, default=None, help="the wall a skin voxel stands for, mm (default: the contract's least wall; 0: the voxel itself)")
    ap.add_argument("--cavity", default="cup", choices=["cup", "rooms"], help="each half a cup open to the split, or each room its own cylinder")
    ap.add_argument("--ramp", type=int, default=PENALTY_RAMP, help=f"iterations over which SIMP's penalty rises from 1 to 3 (default {PENALTY_RAMP}; 0: 3 throughout)")
    ap.add_argument("--tag", default="", help="a suffix for the run's files")
    ap.add_argument("--resume", action="store_true", help="carry on from the run's checkpoint")
    ap.add_argument("--route", default="cast", choices=["cast", "split", "free"],
                    help="cast: each column one piece along the pull; split: one piece from the joint out (a mould parted at the joint); free: additive, no filter")  # fmt: skip
    ap.add_argument("--robust", type=float, default=0.0, help="the robust formulation's threshold shift (e.g. 0.2: eroded 0.7, nominal 0.5, dilated 0.3); 0: off")
    ap.add_argument("--start", default="", help="a run's stem whose design variables start this one (the same model)")
    ap.add_argument("--beta0", type=float, default=1.0, help="the projection's sharpness at the start (with --start)")
    ap.add_argument("--robust-p", type=float, default=0.0, help="with --robust: each seat and case's realisations one constraint, their p-norm (e.g. 16)")
    ap.add_argument("--cases", default="", help="the load cases, comma-separated (default 'peak drive,peak reverse')")
    ap.add_argument("--beta-most", type=float, default=None, help="the sharpening's last sharpness (default 16)")
    ap.add_argument("--every", type=int, default=None, help="iterations at one sharpness at most (default 40)")
    ap.add_argument("--settle", type=float, default=None, help="double the sharpness as soon as a step falls under this (one run, no stages)")
    ap.add_argument("--max-member", type=float, default=None,
                    help="the greatest placed section, mm (a casting rule as a constraint, so the metal forms ribs, never lumps; LOP-20), e.g. 12")  # fmt: skip
    ap.add_argument("--trade", action="store_true",
                    help="freeze the trade's bearing bosses (1.25·D + 10 mm) and the flange's band, as the skin drawing draws them (LOP-20)")  # fmt: skip
    ap.add_argument("--beds", action="store_true",
                    help="with compliance_tilt: every seat's bearing bed at most the design to beat's, in the graded cases (LOP-20)")  # fmt: skip
    ap.add_argument("--ribs", action="store_true",
                    help="with --band: the free voxels only on the production rib network (a wheel round each bore, links, ridges, gussets; LOP-23)")  # fmt: skip
    ap.add_argument("--ribs-from", default="", help="with --band: the rib network and a free run's members' centre-lines (a run's stem on the same voxels)")
    ap.add_argument("--fins", action="store_true", help=f"with --band: the rib network and fins up the side walls every {FIN_PITCH:g} mm of the inside's outline")
    ap.add_argument("--rib-filter", action="store_true",
                    help=f"with --band: each piece of the rib network (a spoke's or link's {SEGMENT:g} mm, an arc, a boss's annulus, a fin) at one height, as production's ribs stand")  # fmt: skip
    ap.add_argument("--plan-gap", type=float, default=None,
                    help="the members' plan rule (LOP-23, `topo.plan_rule`): members at most --plan-width wide, grown by half this gap, mm; "
                         "gap 12 and width 8 pass ribs 16-20 mm apart and fail every lattice")  # fmt: skip
    ap.add_argument("--plan-width", type=float, default=8.0, help="with --plan-gap: the members' greatest width in plan, mm (default 8)")
    ap.add_argument("--height-field", type=float, default=None,
                    help="the height field (LOP-23, `topo.Voxels`): one design variable a column, the metal's height there from the split "
                         "or its wall, smoothed over this radius in plan, mm (castable by construction; the mounts' regions reach the split)")  # fmt: skip
    ap.add_argument("--safety", type=float, default=1.0,
                    help="the optimiser's factor of safety (LOP-24): every tilt and bed held at most 1/this of its line, "
                         "covering the model's optimism; the grade judges the true lines (default 1)")  # fmt: skip
    ap.add_argument("--height-volumes", default="",
                    help="with --height-field (LOP-24): the design space divided into volumes, each its own form (an .npz; `topo.volume_map`)")  # fmt: skip
    ap.add_argument("--height-features", default="",
                    help="with --height-field (LOP-24): a region round one bore given to features' parameters (a file; `topo.feature_map`)")  # fmt: skip
    ap.add_argument("--safety-beds", type=float, default=None,
                    help="the beds' own factor of safety (LOP-24; default: --safety's): every bed held at most 1/this of its line")  # fmt: skip
    ap.add_argument("--space", default="",
                    help="the agent's design space for this iteration (LOP-24): a regions file, each half's regions in plan (mm); "
                         "only their columns are free within the band")  # fmt: skip
    ap.add_argument("--perimeter", type=float, default=None,
                    help="with --height-field (LOP-26): the members' outline in plan at most this many mm (`topo.perimeter_pairs`): fewer, "
                         "longer, continuous members, no dashes or worms")  # fmt: skip
    ap.add_argument("--parts", default="",
                    help="with --height-field (LOP-26, Refine): the design production's parts alone, read by `refine_read.py` (a file); "
                         "their nodes' places and sizes the variables, a column no part covers empty")  # fmt: skip
    ap.add_argument("--empty", action="store_true",
                    help="with --height-field (LOP-27, the empty start): no fixed shell or flange land, the walls the optimiser's; "
                         "fixed only the seats' rings (none with --shell-fixed), the mounts and the bolts' bosses; oil-tight by each "
                         "run's least height")  # fmt: skip
    ap.add_argument("--protect", action="store_true",
                    help="with --empty (LOP-28): the functional interfaces a non-design base, drawn exact: each bearing's boss (the layout's "
                         "cylinder, boss_r, along its seat), the sealing land, the bolts' bosses and the mounts")  # fmt: skip
    ap.add_argument("--bending", default="",
                    help="with --height-field (LOP-28, the semantic rules): each marked region's mean bending of the outer surface at most "
                         "its bound (an .npz from `semantic_regions.py`: the regions' weights a column and their bounds, RMS 1/m)")  # fmt: skip
    ap.add_argument("--brackets", default="",
                    help="(LOP-28, the semantic rules) each bracket's metal at least its floor (an .npz from `semantic_regions.py`: each free "
                         "voxel's bracket and each bracket's floor), so no bracket pays for another region")  # fmt: skip
    ap.add_argument("--first-mode", type=float, default=0.0,
                    help="(LOP-29, with --modes) the first mode at least this many Hz, held with the orders' margin (the engineer: 500)")
    ap.add_argument("--first-margin", type=float, default=0.0,
                    help="(LOP-29, with --first-mode) the floor held at first-mode x (1 + this); none by default")
    ap.add_argument("--modes", type=float, default=0.0,
                    help="(LOP-29) the model's modes held clear of each gear order by this share each side (0.12: the mode just below at "
                         "most 12 %% under the order, the one just above at least 12 %% over), read on each analysis's factor")  # fmt: skip
    ap.add_argument("--no-towers", dest="towers", action="store_false",
                    help="(LOP-29, with --protect) the bearing towers left out of the protected set: the optimiser builds the bosses")
    ap.add_argument("--shell-fixed", action="store_true",
                    help="(LOP-29, with --empty) the 4 mm shell protected: the least walls' cubes frozen whole, the optimiser adding on top")
    ap.add_argument("--least-width", type=float, default=0.0,
                    help="(LOP-29, with --height-field) the members' least width in plan, mm (at least two cubes, e.g. 8 at 4 mm): a "
                         "column's height counts only up to what the fullest block of columns on its level reaches (`topo.open_heights`)")  # fmt: skip
    ap.add_argument("--spline", default="",
                    help="(LOP-30, with --height-field) the design variables smooth B-spline fields per half, '<outline mm>:<height "
                         "mm>' knot spacings (e.g. 4:8): an outline field (metal where positive) and two height fields (the columns "
                         "on the split, those on a wall), every member at least the least member proud (`topo.spline_setup`)")  # fmt: skip
    ap.add_argument("--least-gap", type=float, default=0.0,
                    help="(LOP-30, with --spline) no hole or slot in plan narrower than this, mm (the outline field closed, on its points)")
    ap.add_argument("--outline", type=float, default=0.0,
                    help="(LOP-30, with --spline) the members' outline in plan at most this long, mm, on the smooth outline "
                         "(`topo.Voxels.spline_outline`): every wiggle, hole and island costs")  # fmt: skip
    ap.add_argument("--section", default="",
                    help="(LOP-30, with --spline) the section rule, '<round mm>:<fillet mm>' (e.g. 4:4): every member's free "
                         "edges rounded in the optimiser and the drawing (`topo.section_drop`), its roots filleted in the drawing")  # fmt: skip
    ap.add_argument("--top", action="store_true", help="(LOP-30, F1, with --spline) the height fields the members' free end, one smooth surface")
    ap.add_argument("--window", default="",
                    help="(LOP-30, F2, with --spline) the section window '<width mm>:...:<cap mm>:...' (one cap more than widths, "
                         "e.g. 12:16:20:32:12): a member at most the first cap tall where narrower than the first width, the next "
                         "where at least that wide")  # fmt: skip
    ap.add_argument("--window-free", default="mounts",
                    help="(LOP-30, with --window) where the window does not cap, 'mounts' and/or 'bosses' (the bearings' bosses, "
                         "within 0.625 D + 5 mm of each axis, as castability's section check leaves them out)")  # fmt: skip
    ap.add_argument("--window-split", default="",
                    help="(LOP-30, with --window) the side walls' gussets' (the members hanging from the split) own caps, mm, "
                         "one per width class as --window's caps (e.g. 999:30:20:10: a thin gusset as deep as the space allows)")  # fmt: skip
    ap.add_argument("--penal-most", type=float, default=0.0,
                    help="(LOP-30, with --spline) SIMP's penalty at most this (1: a cube's share of real geometry counted "
                         "linearly, so a 4 mm rib half in each of two cubes is as stiff as in one; default 3)")  # fmt: skip
    ap.add_argument("--disc", action="store_true", help="(LOP-30, with --spline) the openings and closings over discs, not squares")
    ap.add_argument("--soft-dist", action="store_true", help="(LOP-30, with --section) the round's distance a soft minimum to the points outside")
    ap.add_argument("--spline-bend", default="",
                    help="(LOP-30, F3, with --spline) a JSON file of the fields' bending limits ('outline0', 'split1', 'wall0', ...)")
    ap.add_argument("--lump-floor", type=float, default=0.0,
                    help="(LOP-30, with --lump-fixed) each ball's placed metal at most what its fixed metal leaves of 0.6, never "
                         "under this (e.g. 0.25): the union lump rule held so it can be met")  # fmt: skip
    ap.add_argument("--lump-fixed", type=float, default=0.0,
                    help="(LOP-30, with --max-member) the lump rule counting the fixed metal within this many mm of the split")
    ap.add_argument("--sizes", type=float, default=0.0,
                    help="(LOP-30, with --spline and --least-width/--least-gap) the least width and gap as constraints on the smooth "
                         "field, each at most this share of the metal (e.g. 0.005), the field itself the geometry")  # fmt: skip
    ap.add_argument("--gap-shell", action="store_true",
                    help="(LOP-30, with --spline --least-gap --sizes) the least gap read against the shell too: no slot narrower "
                         "between a member and the half's fixed metal (G)")  # fmt: skip
    ap.add_argument("--fair", default="",
                    help="(LOP-32, with --height-field and --start) the members' fairing stage, '<top bend 1/mm>:<top slope>:<width "
                         "change>' targets (e.g. 0.06:1.0:0.3; 0 leaves one out): on a temporary skeleton of the members, each "
                         "measure's local worst held under a limit tightened from the start's to its target (`member_fair`), the "
                         "topology frozen")  # fmt: skip
    a = ap.parse_args()
    if a.fast:
        os.environ["LOOP_FAST"] = "1"  # read at each call by topo.Voxels.analyse and mma.MMA
    main(a.budget, a.voxel, a.iterations, a.band_opt or a.band, a.objective, a.joint, a.skin, a.cavity, a.tag, a.resume, a.ramp, a.route, a.robust, a.start, a.beta0, a.robust_p,
         tuple(c.strip() for c in a.cases.split(",") if c.strip()), a.beta_most, a.every, a.settle, a.max_member, a.trade, a.beds, a.ribs, a.ribs_from, a.fins, a.rib_filter,
         a.plan_gap, a.plan_width, a.height_field, a.safety, a.space, a.safety_beds, a.height_features, a.height_volumes, a.parts, a.perimeter, a.empty,
         a.bending, a.brackets, a.protect, a.modes, a.shell_fixed, a.towers, a.first_mode, a.first_margin, a.least_width, a.spline,
         a.least_gap, a.outline, a.section, a.top, a.window, a.disc, a.soft_dist, a.spline_bend, a.lump_fixed, a.sizes, a.window_free,
         a.penal_most, a.window_split, a.lump_floor, a.gap_shell, a.fair)  # fmt: skip
