"""An iteration's design space drawn from the last runs (LOP-24; the engineer, 11 October 20:16: the agent
draws each iteration's design space from what the last optimisation showed, looser first, sharper
after). The members that stand in at least `--min` of the runs (each half's own heights, a member a
column at least 4 mm high), closed over `--close` mm (nearby members joined into one region), grown
by `--grow` mm (the room the optimiser keeps to move them), islands under 400 mm² dropped; then cut
into regions by the nearest hard point of the half (each bore, each mount on the motor side), so the
fill can be read region by region. Each region's outline and holes in plan (mm), simplified to
`--tolerance` mm, into data/first_loop/<label>.json (`topo_free.py --space`), with its picture.

    space_from_runs.py <label> --runs <run> [<run> ...] [--min 1] [--grow 12] [--close 16] [--tolerance 1.5]"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from skimage.measure import approximate_polygon, find_contours  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0  # mm
ISLAND = 400.0  # mm²
HALVES = (("motor_side", "-z"), ("cover", "+z"))


def disc(r_mm: float) -> np.ndarray:
    r = int(np.ceil(r_mm))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    return (xx**2 + yy**2) <= r_mm**2


def polygons_of(mask: np.ndarray, x0: float, y0: float, tol: float) -> list[dict]:
    """The mask's outlines (each with its holes) in plan mm, from its contours on the 1 mm grid."""
    contours = [c for c in find_contours(np.pad(mask, 1).astype(float), 0.5) if len(c) >= 8]
    rings = []
    for c in contours:
        c = approximate_polygon(c, tolerance=tol)
        pts = np.column_stack([x0 + c[:, 0] - 1 + 0.5, y0 + c[:, 1] - 1 + 0.5])
        area = 0.5 * float(np.sum(pts[:-1, 0] * pts[1:, 1] - pts[1:, 0] * pts[:-1, 1]))
        if abs(area) >= 1.0:
            rings.append(pts)
    from matplotlib.path import Path as MPath

    paths = [MPath(r) for r in rings]
    depth = [sum(paths[j].contains_point(r[0]) for j in range(len(rings)) if j != i) for i, r in enumerate(rings)]
    out = []
    for i, r in enumerate(rings):
        if depth[i] % 2 == 0:
            holes = [rings[j].tolist() for j in range(len(rings)) if depth[j] == depth[i] + 1 and paths[i].contains_point(rings[j][0])]
            out.append({"outline": r.tolist(), "holes": holes})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("label")
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--min", type=int, default=1, help="a member in at least this many of the runs")
    ap.add_argument("--grow", type=float, default=12.0, help="mm the members are grown by")
    ap.add_argument("--close", type=float, default=16.0, help="mm over which nearby members join into one region")
    ap.add_argument("--tolerance", type=float, default=1.5, help="mm the outlines are simplified to")
    a = ap.parse_args()

    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    heights = [shh.column_heights(r) for r in a.runs]
    h, lo, n = heights[0]["h"], heights[0]["lo"], heights[0]["n"]
    x0, y0 = float(lo[0]), float(lo[1])
    regions_out, pics = {}, {}
    stats = []
    for half, side in HALVES:
        stack = np.stack([ndi.zoom(c[half], h, order=3) >= MEMBER for c in heights])
        keep = stack.sum(axis=0) >= a.min
        if a.close > 0:
            keep = ndi.binary_closing(keep, structure=disc(a.close / 2.0))
        if a.grow > 0:
            keep = ndi.binary_dilation(keep, structure=disc(a.grow))
        lab, nl = ndi.label(keep)
        sizes = ndi.sum(keep, lab, range(1, nl + 1))
        keep &= np.isin(lab, 1 + np.flatnonzero(sizes >= ISLAND))
        # the hard points of the half: each bore of this side, and each mount on the motor side
        points = [(f"{b['shaft']} bore", np.asarray(b["axis"], float)) for b in lay["bearings"] if b["side"] == side]
        if half == "motor_side":
            points += [(m["name"], np.asarray(m["centre"], float)) for m in lay["mounts"]]
        X, Y = np.meshgrid(x0 + np.arange(keep.shape[0]) + 0.5, y0 + np.arange(keep.shape[1]) + 0.5, indexing="ij")
        dist = np.stack([np.hypot(X - p[0], Y - p[1]) for _, p in points])
        owner = np.argmin(dist, axis=0)
        regs = []
        for k, (name, _) in enumerate(points):
            part = keep & (owner == k)
            if part.sum() < ISLAND:
                continue
            for j, poly in enumerate(polygons_of(part, x0, y0, a.tolerance)):
                regs.append({"name": f"near the {name}" + (f" ({j + 1})" if j else ""), **poly})
            stats.append((half, name, float(part.sum())))
        regions_out[half] = regs
        pics[half] = (keep, owner, points)
    rec = {"label": a.label, "from_runs": a.runs, "min": a.min, "grow_mm": a.grow, "close_mm": a.close, "tolerance_mm": a.tolerance,
           "halves": regions_out}  # fmt: skip
    path = OUT / f"{a.label}.json"
    path.write_text(json.dumps(rec, indent=1), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    ext = [x0, x0 + pics["cover"][0].shape[0], y0, y0 + pics["cover"][0].shape[1]]
    for ax, (half, side) in zip(axes, HALVES):
        keep, owner, points = pics[half]
        shown = np.where(keep, owner.astype(float), np.nan)
        ax.imshow(shown.T, origin="lower", extent=ext, cmap="tab10", vmin=0, vmax=9, alpha=0.45)
        for reg in regions_out[half]:
            ax.add_patch(Polygon(np.asarray(reg["outline"]), closed=True, fill=False, ec="k", lw=1.0))
            for hole in reg["holes"]:
                ax.add_patch(Polygon(np.asarray(hole), closed=True, fill=False, ec="k", lw=0.6, ls="--"))
        for b in lay["bearings"]:
            if b["side"] == side:
                ax.add_patch(Circle(b["axis"], b["D"] / 2, fill=True, fc="white", ec="k"))
        for bx, by in lay["bolts"]:
            ax.add_patch(Circle((bx, by), 10.0, fill=False, ec="#666", lw=0.6))
        if half == "motor_side":
            for m in lay["mounts"]:
                ax.add_patch(Circle(m["centre"], 18.0, fc="#444", ec="k"))
        for name, p in points:
            ax.text(p[0], p[1], name, fontsize=8, ha="center", va="center", color="k")
        ax.set_aspect("equal")
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        ax.set_title(f"{half.replace('_', ' ')}: {len(regions_out[half])} regions", fontsize=11)
    fig.suptitle(f"The design space {a.label}: members in at least {a.min} of {len(a.runs)} runs, closed over {a.close:g} mm, "
                 f"grown {a.grow:g} mm, cut by the nearest bore or mount", fontsize=11)  # fmt: skip
    pic = OUT / f"{a.label}.png"
    fig.savefig(pic, dpi=100)
    print(path)
    print(pic)
    for half, name, area in stats:
        print(f"  {half}: near the {name}: {area / 100:.0f} cm² in plan")


if __name__ == "__main__":
    main()
