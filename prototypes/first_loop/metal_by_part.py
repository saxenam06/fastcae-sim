"""PROTOTYPE (LOP-27) - where two runs differ in placed metal (the engineer, 12 October 23:51: case 3's web "ate some
material from bracket"): each run's free voxels' metal (its physical density times the voxel's volume) summed by part,
each bore's surroundings, each mount's, the split flange and the walls (`mode_shape.parts`, the parts the modes are
read by), and the change from the first run to the second. Copied from the session's scratchpad.

Run: .venv/Scripts/python.exe prototypes/first_loop/metal_by_part.py <run a> <run b> [<label a> <label b>]"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mode_shape  # noqa: E402

OUT = mode_shape.OUT


def by_part(run: str, lay: dict) -> tuple[dict[str, float], float]:
    """A run's placed metal in cm³ by part, and in all."""
    z = np.load(OUT / f"{run}.npz")
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    e = z["elem"][z["free_e"]]
    i, j, k = np.unravel_index(e, tuple(n))
    xyz = np.c_[lo[0] + h * (i + 0.5), lo[1] + h * (j + 0.5), lo[2] + h * (k + 0.5)]
    owner, names = mode_shape.parts(xyz, lay)
    vol = np.asarray(z["phys"], float) * h**3 / 1e3
    return {nm: float(vol[owner == q].sum()) for q, nm in enumerate(names)}, float(vol.sum())


def main(run_a: str, run_b: str, label_a: str, label_b: str) -> None:
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    a, ta = by_part(run_a, lay)
    b, tb = by_part(run_b, lay)
    print(f"placed metal (cm³): {label_a} {ta:.0f}, {label_b} {tb:.0f}")
    print(f"{'part':42s} {label_a:>10s} {label_b:>10s} {'change':>8s}")
    for nm in sorted(a, key=lambda q: b[q] - a[q]):
        print(f"{nm:42s} {a[nm]:10.1f} {b[nm]:10.1f} {b[nm] - a[nm]:+8.1f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], *(args[2:4] if len(args) >= 4 else args[:2]))
