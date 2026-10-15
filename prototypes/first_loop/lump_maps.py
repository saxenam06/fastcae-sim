"""PROTOTYPE (LOP-27) - why the lumps grew (the engineer, 12 October 21:28-21:36): each design's half filled on one
2 mm grid; per column in plan, how far the metal stands off the inside; maps side by side on one scale, the
differences, a profile across the web between the bores, and the web's numbers (copied from the session's scratchpad;
its designs are the evening's, or those given). Run: lump_maps.py [cover|motor_side] [design=label ...]
(the difference maps take the second design against the first, the third against the second, the fourth against the first)
Writes data/first_loop/lump_maps_<half>.png."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "prototypes" / "first_loop"))

import cup as cupmod  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mesh_route as mr  # noqa: E402
import shell as convex  # noqa: E402
import trimesh  # noqa: E402
from outcome_cad import OUT, rooms_mask  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

HALF = sys.argv[1] if len(sys.argv) > 1 else "cover"
LOWER = HALF == "motor_side"
DESIGNS = [("empty1_5.5kg", "1: 6 mm plan smoothing"), ("empty2_hf12_5.5kg", "2: 12 mm plan smoothing"),
           ("empty2_exact_5.5kg", "3: 12 mm + exact walls"), ("empty1_exact_5.5kg", "4: 6 mm + exact walls (fixed)")]  # fmt: skip
if len(sys.argv) > 2:  # designs given: design=label ...
    DESIGNS = [tuple(a.split("=", 1)) if "=" in a else (a, a) for a in sys.argv[2:]]
DESIGNS = [d for d in DESIGNS if (OUT / f"{d[0]}_{HALF}.ply").exists()]
CELL = 2.0
layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
z_split = float(layout["z"]["split"])
meshes = [trimesh.load(str(OUT / f"{d}_{HALF}.ply"), process=True) for d, _ in DESIGNS]
lo, shape = mr.grid_over(meshes, CELL, pad=3)
lo = np.asarray(lo, float).copy()
lo[2] = z_split - CELL * np.ceil((z_split - lo[2]) / CELL)
shape = np.asarray(shape, int).copy()
shape[2] += 2
spec, _ = load_and_validate(convex.CONTRACT)
chain = complete_chain(spec)
gaps = spec.requirement.shaft_layout
rooms = cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
inside = rooms_mask({"n": shape, "lo": lo, "h": CELL}, rooms, z_split, HALF)
zs = lo[2] + CELL * (np.arange(shape[2]) + 0.5)
xs = lo[0] + CELL * (np.arange(shape[0]) + 0.5)
ys = lo[1] + CELL * (np.arange(shape[1]) + 0.5)
side = (zs < z_split) if LOWER else (zs >= z_split)
has = inside.any(axis=2)
if LOWER:  # the inside's far face, or the split
    far = np.where(has, np.where(inside, zs[None, None, :], np.inf).min(axis=2), z_split)
else:
    far = np.where(has, np.where(inside, zs[None, None, :], -np.inf).max(axis=2), z_split)

standoff = []
for tm in meshes:
    metal = mr.occupancy(tm, CELL, lo, shape)[0] & ~inside & side[None, None, :]
    if LOWER:
        bot = np.where(metal, zs[None, None, :], np.inf).min(axis=2)
        standoff.append(np.where(np.isfinite(bot), far - (bot - CELL / 2), np.nan))
    else:
        top = np.where(metal, zs[None, None, :], -np.inf).max(axis=2)
        standoff.append(np.where(np.isfinite(top), top + CELL / 2 - far, np.nan))

bores = {b["shaft"]: b for b in layout["bearings"] if b["side"] == ("-z" if LOWER else "+z")}
A, B, C = (np.array(bores[k]["axis"]) for k in ("intermediate", "output", "input"))
PX, PY = np.meshgrid(xs, ys, indexing="ij")


def band(p, q, half_width):
    """Plan cells within half_width of the segment p-q, outside every bore's boss (1.25 D + 10 over 2)."""
    d = q - p
    t = np.clip(((PX - p[0]) * d[0] + (PY - p[1]) * d[1]) / (d @ d), 0, 1)
    near = np.hypot(PX - (p[0] + t * d[0]), PY - (p[1] + t * d[1])) <= half_width
    for b in bores.values():
        near &= np.hypot(PX - b["axis"][0], PY - b["axis"][1]) > (1.25 * b["D"] + 10) / 2
    return near


region = band(A, B, 30.0) | band(C, B, 30.0) | band(C, A, 30.0)
print(f"[{HALF}] the web between the bores (within 30 mm of each line between two bores, the bosses left out):")
for (d, label), s in zip(DESIGNS, standoff, strict=True):
    ss = s[region & np.isfinite(s)]
    vol = float(np.nansum(np.where(region, s, 0.0))) * CELL * CELL / 1e3
    proud = float(np.mean(ss > 4.5 + 1e-6)) if ss.size else 0.0
    print(f"  {label:32s} metal off the inside {vol:6.0f} cm3; median {np.median(ss):5.1f} mm, 90 % {np.percentile(ss, 90):5.1f} mm; "
          f"share standing more than the least wall off {100 * proud:4.0f} %")  # fmt: skip

nd = len(DESIGNS)
if len(sys.argv) > 2:  # each given design against the first
    pairs = [(i, 0, f"{DESIGNS[i][1]} minus {DESIGNS[0][1]}") for i in range(1, min(nd, 4))]
else:
    pairs = [(1, 0, "2 minus 1: the 12 mm smoothing"), (2, 1, "3 minus 2: the exact walls on the 12 mm field")]
    if nd > 3:
        pairs.append((3, 0, "4 minus 1: the fixed exact walls on the 6 mm field"))
ncol = max(nd, len(pairs) + 1)
fig, axes = plt.subplots(2, ncol, figsize=(5.2 * ncol, 10.5))
ext = [xs[0], xs[-1], ys[0], ys[-1]]
for k, ((d, label), s) in enumerate(zip(DESIGNS, standoff, strict=True)):
    im = axes[0, k].imshow(s.T, origin="lower", extent=ext, cmap="viridis", vmin=0, vmax=30)
    axes[0, k].set_title(f"{label}\nthe metal off the inside (mm)", fontsize=10)
for k, (i, j, label) in enumerate(pairs):
    diff = np.nan_to_num(standoff[i], nan=0.0) - np.nan_to_num(standoff[j], nan=0.0)
    im2 = axes[1, k].imshow(diff.T, origin="lower", extent=ext, cmap="RdBu_r", vmin=-15, vmax=15)
    axes[1, k].set_title(f"{label}\n(mm; red more metal)", fontsize=10)
ax = axes[1, len(pairs)]
t_line = np.linspace(0, 1, 300)
pts = A[None, :] + t_line[:, None] * (B - A)[None, :]
ii = np.clip(((pts[:, 0] - lo[0]) / CELL).astype(int), 0, shape[0] - 1)
jj = np.clip(((pts[:, 1] - lo[1]) / CELL).astype(int), 0, shape[1] - 1)
for (d, label), s in zip(DESIGNS, standoff, strict=True):
    ax.plot(t_line * np.linalg.norm(B - A), s[ii, jj], label=label)
ax.set_xlabel("mm from the intermediate bore toward the output bore")
ax.set_ylabel("the metal off the inside (mm)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
for row, n_used in ((0, nd), (1, len(pairs))):
    for ax in axes[row, :n_used]:
        for name, b in bores.items():
            ax.add_patch(plt.Circle(b["axis"], b["D"] / 2, fill=False, color="w" if row == 0 else "k", lw=1))
            ax.text(b["axis"][0], b["axis"][1], name[:5], color="w" if row == 0 else "k", ha="center", va="center", fontsize=8)
        ax.contour(xs, ys, region.T.astype(float), levels=[0.5], colors="orange", linewidths=0.8)
        ax.set_aspect("equal")
for row, n_used in ((0, nd), (1, len(pairs) + 1)):
    for ax in axes[row, n_used:]:
        ax.axis("off")
fig.colorbar(im, ax=axes[0, :nd], shrink=0.6)
fig.colorbar(im2, ax=axes[1, : len(pairs)], shrink=0.6)
fig.suptitle(f"The {HALF.replace('_', ' ')}, seen from outside along the pull's axis (plan x, y in mm)")
name = f"lump_maps_{HALF}.png" if len(sys.argv) <= 2 else f"lump_maps_{HALF}_{'_vs_'.join(d for d, _ in DESIGNS[:2])}.png"
fig.savefig(OUT / name, dpi=70, bbox_inches="tight")
print(OUT / name)
