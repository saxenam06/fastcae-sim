"""The next iteration's design volume from the hard points (LOP-24; the engineer, 12 October 00:45-01:02:
regions round the bores, wedges between the mounts and the bores or the flange bolts, together covering most
of the free optimisation's metal, so that the spill, which no region holds, is left out; shown as volumes).

The hard points are the contract's, by kind: each cylindrical seat (a bearing's bore, with its boss radius),
each mount's lug, each flange bolt's boss. The candidates are regular solids between them:
- **a boss:** the free voxels over a seat's end wall within its boss radius (a ring on the wall, up to the band);
- **a strip:** the free voxels of a half within half of `--width` of the shortest path along the band (round
  the shell, over its edges) from one hard point's anchor to another's: a strip of one width lying on the
  shell, as a rib does; a "wedge" when one end is a mount's lug. Seat to seat, each mount to its nearest seats
  and bolts, each seat to every bolt within `--reach` of its boss's edge. (A straight hull between a boss on
  the end wall and a bolt at the split cut through the shell's corner, so it held almost nothing, 12 October
  01:10.)

`first <free run>`: each candidate scored by the free run's metal (its voxels at density 0.5 or more); a
selection (an integer program, scipy's HiGHS) keeps every boss and picks the smallest strips (by their voxels)
that, with the bosses, hold at least `--cover` of the free run's metal, and at least one strip at each mount;
the spill is the metal no chosen region holds.

`next <run> <label before>`: each chosen region read by the run's metal and shrunk to it: a strip narrowed to
its metal's own width about its path (the metal's 90th percentile distance from it, plus a voxel, in 4 mm
steps, at least `--least`), a boss to the radius its metal reaches (plus a voxel); a region holding under
`--drop` of its voxels as metal is dropped (a boss never). With `--to <mm>` every strip is narrowed to at most
that width whatever its metal says: the volumes shrunk by rule, step by step (inside a region the least-metal
optimiser spreads its metal to the region's edges, 12 October 01:20, so its metal alone never shrinks it).
Printed: what each region holds and becomes.

Either writes data/first_loop/<label>.npz (mask: the regions' cells; label: each cell's region; lo, n, h),
<label>.json (the candidates, their metal and whether chosen, each region's width and boss radius) and
<label>.png (each half in plan from outside: the regions, the metal they hold, the metal they leave out).
`topo_free.py --space <label>.npz` optimises inside them.

    regions.py first <free run> --label <label> [--width 48] [--cover 0.9] [--seats 2] [--bolts 3] [--reach 120]
    regions.py next <run> <label before> --label <label> [--least 16] [--drop 0.12]"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import topo_free as tf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"


def context(run: str) -> dict:
    """The model a run was made on (rebuilt from its record), its cells and the run's metal."""
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
    space = rec.get("space") or ""
    model = tf.build_free(float(rec["voxel_mm"]), layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin,
                          cavity=rec.get("cavity", "cup"), route=rec.get("route", "split"), flange=bool(rec.get("flange")),
                          mount_reach=rec.get("mount_reach") or "corridor",
                          height_field=(rec.get("height_field") or {}).get("radius_mm"), space=space)  # fmt: skip
    n, lo, h, ks = tuple(int(v) for v in model["n"]), np.asarray(model["lo"], float), float(model["h"]), int(model["k_split"])
    kind = np.asarray(model["kind"])
    z = np.load(OUT / f"{run}.npz")
    if int((kind == 0).sum()) != len(z["free_e"]):
        raise ValueError(f"{run}: the rebuilt model has {(kind == 0).sum():,} free voxels, the run {len(z['free_e']):,}")
    ii, jj, kk = np.unravel_index(np.arange(int(np.prod(n))), n)
    xyz = np.column_stack([lo[0] + h * (ii + 0.5), lo[1] + h * (jj + 0.5), lo[2] + h * (kk + 0.5)])
    phys = np.asarray(z["phys"], float)
    dens = phys if len(phys) == len(z["free_e"]) else phys[z["free_e"]]
    metal = np.zeros(len(kind), bool)
    metal[np.asarray(z["elem"])[np.asarray(z["free_e"])[dens >= 0.5]]] = True
    half_cover = kk >= ks
    return {"model": model, "info": model["info"], "n": n, "lo": lo, "h": h, "ks": ks, "kind": kind, "xyz": xyz, "metal": metal,
            "halves": {"motor_side": ~half_cover, "cover": half_cover}, "half_cover": half_cover, "run": run}  # fmt: skip


def band_graph(allowed: np.ndarray, n: tuple) -> tuple:
    """The face-neighbour graph of the allowed cells (one edge a shared face): (the graph, cell -> node, node -> cell)."""
    cells = np.flatnonzero(allowed)
    node = np.full(allowed.size, -1, np.int64)
    node[cells] = np.arange(len(cells))
    grid = allowed.reshape(n)
    rows, cols = [], []
    for axis in range(3):
        a = np.zeros(n, bool)
        sl_a, sl_b = [slice(None)] * 3, [slice(None)] * 3
        sl_a[axis], sl_b[axis] = slice(0, n[axis] - 1), slice(1, n[axis])
        a[tuple(sl_a)] = grid[tuple(sl_a)] & grid[tuple(sl_b)]
        src = np.flatnonzero(a.ravel())
        step = int(np.prod(n[axis + 1:])) if axis < 2 else 1
        rows.append(node[src])
        cols.append(node[src + step])
    r, c = np.concatenate(rows), np.concatenate(cols)
    g = coo_matrix((np.ones(len(r)), (r, c)), shape=(len(cells), len(cells))).tocsr()
    return (g + g.T).tocsr(), node, cells


def geodesic(graph, node, cells, a: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """The cells of the shortest path along the graph from any of `a`'s cells to the nearest of `b`'s."""
    from scipy.sparse.csgraph import dijkstra

    src = node[np.flatnonzero(a)]
    src = src[src >= 0]
    dst = node[np.flatnonzero(b)]
    dst = dst[dst >= 0]
    if not len(src) or not len(dst):
        return None
    dist, pred, _ = dijkstra(graph, indices=src, min_only=True, return_predecessors=True)
    end = dst[np.argmin(dist[dst])]
    if not np.isfinite(dist[end]):
        return None
    path = [end]
    while pred[path[-1]] >= 0:
        path.append(pred[path[-1]])
    return cells[np.asarray(path)]


def candidates(ctx: dict, width: float, n_seats: int, n_bolts: int, reach_mm: float) -> list[dict]:
    """Every boss and every strip between pairs of hard points (see the module's words), each with its cells,
    and a strip with its path and half (to be narrowed later)."""
    from scipy.ndimage import distance_transform_edt

    info, n, h, kind, xyz, masks, halves = ctx["info"], ctx["n"], ctx["h"], ctx["kind"], ctx["xyz"], ctx["model"]["masks"], ctx["halves"]
    free = kind == 0
    half_cover = ctx["half_cover"]
    points = []
    for b in info["bearings"]:
        name = "cover" if b["side"] == "+z" else "motor_side"
        r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
        boss = free & halves[name] & (r <= float(b["boss_r"]))
        points.append({"name": f"the {b['shaft']} bore ({'cover' if name == 'cover' else 'motor side'})", "kind": "seat", "half": name,
                       "xy": np.asarray(b["axis"], float), "r": float(b["boss_r"]), "seat_r": 0.5 * float(b["D"]), "boss": boss,
                       "anchor": {name: boss}})  # fmt: skip
    mount_d = float(info["settings"].get("mount_diameter", 36.0))
    for m in info["mounts"]:
        r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
        lug = (np.asarray(masks["mounts"], bool) | free) & ~half_cover & (r <= 0.5 * mount_d + h)
        points.append({"name": m["name"], "kind": "lug", "half": "motor_side", "xy": np.asarray(m["centre"], float), "r": 0.5 * mount_d,
                       "anchor": {"motor_side": lug}})  # fmt: skip
    bolt_r = 0.5 * float(info["settings"].get("bolt_boss", 20.0))
    flange = np.asarray(masks["flange"], bool)
    for t_, (bx, by) in enumerate(info["bolts"]):
        r = np.hypot(xyz[:, 0] - bx, xyz[:, 1] - by)
        near = (flange & (r <= bolt_r + h)) | (free & (r <= bolt_r + 2 * h))
        points.append({"name": f"bolt {t_ + 1}", "kind": "bolt", "half": "both", "xy": np.array([bx, by], float), "r": bolt_r,
                       "anchor": {k: near & v for k, v in halves.items()}})  # fmt: skip
    cands = []
    for p in points:
        if p["kind"] == "seat":
            cands.append({"name": f"the boss of {p['name']}", "kind": "boss", "ends": [p["name"]], "cells": p["boss"], "forced": True,
                          "half": p["half"], "xy": p["xy"].tolist(), "boss_r": p["r"], "seat_r": p["seat_r"]})  # fmt: skip
    seats = [p for p in points if p["kind"] == "seat"]
    lugs = [p for p in points if p["kind"] == "lug"]
    bolts = [p for p in points if p["kind"] == "bolt"]
    dist = lambda a, b: float(np.hypot(*(a["xy"] - b["xy"])))  # noqa: E731
    pairs = []
    for i, a in enumerate(seats):
        for b in seats[i + 1:]:
            if a["half"] == b["half"]:
                pairs.append((a, b, a["half"]))
    for m in lugs:
        for s in sorted([s for s in seats if s["half"] == "motor_side"], key=lambda s: dist(m, s))[:n_seats]:
            pairs.append((m, s, "motor_side"))
        for t_ in sorted(bolts, key=lambda t_: dist(m, t_))[:n_bolts]:
            pairs.append((m, t_, "motor_side"))
    for s in seats:
        for t_ in bolts:
            if dist(s, t_) - s["r"] <= reach_mm:
                pairs.append((s, t_, s["half"]))
    graphs = {}
    for name, side in halves.items():
        allowed = free & side
        for p in points:
            if name in p["anchor"]:
                allowed |= p["anchor"][name]
        graphs[name] = band_graph(allowed, n)
    bosses = np.zeros(len(kind), bool)
    for s in seats:
        bosses |= s["boss"]
    for a, b, name in pairs:
        path = geodesic(*graphs[name], a["anchor"][name], b["anchor"][name])
        if path is None:
            continue
        line = np.zeros(n, bool)
        line.flat[path] = True
        dpath = distance_transform_edt(~line, sampling=h).ravel()
        cells = free & halves[name] & (dpath <= 0.5 * width) & ~bosses
        if cells.sum() < 4:
            continue
        cands.append({"name": f"{a['name']} to {b['name']}", "kind": "wedge" if "lug" in (a["kind"], b["kind"]) else "strip",
                      "ends": [a["name"], b["name"]], "cells": cells, "forced": False, "half": name, "path": path, "dpath": dpath,
                      "width": width, "path_mm": round(len(path) * h, 1)})  # fmt: skip
    for c in cands:
        c["size"] = int(c["cells"].sum())
        c["metal"] = int((c["cells"] & ctx["metal"]).sum())
    return cands


def first(run: str, label: str, width: float, cover_share: float, n_seats: int, n_bolts: int, reach_mm: float) -> dict:
    ctx = context(run)
    cands = candidates(ctx, width, n_seats, n_bolts, reach_mm)
    metal, kind = ctx["metal"], ctx["kind"]
    held_any = np.zeros(len(kind), bool)
    for c in cands:
        held_any |= c["cells"]
    m_idx = np.flatnonzero(metal & held_any)
    total = int(metal.sum())
    reach = len(m_idx) / max(total, 1)
    target = min(cover_share, 0.98 * reach) * total
    nc, nm = len(cands), len(m_idx)
    rows, cols, vals = list(range(nm)), list(range(nc, nc + nm)), [1.0] * nm  # y_v - the candidates holding v <= 0
    for ci, c in enumerate(cands):
        hit = np.flatnonzero(c["cells"][m_idx])
        rows += hit.tolist()
        cols += [ci] * len(hit)
        vals += [-1.0] * len(hit)
    a_cov = coo_matrix((vals, (rows, cols)), shape=(nm, nc + nm)).tocsr()
    cons = [LinearConstraint(a_cov, -np.inf, 0.0), LinearConstraint(np.r_[np.zeros(nc), np.ones(nm)][None, :], target, np.inf)]
    for name in sorted({e for c in cands for e in c["ends"] if e.startswith("mount")}):
        row = np.array([1.0 if name in c["ends"] else 0.0 for c in cands] + [0.0] * nm)
        cons.append(LinearConstraint(row[None, :], 1.0, np.inf))
    cost = np.r_[[c["size"] for c in cands], np.zeros(nm)].astype(float)
    lb = np.r_[[1.0 if c["forced"] else 0.0 for c in cands], np.zeros(nm)]
    res = milp(cost, constraints=cons, integrality=np.r_[np.ones(nc), np.zeros(nm)], bounds=Bounds(lb, np.ones(nc + nm)),
               options={"time_limit": 120, "disp": False})  # fmt: skip
    if res.x is None:
        raise RuntimeError(f"the selection found no set: {res.message}")
    chosen = res.x[:nc] > 0.5
    print(f"{len(cands)} candidates ({sum(c['kind'] == 'boss' for c in cands)} bosses, {sum(c['kind'] != 'boss' for c in cands)} strips "
          f"and wedges); together they reach {100 * reach:.0f} % of the free run's metal")  # fmt: skip
    for ci, c in enumerate(cands):
        if chosen[ci]:
            print(f"  * {c['name']:<58} {c['kind']:<6} {c['size']:6,} voxels, {100 * c['metal'] / max(c['size'], 1):3.0f} % metal")
    regions = [dict(c, id=ci) for ci, c in enumerate(cands) if chosen[ci]]
    return write(ctx, label, regions, cands, chosen, {"step": "first", "width_mm": width, "cover": cover_share, "reach": reach})


def refine(run: str, before: str, label: str, least: float, drop: float, width: float, n_seats: int, n_bolts: int, reach_mm: float,
           to: float | None = None) -> dict:  # fmt: skip
    """Each region of `before` read by `run`'s metal and shrunk to it (the module's words)."""
    from scipy.ndimage import distance_transform_edt  # noqa: F401 - the paths' distances are the candidates' own

    prev = json.loads((OUT / f"{before}.json").read_text(encoding="utf-8"))
    ctx = context(run)
    base = context(prev["run"]) if prev.get("run") and prev["run"] != run else ctx
    cands = candidates(base, prev.get("width_mm", width), n_seats, n_bolts, reach_mm)  # the same candidates, the same paths
    by_name = {c["name"]: c for c in cands}
    metal, h, xyz, kind = ctx["metal"], ctx["h"], ctx["xyz"], ctx["kind"]
    free = kind == 0
    regions = []
    for r_ in prev["regions"]:
        c = by_name.get(r_["name"])
        if c is None:
            print(f"  {r_['name']}: not rebuilt, left out")
            continue
        cells = c["cells"].copy()
        if r_["kind"] == "boss":
            rr = np.hypot(xyz[:, 0] - c["xy"][0], xyz[:, 1] - c["xy"][1])
            cur = r_.get("boss_r", c["boss_r"])
            cells = free & ctx["halves"][c["half"]] & (rr <= cur)
            held = cells & metal
            reach = float(np.quantile(rr[held], 0.9)) if held.sum() >= 5 else c["seat_r"] + 2 * h
            new_r = min(cur, max(c["seat_r"] + 2 * h, reach + h))
            new = free & ctx["halves"][c["half"]] & (rr <= new_r)
            note = f"its metal reaches {reach:.0f} mm: the boss radius {cur:.1f} → {new_r:.1f} mm"
            regions.append(dict(c, id=c.get("id", 0), cells=new, boss_r=new_r))
        else:
            cur_w = r_.get("width", c["width"])
            cells = free & ctx["halves"][c["half"]] & (c["dpath"] <= 0.5 * cur_w)
            held = cells & metal
            fill = held.sum() / max(cells.sum(), 1)
            if fill < drop:
                print(f"  {r_['name']:<58} {100 * fill:3.0f} % metal: dropped")
                continue
            d90 = float(np.quantile(c["dpath"][held], 0.9)) if held.sum() >= 5 else 0.5 * least
            new_w = min(cur_w, max(least, 4.0 * math.ceil(2.0 * (d90 + h) / 4.0)))
            if to:  # shrunk by rule, step by step (the engineer, 00:45: "then shrink volumes gradually")
                new_w = max(least, min(new_w, to))
            new = free & ctx["halves"][c["half"]] & (c["dpath"] <= 0.5 * new_w)
            note = f"{100 * fill:3.0f} % metal, its metal within {d90:.0f} mm of the path: {cur_w:g} → {new_w:g} mm wide"
            regions.append(dict(c, cells=new, width=new_w))
        print(f"  {r_['name']:<58} {note}")
    for i, r_ in enumerate(regions):
        r_["id"] = i
        r_["size"] = int(r_["cells"].sum())
        r_["metal"] = int((r_["cells"] & metal).sum())
    return write(ctx, label, regions, None, None, {"step": "next", "before": before, "width_mm": prev.get("width_mm", width)})


def write(ctx: dict, label: str, regions: list, cands: list | None, chosen, extra: dict) -> dict:
    n, h, lo, metal, kind = ctx["n"], ctx["h"], ctx["lo"], ctx["metal"], ctx["kind"]
    mask = np.zeros(len(kind), bool)
    lab = np.full(len(kind), -1, np.int16)
    for i, r_ in enumerate(regions):
        lab[r_["cells"] & (lab < 0)] = i
        mask |= r_["cells"]
    total = int(metal.sum())
    held = int((mask & metal).sum())
    print(f"{label}: {len(regions)} regions, {int(mask.sum()):,} voxels ({100 * mask.sum() / (kind == 0).sum():.0f} % of the free), holding "
          f"{100 * held / max(total, 1):.0f} % of the run's metal; left out: {total - held:,} voxels ({(total - held) * h**3 * 2.7e-6:.2f} kg)")  # fmt: skip
    np.savez_compressed(OUT / f"{label}.npz", mask=mask.reshape(n), label=lab.reshape(n), lo=lo, n=np.asarray(n), h=h)
    keys = ("name", "kind", "ends", "half", "width", "boss_r", "seat_r", "xy", "path_mm")
    out = {"label": label, "run": ctx["run"], **extra, "held": held / max(total, 1), "chosen_voxels": int(mask.sum()),
           "free_voxels": int((kind == 0).sum()),
           "regions": [{"id": i, **{k: r_[k] for k in keys if k in r_}, "voxels": int(r_["cells"].sum()), "metal": int((r_["cells"] & metal).sum())}
                       for i, r_ in enumerate(regions)],
           "candidates": [{"id": i, "name": r_["name"], "kind": r_["kind"], "ends": r_["ends"], "voxels": int(r_["cells"].sum()),
                           "metal": int((r_["cells"] & metal).sum()), "chosen": True} for i, r_ in enumerate(regions)]}  # fmt: skip
    if cands is not None:
        out["all_candidates"] = [{"name": c["name"], "kind": c["kind"], "voxels": c["size"], "metal": c["metal"], "chosen": bool(chosen[ci])}
                                 for ci, c in enumerate(cands)]  # fmt: skip
    (OUT / f"{label}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    picture(label, mask.reshape(n), metal.reshape(n), lab.reshape(n), lo, h, ctx["ks"], ctx["info"], len(regions))
    return out


def picture(label, mask, metal, lab, lo, h, ks, info, n_regions):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    cmap = plt.get_cmap("tab20")
    for ax, (half, sl) in zip(axes, (("motor_side", slice(0, ks)), ("cover", slice(ks, None)))):
        m_plan = mask[:, :, sl].any(axis=2)
        metal_plan = metal[:, :, sl].any(axis=2)
        lab_plan = np.where(lab[:, :, sl] >= 0, lab[:, :, sl], 10_000).min(axis=2)
        ex = [lo[0], lo[0] + h * mask.shape[0], lo[1], lo[1] + h * mask.shape[1]]
        rgb = np.ones(m_plan.shape + (3,))
        for ci in range(n_regions):
            rgb[lab_plan == ci] = np.asarray(cmap(ci % 20)[:3]) * 0.55 + 0.45
        rgb[metal_plan & ~m_plan] = (0.85, 0.15, 0.15)
        ax.imshow(np.transpose(rgb, (1, 0, 2)), origin="lower", extent=ex, interpolation="nearest")
        hy, hx = np.nonzero((metal_plan & m_plan).T)
        ax.scatter(lo[0] + h * (hx + 0.5), lo[1] + h * (hy + 0.5), s=1.2, c="k", alpha=0.35, linewidths=0)
        for b in info["bearings"]:
            if (b["side"] == "+z") == (half == "cover"):
                ax.add_patch(plt.Circle(b["axis"], b["D"] / 2, fill=False, color="b", lw=0.8))
        for mnt in info["mounts"]:
            ax.plot(*mnt["centre"], "b+")
        for bx, by in info["bolts"]:
            ax.plot(bx, by, "o", ms=3, mfc="none", mec="0.3")
        ax.set_aspect("equal")
        ax.set_title(f"{half}: the regions (tinted), the run's metal they hold (dots), the metal left out (red)", fontsize=8)
    fig.suptitle(f"{label}: the design volume from the hard points")
    fig.savefig(OUT / f"{label}.png", dpi=110, bbox_inches="tight")
    print(OUT / f"{label}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=("first", "next"))
    ap.add_argument("run")
    ap.add_argument("before", nargs="?", default="")
    ap.add_argument("--label", required=True)
    ap.add_argument("--width", type=float, default=48.0, help="mm: a strip's width at first")
    ap.add_argument("--cover", type=float, default=0.9, help="the share of the free run's metal the chosen regions must hold")
    ap.add_argument("--seats", type=int, default=2, help="each mount's strips to its nearest seats")
    ap.add_argument("--bolts", type=int, default=3, help="each mount's strips to its nearest flange bolts")
    ap.add_argument("--reach", type=float, default=120.0, help="mm: each seat's strips to every bolt this near its boss's edge")
    ap.add_argument("--least", type=float, default=16.0, help="next: mm, a strip's least width")
    ap.add_argument("--drop", type=float, default=0.12, help="next: a region holding less of its voxels as metal is dropped")
    ap.add_argument("--to", type=float, default=None, help="next: mm, every strip at most this wide (the volumes shrunk by rule, step by step)")
    a = ap.parse_args()
    if a.step == "first":
        first(a.run, a.label, a.width, a.cover, a.seats, a.bolts, a.reach)
    else:
        refine(a.run, a.before, a.label, a.least, a.drop, a.width, a.seats, a.bolts, a.reach, a.to)
