"""The next iteration's design space from the last one's fill (LOP-24; the engineer, 11 October 20:16:
iterate the design space until the optimiser fills its features, then stop). Region by region, from
the run's own members inside each region (a column at least 4 mm high) and its fill (`space_fill.py`):
- under `--drop` of its plan covered: dropped (the physics does not want it);
- under `--trim` covered: trimmed to the metal placed in it (closed over 4 mm, grown 2 mm);
- at least `--full` covered: grown by `--grow` mm (pressed against its own outline, it may want more);
- between: kept as it is.
Converged when every region lies between `--trim` and `--full`. Writes data/first_loop/<label>.json
(`topo_free.py --space`) and its picture, and prints what it did to each region.

    space_refine.py <label> --run <run> [--drop 0.45] [--trim 0.7] [--full 0.95] [--grow 4]"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
import topo_free as tf  # noqa: E402
from space_from_runs import disc, polygons_of  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0
HALVES = (("motor_side", "-z"), ("cover", "+z"))


def mask_of(reg: dict, pts: np.ndarray, shape) -> np.ndarray:
    inside = MPath(np.asarray(reg["outline"], float)).contains_points(pts)
    for hole in reg.get("holes", []):
        inside &= ~MPath(np.asarray(hole, float)).contains_points(pts)
    return inside.reshape(shape)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("label")
    ap.add_argument("--run", required=True)
    ap.add_argument("--drop", type=float, default=0.45)
    ap.add_argument("--trim", type=float, default=0.7)
    ap.add_argument("--full", type=float, default=0.95)
    ap.add_argument("--grow", type=float, default=4.0)
    a = ap.parse_args()

    rec = json.loads((OUT / f"{a.run}.json").read_text(encoding="utf-8"))
    space = tf.space_regions(rec["space"])
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    ch = shh.column_heights(a.run)
    h, lo = ch["h"], ch["lo"]
    x0, y0 = float(lo[0]), float(lo[1])
    out, pics, actions = {}, {}, []
    for half, side in HALVES:
        big = ndi.zoom(ch[half], h, order=3)
        member = big >= MEMBER
        X, Y = np.meshgrid(x0 + np.arange(big.shape[0]) + 0.5, y0 + np.arange(big.shape[1]) + 0.5, indexing="ij")
        pts = np.column_stack([X.ravel(), Y.ravel()])
        keep = np.zeros(big.shape, dtype=np.int32)  # the next space, labelled by region index + 1
        names = {}
        for k, reg in enumerate(space["halves"].get(half, [])):
            m = mask_of(reg, pts, big.shape)
            area = int(m.sum())
            if area == 0:
                continue
            covered = float((member & m).sum()) / area
            if covered < a.drop:
                actions.append((half, reg["name"], covered, "dropped"))
                continue
            if covered < a.trim:
                new = ndi.binary_dilation(ndi.binary_closing(member & m, structure=disc(2.0)), structure=disc(2.0))
                what = "trimmed to its metal"
            elif covered >= a.full:
                new = ndi.binary_dilation(m, structure=disc(a.grow))
                what = f"grown {a.grow:g} mm"
            else:
                new = m
                what = "kept"
            keep[new & (keep == 0)] = k + 1
            names[k + 1] = reg["name"]
            actions.append((half, reg["name"], covered, what))
        regs = []
        for code, name in names.items():
            for j, poly in enumerate(polygons_of(keep == code, x0, y0, 1.0)):
                regs.append({"name": name + (f" ({j + 1})" if j else ""), **poly})
        out[half] = regs
        pics[half] = (keep, member)
    path = OUT / f"{a.label}.json"
    path.write_text(json.dumps({"label": a.label, "from_run": a.run, "from_space": rec["space"], "drop": a.drop, "trim": a.trim,
                                "full": a.full, "grow_mm": a.grow, "halves": out}, indent=1), encoding="utf-8")  # fmt: skip

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    keep0 = pics["cover"][0]
    ext = [x0, x0 + keep0.shape[0], y0, y0 + keep0.shape[1]]
    for ax, (half, side) in zip(axes, HALVES):
        keep, member = pics[half]
        ax.imshow(np.where(member, 0.7, 1.0).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
        for reg in out[half]:
            ax.add_patch(Polygon(np.asarray(reg["outline"]), closed=True, fc="#4a7bd055", ec="#1f4fa0", lw=0.8))
        for b in lay["bearings"]:
            if b["side"] == side:
                ax.add_patch(Circle(b["axis"], b["D"] / 2, fill=True, fc="white", ec="k"))
        if half == "motor_side":
            for m in lay["mounts"]:
                ax.add_patch(Circle(m["centre"], 18.0, fc="#444", ec="k"))
        ax.set_aspect("equal")
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        n_act = {w: sum(1 for x in actions if x[0] == half and x[3].startswith(w)) for w in ("dropped", "trimmed", "grown", "kept")}
        ax.set_title(f"{half.replace('_', ' ')}: " + ", ".join(f"{v} {k}" for k, v in n_act.items()) + " (grey: the run's members)", fontsize=10)
    fig.suptitle(f"The design space {a.label}, refined from the fill of {rec['space']}", fontsize=11)
    pic = OUT / f"{a.label}.png"
    fig.savefig(pic, dpi=100)
    print(path)
    print(pic)
    for half, name, covered, what in actions:
        print(f"  {half}: {name}: {100 * covered:.0f} % covered → {what}")


if __name__ == "__main__":
    main()
