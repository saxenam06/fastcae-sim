"""PROTOTYPE (LOP-17) - TOBS: topology optimisation with every voxel metal or air at every step
(Sivapuram & Picelli 2018; the subproblem as Mamedes, Picelli & Labaki 2023 state it, read in
`docs/research/2026-10-10-tobs-binary-topology-optimisation.md`).

Why: the density optimiser (`topo.solve_model`) spends whatever grey it is allowed. At β 128 its
last 72 grey voxels (10 g) still halved its number, 0.75 against 1.45 as metal or air (10 October
11:16), so its search steers by a credit no casting has. Here the design is metal or air
throughout, and every number reported is a real shape's.

**The design.** Per run, metal from the run's anchor out to a length L, at least past its farthest
frozen voxel. A run is a column's stretch of modelled voxels along the pull, broken at the split
and wherever a voxel is not modelled, as the casting filter's runs are. Its anchor is its end
nearest the split. So every iterate is one piece from the joint out, castable in the two-part
mould by construction: a fixed point of the anchored casting filter, which is checked.

**Each iteration:**
1. FE of the design (`topo.Voxels.analyse`, both cases), and the 12 seat ratios' derivatives by
   adjoints. At SIMP's penalty 1 the derivative is the secant one: the first-order change a full
   flip from air to metal (or back) makes, for void and solid voxels alike. At metal or air the
   stiffness is the same as at penalty 3.
2. The derivatives filtered over the model's filter (radius `topo.FILTER` voxels) and averaged
   with the last accepted iteration's (BESO's and TOBS's stabilisation).
3. The flips, by an integer linear program (scipy's `milp`, HiGHS):
   - minimise z, the worst seat's linearised ratio, with every seat's ratio in both cases ≤ z;
   - the mass within its budget, moving at most `EPS` of itself a step when far from it (TOBS's
     relaxation);
   - at most `beta` × N flips (TOBS's truncation);
   - per run at most `PER_RUN` voxels added or removed at its far end, one way only.
4. FE of the proposal. It is kept if its worst seat is lower. Otherwise beta is halved and the
   program solved again from the same derivatives (a trust region on the flip limit).

Run: .venv/Scripts/python.exe prototypes/first_loop/tobs.py <start run stem> [iterations]
     [--budget 7.73] [--beta 0.01] [--per-run 2] [--tag t] [--check K]
`--check K` instead compares, for K single flips from the start, the predicted change of every
ratio (the secant derivative, unfiltered) with FE's, and stops.
Writes data/first_loop/tobs_<...>.npz/.json/.png in topo_free.py's format (phys 0 or 1), so
outcome_cad.py, voxel_vs_fe.py and field_and_cad.py read it unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from topo_free import OUT, build_free, full_speed  # noqa: E402

say = topo.say
OBJECTIVE = "misalignment_bound"
BETA = 0.01  # the flip limit, a fraction of the free voxels (TOBS's truncation; 0.05 in the papers' 3D cantilever)
EPS = 0.01  # the mass moves at most this fraction of itself a step toward its budget (TOBS's relaxation)
PER_RUN = 2  # voxels a run may grow or shrink by in one step
MILP_SECONDS = 15.0  # the integer program's time limit a solve: its best found so far is taken; FE checks every step


class Runs:
    """The model's runs, each from its anchor outward, and the design as one length a run.
    `pos[r]` holds the run's voxels' free positions (index into `Voxels.free_e`; -1 for a frozen
    voxel), `least[r]` the length reaching past its farthest frozen voxel."""

    def __init__(self, kind: np.ndarray, n: np.ndarray, k_split: int, elem: np.ndarray, free_e: np.ndarray):
        grid_to_free = np.full(int(np.prod(n)), -1)
        grid_to_free[elem[free_e]] = np.arange(len(free_e))
        modelled = (np.asarray(kind) >= 0).reshape(tuple(n))  # the model keeps `kind` flat
        self.pos, self.least = [], []
        forced = []  # free voxels in runs metal throughout (a frozen voxel at the far end): always metal
        for i in range(n[0]):
            for j in range(n[1]):
                col = modelled[i, j]
                k = 0
                while k < n[2]:
                    if not col[k]:
                        k += 1
                        continue
                    start = k
                    k += 1
                    while k < n[2] and col[k] and k != k_split:
                        k += 1
                    seg = np.arange(start, k)
                    order = seg if start >= k_split else seg[::-1]  # from the anchor, the end nearest the split
                    flat = (i * n[1] + j) * n[2] + order
                    fp = grid_to_free[flat]
                    frozen_at = np.flatnonzero(fp < 0)
                    least = int(frozen_at[-1]) + 1 if len(frozen_at) else 0
                    if least < len(fp):  # a run with something free to decide
                        self.pos.append(fp)
                        self.least.append(least)
                    else:
                        forced.append(fp[fp >= 0])
        self.least = np.array(self.least)
        self.size = np.array([len(p) for p in self.pos])
        self.n_free = len(free_e)
        self.forced = np.concatenate(forced) if forced else np.zeros(0, int)
        covered = np.concatenate([p[p >= 0] for p in self.pos])
        self.decided = len(np.unique(covered))  # free voxels some run decides (the forced runs' are always metal)

    def lengths_from(self, phys: np.ndarray) -> np.ndarray:
        """Each run's length from a field: out to its farthest voxel at 0.5 or more, at least its
        least (everything between the anchor and that voxel filled, as the casting filter fills)."""
        out = np.empty(len(self.pos), int)
        for r, p in enumerate(self.pos):
            metal = (p < 0) | ((p >= 0) & (phys[np.maximum(p, 0)] >= 0.5))
            last = np.flatnonzero(metal)
            out[r] = max(self.least[r], int(last[-1]) + 1 if len(last) else 0)
        return out

    def design(self, lengths: np.ndarray) -> np.ndarray:
        """The free voxels' 0 or 1 for the runs' lengths (the forced runs' always 1)."""
        x = np.zeros(self.n_free)
        x[self.forced] = 1.0
        for r, p in enumerate(self.pos):
            q = p[: lengths[r]]
            x[q[q >= 0]] = 1.0
        return x

    def candidates(self, lengths: np.ndarray, per_run: int):
        """The flips one step may make: (run, sign, depth, free position); sign +1 adds the voxel
        at depth k past the run's end, -1 removes the k-th from its end."""
        out = []
        for r, p in enumerate(self.pos):
            L = lengths[r]
            for k in range(1, per_run + 1):
                if L + k - 1 < len(p):
                    out.append((r, 1, k, int(p[L + k - 1])))
            for k in range(1, per_run + 1):
                if L - k >= self.least[r]:
                    out.append((r, -1, k, int(p[L - k])))
        return out


def flips(cands, sens: np.ndarray, ratios: np.ndarray, mass_room: float, most: int, per_run: int):
    """The integer program: which candidate flips (0 or 1 each) minimise z subject to every
    linearised ratio <= z, the mass change <= mass_room (voxels), at most `most` flips, and per
    run its flips contiguous at its end and one way only. Returns (chosen 0/1, z, seconds)."""
    from scipy.optimize import Bounds, LinearConstraint, milp

    m = len(cands)
    if m == 0:
        return np.zeros(0, bool), float(ratios.max()), 0.0
    run = np.array([c[0] for c in cands])
    sign = np.array([c[1] for c in cands], float)
    depth = np.array([c[2] for c in cands])
    p = np.array([c[3] for c in cands])
    a = sens[:, p] * sign[None, :]  # (ratios, candidates): the linear change of each ratio
    nr = len(ratios)
    # rows: the ratios (a y - z <= -r), the mass, the flip count
    dense = sp.csr_matrix(np.hstack([a, -np.ones((nr, 1))]))
    mass_row = sp.csr_matrix(np.r_[sign, 0.0][None, :])
    count_row = sp.csr_matrix(np.r_[np.ones(m), 0.0][None, :])
    # per run: y(k+1) <= y(k) on each side, and one side only
    rows, cols, vals = [], [], []
    nrow = 0
    index = {(int(run[i]), int(sign[i]), int(depth[i])): i for i in range(m)}
    for (r, s, k), i in index.items():
        if k >= 2 and (r, s, k - 1) in index:
            rows += [nrow, nrow]
            cols += [i, index[(r, s, k - 1)]]
            vals += [1.0, -1.0]
            nrow += 1
        if s == 1 and k == 1 and (r, -1, 1) in index:
            rows += [nrow, nrow]
            cols += [i, index[(r, -1, 1)]]
            vals += [1.0, 1.0]
            nrow += 1
    order_rows = sp.csr_matrix((vals, (rows, cols)), shape=(nrow, m + 1))
    # an order row (entries 1 and -1) is <= 0; a one-side row (1 and 1) is <= 1
    sums = np.asarray(order_rows.sum(axis=1)).ravel()
    upper_order = np.where(sums > 1.5, 1.0, 0.0)
    a_all = sp.vstack([dense, mass_row, count_row, order_rows]).tocsr()
    lower = np.full(a_all.shape[0], -np.inf)
    upper = np.r_[-ratios, mass_room, float(most), upper_order]
    tiny = 1e-7 * max(float(ratios.max()), 1e-9)  # fewer flips break ties
    c = np.r_[np.full(m, tiny), 1.0]
    t0 = time.time()
    res = milp(c, constraints=LinearConstraint(a_all, lower, upper), integrality=np.r_[np.ones(m), 0.0],
               bounds=Bounds(np.r_[np.zeros(m), 0.0], np.r_[np.ones(m), np.inf]),
               options={"time_limit": MILP_SECONDS, "mip_rel_gap": 1e-3, "disp": False})  # fmt: skip
    seconds = time.time() - t0
    if res.x is None:
        return None, float("nan"), seconds
    chosen = res.x[:m] > 0.5
    return chosen, float(res.x[m]), seconds


def sensitivities(vox, d_ratios: np.ndarray, x: np.ndarray) -> np.ndarray:
    """The ratios' derivatives at the free voxels as BESO and TOBS take them: a metal voxel's own
    secant derivative, an empty voxel's from its metal neighbours through the filter. An empty
    voxel's own value comes from displacements in the soft void round it. It is wrong, in sign
    and up to a thousand times in size: 4 of 5 additions in the check, 10 October 11:49 (FE
    -0.0027 against -1.53 predicted). Removals came out right in sign, at about half FE's change."""
    raw = d_ratios[:, vox.free_e] * (x[None, :] > 0.5)
    return np.asarray((vox.hmat @ raw.T).T) / vox.hs[None, :]


def apply(lengths: np.ndarray, cands, chosen) -> np.ndarray:
    new = lengths.copy()
    for (r, s, _k, _p), on in zip(cands, chosen, strict=True):
        if on:
            new[r] += s
    return new


def named(vox, vector) -> dict:
    return {f"{k[0][0]} {k[0][1]} case {k[1]}": float(v) for k, v in zip(vox.keys, vector, strict=True)}


def castable(vox, x: np.ndarray) -> float:
    """How far the design is from a fixed point of the anchored casting filter: 0 when every run
    is one piece from its anchor out."""
    dens = np.ones(len(vox.elem))
    dens[vox.free_e] = x
    return float(np.abs(vox.cast[0](dens)[vox.free_e] - x).max())


def main(start: str, iterations: int = 100, budget: float = 7.73, beta0: float = BETA, per_run: int = PER_RUN,
         tag: str = "", check: int = 0) -> None:  # fmt: skip
    t_all = time.time()
    fast = full_speed()
    z0 = np.load(OUT / f"{start}.npz")
    rec0 = json.loads((OUT / f"{start}.json").read_text(encoding="utf-8"))
    h = float(z0["h"])
    skin = rec0["skin"]["wall_mm"] if isinstance(rec0.get("skin"), dict) else None
    model = build_free(h, layout=rec0.get("layout", "grammar4"), band=rec0.get("band_mm"), joint="bolts", skin=skin,
                       cavity=rec0.get("cavity", "cup"), penalty_ramp=0, route="split", flange=rec0.get("flange", False),
                       mount_reach=rec0.get("mount_reach") or "corridor")  # fmt: skip
    vox = topo.Voxels(model)
    if len(z0["phys"]) != len(vox.free_e):
        raise ValueError(f"{start}: {len(z0['phys']):,} free voxels, the model {len(vox.free_e):,}")
    runs = Runs(model["kind"], model["n"], model["k_split"], vox.elem, vox.free_e)
    lengths = runs.lengths_from(np.asarray(z0["phys"], float))
    x = runs.design(lengths)
    vox_kg = topo.DENSITY * h**3
    target = (budget - model["frozen_kg"]) / vox_kg  # the free metal's budget, voxels
    gap = castable(vox, x)
    say(f"TOBS from {start}: {len(runs.pos):,} runs decide {runs.decided:,} of {runs.n_free:,} free voxels; the start as metal or air "
        f"{x.sum() * vox_kg:.3f} kg placed (budget {target * vox_kg:.3f}); castable along the pull: {'yes' if gap < 1e-6 else f'no ({gap:.2e})'}"
        f"{'' if fast else ' (full speed not granted)'}")  # fmt: skip

    def solve(x_, adjoints: bool):
        dens = np.ones(len(vox.elem))
        dens[vox.free_e] = x_
        return vox.analyse(dens, OBJECTIVE, 1.0, adjoints=adjoints)

    state = solve(x, True)
    say(f"the start: worst {state['ratio_vector'].max():.4f}x its line (voxel model, metal or air)")
    if check:
        # the secant prediction of single flips against FE's change
        rng = np.random.default_rng(10)
        cands = runs.candidates(lengths, 1)
        picks = rng.choice(len(cands), size=min(check, len(cands)), replace=False)
        r0 = state["ratio_vector"]
        sens = sensitivities(vox, state["d_ratios"], x)  # what the program steps by
        rows = []
        for i in picks:
            r, s, k, p = cands[i]
            x1 = x.copy()
            x1[p] = 1.0 if s > 0 else 0.0
            t = solve(x1, False)
            vox.release(t)
            true = t["ratio_vector"] - r0
            pred = s * sens[:, p]
            j = int(np.argmax(np.abs(true)))
            rows.append({"flip": "add" if s > 0 else "remove", "voxel": int(p), "seat": list(named(vox, true))[j],
                         "true": float(true[j]), "predicted": float(pred[j]), "worst_true": float(t["ratio_vector"].max() - r0.max())})  # fmt: skip
            say(f"  {rows[-1]['flip']:6s} voxel {p:6d}: largest change at {rows[-1]['seat']}: FE {true[j]:+.5f}, predicted {pred[j]:+.5f}; worst {rows[-1]['worst_true']:+.5f}")
        t_ = np.array([q["true"] for q in rows])
        p_ = np.array([q["predicted"] for q in rows])
        corr = float(np.corrcoef(t_, p_)[0, 1]) if len(rows) > 2 else float("nan")
        say(f"the secant prediction against FE over {len(rows)} flips: correlation {corr:.3f}, ratio of sums {p_.sum() / t_.sum() if t_.sum() else float('nan'):.3f}")
        (OUT / f"tobs_check_{start}.json").write_text(json.dumps({"start": start, "flips": rows, "correlation": corr}, indent=1), encoding="utf-8")
        return

    stem = f"tobs_{OBJECTIVE}_{budget:g}kg_{h:g}mm_cup_bolts_skin4_split" + (f"_{tag}" if tag else "")
    history = []
    sens_prev = None
    beta = beta0
    best_x, best = x.copy(), state
    stale = 0
    for it in range(1, iterations + 1):
        t0 = time.time()
        r = state["ratio_vector"]
        filtered = sensitivities(vox, state["d_ratios"], x)
        sens = filtered if sens_prev is None else 0.5 * (filtered + sens_prev)
        m = float(x.sum())
        if target < (1 - EPS) * m:
            room = -EPS * m
        elif target > (1 + EPS) * m:
            room = EPS * m
        else:
            room = target - m
        cands = runs.candidates(lengths, per_run)
        kept = False
        tries = 0
        while not kept:
            most = int(beta * runs.n_free)
            if most < 1:
                break
            chosen, z_pred, t_milp = flips(cands, sens, r, room, most, per_run)
            tries += 1
            if chosen is None or not chosen.any():
                say(f"it {it:3d}: the program found no flip that helps (beta {beta:.4g}); stopping")
                most = 0
                break
            new_lengths = apply(lengths, cands, chosen)
            x_new = runs.design(new_lengths)
            trial = solve(x_new, False)
            worse = trial["ratio_vector"].max() >= r.max()
            if worse:
                vox.release(trial)
                say(f"it {it:3d}: {int(chosen.sum())} flips promised {z_pred:.4f}, FE {trial['ratio_vector'].max():.4f} >= {r.max():.4f}: refused, beta {beta:.4g} -> {beta / 2:.4g}")
                beta /= 2
                continue
            kept = True
            state = vox.finish(trial)
            n_add = int(sum(1 for c, on in zip(cands, chosen, strict=True) if on and c[1] > 0))
            n_rem = int(chosen.sum()) - n_add
            lengths, x, sens_prev = new_lengths, x_new, sens
            row = {"iteration": it, "worst": float(state["ratio_vector"].max()), "predicted": z_pred, "mass_kg": float(x.sum() * vox_kg),
                   "added": n_add, "removed": n_rem, "beta": beta, "tries": tries, "milp_seconds": t_milp, "seconds": time.time() - t0,
                   "ratios": named(vox, state["ratio_vector"])}  # fmt: skip
            history.append(row)
            seat = max(row["ratios"], key=row["ratios"].get)
            say(f"it {it:3d}: worst {row['worst']:.4f}x its line at {seat} (metal or air; predicted {z_pred:.4f}), mass {row['mass_kg']:.3f} kg, "
                f"+{n_add}/-{n_rem} voxels, beta {beta:.4g}, {tries} {'try' if tries == 1 else 'tries'}, program {t_milp:.1f} s, {row['seconds']:.1f} s")  # fmt: skip
            improved = best["ratio_vector"].max() - row["worst"]  # a kept step is always the best so far
            best_x, best = x.copy(), state
            stale = stale + 1 if improved < 1e-3 * row["worst"] else 0
            beta = min(beta0, 1.5 * beta)
            if it % 10 == 0:
                np.savez_compressed(OUT / f"{stem}_checkpoint.npz", x=x, lengths=lengths, iteration=it)
        if not kept or stale >= 8:
            if stale >= 8:
                say(f"it {it:3d}: 8 iterations each under 0.1 % better; stopping")
            break
    x, state = best_x, best
    gap = castable(vox, x)
    worst = float(state["ratio_vector"].max())
    say(f"done: worst {worst:.4f}x its line as metal or air, {x.sum() * vox_kg:.3f} kg placed; castable along the pull: {'yes' if gap < 1e-6 else f'no ({gap:.2e})'}")
    np.savez_compressed(OUT / f"{stem}.npz", phys=x, x=x, free_e=vox.free_e, elem=vox.elem, frozen=vox.frozen, ijk=vox.ijk,
                        lo=model["lo"], n=model["n"], h=h, k_split=model["k_split"], beta=np.inf)  # fmt: skip
    record = {"layout": rec0.get("layout", "grammar4"), "objective": OBJECTIVE, "budget_kg": budget, "frozen_kg": model["frozen_kg"],
              "voxel_mm": h, "cavity": rec0.get("cavity", "cup"), "joint": vox.joint_note, "skin": model["skin"],
              "element": "hex8 with Wilson's incompatible modes", "factor": "fe.py's single-precision factor, refined", "route": "split",
              "casting": "each run one piece from its end at the split out (by construction)",
              "method": {"name": "TOBS", "beta": beta0, "eps": EPS, "per_run": per_run, "filter_voxels": topo.FILTER, "milp": "scipy HiGHS"},
              "projection": None, "penalty_ramp": 0, "band_mm": rec0.get("band_mm"), "start": start, "history": history,
              "ratios": named(vox, state["ratio_vector"]), "binary": {"worst": worst, "ratios": named(vox, state["ratio_vector"]),
              "metal_voxels": int(x.sum()), "mass_kg": float(x.sum() * vox_kg)}, "unknowns": vox.n_dof, "seconds": time.time() - t_all}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    topo.picture(model, {"ijk": vox.ijk, "frozen": vox.frozen, "elem": vox.elem, "free_e": vox.free_e, "phys": x}, OUT / f"{stem}.png",
                 f"TOBS, {OBJECTIVE}, {budget:g} kg")  # fmt: skip
    say(f"done in {time.time() - t_all:.0f} s; {stem}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="TOBS: the housing's field with every voxel metal or air (prototype).")
    ap.add_argument("start", help="the run whose field starts this one (its voxels at 0.5)")
    ap.add_argument("iterations", nargs="?", type=int, default=100)
    ap.add_argument("--budget", type=float, default=7.73, help="the whole housing's mass, kg")
    ap.add_argument("--beta", type=float, default=BETA, help="the flip limit, a fraction of the free voxels")
    ap.add_argument("--per-run", type=int, default=PER_RUN, help="voxels a run may grow or shrink by a step")
    ap.add_argument("--tag", default="")
    ap.add_argument("--check", type=int, default=0, help="compare the predicted and FE change of K single flips, then stop")
    a = ap.parse_args()
    main(a.start, a.iterations, a.budget, a.beta, a.per_run, a.tag, a.check)
