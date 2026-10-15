"""PROTOTYPE (LOP-28) - the hand-over's map: a design's features and members, where they stand, what shape, what size, read
from the optimiser's own field, for a CAD designer to draw from (the engineer, 13 October 01:30: "a production quality housing
geometry that meets the goal and can be delivered to a cad designer who gets clear direction about the features and members
to be drawn where and in what shape").

Per half, on the run's own 4 mm columns (the first run from the split):
- **the protected features** (the layout's, held by the run: `--protect`): each bearing's boss (a tower of Ø 2 boss_r from a
  wall past its seat to the split), the bolts' bosses, the mounts' lugs, the sealing land; listed with their sizes;
- **the walls:** the inside grown by the least wall (the lobes), drawn as outlines;
- **the members:** the run's placed metal beyond each column's least height (as the drawing takes it, `exact_walls.extra_placed`),
  outside the protected features, at least `PROUD` mm proud of its wall: each connected piece thinned to its skeleton
  (`skeleton_members`), each branch a member with its centre-line, length, width (twice the distance to its edge, median),
  height off its wall (median and most), straight or curved, what each end meets (a boss, a mount, a bolt's boss, the wall's
  edge or another member, within `TOUCH` mm), and its kind: a rib (no wider than `RIB_W`, at least 2.5 times as long as
  wide), an arm (meeting a mount), a gusset (short, from a boss or the wall), or a web (wider).
Writes data/first_loop/member_map_<design>.png (both halves, members numbered and coloured by kind, features labelled),
member_map_<design>.json and member_map_<design>.md (the table).

Run: .venv/Scripts/python.exe prototypes/first_loop/member_map.py <design>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import exact_walls  # noqa: E402
import skeleton_members as sk  # noqa: E402
import topo  # noqa: E402

OUT = topo.OUT
PROUD = 4.0  # mm: a member stands at least this proud of its wall
TOUCH = 10.0  # mm: an end meets what lies within this
RIB_W = 14.0  # mm: a rib no wider
PRUNE = 12.0  # mm: shorter twigs pruned
CRUMB = 6  # cells: smaller pieces dropped
COLOURS = {"rib": "tab:red", "arm": "tab:purple", "gusset": "tab:orange", "web": "tab:green", "network": "tab:brown"}
RUN_TOL = 6.0  # mm: a centre-line simplified to straight runs within this (the designer's reading)
# the kinds drawn as the field has them (their depth varies: to a lug, at a junction); the rest as straight runs at their deep
# height (13 October 04:25: `final10rp` held every static line so, at +0.3 kg; at their median heights they lost a third)
AS_FIELD = ("arm", "network")
RUN_LEAST = 6.0  # mm: shorter runs are folded into their neighbours


def _rdp(p: np.ndarray, tol: float) -> list[int]:
    """Ramer-Douglas-Peucker: the indices of a polyline's points kept so that every dropped point lies within `tol` of
    the straight run that replaces it."""
    keep, stack = {0, len(p) - 1}, [(0, len(p) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        d = p[b] - p[a]
        nd = float(np.hypot(*d))
        rel = p[a + 1 : b] - p[a]
        off = np.abs(rel[:, 0] * d[1] - rel[:, 1] * d[0]) / nd if nd > 1e-9 else np.hypot(rel[:, 0], rel[:, 1])
        k = int(np.argmax(off))
        if off[k] > tol:
            keep.add(a + 1 + k)
            stack += [(a, a + 1 + k), (a + 1 + k, b)]
    return sorted(keep)


def snap_runs(runs: list[dict], met: list[tuple]) -> list[dict]:
    """(LOP-28) Production's ribs end on something: each feature the member meets (a boss, a lug, a bolt's boss: (name,
    centre, radius)) is reached by a connector run from the member's nearest run onto the feature's face, as wide as that
    run and as tall as it is there, unless that run already reaches the face (the skeleton stops short of a member's
    edge: mount-3's arm parted from its lug, 13 October 04:05)."""
    out = list(runs)
    for name, c, rad in met:
        best = None
        for r_ in runs:
            a, b = np.asarray(r_["from_mm"], float), np.asarray(r_["to_mm"], float)
            d = b - a
            t = float(np.clip(((c - a) @ d) / max(float(d @ d), 1e-9), 0.0, 1.0))
            p = a + t * d
            gap = float(np.hypot(*(p - c))) - rad - r_["width_mm"] / 2
            if best is None or gap < best[0]:
                best = (gap, p, t, r_)
        if best is None or (best[0] <= 0.0 and not name.startswith("mount")):  # a lug always gets its web, over its length
            continue
        _, p, t, r_ = best
        tall = r_["height_from_mm"] + (r_["height_to_mm"] - r_["height_from_mm"]) * t
        q = c + (p - c) / max(float(np.hypot(*(p - c))), 1e-9) * (rad - 1.0)
        out.append({"from_mm": [round(float(v), 1) for v in p], "to_mm": [round(float(v), 1) for v in q],
                    "length_mm": round(float(np.hypot(*(q - p))), 1), "width_mm": r_["width_mm"], "height_mm": round(tall, 1),
                    "height_from_mm": round(tall, 1), "height_to_mm": round(tall, 1), "height_deep_mm": r_.get("height_deep_mm", round(tall, 1)),
                    "connector": True, "meets": name})  # fmt: skip
    return out


def _seg_dist(xy: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Each point's distance to the segment a-b."""
    d = b - a
    t = np.clip(((xy - a) @ d) / max(float(d @ d), 1e-9), 0.0, 1.0)
    return np.hypot(*(xy - (a + t[:, None] * d[None, :])).T)


def runs_of(paths: list[list[list[float]]], xy: np.ndarray, hts: np.ndarray, h: float, ends: tuple) -> list[dict]:
    """(LOP-28) A member read as a designer draws it: each branch of its centre-line simplified to straight runs (`_rdp`,
    `RUN_TOL`), every cell of the member given to its nearest run, so each run's width is its cells' area over its length
    and its height their median metal beyond the wall. A member with no branch is one run along its main direction."""
    segs = []
    for path in paths:
        p = np.asarray(path, float)
        idx = _rdp(p, RUN_TOL)
        segs += [(p[i], p[j]) for i, j in zip(idx[:-1], idx[1:], strict=True) if np.hypot(*(p[j] - p[i])) >= RUN_LEAST]
    if not segs:
        segs = [(np.asarray(ends[0], float), np.asarray(ends[1], float))]
    dist = np.stack([_seg_dist(xy, a, b) for a, b in segs], axis=1)
    own = np.argmin(dist, axis=1)
    out = []
    for j, (a, b) in enumerate(segs):
        mine = own == j
        if not mine.any():
            continue
        length = float(np.hypot(*(b - a)))
        # the height at each end (the median of the run's cells in its end third) as well as along it: a bracket deepens
        # toward its lug, and one height cut mount-3's arm short of it (13 October 04:03)
        t = np.clip(((xy[mine] - a) @ (b - a)) / max(length**2, 1e-9), 0.0, 1.0)
        mid = float(np.median(hts[mine]))
        h_a = float(np.median(hts[mine][t <= 1 / 3])) if (t <= 1 / 3).any() else mid
        h_b = float(np.median(hts[mine][t >= 2 / 3])) if (t >= 2 / 3).any() else mid
        out.append({"from_mm": [round(float(v), 1) for v in a], "to_mm": [round(float(v), 1) for v in b], "length_mm": round(length, 1),
                    "width_mm": round(float(mine.sum()) * h * h / (length + h), 1), "height_mm": round(mid, 1),
                    "height_from_mm": round(h_a, 1), "height_to_mm": round(h_b, 1),
                    "height_deep_mm": round(float(np.percentile(hts[mine], 90)), 1)})  # fmt: skip
    return out


def _rooms() -> list[dict]:
    """The contract's gear rooms (`cup.rooms`)."""
    import cup as cupmod
    import shell as convex

    from zenryx.contract.validate import load_and_validate
    from zenryx.domains.gearbox.chain import complete_chain
    from zenryx.domains.gearbox.forces import value_in

    spec, _ = load_and_validate(convex.CONTRACT)
    gaps = spec.requirement.shaft_layout
    return cupmod.rooms(complete_chain(spec), value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))


def _room_pieces(layout: dict, half: str) -> list[dict]:
    """The half's rooms in plan (`cup.pieces`), each a circle with its far face."""
    import cup as cupmod

    return cupmod.pieces(_rooms(), float(layout["z"]["split"]), half)


def _lug_webs(rec: dict, layout: dict) -> list[dict]:
    """The design's fixed lug webs (`exact_walls.lug_webs`, `LOOP_LUG_WEBS`), if it has them."""
    spec = (rec.get("skin") or {}).get("lug_webs")
    if not spec:
        return []
    thick, spread = (float(v) for v in spec.split(":"))
    return exact_walls.lug_webs(layout, _rooms(), float(layout["z"]["split"]), thick, spread)


def _draw_spokes(ax, layout: dict, feats: list[dict], half: str) -> None:
    """The fixed panel spokes, if the half has them, each from its boss out to the end wall's rim (the rooms' outline)."""
    spoke_f = next((f for f in feats if f["kind"] == "panel spokes"), None)
    if spoke_f is None:
        return
    side = "-z" if half == "motor_side" else "+z"
    pieces = _room_pieces(layout, half)
    pitch_ = float(spoke_f["of"].split("°")[0].split()[-1])
    for b in layout["bearings"]:
        if b["side"] != side:
            continue
        for ang in np.radians(np.arange(0.0, 360.0, pitch_)):
            rr = np.arange(float(b["boss_r"]) - 2.0, 260.0, 2.0)
            qx, qy = b["axis"][0] + rr * np.cos(ang), b["axis"][1] + rr * np.sin(ang)
            on = np.zeros(len(rr), bool)
            for p in pieces:
                on |= np.hypot(qx - p["axis"][0], qy - p["axis"][1]) <= p["r"]
            if on.any():
                last = int(np.flatnonzero(~on)[0]) if (~on).any() else len(rr)
                ax.plot(qx[:last], qy[:last], color="tab:pink", lw=1.6, ls="--")


def reading(design: str, out: dict, layout: dict, png: Path) -> None:
    """(LOP-28) The designer's reading: each half along its pull with its walls' outside (each room grown by the least wall),
    its protected features and each member's runs (`runs_of`) drawn as rib footprints as wide as the run, coloured by the
    run's height off the wall and labelled width × height (mm). A reading of the field for the CAD designer; FE judged the
    field, not this."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Polygon

    s = layout["settings"]
    wall = float(s["wall"])
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    pc = None
    for ax, half in zip(axes, ("cover", "motor_side"), strict=True):
        lower = half == "motor_side"
        side = "-z" if lower else "+z"
        d = out["halves"][half]
        th = np.linspace(0.0, 2.0 * np.pi, 181)
        for p in _room_pieces(layout, half):
            ax.plot(p["axis"][0] + (p["r"] + wall) * np.cos(th), p["axis"][1] + (p["r"] + wall) * np.sin(th), color="0.7", lw=0.8)
        for b in layout["bearings"]:
            if b["side"] != side:
                continue
            ax.add_patch(plt.Circle(b["axis"], float(b["boss_r"]), fc="tab:blue", alpha=0.15, ec="tab:blue", lw=1.5))
            ax.text(b["axis"][0], b["axis"][1], f"{b['shaft']}\nØ{2 * float(b['boss_r']):g}", color="tab:blue", fontsize=8, ha="center", va="center")
        for c in layout["bolts"]:
            ax.add_patch(plt.Circle(c, s["bolt_boss"] / 2, fill=False, color="tab:cyan", lw=1))
        if lower:
            for m in layout["mounts"]:
                ax.add_patch(plt.Circle(m["centre"], s["mount_diameter"] / 2, fc="tab:blue", alpha=0.15, ec="tab:blue", lw=1.5))
                ax.text(*m["centre"], f"{m['name']}\nØ{s['mount_diameter']:g}", color="tab:blue", fontsize=7, ha="center", va="center")
        _draw_spokes(ax, layout, d["features"], half)
        for w in d.get("lug_webs", []):  # the fixed lug webs, as the bosses: protected
            ax.plot([w["from"][0], w["to"][0]], [w["from"][1], w["to"][1]], color="tab:blue", lw=3.0, solid_capstyle="round")
        polys, heights, field_polys = [], [], []
        for m_ in d["members"]:
            as_field = m_["kind"] in AS_FIELD
            for r_ in m_["runs"]:
                a, b = np.asarray(r_["from_mm"], float), np.asarray(r_["to_mm"], float)
                length = float(np.hypot(*(b - a)))
                if length < 1e-6:
                    continue
                t = (b - a) / length
                # the run's footprint with round ends, so runs that meet join as the designer's ribs do
                half_w = r_["width_mm"] / 2
                arc = np.linspace(-np.pi / 2, np.pi / 2, 9)
                n_ = np.array([-t[1], t[0]])
                cap_b = [b + half_w * (np.cos(q) * t + np.sin(q) * n_) for q in arc]
                cap_a = [a + half_w * (-np.cos(q) * t - np.sin(q) * n_) for q in arc]
                if as_field:  # an arm's or a network's depth varies: drawn from the field, outlined here only
                    field_polys.append(Polygon([*cap_b, *cap_a], closed=True))
                    continue
                polys.append(Polygon([*cap_b, *cap_a], closed=True))
                deep = r_.get("height_deep_mm", r_["height_mm"])
                heights.append(deep)
                if length >= 20.0:
                    ang = float(np.degrees(np.arctan2(t[1], t[0])))
                    ang = ang - 180.0 if ang > 90.0 else ang + 180.0 if ang <= -90.0 else ang
                    ax.text(*(0.5 * (a + b)), f"{r_['width_mm']:.0f}×{deep:.0f}", fontsize=6.5, ha="center", va="center",
                            rotation=ang, rotation_mode="anchor", color="k")  # fmt: skip
            ax.text(*m_["centre_mm"], m_["id"] + (" (field)" if as_field else ""), fontsize=8, fontweight="bold", color="tab:red",
                    bbox={"facecolor": "white", "alpha": 0.75, "pad": 1, "lw": 0})  # fmt: skip
        ax.add_collection(PatchCollection(field_polys, facecolor="none", edgecolor="tab:red", linewidths=1.0, hatch="////", alpha=0.6))
        pc = PatchCollection(polys, cmap="viridis", edgecolor="k", linewidths=0.4)
        pc.set_array(np.asarray(heights, float))
        pc.set_clim(0.0, 40.0)
        ax.add_collection(pc)
        ax.set_title(f"{design} as a designer would draw it: the {half.replace('_', ' ')} from outside along its pull", fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(-210.0, 210.0)
        ax.set_ylim(-110.0, 310.0)
        ax.grid(True, color="0.9", lw=0.6)
    if pc is not None:
        fig.colorbar(pc, ax=axes, shrink=0.6, label="the run's deep height off the wall (mm)")
    fig.text(0.42, 0.14, "Coloured: ribs, webs and gussets, each straight run labelled width × deep height off the wall (mm). Hatched: arms and "
             "networks, drawn as the field has them (their depth varies). Blue: protected bosses and lugs. Pink: panel spokes.",
             ha="center", fontsize=9)  # fmt: skip
    fig.savefig(png, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(png)


def main(design: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.ndimage import label as cc_label
    from skimage.morphology import skeletonize

    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    run = rec["outcome_of"]
    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    s = layout["settings"]
    z = np.load(OUT / f"{run}.npz")
    n, lo, h, ks = z["n"].astype(int), z["lo"].astype(float), float(z["h"]), int(z["k_split"])
    extra = exact_walls.extra_placed(run)  # (n): the placed metal beyond each column's least height
    kz = np.arange(n[2])
    xs, ys = lo[0] + h * (np.arange(n[0]) + 0.5), lo[1] + h * (np.arange(n[1]) + 0.5)
    PX, PY = np.meshgrid(xs, ys, indexing="ij")
    out = {"design": design, "run": run, "voxel_mm": h, "halves": {}}
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    for ax, (half, lower) in zip(axes, (("cover", False), ("motor_side", True)), strict=True):
        side = "-z" if lower else "+z"
        in_half = (kz < ks) if lower else (kz >= ks)
        ext = (extra & in_half[None, None, :]).sum(axis=2) * h  # mm of metal beyond the least walls
        feats, prot, webs = [], np.zeros((n[0], n[1]), bool), []
        for b in layout["bearings"]:
            if b["side"] != side:
                continue
            r = np.hypot(PX - b["axis"][0], PY - b["axis"][1])
            prot |= r <= float(b["boss_r"]) + 2.0
            feats.append({"kind": "bearing boss", "of": f"{b['shaft']} {b['side']}", "centre_mm": [round(v, 1) for v in b["axis"]],
                          "diameter_mm": round(2 * float(b["boss_r"]), 1), "bore_mm": b["D"],
                          "z_mm": [round(b["z"][0] - s["wall"], 1), round(layout["z"]["split"], 1)] if lower else [round(layout["z"]["split"], 1), round(b["z"][1] + s["wall"], 1)]})  # fmt: skip
        for c in layout["bolts"]:
            prot |= np.hypot(PX - c[0], PY - c[1]) <= s["bolt_boss"] / 2 + 2.0
        feats.append({"kind": "bolt bosses", "count": len(layout["bolts"]), "diameter_mm": s["bolt_boss"], "thickness_mm": layout["flange"]["thickness"]})
        skin_ = rec.get("skin") or {}
        spokes = (skin_.get("panel_spokes_motor") if half == "motor_side" else None) or skin_.get("panel_spokes")
        if spokes and half in (rec.get("skin") or {}).get("spoke_halves", "cover,motor_side"):
            pitch_, thick_, high_ = (float(v) for v in spokes.split(":"))
            feats.append({"kind": "panel spokes", "of": f"every {pitch_:g}° from each boss to the rim", "thickness_mm": thick_, "height_mm": high_})
        feats.append({"kind": "sealing land", "width_mm": layout["flange"]["land_width"], "thickness_mm": layout["flange"]["thickness"]})
        if lower:
            for m in layout["mounts"]:
                prot |= np.hypot(PX - m["centre"][0], PY - m["centre"][1]) <= s["mount_diameter"] / 2 + 2.0
                feats.append({"kind": "mount lug", "of": m["name"], "centre_mm": [round(v, 1) for v in m["centre"]], "diameter_mm": s["mount_diameter"],
                              "z_mm": [round(v, 1) for v in m["z"]]})  # fmt: skip
            webs = _lug_webs(rec, layout)
            for w in webs:
                prot |= exact_walls.seg_plan_dist(PX, PY, w["from"], w["to"]) <= w["thickness"] / 2 + 2.0
            if webs:
                feats.append({"kind": "lug webs", "of": "two from each lug to its room's wall, from the lug's far end to the split",
                              "thickness_mm": webs[0]["thickness"], "ends_mm": "; ".join(f"{w['mount']} → [{w['to'][0]:.1f}, {w['to'][1]:.1f}]" for w in webs)})  # fmt: skip
        foot = (ext >= PROUD) & ~prot
        lab, n_lab = cc_label(foot, np.ones((3, 3), int))
        for k in range(1, n_lab + 1):
            if (lab == k).sum() < CRUMB:
                foot[lab == k] = False
        skel = sk.prune(skeletonize(foot), PRUNE / h)
        ends_targets = [(f["of"], np.asarray(f["centre_mm"]), f["diameter_mm"] / 2) for f in feats if "centre_mm" in f]
        bolts_xy = np.asarray(layout["bolts"], float)
        members = []
        lab, n_lab = cc_label(foot, np.ones((3, 3), int))
        for k in range(1, n_lab + 1):  # each connected member one entry: its main direction, length, width and height
            comp = lab == k
            cells = np.argwhere(comp)
            xy = lo[:2][None, :] + h * (cells + 0.5)
            area = len(cells) * h * h
            centre = xy.mean(axis=0)
            evals, evecs = np.linalg.eigh(np.cov((xy - centre).T) + 1e-9 * np.eye(2))
            u = evecs[:, -1]
            proj = (xy - centre) @ u
            length = float(proj.max() - proj.min()) + h
            width = area / length
            hts = ext[comp]
            sk_c = skel & comp
            branches, deg = sk.skeleton_graph(sk_c)
            n_ends = int(((deg == 1) & sk_c).sum())
            touches = [name for name, c, r in ends_targets if np.min(np.hypot(xy[:, 0] - c[0], xy[:, 1] - c[1])) <= r + TOUCH]
            if len(bolts_xy) and np.min(np.hypot(xy[:, None, 0] - bolts_xy[None, :, 0], xy[:, None, 1] - bolts_xy[None, :, 1])) <= s["bolt_boss"] / 2 + TOUCH:
                touches.append("bolts' bosses")
            off = np.abs((xy - centre) @ np.array([-u[1], u[0]]))
            straight = bool(np.percentile(off, 90) <= max(3.0, 0.75 * width))
            if any(t_.startswith("mount") for t_ in touches):
                kind = "arm"
            elif n_ends > 2:
                kind = "network"
            elif width > RIB_W:
                kind = "web"
            elif length < 25.0:
                kind = "gusset"
            elif length >= 2.5 * width:
                kind = "rib"
            else:
                kind = "web"
            paths = [[[round(float(lo[0] + h * (c_[0] + 0.5)), 1), round(float(lo[1] + h * (c_[1] + 0.5)), 1)] for c_ in br] for br in branches if len(br) >= 2]
            runs = runs_of(paths, xy, hts, h, (centre + proj.min() * u, centre + proj.max() * u))
            met = [t_ for t_ in ends_targets + [("bolt", np.asarray(c, float), s["bolt_boss"] / 2) for c in layout["bolts"]]
                   if np.min(np.hypot(xy[:, 0] - t_[1][0], xy[:, 1] - t_[1][1])) <= t_[2] + TOUCH]  # fmt: skip
            runs = snap_runs(runs, met)
            members.append({"runs": runs, "cells_ij": cells.tolist(),"id": f"{'C' if half == 'cover' else 'M'}{len(members) + 1}", "kind": kind, "centre_mm": [round(float(v), 1) for v in centre],
                            "from_mm": [round(float(v), 1) for v in centre + proj.min() * u], "to_mm": [round(float(v), 1) for v in centre + proj.max() * u],
                            "length_mm": round(float(length), 1), "width_mm": round(float(width), 1), "area_cm2": round(float(area) / 100.0, 1),
                            "height_mm": round(float(np.median(hts)), 1), "height_most_mm": round(float(hts.max()), 1),
                            "shape": ("straight" if straight else "curved") if n_ends <= 2 else f"branched ({n_ends} ends)",
                            "meets": touches or ["the wall"], "angle_deg": round(float(np.degrees(np.arctan2(u[1], u[0]))) % 180.0, 0),
                            "paths_mm": paths})  # fmt: skip
        out["halves"][half] = {"features": feats, "members": members, "member_area_cm2": round(float(foot.sum()) * h * h / 100.0, 1),
                               "lug_webs": [{"from": w["from"], "to": w["to"], "thickness": w["thickness"]} for w in webs]}  # fmt: skip
        # the picture: the members' metal off the wall, the features, the members numbered
        shown = np.where(ext > 0, ext, np.nan)
        im = ax.imshow(shown.T, origin="lower", extent=[xs[0] - h / 2, xs[-1] + h / 2, ys[0] - h / 2, ys[-1] + h / 2], cmap="Greys", vmin=0, vmax=40, alpha=0.6)
        for f in feats:
            if "centre_mm" in f:
                ax.add_patch(plt.Circle(f["centre_mm"], f["diameter_mm"] / 2, fill=False, color="tab:blue", lw=1.5))
                ax.text(f["centre_mm"][0], f["centre_mm"][1], f"{f['of']}\nØ{f['diameter_mm']:g}", color="tab:blue", fontsize=8, ha="center", va="center")
        for c in layout["bolts"]:
            ax.add_patch(plt.Circle(c, s["bolt_boss"] / 2, fill=False, color="tab:cyan", lw=1))
        _draw_spokes(ax, layout, feats, half)
        for w in out["halves"][half].get("lug_webs", []):  # the fixed lug webs, as the bosses: protected
            ax.plot([w["from"][0], w["to"][0]], [w["from"][1], w["to"][1]], color="tab:blue", lw=3.0, solid_capstyle="round")
        for m_ in members:
            for path in m_["paths_mm"]:
                p_ = np.asarray(path)
                ax.plot(p_[:, 0], p_[:, 1], color=COLOURS[m_["kind"]], lw=2.5)
            if not m_["paths_mm"]:
                p_ = np.asarray([m_["from_mm"], m_["to_mm"]])
                ax.plot(p_[:, 0], p_[:, 1], color=COLOURS[m_["kind"]], lw=2.5)
            ax.text(*m_["centre_mm"], m_["id"], fontsize=8, color="k", bbox={"facecolor": "white", "alpha": 0.7, "pad": 1, "lw": 0})
        ax.set_title(f"{design}: the {half.replace('_', ' ')} from outside along the pull (grey: metal beyond the 4 mm wall, mm)", fontsize=10)
        ax.set_aspect("equal")
    for kind, colour in COLOURS.items():
        axes[1].plot([], [], color=colour, lw=2.5, label=kind)
    axes[1].plot([], [], color="tab:blue", lw=1.5, label="bearing boss (protected)")
    axes[1].plot([], [], color="tab:pink", lw=1.6, ls="--", label="panel spoke (protected)")
    axes[1].legend(loc="lower right", fontsize=9)
    fig.colorbar(im, ax=axes, shrink=0.6, label="metal beyond the least wall (mm)")
    png = OUT / f"member_map_{design}.png"
    fig.savefig(png, dpi=80, bbox_inches="tight")
    plt.close(fig)
    reading(design, out, layout, OUT / f"member_reading_{design}.png")
    (OUT / f"member_map_{design}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = [f"# {design}: features and members", "", f"From the run `{run}` ({h:g} mm columns).", ""]
    for half, d in out["halves"].items():
        lines += [f"## The {half.replace('_', ' ')}", "", "| Feature | Of | Where (mm) | Size (mm) |", "|---|---|---|---|"]
        for f in d["features"]:
            where = f.get("centre_mm", "")
            size = ", ".join(f"{k.replace('_mm', '')} {v}" for k, v in f.items() if k.endswith("_mm") and k != "centre_mm")
            lines.append(f"| {f['kind']} | {f.get('of', f.get('count', ''))} | {where} | {size} |")
        lines += ["", "| Member | Kind | Along (mm, from → to) | Length | Width | Height off the wall (median / most) | Shape | Meets |", "|---|---|---|---|---|---|---|---|"]
        for m_ in d["members"]:
            lines.append(f"| {m_['id']} | {m_['kind']} | {m_['from_mm']} → {m_['to_mm']} | {m_['length_mm']} | {m_['width_mm']} | {m_['height_mm']} / {m_['height_most_mm']} | {m_['shape']} | {' and '.join(m_['meets'])} |")
        lines += ["", "The designer's reading: each member's straight runs (`runs_of`), with each run's width and heights off the wall. "
                  "Draw a rib's, a web's or a gusset's run at its deep height; an arm or a network as the field has it.", "",
                  "| Member | Draw | Run | From (mm) | To (mm) | Length | Width | Deep height | Height at its start / middle / end |",
                  "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for m_ in d["members"]:
            how = "as the field" if m_["kind"] in AS_FIELD else "straight, deep height"
            for j, r_ in enumerate(m_["runs"], 1):
                lines.append(f"| {m_['id']} | {how} | {j} | {r_['from_mm']} | {r_['to_mm']} | {r_['length_mm']} | {r_['width_mm']} | "
                             f"{r_.get('height_deep_mm', '')} | {r_['height_from_mm']} / {r_['height_mm']} / {r_['height_to_mm']} |")  # fmt: skip
        lines.append("")
    (OUT / f"member_map_{design}.md").write_text("\n".join(lines), encoding="utf-8")
    for half, d in out["halves"].items():
        kinds = {}
        for m_ in d["members"]:
            kinds[m_["kind"]] = kinds.get(m_["kind"], 0) + 1
        print(f"{half}: {len(d['members'])} members {kinds}, {d['member_area_cm2']} cm² of plan beyond the walls")
    print(png)


if __name__ == "__main__":
    main(sys.argv[1])
