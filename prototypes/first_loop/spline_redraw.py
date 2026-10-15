"""PROTOTYPE (LOP-30) - a spline run's own design variables read under other spline rules, saved as a run of its own for
the drawing, with no optimisation. The geometry proof of the engineer's reviews (14 October 23:13): `baseline2_spl3`'s
fields read with the smooth top (F1, `--top`) and drawn, to see whether the stairs and the comb along the side walls go
when each member's free end is one surface rather than a height above each column's own level.

    spline_redraw.py <run stem> <new run stem> [--top] [--window <spec>] [--disc] [--soft-dist]
    spline_redraw.py <run stem> <new run stem> --state <checkpoint npz> --spec <spline spec json>

Writes data/first_loop/<new run stem>.npz and .json (the run's record, its spline rules updated, `redrawn_from` its
source). The same design variables mean other shapes under other rules (with F1 a height field's values are the free
end's place, not a height above a level): a proof of the rules' geometry, not a design. With `--state` and `--spec`
(15 October 01:07; the engineer: "If we stop now and see the drawing will I see the geometry") the design variables and
sharpness are a stopped run's checkpoint and its spline rules are the spec's (the record's `spline`), the run given only
for the set-up it shares: a running campaign's state drawn as it stands, not a finished design.
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
    ap.add_argument("new")
    ap.add_argument("--top", action="store_true")
    ap.add_argument("--window", default="")
    ap.add_argument("--disc", action="store_true")
    ap.add_argument("--soft-dist", action="store_true")
    ap.add_argument("--state", default="", help="a checkpoint's npz (x, beta): its design variables in place of the run's")
    ap.add_argument("--spec", default="", help="a spline spec's JSON in place of the run's (and of the flags)")
    a = ap.parse_args()
    rec = json.loads((OUT / f"{a.run}.json").read_text(encoding="utf-8"))
    z = np.load(a.state) if a.state else np.load(OUT / f"{a.run}.npz")
    model = build_free(float(rec["voxel_mm"]), band=rec["band_mm"], flange=bool(rec["flange"]), mount_reach=rec["mount_reach"],
                       height_field=float(rec["height_field"]["radius_mm"]), empty=bool(rec["empty"]), protect=bool(rec["protect"]),
                       flange_whole=bool(rec.get("flange_whole", True)), drawing_clear=bool(rec.get("drawing_clear")),
                       couplings=rec.get("couplings", "glue"), shell_fixed=bool(rec.get("shell_fixed")), towers=bool(rec.get("towers", True)),
                       route=rec.get("route", "cast"), cavity=rec.get("cavity", "cup"))  # fmt: skip
    model["least_height_mm"], model["least_width_mm"] = rec.get("least_height_mm"), rec.get("least_width_mm")
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8")) if a.spec else dict(rec["spline"])
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
    model["spline"] = spec
    vox = topo.Voxels(model)
    x, beta = np.asarray(z["x"], float), float(z["beta"])
    if len(x) != vox.n_design:
        raise SystemExit(f"{a.run} has {len(x)} design variables, the rebuilt model {vox.n_design}: not the same set-up")
    dens = vox.physical(x, beta)
    cols = vox.spline_columns(x, beta)
    z_setup = np.load(OUT / f"{a.run}.npz")  # the set-up's own (a checkpoint keeps only x and beta)
    extra = {"height_min": z_setup["height_min"]} if "height_min" in z_setup.files else {}
    extra.update({f"spl_{k}": v for k, v in cols.items()})
    np.savez_compressed(OUT / f"{a.new}.npz", phys=dens[vox.free_e], x=x, free_e=vox.free_e, elem=vox.elem, frozen=vox.frozen, ijk=vox.ijk,
                        lo=np.asarray(model["lo"]), n=np.asarray(model["n"]), h=float(model["h"]), k_split=int(model["k_split"]), beta=beta,
                        **extra)  # fmt: skip
    if a.state:
        note = f"a stopped run's checkpoint ({Path(a.state).name}: iteration {int(z['iteration'])}, beta {beta:g}); not finished"
    else:
        note = "its design variables read under other spline rules; not optimised"
    rec2 = dict(rec, spline=spec, redrawn_from=a.state or a.run, history=[], binary=None, objective=f"{rec.get('objective')} ({note})")
    (OUT / f"{a.new}.json").write_text(json.dumps(rec2, indent=1, default=float), encoding="utf-8")
    placed = float(dens[vox.free_e].sum()) * topo.DENSITY * float(model["h"]) ** 3
    src = f" (the source {float(np.asarray(z['phys']).sum()) * topo.DENSITY * float(model['h']) ** 3:.2f})" if "phys" in z.files else ""
    print(f"{a.new}: {placed:.2f} kg placed{src}; {note}")


if __name__ == "__main__":
    main()
