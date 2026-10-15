"""PROTOTYPE (LOP-24) - the housing as parametric CAD: production's features from a recipe (the engineer,
12 October 08:43: "pick one best looking and deliver as parametric cad", after the night's smooth drawings
of free heights were judged unmanufacturable: "who will even accept or manufacture such housing geometry").

The concept is the night's best-looking (`prod19_asis`: the `ln6` layout read from the free run's flow), but
every feature is now a manufacturing feature with its own parameters, never the optimiser's columns:
- **a boss** round each bearing's bore: a ring `width` past the bore, its machined face `height` past the
  end wall it stands on;
- **a bridge** between two seats of a half (the free run's tie, which the gears' separating forces load):
  a web `t` thick along the seats' centre line, from boss to boss, flat-topped `h` past the walls;
- **a rib** along each of the flow's lines over the end walls (to a bolt or a mount): a plate `t` thick,
  its top straight from `h0` at the boss to `h1` at the wall's edge;
- **a spoke** across each bare panel: radial from a boss every `spoke_step` degrees where no rib runs,
  `t` thick, `h0` to `h1` (production's spoked end faces; the panel rule moved the cover's mode by s2's
  order out of its band, `prod19_asis`);
- **a gusset** at each flange bolt: a triangle `t` thick standing on the flange, `h` up the side wall,
  coming down to the flange short of the bolt's socket;
- **an arm** to each mount's lug (the motor side): a web `t` wide with its roots rounded (`grammar.tie_wire`).
The rib heights come from the optimiser (each rib's form in the run: its columns' heights along it, a
straight line fitted, clipped to `H_RANGE`), so the CAD stays load-aware; every other size is the recipe's.
Everything else is the exact-CAD route's (`ribbed_cad.py`): the contract's exact shell, each feature a plate
under a ruled top (`ribbed_cad.plate`), fused pairwise and checked by volume, cut flat at the split, every
exact cut, STEP and B-rep, FE's own mesh (`ribbed_cad.mesh_body`), the record as the B-rep drawings write it.

The recipe is the parametric definition: `<design>_recipe.json` beside the CAD; edit it and build again
with `--recipe`.

Run: .venv/Scripts/python.exe prototypes/first_loop/param_cad.py <run stem> <design stem> [--recipe <json>]
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import cup as cupmod  # noqa: E402
import grammar  # noqa: E402
import outcome_cad as oc  # noqa: E402
import ribbed_cad as rc  # noqa: E402
import shell as convex  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import cylinder  # noqa: E402

OUT = rc.OUT
say = rc.say
H_RANGE = (6.0, 24.0)  # mm, a rib's height off its wall (the band's 24 the most)
PARAMS = {  # the recipe's sizes (mm, degrees): production's proportions (ribs 0.8-1.0 x the wall plus, `ribbed_cad.RIB_BAND`)
    "boss_width": 8.0, "boss_height": 8.0,
    "bridge_t": 10.0, "bridge_h": 24.0,
    "rib_t": 5.0, "rib_least_mean": 3.0,
    "spoke_t": 5.0, "spoke_h0": 14.0, "spoke_h1": 8.0, "spoke_step": 30.0, "spoke_least": 30.0, "spoke_clear": 15.0,
    "gusset_t": 5.0, "gusset_h": 24.0,
    "arm_t": 25.0, "arm_root": 6.0, "arm_stub": 6.0,
    # the fillets (the engineer, 08:52: "can you add also fillets"): the shell's end faces' rims, the bosses'
    # faces' edges, every rib's top a full round (drawn: a loft of production's rib section), the roots
    "rim_r": 3.0, "boss_edge_r": 2.0, "root_r": 3.0,
    # the fins (12 October 09:06, after `param3`'s FE: 273 µm, the cover's seats at the tips of their tubes, 4 mm walls
    # 45-70 mm long from the split; the free run held them with the metal beside them, up to the band out): radial
    # plates every `fin_step` round each room's outside, `fin_depth` out from its wall, from just under its rim down
    # to `fin_tip` off what lies beyond (production's side ribs and the bearings' buttresses)
    "fin_step": 30.0, "fin_t": 6.0, "fin_depth": 20.0, "fin_tip": 6.0, "fin_least_r": 20.0,
    # a boss is a collar over its seat's own length and `boss_below` past it toward the split, not the whole tube
    "boss_below": 8.0,
}  # fmt: skip
SINK = 5.0  # mm a rib's section runs under the face it stands on (the 4 mm wall and a millimetre: the inside's cut takes it)


def rooms_of(all_rooms: list[dict], z_split: float, half: str, wall: float) -> list[tuple[np.ndarray, float]]:
    """A half's rooms' outsides in plan: (axis, radius to the wall's outer face)."""
    return [(np.asarray(p["axis"], float), float(p["r"]) + wall) for p in cupmod.pieces(all_rooms, z_split, half)]


def inside(p: np.ndarray, rooms: list) -> np.ndarray:
    """Whether each plan point lies within the half's outline (its rooms' outsides)."""
    p = np.atleast_2d(p)
    return np.any([np.hypot(*(p - ax).T) <= r for ax, r in rooms], axis=0)


def to_edge(start: np.ndarray, u: np.ndarray, rooms: list, step: float = 1.0, most: float = 400.0) -> float:
    """How far from `start` along `u` the ray stays within the outline (mm)."""
    s = np.arange(0.0, most, step)
    ok = inside(start[None, :] + s[:, None] * u[None, :], rooms)
    return float(s[np.argmin(ok)] if not ok.all() else most)


def recipe_from(run: str, layout: dict) -> dict:
    """The default recipe from the run's layout of forms (its record's `height_volumes`, `section_forms.py`):
    its bridges and its ribs over the end walls, each rib's heights from the optimiser's own columns."""
    import implicit_draw as idr

    rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / f"{Path(rec['height_volumes']).stem.removesuffix('_cols')}.json").read_text(encoding="utf-8"))
    mem = idr.members(run)
    cl = mem["cols"]
    p = dict(PARAMS)
    seats = layout["bearings"]
    features = {"bosses": [], "bridges": [], "ribs": [], "spokes": [], "gussets": [], "arms": []}
    for b in seats:
        features["bosses"].append({"half": "cover" if b["side"] == "+z" else "motor_side", "shaft": b["shaft"], "axis": b["axis"], "D": b["D"],
                                   "seat_z": b["z"], "width": p["boss_width"], "height": p["boss_height"], "below": p["boss_below"]})  # fmt: skip
    for v, item in enumerate(meta["volumes"]):
        if item["kind"] == "bridge":
            m = re.search(r"between the (\w+) and (\w+) seats", item["name"])
            if m:
                features["bridges"].append({"half": item["half"], "a": m.group(1), "b": m.group(2), "t": p["bridge_t"], "h": p["bridge_h"]})
        elif item["kind"] == "rib" and item.get("over") == "the end walls":
            mine = np.flatnonzero(cl["layout"] == v)
            t = np.minimum(np.maximum(cl["t"][mine], 0.0), cl["room"][mine])
            if not len(mine) or float(t.mean()) < p["rib_least_mean"]:
                continue
            s = cl["s"][mine]
            a = np.column_stack([np.ones_like(s), s])
            c0, c1 = np.linalg.lstsq(a, t, rcond=None)[0]
            h0, h1 = (float(np.clip(c0 + c1 * x, *H_RANGE)) for x in (0.0, 1.0))
            features["ribs"].append({"half": item["half"], "a": item["a_mm"], "b": item["b_mm"], "t": p["rib_t"], "h0": round(h0, 1), "h1": round(h1, 1),
                                     "from": "the optimiser's heights along its form"})  # fmt: skip
    for i, _ in enumerate(layout["bolts"]):
        for half in ("motor_side", "cover"):
            features["gussets"].append({"half": half, "bolt": i, "t": p["gusset_t"], "h": p["gusset_h"]})
    for m in layout["mounts"]:
        features["arms"].append({"mount": m["name"], "t": p["arm_t"], "root": p["arm_root"], "stub": p["arm_stub"]})
    features["spokes"] = [{"half": h, "step": p["spoke_step"], "t": p["spoke_t"], "h0": p["spoke_h0"], "h1": p["spoke_h1"],
                           "least": p["spoke_least"], "clear": p["spoke_clear"]} for h in ("motor_side", "cover")]  # fmt: skip
    features["fins"] = [{"half": h, "step": p["fin_step"], "t": p["fin_t"], "depth": p["fin_depth"], "tip": p["fin_tip"], "least_r": p["fin_least_r"]}
                        for h in ("motor_side", "cover")]  # fmt: skip
    return {"design_of": run, "concept": "the ln6 layout read from the free run's flow (prod19_asis's), as production's features",
            "params": p, "features": features}  # fmt: skip


def rounded_rib(a, b, t: float, z_a: float, z_b: float, h_a: float, h_b: float, out: float) -> cq.Shape | None:
    """A straight rib with a full-round top, as production casts it: a ruled loft between its section at each
    end (`grammar.pill_wire`: `t` wide, from SINK under its face to its height off it, the top a semicircle),
    the faces at z_a and z_b, the heights h_a and h_b. None where the section would be lower than its round."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if min(h_a, h_b) <= 0.5 * t + 0.5:
        return None
    tangent = cq.Vector(float(b[0] - a[0]), float(b[1] - a[1]), 0.0)
    up = cq.Vector(0.0, 0.0, out)
    w0 = grammar.pill_wire(cq.Vector(float(a[0]), float(a[1]), z_a), tangent, up, t, h_a, SINK)
    w1 = grammar.pill_wire(cq.Vector(float(b[0]), float(b[1]), z_b), tangent, up, t, h_b, SINK)
    solid = cq.Solid.makeLoft([w0, w1], ruled=True)
    return solid if solid.isValid() and solid.Volume() > 0 else None


def roots(body: cq.Shape, levels: list[float], out: float, tol: float = 0.05) -> list:
    """The body's concave edges where a feature stands on a face along the pull: each edge between a face square
    to the pull at one of `levels` (z) and a face standing up from it (a rib's side or end, a boss's side), on the
    side the half's features rise (`out`)."""
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape

    amap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(body.wrapped, TopAbs_EDGE, TopAbs_FACE, amap)
    found = []
    for i in range(1, amap.Extent() + 1):
        edge = cq.Edge(amap.FindKey(i))
        faces = [cq.Face(f) for f in amap.FindFromIndex(i)]
        if len(faces) != 2:
            continue
        lo_, hi_ = edge.BoundingBox().zmin, edge.BoundingBox().zmax
        if hi_ - lo_ > tol or not any(abs(lo_ - z) < tol for z in levels):
            continue  # an edge lying on one of the faces the features stand on
        flat = [f for f in faces if f.geomType() == "PLANE" and abs(abs(f.normalAt(f.Center()).z) - 1.0) < 1e-6]
        upright = [f for f in faces if f not in flat]
        if len(flat) != 1 or len(upright) != 1:
            continue
        bb = upright[0].BoundingBox()
        rises = bb.zmax > hi_ + 1.0 if out > 0 else bb.zmin < lo_ - 1.0
        if rises:
            found.append(edge)
    return found


def signature(e) -> tuple:
    c = e.Center()
    return (round(c.x, 2), round(c.y, 2), round(c.z, 2), round(e.Length(), 2))


def filleted(body: cq.Shape, select, r: float, name: str) -> cq.Shape:
    """The body with the edges `select(body)` finds filleted at r: all at once, else by halves (bisected, each half
    found again on the body as it then is, by its edges' centres and lengths), a single edge OCC refuses left as it
    is. Each step is kept only if the body stays one valid solid gaining at most the fillets' own metal (OCC's
    fillets of many edges at once refuse where one of them meets another feature badly)."""

    def tried(shape, group):
        try:
            out_ = shape.fillet(r, group)
        except Exception:  # noqa: BLE001 - OCC's refusal is the answer
            return None
        corner = r * r * sum(e.Length() for e in group)  # a fillet adds (a root) or takes (a rim) at most its corner's metal
        # (no more solids than it had: the motor side's shell is its cup and its lugs, several solids till the arms join them)
        ok = out_.isValid() and len(out_.Solids()) <= len(shape.Solids()) and abs(out_.Volume() - shape.Volume()) <= corner + 1.0
        return out_ if ok else None

    targets = [signature(e) for e in select(body)]
    if not targets:
        return body
    done, refused = 0, 0

    def run(shape, wanted: list) -> cq.Shape:
        nonlocal done, refused
        now = [e for e in select(shape) if signature(e) in set(wanted)]
        if not now:
            return shape
        got = tried(shape, now)
        if got is not None:
            done += len(now)
            return got
        if len(now) == 1:
            refused += 1
            return shape
        half_ = len(wanted) // 2
        shape = run(shape, wanted[:half_])
        return run(shape, wanted[half_:])

    body = run(body, targets)
    say(f"  {name}: {done} of {len(targets)} edges filleted at {r:g} mm" + (f", {refused} refused and left sharp" if refused else ""))
    return body


def straight(a, b, n: int | None = None) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = n or max(2, int(math.hypot(*(b - a)) / 8.0) + 1)
    return a[None, :] + np.linspace(0.0, 1.0, n)[:, None] * (b - a)[None, :]


def half_parts(recipe: dict, layout: dict, all_rooms: list, half: str) -> tuple[list[cq.Shape], dict]:
    """The half's features as solids (unjoined), and what was drawn."""
    s = layout["settings"]
    z_split, wall, t_f = float(layout["z"]["split"]), float(s["wall"]), float(s["flange_thickness"])
    lower = half == "motor_side"
    out = -1.0 if lower else 1.0
    base = rc.base_of(layout, all_rooms, half)
    rooms = rooms_of(all_rooms, z_split, half, wall)
    z_far = 300.0
    z0, z1 = (z_split - z_far, z_split + rc.PAST_SPLIT) if lower else (z_split - rc.PAST_SPLIT, z_split + z_far)
    f = recipe["features"]
    parts, drawn = [], {"bosses": 0, "bridges": 0, "ribs": 0, "spokes": 0, "gussets": 0, "arms": 0}
    seats = {b["shaft"]: b for b in f["bosses"] if b["half"] == half}
    # the bosses: a ring from the split to its machined face, the bore and the inside cut exact after
    p = recipe["params"]

    def feature(a, b, t: float, h_a: float, h_b: float) -> cq.Shape:
        """A straight feature from a to b, `t` thick, h_a and h_b off the faces under its ends: with a full-round
        top where it stands on one face (`rounded_rib`), else a plate under a straight top (`ribbed_cad.plate`)."""
        path = straight(a, b)
        zb = base(path)
        if np.ptp(zb) <= 1.0:
            got = rounded_rib(path[0], path[-1], t, float(zb[0]), float(zb[-1]), h_a, h_b, out)
            if got is not None:
                return got
        top = np.linspace(zb[0] + out * h_a, zb[-1] + out * h_b, len(path))
        return rc.plate(path, top, t, z0, z1, out)

    for b in seats.values():
        ax = np.asarray(b["axis"], float)
        face = float(base(ax[None, :])[0]) + out * float(b["height"])
        if b.get("seat_z") is not None:  # a collar over the seat and `below` past it toward the split
            near_end = min(b["seat_z"]) if not lower else max(b["seat_z"])
            start = near_end - out * float(b.get("below", 0.0))
        else:  # (the first recipes: the whole tube from the split)
            start = z_split - out * rc.PAST_SPLIT
        lo_, hi_ = sorted((start, face))
        boss = cylinder(ax, lo_, hi_, 2 * (0.5 * float(b["D"]) + float(b["width"])))
        edge = [e for e in boss.Edges() if e.geomType() == "CIRCLE" and abs(e.Center().z - face) < 0.01]
        try:  # the machined face's outer edge rounded (a simple solid: OCC fillets it)
            rounded = boss.fillet(float(p.get("boss_edge_r", 0.0)), edge) if p.get("boss_edge_r") else boss
            boss = rounded if rounded.isValid() else boss
        except Exception:  # noqa: BLE001
            pass
        parts.append(boss)
        drawn["bosses"] += 1

    def rim(b) -> float:
        return 0.5 * float(b["D"]) + float(b["width"])

    taken = {k: [] for k in seats}  # each boss's directions already ribbed (degrees)
    # the bridges: a web along the seats' centre line from rim to rim, flat-topped
    for br in f["bridges"]:
        if br["half"] != half or br["a"] not in seats or br["b"] not in seats:
            continue
        a, b = seats[br["a"]], seats[br["b"]]
        ca, cb = np.asarray(a["axis"], float), np.asarray(b["axis"], float)
        d = cb - ca
        L = float(np.hypot(*d))
        if L <= rim(a) + rim(b) + 4.0:
            continue  # the bosses touch: their rings are the tie
        u = d / L
        pa, pb = ca + u * (rim(a) - 2.0), cb - u * (rim(b) - 2.0)
        zb = base(straight(pa, pb))
        crest = (max if not lower else min)(zb) + out * float(br["h"])  # one flat crest over both bosses' walls
        parts.append(feature(pa, pb, float(br["t"]), out * (crest - float(zb[0])), out * (crest - float(zb[-1]))))
        taken[br["a"]].append(math.degrees(math.atan2(u[1], u[0])))
        taken[br["b"]].append(math.degrees(math.atan2(-u[1], -u[0])))
        drawn["bridges"] += 1
    # the ribs on the flow's lines: straight, from h0 off the wall at their start to h1 at their end
    for rb in f["ribs"]:
        if rb["half"] != half:
            continue
        a, b = np.asarray(rb["a"], float), np.asarray(rb["b"], float)
        # its ends 3 mm within the wall's edge: an end on the side wall's cylinder left a face 0.12 mm wide (`param1`)
        u = (b - a) / max(float(math.hypot(*(b - a))), 1e-9)
        if inside(a, rooms)[0]:
            b = a + u * min(float(math.hypot(*(b - a))), to_edge(a, u, rooms, 0.5) - 3.0)
        if math.hypot(*(b - a)) < 10.0:
            continue
        parts.append(feature(a, b, float(rb["t"]), float(rb["h0"]), float(rb["h1"])))
        for k, sb in seats.items():  # the direction it leaves a boss along, if it starts at one
            c = np.asarray(sb["axis"], float)
            if math.hypot(*(a - c)) <= rim(sb) + 12.0:
                taken[k].append(math.degrees(math.atan2(*(b - c)[::-1])))
        drawn["ribs"] += 1
    # the spokes: radial from each boss where no rib leaves it, across its own room's end wall
    for sp in f["spokes"]:
        if sp["half"] != half:
            continue
        for k, sb in seats.items():
            c = np.asarray(sb["axis"], float)
            for ang in np.arange(0.0, 360.0, float(sp["step"])):
                if any(abs((ang - t + 180.0) % 360.0 - 180.0) < float(sp["clear"]) for t in taken[k]):
                    continue
                u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
                start = c + u * (rim(sb) - 2.0)
                length = to_edge(start, u, rooms) - 3.0
                if length < float(sp["least"]):
                    continue
                path = straight(start, start + u * length)
                if any(np.hypot(*(path - np.asarray(o["axis"], float)).T).min() < rim(o) + 2.0 for kk, o in seats.items() if kk != k):
                    continue  # it would run into another boss
                zb = base(path)
                if np.ptp(zb) > 1.0:
                    continue  # one end wall only: a spoke never steps
                parts.append(feature(path[0], path[-1], float(sp["t"]), float(sp["h0"]), float(sp["h1"])))
                taken[k].append(float(ang))
                drawn["spokes"] += 1
    # the gussets: at each bolt, a triangle on the flange from the side wall out, short of the bolt's socket
    socket_r = 0.5 * float(oc.SOCKET[0])
    face = z_split + out * t_f
    for g in f["gussets"]:
        if g["half"] != half:
            continue
        bolt = np.asarray(layout["bolts"][g["bolt"]], float)
        ax, r = min(rooms, key=lambda q: np.hypot(*(bolt - q[0])) - q[1])
        u = (bolt - ax) / max(float(np.hypot(*(bolt - ax))), 1e-9)
        q0 = ax + u * (r - 1.0)
        q1 = bolt - u * (socket_r + 3.0)
        if float((q1 - q0) @ u) < 6.0:
            continue
        # on the flange's face, from its height at the wall down to its own round at the bolt: a triangle with a
        # full-round top (its end inside the side wall stands on the flange's face too, not on the end wall above)
        tip = 0.5 * float(g["t"]) + 1.0
        got = rounded_rib(q0, q1, float(g["t"]), face, face, float(g["h"]), tip, out)
        if got is None:
            path = straight(q0, q1, 4)
            got = rc.plate(path, np.linspace(face + out * float(g["h"]), face + out * tip, len(path)), float(g["t"]), z0, z1, out)
        parts.append(got)
        drawn["gussets"] += 1
    # the fins: round each room's outside every `step` degrees, `depth` out from its wall, from just under its rim
    # down to `tip` off what lies beyond it (a tower's buttresses on the end wall it stands on, a lobe's side ribs
    # down to the flange); none buried in a room at least as tall, none in a bolt's socket or a bracket's room
    pieces_here = cupmod.pieces(all_rooms, z_split, half)
    bolts_xy = np.asarray(layout["bolts"], float)
    brackets_xy = [(np.asarray(bk["centre"], float), float(bk["radius"])) for bk in layout.get("brackets") or [] if bk.get("centre")]
    drawn["fins"] = 0
    for fn in f.get("fins", []):
        if fn["half"] != half:
            continue
        for pc in pieces_here:
            if float(pc["r"]) < float(fn["least_r"]):
                continue
            ax = np.asarray(pc["axis"], float)
            r_o = float(pc["r"]) + wall
            if any(np.allclose(np.asarray(qq["axis"], float), ax) and float(qq["r"]) > float(pc["r"]) and out * (float(qq["far"]) - float(pc["far"])) >= 0.0
                   for qq in pieces_here if qq is not pc):  # fmt: skip
                continue  # a room inside a wider and taller one on its axis: its fins would stand inside that one's
            # its top 6 mm under the rim, clear of the rim's fillet (a plate meeting the fillet's torus crashed OCC, `param4`)
            top_wall = float(pc["far"]) + out * wall - out * (float(p.get("rim_r", 0.0)) + 6.0)
            for ang in np.arange(0.0, 360.0, float(fn["step"])):
                u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
                q0, q1 = ax + u * (r_o - 1.0), ax + u * (r_o + float(fn["depth"]))
                path = straight(q0, q1, 6)
                if any(np.hypot(*(q1 - np.asarray(qq["axis"], float))) < float(qq["r"]) + wall and out * (float(qq["far"]) - float(pc["far"])) >= 0.0
                       for qq in pieces_here if qq is not pc):  # fmt: skip
                    continue  # its tip inside a room at least as tall: buried
                if len(bolts_xy) and float(np.hypot(path[:, None, 0] - bolts_xy[None, :, 0], path[:, None, 1] - bolts_xy[None, :, 1]).min()) < socket_r + 4.0:
                    continue
                if any(float(np.hypot(*(path - c).T).min()) < rr + 3.0 for c, rr in brackets_xy):
                    continue
                top_tip = float(base(q1[None, :])[0]) + out * float(fn["tip"])
                if out * (top_wall - top_tip) < 6.0:
                    continue  # nothing to stand up
                parts.append(rc.plate(path, np.linspace(top_wall, top_tip, len(path)), float(fn["t"]), z0, z1, out))
                drawn["fins"] += 1
    # the arms: each mount's lug tied to the nearest wall by a web, its roots rounded
    if lower:
        for arm in f["arms"]:
            m = next(mm for mm in layout["mounts"] if mm["name"] == arm["mount"])
            c = np.asarray(m["centre"], float)
            r_m = 0.5 * float(s["mount_diameter"])
            ax, r = min(rooms, key=lambda q: np.hypot(*(c - q[0])) - q[1])
            u = (ax - c) / max(float(np.hypot(*(ax - c))), 1e-9)
            reach = float(np.hypot(*(ax - c))) - r
            if reach <= r_m + 2.0:
                continue  # the lug stands on the wall
            wire = grammar.tie_wire(c, u, r_m, float(arm["t"]), reach, float(arm["root"]), float(arm["root"]), float(arm["stub"]), float(m["z"][0]))
            solid = cq.Solid.extrudeLinear(cq.Face.makeFromWires(wire), cq.Vector(0, 0, float(m["z"][1]) - float(m["z"][0])))
            parts.append(solid)
            drawn["arms"] += 1
    return parts, drawn


def build(run: str, stem: str, recipe_path: str | None = None) -> dict:
    t0 = time.time()
    layout = json.loads((OUT / f"{oc.layout_of(run)}.json").read_text(encoding="utf-8"))
    s = layout["settings"]
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    z_split, wall, draft = float(layout["z"]["split"]), float(s["wall"]), float(s.get("draft", 0.0))
    recipe = json.loads(Path(recipe_path).read_text(encoding="utf-8")) if recipe_path else recipe_from(run, layout)
    (OUT / f"{stem}_recipe.json").write_text(json.dumps(recipe, indent=1), encoding="utf-8")
    halves, organic, meshes, held, drawn_all = {}, {}, {}, list(layout["mounts"]), {}
    for half in ("motor_side", "cover"):
        t1 = time.time()
        lower = half == "motor_side"
        shell = oc.exact_shell(layout, all_rooms, z_split, half, wall, draft)
        p = recipe["params"]
        out = -1.0 if lower else 1.0
        t_f = float(s["flange_thickness"])
        if p.get("rim_r"):  # the end faces' rims rounded (the engineer, 11 October: "the shell itself looks quite edgy")
            def rims(sh):
                return [e for e in sh.Edges() if e.geomType() == "CIRCLE" and abs(e.Center().z - z_split) > t_f + 2.0]

            shell = filleted(shell, rims, float(p["rim_r"]), f"{half}'s rims")
        parts, drawn = half_parts(recipe, layout, all_rooms, half)
        drawn_all[half] = drawn
        say(f"{half}: " + ", ".join(f"{v} {k}" for k, v in drawn.items()))
        say(f"{half}: fusing the features")
        feats = rc.union(parts, f"{half}'s features") if parts else None
        say(f"{half}: fusing them onto the shell")
        body = rc.union([shell, feats], f"{half}'s shell and features") if feats is not None else shell
        say(f"{half}: fused, {body.Volume() / 1e3:.0f} cm3, valid {body.isValid()}")
        # (the roots' fillets are a pass of their own, `roots_pass`: inside the build, OCC's fillet crashed the process
        # once the fins were on, `param4` and `param5`, 12 October 09:15-09:20; a crash there loses nothing)
        meshes[half] = rc.mesh_body([body], layout, all_rooms, half)
        beyond = cq.Solid.makeBox(4000.0, 4000.0, 1000.0, cq.Vector(-2000.0, -2000.0, z_split if lower else z_split - 1000.0))
        body = body.cut(beyond)
        organic[half] = body
        for name, tool in rc.exact_cuts(layout, all_rooms, half):
            cut = body.cut(tool)
            if not cut.isValid():
                say(f"{half}: the cut '{name}' left the body invalid")
            body = cut
        tidy = body.clean()
        if tidy.isValid() and abs(tidy.Volume() - body.Volume()) < 1.0:
            body = tidy
        thin = rc.thin_faces(body)
        if thin:
            say(f"{half}: {len(thin)} faces under 0.5 mm wide, the narrowest: " + "; ".join(f"{w:.3f} mm {k} at {c_}" for w, c_, k in thin[:5]))
        solids = sorted(body.Solids(), key=lambda x: x.Volume(), reverse=True)
        if len(solids) > 1:
            say(f"{half}: {len(solids) - 1} loose pieces dropped, {sum(x.Volume() for x in solids[1:]) / 1e3:.1f} cm3")
        body = solids[0]
        if lower:
            held = []
            for m in layout["mounts"]:
                ring = cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]).cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
                if body.intersect(ring).Volume() > 0.6 * ring.Volume():
                    held.append(m)
        halves[half] = body
        say(f"{half}: drawn in {time.time() - t1:.0f} s: {len(body.Faces())} faces, {body.Volume() / 1e3:.0f} cm3, valid {body.isValid()}")
    import mesh_route as mr

    bearings, bolts, mounts = layout["bearings"], layout["bolts"], layout["mounts"]
    names = {half: convex._name_faces(shape, bearings, bolts, mounts, [], z_split, s, []) for half, shape in halves.items()}
    files = {}
    for half, shape in halves.items():
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{stem}_{half}.step"))
        shape.exportBrep(str(OUT / f"{stem}_{half}.brep"))
        tm = mr.to_trimesh(meshes[half])
        tm.export(str(OUT / f"{stem}_{half}.stl"))
        tm.export(str(OUT / f"{stem}_{half}.ply"))
        files[half] = f"{stem}_{half}.stl"
        say(f"{half}: FE's mesh, {len(tm.faces):,} triangles, watertight {tm.is_watertight}, {tm.volume / 1e3:.0f} cm3 (the B-rep {shape.Volume() / 1e3:.0f})")
    mass = {half: shape.Volume() * s["density"] for half, shape in halves.items()}
    record = {**layout, "stem": stem, "form": "outcome", "drawing": "param", "route": "brep", "skin_bosses": False, "outcome_of": run,
              "recipe": f"{stem}_recipe.json", "drawn": drawn_all, "bolts": bolts, "mounts": held, "mounts_layout": mounts,
              "mass_kg": {**mass, "total": sum(mass.values())}, "faces": {half: {str(k): v for k, v in nm.items()} for half, nm in names.items()},
              "seconds": time.time() - t0, "files": files, "brep": {half: f"{stem}_{half}.brep" for half in halves}}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1, default=list), encoding="utf-8")
    files_o = {}
    for half, shape in organic.items():
        shape.exportBrep(str(OUT / f"{stem}_organic_{half}.brep"))
        mr.tessellated(shape, 0.1).export(str(OUT / f"{stem}_organic_{half}.stl"))
        files_o[half] = f"{stem}_organic_{half}.stl"
    mass_o = {half: shape.Volume() * s["density"] for half, shape in organic.items()}
    shown = {**record, "stem": f"{stem}_organic", "form": "organic", "organic_of": stem, "mass_kg": {**mass_o, "total": sum(mass_o.values())},
             "files": files_o, "brep": {half: f"{stem}_organic_{half}.brep" for half in organic}}  # fmt: skip
    (OUT / f"{stem}_organic.json").write_text(json.dumps(shown, indent=1, default=list), encoding="utf-8")
    say(f"{stem}: {record['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f}); {len(held)} of {len(mounts)} "
        f"mounts held; drawn in {record['seconds']:.0f} s; the recipe: {stem}_recipe.json")  # fmt: skip
    return record


def roots_pass(stem: str) -> None:
    """The roots' fillets on a built design's B-rep, a pass of its own (run as its own process: OCC's fillet can
    crash it, and then the design stays as built): each half's concave edges where a rib, a fin or a boss meets the
    face it stands on (`roots`), filleted at the recipe's `root_r` (`filleted`); its STEP and B-rep written again,
    the sharp ones kept as `<stem>_<half>_sharp.*`."""
    rec = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    recipe = json.loads((OUT / rec["recipe"]).read_text(encoding="utf-8"))
    r = float(recipe["params"].get("root_r") or 0.0)
    if r <= 0:
        return
    s = rec["settings"]
    spec, _ = load_and_validate(convex.CONTRACT)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(complete_chain(spec), value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    z_split, wall, t_f = float(rec["z"]["split"]), float(s["wall"]), float(s["flange_thickness"])
    for half in ("motor_side", "cover"):
        out = -1.0 if half == "motor_side" else 1.0
        body = cq.Shape.importBrep(str(OUT / f"{stem}_{half}.brep"))
        levels = sorted({round(float(q["far"]) + out * wall, 3) for q in cupmod.pieces(all_rooms, z_split, half)}
                        | {round(z_split + out * t_f, 3), round(z_split + out * wall, 3)})  # fmt: skip
        done = filleted(body, lambda sh, lv=levels, o=out: roots(sh, lv, o), r, f"{half}'s roots")
        if done is body or not done.isValid():
            continue
        body.exportBrep(str(OUT / f"{stem}_{half}_sharp.brep"))
        done.exportBrep(str(OUT / f"{stem}_{half}.brep"))
        cq.exporters.export(cq.Workplane().add(done), str(OUT / f"{stem}_{half}.step"))
        say(f"{half}: the roots filleted, {done.Volume() / 1e3:.0f} cm3 (was {body.Volume() / 1e3:.0f}), {len(done.Faces())} faces; STEP written")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--roots":
        roots_pass(args[1])
        sys.exit(0)
    recipe = None
    if "--recipe" in args:
        i = args.index("--recipe")
        recipe = args[i + 1]
        args = args[:i] + args[i + 2 :]
    build(args[0], args[1], recipe)
