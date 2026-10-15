"""PROTOTYPE (LOP-30) - TetGen's own intersection report (switch d) on a drawn half coarsened as FE coarsens it: the facets it finds
intersecting, their places and what lies near them. TetGen runs in a child process (it can crash), its output parsed."""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesh_route as mr  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design, half, edge = sys.argv[1], sys.argv[2], float(sys.argv[3])
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
raw = mr.load(OUT / f"{design}_{half}.ply")
import pymeshlab
s_ = mr.to_trimesh(mr.from_arrays(raw.vertices, raw.faces).simplify(0.2))
ms_ = pymeshlab.MeshSet()
ms_.add_mesh(pymeshlab.Mesh(np.asarray(s_.vertices, float), np.asarray(s_.faces, np.int32)))
ms_.meshing_decimation_quadric_edge_collapse(targetfacenum=int(max(4000, s_.area / (0.433 * edge**2))), preserveboundary=True, preservenormal=True, preservetopology=True, optimalplacement=True, planarquadric=True, qualitythr=0.4)
v, f = np.asarray(ms_.current_mesh().vertex_matrix(), float), np.asarray(ms_.current_mesh().face_matrix(), np.int64)
CHILD = (
    "import sys, numpy as np, tetgen\n"
    "z = np.load(sys.argv[1])\n"
    "tg = tetgen.TetGen(z['v'], z['f'].astype(np.int32))\n"
    "try:\n"
    "    tg.tetrahedralize(switches='pdV')\n"
    "except Exception as e:\n"
    "    print('ERR', e)\n"
)
with tempfile.TemporaryDirectory(prefix="tgd_") as tmp:
    src = Path(tmp) / "in.npz"
    np.savez(src, v=v, f=f)
    py = sys.executable
    p = subprocess.run([py, "-c", CHILD, str(src)], capture_output=True, text=True, timeout=600)
out = (p.stdout or "") + (p.stderr or "")
lines = out.splitlines()
print(f"{design} {half} at {edge:g} mm: {len(f):,} faces; TetGen said {len(lines)} lines")
for ln in lines:
    if True:
        print("  ", ln[:200])
# facet indices in lines like "  Facet #12 (1, 2, 3) and facet #34 (...)" or "  1:  (a, b, c)"
nums = [int(x) for ln in lines if "facet" in ln.lower() for x in re.findall(r"#(\d+)", ln)]
if not nums:
    tri = [tuple(int(a) for a in re.findall(r"\d+", ln)[:3]) for ln in lines if re.search(r"\(\s*\d+,\s*\d+,\s*\d+\s*\)", ln)]
    print(f"   {len(tri)} triangles listed by their vertices")
    pts = [v[[a - 1, b - 1, c - 1]].mean(axis=0) for a, b, c in tri if max(a, b, c) <= len(v)]
else:
    pts = [v[f[i - 1]].mean(axis=0) for i in nums if 0 < i <= len(f)]
pts = np.asarray(pts)
if len(pts):
    keys = np.floor(pts / 10.0).astype(int)
    uniq, inv = np.unique(keys, axis=0, return_inverse=True)
    for g in np.argsort(-np.bincount(inv.ravel()))[:12]:
        c = pts[inv.ravel() == g].mean(axis=0)
        near = [f"{b['shaft']} {b['side']} r{float(np.hypot(c[0] - b['axis'][0], c[1] - b['axis'][1])):.0f}" for b in lay["bearings"]
                if float(np.hypot(c[0] - b["axis"][0], c[1] - b["axis"][1])) < 0.5 * float(b["D"]) + 25]
        bolts = np.asarray(lay["bolts"], float)
        db = float(np.min(np.hypot(*(bolts[:, :2] - c[:2]).T)))
        print(f"   x{int((inv.ravel() == g).sum())} at ({c[0]:.0f}, {c[1]:.0f}, {c[2]:.0f}); nearest bolt {db:.0f} mm; {', '.join(near)}")
