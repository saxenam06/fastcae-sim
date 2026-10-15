"""The toy's pictures (LOP-34; a prototype): a drawing's height map shaded as seen along the pull
(as production's photos show end faces), and its mesh from an oblique camera (pyvista, off screen).

`pictures.py <label>_<kind> ...`: for each drawn design (`data/rib_field/<name>_drawn.npz` and
`<name>.stl`) writes `<name>_plan.png` and `<name>_3d.png`; `--sheet <out> <title>:<name> ...` puts
designs side by side with their FE numbers (`<name>_fe.json`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402


def plan(z: np.ndarray, out: Path, title: str = "") -> None:
    ls = LightSource(azdeg=315, altdeg=40)
    zz = np.where(z > 0, z, np.nan).T
    rgb = ls.shade(np.nan_to_num(zz, nan=0.0), cmap=plt.cm.gray, vert_exag=3.0, blend_mode="soft",
                   vmin=-30, vmax=toy.WALL + toy.BAND + 4)
    rgb[np.isnan(zz)] = 1.0
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ax.imshow(rgb, origin="lower", extent=(0, toy.LX, 0, toy.LY))
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def oblique(stl: Path, out: Path, title: str = "") -> None:
    import pyvista as pv

    pv.OFF_SCREEN = True
    m = pv.read(str(stl)).compute_normals(feature_angle=40.0, split_vertices=True)
    p = pv.Plotter(off_screen=True, window_size=(1200, 900))
    p.set_background("white")
    p.add_mesh(m, color="#c9ced4", smooth_shading=True, specular=0.3, specular_power=20)
    c = np.array([toy.LX / 2, toy.LY / 2, 10.0])
    p.camera_position = [tuple(c + np.array([-120.0, -260.0, 260.0])), tuple(c), (0, 0, 1)]
    p.camera.zoom(1.25)
    if title:
        p.add_text(title, font_size=12, color="black")
    p.screenshot(str(out))
    p.close()


def sheet(out: Path, items: list[tuple[str, str]]) -> None:
    from matplotlib.image import imread

    rows = len(items)
    fig, axes = plt.subplots(rows, 2, figsize=(13, 5.0 * rows))
    axes = np.atleast_2d(axes)
    for r, (title, name) in enumerate(items):
        fe = json.loads((toy.OUT / f"{name}_fe.json").read_text(encoding="utf-8"))
        words = (
            f"{title}\nFE: compliance {fe['compliance']:.1f} N mm, tilt "
            f"{max(fe['tilt_mrad']):.4f} mrad, placed metal {fe['placed_kg']:.3f} kg"
        )
        for c, suffix in enumerate(("plan", "3d")):
            ax = axes[r, c]
            ax.imshow(imread(toy.OUT / f"{name}_{suffix}.png"))
            ax.set_xticks([])
            ax.set_yticks([])
            if c == 0:
                ax.set_title(words, loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main() -> None:
    if sys.argv[1] == "--sheet":
        out = Path(sys.argv[2])
        items = [tuple(a.split(":", 1)) for a in sys.argv[3:]]
        sheet(out, items)
        print(out)
        return
    for name in sys.argv[1:]:
        d = np.load(toy.OUT / f"{name}_drawn.npz")
        plan(d["z"], toy.OUT / f"{name}_plan.png")
        oblique(toy.OUT / f"{name}.stl", toy.OUT / f"{name}_3d.png")
        print(name)


if __name__ == "__main__":
    main()
