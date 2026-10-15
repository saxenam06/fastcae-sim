"""The housing's rib-direction field optimised (LOP-34; a prototype): the product's problem with the
free cubes as ribs. `optimise.py <label> [iterations] [--voxel=<mm>] [--start=<npz>]`.

The problem is the final recipe's (`mass_tilt`): the least placed metal, every seat's tilt and every
bed at most 1/1.5 of its line in the peak drive (the product's measures, `vox.seats`, `vox.bed_*`),
the placed metal at most the budget's remainder; and every group's fastcae rules (`field.py`,
`prototypes/rib_field/rules.py`). The modes are not held (the CPU's time): FE reads them after.
MMA (the product's GCMMA's step, no inner loop), the directions' start from the strains of the
first analysis. Writes `data/rib_housing/<label>.npz` (the design vector, every group's start
directions, every column's families and direction) every `SAVE` iterations and at the end, and
`<label>.json` (the history and the set-up).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import field as fieldmod  # noqa: E402
import housing  # noqa: E402
import ribmodel  # noqa: E402
from zenryx.domains.gearbox.housing.mma import MMA  # noqa: E402

SAVE = 5
MOVE = 0.1


def save(label, hf, x, history, extra):
    pc = hf.per_column(x)
    np.savez_compressed(
        housing.OUT / f"{label}.npz",
        x=x,
        theta=pc["theta"],
        rho=np.stack([f["rho"] for f in pc["fam"]]),
        h=np.stack([f["h"] for f in pc["fam"]]),
        zcols=hf.zcols,
        hs=hf.solid(x)["hs"],
        **{f"theta0_{g.name}": g.theta0 for g in hf.groups},
    )
    (housing.OUT / f"{label}.json").write_text(
        json.dumps({"history": history, **extra}, indent=1), encoding="utf-8"
    )


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    label = args[0]
    iterations = int(args[1]) if len(args) > 1 else 80
    voxel = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--voxel=")), 4.0))
    start = next((a.split("=")[1] for a in sys.argv if a.startswith("--start=")), None)
    t0 = time.time()
    vox, model = housing.product_model(voxel)
    groups = housing.column_groups(vox)
    rm = ribmodel.RibModel(vox)
    hf = fieldmod.HousingField(vox, groups, rm.c_local, rm.c_iso)
    free_kg = model["budget_kg"] - model["frozen_kg"]
    print(f"the field: {len(hf.groups)} groups, {hf.size:,} variables; the budget's remainder {free_kg:.2f} kg")
    x = hf.start(0.6)
    if start:
        z = np.load(start)
        x = z["x"]
        for g in hf.groups:
            g.theta0 = z[f"theta0_{g.name}"]
            g.theta0_grad = fieldmod.rules.theta_gradient(g.theta0, g.ij, hf.a)
    else:
        c, pc = hf.stiffness(x)
        out = rm.analyse(c, adjoints=False)
        hf.align(rm.energy(out["q"]), pc)
        print(f"the start's directions from its strains ({time.time() - t0:.0f} s)")
    extra = {"label": label, "voxel": voxel, "budget_kg": model["budget_kg"], "frozen_kg": model["frozen_kg"],
             "free_kg": free_kg, "groups": [g.name for g in hf.groups], "spacing": fieldmod.SPACING,
             "knot": fieldmod.KNOT, "tall": fieldmod.toy.TALL, "rules": {
                 "T_NEAR": fieldmod.rules.T_NEAR, "T_FAR": fieldmod.rules.T_FAR,
                 "END_REACH": fieldmod.rules.END_REACH, "LIMIT_T": fieldmod.rules.LIMIT_T,
                 "LIMIT_H": fieldmod.rules.LIMIT_H, "LIMIT_A": fieldmod.rules.LIMIT_A,
                 "R_BEND": fieldmod.rules.R_BEND}}
    history = []
    opt = None
    for it in range(iterations):
        t1 = time.time()
        c, pc = hf.stiffness(x)
        out = rm.analyse(c)
        mass = hf.mass(pc)
        dm = hf.back(pc, mass=True)
        f, df, names = [], [], []
        for i, r in enumerate(out["ratios"]):
            f.append(r - 1.0)
            df.append(hf.back(pc, out["d_ratio"][i]))
            names.append(f"tilt {vox.keys[i][0][0]} {vox.keys[i][0][1]}")
        for i, b in enumerate(out["beds"]):
            f.append(b - 1.0)
            df.append(hf.back(pc, out["d_bed"][i]))
            names.append(f"bed {vox.bed_keys[i][0][0]} {vox.bed_keys[i][0][1]}")
        f.append(mass / free_kg - 1.0)
        df.append(dm / free_kg)
        names.append("budget")
        for name, g, dg, _meas in hf.rules(x):
            f.append(g)
            df.append(dg)
            names.append(name)
        f, df = np.array(f), np.array(df)
        worst = int(np.argmax(f))
        ribs_kg, solid_kg = hf.masses(pc)
        row = {"it": it, "placed_kg": mass, "ribs_kg": ribs_kg, "solid_kg": solid_kg,
               "tilts": out["ratios"].tolist(), "beds": out["beds"].tolist(),
               "tilt_worst": float(out["ratios"].max()),
               "bed_worst": float(out["beds"].max()), "worst": names[worst], "worst_g": float(f[worst]),
               "violated": [n for n, v in zip(names, f, strict=True) if v > 0.01],
               "seconds": time.time() - t1}
        history.append(row)
        print(f"it {it:3d}: placed {mass:.3f} kg (ribs {ribs_kg:.3f}, solid {solid_kg:.3f}), "
              f"tilt {row['tilt_worst']:.3f}, bed {row['bed_worst']:.3f} of "
              f"their lines; the worst {names[worst]} {f[worst]:+.3f}; {len(row['violated'])} over; "
              f"{row['seconds']:.0f} s", flush=True)
        if opt is None:
            opt = MMA(len(x), len(f), 0.0, 1.0)
        x = opt.propose(x, mass / free_kg, dm / free_kg, f, df, move=MOVE)
        if (it + 1) % SAVE == 0:
            save(label, hf, x, history, extra)
    save(label, hf, x, history, extra)
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
