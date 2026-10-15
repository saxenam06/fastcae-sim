"""The mass sweep read (LOP-24; a campaign's first move, `mass_sweep.sh`): each height-field run's
members in plan, half by half, side by side; then, over the runs of one plan smoothing, how many
place a member at each point (the stable load paths) and the least budget at which a member stands
there (the core ones, which appear first). Each run's own numbers in its title: the budget, the
optimiser's binary check against its lines (with its factor of safety), the members' cover of the
inside's plan and their median width on their centre-lines.

    sweep_picture.py <label> <run> [<run> ...]

Writes data/first_loop/sweep_fields_<label>.png and sweep_rank_<label>.png, and prints a line a run."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from skimage.morphology import skeletonize  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
import topo_free as tf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0  # mm: a column at least this high off its base holds a member
HALVES = (("motor_side", "-z", "motor side"), ("cover", "+z", "cover"))


def read(run: str) -> dict:
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    ch = shh.column_heights(run)
    return {"run": run, "rec": rec, "ch": ch}


def main(label: str, runs: list[str]) -> None:
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    data = [read(r) for r in runs]
    data.sort(key=lambda d: (d["rec"]["height_field"]["radius_mm"], d["rec"]["budget_kg"]))
    h, lo, n = data[0]["ch"]["h"], data[0]["ch"]["lo"], data[0]["ch"]["n"]
    rec0 = data[0]["rec"]
    skin = rec0["skin"]["wall_mm"] if rec0["skin"]["mass_share"] < 1.0 else None
    model = tf.build_free(h, layout=rec0.get("layout", tf.LAYOUT), band=rec0.get("band_mm"), skin=skin, cavity=rec0.get("cavity", "cup"),
                          route=rec0.get("route", "split"), flange=bool(rec0.get("flange")), mount_reach=rec0.get("mount_reach") or "corridor",
                          height_field=rec0["height_field"]["radius_mm"])  # fmt: skip
    ks = model["k_split"]
    rooms = np.asarray(model["masks"]["rooms"]).reshape(tuple(n))
    inside = {"motor_side": rooms[:, :, :ks].any(axis=2), "cover": rooms[:, :, ks:].any(axis=2)}
    ext = [lo[0], lo[0] + n[0] * h, lo[1], lo[1] + n[1] * h]

    def marks(ax, side: str, mounts: bool) -> None:
        for b in lay["bearings"]:
            if b["side"] == side:
                ax.add_patch(Circle(b["axis"], b["D"] / 2, fill=True, fc="white", ec="k", lw=0.8))
        for bx, by in lay["bolts"]:
            ax.add_patch(Circle((bx, by), 10.0, fill=False, ec="#666", lw=0.6))
        if mounts:
            for m in lay["mounts"]:
                ax.add_patch(Circle(m["centre"], 18.0, fill=True, fc="#444", ec="k"))
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])

    stats = []
    fig, axes = plt.subplots(2, len(data), figsize=(4.2 * len(data), 9.0), squeeze=False)
    fig.subplots_adjust(left=0.03, right=0.92, top=0.86, bottom=0.03, wspace=0.05, hspace=0.12)
    for j, d in enumerate(data):
        rec, ch = d["rec"], d["ch"]
        b = rec.get("binary") or {}
        row = {"run": d["run"], "budget": rec["budget_kg"], "smooth": rec["height_field"]["radius_mm"], "safety": rec.get("safety", 1.0),
               "worst": b.get("worst"), "bed": b.get("bed_worst"), "kg": b.get("mass_kg")}  # fmt: skip
        for i, (half, side, name) in enumerate(HALVES):
            m4 = ch[half]
            big = ndi.zoom(m4, h, order=3)
            big_in = ndi.zoom(inside[half].astype(float), h, order=1) > 0.5
            member = big >= MEMBER
            sk = skeletonize(member)
            widths = 2.0 * ndi.distance_transform_edt(member)[sk]
            row[f"{half}_cover"] = 100.0 * (member & big_in).sum() / max(big_in.sum(), 1)
            row[f"{half}_width"] = float(np.median(widths)) if widths.size else 0.0
            ax = axes[i, j]
            ax.imshow(np.where(big_in, 0.88, 1.0).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
            im = ax.imshow(np.where(member, big, np.nan).T, origin="lower", extent=ext, cmap="viridis", vmin=MEMBER, vmax=40)
            marks(ax, side, half == "motor_side")
            ax.set_title(f"{name}: covers {row[f'{half}_cover']:.0f} %, width {row[f'{half}_width']:.0f} mm", fontsize=9)
        ok = "meets its lines" if (row["worst"] or 9) <= 1.0 + 1e-3 and (row["bed"] or 0) <= 1.0 + 1e-3 else "misses its lines"
        axes[0, j].text(0.5, 1.16, f"{row['budget']:g} kg, smoothing {row['smooth']:g} mm\n"
                        f"model: tilt {row['worst']:.3f}, bed {row['bed']:.3f} of the lines / {row['safety']:g} ({ok})",
                        transform=axes[0, j].transAxes, ha="center", va="bottom", fontsize=10, weight="bold")  # fmt: skip
        stats.append(row)
    cax = fig.add_axes([0.935, 0.2, 0.012, 0.55])
    fig.colorbar(im, cax=cax, label="member height off its base, mm")
    fig.suptitle(f"The free run's mass sweep ({label}): each half's members in plan; grey, the inside's plan", fontsize=13, weight="bold")
    out1 = OUT / f"sweep_fields_{label}.png"
    fig.savefig(out1, dpi=95)
    plt.close(fig)

    # the ranking over the runs of the most common smoothing
    smooth = max(set(r["smooth"] for r in stats), key=lambda s: sum(r["smooth"] == s for r in stats))
    same = [d for d in data if d["rec"]["height_field"]["radius_mm"] == smooth]
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 11.0), squeeze=False)
    fig.subplots_adjust(left=0.03, right=0.9, top=0.9, bottom=0.03, wspace=0.12, hspace=0.12)
    budgets = [d["rec"]["budget_kg"] for d in same]
    for i, (half, side, name) in enumerate(HALVES):
        big_in = ndi.zoom(inside[half].astype(float), h, order=1) > 0.5
        stack = np.stack([ndi.zoom(d["ch"][half], h, order=3) >= MEMBER for d in same])
        count = stack.sum(axis=0)
        first = np.where(stack.any(axis=0), np.asarray(budgets)[np.argmax(stack, axis=0)], np.nan)
        for k, (arr, title, cmap, vmax) in enumerate(((count, f"{name}: in how many of the {len(same)} runs a member stands", "magma_r", len(same)),
                                                     (first, f"{name}: the least budget with a member there, kg", "plasma", max(budgets)))):  # fmt: skip
            ax = axes[i, k]
            ax.imshow(np.where(big_in, 0.88, 1.0).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
            shown = np.where(count > 0, arr, np.nan)
            im = ax.imshow(shown.T, origin="lower", extent=ext, cmap=cmap, vmin=(1 if k == 0 else min(budgets)), vmax=vmax)
            marks(ax, side, half == "motor_side")
            ax.set_title(title, fontsize=10)
            fig.colorbar(im, ax=ax, shrink=0.8)
    fig.suptitle(f"The mass sweep's ranking ({label}, smoothing {smooth:g} mm, budgets {', '.join(f'{b:g}' for b in budgets)} kg)", fontsize=13, weight="bold")
    out2 = OUT / f"sweep_rank_{label}.png"
    fig.savefig(out2, dpi=95)
    plt.close(fig)
    print(out1)
    print(out2)
    for r in stats:
        print(f"{r['budget']:g} kg, smoothing {r['smooth']:g}: model tilt {r['worst']:.3f}, bed {r['bed']:.3f} (of lines/{r['safety']:g}); "
              f"placed {r['kg']} kg; motor side covers {r['motor_side_cover']:.0f} % at {r['motor_side_width']:.0f} mm, "
              f"cover {r['cover_cover']:.0f} % at {r['cover_width']:.0f} mm | {r['run']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
