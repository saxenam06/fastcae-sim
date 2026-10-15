"""PROTOTYPE (LOP-30) - where a drawn design's thickest sections are (castability's lump measure, a gate of the engineer's
reviews, 14 October 23:13: "no section over 16 mm outside the bearings' bosses and the mounts' eyes"). Each half filled on
a 1 mm grid; at each metal cell the largest ball inside the metal (twice its distance to the air); the bearings' bosses
and the mounts' eyes left out in plan. Prints each half's largest section and its places over the limit, grouped, each
with what lies there (a bolt's boss, at the split) and how many mm³ are that thick.

    lump_where.py <design> [--limit 16]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "first_loop"


def main() -> None:
    import trimesh
    from scipy.ndimage import distance_transform_edt, label

    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--limit", type=float, default=16.0)
    a = ap.parse_args()
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    z_split = float(lay["z"]["split"])
    bolts = np.asarray(lay["bolts"], float)
    out = {}
    for half in ("motor_side", "cover"):
        m = trimesh.load(OUT / f"{a.design}_{half}.ply")
        lo, hi = m.bounds
        g = 1.0
        xs, ys, zs = (np.arange(lo[i] + 0.5 * g, hi[i], g) for i in range(3))
        pts = m.voxelized(pitch=g).fill().points
        metal = np.zeros((len(xs), len(ys), len(zs)), bool)
        idx = np.floor((pts - lo) / g).astype(int)
        ok = np.all((idx >= 0) & (idx < np.array(metal.shape)), axis=1)
        metal[tuple(idx[ok].T)] = True
        ball = 2.0 * distance_transform_edt(metal) * g
        gx, gy = np.meshgrid(xs, ys, indexing="ij")
        own = np.zeros(gx.shape, bool)
        for b in lay["bearings"]:
            own |= np.hypot(gx - b["axis"][0], gy - b["axis"][1]) <= 0.625 * float(b["D"]) + 5.0
        for m_ in lay["mounts"]:
            own |= np.hypot(gx - m_["centre"][0], gy - m_["centre"][1]) <= 0.5 * float(lay["settings"]["mount_diameter"]) + 4.0
        mb = np.where(own[:, :, None], 0.0, ball)
        thick = mb > a.limit
        lab, n = label(thick)
        out[half] = {"largest_mm": float(mb.max()), "over_mm3": int(thick.sum()), "places": int(n)}
        print(f"{a.design} {half}: the largest section outside the bosses {mb.max():.1f} mm; {int(thick.sum()):,} mm3 over {a.limit:g} mm in {n} places")
        for p in sorted(range(1, n + 1), key=lambda p: -float(mb[lab == p].max()))[:8]:
            cells = np.argwhere(lab == p)
            c = np.array([xs[cells[:, 0]].mean(), ys[cells[:, 1]].mean(), zs[cells[:, 2]].mean()])
            d_bolt = float(np.min(np.hypot(*(bolts[:, :2] - c[:2]).T)))
            dz = c[2] - z_split
            where = ("by a bolt's boss" if d_bolt < 18 else "") + (", at the split" if abs(dz) < 12 else "")
            print(f"   {len(cells):6,} mm3 up to {mb[lab == p].max():.1f} mm, at ({c[0]:.0f}, {c[1]:.0f}), {dz:+.0f} mm from the split{(' ' + where) if where else ''}")
    (OUT / f"lumps_{a.design}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
