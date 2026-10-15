"""Can the drawn housing be cast as its contract says? (moved from
`prototypes/first_loop/castable.py`: `contract_rules`, `Rays`, `inside_voxels`, `judge_half` and
`main` on the mesh route; LOP-33). The contract's manufacturing rules measured on each half's mesh,
coarsened to `MESH_EDGE` triangles, each triangle its own face:
- the pull direction (hard): a face turned one way along the pull that sees the part again that way
  is an undercut; a closed void is one by definition;
- the least wall: the thickness under each face, along its inward normal;
- reported, not judged: the thick sections (the largest ball inside the metal, from a 1 mm distance
  map) and the members' largest section outside the seats' bosses and the mounts' eyes (the lump
  rule).
Writes `castable_<design>.json` and its picture `castable_<design>.png`.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from zenryx.domains.gearbox.housing import mesh as mr
from zenryx.domains.gearbox.housing import say

HALVES = {"motor_side": "motor-side", "cover": "cover"}  # the drawing's half -> the contract's part
PARALLEL = 0.02  # |n·d| below this (about 1.1°): a face along the pull, formed by either mould part
EPS = 0.02  # mm: a ray starts this far off its face
OFFSET = 0.3  # mm: a pull ray starts this far off its face along its normal
HIT = 0.1  # mm: crossings nearer than this are the face itself
VOXEL = 1.0  # mm: the distance map's cell
THICK = 1.5  # a section is thick past this many walls (reported)
LUMP_MM = 16.0  # mm: the members' largest section outside the seats' bosses and the mounts' eyes
MESH_EDGE = 4.0  # mm: a half's triangles for the rays


def contract_rules(contract: Path) -> tuple[dict[str, np.ndarray], float]:
    m = json.loads(contract.read_text(encoding="utf-8"))["manufacturing"]
    pulls = {
        p["part"]: np.asarray(p["direction"]["value"]["values"], float)
        for p in m["pull_directions"]
    }
    return pulls, float(m["min_wall"]["value"]["value"])


class Rays:
    """Segments against the half's surface (VTK's OBB tree)."""

    def __init__(self, points: np.ndarray, tris: np.ndarray, owner: np.ndarray):
        import pyvista as pv
        import vtk

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
        the face `skip_face` are left out."""
        found = self.crossings(a, b)
        if not len(found):
            return None
        d = np.linalg.norm(found - a, axis=1)
        ok = d > HIT
        if skip_face is not None:
            ids = np.asarray(
                [self.ids.GetId(i) for i in range(self.ids.GetNumberOfIds())], dtype=int
            )
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


def judge_half(half: str, info: dict, layout: dict, out: Path, pull: np.ndarray, least: float):
    from scipy.ndimage import distance_transform_edt

    tm = mr.load(out / info["files"][half])
    points, tris = mr.coarse(tm, MESH_EDGE)
    owner = np.arange(len(tris))
    p = points[tris]
    centre = p.mean(axis=1)
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    keep = area > 1e-9
    normal = np.zeros_like(cross)
    normal[keep] = cross[keep] / (2 * area[keep, None])
    volume = float(
        (centre * normal * area[:, None]).sum() / 3
    )  # the divergence theorem: > 0 if outward
    if volume < 0:
        normal, volume = -normal, -volume
    rays = Rays(points, tris, owner)
    wall = float(info["settings"]["wall"])
    along = normal @ pull
    under = np.zeros(len(tris), bool)
    # each triangle is a face, which cannot hide itself: a ray along it skips its own crossings
    for i in np.nonzero(keep & (np.abs(along) >= PARALLEL))[0]:
        s = np.sign(along[i]) * pull
        start = centre[i] + OFFSET * normal[i] + EPS * s
        skip = int(owner[i]) if abs(along[i]) < 0.2 else None
        under[i] = rays.first(start, start + 3000.0 * s, skip) is not None
    thickness = np.full(len(tris), np.nan)
    for i in np.nonzero(keep)[0]:
        t = rays.first(centre[i] - EPS * normal[i], centre[i] - 400.0 * normal[i])
        if t is not None:
            thickness[i] = t + EPS
    thin = keep & (thickness < least - 0.1)
    voids = [-float(piece.volume) for piece in tm.split(only_watertight=False) if piece.volume < 0]
    lo, hi = points.min(axis=0) - 2.0, points.max(axis=0) + 2.0
    metal, (xs, ys, zs) = inside_voxels(rays, lo, hi)
    ball = (
        2.0 * distance_transform_edt(metal) * VOXEL
    )  # the diameter of the ball centred in each cell
    heavy = ball > THICK * wall
    ix, iy, iz = np.nonzero(heavy)
    spots = np.column_stack([xs[ix], ys[iy], zs[iz]]) if len(ix) else np.zeros((0, 3))
    total = float(area[keep].sum())
    faces = []
    for f in np.unique(owner[under]):
        sel = under & (owner == f)
        c = centre[sel]
        faces.append(
            {
                "face": int(f),
                "kind": "MESH",
                "role": "wall",
                "cm2": round(float(area[sel].sum()) / 100.0, 2),
                "share_of_face": round(
                    float(area[sel].sum() / max(area[owner == f].sum(), 1e-9)), 2
                ),
                "lo": [round(float(v), 1) for v in c.min(axis=0)],
                "hi": [round(float(v), 1) for v in c.max(axis=0)],
                "normal": [round(float(v), 2) for v in normal[sel].mean(axis=0)],
            }
        )
    faces.sort(key=lambda d: -d["cm2"])
    # the members' largest section: the ball inside the metal, each seat's boss (1.25·D + 10 across)
    # and each mount's eye left out; a lump where members cross is what it catches
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    own = np.zeros(gx.shape, bool)
    for b in layout["bearings"]:
        own |= np.hypot(gx - b["axis"][0], gy - b["axis"][1]) <= 0.625 * float(b["D"]) + 5.0
    for m_ in layout["mounts"]:
        own |= (
            np.hypot(gx - m_["centre"][0], gy - m_["centre"][1])
            <= 0.5 * float(layout["settings"]["mount_diameter"]) + 4.0
        )
    members_ball = np.where(own[:, :, None], 0.0, ball)
    under_cm2 = round(float(area[under].sum()) / 100.0, 1)
    result = {
        "half": half,
        "pull": pull.tolist(),
        "largest_section_members_mm": round(float(members_ball.max()), 1),
        "lump_rule": "PASS" if float(members_ball.max()) <= LUMP_MM else "FAIL",
        "area_cm2": round(total / 100.0, 1),
        "volume_cm3_mesh": round(volume / 1000.0, 1),
        "volume_cm3_voxels": round(float(metal.sum()) * VOXEL**3 / 1000.0, 1),
        "undercut_cm2": under_cm2,
        "undercut_share": round(float(area[under].sum()) / total, 4),
        "undercut_by_role_cm2": {"wall": under_cm2} if under.any() else {},
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


def castability(design: str, out: Path, contract: Path) -> dict:
    """Each half of `design` measured; `castable_<design>.json` and its picture written."""
    import pyvista as pv

    pulls, least = contract_rules(contract)
    info = json.loads((out / f"{design}.json").read_text(encoding="utf-8"))
    layout = json.loads((out / "contract.json").read_text(encoding="utf-8"))
    halves, meshes, spots = [], {}, {}
    for half, part in HALVES.items():
        say(f"{design} {half}: measuring")
        result, mesh, hot = judge_half(half, info, layout, out, pulls[part], least)
        halves.append(result)
        meshes[half], spots[half] = mesh, hot
        say(f"{design} {half}: {json.dumps(result)}")
    record = {"stem": design, "halves": halves}
    (out / f"castable_{design}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(1, 2), window_size=(1800, 850), off_screen=True)
    views = (((0.55, -0.45, 0.75), "the cover's side"), ((-0.55, -0.45, -0.75), "the motor's side"))
    for col, (view, title) in enumerate(views):
        plotter.subplot(0, col)
        for half in HALVES:
            plotter.add_mesh(meshes[half], scalars="rgb", rgb=True)
            if len(spots[half]):
                pts = spots[half][:: max(1, len(spots[half]) // 6000)]
                plotter.add_points(
                    pts, color=(1.0, 0.6, 0.1), point_size=4, render_points_as_spheres=True
                )
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        words = [f"{title}: red = undercut along the pull, blue = under the 4 mm least wall,"]
        words.append(
            f"orange = metal in a section over {THICK * float(info['settings']['wall']):.0f} mm"
        )
        if col == 0:
            for r in halves:
                words.append(
                    f"{r['half']}: pull {r['pull_rule']} ({100 * r['undercut_share']:.1f} % of the "
                    "area undercut, "
                    f"{r['closed_voids']} closed voids), least wall {r['least_wall_rule']}, "
                    f"largest section {r['largest_section_mm']:.0f} mm"
                )
        plotter.add_text("\n".join(words), font_size=9)
    plotter.screenshot(str(out / f"castable_{design}.png"))
    plotter.close()
    say(f"{design}: castable_{design}.png")
    return record
