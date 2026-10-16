"""Each mount's web reach to the wall against its angle (LOP-34, the restart; a prototype): where a
web's ray grazes a room its reach jumps, and no derivative follows it.
`reach_probe.py [voxel mm]` writes `data/rib_walls/reach_<voxel>.png`."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "rib_housing"))
sys.path.insert(0, str(HERE))  # first: rib_housing has an optimise.py too
import housing  # noqa: E402
import optimise  # noqa: E402
import surface  # noqa: E402
import wallfield as wfm  # noqa: E402


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    vox, _ = housing.product_model(voxel, out=optimise.model_dir(voxel))
    layout = json.loads((optimise.model_dir(voxel) / "contract.json").read_text(encoding="utf-8"))
    rooms = surface.rooms_of(vox)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, mt in zip(axes, layout["mounts"], strict=True):
        cxy = np.asarray(mt["centre"], float)
        zmid = 0.5 * (mt["z"][0] + mt["z"][1])
        half = "motor_side" if mt["z"][1] <= float(layout["z"]["split"]) else "cover"
        probe = wfm.WallField.__new__(wfm.WallField)
        probe.surface, probe.layout = surface, layout
        ang = np.radians(np.arange(0.0, 360.0, 0.5))
        reach = np.array([probe._ray(cxy, zmid, a, half, rooms) for a in ang])
        phi0 = float(ang[np.argmin(reach)])
        off = np.degrees(np.angle(np.exp(1j * (ang - phi0))))
        keep = np.abs(off) <= 70
        order = np.argsort(off[keep])
        ax.plot(off[keep][order], reach[keep][order], ".-", ms=2)
        jumps = np.abs(np.diff(reach[keep][order]))
        ax.set_title(f"{mt['name']}: reach from the lug against the angle off the nearest way "
                     f"(largest step {jumps.max():.1f} mm at 0.5 deg)")
        ax.set_xlabel("deg off the nearest way to the wall")
        ax.set_ylabel("mm")
        for lim in (10, 60):
            ax.axvline(lim, c="0.7", lw=0.5)
            ax.axvline(-lim, c="0.7", lw=0.5)
        print(f"{mt['name']}: nearest way {math.degrees(phi0):.1f} deg at {reach.min():.1f} mm; the largest "
              f"step within 70 deg {jumps.max():.1f} mm")
    fig.tight_layout()
    out = optimise.OUT / f"reach_{voxel:g}.png"
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == "__main__":
    main()
