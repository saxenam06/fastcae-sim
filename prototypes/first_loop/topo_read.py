"""PROTOTYPE (LOP-16) - an optimisation's field read in plan, face by face: the first step of
interpreting it into the generator's recipe.

For each column of voxels along the shafts, in each half:
- **on the end face:** how far the metal stands beyond the frozen skin's outer face (the cover's
  top, the motor side's bottom): where the end wall wants to be thicker, a bridge or a drum, or
  ribs;
- **outside the walls:** columns with metal but no skin, in plan, with how much metal they hold:
  belts, gussets, struts to the mounts.
Drawn as maps in plan over the gears' rooms, the bearings and the mounts, and summarised in
numbers.

Run: uv run python prototypes/first_loop/topo_read.py <run stem>
     (e.g. topofree_misalignment_7.73kg_6mm_projected; writes data/first_loop/<stem>_read.png and
     _read.json)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from topo import OUT  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402

PLACED = 0.5


def read(stem: str) -> dict:
    import topo

    z = np.load(OUT / f"{stem}.npz")
    run = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    info = json.loads((OUT / f"{run.get('layout', 'grammar4')}.json").read_text(encoding="utf-8"))
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    k_split = int(z["k_split"]) if "k_split" in z else int(round((info["z"]["split"] - lo[2]) / h))
    total = int(np.prod(n))
    frozen = np.zeros(total, bool)
    frozen[z["elem"][z["frozen"].astype(bool)]] = True
    metal = frozen.copy()
    metal[z["elem"][z["free_e"][z["phys"] > PLACED]]] = True
    frozen, metal = frozen.reshape(n), metal.reshape(n)
    k = np.arange(n[2])[None, None, :]

    def extent(mask, half, outward):
        """Per column: the outermost voxel index of `mask` in the half, or -1."""
        sel = mask & ((k >= k_split) if half == "cover" else (k < k_split))
        if outward > 0:
            idx = np.where(sel, k, -1).max(axis=2)
        else:
            idx = np.where(sel, k, n[2]).min(axis=2)
            idx = np.where(idx == n[2], -1, idx)
        return idx

    maps = {}
    for half, outward in (("cover", 1), ("motor_side", -1)):
        top_m, top_f = extent(metal, half, outward), extent(frozen, half, outward)
        beyond = np.where((top_m >= 0) & (top_f >= 0), (top_m - top_f) * outward, 0) * h  # mm past the skin's face
        sel = (k >= k_split) if half == "cover" else (k < k_split)
        outside = np.where(~(frozen & sel).any(axis=2), (metal & sel).sum(axis=2) * h, 0.0)  # mm of metal in columns with no skin
        # where the metal ends, outward, in the model's own z (the outer face of its last voxel)
        reach = np.where(top_m >= 0, lo[2] + h * (top_m + (1 if outward > 0 else 0)), np.nan)
        skin = (frozen & sel).any(axis=2)  # the columns the model's skin covers, in plan
        maps[half] = {"beyond": beyond, "outside": outside, "reach": reach, "skin": skin}

    spec, _ = load_and_validate(topo.CONTRACT)
    chain = complete_chain(spec)
    xs = lo[0] + h * (np.arange(n[0]) + 0.5)
    ys = lo[1] + h * (np.arange(n[1]) + 0.5)
    # the maps themselves, for grammar.py to lay its ribs on (indexed [x, y])
    np.savez_compressed(OUT / f"{stem}_plan.npz", xs=xs, ys=ys, h=h, **{f"{half}_{key}": m[key] for half, m in maps.items() for key in m})
    summary = {}
    for half, m in maps.items():
        b, o = m["beyond"], m["outside"]
        summary[half] = {
            "end face: columns thickened": int((b > 0).sum()),
            "end face: most, mm": float(b.max()),
            "end face: mean where thickened, mm": round(float(b[b > 0].mean()), 1) if (b > 0).any() else 0.0,
            "outside the walls: columns with metal": int((o > 0).sum()),
        }
    sides = {"cover": "+z", "motor_side": "-z"}
    lines = {half: rib_lines(maps[half]["beyond"], xs, ys, h, [b for b in info["bearings"] if b["side"] == sides[half]]) for half in maps}
    for half in lines:
        summary[half]["rib lines"] = len(lines[half])
    picture(stem, maps, xs, ys, chain, info, h, lines)
    recipe, reasons = read_recipe(stem, maps, xs, ys, info, lines)
    out = {"stem": stem, "summary": summary, "ribs": lines, "recipe": recipe, "reasons": reasons}
    (OUT / f"{stem}_read.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return out


def rib_lines(beyond: np.ndarray, xs: np.ndarray, ys: np.ndarray, h: float, bearings=(), shortest: float = 4.0) -> list[dict]:
    """The field's ridges on an end face as rib lines.

    The metal beyond the skin, in plan, thinned to its skeleton. The skeleton's junctions are its
    pixels with other than two neighbours, and touching junction pixels are one junction (skeletons
    form small clusters where lines meet: counted apart, the lines that met there seemed to end
    nowhere, 23:53). Lines are traced between junctions, and closed loops on their own (a ring round
    a bearing often has no junction). Spurs shorter than `shortest` voxels are pruned. At each
    junction the two lines that run on most nearly straight (within 30°) are joined; a line left
    over there ends on the longest line at that junction (a T). A line lying round a bearing at an
    even radius (within 12 %) over at least 90° is a ring round that bearing: the generator draws it
    closed, as a casting would. Each line is simplified within a voxel, smoothed, and given the
    field's mean height along it."""
    from scipy.ndimage import label
    from skimage.morphology import skeletonize

    skel = skeletonize(beyond > 0)
    pts = set(zip(*np.nonzero(skel), strict=True))

    def nbrs(p):
        i, j = p
        return [(i + di, j + dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di or dj) and (i + di, j + dj) in pts]

    node_px = {p for p in pts if len(nbrs(p)) != 2}
    grid = np.zeros(skel.shape, bool)
    for p in node_px:
        grid[p] = True
    lab, _ = label(grid, structure=np.ones((3, 3), bool))
    junction = {p: int(lab[p]) for p in node_px}
    seen, chains = set(), []  # chains: [pixels], closed?
    for a in node_px:
        for b in nbrs(a):
            if b in node_px or (a, b) in seen:
                continue
            path, prev, cur = [a], a, b
            while True:
                seen.add((prev, cur))
                seen.add((cur, prev))
                path.append(cur)
                if cur in node_px:
                    break
                nxt = [q for q in nbrs(cur) if q != prev and (cur, q) not in seen]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
            chains.append((path, False))
    visited = {p for path, _ in chains for p in path}
    for p in pts - visited:  # closed loops, no junction on them
        if p in visited:
            continue
        loop, prev, cur = [p], None, p
        while True:
            nxt = [q for q in nbrs(cur) if q != prev and q not in loop[1:]]
            visited.add(cur)
            if not nxt or (len(loop) > 2 and loop[0] in nbrs(cur) and prev is not None and all(q in loop for q in nbrs(cur))):
                break
            prev, cur = cur, nxt[0]
            if cur == loop[0]:
                break
            loop.append(cur)
        if len(loop) >= shortest:
            chains.append((loop + [loop[0]], True))

    def end_junction(path, end):
        p = path[0] if end == 0 else path[-1]
        return junction.get(p)

    # prune: stubs between junctions shorter than `shortest`, and short spurs
    kept = []
    for path, closed in chains:
        if closed:
            kept.append([path, True])
            continue
        j0, j1 = end_junction(path, 0), end_junction(path, 1)
        degree = {j: sum(1 for pth, cl in chains if not cl for e in (0, 1) if end_junction(pth, e) == j) for j in (j0, j1)}
        free = [j for j in (j0, j1) if degree.get(j, 0) <= 1]
        if len(path) < shortest and (len(free) == 0 or len(free) == 1):
            continue
        kept.append([path, False])
    chains = kept

    def direction(path, end):
        a, b = (path[0], path[min(3, len(path) - 1)]) if end == 0 else (path[-1], path[max(-4, -len(path))])
        v = np.array(b, float) - np.array(a, float)
        return v / max(np.linalg.norm(v), 1e-9)

    joined = True
    while joined:
        joined = False
        ends = {}
        for ci, (path, closed) in enumerate(chains):
            if closed:
                continue
            for end in (0, 1):
                j = end_junction(path, end)
                if j is not None:
                    ends.setdefault(j, []).append((ci, end))
        for j, members in ends.items():
            best = None
            for x_ in range(len(members)):
                for y_ in range(x_ + 1, len(members)):
                    (ca, ea), (cb, eb) = members[x_], members[y_]
                    if ca == cb:
                        continue
                    straight = -float(direction(chains[ca][0], ea) @ direction(chains[cb][0], eb))
                    if straight > math.cos(math.radians(30)) and (best is None or straight > best[0]):
                        best = (straight, ca, ea, cb, eb)
            if best:
                _, ca, ea, cb, eb = best
                a = chains[ca][0] if ea == 1 else chains[ca][0][::-1]
                b = chains[cb][0] if eb == 0 else chains[cb][0][::-1]
                chains[ca][0] = a + b
                del chains[cb]
                joined = True
                break
    # T ends: a line's end at a junction other lines reach ends on the longest of them
    through = {}
    for ci, (path, closed) in enumerate(chains):
        for p in path:
            j = junction.get(p)
            if j is not None:
                through.setdefault(j, set()).add(ci)
    tees = {}
    for ci, (path, closed) in enumerate(chains):
        if closed:
            continue
        for end in (0, 1):
            j = end_junction(path, end)
            others = [c for c in through.get(j, ()) if c != ci]
            if others:
                tees[(ci, end)] = max(others, key=lambda c: len(chains[c][0]))
    out = []
    for ci, (path, closed) in enumerate(chains):
        xy = np.array([[xs[i], ys[j]] for i, j in path], float)
        heights = [beyond[i, j] for i, j in path]
        line = {"points": None, "height": round(float(np.mean(heights)), 1),
                "length": round(float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()), 1),
                "tees": {str(end): other for (c, end), other in tees.items() if c == ci}, "closed": closed}  # fmt: skip
        for bi, b in enumerate(bearings):
            r = np.hypot(xy[:, 0] - b["axis"][0], xy[:, 1] - b["axis"][1])
            ang = np.unwrap(np.arctan2(xy[:, 1] - b["axis"][1], xy[:, 0] - b["axis"][0]))
            span = math.degrees(float(ang.max() - ang.min()))
            if r.mean() > b["D"] / 2 and r.std() < 0.12 * r.mean() and span >= 90.0 and r.mean() < b["D"] + 40.0:
                line["ring"] = {"bearing": bi, "shaft": b["shaft"], "radius": round(float(r.mean()), 1), "span_deg": round(span)}
                break
        keep = xy if closed else _smooth(_simplify(xy, h), 2)
        line["points"] = [[round(float(x), 1), round(float(y), 1)] for x, y in keep]
        out.append(line)
    return out


def read_recipe(stem: str, maps: dict, xs: np.ndarray, ys: np.ndarray, info: dict, lines: dict) -> tuple[dict, dict]:
    """The field read as the generator's recipe: the housing's form as well as its ribs, every
    choice with the measure that made it (the engineer, 23:41: the housing starts only from what
    the shafts, bearings and gears fix; the first reading borrowed a style's body and lost the
    field's pattern). The tool proposes; each reason says why, so the agent can overrule it."""
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    s = info["settings"]
    reasons = {}
    bear = {(b["shaft"], b["side"]): b for b in info["bearings"]}

    def ring_mean(beyond, axis, r0, r1):
        r = np.hypot(X - axis[0], Y - axis[1])
        sel = (r >= r0) & (r <= r1)
        return float(beyond[sel].mean()) if sel.any() else 0.0

    # the cover: towers if the field rings each bearing, a bridge if it fills the corridor between
    cover = maps["cover"]["beyond"]
    bi, bo = bear[("intermediate", "+z")], bear[("output", "+z")]
    rings = [ring_mean(cover, b["axis"], b["boss_r"] - 10.0, b["boss_r"] + 15.0) for b in (bi, bo)]
    a, b_ = np.asarray(bi["axis"], float), np.asarray(bo["axis"], float)
    d = (b_ - a) / np.linalg.norm(b_ - a)
    t = np.clip((X - a[0]) * d[0] + (Y - a[1]) * d[1], 0.0, np.linalg.norm(b_ - a))
    off = np.hypot(X - (a[0] + t * d[0]), Y - (a[1] + t * d[1]))
    corridor = (off <= min(bi["boss_r"], bo["boss_r"])) & (np.hypot(X - a[0], Y - a[1]) > bi["boss_r"]) & (np.hypot(X - b_[0], Y - b_[1]) > bo["boss_r"])
    corridor_mean = float(cover[corridor].mean()) if corridor.any() else 0.0
    cover_form = "bridge" if corridor_mean >= 0.6 * max(np.mean(rings), 1e-9) else "towers"
    reasons["cover"] = (f"{cover_form}: the field stands {corridor_mean:.0f} mm proud in the corridor between the intermediate's and the "
                        f"output's bearings, against {rings[0]:.0f} and {rings[1]:.0f} mm in rings round each (a bridge from 60 % of the rings)")  # fmt: skip
    # the motor side: a drum per deeper shaft, as the skin's end walls stand at each gear room's depth
    reasons["levels"] = "drums: the optimiser's skin closes each gear room at its own depth, so each bearing's wall stands at its own level"
    reasons["outline"] = "lobed, blend 30: the skin hugs each gear room, with waists between them"
    # the wheel inside the motor's ring: only if the field put metal inside the ring
    motor = maps["motor_side"]["beyond"]
    inp = bear[("input", "-z")]["axis"]
    hole = np.hypot(X - inp[0], Y - inp[1]) < s["motor_ring"][0] / 2
    share = float((motor[hole] > 0).mean()) if hole.any() else 0.0
    wheel = {"spokes": 8, "ring": False} if share > 0.25 else {"spokes": 0, "ring": False}
    reasons["wheel"] = f"{'spokes' if wheel['spokes'] else 'none'}: the field fills {100 * share:.0f} % of the motor ring's bore (spokes from 25 %)"
    # ears: where the field struts out to a mount
    struts = []
    for m in info["mounts"]:
        near = np.hypot(X - m["centre"][0], Y - m["centre"][1]) < 40.0
        struts.append(int((maps["motor_side"]["outside"][near] > 0).sum() + (maps["cover"]["outside"][near] > 0).sum()))
    ears = sum(c >= 3 for c in struts) >= 2
    reasons["ears"] = f"{ears}: the field's metal outside the walls within 40 mm of the mounts, per mount: {struts} columns (ears where two or more reach)"
    heights = [ln["height"] for ln in lines["cover"] + lines["motor_side"] if ln["length"] > 30.0]
    rib_height = float(np.clip(np.median(heights) if heights else 20.0, 12.0, 26.0))
    reasons["rib_height"] = f"{rib_height:.0f} mm: the median height of the field's longer lines, held to 12-26 mm"
    recipe = {
        "outline": {"family": "lobed", "blend": 30.0}, "levels": "drums", "cover": cover_form,
        "spokes": "none", "delta": False, "ears": ears, "wheel": wheel, "rim": False, "motor_ring": "plain",
        "pattern": {"kind": "field", "run": stem},
        "settings": {"rib_height": round(rib_height, 1), "rib": 6.0},
    }  # fmt: skip
    return recipe, reasons


def _smooth(xy: np.ndarray, rounds: int) -> np.ndarray:
    """Chaikin's corner cutting, its ends kept: a simplified line's kinks taken off."""
    for _ in range(rounds):
        if len(xy) < 3:
            return xy
        q = 0.75 * xy[:-1] + 0.25 * xy[1:]
        r = 0.25 * xy[:-1] + 0.75 * xy[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2], mid[1::2] = q, r
        xy = np.vstack([xy[:1], mid[1:-1], xy[-1:]])
    return xy


def _simplify(xy: np.ndarray, tol: float) -> np.ndarray:
    """Douglas-Peucker within `tol`."""
    if len(xy) < 3:
        return xy
    a, b = xy[0], xy[-1]
    ab = b - a
    norm = max(float(np.linalg.norm(ab)), 1e-9)
    d = np.abs(ab[0] * (xy[:, 1] - a[1]) - ab[1] * (xy[:, 0] - a[0])) / norm
    k = int(np.argmax(d))
    if d[k] <= tol:
        return np.array([a, b])
    return np.vstack([_simplify(xy[: k + 1], tol)[:-1], _simplify(xy[k:], tol)])


def picture(stem, maps, xs, ys, chain, info, h, lines=None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    fig, axes = plt.subplots(2, 2, figsize=(14, 13))
    extent = (xs[0] - h / 2, xs[-1] + h / 2, ys[0] - h / 2, ys[-1] + h / 2)
    titles = {
        ("cover", "beyond"): "Cover: metal beyond the skin's top face (mm)",
        ("motor_side", "beyond"): "Motor side: metal beyond the skin's bottom face (mm)",
        ("cover", "outside"): "Cover: metal outside the walls, per column (mm along the shafts)",
        ("motor_side", "outside"): "Motor side: metal outside the walls, per column (mm)",
    }
    for row, kind in enumerate(("beyond", "outside")):
        for col, half in enumerate(("cover", "motor_side")):
            ax = axes[row][col]
            data = np.ma.masked_where(maps[half][kind] <= 0, maps[half][kind]).T
            im = ax.imshow(data, origin="lower", extent=extent, cmap="viridis", interpolation="nearest")
            fig.colorbar(im, ax=ax, shrink=0.8)
            for st in chain.layout.shafts:
                for p in st.parts:
                    if p.kind in ("gear", "carrier"):
                        ax.add_patch(Circle(st.axis, p.diameter / 2, fill=False, ec="#d08a2a", lw=1.0))
                ax.plot(*st.axis, "k+", ms=10)
            for b in info["bearings"]:
                ax.add_patch(Circle(b["axis"], b["D"] / 2, fill=False, ec="#2a6fd0", lw=1.0, ls="--"))
            for m in info["mounts"]:
                ax.plot(*m["centre"], "rs", ms=8)
            if lines and kind == "beyond":
                for r in lines[half]:
                    p = np.asarray(r["points"])
                    ax.plot(p[:, 0], p[:, 1], "-", color="#e8402a", lw=1.6)
            ax.set_title(titles[(half, kind)] + (" · rib lines red" if lines and kind == "beyond" else ""), fontsize=10)
            ax.set_aspect("equal")
            ax.set_xlabel("x, mm")
            ax.set_ylabel("y, mm")
    fig.suptitle(f"{stem}: the field read in plan (gears orange, bearings blue dashed, mounts red)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / f"{stem}_read.png", dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    read(sys.argv[1] if len(sys.argv) > 1 else "topofree_misalignment_7.73kg_6mm_projected")
