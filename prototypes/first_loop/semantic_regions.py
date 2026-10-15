"""PROTOTYPE (LOP-28) - the semantic rules' regions: which columns of the design space are broad panels whose outer surface
must stay calm, and which voxels hold each bracket, for `topo_free.py --bending` and `--brackets` (the engineer, 13 October
00:03-00:21, with a reviewer's notes: "the optimiser understands structural performance, but it does not understand which
shapes should remain geometrically calm"; "a smoothness penalty alone will not solve the bracket problem").

The regions come from the contract's geometry, never from a run's metal (D16: the design space is the same in every run):
- **a bridge** (`--bridge <half>:<shaft a>:<shaft b>:<bound>`): the patch between two bearings of one half, the tapered hull
  of their circles grown `--reach` mm past each bore's radius, less the circles (as `web_form.py` lays it), every first-run
  column of the half; weight 1 inside, fading to 0 over `--fade` mm outside, so the rule's edge makes no new step. Its bound
  is the RMS bending allowed (1/m): a number, or a share of the reference run's own (`0.25x`);
- **the brackets** (`--brackets <share>`): every free voxel round each mount, as `mode_shape.parts` gives them (within 60 mm
  of the mount's centre in plan, the bores' surroundings first), each bracket's floor that share of the reference run's metal
  there.

The bending is measured as the optimiser holds it (`topo.bending_operator`, `topo.bending_value`) on the reference run's own
heights. Writes data/first_loop/<label>_regions.npz, <label>_brackets.npz and <label>_regions.png (the weights over the
reference's metal in plan, each half).

Run: .venv/Scripts/python.exe prototypes/first_loop/semantic_regions.py <reference run> --label <l>
     [--bridge cover:intermediate:output:0.25x ...] [--brackets 1.0] [--fade 10] [--reach 6]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import mode_shape  # noqa: E402
import roughness  # noqa: E402
import topo  # noqa: E402

OUT = topo.OUT


def bridge_weights(f: dict, layout: dict, half: str, shaft_a: str, shaft_b: str, reach: float, fade: float) -> np.ndarray:
    """A bridge's weight a column: 1 inside the hull of the two bores' grown circles less the circles, fading to 0 over `fade` mm."""
    h, lo = f["h"], f["lo"]
    hv = 1 if half == "cover" else 0
    side = "+z" if half == "cover" else "-z"
    bores = {b["shaft"]: b for b in layout["bearings"] if b["side"] == side}
    a, b = bores[shaft_a], bores[shaft_b]
    ca, cb = np.asarray(a["axis"], float), np.asarray(b["axis"], float)
    ra, rb = a["D"] / 2 + reach, b["D"] / 2 + reach
    x = lo[0] + h * (f["pts"][:, 0] + 0.5)
    y = lo[1] + h * (f["pts"][:, 1] + 0.5)
    d = cb - ca
    t = np.clip(((x - ca[0]) * d[0] + (y - ca[1]) * d[1]) / float(d @ d), 0.0, 1.0)
    hull = np.hypot(x - (ca[0] + t * d[0]), y - (ca[1] + t * d[1])) <= ra + t * (rb - ra)
    circles = (np.hypot(x - ca[0], y - ca[1]) <= ra) | (np.hypot(x - cb[0], y - cb[1]) <= rb)
    mine = (f["half"] == hv) & (f["run"] == 1)
    inside = hull & ~circles & mine
    w = inside.astype(float)
    if fade > 0 and inside.any():
        dist, _ = cKDTree(np.column_stack([x[inside], y[inside]])).query(np.column_stack([x, y]))
        w = np.where(inside, 1.0, np.where(mine & ~circles, np.clip(1.0 - dist / fade, 0.0, 1.0), 0.0))
    return w


KINDS = {"bend": 0, "dev": 1}  # the bending (a calm patch), the double curvature (no bumps, dents or wrinkles; ribs free)


def faded(f: dict, inside: np.ndarray, allowed: np.ndarray, fade: float) -> np.ndarray:
    """1 inside, fading to 0 over `fade` mm across the allowed columns outside."""
    h, lo = f["h"], f["lo"]
    w = inside.astype(float)
    if fade > 0 and inside.any():
        x = lo[0] + h * (f["pts"][:, 0] + 0.5)
        y = lo[1] + h * (f["pts"][:, 1] + 0.5)
        dist, _ = cKDTree(np.column_stack([x[inside], y[inside]])).query(np.column_stack([x, y]))
        w = np.where(inside, 1.0, np.where(allowed, np.clip(1.0 - dist / fade, 0.0, 1.0), 0.0))
    return w


def boss_rings(f: dict, layout: dict, half: str, ring: float) -> np.ndarray:
    """Every first-run column of the half within `ring` mm outside any of its bores' bosses (boss_r): the bosses' cylindrical regions."""
    h, lo = f["h"], f["lo"]
    hv = 1 if half == "cover" else 0
    x = lo[0] + h * (f["pts"][:, 0] + 0.5)
    y = lo[1] + h * (f["pts"][:, 1] + 0.5)
    near = np.zeros(len(x), bool)
    for b in layout["bearings"]:
        if b["side"] == ("+z" if hv == 1 else "-z"):
            r = np.hypot(x - b["axis"][0], y - b["axis"][1])
            near |= (r >= b["D"] / 2) & (r <= float(b["boss_r"]) + ring)
    return near & (f["half"] == hv) & (f["run"] == 1)


def main(run: str, label: str, bridges: list[str], bosses: str, panels: str, brackets: float | None, fade: float, reach: float,
         ring: float, floors: list[float] | None = None, everywhere: str = "") -> None:  # fmt: skip
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    f = roughness.tops(run)
    h = f["h"]
    names, weights, bounds_spec, kinds = [], [], [], []
    taken = {0: np.zeros(len(f["pts"]), bool), 1: np.zeros(len(f["pts"]), bool)}  # each half's columns a region already holds
    for spec in bridges:
        half, sa, sb, bound, *kind = spec.split(":")
        w = bridge_weights(f, layout, half, sa, sb, reach, fade)
        names.append(f"{half} {sa}-{sb} bridge")
        weights.append(w)
        bounds_spec.append(bound)
        kinds.append(KINDS[kind[0] if kind else "bend"])
        taken[1 if half == "cover" else 0] |= w >= 1
    for half, hv in (("cover", 1), ("motor_side", 0)):
        mine = (f["half"] == hv) & (f["run"] == 1)
        if everywhere:  # (LOP-28, production's surfaces) every first-run column of the half, one region
            bound, *kind = everywhere.split(":")
            names.append(f"{half} everywhere")
            weights.append(mine.astype(float))
            bounds_spec.append(bound)
            kinds.append(KINDS[kind[0] if kind else "dev"])
        rings = boss_rings(f, layout, half, ring) & ~taken[hv]
        if bosses:
            bound, *kind = bosses.split(":")
            names.append(f"{half} bosses")
            weights.append(faded(f, rings, mine & ~taken[hv], fade))
            bounds_spec.append(bound)
            kinds.append(KINDS[kind[0] if kind else "dev"])
        if panels:
            bound, *kind = panels.split(":")
            panel = mine & (f["base"] > 0.5 * h) & ~rings & ~taken[hv]  # the end walls: standing on a room, not a ring's, not a bridge's
            names.append(f"{half} panels")
            weights.append(faded(f, panel, mine & ~taken[hv] & ~rings, fade))
            bounds_spec.append(bound)
            kinds.append(KINDS[kind[0] if kind else "dev"])
    out = {}
    if weights:
        w = np.vstack(weights)
        op = topo.bending_operator(f["height"], f["ijk_free"], w)
        b, _ = topo.bending_value(op, f["t"], kinds)
        rms_ref = topo.bending_rms(b, kinds, h)
        bounds = np.array([float(s[:-1]) * r if s.endswith("x") else float(s) for s, r in zip(bounds_spec, rms_ref, strict=True)], float)
        np.savez_compressed(OUT / f"{label}_regions.npz", weights=w.astype(np.float32), rms_per_m=bounds, names=np.array(names), kinds=np.array(kinds),
                            reference_rms_per_m=rms_ref, reference=np.array(run), fade_mm=fade, reach_mm=reach, ring_mm=ring)  # fmt: skip
        for nm, k, wk, r, bd, n_c in zip(names, kinds, w, rms_ref, bounds, (op["w"] > 0).sum(axis=1), strict=True):
            print(f"{nm:34s} {'double curv.' if k == 1 else 'bending':12s} {int((wk >= 1).sum()):5d} columns inside, {int(((wk > 0) & (wk < 1)).sum()):4d} "
                  f"in the fade, {n_c:5d} centres read; the reference's {r:7.1f} 1/m, the bound {bd:7.1f}")  # fmt: skip
        out["weights"] = w
    if brackets is not None:
        e = f["ijk_free"]
        xyz = np.column_stack([f["lo"][k] + h * (e[:, k] + 0.5) for k in range(3)])
        owner, part_names = mode_shape.parts(xyz, layout)
        mounts = [m["name"] for m in layout["mounts"]]
        of = np.full(len(xyz), -1, np.int64)
        for k, nm in enumerate(mounts):
            of[owner == part_names.index(nm)] = k
        metal = np.array([f["phys"][of == k].sum() for k in range(len(mounts))])
        least = brackets * metal
        if floors:  # absolute floors (cm³), e.g. another run's brackets', on this reference's voxels
            least = np.asarray(floors, float) * 1000.0 / h**3
        np.savez_compressed(OUT / f"{label}_brackets.npz", of=of, least_vox=least, names=np.array(mounts), reference=np.array(run), share=brackets)
        for nm, mv, lv, cnt in zip(mounts, metal, least, [(of == k).sum() for k in range(len(mounts))], strict=True):
            print(f"{nm:10s} {cnt:5d} free voxels; the reference's metal {mv * h**3 / 1000:6.1f} cm³, the floor {lv * h**3 / 1000:6.1f} cm³")
    try:  # the regions over the reference's metal, each half
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        n, lo = f["n"], f["lo"]
        fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        for ax, (half_name, hv) in zip(axes, (("cover", 1), ("motor_side", 0)), strict=True):
            sel = (f["half"] == hv) & (f["run"] == 1)
            top = np.full((n[0], n[1]), np.nan)
            top[f["pts"][sel, 0], f["pts"][sel, 1]] = (f["optimiser"] - f["base"])[sel]
            ext = [lo[0], lo[0] + n[0] * h, lo[1], lo[1] + n[1] * h]
            ax.imshow(top.T, origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=40)
            if "weights" in out:
                wmax = np.zeros((n[0], n[1]))
                wmax[f["pts"][sel, 0], f["pts"][sel, 1]] = out["weights"][:, sel].max(axis=0)
                ax.imshow(np.ma.masked_less_equal(wmax.T, 0.0), origin="lower", extent=ext, cmap="autumn_r", alpha=0.55, vmin=0, vmax=1)
            for bb in layout["bearings"]:
                if bb["side"] == ("+z" if hv == 1 else "-z"):
                    ax.add_patch(plt.Circle(bb["axis"], bb["D"] / 2, fill=False, color="c"))
                    ax.text(bb["axis"][0], bb["axis"][1], bb["shaft"][:5], color="c", ha="center", va="center", fontsize=8)
            for m in layout["mounts"]:
                ax.add_patch(plt.Circle(m["centre"], 60.0, fill=False, color="tab:blue", ls="--"))
                ax.text(m["centre"][0], m["centre"][1], m["name"], color="tab:blue", fontsize=8)
            ax.set_title(f"{label}: {half_name.replace('_', ' ')} (grey: the reference's metal off its base, mm; orange: the bending rule's weight)", fontsize=9)
            ax.set_aspect("equal")
        fig.savefig(OUT / f"{label}_regions.png", dpi=80, bbox_inches="tight")
        print(OUT / f"{label}_regions.png")
    except Exception as exc:  # the picture is for checking only
        print(f"(no picture: {exc})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The semantic rules' regions (LOP-28).")
    ap.add_argument("run", help="the reference run (its columns and free voxels are the model's)")
    ap.add_argument("--label", required=True)
    ap.add_argument("--bridge", action="append", default=[],
                    help="<half>:<shaft a>:<shaft b>:<bound>[:bend|dev]: the patch between two bearings (the bound in 1/m, or a share of the "
                         "reference's, e.g. 0.25x; the bending by default)")  # fmt: skip
    ap.add_argument("--bosses", default="", help="<bound>[:bend|dev]: each half's rings round its bosses (the double curvature by default)")
    ap.add_argument("--panels", default="", help="<bound>[:bend|dev]: each half's end walls outside the rings and bridges (the double curvature by default)")
    ap.add_argument("--brackets", type=float, default=None, help="each bracket's floor, a share of the reference's metal round its mount (e.g. 1.0)")
    ap.add_argument("--fade", type=float, default=10.0, help="mm over which a region's weight fades outside it (default 10)")
    ap.add_argument("--reach", type=float, default=6.0, help="mm past each bore's radius a bridge's circles reach (default 6)")
    ap.add_argument("--ring", type=float, default=15.0, help="mm outside each boss its ring reaches (default 15)")
    ap.add_argument("--bracket-floors", default="", help="with --brackets: each bracket's floor in cm³ (comma-separated, the layout's mounts' order)")
    ap.add_argument("--everywhere", default="", help="<bound>[:bend|dev]: each half's every first-run column one region (the double curvature by default)")
    a = ap.parse_args()
    main(a.run, a.label, a.bridge, a.bosses, a.panels, a.brackets, a.fade, a.reach, a.ring,
         [float(v) for v in a.bracket_floors.split(",")] if a.bracket_floors else None, a.everywhere)  # fmt: skip
