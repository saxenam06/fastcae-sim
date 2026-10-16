"""Where the end rule acts on the walls (LOP-34, the restart; a prototype): every wall point's
distance to a hard point and to the design space's edge, and the rule's weight, pictured per half
from outside. `weights_view.py [voxel mm]` writes `data/rib_walls/weights_<voxel>.png`."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import optimise  # noqa: E402


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    vox, model, layout, rm, cm, wf, prep = optimise.build(voxel)
    first = prep["first"] > 0
    for name, v in (("hard point", wf.hard_dist), ("edge", prep["edge_dist"]), ("weight", prep["w_end"])):
        print(f"{name}: {np.percentile(v[first], [5, 25, 50, 75, 95]).round(2)}")
    fig = plt.figure(figsize=(22, 10))
    for k, (half, sel) in enumerate((("cover", ~cm["lower"]), ("motor_side", cm["lower"]))):
        for j, (name, v, cmap) in enumerate((("distance to a hard point (mm)", np.minimum(wf.hard_dist, 40), "viridis"),
                                             ("the end rule's weight (edges black)", prep["w_end"], "magma"))):
            ax = fig.add_subplot(2, 2, 2 * k + j + 1, projection="3d")
            s = np.flatnonzero(first & sel)
            f = cm["foot"][s]
            col = np.where(prep["edge"][s][:, None], np.array([[0, 0, 0, 1.0]]), plt.get_cmap(cmap)(v[s] / max(v[s].max(), 1e-9)))
            ax.scatter(f[:, 0], f[:, 1], f[:, 2], s=3, c=col)
            ax.view_init(elev=28 if half == "cover" else -28, azim=-60)
            ax.set_title(f"the {half.replace('_', ' ')}: {name}")
            ax.set_box_aspect((1, 1, 0.6))
    fig.tight_layout()
    out = optimise.OUT / f"weights_{voxel:g}.png"
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == "__main__":
    main()
