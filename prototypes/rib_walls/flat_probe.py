"""Where a drawn half's FE mesh holds its flattest tets (LOP-34, the restart; a prototype):
`flat_probe.py <design> <half> [<edge mm>] [--folder=<dir>]` coarsens the half as FE does
(`mesh.coarse`), meshes it by TetGen at FE's first quality (`fe.tetrahedralize_guarded`), and prints
the flattest tets' centres, their shape, and what of the layout and the drawing lies near each (a
bore's axis, a bolt, a mount; the plan reading's ribs, fins, footprint edge)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    from zenryx.domains.gearbox.housing import fe
    from zenryx.domains.gearbox.housing import mesh as mr

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", ROOT / "data" / "rib_walls"))
    design, half = args[0], args[1]
    edge = float(args[2]) if len(args) > 2 else fe.SURFACE_EDGE
    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    raw = mr.load(folder / info["files"][half])
    verts, faces = mr.coarse(raw, edge, keep_near=np.zeros((0, 3)))
    if "--needles" in sys.argv:
        import needles

        verts, faces = needles.merged(np.asarray(verts, float), np.asarray(faces, np.int64))
    regular = (1.5 * fe.SIZE) ** 3 / (6.0 * math.sqrt(2.0))
    nodes, tets = fe.tetrahedralize_guarded(verts, faces, fe.QUALITY_LADDER[0], regular)
    nodes, tets = np.asarray(nodes, float), np.asarray(tets, np.int64)
    shape = fe.tet_shape(nodes, tets)
    order = np.argsort(shape)[:12]
    lay = json.loads((folder / "contract.json").read_text(encoding="utf-8"))
    print(f"{design} {half} at {edge:g} mm: {len(faces):,} surface triangles, {len(tets):,} tets; "
          f"{int((shape < 1e-5).sum())} under 1e-5, {int((shape < 1e-4).sum())} under 1e-4")
    bad = np.flatnonzero(shape < 1e-5)
    if len(bad):
        cen = nodes[tets[bad]].mean(axis=1)
        key = np.floor(cen / 10.0).astype(int)
        cells, counts = np.unique(key, axis=0, return_counts=True)
        top = np.argsort(-counts)[:15]
        print("where the tets under 1e-5 bunch (10 mm cells: their lower corner, the count):")
        for j in top:
            print(f"  ({cells[j][0] * 10}, {cells[j][1] * 10}, {cells[j][2] * 10}): {counts[j]}")
        zs = np.round(cen[:, 2]).astype(int)
        zv, zc = np.unique(zs, return_counts=True)
        print("  by height (mm: count): " + ", ".join(f"{a}: {b}" for a, b in zip(zv, zc, strict=True) if b > 200))
    for i in order:
        c = nodes[tets[i]].mean(axis=0)
        near = []
        for b in lay["bearings"]:
            r = math.hypot(c[0] - b["axis"][0], c[1] - b["axis"][1])
            if r < b["D"] / 2 + 60:
                near.append(f"{b['shaft']} {b['side']} r {r:.0f} (D/2 {b['D'] / 2:g}), z {b['z'][0]:.0f}..{b['z'][1]:.0f}")
        for m in lay["mounts"]:
            r = math.hypot(c[0] - m["centre"][0], c[1] - m["centre"][1])
            if r < 60:
                near.append(f"{m['name']} r {r:.0f}")
        for bc in lay["bolts"]:
            r = math.hypot(c[0] - bc[0], c[1] - bc[1])
            if r < 20:
                near.append(f"a bolt r {r:.0f}")
        on_surface = bool(np.isin(tets[i], np.unique(faces)).sum() >= 3)
        print(f"  shape {shape[i]:.2e} at ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f}){' on the surface' if on_surface else ''}: "
              f"{'; '.join(near) or 'nothing of the layout near'}")


if __name__ == "__main__":
    main()
