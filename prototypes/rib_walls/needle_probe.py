"""A coarsened half's shortest edges and thinnest triangles (LOP-34, the restart; a prototype):
`needle_probe.py <design> <half> [<edge mm>] [--near=x,y,z] [--folder=<dir>]` coarsens the half as FE
does (`mesh.coarse`) and prints its shortest edges and its triangles of least height (2 area over
the longest edge), with their places, nearest first to `--near` when given."""

from __future__ import annotations

import json
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
    v, f = mr.coarse(raw, edge, keep_near=np.zeros((0, 3)))
    v, f = np.asarray(v, float), np.asarray(f, np.int64)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    length = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    longest = np.max(np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1),
                               np.linalg.norm(a - c, axis=1)]), axis=0)
    height = 2 * area / np.maximum(longest, 1e-12)
    print(f"{design} {half} at {edge:g} mm: {len(f):,} triangles; edges under 0.1 mm: {int((length < 0.1).sum())}, "
          f"under 0.5: {int((length < 0.5).sum())}; triangles under 0.05 mm high: {int((height < 0.05).sum())}, "
          f"under 0.2: {int((height < 0.2).sum())}")
    near = np.array([float(t) for t in opt["near"].split(",")]) if "near" in opt else None
    for name, vals, where in (("edge", length, 0.5 * (v[e[:, 0]] + v[e[:, 1]])), ("triangle height", height, (a + b + c) / 3)):
        idx = np.argsort(vals)[:400]
        if near is not None:
            idx = idx[np.argsort(np.linalg.norm(where[idx] - near, axis=1))]
        for i in idx[:10]:
            d = "" if near is None else f", {np.linalg.norm(where[i] - near):.1f} mm from the point"
            print(f"  {name} {vals[i]:.4f} mm at ({where[i][0]:.1f}, {where[i][1]:.1f}, {where[i][2]:.1f}){d}")


if __name__ == "__main__":
    main()
