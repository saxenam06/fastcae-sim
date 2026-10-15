"""PROTOTYPE (LOP-30) - can a spline run's members reach each mount's lug under a cap on the members' height? (15 October
00:00: the section window, F2, capped every member at 32 mm and the first `spl5`'s mounts came loose.) For each lug, the
free voxels face-adjacent to its cubes and the least height (above its column's level) a column needs to hold one; then,
for each cap, whether each lug is joined face to face to the housing through the fixed metal and the free voxels a column
of at most that height holds, the columns the window leaves free (the mounts' reach discs) at their full height.

    lug_reach_probe.py <run stem> [--window <widths>:<caps>]

The run's set-up is rebuilt from its record (`build_free`), its spline rules with the window given (by default the
night's: 10:12:14:16:18:20:18:20:24:28:32:22:12, discs).
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
    from scipy.ndimage import label

    import topo
    from topo_free import build_free

    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--window", default="10:12:14:16:18:20:18:20:24:28:32:22:12")
    a = ap.parse_args()
    rec = json.loads((OUT / f"{a.run}.json").read_text(encoding="utf-8"))
    model = build_free(float(rec["voxel_mm"]), band=rec["band_mm"], flange=bool(rec["flange"]), mount_reach=rec["mount_reach"],
                       height_field=float(rec["height_field"]["radius_mm"]), empty=bool(rec["empty"]), protect=bool(rec["protect"]),
                       flange_whole=bool(rec.get("flange_whole", True)), drawing_clear=bool(rec.get("drawing_clear")),
                       couplings=rec.get("couplings", "glue"), shell_fixed=bool(rec.get("shell_fixed")), towers=bool(rec.get("towers", True)),
                       route=rec.get("route", "cast"), cavity=rec.get("cavity", "cup"))  # fmt: skip
    model["least_height_mm"], model["least_width_mm"] = rec.get("least_height_mm"), rec.get("least_width_mm")
    v_ = [float(s_) for s_ in a.window.split(":")]
    n_w = (len(v_) - 1) // 2
    model["spline"] = dict(rec["spline"], window={"widths_mm": v_[:n_w], "caps_mm": v_[n_w:]}, disc=True)
    vox = topo.Voxels(model)
    hh, sp_ = vox.height, vox.spline
    h, lo = float(model["h"]), np.asarray(model["lo"], float)
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    r_lug = 0.5 * float(lay["settings"]["mount_diameter"])
    ijk = vox.ijk
    centre = lo + h * (ijk + 0.5)
    free_e = vox.free_e
    free_pos = {tuple(ijk[e]): i for i, e in enumerate(free_e)}
    lugs = []
    for m in lay["mounts"]:
        cx, cy = m["centre"]
        z0, z1 = m["z"]
        inside = (np.hypot(centre[:, 0] - cx, centre[:, 1] - cy) <= r_lug) & (centre[:, 2] >= z0) & (centre[:, 2] <= z1)
        lugs.append(inside)
        need = []
        for c in ijk[inside]:
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                i = free_pos.get((int(c[0] + d[0]), int(c[1] + d[1]), int(c[2] + d[2])))
                if i is not None:
                    need.append(float(hh["pos"][i]) + 1.0)
        least = f"{h * min(need):.0f} mm" if need else "none beside it"
        print(f"{m['name']}: {int(inside.sum())} lug cubes, {len(need)} free voxels beside them; the least column height to hold one {least}")
    free_col = np.zeros(len(sp_["on_split"]), bool)
    if sp_["window"] is not None and sp_["window"]["free"] is not None:
        free_col[sp_["sub_col"][sp_["window"]["free"]]] = True
    print(f"the window leaves {int(free_col.sum()):,} columns their full height (the mounts' reach discs: "
          f"{[(d_['name'], round(d_['reach_mm'], 1)) for d_ in model.get('mount_discs') or []]})")  # fmt: skip
    n = [int(v) for v in model["n"]]
    frozen = np.zeros(len(ijk), bool)
    frozen[vox.frozen] = True
    for cap in (24.0, 32.0, 36.0, 40.0, 48.0, 64.0):
        for with_free in (False, True):
            grid = np.zeros(n, bool)
            grid[tuple(ijk[frozen].T)] = True
            ok_free = h * (np.asarray(hh["pos"], float) + 1.0) <= cap
            if with_free:
                ok_free |= free_col[np.asarray(hh["col"])]
            grid[tuple(ijk[free_e[ok_free]].T)] = True
            lab, _ = label(grid)
            sizes = np.bincount(lab.ravel())
            sizes[0] = 0
            main_ = int(np.argmax(sizes))
            joined = [main_ in set(lab[tuple(ijk[s_].T)].tolist()) for s_ in lugs]
            print(f"every column at most {cap:g} mm{' (the discs free)' if with_free else ''}: each lug joined to the housing {joined}")


if __name__ == "__main__":
    main()
