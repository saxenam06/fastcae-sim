"""The design drawn from the optimisation's field (moved from
`prototypes/first_loop/outcome_cad.py`: `field_of`, `rooms_mask`, `skin_parts`, `cube_fidelity`,
`build_mesh` on the final recipe's path; LOP-33).

The final recipe's run is an empty start (no fixed shell: its walls are its own metal) with its
interfaces protected and no bearings' towers. It is drawn as one field on a fine grid, each half in
turn:
- the members from the run's columns (`columns`), their free edges rounded, joined to the least
  walls and the protected interfaces (`walls`, exact in the same field) with filleted roots;
- the mounts, the sealing land and the bolts' bosses as fixed metal, blurred once;
- the kept-clear spaces (the exits, the vehicle's brackets, the bolts' sockets) cut smoothly;
- contoured at 0.5 (marching cubes), cut flat at the split, then every exact cut by manifold3d (the
  exits, the brackets' rooms, the inside, the bearings' bores and their paths in, the mounts' and
  the bolts' holes, each bolt's socket where the half holds its boss), its largest piece kept.
Each half is written as `<design>_<half>.stl` and `.ply`, the organic body before the cuts as
`<design>_organic_<half>.stl`, the record as `<design>.json` (with `<design>_organic.json`).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import cup as cupmod
from zenryx.domains.gearbox.housing import mesh as mr
from zenryx.domains.gearbox.housing import say
from zenryx.domains.gearbox.housing.columns import members_sdf, run_columns
from zenryx.domains.gearbox.housing.walls import (
    density,
    extra_placed,
    interface_sdf,
    least_sdf,
    ramp,
    round_union,
    seal_seat_mm,
)

BURY = 2.0  # mm: the fixed parts' grid copies stand this far under their exact faces
FIXED_BLUR = 1.0  # cells: the fixed parts blurred once
FINE_MARGIN = 2.0  # mm: a kept-clear space emptied this far past its boundary
ROUND_MM = 3.0  # the members' free edges rounded
FILLET_MM = 4.0  # the members' roots filleted to the exact parts


@dataclass(frozen=True)
class DrawSettings:
    """The recipe's drawing settings (its `LOOP_*` environment)."""

    plan_sigma_mm: float  # LOOP_VOXEL_SMOOTH: the outline blurred among a column's peers
    smooth_mm: float  # LOOP_DRAW_SMOOTH: each member's free end smoothed in plan
    smooth_range_mm: float  # LOOP_DRAW_SMOOTH_RANGE: steps taller than this kept
    fine_mm: float  # LOOP_DRAW_FINE: the drawing's grid

    @classmethod
    def from_env(cls, env) -> DrawSettings:
        return cls(
            plan_sigma_mm=float(env["LOOP_VOXEL_SMOOTH"]),
            smooth_mm=float(env["LOOP_DRAW_SMOOTH"]),
            smooth_range_mm=float(env["LOOP_DRAW_SMOOTH_RANGE"]),
            fine_mm=float(env["LOOP_DRAW_FINE"]),
        )


def field_of(z) -> dict:
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    rho = np.zeros(int(np.prod(n)))
    rho[z["elem"][z["frozen"].astype(bool)]] = 1.0
    rho[z["elem"][z["free_e"]]] = np.maximum(rho[z["elem"][z["free_e"]]], z["phys"])
    return {"rho": rho.reshape(n), "n": n, "lo": lo, "h": h, "k_split": int(z["k_split"])}


def rooms_mask(f: dict, all_rooms: list[dict], z_split: float, half: str) -> np.ndarray:
    """The cells inside the half's cup (every room's footprint from its far end to the split)."""
    n, lo, h = f["n"], f["lo"], f["h"]
    xs, ys, zs = (lo[i] + h * (np.arange(n[i]) + 0.5) for i in range(3))
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    inside = np.zeros(tuple(n), bool)
    for p in cupmod.pieces(all_rooms, z_split, half):
        span = (
            (gz >= p["far"]) & (gz <= z_split)
            if half == "motor_side"
            else (gz <= p["far"]) & (gz >= z_split)
        )
        inside |= span & (np.hypot(gx - p["axis"][0], gy - p["axis"][1]) <= p["r"])
    return inside


def half_parts(
    f: dict,
    layout: dict,
    all_rooms: list[dict],
    z_split: float,
    half: str,
    cols: dict,
    seat: float,
    fine: float,
    st: DrawSettings,
) -> dict:
    """What a half holds on the fine grid: the members joined to the exact parts (`members`), their
    faces' ramp (`exact`), the fixed metal (`fixed`), the inside (`cavity`) and the kept-clear
    spaces (`clear`, and `clear_sdf` their signed distance)."""
    from matplotlib.path import Path as Polygon
    from scipy.ndimage import distance_transform_edt

    s = layout["settings"]
    lower = half == "motor_side"
    h, lo, n = f["h"], f["lo"], f["n"]
    n_f = np.ceil(n * h / fine).astype(int)
    lo_f = np.asarray(lo, float)
    xs, ys, zs = (lo_f[i] + fine * (np.arange(n_f[i]) + 0.5) for i in range(3))
    gx, gy, gz = np.meshgrid(
        *((v.astype(np.float32) for v in (xs, ys, zs)) if fine < 2.0 else (xs, ys, zs)),
        indexing="ij",
    )
    ks = int(np.searchsorted(zs, z_split))  # the first cell above the split
    side = (gz < z_split) if lower else (gz >= z_split)
    fine_grid = {"n": n_f, "lo": lo_f, "h": fine}
    cavity = rooms_mask(fine_grid, all_rooms, z_split, half)
    union = cavity | rooms_mask(fine_grid, all_rooms, z_split, "cover" if lower else "motor_side")
    metal = (
        cavity.copy()
    )  # the walls are the field's: the rooms only, filled for the exact cut after
    # the members, from the run's columns, as a signed distance; the families part on the cup's
    # outline (its wall's mid-line)
    px_, py_ = np.meshgrid(xs, ys, indexing="ij")
    footprint = np.zeros(px_.shape, bool)
    for pc in cupmod.pieces(all_rooms, z_split, half):
        footprint |= (
            np.hypot(px_ - pc["axis"][0], py_ - pc["axis"][1]) <= float(pc["r"]) + 0.5 * s["wall"]
        )
    mem_sdf = members_sdf(cols, half, f, xs, ys, zs, footprint, st.smooth_mm, st.smooth_range_mm)
    # the least walls and the protected interfaces at their true faces, the members joined to them
    # with filleted roots
    exact_sdf = least_sdf(gx, gy, gz, layout, all_rooms, z_split, half, seat)
    exact_sdf = np.minimum(exact_sdf, interface_sdf(gx, gy, gz, layout, z_split, half))
    members = np.maximum(
        np.zeros(mem_sdf.shape, np.float32), ramp(round_union(mem_sdf, exact_sdf, FILLET_MM), fine)
    )
    members = np.maximum(
        members, density(exact_sdf + fine)
    )  # the cells' copy, a cell inside the faces
    t_f = s["flange_thickness"]
    for m in layout["mounts"] if lower else []:
        r_m = np.hypot(gx - m["centre"][0], gy - m["centre"][1])
        metal |= (
            (r_m <= s["mount_diameter"] / 2 - BURY)
            & (gz >= m["z"][0] + BURY)
            & (gz <= m["z"][1] - BURY)
        )
    outline = Polygon(np.asarray(layout["joint_outline"], float))
    plan = outline.contains_points(
        np.column_stack([gx[:, :, 0].ravel(), gy[:, :, 0].ravel()])
    ).reshape(gx.shape[:2])
    # the joint's face: the sealing land round the whole inside at the split and each bolt's boss on
    # it, a flange thick
    foot = union[:, :, ks - 1] | union[:, :, ks]
    land = (
        distance_transform_edt(~foot) * fine <= layout["flange"]["land_width"] - BURY + 0.5 * fine
    ) & ~foot
    for c in layout["bolts"]:
        land |= np.hypot(gx[:, :, 0] - c[0], gy[:, :, 0] - c[1]) <= s["bolt_boss"] / 2 - BURY
    metal |= (land & plan)[:, :, None] & (np.abs(gz - z_split) <= t_f - BURY) & side
    # the kept-clear spaces: the exits, the vehicle's bracket beyond each end of each mount, each
    # bolt's head and a hex key's room over it; as cells and as a signed distance (a cylinder's the
    # larger of its radial and axial distance)
    clear = np.zeros(gx.shape, bool)
    clear_sdf = np.full(gx.shape, np.inf, np.float32)

    def cyl_sdf(cx_, cy_, r_, z0_, z1_):
        return np.maximum(np.hypot(gx - cx_, gy - cy_) - r_, np.maximum(z0_ - gz, gz - z1_)).astype(
            np.float32
        )

    for e in layout.get("exits") or []:
        r_e = np.hypot(gx - e["centre"][0], gy - e["centre"][1])
        clear |= (r_e < e["radius"] + FINE_MARGIN) & (gz >= e["z"][0]) & (gz <= e["z"][1])
        clear_sdf = np.minimum(
            clear_sdf, cyl_sdf(e["centre"][0], e["centre"][1], e["radius"], e["z"][0], e["z"][1])
        )
    centre_of = {m["name"]: m["centre"] for m in layout["mounts"]}
    for b in layout.get("brackets") or []:
        cx, cy = b.get("centre") or centre_of[b["name"].split(" bracket")[0]]
        clear |= (
            (np.hypot(gx - cx, gy - cy) < b["radius"] + FINE_MARGIN)
            & (gz >= b["z"][0])
            & (gz <= b["z"][1])
        )
        clear_sdf = np.minimum(clear_sdf, cyl_sdf(cx, cy, b["radius"], b["z"][0], b["z"][1]))
    d_sock, h_sock = s["bolt_socket"]
    for c in layout["bolts"]:
        r_c = np.hypot(gx - c[0], gy - c[1])
        beyond = (
            (gz < z_split - t_f) & (gz >= z_split - t_f - h_sock)
            if lower
            else (gz > z_split + t_f) & (gz <= z_split + t_f + h_sock)
        )
        clear |= (r_c < d_sock / 2 + FINE_MARGIN) & beyond
        z0_s, z1_s = (
            (z_split - t_f - h_sock, z_split - t_f)
            if lower
            else (z_split + t_f, z_split + t_f + h_sock)
        )
        clear_sdf = np.minimum(clear_sdf, cyl_sdf(c[0], c[1], d_sock / 2, z0_s, z1_s))
    exact = np.where(side & ~clear, ramp(exact_sdf, fine), 0.0).astype(np.float32)
    return {
        "lo": lo_f,
        "ks": ks,
        "side": side,
        "cavity": cavity,
        "fixed": metal & side,
        "members": members,
        "clear": clear,
        "clear_sdf": clear_sdf,
        "exact": exact,
    }


def cube_fidelity(
    placed: np.ndarray,
    f: dict,
    halves: dict,
    organic: dict,
    parts: dict,
    z_split: float,
    fine: float,
) -> dict:
    """How many of the run's metal cubes (`placed`, on its own grid) the drawn halves hold, each
    cube's centre tested inside its half's drawn mesh: lost by the drawing, in a space the drawing
    keeps clear, or loose in the run's own field (joined to nothing). A report: the columns' outline
    holds each cube by its share, not whole."""
    import pyvista as pv
    from scipy.ndimage import label

    def inside(body, pts: np.ndarray) -> np.ndarray:
        tm = mr.to_trimesh(body)
        surf = pv.PolyData(
            np.asarray(tm.vertices),
            np.hstack([np.full((len(tm.faces), 1), 3), np.asarray(tm.faces)]).ravel(),
        )
        sel = pv.PolyData(pts).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)
        return np.asarray(sel["SelectedPoints"]).astype(bool)

    h, lo = float(f["h"]), np.asarray(f["lo"], float)
    ijk = np.argwhere(placed)
    # the run's own loose metal: placed cubes outside their half's largest face-joined piece of
    # metal (the fixed cubes too)
    metal = np.asarray(f["rho"]) >= 0.5
    joined = np.zeros(metal.shape, bool)
    ks_ = int(f["k_split"])
    for sl in (np.s_[:, :, :ks_], np.s_[:, :, ks_:]):
        lab, k = label(metal[sl])
        if k:
            sizes = np.bincount(lab.ravel())
            sizes[0] = 0
            joined[sl] = lab == int(np.argmax(sizes))
    loose_cube = ~joined[tuple(ijk.T)] if len(ijk) else np.zeros(0, bool)
    centres = lo[None, :] + h * (ijk + 0.5)
    offs = (
        0.25 * h * np.array([[a, b, c] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)], float)
    )  # a point in each octant
    own, clear, loose = 0, 0, 0
    for half, body in halves.items():
        mine = centres[:, 2] < z_split if half == "motor_side" else centres[:, 2] >= z_split
        if not mine.any():
            continue
        pts = centres[mine]
        lost = ~inside(body, pts)
        loose_here = lost & loose_cube[mine]
        loose += int(loose_here.sum())
        lost &= ~loose_here
        if not lost.any():
            continue
        kept_clear = inside(organic[half], pts[lost])
        grid = parts[half]["clear"]
        lo_f = np.asarray(parts[half]["lo"], float)
        for o in offs:
            idx = np.floor((pts[lost] + o - lo_f) / fine).astype(int)
            ok = np.all((idx >= 0) & (idx < np.asarray(grid.shape)), axis=1)
            kept_clear[ok] |= grid[tuple(idx[ok].T)]
        clear += int(kept_clear.sum())
        own += int((~kept_clear).sum())
    n = max(len(centres), 1)
    out = {
        "cubes": int(len(centres)),
        "lost": own,
        "lost_share": own / n,
        "kept_clear": clear,
        "kept_clear_share": clear / n,
        "loose": loose,
        "loose_share": loose / n,
    }
    say(
        f"the drawing holds {len(centres) - own - clear - loose:,} of the run's {len(centres):,} "
        f"metal cubes: {own:,} lost by the drawing "
        f"({100 * out['lost_share']:.2f} %), {clear:,} in spaces it keeps clear "
        f"({100 * out['kept_clear_share']:.2f} %), "
        f"{loose:,} loose in the run's own field, joined to nothing "
        f"({100 * out['loose_share']:.2f} %)"
    )
    return out


def draw(run: str, design: str, out: Path, contract: Path, st: DrawSettings) -> dict:
    """The design drawn from the run `run` (its `<run>.json` and `.npz` in `out`); its record."""
    import manifold3d as mf
    from scipy.ndimage import gaussian_filter

    t0 = time.time()
    rec = json.loads((out / f"{run}.json").read_text(encoding="utf-8"))
    if not (
        rec.get("empty")
        and rec.get("protect")
        and rec.get("towers") is False
        and rec.get("layout") == "contract"
    ):
        raise ValueError(
            f"{run} is not a run of the final recipe (an empty start on the contract's layout, "
            "protected, no towers)"
        )
    layout = json.loads((out / "contract.json").read_text(encoding="utf-8"))
    s = layout["settings"]
    spec, _ = load_and_validate(contract)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial, axial = (
        value_in(gaps.min_radial_clearance, "mm"),
        value_in(gaps.min_axial_clearance, "mm"),
    )
    z_split, wall, draft = layout["z"]["split"], s["wall"], s.get("draft", 0.0)
    bearings, bolts, mounts = layout["bearings"], layout["bolts"], layout["mounts"]
    brackets = {b["name"]: b for b in layout.get("brackets", [])}
    t_f = s["flange_thickness"]
    fine = st.fine_mm
    z = np.load(out / f"{run}.npz")
    f = field_of(z)
    all_rooms = cupmod.rooms(chain, radial, axial)
    placed = extra_placed(z)
    cols = run_columns(z, st.plan_sigma_mm, ROUND_MM)
    say(
        f"{run[:60]}...: drawn as a spline run, {cols['holding']:,} of {cols['columns']:,} columns "
        "holding metal, the outline blurred "
        f"over {st.plan_sigma_mm:g} mm, the free edges rounded {ROUND_MM:g} mm"
    )
    seat = seal_seat_mm(spec)
    parts: dict = {}
    halves, organic, kept_of, held = {}, {}, {}, list(mounts)
    for half in ("motor_side", "cover"):
        p = half_parts(f, layout, all_rooms, z_split, half, cols, seat, fine, st)
        t1 = time.time()
        lower = half == "motor_side"
        ks = p["ks"]
        # the members cut smoothly by the kept-clear spaces FINE_MARGIN past them; the fixed parts
        # blurred once and cut at the spaces themselves; the exact faces' ramp held
        own = np.where(
            p["side"] & ~p["cavity"],
            np.minimum(p["members"], ramp(FINE_MARGIN - p["clear_sdf"], fine)),
            0.0,
        )
        fixed_s = gaussian_filter(p["fixed"].astype(np.float32), sigma=FIXED_BLUR)
        fixed_s = np.minimum(fixed_s, ramp(-p["clear_sdf"], fine))
        rho_s = np.maximum(fixed_s, own)
        held_up = p["exact"].copy()
        for k in (
            (ks, ks + 1, ks + 2) if lower else (ks - 1, ks - 2, ks - 3)
        ):  # carried past the split, cut flat after
            rho_s[:, :, k] = rho_s[:, :, ks - 1 if lower else ks]
            held_up[:, :, k] = held_up[:, :, ks - 1 if lower else ks]
        rho_s = np.maximum(rho_s, held_up)
        rho_s[np.abs(rho_s - 0.5) < 1e-6] = (
            0.5 + 1e-5
        )  # a node exactly at the level makes degenerate triangles
        body = mr.from_trimesh(mr.contour(rho_s, p["lo"], fine, 0.5))
        body = body ^ mr.half_space(z_split, keep_below=lower)  # cut flat at the split
        organic[half] = body
        cuts = []
        for e in layout.get("exits") or []:
            z0, z1 = e["z"]
            if (z1 <= z_split) == lower:
                cuts.append(
                    mr.cylinder(e["centre"], z0 - 1.0, z1 + 1e-3, 2 * e["radius"])
                    if lower
                    else mr.cylinder(e["centre"], z0 - 1e-3, z1 + 1.0, 2 * e["radius"])
                )
        for m in mounts:  # the vehicle's bracket and bolt beyond both faces
            for end in ("-z", "+z"):
                room = brackets[f"{m['name']} bracket {end}"]
                cuts.append(
                    mr.cylinder(m["centre"], room["z"][0], room["z"][1], 2 * room["radius"])
                )
        cuts.append(
            mr.from_shape(cupmod.cup(all_rooms, z_split, half, wall, draft)[1])
        )  # the inside, exact
        for b in bearings:
            if (b["side"] == "-z") != lower:
                continue
            z0, z1 = b["z"]
            cuts.append(mr.cylinder(b["axis"], z0, z1, b["D"]))
            cuts.append(
                mr.cylinder(b["axis"], *sorted((z1 if lower else z0, z_split)), b["D"] + 1.0)
            )  # its path in from the split
        for m in mounts if lower else []:
            cuts.append(mr.cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
        # a bolt joins the halves where the body holds most of its boss: its head's seat and a hex
        # key's room cut, its hole through
        kept = []
        for c in bolts:
            boss = (
                mr.cylinder(c, z_split - t_f, z_split, s["bolt_boss"])
                if lower
                else mr.cylinder(c, z_split, z_split + t_f, s["bolt_boss"])
            )
            if mr.volume_of(body ^ boss) > 0.6 * mr.volume_of(boss):
                kept.append(c)
                d_s, h_s = s["bolt_socket"]
                cuts.append(
                    mr.cylinder(c, z_split - t_f - h_s, z_split - t_f, d_s)
                    if lower
                    else mr.cylinder(c, z_split + t_f, z_split + t_f + h_s, d_s)
                )
                cuts.append(
                    mr.cylinder(c, z_split - t_f - 1.0, z_split + t_f + 1.0, s["bolt_hole"])
                )
        body = body - mf.Manifold.batch_boolean(cuts, mf.OpType.Add)
        body, dropped = mr.largest(body)
        if dropped:
            say(f"{half}: {dropped / 1e3:.1f} cm3 of loose pieces dropped")
        if lower:
            held = []
            for m in mounts:
                ring = mr.cylinder(
                    m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]
                ) - mr.cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"])
                if mr.volume_of(body ^ ring) > 0.6 * mr.volume_of(ring):
                    held.append(m)
        halves[half], kept_of[half] = body, kept
        tm = mr.to_trimesh(body)
        tm.export(str(out / f"{design}_{half}.stl"))
        tm.export(str(out / f"{design}_{half}.ply"))  # indexed: manifold3d's own topology, for FE
        mr.to_trimesh(organic[half]).export(str(out / f"{design}_organic_{half}.stl"))
        say(
            f"{half}: by the mesh route in {time.time() - t1:.1f} s: {len(tm.faces):,} triangles, "
            f"watertight {tm.is_watertight}, "
            f"{mr.volume_of(body) / 1e3:.0f} cm3, {len(kept)} of {len(bolts)} bolts' bosses held"
        )
        parts[half] = {
            "clear": p["clear"],
            "lo": p["lo"],
        }  # what the cube check reads; the half's grids freed
        p = rho_s = own = fixed_s = held_up = None
    fidelity = cube_fidelity(placed, f, halves, organic, parts, z_split, fine)
    both = set(map(tuple, kept_of["motor_side"])) & set(map(tuple, kept_of["cover"]))
    bolts_used = [list(c) for c in bolts if tuple(c) in both]
    if len(held) < len(mounts):
        say(f"{design}: the body holds {len(held)} of the layout's {len(mounts)} mounts")
    mass = {half: mr.volume_of(body) * s["density"] for half, body in halves.items()}
    record = {
        **layout,
        "stem": design,
        "form": "outcome",
        "drawing": "one field",
        "route": "mesh",
        "empty": True,
        "skin": {
            "exact_walls": True,
            "protect": True,
            "fidelity": fidelity,
            "grid_mm": fine,
            "voxel_smooth": {
                "plan_sigma_mm": st.plan_sigma_mm,
                "round_mm": ROUND_MM,
                "fillet_mm": FILLET_MM,
            },
            "draw_smooth_mm": st.smooth_mm,
            "draw_smooth_range_mm": st.smooth_range_mm,
        },
        "outcome_of": run,
        "bolts": bolts_used,
        "mounts": held,
        "mounts_layout": mounts,
        "mass_kg": {**mass, "total": sum(mass.values())},
        "faces": {},
        "files": {half: f"{design}_{half}.stl" for half in halves},
        "seconds": time.time() - t0,
    }
    (out / f"{design}.json").write_text(
        json.dumps(record, indent=1, default=list), encoding="utf-8"
    )
    mass_o = {half: mr.volume_of(body) * s["density"] for half, body in organic.items()}
    shown = {
        **record,
        "stem": f"{design}_organic",
        "form": "organic",
        "organic_of": design,
        "mass_kg": {**mass_o, "total": sum(mass_o.values())},
        "files": {half: f"{design}_organic_{half}.stl" for half in organic},
    }
    (out / f"{design}_organic.json").write_text(
        json.dumps(shown, indent=1, default=list), encoding="utf-8"
    )
    say(
        f"{design}: {record['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, "
        f"cover {mass['cover']:.2f}); "
        f"bolts joining the halves {len(bolts_used)} of {len(bolts)}; drawn in "
        f"{record['seconds']:.0f} s"
    )
    return record
