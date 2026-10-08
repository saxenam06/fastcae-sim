"""PROTOTYPE - not product code, not the judge.

Plan Part C, Task 11 (join and export): the field's marching-cubes mesh (Task 10) and the core's
tessellation (Task 9) are united with manifold3d; then the machined features are cut again at
their finished sizes (+0.02 mm, so the cutters' exact cylinders and planes are the faces that
remain): the three bores, the two shaft passages, the bolt-boss holes, the motor flange's face,
spigot and holes, the mount pad's face and holes, and the split face itself. The result must be
a valid manifold (watertight).

Every triangle keeps where it came from (manifold3d's run original ids): field, core, or a
machining cutter. Cutter triangles are the machined faces; the rest are cast faces.

Reported checks on the joined housing (not enforced), with field.py's functions:
- mass at 2.66 g/cm3 (card from Kim et al. 2024 via the spec; prototype), bounding box;
- intrusion into the gears' keep-outs, the bearings and the shafts (volumes, should be 0);
- volume outside the installation space (A3);
- closed except at the split face and the two shaft passages (voxel flood fill);
- enclosed voids (mesh shells of negative volume, and a voxel flood fill from outside);
- wall-thickness map (local thickness from the distance transform, 1.0 mm voxels);
- draft map: share of the cast area at less than 1 deg to the pull direction (+z, A7).
Outputs: housing.stl, housing.glb, housing_maps.npz, join.json.
"""

from __future__ import annotations

import json
import math
import sys
import time

import field as FD
import manifold3d as m3
import numpy as np
import params as P
import trimesh
from layout import load_layout, peak_memory_mb

OP_ADD = m3.OpType.Add

ORIGIN_NAMES = [
    "field",
    "core",
    "bore",
    "shaft passage",
    "bolt-boss hole",
    "flange face",
    "flange spigot",
    "flange hole",
    "split face",
    "pad face",
    "pad hole",
]
MACHINED_FROM = 2  # origin index >= 2: a machining cutter, i.e. a machined face


def to_manifold(V, F, what):
    mesh = m3.Mesh(
        vert_properties=np.ascontiguousarray(V, dtype=np.float32),
        tri_verts=np.ascontiguousarray(F, dtype=np.uint32),
    )
    m = m3.Manifold(mesh)
    if m.status() != m3.Error.NoError:
        raise RuntimeError(f"{what}: not a manifold mesh ({m.status()})")
    return m


def zcyl(cx, cy, z0, z1, r, n):
    return m3.Manifold.cylinder(z1 - z0, r, r, n).translate((cx, cy, z0))


def segs(r):
    return int(min(720, max(96, math.ceil(2 * math.pi * r / 0.4))))


def cutters(lay, bosses, flange_holes):
    """Machining cutters at the finished size + CUT_OVERSIZE in every direction (radius and
    depth), so no cutter face is coplanar with one of the core's own exact faces; coplanar
    floors left zero-area slivers and pinched vertices in the first join."""
    e = P.CUT_OVERSIZE
    groups = {k: [] for k in ORIGIN_NAMES[MACHINED_FROM:]}
    for s in lay.back:
        groups["bore"].append(zcyl(s.cx, s.cy, s.z0 - 4.0, s.z1 + e, s.D / 2 + e, segs(s.D / 2)))
        if s.through:
            groups["shaft passage"].append(
                zcyl(
                    s.cx,
                    s.cy,
                    s.z1 - 0.5,
                    s.ring_top + 60.0,
                    s.r_shoulder_hole + e,
                    segs(s.r_shoulder_hole),
                )
            )
    for bx, by in bosses:
        groups["bolt-boss hole"].append(
            zcyl(bx, by, -2.0, P.BOSS_HEIGHT + 0.3, P.BOSS_HOLE / 2 + e, segs(P.BOSS_HOLE / 2))
        )
    cx, cy = lay.flange_c
    zf = lay.z_flange
    groups["flange face"].append(zcyl(cx, cy, zf - e, zf + 20.0, lay.flange_r_out + 8.0, 360))
    groups["flange spigot"].append(
        zcyl(
            cx,
            cy,
            zf - lay.flange_spigot_depth - e,
            zf + 1.0,
            lay.flange_r_spigot + e,
            segs(lay.flange_r_spigot),
        )
    )
    for hx, hy in flange_holes:
        groups["flange hole"].append(
            zcyl(
                hx,
                hy,
                zf - P.FLANGE_HOLE_DEPTH - e,
                zf + 1.0,
                lay.flange_hole_r + e,
                segs(lay.flange_hole_r),
            )
        )
    big = 2000.0
    groups["split face"].append(
        m3.Manifold.cube((big, big, 100.0)).translate((-big / 2 + 100.0, -big / 2, -100.0 + e))
    )
    x_face = lay.pad_face_x
    z0, z1 = lay.pad_z
    groups["pad face"].append(
        m3.Manifold.cube((60.0, 80.0, (z1 - z0) + 40.0)).translate((x_face - e, -40.0, z0 - 20.0))
    )
    for hz in lay.pad_hole_z:
        c = m3.Manifold.cylinder(
            P.PAD_HOLE_DEPTH + 5.0 + e, lay.pad_hole_r + e, lay.pad_hole_r + e, segs(lay.pad_hole_r)
        ).rotate((0.0, 90.0, 0.0))
        groups["pad hole"].append(c.translate((x_face - P.PAD_HOLE_DEPTH - e, 0.0, hz)))
    return groups


def keepout_solids(lay):
    gears = [zcyl(g.cx, g.cy, *g.z_keepout, g.r_keepout, 360) for g in lay.gears]
    bearings = [zcyl(s.cx, s.cy, s.z0, s.z1, s.D / 2, segs(s.D / 2)) for s in lay.seats]
    shafts = []
    for shaft, (cx, cy) in lay.axes.items():
        a, b = lay.cover_by[shaft], lay.back_by[shaft]
        r = (max(a.d, b.d) + P.SHAFT_DIAMETER_EXTRA) / 2
        shafts.append(zcyl(cx, cy, 0.5 * (a.z0 + a.z1), 0.5 * (b.z0 + b.z1), r, segs(r)))
    return (
        m3.Manifold.batch_boolean(gears, OP_ADD),
        m3.Manifold.batch_boolean(bearings, OP_ADD),
        m3.Manifold.batch_boolean(shafts, OP_ADD),
    )


def triangle_origins(mesh, id_to_origin):
    n_tri = len(mesh.tri_verts)
    ri = np.asarray(mesh.run_index, dtype=np.int64)
    if ri[-1] == 3 * n_tri:
        ri = ri // 3
    ids = np.asarray(mesh.run_original_id, dtype=np.int64)
    lab = np.full(n_tri, -1, dtype=np.int16)
    for k, oid in enumerate(ids):
        lab[ri[k] : ri[k + 1]] = id_to_origin.get(int(oid), -1)
    return lab


def closed_check(occ, lo, pitch, lay):
    """Plug the split opening and the two shaft passages; then the gear space must not reach
    the outside air."""
    from scipy import ndimage

    occ2 = occ.copy()
    nz_plug = int(math.ceil((1.5 - lo[2]) / pitch))
    occ2[:, :, : max(nz_plug, 0)] = True
    xs = lo[0] + (np.arange(occ.shape[0]) + 0.5) * pitch
    ys = lo[1] + (np.arange(occ.shape[1]) + 0.5) * pitch
    zs = lo[2] + (np.arange(occ.shape[2]) + 0.5) * pitch
    for s in lay.back:
        if not s.through:
            continue
        rho = np.hypot(xs[:, None] - s.cx, ys[None, :] - s.cy)
        disc = rho <= s.r_shoulder_hole + 1.5
        zsel = np.nonzero((zs >= s.z1 - 1.0) & (zs <= s.ring_top + 1.0))[0]
        occ2[:, :, zsel] |= disc[:, :, None]
    lab, _ = ndimage.label(~occ2)
    border = set(
        np.unique(
            np.r_[
                lab[0].ravel(),
                lab[-1].ravel(),
                lab[:, 0].ravel(),
                lab[:, -1].ravel(),
                lab[:, :, -1].ravel(),
            ]
        ).tolist()
    )
    g4 = next(g for g in lay.gears if g.name == "g4")
    seeds = [
        (g4.cx + 0.6 * g4.r_tip, g4.cy, 0.5 * (g4.z0 + g4.z1)),
        (lay.axes["input"][0], lay.axes["input"][1], 20.0),
    ]
    reached = []
    for sx, sy, sz in seeds:
        i, j, k = (int((sx - lo[0]) / pitch), int((sy - lo[1]) / pitch), int((sz - lo[2]) / pitch))
        reached.append(bool(lab[i, j, k] in border) if lab[i, j, k] else None)
    return {
        "gear_space_reaches_outside_with_split_and_passages_plugged": reached,
        "closed_except_split_face_and_passages": not any(r for r in reached if r),
    }


def main():
    t0 = time.time()
    lay = load_layout()
    outline = json.loads((P.OUT / "outline.json").read_text(encoding="utf-8"))
    core_rep = json.loads((P.OUT / "core.json").read_text(encoding="utf-8"))
    fm = np.load(P.OUT / "field_mesh.npz")
    field_m = to_manifold(fm["vertices"], fm["faces"], "field mesh").as_original()
    core_tm = trimesh.load(P.OUT / "core.stl", process=True)
    if not core_tm.is_watertight:
        raise RuntimeError("core.stl is not watertight")
    core_m = to_manifold(core_tm.vertices, core_tm.faces, "core mesh").as_original()

    id_to_origin = {field_m.original_id(): 0, core_m.original_id(): 1}
    groups = cutters(lay, outline["bosses"], core_rep["motor_flange"]["holes"])
    cut_list = []
    for gi, name in enumerate(ORIGIN_NAMES[MACHINED_FROM:], start=MACHINED_FROM):
        for c in groups[name]:
            c = c.as_original()
            id_to_origin[c.original_id()] = gi
            cut_list.append(c)
    union = m3.Manifold.batch_boolean([field_m, core_m], OP_ADD)
    cut_all = m3.Manifold.batch_boolean(cut_list, OP_ADD)
    housing = union - cut_all
    if housing.status() != m3.Error.NoError:
        raise RuntimeError(f"boolean failed: {housing.status()}")
    t_bool = time.time() - t0

    mesh = housing.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    F = np.asarray(mesh.tri_verts).astype(np.int64)
    origin = triangle_origins(mesh, id_to_origin)
    # A file reader merges vertices by position; check the mesh as it will be read. Two
    # distinct vertices at one position (a pinch) would turn into non-manifold edges.
    tm = trimesh.Trimesh(V, F, process=True)
    repair = {
        "duplicate_positions_in_boolean_output": int(len(V) - len(tm.vertices)),
        "zero_area_faces_removed": 0,
    }
    if not (tm.is_watertight and len(tm.split(only_watertight=False)) == 1):
        keep = tm.area_faces > 1e-9  # zero-area slivers left by near-coincident faces
        repair["zero_area_faces_removed"] = int((~keep).sum())
        tm.update_faces(keep)
        tm.remove_unreferenced_vertices()
        origin = origin[keep]
        if not (tm.is_watertight and len(tm.split(only_watertight=False)) == 1):
            raise RuntimeError(f"the housing mesh is not one watertight body: {repair}")
    V, F = tm.vertices.copy(), tm.faces.copy()
    bodies = housing.decompose()
    vol = housing.volume()
    mass = vol * P.DENSITY_KG_PER_MM3

    # ---- keep-outs, installation space
    k_gears, k_bear, k_shaft = keepout_solids(lay)
    intr = {
        "gears_keepout_mm3": (housing ^ k_gears).volume(),
        "bearings_mm3": (housing ^ k_bear).volume(),
        "shafts_mm3": (housing ^ k_shaft).volume(),
    }
    lo_s, hi_s = lay.space_lo, lay.space_hi
    box = m3.Manifold.cube(tuple(hi_s - lo_s)).translate(tuple(lo_s))
    outside_space = vol - (housing ^ box).volume()

    # ---- voids from the mesh: shells with negative volume are enclosed cavities
    parts = tm.split(only_watertight=False)
    neg_shells = [p for p in parts if p.is_watertight and p.volume < 0]

    # ---- voxel checks: closed shell, voids, local thickness
    pitch = P.CHECK_VOXEL
    jit = np.array([0.137, 0.291, 0.0]) * pitch
    lo = V.min(0) - 3 * pitch + jit
    shape = tuple(int(math.ceil((V.max(0)[i] + 3 * pitch - lo[i]) / pitch)) for i in range(3))
    occ = FD.voxelize_mesh(V, F, lo, pitch, shape)
    vox_vol = occ.sum() * pitch**3
    voids = FD.enclosed_voids(occ, pitch)
    closed = closed_check(occ, lo, pitch, lay)
    t_lt = time.time()
    lt = FD.local_thickness(occ, pitch)
    t_lt = time.time() - t_lt
    vn = tm.vertex_normals
    v_thick = FD.sample_inside(lt, lo, pitch, V, vn)
    del lt, occ

    tri_area = tm.area_faces
    tri_thick = v_thick[F].mean(axis=1)

    def wpct(x, w, q):
        o = np.argsort(x)
        c = np.cumsum(w[o])
        return float(x[o][np.searchsorted(c, q * c[-1])])

    thickness = {
        "voxel_mm": pitch,
        "min_mm": round(float(tri_thick.min()), 2),
        "p1_mm": round(wpct(tri_thick, tri_area, 0.01), 2),
        "p5_mm": round(wpct(tri_thick, tri_area, 0.05), 2),
        "median_mm": round(wpct(tri_thick, tri_area, 0.50), 2),
        "p95_mm": round(wpct(tri_thick, tri_area, 0.95), 2),
        "max_mm": round(float(tri_thick.max()), 2),
        "area_share_below_min_wall": round(
            float(tri_area[tri_thick < P.MIN_WALL].sum() / tri_area.sum()), 4
        ),
        "min_wall_mm": P.MIN_WALL,
        "note": (
            "local thickness (largest inscribed ball) on a 1.0 mm voxel copy, sampled "
            "just inside each vertex; about +-1 mm from the voxel size"
        ),
    }

    # ---- draft map: field triangles use the field's smooth normal, core triangles their
    # facet normal; machined faces (cutters) are not cast faces and are left out.
    fz = np.load(P.OUT / "field.npz")
    cen = tm.triangles_center
    normals = tm.face_normals.copy()
    is_field = origin == 0
    if is_field.any():
        # the field before the split-face cut, so faces just above z = 0 get their true normal
        normals[is_field] = FD.field_gradient_at(
            fz["S_normals"], fz["lo"], float(fz["h"]), cen[is_field]
        )
    ang = FD.draft_angles_deg(normals)
    cast = (origin >= 0) & (origin < MACHINED_FROM)
    low = cast & (ang < P.DRAFT_CHECK_DEG)
    draft = {
        "threshold_deg": P.DRAFT_CHECK_DEG,
        "cast_area_mm2": round(float(tri_area[cast].sum()), 1),
        "machined_area_mm2": round(float(tri_area[origin >= MACHINED_FROM].sum()), 1),
        "share_of_cast_area_below_threshold": round(
            float(tri_area[low].sum() / tri_area[cast].sum()), 5
        ),
        "below_threshold_by_origin_mm2": {
            ORIGIN_NAMES[k]: round(float(tri_area[low & (origin == k)].sum()), 1) for k in (0, 1)
        },
        "unlabelled_triangles": int((origin < 0).sum()),
        "note": "angle between the face and +z; machined faces left out",
    }

    # ---- exports
    stl = P.OUT / "housing.stl"
    glb = P.OUT / "housing.glb"
    tm.export(stl)
    g_tm = tm.copy()
    g_tm.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[205, 205, 200, 255], metallicFactor=0.2, roughnessFactor=0.6
        )
    )
    g_tm.export(glb)
    np.savez_compressed(
        P.OUT / "housing_maps.npz",
        vertices=V,
        faces=F,
        origin=origin,
        vertex_thickness=v_thick,
        face_draft_deg=ang,
        face_cast=cast,
    )
    # read the exported files back as any other tool would
    reread = {}
    for path in (stl, glb):
        rd = trimesh.load(path, force="mesh")
        reread[path.name] = {
            "watertight": bool(rd.is_watertight),
            "components": len(rd.split(only_watertight=False)),
            "volume_mm3": round(float(rd.volume), 1),
        }
    if not all(r["watertight"] and r["components"] == 1 for r in reread.values()):
        raise RuntimeError(f"an exported file does not read back as one watertight body: {reread}")

    bb_lo, bb_hi = V.min(0), V.max(0)
    report = {
        "PROTOTYPE": "plan Part C, Task 11 (join); not product code, not the judge",
        "mass_kg": round(mass, 4),
        "mass_provenance": P.DENSITY_LABEL,
        "volume_mm3": round(vol, 1),
        "volume_check_voxels_mm3": round(float(vox_vol), 1),
        "bounding_box_mm": {
            "lo": [round(float(v), 2) for v in bb_lo],
            "hi": [round(float(v), 2) for v in bb_hi],
            "size": [round(float(v), 2) for v in bb_hi - bb_lo],
        },
        "triangles": int(len(F)),
        "manifold_status": str(housing.status()),
        "watertight": bool(tm.is_watertight),
        "winding_consistent": bool(tm.is_winding_consistent),
        "bodies": len(bodies),
        "components_as_read": len(tm.split(only_watertight=False)),
        "genus": housing.genus(),
        "mesh_repair": repair,
        "exported_files_read_back": reread,
        "keepout_intrusion": {k: round(v, 3) for k, v in intr.items()},
        "outside_installation_space_mm3": round(outside_space, 1),
        "closed_shell": closed,
        "enclosed_voids": {
            "mesh_shells_with_negative_volume": len(neg_shells),
            "voxel_flood_fill": voids,
        },
        "thickness": thickness,
        "draft": draft,
        "triangle_origins": {
            ORIGIN_NAMES[k]: int((origin == k).sum()) for k in range(len(ORIGIN_NAMES))
        },
        "time_s": {
            "boolean": round(t_bool, 1),
            "local_thickness": round(t_lt, 1),
            "total": round(time.time() - t0, 1),
        },
        "peak_memory_mb": peak_memory_mb(),
        "files": {"stl": str(stl), "glb": str(glb)},
    }
    (P.OUT / "join.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(
        f"join: mass {mass:.3f} kg, {len(F)} triangles, watertight {tm.is_watertight}, "
        f"bodies {len(bodies)}, genus {housing.genus()}"
    )
    print(
        f"  keep-out intrusion {intr}; outside the installation space {outside_space / 1e3:.2f} cm3"
    )
    print(f"  closed {closed}; voids mesh {len(neg_shells)} / voxel {voids['count']}")
    print(f"  thickness {thickness}")
    print(
        f"  draft share below {P.DRAFT_CHECK_DEG} deg: "
        f"{draft['share_of_cast_area_below_threshold']:.4f} "
        f"{draft['below_threshold_by_origin_mm2']}"
    )
    print(
        f"  housing.stl, housing.glb, housing_maps.npz, join.json -> {P.OUT}; "
        f"{report['time_s']} s; peak {report['peak_memory_mb']:.0f} MB"
    )
    return report


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
