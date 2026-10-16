"""Sections of a drawn half near a point (LOP-34, the restart; a prototype): `section_probe.py <design>
<half> <x,y,z> [<reach mm>] [--folder=<dir>]` cuts the half's drawn mesh by the plane z through the
point (plan) and by the vertical plane through it and the nearest bearing's axis, within `reach`
(25 mm), and draws both with the layout's circles; `data/rib_walls/section_<design>_<half>.png`."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh

    from zenryx.domains.gearbox.housing import mesh as mr

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", ROOT / "data" / "rib_walls"))
    design, half = args[0], args[1]
    p = np.array([float(v) for v in args[2].split(",")])
    reach = float(args[3]) if len(args) > 3 else 25.0
    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    tm = mr.load(folder / info["files"][half])
    if not isinstance(tm, trimesh.Trimesh):
        tm = trimesh.Trimesh(*tm) if isinstance(tm, tuple) else trimesh.Trimesh(tm.vertices, tm.faces)
    lay = json.loads((folder / "contract.json").read_text(encoding="utf-8"))
    b = min(lay["bearings"], key=lambda b: math.hypot(p[0] - b["axis"][0], p[1] - b["axis"][1]))
    u = np.array([p[0] - b["axis"][0], p[1] - b["axis"][1], 0.0])
    u /= np.linalg.norm(u)
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    sec = tm.section(plane_origin=p, plane_normal=[0, 0, 1])
    ax = axes[0]
    if sec is not None:
        for seg in sec.discrete:
            ax.plot(seg[:, 0], seg[:, 1], "k-", lw=0.8)
    for bb in lay["bearings"]:
        for r in (bb["D"] / 2, bb["D"] / 2 + 4):
            t = np.linspace(0, 2 * np.pi, 400)
            ax.plot(bb["axis"][0] + r * np.cos(t), bb["axis"][1] + r * np.sin(t), "c-", lw=0.4)
    for c in lay["bolts"]:
        t = np.linspace(0, 2 * np.pi, 100)
        ax.plot(c[0] + 10 * np.cos(t), c[1] + 10 * np.sin(t), "m-", lw=0.5)
    ax.plot(p[0], p[1], "r+", ms=14)
    ax.set_xlim(p[0] - reach, p[0] + reach)
    ax.set_ylim(p[1] - reach, p[1] + reach)
    ax.set_aspect("equal")
    ax.set_title(f"{design} {half}: the section at z {p[2]:g} (black), bores (cyan), bolts' bosses (magenta)")
    normal = np.cross(u, [0, 0, 1.0])
    sec = tm.section(plane_origin=p, plane_normal=normal)
    ax = axes[1]
    if sec is not None:
        for seg in sec.discrete:
            s_ = (seg - np.array([b["axis"][0], b["axis"][1], 0.0])) @ u
            ax.plot(s_, seg[:, 2], "k-", lw=0.8)
    r0 = math.hypot(p[0] - b["axis"][0], p[1] - b["axis"][1])
    ax.plot(r0, p[2], "r+", ms=14)
    ax.axhline(float(lay["z"]["split"]), c="0.6", lw=0.5)
    ax.set_xlim(r0 - reach, r0 + reach)
    ax.set_ylim(p[2] - reach, p[2] + reach)
    ax.set_aspect("equal")
    ax.set_title(f"the section through the point and {b['shaft']} {b['side']}'s axis: radius from it (mm), z")
    out = folder / f"section_{design}_{half}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == "__main__":
    main()
