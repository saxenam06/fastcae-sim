"""Where a walls design's gap between the model and FE comes from (LOP-34, the restart; a prototype):
`model_vs_fe.py <label> <design> [--voxel=<mm>]` solves the model three ways and puts FE's reading
beside them: the run's own field (ribs as laminates, features solid); the drawing voxelised onto the
model's free cubes (each cube's share of the drawn halves, sampled 3 x 3 x 3, as isotropic metal at
that share); and FE's (`fe_<design>.json`). The model on the drawing near FE: the model is fair and
the drawing lost what the field held; the model on the drawing far stiffer than FE: the model
flatters (its resolution, its fixed cubes)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "rib_housing"))
sys.path.insert(0, str(HERE))
import drawwall  # noqa: E402
import ribmodel  # noqa: E402


def shares(vox, model, folder: Path, design: str, sub: int = 3) -> np.ndarray:
    """Each free cube's share inside the drawn halves (sampled sub^3 points a cube)."""
    import pyvista as pv

    from zenryx.domains.gearbox.housing import mesh as mr

    info = json.loads((folder / f"{design}.json").read_text(encoding="utf-8"))
    h, lo = float(model["h"]), np.asarray(model["lo"], float)
    ijk = vox.ijk[vox.free_e]
    offs = (np.stack(np.meshgrid(*([np.arange(sub)] * 3), indexing="ij"), -1).reshape(-1, 3) + 0.5) / sub
    inside = np.zeros((len(ijk), len(offs)), bool)
    for half in ("motor_side", "cover"):
        tm = mr.load(folder / info["files"][half])
        surf = pv.PolyData(np.asarray(tm.vertices), np.hstack([np.full((len(tm.faces), 1), 3),
                                                               np.asarray(tm.faces)]).ravel())
        lo_b, hi_b = np.asarray(tm.vertices).min(axis=0), np.asarray(tm.vertices).max(axis=0)
        for k, o in enumerate(offs):
            pts = lo + (ijk + o) * h
            near = np.all((pts >= lo_b - 1) & (pts <= hi_b + 1), axis=1)
            if near.any():
                sel = pv.PolyData(pts[near]).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)
                inside[np.flatnonzero(near), k] |= np.asarray(sel["SelectedPoints"]).astype(bool)
    return inside.mean(axis=1)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    label, design = args[0], args[1]
    voxel = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--voxel=")), 4.0))
    vox, model, layout, rooms, wf, x = drawwall.rebuild(label, voxel)
    rm = ribmodel.RibModel(vox)
    c, pc = wf.stiffness(x)
    own = rm.analyse(c, adjoints=False)
    d = shares(vox, model, drawwall.OUT, design)
    c_draw = (ribmodel.ERSATZ + d)[:, None, None] * rm.c_iso[None]
    drawn = rm.analyse(c_draw, adjoints=False)
    a3 = float(model["h"]) ** 3 * float(vox.density)
    fe = json.loads((drawwall.OUT / f"fe_{design}.json").read_text(encoding="utf-8"))
    print(f"the free cubes' metal: the field's {wf.mass(pc):.2f} kg, the drawing's on the model's cubes {d.sum() * a3:.2f} kg "
          f"(with the fixed {model['frozen_kg']:.2f})")
    names = [f"{k[0][0]} {k[0][1]}" for k in vox.keys]
    lines = [line for _, line, _, _ in vox.seats]
    print("seat               tilt over its 1/1.5 line: field / drawing in the model;   bed: field / drawing")
    for i, n in enumerate(names):
        print(f"  {n:18s} {own['ratios'][i]:6.3f} / {drawn['ratios'][i]:6.3f}            "
              f"{own['beds'][i]:6.3f} / {drawn['beds'][i]:6.3f}")
    print(f"the worst: tilt {own['ratios'].max():.3f} / {drawn['ratios'].max():.3f}; bed {own['beds'].max():.3f} / "
          f"{drawn['beds'].max():.3f} (1 = the line over the safety, {vox.model.get('safety', 1.5)})")
    for case, v in fe["cases"].items():
        print(f"FE, {case}: {json.dumps(v, default=str)[:700]}")
    _ = lines


if __name__ == "__main__":
    main()
