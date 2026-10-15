"""Where a design's modes live (LOP-24, the plan's step 3: the clashing mode located by its shape, then
steered): for each mode within `--within` of a gear mesh's frequency (all with `--all`), its kinetic
energy (each node's lumped mass times its mass-normalised displacement squared; they sum to one) shared
among the housing's parts: each bore's surroundings (within its boss radius plus 40 mm in plan, the
nearer boss's edge taking a point both reach), each mount's (within 60 mm), the split flange (within
12 mm of the split, outside those) and the walls; and a plan picture of each half, every node coloured
by its displacement in the mode. FE keeps the shapes in `fe_<design>_modes.npz` (fe.py, MODE_SHAPES).

    mode_shape.py <design> [--within 0.10] [--all]

Prints a line a mode; writes data/first_loop/modes_<design>.png and modes_<design>.json."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
BORE_REACH = 40.0  # mm past a bore's boss radius
MOUNT_REACH = 60.0  # mm round a mount's centre
FLANGE_BAND = 12.0  # mm either side of the split


def parts(xyz: np.ndarray, lay: dict) -> tuple[np.ndarray, list[str]]:
    """Each node's part (an index into the names)."""
    z_split = float(lay["z"]["split"])
    names, owner = [], np.full(len(xyz), -1)
    best = np.full(len(xyz), np.inf)
    for side in ("-z", "+z"):
        here = xyz[:, 2] < z_split if side == "-z" else xyz[:, 2] >= z_split
        for b in (b for b in lay["bearings"] if b["side"] == side):
            r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
            edge = r - float(b["boss_r"])
            take = here & (edge <= BORE_REACH) & (edge < best)
            names.append(f"the {b['shaft']} bore ({'motor side' if side == '-z' else 'cover'})")
            owner[take] = len(names) - 1
            best[take] = edge[take]
    for m in lay["mounts"]:
        r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
        take = r <= MOUNT_REACH
        names.append(m["name"])
        owner[take] = len(names) - 1
    flange = (owner < 0) & (np.abs(xyz[:, 2] - z_split) <= FLANGE_BAND)
    names.append("the split flange")
    owner[flange] = len(names) - 1
    names.append("the walls")
    owner[owner < 0] = len(names) - 1
    return owner, names


def main(design: str, within: float, every: bool) -> list[dict]:
    fe = json.loads((OUT / f"fe_{design}.json").read_text(encoding="utf-8"))
    mz = np.load(OUT / f"fe_{design}_modes.npz")
    mesh = np.load(OUT / f"fe_{design}.npz")
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    halves = [h for h in ("motor_side", "cover") if f"{h}_nodes" in mesh]
    xyz = np.concatenate([mesh[f"{h}_nodes"] for h in halves])
    start = {h: int(mesh[f"{h}_offset"]) // 3 for h in halves}
    hz, mag, mass = np.asarray(mz["hz"]), np.asarray(mz["magnitude"], float), np.asarray(mz["node_mass"], float)
    owner, names = parts(xyz, lay)
    orders = fe.get("mesh_hz", {})
    rows = []
    for k, f in enumerate(hz):
        near = min(((name, (f - o) / o) for name, o in orders.items()), key=lambda t: abs(t[1])) if orders else (None, np.inf)
        if not every and abs(near[1]) > within:
            continue
        energy = mass * mag[:, k] ** 2
        share = np.bincount(owner, weights=energy, minlength=len(names)) / max(energy.sum(), 1e-30)
        top = np.argsort(share)[::-1][:4]
        rows.append({"mode": k + 1, "hz": float(f), "order": near[0], "off": float(near[1]),
                     "shares": {names[i]: float(share[i]) for i in np.argsort(share)[::-1] if share[i] >= 0.01}})  # fmt: skip
        print(f"mode {k + 1}: {f:,.0f} Hz ({near[0]}'s {orders.get(near[0], 0):,.0f} Hz, {100 * near[1]:+.1f} %): "
              + ", ".join(f"{100 * share[i]:.0f} % {names[i]}" for i in top))  # fmt: skip
    (OUT / f"modes_{design}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    if not rows:
        print("no mode near an order")
        return rows

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(rows), 2, figsize=(12, 5.6 * len(rows)), squeeze=False)
    for row, (ax_m, ax_c) in zip(rows, axes):
        k = row["mode"] - 1
        u = mag[:, k] / max(mag[:, k].max(), 1e-30)
        for ax, h in ((ax_m, "motor_side"), (ax_c, "cover")):
            if h not in start:
                continue
            n_h = len(mesh[f"{h}_nodes"])
            sl = slice(start[h], start[h] + n_h)
            order = np.argsort(u[sl])
            p = xyz[sl][order]
            sc = ax.scatter(p[:, 0], p[:, 1], c=u[sl][order], s=1.5, cmap="inferno", vmin=0, vmax=1, linewidths=0)
            for b in lay["bearings"]:
                if (b["side"] == "-z") == (h == "motor_side"):
                    ax.add_patch(plt.Circle(b["axis"], b["D"] / 2, fill=False, color="c", lw=0.8))
            for m in lay["mounts"]:
                ax.plot(*m["centre"], "c+")
            ax.set_aspect("equal")
            ax.set_title(f"{h}: mode {row['mode']}, {row['hz']:,.0f} Hz ({row['order']} {100 * row['off']:+.1f} %)", fontsize=9)
        fig.colorbar(sc, ax=ax_c, shrink=0.7, label="displacement in the mode (of its largest)")
    fig.suptitle(f"{design}: the modes near an order, from above")
    png = OUT / f"modes_{design}.png"
    fig.savefig(png, dpi=100, bbox_inches="tight")
    print(png)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("design")
    ap.add_argument("--within", type=float, default=0.10, help="a mode this near an order (a share of it) is read")
    ap.add_argument("--all", action="store_true", help="read every mode")
    a = ap.parse_args()
    main(a.design, a.within, a.all)
