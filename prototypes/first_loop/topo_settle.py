"""PROTOTYPE (LOP-16) - does the update settle where run 2's did not? Optimality criteria on the
misalignment's p-norm against GCMMA on the bound formulation, each started from run 2's last
field at full sharpness (beta 16), in run 2's own model: the rooms each their own cylinder, the
halves glued, the skin the whole voxel, the penalty 3 (`topo_free.build_free(6, cavity="rooms",
joint="glued", skin=0, penalty_ramp=0)` rebuilds it exactly: 6,604 frozen voxels, 3.71 kg).

Run 2 ended alternating every iteration, 0.159 <-> 0.196, its worst seat swapping between the
input's two bearings with the step at its limit. The start here is its last densities taken as
the design (a field at beta 16 passes the filter and the projection nearly unchanged), so both
updates begin where the alternation was. OC runs with today's late settings (steps 0.05, damping
0.3: run 3's, which alternated too).

Run: .venv/Scripts/python.exe prototypes/first_loop/topo_settle.py [iterations]
     (default 10 each: about 1 min for OC, 5-10 min for GCMMA at 6 mm; writes
     data/first_loop/topofree_settle_6mm.json)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from topo import OUT, say  # noqa: E402
from topo_free import build_free, full_speed  # noqa: E402

RUN2 = "topofree_misalignment_7.73kg_6mm_projected"


def main(iterations: int = 10) -> None:
    full_speed()
    model = build_free(6.0, cavity="rooms", joint="glued", skin=0.0, penalty_ramp=0)
    kind = model["kind"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    run2 = np.load(OUT / f"{RUN2}.npz")
    same = np.array_equal(run2["elem"], elem) and np.array_equal(run2["free_e"], free_e)
    say(f"run 2's voxels and this model's {'agree' if same else 'DIFFER'}: {len(free_e):,} free")
    assert same, "the model is not run 2's"
    start = np.asarray(run2["phys"], float)
    free_kg = 7.73 - model["frozen_kg"]
    record = {}
    for objective in ("misalignment", "misalignment_bound"):
        t0 = time.time()
        result = topo.solve_model(model, free_kg, 160 + iterations, objective, start=start, beta0=16.0, first=161)
        rows = result["history"]
        record[objective] = {"seconds": time.time() - t0, "history": [{k: r[k] for k in ("iteration", "objective", "worst_ratio", "worst_seat", "change", "mass_kg") if k in r} for r in rows]}
    (OUT / "topofree_settle_6mm.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"\n{'':4s} {'OC: p-norm':>11s} {'worst':>7s} {'seat':24s} {'change':>7s}   {'GCMMA: worst':>12s} {'seat':24s} {'change':>7s} {'kg':>6s}")
    oc, gc = record["misalignment"]["history"], record["misalignment_bound"]["history"]
    for i in range(max(len(oc), len(gc))):
        a = oc[i] if i < len(oc) else None
        b = gc[i] if i < len(gc) else None
        left = f"{a['objective']:11.4f} {a['worst_ratio']:7.4f} {a['worst_seat']:24s} {a['change']:7.3f}" if a else " " * 53
        right = f"{b['worst_ratio']:12.4f} {b['worst_seat']:24s} {b['change']:7.3f} {b['mass_kg']:6.3f}" if b else ""
        print(f"{(a or b)['iteration']:4d} {left}   {right}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
