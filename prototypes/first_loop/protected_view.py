"""PROTOTYPE (LOP-29) - the fixed set as geometry, from the contract's layout (`data/first_loop/contract.json`), not a mesh of a
design (the engineer, 13 October 22:44: "a picture of the protected regions... some kind of a geometrical figure"; 14 October
00:13: the fixed set is the shell, the sealing land, the bolts' bores, the bearing bores and the mounts, one description for the
optimiser, the drawing and FE). Each part exact, as `exact_walls.least_sdf` and `interface_sdf` describe it:
- the shell: 4 mm round the whole gearbox (gears, shafts, bearings), split at the split plane: in each half the walls round its
  rooms (each room from its far end to the split, `cup.pieces`), the seals' seats (A16) and, where the other half's rooms reach
  past its own at the split, the shell closing them;
- the bearing bores, marked where the loads act (red);
- the sealing land: the band between the layout's outer and inner outlines (10 mm round the inside), a flange deep each half;
- the bolts' bores: each bolt's boss (Ø 20 mm round its Ø 9 mm hole), a flange deep;
- on the motor side, the mounts' lugs (Ø 36 mm round their Ø 11 mm holes).
With `--towers`, each bearing's tower too (Ø 1.25·D + 10 mm, from a least wall past its seat to the split; LOP-28's, off in
the baselines since 13 October 23:49). Each half from outside and from the split, the rooms ghosted, then each half in plan
along its pull from outside. Writes data/first_loop/protected_regions.png.

Run: .venv/Scripts/python.exe prototypes/first_loop/protected_view.py [--towers]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE.parents[1] / "data" / "first_loop"
COLOURS = {"shell": "#9aa7b8", "land": "#e2c044", "boss": "#2e9e5b", "lug": "#8e5bb5", "load": "#d23c32", "tower": "#5b3fa0",
           "room": "#c9ced6"}  # fmt: skip
NAMES = {"shell": "the shell: 4 mm round the whole gearbox, split in two", "land": "the sealing land: 10 mm wide, 8 mm deep each half",
         "boss": "the bolts' bores: Ø 20 mm bosses round Ø 9 mm holes (the halves tied here)",
         "lug": "the mounts' lugs: Ø 36 mm round Ø 11 mm holes (the housing held here)", "load": "the bearing bores (the loads act here)",
         "tower": "bearing towers (Ø 1.25·D + 10 mm)", "room": "the rooms inside (gears, bearings), for orientation"}  # fmt: skip


def solids(lay: dict, all_rooms: list[dict], half: str, towers: bool = False):
    """The half's fixed solids (manifold3d) by kind, each part disjoint from the others, and its rooms."""
    import manifold3d as mf

    import cup as cupmod
    import exact_walls as ew
    import mesh_route as mr

    s = lay["settings"]
    z_s = float(lay["z"]["split"])
    t_f = float(lay["flange"]["thickness"])
    wall = float(s["wall"])
    lower = half == "motor_side"
    other = "cover" if lower else "motor_side"

    def union(parts):
        parts = [p for p in parts if not p.is_empty()]
        return mf.Manifold.batch_boolean(parts, mf.OpType.Add) if parts else mf.Manifold()

    own = cupmod.pieces(all_rooms, z_s, half)
    z_open = z_s + 1.0 if lower else z_s - 1.0  # the rooms run a millimetre past the split: a cut flush with it left a lid
    room = union([mr.cylinder(p["axis"], *sorted((p["far"], z_open)), 2 * p["r"]) for p in own])
    grown = union([mr.cylinder(p["axis"], p["far"] - wall if lower else z_s, z_s if lower else p["far"] + wall, 2 * (p["r"] + wall)) for p in own])
    z_pl = (z_s - wall, z_s) if lower else (z_s, z_s + wall)
    slab = union([mr.cylinder(p["axis"], *z_pl, 2 * (p["r"] + wall)) for p in cupmod.pieces(all_rooms, z_s, other)])
    seat = ew._seal_seat_mm()
    seals, exits = [], []
    for e in lay.get("exits") or []:
        if (e["z"][1] <= z_s) != lower:
            continue
        exits.append(mr.cylinder(e["centre"], e["z"][0] - 1.0, e["z"][1] + 1.0, 2 * e["radius"]))
        if e["kind"] == "seal":
            inner = e["z"][1] if lower else e["z"][0]
            seals.append(mr.cylinder(e["centre"], *((inner, inner + seat) if lower else (inner - seat, inner)), 2 * (e["radius"] + wall)))
    cut = union([room, *exits])
    shell = union([grown, slab, *seals]) - cut
    zl, zh = (z_s - t_f, z_s) if lower else (z_s, z_s + t_f)
    fl = lay["flange"]
    land = union([mr.cylinder(c["centre"], zl, zh, 2 * c["radius"]) for c in fl["outer"]]) - union(
        [mr.cylinder(c["centre"], zl - 1, zh + 1, 2 * c["radius"]) for c in fl["inner"]]
    )
    boss_full = union([mr.cylinder(c, zl, zh, s["bolt_boss"]) for c in lay["bolts"]])
    holes = union([mr.cylinder(c, zl - 1, zh + 1, s["bolt_hole"]) for c in lay["bolts"]])
    out = {}
    out["land"] = land - boss_full
    out["boss"] = boss_full - holes
    out["shell"] = shell - land - boss_full
    # each bearing bore marked where its load acts: a skin a millimetre thick on the bore's face, along the seat
    out["load"] = union([mr.cylinder(b["axis"], b["z"][0], b["z"][1], b["D"]) - mr.cylinder(b["axis"], b["z"][0] - 1, b["z"][1] + 1, b["D"] - 2.0)
                         for b in lay["bearings"] if (b["side"] == "-z") == lower])  # fmt: skip
    if lower:
        out["lug"] = union([mr.cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]) - mr.cylinder(m["centre"], m["z"][0] - 1, m["z"][1] + 1, s["mount_hole"])
                            for m in lay["mounts"]])  # fmt: skip
    if towers:
        tw = []
        for b in lay["bearings"]:
            if (b["side"] == "-z") != lower:
                continue
            z0, z1 = b["z"]
            z_lo, z_hi = (z0 - wall, z_s - 0.1) if lower else (z_s + 0.1, z1 + wall)  # 0.1 mm short of the split, for the picture alone
            tw.append(mr.cylinder(b["axis"], z_lo, z_hi, 2 * float(b["boss_r"])))
        out["tower"] = union(tw) - cut - shell - land - boss_full
    return {k: v for k, v in out.items() if not v.is_empty()}, room


def to_pv(man):
    import pyvista as pv

    import mesh_route as mr

    tm = mr.to_trimesh(man)
    return pv.PolyData(np.asarray(tm.vertices), np.hstack([np.full((len(tm.faces), 1), 3), np.asarray(tm.faces)]).ravel())


def render(out: dict, room, half: str, inside: bool, path: Path) -> None:
    """One half from outside along its pull, or from the split looking in, a little off the pull; y down the page."""
    import pyvista as pv

    pl = pv.Plotter(off_screen=True, window_size=(1100, 1000))
    pl.set_background("white")
    if not inside:  # from the split the rooms' faces lie on the walls' own and stripe them
        pl.add_mesh(to_pv(room), color=COLOURS["room"], opacity=0.16, smooth_shading=True)
    for kind, man in out.items():
        pl.add_mesh(to_pv(man), color=COLOURS[kind], smooth_shading=True, specular=0.2)
    pl.view_xy()
    c = np.array(pl.camera.focal_point)
    below = (half == "motor_side") != inside  # the motor side's outside is below it, its inside above
    look = np.array([0.30, 0.35, -0.89 if below else 0.89])
    pl.camera.position = tuple(c + 900.0 * look / np.linalg.norm(look))
    pl.camera.up = (0.0, -1.0, 0.0)
    pl.reset_camera()
    pl.camera.zoom(1.35)
    name = "the motor side" if half == "motor_side" else "the cover"
    pl.add_text(f"{name}, from {'the split, looking in' if inside else 'outside'}", font_size=12, color="black")
    pl.screenshot(str(path))
    pl.close()


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from PIL import Image

    import cup as cupmod
    import topo
    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.complete import complete_chain
    from zenryx.domains.gearbox.forces import value_in

    ap = argparse.ArgumentParser()
    ap.add_argument("--towers", action="store_true", help="the bearing towers too (LOP-28's set)")
    a = ap.parse_args()
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(topo.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    parts = {half: solids(lay, all_rooms, half, a.towers) for half in ("motor_side", "cover")}
    kinds = [k for k in NAMES if k != "room" and any(k in out for out, _ in parts.values())]

    rows = []
    for inside in (False, True):
        files = []
        for half, (out, room) in parts.items():
            f = OUT / f"protected_regions_3d_{half}_{'in' if inside else 'out'}.png"
            render(out, room, half, inside, f)
            files.append(f)
        ims = [Image.open(f).convert("RGB") for f in files]
        row = Image.new("RGB", (sum(i.width for i in ims), max(i.height for i in ims)), "white")
        x_ = 0
        for i in ims:
            row.paste(i, (x_, 0))
            x_ += i.width
        rows.append(row)

    # in plan, each half along its pull from outside: the parts as filled outlines, sampled on a 0.5 mm grid
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.4))
    s = lay["settings"]
    wall = float(s["wall"])
    xs = np.arange(min(p[0] for p in lay["outline"]) - 20, max(p[0] for p in lay["outline"]) + 20, 0.5)
    ys = np.arange(min(p[1] for p in lay["outline"]) - 20, max(p[1] for p in lay["outline"]) + 20, 0.5)
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    z_s = float(lay["z"]["split"])
    for ax, half in zip(axes, ("motor_side", "cover"), strict=True):
        lower = half == "motor_side"
        other = "cover" if lower else "motor_side"
        img = np.ones(X.shape + (3,))

        def paint(mask, colour, alpha=1.0, img=img):
            c = np.array(matplotlib.colors.to_rgb(colour))
            img[mask] = (1 - alpha) * img[mask] + alpha * c

        def discs(pieces, grow=0.0):
            m = np.zeros(X.shape, bool)
            for p in pieces:
                m |= np.hypot(X - p["axis"][0], Y - p["axis"][1]) <= p["r"] + grow
            return m

        own = cupmod.pieces(all_rooms, z_s, half)
        own_in, own_out = discs(own), discs(own, wall)
        paint(own_in, COLOURS["shell"], 0.45)  # the end walls, seen from outside
        paint(own_out & ~own_in, COLOURS["shell"])  # the side walls
        paint(discs(cupmod.pieces(all_rooms, z_s, other), wall) & ~own_out, COLOURS["shell"], 0.75)  # closing the other half's rooms
        fl = lay["flange"]
        d_out = np.min([np.hypot(X - c["centre"][0], Y - c["centre"][1]) - c["radius"] for c in fl["outer"]], axis=0)
        d_in = np.min([np.hypot(X - c["centre"][0], Y - c["centre"][1]) - c["radius"] for c in fl["inner"]], axis=0)
        paint((d_out <= 0) & (d_in >= 0), COLOURS["land"])
        for b in lay["bearings"]:
            if (b["side"] == "-z") != lower:
                continue
            r = np.hypot(X - b["axis"][0], Y - b["axis"][1])
            if a.towers:
                paint((r <= float(b["boss_r"])) & (r >= b["D"] / 2 + wall), COLOURS["tower"], 0.6)
            paint((r <= b["D"] / 2 + 1.0) & (r >= b["D"] / 2 - 1.0), COLOURS["load"])
            ax.annotate(f"{b['shaft']}\nbearing Ø{b['D']:g}\n(load)", b["axis"], ha="center", va="center", fontsize=8)
        for c in lay["bolts"]:
            r = np.hypot(X - c[0], Y - c[1])
            paint((r <= s["bolt_boss"] / 2) & (r >= s["bolt_hole"] / 2), COLOURS["boss"])
        if lower:
            for m in lay["mounts"]:
                r = np.hypot(X - m["centre"][0], Y - m["centre"][1])
                paint((r <= s["mount_diameter"] / 2) & (r >= s["mount_hole"] / 2), COLOURS["lug"])
                ax.annotate(m["name"], (m["centre"][0], m["centre"][1] - 26), ha="center", fontsize=8)
        ax.imshow(img, origin="upper", extent=[xs[0], xs[-1], ys[-1], ys[0]], interpolation="nearest")
        ax.set_title(("the motor side" if lower else "the cover") + ", along its pull, from outside (the end walls pale)", fontsize=11)
        if not lower:
            ax.invert_xaxis()  # the cover seen from outside, as its face picture
        ax.set_aspect("equal")
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("y (mm)")
    fig.legend(handles=[Patch(color=COLOURS[k], label=NAMES[k]) for k in kinds], loc="lower center", ncol=2, fontsize=10)
    fig.subplots_adjust(bottom=0.17)
    plan = OUT / "protected_regions_plan.png"
    fig.savefig(plan, dpi=90, bbox_inches="tight")
    plt.close(fig)

    # the sheet: the 3D views from outside and from the split above, the plans below
    p_im = Image.open(plan).convert("RGB")
    rows = [r.resize((p_im.width, int(r.height * p_im.width / r.width)), Image.LANCZOS) for r in rows]
    sheet = Image.new("RGB", (p_im.width, sum(r.height for r in rows) + p_im.height), "white")
    y_ = 0
    for r in rows:
        sheet.paste(r, (0, y_))
        y_ += r.height
    sheet.paste(p_im, (0, y_))
    sheet.save(OUT / "protected_regions.png")
    print(OUT / "protected_regions.png")


if __name__ == "__main__":
    main()
