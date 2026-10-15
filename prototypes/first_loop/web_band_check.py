"""PROTOTYPE (LOP-27) - is the web between the cover's intermediate and output bores pressed against the height limit (the 24 mm band)?
On row 1's run (empty1): per plan column of the cover half, the metal's top (the highest voxel at 0.5 or more) against
the highest voxel the design space allows there (the band's top), across the line between the two bores at its middle,
and the share of the web's columns whose metal reaches the band's top."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "prototypes" / "first_loop"))

from outcome_cad import OUT  # noqa: E402

RUN = "topofree_compliance_tilt_5.5kg_4mm_projected_band24_cup_bolts_split_contract_drive_empty1_5.5kg_empty_hf6_single_flange_beds_sf1.15"
z = np.load(OUT / f"{RUN}.npz")
n, lo, h, ks = z["n"].astype(int), z["lo"].astype(float), float(z["h"]), int(z["k_split"])
modelled = np.zeros(int(np.prod(n)), bool)
modelled[z["elem"]] = True
metal = np.zeros(int(np.prod(n)), bool)
metal[z["elem"][z["frozen"].astype(bool)]] = True
metal[z["elem"][z["free_e"]]] = np.asarray(z["phys"]) >= 0.5
modelled, metal = modelled.reshape(n), metal.reshape(n)
zc = lo[2] + h * (np.arange(n[2]) + 0.5)
cov = np.arange(n[2]) >= ks
top_metal = np.where(metal & cov[None, None, :], zc[None, None, :], -np.inf).max(axis=2)
top_space = np.where(modelled & cov[None, None, :], zc[None, None, :], -np.inf).max(axis=2)
layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
b = {x["shaft"]: x for x in layout["bearings"] if x["side"] == "+z"}
A, B = np.array(b["intermediate"]["axis"]), np.array(b["output"]["axis"])
mid, d = 0.5 * (A + B), (B - A) / np.linalg.norm(B - A)
perp = np.array([-d[1], d[0]])
print("across the web at the middle between the intermediate and output bores (s: mm across, along +perp):")
print("   s   metal top  space top  pressed")
for s in range(-60, 61, 6):
    p = mid + s * perp
    i, j = int((p[0] - lo[0]) / h), int((p[1] - lo[1]) / h)
    if 0 <= i < n[0] and 0 <= j < n[1]:
        tm, ts = top_metal[i, j], top_space[i, j]
        print(f"{s:5d}  {tm:9.1f}  {ts:9.1f}  {'yes' if np.isfinite(tm) and tm >= ts - 1e-6 else ''}")
# the web's columns: within 30 mm of the segment, outside both bosses
xs = lo[0] + h * (np.arange(n[0]) + 0.5)
ys = lo[1] + h * (np.arange(n[1]) + 0.5)
PX, PY = np.meshgrid(xs, ys, indexing="ij")
t = np.clip(((PX - A[0]) * (B - A)[0] + (PY - A[1]) * (B - A)[1]) / ((B - A) @ (B - A)), 0, 1)
web = np.hypot(PX - (A[0] + t * (B - A)[0]), PY - (A[1] + t * (B - A)[1])) <= 30
for x in (b["intermediate"], b["output"]):
    web &= np.hypot(PX - x["axis"][0], PY - x["axis"][1]) > (1.25 * x["D"] + 10) / 2
has = web & np.isfinite(top_metal)
pressed = has & (top_metal >= top_space - 1e-6)
print(f"the web's columns with metal: {int(has.sum())}; pressed against the space's top: {int(pressed.sum())} ({100 * pressed.sum() / max(has.sum(), 1):.0f} %)")
