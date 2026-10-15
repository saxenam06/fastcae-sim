"""PROTOTYPE (LOP-29) - the optimiser's own model against FE on the same design, statics and modes: where a gap between them
comes from. `voxel_vs_fe.py` (LOP-17) did this for the B-rep designs of 10 October; this one reads the empty start's runs
(`build_free` with the run's record: the height field, the empty start, the protected interfaces, the flange's whole cubes)
and the mesh route's drawings (each half's STL), and reads the modes too (`topo.Voxels.with_modes`).

On the run's own model, three shapes, each free voxel metal (1) or air (0), the fixed ones as they are:
- `field at 0.5`: the run's densities at 0.5 (it must give back the run's binary check);
- `drawing`: the drawn design voxelised (a free voxel metal when its centre lies inside its half's drawn mesh);
- `drawing + field`: both.
For each: every seat's displacement (its bed against the design to beat's, as the grade's) and tilt (its ratio to its line),
and the lowest modes; then FE's grade and modes for the same design. If `drawing` reads near FE, the model is fair and the
drawing lost the field's metal; if it reads near `field at 0.5`, the model itself is stiffer than FE on the same shape.

Run: .venv/Scripts/python.exe prototypes/first_loop/model_vs_fe.py <design>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

OUT = HERE.parents[1] / "data" / "first_loop"


def inside_drawing(design: str, rec: dict, centres: np.ndarray, z_split: float) -> np.ndarray:
    """Which centres lie inside the design's drawn halves (their STLs): the motor side's below the split, the cover's above."""
    import pyvista as pv

    inside = np.zeros(len(centres), bool)
    for half in ("motor_side", "cover"):
        surf = pv.read(str(OUT / rec["files"][half])).triangulate().clean()
        mine = centres[:, 2] < z_split if half == "motor_side" else centres[:, 2] >= z_split
        sel = pv.PolyData(centres[mine]).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)
        inside[np.flatnonzero(mine)] = np.asarray(sel["SelectedPoints"]).astype(bool)
    return inside


def main(design: str, fe_stem: str | None = None) -> dict:
    import topo
    from grade import REFERENCE
    from topo_free import build_free

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    run = rec["outcome_of"]
    rr = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    h = float(z["h"])
    model = build_free(h, band=rr.get("band_mm"), flange=bool(rr.get("flange")), mount_reach=rr.get("mount_reach") or "disc",
                       height_field=(rr.get("height_field") or {}).get("radius_mm"), empty=bool(rr.get("empty")),
                       protect=bool(rr.get("protect")), flange_whole=bool(rr.get("flange_whole")),
                       drawing_clear=bool(rr.get("drawing_clear")), couplings=rr.get("couplings") or "glue", shell_fixed=bool(rr.get("shell_fixed")), towers=bool(rr.get("towers", True)))  # fmt: skip
    model["cases"] = tuple(rr.get("cases") or ("peak drive",))
    model["beds_mm"] = {"peak drive": REFERENCE["peak drive"] / 1000.0}
    model["modes"] = {"margin": 0.12, "count": 14}
    vox = topo.Voxels(model)
    if len(vox.elem) != len(z["elem"]) or not np.array_equal(vox.elem, z["elem"]):
        raise SystemExit(f"{run}: its model built again does not give its voxels ({len(vox.elem):,} against {len(z['elem']):,})")
    free = vox.free_e
    lo, ks = np.asarray(model["lo"], float), int(model["k_split"])
    centres = lo + h * (vox.ijk + 0.5)
    z_split = lo[2] + h * ks
    field = np.asarray(z["phys"], float) >= 0.5
    drawn = inside_drawing(design, rec, centres, z_split)[free]
    shapes = {"field at 0.5": field, "drawing": drawn, "drawing + field": field | drawn}
    out = {"design": design, "run": run, "shapes": {}}
    for name, d_free in shapes.items():
        dens = np.ones(len(vox.elem))
        dens[free] = d_free.astype(float)
        a = vox.with_modes(vox.analyse(dens, "compliance_bound", adjoints=False))
        vox.release(a)
        beds_um = [float(v) * REFERENCE["peak drive"] for v in a["bed_vector"]]
        out["shapes"][name] = {"metal_voxels": int(d_free.sum()), "worst_bed_um": max(beds_um), "worst_tilt": float(a["ratio_vector"].max()),
                               "modes_hz": [round(float(v), 1) for v in a["modes_hz"]]}  # fmt: skip
        print(f"{name:16s} metal {int(d_free.sum()):7,} voxels; worst seat {max(beds_um):6.1f} µm, tilt {a['ratio_vector'].max():.3f} x; "
              f"modes {', '.join(f'{v:.0f}' for v in a['modes_hz'][:10])} Hz", flush=True)  # fmt: skip
    fe_stem = fe_stem or design  # (LOP-29) another judgement of the same design: fe_<fe_stem>.json, its grade
    g = {x["stem"]: x for x in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))}.get(fe_stem)
    fe = json.loads((OUT / f"fe_{fe_stem}.json").read_text(encoding="utf-8"))
    if g:
        lt = g["lines"]
        out["fe"] = {"worst_bed_um": lt["displacement, peak drive"]["value_um"], "worst_tilt": lt["misalignment (worst seat against its line)"]["ratio"],
                     "modes_hz": [round(float(v), 1) for v in fe["modes_hz"]]}  # fmt: skip
        print(f"{'FE':16s} {'':22s} worst seat {out['fe']['worst_bed_um']:6.1f} µm, tilt {out['fe']['worst_tilt']:.3f} x; "
              f"modes {', '.join(f'{v:.0f}' for v in fe['modes_hz'][:10])} Hz")  # fmt: skip
    (OUT / f"model_vs_fe_{fe_stem}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
