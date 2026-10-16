"""What a drawn half's surface holds near a point (LOP-34; a prototype): `rim_probe.py <design>
<half> <x,y,z> [radius mm] [--folder=<dir>]` lists the vertices within the radius, by height, with
their distance from the nearest mount's axis: where two faces lie nearly on one plane, or a sliver
stands between two cuts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "rib_housing"


def main() -> None:
    from zenryx.domains.gearbox.housing import mesh as mr

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", OUT))
    design, half = args[0], args[1]
    p = np.array([float(v) for v in args[2].split(",")])
    rad = float(args[3]) if len(args) > 3 else 4.0
    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    tm = mr.to_trimesh(mr.load(folder / info["files"][half])) if not hasattr(mr.load(folder / info["files"][half]), "vertices") else mr.load(folder / info["files"][half])
    v = np.asarray(tm.vertices)
    f = np.asarray(tm.faces)
    near = np.linalg.norm(v - p, axis=1) < rad
    m = min(info["mounts_layout"], key=lambda mt: np.hypot(p[0] - mt["centre"][0], p[1] - mt["centre"][1]))
    r = np.hypot(v[near, 0] - m["centre"][0], v[near, 1] - m["centre"][1])
    z = v[near, 2]
    print(f"{design} {half}: {near.sum()} vertices within {rad:g} mm of {p}; nearest mount {m['name']}")
    levels, counts = np.unique(np.round(z, 2), return_counts=True)
    for lv, c in zip(levels, counts, strict=True):
        rr = r[np.round(z, 2) == lv]
        print(f"  z {lv:8.2f}: {c:4d} vertices, r {rr.min():.2f}..{rr.max():.2f}")
    tri = near[f].any(axis=1)
    e = v[f[tri]]
    area = 0.5 * np.linalg.norm(np.cross(e[:, 1] - e[:, 0], e[:, 2] - e[:, 0]), axis=1)
    edges = np.stack([np.linalg.norm(e[:, i] - e[:, (i + 1) % 3], axis=1) for i in range(3)], axis=1)
    thin = 2 * area / np.maximum(edges.max(axis=1), 1e-12)  # each triangle's height on its longest edge
    print(f"  {tri.sum()} triangles; the thinnest heights (mm): {np.round(np.sort(thin)[:8], 4)}")


if __name__ == "__main__":
    main()
