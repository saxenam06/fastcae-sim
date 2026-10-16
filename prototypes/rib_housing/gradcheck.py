"""The housing field's derivatives against central differences (LOP-34; a prototype): a tilt, a bed
and the mass by a few design variables (a thickness, a height and a turn), and one rule.
`gradcheck.py [voxel mm] [--solid] [--picks=<i,...>] [--steps=<h,...>]` (5 mm by default: the least width needs two cubes of 8 mm)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import field as fieldmod  # noqa: E402
import housing  # noqa: E402
import ribmodel  # noqa: E402


STEPS = tuple(float(v) for v in next((a.split("=")[1] for a in sys.argv if a.startswith("--steps=")),
                                        "1e-3,1e-4").split(","))


def main() -> None:
    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    vox, model = housing.product_model(voxel, out=housing.OUT / f"v{voxel:g}")
    rm = ribmodel.RibModel(vox)
    hf = fieldmod.HousingField(vox, housing.column_groups(vox), rm.c_local, rm.c_iso)
    rng = np.random.default_rng(1)
    x = rng.uniform(0.3, 0.8, hf.size)
    c, pc = hf.stiffness(x)
    hf.align(rm.energy(rm.analyse(c, adjoints=False)["q"]), pc)
    c, pc = hf.stiffness(x)
    out = rm.analyse(c)
    g0 = hf.groups[0]
    n = g0.n
    d_tilt = hf.back(pc, out["d_ratio"][int(np.argmax(out["ratios"]))])
    d_bed = hf.back(pc, out["d_bed"][int(np.argmax(out["beds"]))])
    d_mass = hf.back(pc, mass=True)
    i_t, i_b = int(np.argmax(out["ratios"])), int(np.argmax(out["beds"]))
    nr = hf.n_rib
    picks = [int(nr + np.argmax(np.abs(d_tilt[nr:]))), int(nr + np.argmax(np.abs(d_bed[nr:]))),
             int(np.argmax(np.abs(d_tilt[: 2 * n]))), int(2 * n + np.argmax(np.abs(d_tilt[2 * n : 4 * n]))),
             int(4 * n + np.argmax(np.abs(d_tilt[4 * n : 5 * n]))), int(n + np.argmax(np.abs(d_tilt[n : 2 * n])))]
    if "--solid" in sys.argv:
        picks = picks[:2]
    only = next((a.split("=")[1] for a in sys.argv if a.startswith("--picks=")), None)
    if only:
        picks = [int(v) for v in only.split(",")]
    worst = 0.0
    for k in picks:
        for name, an, fn in (
            ("tilt", d_tilt[k], lambda xx: rm.analyse(hf.stiffness(xx)[0], adjoints=False)["ratios"][i_t]),
            ("bed", d_bed[k], lambda xx: rm.analyse(hf.stiffness(xx)[0], adjoints=False)["beds"][i_b]),
            ("mass", d_mass[k], lambda xx: hf.mass(hf.stiffness(xx)[1])),
        ):
            best = None
            for h in STEPS:
                xp, xm = x.copy(), x.copy()
                xp[k] += h
                xm[k] -= h
                fd = (fn(xp) - fn(xm)) / (2 * h)
                err = abs(fd - an) / max(abs(fd), abs(an), 1e-14)
                if best is None or err < best[0]:
                    best = (err, fd)
            worst = max(worst, best[0])
            print(f"{name} by x[{k}]: analytic {an:.6e}, central {best[1]:.6e}, relative {best[0]:.2e}", flush=True)
    for name, _g, dg, _ in hf.rules(x)[:4]:
        k = int(np.argmax(np.abs(dg)))
        xp, xm = x.copy(), x.copy()
        xp[k] += 1e-5
        xm[k] -= 1e-5
        gp = dict((r[0], r[1]) for r in hf.rules(xp))[name]
        gm = dict((r[0], r[1]) for r in hf.rules(xm))[name]
        fd = (gp - gm) / 2e-5
        err = abs(fd - dg[k]) / max(abs(fd), abs(dg[k]), 1e-14)
        worst = max(worst, err)
        print(f"rule {name} by x[{k}]: analytic {dg[k]:.6e}, central {fd:.6e}, relative {err:.2e}")
    print(f"worst relative difference {worst:.2e}")


if __name__ == "__main__":
    main()
