"""PROTOTYPE (LOP-17) - the optimiser's voxel model against the CAD's FE, on the same shape.

The anchored outcome's CAD (`outcome_cad.py`) read 1.45 × its line in fe.py, where the voxel model
had promised 0.087 for the field it was drawn from (10 October 05:15). Either the model flatters
the very shape it optimised, or the drawing lost the field's load paths. This solves the
optimiser's own model (`topo_free.build_free`, `topo.Voxels`) on several shapes, each its free
voxels metal (1) or air (0), the frozen voxels left as they are:
- `field`: the run's own densities (it must give back the run's last ratio);
- `field_bin`: the field at 0.5;
- `cad`: the CAD voxelised (a free voxel is metal when its centre lies inside the CAD's half);
- `blur 0.6/0.45`, `blur 0.7/0.5`: the field at 0.5, closed, blurred and contoured as
  `outcome_cad.organic_half`'s rungs do, sampled at the voxels' centres (no zones, no cuts);
- `cad + field at split`, `cad + field elsewhere`, `cad + field`: the field's metal the CAD lost,
  put back near the split (two voxel layers each side) or elsewhere or everywhere.
If `cad` reads near fe.py's number, the model is fair and the drawing lost load paths; the blurs
and the put-backs then say which step lost them. Each seat and case's ratio is printed.

Run: .venv/Scripts/python.exe prototypes/first_loop/voxel_vs_fe.py <run stem> <design stem> [route]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from topo_free import OUT, build_free  # noqa: E402


def voxelised(design: str, centres: np.ndarray, k_split_z: float) -> np.ndarray:
    """Which centres lie inside the design's CAD: the motor side's below the split, the cover's above."""
    import cadquery as cq
    import pyvista as pv

    inside = np.zeros(len(centres), bool)
    for half in ("motor_side", "cover"):
        shape = cq.Shape.importBrep(str(OUT / f"{design}_{half}.brep"))
        verts, tris = shape.tessellate(0.2, 0.3)
        surf = pv.PolyData(np.array([v.toTuple() for v in verts]), np.hstack([np.full((len(tris), 1), 3), np.asarray(tris)]).ravel())
        mine = centres[:, 2] < k_split_z if half == "motor_side" else centres[:, 2] >= k_split_z
        pts = pv.PolyData(centres[mine])
        sel = pts.select_enclosed_points(surf, tolerance=1e-6, check_surface=False)
        inside[np.flatnonzero(mine)] = np.asarray(sel["SelectedPoints"]).astype(bool)
    return inside


def blurred(metal: np.ndarray, ks: int, sigma: float, level: float) -> np.ndarray:
    """The metal closed, each half blurred apart (as `organic_half` does) and taken at `level`."""
    from scipy.ndimage import binary_closing, gaussian_filter, generate_binary_structure

    closed = binary_closing(np.pad(metal, 1), structure=generate_binary_structure(3, 1))[1:-1, 1:-1, 1:-1]
    out = np.zeros_like(metal)
    for half in ("motor_side", "cover"):
        rho = closed.astype(float)
        if half == "cover":
            rho[:, :, :ks] = 0.0
            for k in (ks - 1, ks - 2):
                rho[:, :, k] = rho[:, :, ks]
        else:
            rho[:, :, ks:] = 0.0
            for k in (ks, ks + 1):
                rho[:, :, k] = rho[:, :, ks - 1]
        g = gaussian_filter(rho, sigma=sigma) >= level
        if half == "cover":
            out[:, :, ks:] |= g[:, :, ks:]
        else:
            out[:, :, :ks] |= g[:, :, :ks]
    return out


def parts(vox, a: dict) -> list[tuple[float, float, float]]:
    """Each seat and case's (housing, shaft, both) as ratios to its line: the seat's tilt against
    its shaft's chord, the shaft's own lean there, and their difference (the ratio judged)."""
    uf = a["u"][vox.free]
    out = []
    for key, _rr, line, l1, l2 in vox.seats:
        for c in range(2):
            lx, ly = vox.lean_of[(key, c)]
            v1, v2 = float((l1 @ uf[:, c])[0]), float((l2 @ uf[:, c])[0])
            out.append((np.hypot(v1, v2) / line, np.hypot(lx, ly) / line, np.hypot(v1 - lx, v2 - ly) / line))
    return out


def main(run: str, design: str, route: str = "split") -> dict:
    z = np.load(OUT / f"{run}.npz")
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    h = float(z["h"])
    skin = rec["skin"]["wall_mm"] if isinstance(rec.get("skin"), dict) else None
    model = build_free(h, layout=rec.get("layout", "grammar4"), band=rec.get("band_mm"), joint="bolts", skin=skin,
                       cavity=rec.get("cavity", "cup"), penalty_ramp=rec.get("penalty_ramp", 20), route=route,
                       flange=rec.get("flange", False), mount_reach=rec.get("mount_reach") or "corridor")  # fmt: skip
    vox = topo.Voxels(model)
    n_el = len(vox.elem)
    free = vox.free_e
    lo, n, ks = model["lo"], model["n"], model["k_split"]
    ijk = np.column_stack(np.unravel_index(vox.elem, tuple(n)))
    centres = lo + h * (ijk + 0.5)
    k_split_z = lo[2] + h * ks
    phys = np.asarray(z["phys"], float)
    field_bin = phys >= 0.5
    cad = voxelised(design, centres, k_split_z)[free]
    # the field at 0.5 on the whole grid, every frozen voxel metal too, as `outcome_cad.field_of` reads it
    grid = np.zeros(tuple(n), bool)
    frozen_e = np.ones(n_el, bool)
    frozen_e[free] = False
    grid[tuple(ijk[frozen_e].T)] = True
    grid[tuple(ijk[free][field_bin].T)] = True
    lost = field_bin & ~cad
    near_split = np.abs(ijk[free][:, 2] + 0.5 - ks) <= 2.0
    grey = (phys > 0.05) & (phys < 0.95)
    print(f"the field: {grey.sum():,} of {len(phys):,} free voxels grey (0.05-0.95), holding {phys[grey].sum():,.0f} voxels' metal; "
          f"{(phys >= 0.5).sum():,} at 0.5 or more, {(phys >= 0.3).sum():,} at 0.3, {(phys >= 0.7).sum():,} at 0.7")  # fmt: skip
    shapes = {"field": phys, "field at 0.3": phys >= 0.3, "field_bin": field_bin, "field at 0.7": phys >= 0.7, "cad": cad}
    for sigma, level in ((0.6, 0.45), (0.7, 0.5)):
        b = blurred(grid, ks, sigma, level)
        shapes[f"blur {sigma}/{level}"] = b[tuple(ijk[free].T)]
    shapes["cad + field at split"] = cad | (lost & near_split)
    shapes["cad + field elsewhere"] = cad | (lost & ~near_split)
    shapes["cad + field"] = cad | field_bin
    out = {"keys": [f"{k[0][0]} {k[0][1]} case {k[1]}" for k in vox.keys], "shapes": {}}
    for name, d_free in shapes.items():
        dens = np.ones(n_el)
        dens[free] = np.asarray(d_free, float)
        a = vox.analyse(dens, "misalignment_bound", adjoints=False)
        p = parts(vox, a)
        vox.release(a)
        metal = float(np.asarray(d_free, float).sum())
        out["shapes"][name] = {"ratios": a["ratio_vector"].tolist(), "worst": float(a["ratio_vector"].max()), "metal_voxels": metal,
                               "housing": [q[0] for q in p], "shaft": [q[1] for q in p]}  # fmt: skip
        print(f"{name:24s} worst {a['ratio_vector'].max():7.3f}  metal voxels {metal:9,.0f}  ratios " + " ".join(f"{r:.2f}" for r in a["ratio_vector"]), flush=True)
        print(f"{'':24s} the housing's tilt alone " + " ".join(f"{q[0]:.2f}" for q in p) + "; the shafts' lean " + " ".join(f"{q[1]:.2f}" for q in p), flush=True)
    out["lost"] = {"at_split": int((lost & near_split).sum()), "elsewhere": int((lost & ~near_split).sum())}
    out["added"] = int((cad & ~field_bin).sum())
    print(f"field metal the CAD lost: {out['lost']['at_split']:,} voxels near the split, {out['lost']['elsewhere']:,} elsewhere; the CAD's metal the field had not: {out['added']:,}")
    (OUT / f"voxel_vs_fe_{design}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "split")
