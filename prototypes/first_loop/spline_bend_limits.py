"""PROTOTYPE (LOP-30, F3) - the bending limits of a spline run's fields (`topo_free.py --spline-bend <json>`) as a share of
another run's own bending, field by field (the engineer, 14 October 23:01: half of `baseline2_spl3`'s). The run is rebuilt
under the spline rules the new run will have, so each field's bending is read in that run's units (with the smooth top a
height field's unit is its free end's span, `Voxels.spline_bending`).

    spline_bend_limits.py <run stem> <out json> [--share 0.5] [--top] [--window <spec>] [--disc] [--soft-dist] [--sizes <s>]

Writes {"outline0": .., "outline1": .., "split0": .., ...}: each field's bending (mm² over the knots' spacing², summed
squared second differences of the control points) times the share.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE.parents[1] / "data" / "first_loop"


def main() -> None:
    import topo
    from topo_free import build_free

    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--share", type=float, default=0.5)
    ap.add_argument("--top", action="store_true")
    ap.add_argument("--window", default="")
    ap.add_argument("--disc", action="store_true")
    ap.add_argument("--soft-dist", action="store_true")
    ap.add_argument("--sizes", type=float, default=0.0)
    a = ap.parse_args()
    rec = json.loads((OUT / f"{a.run}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{a.run}.npz")
    model = build_free(float(rec["voxel_mm"]), band=rec["band_mm"], flange=bool(rec["flange"]), mount_reach=rec["mount_reach"],
                       height_field=float(rec["height_field"]["radius_mm"]), empty=bool(rec["empty"]), protect=bool(rec["protect"]),
                       flange_whole=bool(rec.get("flange_whole", True)), drawing_clear=bool(rec.get("drawing_clear")),
                       couplings=rec.get("couplings", "glue"), shell_fixed=bool(rec.get("shell_fixed")), towers=bool(rec.get("towers", True)),
                       route=rec.get("route", "cast"), cavity=rec.get("cavity", "cup"))  # fmt: skip
    model["least_height_mm"], model["least_width_mm"] = rec.get("least_height_mm"), rec.get("least_width_mm")
    spec = dict(rec["spline"])
    if a.top:
        spec["top"] = True
    if a.window:
        v_ = [float(s_) for s_ in a.window.split(":")]
        n_w = (len(v_) - 1) // 2
        spec["window"] = {"widths_mm": v_[:n_w], "caps_mm": v_[n_w:]}
    if a.disc:
        spec["disc"] = True
    if a.soft_dist:
        spec["dist"] = "soft"
    if a.sizes > 0:
        spec["sizes"] = a.sizes
    model["spline"] = spec
    vox = topo.Voxels(model)
    x = np.asarray(z["x"], float)
    if len(x) != vox.n_design:
        raise SystemExit(f"{a.run} has {len(x)} design variables, the rebuilt model {vox.n_design}: not the same set-up")
    vals, _ = vox.spline_bending(x)
    out = {}
    for op, v_ in zip(vox.spline["bend_ops"], vals, strict=True):
        key = f"{'outline' if op['kind'] == 'outline' else op['family']}{op['half']}"
        out[key] = a.share * float(v_)
        print(f"{key:9s} {a.run[-40:]}'s bending {float(v_):10.4g}, the limit {a.share * float(v_):10.4g}")
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(Path(a.out))


if __name__ == "__main__":
    main()
