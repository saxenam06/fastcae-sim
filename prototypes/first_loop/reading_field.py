"""PROTOTYPE (LOP-28) - the designer's reading put back into the field, to be judged: does a housing drawn as the reading
says (each member's straight runs, each one width and one height off the wall: `member_map.runs_of`) keep the design's
lines? A run of the optimiser is copied with its placed metal beyond the least walls replaced: under each run's footprint
(within half its width of its centre-line, round-ended) each column holds the run's height, and nothing elsewhere; the
least walls, the protected interfaces and the fixed spokes stay as they were. What the reading leaves out goes: metal
under 4 mm proud of its wall, crumbs, metal hugging the protected features.

Writes data/first_loop/<run>_reading.npz and .json (the run's record, marked), for `propose.py <design> --run <run>_reading`
(drawn and judged as any design: the same environment as the design's).

Run: .venv/Scripts/python.exe prototypes/first_loop/reading_field.py <design>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OUT = HERE.parents[1] / "data" / "first_loop"


def main(design: str, keep: tuple[str, ...] = (), label: str = "reading", deep: bool = False) -> str:
    import exact_walls
    import topo
    from member_map import _seg_dist

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    run = rec["outcome_of"]
    mm = json.loads((OUT / f"member_map_{design}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    n = z["n"].astype(int)
    h, lo, ks = float(z["h"]), z["lo"].astype(float), int(z["k_split"])
    elem, free_e, frozen = z["elem"], z["free_e"], z["frozen"].astype(bool)
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, _, _ = topo.height_columns(kind, n, ks, elem, free_e)
    need = exact_walls._height_min(run, z)[elem[free_e]]
    tmin = np.zeros(int(col.max()) + 1)
    np.maximum.at(tmin, col, need)
    least = np.ceil(tmin[col] - 1e-6)
    ijk = z["ijk"][free_e]
    xs, ys = lo[0] + h * (np.arange(n[0]) + 0.5), lo[1] + h * (np.arange(n[1]) + 0.5)
    px, py = np.meshgrid(xs, ys, indexing="ij")
    cells = np.stack([px.ravel(), py.ravel()], axis=1)
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    lug_z = {m["name"]: float(m["z"][0]) for m in layout["mounts"]}
    reach = {}
    lug_web = np.full(n[:2], np.inf)  # the motor side's columns filled from the split down to a lug's far end
    for half, d in mm["halves"].items():  # each half's columns: the reading's metal beyond the least wall, in voxels
        vox = np.zeros(n[:2], np.int64)
        for m_ in d["members"]:
            for r_ in m_["runs"]:
                a, b = np.asarray(r_["from_mm"], float), np.asarray(r_["to_mm"], float)
                inside = (_seg_dist(cells, a, b) <= r_["width_mm"] / 2).reshape(n[:2])
                if r_.get("meets") in lug_z:  # a lug's web spans the lug: it joins it from the side, over its length
                    lug_web = np.where(inside, np.minimum(lug_web, lug_z[r_["meets"]]), lug_web)
                # the run's height tapers from its start to its end (a bracket deepens toward its lug); with `deep`, the
                # designer's rule instead: each run as tall as its deep part (the 90th percentile of its metal's heights)
                t = np.clip(((cells - a) @ (b - a)) / max(float((b - a) @ (b - a)), 1e-9), 0.0, 1.0).reshape(n[:2])
                tall = r_["height_from_mm"] + (r_["height_to_mm"] - r_["height_from_mm"]) * t
                if deep:
                    tall = np.maximum(tall, r_.get("height_deep_mm", r_["height_mm"]))
                vox = np.where(inside, np.maximum(vox, np.rint(tall / h).astype(np.int64)), vox)
        reach[half] = vox
    lower = ijk[:, 2] < ks
    target = least + np.where(lower, reach["motor_side"][ijk[:, 0], ijk[:, 1]], reach["cover"][ijk[:, 0], ijk[:, 1]])
    # the protected features' own surroundings stay as the run has them (as `member_map` leaves them out of the members):
    # within 2 mm of each boss, bolt's boss and lug, where the members' roots meet them (without them mount-3's arm parted
    # from its lug, 13 October 04:02)
    s = layout["settings"]
    prot = {half: np.zeros(n[:2], bool) for half in ("cover", "motor_side")}
    for half, side in (("cover", "+z"), ("motor_side", "-z")):
        for b in layout["bearings"]:
            if b["side"] == side:
                prot[half] |= np.hypot(px - b["axis"][0], py - b["axis"][1]) <= float(b["boss_r"]) + 2.0
        for c in layout["bolts"]:
            prot[half] |= np.hypot(px - c[0], py - c[1]) <= s["bolt_boss"] / 2 + 2.0
    for m in layout["mounts"]:
        prot["motor_side"] |= np.hypot(px - m["centre"][0], py - m["centre"][1]) <= s["mount_diameter"] / 2 + 2.0
    # members of the kinds in `keep` (e.g. the arms to the lugs) stay as the run has them: their own cells, at their own heights
    for half, d in mm["halves"].items():
        for m_ in d["members"]:
            if m_["kind"] in keep and m_.get("cells_ij"):
                ij = np.asarray(m_["cells_ij"], int)
                prot[half][ij[:, 0], ij[:, 1]] = True
    kept = np.where(lower, prot["motor_side"][ijk[:, 0], ijk[:, 1]], prot["cover"][ijk[:, 0], ijk[:, 1]])
    phys = np.asarray(z["phys"], float).copy()
    beyond = (pos >= least) & ~kept
    before = float((phys[pos >= least] >= 0.5).sum())
    phys[beyond] = (pos[beyond] < target[beyond]).astype(float)
    # a lug's web: the motor side's columns under it filled from the split down to the lug's far end (the lug hangs 33-63 mm
    # under the split with its bolt's room kept clear above it, so a web joins it only from the side: 13 October 04:08)
    z_vox = lo[2] + h * (ijk[:, 2] + 0.5)
    web = lower & beyond & (z_vox >= lug_web[ijk[:, 0], ijk[:, 1]])
    phys[web] = 1.0
    after = float((phys[pos >= least] >= 0.5).sum())
    stem = f"{run}_{label}"
    np.savez_compressed(OUT / f"{stem}.npz", **{k: z[k] for k in z.files if k != "phys"}, phys=phys)
    run_rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    run_rec["reading_of"] = {"design": design, "run": run, "note": "the placed metal beyond the least walls replaced by the "
                             "designer's reading (member_map.runs_of): each run one width and a tapered height", "kept_kinds": list(keep),
                             "voxels_before": before, "voxels_after": after}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(run_rec, indent=1), encoding="utf-8")
    print(f"{stem}: the metal beyond the least walls {before * h**3 / 1000:.0f} cm³ in the run, {after * h**3 / 1000:.0f} cm³ in the reading")
    return stem


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="The designer's reading put back into the field (LOP-28).")
    ap.add_argument("design")
    ap.add_argument("--keep", default="", help="member kinds kept as the run has them, e.g. arm or arm,network")
    ap.add_argument("--label", default="reading", help="the new run's suffix (default reading)")
    ap.add_argument("--deep", action="store_true", help="each run as tall as its deep part (its 90th percentile), not tapered")
    a = ap.parse_args()
    main(a.design, tuple(k.strip() for k in a.keep.split(",") if k.strip()), a.label, a.deep)
