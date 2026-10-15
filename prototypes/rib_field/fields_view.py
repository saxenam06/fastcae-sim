"""A run's fields in plan (LOP-34): each family's amount (rho) and height, the directions as short
strokes, and the free columns' heights beside them. `fields_view.py <label> [<columns label>]`
writes `data/rib_field/fields_<label>.png`."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402


def on_grid(values, ij, a):
    nx, ny = int(round(toy.LX / a)), int(round(toy.LY / a))
    g = np.full((nx, ny), np.nan)
    g[ij[:, 0], ij[:, 1]] = values
    return g


def outline(ax):
    t = np.linspace(0, 2 * np.pi, 120)
    for (x, y), r in [(toy.BORE, toy.R_BORE), (toy.BORE, toy.R_BOSS), (toy.LUG, toy.R_LUG)] + [
        (b, toy.R_BOLT) for b in toy.BOLTS
    ]:
        ax.plot(x + r * np.cos(t), y + r * np.sin(t), "k-", lw=0.6)
    ax.set_xlim(0, toy.LX)
    ax.set_ylim(0, toy.LY)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def main() -> None:
    label = sys.argv[1]
    cols_label = sys.argv[2] if len(sys.argv) > 2 else None
    f = np.load(toy.OUT / f"{label}_field.npz")
    a = float(f["voxel"])
    ij, xy = f["cols_ij"], f["cols_xy"]
    fams = int(f["families"])
    panels = 2 * fams + (1 if cols_label else 0)
    fig, axes = plt.subplots(1, panels, figsize=(4.2 * panels, 3.8))
    axes = np.atleast_1d(axes)
    ext = (0, toy.LX, 0, toy.LY)
    for k in range(fams):
        th = f["theta"] + k * np.pi / 2
        ax = axes[2 * k]
        im = ax.imshow(on_grid(f["rho"][k] * toy.SPACING, ij, a).T, origin="lower", extent=ext,
                       cmap="viridis", vmin=0, vmax=toy.T_MOST)
        keep = f["rho"][k] * toy.SPACING > 1.0
        d = 0.45 * a
        ax.plot(np.stack([xy[keep, 0] - d * np.cos(th[keep]), xy[keep, 0] + d * np.cos(th[keep])]),
                np.stack([xy[keep, 1] - d * np.sin(th[keep]), xy[keep, 1] + d * np.sin(th[keep])]),
                "w-", lw=0.8)
        plt.colorbar(im, ax=ax, fraction=0.04, label="rib thickness, mm")
        ax.set_title(f"family {k + 1}: thickness and direction")
        outline(ax)
        ax = axes[2 * k + 1]
        im = ax.imshow(on_grid(f["h"][k], ij, a).T, origin="lower", extent=ext, cmap="magma",
                       vmin=0, vmax=toy.BAND)
        plt.colorbar(im, ax=ax, fraction=0.04, label="rib height, mm")
        ax.set_title(f"family {k + 1}: height")
        outline(ax)
    if cols_label:
        c = np.load(toy.OUT / f"{cols_label}_columns.npz")
        ax = axes[-1]
        im = ax.imshow(on_grid(c["h"], c["cols_ij"], float(c["voxel"])).T, origin="lower",
                       extent=ext, cmap="magma", vmin=0, vmax=toy.BAND)
        plt.colorbar(im, ax=ax, fraction=0.04, label="column height, mm")
        ax.set_title("free columns: height")
        outline(ax)
    fig.tight_layout()
    out = toy.OUT / f"fields_{label}.png"
    fig.savefig(out, dpi=110)
    print(out)


if __name__ == "__main__":
    main()
