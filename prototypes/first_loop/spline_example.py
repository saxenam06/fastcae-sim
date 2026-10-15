"""PROTOTYPE (LOP-30) - one bracket and one rib made by hand through the spline space's own control points, drawn by the
normal drawing route (`outcome_cad.py ... skin mesh`, `spline_members`) and pictured in 3D with the control points in
place (the engineer, 14 October 19:36: "show more in 3d laying this on a shell surface ... an example how a bracket or
member gets created through the same control points and representation").

- The bracket: two legs from the motor side's side wall to mount-1's lug. Its outline: the outline field's control points
  near the legs set positive (fitted to 7 mm less the distance to the legs: legs about 14 mm wide), all others -8 mm. Its
  depth: the height field of the members standing on the split, from 40 mm below the split at the wall to 64 mm at the
  lug (the lug sits 33-63 mm below the split).
- The rib: across the end wall between two bearings' bosses, 10 mm wide, standing 16 mm out of the end wall (the height
  field of the members standing on the end walls).
No optimisation and no FE: the representation alone, as the optimiser would set it.

Run: .venv/Scripts/python.exe prototypes/first_loop/spline_example.py   (writes data/first_loop/spline_example.png)"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from scipy.sparse.linalg import lsqr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
OUT = ROOT / "data" / "first_loop"
# (the engineer, 14 October 20:34: "Start with A") LOOP_EXAMPLE_SECTION="<round mm>:<fillet mm>" draws the same fields with
# the section rule (`topo.section_drop`, the drawing's fillets), as `spline_example_sec`
SECTION = os.environ.get("LOOP_EXAMPLE_SECTION", "")
STEM, DESIGN = ("spline_example_sec_run", "spline_example_sec") if SECTION else ("spline_example_run", "spline_example")


def seg_dist(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = b - a
    t = np.clip(((p - a) @ d) / float(d @ d), 0.0, 1.0)
    return np.hypot(*(p - (a + t[:, None] * d)).T), t


def main() -> Path:
    import topo
    from topo_free import build_free

    spec = {"phi_mm": 6.0, "h_mm": 12.0, "gap_mm": 8.0}
    if SECTION:
        spec["round_mm"], spec["fillet_mm"] = (float(v) for v in SECTION.split(":"))
    model = build_free(4.0, band=24.0, flange=True, mount_reach="disc", height_field=4.0, empty=True, protect=True, flange_whole=True,
                       drawing_clear=True, couplings="kinematic", shell_fixed=True, towers=False)  # fmt: skip
    model["least_height_mm"], model["least_width_mm"], model["spline"] = 8.0, 8.0, spec
    vox = topo.Voxels(model)
    sp_, hh = vox.spline, vox.height
    lo, h = np.asarray(model["lo"], float), 4.0
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    z_split = float(layout["z"]["split"])
    m1 = next(m for m in layout["mounts"] if m["name"] == "mount-1")
    c_m = np.asarray(m1["centre"], float)[:2]
    cxy = lo[:2] + h * (hh["pts"] + 0.5)
    motor = sp_["half"] == 0
    # the shell's outer face in plan: the motor side's rooms' circles and the 4 mm wall (as the drawing reads the cup); the
    # columns past a mount's room count as standing on a wall too, so they are no guide to the shell
    import outcome_cad as oc

    c_spec, _ = oc.load_and_validate(oc.convex.CONTRACT)
    gaps = c_spec.requirement.shaft_layout
    rooms = oc.cupmod.pieces(oc.cupmod.rooms(oc.complete_chain(c_spec), oc.value_in(gaps.min_radial_clearance, "mm"),
                                             oc.value_in(gaps.min_axial_clearance, "mm")), z_split, "motor_side")  # fmt: skip
    wall_mm = float(layout["settings"]["wall"])

    def shell_gap(p: np.ndarray) -> float:
        return min(float(np.hypot(*(p - np.asarray(pc["axis"][:2], float))) - float(pc["r"]) - wall_mm) for pc in rooms)

    # the legs: from the lug towards the nearest room, 25 degrees either side, to the shell's outer face
    near = np.asarray(min(rooms, key=lambda pc: np.hypot(*(np.asarray(pc["axis"][:2], float) - c_m)))["axis"][:2], float)
    ang0 = np.arctan2(*(near - c_m)[::-1])

    def hit(da: float):
        u = np.array([np.cos(ang0 + da), np.sin(ang0 + da)])
        for r in np.arange(10.0, 260.0, 1.0):
            p = c_m + r * u
            if shell_gap(p) <= 1.0:
                return p
        return None

    ends = []
    for sign in (-1.0, 1.0):  # a leg each side of the nearest wall, as far round as 25 degrees and no further than it lands
        for deg in (25, 20, 15, 30, 10, 35):
            p = hit(sign * np.radians(deg))
            if p is not None:
                ends.append(p)
                break
    if len(ends) < 2:
        raise SystemExit(f"the bracket's legs found {len(ends)} wall points round mount-1")
    print("the legs from", np.round(c_m, 1), "to", [np.round(e, 1).tolist() for e in ends])
    # the rib: between the motor side's first two bearings' bosses (their edges), on the end wall
    brs = [b for b in layout["bearings"] if b["side"] == "-z"][:2]
    ca, cb = (np.asarray(b["axis"], float)[:2] for b in brs)
    ua = (cb - ca) / np.linalg.norm(cb - ca)
    ra, rb = (float(b.get("boss_r") or 30.0) for b in brs)
    r_a, r_b = ca + ua * ra, cb - ua * rb
    # the outline field's targets at the points: the legs on the split's members, the rib on the end walls'
    q = sp_["q"]
    sub = lo[:2] + (h / q) * (sp_["sub_ij"] + 0.5)
    on_split_s = sp_["on_split"][sp_["sub_col"]]
    motor_s = sp_["sub_half"] == 0
    d_leg = np.minimum(*(seg_dist(sub, c_m, e)[0] for e in ends))
    d_rib = seg_dist(sub, r_a, r_b)[0]
    target = np.full(len(sub), -8.0)
    leg = motor_s & on_split_s
    rib = motor_s & ~on_split_s
    target[leg] = np.clip(7.0 - d_leg[leg], -8.0, 8.0)
    target[rib] = np.clip(5.0 - d_rib[rib], -8.0, 8.0)
    c_phi = np.clip(lsqr(sp_["B_phi"], target + 8.0, damp=1e-3, atol=1e-10, btol=1e-10, iter_lim=50000)[0] - 8.0, -8.0, 8.0)
    # the heights (voxels from each column's base): the legs deepening towards the lug, the rib 16 mm
    s_leg = np.max(np.column_stack([1.0 - seg_dist(cxy, c_m, e)[1] for e in ends]), axis=1)  # 0 at the wall, 1 at the lug
    t_want = np.where(sp_["on_split"], 10.0 + 6.0 * s_leg, 4.0)
    span = hh["L"] - sp_["least"]
    x_h = np.clip(lsqr(sp_["B_h"], np.clip((t_want - sp_["least"]) / span, 0, 1), damp=1e-3, atol=1e-10, btol=1e-10, iter_lim=50000)[0], 0, 1)
    x = np.r_[0.5 * (c_phi / sp_["range"] + 1.0), x_h]
    beta = 16.0
    dens = vox.physical(x, beta)
    cols = vox.spline_columns(x, beta)
    # a run of its own: the field and the record (lw8's set-up), then the normal drawing
    src = json.loads((OUT / "baseline2_lw8.json").read_text(encoding="utf-8"))["outcome_of"]
    z0 = np.load(OUT / f"{src}.npz")
    extra = {"height_min": z0["height_min"]} if "height_min" in z0.files else {}
    extra.update({f"spl_{k}": v for k, v in cols.items()})
    np.savez_compressed(OUT / f"{STEM}.npz", phys=dens[vox.free_e], x=x, free_e=vox.free_e, elem=vox.elem, frozen=vox.frozen, ijk=vox.ijk,
                        lo=lo, n=np.asarray(model["n"]), h=h, k_split=int(model["k_split"]), beta=beta, **extra)  # fmt: skip
    rec = json.loads((OUT / f"{src}.json").read_text(encoding="utf-8"))
    rec.update({"spline": spec, "objective": "an example made by hand", "binary": None, "history": []})
    (OUT / f"{STEM}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    env = dict(os.environ, LOOP_EXACT_WALLS="1")
    subprocess.run([sys.executable, str(HERE / "outcome_cad.py"), STEM, DESIGN, "skin", "mesh"], env=env, check=True,
                   stdout=open(OUT / f"build_{DESIGN}.log", "w"), stderr=subprocess.STDOUT)  # fmt: skip
    body = pv.read(OUT / f"{DESIGN}_motor_side.ply")
    # the control points in place: the outline's at the base each region's members stand on, coloured by value; the
    # heights' (the split's members) as spheres at the depth they set, on stalks from the split
    fo = next(fd for fd in sp_["fields"] if fd["kind"] == "outline" and fd["half"] == 0)
    fs = next(fd for fd in sp_["fields"] if fd["kind"] == "height" and fd["half"] == 0 and fd["family"] == "split")

    def knots(fd):
        ia, ja = np.unravel_index(fd["kept"], tuple(fd["shape"]))
        return np.column_stack([fd["origin"][0] + fd["spacing"] * (ia - 1), fd["origin"][1] + fd["spacing"] * (ja - 1)])

    ko = knots(fo)
    vo = c_phi[fo["offset"] : fo["offset"] + len(fo["kept"])]
    ks_ = knots(fs)
    vs = sp_["least"] + span * x_h[fs["offset"] : fs["offset"] + len(fs["kept"])]
    # the bracket's neighbourhood: its control points and the body cropped round it
    pts_b = np.vstack([c_m, *ends])
    bx0, by0 = pts_b.min(axis=0) - 28.0
    bx1, by1 = pts_b.max(axis=0) + 28.0
    in_b = (ko[:, 0] > bx0) & (ko[:, 0] < bx1) & (ko[:, 1] > by0) & (ko[:, 1] < by1)
    p_out = np.column_stack([ko[in_b], np.full(int(in_b.sum()), z_split + 1.0)])
    d_h = np.minimum(*(seg_dist(ks_, c_m, e)[0] for e in ends))
    on_leg = d_h < 9.0  # the height field's control points the legs read
    p_h = np.column_stack([ks_[on_leg], z_split - h * vs[on_leg]])
    stalks = pv.PolyData()
    for pt in p_h:
        stalks = stalks.merge(pv.Line((pt[0], pt[1], z_split), tuple(pt)))
    split_plane = pv.Plane(center=(0.5 * (bx0 + bx1), 0.5 * (by0 + by1), z_split + 0.5), direction=(0, 0, 1), i_size=bx1 - bx0,
                           j_size=by1 - by0)  # fmt: skip
    crop_b = body.clip_box(bounds=(bx0, bx1, by0, by1, -90.0, z_split + 1.0), invert=False)
    # the rib's: its control points on the end wall's face under it
    rib_mid = 0.5 * (r_a + r_b)
    near_rib = np.flatnonzero(motor & ~sp_["on_split"])
    k_face = int(np.median(sp_["base"][near_rib[np.argsort(np.hypot(*(cxy[near_rib] - rib_mid).T))[:20]]]))
    z_face = lo[2] + h * (k_face + 1)  # the end wall's outside (the motor side's columns run downward from it)
    rx0, ry0 = np.minimum(r_a, r_b) - 30.0
    rx1, ry1 = np.maximum(r_a, r_b) + 30.0
    in_r = (ko[:, 0] > rx0) & (ko[:, 0] < rx1) & (ko[:, 1] > ry0) & (ko[:, 1] < ry1)
    p_rib = np.column_stack([ko[in_r], np.full(int(in_r.sum()), z_face - 25.0)])  # drawn below the wall, so the rib hides none
    crop_r = body.clip_box(bounds=(rx0, rx1, ry0, ry1, z_face - 40.0, z_face + 30.0), invert=False)
    pl = pv.Plotter(shape=(2, 2), window_size=(2000, 1600), off_screen=True)
    look = dict(color="#cfcfcf", smooth_shading=True, specular=0.3, ambient=0.3)
    bc = np.r_[0.5 * (bx0 + bx1), 0.5 * (by0 + by1), z_split - 35.0]
    above = [tuple(bc + np.array([-150.0, -190.0, 260.0])), tuple(bc), (0, 0, 1)]  # from the split's side, looking down

    pl.subplot(0, 0)
    pl.add_text("1. The bracket's control points. On the split (blue plane): the outline's, every 6 mm; red ones\n   say metal, blue "
                "air. Hanging below: the height field's, each at the depth it gives the leg there", font_size=10)  # fmt: skip
    pl.add_mesh(crop_b, **look)
    pl.add_mesh(split_plane, color="#5dade2", opacity=0.25)
    pl.add_points(p_out, scalars=vo[in_b], cmap="coolwarm", clim=[-8, 8], render_points_as_spheres=True, point_size=13,
                  scalar_bar_args={"title": "outline control value, mm (red metal, blue air)"})  # fmt: skip
    pl.add_mesh(stalks, color="#e67e22", line_width=2)
    pl.add_points(p_h, color="#e67e22", render_points_as_spheres=True, point_size=16)
    pl.camera_position = above
    pl.subplot(0, 1)
    pl.add_text("2. The bracket they make, alone: two legs from the side wall to mount-1's lug,\n   deepening from 40 mm below the split at "
                "the wall to 64 mm at the lug", font_size=10)  # fmt: skip
    pl.add_mesh(crop_b, **look)
    pl.camera_position = above
    pl.subplot(1, 0)
    pl.add_text("3. The rib across the end wall, seen from outside: the outline's control points\n   (shown below the wall), red where "
                "the rib is; it stands 16 mm out of the wall", font_size=10)  # fmt: skip
    pl.add_mesh(crop_r, **look)
    pl.add_points(p_rib, scalars=vo[in_r], cmap="coolwarm", clim=[-8, 8], render_points_as_spheres=True, point_size=12, show_scalar_bar=False)
    rc = np.r_[rib_mid, z_face - 10.0]
    pl.camera_position = [tuple(rc + np.array([-60.0, -150.0, -190.0])), tuple(rc), (0, 0, -1)]
    pl.subplot(1, 1)
    pl.add_text("4. The whole motor side from outside: the 4 mm shell and fixed parts, with only\n   these two members added "
                "(boxes: the bracket, the rib)", font_size=10)  # fmt: skip
    pl.add_mesh(body, **look)
    pl.add_mesh(pv.Box(bounds=(bx0, bx1, by0, by1, -90.0, z_split + 1.0)), style="wireframe", color="#e67e22", line_width=3)
    pl.add_mesh(pv.Box(bounds=(rx0, rx1, ry0, ry1, z_face - 40.0, z_face + 30.0)), style="wireframe", color="#c0392b", line_width=3)
    cen = np.asarray(body.center)
    pl.camera_position = [tuple(cen + np.array([-260.0, -420.0, -380.0])), tuple(cen), (0, 0, -1)]
    out = OUT / f"{DESIGN}.png"
    pl.screenshot(str(out))
    print(out)
    return out


if __name__ == "__main__":
    main()
