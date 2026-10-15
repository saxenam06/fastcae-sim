"""PROTOTYPE (LOP-20) - the skin drawing's solids as watertight triangle meshes, their booleans by
manifold3d (surface-mesh boolean fusion: the engineer's option 2 of 25 September, after the CAD
fuse), for a pipeline of minutes.

Why (11 October 01:26-01:40): the skin drawing's route through OCC (the smoothed field remeshed,
smoothed, sewn into a B-rep of 25,000 triangular faces, then fused with the exact shell and cut by
some fifty exact solids one boolean at a time, then a heal) took 5.5 minutes on
`outcome_skin_6mm_drive`, and on the one run's field no blur closed the motor side's surface at 5
mm triangles (the smoothing and the remeshing fold thin members); at 2.5 mm it closed but took 10
minutes and left faces 0.000 mm wide. Here:

- the members' surface is the blurred field's contour by marching cubes alone, which is watertight
  by construction (no smoothing, no remeshing: the blur makes it fair);
- the exact solids (the contract's shell, the cavity, every cut) are tessellated finely (0.05 mm
  chord) or built as manifold3d's cylinders (`SEGMENTS` a turn: 0.0015 mm off a Ø100 bore), so the
  machined faces stay crisp, the bores round;
- every boolean is manifold3d's: exact on its meshes, its result watertight, in milliseconds.

The result is a triangle mesh per half (`<stem>_<half>.stl`, and `.ply` with its topology). FE
coarsens it (`coarse`) and fills it with TetGen's tets (`fe.mesh_tetgen`); the castability check
and the pictures read its triangles.
"""

from __future__ import annotations

import numpy as np

SEGMENTS = 360  # facets a turn on a machined cylinder


def from_arrays(verts, faces):
    import manifold3d as mf

    mesh = mf.Mesh64(vert_properties=np.ascontiguousarray(verts, dtype=np.float64), tri_verts=np.ascontiguousarray(faces, dtype=np.uint32))
    out = mf.Manifold(mesh)
    if out.status() != mf.Error.NoError:
        raise ValueError(f"not a manifold mesh ({out.status()})")
    return out


def from_trimesh(tm):
    return from_arrays(tm.vertices, tm.faces)


def to_trimesh(man):
    import trimesh

    mesh = man.to_mesh64()
    # manifold3d's own topology, exactly: merging coincident vertices (process=True) can pinch two
    # sheets that touch into one non-manifold vertex, which gmsh then cannot parametrise
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def from_shape(shape, deflection: float = 0.05):
    """A B-rep solid (CadQuery) as a manifold: meshed with an absolute chord (CLAUDE.md's
    tessellation pitfall), its faces' vertices welded along their shared edges."""
    import trimesh
    from OCP.BRepMesh import BRepMesh_IncrementalMesh

    BRepMesh_IncrementalMesh(shape.wrapped, deflection, False, 0.1, True)
    verts, tris = shape.tessellate(deflection, 0.1)
    tm = trimesh.Trimesh(np.array([(v.x, v.y, v.z) for v in verts]), np.array(tris), process=True)
    tm.merge_vertices(digits_vertex=6)
    if not tm.is_watertight:
        trimesh.repair.fill_holes(tm)
    return from_trimesh(tm)


def cylinder(centre, z0: float, z1: float, diameter: float):
    """A cylinder along z, as `zenryx.geometry.solids.cylinder` gives it, as a manifold."""
    import manifold3d as mf

    lo, hi = min(z0, z1), max(z0, z1)
    return mf.Manifold.cylinder(hi - lo, diameter / 2.0, -1.0, SEGMENTS, False).translate((float(centre[0]), float(centre[1]), lo))


def half_space(z: float, keep_below: bool, reach: float = 4000.0):
    """The half of space a half keeps: below z (the motor side) or above."""
    import manifold3d as mf

    box = mf.Manifold.cube((2 * reach, 2 * reach, reach), False)
    return box.translate((-reach, -reach, z - reach if keep_below else z))


def contour(rho, lo, h: float, sigma: float, level: float = 0.5, keep=None):
    """The field's contour at `level` after a blur over `sigma` cells (marching cubes on the padded
    grid: watertight, the cells' centres at lo + (i + 1/2) h), its largest piece. With `keep` (LOP-29), the blurred
    field held at 1 in those cells, so the outline never passes inside them (the optimiser's metal cubes: the blur had
    thinned a member one cube wide and dropped a lone or diagonal cube, `lop29_modes`, 13 October 19:58); `keep` may be a
    density too (the exact parts' faces as a ramp, `exact_walls.ramp`)."""
    import trimesh
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes

    field = gaussian_filter(np.pad(rho.astype(float), 2), sigma=sigma)
    if keep is not None:
        field = np.maximum(field, np.pad(np.asarray(keep, float), 2))
    verts, faces, _, _ = marching_cubes(field, level=level, spacing=(h, h, h))
    verts += np.asarray(lo) - 2 * h + 0.5 * h
    tm = trimesh.Trimesh(verts, faces[:, ::-1], process=True)  # marching cubes winds inward here
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    if tm.volume < 0:
        tm.invert()
    return tm


def faithful(rho, lo, h: float, sample_mm: float, sigma: float = 1.0, level: float = 0.5, ridge: float = 0.0):
    """The field's surface drawn smooth and faithful (LOP-27; Ježek et al. 2025's two steps, read in
    `docs/research/2026-10-12-smooth-extraction-rho2sdf.md`): the plain contour's (`contour`) signed
    distance sampled on a lattice `sample_mm` apart, laid on the cells' grid's own voxel centres (lo +
    (j + 1/2) sample_mm: the optimiser's voxels when it is their size, so a wall one voxel thick holds a
    sample), interpolated exactly by Gaussian radial basis functions as wide as the lattice (separable on
    a regular lattice: one small solve an axis, no dense matrix), evaluated at the cells, shifted
    uniformly until it encloses the plain contour's volume, and contoured at zero. Smooth between the
    samples, unmoved at them, the mass kept: where `contour_sdf` blurs the distance (which moves the
    surface and thins members) and keeps no volume. The distance is to the plain contour's nearest
    vertex (marching cubes' vertices lie at most a cell apart), signed by the blurred field.

    At the voxel's own spacing the exact interpolation reproduces the voxels' facets (the method keeps
    what it is given; 12 October 21:05, `empty1_faithful_5.5kg`) and rings on their steps, which rounded
    vertical sides into undercuts (4.7 % against 0.6 %). `ridge` > 0 fits instead of interpolating:
    each axis' Gaussian system with `ridge` on its diagonal (a separable Tikhonov fit), which damps the
    lattice's shortest waves (at `ridge` 0.3 an axis' shortest wave to half at the samples) and rings
    less on them.
    Returns (the surface, a note of the shift and the volumes)."""
    import trimesh
    from scipy.ndimage import gaussian_filter, map_coordinates
    from scipy.spatial import cKDTree
    from skimage.measure import marching_cubes

    plain = contour(rho, lo, h, sigma, level)
    pad = 2
    field = gaussian_filter(np.pad(rho.astype(float), pad), sigma=sigma)  # as `contour` reads it
    n = np.array(field.shape)
    org = np.asarray(lo, float) - pad * h  # the padded grid's lower corner; its cells' centres at org + (i + 1/2) h
    lattice, cells = [], []
    for a in range(3):
        j0 = int(np.floor((org[a] - lo[a]) / sample_mm - 1.5))
        j1 = int(np.ceil((org[a] + n[a] * h - lo[a]) / sample_mm + 0.5))
        lattice.append(lo[a] + (np.arange(j0, j1 + 1) + 0.5) * sample_mm)
        cells.append(org[a] + (np.arange(n[a]) + 0.5) * h)
    P = np.stack(np.meshgrid(*lattice, indexing="ij"), axis=-1).reshape(-1, 3)
    dist = cKDTree(plain.vertices).query(P)[0]
    inside = map_coordinates(field, ((P - org) / h - 0.5).T, order=1, mode="nearest") >= level
    values = np.where(inside, dist, -dist).reshape(tuple(len(s) for s in lattice))

    def along(mat, arr, axis):  # mat (m x k) applied along `axis` (of length k)
        moved = np.moveaxis(arr, axis, 0)
        out = mat @ moved.reshape(moved.shape[0], -1)
        return np.moveaxis(out.reshape((mat.shape[0],) + moved.shape[1:]), 0, axis)

    w = values
    for a, s in enumerate(lattice):  # the weights: the Gaussian system, an axis at a time (condition about 6 an axis)
        kern = np.exp(-(((s[:, None] - s[None, :]) / sample_mm) ** 2))
        w = along(np.linalg.inv(kern + ridge * np.eye(len(s))), w, a)
    smooth = w
    for a, (s, c) in enumerate(zip(lattice, cells, strict=True)):  # evaluated at the cells
        smooth = along(np.exp(-(((c[:, None] - s[None, :]) / sample_mm) ** 2)), smooth, a)
    target = float(plain.volume)
    low, high = -2.0 * sample_mm, 2.0 * sample_mm  # the shift, mm: more metal as it rises
    for _ in range(40):
        mid = 0.5 * (low + high)
        if float((smooth + mid > 0.0).sum()) * h**3 > target:
            high = mid
        else:
            low = mid
    shift = 0.5 * (low + high)
    verts, faces, _, _ = marching_cubes(smooth + shift, level=0.0, spacing=(h, h, h))
    verts += org + 0.5 * h
    tm = trimesh.Trimesh(verts, faces[:, ::-1], process=True)  # inward winding, as `contour`'s
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    if tm.volume < 0:
        tm.invert()
    note = {"sample_mm": sample_mm, "ridge": ridge, "shift_mm": round(shift, 3), "plain_cm3": round(target / 1e3, 1), "smooth_cm3": round(float(tm.volume) / 1e3, 1),
            "samples": int(P.shape[0])}  # fmt: skip
    return tm, note


def contour_sdf(rho, lo, h: float, sigma_mm: float):
    """The metal's (rho at 0.5 or more) contour from its signed distance, smoothed (LOP-23, 11
    October 16:15; Ježek et al. 2025 smooth a SIMP field's signed distance for the same end): the
    distance to the metal's surface (mm, negative inside) blurred over `sigma_mm`, contoured at
    zero. A blur keeps a plane's distance, so flat faces stay where they are; convex edges round and
    concave corners fill; a member thinner than about twice `sigma_mm` thins less than under the
    density's blur. Its largest watertight piece, outward."""
    import trimesh
    from scipy.ndimage import distance_transform_edt, gaussian_filter
    from skimage.measure import marching_cubes

    inside = np.pad(np.asarray(rho) >= 0.5, 3)
    dist = (distance_transform_edt(~inside) - distance_transform_edt(inside)) * h
    dist = gaussian_filter(dist, sigma=sigma_mm / h)
    verts, faces, _, _ = marching_cubes(dist, level=0.0, spacing=(h, h, h))
    verts += np.asarray(lo) - 3 * h + 0.5 * h
    tm = trimesh.Trimesh(verts, faces, process=True)
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    if tm.volume < 0:
        tm.invert()
    return tm


def tessellated(shape, deflection: float = 0.05):
    """A B-rep solid's closed triangle mesh (its faces' vertices welded), without manifold3d's
    checks: `occupancy` needs it closed, not manifold."""
    import trimesh
    from OCP.BRepMesh import BRepMesh_IncrementalMesh

    BRepMesh_IncrementalMesh(shape.wrapped, deflection, False, 0.1, True)
    verts, tris = shape.tessellate(deflection, 0.1)
    tm = trimesh.Trimesh(np.array([(v.x, v.y, v.z) for v in verts]), np.array(tris), process=True)
    tm.merge_vertices(digits_vertex=6)
    return tm


def grid_over(meshes, step: float, pad: int = 3):
    """One grid of `step` mm over closed meshes: its lo and its shape (cells)."""
    lo_b = np.min([m.bounds[0] for m in meshes], axis=0)
    hi_b = np.max([m.bounds[1] for m in meshes], axis=0)
    return lo_b - pad * step, np.ceil((hi_b - lo_b) / step).astype(int) + 2 * pad


def occupancy(mesh, step: float, lo=None, shape=None, pad: int = 3):
    """A closed solid's cells on a grid of `step` mm (cell centres lo + (i + 1/2) step), filled
    column by column along z between each pair of its surface's crossings (parity), and the
    grid's lo. With `contour` it gives the solid's surface free of any feature under a cell: the
    ribbed drawing's exact parts met in faces 0.002 mm wide, which TetGen could not mesh (11
    October 04:15). `mesh` a manifold or a trimesh; `lo` and `shape` a grid shared with others
    (`grid_over`). Returns (cells (bool, x by y by z), lo, columns whose crossings were odd)."""
    tm = mesh if hasattr(mesh, "faces") and hasattr(mesh, "vertices") and not hasattr(mesh, "decompose") else to_trimesh(mesh)
    if lo is None:
        lo, shape = grid_over([tm], step, pad)
    tri = tm.vertices[tm.faces]
    # the columns' centres, nudged off the cells' lattice so that no column runs through an edge
    x0, y0 = lo[0] + 0.5 * step + 1.37e-4, lo[1] + 0.5 * step + 2.71e-4
    i_lo = np.ceil((tri[:, :, 0].min(axis=1) - x0) / step).astype(int)
    i_hi = np.floor((tri[:, :, 0].max(axis=1) - x0) / step).astype(int)
    j_lo = np.ceil((tri[:, :, 1].min(axis=1) - y0) / step).astype(int)
    j_hi = np.floor((tri[:, :, 1].max(axis=1) - y0) / step).astype(int)
    ni, nj = np.maximum(i_hi - i_lo + 1, 0), np.maximum(j_hi - j_lo + 1, 0)
    count = ni * nj
    t_id = np.repeat(np.arange(len(tri)), count)
    local = np.arange(int(count.sum())) - np.repeat(np.cumsum(count) - count, count)
    i = i_lo[t_id] + local // np.maximum(nj[t_id], 1)
    j = j_lo[t_id] + local % np.maximum(nj[t_id], 1)
    px, py = x0 + step * i, y0 + step * j
    a, b, c = tri[t_id, 0], tri[t_id, 1], tri[t_id, 2]
    det = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(det) > 1e-12
    det = np.where(ok, det, 1.0)
    w1 = ((b[:, 1] - c[:, 1]) * (px - c[:, 0]) + (c[:, 0] - b[:, 0]) * (py - c[:, 1])) / det
    w2 = ((c[:, 1] - a[:, 1]) * (px - c[:, 0]) + (a[:, 0] - c[:, 0]) * (py - c[:, 1])) / det
    w3 = 1.0 - w1 - w2
    inside = ok & (w1 >= 0) & (w2 >= 0) & (w3 >= 0)
    zc = w1 * a[:, 2] + w2 * b[:, 2] + w3 * c[:, 2]
    i, j, zc = i[inside], j[inside], zc[inside]
    order = np.lexsort((zc, j, i))
    i, j, zc = i[order], j[order], zc[order]
    key = i * (shape[1] + 1) + j
    start = np.flatnonzero(np.concatenate([[True], key[1:] != key[:-1]]))
    runs = np.diff(np.concatenate([start, [len(key)]]))
    odd = int((runs % 2 == 1).sum())
    rank = np.arange(len(key)) - np.repeat(start, runs)
    even_col = np.repeat(runs % 2 == 0, runs)
    first = (rank % 2 == 0) & even_col
    z_in, z_out = zc[first], zc[np.flatnonzero(first) + 1]
    ci, cj = i[first], j[first]
    k_lo = np.ceil((z_in - lo[2]) / step - 0.5).astype(int)
    k_hi = np.floor((z_out - lo[2]) / step - 0.5).astype(int)
    span = np.maximum(k_hi - k_lo + 1, 0)
    cells = np.zeros(tuple(shape), bool)
    s_id = np.repeat(np.arange(len(span)), span)
    k = k_lo[s_id] + (np.arange(int(span.sum())) - np.repeat(np.cumsum(span) - span, span))
    cells[ci[s_id], cj[s_id], k] = True
    return cells, lo, odd


def load(path):
    """A half's watertight mesh: its indexed copy (`.ply`, manifold3d's own topology) beside the STL
    when there is one; an STL keeps no shared vertices, so it is welded."""
    from pathlib import Path

    import trimesh

    path = Path(path)
    ply = path.with_suffix(".ply")
    tm = trimesh.load(str(ply if ply.exists() else path), process=False)
    return tm if tm.is_watertight else trimesh.load(str(path), process=True)


def crossing_centres(verts, faces) -> np.ndarray:
    """The centres of a mesh's faces that cross another of its faces (pymeshlab's test)."""
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(np.asarray(verts, float), np.asarray(faces, np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    sel = ms.current_mesh().face_selection_array()
    return np.asarray(verts, float)[np.asarray(faces)[sel]].mean(axis=1)


KEPT_REACH = 15.0  # mm round a crossing, the faces kept out of the next decimation (wider each round)
NEEDLE = 0.02  # mm: edges shorter are collapsed after the decimation (`coarse`)
KEPT_ROUNDS = 8  # 5 left 8 crossings on a smooth drawing's motor side, whose own surface crosses nowhere (`fa9_bar2`, 12 October 04:55)


def coarse(tm, edge: float, keep_near: np.ndarray | None = None):
    """A watertight mesh coarsened for a judge (FE's tets, the castability's rays): manifold3d's
    simplify (edges under 0.05 mm collapsed: the booleans' slivers), then quadric edge collapses
    (pymeshlab, topology kept) to triangles of about `edge` mm. Returns (vertices, faces).

    It never hands on a surface that crosses itself (TetGen refuses one): where the collapse folds
    the surface it is decimated as it is, and where the decimation folds it, it is decimated again
    with the faces within `KEPT_REACH` of each crossing kept out of it, up to `KEPT_ROUNDS` times.
    A ribbed design's bare 4 mm walls between its ribs folded at 9 mm triangles (`ribbed_cad.py`,
    11 October 03:50); the marching cubes' members never did, and are decimated as before."""
    import pymeshlab
    from scipy.spatial import cKDTree

    # (15 October 03:15) a tolerance that leaves no crossing, before falling back to the raw surface: at 0.05 mm `spl8`'s
    # motor side crossed itself twice and its raw surface carried 983 triangles of no area (`degenerate_centres`), at 0.2
    # none crossed and 24 had no area
    for tol in (0.05, 0.1, 0.2):
        s = to_trimesh(from_arrays(tm.vertices, tm.faces).simplify(tol))
        if not len(crossing_centres(s.vertices, s.faces)):
            break
    else:
        s = tm
    v0, f0 = np.asarray(s.vertices, float), np.asarray(s.faces, np.int32)
    centres = v0[f0].mean(axis=1)
    target = int(max(4000, s.area / (0.433 * edge**2)))
    kept = np.zeros(len(f0), bool)
    if keep_near is not None and len(keep_near):  # (15 October 03:15) places TetGen refused (`fe.mesh_tetgen`): kept fine
        kept |= cKDTree(np.asarray(keep_near, float).reshape(-1, 3)).query(centres, distance_upper_bound=2.0 * KEPT_REACH)[0] < 2.0 * KEPT_REACH
    for rnd in range(KEPT_ROUNDS):
        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(v0, f0, f_scalar_array=(~kept).astype(float)))
        if kept.any():
            ms.compute_selection_by_condition_per_face(condselect="fq > 0.5")
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target + int(kept.sum()), preserveboundary=True, preservenormal=True,
                                                    preservetopology=True, optimalplacement=True, planarquadric=True, qualitythr=0.4,
                                                    selected=bool(kept.any()))  # fmt: skip
        m = ms.current_mesh()
        v, f = np.asarray(m.vertex_matrix(), float), np.asarray(m.face_matrix(), np.int64)
        crossing = crossing_centres(v, f)
        if not len(crossing):
            # (15 October 03:35) edges under NEEDLE mm collapsed: marching cubes puts two vertices 1e-4 mm apart where a
            # grid value lies a hair off the level, the decimation keeps them, and TetGen builds hundreds of flat tets on
            # the needle triangle (`spl8`'s motor side: 249 at one place, shapes 1e-7)
            try:
                tidy = to_trimesh(from_arrays(v, f).simplify(NEEDLE))
                v2, f2 = np.asarray(tidy.vertices, float), np.asarray(tidy.faces, np.int64)
                if len(f2) and not len(crossing_centres(v2, f2)):
                    return v2, f2
            except ValueError:
                pass
            return v, f
        reach = KEPT_REACH * (1.0 + 0.5 * rnd)
        kept |= cKDTree(crossing).query(centres, distance_upper_bound=reach)[0] < reach
    raise RuntimeError(f"the coarsened surface still crosses itself at {len(crossing)} faces after {KEPT_ROUNDS} rounds")


def degenerate_centres(v: np.ndarray, f: np.ndarray, rel: float = 1e-6) -> np.ndarray:
    """(15 October 03:00) The centres of triangles with next to no area, three points on a line: TetGen refuses them as
    self-intersections where pymeshlab's crossing test sees none (`spl8`'s motor side at 7 mm: two triangles of a
    vertical crease's vertices, one above another at (0.8, 187.4)). A triangle is one when its area is under `rel` of
    its longest edge squared."""
    t = np.asarray(v, float)[np.asarray(f, np.int64)]
    area2 = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    longest = np.max([np.sum((t[:, i] - t[:, (i + 1) % 3]) ** 2, axis=1) for i in range(3)], axis=0)
    return t[area2 <= 2.0 * rel * np.maximum(longest, 1e-12)].mean(axis=1)


def volume_of(man) -> float:
    return float(man.volume())


def largest(man):
    """The largest piece (the loose ones dropped) and the volume dropped."""
    parts = man.decompose()
    if len(parts) <= 1:
        return man, 0.0
    parts = sorted(parts, key=lambda p: p.volume(), reverse=True)
    return parts[0], float(sum(p.volume() for p in parts[1:]))
