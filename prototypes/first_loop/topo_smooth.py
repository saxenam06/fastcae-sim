"""PROTOTYPE (LOP-16) - an optimisation's field as a smooth surface: the "organic" route, as
printed parts are drawn straight from the field (implicit smoothing), beside the parametric
reading into the generator's recipe.

The field (frozen voxels and the material placed) filtered a little, its 0.5 level surface found
by marching cubes, then smoothed by Taubin's filter (no shrinking); pictured over the gears.
The contract's process is printed sand moulds, which need no draft, and the optimiser kept the
pull rule by its casting filter: such a surface could itself be cast. Whether the smoothing keeps
the pull rule, the least wall and the seats is for castable.py and the FE to say (not yet: this
writes the surface and its picture).

Run: uv run python prototypes/first_loop/topo_smooth.py <run stem>
     (writes data/first_loop/<stem>_smooth.stl and _smooth.png)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

from topo import OUT  # noqa: E402


def smooth(stem: str) -> Path:
    import pyvista as pv
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes

    z = np.load(OUT / f"{stem}.npz")
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    field = np.zeros(int(np.prod(n)))
    field[z["elem"][z["frozen"].astype(bool)]] = 1.0
    field[z["elem"][z["free_e"]]] = np.maximum(field[z["elem"][z["free_e"]]], z["phys"])
    field = gaussian_filter(np.pad(field.reshape(n), 2), sigma=0.7)
    verts, faces, _, _ = marching_cubes(field, level=0.5, spacing=(h, h, h))
    verts += lo - 2 * h + 0.5 * h
    mesh = pv.PolyData(verts, np.hstack([np.full((len(faces), 1), 3), faces]).ravel())
    mesh = mesh.smooth_taubin(n_iter=40, pass_band=0.05).compute_normals()
    stl = OUT / f"{stem}_smooth.stl"
    mesh.save(str(stl))
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(1, 2), window_size=(1600, 760), off_screen=True)
    for col, view in enumerate(((0.6, -0.5, 0.8), (-0.6, -0.5, -0.8))):
        plotter.subplot(0, col)
        plotter.add_mesh(mesh, color=(0.80, 0.81, 0.83), smooth_shading=True, specular=0.4, specular_power=25)
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        plotter.add_text(f"{stem}: the field smoothed ({'the cover' if col == 0 else 'the motor side'})", font_size=9)
    plotter.screenshot(str(OUT / f"{stem}_smooth.png"))
    plotter.close()
    print(f"{stl.name}: {mesh.n_points:,} points, {mesh.n_cells:,} triangles")
    return stl


if __name__ == "__main__":
    smooth(sys.argv[1] if len(sys.argv) > 1 else "topofree_misalignment_7.73kg_6mm_projected")
