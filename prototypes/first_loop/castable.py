"""PROTOTYPE (LOP) - can the housing be cast as its contract says? The contract's manufacturing
rules measured on the built CAD of each half, no FE:

- **the pull direction** (hard, the engineer 02:12): every face must be formed by a mould part
  drawn along the half's pull direction or against it. A face turned one way along the pull that
  sees the part again that way is an undercut; a closed void is one by definition;
- **the least wall** (4 mm, D7): the thickness under each face, along its inward normal;
- reported, not judged (the contract holds no rule for them yet): the thick sections, where a
  sand casting feeds badly (the largest ball inside the metal, from a 1 mm distance map), and the
  generator's sharp inside corners (it makes no fillet).

Run: uv run python prototypes/first_loop/castable.py <stem> [<stem> ...]
Reads data/first_loop/<stem>.json and <stem>_<half>.brep and the contract; writes
data/first_loop/castable_<stem>.json and castable_<stem>.png.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np
import pyvista as pv
import vtk
from scipy.ndimage import distance_transform_edt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))

HALVES = {"motor_side": "motor-side", "cover": "cover"}  # this prototype's half -> the contract's part
PARALLEL = 0.02  # |n·d| below this (about 1.1°): a face along the pull, formed by either mould part
EPS = 0.02  # mm: a ray starts this far off its face
OFFSET = 0.3  # mm: a pull ray starts this far off its face along the face's exact normal, past the
#               tessellation's 0.2 mm chord: a ray along a face drafted 1.5° otherwise re-crossed
#               the face's own facets about 10 mm on (9 October 19:15)
HIT = 0.1  # mm: crossings nearer than this are the face itself
VOXEL = 1.0  # mm: the distance map's cell
THICK = 1.5  # a section is thick past this many walls (provisional, until the process profile holds a rule)
LUMP_MM = 16.0  # mm: the members' largest section outside the seats' bosses and the mounts' eyes (12 October 15:27, the lump gate)


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def contract_rules() -> tuple[dict[str, np.ndarray], float]:
    m = json.loads(CONTRACT.read_text(encoding="utf-8"))["manufacturing"]
    pulls = {p["part"]: np.asarray(p["direction"]["value"]["values"], float) for p in m["pull_directions"]}
    return pulls, float(m["min_wall"]["value"]["value"])


def triangles(shape: cq.Shape, names: dict[str, str]):
    """The half's faces as triangles, each with its face's role and the index of its face. The
    whole half is meshed first to an absolute 0.1 mm chord: CadQuery's own tessellation is
    relative to each face's size, about 1 mm on the large walls, and a ray along a drafted wall
    then clipped the fillets' facets at its foot (9 October 19:18)."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh

    BRepMesh_IncrementalMesh(shape.wrapped, 0.1, False, 0.25, True)
    points, tris, roles, owner = [], [], [], []
    base = 0
    for k, face in enumerate(shape.Faces()):
        verts, tri = face.tessellate(0.1, 0.25)
        if not tri:
            continue
        points.extend((v.x, v.y, v.z) for v in verts)
        tris.extend((a + base, b + base, c + base) for a, b, c in tri)
        roles.extend([names.get(str(k), "wall").split(":")[0]] * len(tri))
        owner.extend([k] * len(tri))
        base += len(verts)
    return np.asarray(points), np.asarray(tris), np.asarray(roles), np.asarray(owner)


def exact_normals(shape: cq.Shape, owner: np.ndarray, centre: np.ndarray, facet: np.ndarray) -> np.ndarray:
    """Each triangle's normal taken from its CAD face at the triangle's centre, turned to agree
    with the facet's. A facet on a face drafted 1.5° can lean the wrong way by more than the draft
    (9 October 19:05), and the pull test must read the face's own slope, not the facet's."""
    faces = shape.Faces()
    out = facet.copy()
    for k in np.unique(owner):
        face = faces[int(k)]
        idx = np.nonzero(owner == k)[0]
        if face.geomType() == "PLANE":
            n = face.normalAt()
            v = np.array([n.x, n.y, n.z])
            out[idx] = v if v @ facet[idx].sum(axis=0) >= 0 else -v
            continue
        for i in idx:
            n = face.normalAt(cq.Vector(*centre[i]))
            v = np.array([n.x, n.y, n.z])
            out[i] = v if v @ facet[i] >= 0 else -v
    return out


class Rays:
    """Segments against the half's surface (VTK's OBB tree)."""

    def __init__(self, points: np.ndarray, tris: np.ndarray, owner: np.ndarray | None = None):
        self.owner = owner
        self.poly = pv.PolyData(points, np.hstack([np.full((len(tris), 1), 3), tris]).ravel())
        self.tree = vtk.vtkOBBTree()
        self.tree.SetDataSet(self.poly)
        self.tree.BuildLocator()
        self.hits, self.ids = vtk.vtkPoints(), vtk.vtkIdList()

    def crossings(self, a, b) -> np.ndarray:
        self.hits.Reset()
        self.ids.Reset()
        self.tree.IntersectWithLine(list(a), list(b), self.hits, self.ids)
        n = self.hits.GetNumberOfPoints()
        return np.asarray([self.hits.GetPoint(i) for i in range(n)]).reshape(-1, 3)

    def first(self, a: np.ndarray, b: np.ndarray, skip_face: int | None = None) -> float | None:
        """The distance from a to the nearest crossing beyond HIT on the segment a-b; crossings of
        the CAD face `skip_face` are left out."""
        found = self.crossings(a, b)
        if not len(found):
            return None
        d = np.linalg.norm(found - a, axis=1)
        ok = d > HIT
        if skip_face is not None and self.owner is not None:
            ids = np.asarray([self.ids.GetId(i) for i in range(self.ids.GetNumberOfIds())], dtype=int)
            ok &= self.owner[ids] != skip_face
        d = d[ok]
        return float(d.min()) if len(d) else None


def inside_voxels(rays: Rays, lo: np.ndarray, hi: np.ndarray):
    """The metal on a VOXEL grid, by the parity of each column's crossings along z."""
    xs = np.arange(lo[0] + VOXEL / 2, hi[0], VOXEL) + 0.0137
    ys = np.arange(lo[1] + VOXEL / 2, hi[1], VOXEL) + 0.0071
    zs = np.arange(lo[2] + VOXEL / 2, hi[2], VOXEL)
    metal = np.zeros((len(xs), len(ys), len(zs)), bool)
    for ix, x in enumerate(xs):
        for iy, y in enumerate(ys):
            z = rays.crossings((x, y, lo[2] - 5.0), (x, y, hi[2] + 5.0))
            if len(z) < 2:
                continue
            z = np.sort(z[:, 2])
            z = z[np.concatenate(([True], np.diff(z) > 1e-6))]  # a crossing on a shared edge, once
            for a, b in zip(z[0::2], z[1::2], strict=False):
                metal[ix, iy, (zs > a) & (zs < b)] = True
    return metal, (xs, ys, zs)


MESH_EDGE = 4.0  # mm: a mesh-route half's triangles for the rays (`mesh_route.coarse`), finer than FE's 9


def judge_half(stem: str, half: str, info: dict, pull: np.ndarray, least: float) -> tuple[dict, pv.PolyData, np.ndarray]:
    files = {} if info.get("brep") else (info.get("files") or {})  # a B-rep drawing (ribbed_cad.py) is judged and shown as its CAD; FE reads its own mesh
    shape = None
    if half in files:  # drawn by the mesh route (11 October): its triangles, each its own face
        import mesh_route as mr

        tm = mr.load(OUT / files[half])
        points, tris = mr.coarse(tm, MESH_EDGE)
        roles, owner = np.full(len(tris), "wall"), np.arange(len(tris))
    else:
        shape = cq.Shape.importBrep(str(OUT / f"{stem}_{half}.brep"))
        points, tris, roles, owner = triangles(shape, info["faces"][half])
    p = points[tris]
    centre = p.mean(axis=1)
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    keep = area > 1e-9
    normal = np.zeros_like(cross)
    normal[keep] = cross[keep] / (2 * area[keep, None])
    volume = float((centre * normal * area[:, None]).sum() / 3)  # the divergence theorem: > 0 if outward
    if volume < 0:
        normal, volume = -normal, -volume
    if shape is not None:  # a mesh's facets are its faces: their normals are exact (its cylinders 360 facets a turn)
        normal[keep] = exact_normals(shape, owner[keep], centre[keep], normal[keep])
    rays = Rays(points, tris, owner)
    wall = float(info.get("settings", {}).get("wall", 6.0))

    along = normal @ pull
    under = np.zeros(len(tris), bool)
    # A face drafted along the pull (a cone, a cylinder or a plane round z, |n·d| under 0.2) cannot
    # hide itself from the pull; a ray along it that meets its own facets again meets the
    # tessellation's chords, not the part (9 October 19:15), and those crossings are left out.
    if shape is None:  # a mesh: each triangle is a face, which cannot hide itself
        kinds = np.full(len(tris), "MESH")
        self_safe = np.ones(len(tris), bool)
    else:
        kinds = np.array([f.geomType() for f in shape.Faces()])
        self_safe = np.isin(kinds, ("CONE", "CYLINDER", "PLANE"))
    # So can a free-form face (a field body's drafted side, a ruled B-spline) that nowhere turns
    # against the pull: its exact normals all on one side of the split plane. Left to the ray
    # alone, the cover's drafted terraces read 22.4 cm² of undercut on faces whose normals all
    # stood the full 1.5° up (10 October 01:22). (A face that spirals over itself while facing
    # one way would pass here; none is drawn.)
    for k in np.nonzero(~self_safe)[0]:
        mine = keep & (owner == k)
        if mine.any() and (along_of := normal[mine] @ pull).size and (along_of.min() >= -1e-3 or along_of.max() <= 1e-3):
            self_safe[k] = True
    for i in np.nonzero(keep & (np.abs(along) >= PARALLEL))[0]:
        s = np.sign(along[i]) * pull
        start = centre[i] + OFFSET * normal[i] + EPS * s
        skip = int(owner[i]) if (self_safe[owner[i]] and abs(along[i]) < 0.2) else None
        under[i] = rays.first(start, start + 3000.0 * s, skip) is not None

    thickness = np.full(len(tris), np.nan)
    for i in np.nonzero(keep)[0]:
        t = rays.first(centre[i] - EPS * normal[i], centre[i] - 400.0 * normal[i])
        if t is not None:
            thickness[i] = t + EPS
    thin = keep & (thickness < least - 0.1)

    voids = []
    if shape is None:  # a mesh's closed voids: its pieces that face inward
        voids = [-float(piece.volume) for piece in tm.split(only_watertight=False) if piece.volume < 0]
    else:
        for solid in shape.Solids():
            shells = sorted((abs(cq.Solid.makeSolid(sh).Volume()) for sh in solid.Shells()), reverse=True)
            voids.extend(shells[1:])

    lo, hi = points.min(axis=0) - 2.0, points.max(axis=0) + 2.0
    metal, (xs, ys, zs) = inside_voxels(rays, lo, hi)
    ball = 2.0 * distance_transform_edt(metal) * VOXEL  # the diameter of the ball centred in each cell
    heavy = ball > THICK * wall
    ix, iy, iz = np.nonzero(heavy)
    spots = np.column_stack([xs[ix], ys[iy], zs[iz]]) if len(ix) else np.zeros((0, 3))

    total = float(area[keep].sum())
    by_role = {}
    for role in np.unique(roles[under]):
        by_role[str(role)] = round(float(area[under & (roles == role)].sum()) / 100.0, 1)  # cm²
    # where the undercut is: the B-rep faces holding most of it, with their kind and extent
    faces = []
    for f in np.unique(owner[under]):
        sel = under & (owner == f)
        c = centre[sel]
        faces.append({
            "face": int(f),
            "kind": str(kinds[f]),
            "role": str(roles[sel][0]),
            "cm2": round(float(area[sel].sum()) / 100.0, 2),
            "share_of_face": round(float(area[sel].sum() / max(area[owner == f].sum(), 1e-9)), 2),
            "lo": [round(float(v), 1) for v in c.min(axis=0)],
            "hi": [round(float(v), 1) for v in c.max(axis=0)],
            "normal": [round(float(v), 2) for v in normal[sel].mean(axis=0)],
        })
    faces.sort(key=lambda d: -d["cm2"])
    # the members' largest section (LOP-25; the engineer, 12 October 15:23-15:27, "how to prevent such lumps"): the ball
    # inside the metal, the contract's own thick parts left out (each seat's boss, the trade's 1.25·D + 10 across, and
    # each mount's eye); a lump where members cross is what it catches
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    own = np.zeros(gx.shape, bool)
    for b in lay["bearings"]:
        own |= np.hypot(gx - b["axis"][0], gy - b["axis"][1]) <= 0.625 * float(b["D"]) + 5.0
    for m_ in lay["mounts"]:
        own |= np.hypot(gx - m_["centre"][0], gy - m_["centre"][1]) <= 0.5 * float(lay["settings"]["mount_diameter"]) + 4.0
    members_ball = np.where(own[:, :, None], 0.0, ball)
    result = {
        "half": half,
        "pull": pull.tolist(),
        "largest_section_members_mm": round(float(members_ball.max()), 1),
        "lump_rule": "PASS" if float(members_ball.max()) <= LUMP_MM else "FAIL",
        "area_cm2": round(total / 100.0, 1),
        "volume_cm3_mesh": round(volume / 1000.0, 1),
        "volume_cm3_voxels": round(float(metal.sum()) * VOXEL**3 / 1000.0, 1),
        "undercut_cm2": round(float(area[under].sum()) / 100.0, 1),
        "undercut_share": round(float(area[under].sum()) / total, 4),
        "undercut_by_role_cm2": by_role,
        "undercut_faces": faces[:12],
        "closed_voids": len(voids),
        "closed_void_cm3": round(sum(voids) / 1000.0, 1),
        "thinner_than_least_wall_cm2": round(float(area[thin].sum()) / 100.0, 1),
        "least_thickness_mm": round(float(np.nanmin(thickness[keep])), 2),
        "largest_section_mm": round(float(ball.max()), 1),
        "thick_cm3": round(float(heavy.sum()) * VOXEL**3 / 1000.0, 1),
        "thick_line_mm": THICK * wall,
        "pull_rule": "PASS" if not under.any() and not voids else "FAIL",
        "least_wall_rule": "PASS" if not thin.any() else "FAIL",
    }
    colours = np.tile(np.array([200, 202, 205], np.uint8), (len(tris), 1))
    colours[thin] = (40, 110, 220)
    colours[under] = (220, 40, 40)
    rays.poly.cell_data["rgb"] = colours
    return result, rays.poly, spots


def main(stems: list[str]) -> None:
    pulls, least = contract_rules()
    for stem in stems:
        info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
        info.setdefault("settings", {})
        halves, meshes, spots = [], {}, {}
        for half, part in HALVES.items():
            say(f"{stem} {half}: measuring")
            result, mesh, hot = judge_half(stem, half, info, pulls[part], least)
            halves.append(result)
            meshes[half], spots[half] = mesh, hot
            say(f"{stem} {half}: {json.dumps(result)}")
        (OUT / f"castable_{stem}.json").write_text(json.dumps({"stem": stem, "halves": halves}, indent=1), encoding="utf-8")

        pv.OFF_SCREEN = True
        plotter = pv.Plotter(shape=(1, 2), window_size=(1800, 850), off_screen=True)
        views = (((0.55, -0.45, 0.75), "the cover's side"), ((-0.55, -0.45, -0.75), "the motor's side"))
        for col, (view, title) in enumerate(views):
            plotter.subplot(0, col)
            for half in HALVES:
                plotter.add_mesh(meshes[half], scalars="rgb", rgb=True)
                if len(spots[half]):
                    pts = spots[half][:: max(1, len(spots[half]) // 6000)]
                    plotter.add_points(pts, color=(1.0, 0.6, 0.1), point_size=4, render_points_as_spheres=True)
            plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
            words = [f"{title}: red = undercut along the pull, blue = under the 4 mm least wall,"]
            words.append(f"orange = metal in a section over {THICK * float(info['settings'].get('wall', 6.0)):.0f} mm")
            if col == 0:
                for r in halves:
                    words.append(f"{r['half']}: pull {r['pull_rule']} ({100 * r['undercut_share']:.1f} % of the area undercut, "
                                 f"{r['closed_voids']} closed voids), least wall {r['least_wall_rule']}, "
                                 f"largest section {r['largest_section_mm']:.0f} mm")
            plotter.add_text("\n".join(words), font_size=9)
        plotter.screenshot(str(OUT / f"castable_{stem}.png"))
        plotter.close()
        say(f"{stem}: castable_{stem}.png")


if __name__ == "__main__":
    main(sys.argv[1:])
