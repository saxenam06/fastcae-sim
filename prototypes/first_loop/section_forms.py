"""A form of its own for each clean section (LOP-24, approach 1 as the engineer meant it, 12 October 01:34: the
design space sectioned by the housing's geometry, each section given a form so that metal cannot smear across
it; the places from the material flow, the sizes the optimiser's).

Each section of `sections.py` has a centre in plan: its room's axis, or its mount's centre. The run's metal in
the section (height-weighted) is binned by its direction from the centre in `BINS` sectors; each sector holding
at least `--peak` of the fullest one's metal, at least `--sep` degrees from a stronger one, becomes a **rib**: a
radial strip `--rib` mm wide through the section, its height linear from the section's inner edge to its outer
(a root and a tip height). On an end face it is a spoke from the boss outwards, in a side band a fin along the
pull (the column's run from the split), in a mount's zone an arm from the lug to the shell. A boss stays one ring
(one height). The rest of each section is one more volume of one height (`--rest const`, the section's own wall
thickening) or empty (`--rest none`). Then `topo_free.py --height-volumes <label>_cols.npz` sizes every rib and
ring.

    section_forms.py <run> <sections label> --label <label> [--rib 10] [--sep 30] [--peak 0.5] [--rest const]

Writes data/first_loop/<label>_cols.npz (each column's volume, its law and its place along a rib), <label>.json
(the volumes: each one's section, kind, direction, columns, the run's metal in it) and <label>.png."""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions as rg  # noqa: E402
import smooth_heights as shh  # noqa: E402
import topo  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"
BINS = 36


def outline_pieces() -> dict:
    """Each half's rooms' outsides in plan: (axis, radius to the wall's outer face) per piece (`cup.pieces`)."""
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    import cup as cupmod
    import shell as convex
    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.chain import complete_chain
    from zenryx.domains.gearbox.forces import value_in

    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    wall, z_split = float(lay["settings"]["wall"]), float(lay["z"]["split"])
    spec, _ = load_and_validate(convex.CONTRACT)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(complete_chain(spec), value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    return {half: [(np.asarray(p["axis"], float), float(p["r"]) + wall) for p in cupmod.pieces(all_rooms, z_split, half)] for half in ("motor_side", "cover")}


def outline_inside(ctx: dict):
    """A function (half, n0, n1) -> the plan cells within that half's shell outline (its rooms' outsides)."""
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    import cup as cupmod
    import shell as convex
    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.chain import complete_chain
    from zenryx.domains.gearbox.forces import value_in

    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    wall, z_split = float(lay["settings"]["wall"]), float(lay["z"]["split"])
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    lo, h = ctx["lo"], ctx["h"]

    def inside(half: str, n0: int, n1: int) -> np.ndarray:
        gx = lo[0] + h * (np.arange(n0) + 0.5)
        gy = lo[1] + h * (np.arange(n1) + 0.5)
        px, py = np.meshgrid(gx, gy, indexing="ij")
        m = np.zeros((n0, n1), bool)
        for p in cupmod.pieces(all_rooms, z_split, half):
            m |= np.hypot(px - p["axis"][0], py - p["axis"][1]) <= float(p["r"]) + wall
        return m

    return inside


def flow_ribs(weight: np.ndarray, pts: np.ndarray, layer: np.ndarray, h: float, inside_of, prune_mm: float, tol: float,
              least_w: float, most_w: float) -> list[dict]:
    """The flow's own lines as ribs (12 October 01:47: per-section spokes missed the load paths that cross the
    sections): each half's metal in plan, over the end walls and beside the side walls apart, thinned to its
    skeleton (`skeleton_members`), its twigs under `prune_mm` pruned, each branch simplified to straight
    segments (Douglas-Peucker, `tol` mm); a segment's rib as wide as the metal about it (twice its distance to
    the metal's edge, in 4 mm steps, from `least_w` to `most_w`). Returns each segment: its half, its ends (mm)
    and its width."""
    from scipy.ndimage import distance_transform_edt
    from skimage.measure import approximate_polygon
    from skimage.morphology import skeletonize

    import skeleton_members as sk

    out = []
    n0, n1 = int(pts[:, 0].max()) + 1, int(pts[:, 1].max()) + 1
    for half, base in (("motor_side", 1), ("cover", 10_001)):
        sel = layer == base
        plan = np.zeros((n0, n1))
        plan[pts[sel, 0].astype(int), pts[sel, 1].astype(int)] = weight[sel]
        inside = inside_of(half, n0, n1)
        for keep in (inside, ~inside):
            foot = (plan > 0) & keep
            if foot.sum() < 6:
                continue
            edt = distance_transform_edt(foot) * h
            skel = sk.prune(skeletonize(foot), prune_mm / h)
            branches, _ = sk.skeleton_graph(skel)
            for b in branches:
                cells = np.asarray(b, float)
                if len(cells) < 3:
                    continue
                poly = approximate_polygon(cells, tolerance=tol / h)
                for p0, p1 in zip(poly[:-1], poly[1:]):
                    if np.hypot(*(p1 - p0)) * h < 8.0:
                        continue
                    k = np.linspace(0.0, 1.0, 9)
                    seg = p0[None, :] + k[:, None] * (p1 - p0)[None, :]
                    ii = np.clip(np.rint(seg[:, 0]).astype(int), 0, n0 - 1)
                    jj = np.clip(np.rint(seg[:, 1]).astype(int), 0, n1 - 1)
                    width = float(np.median(2.0 * edt[ii, jj]))
                    width = min(most_w, max(least_w, 4.0 * round(width / 4.0)))
                    out.append({"half": half, "a": (p0 + 0.5).tolist(), "b": (p1 + 0.5).tolist(), "width": width,
                                "over": "the end walls" if keep is inside else "the side walls"})  # fmt: skip
    return out


def line_ribs(ctx: dict, pts: np.ndarray, layer: np.ndarray, weight: np.ndarray, width: float, reach: float, fill_least: float,
              overlap_most: float, n_bolts: int, seat_pairs: bool = True) -> list[dict]:  # fmt: skip
    """Straight ribs between the hard points where the flow runs (12 October 02:50; production's pattern, judged
    against the photos: plates from each bearing's boss to the next boss, to the flange's bolts and to the mounts,
    each mount's lug tied to its nearest bolts). The candidates per half: seat to seat, each seat to every bolt
    within `reach` of its centre and to every mount, each mount to its `n_bolts` nearest bolts; each a strip
    `width` wide from one hard point's rim to the other's. Each is scored by the run's flow: the share of its
    columns holding the run's metal (`weight` > 0). Taken best first while that share is at least `fill_least`
    and at most `overlap_most` of its columns already belong to a rib taken before. Returns each rib: its half,
    its ends (plan cells) and its width."""
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    lo, h = ctx["lo"], ctx["h"]
    pc_mm = lo[:2] + h * (pts[:, :2] + 0.5)
    out = []
    for half, base in (("motor_side", 1), ("cover", 10_001)):
        sel = np.flatnonzero(layer == base)
        hard = [("seat", np.asarray(b["axis"], float), 0.5 * float(b["D"]) + 6.0) for b in lay["bearings"] if (b["side"] == "+z") == (half == "cover")]
        bolts = [("bolt", np.asarray(c, float), 10.0) for c in lay["bolts"]]
        mounts = [("mount", np.asarray(m["centre"], float), 18.0) for m in lay["mounts"]] if half == "motor_side" else []
        pairs = [(a, b) for k, a in enumerate(hard) for b in hard[k + 1:]] if seat_pairs else []
        pairs += [(a, b) for a in hard for b in bolts if np.hypot(*(a[1] - b[1])) <= reach]
        pairs += [(a, b) for a in hard for b in mounts]
        for m in mounts:
            pairs += [(m, b) for b in sorted(bolts, key=lambda b: np.hypot(*(m[1] - b[1])))[:n_bolts]]
        cands = []
        for a, b in pairs:
            d = b[1] - a[1]
            length = float(np.hypot(*d))
            if length <= a[2] + b[2] + 8.0:
                continue
            u = d / length
            p0, p1 = a[1] + u * a[2], b[1] - u * b[2]
            seg = p1 - p0
            sv = ((pc_mm[sel] - p0) @ seg) / float(seg @ seg)
            foot = p0 + np.clip(sv, 0.0, 1.0)[:, None] * seg
            dist = np.hypot(*(pc_mm[sel] - foot).T)
            strip = sel[(dist <= 0.5 * width) & (sv >= 0.0) & (sv <= 1.0)]
            if len(strip) < 4:
                continue
            fill = float((weight[strip] > 0).mean())
            cands.append({"half": half, "from": a[0], "to": b[0], "a_mm": p0, "b_mm": p1, "cols": strip, "fill": fill})
        taken = np.zeros(len(pts), bool)
        for c in sorted(cands, key=lambda c: -c["fill"]):
            if c["fill"] < fill_least:
                break
            if taken[c["cols"]].mean() > overlap_most:
                continue
            taken[c["cols"]] = True
            out.append({"half": half, "a": ((c["a_mm"] - lo[:2]) / h).tolist(), "b": ((c["b_mm"] - lo[:2]) / h).tolist(), "width": width,
                        "from": c["from"], "to": c["to"], "fill": c["fill"]})  # fmt: skip
        print(f"{half}: {len(cands)} candidates, {sum(o['half'] == half for o in out)} ribs taken "
              f"({', '.join(f'{o['from']}-{o['to']} {o['fill']:.2f}' for o in out if o['half'] == half)})")  # fmt: skip
    return out


def main(run: str, sections: str, label: str, rib: float, sep: float, peak: float, rest: str, ribs_from: str = "angles",
         reach: float = 170.0, fill_least: float = 0.45, overlap_most: float = 0.35, n_bolts: int = 3, bridges: bool = False,
         belt: str = "none", belt_mm: float = 24.0, ring_mm: float = 0.0, gusset_gap: float = 24.0, gusset_w: float = 8.0,
         bridge_mm: float = 6.0, free_forms: bool = False) -> dict:  # fmt: skip
    ctx = rg.context(run)
    model, kind, h, lo = ctx["model"], ctx["kind"], ctx["h"], ctx["lo"]
    sec = json.loads((OUT / f"{sections}.json").read_text(encoding="utf-8"))
    cols = np.load(OUT / f"{sections}_cols.npz")
    sec_of_col = np.asarray(cols["vol_of_col"], np.int64)
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    if len(sec_of_col) != len(pts):
        raise ValueError(f"{sections}: {len(sec_of_col):,} columns, the model {len(pts):,}")
    cx = lo[0] + h * (pts[:, 0] + 0.5)
    cy = lo[1] + h * (pts[:, 1] + 0.5)
    # the run's metal a column: its height off its base (mm), the first run of each half (smooth_heights' maps)
    maps = shh.column_heights(run)
    t = np.zeros(len(pts))
    for half, base in (("motor_side", 1), ("cover", 10_001)):
        sel = layer == base
        t[sel] = maps[half][pts[sel, 0].astype(int), pts[sel, 1].astype(int)]
    weight = np.where(t >= 4.0, t, 0.0)
    vol_of_col = np.full(len(pts), -1, np.int64)
    s_of_col = np.zeros(len(pts), np.float32)
    law, volumes = [], []
    taken_all = np.zeros(len(pts), bool)
    if ribs_from in ("flow", "lines"):  # ribs along lines across the sections, then each section's ring or thickness
        insides = outline_inside(ctx)
        n0, n1 = int(pts[:, 0].max()) + 1, int(pts[:, 1].max()) + 1
        inside_col = np.zeros(len(pts), bool)
        for half, base in (("motor_side", 1), ("cover", 10_001)):
            m_in = insides(half, n0, n1)
            sel = layer == base
            inside_col[sel] = m_in[pts[sel, 0].astype(int), pts[sel, 1].astype(int)]
        pc = pts[:, :2] + 0.5
        if ribs_from == "lines" and ring_mm > 0:  # each bore's boss an annulus `ring_mm` wide (12 October 03:17: the boss
            # sections' whole areas as rings took the room between the input and intermediate bores, the optimiser left the
            # input's ring at nothing, and FE read the two seats pushed 40 µm apart)
            lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
            pc_mm = lo[:2] + h * (pts[:, :2] + 0.5)
            for b in lay["bearings"]:
                half = "cover" if b["side"] == "+z" else "motor_side"
                rho = np.hypot(*(pc_mm - np.asarray(b["axis"], float)).T)
                mine = np.flatnonzero((layer == (10_001 if half == "cover" else 1)) & ~taken_all & (rho <= 0.5 * float(b["D"]) + ring_mm))
                if len(mine) < 3:
                    continue
                sid = next((s["id"] for s in sec["sections"] if s["kind"] == "boss" and np.hypot(*(np.asarray(s["axis"]) - b["axis"])) < 1.0), -1)
                volumes.append({"name": f"{'Cover' if half == 'cover' else 'Motor side'}: the boss of the {b['shaft']} bore: the ring", "kind": "ring",
                                "section": sid, "half": half, "columns": len(mine), "metal": float(weight[mine].sum())})  # fmt: skip
                vol_of_col[mine] = len(law)
                law.append(0)
                taken_all[mine] = True
        elif ribs_from == "lines":  # the bosses' rings first: each rib starts at a boss's rim
            for s in sec["sections"]:
                mine = np.flatnonzero((sec_of_col == s["id"]) & ~taken_all)
                if s["kind"] != "boss" or not len(mine):
                    continue
                volumes.append({"name": f"{s['name']}: the ring", "kind": "ring", "section": s["id"], "columns": len(mine), "metal": float(weight[mine].sum())})
                vol_of_col[mine] = len(law)
                law.append(0)
                taken_all[mine] = True
        if ribs_from == "lines":
            if bridges:  # the bearings' bridges and their web (12 October 02:50: the free run fills the end wall between the
                # bores to the band's full height, a web tying the seats together; 12 mm ribs seat to seat, all at the band's
                # height, read the beds 2.6 times their line): each pair of seats on a half the hull of their bosses, a
                # height from one seat to the other, and the triangle between three seats one height
                lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
                pc_mm = lo[:2] + h * (pts[:, :2] + 0.5)
                for half, base in (("motor_side", 1), ("cover", 10_001)):
                    seats = [(b["shaft"], np.asarray(b["axis"], float), 0.5 * float(b["D"]) + bridge_mm) for b in lay["bearings"] if (b["side"] == "+z") == (half == "cover")]
                    on_half = (layer == base) & inside_col
                    links = []
                    for k, (na, ca, ra) in enumerate(seats):
                        for nb, cb, rb in seats[k + 1:]:
                            d = cb - ca
                            sv = ((pc_mm - ca) @ d) / float(d @ d)
                            sc = np.clip(sv, 0.0, 1.0)
                            dist = np.hypot(*(pc_mm - (ca + sc[:, None] * d)).T)
                            hull = on_half & ~taken_all & (dist <= ra + sc * (rb - ra))
                            if hull.sum() >= 4:
                                links.append((float((weight[hull] > 0).mean()), na, nb, hull, sc))
                    for fill, na, nb, hull, sc in sorted(links, key=lambda x: -x[0]):
                        hull = hull & ~taken_all
                        if fill < fill_least or hull.sum() < 4:
                            continue
                        volumes.append({"name": f"{'Cover' if half == 'cover' else 'Motor side'}: the bridge between the {na} and {nb} seats",
                                        "kind": "bridge", "section": -1, "columns": int(hull.sum()), "metal": float(weight[hull].sum()), "half": half, "fill": fill})  # fmt: skip
                        vol_of_col[hull] = len(law)
                        s_of_col[hull] = sc[hull]
                        law.append(1)
                        taken_all |= hull
                    if len(seats) == 3:
                        tri = np.array([c for _, c, _ in seats])
                        (x1, y1), (x2, y2), (x3, y3) = tri
                        den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
                        l1 = ((y2 - y3) * (pc_mm[:, 0] - x3) + (x3 - x2) * (pc_mm[:, 1] - y3)) / den
                        l2 = ((y3 - y1) * (pc_mm[:, 0] - x3) + (x1 - x3) * (pc_mm[:, 1] - y3)) / den
                        web = on_half & ~taken_all & (l1 >= 0) & (l2 >= 0) & (1.0 - l1 - l2 >= 0)
                        if web.sum() >= 4 and float((weight[web] > 0).mean()) >= fill_least:
                            volumes.append({"name": f"{'Cover' if half == 'cover' else 'Motor side'}: the web between its three seats", "kind": "web",
                                            "section": -1, "columns": int(web.sum()), "metal": float(weight[web].sum()), "half": half,
                                            "fill": float((weight[web] > 0).mean())})  # fmt: skip
                            vol_of_col[web] = len(law)
                            law.append(0)
                            taken_all |= web
            segments = line_ribs(ctx, pts, layer, weight, rib, reach, fill_least, overlap_most, n_bolts, seat_pairs=not bridges)
        else:
            segments = flow_ribs(weight, pts, layer, h, insides, 20.0, 6.0, 8.0, 24.0)
        for sgm in segments:
            base = 1 if sgm["half"] == "motor_side" else 10_001
            a, b = np.asarray(sgm["a"]), np.asarray(sgm["b"])
            d = b - a
            sv = ((pc - a) @ d) / max(float(d @ d), 1e-9)
            foot = a + np.clip(sv, 0.0, 1.0)[:, None] * d
            dist = np.hypot(*(pc - foot).T) * h
            near = (layer == base) & ~taken_all & (dist <= 0.5 * sgm["width"]) & (sv >= -0.05) & (sv <= 1.05)
            # a line from a boss to a bolt runs over the end wall, then beside the side wall down to the split: each
            # part its own rib (its own root and tip), as their columns stand on walls far apart along the pull
            parts = [sgm["over"]] if "over" in sgm else ["the end walls", "the side walls"]
            for over in parts:
                strip = near & (inside_col if over == "the end walls" else ~inside_col)
                if strip.sum() < 3:
                    continue
                s0, s1 = float(np.clip(sv[strip], 0, 1).min()), float(np.clip(sv[strip], 0, 1).max())
                pa, pb = a + s0 * d, a + s1 * d
                ang = math.degrees(math.atan2(d[1], d[0]))
                volumes.append({"name": f"{'Cover' if sgm['half'] == 'cover' else 'Motor side'}: a rib {sgm['width']:g} mm wide over {over} at {ang:.0f}°"
                                + (f" ({sgm['from']} to {sgm['to']})" if "from" in sgm else ""),
                                "kind": "rib", "section": -1, "angle": ang, "columns": int(strip.sum()), "metal": float(weight[strip].sum()),
                                "half": sgm["half"], "over": over, "width": sgm["width"],
                                "a_mm": (lo[:2] + h * pa).tolist(), "b_mm": (lo[:2] + h * pb).tolist()})  # fmt: skip
                vol_of_col[strip] = len(law)
                s_of_col[strip] = np.clip((sv[strip] - s0) / max(s1 - s0, 1e-9), 0.0, 1.0)
                law.append(1)
                taken_all |= strip
        if ribs_from == "lines" and belt == "volumes":  # the mounts' lugs, then the belt along the split (12 October 02:58: the metal
            # the bridges, rings and ribs left out of `sf_4` was mostly a belt round each half beside its side walls, up
            # to 20 mm and more off the split: the joint's stiff band, production's deep flange and its gussets)
            from scipy.ndimage import distance_transform_edt

            for s in sec["sections"]:
                mine = np.flatnonzero((sec_of_col == s["id"]) & ~taken_all & ~inside_col)
                if s["kind"] != "mount" or len(mine) < 3:
                    continue
                volumes.append({"name": f"{s['name']}: the lug's root", "kind": "lug", "section": s["id"], "columns": len(mine), "metal": float(weight[mine].sum())})
                vol_of_col[mine] = len(law)
                law.append(0)
                taken_all[mine] = True
            lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
            bolts = np.asarray(lay["bolts"], float)
            pc_mm = lo[:2] + h * (pts[:, :2] + 0.5)
            for half, base in (("motor_side", 1), ("cover", 10_001)):
                sel = layer == base
                plan_in = np.zeros((n0, n1), bool)
                plan_in[pts[sel & inside_col, 0].astype(int), pts[sel & inside_col, 1].astype(int)] = True
                d_out = distance_transform_edt(~plan_in) * h  # each plan cell's distance from the outline, mm
                rest_out = np.flatnonzero(sel & ~inside_col & ~taken_all)
                near = np.argmin(np.hypot(pc_mm[rest_out, 0, None] - bolts[None, :, 0], pc_mm[rest_out, 1, None] - bolts[None, :, 1]), axis=1)
                for kb in range(len(bolts)):
                    mine = rest_out[near == kb]
                    if len(mine) < 3:
                        continue
                    volumes.append({"name": f"{'Cover' if half == 'cover' else 'Motor side'}: the belt at bolt {kb + 1}", "kind": "belt", "section": -1,
                                    "columns": len(mine), "metal": float(weight[mine].sum()), "half": half})  # fmt: skip
                    vol_of_col[mine] = len(law)
                    s_of_col[mine] = np.clip(d_out[pts[mine, 0].astype(int), pts[mine, 1].astype(int)] / max(belt_mm, h), 0.0, 1.0)  # root at the wall
                    law.append(1)
                    taken_all[mine] = True
    if ribs_from == "lines" and belt == "gussets":  # beside the side walls, radial plates every `gusset_gap` mm round each
        # room (12 October 03:17: production's flange gussets, where the free run laid a belt and one height a bolt cost
        # 2 kg); each `gusset_w` wide, its height from the split, a root at the wall and a tip at the band's edge
        pcs = outline_pieces()
        pc_mm = lo[:2] + h * (pts[:, :2] + 0.5)
        for half, base in (("motor_side", 1), ("cover", 10_001)):
            cols_out = np.flatnonzero((layer == base) & ~inside_col & ~taken_all)
            if not len(cols_out):
                continue
            d = np.stack([np.hypot(*(pc_mm[cols_out] - ax).T) - r_o for ax, r_o in pcs[half]])
            near = np.argmin(d, axis=0)
            for kp, (ax, r_o) in enumerate(pcs[half]):
                mine = cols_out[near == kp]
                if not len(mine):
                    continue
                rel = pc_mm[mine] - ax
                theta, rho = np.arctan2(rel[:, 1], rel[:, 0]), np.hypot(*rel.T)
                dth = gusset_gap / r_o
                kk = np.rint(theta / dth).astype(int)
                on = np.abs(rho * np.sin(theta - kk * dth)) <= 0.5 * gusset_w
                for q in np.unique(kk[on]):
                    g_cols = mine[on & (kk == q)]
                    if len(g_cols) < 2:
                        continue
                    volumes.append({"name": f"{'Cover' if half == 'cover' else 'Motor side'}: a gusset at {math.degrees(q * dth):.0f}° round the room at "
                                            f"({ax[0]:.0f}, {ax[1]:.0f})", "kind": "gusset", "section": -1, "columns": len(g_cols),
                                    "metal": float(weight[g_cols].sum()), "half": half, "over": "the side walls", "width": gusset_w,
                                    "a_mm": (ax + r_o * np.array([math.cos(q * dth), math.sin(q * dth)])).tolist(),
                                    "b_mm": (ax + (r_o + belt_mm) * np.array([math.cos(q * dth), math.sin(q * dth)])).tolist()})  # fmt: skip
                    vol_of_col[g_cols] = len(law)
                    s_of_col[g_cols] = np.clip((rho[on & (kk == q)] - r_o) / max(belt_mm, h), 0.0, 1.0)
                    law.append(1)
                    taken_all[g_cols] = True
    for s in sec["sections"]:
        mine = np.flatnonzero((sec_of_col == s["id"]) & ~taken_all)
        if not len(mine):
            continue
        if ribs_from in ("flow", "lines"):  # the bosses rings, the rest of each section one thickness, free or empty
            w_ = weight[mine]
            if s["kind"] == "boss" or rest == "const":
                volumes.append({"name": f"{s['name']}: the ring" if s["kind"] == "boss" else f"{s['name']}: its thickness",
                                "kind": "ring" if s["kind"] == "boss" else "rest", "section": s["id"], "columns": len(mine), "metal": float(w_.sum())})  # fmt: skip
                vol_of_col[mine] = len(law)
                law.append(0)
            elif rest == "none":  # held empty (`topo.volume_map`'s -2): left free, the optimiser painted them (12 October 02:27)
                # with a free belt (12 October 03:02: the belt and the lugs as one-height volumes cost 2 kg over the free
                # run's), the columns beside the side walls stay the optimiser's own, the end walls' rest empty
                vol_of_col[mine[inside_col[mine]] if belt == "free" else mine] = -2
            # rest "free": left to the optimiser, each column its own height (the wall thickened where it pays)
            continue
        ax, ay = s["axis"]
        dx, dy = cx[mine] - ax, cy[mine] - ay
        r = np.hypot(dx, dy)
        ang = np.degrees(np.arctan2(dy, dx))
        w = weight[mine]
        if s["kind"] == "boss" or w.sum() <= 0:
            volumes.append({"name": f"{s['name']}: the ring" if s["kind"] == "boss" else f"{s['name']}: its thickness", "kind": "ring" if s["kind"] == "boss" else "rest",
                            "section": s["id"], "columns": len(mine), "metal": float(w.sum())})  # fmt: skip
            vol_of_col[mine] = len(law)
            law.append(0)
            continue
        hist, edges = np.histogram(ang, bins=BINS, range=(-180.0, 180.0), weights=w)
        order = np.argsort(hist)[::-1]
        chosen = []
        for b in order:
            if hist[b] < peak * hist[order[0]]:
                break
            centre = 0.5 * (edges[b] + edges[b + 1])
            if all(abs((centre - c + 180.0) % 360.0 - 180.0) >= sep for c in chosen):
                chosen.append(centre)
        taken = np.zeros(len(mine), bool)
        r_in, r_out = float(r.min()), float(r.max())
        for c in chosen:
            u = np.array([math.cos(math.radians(c)), math.sin(math.radians(c))])
            along = dx * u[0] + dy * u[1]
            across = np.abs(-dx * u[1] + dy * u[0])
            strip = (along > 0) & (across <= 0.5 * rib) & ~taken
            if strip.sum() < 3:
                continue
            a0, a1 = float(along[strip].min()), float(along[strip].max())
            word = {"end": "a spoke", "side": "a fin", "mount": "an arm"}.get(s["kind"], "a rib")
            volumes.append({"name": f"{s['name']}: {word} at {c:.0f}°", "kind": {"end": "spoke", "side": "fin", "mount": "arm"}.get(s["kind"], "rib"),
                            "section": s["id"], "angle": c, "columns": int(strip.sum()), "metal": float(w[strip].sum())})  # fmt: skip
            idx = mine[strip]
            vol_of_col[idx] = len(law)
            s_of_col[idx] = np.clip((along[strip] - a0) / max(a1 - a0, 1e-6), 0.0, 1.0)
            law.append(1)
            taken |= strip
        left = mine[~taken]
        if len(left) and rest == "const":
            volumes.append({"name": f"{s['name']}: its thickness", "kind": "rest", "section": s["id"], "columns": len(left), "metal": float(w[~taken].sum())})
            vol_of_col[left] = len(law)
            law.append(0)
        del r_in, r_out
    law = np.asarray(law, np.int8)
    layout_of_col = vol_of_col.copy()
    if free_forms:  # the plan regular, the heights free (12 October 03:25: one height a ring, a bridge or a rib cost twice
        # the free run's metal, `ln_5` 9.25 kg): every column of a form its own height, mixed by the plan filter among the
        # forms' columns only, so the metal can only make the forms; every other column empty
        vol_of_col = np.where(layout_of_col >= 0, -1, -2)
        law = np.zeros(0, np.int8)
    np.savez_compressed(OUT / f"{label}_cols.npz", vol_of_col=vol_of_col.astype(np.int32), law=law, s_of_col=s_of_col,
                        layout_of_col=layout_of_col.astype(np.int32))  # fmt: skip
    total = max(float(weight.sum()), 1e-9)
    for v in volumes:
        v["metal_share"] = v["metal"] / total
    out = {"label": label, "run": run, "sections": sections, "rib_mm": rib, "rest": rest, "volumes": volumes,
           "ribs": int(sum(v["kind"] in ("spoke", "fin", "arm", "rib") for v in volumes)), "parameters": int((law == 1).sum() * 2 + (law == 0).sum())}
    (OUT / f"{label}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    held = sum(v["metal"] for v in volumes if v["kind"] in ("spoke", "fin", "arm", "rib", "ring")) / total
    print(f"{len(volumes)} volumes ({out['ribs']} ribs: {sum(v['kind'] == 'spoke' for v in volumes)} spokes, {sum(v['kind'] == 'fin' for v in volumes)} fins, "
          f"{sum(v['kind'] == 'arm' for v in volumes)} arms; {sum(v['kind'] == 'ring' for v in volumes)} rings), {out['parameters']} parameters; "
          f"the ribs and rings lie where {100 * held:.0f} % of the run's metal was")  # fmt: skip
    picture(label, pts, layer, layout_of_col, law, volumes, lo, h, ctx["info"])
    return out


def picture(label, pts, layer, vol_of_col, law, volumes, lo, h, info):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    tint = {"spoke": (0.85, 0.35, 0.15), "fin": (0.20, 0.55, 0.80), "arm": (0.85, 0.65, 0.10), "rib": (0.6, 0.3, 0.6), "ring": (0.15, 0.45, 0.25),
            "bridge": (0.95, 0.55, 0.20), "web": (0.95, 0.80, 0.30), "belt": (0.30, 0.70, 0.75), "lug": (0.55, 0.40, 0.20), "gusset": (0.20, 0.35, 0.85),
            "rest": (0.88, 0.88, 0.88)}  # fmt: skip
    for ax, (half, base) in zip(axes, (("motor_side", 1), ("cover", 10_001))):
        sel = (layer == base) & (vol_of_col >= 0)
        cx = lo[0] + h * (pts[sel, 0] + 0.5)
        cy = lo[1] + h * (pts[sel, 1] + 0.5)
        colours = np.array([tint[volumes[v]["kind"]] for v in vol_of_col[sel]])
        ax.scatter(cx, cy, s=4, c=colours, marker="s", linewidths=0)
        for b in info["bearings"]:
            if (b["side"] == "+z") == (half == "cover"):
                ax.add_patch(plt.Circle(b["axis"], b["D"] / 2, fill=False, color="k", lw=0.8))
        for m in info["mounts"]:
            ax.plot(*m["centre"], "k+")
        ax.set_aspect("equal")
        ax.set_title(f"{half}: spokes (orange), fins (blue), arms (yellow), rings (green), each section's rest (grey)", fontsize=8)
    fig.suptitle(f"{label}: each section's form, its ribs where the flow runs")
    fig.savefig(OUT / f"{label}.png", dpi=110, bbox_inches="tight")
    print(OUT / f"{label}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("sections")
    ap.add_argument("--label", required=True)
    ap.add_argument("--rib", type=float, default=10.0, help="mm, a rib's width")
    ap.add_argument("--sep", type=float, default=30.0, help="degrees between two ribs of one section")
    ap.add_argument("--peak", type=float, default=0.5, help="a direction holding at least this share of the fullest one's metal becomes a rib")
    ap.add_argument("--rest", default="const", choices=("const", "none", "free"), help="each section's rest: one height, empty, or each column free")
    ap.add_argument("--ribs-from", default="angles", choices=("angles", "flow", "lines"),
                    help="the ribs from each section's directions (angles), along the flow's own lines across the sections (flow), "
                         "or straight between the hard points where the flow runs (lines)")  # fmt: skip
    ap.add_argument("--reach", type=float, default=170.0, help="lines: mm, a seat's ribs to every bolt this near its centre")
    ap.add_argument("--fill", type=float, default=0.45, help="lines: the least share of a rib's columns holding the run's metal")
    ap.add_argument("--overlap", type=float, default=0.35, help="lines: the most share of a rib's columns already another's")
    ap.add_argument("--bolts", type=int, default=3, help="lines: each mount's ribs to its nearest bolts")
    ap.add_argument("--bridges", action="store_true", help="lines: the seats tied by bridges (their bosses' hull) and a web between three, not ribs")
    ap.add_argument("--belt", default="none", choices=("none", "volumes", "free", "gussets"),
                    help="lines: beside the side walls: held empty with the rest, the mounts' lugs and a belt a volume per bolt, free, or gussets")  # fmt: skip
    ap.add_argument("--ring", type=float, default=0.0, help="lines: mm, each bore's ring an annulus this wide (0: the boss sections)")
    ap.add_argument("--gusset-gap", type=float, default=24.0, help="lines, gussets: mm between two round a room")
    ap.add_argument("--gusset-w", type=float, default=8.0, help="lines, gussets: mm, a gusset's width")
    ap.add_argument("--bridge-r", type=float, default=6.0, help="lines, bridges: mm past each bore's radius the hull of two bosses reaches")
    ap.add_argument("--free-forms", action="store_true", help="every form's columns free (each its own height), every other column empty")
    a = ap.parse_args()
    main(a.run, a.sections, a.label, a.rib, a.sep, a.peak, a.rest, a.ribs_from, a.reach, a.fill, a.overlap, a.bolts, a.bridges, a.belt,
         ring_mm=a.ring, gusset_gap=a.gusset_gap, gusset_w=a.gusset_w, bridge_mm=a.bridge_r, free_forms=a.free_forms)  # fmt: skip
