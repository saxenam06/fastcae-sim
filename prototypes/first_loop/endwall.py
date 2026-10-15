"""PROTOTYPE (LOP) - where the tilt comes from: the end walls' bowing, and each seat's own share.

From a stored FE answer (fe_<stem>.npz, no solve), for each load case and each half:
- the out-of-plane displacement u_z of the outer end faces (one face per pod, since the pods step),
  drawn in plan with the seats, bolts and mounts;
- at each seat, two arrows: where the seat's axis leans (its own rotation), and where it leans
  against its shaft's line (what the bearing feels).
And a table per seat and case that splits the seat's rotation into the wall's share (the slope of
the end face in a ring round the boss, fitted as a plane) and the seat's own share beyond the wall
(the boss and seat bending on their own). A seat that turns with its wall wants the wall stiffened
(spokes, a rim, a conical web, thickness); one that turns more than its wall wants its boss tied in
(gussets, a longer boss, a web between bosses).

Run: uv run python prototypes/first_loop/endwall.py [stem]     (default: lobed_e10)
Reads data/first_loop/fe_<stem>.{npz,json} and <stem>.json; writes data/first_loop/endwall_<stem>.png.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.path import Path as MplPath

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "first_loop"
ON_FACE = 0.3  # mm: a node this near a pod's end plane lies on its end face
RING = (4.0, 24.0)  # mm beyond the seat's radius: the ring of wall whose slope is the wall's share
HALF_OF = {"-z": "motor_side", "+z": "cover"}


def pods_of(cad: dict) -> list[dict]:
    """The lobed form's pods; the convex shell is one pod spanning the whole housing."""
    if "pods" in cad:
        return cad["pods"]
    return [
        {"shaft": shaft, "z": [cad["z"]["lo"], cad["z"]["hi"]], "outer": cad["outer_outline"]}
        for shaft in ("input", "intermediate", "output")
    ]


def end_faces(cad: dict, half: str, nodes: np.ndarray) -> dict[str, np.ndarray]:
    """The node ids on each pod's outer end face of one half."""
    faces = {}
    for pod in pods_of(cad):
        z_end = pod["z"][0] if half == "motor_side" else pod["z"][1]
        on_plane = np.flatnonzero(np.abs(nodes[:, 2] - z_end) < ON_FACE)
        inside = MplPath(np.asarray(pod["outer"])).contains_points(nodes[on_plane, :2])
        faces[pod["shaft"]] = on_plane[inside]
    return faces


def rigid_fit(x: np.ndarray, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The best-fit rigid motion u = t + theta x (x - c) of a node set, as (t, theta)."""
    c = x.mean(axis=0)
    r = x - c
    # Rows: u_i = t + theta x r_i; theta x r = -r x theta = -skew(r) theta.
    a = np.zeros((3 * len(x), 6))
    a[0::3, 0] = a[1::3, 1] = a[2::3, 2] = 1.0
    a[0::3, 4], a[0::3, 5] = r[:, 2], -r[:, 1]
    a[1::3, 3], a[1::3, 5] = -r[:, 2], r[:, 0]
    a[2::3, 3], a[2::3, 4] = r[:, 1], -r[:, 0]
    sol, *_ = np.linalg.lstsq(a, u.ravel(), rcond=None)
    return sol[:3], sol[3:]


def joint_share(field, cad: dict, fe: dict, halves: dict, case_index: int, case: str) -> list[str]:
    """How much of each shaft's line tilt is the two halves turning against each other at the
    split: each half's rigid motion fitted over its split-face nodes, the relative rotation, and
    the line tilt it alone would give (the cover's seat carried round the split plane)."""
    z_split = cad["z"]["split"]
    fits = {}
    for half, (nodes, offset) in halves.items():
        ids = np.flatnonzero(np.abs(nodes[:, 2] - z_split) < ON_FACE)
        u = field["u"][offset : offset + 3 * len(nodes), case_index].reshape(-1, 3)
        fits[half] = rigid_fit(nodes[ids], u[ids])
    theta = fits["cover"][1] - fits["motor_side"][1]
    shift = fits["cover"][0] - fits["motor_side"][0]
    lines = [
        f"{case}: at the split the halves turn {1000 * math.hypot(theta[0], theta[1]):.2f} mrad against "
        f"each other and shift {1000 * math.hypot(shift[0], shift[1]):.0f} µm sideways"
    ]
    for shaft, sh in fe["cases"][case]["shafts"].items():
        a_, b_ = fe["cases"][case]["seats"][f"{shaft} -z"], fe["cases"][case]["seats"][f"{shaft} +z"]
        measured = np.array([b_["u"][0] - a_["u"][0], b_["u"][1] - a_["u"][1]]) / sh["span_mm"]
        z_c = next(0.5 * (b["z"][0] + b["z"][1]) for b in cad["bearings"] if b["shaft"] == shaft and b["side"] == "+z")
        from_joint = np.array([theta[1], -theta[0]]) * (z_c - z_split) / sh["span_mm"]
        lines.append(
            f"   {shaft:13s} line tilt {1000 * np.hypot(*measured):.2f} mrad; from the joint alone "
            f"{1000 * np.hypot(*from_joint):.2f}; the rest (the lobes bending) {1000 * np.hypot(*(measured - from_joint)):.2f}"
        )
    return lines


def wall_slope(xy: np.ndarray, uz: np.ndarray) -> tuple[float, float]:
    """The rotation (theta_x, theta_y) of the plane u_z = a + b x + c y fitted to a ring of wall:
    u = theta x r gives u_z = theta_x y - theta_y x, so theta_x = c and theta_y = -b."""
    a = np.c_[np.ones(len(xy)), xy]
    coef, *_ = np.linalg.lstsq(a, uz, rcond=None)
    return float(coef[2]), float(-coef[1])


def main(stem: str = "lobed_e10") -> None:
    field = np.load(OUT / f"fe_{stem}.npz")
    fe = json.loads((OUT / f"fe_{stem}.json").read_text(encoding="utf-8"))
    cad = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    cases = list(fe["cases"])
    halves = {
        "motor_side": (field["motor_side_nodes"], int(field["motor_side_offset"])),
        "cover": (field["cover_nodes"], int(field["cover_offset"])),
    }
    seats = {(b["shaft"], b["side"]): b for b in cad["bearings"]}

    fig, axes = plt.subplots(len(cases), 2, figsize=(16, 8 * len(cases)))
    rows = []
    for i, case in enumerate(cases):
        out = fe["cases"][case]
        for j, (half, (nodes, offset)) in enumerate(halves.items()):
            u = field["u"][offset : offset + 3 * len(nodes), i].reshape(-1, 3)
            ax = axes[i][j]
            faces = end_faces(cad, half, nodes)
            ids = np.concatenate(list(faces.values()))
            uz = 1000 * u[ids, 2]
            limit = max(1.0, float(np.percentile(np.abs(uz), 99)))
            sc = ax.scatter(nodes[ids, 0], nodes[ids, 1], c=uz, s=3, cmap="coolwarm", vmin=-limit, vmax=limit)
            fig.colorbar(sc, ax=ax, label="u_z, µm (+ out of the housing on the cover, into it on the motor side)")
            for pod in pods_of(cad):
                outline = np.asarray(pod["outer"] + [pod["outer"][0]])
                ax.plot(outline[:, 0], outline[:, 1], color="0.5", lw=0.8)
            for (shaft, side), b in seats.items():
                if HALF_OF[side] != half:
                    continue
                cx, cy = b["axis"]
                ax.add_patch(plt.Circle((cx, cy), b["D"] / 2, fill=False, color="k", lw=1.2))
                seat = out["seats"][f"{shaft} {side}"]
                tx, ty = seat["theta"][0], seat["theta"][1]
                # The seat's axis, (theta_y, -theta_x, 1) after the rotation, leans this way (mm per m).
                lean = np.array([ty, -tx]) * 1000
                sh = out["shafts"][shaft]
                a_, b_ = out["seats"][f"{shaft} -z"], out["seats"][f"{shaft} +z"]
                line = np.array([(b_["u"][0] - a_["u"][0]), (b_["u"][1] - a_["u"][1])]) / sh["span_mm"] * 1000
                rel = lean - line
                scale = 40.0  # mm of arrow per mrad
                ax.annotate("", xy=(cx + scale * lean[0], cy + scale * lean[1]), xytext=(cx, cy),
                            arrowprops=dict(arrowstyle="->", color="k", lw=2))  # fmt: skip
                ax.annotate("", xy=(cx + scale * rel[0], cy + scale * rel[1]), xytext=(cx, cy),
                            arrowprops=dict(arrowstyle="->", color="m", lw=2))  # fmt: skip
                # The wall's share: the end face's slope in a ring round the seat.
                face = faces[shaft]
                r = np.hypot(nodes[face, 0] - cx, nodes[face, 1] - cy)
                ring = face[(r > b["D"] / 2 + RING[0]) & (r < b["D"] / 2 + RING[1])]
                wx, wy = wall_slope(nodes[ring, :2], u[ring, 2]) if len(ring) > 20 else (math.nan, math.nan)
                own = 1000 * math.hypot(tx, ty)
                wall = 1000 * math.hypot(wx, wy)
                local = 1000 * math.hypot(tx - wx, ty - wy)
                rows.append((case, shaft, side, own, wall, local, math.hypot(*rel), len(ring)))
                ax.text(cx, cy - b["D"] / 2 - 6, f"{shaft} {side}\nown {own:.2f}  wall {wall:.2f}  local {local:.2f} mrad",
                        ha="center", va="top", fontsize=8)  # fmt: skip
            for m in cad["mounts"]:
                ax.plot(*m["centre"], "rs", ms=8)
            for hole in cad.get("bolts", []):
                c = hole["centre"] if isinstance(hole, dict) else hole
                ax.plot(c[0], c[1], "o", color="orange", ms=4)
            ax.set_aspect("equal")
            ax.set_title(f"{case}: {half.replace('_', ' ')} end faces, u_z; arrows: seat's lean (black), against the shaft (magenta)")
    fig.suptitle(f"{stem}: where the end walls bow (plan view, x right, y up; arrows 40 mm per mrad)")
    fig.tight_layout()
    fig.savefig(OUT / f"endwall_{stem}.png", dpi=110)

    print(f"{'case':14s} {'seat':18s} {'own':>6s} {'wall':>6s} {'local':>6s} {'vs shaft':>8s}  ring nodes  (mrad)")
    for case, shaft, side, own, wall, local, rel, n in rows:
        print(f"{case:14s} {shaft + ' ' + side:18s} {own:6.2f} {wall:6.2f} {local:6.2f} {rel:8.2f}  {n}")
    for i, case in enumerate(cases):
        print("\n".join(joint_share(field, cad, fe, halves, i, case)))


if __name__ == "__main__":
    main(*sys.argv[1:2])
