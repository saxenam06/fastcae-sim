"""Where a drawn half's coarsened FE surface intersects itself, by pymeshlab (LOP-34; a prototype):
`self_cross.py <design> <half> [<edge mm>] [--folder=<dir>] [--first-round]` coarsens as FE does (`mesh.coarse`; with `--first-round` its first decimation alone)
and selects the self-intersecting faces (`compute_selection_by_self_intersections_per_face`);
prints them clustered 10 mm apart, with what of the layout is near each."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "rib_housing"


def main() -> None:
    import pymeshlab
    from scipy.cluster.hierarchy import fcluster, linkage

    from zenryx.domains.gearbox.housing import fe
    from zenryx.domains.gearbox.housing import mesh as mr

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", OUT))
    design, half = args[0], args[1]
    edge = float(args[2]) if len(args) > 2 else fe.SURFACE_EDGE
    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    raw = mr.load(folder / info["files"][half])
    if "--first-round" in sys.argv:  # the coarsening's first decimation alone: where it folds
        s = mr.to_trimesh(mr.from_arrays(raw.vertices, raw.faces).simplify(0.05))
        ms0 = pymeshlab.MeshSet()
        ms0.add_mesh(pymeshlab.Mesh(np.asarray(s.vertices, float), np.asarray(s.faces, np.int32)))
        ms0.meshing_decimation_quadric_edge_collapse(
            targetfacenum=int(max(4000, s.area / (0.433 * edge**2))), preserveboundary=True,
            preservenormal=True, preservetopology=True, optimalplacement=True, planarquadric=True,
            qualitythr=0.4)
        verts, faces = ms0.current_mesh().vertex_matrix(), ms0.current_mesh().face_matrix()
    else:
        try:
            verts, faces = mr.coarse(raw, edge)
        except RuntimeError as e:
            print(f"the coarsening itself refused: {e}")
            return
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(np.asarray(verts, float), np.asarray(faces, np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    sel = ms.current_mesh().face_selection_array()
    cen = np.asarray(verts)[np.asarray(faces)[sel]].mean(axis=1)
    print(f"{design} {half} at {edge:g} mm: {len(faces):,} triangles, {int(sel.sum())} self-intersecting")
    if len(cen) == 0:
        return
    lab = fcluster(linkage(cen, "single"), 10.0, "distance") if len(cen) > 1 else np.array([1])
    lay = json.loads((folder / "contract.json").read_text(encoding="utf-8"))
    for k in np.unique(lab):
        c = cen[lab == k].mean(axis=0)
        near = []
        for b in lay["bearings"]:
            d = np.hypot(c[0] - b["axis"][0], c[1] - b["axis"][1])
            if d < b["D"] / 2 + 30:
                near.append(f"{b['shaft']} {b['side']} bore r {d:.0f}")
        for i, bolt in enumerate(lay["bolts"]):
            if np.hypot(c[0] - bolt[0], c[1] - bolt[1]) < 20:
                near.append(f"bolt {i + 1}")
        for m in lay["mounts"]:
            if np.hypot(c[0] - m["centre"][0], c[1] - m["centre"][1]) < 50:
                near.append(m["name"])
        print(f"  {int((lab == k).sum()):3d} faces about ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f}): " + ("; ".join(near) or "open"))


if __name__ == "__main__":
    main()
