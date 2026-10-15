"""How much of each region of an iteration's design space the optimiser filled (LOP-24; the engineer,
11 October 20:16: stop when the features are nearly filled). For a height-field run inside a design
space (`topo_free.py --space`), region by region: the share of its plan under a member (a column at
least 4 mm high), the members' mean height, and the share of its volume within the height envelope
the metal fills. Meaningful when the metal was not forced (the least-metal objective, `mass_tilt`).

    space_fill.py <run> [<regions file>]   (the regions default to the run's own `space`)

Prints a line a region and writes data/first_loop/fill_<run's design-space label>.json."""

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
import topo_free as tf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0


def main(run: str, regions_path: str | None) -> None:
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    regions_path = regions_path or rec.get("space")
    if not regions_path:
        raise SystemExit(f"{run}: no design space given and none in its record")
    regions = tf.space_regions(regions_path)
    band = float(rec.get("band_mm") or 24.0)
    ch = shh.column_heights(run)
    h, lo = ch["h"], ch["lo"]
    x0, y0 = float(lo[0]), float(lo[1])
    rows = []
    for half in ("motor_side", "cover"):
        big = ndi.zoom(ch[half], h, order=3)
        X, Y = np.meshgrid(x0 + np.arange(big.shape[0]) + 0.5, y0 + np.arange(big.shape[1]) + 0.5, indexing="ij")
        pts = np.column_stack([X.ravel(), Y.ravel()])
        for reg in regions["halves"].get(half, []):
            inside = MPath(np.asarray(reg["outline"], float)).contains_points(pts)
            for hole in reg.get("holes", []):
                inside &= ~MPath(np.asarray(hole, float)).contains_points(pts)
            inside = inside.reshape(big.shape)
            area = float(inside.sum())  # mm², a 1 mm grid
            if area <= 0:
                continue
            hgt = np.clip(big[inside], 0.0, band)
            member = hgt >= MEMBER
            rows.append({"half": half, "region": reg["name"], "area_cm2": area / 100.0,
                         "covered": float(member.mean()), "mean_height_mm": float(hgt[member].mean()) if member.any() else 0.0,
                         "volume_fill": float(hgt.sum() / (area * band))})  # fmt: skip
    label = Path(regions_path).stem
    out = OUT / f"fill_{label}_{run[-40:]}.json"
    out.write_text(json.dumps({"run": run, "regions": regions_path, "rows": rows}, indent=1), encoding="utf-8")
    print(out)
    for r in rows:
        print(f"  {r['half']}: {r['region']}: {r['area_cm2']:.0f} cm², covered {100 * r['covered']:.0f} %, members' mean height "
              f"{r['mean_height_mm']:.0f} mm, volume filled {100 * r['volume_fill']:.0f} %")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
