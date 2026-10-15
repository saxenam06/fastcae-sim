"""A campaign's moves for the Campaigns page (LOP-24; the engineer, 11 October 21:37: "I want to see your
decisions on the UI for each iteration: what design space you considered and what was the result, if
the design space was changed in that iteration... later the same can be used to analyse the runtime
agent"). As fastcae's Optimize tab showed an agent's iterations (fastcae-v1:ui/src/optimize/Optimize.tsx):
each move with what it saw, what it decided and why, its settings and what changed, the levers not
pulled, its design space (and whether it changed), its results by the optimiser's own check and by FE,
its verdict and the next move; who decided each.

The source is the campaign's decision log, data/first_loop/agent/<campaign>.json (the agent writes it,
move by move; the runtime agent will write the same). No number is copied by hand: each result's
model numbers come from its run's record (the metal-or-air check, read against the true lines: the
optimiser held them at 1/safety), its FE numbers from the grades (`grades.json`). Each design space's
regions are inlined for the page to draw; the housing's context (each half's inside in plan, the bores,
the bolts, the mounts) once. Pictures are copied as thumbnails.

    campaign_export.py <campaign>   →  web/src/records/campaigns/<campaign>.json (+ thumbnails)"""

import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scipy import ndimage as ndi  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "first_loop"
WEB = ROOT / "web" / "src" / "records" / "campaigns"
BEDS_UM = 52.2  # the reference's beds (grade.REFERENCE, peak drive)


def thumb(src: Path, dst: Path, width: int = 720) -> bool:
    if not src.exists():
        return False
    try:
        from PIL import Image

        im = Image.open(src)
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(dst, optimize=True)
    except Exception:  # noqa: BLE001 - a picture that will not shrink is copied as it is
        shutil.copyfile(src, dst)
    return True


def model_of(run: str) -> dict | None:
    p = OUT / f"{run}.json"
    if not p.exists():
        return None
    rec = json.loads(p.read_text(encoding="utf-8"))
    b = rec.get("binary") or {}
    if not b:
        return {"done": False}
    sf = float(rec.get("safety") or 1.0)
    sfb = float(rec.get("safety_beds") or sf)
    z = OUT / f"{run}.npz"
    free = int(len(np.load(z)["free_e"])) if z.exists() else None
    return {
        "done": True,
        "kg": float(b["mass_kg"]) + float(rec.get("frozen_kg") or 0.0),
        "tilt": float(b["worst"]) / sf,
        "beds_um": float(b["bed_worst"]) * BEDS_UM / sfb if b.get("bed_worst") is not None else None,
        "safety": sf,
        "safety_beds": sfb,
        "objective": rec.get("objective"),
        "seconds": rec.get("seconds"),
        "free_voxels": free,
    }


def fe_of(design: str, grades: dict) -> dict | None:
    g = grades.get(design)
    if not g:
        return None
    L = g["lines"]
    return {
        "kg": g["mass_kg"],
        "beds_um": L["displacement, peak drive"]["value_um"],
        "beds_ok": L["displacement, peak drive"]["pass"],
        "tilt": L["misalignment (worst seat against its line)"]["ratio"],
        "tilt_ok": L["misalignment (worst seat against its line)"]["pass"],
        "first_hz": g.get("first_mode_hz"),
        "clashes": L["orders"]["clashes"],
        "orders_ok": L["orders"]["pass"],
        "mass_ok": L["mass"]["pass"],
        "pass": g["pass"],
    }


def context(lay: dict) -> dict:
    """Each half's inside in plan (the shell's footprint), the bores, the bolts, the mounts."""
    import topo_free as tf
    from space_from_runs import polygons_of

    model = tf.build_free(4.0, band=24.0, flange=True, route="split", mount_reach="disc")
    n, lo, ks = model["n"], model["lo"], model["k_split"]
    rooms = np.asarray(model["masks"]["rooms"]).reshape(tuple(n))
    out = {"halves": {}}
    for half, sl in (("motor_side", slice(0, ks)), ("cover", slice(ks, None))):
        inside = ndi.zoom(rooms[:, :, sl].any(axis=2).astype(float), 4.0, order=1) > 0.5
        out["halves"][half] = [p["outline"] for p in polygons_of(inside, float(lo[0]), float(lo[1]), 1.5)]
    out["bores"] = [{"shaft": b["shaft"], "side": b["side"], "axis": b["axis"], "r": b["D"] / 2.0, "boss_r": b["boss_r"]} for b in lay["bearings"]]
    out["bolts"] = lay["bolts"]
    out["mounts"] = [{"name": m["name"], "centre": m["centre"], "r": 0.5 * float(lay["settings"].get("mount_diameter", 36.0))} for m in lay["mounts"]]
    xs = np.concatenate([np.asarray(p)[:, 0] for h in out["halves"].values() for p in h] + [np.asarray([m["centre"][0] for m in out["mounts"]])])
    ys = np.concatenate([np.asarray(p)[:, 1] for h in out["halves"].values() for p in h] + [np.asarray([m["centre"][1] for m in out["mounts"]])])
    out["box"] = [float(xs.min()) - 30, float(ys.min()) - 30, float(xs.max()) + 30, float(ys.max()) + 30]
    return out


def feature_space(features: str, run: str | None) -> tuple[dict, dict]:
    """A `--height-features` file's features as plan regions per half (each feature's own columns, as
    `topo.feature_map` gives them) and, once its run is done, each one's fill: the share of its columns
    holding a member (MEMBER_MM or more high) and their mean height. The bore experiment (LOP-24)."""
    import scipy.sparse as sps
    from scipy.spatial import cKDTree
    from space_from_runs import polygons_of

    import topo
    import topo_free as tf

    spec = json.loads((OUT / features).read_text(encoding="utf-8"))
    if run and (OUT / f"{run}.json").exists():  # the model the run was made on, rebuilt from its record
        rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
        skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
        model = tf.build_free(4.0, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                              route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                              height_field=rec["height_field"]["radius_mm"])  # fmt: skip
    else:
        model = tf.build_free(4.0, band=24.0, flange=True, route="split", mount_reach="disc", height_field=6.0)
    kind, n, h, lo = model["kind"], model["n"], model["h"], model["lo"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, n, model["k_split"], elem, free_e)
    radius = 6.0 / h
    plan = np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]])
    tree = cKDTree(plan)
    pp = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    fmat = (sps.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(len(pts), len(pts))).tocsr() + sps.eye(len(pts)) * radius).tocsr()
    _, _, feat = topo.feature_map(spec, model["info"], pts, layer, lo, h, fmat, len(pts))
    heights = None
    if run and (OUT / f"{run}.npz").exists():
        import smooth_heights as shh

        heights = shh.column_heights(run)
    half, base = spec["half"], 1 if spec["half"] == "motor_side" else 10_001
    sel = layer == base
    room = np.bincount(col, minlength=len(pts)) * h  # mm: each column's free voxels
    regions, fill = {half: []}, {}

    def outline(m, name: str, kind: str | None = None) -> None:
        cells = np.zeros((n[0], n[1]))
        cells[pts[m, 0].astype(int), pts[m, 1].astype(int)] = 1.0
        mask = ndi.zoom(cells, h, order=1) > 0.5
        for p in polygons_of(mask, float(lo[0]), float(lo[1]), 1.0):
            regions[half].append({"name": name, "outline": p["outline"], "holes": p.get("holes", []), **({"kind": kind} if kind else {})})

    empty = sel & feat["region"] & (feat["owner"] < 0)
    if empty.any():
        outline(empty, "the region's rest", "empty")
    for k, f in enumerate(feat["features"]):
        m = sel & (feat["owner"] == k)
        if not m.any():
            continue
        outline(m, f["name"], "free" if f.get("free") else "feature")
        ii, jj = pts[m, 0].astype(int), pts[m, 1].astype(int)
        if heights is not None:  # each column's height, at most its own free voxels (the band)
            t = np.minimum(heights[half][ii, jj], room[m])
            held = t >= MEMBER_MM
            fill[f"{half}|{f['name']}"] = {"covered": float(held.mean()), "volume": float(held.mean()), "height_mm": float(t[held].mean()) if held.any() else 0.0}
    return regions, fill


MEMBER_MM = 4.0  # a column this high off its base holds a member (bore_spill.MEMBER)
WEB3D = WEB / "space3d"
# Each 3D layer's look: (label, kind, colour, alpha, note)
LOOK3D = {
    "fixed": ("Held fixed", "fixed", (0.70, 0.72, 0.76), 0.35, "the wall, the seats, the split flange and the mounts: metal the optimiser holds"),
    "space": ("Free", "free", (0.18, 0.62, 0.42), 0.16, "where the optimiser may place metal"),
    "volumes": ("The area's volumes", "free", (0.20, 0.45, 0.85), 0.55, "the regular volumes round the area: free inside"),
    "features": ("Features", "fixed", (0.95, 0.70, 0.10), 0.75, "standard features: their sizes the optimiser's"),
    "empty": ("Held empty", "kept_out", (0.45, 0.45, 0.50), 0.25, "the area's rest, held empty"),
    "metal": ("Metal placed", "fixed", (0.80, 0.42, 0.22), 0.30, "the run's metal (its densities at 0.5), seen through"),
    "region_boss": ("Bosses", "free", (0.20, 0.45, 0.85), 0.45, "a region on each bore's boss: its seat's wall out to the boss radius"),
    "region_strip": ("Strips", "free", (0.25, 0.70, 0.55), 0.40, "regions along the shell between two hard points (bores, flange bolts)"),
    "region_wedge": ("Wedges to the mounts", "free", (0.85, 0.65, 0.20), 0.45, "regions along the shell from a mount's lug to a bore or a bolt"),
}


VIEW = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])  # the viewer's frame (zenryx.api.volumes.VIEW)


def volume_mesh(mask: np.ndarray, lo: np.ndarray, h: float, step: int = 1) -> str | None:
    """A cell mask drawn as a volume, not voxels (the engineer, 12 October 01:02): its surface by marching cubes
    of the mask blurred over a voxel (smooth, no steps), in the viewer's frame, packed as the Contract page's
    meshes are (FCMESH03, `zenryx.api.mesh.encode`)."""
    import base64

    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes

    sys.path.insert(0, str(ROOT / "src"))
    from zenryx.api.mesh import encode

    if not mask.any():
        return None
    vol = gaussian_filter(np.pad(mask.astype(np.float32), 2), 0.8)
    verts, faces, normals, _ = marching_cubes(vol, 0.5, spacing=(h, h, h), step_size=step)
    verts = verts + lo - 1.5 * h  # padded index p is the cell p - 2, its centre lo + h (p - 2 + 0.5)
    v = verts @ VIEW.T
    nrm = -(normals @ VIEW.T)
    corner = nrm[faces].reshape(-1, 3)
    corner /= np.maximum(np.linalg.norm(corner, axis=1, keepdims=True), 1e-9)
    packed = encode(v.astype(np.float32), faces.astype(np.int64), np.zeros(len(faces), np.int64), normals=corner)
    return base64.b64encode(packed).decode("ascii")


def space3d(campaign: str, moves: list) -> Path | None:
    """Each move's design space in 3D (the engineer, 12 October 00:04: "I want to see design spaces in
    3D on UI and each iteration on UI"), on the run's own voxels as the Contract page's voxel layers
    (`setup_export.faces_of`, `turned`): the metal held fixed (once); for each move with a run, where
    the optimiser may place metal, for a move on one area its regular volumes, its features and what
    it holds empty, and the metal the run placed. A layer is kept once and named by its key; each move
    lists its own. Writes web/src/records/campaigns/space3d/<campaign>.json, which the page loads when
    its 3D view opens."""
    import hashlib

    import scipy.sparse as sps
    from scipy.spatial import cKDTree

    import topo
    import topo_free as tf

    layers, per_move, grid, context, focus = {}, {}, None, [], {}

    def keep(mask: np.ndarray, h: float, lo: np.ndarray, step: int = 1) -> tuple[str, int]:
        key = hashlib.sha1(np.packbits(mask).tobytes()).hexdigest()[:12]
        if key not in layers:  # drawn as a volume: a smooth surface (`volume_mesh`), not voxels
            layers[key] = {"mesh": volume_mesh(mask, lo, h, step), "cells": int(mask.sum()), "litres": round(float(mask.sum()) * h**3 / 1e6, 3)}
        return key, layers[key]["cells"]

    def region_rows(space: str, n, lo, h, free_cells: np.ndarray | None) -> list:
        """The regions from the hard points (`regions.py`), a layer a kind, on the cells the run holds free."""
        p = OUT / space
        if not p.exists() or not p.with_suffix(".json").exists():
            return []
        lab = np.load(p)["label"]
        cands = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))["candidates"]
        out_rows = []
        for k_ in ("boss", "strip", "wedge"):
            ids = [c["id"] for c in cands if c["kind"] == k_ and c["chosen"]]
            mask = np.isin(lab, ids)
            if free_cells is not None:
                mask &= free_cells
            if mask.any():
                out_rows.append(entry(f"region_{k_}", *keep(mask, h, lo)))
        return out_rows

    def entry(lid: str, key: str, cells: int) -> dict:
        label, kind, colour, alpha, note = LOOK3D[lid]
        return {"id": lid, "key": key, "label": label, "kind": kind, "colour": colour, "alpha": alpha, "cells": cells, "note": note}

    palette = [(0.20, 0.45, 0.85), (0.85, 0.30, 0.25), (0.25, 0.65, 0.40), (0.85, 0.65, 0.15), (0.55, 0.35, 0.75), (0.15, 0.65, 0.70)]
    kinds = {"ring": ("Rings (the bosses)", (0.15, 0.45, 0.25)), "rib": ("Ribs along the flow", (0.85, 0.35, 0.15)),
             "spoke": ("Spokes", (0.85, 0.35, 0.15)), "fin": ("Fins", (0.20, 0.55, 0.80)), "arm": ("Arms to the mounts", (0.85, 0.65, 0.10)),
             "rest": ("Each section's thickness", (0.60, 0.62, 0.66)), "end": ("Sections: the end faces", (0.30, 0.50, 0.85)),
             "side": ("Sections: beside the side walls", (0.25, 0.65, 0.45)), "boss": ("Sections: the bosses", (0.15, 0.45, 0.25)),
             "mount": ("Sections: the mounts' zones", (0.85, 0.65, 0.10)),
             "bridge": ("Bridges between the seats", (0.95, 0.55, 0.20)), "web": ("The web between three seats", (0.95, 0.80, 0.30)),
             "belt": ("The belt along the split", (0.30, 0.70, 0.75)), "lug": ("The mounts' lugs", (0.55, 0.40, 0.20)),
             "gusset": ("Gussets beside the side walls", (0.20, 0.35, 0.85))}  # fmt: skip

    def volume_rows(run: str, hv: str, n, lo, h, elem, free_e) -> list:
        """The design space's volumes (`topo.volume_map`), a layer a kind: the run's free voxels in their columns."""
        p = OUT / hv
        meta = OUT / f"{Path(hv).stem.removesuffix('_cols')}.json"
        if not p.exists() or not meta.exists():
            return []
        items = json.loads(meta.read_text(encoding="utf-8"))
        items = items.get("volumes") or items.get("sections") or []
        z_ = np.load(p)
        vol_of_col = z_["layout_of_col"] if "layout_of_col" in z_.files else z_["vol_of_col"]  # the forms, free or sized
        rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
        skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
        model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                              route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                              height_field=rec["height_field"]["radius_mm"], space=rec.get("space") or "")  # fmt: skip
        m_elem = np.flatnonzero(model["kind"] >= 0)
        m_free = np.flatnonzero(model["kind"][m_elem] == 0)
        if len(m_free) != len(free_e):
            return []
        col = topo.height_columns(model["kind"], model["n"], model["k_split"], m_elem, m_free)[0]
        vol_of_vox = vol_of_col[col]
        kind_of = np.array([it.get("kind", "rest") for it in items] + ["none"])
        out_rows = []
        for k_, (label_, colour) in kinds.items():
            sel = (vol_of_vox >= 0) & (kind_of[np.where(vol_of_vox >= 0, vol_of_vox, len(items))] == k_)
            if not sel.any():
                continue
            mask = np.zeros(n, bool)
            mask.flat[elem[free_e[sel]]] = True
            key, cells = keep(mask, h, lo)
            out_rows.append({"id": f"volumes_{k_}", "key": key, "kind": "free", "cells": cells, "label": label_, "colour": colour,
                             "alpha": 0.45, "note": f"{int(sum(1 for it in items if it.get('kind') == k_))} volumes, each its own form"})  # fmt: skip
        return out_rows

    def domain_rows(space: str, n, lo, h, free_flat: np.ndarray, split_k: int) -> list:
        """Each design domain (`domains_from_flow.py`) a layer of its own colour: the run's free cells under it."""
        from matplotlib.path import Path as MPath

        spec = json.loads((OUT / space).read_text(encoding="utf-8"))
        ijk = np.stack(np.unravel_index(free_flat, n), axis=1)
        xy = lo[:2] + h * (ijk[:, :2] + 0.5)
        out_rows, c = [], 0
        for half, regs in spec.get("halves", {}).items():
            on = ijk[:, 2] >= split_k if half == "cover" else ijk[:, 2] < split_k
            for r_ in regs:
                inside = MPath(np.asarray(r_["outline"], float)).contains_points(xy) & on
                for hole in r_.get("holes", []):
                    inside &= ~MPath(np.asarray(hole, float)).contains_points(xy)
                if not inside.any():
                    continue
                mask = np.zeros(n, bool)
                mask.flat[free_flat[inside]] = True
                key, cells = keep(mask, h, lo)
                where = ", ".join(r_.get("touches", [])) or "no hard point"
                out_rows.append({"id": f"domain_{half}_{r_['name'].split()[-1]}", "key": key, "kind": "free", "cells": cells,
                                 "label": f"{'Cover' if half == 'cover' else 'Motor side'}, {r_['name']}",
                                 "colour": palette[c % len(palette)], "alpha": 0.40,
                                 "note": f"a design domain: {100 * r_.get('metal_share', 0):.0f} % of the flow it was drawn from; {where}"})  # fmt: skip
                c += 1
        return out_rows

    for mv in moves:
        run = next((r["run"] for r in mv["results"] if r.get("run") and (r.get("model") or {}).get("done")), None)
        planned = (mv.get("space") or {}).get("mask")
        if (not run or not (OUT / f"{run}.npz").exists()) and planned and (OUT / planned).exists():  # a design volume not yet run
            rz = np.load(OUT / planned)
            rows = region_rows(planned, tuple(int(v) for v in rz["n"]), np.asarray(rz["lo"], float), float(rz["h"]), None)
            if rows:
                per_move[str(mv["n"])] = rows
            continue
        if not run or not (OUT / f"{run}.npz").exists():
            continue
        z = np.load(OUT / f"{run}.npz")
        n, lo, h = tuple(int(v) for v in z["n"]), np.asarray(z["lo"], float), float(z["h"])
        elem, free_e, frozen, phys = z["elem"], z["free_e"], z["frozen"].astype(bool), np.asarray(z["phys"], float)
        if grid is None:
            centre0 = lo + h / 2
            grid = {"size": h, "shape": [n[0], n[2], n[1]], "origin": [centre0[0], centre0[2], -(centre0[1] + (n[1] - 1) * h)]}
            fixed = np.zeros(n, bool)
            fixed.flat[elem[frozen]] = True
            context.append(entry("fixed", *keep(fixed, h, lo, 2)))
        rows = []
        cls = np.zeros(len(free_e), np.int8)  # 0 free, 1 the area's volumes, 2 features, 3 held empty
        spec = (json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")) or {}).get("height_features")
        if spec:
            rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
            skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
            model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                                  route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                                  height_field=rec["height_field"]["radius_mm"])  # fmt: skip
            kind = model["kind"]
            m_elem = np.flatnonzero(kind >= 0)
            m_free = np.flatnonzero(kind[m_elem] == 0)
            if len(m_free) == len(free_e):
                col, _, pts, layer = topo.height_columns(kind, model["n"], model["k_split"], m_elem, m_free)
                radius = float(rec["height_field"]["radius_mm"]) / h
                tree = cKDTree(np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]]))
                pp = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
                fmat = (sps.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(len(pts), len(pts))).tocsr()
                        + sps.eye(len(pts)) * radius).tocsr()  # fmt: skip
                _, _, feat = topo.feature_map(spec, model["info"], pts, layer, model["lo"], h, fmat, len(pts))
                owner, region = feat["owner"], feat["region"]
                is_free = np.array([f["free"] for f in feat["features"]] + [False])
                c_cls = np.where(~region, 0, np.where(owner < 0, 3, np.where(is_free[owner], 1, 2)))
                cls = c_cls[col].astype(np.int8)
        if (cls > 0).any():  # the view opens on the area, from the side its half faces (the viewer's frame: x, z, -y)
            ijk = np.stack(np.unravel_index(elem[free_e[cls > 0]], n), axis=1)
            xyz = lo + h * (ijk + 0.5)
            view = np.column_stack([xyz[:, 0], xyz[:, 2], -xyz[:, 1]])
            box = np.concatenate([view.min(axis=0) - 2 * h, view.max(axis=0) + 2 * h])
            focus[str(mv["n"])] = {"bbox": [round(float(v), 1) for v in box], "from": [0.35, -1.0 if spec["half"] == "motor_side" else 1.0, 0.45]}
        for lid, which in (("space", 0), ("volumes", 1), ("features", 2), ("empty", 3)):
            sel = cls == which
            if not sel.any():
                continue
            mask = np.zeros(n, bool)
            mask.flat[elem[free_e[sel]]] = True
            rows.append(entry(lid, *keep(mask, h, lo, 2 if lid == "space" else 1)))
        rec_space = (json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")) or {}).get("space") or ""
        if str(rec_space).endswith(".npz"):  # the design volume from the hard points, its regions by kind
            free_cells = np.zeros(n, bool)
            free_cells.flat[elem[free_e]] = True
            rows += region_rows(rec_space, n, lo, h, free_cells)
        elif str(rec_space).endswith(".json") and (OUT / rec_space).exists():  # organised design domains (`domains_from_flow.py`)
            rows += domain_rows(rec_space, n, lo, h, elem[free_e], int(z["k_split"]))
        hv = (json.loads((OUT / f"{run}.json").read_text(encoding="utf-8")) or {}).get("height_volumes")
        if hv:  # the design space in volumes (`sections.py`, `section_forms.py`): a layer a kind
            rows += volume_rows(run, hv, n, lo, h, elem, free_e)
        metal = np.zeros(n, bool)
        dens = phys if len(phys) == len(free_e) else phys[free_e]  # a run keeps its free voxels' densities
        metal.flat[elem[free_e[dens >= 0.5]]] = True
        rows.append(entry("metal", *keep(metal, h, lo)))
        per_move[str(mv["n"])] = rows
    if grid is None:
        return None
    WEB3D.mkdir(parents=True, exist_ok=True)
    path = WEB3D / f"{campaign}.json"
    path.write_text(json.dumps({"voxel_mm": grid["size"], "grid": grid, "layers": layers, "context": context, "moves": per_move, "focus": focus}),
                    encoding="utf-8")  # fmt: skip
    print(path, f"{len(per_move)} moves in 3D, {len(layers)} layers, {path.stat().st_size / 1e6:.1f} MB")
    return path


def main(campaign: str) -> None:
    src = json.loads((OUT / "agent" / f"{campaign}.json").read_text(encoding="utf-8"))
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))}
    WEB.mkdir(parents=True, exist_ok=True)
    moves = []
    fe_runs = 0
    best = None
    for mv in src["moves"]:
        mv = dict(mv)
        results = []
        for r in mv.get("results", []):
            r = dict(r)
            if r.get("run"):
                r["model"] = model_of(r["run"])
            if r.get("design"):
                r["fe"] = fe_of(r["design"], grades)
                if r["fe"]:
                    fe_runs += 1
                    if r["fe"]["pass"] and (best is None or r["fe"]["kg"] < best["kg"]):
                        best = {"design": r["design"], "kg": r["fe"]["kg"], "move": mv["n"]}
                pic = f"{campaign}_{r['design']}.png"
                r["picture"] = pic if thumb(OUT / f"look_{r['design']}.png", WEB / pic) else None
            results.append(r)
        mv["results"] = results
        sp = dict(mv.get("space") or {})
        if sp.get("file"):
            regions = json.loads((OUT / sp["file"]).read_text(encoding="utf-8"))
            fills = {}
            for r in mv["results"]:
                for f in OUT.glob(f"fill_{Path(sp['file']).stem}_*.json"):
                    rec = json.loads(f.read_text(encoding="utf-8"))
                    if rec.get("run") == r.get("run"):
                        fills = {f"{row['half']}|{row['region']}": row for row in rec["rows"]}
            sp["fill"] = {k: {"covered": v["covered"], "volume": v["volume_fill"], "height_mm": v["mean_height_mm"]} for k, v in fills.items()}
            sp["regions"] = {h: [{"name": g["name"], "outline": g["outline"], "holes": g.get("holes", [])} for g in regs] for h, regs in regions["halves"].items()}
        elif sp.get("features"):  # the bore experiment: the features as regions, filled to the heights the optimiser gave them
            run = next((r["run"] for r in mv["results"] if r.get("run") and (r.get("model") or {}).get("done")), None)
            sp["regions"], sp["fill"] = feature_space(sp["features"], run)
        mv["space"] = sp
        pics = []
        for name in mv.get("pictures", []):
            dst = f"{campaign}_{name}"
            if thumb(OUT / name, WEB / dst, 1100):
                pics.append(dst)
        if sp.get("file"):
            dst = f"{campaign}_{Path(sp['file']).stem}.png"
            if thumb(OUT / f"{Path(sp['file']).stem}.png", WEB / dst, 1100):
                pics.append(dst)
        mv["pictures"] = pics
        moves.append(mv)
    out = {**{k: v for k, v in src.items() if k != "moves"}, "moves": moves, "fe_runs": fe_runs, "best": best, "context": context(lay)}
    path = WEB / f"{campaign}.json"
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(path, f"{len(moves)} moves, {fe_runs} FE runs, best {best}")
    space3d(campaign, moves)


if __name__ == "__main__":
    main(sys.argv[1])
