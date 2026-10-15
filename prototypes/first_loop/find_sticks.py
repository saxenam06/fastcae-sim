"""PROTOTYPE (LOP-30) - Thin tall sticks in a drawn half: cut it across the pull at several heights and list each small closed section (under
`--most` mm² of area), where it stands, at which heights, with the nearest bolt and mount.

    find_sticks.py <design> <half> [--most 60]
"""

import json
import sys
from pathlib import Path

import numpy as np
import trimesh

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
design, half = sys.argv[1], sys.argv[2]
most = float(sys.argv[sys.argv.index("--most") + 1]) if "--most" in sys.argv else 60.0
lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
m = trimesh.load(OUT / f"{design}_{half}.ply")
z0, z1 = m.bounds[0, 2], m.bounds[1, 2]
split = float(lay["z"]["split"])
bolts = np.asarray([b[:2] for b in lay["bolts"]], float)
found = {}
for z in np.arange(z0 + 2.0, z1 - 1.0, 2.0):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        continue
    for poly in sec.to_planar()[0].polygons_closed if False else []:
        pass
    for ent in sec.discrete:
        if len(ent) < 4:
            continue
        x, y = ent[:, 0], ent[:, 1]
        area = 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
        if area < most:
            c = (round(float(x.mean()) / 4) * 4, round(float(y.mean()) / 4) * 4)
            found.setdefault(c, []).append((float(z), float(area)))
for c, rows in sorted(found.items(), key=lambda kv: -len(kv[1])):
    if len(rows) < 4:
        continue
    zs = [r[0] for r in rows]
    nb = np.hypot(bolts[:, 0] - c[0], bolts[:, 1] - c[1])
    mm = min(((mt["name"], float(np.hypot(mt["centre"][0] - c[0], mt["centre"][1] - c[1]))) for mt in lay["mounts"]), key=lambda v: v[1])
    print(f"{half} at ({c[0]}, {c[1]}): small sections at {len(rows)} heights, |z - split| {abs(min(zs) - split):.0f}-{abs(max(zs) - split):.0f} mm, "
          f"area {min(r[1] for r in rows):.0f}-{max(r[1] for r in rows):.0f} mm2; nearest bolt {nb.min():.0f} mm, {mm[0]} {mm[1]:.0f} mm")
