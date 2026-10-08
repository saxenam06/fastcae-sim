"""PROTOTYPE (LOP) - a designer's hypothesis, not an optimiser's reading.

The binding seats are the intermediate's tapered pair, and their tilt comes from the shaft's
axial thrust (12 kN on the -z seat in reverse) bending the end walls out of their plane round the
bosses. So: radial ribs round each of the intermediate's two bosses, on its own pod's end faces,
out to the pod's rim, `count` of them, `height` tall and `thickness` thick.

Run: uv run python prototypes/first_loop/hypothesis.py <stem> [end_wall] [count] [height] [thickness]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lobed  # noqa: E402
import read  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"


def radial_ribs(base: str, shafts=("intermediate",), count=8, height=20.0, thickness=6.0):
    info = json.loads((OUT / f"{base}.json").read_text(encoding="utf-8"))
    pods = {p["shaft"]: p for p in info["pods"]}
    ribs = []
    for b in info["bearings"]:
        if b["shaft"] not in shafts:
            continue
        pod = pods[b["shaft"]]
        start = b["D"] / 2 + info["settings"]["boss"]
        z_base = pod["z"][0] if b["side"] == "-z" else pod["z"][1]
        for k in range(count):
            a = 2 * math.pi * (k + 0.5) / count
            rim = read.rim_point([tuple(p) for p in pod["outer"]], tuple(b["axis"]), a)
            if rim is None:
                continue
            first = (b["axis"][0] + start * math.cos(a), b["axis"][1] + start * math.sin(a))
            if math.dist(first, rim) < 8:
                continue
            ribs.append({"face": b["side"], "a": first, "b": rim, "height": height,
                         "thickness": thickness, "z_base": z_base, "pod": b["shaft"]})  # fmt: skip
    return ribs


def main(stem: str, end_wall: float = 6.0, count: int = 8, height: float = 20.0, thickness: float = 6.0):
    overrides = {"end_wall": end_wall}
    base = lobed.build(f"{stem}_base", overrides=overrides)  # for the pods' outlines
    ribs = radial_ribs(f"{stem}_base", count=count, height=height, thickness=thickness)
    result = lobed.build(stem, ribs=ribs, overrides=overrides)
    print(f"{stem}: {len(ribs)} ribs, {result['mass_kg']['total']:.3f} kg (base {base['mass_kg']['total']:.3f} kg)")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], *(float(v) if i != 1 else int(v) for i, v in enumerate(a[1:])))
