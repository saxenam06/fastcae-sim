"""An iteration's design space as production's features, drawn from the last run's members (LOP-24;
the engineer, 11 October 20:16: "next iteration further refining it... clearly defining the rib
patterns if they are now more clearly visible"). Each half's members (columns at least 4 mm high)
are read into:
- a **ring** round each bore of the half that the members wrap (at least `--wrap` of an annulus round
  the bore covered): an annulus from the bore's wall out to where its members end radially;
- **ribs** along the members' centre-lines (the skeleton, pruned of spurs under `--spur` mm, each
  branch smoothed): a strip `--rib` mm wide round each branch, its ends run on to the ring, boss or
  member they reach;
- **pads** where a member is broader than `--pad` mm: its own outline, kept as it is.
The union of the features is the next design space: the optimiser places metal in them only, and
how much of each it fills says whether the feature is right (`space_fill.py`; the least-metal
objective). Each feature a region in data/first_loop/<label>.json (`topo_free.py --space`), pictured.

    space_features.py <label> --run <run> [--rib 8] [--pad 24] [--wrap 0.5] [--spur 12] [--tolerance 1.0]"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from skimage.morphology import skeletonize  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
from space_from_runs import disc, polygons_of  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0
HALVES = (("motor_side", "-z"), ("cover", "+z"))


def prune(sk: np.ndarray, spur: int) -> np.ndarray:
    """The skeleton with its spurs (end branches shorter than `spur` cells) removed, a few passes."""
    k = np.ones((3, 3), int)
    sk = sk.copy()
    for _ in range(3):
        nb = ndi.convolve(sk.astype(int), k, mode="constant") - sk
        ends = sk & (nb == 1)
        junction = sk & (nb >= 3)
        lab, nl = ndi.label(sk & ~ndi.binary_dilation(junction, structure=np.ones((3, 3), bool)), structure=np.ones((3, 3), bool))
        if nl == 0:
            break
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, nl + 1))
        touches_end = ndi.maximum(ends.astype(int), lab, range(1, nl + 1))
        drop = np.isin(lab, 1 + np.flatnonzero((sizes < spur) & (touches_end > 0)))
        if not drop.any():
            break
        sk &= ~drop
    return sk


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("label")
    ap.add_argument("--run", required=True)
    ap.add_argument("--rib", type=float, default=8.0, help="mm, the ribs' strip width")
    ap.add_argument("--pad", type=float, default=24.0, help="mm, a member broader than this stays a pad")
    ap.add_argument("--wrap", type=float, default=0.5, help="the share of an annulus round a bore its members must cover for a ring")
    ap.add_argument("--spur", type=float, default=12.0, help="mm, skeleton spurs shorter than this dropped")
    ap.add_argument("--tolerance", type=float, default=1.0, help="mm the outlines are simplified to")
    a = ap.parse_args()

    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    ch = shh.column_heights(a.run)
    h, lo = ch["h"], ch["lo"]
    x0, y0 = float(lo[0]), float(lo[1])
    out, pics, stats = {}, {}, []
    for half, side in HALVES:
        big = ndi.zoom(ch[half], h, order=3)
        member = big >= MEMBER
        member = ndi.binary_opening(member, structure=disc(1.5))
        X, Y = np.meshgrid(x0 + np.arange(big.shape[0]) + 0.5, y0 + np.arange(big.shape[1]) + 0.5, indexing="ij")
        feats = np.zeros(big.shape, dtype=np.int32)  # 1 ring, 2 rib, 3 pad
        regions = []
        # rings: each bore of this side its members wrap
        for b in (b for b in lay["bearings"] if b["side"] == side):
            r = np.hypot(X - b["axis"][0], Y - b["axis"][1])
            r_in = b["D"] / 2.0
            band_r = (r >= r_in) & (r <= r_in + 16.0)
            if band_r.sum() == 0 or member[band_r].mean() < a.wrap:
                continue
            # where the members end radially: the 80th percentile of the radius of member cells within 40 mm of the bore's wall
            near = member & (r >= r_in) & (r <= r_in + 40.0)
            r_out = float(np.percentile(r[near], 80)) if near.any() else r_in + 12.0
            ring = (r >= r_in) & (r <= max(r_out, r_in + 10.0))
            feats[ring & (feats == 0)] = 1
            for j, poly in enumerate(polygons_of(ring, x0, y0, a.tolerance)):
                regions.append({"name": f"ring round the {b['shaft']} bore" + (f" ({j + 1})" if j else ""), "kind": "ring", **poly})
            stats.append((half, f"ring round the {b['shaft']} bore", r_in, r_out))
        # pads: members broader than --pad (the distance to their edge more than half of it)
        dist = ndi.distance_transform_edt(member)
        broad = ndi.binary_dilation(dist >= a.pad / 2.0, structure=disc(a.pad / 2.0)) & member
        feats[broad & (feats == 0)] = 3
        # ribs: strips round the pruned, smoothed centre-lines of the rest
        thin = member & ~broad
        sk = prune(skeletonize(thin), int(a.spur))
        strip = ndi.binary_dilation(sk, structure=disc(a.rib / 2.0))
        feats[strip & (feats == 0)] = 2
        for kind, code in (("pads", 3), ("ribs", 2)):
            part = feats == code
            if part.sum() < 50:
                continue
            for j, poly in enumerate(polygons_of(part, x0, y0, a.tolerance)):
                regions.append({"name": f"{kind} {j + 1}", "kind": kind[:-1], **poly})
        out[half] = regions
        pics[half] = (feats, member)
    rec = {"label": a.label, "from_run": a.run, "rib_mm": a.rib, "pad_mm": a.pad, "wrap": a.wrap, "spur_mm": a.spur, "halves": out}
    path = OUT / f"{a.label}.json"
    path.write_text(json.dumps(rec, indent=1), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    feats0 = pics["cover"][0]
    ext = [x0, x0 + feats0.shape[0], y0, y0 + feats0.shape[1]]
    for ax, (half, side) in zip(axes, HALVES):
        feats, member = pics[half]
        ax.imshow(np.where(member, 0.75, 1.0).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
        ax.imshow(np.where(feats > 0, feats.astype(float), np.nan).T, origin="lower", extent=ext, cmap="Set1", vmin=1, vmax=9, alpha=0.6)
        for reg in out[half]:
            ax.add_patch(Polygon(np.asarray(reg["outline"]), closed=True, fill=False, ec="k", lw=0.7))
        for b in lay["bearings"]:
            if b["side"] == side:
                ax.add_patch(Circle(b["axis"], b["D"] / 2, fill=True, fc="white", ec="k"))
        for bx, by in lay["bolts"]:
            ax.add_patch(Circle((bx, by), 10.0, fill=False, ec="#666", lw=0.6))
        if half == "motor_side":
            for m in lay["mounts"]:
                ax.add_patch(Circle(m["centre"], 18.0, fc="#444", ec="k"))
        ax.set_aspect("equal")
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        n_k = {k: sum(1 for r in out[half] if r["kind"] == k) for k in ("ring", "rib", "pad")}
        ax.set_title(f"{half.replace('_', ' ')}: {n_k['ring']} rings, {n_k['rib']} rib groups, {n_k['pad']} pads (grey: the run's members)", fontsize=10)
    fig.suptitle(f"The design space {a.label} as features: red rings, blue ribs {a.rib:g} mm wide, purple pads (from {a.run[-60:]})", fontsize=10)
    pic = OUT / f"{a.label}.png"
    fig.savefig(pic, dpi=100)
    print(path)
    print(pic)
    for half, name, r_in, r_out in stats:
        print(f"  {half}: {name}: {r_in:.0f} to {r_out:.0f} mm")


if __name__ == "__main__":
    main()
