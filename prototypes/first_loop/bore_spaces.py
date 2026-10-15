"""The design space iterated round one bore (LOP-24; the method agreed with the engineer, 11 October
22:35-23:04, and 12 October 00:04: the optimiser's metal, not the agent, gives the shapes' places). Each
step writes a `--height-features` file for `topo_free.py` in which the area's volumes are marked
`"free": true` (`topo.feature_map`): the optimiser places metal freely inside them, the rest of the
area is held empty, the rest of the part stays free. Then the clear shapes become standard features
whose sizes the optimiser chooses.

- `first <free run>`: regular volumes over the free run's metal round the bore: the boss as a ring (and
  the cap behind a blind seat, kept as the wedges are), and wedges of `--wedge` degrees from the boss
  out to the area's edge, each kept where the free run's members cover at least `--keep` of its plan.
- `next <run> <volumes>`: how the run filled each volume, and the next space from it. A wedge whose
  metal lines up (its spread across the line under `--line` of a uniform fill's) is narrowed to a strip
  `--strip` mm wide along that line, out to where the metal ends; a wedge filled broadly (at least
  `--broad`) is kept; one filled under `--drop` is dropped; any other is split in two. A strip stays
  while its metal runs along it (at least `--drop`).
- `features <run> <volumes>`: each volume that holds a clear shape becomes its standard feature: a strip
  a rib `--rib` mm wide along its metal's line (a root and a tip height), a broadly filled wedge a web
  (a sector, one height), the boss a ring. A volume with no clear shape stays free, unresolved.

Every reading is printed a volume and kept in the file's `reading`; the file is
data/first_loop/<label>.json, its plan pictured by `feature_map_check.py`.

    bore_spaces.py first <free run> --label <label> [--half motor_side] [--bore intermediate] [--reach 40] [--wedge 30] [--keep 0.25]
    bore_spaces.py next <run> <volumes file> --label <label>
    bore_spaces.py features <run> <volumes file> --label <label>"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sps
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
import topo  # noqa: E402
import topo_free as tf  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0  # mm: a column this high off its base holds a member (bore_spill.MEMBER)


def area(spec: dict, run: str) -> dict:
    """The area's columns and each volume's, on the model a run was made on (rebuilt from its record),
    with the run's heights (mm off each column's base, at most its own free voxels)."""
    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
    model = tf.build_free(4.0, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                          route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                          height_field=rec["height_field"]["radius_mm"])  # fmt: skip
    kind, n, h, lo = model["kind"], model["n"], model["h"], model["lo"]
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, n, model["k_split"], elem, free_e)
    radius = float(rec["height_field"]["radius_mm"]) / h
    plan = np.column_stack([pts[:, 0] + 1_000_000.0 * layer, pts[:, 1]])
    tree = cKDTree(plan)
    pp = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    fmat = (sps.coo_matrix((np.maximum(0.0, radius - pp.data), (pp.row, pp.col)), shape=(len(pts), len(pts))).tocsr() + sps.eye(len(pts)) * radius).tocsr()
    _, _, feat = topo.feature_map(spec, model["info"], pts, layer, lo, h, fmat, len(pts))
    side = "+z" if spec["half"] == "cover" else "-z"
    me = next(b for b in model["info"]["bearings"] if b["side"] == side and b["shaft"] == spec["bore"])
    cx = lo[0] + h * (pts[:, 0] + 0.5)
    cy = lo[1] + h * (pts[:, 1] + 0.5)
    sel = layer == (1 if spec["half"] == "motor_side" else 10_001)
    room = np.bincount(col, minlength=len(pts)) * h
    maps = shh.column_heights(run)
    t = np.zeros(len(pts))
    t[sel] = maps[spec["half"]][pts[sel, 0].astype(int), pts[sel, 1].astype(int)]
    t = np.minimum(np.maximum(t, 0.0), room)
    return {"feat": feat, "me": me, "sel": sel, "t": t, "r": np.hypot(cx - me["axis"][0], cy - me["axis"][1]),
            "ang": np.degrees(np.arctan2(cy - me["axis"][1], cx - me["axis"][0])), "h": h}  # fmt: skip


def in_sector(ang: np.ndarray, a0: float, a1: float) -> np.ndarray:
    return (ang - a0) % 360.0 <= (a1 - a0) % 360.0


def read(A: dict, m: np.ndarray) -> dict:
    """A volume's fill: the share of its plan holding a member, the members' mean height, and the
    line its metal makes: the metal-weighted direction (degrees), the spread across it (mm) and how
    far out the metal goes (mm from the axis, its 90th percentile)."""
    t, r, ang = A["t"][m], A["r"][m], A["ang"][m]
    mem = t >= MEMBER
    out = {"columns": int(m.sum()), "covered": float(mem.mean()) if m.any() else 0.0,
           "height_mm": float(t[mem].mean()) if mem.any() else 0.0}  # fmt: skip
    if mem.sum() >= 2:
        w = t[mem]
        th = np.radians(ang[mem])
        mean = math.degrees(math.atan2(float((w * np.sin(th)).sum()), float((w * np.cos(th)).sum())))
        across = r[mem] * np.sin(th - math.radians(mean))
        order = np.argsort(r[mem])
        cum = np.cumsum(w[order]) / w.sum()
        out.update({"line_deg": mean, "across_mm": float(np.sqrt((w * across**2).sum() / w.sum())),
                    "reach_mm": float(r[mem][order][min(np.searchsorted(cum, 0.9), len(order) - 1)])})  # fmt: skip
    return out


def write(label: str, spec: dict, volumes: list, reading: list, step: str) -> Path:
    out = dict({k: v for k, v in spec.items() if k not in ("features", "reading", "family", "step")}, family="volumes", step=step,
               features=volumes, reading=reading)  # fmt: skip
    path = OUT / f"{label}.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(path.name + ": " + ", ".join(f"{v['name']}{' (free)' if v.get('free') else ''}" for v in volumes))
    return path


def first(run: str, half: str, bore: str, reach: float, wedge: float, keep: float, label: str) -> Path:
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    side = "+z" if half == "cover" else "-z"
    me = next(b for b in lay["bearings"] if b["side"] == side and b["shaft"] == bore)
    boss, seat = float(me["boss_r"]), 0.5 * float(me["D"])
    spec = {"half": half, "bore": bore, "radius": boss + reach, "features": []}
    A = area(spec, run)
    reg = A["feat"]["region"] & A["sel"]
    metal = reg & (A["t"] >= MEMBER)
    volumes, reading = [], []
    candidates = [{"name": "cap", "kind": "ring", "r_in": 0.0, "r_out": seat, "free": True},
                  {"name": "boss", "kind": "ring", "r_in": seat, "r_out": boss, "free": True}]  # fmt: skip
    for i in range(int(round(360.0 / wedge))):
        a0 = -180.0 + i * wedge
        candidates.append({"name": f"wedge {a0:.0f}° to {a0 + wedge:.0f}°", "kind": "sector", "r_in": boss, "r_out": boss + reach,
                           "a0": a0, "a1": a0 + wedge, "free": True})  # fmt: skip
    covered_metal = np.zeros(len(reg), bool)
    for v in candidates:
        m = reg & (A["r"] >= v["r_in"]) & (A["r"] <= v["r_out"])
        if v["kind"] == "sector":
            m &= in_sector(A["ang"], v["a0"], v["a1"])
        if not m.any():
            continue
        f = read(A, m)
        kept = v["name"] == "boss" or f["covered"] >= keep
        reading.append({"volume": v["name"], **f, "verdict": "kept" if kept else "dropped: the free run's members cover too little of it"})
        if kept:
            volumes.append(v)
            covered_metal |= m & metal
        print(f"{v['name']:>18}: {f['columns']:4d} columns, {100 * f['covered']:3.0f} % under members, {f['height_mm']:4.1f} mm high"
              f" -> {'kept' if kept else 'dropped'}")  # fmt: skip
    share = covered_metal.sum() / max(int(metal.sum()), 1)
    print(f"the kept volumes hold {100 * share:.0f} % of the free run's members in the area")
    reading.append({"volume": "all", "metal_held": float(share)})
    return write(label, spec, volumes, reading, "first")


def next_space(run: str, volumes_file: str, label: str, strip: float, line: float, broad: float, drop: float) -> Path:
    spec = json.loads((OUT / volumes_file).read_text(encoding="utf-8"))
    A = area(spec, run)
    boss, outer = float(A["me"]["boss_r"]), float(spec["radius"])
    volumes, reading = [], []
    for k, v in enumerate(spec["features"]):
        m = A["sel"] & (A["feat"]["owner"] == k)
        if not m.any():
            continue
        f = read(A, m)
        if not v.get("free"):  # a feature already: kept as it is
            volumes.append(v)
            reading.append({"volume": v["name"], **f, "verdict": "a feature: kept"})
            continue
        if v["kind"] == "ring":
            verdict = "kept" if (v["name"] == "boss" or f["covered"] >= drop) else "dropped: barely filled"
            if verdict == "kept":
                volumes.append(v)
        elif f["covered"] < drop:
            verdict = "dropped: barely filled"
        elif v["kind"] == "sector":
            width = math.radians((v["a1"] - v["a0"]) % 360.0)
            span = float(np.mean(A["r"][m])) * width  # mm across the wedge at its columns' mean radius
            uniform = span / math.sqrt(12.0)
            # filled broadly: a web, kept; else its metal lines up, or the wedge is already no wider than two
            # strips: a strip along the metal's line, as wide as the metal (its spread's uniform width plus a
            # voxel, in 4 mm steps), at least `strip`
            if f["covered"] >= broad:
                volumes.append(v)
                verdict = "filled broadly: kept"
            elif "across_mm" in f and (f["across_mm"] <= line * uniform or span <= 2 * strip):
                r1 = min(outer, f["reach_mm"] + 2 * A["h"])
                w = max(strip, 4.0 * math.ceil((math.sqrt(12.0) * f["across_mm"] + A["h"]) / 4.0))
                volumes.append({"name": f"strip {f['line_deg']:.0f}°", "kind": "rib", "angle": f["line_deg"], "r0": boss, "r1": r1,
                                "width": w, "free": True, "metal": f["covered"] * f["columns"]})  # fmt: skip
                verdict = f"lines up at {f['line_deg']:.0f}° (spread {f['across_mm']:.1f} mm across, a uniform fill's {uniform:.1f}): a strip {w:g} mm wide to {r1:.0f} mm"
            else:
                mid = v["a0"] + 0.5 * ((v["a1"] - v["a0"]) % 360.0)
                volumes += [dict(v, name=f"wedge {v['a0']:.0f}° to {mid:.0f}°", a1=mid), dict(v, name=f"wedge {mid:.0f}° to {v['a1']:.0f}°", a0=mid)]
                verdict = "filled in parts, no line: split in two"
        else:  # a strip: kept while its metal runs along it
            volumes.append(dict(v, angle=f.get("line_deg", v["angle"])))
            verdict = f"its metal runs along it ({100 * f['covered']:.0f} %): kept, at {f.get('line_deg', v['angle']):.0f}°"
        reading.append({"volume": v["name"], **f, "verdict": verdict})
        print(f"{v['name']:>18}: {100 * f['covered']:3.0f} % under members, {f['height_mm']:4.1f} mm high"
              + (f", line {f['line_deg']:.0f}°, {f['across_mm']:.1f} mm across, out to {f['reach_mm']:.0f} mm" if "across_mm" in f else "")
              + f" -> {verdict}")  # fmt: skip
    # strips that overlap at the area's middle radius are one member: merged along their metal-weighted line,
    # while the merged strip stays at most three strips wide (wider, they stay two and the first holds the overlap)
    mid = 0.5 * (boss + outer)
    strips = sorted([v for v in volumes if v["kind"] == "rib" and "metal" in v], key=lambda v: v["angle"])
    merged = []
    for s in strips:
        last = merged[-1] if merged else None
        gap = math.radians(abs(s["angle"] - last["angle"])) * mid if last else 0.0
        width = 4.0 * math.ceil((gap + max(last["width"], s["width"])) / 4.0) if last else 0.0
        if last and gap < 0.5 * (s["width"] + last["width"]) and width <= 3 * strip:
            wsum = last["metal"] + s["metal"]
            angle = (last["angle"] * last["metal"] + s["angle"] * s["metal"]) / max(wsum, 1e-9)
            merged[-1] = dict(last, name=f"strip {angle:.0f}°", angle=angle, width=width, r1=max(last["r1"], s["r1"]), metal=wsum)
            print(f"{'':>18}  strips at {last['angle']:.0f}° and {s['angle']:.0f}° overlap: one strip {width:g} mm wide at {angle:.0f}°")
        else:
            merged.append(s)
    volumes = [v for v in volumes if not (v["kind"] == "rib" and "metal" in v)] + [{k: x for k, x in v.items() if k != "metal"} for v in merged]
    return write(label, spec, volumes, reading, "next")


def features(run: str, volumes_file: str, label: str, rib: float, broad: float, drop: float) -> Path:
    spec = json.loads((OUT / volumes_file).read_text(encoding="utf-8"))
    A = area(spec, run)
    volumes, reading = [], []
    for k, v in enumerate(spec["features"]):
        m = A["sel"] & (A["feat"]["owner"] == k)
        if not m.any():
            continue
        f = read(A, m)
        if not v.get("free"):
            volumes.append(v)
            verdict = "a feature: kept"
        elif v["kind"] == "ring":
            if v["name"] == "boss" or f["covered"] >= broad:
                volumes.append({k_: x for k_, x in v.items() if k_ != "free"})
                verdict = "a ring: as a feature"
            elif f["covered"] >= drop:
                volumes.append(v)
                verdict = "no ring there, but metal: left free, unresolved"
            else:
                verdict = "dropped: barely filled"
        elif v["kind"] == "rib":
            if f["covered"] >= drop:
                # as wide as its metal (its spread's uniform width, in 4 mm steps), at least `rib`, at most the strip
                w = min(v["width"], max(rib, 4.0 * round(math.sqrt(12.0) * f.get("across_mm", 0.0) / 4.0)))
                volumes.append({"name": f"rib {f.get('line_deg', v['angle']):.0f}°", "kind": "rib", "angle": f.get("line_deg", v["angle"]),
                                "r0": v["r0"], "r1": v["r1"], "width": w})  # fmt: skip
                verdict = f"a rib {w:g} mm wide at {f.get('line_deg', v['angle']):.0f}°, its heights the optimiser's"
            else:
                verdict = "dropped: its metal does not run along it"
        elif f["covered"] >= broad:
            volumes.append({k_: x for k_, x in v.items() if k_ != "free"} | {"name": v["name"].replace("wedge", "web")})
            verdict = "filled broadly: a web"
        elif f["covered"] >= drop:
            volumes.append(v)
            verdict = "no clear shape: left free, unresolved"
        else:
            verdict = "dropped: barely filled"
        reading.append({"volume": v["name"], **f, "verdict": verdict})
        print(f"{v['name']:>18}: {100 * f['covered']:3.0f} % under members -> {verdict}")
    return write(label, spec, volumes, reading, "features")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", choices=("first", "next", "features"))
    ap.add_argument("run")
    ap.add_argument("volumes", nargs="?", default="")
    ap.add_argument("--label", required=True)
    ap.add_argument("--half", default="motor_side", choices=("motor_side", "cover"))
    ap.add_argument("--bore", default="intermediate")
    ap.add_argument("--reach", type=float, default=40.0, help="mm past the boss radius: the area's edge")
    ap.add_argument("--wedge", type=float, default=30.0, help="degrees, each first wedge")
    ap.add_argument("--keep", type=float, default=0.25, help="first: a wedge kept where the free run's members cover this much of it")
    ap.add_argument("--strip", type=float, default=16.0, help="mm, a strip's width")
    ap.add_argument("--line", type=float, default=0.5, help="a wedge's metal lines up when its spread across is under this share of a uniform fill's")
    ap.add_argument("--broad", type=float, default=0.6, help="a volume filled at least this much is filled broadly")
    ap.add_argument("--drop", type=float, default=0.15, help="a volume filled under this much is dropped")
    ap.add_argument("--rib", type=float, default=8.0, help="mm, a rib's width (two 4 mm voxels)")
    a = ap.parse_args()
    if a.step == "first":
        first(a.run, a.half, a.bore, a.reach, a.wedge, a.keep, a.label)
    elif a.step == "next":
        next_space(a.run, a.volumes, a.label, a.strip, a.line, a.broad, a.drop)
    else:
        features(a.run, a.volumes, a.label, a.rib, a.broad, a.drop)
