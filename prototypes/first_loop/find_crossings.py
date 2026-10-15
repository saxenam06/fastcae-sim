"""PROTOTYPE (LOP-30) - Where a drawn half's surface crosses itself: the drawn mesh as it is and coarsened as FE coarsens it, the self-
intersecting faces found by pymeshlab, grouped, each group's centre and what lies near it (a bearing's bore, a mount, a
bolt, the split)."""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesh_route as mr  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design, half = sys.argv[1], sys.argv[2]
edges = [float(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "0,7").split(",")]
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
raw = mr.load(OUT / f"{design}_{half}.ply")
import pymeshlab  # noqa: E402

for edge in edges:
    if edge > 0:
        v, f = mr.coarse(raw, edge)
    else:
        v, f = np.asarray(raw.vertices, float), np.asarray(raw.faces, np.int64)
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=v, face_matrix=f))
    ms.compute_selection_by_self_intersections_per_face()
    sel = ms.current_mesh().face_selection_array()
    idx = np.flatnonzero(sel)
    print(f"{design} {half} at {'the drawn surface' if edge <= 0 else f'{edge:g} mm triangles'}: {len(f):,} faces, {len(idx)} crossing")
    if not len(idx):
        continue
    cen = v[f[idx]].mean(axis=1)
    # group by 10 mm cells
    keys = np.floor(cen / 10.0).astype(int)
    uniq, inv = np.unique(keys, axis=0, return_inverse=True)
    for g in range(min(len(uniq), 12)):
        c = cen[inv.ravel() == g].mean(axis=0)
        near = []
        for b in lay["bearings"]:
            r = float(np.hypot(c[0] - b["axis"][0], c[1] - b["axis"][1]))
            if r < 0.5 * float(b["D"]) + 25:
                near.append(f"{b['shaft']} {b['side']} bore (r {r:.0f})")
        for m in lay["mounts"]:
            if float(np.hypot(c[0] - m["centre"][0], c[1] - m["centre"][1])) < 40:
                near.append(m["name"])
        print(f"   {int((inv.ravel() == g).sum())} faces at ({c[0]:.0f}, {c[1]:.0f}, {c[2]:.0f}) {', '.join(near)}")
