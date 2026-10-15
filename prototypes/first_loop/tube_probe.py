"""PROTOTYPE (LOP-27) - the bearing tubes' wall thickness in row 1 (empty1) and row 4 (empty1_exact): rays out from each cover-side bearing's
axis at mid-height of its seat, every 30 degrees; the metal from the bore out to the first air."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototypes" / "first_loop"))

import trimesh  # noqa: E402

OUT = ROOT / "data" / "first_loop"
layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))


def crossings(tri, origin, direction):
    """Distances along a ray to every triangle it crosses (Moller-Trumbore, vectorised)."""
    v0, v1, v2 = tri[:, 0], tri[:, 1], tri[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    p = np.cross(direction, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = origin - v0
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = np.einsum("j,ij->i", direction, q) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
    return np.sort(t[hit])


for d in ("empty1_5.5kg", "empty1_exact_5.5kg"):
    tm = trimesh.load(str(OUT / f"{d}_cover.ply"), process=True)
    tri = tm.vertices[tm.faces]
    print(d)
    for b in layout["bearings"]:
        if b["side"] != "+z":
            continue
        zc = 0.5 * (b["z"][0] + b["z"][1])
        walls = []
        for ang in range(0, 360, 30):
            a = np.radians(ang)
            direction = np.array([np.cos(a), np.sin(a), 0.0])
            origin = np.array([b["axis"][0], b["axis"][1], zc])
            t = crossings(tri, origin, direction)
            # the first crossing is the bore (into the metal), the next the way out
            walls.append(round(float(t[1] - t[0]), 1) if len(t) >= 2 else None)
        ok = [w for w in walls if w is not None]
        print(f"   {b['shaft']:12s} bore D {b['D']:g} at z {zc:.1f}: wall out from the bore every 30 deg {walls}; median {np.median(ok):.1f} mm")
