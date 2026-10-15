"""PROTOTYPE (LOP-16) - one design field analysed in the free model's variants, one solve each:
the halves glued at the split against joined only at the bolts, and the skin as the whole voxel
against the contract's least wall. What each choice costs in stiffness before any optimisation.

The fields: `uniform`, every free voxel at the density that weighs the budget after the filter,
the projection (beta 1) and the casting filter (the bound run's start), the same in every variant
(the free voxels are the same in all four; only the skin's stiffness and the joint differ); and
`solid`, every free voxel metal. Reported per variant: each case's compliance (f'u, N mm), the
worst seat's misalignment over its line and the mean over the 12, and the time the solve and its
12 adjoints took.

Run: .venv/Scripts/python.exe prototypes/first_loop/topo_variants.py [voxel_mm] [budget_kg]
     (one 6 mm solve with its adjoints is about 10 s; prints a table, writes
     data/first_loop/topofree_variants_<voxel>mm.json)
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from topo import DENSITY, OUT, say  # noqa: E402
from topo_free import build_free  # noqa: E402

VARIANTS = [("glued", 0.0), ("glued", None), ("bolts", 0.0), ("bolts", None)]  # (joint, skin: 0 the voxel, None the least wall)


def main(h: float = 6.0, budget: float = 7.73) -> None:
    rows = []
    x_uniform = None
    for joint, skin in VARIANTS:
        model = build_free(h, joint=joint, skin=skin)
        vox = topo.Voxels(model)
        if x_uniform is None:
            # the default model's budget for its free voxels (the skin as the least wall)
            free_kg = budget - build_free(h, joint="bolts", skin=None)["frozen_kg"]
            x_uniform = topo._uniform_start(vox, free_kg / DENSITY / h**3, 1.0)
        for field, x in (("uniform", x_uniform), ("solid", np.ones(len(vox.free_e)))):
            dens = vox.physical(x, 1.0)
            out = vox.analyse(dens, "misalignment_bound")
            u = out["u"]
            comp = [float(vox.rhs[:, c] @ u[vox.free, c]) for c in range(2)]
            r = out["ratio_vector"]
            worst = int(np.argmax(r))
            k = vox.keys[worst]
            row = {"joint": joint, "skin": model["skin"]["wall_mm"], "field": field, "free_kg": float(dens[vox.free_e].sum() * DENSITY * h**3),
                   "compliance_Nmm": comp, "worst_ratio": float(r[worst]), "worst_seat": f"{k[0][0]} {k[0][1]} case {k[1]}",
                   "mean_ratio": float(r.mean()), "ratios": {f"{kc[0][0]} {kc[0][1]} case {kc[1]}": float(v) for kc, v in zip(vox.keys, r, strict=True)},
                   "clock": out["clock"], "steps": out["steps"], "joint_note": vox.joint_note}  # fmt: skip
            rows.append(row)
            say(f"{joint:5s} skin {row['skin']:g} mm, {field:7s}: compliance {comp[0]:9.1f} / {comp[1]:9.1f} N mm, worst {r[worst]:.4f} at {row['worst_seat']}, mean {r.mean():.4f}; "
                f"factor {out['clock']['factor']:.1f} s, 2 solves {out['clock']['solves']:.1f} s, 12 adjoints {out['clock']['adjoints']:.1f} s ({sum(out['steps'][2:])} refinement steps), total {out['clock']['total']:.1f} s")  # fmt: skip
        del vox, model
        gc.collect()
    (OUT / f"topofree_variants_{h:g}mm.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    base = {(r_["field"]): r_ for r_ in rows if r_["joint"] == "glued" and r_["skin"] == h}
    print(f"\n{'joint':6s} {'skin':>5s} {'field':8s} {'drive N mm':>11s} {'reverse':>9s} {'worst':>7s} {'mean':>7s}  against glued, voxel skin (compliance, worst)")
    for r_ in rows:
        b_ = base[r_["field"]]
        print(f"{r_['joint']:6s} {r_['skin']:5g} {r_['field']:8s} {r_['compliance_Nmm'][0]:11.1f} {r_['compliance_Nmm'][1]:9.1f} {r_['worst_ratio']:7.4f} {r_['mean_ratio']:7.4f}  "
              f"x{r_['compliance_Nmm'][0] / b_['compliance_Nmm'][0]:.3f} / x{r_['compliance_Nmm'][1] / b_['compliance_Nmm'][1]:.3f}, x{r_['worst_ratio'] / b_['worst_ratio']:.3f}")  # fmt: skip


if __name__ == "__main__":
    t0 = time.time()
    a = sys.argv[1:]
    main(float(a[0]) if a else 6.0, float(a[1]) if len(a) > 1 else 7.73)
    print(f"{time.time() - t0:.0f} s")
