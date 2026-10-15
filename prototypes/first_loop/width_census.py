"""PROTOTYPE (LOP-29, 14 October; the engineer, 13:42: "lets try a") The members' width in plan, read from a run's own
cubes: in each slice along the pull, each half's placed cubes (the optimiser's metal at 0.5, the fixed parts apart, as
`topo.least_width_blocks` counts them) that lie in no full 2 x 2 block of placed cubes (a member one cube, 4 mm, wide),
the corner-only contacts (two placed cubes touching at an edge alone, a hinge in the model and a pinch in the drawing),
and the loose cubes (placed metal joined face to face to nothing but its own piece, as `topo.Voxels.loose`). A
design's name reads its run (`outcome_of`).

Run: .venv/Scripts/python.exe prototypes/first_loop/width_census.py <design or run> [...] [--out <png>]
Writes data/first_loop/width_census_<design>.json each, and with --out a plan picture of every design's halves: the placed
metal grey, the columns holding a one-cube member red, the corner-only contacts black."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
DENSITY = 2.7e-6  # kg/mm³, the housing's aluminium (as everywhere in the loop)


def run_of(name: str) -> str:
    p = OUT / f"{name}.json"
    if p.exists():
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("outcome_of"):
            return rec["outcome_of"]
    return name


def census(name: str) -> dict:
    run = run_of(name)
    z = np.load(OUT / f"{run}.npz")
    n, ks, h = tuple(int(v) for v in z["n"]), int(z["k_split"]), float(z["h"])
    ijk = z["ijk"]
    placed = np.zeros(n, bool)
    fi = ijk[z["free_e"][np.asarray(z["phys"], float) >= 0.5]]
    placed[fi[:, 0], fi[:, 1], fi[:, 2]] = True
    fixed = np.zeros(n, bool)
    fx = ijk[z["frozen"]]
    fixed[fx[:, 0], fx[:, 1], fx[:, 2]] = True
    out = {"design": name, "run": run, "h_mm": h, "halves": {}}
    maps = {}
    for half, sl in (("motor_side", slice(0, ks)), ("cover", slice(ks, n[2]))):
        p = placed[:, :, sl]
        # the 2 x 2 windows of each slice, by their corner: full, and the corner-only contacts
        a, b, c, d = p[:-1, :-1, :], p[1:, :-1, :], p[:-1, 1:, :], p[1:, 1:, :]
        full = a & b & c & d
        covered = np.zeros_like(p)
        covered[:-1, :-1, :] |= full
        covered[1:, :-1, :] |= full
        covered[:-1, 1:, :] |= full
        covered[1:, 1:, :] |= full
        thin = p & ~covered
        corner = (a & d & ~b & ~c) | (b & c & ~a & ~d)
        # loose: placed metal outside the half's largest piece of metal (placed or fixed), joined face to face
        lab, _ = ndi.label(p | fixed[:, :, sl])
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        loose = p & (lab != int(sizes.argmax()))
        kg = h**3 * DENSITY
        out["halves"][half] = {
            "placed_cubes": int(p.sum()), "placed_kg": round(float(p.sum()) * kg, 3),
            "thin_cubes": int(thin.sum()), "thin_share": round(float(thin.sum()) / max(int(p.sum()), 1), 4),
            "thin_kg": round(float(thin.sum()) * kg, 3), "thin_columns": int(thin.any(axis=2).sum()),
            "corner_contacts": int(corner.sum()), "loose_cubes": int(loose.sum()),
        }  # fmt: skip
        maps[half] = {"placed": p.any(axis=2), "thin": thin.any(axis=2), "corner": corner.any(axis=2)}
    (OUT / f"width_census_{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return {"record": out, "maps": maps}


def picture(results: list, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(results), 2, figsize=(12, 5.4 * len(results)), squeeze=False)
    for row, res in enumerate(results):
        rec = res["record"]
        for col, half in enumerate(("motor_side", "cover")):
            m, r = res["maps"][half], rec["halves"][half]
            img = np.ones(m["placed"].shape + (3,))
            img[m["placed"]] = (0.62, 0.62, 0.62)
            img[m["thin"]] = (0.85, 0.12, 0.10)
            ax = axes[row, col]
            ax.imshow(np.transpose(img, (1, 0, 2)), origin="lower", interpolation="nearest")
            cj, ci = np.nonzero(m["corner"].T)
            ax.plot(ci + 0.5, cj + 0.5, "k.", markersize=3)
            ax.set_title(f"{rec['design']} - {half.replace('_', ' ')}\none-cube metal {r['thin_cubes']:,} cubes "
                         f"({100 * r['thin_share']:.1f} %, {r['thin_kg']:.2f} kg), corner contacts {r['corner_contacts']}, "
                         f"loose {r['loose_cubes']}", fontsize=10)  # fmt: skip
            ax.set_xticks([])
            ax.set_yticks([])
    fig.text(0.01, 0.003, "grey: the optimiser's placed metal seen along the pull; red: columns holding metal in no full 2 x 2 "
             "block of placed cubes (a member one cube, 4 mm, wide); black: corner-only contacts", fontsize=9)  # fmt: skip
    fig.tight_layout(rect=(0, 0.015, 1, 1))
    fig.savefig(path, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    args = sys.argv[1:]
    out_png = None
    if "--out" in args:
        k = args.index("--out")
        out_png = Path(args[k + 1])
        args = args[:k] + args[k + 2:]
    results = [census(name) for name in args]
    for res in results:
        rec = res["record"]
        for half, r in rec["halves"].items():
            print(f"{rec['design']:<24} {half:<10} placed {r['placed_cubes']:>6,} cubes ({r['placed_kg']:.2f} kg); one-cube "
                  f"{r['thin_cubes']:>5,} ({100 * r['thin_share']:4.1f} %, {r['thin_kg']:.2f} kg, {r['thin_columns']:,} columns); "
                  f"corner contacts {r['corner_contacts']:>4}; loose {r['loose_cubes']:>4}")  # fmt: skip
    if out_png is not None:
        picture(results, out_png if out_png.is_absolute() else OUT / out_png)
        print(f"wrote {out_png}")
