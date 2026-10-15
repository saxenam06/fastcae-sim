"""PROTOTYPE (LOP-12) - the style presets side by side: each design assembled, as the trade's
pictures show a housing, with what it is (its preset), its mass, whether it can be cast, and what
the FE says of it.

Run: uv run python prototypes/first_loop/gallery.py <stem> [<stem> ...]
Reads data/first_loop/<stem>.json and _<half>.brep, castable_<stem>.json and grades.json; writes
data/first_loop/gallery.png.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq
import pyvista as pv

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from look import EDGE, METAL, edges, surface  # noqa: E402

ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"


def fresh(path: Path, stem: str) -> bool:
    """A result made after its design's latest build (an older one judged a CAD since replaced)."""
    return path.exists() and path.stat().st_mtime >= (OUT / f"{stem}.json").stat().st_mtime


def caption(stem: str) -> str:
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    words = [f"{stem}: {info['mass_kg']['total']:.2f} kg"]
    cast = OUT / f"castable_{stem}.json"
    if fresh(cast, stem):
        halves = json.loads(cast.read_text(encoding="utf-8"))["halves"]
        under = sum(h["undercut_cm2"] for h in halves)
        voids = sum(h["closed_voids"] for h in halves)
        words.append(f"undercut {under:.1f} cm2, {voids} closed voids")
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))} if (OUT / "grades.json").exists() else {}
    g = grades.get(stem) if fresh(OUT / f"fe_{stem}.json", stem) else None
    if g is None:
        log = OUT / f"fe_{stem}.log"
        failed = fresh(log, stem) and "did not refine" in log.read_text(encoding="utf-8", errors="replace")
        words.append("FE failed: the factor did not refine" if failed else "FE: not yet run on this build")
    else:
        lines = g["lines"]
        words.append(
            f"{lines['displacement, peak drive']['value_um']:.0f}/{lines['displacement, peak reverse']['value_um']:.0f} um; "
            f"misalignment {lines['misalignment (worst seat against its line)']['ratio']:.2f}x; "
            f"mode {g.get('first_mode_hz') or 0:.0f} Hz"
        )
    return "\n".join(words)


VIEWS = {
    # turned three-quarter views, alternating sides (gallery.png)
    "turned": [(0.75, -0.35, 0.55), (-0.7, 0.45, -0.55)],
    # straight down the shafts at the cover, then at the motor face: the silhouettes (gallery_cover.png, gallery_motor.png)
    "cover": [(0.0, 0.0, 1.0)],
    "motor": [(0.0, 0.0, -1.0)],
}


def main(stems: list[str], view: str = "turned") -> None:
    cols = 3
    rows = math.ceil(len(stems) / cols)
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(rows, cols), window_size=(600 * cols, 560 * rows), off_screen=True)
    for k, stem in enumerate(stems):
        plotter.subplot(k // cols, k % cols)
        for half in ("motor_side", "cover"):
            shape = cq.Shape.importBrep(str(OUT / f"{stem}_{half}.brep"))
            plotter.add_mesh(surface(shape), color=METAL, smooth_shading=True, specular=0.35, specular_power=20, ambient=0.25, diffuse=0.75)
            plotter.add_mesh(edges(shape), color=EDGE, line_width=1.0)
        views = VIEWS[view]
        plotter.view_vector(views[k % len(views)], viewup=(0.0, -1.0, 0.0))
        plotter.add_text(caption(stem), font_size=9)
    name = "gallery.png" if view == "turned" else f"gallery_{view}.png"
    plotter.screenshot(str(OUT / name))
    plotter.close()
    print(name)


if __name__ == "__main__":
    # gallery.py [--cover | --motor] <stem> [<stem> ...]
    args = sys.argv[1:]
    chosen = next((a[2:] for a in args if a in ("--cover", "--motor")), "turned")
    main([a for a in args if not a.startswith("--")], chosen)
