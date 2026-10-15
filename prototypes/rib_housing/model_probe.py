"""One analysis of the housing's rib model (LOP-34; a prototype): every free cube a rib cube of one
share and direction; its time, memory and measures; and one measure's derivative by a cube's
stiffness against a central difference. `model_probe.py [voxel mm]`."""

from __future__ import annotations

import resource
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import housing  # noqa: E402
import ribmodel  # noqa: E402


def main() -> None:
    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    vox, _ = housing.product_model(voxel)
    rm = ribmodel.RibModel(vox)
    n = len(rm.free)
    rng = np.random.default_rng(0)
    theta = rng.uniform(0, np.pi, n)
    crib, _ = ribmodel.toymodel.rib_tensor(theta, rm.c_local)
    c = 0.15 * crib + ribmodel.ERSATZ * rm.c_iso
    t0 = time.time()
    out = rm.analyse(c)
    print(f"analysis {time.time() - t0:.0f} s {out['clock']}; peak memory "
          f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6:.1f} GB")
    print("tilt ratios", np.round(out["ratios"], 3), "beds", np.round(out["beds"], 3))
    i = int(np.argmax(out["ratios"]))
    e = int(np.argmax(np.abs(out["d_ratio"][i]).sum(axis=(1, 2))))
    dc = np.zeros((6, 6))
    dc[0, 0] = 1.0
    step = 1e-3 * float(np.abs(c[e]).max())
    cp, cm = c.copy(), c.copy()
    cp[e] += step * dc
    cm[e] -= step * dc
    fd = (rm.analyse(cp, adjoints=False)["ratios"][i] - rm.analyse(cm, adjoints=False)["ratios"][i]) / (2 * step)
    an = float((out["d_ratio"][i, e] * dc).sum())
    print(f"d ratio[{i}] / d C[{e}][0,0]: analytic {an:.6e}, central {fd:.6e}, relative {abs(an - fd) / abs(fd):.2e}")


if __name__ == "__main__":
    main()
