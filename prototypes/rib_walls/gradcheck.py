"""The walls field's derivatives against central differences (LOP-34, the restart; a prototype).
`gradcheck.py [voxel mm] [--steps=<h,...>]` (5 mm by default).

First the frame: `wallfield.frame_rotation` on a flat wall (n = z, e1 = x) against the toy's checked
`strain_rotation`, and `rib_tensor`'s derivative by the angle. Then a tilt, a bed and the mass by
one variable of each kind: a family's thickness share, its height share and the turn on the
motor side, each ring boss's radius and height, each web's thickness and spread (the variable with
the largest tilt derivative of its kind)."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "rib_housing"))
sys.path.insert(0, str(HERE.parents[0] / "rib_field"))
import housing  # noqa: E402
import model as toymodel  # noqa: E402
import ribmodel  # noqa: E402
import surface  # noqa: E402
import wallfield  # noqa: E402

STEPS = tuple(float(v) for v in next((a.split("=")[1] for a in sys.argv if a.startswith("--steps=")),
                                        "1e-3,1e-4").split(","))


def frame_check(c_local) -> float:
    rng = np.random.default_rng(0)
    th = rng.uniform(-math.pi, math.pi, 5)
    n = np.tile([0.0, 0.0, 1.0], (5, 1))
    e1 = np.tile([1.0, 0.0, 0.0], (5, 1))
    e2 = np.cross(n, e1)
    t = np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2
    R = np.stack([t, np.cross(n, t), n], axis=2)
    T, _ = wallfield.frame_rotation(R)
    T_toy, _ = toymodel.strain_rotation(th)
    err = float(np.abs(T - T_toy).max())
    print(f"the frame on a flat wall against the toy's strain rotation: largest difference {err:.2e}")
    # a tilted wall: the derivative by the angle
    nn = rng.normal(size=(5, 3))
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    f1, f2, _ = surface.frames(nn)
    C, dC = wallfield.rib_tensor(th, f1, f2, nn, c_local)
    h = 1e-6
    Cp, _ = wallfield.rib_tensor(th + h, f1, f2, nn, c_local)
    Cm, _ = wallfield.rib_tensor(th - h, f1, f2, nn, c_local)
    e2_ = float(np.abs((Cp - Cm) / (2 * h) - dC).max() / np.abs(dC).max())
    sym = float(np.abs(C - C.transpose(0, 2, 1)).max() / np.abs(C).max())
    print(f"rib_tensor on tilted walls: d/dtheta against central differences {e2_:.2e}; asymmetry {sym:.2e}")
    # the plate takes nothing across it: a strain along m alone stores no energy
    m = np.cross(nn, np.cos(th)[:, None] * f1 + np.sin(th)[:, None] * f2)
    eps = np.stack([m[:, 0] ** 2, m[:, 1] ** 2, m[:, 2] ** 2, 2 * m[:, 1] * m[:, 2], 2 * m[:, 0] * m[:, 2],
                    2 * m[:, 0] * m[:, 1]], axis=1)
    across = float(np.abs(np.einsum("np,npq,nq->n", eps, C, eps)).max() / np.abs(C).max())
    print(f"a stretch across the plate (along m) stores {across:.2e} of the stiffness (nothing)")
    return max(err, e2_, sym, across)


def rules_check(wf, x) -> float:
    """Each half's two rules by the variable each moves most, of each kind."""
    import wallrules

    rng = np.random.default_rng(2)
    wf.theta0 = rng.uniform(-math.pi, math.pi, wf.n_cubes)
    prep = wallrules.prepare(wf)
    print(f"the rules: {int(prep['first'].sum()):,} wall points, {int(prep['edge'].sum()):,} on the design "
          f"space's edge; the end rule's weight {np.percentile(prep['w_end'][prep['first'] > 0], [5, 50, 95]).round(2)}")
    base = {r[0]: r for r in wallrules.rules(wf, x, prep)}
    worst = 0.0
    for name, (_n, g0, dg, meas) in base.items():
        print(f"{name}: G {g0:+.3f} (the measure {meas:.4f})")
        hf = wf.halves[0] if name.startswith("motor_side") else wf.halves[1]
        for k in range(5):
            o = hf["off"] + k * hf["nb"]
            i = int(o + np.argmax(np.abs(dg[o: o + hf["nb"]])))
            if dg[i] == 0.0:
                continue
            best = None
            for h in (1e-4, 1e-5, 1e-6):
                xp, xm = x.copy(), x.copy()
                xp[i] += h
                xm[i] -= h
                gp = {r[0]: r[1] for r in wallrules.rules(wf, xp, prep)}[name]
                gm = {r[0]: r[1] for r in wallrules.rules(wf, xm, prep)}[name]
                fd = (gp - gm) / (2 * h)
                err = abs(fd - dg[i]) / max(abs(fd), abs(dg[i]), 1e-14)
                if best is None or err < best[0]:
                    best = (err, fd)
            worst = max(worst, best[0])
            print(f"  by x[{i}] ({('sigma0', 'r0', 'sigma1', 'r1', 'tau')[k]}): analytic {dg[i]:.6e}, "
                  f"central {best[1]:.6e}, relative {best[0]:.2e}", flush=True)
    return worst


def main() -> None:
    voxel = float(next((a for a in sys.argv[1:] if not a.startswith("--")), 5.0))
    t0 = time.time()
    vox, model = housing.product_model(voxel, out=housing.OUT / f"v{voxel:g}")
    layout = json.loads((housing.OUT / f"v{voxel:g}" / "contract.json").read_text(encoding="utf-8"))
    rm = ribmodel.RibModel(vox)
    worst = frame_check(rm.c_local)
    rooms = surface.rooms_of(vox)
    cm = surface.map_cubes(vox, layout, rooms)
    wf = wallfield.WallField(vox, cm, layout, rm.c_local, rm.c_iso, rooms)
    if "--rules" in sys.argv:
        rng = np.random.default_rng(1)
        x = wf.start()
        x[: wf.n_field] = rng.uniform(0.6, 1.0, wf.n_field)
        print(f"worst relative difference {max(worst, rules_check(wf, x)):.2e} ({time.time() - t0:.0f} s)")
        return
    print(f"the walls field: {wf.size:,} variables ({wf.n_field:,} in the fields, {len(wf.bosses)} bosses, "
          f"{len(wf.webs)} brackets of two webs; {time.time() - t0:.0f} s)", flush=True)
    for b in wf.bosses:
        print(f"  boss {b['name']}: {len(b['cubes'])} cubes in its reach")
    for w in wf.webs:
        print(f"  {w['name']}'s webs: {len(w['cubes'])} cubes in reach, towards {math.degrees(w['phi0']):.0f} deg, "
              f"the wall {w['reach0']:.0f} mm off; spread {math.degrees(wallfield.WEB_SPREAD[0]):.0f} to "
              f"{math.degrees(wallfield.WEB_SPREAD[0] + w['span']):.0f} deg; webs at most {w['l_cap']:.0f} mm long")
    rng = np.random.default_rng(1)
    x = np.zeros(wf.size)
    for hf in wf.halves:
        for k, (lo, hi) in enumerate(((0.75, 1.0), (0.3, 0.9), (0.75, 1.0), (0.3, 0.9), (0.3, 0.7))):
            o = hf["off"] + k * hf["nb"]
            x[o: o + hf["nb"]] = rng.uniform(lo, hi, hf["nb"])
    x[wf.n_field: wf.n_field + 2 * len(wf.bosses)] = rng.uniform(0.2, 0.8, 2 * len(wf.bosses))
    x[wf.n_field + 2 * len(wf.bosses):] = rng.uniform(0.55, 0.9, 2 * len(wf.webs))
    c, pc = wf.stiffness(x)
    wf.align(rm.energy(rm.analyse(c, adjoints=False)["q"]), pc)
    c, pc = wf.stiffness(x)
    ribs_kg, solid_kg = wf.masses(pc)
    print(f"at the check's point: ribs {ribs_kg:.3f} kg, features {solid_kg:.3f} kg", flush=True)
    out = rm.analyse(c)
    i_t, i_b = int(np.argmax(out["ratios"])), int(np.argmax(out["beds"]))
    d_tilt = wf.back(pc, out["d_ratio"][i_t])
    d_bed = wf.back(pc, out["d_bed"][i_b])
    d_mass = wf.back(pc, mass=True)
    print(f"tilt {out['ratios'][i_t]:.3f}, bed {out['beds'][i_b]:.3f} of their lines", flush=True)
    hf = wf.halves[0]
    picks = []
    for k, name in enumerate(("sigma0", "r0", "sigma1", "r1", "tau")):
        o = hf["off"] + k * hf["nb"]
        picks.append((name, int(o + np.argmax(np.abs(d_tilt[o: o + hf["nb"]])))))
    for i, b in enumerate(wf.bosses):
        o = wf.n_field + 2 * i
        picks += [(f"boss {b['name']} radius", o), (f"boss {b['name']} height", o + 1)]
    for i, w in enumerate(wf.webs):
        o = wf.n_field + 2 * len(wf.bosses) + 2 * i
        picks += [(f"{w['name']} web thickness", o), (f"{w['name']} web spread", o + 1)]
    if "--features" in sys.argv:  # the fields' kinds once (sigma0, tau), every feature's
        picks = [picks[0], picks[4]] + picks[5:]
    cache = {}

    def measures(xx):
        key = xx.tobytes()
        if key not in cache:
            cc, pcc = wf.stiffness(xx)
            o = rm.analyse(cc, adjoints=False)
            cache[key] = (o["ratios"][i_t], o["beds"][i_b], wf.mass(pcc))
        return cache[key]

    for label, k in picks:
        for j, (name, an) in enumerate((("tilt", d_tilt[k]), ("bed", d_bed[k]), ("mass", d_mass[k]))):
            best = None
            for h in STEPS:
                xp, xm = x.copy(), x.copy()
                xp[k] += h
                xm[k] -= h
                fd = (measures(xp)[j] - measures(xm)[j]) / (2 * h)
                err = abs(fd - an) / max(abs(fd), abs(an), 1e-14)
                if best is None or err < best[0]:
                    best = (err, fd)
            # a derivative under 1e-6 of the largest of its measure's is noise either way
            scale = {"tilt": np.abs(d_tilt).max(), "bed": np.abs(d_bed).max(), "mass": np.abs(d_mass).max()}[name]
            if max(abs(an), abs(best[1])) > 1e-6 * scale:
                worst = max(worst, best[0])
            print(f"{name} by {label} (x[{k}]): analytic {an:.6e}, central {best[1]:.6e}, relative {best[0]:.2e}",
                  flush=True)
    print(f"worst relative difference {worst:.2e} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
