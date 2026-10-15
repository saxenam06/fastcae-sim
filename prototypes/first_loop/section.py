"""PROTOTYPE (LOP) - a design's CAD cut across the shafts, so a member's height off the wall and its
thickness can be read. Each section is drawn on a millimetre grid: the metal filled, the inside's
edge dark, and the outer edge coloured by how deep the metal is there: its distance, in the
section, to the inside, which is the contract's (each part's room, as `topo_free.build_free`'s cup
takes it, in the half from its far end to the split). The wall alone reads its 4 mm; a member
standing off it reads the wall and its height. The deepest places are labelled. Over an end wall
(a room that ends below the cut) the depth is in the plan only, not through the end wall.

Run: .venv/Scripts/python.exe prototypes/first_loop/section.py <design> <half> <z> [<z> ...]
     [--box x0 x1 y0 y1] [--side]
     (half: cover or motor_side; z in mm, the contract's frame; --box zooms every section to a
     window of the plan; --side adds the half seen from +x, y up, with the cuts marked)
Reads data/first_loop/<design>.json and <design>_<half>.brep; writes
data/first_loop/section_<design>_<half>.png and prints each section's deepest places.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from castable import OUT, triangles  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

LABEL_OVER = 3.0  # mm past the wall: a place this much deeper is labelled
LABEL_APART = 25.0  # mm between two labels on the same edge


def rooms() -> list[tuple[float, float, float, float, float]]:
    """Every part's room as `topo_free.build_free` takes it: (axis x, axis y, radius, z from, z to)."""
    spec, _ = load_and_validate(topo.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial = value_in(gaps.min_radial_clearance, "mm")
    axial = value_in(gaps.min_axial_clearance, "mm")
    out = []
    for stack in chain.layout.shafts:
        (ax, ay), shaft = stack.axis, stack.shaft
        least = []
        for p in stack.parts:
            if p.kind in ("gear", "carrier"):
                out.append((ax, ay, p.diameter / 2 + radial, p.z_min - axial, p.z_max + axial))
            elif p.kind == "bearing":
                out.append((ax, ay, p.diameter / 2, p.z_min, p.z_max))
                choice = chain.bearings.get((shaft, p.name.rsplit(" ", 1)[-1]))
                least.append(choice.bearing.d if choice else 0.5 * p.diameter)
        out.append((ax, ay, min(least) / 2, *stack.ends))
    return out


def inside_depth(points: np.ndarray, z: float, half: str, split: float, parts) -> np.ndarray:
    """Each plan point's distance to the half's inside at height z: the union of the rooms whose cup
    reaches z (in the cover, a room ending above z; in the motor side, one starting below it)."""
    here = [(x, y, r) for x, y, r, z0, z1 in parts if (z < z1 if half == "cover" else z > z0)]
    if not here:
        return np.full(len(points), np.nan)
    c = np.asarray(here)
    d = np.hypot(points[:, None, 0] - c[None, :, 0], points[:, None, 1] - c[None, :, 1]) - c[None, :, 2]
    return d.min(axis=1)


def loops_at(poly: pv.PolyData, z: float) -> list[np.ndarray]:
    """The section's closed loops at height z, each an (n, 2) array of plan points."""
    cut = poly.slice(normal=(0.0, 0.0, 1.0), origin=(0.0, 0.0, z))
    if cut.n_points == 0:
        return []
    cut = cut.strip(join=True)
    out, lines, i = [], cut.lines, 0
    while i < len(lines):
        n = lines[i]
        ids = lines[i + 1 : i + 1 + n]
        i += n + 1
        pts = cut.points[ids][:, :2]
        if len(pts) >= 4:
            out.append(pts)
    return out


def area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def depth_of(loops: list[np.ndarray]) -> list[int]:
    """Each loop's nesting depth: how many other loops hold it. Even: metal's outer edge; odd: a hole's."""
    paths = [MPath(p) for p in loops]
    return [sum(paths[j].contains_point(loops[i][0]) for j in range(len(loops)) if j != i) for i in range(len(loops))]


def side_view(ax, poly: pv.PolyData, cuts: list[float], half: str) -> None:
    """The half seen from +x with y up, shaded from the eye, the cover's +z to the left (as the UI's
    camera looked on 11 October 00:01); the cuts as lines."""
    faces = poly.faces.reshape(-1, 4)[:, 1:]
    tri = poly.points[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    front = n[:, 0] > 0.0
    tri, shade = tri[front], n[front, 0]
    order = np.argsort(tri[:, :, 0].mean(axis=1))  # far first: the painter's order
    from matplotlib.collections import PolyCollection

    grey = (0.35 + 0.6 * shade[order])[:, None] * np.array([0.62, 0.74, 0.66])[None, :]
    ax.add_collection(PolyCollection(tri[order][:, :, [2, 1]], facecolors=grey, edgecolors="none"))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.invert_xaxis()
    for z in cuts:
        ax.axvline(z, color="#b91c1c", lw=1.0)
        ax.text(z, ax.get_ylim()[1], f" z {z:g}", color="#b91c1c", fontsize=8, rotation=90, va="top")
    ax.minorticks_on()
    ax.grid(which="major", color="#9ca3af", lw=0.5)
    ax.set_title(f"{half.replace('_', ' ')} seen from +x (y up, +z to the left)")
    ax.set_xlabel("z, mm")
    ax.set_ylabel("y, mm")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("half", choices=("cover", "motor_side"))
    ap.add_argument("z", type=float, nargs="+")
    ap.add_argument("--box", type=float, nargs=4, default=None)
    ap.add_argument("--side", action="store_true")
    a = ap.parse_args()
    info = json.loads((OUT / f"{a.design}.json").read_text(encoding="utf-8"))
    wall = float(info.get("skin", {}).get("wall_mm") or info.get("hypothesis", {}).get("wall_mm") or 4.0)
    split = float(info["z"]["split"])
    parts = rooms()
    shape = cq.Shape.importBrep(str(OUT / f"{a.design}_{a.half}.brep"))
    points, tris, _, _ = triangles(shape, info.get("faces", {}).get(a.half, {}))
    poly = pv.PolyData(points, np.hstack([np.full((len(tris), 1), 3), tris]).ravel()).clean()

    panels = len(a.z) + (1 if a.side else 0)
    cols = min(panels, 3)
    rows = int(np.ceil(panels / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(7.2 * cols, 6.8 * rows), squeeze=False)
    norm = plt.Normalize(0.0, 40.0)
    flat = list(axes.ravel())
    if a.side:
        side_view(flat.pop(0), poly, a.z, a.half)
    for ax, z in zip(flat, a.z, strict=False):
        loops = loops_at(poly, z)
        if not loops:
            ax.set_title(f"z = {z:g} mm: no metal")
            continue
        nest = depth_of(loops)
        # One compound path, every hole turned against its outer edge, so the fill leaves holes open.
        verts, codes = [], []
        for p, d in zip(loops, nest, strict=True):
            q = p if (area(p) > 0) == (d % 2 == 0) else p[::-1]
            verts.extend(q.tolist() + [q[0].tolist()])
            codes.extend([MPath.MOVETO] + [MPath.LINETO] * (len(q) - 1) + [MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(verts, codes), facecolor="#d9dde3", edgecolor="none"))
        for p, d in zip(loops, nest, strict=True):
            if d % 2 == 1:
                ax.plot(*np.vstack([p, p[:1]]).T, color="#1f2937", lw=1.1)
        # The contract's inside at this height, dashed: the depth is measured to it.
        here = [(x, y, r) for x, y, r, z0, z1 in parts if (z < z1 if a.half == "cover" else z > z0)]
        t = np.linspace(0.0, 2.0 * np.pi, 181)
        for x, y, r in here:
            ax.plot(x + r * np.cos(t), y + r * np.sin(t), color="#2563eb", lw=0.6, ls="--")
        print(f"z = {z:g} mm: {len(loops)} loops; the inside: {len(here)} rooms")
        for p, d in zip(loops, nest, strict=True):
            if d % 2 == 1:
                continue
            ring = np.vstack([p, p[:1]])
            deep = inside_depth(ring, z, a.half, split, parts)
            seg = np.stack([ring[:-1], ring[1:]], axis=1)
            lc = LineCollection(seg, cmap="viridis", norm=norm, linewidths=2.6)
            lc.set_array(0.5 * (deep[:-1] + deep[1:]))
            ax.add_collection(lc)
            # Label the deepest places: local maxima at least LABEL_OVER past the wall, LABEL_APART apart.
            order = np.argsort(-deep[:-1])
            placed: list[np.ndarray] = []
            for k in order:
                if not np.isfinite(deep[k]) or deep[k] < wall + LABEL_OVER:
                    break
                if any(np.linalg.norm(ring[k] - q) < LABEL_APART for q in placed):
                    continue
                if a.box and not (a.box[0] <= ring[k, 0] <= a.box[1] and a.box[2] <= ring[k, 1] <= a.box[3]):
                    continue
                placed.append(ring[k])
                ax.plot(*ring[k], "o", color="#b91c1c", ms=4)
                ax.annotate(f"{deep[k]:.1f}", ring[k], xytext=(4, 4), textcoords="offset points", fontsize=8, color="#b91c1c")
                print(f"   deep {deep[k]:5.1f} mm at x {ring[k, 0]:7.1f}, y {ring[k, 1]:7.1f}  (off the wall {deep[k] - wall:5.1f} mm)")
                if len(placed) >= 14:
                    break
        ax.set_aspect("equal")
        if a.box:
            ax.set_xlim(a.box[0], a.box[1])
            ax.set_ylim(a.box[2], a.box[3])
        else:
            ax.autoscale_view()
        ax.minorticks_on()
        ax.grid(which="major", color="#9ca3af", lw=0.6)
        ax.grid(which="minor", color="#e5e7eb", lw=0.4)
        ax.set_title(f"{a.half.replace('_', ' ')}, cut at z = {z:g} mm (the split at {info['z']['split']:.2f})")
        ax.set_xlabel("x, mm")
        ax.set_ylabel("y, mm")
    for ax in flat[len(a.z) :]:
        ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    fig.colorbar(sm, ax=axes.ravel().tolist(), shrink=0.6, label=f"metal's depth off the inside, mm (the wall: {wall:g})")
    fig.suptitle(f"{a.design}: sections across the shafts; red: the deepest places, mm off the inside", fontsize=11)
    path = OUT / f"section_{a.design}_{a.half}.png"
    fig.savefig(path, dpi=110)
    print("wrote", path)


if __name__ == "__main__":
    main()
