"""The optimiser's layout built as clean ribs (LOP-23, 11 October 15:30; the engineer, 15:16-15:24: "why
are the ribs broken"; "see how bad a design we got"). The optimiser decides where the load paths
run; this decides how each one is built.

Each half's members are read from the run's field as a plan map of their height off the shell. The
casting filter makes the field a height map over its plan (`interval_census.py`). That map is read
as a network of lines:
- tiny islands (under ISLAND mm²) are dropped;
- the members' centre-lines are found (the skeleton, free ends under SPUR mm pruned);
- the lines are cut at their junctions into edges, each smoothed into a fair curve (a smoothing
  spline) and joined back to its junctions;
- short free ends (under SHORT mm) and edges lower than LOW mm are dropped.

Each edge is built as one rib:
- one width, the nearest of WIDTHS to its members' own;
- one height, its members' median;
- a fully rounded top and rounded ends.

The ribs meet at the junctions as they stand. `members_field` puts them on the mesh route's 2 mm
grid, each column's metal from the split out to the rib's top, where the root fillets, kept-clear
spaces, exact shell and cuts apply as for any drawing (`outcome_cad.build_mesh` with
LOOP_CLEAN_MEMBERS=ribs). FE judges it.

Run alone, it pictures a run's members and its ribs in plan: `clean_ribs.py <run> [label]`."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
FINE_PLAN = 1.0  # mm, the plan grid
ISLAND = 300.0  # mm², the smallest member kept
SPUR = 8.0  # mm, the shortest free end of a centre-line kept by the pruning
SHORT = 14.0  # mm, the shortest free-ended edge kept as a rib
LOW = 3.0  # mm, the lowest rib kept
WIDTHS = (6.0, 8.0, 10.0, 12.0, 16.0)  # mm, the ribs' widths (the broad ones round a boss or a bore)
SMOOTH = 1.6  # mm, the smoothing spline's mean deviation from the centre-line
ATTACH = 5.0  # mm: an edge's end within this of a junction joins it
SNAP = 10.0  # mm: a free end within this of another rib is carried on to it in a straight line


def field_plan(run: str) -> dict:
    z = np.load(OUT / f"{run}.npz")
    n = z["n"].astype(int)
    placed = np.zeros(int(np.prod(n)), bool)
    frozen = np.zeros(int(np.prod(n)), bool)
    placed[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    frozen[z["elem"][z["frozen"].astype(bool)]] = True
    return {"h": float(z["h"]), "n": n, "ks": int(z["k_split"]), "lo": z["lo"].astype(float),
            "placed": placed.reshape(tuple(n)), "frozen": frozen.reshape(tuple(n))}  # fmt: skip


def heights(fp: dict, half: str) -> np.ndarray:
    """Each column's members' height off the fixed metal under them, mm: from the depth of the
    outermost placed voxel from the split, less that of the outermost fixed one (so a mount's arm,
    whose run starts under the split, is measured from the split, as it is drawn)."""
    h, ks, n = fp["h"], fp["ks"], fp["n"]
    if half == "motor_side":
        pl, fr = fp["placed"][:, :, :ks], fp["frozen"][:, :, :ks]
        kk = np.arange(ks)[None, None, :]

        def depth(m):
            low = np.where(m, kk, ks).min(axis=2)
            return np.where(low < ks, ks - low, 0)
    else:
        pl, fr = fp["placed"][:, :, ks:], fp["frozen"][:, :, ks:]
        kk = np.arange(ks, n[2])[None, None, :]

        def depth(m):
            high = np.where(m, kk, -1).max(axis=2)
            return np.where(high >= 0, high - ks + 1, 0)

    d_p, d_f = depth(pl), depth(fr)
    return np.where(d_p > 0, np.maximum(d_p - d_f, 0), 0) * h


def _prune(skel: np.ndarray, length: float) -> np.ndarray:
    skel = skel.copy()
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    kernel = np.ones((3, 3), int)
    kernel[1, 1] = 0
    for _ in range(3):
        deg = ndi.convolve(skel.astype(int), kernel, mode="constant") * skel
        for e in np.argwhere(deg == 1):
            path, cur = [tuple(e)], tuple(e)
            while len(path) <= length:
                nxt = [(cur[0] + a, cur[1] + b) for a, b in nb
                       if 0 <= cur[0] + a < skel.shape[0] and 0 <= cur[1] + b < skel.shape[1]
                       and skel[cur[0] + a, cur[1] + b] and (cur[0] + a, cur[1] + b) not in path]  # fmt: skip
                if len(nxt) != 1 or deg[nxt[0]] >= 3:
                    break
                cur = nxt[0]
                path.append(cur)
            if len(path) <= length:
                for q in path:
                    skel[q] = False
    return skel


def _order(pix: np.ndarray) -> np.ndarray:
    """A chain of 8-connected pixels in order from one end (or anywhere on a loop)."""
    s = {tuple(p) for p in pix}

    def nbrs(p):
        return [(p[0] + a, p[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (p[0] + a, p[1] + b) in s]

    ends = [p for p in s if len(nbrs(p)) <= 1]
    cur = min(ends) if ends else min(s)
    out, seen = [cur], {cur}
    while True:
        nxt = [q for q in nbrs(cur) if q not in seen]
        if not nxt:
            break
        nxt.sort(key=lambda q: abs(q[0] - cur[0]) + abs(q[1] - cur[1]))  # a side neighbour before a corner one
        cur = nxt[0]
        out.append(cur)
        seen.add(cur)
    return np.asarray(out, float)


def _fair(pts: np.ndarray, closed: bool) -> np.ndarray:
    """A smoothing spline through the chain, sampled every FINE_PLAN: its ends held."""
    from scipy.interpolate import splev, splprep

    if len(pts) < 5:
        return pts
    w = np.ones(len(pts))
    if not closed:
        w[0] = w[-1] = 50.0
    try:
        tck, _ = splprep([pts[:, 0], pts[:, 1]], w=w, s=len(pts) * (SMOOTH / FINE_PLAN) ** 2, k=3, per=1 if closed else 0)
    except (ValueError, TypeError):
        return pts
    length = float(np.hypot(*np.diff(pts, axis=0).T).sum())
    u = np.linspace(0.0, 1.0, max(int(length / FINE_PLAN) + 2, 3))
    x, y = splev(u, tck)
    return np.column_stack([x, y])


def network(m4: np.ndarray, h: float) -> tuple[list[dict], np.ndarray, dict]:
    """A half's members (mm high, on the field's h grid) as ribs: each a fair curve (plan cells of
    FINE_PLAN), a width and a height; with the cleaned mask and a summary."""
    from skimage.morphology import skeletonize

    s = int(round(h / FINE_PLAN))
    present = m4 >= 0.5 * h
    mask = ndi.zoom(ndi.gaussian_filter(present.astype(float), 0.7), s, order=1) >= 0.5
    m1 = np.kron(m4, np.ones((s, s)))[: mask.shape[0], : mask.shape[1]]
    lab, k = ndi.label(mask)
    areas = ndi.sum(mask, lab, index=np.arange(1, k + 1)) * FINE_PLAN**2 if k else np.zeros(0)
    mask = np.r_[False, areas >= ISLAND][lab]
    dt = ndi.distance_transform_edt(mask) * FINE_PLAN
    skel = _prune(skeletonize(mask), SPUR / FINE_PLAN)
    kernel = np.ones((3, 3), int)
    kernel[1, 1] = 0
    deg = ndi.convolve(skel.astype(int), kernel, mode="constant") * skel
    junction = ndi.binary_dilation(skel & (deg >= 3), structure=np.ones((3, 3))) & skel
    jlab, nj = ndi.label(junction, structure=np.ones((3, 3)))
    centres = np.asarray(ndi.center_of_mass(junction, jlab, range(1, nj + 1))) if nj else np.zeros((0, 2))
    elab, ne = ndi.label(skel & ~junction, structure=np.ones((3, 3)))
    tall = ndi.maximum_filter(m1, size=3)
    ribs, dropped = [], 0
    for e in range(1, ne + 1):
        pix = np.argwhere(elab == e)
        chain = _order(pix)
        ends_free = []
        pts = [chain]
        for end, where in ((chain[0], 0), (chain[-1], -1)):
            if len(centres):
                d = np.hypot(*(centres - end).T)
                j = int(np.argmin(d))
                if d[j] <= ATTACH / FINE_PLAN:
                    pts.insert(0 if where == 0 else len(pts), centres[j][None, :])
                    continue
            ends_free.append(where)
        chain_j = np.vstack(pts)
        closed = len(chain) > 8 and np.hypot(*(chain[0] - chain[-1])) <= 1.5 and not len(ends_free) < 2
        length = float(np.hypot(*np.diff(chain_j, axis=0).T).sum()) * FINE_PLAN
        ii, jj = pix[:, 0], pix[:, 1]
        height = float(np.median(tall[ii, jj]))
        width = float(np.median(2.0 * dt[ii, jj]))
        if height < LOW or (ends_free and length < SHORT):
            dropped += 1
            continue
        wc = float(min(WIDTHS, key=lambda w: abs(w - width)))
        ribs.append({"curve": _fair(chain_j, closed), "width": wc, "height": height, "length_mm": length,
                     "free": [w for w in ends_free] if not closed else []})  # fmt: skip
    snapped = _snap(ribs)
    summary = {"ribs": len(ribs), "dropped": dropped, "ends_snapped": snapped, "length_mm": float(sum(r["length_mm"] for r in ribs)),
               "widths": {f"{w:g}": sum(1 for r in ribs if r["width"] == w) for w in WIDTHS}}  # fmt: skip
    return ribs, mask, summary


def _snap(ribs: list[dict]) -> int:
    """Each rib's free end within SNAP of another rib carried on to its nearest point in a
    straight line, so ribs meet rather than stop short of each other. Returns how many."""
    from scipy.spatial import cKDTree

    if len(ribs) < 2:
        return 0
    pts = np.vstack([r["curve"] for r in ribs])
    owner = np.concatenate([np.full(len(r["curve"]), i) for i, r in enumerate(ribs)])
    tree = cKDTree(pts)
    count = 0
    for i, r in enumerate(ribs):
        for where in r["free"]:
            end = r["curve"][where]
            near = [k for k in tree.query_ball_point(end, SNAP / FINE_PLAN) if owner[k] != i]
            if not near:
                continue
            k = min(near, key=lambda q: float(np.hypot(*(pts[q] - end))))
            step = pts[k] - end
            n = max(int(np.hypot(*step) / FINE_PLAN), 1)
            line = end + step * (np.arange(1, n + 1)[:, None] / n)
            r["curve"] = np.vstack([line[::-1], r["curve"]]) if where == 0 else np.vstack([r["curve"], line])
            count += 1
    return count


def render(ribs: list[dict], shape: tuple) -> np.ndarray:
    """The ribs' height map on the plan grid: each a stroke of its width along its curve, its top
    fully rounded (a semicircle across), its ends rounded; where ribs meet, the taller stands."""
    from scipy.spatial import cKDTree

    out = np.zeros(shape)
    for r in ribs:
        c, half = r["curve"], r["width"] / 2.0 / FINE_PLAN
        lo = np.maximum(np.floor(c.min(axis=0) - half - 1).astype(int), 0)
        hi = np.minimum(np.ceil(c.max(axis=0) + half + 1).astype(int), np.asarray(shape) - 1)
        if np.any(hi < lo):
            continue
        gi, gj = np.mgrid[lo[0] : hi[0] + 1, lo[1] : hi[1] + 1]
        pts = np.column_stack([gi.ravel(), gj.ravel()]).astype(float)
        # dense samples of the curve (every half cell) for the distance to it
        seg = np.diff(c, axis=0)
        n_sub = np.maximum(np.ceil(np.hypot(*seg.T) / 0.5).astype(int), 1)
        dense = np.vstack([c[:-1][i] + seg[i] * (np.arange(n_sub[i])[:, None] / n_sub[i]) for i in range(len(seg))] + [c[-1:]]) if len(c) > 1 else c
        d, _ = cKDTree(dense).query(pts)
        inside = d <= half
        top = r["height"] - (half - np.sqrt(np.maximum(half * half - d * d, 0.0))) * FINE_PLAN
        z = np.where(inside, top, 0.0).reshape(gi.shape)
        out[lo[0] : hi[0] + 1, lo[1] : hi[1] + 1] = np.maximum(out[lo[0] : hi[0] + 1, lo[1] : hi[1] + 1], z)
    return out


SEAT_ZONE = 25.0  # mm past each bearing's bore: the field's own metal kept there, smoothed (a boss), not read as ribs
SEAT_BLUR = 2.0  # mm, the smoothing of a seat zone's metal


def seat_zones(fp: dict, half: str, shape: tuple) -> np.ndarray:
    """The plan cells within SEAT_ZONE of each of the half's bearings' bores (the layout's)."""
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    side = "-z" if half == "motor_side" else "+z"
    x = fp["lo"][0] + FINE_PLAN * (np.arange(shape[0]) + 0.5)
    y = fp["lo"][1] + FINE_PLAN * (np.arange(shape[1]) + 0.5)
    X, Y = np.meshgrid(x, y, indexing="ij")
    zone = np.zeros(shape, bool)
    for b in layout["bearings"]:
        if b["side"] == side:
            zone |= np.hypot(X - b["axis"][0], Y - b["axis"][1]) <= b["D"] / 2.0 + SEAT_ZONE
    return zone


def clean_plan(m4: np.ndarray, h: float, zone: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
    """The clean heights: the ribs, and within the seat zones (`zone`, plan cells of FINE_PLAN)
    the field's own members smoothed, as the bosses the seats need (the cover's output seat lost
    70 % of its metal as ribs, and the beds doubled: 42.4 -> 84.5 µm, 11 October 15:30)."""
    ribs, mask, summary = network(m4, h)
    plan = render(ribs, mask.shape)
    if zone is not None:
        s = int(round(h / FINE_PLAN))
        m1 = np.kron(m4, np.ones((s, s)))[: mask.shape[0], : mask.shape[1]]
        soft = ndi.gaussian_filter((m1 > 0).astype(float), SEAT_BLUR / FINE_PLAN) >= 0.5
        num = ndi.gaussian_filter(np.where(m1 > 0, m1, 0.0), SEAT_BLUR / FINE_PLAN)
        den = ndi.gaussian_filter((m1 > 0).astype(float), SEAT_BLUR / FINE_PLAN)
        boss = np.where(soft & zone[: mask.shape[0], : mask.shape[1]], num / np.maximum(den, 1e-9), 0.0)
        plan = np.maximum(plan, boss)
        summary["seat_zone_cm3"] = float(boss.sum() * FINE_PLAN**2 / 1000.0)
    summary["volume_cm3_before"] = float(m4.sum() * h * h / 1000.0)
    summary["volume_cm3_after"] = float(plan.sum() * FINE_PLAN**2 / 1000.0)
    return plan, summary


def members_field(run: str, p: dict, half: str, bury: float, fine: float) -> tuple[np.ndarray, dict]:
    """The ribs on the mesh route's grid (`outcome_cad.skin_parts`'s `p`): each column's metal from
    the split out to its rib's top, the top the exact shell's outer face plus the rib's height."""
    fp = field_plan(run)
    m4 = heights(fp, half)
    s4 = int(round(fp["h"] / FINE_PLAN))
    clean, stats = clean_plan(m4, fp["h"], seat_zones(fp, half, (m4.shape[0] * s4, m4.shape[1] * s4)))
    s = int(round(fine / FINE_PLAN))
    n_f = p["n_f"]
    grid = np.zeros((n_f[0] * s, n_f[1] * s))
    a, b = min(grid.shape[0], clean.shape[0]), min(grid.shape[1], clean.shape[1])
    grid[:a, :b] = clean[:a, :b]
    m_f = grid.reshape(n_f[0], s, n_f[1], s).max(axis=(1, 3))
    fixed, ks = p["fixed"], p["ks"]
    kk = np.arange(n_f[2])[None, None, :]
    if half == "motor_side":
        lowest = np.where(fixed, kk, n_f[2]).min(axis=2)
        d_fixed = np.where(lowest < n_f[2], ks - lowest, 0)
    else:
        highest = np.where(fixed, kk, -1).max(axis=2)
        d_fixed = np.where(highest >= 0, highest - ks + 1, 0)
    under = np.where(d_fixed > 0, int(round(bury / fine)), 0)
    top = np.where(m_f > 0.0, d_fixed + under + np.rint(m_f / fine), 0).astype(int)
    if half == "motor_side":
        members = (kk >= ks - top[..., None]) & (kk < ks)
    else:
        members = (kk >= ks) & (kk < ks + top[..., None])
    return members.astype(np.float32), stats


def picture(run: str, label: str) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fp = field_plan(run)
    fig, axes = plt.subplots(2, 2, figsize=(12, 11), dpi=120)
    summary = {}
    for row, half in enumerate(("motor_side", "cover")):
        m4 = heights(fp, half)
        s4 = int(round(fp["h"] / FINE_PLAN))
        clean, stats = clean_plan(m4, fp["h"], seat_zones(fp, half, (m4.shape[0] * s4, m4.shape[1] * s4)))
        summary[half] = stats
        for col, (img, title) in enumerate(((m4, "as optimised (4 mm voxels)"), (clean, f"as ribs ({stats['ribs']} ribs, 1 mm)"))):
            ax = axes[row, col]
            ax.imshow(np.where(img > 0, img, np.nan).T, origin="lower", cmap="viridis", vmin=0, vmax=28, interpolation="nearest")
            ax.set_title(f"{half.replace('_', ' ')}: {title}", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle(f"{label}: the members' height off the shell, as optimised and as ribs", fontsize=12)
    path = OUT / f"clean_ribs_{label}.png"
    fig.savefig(path)
    print(json.dumps(summary, indent=1))
    return path


if __name__ == "__main__":
    print(picture(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "run"))
