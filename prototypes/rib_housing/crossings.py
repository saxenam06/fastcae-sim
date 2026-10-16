"""Where a drawn half's FE surface crosses itself (LOP-34; a prototype): `crossings.py <design>
<half> [<edge mm>]` coarsens the half's mesh as FE does (`mesh.coarse` to `fe.SURFACE_EDGE`) and asks
TetGen which triangles it skips as self-intersecting (`fe.tetgen_skipped`); prints their centres
and what of the layout is near each (a bore, a bolt, a mount)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "rib_housing"


def main() -> None:
    from zenryx.domains.gearbox.housing import fe
    from zenryx.domains.gearbox.housing import mesh as mr

    design, half = sys.argv[1], sys.argv[2]
    edge = float(sys.argv[3]) if len(sys.argv) > 3 else fe.SURFACE_EDGE
    info = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    raw = mr.load(OUT / info["files"][half])
    verts, faces = mr.coarse(raw, edge)
    os.chdir(tempfile.mkdtemp(dir=OUT / "fe_cwd"))
    centres = fe.tetgen_skipped(verts, faces)
    print(f"{design} {half} at {edge:g} mm: {len(faces):,} triangles, {len(centres)} skipped")
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    for c in centres[:20]:
        near = []
        for b in lay["bearings"]:
            d = np.hypot(c[0] - b["axis"][0], c[1] - b["axis"][1])
            if d < b["D"] / 2 + 30:
                near.append(f"{b['shaft']} {b['side']} bore (r {d:.0f}, D/2 {b['D'] / 2:.0f}, z {b['z'][0]:.0f}..{b['z'][1]:.0f})")
        for k, bolt in enumerate(lay["bolts"]):
            d = np.hypot(c[0] - bolt[0], c[1] - bolt[1])
            if d < 20:
                near.append(f"bolt {k + 1} (r {d:.0f})")
        for m in lay["mounts"]:
            d = np.hypot(c[0] - m["centre"][0], c[1] - m["centre"][1])
            if d < 50:
                near.append(f"{m['name']} (r {d:.0f})")
        print(f"  at ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f}), split {lay['z']['split']:.1f}: " + ("; ".join(near) or "open wall"))


if __name__ == "__main__":
    main()
