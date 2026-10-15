"""A check of the height field's features (LOP-24, `topo.feature_map`), on the CPU (no solve): the model
rebuilt from a free run's record with a `--height-features` file; each feature's columns counted; the
densities' derivatives by the design variables (`Voxels.back`) against central differences, for some
feature parameters and some free columns; and a plan picture of each half's columns by owner (each
feature a colour, the region's empty columns grey, the free ones pale), the bores drawn.

    feature_map_check.py <free run> <features file> [--beta 4]

Writes data/first_loop/feature_map_<features stem>.png."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import topo  # noqa: E402
import topo_free as tf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"


def main(run: str, features: str, beta: float) -> dict:
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    fpath = Path(features) if Path(features).exists() else OUT / features
    spec = json.loads(fpath.read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    h = float(z["h"])
    skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
    model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                          route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                          height_field=rec["height_field"]["radius_mm"], space=rec.get("space") or "")  # fmt: skip
    model["cases"] = tuple(rec.get("cases") or ("peak drive",))
    model["height_features"] = spec
    vox = topo.Voxels(model)
    feat = vox.features
    rows = []
    for f in feat["features"]:
        rows.append(f"{f['name']}: {f['columns']} columns, parameters {f['params']}")
        if f["columns"] == 0:
            rows[-1] += "  <- covers nothing"
    print("\n".join(rows))

    # the derivatives: f(x) = w . densities over the free voxels
    rng = np.random.default_rng(0)
    x = rng.uniform(0.2, 0.6, vox.n_design)
    w = np.zeros(len(vox.elem))
    w[vox.free_e] = rng.normal(size=len(vox.free_e))
    grad = vox.back(w, x, beta)
    picks = [p for f in feat["features"] for p in f["params"][:1]][:4]
    picks += list(rng.choice(feat["n_free"], 3, replace=False))
    worst = 0.0
    for i in picks:
        e = 1e-5
        xp, xm = x.copy(), x.copy()
        xp[i] += e
        xm[i] -= e
        fd = (w @ vox.physical(xp, beta) - w @ vox.physical(xm, beta)) / (2 * e)
        rel = abs(fd - grad[i]) / max(abs(fd), 1e-12)
        worst = max(worst, rel)
        print(f"variable {i:>6} ({'a feature parameter' if i >= feat['n_free'] else 'a free column'}): adjoint {grad[i]: .6e}, "
              f"central difference {fd: .6e}, relative gap {rel:.1e}")  # fmt: skip
    print(f"the worst relative gap {worst:.1e}")

    # the plan picture
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col, pos, pts, layer = topo.height_columns(model["kind"], model["n"], model["k_split"], vox.elem, vox.free_e)
    lo = model["lo"]
    owner, region = feat["owner"], feat["region"]
    lay = model["info"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    cmap = plt.get_cmap("tab20")
    for ax, (half, base) in zip(axes, (("motor_side", 0), ("cover", 10_000))):
        sel = layer == base + 1
        cx = lo[0] + h * (pts[sel, 0] + 0.5)
        cy = lo[1] + h * (pts[sel, 1] + 0.5)
        own, reg = owner[sel], region[sel]
        ax.scatter(cx[~reg], cy[~reg], s=5, c="#dddddd", marker="s", linewidths=0)
        ax.scatter(cx[reg & (own < 0)], cy[reg & (own < 0)], s=5, c="#777777", marker="s", linewidths=0)
        for k, f in enumerate(feat["features"]):
            m = own == k
            if m.any():
                ax.scatter(cx[m], cy[m], s=5, color=cmap(k % 20), marker="s", linewidths=0, label=f["name"])
        side = "+z" if half == "cover" else "-z"
        for b in lay["bearings"]:
            if b["side"] == side:
                ax.add_patch(plt.Circle(b["axis"], b["D"] / 2, fill=False, color="k", lw=0.8))
                ax.add_patch(plt.Circle(b["axis"], b["boss_r"], fill=False, color="k", lw=0.5, ls=":"))
        for mnt in lay["mounts"]:
            ax.plot(*mnt["centre"], "k+")
        ax.set_aspect("equal")
        ax.set_title(f"{half}: the free columns pale, the region's empty grey, each feature a colour")
        if half == spec["half"]:
            ax.legend(fontsize=6, loc="upper left", markerscale=3)
    fig.suptitle(f"{fpath.stem}: {spec.get('family', '')} round the {spec['bore']} bore ({spec['half']})")
    png = OUT / f"feature_map_{fpath.stem}.png"
    fig.savefig(png, dpi=110, bbox_inches="tight")
    print(png)
    return {"worst": worst, "png": str(png)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("features")
    ap.add_argument("--beta", type=float, default=4.0)
    a = ap.parse_args()
    main(a.run, a.features, a.beta)
