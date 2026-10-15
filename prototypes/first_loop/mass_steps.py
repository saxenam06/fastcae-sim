"""Where the mesh route's drawing gains its mass, step by step (LOP-23; the engineer, 11 October
13:22: "why drawing lands higher than the optimization?"). The run is drawn again by
`outcome_cad.build_mesh` with its steps taken away one at a time: the root fillet, the members' level
below 0.5, the column fill from the split, the one-cell closing. What is left is set against the
optimiser's own metal-or-air field and its fixed metal. `mass_where.py` says where a drawing's extra
metal lies; this says which step put it there.

Each drawing goes to `data/first_loop/probe/` (no listing reads it), and the table to
`probe/mass_steps_<run>.json`.

Measured on `outcome_free24_4mm_7.3kg`'s run (11 October 13:32): 8.34 kg drawn against 7.32; the
fillet +0.48 kg, the closing +0.34, the level 0.45 +0.20, the column fill +0.03; with none of them
7.28 kg.

Run: .venv/Scripts/python.exe prototypes/first_loop/mass_steps.py <run stem>"""

import json
import sys
import time

import numpy as np
import outcome_cad as oc


def without(original, column: bool, closing: bool):
    """`skin_metal` with its column fill and its closing each kept or taken away (no fillet)."""
    from scipy.ndimage import binary_closing, generate_binary_structure

    if column and closing:
        return original

    def metal(p, level):
        m = p["fixed"] | ((p["members"] >= level) & p["side"] & ~p["cavity"])
        if closing:
            m = binary_closing(np.pad(m, 1), structure=generate_binary_structure(3, 1))[1:-1, 1:-1, 1:-1]
        return m & ~p["clear"] & p["side"]

    return metal


# (name, the fillet's radius in mm, the members' level or None for the drawing's own, the column fill, the closing)
STEPS = (
    ("as drawn", 4.0, None, True, True),
    ("no root fillet", 0.0, None, True, True),
    ("no fillet, level 0.5", 0.0, 0.5, True, True),
    ("no fillet, 0.5, no column fill", 0.0, 0.5, False, True),
    ("no fillet, 0.5, no column fill, no closing", 0.0, 0.5, False, False),
)


def main(run: str) -> dict:
    out = oc.OUT
    (out / "probe").mkdir(exist_ok=True)
    rec = json.loads((out / f"{run}.json").read_text(encoding="utf-8"))
    z = np.load(out / f"{run}.npz")
    h = float(z["h"])
    density = json.loads((out / f"{oc.layout_of(run)}.json").read_text(encoding="utf-8"))["settings"]["density"]
    placed = float((z["phys"] >= 0.5).sum()) * h**3 * density
    fixed = rec["frozen_kg"]
    print(f"{run}: the optimiser's metal-or-air field places {placed:.3f} kg on {fixed:.3f} kg fixed, {placed + fixed:.3f} kg", flush=True)
    original_metal, original_level, original_fillet = oc.skin_metal, oc.member_level, oc.ROOT_FILLET
    rows = []
    try:
        for i, (name, fillet, level, column, closing) in enumerate(STEPS):
            t0 = time.time()
            oc.ROOT_FILLET = fillet
            oc.member_level = original_level if level is None else (lambda h_, wall_, lv=level: lv)
            oc.skin_metal = without(original_metal, column, closing)
            r = oc.build_mesh(run, f"probe/step{i}")
            rows.append({"step": name, "kg": r["mass_kg"]["total"], "level": r["skin"]["members_level"]})
            print(f"[{time.time() - t0:.0f} s] {name}: {r['mass_kg']['total']:.3f} kg, the members read at {r['skin']['members_level']:.3f}", flush=True)
    finally:
        oc.skin_metal, oc.member_level, oc.ROOT_FILLET = original_metal, original_level, original_fillet
    print("each step's mass (taken away in turn):")
    for a, b in zip(rows, rows[1:]):
        print(f"  {a['step']} -> {b['step']}: {a['kg'] - b['kg']:+.3f} kg")
    print(f"  left over the optimiser's {placed + fixed:.3f} kg: {rows[-1]['kg'] - placed - fixed:+.3f} kg")
    result = {"run": run, "placed_kg": placed, "fixed_kg": fixed, "rows": rows}
    (out / "probe" / f"mass_steps_{run}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


if __name__ == "__main__":
    main(sys.argv[1])
