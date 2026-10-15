"""PROTOTYPE (LOP) - not product code: the housing in its lobed form, one pod per shaft.

The convex form (shell.py) wraps all three shafts in one hull between two planar end walls at the
housing's extremes, so a bearing whose shaft ends early sits deep inside on a long tube, and the
end walls are large flat plates. A reducer housing is lobed instead: it follows each shaft.

- **A pod per shaft:** the hull of that shaft's gears (and the differential, and for the output the
  sump) grown by the least radial clearance, walled; with the bosses of its two bearings; spanning
  that shaft's own length (its housing faces from the layout). The pods fused make the housing, so
  each end wall steps to its own shaft's end and every boss is short.
- The rest as the convex form: the cavity (the pods' inner hulls), seats and shoulders, seal bores,
  the split across the shafts with a flange on each half (the pods' outlines grown by the flange's
  width, bolts on each pod's bolt line except where another pod covers them), the mounts on the
  outline's extremes, the motor ring round the input's motor-side face.

Run: uv run python prototypes/first_loop/lobed.py [stem]     (default: lobed)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import shell as convex  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import cylinder, fuse, hull_of_circles, prism  # noqa: E402

OUT = ROOT / "data" / "first_loop"
say = convex.say


def _in_poly(poly, x, y) -> bool:
    return convex._in_poly(list(poly), x, y)


def _ray_hit(outline, axis, angle):
    """Where the ray from `axis` at `angle` leaves the outline polygon (the farthest crossing)."""
    ox, oy = axis
    dx, dy = math.cos(angle), math.sin(angle)
    best = None
    n = len(outline)
    for i in range(n):
        (x1, y1), (x2, y2) = outline[i], outline[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - ox) * ey - (y1 - oy) * ex) / den
        u = ((x1 - ox) * dy - (y1 - oy) * dx) / den
        if t > 0 and 0.0 <= u <= 1.0 and (best is None or t > best):
            best = t
    return None if best is None else (ox + best * dx, oy + best * dy)


def _outline_in(pod, wall, w):
    """The pod's outline drawn `w` nearer its axis: the inner edge of a rim of width `w`."""
    return hull_of_circles(
        [(cx, cy, r + wall - w) for cx, cy, r in pod["cavity"]]
        + [(bx, by, r - w) for bx, by, r in pod["bosses"]]
    )


OUTLINE_CLEAR = 1.0  # mm: a pod's outline passes this far outside its bosses' cylinders
HEAL_MM = 0.5  # mm: strip and spot faces narrower than this are healed away before meshing
SNAP_ENDS = 3.0  # mm: same-side pod ends, or overlapping bosses' inner ends, this near are one plane
SNAP_WALL = 2.0  # mm: a wall's inside face this near another construction plane moves onto it


def _surface_meshes(shape, size: float = 8.0) -> bool:
    """Whether gmsh meshes the shape's surface and fills it with tetrahedra (a heal can leave two
    faces lying on each other, which the volume mesher refuses)."""
    import tempfile

    import gmsh

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "probe.brep"
        shape.exportBrep(str(path))
        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.occ.importShapes(str(path))
            gmsh.model.occ.synchronize()
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.option.setNumber("Mesh.MeshSizeMin", 1.2)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
            gmsh.option.setNumber("Mesh.Algorithm3D", 10)
            gmsh.model.mesh.generate(3)
            return True
        except Exception:  # noqa: BLE001 - any meshing failure refuses the heal
            return False
        finally:
            gmsh.finalize()


def snap_planes(pods, bearings, end_side, s) -> None:
    """No two construction planes a sliver apart (fastcae's lesson of 29 September: the mesher's
    slivers are born on narrow faces, and a stiffness full of them is more than a single-precision
    factor can precondition). Mutates the pods' ends, `end_side` (the walls' thicknesses) and each
    bearing's `boss_end` (where its boss stops inside the housing):
    - pods' ends on the same side within SNAP_ENDS: all to the outermost of them;
    - a wall's inside face within SNAP_WALL of a seat's end or of another pod's end or inside face:
      onto that plane (the wall at least 3 mm);
    - two bosses that overlap in plan, their inner ends within SNAP_ENDS: both to the one further in.
    """
    for k, side in ((0, "-z"), (1, "+z")):
        ends = sorted(pods, key=lambda p: p["z"][k])
        for i, p in enumerate(ends):
            for q in ends[i + 1 :]:
                if abs(q["z"][k] - p["z"][k]) < SNAP_ENDS:
                    outer = min(p["z"][k], q["z"][k]) if side == "-z" else max(p["z"][k], q["z"][k])
                    for r in (p, q):
                        z = list(r["z"])
                        z[k] = outer
                        r["z"] = tuple(z)
    moved = []
    for p in pods:
        for k, side in ((0, "-z"), (1, "+z")):
            sign = 1.0 if side == "-z" else -1.0
            face = p["z"][k] + sign * end_side[(p["shaft"], side)]
            planes = [z for b in bearings for z in b["z"]]
            planes += [q["z"][j] for q in pods if q is not p for j in (0, 1)]
            planes += [q["z"][j] + (1.0 if j == 0 else -1.0) * end_side[(q["shaft"], "-z" if j == 0 else "+z")] for q in pods if q is not p for j in (0, 1)]
            near = [z for z in planes if 1e-6 < abs(z - face) < SNAP_WALL]
            if near:
                target = min(near, key=lambda z: abs(z - face))
                t = abs(target - p["z"][k])
                # a snap only ever thickens a wall (never trades stiffness for a clean mesh)
                if t >= end_side[(p["shaft"], side)]:
                    end_side[(p["shaft"], side)] = t
                    moved.append(f"{p['shaft']} {side} wall {abs(face - p['z'][k]):.2f} -> {t:.2f} mm")
    for b in bearings:
        b["boss_end"] = b["z"][1] if b["side"] == "-z" else b["z"][0]
    for i, a in enumerate(bearings):
        for c in bearings[i + 1 :]:
            if a["side"] != c["side"]:
                continue
            reach = a["D"] / 2 + c["D"] / 2 + 2 * s["boss"]
            if math.dist(a["axis"], c["axis"]) >= reach or abs(a["boss_end"] - c["boss_end"]) >= SNAP_ENDS:
                continue
            further = max(a["boss_end"], c["boss_end"]) if a["side"] == "-z" else min(a["boss_end"], c["boss_end"])
            a["boss_end"] = c["boss_end"] = further
            moved.append(f"bosses {a['shaft']}/{c['shaft']} {a['side']} end at {further:.2f}")
    if moved:
        say("planes snapped: " + "; ".join(moved))


def trade_forms(s, pods, bearings, mounts, bolts, z_split):
    """The trade's forms on the lobed shell, from the settings (LOP-7; the trade-and-art note,
    section 5): spokes from every boss to its pod's rim (`wheel`), a rim standing on each end face's
    perimeter (`wheel.rim_width/rim_depth`), ribs between neighbouring bosses along the lines of
    centres (`delta`), and gussets along the lobes from the flange lip to the end face
    (`gussets`). Spokes and delta ribs come back as rib records for the rib builder; rims and
    gussets as (polygon, z0, z1) prisms. The input pod's motor side is left to the motor."""
    pod_of = {p["shaft"]: p for p in pods}
    wall = s["wall"]
    ribs, prisms = [], []

    def faces_of(pod):
        for side in ("-z", "+z"):
            if pod["shaft"] == "input" and side == "-z":
                continue  # the motor's flange plate and ring sit there
            yield side, pod["tops"][side]

    wheel = s.get("wheel")
    if wheel:
        for b in bearings:
            pod = pod_of[b["shaft"]]
            side = b["side"]
            if pod["shaft"] == "input" and side == "-z":
                continue
            z_end = pod["tops"][side]
            start = b["D"] / 2 + s["boss"] - 2.0
            for k in range(wheel["count"]):
                a = 2 * math.pi * (k + 0.5) / wheel["count"]
                rim = _ray_hit(pod["outer"], b["axis"], a)
                first = (b["axis"][0] + start * math.cos(a), b["axis"][1] + start * math.sin(a))
                if rim is None or math.dist(first, rim) < 6.0:
                    continue
                # On a dished face the spoke stands on the cone: its prism reaches from the
                # plateau's height out by `depth`, and down to the rim's level.
                ribs.append({"face": side, "a": first, "b": rim, "height": wheel["depth"] + pod["rise"][side],
                             "thickness": wheel["thickness"], "z_base": z_end, "pod": b["shaft"]})  # fmt: skip
        if wheel.get("rim_width"):
            for pod in pods:
                inner = _outline_in(pod, wall, wheel["rim_width"])
                for side, z_end in faces_of(pod):
                    z0, z1 = (z_end - wheel["rim_depth"], z_end + 1.0) if side == "-z" else (z_end - 1.0, z_end + wheel["rim_depth"])
                    prisms.append(("rim", pod["outer"], inner, z0, z1))
    delta = s.get("delta")
    if delta:
        axes = {b["shaft"]: b["axis"] for b in bearings}
        radii = {(b["shaft"], b["side"]): b["D"] / 2 + s["boss"] - 2.0 for b in bearings}
        for sa, sb in (("input", "intermediate"), ("intermediate", "output"), ("input", "output")):
            for side in ("-z", "+z"):
                if side == "-z" and "input" in (sa, sb):
                    continue
                za, zb = pod_of[sa]["tops"][side], pod_of[sb]["tops"][side]
                if abs(za - zb) > delta["depth"]:
                    continue  # the faces step too far apart for one rib
                (ax, ay), (bx, by) = axes[sa], axes[sb]
                length = math.hypot(bx - ax, by - ay)
                ux, uy = (bx - ax) / length, (by - ay) / length
                ra, rb = radii[(sa, side)], radii[(sb, side)]
                base = min(za, zb) if side == "-z" else max(za, zb)
                ribs.append({"face": side, "a": (ax + ux * ra, ay + uy * ra), "b": (bx - ux * rb, by - uy * rb),
                             "height": delta["depth"] + abs(za - zb), "thickness": delta["thickness"],
                             "z_base": base, "pods": [sa, sb]})  # fmt: skip
    lattice = s.get("lattice")
    if lattice:
        # GRM's cross-hatched lattice (OED2023 slide 13): two families of straight ribs across
        # each end face, `pitch` apart, at `angle` and `angle + 90` degrees, clipped to the pod's
        # outline by the rib builder, with a rim round the face (`rim_width`, `rim_depth`).
        for pod in pods:
            axis = next(b["axis"] for b in bearings if b["shaft"] == pod["shaft"])
            for side, z_end in faces_of(pod):
                if side not in lattice.get("sides", ("-z", "+z")):
                    continue
                for k_dir in (0, 1):
                    a = math.radians(lattice.get("angle", 0.0) + 90.0 * k_dir)
                    tx, ty = math.cos(a), math.sin(a)
                    nx, ny = -ty, tx
                    reach = max(math.dist(axis, pt) for pt in pod["outer"]) + 5.0
                    count = int(reach // lattice["pitch"])
                    for i in range(-count, count + 1):
                        d = (i + 0.5 * lattice.get("offset", 0.0)) * lattice["pitch"]
                        cx_, cy_ = axis[0] + d * nx, axis[1] + d * ny
                        ribs.append({"face": side, "a": (cx_ - reach * tx, cy_ - reach * ty),
                                     "b": (cx_ + reach * tx, cy_ + reach * ty), "height": lattice["depth"],
                                     "thickness": lattice["thickness"], "z_base": z_end, "pod": pod["shaft"]})  # fmt: skip
                if lattice.get("rim_width"):
                    inner = _outline_in(pod, wall, lattice["rim_width"])
                    z0, z1 = (z_end - lattice["rim_depth"], z_end + 1.0) if side == "-z" else (z_end - 1.0, z_end + lattice["rim_depth"])
                    prisms.append(("rim", pod["outer"], inner, z0, z1))
                if lattice.get("skin"):
                    # A skin closing the lattice: the end wall becomes a box of two skins and the
                    # ribs as its webs (a cored double wall, castable in a printed sand mould).
                    # The motor's room and the half-shafts' room are cut from it like the ribs.
                    t = lattice["skin"]
                    top = z_end + lattice["depth"] if side == "+z" else z_end - lattice["depth"]
                    z0, z1 = (top - t, top) if side == "+z" else (top, top + t)
                    prisms.append(("skin", pod["outer"], None, z0, z1))
    inner = s.get("inner_lattice")
    if inner:
        # The same crossing ribs on each end wall's inside face, `depth` into the housing; the rib
        # builder clips them to the pod's cavity outline and keeps them out of the gears', the
        # carrier's and the shafts' room (rib["inner"]).
        sides_wanted = inner.get("sides", ("-z", "+z"))
        for pod in pods:
            axis = next(b["axis"] for b in bearings if b["shaft"] == pod["shaft"])
            for side in sides_wanted:
                z_in = pod["tops"][side] + (pod["thick"][side] if side == "-z" else -pod["thick"][side])
                # an inside rib on a -z wall stands towards +z: built as a "+z" rib on z_in
                face = "+z" if side == "-z" else "-z"
                for k_dir in (0, 1):
                    a = math.radians(inner.get("angle", 0.0) + 90.0 * k_dir)
                    tx, ty = math.cos(a), math.sin(a)
                    nx, ny = -ty, tx
                    reach = max(math.dist(axis, pt) for pt in pod["inner"]) + 5.0
                    count = int(reach // inner["pitch"])
                    for i in range(-count, count + 1):
                        d = (i + 0.5 * inner.get("offset", 0.0)) * inner["pitch"]
                        cx_, cy_ = axis[0] + d * nx, axis[1] + d * ny
                        ribs.append({"face": face, "a": (cx_ - reach * tx, cy_ - reach * ty),
                                     "b": (cx_ + reach * tx, cy_ + reach * ty), "height": inner["depth"],
                                     "thickness": inner["thickness"], "z_base": z_in, "pod": pod["shaft"], "inner": True})  # fmt: skip
                if inner.get("skin"):
                    # The inside skin, closing the inside lattice into a box; it is a rib record
                    # too, so that the builder keeps it inside the cavity and out of the parts' room.
                    t = inner["skin"]
                    top = z_in + inner["depth"] if face == "+z" else z_in - inner["depth"]
                    ribs.append({"face": face, "skin": True, "outline": pod["inner"], "z_base": top - t if face == "+z" else top,
                                 "height": t, "pod": pod["shaft"], "inner": True})  # fmt: skip
    hoops = s.get("hoops")
    if hoops:
        # Rings round each lobe's side wall (the hoops of a barrel), `count` per half between the
        # flange and the end wall, `height` proud of the wall and `thickness` along it: they keep
        # the lobes' sections from ovalising under the seats' radial loads.
        t_f = s["flange_thickness"]
        for pod in pods:
            grown = hull_of_circles([(cx, cy, r + wall + hoops["height"]) for cx, cy, r in pod["cavity"]] + [(bx, by, r + hoops["height"]) for bx, by, r in pod["bosses"]])
            for lo_, hi_ in ((pod["tops"]["-z"] + pod["thick"]["-z"], z_split - t_f), (z_split + t_f, pod["tops"]["+z"] - pod["thick"]["+z"])):
                n = hoops["count"]
                for k in range(n):
                    zc = lo_ + (k + 0.5) * (hi_ - lo_) / n
                    prisms.append(("hoop", grown, pod["outer"], zc - hoops["thickness"] / 2, zc + hoops["thickness"] / 2))
    gussets = s.get("gussets")
    if gussets:
        t_f = s["flange_thickness"]
        for pod in pods:
            axis = next(b["axis"] for b in bearings if b["shaft"] == pod["shaft"])
            others = [q["outer"] for q in pods if q["shaft"] != pod["shaft"]]
            for side, z_end in faces_of(pod):
                z0, z1 = (z_end - gussets["depth"], z_split - t_f) if side == "-z" else (z_split + t_f, z_end + gussets["depth"])
                count = int(round(360.0 / gussets["every_deg"]))
                for k in range(count):
                    a = 2 * math.pi * (k + 0.5) / count
                    p = _ray_hit(pod["outer"], axis, a)
                    if p is None or any(_in_poly(o, *p) for o in others):
                        continue
                    nx, ny = math.cos(a), math.sin(a)
                    far = (p[0] + nx * gussets["out"], p[1] + ny * gussets["out"])
                    # A bolt's hole must clear the plate: its centre at least the hole's radius,
                    # the plate's half thickness and 4 mm from the plate's line.
                    clear = s["bolt_hole"] / 2 + gussets["thickness"] / 2 + 4.0
                    if any(abs((c[0] - p[0]) * ny - (c[1] - p[1]) * nx) < clear and -clear < (c[0] - p[0]) * nx + (c[1] - p[1]) * ny < gussets["out"] + clear for c in bolts):
                        continue  # a bolt sits on this line of the flange
                    near = (p[0] - nx * 2.0, p[1] - ny * 2.0)
                    t = gussets["thickness"] / 2
                    poly = [(near[0] - ny * t, near[1] + nx * t), (far[0] - ny * t, far[1] + nx * t),
                            (far[0] + ny * t, far[1] - nx * t), (near[0] + ny * t, near[1] - nx * t)]  # fmt: skip
                    prisms.append(("gusset", poly, None, z0, z1))
    return ribs, prisms


def build(stem: str = "lobed", ribs: list | None = None, overrides: dict | None = None) -> dict:
    s = {**convex.SETTINGS, **(overrides or {})}
    spec, refusals = load_and_validate(convex.CONTRACT)
    assert refusals == [], refusals
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial = value_in(gaps.min_radial_clearance, "mm")
    sealed = {(e.shaft, e.side.value) for e in gaps.sealed_ends}
    wall = s["wall"]
    end = s.get("end_wall", wall)
    # The end walls' thickness per pod and side (`end_walls`: shaft -> mm, or shaft -> {side: mm}),
    # else `end_wall` for all. A thicker wall grows inward, into the room behind the bearings.
    def _wall(shaft, side):
        given = s.get("end_walls", {}).get(shaft, end)
        return float(given.get(side, end)) if isinstance(given, dict) else float(given)

    end_side = {(sh, sd): _wall(sh, sd) for sh in ("input", "intermediate", "output") for sd in ("-z", "+z")}
    end_of = {sh: end_side[(sh, "-z")] for sh in ("input", "intermediate", "output")}

    pods, bearings = [], []
    for stack in chain.layout.shafts:
        x, y = stack.axis
        cavity, bosses = [], []
        for p in stack.parts:
            if p.kind in ("gear", "carrier"):
                cavity.append((x, y, p.diameter / 2 + radial))
            elif p.kind == "bearing":
                side = p.name.rsplit(" ", 1)[-1]
                choice = chain.bearings.get((stack.shaft, side))
                bearings.append(
                    {
                        "shaft": stack.shaft,
                        "side": side,
                        "axis": (x, y),
                        "D": p.diameter,
                        "d": choice.bearing.d if choice else p.diameter / 2,
                        "z": (p.z_min, p.z_max),
                        "sealed": (stack.shaft, side) in sealed,
                        "designation": choice.bearing.designation if choice else "guess",
                    }
                )
                bosses.append((x, y, p.diameter / 2 + s["boss"]))
        if stack.shaft == "output":
            tip = max(p.diameter for p in stack.parts if p.kind == "gear")
            floor = y + tip / 2 + s["sump"]
            cavity.append((x, floor - 25.0, 25.0))
        pods.append(
            {
                "shaft": stack.shaft,
                "cavity": cavity,
                "bosses": bosses,
                "inner": hull_of_circles(cavity),
                # The bosses' circles drawn 1 mm wider in the outline: the outline is a polygon,
                # and where its chords ran along a boss's true cylinder of the same radius the two
                # crossed in hairline faces (0.02-0.03 mm), the slivers of the mesh (11:40).
                # the side wall per pod (`walls`: shaft -> mm), else `wall`
                "outer": hull_of_circles([(cx, cy, r + s.get("walls", {}).get(stack.shaft, wall)) for cx, cy, r in cavity] + [(bx, by, r + OUTLINE_CLEAR) for bx, by, r in bosses]),
                "z": tuple(stack.ends),
            }
        )
    snap_planes(pods, bearings, end_side, s)
    z_lo = min(p["z"][0] for p in pods)
    z_hi = max(p["z"][1] for p in pods)
    body = fuse([prism(p["outer"], *p["z"]) for p in pods])
    body = body.cut(fuse([prism(p["inner"], p["z"][0] + end_side[(p["shaft"], "-z")], p["z"][1] - end_side[(p["shaft"], "+z")]) for p in pods]))
    pod_of = {p["shaft"]: p for p in pods}
    axis_of = {b["shaft"]: b["axis"] for b in bearings}
    # The dish (the trade-and-art note, family 3): a pod's end wall as a shallow cone from its
    # rim up to a plateau on the boss, the wall `end` thick along the cone's normal, so the thrust
    # goes into the cone as membrane force. `tops` are each pod's outermost z per side, the
    # plateau where it is dished, the flat end face where it is not.
    dish = s.get("dish")
    for p in pods:
        p["rise"] = {"-z": 0.0, "+z": 0.0}
        p["tops"] = {"-z": p["z"][0], "+z": p["z"][1]}
        p["end"] = end_of[p["shaft"]]
    if dish:
        for shaft, side in dish["faces"]:
            pod = pod_of[shaft]
            pod["rise"][side] = float(dish["rise"])
            pod["tops"][side] = pod["z"][1] + dish["rise"] if side == "+z" else pod["z"][0] - dish["rise"]
        # A dome covers its pod's whole outline, which overlaps the neighbouring pods: it is
        # kept out of their cavities, and out of the motor's and the half-shafts' room.
        all_cavities = fuse([prism(q["inner"], q["z"][0] + end, q["z"][1] - end) for q in pods])
        motor_room = cylinder(axis_of["input"], z_lo - 400, pod_of["input"]["z"][0] + 0.5, s["motor_ring"][1] + 30)
        shaft_room = cylinder(axis_of["output"], z_lo - 400, z_hi + 400, 90.0)
        for p in pods:
            axis = axis_of[p["shaft"]]
            for side in ("-z", "+z"):
                h = p["rise"][side]
                if h <= 0:
                    continue
                z_end = p["z"][1] if side == "+z" else p["z"][0]
                sign = 1.0 if side == "+z" else -1.0
                way = cq.Vector(0, 0, sign)
                r_apex = max(r for _, _, r in p["bosses"])
                r_rim = max(math.dist(axis, pt) for pt in p["outer"]) + 1.0
                alpha = math.atan2(h, r_rim - r_apex)  # the cone's slope from the end plane
                t_plane = end / math.sin(alpha)  # the wall, measured in the plane
                # The cones start 1 mm inside the end wall, so no face of theirs lies on the
                # end face (a boolean on coincident faces is fragile); fuzzy booleans for the rest.
                lap = 1.0
                base = cq.Vector(axis[0], axis[1], z_end - sign * lap)
                grow = lap / math.tan(alpha)
                outer = cq.Solid.makeCone(r_rim + grow, r_apex, h + lap, pnt=base, dir=way)
                inner = cq.Solid.makeCone(
                    r_rim - t_plane + grow, max(r_apex - end * math.tan(alpha / 2), 1.0), h - end + lap, pnt=base, dir=way
                )
                span = (z_end - lap - 1.0, z_end + h + 1.0) if side == "+z" else (z_end - h - 1.0, z_end + lap + 1.0)
                dome = outer.intersect(prism(p["outer"], *span)).cut(all_cavities).cut(shaft_room)
                if side == "-z":
                    dome = dome.cut(motor_room)
                hollow = inner.intersect(prism(p["inner"], *span))
                # The flat end wall it replaces, within the cavity and the cone's base.
                old = (z_end - end - 1.0, z_end + 1e-3) if side == "+z" else (z_end - 1e-3, z_end + end + 1.0)
                flat = cylinder(axis, *old, 2 * (r_rim - t_plane)).intersect(prism(p["inner"], *old))
                before = body.Volume()
                body = body.fuse(dome, tol=0.01)
                say(f"  fused: {body.ShapeType()} of {len(body.Solids())} solids, valid {body.isValid()}, {body.Volume() / 1e3:.0f} cm3")
                body = body.cut(hollow, tol=0.01)
                say(f"  hollowed: {body.ShapeType()} of {len(body.Solids())} solids, valid {body.isValid()}, {body.Volume() / 1e3:.0f} cm3")
                body = body.cut(flat, tol=0.01)
                say(
                    f"dish {p['shaft']} {side}: rise {h:.0f}, cone slope {math.degrees(alpha):.0f} deg, "
                    f"dome {dome.Volume() / 1e3:.0f} cm3, hollow {hollow.Volume() / 1e3:.0f}, flat {flat.Volume() / 1e3:.0f}; "
                    f"body {before / 1e3:.0f} -> {body.Volume() / 1e3:.0f} cm3"
                )
    # The collar (family 6): the end wall thicker round each boss, a disc of `ratio` times the
    # seat's diameter standing `thickness - end` proud of the face; the bores are cut below.
    collar = s.get("collar")
    for p in pods:
        p["thick"] = {"-z": end_side[(p["shaft"], "-z")], "+z": end_side[(p["shaft"], "+z")]}
    if collar:
        for b in bearings:
            pod = pod_of[b["shaft"]]
            side = b["side"]
            extra = collar["thickness"] - pod["end"]
            if (pod["shaft"] == "input" and side == "-z") or extra <= 0:
                continue
            z_end = pod["tops"][side]
            z0, z1 = (z_end - 1.0, z_end + extra) if side == "+z" else (z_end - extra, z_end + 1.0)
            body = body.fuse(cylinder(b["axis"], z0, z1, collar["ratio"] * b["D"]))
            pod["tops"][side] = z_end + extra if side == "+z" else z_end - extra
            pod["thick"][side] = collar["thickness"]
    say(f"shell with its end walls: {body.Volume() / 1e3:.0f} cm3")
    for b in bearings:
        lo, hi = pod_of[b["shaft"]]["tops"]["-z"], pod_of[b["shaft"]]["tops"]["+z"]
        if b["side"] == "-z":
            body = body.fuse(cylinder(b["axis"], lo, b["boss_end"], b["D"] + 2 * s["boss"]))
        else:
            body = body.fuse(cylinder(b["axis"], b["boss_end"], hi, b["D"] + 2 * s["boss"]))
    # Gussets at each boss's root, inside the housing (Son 2019's rib, a ring of them): triangular
    # plates in radial planes between the boss's tube and the end wall's inner face, within the
    # room behind the bearing, where no gear is. They carry the seat's moment into the wall at a
    # larger radius instead of bending the wall round the bore.
    gin = s.get("inner_gussets")
    if gin:
        # Every gear's and the carrier's room, grown by the least clearances: no gusset enters it.
        axial = value_in(gaps.min_axial_clearance, "mm") if getattr(gaps, "min_axial_clearance", None) else 3.0
        rooms = fuse([
            cylinder(st.axis, p.z_min - axial, p.z_max + axial, p.diameter + 2 * radial)
            for st in chain.layout.shafts for p in st.parts if p.kind in ("gear", "carrier")
        ])  # fmt: skip
        made = 0
        for b in bearings:
            pod = pod_of[b["shaft"]]
            z0, z1 = b["z"]
            r_boss = b["D"] / 2 + s["boss"]
            # From the end wall's inner face to the boss's inner end, beside the boss.
            if b["side"] == "-z":
                z_wall, z_tip = pod["tops"]["-z"] + pod["thick"]["-z"], z1
            else:
                z_wall, z_tip = pod["tops"]["+z"] - pod["thick"]["+z"], z0
            if abs(z_tip - z_wall) < 3.0:
                continue
            for k in range(gin["count"]):
                a = 2 * math.pi * (k + 0.5) / gin["count"]
                tri = (
                    cq.Workplane("XZ")
                    .polyline([(r_boss - 1.0, z_wall), (r_boss + gin["length"], z_wall), (r_boss - 1.0, z_tip)])
                    .close()
                    .extrude(gin["thickness"] / 2, both=True)
                    .val()
                )
                # Drawn in the x-z plane at the origin: turned to its angle, then moved to the axis.
                # The wall's own thickness is added to the triangle so that it fuses into the wall.
                tri = tri.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), math.degrees(a))
                tri = tri.translate(cq.Vector(b["axis"][0], b["axis"][1], 0))
                tri = tri.cut(rooms)
                if tri.wrapped.IsNull() or tri.Volume() < 1.0:
                    continue
                body = body.fuse(tri)
                made += 1
        say(f"inner gussets: {made} kept clear of the gears")
    say(f"with the bosses: {body.Volume() / 1e3:.0f} cm3")
    input_axis = next(st.axis for st in chain.layout.shafts if st.shaft == "input")
    z_motor = pod_of["input"]["z"][0]
    ring_in, ring_out = s["motor_ring"]
    t_ring = s["motor_ring_thickness"]
    ring = (
        cq.Workplane("XY", origin=(0, 0, z_motor - t_ring))
        .center(*input_axis)
        .circle(ring_out / 2)
        .circle(ring_in / 2)
        .extrude(t_ring)
        .val()
    )
    # The input's lobe is narrower than the motor's ring: a round flange plate on its motor-side
    # face, as wide as the ring, carries it (the motor's interface).
    body = body.fuse(cylinder(input_axis, z_motor, z_motor + end, ring_out))
    say(f"with the motor plate: {body.Volume() / 1e3:.0f} cm3, {len(body.Solids())} solids, valid {body.isValid()}")
    body = body.fuse(ring)
    say(f"with the motor ring: {body.Volume() / 1e3:.0f} cm3, {len(body.Solids())} solids, valid {body.isValid()}")
    # Mounts on the outline's extremes, each on the motor-side end of the pod it stands on.
    points = [(pt, p) for p in pods for pt in p["outer"]]
    cx = sum(pt[0] for pt, _ in points) / len(points)
    cy = sum(pt[1] for pt, _ in points) / len(points)
    mounts = []
    sides = s.get("mount_sides", ["-z", "-z", "-z"])
    for direction, side in zip(((-1.0, -0.6), (1.0, -0.4), (0.15, 1.0)), sides, strict=True):
        n = math.hypot(*direction)
        ux, uy = direction[0] / n, direction[1] / n
        far, pod = max(points, key=lambda q: (q[0][0] - cx) * ux + (q[0][1] - cy) * uy)
        centre = (far[0] + ux * s["mount_diameter"] * 0.25, far[1] + uy * s["mount_diameter"] * 0.25)
        if side == "-z":
            z0 = pod["z"][0] + 8.0
            z1 = z0 + s["mount_length"]
        else:
            z1 = pod["z"][1] - 8.0
            z0 = z1 - s["mount_length"]
        body = body.fuse(cylinder(centre, z0, z1, s["mount_diameter"]))
        say(f"with a mount on the {pod['shaft']} pod: {body.Volume() / 1e3:.0f} cm3, {len(body.Solids())} solids")
        mounts.append({"centre": centre, "z": (z0, z1), "normal": (ux, uy, 0.0), "pod": pod["shaft"]})
    # The split across the shafts and its bolts' positions, as the convex form's (the halves are
    # cut below; the gussets need the bolts now).
    first = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear" and p.name.startswith("s1")]
    second = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear" and p.name.startswith("s2")]
    z_split = (max(p.z_max for p in first) + min(p.z_min for p in second)) / 2
    for p in pods:
        assert p["z"][0] < z_split < p["z"][1], f"the split misses the {p['shaft']} pod"
    bolts = []
    for i, p in enumerate(pods):
        line = hull_of_circles([(cx_, cy_, r + wall + s["flange_bolt_axis"]) for cx_, cy_, r in p["cavity"]] + [(bx, by, r + s["flange_bolt_axis"]) for bx, by, r in p["bosses"]])
        for c in convex._along(line, s["bolt_pitch"]):
            covered = any(_in_poly(q["outer"], *c) for j, q in enumerate(pods) if j != i)
            near = any(math.dist(c, other) < 0.6 * s["bolt_pitch"] for other in bolts)
            if not covered and not near:
                bolts.append(c)
    # The trade's forms (LOP-7), then the ribs given: every added solid is kept out of the pods'
    # cavities, the motor's room and the half-shafts' room.
    forms_ribs, forms_prisms = trade_forms(s, pods, bearings, mounts, bolts, z_split)
    ribs = list(ribs or []) + forms_ribs
    cavities = fuse([prism(p["inner"], p["z"][0] + end, p["z"][1] - end) for p in pods])
    output_axis_xy = next(st.axis for st in chain.layout.shafts if st.shaft == "output")

    def _empty(solid) -> bool:
        try:
            return solid.wrapped.IsNull() or solid.Volume() < 1e-3
        except Exception:  # noqa: BLE001 - OCC raises on a null shape; that is "empty"
            return True

    def room(solid, face):
        """The solid kept out of the cavities and the motor's and half-shafts' room; None when
        nothing of it is left (a spoke wholly inside a neighbouring pod, for example)."""
        for cutter in (
            [cavities]
            + ([cylinder(input_axis, z_lo - 400, z_motor + 0.5, ring_out + 30)] if face == "-z" else [])
            + [cylinder(output_axis_xy, z_lo - 400, z_hi + 400, 90.0)]
        ):
            if _empty(solid):
                return None
            solid = solid.cut(cutter)
        return None if _empty(solid) else solid

    rib_boxes = []
    added = []
    keep_out = None
    if any(r.get("inner") for r in ribs):
        # The gears', the carrier's and the shafts' room, grown by the least clearances.
        axial_c = value_in(gaps.min_axial_clearance, "mm") if getattr(gaps, "min_axial_clearance", None) else 3.0
        parts_room = [
            cylinder(st.axis, p.z_min - axial_c, p.z_max + axial_c, p.diameter + 2 * radial)
            for st in chain.layout.shafts for p in st.parts if p.kind in ("gear", "carrier")
        ]  # fmt: skip
        diameters = {sec.shaft: sec.diameter for sec in chain.sections}
        shafts_room = [
            cylinder(st.axis, z_lo - 50, z_hi + 50, diameters.get(st.shaft, 50.0) + 2 * radial)
            for st in chain.layout.shafts
        ]
        # Each bearing is fitted from the split: its outside diameter's path from its seat to the
        # split stays open.
        fitting = [
            cylinder(b["axis"], *sorted((b["z"][1] if b["side"] == "-z" else b["z"][0], z_split)), b["D"] + 1.0)
            for b in bearings
        ]
        keep_out = fuse(parts_room + shafts_room + fitting)
    for rib in ribs:
        if rib.get("skin"):
            # An inside skin: a plate over the cavity's outline, `height` thick from `z_base`.
            z0 = rib["z_base"]
            solid = prism(rib["outline"], z0, z0 + rib["height"])
            solid = None if _empty(solid) else solid.cut(keep_out)
            if solid is not None and not _empty(solid):
                added.append(solid)
            continue
        (ax, ay), (bx, by) = rib["a"], rib["b"]
        length = math.hypot(bx - ax, by - ay)
        if length < 1.0:
            continue
        nx, ny = -(by - ay) / length, (bx - ax) / length
        t = rib["thickness"] / 2
        poly = [(ax + nx * t, ay + ny * t), (bx + nx * t, by + ny * t), (bx - nx * t, by - ny * t), (ax - nx * t, ay - ny * t)]
        base = rib.get("z_base", z_hi if rib["face"] == "+z" else z_lo)
        names_ = rib.get("pods") or [rib.get("pod")]
        if rib.get("inner"):
            # Inside: from the wall's inside face into the cavity, within the cavity's outline.
            z0, z1 = (base - 1.0, base + rib["height"]) if rib["face"] == "+z" else (base - rib["height"], base + 1.0)
            clip = fuse([prism(pod_of[n]["inner"], z_lo - 500, z_hi + 500) for n in names_ if n in pod_of])
            solid = prism(poly, z0, z1).intersect(clip)
            solid = None if _empty(solid) else solid.cut(keep_out)
            solid = None if solid is None or _empty(solid) else solid
            if solid is not None:
                added.append(solid)
                rib_boxes.append({"poly": poly, "z": (z0, z1)})
            continue
        # The rib's prism starts 1 mm inside the face, or at the rim's level on a dished face.
        into = 1.0 + max((pod_of[n]["rise"][rib["face"]] for n in (rib.get("pods") or [rib.get("pod")]) if n in pod_of), default=0.0)
        z0, z1 = (base - into, base + rib["height"]) if rib["face"] == "+z" else (base - rib["height"], base + into)
        outlines = [pod_of[n]["outer"] for n in names_ if n in pod_of] or [pods[0]["outer"]]
        clip = fuse([prism(o, z_lo - 500, z_hi + 500) for o in outlines])
        solid = room(prism(poly, z0, z1).intersect(clip), rib["face"])
        if solid is not None:
            added.append(solid)
            rib_boxes.append({"poly": poly, "z": (z0, z1)})
    for kind, outer, inner, z0, z1 in forms_prisms:
        solid = prism(outer, z0, z1)
        if inner is not None:
            solid = solid.cut(prism(inner, z0 - 1.0, z1 + 1.0))
        solid = room(solid, "-z" if z1 < z_split else "+z")
        if solid is not None:
            added.append(solid)
    if added:
        body = body.fuse(fuse(added))
        say(f"forms added: {len(ribs)} ribs, {len(forms_prisms)} rims and gussets")
    say(f"with the ring, mounts and forms: {body.Volume() / 1e3:.0f} cm3")
    body = body.clean()
    say(f"cleaned: {body.Volume() / 1e3:.0f} cm3")
    # Seats, shoulders, seal bores, holes.
    for b in bearings:
        z0, z1 = b["z"]
        pod = pod_of[b["shaft"]]
        lo, hi = pod["tops"]["-z"], pod["tops"]["+z"]
        t_lo, t_hi = pod["thick"]["-z"], pod["thick"]["+z"]
        # The seat's bore runs on to the boss's end where a snap moved it past the bearing, so no
        # membrane is left across the bore (the bearing's coupling still takes z0..z1 only).
        body = body.cut(cylinder(b["axis"], min(z0, b["boss_end"]), max(z1, b["boss_end"]), b["D"]))
        if b["side"] == "-z" and z0 > lo + t_lo + 0.5:
            body = body.cut(cylinder(b["axis"], lo + t_lo, z0 + 1e-3, b["D"] - 2 * s["shoulder"]))
        elif b["side"] == "+z" and z1 < hi - t_hi - 0.5:
            body = body.cut(cylinder(b["axis"], z1 - 1e-3, hi - t_hi, b["D"] - 2 * s["shoulder"]))
        if b["sealed"]:
            seal = b["d"] + 2 * s["seal_radial"]
            if b["side"] == "-z":
                body = body.cut(cylinder(b["axis"], lo - t_ring - 1.0, z0 + 1e-3, seal))
            else:
                body = body.cut(cylinder(b["axis"], z1 - 1e-3, hi + 1.0, seal))
    say(f"bored: {body.Volume() / 1e3:.0f} cm3")
    for m in mounts:
        body = body.cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
    motor_holes = []
    for k in range(s["motor_bolts"]):
        a = 2 * math.pi * k / s["motor_bolts"]
        c = (
            input_axis[0] + s["motor_bolt_circle"] / 2 * math.cos(a),
            input_axis[1] + s["motor_bolt_circle"] / 2 * math.sin(a),
        )
        body = body.cut(cylinder(c, z_motor - t_ring - 1.0, z_motor + end - 1.0, s["bolt_hole"]))
        motor_holes.append(c)
    body = body.clean()

    # The halves, cut at the split, each with its flange lip and the bolt holes.
    big = 2000.0
    lower = body.intersect(cq.Workplane("XY", origin=(0, 0, z_lo - 100)).rect(big, big).extrude(z_split - z_lo + 100).val())
    upper = body.intersect(cq.Workplane("XY", origin=(0, 0, z_split)).rect(big, big).extrude(z_hi + 100 - z_split).val())
    t_f = s["flange_thickness"]
    lips = [hull_of_circles([(cx_, cy_, r + wall + s["flange_width"]) for cx_, cy_, r in p["cavity"]] + [(bx, by, r + s["flange_width"]) for bx, by, r in p["bosses"]]) for p in pods]
    cavity_cut = fuse([prism(p["inner"], z_split - t_f - 1, z_split + t_f + 1) for p in pods])
    lower = lower.fuse(fuse([prism(lip, z_split - t_f, z_split) for lip in lips]).cut(cavity_cut)).clean()
    upper = upper.fuse(fuse([prism(lip, z_split, z_split + t_f) for lip in lips]).cut(cavity_cut)).clean()
    for c in bolts:
        lower = lower.cut(cylinder(c, z_split - t_f - 1, z_split + 1, s["bolt_hole"]))
        upper = upper.cut(cylinder(c, z_split - 1, z_split + t_f + 1, s["bolt_hole"]))
    lower, upper = lower.clean(), upper.clean()

    def one_body(shape, name):
        """The half as one solid: pieces of a form that the clearance cuts left free are dropped,
        and said (a floating piece would make the stiffness singular)."""
        solids = sorted(shape.Solids(), key=lambda x: x.Volume(), reverse=True)
        if len(solids) > 1:
            lost = sum(x.Volume() for x in solids[1:])
            say(f"{name}: {len(solids) - 1} loose pieces dropped, {lost / 1e3:.1f} cm3")
            return solids[0]
        return shape

    lower, upper = one_body(lower, "motor side"), one_body(upper, "cover")

    def healed(shape, name):
        """Strip and spot faces under HEAL_MM taken out (OCC's ShapeFix_FixSmallFace, then the
        same-domain faces unified): fastcae's repair, which trades the part's sub-millimetre
        detail for elements a single-precision factor can use (9 October 11:55)."""
        from OCP.ShapeFix import ShapeFix_FixSmallFace, ShapeFix_Shape
        from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

        fix = ShapeFix_FixSmallFace()
        fix.Init(shape.wrapped)
        fix.SetPrecision(HEAL_MM)
        fix.SetMaxTolerance(2 * HEAL_MM)
        fix.Perform()
        whole = ShapeFix_Shape(fix.FixShape())
        whole.Perform()
        unify = ShapeUpgrade_UnifySameDomain(whole.Shape(), True, True, True)
        unify.Build()
        out = cq.Shape.cast(unify.Shape())
        solids = out.Solids()
        if len(solids) != 1 or not out.isValid() or abs(out.Volume() - shape.Volume()) > 0.005 * shape.Volume():
            say(f"{name}: healing refused (solids {len(solids)}, valid {out.isValid()}); kept as built")
            return shape
        if not _surface_meshes(solids[0]):
            say(f"{name}: healing refused (its surface does not mesh: overlapping facets); kept as built")
            return shape
        say(f"{name}: healed, faces {len(shape.Faces())} -> {len(out.Faces())}, volume {(out.Volume() / shape.Volume() - 1) * 100:+.2f} %")
        return solids[0]

    lower, upper = healed(lower, "motor side"), healed(upper, "cover")
    say(f"lobed halves built: {len(bolts)} bolts on the flange; {lower.Volume() / 1e3:.0f} + {upper.Volume() / 1e3:.0f} cm3")

    names = {
        "motor_side": convex._name_faces(lower, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes),
        "cover": convex._name_faces(upper, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for half, shape in (("motor_side", lower), ("cover", upper)):
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{stem}_{half}.step"))
        shape.exportBrep(str(OUT / f"{stem}_{half}.brep"))
    mass = {half: shape.Volume() * s["density"] for half, shape in (("motor_side", lower), ("cover", upper))}
    result = {
        "stem": stem,
        "form": "lobed",
        "ribs": ribs or [],
        "settings": s,
        "z": {"lo": z_lo, "hi": z_hi, "split": z_split, "motor": z_motor},
        "pods": [{k: v for k, v in p.items()} for p in pods],
        "bearings": bearings,
        "mounts": mounts,
        "motor_holes": motor_holes,
        "bolts": bolts,
        "inner_outline": max((p["inner"] for p in pods), key=len),
        "outer_outline": max((p["outer"] for p in pods), key=len),
        "mass_kg": {**mass, "total": sum(mass.values())},
        "faces": {half: {str(k): v for k, v in n.items()} for half, n in names.items()},
    }
    (OUT / f"{stem}.json").write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    say(f"mass {result['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f})")
    return result


if __name__ == "__main__":
    build(*sys.argv[1:2])
