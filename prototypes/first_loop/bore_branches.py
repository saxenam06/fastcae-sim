"""The bore experiment's branches (LOP-24; the plan's §9 step 2, the engineer, 23:20): one bearing bore's
region given to explicit features in competing families, each written as a `--height-features` file for
`topo_free.py` (`topo.feature_map`), from the free run's evidence (`bore_spill.py`: where its metal
stands round the bore). The families, each with the bore's boss as a ring out to its trade boss radius
(and a cap behind the seat, where it is blind, at its own height):
- `spokes`: a wheel of radial ribs at a regular pitch, phased on the free run's fullest direction;
- `web`: a partial ring web over the free run's contiguous fullest span, then the same spokes;
- `ties`: ribs aimed at each neighbour (the half's other bores and the mounts), one a direction
  (a neighbour within `--merge` degrees of a nearer one is left to it).
Every rib starts at the boss's edge and ends at the region's edge (the boss radius plus `--reach`),
the free field carrying on from there. The optimiser sizes every feature: a ring's or a web's height,
a rib's root and tip heights; a feature it doesn't need it lowers to nothing.

    bore_branches.py <free run> [--half motor_side] [--bore intermediate] [--reach 40] [--width 8] [--pitch 30]

Writes data/first_loop/bore_<family>.json and prints each one's features."""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bore_spill  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
SECTORS = bore_spill.SECTORS


def fullest(sectors: list[float]) -> tuple[float, float, float]:
    """The free run's fullest direction (degrees, a sector's centre) and the contiguous span round it
    whose sectors hold at least half its metal (degrees, its edges)."""
    s = np.asarray(sectors, float)
    k = int(np.argmax(s))
    lo = hi = k
    while s[(lo - 1) % SECTORS] >= 0.5 * s[k] and (hi - lo + 1) < SECTORS:
        lo -= 1
    while s[(hi + 1) % SECTORS] >= 0.5 * s[k] and (hi - lo + 1) < SECTORS:
        hi += 1
    width = 360.0 / SECTORS
    return -180.0 + width * (k + 0.5), -180.0 + width * lo, -180.0 + width * (hi + 1)


def main(run: str, half: str, bore: str, reach: float, width: float, pitch: float, merge: float) -> dict:
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    side = "+z" if half == "cover" else "-z"
    me = next(b for b in lay["bearings"] if b["side"] == side and b["shaft"] == bore)
    rows = bore_spill.main(run)
    row = next(r for r in rows if r["half"] == half and r["shaft"] == bore)
    a_full, a0, a1 = fullest(row["sectors_mm"])
    boss = float(me["boss_r"])
    radius = boss + reach
    ring = [{"name": "cap", "kind": "ring", "r_in": 0.0, "r_out": 0.5 * float(me["D"])},  # behind a blind seat
            {"name": "boss", "kind": "ring", "r_in": 0.5 * float(me["D"]), "r_out": boss}]  # fmt: skip
    n_spokes = int(round(360.0 / pitch))
    spokes = [{"name": f"spoke {(a_full + pitch * i + 180.0) % 360.0 - 180.0:.0f}°", "kind": "rib",
               "angle": (a_full + pitch * i + 180.0) % 360.0 - 180.0, "r0": boss, "r1": radius, "width": width} for i in range(n_spokes)]  # fmt: skip
    web = {"name": f"web {a0:.0f}° to {a1:.0f}°", "kind": "sector", "r_in": boss, "r_out": boss + 0.5 * reach, "a0": a0, "a1": a1}
    ax, ay = me["axis"]
    others = [(f"the {b['shaft']} bore", b["axis"]) for b in lay["bearings"] if b["side"] == side and b is not me]
    others += [(m["name"], m["centre"]) for m in lay["mounts"]]
    others.sort(key=lambda o: math.hypot(o[1][0] - ax, o[1][1] - ay))
    ties, taken = [], []
    for name, (x, y) in others:
        ang = math.degrees(math.atan2(y - ay, x - ax))
        if any(abs((ang - t + 180.0) % 360.0 - 180.0) < merge for t in taken):
            continue
        taken.append(ang)
        ties.append({"name": f"tie to {name} ({ang:.0f}°)", "kind": "rib", "to": [x, y], "r0": boss, "r1": radius, "width": width})
    base = {"half": half, "bore": bore, "radius": radius,
            "evidence": {"run": run, "covered": round(row["covered"], 3), "fullest_deg": a_full, "span_deg": [a0, a1]}}  # fmt: skip
    branches = {"spokes": ring + spokes, "web": ring + [web] + spokes, "ties": ring + ties}
    out = {}
    for family, features in branches.items():
        spec = dict(base, family=family, features=features)
        path = OUT / f"bore_{family}.json"
        path.write_text(json.dumps(spec, indent=1), encoding="utf-8")
        out[family] = spec
        print(f"{path.name}: {', '.join(f['name'] for f in features)}")
    print(f"the {bore} bore ({half}): the region {radius:.1f} mm round its axis; the free run's fullest direction {a_full:.0f}°, "
          f"its span {a0:.0f}° to {a1:.0f}°")  # fmt: skip
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("--half", default="motor_side", choices=("motor_side", "cover"))
    ap.add_argument("--bore", default="intermediate")
    ap.add_argument("--reach", type=float, default=40.0, help="mm past the boss radius: the region's edge")
    ap.add_argument("--width", type=float, default=8.0, help="mm, every rib's width (two 4 mm voxels)")
    ap.add_argument("--pitch", type=float, default=30.0, help="degrees between spokes")
    ap.add_argument("--merge", type=float, default=15.0, help="degrees: a tie this near a nearer one's direction is left to it")
    a = ap.parse_args()
    main(a.run, a.half, a.bore, a.reach, a.width, a.pitch, a.merge)
