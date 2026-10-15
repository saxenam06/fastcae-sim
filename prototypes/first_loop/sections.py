"""The design space sectioned cleanly by the housing's own geometry (LOP-24, approach 1 as the engineer meant it,
12 October 01:34: "some nice areas, regions, sections around bores, around shafts, around gears... it's all
around the gearbox... how do we section that properly"; a UTV gearbox housing's design domains as the example).

The shell is the contract's rooms (`cup.pieces`: each gear's and each bore's room a cylinder along the shafts,
from its far end to the split, with the wall round it and past its end). Every free voxel of the band belongs to
the room whose outside it is nearest, on the face it faces: **the end** of that room (beyond its end wall) or
**the side** of it (beside its wall); a voxel beyond an end wall within a bearing's boss radius belongs to that
bearing's **boss**; a voxel nearer a mount's lug than any room's outside, by more than the band, to that
**mount's zone**. So the sections are discs and rings on the end walls and bands round the cylinders, all round
the shell. Each column of the height field takes its voxels' section (the most of them).

The free run's flow then says which sections carry its metal (printed, and in the record). For the optimiser,
`<label>_cols.npz` gives each column its section with one height for the whole section (`topo_free.py
--height-volumes <label>_cols.npz`): each section a form of its own, so that metal cannot smear across it.

    sections.py <run> --label <label> [--least 40]

Writes data/first_loop/<label>.json (the sections: each one's name, kind, room, half, columns, voxels and the
run's metal in it), <label>_cols.npz, <label>_cells.npz (each grid cell's section, for the pictures and the
Campaigns page) and <label>.png (each half from outside: the sections, the run's metal over them)."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
import cup as cupmod  # noqa: E402
import regions as rg  # noqa: E402
import shell as convex  # noqa: E402
import topo  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402

OUT = HERE.parents[1] / "data" / "first_loop"
NAMES = {"gear": "room", "bore": "bore"}


def main(run: str, label: str, least: int) -> dict:
    ctx = rg.context(run)
    info, n, lo, h, ks, kind, xyz, metal = ctx["info"], ctx["n"], ctx["lo"], ctx["h"], ctx["ks"], ctx["kind"], ctx["xyz"], ctx["metal"]
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    wall, z_split, band = float(lay["settings"]["wall"]), float(lay["z"]["split"]), 24.0
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial, axial = value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm")
    all_rooms = cupmod.rooms(chain, radial, axial)
    free = np.flatnonzero(kind == 0)
    fx, fy, fz = xyz[free, 0], xyz[free, 1], xyz[free, 2]
    sec_of = np.full(len(free), -1, np.int64)
    sections = []
    for half in ("motor_side", "cover"):
        lower = half == "motor_side"
        here = (fz < z_split) if lower else (fz >= z_split)
        idx = np.flatnonzero(here)
        px, py, pz = fx[idx], fy[idx], fz[idx]
        pieces = cupmod.pieces(all_rooms, z_split, half)
        best = np.full(len(idx), np.inf)
        which = np.full(len(idx), -1)
        face = np.zeros(len(idx), bool)  # True: beyond the end, False: beside the side
        for k, p in enumerate(pieces):
            r_out = float(p["r"]) + wall
            z_end = float(p["far"]) - wall if lower else float(p["far"]) + wall
            d = np.hypot(px - p["axis"][0], py - p["axis"][1])
            dr = np.maximum(d - r_out, 0.0)
            dz = np.maximum(z_end - pz, 0.0) if lower else np.maximum(pz - z_end, 0.0)
            dist = np.hypot(dr, dz)
            better = dist < best
            best[better] = dist[better]
            which[better] = k
            face[better] = (dz > dr)[better]
        # each (room, face) a section; then the bosses over the end walls and the mounts' zones take theirs
        keys = {}
        for k, p in enumerate(pieces):
            for f_, word in ((True, "the end"), (False, "the side")):
                sel = (which == k) & (face == f_)
                if not sel.any():
                    continue
                room = p.get("name") or f"{p['shaft']} {p['kind']} r{p['r']:.0f}"
                keys[(k, f_)] = len(sections)
                sections.append({"id": len(sections), "half": half, "kind": "end" if f_ else "side", "room": room,
                                 "name": f"{'Cover' if half == 'cover' else 'Motor side'}: {word} of the {p['shaft']} shaft's {NAMES.get(p['kind'], p['kind'])} (r {p['r']:.0f})",
                                 "axis": list(p["axis"]), "r": float(p["r"])})  # fmt: skip
                sec_of[idx[sel]] = keys[(k, f_)]
        side = "+z" if half == "cover" else "-z"
        for b in (b for b in info["bearings"] if b["side"] == side):
            d = np.hypot(px - b["axis"][0], py - b["axis"][1])
            sel = (d <= float(b["boss_r"])) & face
            if sel.any():
                sections.append({"id": len(sections), "half": half, "kind": "boss", "room": f"{b['shaft']} bearing",
                                 "name": f"{'Cover' if half == 'cover' else 'Motor side'}: the boss of the {b['shaft']} bore", "axis": list(b["axis"]),
                                 "r": float(b["boss_r"])})  # fmt: skip
                sec_of[idx[sel]] = len(sections) - 1
        if lower:
            for m in info["mounts"]:
                d = np.hypot(px - m["centre"][0], py - m["centre"][1])
                sel = best > band + h
                sel &= d <= np.min([np.hypot(px - mm["centre"][0], py - mm["centre"][1]) for mm in info["mounts"]], axis=0) + 1e-9
                if sel.any():
                    sections.append({"id": len(sections), "half": half, "kind": "mount", "room": m["name"],
                                     "name": f"Motor side: {m['name']}'s zone", "axis": list(m["centre"]), "r": 0.0})  # fmt: skip
                    sec_of[idx[sel]] = len(sections) - 1
    # small sections folded into their nearest neighbour of the same half
    counts = np.bincount(sec_of[sec_of >= 0], minlength=len(sections))
    keep = counts >= least
    if not keep.all():
        from scipy.spatial import cKDTree

        big = np.flatnonzero(keep[np.maximum(sec_of, 0)] & (sec_of >= 0))
        tree = cKDTree(np.column_stack([fx[big], fy[big], fz[big]]))
        small = np.flatnonzero((sec_of >= 0) & ~keep[np.maximum(sec_of, 0)])
        if len(small):
            _, j = tree.query(np.column_stack([fx[small], fy[small], fz[small]]))
            sec_of[small] = sec_of[big[j]]
    used = np.unique(sec_of[sec_of >= 0])
    renum = {int(o): i for i, o in enumerate(used)}
    sections = [dict(sections[int(o)], id=renum[int(o)]) for o in used]
    sec_of = np.array([renum.get(int(s), -1) for s in sec_of])
    cell = np.full(len(kind), -1, np.int64)
    cell[free] = sec_of
    # each column's section: the most of its voxels'
    model = ctx["model"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], elem, free_e)
    vox_sec = cell[elem[free_e]]
    n_cols = len(pts)
    votes = np.zeros((n_cols, len(sections)), np.int32)
    np.add.at(votes, (col, vox_sec), 1)
    vol_of_col = np.where(votes.sum(axis=1) > 0, votes.argmax(axis=1), -1)
    np.savez_compressed(OUT / f"{label}_cols.npz", vol_of_col=vol_of_col.astype(np.int32), law=np.zeros(len(sections), np.int8),
                        s_of_col=np.zeros(n_cols, np.float32))  # fmt: skip
    np.savez_compressed(OUT / f"{label}_cells.npz", label=cell.reshape(n).astype(np.int16), lo=lo, n=np.asarray(n), h=h)
    total = max(int(metal.sum()), 1)
    for s in sections:
        sel = cell == s["id"]
        s["voxels"] = int(sel.sum())
        s["columns"] = int((vol_of_col == s["id"]).sum())
        s["metal_share"] = float((sel & metal).sum() / total)
        s["fill"] = float((sel & metal).sum() / max(int(sel.sum()), 1))
    sections.sort(key=lambda s: s["id"])
    out = {"label": label, "run": run, "sections": sections, "n_cols": n_cols}
    (OUT / f"{label}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for s in sorted(sections, key=lambda s: -s["metal_share"]):
        print(f"  {s['name']:<62} {s['kind']:<5} {s['voxels']:6,} voxels, {s['columns']:5,} columns; the run's metal {100 * s['metal_share']:4.1f} % "
              f"(it fills {100 * s['fill']:3.0f} %)")  # fmt: skip
    print(f"{len(sections)} sections; every free voxel in one")
    picture(label, cell.reshape(n), metal.reshape(n), lo, h, ks, info, sections)
    return out


def picture(label, cell, metal, lo, h, ks, info, sections):
    """Each half from outside along the pull: the topmost section of each column, the run's metal dotted."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    cmap = plt.get_cmap("tab20")
    for ax, (half, sl) in zip(axes, (("motor_side", slice(0, ks)), ("cover", slice(ks, None)))):
        c = cell[:, :, sl]
        # seen from outside: the motor side from -z (its lowest cells first), the cover from +z
        order = range(c.shape[2]) if half == "motor_side" else range(c.shape[2] - 1, -1, -1)
        top = np.full(c.shape[:2], -1)
        for k in order:
            put = (top < 0) & (c[:, :, k] >= 0)
            top[put] = c[:, :, k][put]
        rgb = np.ones(top.shape + (3,))
        for s in sections:
            if s["half"] == half:
                tint = np.asarray(cmap(s["id"] % 20)[:3])
                rgb[top == s["id"]] = tint * 0.6 + 0.4
        ex = [lo[0], lo[0] + h * c.shape[0], lo[1], lo[1] + h * c.shape[1]]
        ax.imshow(np.transpose(rgb, (1, 0, 2)), origin="lower", extent=ex, interpolation="nearest")
        my, mx = np.nonzero(metal[:, :, sl].any(axis=2).T)
        ax.scatter(lo[0] + h * (mx + 0.5), lo[1] + h * (my + 0.5), s=0.6, c="k", alpha=0.25, linewidths=0)
        for s in sections:
            if s["half"] == half and s["kind"] in ("boss", "end", "mount") and s["metal_share"] >= 0.01:
                sel = top == s["id"]
                if sel.any():
                    ii, jj = np.nonzero(sel)
                    ax.text(lo[0] + h * (ii.mean() + 0.5), lo[1] + h * (jj.mean() + 0.5), f"{s['id']}", fontsize=7, ha="center")
        ax.set_aspect("equal")
        ax.set_title(f"{half} from outside: its sections (a colour each, numbered), the run's metal (dots)", fontsize=8)
    fig.suptitle(f"{label}: the design space sectioned by the housing's own geometry")
    fig.savefig(OUT / f"{label}.png", dpi=110, bbox_inches="tight")
    print(OUT / f"{label}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run")
    ap.add_argument("--label", required=True)
    ap.add_argument("--least", type=int, default=40, help="voxels: a smaller section is folded into its nearest neighbour")
    a = ap.parse_args()
    main(a.run, a.label, a.least)
