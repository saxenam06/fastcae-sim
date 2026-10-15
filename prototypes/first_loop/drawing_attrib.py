"""PROTOTYPE (LOP-29) - which of a drawing's differences from its field moves which seat: the run's own model solved on its
field, then on the field with the drawing's added metal (free voxels inside the drawing, under 0.5 in the field) near one
bearing only, one bearing at a time (each added voxel given to the nearest bearing on its side of the split, within its
boss and 30 mm more in plan; the rest 'elsewhere'), then with all of it, without the drawing's lost metal, and the drawing
itself. With `--seat "<shaft> <side>"` the metal added near that seat is split along it too: past its outer end, along
the seat, between the seat and the split. Statics only; every seat's tilt against its line and the worst seat printed.

`lop29_keep` (13 October 20:38): only the motor side's intermediate seat moved (0.66 in the field, 1.08 drawn), and only by
the 311 voxels added between it and the split, its gear room's floor drawn 4.9 mm where the optimiser had 4 (0.66 → 1.11
alone): the walls' faces were then drawn on the 2 mm cells' faces (`exact_walls.ramp` since).

Run: .venv/Scripts/python.exe prototypes/first_loop/drawing_attrib.py <design> [--seat "<shaft> <side>"]"""

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


def main(design: str, seat: str = "") -> None:
    import topo
    from grade import REFERENCE
    from model_vs_fe import inside_drawing
    from topo_free import build_free

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    run = rec["outcome_of"]
    rr = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    h = float(z["h"])
    model = build_free(h, band=rr.get("band_mm"), flange=bool(rr.get("flange")), mount_reach=rr.get("mount_reach") or "disc",
                       height_field=(rr.get("height_field") or {}).get("radius_mm"), empty=bool(rr.get("empty")),
                       protect=bool(rr.get("protect")), flange_whole=bool(rr.get("flange_whole")),
                       drawing_clear=bool(rr.get("drawing_clear")), couplings=rr.get("couplings") or "glue", shell_fixed=bool(rr.get("shell_fixed")), towers=bool(rr.get("towers", True)))  # fmt: skip
    model["cases"] = tuple(rr.get("cases") or ("peak drive",))
    model["beds_mm"] = {"peak drive": REFERENCE["peak drive"] / 1000.0}
    vox = topo.Voxels(model)
    if len(vox.elem) != len(z["elem"]) or not np.array_equal(vox.elem, z["elem"]):
        raise SystemExit(f"{run}: its model built again does not give its voxels")
    free = vox.free_e
    lo, ks = np.asarray(model["lo"], float), int(model["k_split"])
    centres = lo + h * (vox.ijk + 0.5)
    z_split = lo[2] + h * ks
    xyz = centres[free]
    field = np.asarray(z["phys"], float) >= 0.5
    drawn = inside_drawing(design, rec, centres, z_split)[free]
    added, lost = drawn & ~field, field & ~drawn
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    names = [f"{b['shaft']} {b['side']}" for b in lay["bearings"]]
    owner = np.full(len(xyz), -1)
    best = np.full(len(xyz), np.inf)
    for i, b in enumerate(lay["bearings"]):
        mine = (xyz[:, 2] < z_split) if b["side"] == "-z" else (xyz[:, 2] >= z_split)
        d = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
        take = mine & (d <= float(b["boss_r"]) + 30.0) & (d < best)
        owner[take], best[take] = i, d[take]
    label = lambda i: names[i] if i >= 0 else "elsewhere"  # noqa: E731
    print("seats: " + ", ".join(f"{i + 1} {n}" for i, n in enumerate(names)))
    print("added by region: " + ", ".join(f"{label(i)} {int((added & (owner == i)).sum())}" for i in range(-1, len(names))))
    print("lost by region:  " + ", ".join(f"{label(i)} {int((lost & (owner == i)).sum())}" for i in range(-1, len(names))))

    def read(name: str, metal: np.ndarray) -> None:
        dens = np.ones(len(vox.elem))
        dens[free] = metal.astype(float)
        a = vox.analyse(dens, "compliance_bound", adjoints=False)
        vox.release(a)
        beds = [float(v) * REFERENCE["peak drive"] for v in a["bed_vector"]]
        print(f"{name:40s} +{int((metal & ~field).sum()):5,} -{int((field & ~metal).sum()):4,}; tilts "
              f"{' '.join(f'{v:.2f}' for v in a['ratio_vector'])}; worst seat {max(beds):5.1f} µm", flush=True)  # fmt: skip

    read("field", field)
    for i in range(-1, len(names)):
        read(f"field + added near {label(i)}", field | (added & (owner == i)))
    if seat:
        i = names.index(seat)
        b = lay["bearings"][i]
        z0, z1 = b["z"]
        zz = xyz[:, 2]
        near = added & (owner == i)
        lower = b["side"] == "-z"
        bands = {"past its outer end": near & ((zz < z0) if lower else (zz > z1)), "along the seat": near & (zz >= z0) & (zz <= z1),
                 "between the seat and the split": near & ((zz > z1) if lower else (zz < z0))}  # fmt: skip
        for k, g in bands.items():
            read(f"field + {seat}: {k}", field | g)
    read("field + all added", field | added)
    read("field - all lost", field & ~lost)
    read("the drawing", drawn)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--seat", default="")
    a = ap.parse_args()
    main(a.design, a.seat)
