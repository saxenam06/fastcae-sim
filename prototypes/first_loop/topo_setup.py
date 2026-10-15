"""PROTOTYPE (LOP-16) - the free optimisation's set-up in pictures: slices through the voxel model
showing each kind of space. Kept clear (the cavity: each half a cup open toward the split, round
the gears', bearings' and shafts' rooms; the seals, the motor, the half-shafts' joints); frozen
(the skin, the motor's ring, the mounts); the bolts' footprints where the halves are tied; free
for the optimiser to fill; outside the packaging space.

Run: .venv/Scripts/python.exe prototypes/first_loop/topo_setup.py [voxel_mm] [band_mm]
       [--cavity cup|rooms]
     (writes data/first_loop/topofree_setup.png; with --cavity rooms, the earlier model's
     topofree_setup_rooms.png)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

from topo import OUT  # noqa: E402
from topo_free import build_free  # noqa: E402

KINDS = [  # (mask, label, colour), drawn in this order, the later over the earlier
    ("pack", "free: the optimiser decides", (0.80, 0.92, 0.80)),
    ("rooms", "kept clear inside: the cavity round the gears and differential (with clearances), bearings, shafts", (0.95, 0.78, 0.45)),
    ("clear", "kept clear: seal bores, the motor, the half-shafts' joints, bolt access", (0.85, 0.85, 0.85)),
    ("skin", "frozen: the oil-tight skin, one voxel thick (also the bearing seats)", (0.35, 0.40, 0.48)),
    ("ring", "frozen: the motor's flange ring (A25)", (0.75, 0.25, 0.25)),
    ("mounts", "frozen: the mounts (A20)", (0.55, 0.20, 0.60)),
    ("bolts", "the halves tied: the bolt bosses' footprints, at the split", (0.15, 0.55, 0.85)),
]


def main(h: float = 6.0, band: float | None = None, cavity: str = "cup") -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    model = build_free(h, band=band, cavity=cavity)
    n, lo = model["n"], model["lo"]
    m = {k: v.reshape(n) for k, v in model["masks"].items()}
    info = model["info"]
    z_split = info["z"]["split"]
    zc = lo[2] + h * (np.arange(n[2]) + 0.5)
    stacks = {st.shaft: st for st in model["chain"].layout.shafts}
    k_split = model["k_split"]
    cuts = [
        ("across the shafts, through the first stage (motor side)", int(np.argmin(np.abs(zc - (z_split - 25.0))))),
        ("across the shafts, the split's first layer on the motor side", k_split - 1),
        ("across the shafts, through the second stage (cover)", int(np.argmin(np.abs(zc - (z_split + 25.0))))),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(15, 14))
    extent = (lo[0], lo[0] + n[0] * h, lo[1], lo[1] + n[1] * h)

    def paint(sl, ax, ext):
        img = np.ones(sl["pack"].shape + (3,))
        for key, _, colour in KINDS:
            mask = sl["pack"] & sl["design"] if key == "pack" else sl[key]
            img[mask] = colour
        ax.imshow(np.transpose(img, (1, 0, 2)), origin="lower", extent=ext, interpolation="nearest")

    for ax, (title, k) in zip(axes.ravel()[:3], cuts, strict=True):
        sl = {key: v[:, :, k] for key, v in m.items()}
        paint(sl, ax, extent)
        ax.set_title(f"{title}: z = {zc[k]:.0f} mm", fontsize=10)
        ax.set_xlabel("x, mm")
        ax.set_ylabel("y, mm")
        for shaft, st in stacks.items():
            ax.plot(*st.axis, "k+", ms=10)
            ax.annotate(shaft, st.axis, textcoords="offset points", xytext=(5, 5), fontsize=8)
    # along the shafts: the plane through the intermediate's and the output's axes
    a, b = np.asarray(stacks["intermediate"].axis), np.asarray(stacks["output"].axis)
    d = (b - a) / np.linalg.norm(b - a)
    s_vals = np.arange(-120.0, np.linalg.norm(b - a) + 140.0, h / 2)
    ii = np.clip(((a[0] + s_vals * d[0]) - lo[0]) // h, 0, n[0] - 1).astype(int)
    jj = np.clip(((a[1] + s_vals * d[1]) - lo[1]) // h, 0, n[1] - 1).astype(int)
    sl = {key: v[ii, jj, :] for key, v in m.items()}
    paint(sl, axes[1][1], (s_vals[0], s_vals[-1], lo[2], lo[2] + n[2] * h))
    z_cut = lo[2] + k_split * h
    axes[1][1].axhline(z_cut, color="k", lw=0.8, ls="--")
    axes[1][1].set_title(f"along the shafts, through the intermediate's and the output's axes (dashed: the split, z = {z_cut:.1f} in voxels)", fontsize=10)
    axes[1][1].set_xlabel("from the intermediate's axis towards the output's, mm")
    axes[1][1].set_ylabel("z, mm (along the shafts)")
    axes[1][1].set_aspect("equal")
    handles = [Patch(color=c, label=label) for _, label, c in KINDS] + [Patch(color=(1, 1, 1), label="outside the packaging space")]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9, frameon=False)
    skin = model["skin"]
    inside = "each half a cup open toward the split" if cavity == "cup" else "each room its own cylinder (the earlier model)"
    fig.suptitle(f"The optimisation's set-up ({h:g} mm voxels{f', metal only within {band:g} mm of the skin' if band else ''}; the cavity: {inside}): "
                 f"{model['frozen_kg']:.2f} kg frozen of 7.73, the skin as a {skin['wall_mm']:g} mm wall", fontsize=11)  # fmt: skip
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    out = OUT / ("topofree_setup.png" if cavity == "cup" else f"topofree_setup_{cavity}.png")
    fig.savefig(out, dpi=85)
    plt.close(fig)
    print(out.name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The free optimisation's set-up in pictures (prototype).")
    ap.add_argument("voxel", nargs="?", type=float, default=6.0, help="voxel size, mm (default 6)")
    ap.add_argument("band", nargs="?", type=float, default=None, help="stage 2's band, mm")
    ap.add_argument("--cavity", default="cup", choices=["cup", "rooms"])
    a_ = ap.parse_args()
    main(a_.voxel, a_.band, a_.cavity)
