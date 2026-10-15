"""PROTOTYPE (LOP-23) - a field optimised on production's rib network, drawn as the trade draws ribs.

A run on the network (`topo_free.py --band <mm> --ribs | --ribs-from <run> | --fins`) holds its
metal only on the network's pieces (`topo_free.rib_network`, `side_fins`, `field_lines`): each
spoke's and link's `SEGMENT`, each arc of a boss's ring, each annulus of a boss, each fin and
gusset, each square of a ridge or of a free run's lines. The mesh route draws a field's members as
their voxels blurred: blobs that follow the pieces roughly (11 October 09:27, beside the production
photos: production's ribs are thin and straight, of one section, boss to rim).

Here each piece the optimiser put metal on is drawn as the trade draws a rib: along its own line
(the pieces' geometry), one voxel thick, and along it as far off the shell as the optimiser's metal
stands in each column under it (its plan's "top", the nearest columns' highest), so its mass is the
optimiser's; a boss's annulus as a ring. Drawn whole at its highest the pieces made 8.21 kg of a
6.83 kg design (11 October 09:31). The mount arms (the corridors, off the network) stay as the
field drew them. The rest is the mesh route's (`outcome_cad.build_mesh`): fused with the exact
shell, the roots filleted, cut exact.

Used by `outcome_cad.members_of` for a run whose record has `ribs`, only with LOOP_NETWORK_DRAW=1:
**off by default, a failed attempt** (11 October 09:31-09:46, on outcome_ribsfieldfins24_6.3kg,
whose field the mesh route draws at 6.83 kg, beds 42.0 µm, tilt 0.83 ×, passing). Drawn clean it
was 8.21 kg (each filled piece drawn whole), then 8.54 (every piece through a column drew it), then
7.03 kg with its mass the optimiser's (one owner a column, its height the nearest column's, the
skin's voxel taken from under it), but beds 131 µm, tilt 1.66 ×, first mode 478 Hz: overlapping
pieces (the free run's lines over the spokes, the ridges, the arcs) still fused into masses under
the blur and the fillets, and the mount arms, drawn from the corridors' own metal and a voxel more,
came out thin at their roots. A clean drawing wants a network whose pieces do not overlap, and the
arms drawn as pieces too.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "first_loop"
ON = os.environ.get("LOOP_NETWORK_DRAW", "0") != "0"


def pieces(run: str, force: bool = False) -> dict | None:
    """The run's network rebuilt on its own voxels, with the optimiser's metal on it: per half
    ("motor_side", "cover") a list of {"shape", "mask" (plan, its voxels), "metal" (any of its
    voxels metal)}, the half's "top" (plan, mm off the inside to the network's highest metal in
    each column, 0 where none), and "corridor" (the free voxels off the network: the mounts' arms).
    None for a run not on the network."""
    import topo_free as tf

    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    ribs = rec.get("ribs")
    if not ribs or not (ON or force):  # `force`: the exact network builder (`ribbed_cad.network_parts`)
        return None
    z = np.load(OUT / f"{run}.npz")
    n, h = z["n"].astype(int), float(z["h"])
    band = rec["band_mm"]
    model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=band, skin=rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None,
                          cavity=rec.get("cavity", "cup"), route=rec.get("route", "cast"), flange=bool(rec.get("flange")), ribs=True,
                          ribs_from=ribs.get("from") or "", fins=bool(ribs.get("fin_pitch_mm")),
                          mount_reach=rec.get("mount_reach") or "corridor")  # fmt: skip
    if not np.array_equal(np.asarray(model["n"]), n):
        raise ValueError(f"{run}: the network's voxels {model['n'].tolist()} are not the run's {n.tolist()}")
    info, lo, k_split, kind = model["info"], model["lo"], model["k_split"], model["kind"].reshape(tuple(n))
    masks = {k: v.reshape(tuple(n)) for k, v in model["masks"].items()}
    xc, yc = (lo[i] + h * (np.arange(n[i]) + 0.5) for i in range(2))
    placed = np.zeros(int(np.prod(n)), bool)
    placed[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    placed = placed.reshape(tuple(n))
    skin = masks["skin"] | masks["seats"]
    # each voxel's distance off the inside, mm: off the skin's centres, and the skin's half voxel
    off = distance_transform_edt(~skin) * h + 0.5 * h
    kk = np.arange(n[2])[None, None, :]
    out = {"h": h, "lo": lo, "n": n, "band": band, "wall": float(info["settings"]["wall"])}
    on_net = np.zeros(tuple(n), bool)
    for half in ("motor_side", "cover"):
        lower = half == "motor_side"
        side = kk < k_split if lower else kk >= k_split
        wall_xy = np.column_stack([np.broadcast_to(xc[:, None, None], tuple(n))[skin & side], np.broadcast_to(yc[None, :, None], tuple(n))[skin & side]])
        inside_xy = (masks["rooms"] & side).any(axis=2)
        prims = tf.rib_network(info, xc, yc, h, lower, wall_xy, parts=True, geometry=True)
        if ribs.get("from"):
            prims += [(t, ("cells",)) for t in tf._tiles(tf.field_lines(ribs["from"], n, lo, h, k_split, lower), xc, yc)]
        if ribs.get("fin_pitch_mm"):
            prims += tf.side_fins(inside_xy, xc, yc, h, band, parts=True, geometry=True)
        # each column of metal belongs to one piece, the first that holds it (the bosses' annuli,
        # the rings' arcs, the spokes, the links, the ridges, the gussets, then a free run's lines and
        # the fins): drawn by every piece through it, overlapping pieces drew 1.7-2 times the
        # optimiser's metal (11 October 09:41)
        metal = placed & side & (kind == 0)
        column = metal.any(axis=2)
        owner = np.full(column.shape, -1, dtype=np.int64)
        drawn = []
        for k, (mask, shape) in enumerate(prims):
            on_net |= mask[:, :, None] & side & (kind == 0)
            owner[mask & column & (owner < 0)] = k
            drawn.append({"shape": shape, "mask": mask, "own": None})
        for k, p in enumerate(drawn):
            p["own"] = owner == k
        out[half] = [p for p in drawn if p["own"].any()]
        # each column's highest metal on the network, mm off the inside (its voxel's outer face)
        metal &= on_net
        out[f"top_{half}"] = np.where(metal.any(axis=2), np.where(metal, off + 0.5 * h, 0.0).max(axis=2), 0.0)
    out["corridor"] = (kind == 0) & ~on_net
    return out


def _plan_mask(mask: np.ndarray, lo: np.ndarray, h: float, PX: np.ndarray, PY: np.ndarray, grow: int = 1) -> np.ndarray:
    """A coarse plan mask (grown by `grow` voxels) on the fine plan points PX, PY."""
    m = binary_dilation(mask, iterations=grow) if grow else mask
    i = np.clip(np.floor((PX - lo[0]) / h).astype(int), 0, mask.shape[0] - 1)
    j = np.clip(np.floor((PY - lo[1]) / h).astype(int), 0, mask.shape[1] - 1)
    return m[i, j]


def _width(own: np.ndarray, h: float, length: float, least: float) -> float:
    """A piece's section across: its own columns' area over its length, at least `least` (the
    optimiser's thinnest member, a voxel) and at most two voxels, as the network's pieces are."""
    return float(np.clip(own.sum() * h * h / max(length, h), least, 2.0 * h))


def _to_segment(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = np.clip(((px - a[0]) * dx + (py - a[1]) * dy) / max(dx * dx + dy * dy, 1e-12), 0.0, 1.0)
    return np.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


def clean(net: dict, half: str, PX: np.ndarray, PY: np.ndarray, d_own: np.ndarray, cavity: np.ndarray, side: np.ndarray) -> np.ndarray:
    """The filled pieces of one half drawn clean on the fine grid: (PX, PY) its plan points, `d_own`
    each cell's distance off the half's inside (mm), `cavity` and `side` its masks. Returns the
    cells of metal (bool, the fine grid's shape)."""
    h, lo = net["h"], net["lo"]
    t = h  # one voxel, as the optimiser's thinnest member
    xc, yc = (lo[i] + h * (np.arange(net["n"][i]) + 0.5) for i in range(2))
    top_half = net[f"top_{half}"]
    i = np.clip(np.floor((PX - lo[0]) / h).astype(int), 0, top_half.shape[0] - 1)
    j = np.clip(np.floor((PY - lo[1]) / h).astype(int), 0, top_half.shape[1] - 1)
    fine_top = np.zeros(PX.shape)
    for p in net[half]:
        kind = p["shape"][0]
        # the piece's own height: at each point of its clean line, its nearest own column's (the
        # highest of the next columns lifted the ribs above the optimiser's metal, 09:44)
        own = np.where(p["own"], top_half, 0.0)
        if kind != "annulus":
            near = distance_transform_edt(~p["own"], return_distances=False, return_indices=True)
            own = own[near[0], near[1]]
        tops = own[i, j]
        clip = _plan_mask(p["own"], lo, h, PX, PY, grow=1 if kind != "annulus" else 0)
        if kind == "annulus":
            _, cx, cy, r0, r1 = p["shape"]
            r = np.hypot(PX - cx, PY - cy)
            foot = (r >= r0) & (r <= r1) & clip
        elif kind == "arc":
            _, cx, cy, rr, a0, a1 = p["shape"]
            r = np.hypot(PX - cx, PY - cy)
            ang = np.arctan2(PY - cy, PX - cx)
            width = _width(p["own"], h, rr * (a1 - a0), t)
            foot = (np.abs(r - rr) <= width / 2) & (ang >= a0) & (ang <= a1) & clip
        else:
            if kind == "segment":
                a, b = p["shape"][1], p["shape"][2]
            else:  # a square of cells: the straight line through them (their principal axis)
                ii, jj = np.nonzero(p["own"])
                pts = np.column_stack([xc[ii], yc[jj]])
                c = pts.mean(axis=0)
                if len(pts) < 2:
                    a = b = tuple(c)
                else:
                    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
                    s = (pts - c) @ vt[0]
                    a, b = tuple(c + s.min() * vt[0]), tuple(c + s.max() * vt[0])
            # the line's length within its own columns: the stretch its metal covers
            ii, jj = np.nonzero(p["own"])
            d = np.array([b[0] - a[0], b[1] - a[1]])
            span = float(np.hypot(*d))
            if span > 1e-9:
                s = ((xc[ii] - a[0]) * d[0] + (yc[jj] - a[1]) * d[1]) / span
                length = float(s.max() - s.min()) + h
            else:
                length = h
            foot = (_to_segment(PX, PY, a, b) <= _width(p["own"], h, length, t) / 2) & clip
        fine_top = np.maximum(fine_top, np.where(foot, tops, 0.0))
    # Only where the optimiser's metal stood under a piece: a column without it has no top. In the
    # model a member stands on the skin's voxel, h thick for a wall of `wall`; drawn on the wall
    # itself, it comes down by the difference, so it keeps its own height (and the optimiser's
    # mass): the blobs carried the skin's voxel under each member, 0.5-0.9 kg (08:00).
    drop = max(0.0, h - net["wall"])
    return (fine_top > 0)[:, :, None] & (d_own <= fine_top[:, :, None] - drop) & ~cavity & side
