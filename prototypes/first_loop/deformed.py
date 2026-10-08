"""PROTOTYPE (LOP) - the FE result as pictures: the displacement on the deformed halves, per case.

Run: uv run python prototypes/first_loop/deformed.py [stem]     (default: shell)
Reads data/first_loop/fe_<stem>.npz and .json; writes data/first_loop/fe_<stem>.png.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "first_loop"
SCALE = 150.0  # how much the displacement is magnified in the picture


def main(stem: str = "shell") -> None:
    data = np.load(OUT / f"fe_{stem}.npz")
    info = json.loads((OUT / f"fe_{stem}.json").read_text(encoding="utf-8"))
    cases = list(info["cases"])
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(1, len(cases)), window_size=(1600, 700), off_screen=True)
    top = 0.0
    meshes = []
    for j, _ in enumerate(cases):
        row = []
        for half in ("motor_side", "cover"):
            nodes = data[f"{half}_nodes"]
            tets = data[f"{half}_tets"][:, :4]
            off = int(data[f"{half}_offset"])
            u = data["u"][off : off + 3 * len(nodes), j].reshape(-1, 3)
            cells = np.hstack([np.full((len(tets), 1), 4), tets]).ravel()
            grid = pv.UnstructuredGrid(cells, np.full(len(tets), pv.CellType.TETRA), nodes + SCALE * u)
            grid.point_data["um"] = 1000 * np.linalg.norm(u, axis=1)
            row.append(grid.extract_surface())
            top = max(top, float(grid.point_data["um"].max()))
        meshes.append(row)
    for j, name in enumerate(cases):
        plotter.subplot(0, j)
        for surface in meshes[j]:
            plotter.add_mesh(surface, scalars="um", clim=(0, top), cmap="turbo", show_scalar_bar=(j == 0))
        seats = info["cases"][name]["seats"]
        worst = max(seats.items(), key=lambda kv: kv[1]["displacement_mm"])
        tilt = max(seats.items(), key=lambda kv: kv[1]["tilt_mrad"])
        plotter.add_text(
            f"{name}: displacement in µm, shown x{SCALE:.0f}\nworst seat {worst[0]} "
            f"{1000 * worst[1]['displacement_mm']:.0f} µm, worst tilt {tilt[0]} {tilt[1]['tilt_mrad']:.2f} mrad",
            font_size=9,
        )
        plotter.view_vector((0.6, -0.5, 0.8), viewup=(0.0, -1.0, 0.0))
    plotter.screenshot(str(OUT / f"fe_{stem}.png"))
    print("wrote", OUT / f"fe_{stem}.png")
    for name in cases:
        print(name)
        for seat, v in info["cases"][name]["seats"].items():
            print(f"   {seat:16s} {1000 * v['displacement_mm']:6.0f} µm (radial {1000 * v['radial_mm']:5.0f})  tilt {v['tilt_mrad']:.2f} mrad")
        for shaft, v in info["cases"][name]["shafts"].items():
            print(f"   shaft {shaft:12s} tilt {v['tilt_mrad']:.2f} mrad over {v['span_mm']:.0f} mm")


if __name__ == "__main__":
    main(*sys.argv[1:])
