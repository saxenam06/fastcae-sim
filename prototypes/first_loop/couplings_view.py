"""PROTOTYPE (LOP-29) - the rigid couplings as FE holds them, on a design's own FE mesh (the field mesh, meshed as `fe.py`
meshes it: TetGen's TET4 from the drawn halves, made TET10), drawn as a pre-processor draws them: each coupled node joined by a
line to its centre node (a spider). The engineer, 13 October 23:22: "a pic with couplings at the bolt holes connected together
and at bearing bores and at mounts for the field mesh".
- each bearing seat: its surface nodes to the bearing's centre, where its load acts (blue);
- each bolt: both halves' hole nodes to one centre on the split, which ties the halves there and nowhere else (orange);
- each mount: its hole's nodes to its centre, held fixed (red).
The same node sets as `fe.py`'s kinematic couplings (`on_cylinder` on the mesh's skin). The whole housing, then close-ups of a
bolt, a seat and a mount. Writes data/first_loop/couplings_<design>.png.

With `--model` in place of a design: the optimiser's own model on the baseline's set-up (4 mm cubes), its coupled nodes over its
fixed cubes (`couplings_model.png`).

Run: .venv/Scripts/python.exe prototypes/first_loop/couplings_view.py <design> [size mm] | --model"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE.parents[1] / "data" / "first_loop"
COLOURS = {"seat": "#2b6cb0", "bolt": "#e07b00", "mount": "#c53030"}
SPOKES = 90  # lines drawn a coupling at most (every node is coupled; a sample of their spokes is drawn)


def groups_of(design: str, size: float):
    """Each half's mesh (surface, nodes) and the couplings' node sets with their centres, as `fe.judge` builds them."""
    import pyvista as pv

    import fe
    from fastcae_fe import quadratic

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    s = lay["settings"]
    z_s = float(lay["z"]["split"])
    t_f = float(s["flange_thickness"])
    halves = {}
    for half in ("motor_side", "cover"):
        nodes4, tets4 = fe.mesh_tetgen(OUT / rec["files"][half], size, ready=rec.get("fe_mesh") == "ready")
        tets4 = fe.oriented(nodes4, tets4)
        nodes, tets10 = quadratic(nodes4, tets4)
        cells = np.hstack([np.full((len(tets4), 1), 4), tets4]).ravel()
        grid = pv.UnstructuredGrid(cells, np.full(len(tets4), pv.CellType.TETRA, dtype=np.uint8), nodes4)
        halves[half] = {"nodes": nodes, "skin": fe.skin_nodes(tets10), "surface": grid.extract_surface()}
        fe.say(f"{half}: {len(tets10):,} TET10, {len(nodes):,} nodes")
    out = []
    for b in lay["bearings"]:
        half = "motor_side" if b["side"] == "-z" else "cover"
        h = halves[half]
        ids = fe.on_cylinder(h["nodes"], h["skin"], b["axis"], b["D"] / 2, *b["z"])
        out.append({"kind": "seat", "name": f"{b['shaft']} {b['side']} seat", "pts": h["nodes"][ids], "ref": np.array([*b["axis"], 0.5 * (b["z"][0] + b["z"][1])])})
    lo, hi = halves["motor_side"], halves["cover"]
    for i, c in enumerate(lay["bolts"]):
        a = fe.on_cylinder(lo["nodes"], lo["skin"], c, s["bolt_hole"] / 2, z_s - t_f, z_s)
        b_ = fe.on_cylinder(hi["nodes"], hi["skin"], c, s["bolt_hole"] / 2, z_s, z_s + t_f)
        if len(a) < 6 or len(b_) < 6:
            continue
        out.append({"kind": "bolt", "name": f"bolt {i + 1}", "pts": np.vstack([lo["nodes"][a], hi["nodes"][b_]]), "ref": np.array([c[0], c[1], z_s])})
    for m in lay["mounts"]:
        h = lo if m["z"][1] <= z_s else hi
        ids = fe.on_cylinder(h["nodes"], h["skin"], m["centre"], s["mount_hole"] / 2, *m["z"])
        out.append({"kind": "mount", "name": m["name"], "pts": h["nodes"][ids], "ref": np.array([*m["centre"], 0.5 * (m["z"][0] + m["z"][1])])})
    return halves, out


def model_groups():
    """The optimiser's model on the baseline's set-up (4 mm cubes; the interfaces and the 4 mm shell fixed; the rigid
    couplings): its fixed cubes' surface, and its coupled node sets (`topo.Voxels.coupling_groups`) with their centres."""
    import os

    import pyvista as pv

    os.environ["LOOP_MODEL_COUPLING"] = "kinematic"
    import topo
    from grade import REFERENCE
    from topo_free import build_free

    model = build_free(4.0, band=24.0, flange=True, mount_reach="disc", height_field=6.0, empty=True, protect=True, drawing_clear=True,
                       couplings="kinematic", shell_fixed=True)  # fmt: skip
    model["least_height_mm"] = 8.0
    model["cases"] = ("peak drive",)
    model["beds_mm"] = {"peak drive": REFERENCE["peak drive"] / 1000.0}
    vox = topo.Voxels(model)
    n, lo, h = np.asarray(model["n"]), np.asarray(model["lo"], float), float(model["h"])
    grid = pv.ImageData(dimensions=tuple(int(v) for v in n + 1), spacing=(h, h, h), origin=tuple(lo))
    grid.cell_data["kind"] = np.asarray(model["kind"]).reshape(tuple(n)).ravel(order="F")
    surface = grid.threshold([0.5, 1.5], scalars="kind").extract_surface()
    lay = model["info"]
    centre = {m["name"]: np.array([*m["centre"], 0.5 * (m["z"][0] + m["z"][1])]) for m in lay["mounts"]}
    out = []
    for g in vox.coupling_groups:
        kind = "seat" if g.get("seat") else ("mount" if g.get("fixed") else "bolt")
        ref = centre[g["name"]] if kind == "mount" else np.asarray(g["ref"], float)
        name = g["name"].replace("the ", "") if kind == "seat" else g["name"]
        out.append({"kind": kind, "name": name, "pts": vox.xyz[np.asarray(g["nodes"])], "ref": ref})
    return {"model": {"surface": surface}}, out


def spokes(pts: np.ndarray, ref: np.ndarray):
    import pyvista as pv

    rng = np.random.default_rng(0)
    take = pts if len(pts) <= SPOKES else pts[rng.choice(len(pts), SPOKES, replace=False)]
    p = np.vstack([ref[None, :], take])
    lines = np.hstack([[2, 0, i + 1] for i in range(len(take))])
    return pv.PolyData(p, lines=lines)


def render(halves, groups, focus=None, title="", size=(1100, 900)):
    import pyvista as pv

    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    for h in halves.values():
        pl.add_mesh(h["surface"], color="#c9ced6", opacity=0.22 if focus is None else 0.30, show_edges=focus is not None, edge_color="#9aa3ad",
                    line_width=0.3, smooth_shading=False)  # fmt: skip
    for g in groups:
        col = COLOURS[g["kind"]]
        pl.add_mesh(pv.PolyData(g["pts"]), color=col, point_size=5 if focus is None else 9, render_points_as_spheres=True)
        pl.add_mesh(spokes(g["pts"], g["ref"]), color=col, line_width=1.2 if focus is None else 2.0)
        centre = pv.Sphere(radius=3.0 if focus is None else 2.0, center=g["ref"])
        pl.add_mesh(centre, color="#111111" if g["kind"] != "mount" else COLOURS["mount"])
        if g["kind"] == "mount":  # held: a ground block under its centre
            pl.add_mesh(pv.Cube(center=g["ref"] - np.array([0, 0, 0.0]), x_length=7, y_length=7, z_length=7), color=COLOURS["mount"], opacity=0.55)
    pl.add_text(title, font_size=11, color="black")
    if focus is None:
        pl.camera_position = "iso"
        pl.camera.azimuth = 210
        pl.camera.elevation = 20
        pl.reset_camera()
        pl.camera.zoom(1.3)
    else:
        c = np.asarray(focus["ref"], float)
        pl.camera.focal_point = tuple(c)
        pl.camera.position = tuple(c + focus.get("dir", np.array([0.9, -1.0, 0.8])) * focus.get("dist", 90.0))
        pl.camera.up = (0.0, 0.0, 1.0)
    img = pl.screenshot(return_img=True)
    pl.close()
    return img


def main(design: str, size: float = 8.0) -> None:
    from PIL import Image, ImageDraw, ImageFont

    on_model = design == "--model"
    halves, groups = model_groups() if on_model else groups_of(design, size)
    counts = {k: [g for g in groups if g["kind"] == k] for k in ("seat", "bolt", "mount")}
    title = ("the optimiser's model (4 mm cubes, the baseline's set-up, its fixed cubes shown): the same rigid couplings" if on_model
             else f"{design}: the rigid couplings on FE's mesh (blue seats, orange bolts, red mounts held)")  # fmt: skip
    whole = render(halves, groups, None, title, (1500, 1100))
    bolt = counts["bolt"][0]
    seat = max(counts["seat"], key=lambda g: len(g["pts"]))
    mount = counts["mount"][0]
    close = [render(halves, [bolt], {"ref": bolt["ref"], "dist": 55.0}, f"{bolt['name']}: both halves' hole nodes to one centre on the split"),
             render(halves, [seat], {"ref": seat["ref"], "dist": 170.0, "dir": np.array([0.6, -1.0, 0.9])},
                    f"the {seat['name']}: its surface nodes to the bearing's centre, where the load acts"),  # fmt: skip
             render(halves, [mount], {"ref": mount["ref"], "dist": 80.0}, f"{mount['name']}: its hole's nodes to its centre, held")]
    ims = [Image.fromarray(whole)] + [Image.fromarray(c) for c in close]
    w = ims[0].width
    small = [im.resize((w // 3, int(im.height * (w // 3) / im.width)), Image.LANCZOS) for im in ims[1:]]
    sheet = Image.new("RGB", (w, ims[0].height + max(s_.height for s_ in small) + 70), "white")
    sheet.paste(ims[0], (0, 0))
    x = 0
    for s_ in small:
        sheet.paste(s_, (x, ims[0].height))
        x += s_.width
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    note = (f"{len(counts['seat'])} seats ({', '.join(str(len(g['pts'])) for g in counts['seat'])} nodes), {len(counts['bolt'])} bolts "
            f"({min(len(g['pts']) for g in counts['bolt'])}-{max(len(g['pts']) for g in counts['bolt'])} nodes, both halves), "
            f"{len(counts['mount'])} mounts ({', '.join(str(len(g['pts'])) for g in counts['mount'])} nodes)")  # fmt: skip
    draw.text((16, sheet.height - 52), note, fill="black", font=font)
    draw.text((16, sheet.height - 26), "every node of a set is coupled; a sample of each set's spokes is drawn", fill="black", font=font)
    path = OUT / ("couplings_model.png" if on_model else f"couplings_{design}.png")
    sheet.save(path)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 8.0)
