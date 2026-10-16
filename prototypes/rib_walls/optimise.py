"""The rib field on the walls optimised (LOP-34, the restart; a prototype): the product's problem with
the free cubes as ribs on their walls, ring bosses and two-web brackets.
`optimise.py <label> [iterations] [--voxel=<mm>] [--start=<npz>]`.

The problem is the final recipe's (`mass_tilt`): the least placed metal, every seat's tilt and every
bed at most 1/1.5 of its line in the peak drive (the product's measures), the placed metal at most
the budget's remainder; and each half's fastcae rules (`wallrules.py`). The modes are not held (the
CPU's time): FE reads them after. MMA (the product's GCMMA's step, no inner loop); the directions'
start from the strains of the first analysis (`WallField.align`). Writes
`data/rib_walls/<label>.npz` (the design vector, the start directions, every cube's ribs and
features) every `SAVE` iterations and at the end, `<label>_held.npz` at the last iterate holding
every line within 2 %, and `<label>.json` (the history and the set-up).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "rib_housing"))
import housing  # noqa: E402
import ribmodel  # noqa: E402
import surface  # noqa: E402
import wallfield as wfm  # noqa: E402
import wallrules  # noqa: E402

from zenryx.domains.gearbox.housing.mma import MMA  # noqa: E402

OUT = housing.ROOT / "data" / "rib_walls"
SAVE = 5
MOVE = 0.1
HELD = 0.02


def model_dir(voxel: float) -> Path:
    return housing.OUT if voxel == 4.0 else housing.OUT / f"v{voxel:g}"


def build(voxel: float, say=print):
    """The product's model, the walls, the field and the rules' weights."""
    vox, model = housing.product_model(voxel, out=model_dir(voxel))
    layout = json.loads((model_dir(voxel) / "contract.json").read_text(encoding="utf-8"))
    rm = ribmodel.RibModel(vox, say=say)
    rooms = surface.rooms_of(vox)
    cm = surface.map_cubes(vox, layout, rooms)
    wf = wfm.WallField(vox, cm, layout, rm.c_local, rm.c_iso, rooms)
    prep = wallrules.prepare(wf)
    return vox, model, layout, rm, cm, wf, prep


def save(path: Path, wf, x, extra: dict | None = None):
    _, pc = wf.stiffness(x)
    np.savez_compressed(
        path,
        x=x,
        theta0=wf.theta0,
        theta=pc["theta"],
        t=np.stack([f["t"] for f in pc["fam"]]),
        rho=np.stack([f["rho"] for f in pc["fam"]]),
        h=np.stack([f["h"] for f in pc["fam"]]),
        g=np.stack([f["g"] for f in pc["fam"]]),
        s=pc["s"],
        **{f"cm_{k}": wf.cm[k] for k in ("centre", "lower", "d", "n", "foot", "e1", "e2", "across")},
        **(extra or {}),
    )


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    label = args[0]
    iterations = int(args[1]) if len(args) > 1 else 80
    voxel = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--voxel=")), 4.0))
    start = next((a.split("=")[1] for a in sys.argv if a.startswith("--start=")), None)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    vox, model, layout, rm, cm, wf, prep = build(voxel)
    free_kg = model["budget_kg"] - model["frozen_kg"]
    print(f"the walls field: {wf.size:,} variables ({len(wf.bosses)} ring bosses, {len(wf.webs)} brackets of "
          f"two webs); {int(prep['first'].sum()):,} wall points; the budget's remainder {free_kg:.2f} kg "
          f"({time.time() - t0:.0f} s)", flush=True)
    xmin = wf.lower_bounds()
    x = np.maximum(wf.start(), xmin)
    if start:
        z = np.load(start)
        x, wf.theta0 = z["x"], z["theta0"]
    else:
        c, pc = wf.stiffness(x)
        out = rm.analyse(c, adjoints=False)
        wf.align(rm.energy(out["q"]), pc)
        print(f"the start's directions from its strains ({time.time() - t0:.0f} s)", flush=True)
    extra = {"label": label, "voxel": voxel, "budget_kg": model["budget_kg"], "frozen_kg": model["frozen_kg"],
             "free_kg": free_kg, "settings": {
                 "SPACING": wfm.SPACING, "T_MIN": wfm.T_MIN, "T_RAMP": wfm.T_RAMP, "T_NEAR": wfm.T_NEAR,
                 "T_FAR": wfm.T_FAR, "T_TAPER": wfm.T_TAPER, "H_MOST": wfm.H_MOST, "TALL": wfm.TALL,
                 "KNOT": wfm.KNOT, "BOSS_GROW": wfm.BOSS_GROW, "BOSS_TALL": wfm.BOSS_TALL,
                 "WEB": [wfm.WEB_LEAST, wfm.WEB_MOST], "WEB_SPREAD": wfm.WEB_SPREAD,
                 "LIMIT_T": wallrules.LIMIT_T, "LIMIT_H": wallrules.LIMIT_H, "END_REACH": wallrules.END_REACH},
             "bosses": [b["name"] for b in wf.bosses], "webs": [w["name"] for w in wf.webs]}
    history = []
    opt = None
    for it in range(iterations):
        t1 = time.time()
        c, pc = wf.stiffness(x)
        out = rm.analyse(c)
        mass = wf.mass(pc)
        dm = wf.back(pc, mass=True)
        f, df, names = [], [], []
        for i, r in enumerate(out["ratios"]):
            f.append(r - 1.0)
            df.append(wf.back(pc, out["d_ratio"][i]))
            names.append(f"tilt {vox.keys[i][0][0]} {vox.keys[i][0][1]}")
        for i, b in enumerate(out["beds"]):
            f.append(b - 1.0)
            df.append(wf.back(pc, out["d_bed"][i]))
            names.append(f"bed {vox.bed_keys[i][0][0]} {vox.bed_keys[i][0][1]}")
        f.append(mass / free_kg - 1.0)
        df.append(dm / free_kg)
        names.append("budget")
        n_lines = len(f)
        for name, g, dg, _meas in wallrules.rules(wf, x, prep):
            f.append(g)
            df.append(dg)
            names.append(name)
        f, df = np.array(f), np.array(df)
        worst = int(np.argmax(f))
        ribs_kg, solid_kg = wf.masses(pc)
        bosses = [(wf.bosses[i]["name"], round(wfm.BOSS_GROW[0] + wfm.BOSS_GROW[1] * float(x[wf.n_field + 2 * i]), 1),
                   round(wfm.BOSS_TALL[0] + wfm.BOSS_TALL[1] * float(x[wf.n_field + 2 * i + 1]), 1))
                  for i in range(len(wf.bosses))]
        webs = [(wf.webs[i]["name"], round(wfm.WEB_MOST * float(wf.web_x(x, i)[0]), 1),
                 round(float(np.degrees(wfm.WEB_SPREAD[0] + wf.webs[i]["span"] * wf.web_x(x, i)[1])), 1))
                for i in range(len(wf.webs))]
        row = {"it": it, "placed_kg": mass, "ribs_kg": ribs_kg, "solid_kg": solid_kg,
               "tilts": out["ratios"].tolist(), "beds": out["beds"].tolist(),
               "tilt_worst": float(out["ratios"].max()), "bed_worst": float(out["beds"].max()),
               "rules": {n: float(v) for n, v in zip(names[n_lines:], f[n_lines:], strict=True)},
               "worst": names[worst], "worst_g": float(f[worst]),
               "violated": [n for n, v in zip(names, f, strict=True) if v > 0.01],
               "bosses": bosses, "webs": webs, "seconds": time.time() - t1}
        history.append(row)
        print(f"it {it:3d}: placed {mass:.3f} kg (ribs {ribs_kg:.3f}, features {solid_kg:.3f}), "
              f"tilt {row['tilt_worst']:.3f}, bed {row['bed_worst']:.3f} of their lines; the worst {names[worst]} "
              f"{f[worst]:+.3f}; {len(row['violated'])} over; {row['seconds']:.0f} s", flush=True)
        if it % 10 == 0:
            print(f"    bosses (grow, tall mm) {bosses}; webs (mm, deg) {webs}; rules "
                  f"{ {k: round(v, 3) for k, v in row['rules'].items()} }", flush=True)
        if float(f[:n_lines].max()) <= HELD:
            save(OUT / f"{label}_held.npz", wf, x, {"it": it})
        if opt is None:
            opt = MMA(len(x), len(f), xmin, 1.0)
        x = opt.propose(x, mass / free_kg, dm / free_kg, f, df, move=MOVE)
        if (it + 1) % SAVE == 0:
            save(OUT / f"{label}.npz", wf, x)
            (OUT / f"{label}.json").write_text(json.dumps({"history": history, **extra}, indent=1), encoding="utf-8")
    save(OUT / f"{label}.npz", wf, x)
    (OUT / f"{label}.json").write_text(json.dumps({"history": history, **extra}, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
