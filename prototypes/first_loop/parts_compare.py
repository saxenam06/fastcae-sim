"""PROTOTYPE (LOP-26, Refine) - what the optimiser did to production's parts: a reading's parts at their start (thin grey
outlines) against a run's optimised parts (filled, coloured by their height), each half in plan; a part under the least
height at both ends is gone (red, dashed); every node that moved an arrow from its start.

    parts_compare.py <reading> <run stem> --label <label>

Writes data/first_loop/<label>.png and prints what was kept, what went and how far the nodes moved."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parts as pm  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"


def outline(a, b, width):
    u = (b - a) / max(np.hypot(*(b - a)), 1e-9)
    n = np.array([-u[1], u[0]]) * 0.5 * width
    return [a + n, b + n, b - n, a - n]


def main(reading: str, run: str, label: str) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Wedge

    read = json.loads((OUT / f"{reading}.json").read_text(encoding="utf-8"))
    pmap = pm.PartsMap(read, np.zeros((0, 2)), np.zeros(0))
    start = pmap.params(pmap.start())
    done = json.loads((OUT / f"{run}_parts.json").read_text(encoding="utf-8"))
    least = float(read.get("least_mm") or 8.0)
    top = max(float(read.get("band_mm") or 24.0), 24.0)
    norm = colors.Normalize(0.0, top)
    cmap = matplotlib.colormaps["viridis"]
    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    summary = {}
    for ax, half in zip(axes, ("motor_side", "cover"), strict=True):
        edge = np.asarray(read["edges"][half])
        ax.plot(*np.vstack([edge, edge[:1]]).T, color="#999999", lw=0.8)
        kept = gone = 0
        polys, fills, ghost = [], [], []
        for m0, m1 in zip(start["members"], done["members"], strict=True):
            if m0["half"] != half:
                continue
            a0, b0 = np.asarray(m0["ends"][0]), np.asarray(m0["ends"][1])
            a1, b1 = np.asarray(m1["ends"][0]), np.asarray(m1["ends"][1])
            ghost.append(outline(a0, b0, m0["width"]))
            if max(m1["h"]) < least:
                gone += 1
                ax.add_patch(plt.Polygon(outline(a1, b1, m1["width"]), fill=False, ec="#d62728", ls="--", lw=1.0))
                continue
            kept += 1
            polys.append(outline(a1, b1, m1["width"]))
            fills.append(cmap(norm(0.5 * (m1["h"][0] + m1["h"][1]))))
        ax.add_collection(PolyCollection(ghost, facecolors="none", edgecolors="#bbbbbb", lw=0.6))
        ax.add_collection(PolyCollection(polys, facecolors=fills, edgecolors="none", alpha=0.95))
        for r0, r1 in zip(start["rings"], done["rings"], strict=True):
            if r0["half"] != half:
                continue
            r_in = float(r1.get("r_in") or 0.0) if r1["kind"] == "annulus" else (r1["r"] - 0.5 * r1["width"] if r1["kind"] == "band" else 0.0)
            r_out = r1["r"] + (0.5 * r1["width"] if r1["kind"] == "band" else 0.0)
            if r1["h"] < least:
                ax.add_patch(Wedge(r1["centre"], r_out, 0, 360, width=r_out - r_in, fill=False, ec="#d62728", ls="--"))
                gone += 1
            else:
                ax.add_patch(Wedge(r1["centre"], r_out, 0, 360, width=r_out - r_in, color=cmap(norm(r1["h"])), alpha=0.9, lw=0))
                kept += 1
        moves = []
        for n0, n1 in zip(start["nodes"], done["nodes"], strict=True):
            if n0["half"] != half or n0["kind"] == "fixed":
                continue
            p0, p1 = np.asarray(n0["at"]), np.asarray(n1["at"])
            d = float(np.hypot(*(p1 - p0)))
            moves.append(d)
            if d > 1.0:
                ax.annotate("", xy=p1, xytext=p0, arrowprops={"arrowstyle": "->", "color": "#ff7f0e", "lw": 0.9})
        summary[half] = {"kept": kept, "gone": gone, "node move mm, mean": round(float(np.mean(moves)), 1) if moves else 0.0,
                         "node move mm, most": round(float(np.max(moves)), 1) if moves else 0.0}  # fmt: skip
        ax.set_title(f"{label}, {half.replace('_', ' ')}: {kept} parts kept, {gone} gone (red); nodes moved {summary[half]['node move mm, mean']} mm "
                     f"on average (arrows); grey, the reading's start", fontsize=10)  # fmt: skip
        ax.set_aspect("equal")
        ax.autoscale_view()
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, shrink=0.7, label="a part's height off its base, mm (a member's mean)")
    target = OUT / f"{label}.png"
    fig.savefig(target, dpi=80, bbox_inches="tight")
    print(target)
    print(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("reading")
    ap.add_argument("run")
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    main(a.reading, a.run, a.label)
