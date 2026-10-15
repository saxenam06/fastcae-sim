"""Watertight meshes and their booleans (manifold3d), and a field's contour (moved from
`prototypes/first_loop/mesh_route.py`: `from_arrays`, `from_trimesh`, `to_trimesh`, `from_shape`,
`cylinder`, `half_space`, `contour`, `volume_of`, `largest`; LOP-33)."""

from __future__ import annotations

import numpy as np

SEGMENTS = 360  # facets a turn on a machined cylinder


def from_arrays(verts, faces):
    import manifold3d as mf

    mesh = mf.Mesh64(
        vert_properties=np.ascontiguousarray(verts, dtype=np.float64),
        tri_verts=np.ascontiguousarray(faces, dtype=np.uint32),
    )
    out = mf.Manifold(mesh)
    if out.status() != mf.Error.NoError:
        raise ValueError(f"not a manifold mesh ({out.status()})")
    return out


def from_trimesh(tm):
    return from_arrays(tm.vertices, tm.faces)


def to_trimesh(man):
    """manifold3d's own topology, exactly: merging coincident vertices can pinch two sheets that
    touch into one non-manifold vertex."""
    import trimesh

    mesh = man.to_mesh64()
    return trimesh.Trimesh(
        np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False
    )


def from_shape(shape, deflection: float = 0.05):
    """A B-rep solid (CadQuery) as a manifold: meshed with an absolute chord, its faces' vertices
    welded along their shared edges."""
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
    """A cylinder along z, as a manifold."""
    import manifold3d as mf

    lo, hi = min(z0, z1), max(z0, z1)
    c = mf.Manifold.cylinder(hi - lo, diameter / 2.0, -1.0, SEGMENTS, False)
    return c.translate((float(centre[0]), float(centre[1]), lo))


def half_space(z: float, keep_below: bool, reach: float = 4000.0):
    """The half of space a half keeps: below z (the motor side) or above."""
    import manifold3d as mf

    box = mf.Manifold.cube((2 * reach, 2 * reach, reach), False)
    return box.translate((-reach, -reach, z - reach if keep_below else z))


def contour(rho, lo, h: float, level: float = 0.5):
    """The field's contour at `level` (marching cubes on the padded grid: watertight, the cells'
    centres at lo + (i + 1/2) h), its largest piece."""
    import trimesh
    from skimage.measure import marching_cubes

    field = np.pad(rho.astype(float), 2)
    verts, faces, _, _ = marching_cubes(field, level=level, spacing=(h, h, h))
    verts += np.asarray(lo) - 2 * h + 0.5 * h
    tm = trimesh.Trimesh(verts, faces[:, ::-1], process=True)  # marching cubes winds inward here
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    if tm.volume < 0:
        tm.invert()
    return tm


def grid_over(meshes, step: float, pad: int = 3):
    """One grid of `step` mm over closed meshes: its lo and its shape (cells)."""
    lo_b = np.min([m.bounds[0] for m in meshes], axis=0)
    hi_b = np.max([m.bounds[1] for m in meshes], axis=0)
    return lo_b - pad * step, np.ceil((hi_b - lo_b) / step).astype(int) + 2 * pad


def occupancy(tm, step: float, lo, shape):
    """A closed mesh's cells on a grid of `step` mm (cell centres lo + (i + 1/2) step, `shape`
    cells), filled column by column along z between each pair of its surface's crossings (parity).
    Returns (cells, lo, the columns whose crossings were odd)."""
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


KEPT_REACH = (
    15.0  # mm round a crossing, the faces kept out of the next decimation (wider each round)
)
NEEDLE = 0.02  # mm: edges shorter are collapsed after the decimation (`coarse`)
KEPT_ROUNDS = 8


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


def coarse(tm, edge: float, keep_near: np.ndarray | None = None):
    """A watertight mesh coarsened for a judge (FE's tets, the castability's rays): manifold3d's
    simplify (the booleans' slivers collapsed, at the least tolerance that leaves no crossing), then
    quadric edge collapses (pymeshlab, topology kept) to triangles of about `edge` mm, then edges
    under `NEEDLE` collapsed. Returns (vertices, faces). It never hands on a surface that crosses
    itself (TetGen refuses one): where the decimation folds it, it is decimated again with the faces
    within `KEPT_REACH` of each crossing kept out, up to `KEPT_ROUNDS` times; `keep_near` (places
    TetGen refused) are kept fine from the start."""
    import pymeshlab
    from scipy.spatial import cKDTree

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
    if keep_near is not None and len(keep_near):
        near = cKDTree(np.asarray(keep_near, float).reshape(-1, 3))
        kept |= near.query(centres, distance_upper_bound=2.0 * KEPT_REACH)[0] < 2.0 * KEPT_REACH
    for rnd in range(KEPT_ROUNDS):
        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(v0, f0, f_scalar_array=(~kept).astype(float)))
        if kept.any():
            ms.compute_selection_by_condition_per_face(condselect="fq > 0.5")
        ms.meshing_decimation_quadric_edge_collapse(
            targetfacenum=target + int(kept.sum()),
            preserveboundary=True,
            preservenormal=True,
            preservetopology=True,
            optimalplacement=True,
            planarquadric=True,
            qualitythr=0.4,
            selected=bool(kept.any()),
        )
        m = ms.current_mesh()
        v, f = np.asarray(m.vertex_matrix(), float), np.asarray(m.face_matrix(), np.int64)
        crossing = crossing_centres(v, f)
        if not len(crossing):
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
    raise RuntimeError(
        f"the coarsened surface still crosses itself at {len(crossing)} faces after {KEPT_ROUNDS} "
        "rounds"
    )


def volume_of(man) -> float:
    return float(man.volume())


def largest(man):
    """The largest piece (the loose ones dropped) and the volume dropped."""
    parts = man.decompose()
    if len(parts) <= 1:
        return man, 0.0
    parts = sorted(parts, key=lambda p: p.volume(), reverse=True)
    return parts[0], float(sum(p.volume() for p in parts[1:]))
