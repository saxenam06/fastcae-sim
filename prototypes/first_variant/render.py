"""PROTOTYPE - not product code, not the judge.

Plan Part C, Task 11 (pictures): PNGs of the joined housing, rendered off screen with pyvista
(and the layout with matplotlib), into data/prototypes/first_variant/:
  1 iso.png         the whole main-housing half, isometric from the back;
  2 split_face.png  looking along +z into the split face (the gears' space shown as glass), and
                    the back wall seen from outside (the members);
  3 section.png     a section folded through the three seat axes (input, intermediate, output);
  4 thickness.png   the wall-thickness map on the surface (red: below the 4 mm minimum);
  5 draft.png       the draft map (red: cast faces under 1 deg to the pull direction +z);
  6 layout.png      the gears' pitch circles, the three axes and the 165 mm offset;
  7 route.png       how the route builds it: CadQuery core, field shell and members, joined.
"""

from __future__ import annotations

import json
import math
import sys

import manifold3d as m3
import matplotlib
import numpy as np
import params as P
import pyvista as pv
from layout import load_layout
from matplotlib.colors import ListedColormap

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

pv.OFF_SCREEN = True
GREY = "#d6d6d2"
CORE_BLUE = "#7f9fc8"
MACHINED = "#e08a2e"
RED = "#d62728"
CUT = "#c8694f"
STAGE_COL = {"stage1": "#2a9d8f", "stage2": "#e9a23b"}
SIZE = (1600, 1200)
WIDE = (2200, 1100)
BACK_ISO = (0.55, -0.95, 0.85)
FRONT_ISO = (0.45, -0.75, -0.95)


def polydata(V, F):
    faces = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), F.astype(np.int64)]).ravel()
    return pv.PolyData(np.asarray(V, dtype=np.float64), faces)


def plotter(shape=(1, 1), size=SIZE):
    p = pv.Plotter(
        off_screen=True, window_size=size, shape=shape, lighting="three lights", border=False
    )
    p.set_background("white")
    return p


def add_part(p, mesh, color=GREY, **kw):
    style = dict(
        smooth_shading=True,
        split_sharp_edges=True,
        ambient=0.22,
        diffuse=0.8,
        specular=0.12,
        specular_power=15,
        show_edges=False,
    )
    style.update(kw)
    if "scalars" in style:
        p.add_mesh(mesh, **style)
    else:
        p.add_mesh(mesh, color=color, **style)


def add_housing(p, V, F, origin, color=GREY, point_data=None, cell_data=None, **kw):
    """Field faces smooth-shaded; core and machined faces (exact, finely tessellated, often
    long thin fans on flat faces) flat-shaded, so no normal is smeared across a flat face."""
    pd = polydata(V, F)
    for k, v in (point_data or {}).items():
        pd.point_data[k] = v
    for k, v in (cell_data or {}).items():
        pd.cell_data[k] = v
    origin = np.asarray(origin)
    first = True
    for sel, smooth in ((origin == 0, True), (origin != 0, False)):
        idx = np.nonzero(sel)[0]
        if idx.size == 0:
            continue
        part = pd.extract_cells(idx).extract_surface(algorithm="dataset_surface")
        args = dict(kw)
        if not first:
            args["show_scalar_bar"] = False
            args.pop("scalar_bar_args", None)
        add_part(p, part, color=color, smooth_shading=smooth, **args)
        first = False


def frame(p, vec, up=(0, 0, 1), zoom=1.15):
    p.view_vector(vec, viewup=up)
    p.reset_camera()
    p.camera.zoom(zoom)


def title(p, text, sub=None):
    p.add_text(text, position="upper_left", font_size=13, color="black")
    if sub:
        p.add_text(sub, position="lower_left", font_size=11, color="#333333")


def load():
    m = np.load(P.OUT / "housing_maps.npz")
    join = json.loads((P.OUT / "join.json").read_text(encoding="utf-8"))
    return m, join


# ------------------------------------------------------------------ 1 isometric


def pic_iso(m, join, lay):
    p = plotter()
    add_housing(p, m["vertices"], m["faces"], m["origin"])
    frame(p, BACK_ISO, zoom=1.2)
    bb = join["bounding_box_mm"]["size"]
    title(
        p,
        "Main housing half, isometric from the back (PROTOTYPE)",
        f"mass {join['mass_kg']:.2f} kg at 2.66 g/cm3 (card from Kim et al. 2024 via the "
        f"spec; prototype)\nbounding box {bb[0]:.0f} x {bb[1]:.0f} x {bb[2]:.0f} mm, "
        f"{join['triangles']} triangles, one watertight body: {join['watertight']}\n"
        "motor-flange ring (left), seat rings, bridges, ribs, webs to the mount pad (right)",
    )
    p.add_axes(line_width=2, labels_off=False)
    path = P.OUT / "iso.png"
    p.screenshot(path)
    p.close()
    return path


# ------------------------------------------------------------------ 2 split face


def gear_glass(lay):
    out = []
    for g in lay.gears:
        b = g.z1 - g.z0
        cyl = pv.Cylinder(
            center=(g.cx, g.cy, 0.5 * (g.z0 + g.z1)),
            direction=(0, 0, 1),
            radius=g.r_tip,
            height=b,
            resolution=120,
        )
        out.append((g, cyl))
    return out


def pic_split_face(m, join, lay):
    p = plotter(shape=(1, 2), size=WIDE)
    p.subplot(0, 0)
    add_housing(p, m["vertices"], m["faces"], m["origin"])
    stage = {"g1": "stage1", "g2": "stage1", "g3": "stage2", "g4": "stage2"}
    for g, cyl in gear_glass(lay):
        col = STAGE_COL[stage[g.name]]
        p.add_mesh(cyl, color=col, opacity=0.16, smooth_shading=True)
        ring = pv.Circle(radius=g.r_tip, resolution=180).translate((g.cx, g.cy, g.z0 - 0.5))
        p.add_mesh(
            ring.extract_feature_edges(
                boundary_edges=True, feature_edges=False, manifold_edges=False
            ),
            color=col,
            line_width=3,
        )
    pts = np.array([[*lay.axes[k], -2.0] for k in ("input", "intermediate", "output")])
    p.add_point_labels(
        pts,
        ["input", "intermediate", "output"],
        font_size=16,
        point_size=10,
        point_color="black",
        text_color="black",
        shape_opacity=0.55,
        always_visible=True,
    )
    frame(p, (0, 0, -1), up=(0, 1, 0), zoom=1.25)
    title(
        p,
        "Into the split face, looking along +z (from the cover side; x runs left)",
        "glass and outlines: the gears' tip cylinders (teal stage 1, amber stage 2)\n"
        "grey: the cavity, its back wall with the three seat bores,\n"
        "the sealing lip and the 14 bolt bosses",
    )
    p.add_axes(line_width=2)
    p.subplot(0, 1)
    add_housing(p, m["vertices"], m["faces"], m["origin"])
    frame(p, (0, 0, 1), up=(0, 1, 0), zoom=1.25)
    title(
        p,
        "The back wall from outside, looking along -z",
        "seat rings, motor-flange ring with gussets, bridges input-intermediate-output,\n"
        "webs from each ring to the mount pad (+x end), radial ribs from each ring",
    )
    p.add_axes(line_width=2)
    path = P.OUT / "split_face.png"
    p.screenshot(path)
    p.close()
    return path


# ------------------------------------------------------------------ 3 section


def halfspace(o_xy, n_xy):
    """A big box filling {p : n . (p - o) > 0}."""
    big = 3000.0
    box = m3.Manifold.cube((big, big, 600.0)).translate((0.0, -big / 2, -300.0))
    ang = math.degrees(math.atan2(n_xy[1], n_xy[0]))
    return box.rotate((0.0, 0.0, ang)).translate((o_xy[0], o_xy[1], 0.0))


def mesh_of(man):
    mg = man.to_mesh()
    V = np.asarray(mg.vert_properties)[:, :3]
    F = np.asarray(mg.tri_verts)
    return mg, V, F


def pic_section(m, join, lay):
    H = m3.Manifold(
        m3.Mesh(
            vert_properties=np.asarray(m["vertices"], dtype=np.float32),
            tri_verts=np.asarray(m["faces"], dtype=np.uint32),
        )
    ).as_original()
    a, b, c = (np.array(lay.axes[k]) for k in ("input", "intermediate", "output"))
    e1, e2 = (b - a) / np.linalg.norm(b - a), (c - b) / np.linalg.norm(c - b)
    # right-hand normals of the two legs; the wedge on their side (below the fold) is removed,
    # so the cut faces are seen from -y with x running to the right, as in layout.png
    n1, n2 = np.array([e1[1], -e1[0]]), np.array([e2[1], -e2[0]])
    cut1, cut2 = halfspace(a, n1).as_original(), halfspace(b, n2).as_original()
    removed = cut1 ^ cut2
    cut_ids = {cut1.original_id(), cut2.original_id()}

    p = plotter()
    hs = H - removed
    mg, V, F = mesh_of(hs)
    ri = np.asarray(mg.run_index, dtype=np.int64)
    if ri[-1] == 3 * len(F):
        ri = ri // 3
    is_cut = np.zeros(len(F), dtype=bool)
    for k, oid in enumerate(np.asarray(mg.run_original_id)):
        if int(oid) in cut_ids:
            is_cut[ri[k] : ri[k + 1]] = True
    src = np.asarray(m["origin"])
    face_id = np.asarray(mg.face_id, dtype=np.int64)
    org = np.where(is_cut, -1, src[np.clip(face_id, 0, len(src) - 1)])
    keep = np.nonzero(~is_cut)[0]
    add_housing(p, V, F[keep], org[keep])
    add_part(p, polydata(V, F[is_cut]).clean(), color=CUT, smooth_shading=False)

    def show(man, color, opacity=1.0):
        _, v, f = mesh_of(man - removed)
        if len(f):
            p.add_mesh(
                polydata(v, f), color=color, opacity=opacity, smooth_shading=True, ambient=0.25
            )

    for s in lay.back:
        ring = m3.Manifold.cylinder(
            s.B, s.D / 2 - 0.05, s.D / 2 - 0.05, 180
        ) - m3.Manifold.cylinder(s.B + 2, s.d / 2, s.d / 2, 120).translate((0, 0, -1))
        show(ring.translate((s.cx, s.cy, s.z0)), "#c9a35a")
    for g in lay.gears:
        bore = lay.back_by[g.shaft].d / 2
        gear = m3.Manifold.cylinder(g.z1 - g.z0, g.r_tip, g.r_tip, 240) - m3.Manifold.cylinder(
            g.z1 - g.z0 + 2, bore, bore, 90
        ).translate((0, 0, -1))
        show(gear.translate((g.cx, g.cy, g.z0)), "#8db8e0", opacity=0.5)
    p.add_legend(
        [
            ["housing, cast faces", "#8f8f8a"],
            ["section faces", CUT],
            ["back-wall bearings", "#b38b3c"],
            ["gears (tip cylinders)", "#5a8fc4"],
        ],
        bcolor="white",
        border=True,
        size=(0.26, 0.16),
        loc="upper right",
        face="rectangle",
    )
    vec = n1 + n2
    vec = vec / np.linalg.norm(vec)
    frame(p, (vec[0], vec[1], 0.5), zoom=1.3)
    title(
        p,
        "Section folded through the three seat axes (input - intermediate - output)",
        "the wedge between the two planes through the axes, on the -y side, is removed;\n"
        "z up: back wall with the three seats on top, split face at the bottom. Cover side "
        "(z < 0) not built.",
    )
    path = P.OUT / "section.png"
    p.screenshot(path)
    p.close()
    return path


# ------------------------------------------------------------------ 4 thickness


def pic_thickness(m, join):
    th = join["thickness"]
    p = plotter(shape=(1, 2), size=WIDE)
    for i, (vec, label) in enumerate([(BACK_ISO, "from the back"), (FRONT_ISO, "into the cavity")]):
        p.subplot(0, i)
        add_housing(
            p,
            m["vertices"],
            m["faces"],
            m["origin"],
            point_data={"thickness": np.asarray(m["vertex_thickness"], np.float32)},
            scalars="thickness",
            cmap="viridis",
            clim=[4.0, 16.0],
            below_color=RED,
            above_color="#fde725",
            scalar_bar_args={
                "title": "thickness [mm]\nred: < 4 mm\n",
                "vertical": True,
                "position_x": 0.89,
                "position_y": 0.2,
                "width": 0.05,
                "height": 0.6,
                "n_labels": 7,
                "fmt": "%.0f",
                "color": "black",
                "title_font_size": 16,
                "label_font_size": 14,
            }
            if i == 0
            else None,
            show_scalar_bar=(i == 0),
        )
        frame(p, vec, zoom=1.0 if i == 0 else 1.2)
        if i == 0:
            title(
                p,
                "Wall-thickness map (reported, not enforced)",
                f"local thickness on a {th['voxel_mm']} mm voxel copy (+-1 mm): min "
                f"{th['min_mm']}, p5 {th['p5_mm']}, median {th['median_mm']} mm; "
                f"{100 * th['area_share_below_min_wall']:.1f} % of the area below 4 mm",
            )
        else:
            title(p, label)
    path = P.OUT / "thickness.png"
    p.screenshot(path)
    p.close()
    return path


# ------------------------------------------------------------------ 5 draft


def pic_draft(m, join):
    origin = np.asarray(m["origin"])
    cast = np.asarray(m["face_cast"])
    ang = np.asarray(m["face_draft_deg"])
    cat = np.where(~cast, 2, np.where(ang < P.DRAFT_CHECK_DEG, 1, 0)).astype(np.int32)
    cat[origin < 0] = 0
    cmap = ListedColormap([GREY, RED, "#4a78b5"])
    d = join["draft"]
    p = plotter(shape=(1, 2), size=WIDE)
    for i, (vec, label) in enumerate([(BACK_ISO, "from the back"), (FRONT_ISO, "into the cavity")]):
        p.subplot(0, i)
        add_housing(
            p,
            m["vertices"],
            m["faces"],
            origin,
            cell_data={"cat": cat},
            scalars="cat",
            cmap=cmap,
            clim=[-0.5, 2.5],
            show_scalar_bar=False,
        )
        frame(p, vec, zoom=1.2)
        if i == 0:
            title(
                p,
                "Draft map, pull direction +z (assumption A7)",
                f"red: cast faces under {P.DRAFT_CHECK_DEG:.0f} deg to the pull direction, "
                f"{100 * d['share_of_cast_area_below_threshold']:.2f} % of the cast area; "
                "blue: machined faces (bores, holes, spigot, faces), left out",
            )
            for j, (txt, col) in enumerate(
                (
                    ("grey: cast faces, drafted 1 deg or more", "#6f6f6a"),
                    ("red: cast faces under 1 deg", RED),
                    ("blue: machined faces (not judged)", "#4a78b5"),
                )
            ):
                p.add_text(
                    txt, position=(0.01, 0.9 - 0.04 * j), viewport=True, font_size=12, color=col
                )
        else:
            title(p, label)
    path = P.OUT / "draft.png"
    p.screenshot(path)
    p.close()
    return path


# ------------------------------------------------------------------ 6 layout


def pic_layout(lay):
    d = lay.derived
    outline = json.loads((P.OUT / "outline.json").read_text(encoding="utf-8"))
    core = json.loads((P.OUT / "core.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(13, 9.75), dpi=130)
    cur = outline["curves"]
    for name, col, lw in (
        ("cavity_inner", "#999999", 1.0),
        ("wall_outer", "#555555", 1.4),
        ("lip_outer", "#999999", 0.8),
    ):
        xy = np.array(cur[name])
        ax.plot(xy[:, 0], xy[:, 1], color=col, lw=lw, zorder=1)
    xi, xo = np.array(cur["cavity_inner"]), np.array(cur["wall_outer"])
    ax.fill(xo[:, 0], xo[:, 1], color="#eeeeea", zorder=0)
    ax.fill(xi[:, 0], xi[:, 1], color="white", zorder=0)
    stage = {"g1": "stage1", "g2": "stage1", "g3": "stage2", "g4": "stage2"}
    for gr, g in zip(d["gears"], lay.gears, strict=True):
        col = STAGE_COL[stage[g.name]]
        ax.add_patch(plt.Circle((g.cx, g.cy), g.r_pitch, fill=False, color=col, lw=2.0))
        ax.add_patch(plt.Circle((g.cx, g.cy), g.r_tip, fill=False, color=col, lw=0.9, ls="--"))
        ax.add_patch(
            plt.Circle((g.cx, g.cy), g.r_keepout, fill=False, color="#bbbbbb", lw=0.7, ls=":")
        )
        ang, txy = {
            "g1": (215, (-88, -118)),
            "g2": (55, (150, 200)),
            "g3": (20, (128, 128)),
            "g4": (290, (238, -158)),
        }[g.name]
        px = g.cx + g.r_pitch * math.cos(math.radians(ang))
        py = g.cy + g.r_pitch * math.sin(math.radians(ang))
        ax.annotate(
            f"{g.name}: z {gr['teeth']['value']}, mn {gr['normal_module']['value']}, "
            f"d {gr['pitch_diameter']['value']:.1f}, b {gr['face_width']['value']:.1f}"
            f"\nz-station {gr['axial_station']['value'][0]:.1f}-"
            f"{gr['axial_station']['value'][1]:.1f} mm",
            (px, py),
            xytext=txy,
            fontsize=8,
            color=col,
            ha="center",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1},
            arrowprops={"arrowstyle": "-", "color": col, "lw": 0.7},
        )
    for s in lay.back:
        ax.add_patch(plt.Circle((s.cx, s.cy), s.D / 2, fill=False, color="black", lw=0.8))
    for bx, by in outline["bosses"]:
        ax.add_patch(plt.Circle((bx, by), P.BOSS_DIAMETER / 2, fill=False, color="#555555", lw=0.8))
        ax.add_patch(plt.Circle((bx, by), P.BOSS_HOLE / 2, fill=False, color="#555555", lw=0.6))
    fc = lay.flange_c
    for r, ls in ((lay.flange_r_spigot, "-"), (lay.flange_r_bolt, "-."), (lay.flange_r_out, "-")):
        ax.add_patch(plt.Circle(fc, r, fill=False, color="#7f5fa8", lw=0.8, ls=ls))
    for hx, hy in core["motor_flange"]["holes"]:
        ax.add_patch(plt.Circle((hx, hy), lay.flange_hole_r, fill=False, color="#7f5fa8", lw=0.6))
    ax.text(
        fc[0] - 100,
        fc[1] + 60,
        "motor flange:\nspigot d110,\n6 holes on d130,\nOD 150",
        fontsize=8,
        color="#7f5fa8",
    )
    ax.add_patch(
        plt.Rectangle(
            (lay.pad_face_x - lay.pad_thickness, -lay.pad_half_y),
            lay.pad_thickness,
            2 * lay.pad_half_y,
            color="#4a78b5",
            alpha=0.6,
        )
    )
    ax.text(lay.pad_face_x + 4, 26, "mount pad\n(A4)", fontsize=8, color="#4a78b5")
    names = {"input": "input", "intermediate": "intermediate", "output": "output"}
    for k, (x, y) in lay.axes.items():
        ax.plot(x, y, "k+", ms=14, mew=1.6)
        ax.text(x + 4, y + 4, f"{names[k]}\n({x:.1f}, {y:.1f})", fontsize=9, weight="bold")
    a, b, c = (np.array(lay.axes[k]) for k in ("input", "intermediate", "output"))
    for p0, p1, txt in (
        (a, b, f"a1 = {np.linalg.norm(b - a):.2f} mm"),
        (b, c, f"a2 = {np.linalg.norm(c - b):.2f} mm"),
    ):
        ax.plot(*zip(p0, p1, strict=True), color="#444444", lw=0.8, ls="--")
        u = (p1 - p0) / np.linalg.norm(p1 - p0)
        mid = 0.5 * (p0 + p1) + 7.0 * np.array([-u[1], u[0]])
        ax.text(
            mid[0],
            mid[1],
            txt,
            fontsize=9,
            color="#444444",
            ha="center",
            va="center",
            rotation=math.degrees(math.atan2(u[1], u[0])),
            rotation_mode="anchor",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1},
        )
    yd = -165.0
    ax.annotate("", (a[0], yd), (c[0], yd), arrowprops={"arrowstyle": "<->", "lw": 1.2})
    for x in (a[0], c[0]):
        ax.plot([x, x], [yd - 4, -10], color="black", lw=0.5)
    ax.text(
        0.5 * (a[0] + c[0]),
        yd + 3,
        "165 mm input-to-output offset (published: Hofstetter 2018 Table 2)",
        ha="center",
        fontsize=10,
    )
    rc = d["ratio_check"]["total_ratio"]["value"]
    ax.text(
        0.01,
        0.99,
        "PROTOTYPE layout (plan Part C, Task 8) - rule-of-thumb sizing, not a rating\n"
        f"ratio 25/65 x 23/82 = {rc:.4f}  (9.32 +/- 1 %, Table 2)   |   helix 20 deg, "
        "alpha_n 20 deg, x = 0\n"
        "solid: pitch circles; dashed: tip circles; dotted: keep-outs (tip + 5 mm); "
        "grey band: the drafted wall at the split face",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#999999"},
    )
    ax.set_aspect("equal")
    ax.set_xlim(lay.space_lo[0] - 10, lay.space_hi[0] + 10)
    ax.set_ylim(-190, lay.space_hi[1] + 75)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.grid(color="#eeeeee", lw=0.5)
    fig.tight_layout()
    path = P.OUT / "layout.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ------------------------------------------------------------------ 7 route


def pic_route(m):
    core = pv.read(str(P.OUT / "core.stl"))
    field = pv.read(str(P.OUT / "field.stl"))
    origin = np.asarray(m["origin"])
    o = np.where(origin >= 2, 2, np.clip(origin, 0, 1)).astype(np.int32)
    p = plotter(shape=(1, 3), size=(2400, 900))
    panels = [
        (
            core,
            CORE_BLUE,
            "1  the machined core in CadQuery (exact B-rep)",
            "seat rings, motor flange, mount pad, bolt bosses",
        ),
        (
            field,
            GREY,
            "2  the shell and members in field space",
            "drafted cup, sealing lip, bridges, webs, ribs (1.5 mm voxels), blended into\n"
            "0.3 mm-undersize copies of the core's features",
        ),
        (
            None,
            None,
            "3  joined (manifold3d) and machined again",
            "grey from the field, blue from the core, orange machined",
        ),
    ]
    for i, (msh, col, t1, t2) in enumerate(panels):
        p.subplot(0, i)
        if msh is None:
            add_housing(
                p,
                m["vertices"],
                m["faces"],
                origin,
                cell_data={"o": o},
                scalars="o",
                cmap=ListedColormap([GREY, CORE_BLUE, MACHINED]),
                clim=[-0.5, 2.5],
                show_scalar_bar=False,
            )
        else:
            add_part(p, msh, color=col, smooth_shading=(msh is field))
        frame(p, BACK_ISO, zoom=1.25)
        title(p, t1, t2)
    path = P.OUT / "route.png"
    p.screenshot(path)
    p.close()
    return path


def main():
    lay = load_layout()
    m, join = load()
    paths = [
        pic_iso(m, join, lay),
        pic_split_face(m, join, lay),
        pic_section(m, join, lay),
        pic_thickness(m, join),
        pic_draft(m, join),
        pic_layout(lay),
        pic_route(m),
    ]
    for p_ in paths:
        print(f"picture -> {p_}")
    return [str(p_) for p_ in paths]


if __name__ == "__main__":
    which = sys.argv[1:] or None
    if which:
        lay = load_layout()
        m, join = load()
        fns = {
            "iso": lambda: pic_iso(m, join, lay),
            "split": lambda: pic_split_face(m, join, lay),
            "section": lambda: pic_section(m, join, lay),
            "thickness": lambda: pic_thickness(m, join),
            "draft": lambda: pic_draft(m, join),
            "layout": lambda: pic_layout(lay),
            "route": lambda: pic_route(m),
        }
        for w in which:
            print(f"picture -> {fns[w]()}")
    else:
        main()
