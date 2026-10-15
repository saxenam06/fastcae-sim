"""PROTOTYPE (LOP-17) - checks of `tobs.py` on the CPU, before any solve:
1. the runs: no free voxel in two runs, and how many the runs decide;
2. the start design from a field: castable along the pull (a fixed point of the anchored casting
   filter), and what the fill added to the field at 0.5;
3. single flips at the runs' ends keep a design castable;
4. one step of the integer program, on random derivatives of the real size: its flips obey the
   flip limit, the mass room, and per run the order and one side, and its z is the worst
   linearised ratio. Its time is printed.

Run: .venv/Scripts/python.exe prototypes/first_loop/tobs_check.py <start run stem>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
import tobs  # noqa: E402
from topo_free import OUT, build_free  # noqa: E402


def main(start: str) -> bool:
    z0 = np.load(OUT / f"{start}.npz")
    rec0 = json.loads((OUT / f"{start}.json").read_text(encoding="utf-8"))
    h = float(z0["h"])
    model = build_free(h, layout=rec0.get("layout", "grammar4"), band=rec0.get("band_mm"), joint="bolts", skin=rec0["skin"]["wall_mm"],
                       cavity=rec0.get("cavity", "cup"), penalty_ramp=0, route="split", flange=rec0.get("flange", False),
                       mount_reach=rec0.get("mount_reach") or "corridor")  # fmt: skip
    vox = topo.Voxels(model)
    t0 = time.time()
    runs = tobs.Runs(model["kind"], model["n"], model["k_split"], vox.elem, vox.free_e)
    ok = True
    allpos = np.concatenate([p[p >= 0] for p in runs.pos])
    dup = len(allpos) - len(np.unique(allpos))
    both = np.intersect1d(np.unique(allpos), runs.forced)
    print(f"1. {len(runs.pos):,} runs in {time.time() - t0:.1f} s; they decide {runs.decided:,} of {runs.n_free:,} free voxels, "
          f"{len(runs.forced):,} more forced metal; in two runs: {dup}, in a run and forced: {len(both)}; "
          f"neither: {runs.n_free - runs.decided - len(runs.forced):,}; longest run {runs.size.max()} voxels")  # fmt: skip
    ok &= dup == 0 and len(both) == 0
    phys = np.asarray(z0["phys"], float)
    lengths = runs.lengths_from(phys)
    x = runs.design(lengths)
    gap = tobs.castable(vox, x)
    plain = phys >= 0.5
    print(f"2. the start: {int(x.sum()):,} metal voxels against {int(plain.sum()):,} at 0.5 (the fill added {int((x > 0.5).sum() - (x > 0.5)[plain].sum())}, "
          f"left out {int(plain.sum() - (x > 0.5)[plain].sum())}); castable: {gap:.2e}")  # fmt: skip
    ok &= gap < 1e-6
    rng = np.random.default_rng(0)
    cands = runs.candidates(lengths, 1)
    worst = 0.0
    for i in rng.choice(len(cands), size=min(200, len(cands)), replace=False):
        r, s, _k, p = cands[i]
        x1 = x.copy()
        x1[p] = 1.0 if s > 0 else 0.0
        worst = max(worst, tobs.castable(vox, x1))
    print(f"3. 200 single flips at the runs' ends: the worst gap from castable {worst:.2e}")
    ok &= worst < 1e-6
    cands = runs.candidates(lengths, tobs.PER_RUN)
    sens = rng.normal(0.0, 1e-4, size=(12, runs.n_free))
    ratios = rng.uniform(1.0, 1.5, size=12)
    most, room = int(tobs.BETA * runs.n_free), 50.0
    chosen, z, seconds = tobs.flips(cands, sens, ratios, room, most, tobs.PER_RUN)
    sign = np.array([c[1] for c in cands], float)
    p = np.array([c[3] for c in cands])
    lin = ratios + (sens[:, p] * sign[None, :]) @ chosen.astype(float)
    per = {}
    for (r, s, k, _p), on in zip(cands, chosen, strict=True):
        if on:
            per.setdefault(r, []).append((s, k))
    order_ok = all(len({s for s, _ in v}) == 1 and sorted(k for _, k in v) == list(range(1, len(v) + 1)) for v in per.values())
    print(f"4. {len(cands):,} candidate flips: the program in {seconds:.1f} s chose {int(chosen.sum())} (limit {most}); mass change {sign @ chosen:+.0f} "
          f"(room {room:+.0f}); z {z:.5f} against the worst linearised ratio {lin.max():.5f} (from {ratios.max():.5f}); per run in order and one way: {order_ok}")  # fmt: skip
    ok &= bool(chosen.sum() <= most and sign @ chosen <= room + 1e-9 and abs(z - lin.max()) < 1e-6 and order_ok)
    print("all checks pass" if ok else "A CHECK FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1]) else 1)
