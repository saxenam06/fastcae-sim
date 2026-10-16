"""Needles merged out of a coarsened surface before TetGen (LOP-34, the restart; a prototype; the
product's code is not changed).

The product's `mesh.coarse` collapses edges under `mesh.NEEDLE` (0.02 mm) by manifold3d's simplify and
keeps the result only if it does not cross itself; when it does, it hands on the decimated surface with
its needles, and TetGen fills round a 1e-4 mm edge with thousands of flat tets (16 October:
`walls_w5c`'s cover, 32,000 tets under 1e-5 in one 10 mm cell beside two such edges at the flange's
top, and the single factor did not refine at any rung). `merged` merges the vertices closer than the
needle (pymeshlab), drops the null and repeated faces, and keeps the result only if it is watertight
and crosses nothing. `use()` wraps `mesh.coarse` with it, for this process (`judge.py --needles`).
`needles.py <design> <half> [<edge mm>]` shows it on one half.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def shortest(v, f) -> float:
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    return float(np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1).min())


def least_height(v, f) -> float:
    """The least triangle height: twice its area over its longest edge (mm)."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    longest = np.max(np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1),
                               np.linalg.norm(a - c, axis=1)]), axis=0)
    return float((2 * area / np.maximum(longest, 1e-12)).min())


def merged(v: np.ndarray, f: np.ndarray, needle: float | None = None):
    """(vertices, faces) with the needles merged, or the input when that would break the surface."""
    import pymeshlab
    import trimesh

    from zenryx.domains.gearbox.housing import mesh as mr

    needle = needle or mr.NEEDLE
    if shortest(v, f) >= needle and least_height(v, f) >= needle:
        return v, f

    def valid(v_, f_) -> bool:
        return bool(len(f_)) and trimesh.Trimesh(v_, f_, process=False).is_watertight \
            and not len(mr.crossing_centres(v_, f_))

    def step(v_, f_, ops):
        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(np.asarray(v_, float), np.asarray(f_, np.int32)))
        for op in ops:
            op(ms)
        ms.meshing_remove_duplicate_faces()
        ms.meshing_remove_null_faces()
        ms.meshing_remove_unreferenced_vertices()
        m = ms.current_mesh()
        v2, f2 = np.asarray(m.vertex_matrix(), float), np.asarray(m.face_matrix(), np.int64)
        return (v2, f2) if valid(v2, f2) else (v_, f_)

    # the needles: vertices closer than the needle merged
    v, f = step(v, f, [lambda ms: ms.meshing_merge_close_vertices(threshold=pymeshlab.PureValue(needle))])
    # the slivers (three nearly collinear vertices) by their T-vertices, flipped or collapsed away
    for thr in (40.0, 20.0, 10.0):
        if least_height(v, f) >= needle:
            break
        v, f = step(v, f, [lambda ms, t=thr: ms.meshing_remove_t_vertices(method=0, threshold=t, repeat=True)])
    return v, f


FLAT = 1e-5  # a tet flatter than this is kept fine round and meshed again (3e-6 did not refine)


def mesh_tetgen(path, size, quality, surface, last):
    """The product's `fe.mesh_tetgen`, but a flat tet is treated as TetGen's refusals are: the
    surface kept fine round the flat tets' centres and coarsened again at the same size (up to
    `fe.KEEP_TRIES` times), then the ladder (16 October: `walls_w5c`'s cover made a flat tet on the
    sealing land's chamfer at every rung)."""
    import math
    import time

    from zenryx.domains.gearbox.housing import fe, say
    from zenryx.domains.gearbox.housing import mesh as mr

    t0 = time.time()
    raw = mr.load(path)
    regular = (1.5 * size) ** 3 / (6.0 * math.sqrt(2.0))
    ladder = tuple(dict.fromkeys((surface, round(1.07 * surface, 2), round(0.93 * surface, 2),
                                  *(() if last is None else (last,)))))
    keep = np.zeros((0, 3))
    last_err, best = None, None
    for edge in ladder:
        for k_try in range(fe.KEEP_TRIES + 1):
            if k_try and not len(keep):
                break
            verts, faces = mr.coarse(raw, edge, keep_near=keep)
            try:
                nodes, tets = fe.tetrahedralize_guarded(verts, faces, quality, regular)
            except RuntimeError as e:
                last_err = e
                named = getattr(e, "centres", np.zeros((0, 3)))
                if len(named):
                    keep = np.vstack([keep, named])
                    say(f"{path.stem}: TetGen refused at {edge:g} mm ({e}); {len(named)} places kept fine")
                    continue
                break
            nodes, tets = np.asarray(nodes, float), np.asarray(tets, np.int64)
            shape = fe.tet_shape(nodes, tets)
            if best is None or shape.min() > best[2]:
                best = (nodes, tets, float(shape.min()), len(faces))
            if shape.min() >= FLAT:
                say(f"{path.stem}: TetGen, {len(faces):,} surface triangles, {len(tets):,} tets, worst shape "
                    f"{shape.min():.3g}, {time.time() - t0:.1f} s")
                return nodes, tets
            flats = nodes[tets[shape < FLAT]].mean(axis=1)
            keep = np.vstack([keep, flats])
            say(f"{path.stem}: {len(flats)} tets flatter than {FLAT:g} (worst {shape.min():.2g}) at {edge:g} mm; "
                "kept fine round them, coarsened again")
    if best is None:
        raise last_err or RuntimeError("no surface TetGen accepted")
    say(f"{path.stem}: the best mesh kept: {best[3]:,} surface triangles, {len(best[1]):,} tets, worst shape "
        f"{best[2]:.3g}, {time.time() - t0:.1f} s")
    return best[0], best[1]


def use() -> None:
    from zenryx.domains.gearbox.housing import fe
    from zenryx.domains.gearbox.housing import mesh as mr

    coarse = mr.coarse

    def coarse_merged(tm, edge, keep_near=None):
        v, f = coarse(tm, edge, keep_near=keep_near)
        return merged(np.asarray(v, float), np.asarray(f, np.int64))

    mr.coarse = coarse_merged
    fe.mesh_tetgen = mesh_tetgen


def main() -> None:
    import math

    from zenryx.domains.gearbox.housing import fe
    from zenryx.domains.gearbox.housing import mesh as mr

    design, half = sys.argv[1], sys.argv[2]
    edge = float(sys.argv[3]) if len(sys.argv) > 3 else fe.SURFACE_EDGE
    folder = ROOT / "data" / "rib_walls"
    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    v, f = mr.coarse(mr.load(folder / info["files"][half]), edge, keep_near=np.zeros((0, 3)))
    v, f = np.asarray(v, float), np.asarray(f, np.int64)
    v2, f2 = merged(v, f)
    print(f"{design} {half} at {edge:g} mm: shortest edge {shortest(v, f):.2e} -> {shortest(v2, f2):.2e} mm, "
          f"least triangle height {least_height(v, f):.2e} -> {least_height(v2, f2):.2e} mm; "
          f"{len(f):,} -> {len(f2):,} triangles")
    regular = (1.5 * fe.SIZE) ** 3 / (6.0 * math.sqrt(2.0))
    for name, (vv, ff) in (("as coarsened", (v, f)), ("needles merged", (v2, f2))):
        try:
            nodes, tets = fe.tetrahedralize_guarded(vv, ff, fe.QUALITY_LADDER[0], regular)
            shape = fe.tet_shape(np.asarray(nodes, float), np.asarray(tets, np.int64))
            print(f"  {name}: {len(tets):,} tets, worst shape {shape.min():.2e}, {int((shape < 1e-5).sum())} under 1e-5")
        except RuntimeError as e:
            print(f"  {name}: TetGen refused ({e})")


if __name__ == "__main__":
    main()
