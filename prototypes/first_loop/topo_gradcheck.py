"""PROTOTYPE (LOP-16) - `topo.Voxels`' derivatives checked against finite differences on a coarse
free model: every seat's misalignment ratio in both cases (the bound formulation's 12
constraints) and the mass, with respect to the design variables, through the whole chain: the
density filter, the projection (at beta 4, so its slope matters), the casting filter, SIMP, the
skin's scaled stiffness and the halves joined only at the bolts (`topo_free.build_free`'s
defaults).

At a random design x in [0.2, 0.8], for random directions d (largest entry 1), the central
difference (r(x + e d) - r(x - e d)) / 2e against the adjoint's grad r . d. Each side is one
single-precision factor with its answers refined to 1e-10 in double, so the ratios agree to about
1e-9 and e = 1e-4 leaves a difference of about 1e-5 relative.

With `--beds` (LOP-20, 11 October): on the set-up of 11 October (`build_free(..., flange=True)`),
peak drive alone, `compliance_tilt`'s measures: every seat's misalignment and every seat's bearing
bed over the design to beat's (`model["beds_mm"]`), with the mass.

With `--empty` (LOP-27, the empty start; implies `--beds`): the same measures on the empty set-up
(`build_free(..., flange=True, empty=True, height_field=6)`): the design variables the height
field's columns, the walls' columns standing at least their least heights (`topo.Voxels`).

With `--semantic` (LOP-28, the semantic rules; implies `--empty`): besides, two regions' bending of the columns' heights
(random weights; one the bending, one the double curvature: `topo.bending_operator`, `topo.bending_value`, taken to the
design variables through `topo.Voxels.column_heights` and the plan filter, as `topo.solve_model` does) and two brackets'
metal (random groups of free voxels, through `Voxels.back`).

With `--modes` (LOP-29; implies `--empty`): besides, the model's first modes' frequencies (`Voxels._modes`: shift-invert
Lanczos on the analysis's factor, the housing's lumped mass, near-empty voxels' mass taken down), their derivatives by
the densities taken to the design variables through `Voxels.back`; the eigen-solve tightened (LOOP_MODE_TOL 1e-10) so
the differences are not the solver's noise.

Run: .venv/Scripts/python.exe prototypes/first_loop/topo_gradcheck.py [voxel_mm] [beta] [directions] [--beds] [--empty] [--semantic] [--modes]
     (light: 10 mm voxels by default; prints PASS or FAIL)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import topo  # noqa: E402
from topo_free import build_free  # noqa: E402

TOLERANCE = 1e-3  # relative, on the directional derivative


def main(h: float = 10.0, beta: float = 4.0, directions: int = 2, eps: float = 1e-4, beds: bool = False, empty: bool = False,
         semantic: bool = False, modes: bool = False) -> bool:  # fmt: skip
    t0 = time.time()
    empty = empty or semantic or modes
    beds = beds or empty
    if beds:
        from grade import REFERENCE

        # (LOP-29) the baseline's set-up when asked: the protected interfaces (LOOP_CHECK_PROTECT=1), the fixed shell
        # (LOOP_CHECK_SHELL=1), the least member (LOOP_LEAST_MEMBER); the couplings by LOOP_MODEL_COUPLING (topo.Voxels)
        model = build_free(h, flange=True, empty=empty, height_field=6.0 if empty else None, protect=empty and os.environ.get("LOOP_CHECK_PROTECT") == "1",
                           shell_fixed=empty and os.environ.get("LOOP_CHECK_SHELL") == "1", drawing_clear=os.environ.get("LOOP_CHECK_SHELL") == "1",
                           **({"band": 24.0, "mount_reach": "disc"} if os.environ.get("LOOP_CHECK_SHELL") == "1" else {}))  # the runs' envelope
        if empty and os.environ.get("LOOP_LEAST_MEMBER"):
            model["least_height_mm"] = float(os.environ["LOOP_LEAST_MEMBER"])
        if empty and os.environ.get("LOOP_LEAST_WIDTH"):  # LOP-29: the least member width in plan (`topo.open_heights`), mm
            model["least_width_mm"] = float(os.environ["LOOP_LEAST_WIDTH"])
        if empty and os.environ.get("LOOP_SPLINE"):  # LOP-30: the spline map, "<outline mm>:<height mm>" (`topo.spline_setup`)
            a_, b_ = (float(v) for v in os.environ["LOOP_SPLINE"].split(":"))
            model["spline"] = {"phi_mm": a_, "h_mm": b_}
            if os.environ.get("LOOP_SPLINE_GAP"):  # its least gap, mm
                model["spline"]["gap_mm"] = float(os.environ["LOOP_SPLINE_GAP"])
            if os.environ.get("LOOP_SPLINE_OUTLINE"):  # its outline's limit, mm: the outline's length checked too
                model["spline"]["outline_mm"] = float(os.environ["LOOP_SPLINE_OUTLINE"])
            if os.environ.get("LOOP_SPLINE_SECTION"):  # the section rule, "<round mm>:<fillet mm>" (`topo.section_drop`)
                rnd_, fil_ = (float(v) for v in os.environ["LOOP_SPLINE_SECTION"].split(":"))
                model["spline"]["round_mm"], model["spline"]["fillet_mm"] = rnd_, fil_
            # (LOP-30, F1-F3) the smooth top, the section window ("<widths>:<caps>"), disc openings, the soft distance
            if os.environ.get("LOOP_SPLINE_TOP") == "1":
                model["spline"]["top"] = True
            if os.environ.get("LOOP_SPLINE_WINDOW"):
                v_ = [float(s_) for s_ in os.environ["LOOP_SPLINE_WINDOW"].split(":")]
                n_w = (len(v_) - 1) // 2
                free_ = os.environ.get("LOOP_SPLINE_WINDOW_FREE", "mounts").split(",")
                model["spline"]["window"] = {"widths_mm": v_[:n_w], "caps_mm": v_[n_w:], "bosses_wall_only": "bosses_wall" in free_,
                                             "free": ["bosses" if s_ == "bosses_wall" else s_ for s_ in free_]}  # fmt: skip
                if os.environ.get("LOOP_SPLINE_WINDOW_SPLIT"):  # the side walls' gussets' own caps
                    model["spline"]["window"]["caps_split_mm"] = [float(s_) for s_ in os.environ["LOOP_SPLINE_WINDOW_SPLIT"].split(":")]
            if os.environ.get("LOOP_SPLINE_DISC") == "1":
                model["spline"]["disc"] = True
            if os.environ.get("LOOP_SPLINE_DIST") == "soft":
                model["spline"]["dist"] = "soft"
            if os.environ.get("LOOP_SPLINE_SIZES"):  # the least width and gap as constraints, each at most this share
                model["spline"]["sizes"] = float(os.environ["LOOP_SPLINE_SIZES"])
            if os.environ.get("LOOP_SPLINE_GAP_SHELL") == "1":  # (15 October) the least gap read against the shell too
                model["spline"]["gap_shell"] = True
        if empty and os.environ.get("LOOP_WALL_GATE"):  # LOP-28: production's plain walls, the gated wall metal (`Voxels._wall_extra`)
            model["wall_gate_mm"] = float(os.environ["LOOP_WALL_GATE"])
        model["cases"] = ("peak drive",)
        model["beds_mm"] = {"peak drive": REFERENCE["peak drive"] / 1000.0}
        if modes:  # LOP-29: the first six modes read on each analysis's factor
            model["modes"] = {"margin": 0.12, "count": 6}
            os.environ["LOOP_MODE_TOL"] = "1e-10"
    else:
        model = build_free(h)
    vox = topo.Voxels(model)
    rng = np.random.default_rng(11)
    x = rng.uniform(0.2, 0.8, vox.n_design)  # a free voxel's each, or the height field's column's
    if vox.spline is not None:  # (LOP-30) the outline field positive (0.8-5.6 mm): metal everywhere, a housing joined to its mounts
        # LOOP_CHECK_PHI="<lo>:<hi>" its coefficients' range (as shares of the design variable): from 0.5 the field dips to
        # zero, so the section rule's round (`topo.section_drop`) acts at the point checked (at 0.55 no point is in its reach)
        lo_, hi_ = (float(v) for v in os.environ.get("LOOP_CHECK_PHI", "0.55:0.85").split(":"))
        x[: vox.spline["n_phi"]] = rng.uniform(lo_, hi_, vox.spline["n_phi"])
    kind = "compliance_bound" if beds else "misalignment_bound"

    op, kinds, groups = None, None, None
    if semantic:
        n_cols = vox.height["n_cols"]
        op = topo.bending_operator(vox.height, vox.ijk[vox.free_e], rng.uniform(0.0, 1.0, (2, n_cols)))
        kinds = np.array([0, 1])
        groups = rng.integers(-1, 2, len(vox.free_e))  # each free voxel in bracket 0, 1 or none

    def semantic_values(xv, dens):
        if not semantic:
            return np.zeros(0)
        b, _ = topo.bending_value(op, vox.column_heights(xv, beta)[0], kinds)
        return np.r_[b, [dens[vox.free_e][groups == k].sum() for k in (0, 1)]]

    out_lim = float(((model.get("spline") or {}).get("outline_mm")) or 0.0) if vox.spline is not None else 0.0
    # (LOP-30, F3) LOOP_CHECK_BEND=1: each spline field's bending checked too, after the outline
    n_sb = len(vox.spline["bend_ops"]) if (vox.spline is not None and os.environ.get("LOOP_CHECK_BEND") == "1") else 0
    # (LOP-30) the least width and gap as constraints, after the bending
    n_sz = (int(vox.spline["open"] is not None) + int(vox.spline["close"] is not None)) if (vox.spline is not None and vox.spline["sizes"] is not None) else 0

    def measures(xv):
        dens = vox.physical(xv, beta)
        out = vox.analyse(dens, kind, float(os.environ.get("LOOP_CHECK_PENAL", topo.PENAL)))  # (LOP-30) 1: linear shares
        hz = out["modes_hz"] if modes else np.zeros(0)
        tail = [vox.spline_outline(xv, beta, out_lim)[2]] if out_lim else []  # (LOP-30) the outline's length, last
        tail = tail + (list(vox.spline_bending(xv)[0]) if n_sb else []) + (list(vox.spline_sizes(xv, beta)[0]) if n_sz else [])
        return np.r_[out["ratio_vector"], out["bed_vector"], dens[vox.free_e].sum(), semantic_values(xv, dens), hz, tail], out, dens

    values, out, _ = measures(x)
    rows = [out["d_ratios"]] + ([out["d_beds"]] if beds else []) + [vox.mass_rows[None, :]]
    if semantic:  # the brackets' metal through back(), as the mass
        for k in (0, 1):
            row = np.zeros(len(vox.elem))
            row[vox.free_e[groups == k]] = 1.0
            rows.append(row[None, :])
    if modes:  # each mode's frequency through back(), after the brackets
        rows.append(out["d_modes_hz"])
    grads = vox.back(np.vstack(rows), x, beta)
    if semantic:  # the bending through the columns' heights and the plan filter, as solve_model's bend_of
        t, slope = vox.column_heights(x, beta)
        _, d_t = topo.bending_value(op, t, kinds)
        hh = vox.height
        d_x = np.asarray(hh["M"].T @ (d_t * (slope * hh["L"])[None, :]).T).T
        n_main = len(vox.keys) + (len(vox.bed_keys) if beds else 0) + 1
        grads = np.vstack([grads[:n_main], d_x, grads[n_main:]])
    if out_lim:  # (LOP-30) the outline's length (mm): its own derivative by x, last
        grads = np.vstack([grads, out_lim * vox.spline_outline(x, beta, out_lim)[1][None, :]])
    if n_sb:  # (LOP-30, F3) each field's bending: its own derivative by x, after the outline
        grads = np.vstack([grads, vox.spline_bending(x)[1]])
    if n_sz:  # (LOP-30) the least width and gap: their own derivatives by x, last
        grads = np.vstack([grads, vox.spline_sizes(x, beta)[1]])
    sb_names = [f"bending {op['kind']} {op.get('family') or ''} {op['half']}".replace("  ", " ") for op in vox.spline["bend_ops"]] if n_sb else []
    names = ([f"{k[0][0]} {k[0][1]} case {k[1]}" for k in vox.keys] + [f"bed {k[0][0]} {k[0][1]} case {k[1]}" for k in (vox.bed_keys if beds else [])]
             + ["mass (voxels)"] + (["bending (region 1)", "double curvature (region 2)", "bracket 1 (voxels)", "bracket 2 (voxels)"] if semantic else [])
             + ([f"mode {i_ + 1} (Hz)" for i_ in range(len(values) - len(vox.keys) - (len(vox.bed_keys) if beds else 0) - 1 - (4 if semantic else 0)
                                                          - (1 if out_lim else 0) - n_sb - n_sz)] if modes else [])
             + (["outline (mm)"] if out_lim else []) + sb_names + ["least width (G)", "least gap (G)"][:n_sz])  # fmt: skip
    worst = 0.0
    for i in range(directions):
        d = rng.normal(size=len(x))
        d /= np.abs(d).max()
        plus = measures(x + eps * d)[0]
        minus = measures(x - eps * d)[0]
        fd = (plus - minus) / (2 * eps)
        an = grads @ d
        # each error against its own derivative, or 1 % of the largest of its kind (the tilts, the beds, the mass) in
        # this direction where its own is near zero: the difference's noise is about 1e-7 absolute (single-precision
        # factors refined to 1e-10, eps 1e-4), which a derivative of 1e-5 reads as 1e-2 relative (the empty start's
        # check, 12 October 20:38: 8e-8 on 1.3e-5)
        n_tilt, n_bed = len(vox.keys), len(vox.bed_keys) if beds else 0
        floor = np.empty_like(an)
        n_mass = n_tilt + n_bed + 1
        kinds_of = [slice(0, n_tilt), slice(n_tilt, n_tilt + n_bed), slice(n_tilt + n_bed, n_mass)]
        if semantic:  # each semantic measure its own kind
            kinds_of += [slice(n_mass + k, n_mass + k + 1) for k in range(4)]
        if modes:  # each mode its own kind
            first = n_mass + (4 if semantic else 0)
            kinds_of += [slice(k, k + 1) for k in range(first, len(an))]
        for sl in kinds_of:
            if sl.stop > sl.start:
                floor[sl] = 1e-2 * np.abs(an[sl]).max()
        rel = np.abs(fd - an) / np.maximum(np.abs(an), np.maximum(floor, 1e-30))
        worst = max(worst, float(rel.max()))
        print(f"direction {i + 1}:")
        for name, v, a_, f_, r_ in zip(names, values, an, fd, rel, strict=True):
            print(f"   {name:28s} value {v:11.5g}  adjoint {a_:+.6e}  difference {f_:+.6e}  relative error {r_:.1e}")
    ok = worst < TOLERANCE
    print(f"{'PASS' if ok else 'FAIL'}: the worst relative error {worst:.1e} (tolerance {TOLERANCE:g}); {time.time() - t0:.0f} s")
    return ok


if __name__ == "__main__":
    a = [v for v in sys.argv[1:] if v not in ("--beds", "--empty", "--semantic", "--modes")]
    passed = main(float(a[0]) if a else 10.0, float(a[1]) if len(a) > 1 else 4.0, int(a[2]) if len(a) > 2 else 2,
                  beds="--beds" in sys.argv, empty="--empty" in sys.argv, semantic="--semantic" in sys.argv,
                  modes="--modes" in sys.argv)  # fmt: skip
    sys.exit(0 if passed else 1)
