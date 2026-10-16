"""A walls run's field pictured (LOP-34, the restart; a prototype): per half, from outside, every
wall point where a rib family is live (at least `T_MIN` thick) as a stroke along the rib, coloured
by its height, and the features' metal (ring bosses, bracket webs) as solid cubes.
`fieldview.py <run npz> [out png]` (default `data/rib_walls/field_<stem>.png`)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wallfield as wfm  # noqa: E402


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    path = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else path.with_name(f"field_{path.stem}.png")
    z = np.load(path)
    foot, n, e1, e2, lower = z["cm_foot"], z["cm_n"], z["cm_e1"], z["cm_e2"], z["cm_lower"].astype(bool)
    d, centre = z["cm_d"], z["cm_centre"]
    a = float(np.median(np.diff(np.unique(np.round(centre[:, 0], 3)))))
    first = d < a
    theta, t, h, s = z["theta"], z["t"], z["h"], z["s"]
    cmap = plt.get_cmap("viridis")
    fig = plt.figure(figsize=(24, 20))
    views = (("cover", 28, -60), ("cover", 75, -90), ("motor_side", -28, -60), ("motor_side", -75, -90))
    for k, (half, elev, azim) in enumerate(views):
        sel = lower if half == "motor_side" else ~lower
        ax = fig.add_subplot(2, 2, k + 1, projection="3d")
        segs, cols = [], []
        for fam, style in ((0, 1.0), (1, 0.6)):
            live = np.flatnonzero(first & sel & (t[fam] >= wfm.T_MIN) & (h[fam] >= 3.0))
            th = theta[live] + fam * np.pi / 2
            tt = np.cos(th)[:, None] * e1[live] + np.sin(th)[:, None] * e2[live]
            p = foot[live] + n[live] * 0.5
            segs += list(np.stack([p - 0.45 * a * tt, p + 0.45 * a * tt], axis=1))
            cols += list(cmap(np.clip(h[fam][live] / wfm.H_MOST, 0, 1)) * np.array([style, style, style, 1.0]))
        if segs:
            ax.add_collection3d(Line3DCollection(segs, colors=cols, linewidths=1.6))
        bare = np.flatnonzero(first & sel & (t[0] < wfm.T_MIN) & (t[1] < wfm.T_MIN))
        ax.scatter(foot[bare, 0], foot[bare, 1], foot[bare, 2], s=1, c="0.8")
        solid = np.flatnonzero(sel & (s > 0.5))
        ax.scatter(centre[solid, 0], centre[solid, 1], centre[solid, 2], s=4, c="tab:red", alpha=0.35)
        f = foot[sel]
        ax.set_xlim(f[:, 0].min(), f[:, 0].max())
        ax.set_ylim(f[:, 1].min(), f[:, 1].max())
        ax.set_zlim(f[:, 2].min(), f[:, 2].max())
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect(tuple(np.ptp(f, axis=0) / np.ptp(f, axis=0).max()))
        ax.set_title(f"{path.stem}, the {half.replace('_', ' ')}: ribs as strokes along their run (bright = tall, "
                     f"family 1 darker), bare wall grey, bosses and webs red")
    fig.tight_layout()
    fig.savefig(out, dpi=80)
    print(out)


if __name__ == "__main__":
    main()
