"""A drawn rib design read in plan (LOP-34; a prototype): `plan_view.py <design>` pictures
`drawrib.py`'s plan readings (`plan_<design>_<half>.npz`): each half seen along its pull from
outside, the ribs coloured by height (the two families hatched apart), the solid zones (bosses and
mounts' arms) in grey by height, the field's directions as short strokes, the bores, the mounts and
the bolts; `data/rib_housing/plan_<design>.png`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "rib_housing"


def main() -> None:
    design = sys.argv[1]
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    split = lay["z"]["split"]
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    for ax, half in zip(axes, ("cover", "motor_side"), strict=True):
        z = np.load(OUT / f"plan_{design}_{half}.npz")
        xs, ys = z["x"], z["y"]
        ext = [xs[0], xs[-1], ys[0], ys[-1]]
        lower = half == "motor_side"
        flip = (lambda a: a[::-1, :]) if lower else (lambda a: a)  # noqa: E731: seen from outside
        ext = [-ext[1], -ext[0], ext[2], ext[3]] if lower else ext
        ax.imshow(flip(np.where(z["area"], 0.93, 1.0)).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
        sh = np.ma.masked_where(~z["solid"], z["solid_h"])
        ax.imshow(flip(sh).T, origin="lower", extent=ext, cmap="Greys", vmin=-20, vmax=80, alpha=0.9)
        rh = np.ma.masked_where(z["fam"] == 0, z["rib_h"])
        im = ax.imshow(flip(rh).T, origin="lower", extent=ext, cmap="plasma", vmin=0, vmax=60)
        both = np.ma.masked_where(z["fam"] != 3, np.ones(z["fam"].shape))
        ax.imshow(flip(both).T, origin="lower", extent=ext, cmap="Greens", vmin=0, vmax=1, alpha=0.5)
        th = z["theta"]
        step = 12
        sx, sy = np.meshgrid(np.arange(0, len(xs), step), np.arange(0, len(ys), step), indexing="ij")
        ok = np.isfinite(th[sx, sy])
        px, py, t = xs[sx[ok]], ys[sy[ok]], th[sx[ok], sy[ok]]
        sgn = -1.0 if lower else 1.0
        for k, col in ((0, (0.1, 0.3, 0.8)), (1, (0.6, 0.6, 0.6))):
            a = t + k * np.pi / 2
            dx, dy = 4.0 * np.cos(a) * sgn, 4.0 * np.sin(a)
            ax.plot(np.stack([sgn * px - dx, sgn * px + dx]), np.stack([py - dy, py + dy]), color=col, lw=0.6)
        for b in lay["bearings"]:
            if (0.5 * (b["z"][0] + b["z"][1]) < split) == lower:
                ax.add_patch(plt.Circle((sgn * b["axis"][0], b["axis"][1]), b["D"] / 2, fill=False, color="k", lw=1.2))
        for m in lay["mounts"]:
            if (m["z"][1] <= split) == lower:
                ax.add_patch(plt.Circle((sgn * m["centre"][0], m["centre"][1]), lay["settings"]["mount_diameter"] / 2,
                                        fill=False, color="r", lw=1.2))
        for c in lay["bolts"]:
            ax.add_patch(plt.Circle((sgn * c[0], c[1]), lay["settings"]["bolt_boss"] / 2, fill=False, color="k", lw=0.6))
        ax.set_aspect("equal")
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        ax.set_title(f"{design}: the {half.replace('_', ' ')} from outside, along its pull "
                     f"(ribs by height, mm; grey: the solid bosses and arms; green: both families)")
        fig.colorbar(im, ax=ax, fraction=0.03, label="rib height past its column's base (mm)")
    fig.tight_layout()
    path = OUT / f"plan_{design}.png"
    fig.savefig(path, dpi=110)
    print(path)


if __name__ == "__main__":
    main()
