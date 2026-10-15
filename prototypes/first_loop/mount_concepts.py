"""How the agent steers each mount's joint to the housing (LOP-24; the engineer, 11 October 18:55:
"how will the agent drive the optimisation or induce different material flow constraints so that
different mount-to-housing joining concepts evolve"). The motor side in plan: a free run's members,
and for each mount the concepts' paths, A to its two nearest flange bolts, B to the nearest bearing
bore's ring, C to the nearest wall, D anything but the free run's own arms. Measured on the free run
(the chain's reading step): each mount's arm metal (its open region outside the shell, past the
lug's root), each cell given to the nearest concept path, so the share of the arm that already
follows each concept.

`mount_concepts.py <height-field run> <label>` writes data/first_loop/mount_concepts_<label>.png and
prints the shares."""

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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
import topo_free as tf  # noqa: E402

RUN, LABEL = sys.argv[1], sys.argv[2]
HALF_WIDTH = 12.0  # mm: each path's strip, half the height envelope (as the corridor mode)
PAST_LUG = 30.0  # mm: the metal is read past this distance from the lug's centre (the lug's own root)
REACH = 30.0  # mm: past the lug's distance to the shell, the mount's region (as mount_reach "disc", band 24 + margin)

lay = json.loads((ROOT / "data" / "first_loop" / "contract.json").read_text(encoding="utf-8"))
ch = shh.column_heights(RUN)
h, lo, n = ch["h"], ch["lo"], ch["n"]
rec = json.loads((shh.OUT / f"{RUN}.json").read_text(encoding="utf-8"))
skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                      route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                      height_field=rec["height_field"]["radius_mm"])  # fmt: skip
k_split = model["k_split"]
rooms = np.asarray(model["masks"]["rooms"]).reshape(tuple(n))[:, :, :k_split].any(axis=2)

fine = ndi.zoom(ch["motor_side"], h, order=3)  # the motor side's heights on a 1 mm plan grid
inside = ndi.zoom(rooms.astype(float), h, order=1) > 0.5
shell = ndi.binary_dilation(inside, iterations=4)  # the 4 mm wall round the inside
x0, y0 = lo[0], lo[1]
ext = [x0, x0 + fine.shape[0], y0, y0 + fine.shape[1]]
X, Y = np.meshgrid(x0 + np.arange(fine.shape[0]) + 0.5, y0 + np.arange(fine.shape[1]) + 0.5, indexing="ij")
metal = fine >= 4.0

wall_ij = np.argwhere(shell & ~ndi.binary_erosion(shell))
wall_xy = np.column_stack([x0 + wall_ij[:, 0] + 0.5, y0 + wall_ij[:, 1] + 0.5])
bolts = np.asarray(lay["bolts"], float)
bores = [b for b in lay["bearings"] if b["side"] == "-z"]


def paths(m: dict) -> dict:
    c = np.asarray(m["centre"], float)
    near2 = bolts[np.argsort(np.hypot(*(bolts - c).T))[:2]]
    bore = min(bores, key=lambda b: np.hypot(*(np.asarray(b["axis"]) - c)))
    ax_ = np.asarray(bore["axis"], float)
    u = (c - ax_) / np.linalg.norm(c - ax_)
    ring_pt = ax_ + u * bore["boss_r"]
    wall_pt = wall_xy[np.argmin(np.hypot(*(wall_xy - c).T))]
    return {"A": [(c, near2[0]), (c, near2[1])], "B": [(c, ring_pt)], "C": [(c, wall_pt)], "bore": bore["shaft"]}


def strip(seg: tuple, w: float = HALF_WIDTH) -> np.ndarray:
    a, b = seg
    d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
    q = np.array([-d[1], d[0]]) * w
    return np.array([a + q, b + q, b - q, a - q])


def section(seg: tuple) -> tuple[float, float]:
    """The free run's metal in the path's strip past the lug, as mm² (volume over length), and the length."""
    a, b = seg
    inside_strip = MPath(strip(seg)).contains_points(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    past = np.hypot(X - a[0], Y - a[1]) >= PAST_LUG
    sel = inside_strip & past & ~shell  # the arm itself: outside the shell's own footprint
    length = max(float(np.hypot(*(b - a))) - PAST_LUG, 1.0)
    return float(np.where(sel & metal, fine, 0.0).sum()) / length, length


def region(m: dict) -> np.ndarray:
    """The mount's open region (mount_reach "disc" in plan): within its distance to the shell plus the reach."""
    c = np.asarray(m["centre"], float)
    d_wall = float(np.min(np.hypot(*(wall_xy - c).T)))
    return (np.hypot(X - c[0], Y - c[1]) <= d_wall + REACH) & ~shell


def seg_distance(seg: tuple) -> np.ndarray:
    a, b = seg
    d = b - a
    t = np.clip(((X - a[0]) * d[0] + (Y - a[1]) * d[1]) / max(float(d @ d), 1e-9), 0.0, 1.0)
    return np.hypot(X - (a[0] + t * d[0]), Y - (a[1] + t * d[1]))


def split_arm(m: dict) -> dict:
    """The free run's arm metal round the mount (its open region, outside the shell, past the lug's
    root), each cell given to the nearest concept path: how much of the arm already follows each."""
    ps = paths(m)
    c = np.asarray(m["centre"], float)
    sel = region(m) & metal & (np.hypot(X - c[0], Y - c[1]) >= PAST_LUG)
    segs = [(k, s) for k in "ABC" for s in ps[k]]
    dist = np.stack([seg_distance(s) for _, s in segs])
    owner = np.argmin(dist, axis=0)
    vol = {k: 0.0 for k in "ABC"}
    for idx, (k, _) in enumerate(segs):
        vol[k] += float(np.where(sel & (owner == idx), fine, 0.0).sum()) / 1000.0  # cm³
    total = sum(vol.values())
    return {k: (v, v / total if total else 0.0) for k, v in vol.items()} | {"bore": ps["bore"], "total": total}


colours = {"A": "#1f77b4", "B": "#ff7f0e", "C": "#2ca02c"}
table = {m["name"]: split_arm(m) for m in lay["mounts"]}
arms = np.zeros_like(metal)
for m in lay["mounts"]:
    arms |= region(m) & metal  # the free run's own arms, closed in D

fig, axes = plt.subplots(2, 3, figsize=(21, 14.5))
fig.subplots_adjust(left=0.04, right=0.98, top=0.90, bottom=0.04, wspace=0.12, hspace=0.18)
panels = [("free", "0. The free run: where the metal went"),
          ("A", "A. Carried by the flange's bolts"),
          ("B", "B. Carried by a bearing bore"),
          ("C", "C. Carried by the wall"),
          ("D", "D. Anything but the free run's arms")]  # fmt: skip


def base(ax, faint: bool):
    ax.imshow(np.where(shell, 0.86, 1.0).T, origin="lower", extent=ext, cmap="gray", vmin=0, vmax=1)
    im = ax.imshow(np.where(metal, fine, np.nan).T, origin="lower", extent=ext, cmap="viridis", vmin=4, vmax=60, alpha=0.22 if faint else 1.0)
    for b in bores:
        ax.add_patch(Circle(b["axis"], b["boss_r"], fill=False, ec="k", lw=1.0, ls="--"))
        ax.add_patch(Circle(b["axis"], b["D"] / 2, fill=True, fc="white", ec="k", lw=1.0))
        ax.text(b["axis"][0], b["axis"][1], b["shaft"] + "\nbore", ha="center", va="center", fontsize=9)
    for bx, by in bolts:
        ax.add_patch(Circle((bx, by), 10.0, fill=True, fc="#aaa", ec="k", lw=0.6))
    for m in lay["mounts"]:
        c = m["centre"]
        ax.add_patch(Circle(c, 18.0, fill=True, fc="#444", ec="k", zorder=5))
        ax.text(c[0], c[1] - 34, m["name"], ha="center", fontsize=10, weight="bold", zorder=6)
    ax.set_aspect("equal")
    ax.set_xlim(ext[0] - 5, ext[1] + 5)
    ax.set_ylim(ext[2] - 5, ext[3] + 5)
    ax.tick_params(labelsize=8)
    return im


for ax, (key, title) in zip(axes.ravel(), panels):
    im = base(ax, key != "free")
    for m in lay["mounts"]:
        ps = paths(m)
        for k in "ABC":
            for s in ps[k]:
                a, b = s
                if key == k:
                    ax.add_patch(Polygon(strip(s), closed=True, fc=colours[k], ec=colours[k], alpha=0.5, zorder=4))
                elif key in "ABC":
                    ax.plot([a[0], b[0]], [a[1], b[1]], color="red", lw=1.4, ls=(0, (4, 3)), zorder=4)
        if key == "D":
            ax.contourf(X, Y, region(m).astype(float), levels=[0.5, 1.5], colors=["#9467bd"], alpha=0.3, zorder=3)
    if key == "free":
        fig.colorbar(im, ax=ax, shrink=0.7, label="the free run's member height off its base, mm")
    if key == "D":
        ax.contourf(X, Y, arms.astype(float), levels=[0.5, 1.5], colors=["red"], alpha=0.55, zorder=4)
    ax.set_title(title, fontsize=13, weight="bold")

leg = axes.ravel()[5]
leg.axis("off")
lines = [
    "How the agent steers a mount's joint (each a constraint on the next run):",
    "",
    "Coloured strip: the only place the mount's arm may grow.",
    "    The optimiser decides its form inside: one web or two,",
    "    where it widens, how tall. The agent draws no shape.",
    "Red dashes: paths closed to the arm (keep-out).",
    "Purple: the mount's open region; red: the free run's arms,",
    "    closed (or held to at most 30 % overlap), so the optimiser",
    "    has to find another way: a concept no one listed.",
    "",
    "The free run's arm metal round each mount, by the path it follows:",
]
for name, row in table.items():
    parts = ",  ".join(f"{k} {100 * row[k][1]:.0f} %" for k in "ABC")
    lines.append(f"    {name} ({row['total']:.0f} cm³; nearest bore {row['bore']}): {parts}")
lines += ["", "Grey: the shell in plan; grey discs: the flange's bolt bosses;", "dashed circles: the trade's boss radius round each bore."]
leg.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=11.5, family="DejaVu Sans")
fig.suptitle(f"Mount-to-housing concepts, one free run read and steered: the motor side in plan ({LABEL})", fontsize=15, weight="bold")
out = ROOT / "data" / "first_loop" / f"mount_concepts_{LABEL}.png"
fig.savefig(out, dpi=100)
print(out)
for name, row in table.items():
    print(name, f"arm {row['total']:.1f} cm3, nearest bore {row['bore']}:", " ".join(f"{k} {row[k][0]:.1f} cm3 ({100 * row[k][1]:.0f} %)" for k in "ABC"))
