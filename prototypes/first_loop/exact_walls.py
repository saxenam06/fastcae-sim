"""PROTOTYPE (LOP-27) - the empty start's least walls drawn from the exact inside, smooth, in the same
field as the optimiser's metal: the engineer's "the shell as an approximated function in the same
space" (12 October 20:04), asked for at 21:10 ("first 2 and then 1 on top of it").

Why: drawn from the voxels, an empty start's least walls follow the rooms as the 4 mm voxels cut
them, so its lobes and bosses came out as octagons and steps, and no smoothing after the run took them
away without opening the 4 mm walls (`docs/features/loop/status.md`, Measured, 12 October 21:08).
Here the voxels' least walls are dropped and drawn again from the exact geometry, as one smooth
density beside the optimiser's own metal (`outcome_cad.skin_parts`, `LOOP_EXACT_WALLS=1`):
- `extra_placed`: the run's metal beyond each column's least height (`topo_free.least_heights`, saved
  in the run's `height_min`), with the least wall's top voxel kept under any metal stacked on it, so
  the optimiser's members stand on the exact wall;
- `least_density`: the least walls as a density on the drawing's grid, 0.5 on their faces:
  - the cup's outside, every room of the half at the least wall (its signed distance, so each bore's
    boss is round and each lobe a cylinder);
  - the plate over the other half's wider opening (the other half's rooms as discs at the split);
  - the sealing land round the inside at the split (A26);
  - each sealed exit's seat (A16).
The interfaces (the mounts, the bolts' bosses) are the drawing's own exact parts; the bearings' seats
are the cup's bores at the least wall; every machined face is cut exact after, as before.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import cup as cupmod  # noqa: E402
import topo  # noqa: E402

EDGE = 0.5  # mm, the density's step across a wall's face (0.5 exactly on it)
# mm the walls' faces are laid inside their true place on the drawing's grid. Its 2 mm cells are read whole and
# contoured at their faces, so a face lands on a cell's face: a 4 mm least wall came out 4.96 mm at no bias and
# 2.96 at 1 mm (12 October 21:30-21:34; the plain drawing's voxel walls 2.96 there too, under the least wall).
# None: the faces at their true place, so a 4 mm wall is drawn 3-5 mm on 2 mm cells (4.96 on the cover's big lobe,
# 3.82 over the intermediate's pocket, `empty1_exact_5.5kg`); a 1 mm grid would give 3.5-4.5 (open)
GRID_BIAS = 0.0


@functools.lru_cache(maxsize=1)
def _seal_seat_mm() -> float:
    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.forces import value_in

    spec, _ = load_and_validate(topo.CONTRACT)
    return value_in(spec.requirement.shaft_layout.behind_bearing_sealed, "mm")


def _height_min(stem: str, z) -> np.ndarray:
    """The run's least heights: saved with it (empty starts since 12 October 21:11), else built again
    from its record's set-up (`topo_free.build_free(..., empty=True)`), checked to give its voxels."""
    if "height_min" in z:
        return np.asarray(z["height_min"], float)
    import json

    import topo_free

    rec = json.loads((topo.OUT / f"{stem}.json").read_text(encoding="utf-8"))
    hf = (rec.get("height_field") or {}).get("radius_mm")
    model = topo_free.build_free(float(rec["voxel_mm"]), band=rec.get("band_mm"), flange=bool(rec.get("flange")), height_field=hf,
                                 mount_reach=rec.get("mount_reach") or "corridor", empty=True)  # fmt: skip
    if not np.array_equal(np.flatnonzero(model["kind"] >= 0), np.asarray(z["elem"])):
        raise ValueError(f"{stem}: its set-up built again does not give its voxels; its least heights cannot be rebuilt")
    return np.asarray(model["height_min"], float)


def extra_placed(stem: str) -> np.ndarray:
    """The run's placed metal (its free voxels at 0.5 or more) beyond each column's least height, on
    its own grid: the least walls are drawn exact instead. Nothing of the least wall is kept under a
    member: the drawing fills each column from the split to its last metal, so a member stands on the
    wall below it whatever the voxels did (the least wall's top voxel kept under each member had
    added up to 4 mm there, `empty2_exact_5.5kg`, 12 October 21:30)."""
    z = np.load(topo.OUT / f"{stem}.npz")
    n = z["n"].astype(int)
    elem, free_e, frozen = z["elem"], z["free_e"], z["frozen"].astype(bool)
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, _, _ = topo.height_columns(kind, n, int(z["k_split"]), elem, free_e)
    placed = np.asarray(z["phys"]) >= 0.5
    need = _height_min(stem, z)[elem[free_e]]
    n_cols = int(col.max()) + 1
    tmin = np.zeros(n_cols)
    np.maximum.at(tmin, col, need)
    least = np.ceil(tmin[col] - 1e-6)  # each free voxel's column's least wall, in whole voxels
    keep = placed & (pos >= least)
    out = np.zeros(int(np.prod(n)), bool)
    out[elem[free_e]] = keep
    return out.reshape(n)


def _capped(X, Y, Z, axis, r: float, z_lo: float, z_hi: float) -> np.ndarray:
    """The signed distance (mm, negative inside) to a cylinder along z of radius r from z_lo to z_hi."""
    dr = np.hypot(X - axis[0], Y - axis[1]) - r
    dz = np.maximum(z_lo - Z, Z - z_hi)
    return np.hypot(np.maximum(dr, 0.0), np.maximum(dz, 0.0)) + np.minimum(np.maximum(dr, dz), 0.0)


def _density(sdf: np.ndarray) -> np.ndarray:
    return (0.5 - 0.5 * np.tanh(sdf / EDGE)).astype(np.float32)


def ramp(sdf: np.ndarray, width: float) -> np.ndarray:
    """(LOP-29) A face's density for the contour: 0.5 on the face, linear over `width` mm either side, so marching cubes on
    cells `width` mm apart puts a plane face where it is. A step within EDGE put each face on a cell's face: a 4 mm least
    wall drawn 3-5 mm on 2 mm cells, 4.9 under `lop29_keep`'s intermediate gear room (13 October 20:40)."""
    return np.clip(0.5 - sdf / (2.0 * width), 0.0, 1.0).astype(np.float32)


def round_inter(a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    """(LOP-30, the section rule) Two solids' common part, their signed distances (positive outside), with the edge where
    their faces meet rounded to radius r: a member's side and its free end give its rounded free edge."""
    return np.minimum(-r, np.maximum(a, b)) + np.hypot(np.maximum(r + a, 0.0), np.maximum(r + b, 0.0))


def round_union(a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    """(LOP-30, the section rule) Two solids joined, their signed distances (positive outside), with a fillet of radius r
    where their faces meet: the members and the exact parts give the members' filleted roots."""
    return np.maximum(r, np.minimum(a, b)) - np.hypot(np.maximum(r - a, 0.0), np.maximum(r - b, 0.0))


def interface_density(X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str, towers: bool = True) -> np.ndarray:
    """(LOP-28; the engineer, 13 October 01:20-01:28: "you should have built it in field only", "Everything all protected
    regions should be in field only") The half's protected interfaces as a density in the same field as the run's metal,
    0.5 on their faces, from the exact geometry, so one contour draws the whole as-cast housing:
    - each bearing's boss: the layout's cylinder (boss_r) from a least wall past its seat's outer end down to the split,
      a castable tower (as `topo_free.build_free`'s `protect` holds it; the rooms are cut exact after);
    - the sealing land (the layout's outer circles less its inner ones) and the bolts' bosses, a flange thick;
    - in the motor side, the mounts' lugs."""
    s = layout["settings"]
    wall = float(s["wall"])
    lower = half == "motor_side"
    dens = np.zeros(X.shape, np.float32)
    for b in layout["bearings"] if towers else []:  # (LOP-29) the run's towers, or none
        if (b["side"] == "-z") != lower:
            continue
        z0, z1 = b["z"]
        z_lo, z_hi = (z0 - wall, z_split) if lower else (z_split, z1 + wall)
        dens = np.maximum(dens, _density(_capped(X, Y, Z, b["axis"], float(b["boss_r"]) - GRID_BIAS, z_lo, z_hi)))
    fl = layout.get("flange") or {}
    t_f = float(fl.get("thickness", s["flange_thickness"]))
    z_lo, z_hi = (z_split - t_f, z_split) if lower else (z_split, z_split + t_f)
    if fl:
        d_out = np.min([np.hypot(X[:, :, 0] - c["centre"][0], Y[:, :, 0] - c["centre"][1]) - c["radius"] for c in fl["outer"]], axis=0)
        d_in = np.min([np.hypot(X[:, :, 0] - c["centre"][0], Y[:, :, 0] - c["centre"][1]) - c["radius"] for c in fl["inner"]], axis=0)
        land = np.maximum(np.maximum(d_out, -d_in)[:, :, None], np.maximum(z_lo - Z, Z - z_hi))
        dens = np.maximum(dens, _density(land))
    for c in layout["bolts"]:
        dens = np.maximum(dens, _density(_capped(X, Y, Z, c, float(s["bolt_boss"]) / 2, z_lo, z_hi)))
    if lower:
        for m in layout["mounts"]:
            dens = np.maximum(dens, _density(_capped(X, Y, Z, m["centre"], float(s["mount_diameter"]) / 2, m["z"][0], m["z"][1])))
    return dens


def lug_webs(layout: dict, all_rooms: list[dict], z_split: float, thickness: float = 8.0, spread: float = 25.0) -> list[dict]:
    """(LOP-28) Production's gusseted lug at each mount: two webs from the lug's axis to the outside of its half's nearest
    room, either side of the nearest point (`spread` mm along the wall, or 0.6 of the lug's reach if more, as
    `implicit_draw`'s bracket), each `thickness` mm thick and standing from the lug's far end to the split. A lug hangs
    33-63 mm under the split with its bolt's room kept clear above it, so its webs join it from the side over its length,
    and stand on the split's plane, castable along the pull (13 October 04:08: a bracket read without them parted from its
    lug; 04:58: without its floor of metal mount-3's bracket left the output's bores hanging)."""
    wall = float(layout["settings"]["wall"])
    webs = []
    for m in layout["mounts"]:
        lower = m.get("pod", "motor_side") == "motor_side"
        c = np.asarray(m["centre"], float)
        best = None
        for p in cupmod.pieces(all_rooms, z_split, "motor_side" if lower else "cover"):
            ax = np.asarray(p["axis"], float)
            dist = float(np.hypot(*(c - ax)))
            r_s = float(p["r"]) + wall - 1.0  # a millimetre into the wall, so the web joins it
            if best is None or dist - r_s < best[0]:
                best = (dist - r_s, ax, r_s, dist)
        reach, ax, r_s, dist = best
        u = (c - ax) / max(dist, 1e-9)
        for sgn in (-1.0, 1.0):
            th = sgn * max(spread, 0.6 * reach) / r_s
            q = ax + r_s * np.array([u[0] * np.cos(th) - u[1] * np.sin(th), u[0] * np.sin(th) + u[1] * np.cos(th)])
            webs.append({"mount": m["name"], "from": c.tolist(), "to": q.tolist(), "thickness": thickness,
                         "z": [float(m["z"][0]), z_split] if lower else [z_split, float(m["z"][1])], "lower": lower})  # fmt: skip
    return webs


def seg_plan_dist(px, py, a, b) -> np.ndarray:
    """Each plan point's distance (mm) to the segment a-b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    t = np.clip(((px - a[0]) * d[0] + (py - a[1]) * d[1]) / max(float(d @ d), 1e-9), 0.0, 1.0)
    return np.hypot(px - (a[0] + t * d[0]), py - (a[1] + t * d[1]))


def lug_web_density(X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str, thickness: float = 8.0,
                    spread: float = 25.0) -> np.ndarray:  # fmt: skip
    """(LOP-28) The lugs' webs (`lug_webs`) in the field, 0.5 on their faces, empty in each bolt's room above and below
    its lug (the layout's brackets, kept clear)."""
    lower = half == "motor_side"
    dens = np.zeros(X.shape, np.float32)
    for w in lug_webs(layout, all_rooms, z_split, thickness, spread):
        if w["lower"] != lower:
            continue
        dp = seg_plan_dist(X[:, :, 0], Y[:, :, 0], w["from"], w["to"]) - w["thickness"] / 2
        dens = np.maximum(dens, _density(np.maximum(dp[:, :, None], np.maximum(w["z"][0] - Z, Z - w["z"][1]))))
    for b in layout.get("brackets", []):
        dens[(np.hypot(X - b["centre"][0], Y - b["centre"][1]) < b["radius"]) & (Z > b["z"][0]) & (Z < b["z"][1])] = 0.0
    return dens


def spoke_density(X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str, pitch_deg: float = 30.0,
                  thickness: float = 6.0, height: float = 10.0) -> np.ndarray:  # fmt: skip
    """(LOP-28) Production's panel spokes, in the field: from each of the half's bearing bosses, a radial rib every `pitch_deg`
    across the end walls' outer faces out to their rim, `thickness` mm thick and `height` mm proud of the wall (the trade's
    panel ribs, which raise a panel's modes: on 12 October they moved a cover mode out of s2's band for 0.1 kg). The end
    wall's outer face at each plan point is its outermost room's far face a least wall out; a spoke stops where no room
    lies beneath, at the rim. The optimiser does not see modes, so this is a deliberate design move, judged by FE."""
    s = layout["settings"]
    wall = float(s["wall"])
    lower = half == "motor_side"
    px, py = X[:, :, 0], Y[:, :, 0]
    face = np.full(px.shape, np.nan)
    for p in cupmod.pieces(all_rooms, z_split, half):
        inside = np.hypot(px - p["axis"][0], py - p["axis"][1]) <= p["r"]
        z_face = p["far"] - wall if lower else p["far"] + wall
        face = np.where(inside, np.fmin(face, z_face) if lower else np.fmax(face, z_face), face)
    plan = np.zeros(px.shape, bool)
    for b in layout["bearings"]:
        if (b["side"] == "-z") != lower:
            continue
        dx, dy = px - b["axis"][0], py - b["axis"][1]
        r = np.hypot(dx, dy)
        th = np.degrees(np.arctan2(dy, dx)) % pitch_deg
        off = np.minimum(th, pitch_deg - th)  # degrees to the nearest spoke
        plan |= (r >= float(b["boss_r"]) - 2.0) & (np.radians(off) * r <= thickness / 2)
    plan &= np.isfinite(face)
    zf = np.where(np.isfinite(face), face, 0.0)[:, :, None]
    if lower:
        band = (Z <= zf + 1.0) & (Z >= zf - height)
    else:
        band = (Z >= zf - 1.0) & (Z <= zf + height)
    return (plan[:, :, None] & band).astype(np.float32)


def least_sdf(X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str) -> np.ndarray:
    """(LOP-29) The half's least walls' signed distance (mm, negative in the metal) at their true faces: the cup's outside at
    the least wall (with the plate over the other half's opening), the sealing land and the seals' seats (`least_density`'s
    parts)."""
    s = layout["settings"]
    wall = float(s["wall"])
    lower = half == "motor_side"
    other = "cover" if lower else "motor_side"
    cup_d = np.full(X.shape, np.inf, np.float32)
    plan_d = np.full(X.shape[:2], np.inf, np.float32)
    for which in (half, other):
        for p in cupmod.pieces(all_rooms, z_split, which):
            far = p["far"] if which == half else z_split
            z_lo, z_hi = sorted((far, z_split))
            cup_d = np.minimum(cup_d, _capped(X, Y, Z, p["axis"], p["r"], z_lo, z_hi).astype(np.float32))
            plan_d = np.minimum(plan_d, (np.hypot(X[:, :, 0] - p["axis"][0], Y[:, :, 0] - p["axis"][1]) - p["r"]).astype(np.float32))
    sdf = cup_d - wall
    fl = layout.get("flange") or {}
    if fl:
        # the band round the inside, outside it (14 October: the inside too had drawn the shell 8 mm under the other half's rooms)
        band = np.maximum(plan_d - float(fl["land_width"]), -plan_d)
        sdf = np.minimum(sdf, np.maximum(band[:, :, None], np.abs(Z - z_split) - float(fl["thickness"])))
    seat = _seal_seat_mm()
    for e in layout.get("exits") or []:
        if e["kind"] != "seal" or (e["z"][1] <= z_split) != lower:
            continue
        inner = e["z"][1] if lower else e["z"][0]
        z_lo, z_hi = (inner, inner + seat) if lower else (inner - seat, inner)
        sdf = np.minimum(sdf, _capped(X, Y, Z, e["centre"], e["radius"] + wall, z_lo, z_hi))
    return sdf.astype(np.float32)


def interface_sdf(X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str, towers: bool = True) -> np.ndarray:
    """(LOP-29) The half's protected interfaces' signed distance (mm, negative in the metal) at their true faces
    (`interface_density`'s parts: the bearings' towers, the sealing land, the bolts' bosses, the mounts' lugs)."""
    s = layout["settings"]
    wall = float(s["wall"])
    lower = half == "motor_side"
    sdf = np.full(X.shape, np.inf, np.float32)
    for b in layout["bearings"] if towers else []:  # (LOP-29) the run's towers, or none
        if (b["side"] == "-z") != lower:
            continue
        z0, z1 = b["z"]
        z_lo, z_hi = (z0 - wall, z_split) if lower else (z_split, z1 + wall)
        sdf = np.minimum(sdf, _capped(X, Y, Z, b["axis"], float(b["boss_r"]), z_lo, z_hi))
    fl = layout.get("flange") or {}
    t_f = float(fl.get("thickness", s["flange_thickness"]))
    z_lo, z_hi = (z_split - t_f, z_split) if lower else (z_split, z_split + t_f)
    if fl:
        d_out = np.min([np.hypot(X[:, :, 0] - c["centre"][0], Y[:, :, 0] - c["centre"][1]) - c["radius"] for c in fl["outer"]], axis=0)
        d_in = np.min([np.hypot(X[:, :, 0] - c["centre"][0], Y[:, :, 0] - c["centre"][1]) - c["radius"] for c in fl["inner"]], axis=0)
        sdf = np.minimum(sdf, np.maximum(np.maximum(d_out, -d_in)[:, :, None], np.maximum(z_lo - Z, Z - z_hi)))
    for c in layout["bolts"]:
        sdf = np.minimum(sdf, _capped(X, Y, Z, c, float(s["bolt_boss"]) / 2, z_lo, z_hi))
    if lower:
        for m in layout["mounts"]:
            sdf = np.minimum(sdf, _capped(X, Y, Z, m["centre"], float(s["mount_diameter"]) / 2, m["z"][0], m["z"][1]))
    return sdf.astype(np.float32)


def least_density(X, Y, Z, layout: dict, all_rooms: list[dict], z_split: float, half: str) -> np.ndarray:
    """The half's least walls as a density on the grid's cells (X, Y, Z), 0.5 on their faces, from the
    exact geometry: the cup's outside at the least wall (with the plate over the other half's
    opening), the sealing land and the seals' seats."""
    s = layout["settings"]
    wall = float(s["wall"])
    lower = half == "motor_side"
    other = "cover" if lower else "motor_side"
    cup_d = np.full(X.shape, np.inf, np.float32)
    plan_d = np.full(X.shape[:2], np.inf, np.float32)
    for which in (half, other):
        for p in cupmod.pieces(all_rooms, z_split, which):
            far = p["far"] if which == half else z_split  # the other half's room: a disc at the split
            z_lo, z_hi = sorted((far, z_split))
            cup_d = np.minimum(cup_d, _capped(X, Y, Z, p["axis"], p["r"], z_lo, z_hi).astype(np.float32))
            plan_d = np.minimum(plan_d, (np.hypot(X[:, :, 0] - p["axis"][0], Y[:, :, 0] - p["axis"][1]) - p["r"]).astype(np.float32))
    dens = _density(cup_d - (wall - GRID_BIAS))
    fl = layout.get("flange") or {}
    if fl:  # the sealing land: within its width of the inside in plan, its depth from the split
        band = np.maximum(plan_d - (float(fl["land_width"]) - GRID_BIAS), -plan_d)  # the band round the inside, outside it
        land = np.maximum(band[:, :, None], np.abs(Z - z_split) - (float(fl["thickness"]) - GRID_BIAS))
        dens = np.maximum(dens, _density(land))
    seat = _seal_seat_mm()
    for e in layout.get("exits") or []:
        if e["kind"] != "seal" or (e["z"][1] <= z_split) != lower:
            continue
        inner = e["z"][1] if lower else e["z"][0]  # the exit's end nearest the inside
        z_lo, z_hi = (inner, inner + seat) if lower else (inner - seat, inner)
        dens = np.maximum(dens, _density(_capped(X, Y, Z, e["centre"], e["radius"] + wall - GRID_BIAS, z_lo, z_hi)))
    return dens
