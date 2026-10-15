"""Organised design domains from a run's material flow (LOP-24, approach 1 as the engineer meant it, 12 October
01:23-01:25: "design domains or design spaces based upon the material flow where it is happening, and then you
see more organized material flows... the flow itself will become more organized"; a UTV gearbox housing's
three design domains as the example: smooth patches over a face, round a bearing boss, on a lobe).

From a height-field run, each half's metal in plan (its columns' heights) is blurred over `--sigma` mm and cut
at the level that holds `--cover` of the metal (height-weighted): the dense flow becomes a few smooth patches,
the thin spill falls under the cut. Holes under `--hole` mm across are filled, necks under `--neck` mm cut, and
pieces holding under 2 % of the metal dropped; the outlines are simplified to `--tolerance` mm. Each half's
patches are its design domains for the next run (`topo_free.py --space <label>.json`; each mount's and each
bore's own room always kept, `topo_free.space_mask`).

    domains_from_flow.py <run> --label <label> [--sigma 12] [--cover 0.9] [--hole 20] [--neck 8] [--tolerance 4]

Writes data/first_loop/<label>.json (the domains in plan, each with the metal it holds and the hard points it
touches) and <label>.png (each half in plan: the run's metal, the domains, the metal they leave out)."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
from space_from_runs import polygons_of  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0  # mm: a column this high off its base holds a member


def disc(r_cells: float) -> np.ndarray:
    k = int(np.ceil(r_cells))
    i, j = np.mgrid[-k : k + 1, -k : k + 1]
    return i * i + j * j <= r_cells * r_cells


def domains(weight: np.ndarray, h: float, sigma: float, cover: float, hole: float, neck: float) -> np.ndarray:
    """The plan cells of a half's domains: the blurred metal cut at the level holding `cover` of it."""
    if weight.sum() <= 0:
        return np.zeros(weight.shape, bool)
    blur = ndi.gaussian_filter(weight, sigma / h)
    total = weight.sum()
    lo_l, hi_l = 0.0, float(blur.max())
    for _ in range(40):  # the highest cut that still holds `cover` of the metal
        mid = 0.5 * (lo_l + hi_l)
        if weight[blur >= mid].sum() >= cover * total:
            lo_l = mid
        else:
            hi_l = mid
    dom = blur >= lo_l
    if neck > 0:
        dom = ndi.binary_opening(dom, disc(0.5 * neck / h))
    holes = ndi.binary_fill_holes(dom) & ~dom  # holes under `hole` mm across filled
    lab, n = ndi.label(holes)
    if n:
        area = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) * h * h
        small = np.r_[False, area <= np.pi * (0.5 * hole) ** 2]
        dom |= small[lab]
    lab, n = ndi.label(dom)
    if n:
        held = ndi.sum(weight, lab, index=np.arange(1, n + 1))
        keep = np.r_[False, held >= 0.02 * total]
        dom = keep[lab]
    return dom


def main(run: str, label: str, sigma: float, cover: float, hole: float, neck: float, tol: float) -> dict:
    maps = shh.column_heights(run)
    h, lo = float(maps["h"]), np.asarray(maps["lo"], float)
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    out = {"label": label, "run": run, "sigma_mm": sigma, "cover": cover, "halves": {}, "held": {}}
    pics = {}
    for half in ("motor_side", "cover"):
        t = np.clip(np.asarray(maps[half], float), 0.0, None)
        weight = np.where(t >= MEMBER, t, 0.0)
        dom = domains(weight, h, sigma, cover, hole, neck)
        lab, n = ndi.label(dom)
        regs = []
        side = "+z" if half == "cover" else "-z"
        held_all = float(weight[dom].sum() / max(weight.sum(), 1e-9))
        for k in range(1, n + 1):
            piece = lab == k
            big = ndi.zoom(piece.astype(np.uint8), h, order=0).astype(bool)
            polys = polygons_of(big, float(lo[0]), float(lo[1]), tol)
            ii, jj = np.nonzero(piece)
            xs, ys = lo[0] + h * (ii + 0.5), lo[1] + h * (jj + 0.5)
            touches = [f"the {b['shaft']} bore" for b in lay["bearings"] if b["side"] == side
                       and np.min(np.hypot(xs - b["axis"][0], ys - b["axis"][1])) <= float(b["boss_r"])]  # fmt: skip
            touches += [m["name"] for m in lay["mounts"] if half == "motor_side" and np.min(np.hypot(xs - m["centre"][0], ys - m["centre"][1])) <= 40.0]
            for p in polys:
                regs.append({"name": f"domain {len(regs) + 1}", "outline": p["outline"], "holes": p.get("holes", []),
                             "metal_share": float(weight[piece].sum() / max(weight.sum(), 1e-9)), "touches": touches})  # fmt: skip
        out["halves"][half] = regs
        out["held"][half] = held_all
        pics[half] = (weight, dom)
        print(f"{half}: {len(regs)} domains, {100 * dom.sum() / max((t > 0).sum(), 1):.0f} % of the columns with any metal, holding "
              f"{100 * held_all:.0f} % of the metal; " + "; ".join(f"{r['name']} {100 * r['metal_share']:.0f} % ({', '.join(r['touches']) or 'no hard point'})"
                                                          for r in regs))  # fmt: skip
    (OUT / f"{label}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    picture(label, pics, lo, h, lay)
    return out


def picture(label: str, pics: dict, lo: np.ndarray, h: float, lay: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    for ax, half in zip(axes, ("motor_side", "cover")):
        weight, dom = pics[half]
        ex = [lo[0], lo[0] + h * weight.shape[0], lo[1], lo[1] + h * weight.shape[1]]
        rgb = np.ones(weight.shape + (3,))
        rgb[dom] = (0.80, 0.88, 1.00)
        metal = weight > 0
        shade = np.clip(weight / max(weight.max(), 1e-9), 0, 1)[..., None]
        rgb[metal & dom] = (1 - 0.7 * shade[metal & dom]) * np.array([0.25, 0.40, 0.75]) + 0.7 * shade[metal & dom] * np.array([0.05, 0.10, 0.35])
        rgb[metal & ~dom] = (0.85, 0.15, 0.15)
        ax.imshow(np.transpose(rgb, (1, 0, 2)), origin="lower", extent=ex, interpolation="nearest")
        ax.contour(lo[0] + h * (np.arange(dom.shape[0]) + 0.5), lo[1] + h * (np.arange(dom.shape[1]) + 0.5), dom.T.astype(float), [0.5],
                   colors="k", linewidths=0.8)  # fmt: skip
        for b in lay["bearings"]:
            if (b["side"] == "+z") == (half == "cover"):
                ax.add_patch(plt.Circle(b["axis"], b["D"] / 2, fill=False, color="0.3", lw=0.8))
        for m in lay["mounts"]:
            ax.plot(*m["centre"], "k+")
        ax.set_aspect("equal")
        ax.set_title(f"{half}: the run's metal (blue, darker higher), the domains (outlined), the metal they leave out (red)", fontsize=8)
    fig.suptitle(f"{label}: organised design domains from the material flow")
    fig.savefig(OUT / f"{label}.png", dpi=110, bbox_inches="tight")
    print(OUT / f"{label}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("--label", required=True)
    ap.add_argument("--sigma", type=float, default=12.0, help="mm the metal is blurred over")
    ap.add_argument("--cover", type=float, default=0.9, help="the share of the metal the domains hold")
    ap.add_argument("--hole", type=float, default=20.0, help="mm: holes in a domain narrower than this are filled")
    ap.add_argument("--neck", type=float, default=8.0, help="mm: necks narrower than this are cut")
    ap.add_argument("--tolerance", type=float, default=4.0, help="mm the outlines are simplified to")
    a = ap.parse_args()
    main(a.run, a.label, a.sigma, a.cover, a.hole, a.neck, a.tolerance)
