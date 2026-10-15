"""The optimisation the final recipe runs (moved from `prototypes/first_loop/topo_free.py`: `main`,
`run_stem`, and `topo.py`: `solve_model`, `_uniform_start`, `_flat`; only the final recipe's path;
LOP-16 to LOP-29, LOP-33).

The least metal (`mass_tilt`, the engineer, 11 October 20:04) on the voxel model (`setup.build`,
`voxels.Voxels`): the metal placed is the objective, the budget only a ceiling, and held at once:
- every seat's misalignment in every case at most its line over the factor of safety;
- every seat's bed at most the design to beat's over the safety, in the graded cases;
- the greatest member (a ball round each free voxel at most 0.6 metal, read near its worst ball:
  sections, never lumps);
- the modes clear of the gear orders by the margin, and each of the lowest six at least the first
  mode's floor.
Solved by GCMMA (`mma`) with every function's derivative taken back to the design variables in one
pass; SIMP's penalty ramped from 1 to 3 over the first `PENALTY_RAMP` iterations; the projection's
sharpness raised by √2 as soon as the design settles at it with every mode limit held (at most
`EVERY` iterations after the last), up to `BETA_MOST`; the run stops once settled at the last. Every
run ends with the binary check: the field at 0.5, all metal or air, read by the same model.

Every `SAVE_EVERY` iterations the field as it stands is checked (the binary check) and saved as a
run of its own, `<stem>_it<N>`, which can be drawn and judged later (`--run`). A stop asked for
while it runs (the file `stop_<design>` in the folder: the Run panel's stop, the engineer, 15
October) ends it after the iteration under way, checked and saved as if it had settled.

The method's fixed settings are the agreed baseline's (`propose.py`'s, since 11 October); the
recipe's optimiser arguments give the rest, and only those (`parse`).
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.housing import say
from zenryx.domains.gearbox.housing.mma import MMA
from zenryx.domains.gearbox.housing.setup import PROJECTION, build
from zenryx.domains.gearbox.housing.voxels import (
    FLOOR_MODES,
    MODE_COUNT,
    PENAL,
    Voxels,
    gear_orders,
    greatest_share,
    local_ball,
    mode_gaps,
)
from zenryx.workflow.grade import GRADED_CASES, REFERENCE

OBJECTIVE = "mass_tilt"
CASES = ("peak drive",)
ITERATIONS = 200
PENALTY_RAMP = 20  # iterations over which SIMP's penalty rises from 1 to 3
SETTLE, EVERY, BETA_MOST = (
    0.02,
    25,
    32.0,
)  # the sharpening: settled at a step under SETTLE, at most EVERY at one sharpness
BETA_STEP = (
    2.0**0.5
)  # with the modes held the sharpness rises by this a step (a doubling cut a lug loose at once)
MEMBER_ALPHA = 0.6  # the greatest member: a ball's share of placed metal at most this
# GCMMA's most inner iterations (each one more solve, no adjoints) before a step is taken anyway,
# and its test: a step is taken when every function there stays within PROMISE of the subproblem's
PROMISE, INNER_MOST = 1e-3, 2
SAVE_EVERY = 50  # iterations between the saved states (the engineer, 15 October)
# settled: the objective within a share of itself over a window of iterations at one sharpness;
# SETTLE_BETA moves on to the next sharpness, SETTLE_STOP ends the run at the last
SETTLE_WINDOW, SETTLE_BETA, SETTLE_STOP = 5, 0.005, 0.002


def parse(args: list[str]) -> argparse.Namespace:
    """The recipe's optimiser arguments. The set-up flags must all be given: the moved code holds
    that set-up alone."""
    ap = argparse.ArgumentParser(prog="optimise", description="The final recipe's optimisation.")
    ap.add_argument("--objective", choices=[OBJECTIVE], required=True)
    for flag in ("--empty", "--protect", "--shell-fixed", "--no-towers"):
        ap.add_argument(flag, action="store_true", required=True)
    for opt in (
        "--max-member",
        "--band",
        "--height-field",
        "--safety",
        "--modes",
        "--first-mode",
        "--least-width",
    ):
        ap.add_argument(opt, type=float, required=True)
    return ap.parse_args(args)


def _flat(history: list[dict], window: int, share: float) -> bool:
    """The objective (each row's `bound`) moved less than `share` of itself over the last `window`
    rows."""
    if len(history) < window:
        return False
    f = [float(row["bound"]) for row in history[-window:]]
    return max(f) - min(f) <= share * abs(f[-1])


def _uniform_start(vox: Voxels, target: float, beta: float) -> np.ndarray:
    """The uniform design whose densities weigh the budget (in voxels): a feasible start for MMA."""
    lo_v, hi_v = 0.0, 1.0
    for _ in range(40):
        mid = 0.5 * (lo_v + hi_v)
        if vox.physical(np.full(vox.n_design, mid), beta)[vox.free_e].sum() > target:
            hi_v = mid
        else:
            lo_v = mid
    return np.full(vox.n_design, 0.5 * (lo_v + hi_v))


def solve(
    model: dict,
    budget_kg: float,
    iterations: int = ITERATIONS,
    stop: Path | None = None,
    on_save: Callable[[dict, int], None] | None = None,
) -> dict:
    """GCMMA over the model's free voxels under a mass ceiling (kg of free voxels): the least metal
    with every line held. Returns the field (`phys`, `x`), the history and the binary check."""
    vox = Voxels(model)
    h, density = model["h"], vox.density
    free_e, frozen, elem = vox.free_e, vox.frozen, vox.elem
    beta = 1.0
    target = budget_kg / density / h**3
    greatest = model["max_member"]
    share_ball, share_cells = local_ball(vox.ijk[free_e], greatest["radius_vox"])
    say(
        f"the greatest member: {greatest['mm']:g} mm, a ball of {greatest['radius_vox']:.2f} "
        f"voxels ({share_cells} cells) at most "
        f"{greatest['alpha']:g} metal"
    )

    def share_of(dens_all):
        return greatest_share(
            share_ball, share_cells, dens_all[free_e], greatest["alpha"], greatest["p"]
        )

    # the modes held clear of the gear orders, read on each analysis's factor, as constraints after
    # the beds
    mode_orders, mode_margin = (
        gear_orders(model["spec"], model["chain"]),
        float(model["modes"]["margin"]),
    )
    mode_floor = float(model["modes"]["first"])
    say(
        "the modes held clear of the gear orders: "
        + ", ".join(f"{nm} {f_:.0f} Hz ± {100 * mode_margin:g} %" for nm, f_ in mode_orders.items())
        + f"; the lowest {FLOOR_MODES} modes each at least {mode_floor:.0f} Hz; "
        + f"{vox.mode_count} modes read each analysis"
    )

    def modes_of(state):
        return mode_gaps(
            state["modes_hz"], state["d_modes_hz"], mode_orders, mode_margin, mode_floor
        )

    x = _uniform_start(vox, target, beta)
    say(
        f"{OBJECTIVE} objective; {len(vox.held)} nodes held at the mounts; {len(vox.seats)} seats "
        f"watched; budget {budget_kg:.3f} kg of free voxels"
    )

    def penalty_at(it: int) -> float:
        """SIMP's penalty at iteration `it`: from 1 to 3 in steps of 0.5 over the ramp, then 3."""
        return min(PENAL, 1.0 + 0.5 * math.floor(4.0 * (it - 1) / PENALTY_RAMP))

    def grey_of(dens_free):
        return float(
            ((dens_free > 0.1) & (dens_free < 0.9)).sum() / max(1, (dens_free > 0.1).sum())
        )

    def named(rat):
        return {f"{k[0][0]} {k[0][1]} case {k[1]}": v for k, v in rat.items()}

    def checked(x, beta, done: int, note: str, stopped: int | None = None) -> dict:
        """The field at x as a run: its densities and the binary check (the field at 0.5, all metal
        or air, read by the same model), after `done` iterations."""
        phys = vox.physical(x, beta)[free_e]
        # the binary check: the field at 0.5, all metal or air, read by the same model
        dens_bin = np.ones(len(elem))
        dens_bin[free_e] = (phys >= 0.5).astype(float)
        b_ = vox.with_modes(vox.analyse(dens_bin, PENAL, adjoints=False))
        vox.release(b_)
        binary = {
            "worst": float(b_["ratio_vector"].max()),
            "ratios": named(b_["ratios"]),
            "metal_voxels": int((phys >= 0.5).sum()),
            "mass_kg": float((phys >= 0.5).sum()) * density * h**3,
            "value": float(b_["value"]),
            "shares": False,
            "greatest_share": share_of(dens_bin)[2],
            "beds": named(b_["beds"]),
            "bed_worst": float(b_["bed_vector"].max()),
            "modes_hz": [round(float(v_), 1) for v_ in b_["modes_hz"]],
            "mode_gaps": [float(v_) for v_ in modes_of(b_)[0]],
        }
        say(
            "the binary check: the nominal field at 0.5, all metal or air, reads "
            f"{binary['worst']:.4f}x its line (voxel model), "
            f"{binary['mass_kg']:.3f} kg placed, compliance {binary['value']:.1f} N mm, "
            "the worst bed "
            f"{binary['bed_worst']:.4f}x the "
            f"design to beat's, the greatest member's share {binary['greatest_share']:.3f}, modes "
            + ", ".join(f"{v_:.0f}" for v_ in binary["modes_hz"][:10])
            + " Hz, gaps "
            + ", ".join(f"{v_:+.3f}" for v_ in binary["mode_gaps"])
        )
        return {
            "phys": phys,
            "x": x,
            "free_e": free_e,
            "elem": elem,
            "frozen": frozen,
            "ijk": vox.ijk,
            "history": history,
            "n_dof": vox.n_dof,
            "ratios": named(state["ratios"]),
            "joint": vox.joint_note,
            "beta": beta,
            "binary": binary,
            "settled": note,
            "stopped_at": stopped,
            "iteration": done,
        }

    history = []
    settled = ""
    stopped_at = None
    n_tilt, n_beds = len(vox.keys), len(vox.bed_keys)
    n_modes = 2 * len(mode_orders) + FLOOR_MODES
    first_mode = 2 + n_tilt + n_beds
    mode_rows = slice(first_mode, first_mode + n_modes)
    m = (
        2 + n_tilt + n_beds + n_modes
    )  # the mass, the greatest member, the tilts, the beds, the modes
    # GCMMA's convexity terms carried a tenth over between iterations: the seats' gradients gather
    # on the voxels round them
    opt = MMA(
        vox.n_design,
        m,
        0.0,
        1.0,
        a0=1.0,
        a=np.zeros(m),
        c=np.full(m, 1000.0),
        d=np.ones(m),
        carry=0.1,
    )
    mma_move = PROJECTION["mma_move"]
    scale = 10.0  # the objective, the metal's share of the ceiling, scaled to 10

    def realised(x_at, penal_at: float, with_adjoints: bool) -> dict:
        if not np.all(np.isfinite(x_at)):  # a design with NaN handed to the factoriser hung it
            raise RuntimeError(
                f"the design variables are not all finite: {int((~np.isfinite(x_at)).sum())} of "
                f"{len(x_at)}"
            )
        d_ = vox.physical(x_at, beta)
        if not np.all(np.isfinite(d_)):
            raise RuntimeError(
                f"the densities are not all finite: {int((~np.isfinite(d_)).sum())} of {len(d_)}"
            )
        o_ = vox.analyse(d_, penal_at, adjoints=with_adjoints)
        o_["dens"] = d_
        return o_

    state, state_settings = None, None
    since = 0  # iterations at the current sharpness
    for it in range(1, iterations + 1):
        t0 = time.time()
        penal = penalty_at(it)
        factors = 0
        if state is None or state_settings != (beta, penal):
            # the problem changed (the start, a sharper projection, a higher penalty): the point's
            # functions afresh
            state = realised(x, penal, True)
            state_settings = (beta, penal)
            factors += 1
            say(
                f"it {it:3d}: beta {beta:g}, p {penal:.2f}: the point read afresh, worst "
                f"{state['ratio_vector'].max():.4f}x its line "
                f"(voxel model), mass {state['dens'][free_e].sum() * density * h**3:.3f} kg"
            )
        # every function at the point and its derivative, taken back to x in one pass: the
        # objective, the mass, the greatest member, every seat's tilt and bed, the modes, in that
        # order
        s_ = state
        f0 = scale * float(s_["dens"][free_e].sum()) / target
        rows_d = [scale * vox.mass_rows[None, :] / target, vox.mass_rows[None, :] / target]
        g = [s_["dens"][free_e].sum() / target - 1.0]
        g_s, d_s, _ = share_of(s_["dens"])
        d_all = np.zeros(len(elem))
        d_all[free_e] = d_s
        rows_d.append(d_all[None, :])
        g.append(g_s)
        rows_d.append(s_["d_ratios"])
        g.extend(s_["ratio_vector"] - 1.0)
        rows_d.append(s_["d_beds"])
        g.extend(s_["bed_vector"] - 1.0)
        g_m, d_gm, _ = modes_of(s_)
        rows_d.append(d_gm)
        g.extend(g_m)
        back_all = vox.back(np.vstack(rows_d), x, beta)
        df0, dg, g = back_all[0], back_all[1:], np.asarray(g, float)
        move = mma_move / math.sqrt(beta)
        t1 = time.time()
        x_new = opt.propose(x, f0, df0, g, dg, move=move)
        t_mma = time.time() - t1
        # GCMMA: the proposal's promise checked by one solve there; while an approximation fell
        # below its function, that approximation is made more convex and the step re-solved
        inner = 0
        while True:
            last_try = inner >= INNER_MOST
            trial = realised(x_new, penal, False)
            factors += 1
            mass_new = trial["dens"][free_e].sum() / target - 1.0
            f0_new = scale * (mass_new + 1.0)
            g_new = np.r_[
                mass_new,
                share_of(trial["dens"])[0],
                trial["ratio_vector"] - 1.0,
                trial["bed_vector"] - 1.0,
                g[mode_rows] + dg[mode_rows] @ (x_new - x),
            ]
            kept = opt.conservative(f0_new, g_new, promise=PROMISE)
            if kept or last_try:
                break
            vox.release(trial)
            t1 = time.time()
            x_new = opt.tighten(f0_new, g_new, promise=PROMISE)
            t_mma += time.time() - t1
            inner += 1
        trial = vox.finish(trial)  # the adjoints at the point taken, on its factor
        change = float(np.abs(x_new - x).max())
        x, state = x_new, trial
        r = state["ratio_vector"]
        worst = max(state["ratios"].items(), key=lambda kv: kv[1])
        worst_seat = f"{worst[0][0][0]} {worst[0][0][1]} case {worst[0][1]}"
        free_now = state["dens"][free_e]
        grey = grey_of(free_now)
        clock = state["clock"]
        z_bound = (
            float(free_now.sum()) * density * h**3
        )  # the objective itself: the metal placed, kg
        active = int(np.sum(r >= 0.98 * r.max()))
        share_now = share_of(state["dens"])[2]
        modes_g, _, modes_note = modes_of(state)
        row = {
            "iteration": it,
            "objective": worst[1],
            "change": change,
            "worst_ratio": worst[1],
            "greatest_share": share_now,
            "modes_hz": [round(float(v_), 1) for v_ in state["modes_hz"]],
            "mode_gaps": [float(v_) for v_ in modes_g],
            "worst_seat": worst_seat,
            "beta": beta,
            "penalty": penal,
            "grey_share": grey,
            "seconds": time.time() - t0,
            "mass_kg": z_bound,
            "move": move,
            "ratios": named(state["ratios"]),
            "bound": z_bound,
            "active": active,
            "inner": inner,
            "conservative": bool(kept),
            "factors": factors,
            "mma_seconds": t_mma,
            "newton_steps": opt.last["newton_steps"],
            "clock": {k: round(v, 3) for k, v in clock.items()},
            "solve_steps": state["steps"],
            "bed_worst": float(state["bed_vector"].max()),
        }
        say(
            f"it {it:3d}: worst {worst[1]:.4f}x its line at {worst_seat} (voxel model), metal "
            f"placed (kg) {z_bound:.4f}, "
            f"the worst bed {row['bed_worst']:.4f}x the design to beat's; greatest member's share "
            f"{share_now:.3f} (at most {greatest['alpha']:g}); "
            "modes "
            + ", ".join(f"{v_:.0f}" for v_ in state["modes_hz"][:10])
            + " Hz, gaps "
            + ", ".join(f"{v_:+.3f}" for v_ in modes_g)
            + f" (modes {clock.get('modes', 0.0):.1f} s); {active} within 2 % of it, "
            + f"change {change:.3f} (move {move:.3f}), beta {beta:g}, "
            f"p {penal:.2f}, grey {grey:.2f}; {inner} "
            f"inner{'' if kept else ' (not yet conservative, taken)'}, {factors} factors, "
            f"{row['seconds']:.1f} s"
        )
        history.append(row)
        since += 1
        sharpest = beta >= BETA_MOST
        # The sharpness rises as soon as the design settles at it (a step under SETTLE, or the
        # result flat; at least 5 iterations at this sharpness and the full penalty) with every mode
        # limit held, at most EVERY after the last. At the last sharpness the run stops when no
        # voxel moves (a step under 0.01) or, every limit held, the result is flat within
        # SETTLE_STOP.
        here = history[-since:] if since else []
        flat_beta = since >= SETTLE_WINDOW and _flat(here, SETTLE_WINDOW, SETTLE_BETA)
        flat_stop = since >= SETTLE_WINDOW and _flat(here, SETTLE_WINDOW, SETTLE_STOP)
        held = share_now <= greatest["alpha"] + 0.005 and float(modes_g.max()) <= 0.005
        modes_ok = float(modes_g.max()) <= 0.005
        due = since >= EVERY or (
            since >= 5 and (change < SETTLE or flat_beta) and penal >= PENAL and modes_ok
        )
        if due and not sharpest:
            if not modes_ok:
                say(
                    f"the sharpness raised at iteration {it} with a mode limit still broken "
                    f"({float(modes_g.max()):+.3f}): "
                    f"{EVERY} iterations at beta {beta:g}"
                )
            beta = min(beta * BETA_STEP, BETA_MOST)
            if beta > BETA_MOST * 0.999:
                beta = BETA_MOST
            since = 0
        elif it > 10 and sharpest and penal >= PENAL and (change < 0.01 or (flat_stop and held)):
            settled = f"settled at iteration {it}: " + (
                f"no voxel moves more than {change:.3f}"
                if change < 0.01
                else f"the result within {100 * SETTLE_STOP:g} % of itself over the last "
                f"{SETTLE_WINDOW} iterations at beta {beta:g}"
            )
            say(settled)
            break
        if on_save is not None and it % SAVE_EVERY == 0 and it < iterations:
            # the field as it stands, checked and saved; Lanczos's start kept, so the run goes on as
            # before
            start = getattr(vox, "_mode_start", None)
            on_save(checked(x, beta, it, ""), it)
            vox._mode_start = start
        if stop is not None and stop.exists():
            stopped_at = it
            settled = f"stopped at iteration {it} by the engineer: the field as it stood"
            say(settled)
            break
    return checked(x, beta, len(history), settled, stopped_at)


def stem_of(
    design: str, budget: float, h: float, a: argparse.Namespace, member_p: float, least_mm: float
) -> str:
    """A run's file stem: its objective, budget and voxel, then its model's choices (as every run's
    since 14 October, so a run made here reads as the prototype's)."""
    tag = (
        f"split_contract_drive_{design}_empty_shell_notowers_protect"
        f"_modes{100 * a.modes:g}_fm{a.first_mode:g}_hf{a.height_field:g}"
        f"_single_p{member_p:g}_max{a.max_member:g}_flange_beds_lm{least_mm:g}_lw{a.least_width:g}_sf{a.safety:g}"
    )
    return f"topofree_{OBJECTIVE}_{budget:g}kg_{h:g}mm_projected_band{a.band:g}_cup_bolts_{tag}"


def run(
    design: str,
    budget: float,
    voxel: float,
    args: list[str],
    out: Path,
    contract: Path,
    env: Mapping[str, str],
    iterations: int = ITERATIONS,
) -> tuple[str, str]:
    """The optimisation on the layout record (`out/contract.json`): writes `<stem>.npz` (the field)
    and `<stem>.json` (its record). Returns the stem and the settling note ('' if it did not
    settle)."""
    t0 = time.time()
    a = parse(args)
    member_p, least_mm = float(env["LOOP_MEMBER_P"]), float(env["LOOP_LEAST_MEMBER"])
    spec, refusals = load_and_validate(contract)
    if spec is None:
        raise ValueError(f"{contract.name} does not load: {refusals}")
    layout = json.loads((out / "contract.json").read_text(encoding="utf-8"))
    model = build(layout, spec, voxel, a.band, a.height_field)
    model.update(
        cases=CASES,
        safety=a.safety,
        least_height_mm=least_mm,
        least_width_mm=a.least_width,
        beds_mm={c: REFERENCE[c] / 1000.0 for c in CASES if c in GRADED_CASES},
        modes={"margin": a.modes, "count": MODE_COUNT, "first": a.first_mode, "first_margin": 0.0},
        max_member={
            "mm": a.max_member,
            "alpha": MEMBER_ALPHA,
            "radius_vox": a.max_member / 0.849 / voxel,
            "p": member_p,
        },
    )
    say("metal joined to nothing: 1e-06 of its mass and 1e-06 of its stiffness")
    free_kg = budget - model["frozen_kg"]
    if model["least_kg"] >= free_kg:
        raise ValueError(
            f"the walls need about {model['least_kg']:.2f} kg at least, the budget leaves "
            f"{free_kg:.2f} kg to place"
        )
    stem = stem_of(design, budget, voxel, a, member_p, least_mm)
    say(f"budget {budget:g} kg: {model['frozen_kg']:.2f} frozen, {free_kg:.2f} to place; {stem}")
    stop = out / f"stop_{design}"
    stop.unlink(missing_ok=True)  # a stop left from an earlier run stops nothing now

    def write(name: str, result: dict, **extra) -> None:
        np.savez_compressed(
            out / f"{name}.npz",
            phys=result["phys"],
            x=result["x"],
            free_e=result["free_e"],
            elem=result["elem"],
            frozen=result["frozen"],
            ijk=result["ijk"],
            lo=model["lo"],
            n=model["n"],
            h=voxel,
            k_split=model["k_split"],
            beta=result["beta"],
            height_min=np.asarray(model["height_min"], np.float32),
        )
        projection = dict(PROJECTION, every=EVERY, beta_most=BETA_MOST, settle=SETTLE)
        record = {
            "layout": "contract",
            "objective": OBJECTIVE,
            "budget_kg": budget,
            "frozen_kg": model["frozen_kg"],
            "voxel_mm": voxel,
            "cavity": "cup",
            "joint": result["joint"],
            "element": "hex8 with Wilson's incompatible modes",
            "factor": "the single-precision factor, refined",
            "route": "split",
            "casting": "each half's columns one piece from the joint out to the last metal "
            "(anchored)",
            "projection": projection,
            "penalty_ramp": PENALTY_RAMP,
            "band_mm": a.band,
            "mount_reach": "disc",
            "max_member": model["max_member"],
            "height_field": {"radius_mm": a.height_field},
            "empty": True,
            "least_kg": model["least_kg"],
            "protect": True,
            "shell_fixed": True,
            "towers": False,
            "modes": model["modes"],
            "flange": True,
            "flange_whole": True,
            "drawing_clear": True,
            "couplings": "kinematic",
            "beds_mm": model["beds_mm"],
            "safety": a.safety,
            "safety_beds": a.safety,
            "least_height_mm": least_mm,
            "least_width_mm": a.least_width,
            "loose": {"mass": 1e-6, "stiffness": 1e-6},
            "skin": {
                "wall_mm": 0.0,
                "mass_share": 1.0,
                "stiffness_share": 1.0,
                "empty": True,
                "flange": {"kg": model["flange_kg"]},
            },
            "cases": list(CASES),
            "fast": True,
            "history": result["history"],
            "ratios": result["ratios"],
            "binary": result["binary"],
            "unknowns": result["n_dof"],
            "seconds": time.time() - t0,
            "iterations": result["iteration"],
            **extra,
        }
        (out / f"{name}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")

    def save(result: dict, it: int) -> None:
        write(f"{stem}_it{it:03d}", result, saved_at=it, saved_of=stem)
        say(f"saved the field at iteration {it}: {stem}_it{it:03d}")

    result = solve(model, free_kg, iterations, stop=stop, on_save=save)
    stop.unlink(missing_ok=True)
    write(stem, result, **({"stopped_at": result["stopped_at"]} if result["stopped_at"] else {}))
    say(f"done in {time.time() - t0:.0f} s; {stem}")
    return stem, result["settled"]
