"""The pull-interval census (LOP-23, 11 October 14:05): in every field on today's set-up, how many
columns along the pull hold more than one run of metal (fixed or placed at 0.5) in a half, and how
much metal lies past each column's first run. Columns within a vehicle bracket's room in plan (the
mounts' lugs, a declared exception) are counted apart. The relief route (flow D, proposed in
docs/features/product/2026-10-11-cad-from-a-free-optimisation.md) rests on this being near zero.

Measured 14:05: 98 of 185,845 columns (0.05 %) outside the lugs, at most 0.044 kg a field.

Run: .venv/Scripts/python.exe prototypes/first_loop/interval_census.py"""

import json
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
density = layout["settings"]["density"]
mount_xy = {m["name"]: m["centre"] for m in layout["mounts"]}
brackets = [(b.get("centre") or mount_xy[b["name"].split(" bracket")[0]], b["radius"]) for b in layout.get("brackets", [])]

rows = []
for f in sorted(OUT.glob("topofree_*.json")):
    if "checkpoint" in f.name:
        continue
    try:
        rec = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        continue
    if not isinstance(rec, dict) or rec.get("layout") != "contract" or not rec.get("flange") or not (OUT / f"{f.stem}.npz").exists():
        continue
    z = np.load(OUT / f"{f.stem}.npz")
    n, h, lo, ks = z["n"].astype(int), float(z["h"]), z["lo"], int(z["k_split"])
    metal = np.zeros(int(np.prod(n)), bool)
    metal[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    metal[z["elem"][z["frozen"].astype(bool)]] = True
    metal = metal.reshape(tuple(n))
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    lug = np.zeros(X.shape, bool)
    for (cx, cy), r in brackets:
        lug |= np.hypot(X - cx, Y - cy) <= r + h
    multi, extra, multi_lug, extra_lug, cols = 0, 0, 0, 0, 0
    for lower in (True, False):
        # each half ordered from the split outward (the motor side's split is at its top)
        half = metal[:, :, :ks][:, :, ::-1] if lower else metal[:, :, ks:]
        starts = half & ~np.concatenate([np.zeros(half.shape[:2] + (1,), bool), half[:, :, :-1]], axis=2)
        runs = starts.sum(axis=2)
        cols += int((runs > 0).sum())
        # the metal past each column's first run (the run nearest the split)
        past = (half & (np.cumsum(starts, axis=2) > 1)).sum(axis=2)
        for mask, add in ((~lug, 0), (lug, 1)):
            m_ = (runs > 1) & mask
            if add:
                multi_lug += int(m_.sum())
                extra_lug += int(past[mask].sum())
            else:
                multi += int(m_.sum())
                extra += int(past[mask].sum())
    kg = lambda v: v * h**3 * density  # noqa: E731
    rows.append((f.stem, h, cols, multi, kg(extra), multi_lug, kg(extra_lug)))

print(f"{len(rows)} fields on today's set-up (contract layout, split flange)")
print(f"{'field':72s} {'mm':>3s} {'columns':>8s} {'multi':>6s} {'kg past':>8s} {'lug cols':>8s} {'lug kg':>7s}")
for stem, h, cols, multi, ex, ml, el in rows:
    print(f"{stem[9:81]:72s} {h:3.0f} {cols:8d} {multi:6d} {ex:8.3f} {ml:8d} {el:7.3f}")
tot = np.array([[r[2], r[3], r[4]] for r in rows])
print(f"outside the lugs: {int(tot[:, 1].sum())} of {int(tot[:, 0].sum())} columns hold two runs or more ({100 * tot[:, 1].sum() / tot[:, 0].sum():.2f} %), "
      f"{tot[:, 2].sum() / len(rows):.3f} kg a field past the first run on average, at most {tot[:, 2].max():.3f} kg")
