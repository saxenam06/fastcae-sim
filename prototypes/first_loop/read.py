"""PROTOTYPE (LOP-4) - not product code: read a topology-optimisation result into rib candidates.

The interpretation tool of the topology review (docs/research/2026-10-09-housing-topology-
optimisation-practice.md, §3-4): it proposes, the reader (an agent, or here the loop) chooses.

- **The height map:** on each end face, how tall the optimisation's material stands at each point
  (the density summed along z outwards from the face, in mm).
- **The candidates:** straight paths on each face between the bearing bosses and the mounts there,
  and radial paths from each boss to the housing's rim every 15 degrees.
- **The score:** a candidate's mean material height along its path; its height, the 75th
  percentile of the material along it (10-40 mm); its thickness the process's rib (6 mm).
- **The selection:** the best-scoring candidates that do not overlap one another, until the
  ribs' metal reaches the budget.

Run: uv run python prototypes/first_loop/read.py <topo_stem> [budget_kg]
     writes data/first_loop/<topo_stem>_read.json and _read.png
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "first_loop"
THICKNESS = 6.0  # mm: a sand-cast rib, above the contract's 4 mm least wall
DENSITY = 2.6e-6  # kg/mm³


def density_grid(stem: str):
    d = np.load(OUT / f"{stem}.npz")
    n = d["n"]
    grid = np.zeros(tuple(n))
    ijk = d["ijk"]
    frozen = d["frozen"]
    grid[tuple(ijk[frozen].T)] = np.nan  # the shell itself
    free = d["free_e"]
    grid[tuple(ijk[free].T)] = d["phys"]
    return grid, d["lo"], float(d["h"])


def height_map(grid, lo, h, z_face: float, outward: int, reach: float = 45.0):
    """How tall the optimisation's material stands on a face: the density summed outwards (mm)."""
    k0 = int(round((z_face - lo[2]) / h))
    steps = int(reach / h)
    layers = []
    for s in range(1, steps + 1):
        k = k0 + outward * s
        if 0 <= k < grid.shape[2]:
            layers.append(np.nan_to_num(grid[:, :, k], nan=0.0))
    return h * np.sum(layers, axis=0) if layers else np.zeros(grid.shape[:2])


def sample(height, lo, h, a, b, count=40):
    xs = np.linspace(a[0], b[0], count)
    ys = np.linspace(a[1], b[1], count)
    i = np.clip(((xs - lo[0]) / h).astype(int), 0, height.shape[0] - 1)
    j = np.clip(((ys - lo[1]) / h).astype(int), 0, height.shape[1] - 1)
    return height[i, j]


def rim_point(outline, centre, angle):
    """Where a ray from `centre` at `angle` leaves the outline (the farthest crossing)."""
    ux, uy = math.cos(angle), math.sin(angle)
    best = None
    pts = outline + outline[:1]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
        ex, ey = x2 - x1, y2 - y1
        den = ux * ey - uy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - centre[0]) * ey - (y1 - centre[1]) * ex) / den
        s = ((x1 - centre[0]) * uy - (y1 - centre[1]) * ux) / den
        if t > 0 and 0 <= s <= 1 and (best is None or t > best):
            best = t
    return None if best is None else (centre[0] + ux * best, centre[1] + uy * best)


def overlaps(r1, r2, gap: float = 14.0) -> bool:
    """Two candidates on one face run too close: parallel-ish and near along most of their length."""
    if r1["face"] != r2["face"]:
        return False
    p = np.linspace(0, 1, 12)
    a1, b1 = np.array(r1["a"]), np.array(r1["b"])
    a2, b2 = np.array(r2["a"]), np.array(r2["b"])
    pts1 = a1[None, :] + p[:, None] * (b1 - a1)[None, :]
    seg = b2 - a2
    t = np.clip(((pts1 - a2) @ seg) / max(seg @ seg, 1e-9), 0, 1)
    near = np.linalg.norm(pts1 - (a2 + t[:, None] * seg), axis=1)
    return float((near < gap).mean()) > 0.4


def read(stem: str, budget_kg: float = 1.0) -> dict:
    grid, lo, h = density_grid(stem)
    shell = json.loads((OUT / "shell.json").read_text(encoding="utf-8"))
    outline = [tuple(p) for p in shell["outer_outline"]]
    z_lo, z_hi = shell["z"]["lo"], shell["z"]["hi"]
    faces = {"+z": (z_hi, +1), "-z": (z_lo, -1)}
    maps = {f: height_map(grid, lo, h, z, out) for f, (z, out) in faces.items()}
    candidates = []
    for face, height in maps.items():
        anchors = [tuple(b["axis"]) for b in shell["bearings"] if b["side"] == face]
        if face == "-z":
            anchors += [tuple(m["centre"]) for m in shell["mounts"]]
        for i, a in enumerate(anchors):
            for b in anchors[i + 1 :]:
                candidates.append({"face": face, "a": a, "b": b, "kind": "between"})
        for a in [tuple(b["axis"]) for b in shell["bearings"] if b["side"] == face]:
            for k in range(24):
                rim = rim_point(outline, a, 2 * math.pi * k / 24)
                if rim:
                    candidates.append({"face": face, "a": a, "b": rim, "kind": "radial"})
    for c in candidates:
        values = sample(maps[c["face"]], lo, h, c["a"], c["b"])
        c["score"] = float(values.mean())
        c["height"] = float(np.clip(np.percentile(values, 75), 10.0, 40.0))
        c["length"] = math.dist(c["a"], c["b"])
        c["thickness"] = THICKNESS
        c["kg"] = c["length"] * c["height"] * THICKNESS * DENSITY
    candidates.sort(key=lambda c: -c["score"])
    chosen, used = [], 0.0
    for c in candidates:
        if c["score"] < 3.0:
            break
        if any(overlaps(c, d) for d in chosen):
            continue
        if used + c["kg"] > budget_kg * 1.05:
            continue
        chosen.append(c)
        used += c["kg"]
    result = {
        "stem": stem,
        "budget_kg": budget_kg,
        "ribs_kg": used,
        "chosen": chosen,
        "candidates": len(candidates),
        "top": candidates[:12],
    }
    (OUT / f"{stem}_read.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    _picture(maps, lo, h, outline, chosen, OUT / f"{stem}_read.png", stem)
    print(f"{len(candidates)} candidates; {len(chosen)} chosen, {used:.2f} kg of ribs")
    for c in chosen:
        print(
            f"  {c['face']} {c['kind']:8s} score {c['score']:5.1f} mm, height {c['height']:4.0f} mm, {c['kg']:.3f} kg"
        )
    return result


def skeleton_ribs(stem: str, threshold: float = 6.0, tolerance: float = 6.0) -> dict:
    """The second reading: on each face, the optimisation's material taller than `threshold`
    (mm) thinned to its skeleton (scikit-image), the skeleton's branches between junctions and
    ends simplified into straight segments (Douglas-Peucker to `tolerance` mm), and a rib along
    each, as tall as the material under it (its median, 10-40 mm)."""
    from skimage.morphology import skeletonize

    grid, lo, h = density_grid(stem)
    shell = json.loads((OUT / "shell.json").read_text(encoding="utf-8"))
    z_lo, z_hi = shell["z"]["lo"], shell["z"]["hi"]
    faces = {"+z": (z_hi, +1), "-z": (z_lo, -1)}
    ribs, used = [], 0.0
    maps = {}
    for face, (z, out) in faces.items():
        height = height_map(grid, lo, h, z, out)
        maps[face] = height
        mask = height > threshold
        skel = skeletonize(mask)
        # How wide the band of material is round each skeleton point: twice its distance to the
        # band's edge. A rib takes the band's width (6-16 mm), so the reading keeps the metal.
        from scipy.ndimage import distance_transform_edt

        width_map = 2.0 * h * distance_transform_edt(mask)
        pixels = set(zip(*np.nonzero(skel), strict=True))

        def neighbours(p):
            i, j = p
            return [
                (i + di, j + dj)
                for di in (-1, 0, 1)
                for dj in (-1, 0, 1)
                if (di or dj) and (i + di, j + dj) in pixels
            ]

        nodes = {p for p in pixels if len(neighbours(p)) != 2}
        seen = set()
        paths = []
        for start in nodes:
            for nxt in neighbours(start):
                edge = frozenset((start, nxt))
                if edge in seen:
                    continue
                path = [start, nxt]
                seen.add(edge)
                while path[-1] not in nodes:
                    options = [q for q in neighbours(path[-1]) if q != path[-2]]
                    if not options:
                        break
                    seen.add(frozenset((path[-1], options[0])))
                    path.append(options[0])
                paths.append(path)
        for path in paths:
            pts = np.array([(lo[0] + h * (i + 0.5), lo[1] + h * (j + 0.5)) for i, j in path])
            for a, b in _simplify(pts, tolerance):
                if math.dist(a, b) < 2 * h:
                    continue
                values = sample(height, lo, h, a, b)
                widths = sample(width_map, lo, h, a, b)
                rib = {
                    "face": face,
                    "a": (float(a[0]), float(a[1])),
                    "b": (float(b[0]), float(b[1])),
                    "kind": "skeleton",
                    "score": float(values.mean()),
                    "height": float(np.clip(np.median(values), 10.0, 40.0)),
                    "thickness": float(np.clip(np.median(widths), THICKNESS, 16.0)),
                }
                rib["length"] = math.dist(rib["a"], rib["b"])
                rib["kg"] = rib["length"] * rib["height"] * rib["thickness"] * DENSITY
                ribs.append(rib)
                used += rib["kg"]
    result = {"stem": stem, "method": "skeleton", "ribs_kg": used, "chosen": ribs}
    (OUT / f"{stem}_skeleton.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    outline = [tuple(p) for p in shell["outer_outline"]]
    _picture(maps, lo, h, outline, ribs, OUT / f"{stem}_skeleton.png", stem + " (skeleton)")
    print(f"skeleton: {len(ribs)} ribs, {used:.2f} kg")
    return result


def _simplify(points: np.ndarray, tolerance: float) -> list[tuple[np.ndarray, np.ndarray]]:
    """Douglas-Peucker: the polyline as straight segments within `tolerance` of it."""
    if len(points) < 3:
        return [(points[0], points[-1])]
    a, b = points[0], points[-1]
    ab = b - a
    length = np.linalg.norm(ab)
    if length < 1e-9:
        dist = np.linalg.norm(points - a, axis=1)
    else:
        rel = points - a
        dist = np.abs(ab[0] * rel[:, 1] - ab[1] * rel[:, 0]) / length
    k = int(np.argmax(dist))
    if dist[k] <= tolerance:
        return [(a, b)]
    return _simplify(points[: k + 1], tolerance) + _simplify(points[k:], tolerance)


def _picture(maps, lo, h, outline, chosen, path, stem):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
    for ax, (face, height) in zip(axes, maps.items(), strict=True):
        extent = (lo[0], lo[0] + h * height.shape[0], lo[1], lo[1] + h * height.shape[1])
        im = ax.imshow(height.T, origin="lower", extent=extent, cmap="magma", vmin=0, vmax=40)
        xs, ys = zip(*(outline + outline[:1]), strict=True)
        ax.plot(xs, ys, color="white", lw=1)
        for c in chosen:
            if c["face"] == face:
                ax.plot([c["a"][0], c["b"][0]], [c["a"][1], c["b"][1]], color="cyan", lw=2.5)
        ax.set_title(f"{face} face: the optimisation's material height (mm); ribs chosen in cyan")
        ax.set_aspect("equal")
        ax.invert_yaxis()
    fig.colorbar(im, ax=axes, shrink=0.8)
    fig.suptitle(f"{stem}: read into ribs")
    fig.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 1 and args[1] == "skeleton":
        skeleton_ribs(args[0])
    else:
        read(args[0], float(args[1]) if len(args) > 1 else 1.0)
