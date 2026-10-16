"""A drawn design's halves remeshed for FE (LOP-34; a prototype): `remesh.py <design> <new design>
[<edge mm>] [--check]` writes each half isotropically remeshed (pymeshlab's explicit remeshing,
target edge `edge`, 3 mm by default; its features kept at 30 degrees) as `<new design>_<half>.stl`
and `.ply`, with `<new design>.json` the drawing's record pointing at them; `--check` coarsens each
as FE does (`mesh.coarse` at `fe.SURFACE_EDGE`) and asks TetGen's detection for skipped faces.

Why: the rib drawing's surface (marching cubes on 1 mm cells, the exact cuts) resisted FE's
decimation (`rib_h3`'s motor side kept 672 k triangles at "7 mm" where the reference's coarsens to
16 k), so the raw slivers at a lug's hole rim reached TetGen, which refused them. Remeshed first,
the slivers go and the decimation works on well-shaped triangles. The volume moves by the remesh's
own tolerance (printed)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "rib_housing"


def main() -> None:
    import pymeshlab
    import trimesh

    from zenryx.domains.gearbox.housing import fe
    from zenryx.domains.gearbox.housing import mesh as mr

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    design, new = args[0], args[1]
    edge = float(args[2]) if len(args) > 2 else 3.0
    info = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    files = {}
    for half, name in info["files"].items():
        tm = mr.load(OUT / name)  # a trimesh (the indexed .ply when beside the .stl)
        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(np.asarray(tm.vertices, float), np.asarray(tm.faces, np.int32)))
        ms.meshing_isotropic_explicit_remeshing(targetlen=pymeshlab.PureValue(edge), featuredeg=30.0, iterations=5)
        ms.meshing_remove_duplicate_vertices()
        ms.meshing_remove_null_faces()
        m = ms.current_mesh()
        out = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)
        out.export(str(OUT / f"{new}_{half}.stl"))
        out.export(str(OUT / f"{new}_{half}.ply"))
        files[half] = f"{new}_{half}.stl"
        print(f"{half}: {len(tm.faces):,} -> {len(out.faces):,} triangles, watertight {out.is_watertight}, "
              f"volume {tm.volume / 1e3:.1f} -> {out.volume / 1e3:.1f} cm3", flush=True)
        if "--check" in sys.argv:
            v, f = mr.coarse(mr.load(OUT / files[half]), fe.SURFACE_EDGE)
            here = os.getcwd()
            os.chdir(tempfile.mkdtemp(dir=OUT / "fe_cwd"))
            skipped = fe.tetgen_skipped(v, f)
            os.chdir(here)
            print(f"  coarsened at {fe.SURFACE_EDGE:g} mm: {len(f):,} triangles, {len(skipped)} skipped by TetGen", flush=True)
    rec = {**info, "stem": new, "files": files, "remeshed_from": design, "remesh_edge_mm": edge}
    (OUT / f"{new}.json").write_text(json.dumps(rec, indent=1, default=list), encoding="utf-8")


if __name__ == "__main__":
    main()
