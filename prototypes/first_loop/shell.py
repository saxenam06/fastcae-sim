"""PROTOTYPE (LOP-1) - not product code: the plain housing, shell and wall, no ribs.

From the completed contract (the load tool's round: the layout, the selected bearings, the shaft
sections) and the volumes it fixes, build the EV two-stage reducer's housing as two halves split
across the shafts:

- the walls round the gears' cavity (the hull of every gear and the differential grown by the least
  radial clearance A19), with a sump under the output gear;
- the end walls, and a boss round each bearing from its seat to its end wall, with the seat (the
  bearing's outside Ø over its width) and a shoulder behind it;
- a seal bore through the end wall where a shaft leaves the housing (A17);
- the split across the shafts, between the two stages (the engineer, 9 Oct 02:12), with a flange
  on each half and the bolts through both;
- three mount bosses (A20) and the motor flange's bolt ring round the input (A25).

Every face of each half is then named by its role from the exact CAD geometry (a seat, a shoulder,
a bolt hole, a mount's hole, the motor's bolt holes, the split face, the wall), the halves are
written as STEP with their face names, and the mass is taken from the CAD.

Run: uv run python prototypes/first_loop/shell.py      (outputs in data/first_loop/)
"""

from __future__ import annotations

import json
import os
import math
import sys
import time
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import cylinder, hull_of_circles, prism  # noqa: E402

# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))
OUT = ROOT / "data" / "first_loop"

# The shell-and-wall tool's settings: the housing's own choices, each with where it comes from.
SETTINGS = {
    "end_wall": 6.0,  # mm: the end walls' own thickness (a lever: they bend like plates)
    "wall": 6.0,  # mm: sand casting, above the contract's least wall of 4 mm; Łódź's δ for a
    #               larger case is 7.5 mm
    "boss": 8.0,  # mm of wall round a bearing's seat (about 0.08·D + 1 for these bores, Łódź Ch. 9)
    "shoulder": 3.0,  # mm: how far the shoulder behind a seat stands in from the bore
    "sump": 26.0,  # mm under the output gear's tips: Łódź's H = A (the spaces review, low-medium)
    "flange_width": 24.0,  # mm beyond the wall for M8 (Łódź Table 9.1)
    "flange_bolt_axis": 13.0,  # mm from the wall to the bolts' axis (Łódź Table 9.1, M8)
    "flange_thickness": 9.0,  # mm per half: 1.5·δ at δ = 6 mm (Łódź Ch. 9)
    "bolt_hole": 9.0,  # mm: an M8 clearance hole
    "bolt_pitch": 90.0,  # mm between bolts along the flange (about 10·d plus the cones, Henkel)
    "seal_radial": 10.0,  # mm: a radial shaft seal's section past its shaft (ISO 6194 sizes)
    "mount_diameter": 36.0,  # mm: a mount boss (A20) for an M10 bolt
    "mount_hole": 11.0,  # mm: an M10 clearance hole
    "mount_length": 30.0,  # mm along the shafts
    "motor_ring": (126.0, 174.0),  # mm: the motor flange's ring, inner and outer Ø (A25)
    "motor_bolt_circle": 150.0,  # mm (A25)
    "motor_bolts": 6,  # (A25)
    "motor_ring_thickness": 12.0,  # mm, standing off the motor-side end wall (A25)
    "density": 2.6e-6,  # kg/mm³: EN AC-42100 T6 from the contract (2,600 kg/m³)
}


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def build(stem: str = "shell", ribs: list | None = None, overrides: dict | None = None) -> dict:
    """The housing; `ribs` stand on its end walls (LOP-4), `overrides` change its settings."""
    s = {**SETTINGS, **(overrides or {})}
    spec, refusals = load_and_validate(CONTRACT)
    assert refusals == [], refusals
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial = value_in(gaps.min_radial_clearance, "mm")
    sealed = {(e.shaft, e.side.value) for e in gaps.sealed_ends}
    if chain.refused:
        say(f"note: drawn with a guessed bearing at {sorted(chain.refused)} (none selected yet)")

    # The cavity's circles (end view), and the bosses' circles round the bearings.
    cavity, bosses, bearings = [], [], []
    output_axis, output_tip = None, 0.0
    for stack in chain.layout.shafts:
        x, y = stack.axis
        for p in stack.parts:
            if p.kind in ("gear", "carrier"):
                cavity.append((x, y, p.diameter / 2 + radial))
                if p.kind == "gear" and p.diameter > output_tip and stack.shaft == "output":
                    output_axis, output_tip = (x, y), p.diameter
            elif p.kind == "bearing":
                side = p.name.rsplit(" ", 1)[-1]
                choice = chain.bearings.get((stack.shaft, side))
                bore = choice.bearing.d if choice else p.diameter / 2
                bearings.append(
                    {
                        "shaft": stack.shaft,
                        "side": side,
                        "axis": (x, y),
                        "D": p.diameter,
                        "d": bore,
                        "z": (p.z_min, p.z_max),
                        "sealed": (stack.shaft, side) in sealed,
                        "designation": choice.bearing.designation if choice else "guess",
                    }
                )
                bosses.append((x, y, p.diameter / 2 + s["boss"]))
    # The sump: the floor stands the sump depth below the output gear's tips (+y is down here).
    ox, oy = output_axis
    floor = oy + output_tip / 2 + s["sump"]
    cavity.append((ox, floor - 25.0, 25.0))

    inner = hull_of_circles(cavity)
    outer = hull_of_circles([(x, y, r + s["wall"]) for x, y, r in cavity] + bosses)
    z_lo = min(st.ends[0] for st in chain.layout.shafts)
    z_hi = max(st.ends[1] for st in chain.layout.shafts)
    wall = s["wall"]
    end = s.get("end_wall", wall)
    say(f"outline: {len(outer)} points; housing from z {z_lo:.1f} to {z_hi:.1f} mm")

    body = prism(outer, z_lo, z_hi).cut(prism(inner, z_lo + end, z_hi - end))
    # Each bearing's boss runs from its end wall to the seat's inboard face.
    for b in bearings:
        z0, z1 = b["z"]
        if b["side"] == "-z":
            body = body.fuse(cylinder(b["axis"], z_lo, z1, b["D"] + 2 * s["boss"]))
        else:
            body = body.fuse(cylinder(b["axis"], z0, z_hi, b["D"] + 2 * s["boss"]))
    # The motor flange's ring stands off the motor-side end wall round the input (A25).
    input_axis = next(st.axis for st in chain.layout.shafts if st.shaft == "input")
    ring_in, ring_out = s["motor_ring"]
    t_ring = s["motor_ring_thickness"]
    ring = (
        cq.Workplane("XY", origin=(0, 0, z_lo - t_ring))
        .center(*input_axis)
        .circle(ring_out / 2)
        .circle(ring_in / 2)
        .extrude(t_ring)
        .val()
    )
    body = body.fuse(ring)
    # The mounts (A20): three bosses along the shafts on the motor-side half, half in the wall.
    mounts = []
    cx = sum(p[0] for p in outer) / len(outer)
    cy = sum(p[1] for p in outer) / len(outer)
    for direction in ((-1.0, -0.6), (1.0, -0.4), (0.15, 1.0)):
        n = math.hypot(*direction)
        ux, uy = direction[0] / n, direction[1] / n
        far = max(outer, key=lambda p: (p[0] - cx) * ux + (p[1] - cy) * uy)
        centre = (
            far[0] + ux * s["mount_diameter"] * 0.25,
            far[1] + uy * s["mount_diameter"] * 0.25,
        )
        z0, z1 = z_lo + 8.0, z_lo + 8.0 + s["mount_length"]
        body = body.fuse(cylinder(centre, z0, z1, s["mount_diameter"]))
        mounts.append({"centre": centre, "z": (z0, z1), "normal": (ux, uy, 0.0)})
    # Ribs (LOP-4): plates on the end walls' outer faces along straight paths, clipped to the
    # housing's outline and kept out of the room the motor and the half-shafts need.
    output_axis_xy = next(st.axis for st in chain.layout.shafts if st.shaft == "output")
    rib_boxes = []
    for rib in ribs or []:
        solid, box = _rib(rib, outer, z_lo, z_hi)
        if rib["face"] == "-z":
            solid = solid.cut(cylinder(input_axis, z_lo - 400, z_lo + 0.5, ring_out + 30))
        solid = solid.cut(cylinder(output_axis_xy, z_lo - 400, z_hi + 400, 90.0))
        body = body.fuse(solid)
        rib_boxes.append(box)
    body = body.clean()

    # Seats, shoulders and seal bores, cut after the bosses.
    for b in bearings:
        z0, z1 = b["z"]
        body = body.cut(cylinder(b["axis"], z0, z1, b["D"]))
        # The pocket behind a seat, where the seat stands clear of its end wall; a seat whose back
        # lies in the wall is bored into it, and the wall is its shoulder.
        if b["side"] == "-z" and z0 > z_lo + end + 0.5:
            body = body.cut(cylinder(b["axis"], z_lo + end, z0 + 1e-3, b["D"] - 2 * s["shoulder"]))
        elif b["side"] == "+z" and z1 < z_hi - end - 0.5:
            body = body.cut(cylinder(b["axis"], z1 - 1e-3, z_hi - end, b["D"] - 2 * s["shoulder"]))
        if b["sealed"]:
            seal = b["d"] + 2 * s["seal_radial"]
            if b["side"] == "-z":
                body = body.cut(cylinder(b["axis"], z_lo - t_ring - 1.0, z0 + 1e-3, seal))
            else:
                body = body.cut(cylinder(b["axis"], z1 - 1e-3, z_hi + 1.0, seal))
    for m in mounts:
        body = body.cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
    motor_holes = []
    for k in range(s["motor_bolts"]):
        a = 2 * math.pi * k / s["motor_bolts"]
        c = (
            input_axis[0] + s["motor_bolt_circle"] / 2 * math.cos(a),
            input_axis[1] + s["motor_bolt_circle"] / 2 * math.sin(a),
        )
        body = body.cut(cylinder(c, z_lo - t_ring - 1.0, z_lo + end - 1.0, s["bolt_hole"]))
        motor_holes.append(c)
    body = body.clean()

    # The split, across the shafts, midway between the first stage's gears and the second's.
    planes = dict(chain.layout.planes)
    first = [
        p
        for st in chain.layout.shafts
        for p in st.parts
        if p.kind == "gear" and p.name.startswith("s1")
    ]
    second = [
        p
        for st in chain.layout.shafts
        for p in st.parts
        if p.kind == "gear" and p.name.startswith("s2")
    ]
    z_split = (max(p.z_max for p in first) + min(p.z_min for p in second)) / 2
    for b in bearings:
        assert not (b["z"][0] < z_split < b["z"][1]), f"the split cuts a seat: {b}"
    say(f"split at z {z_split:.2f} mm (stage planes {planes})")
    big = 2000.0
    lower = body.intersect(
        cq.Workplane("XY", origin=(0, 0, z_lo - 100))
        .rect(big, big)
        .extrude(z_split - z_lo + 100)
        .val()
    )
    upper = body.intersect(
        cq.Workplane("XY", origin=(0, 0, z_split))
        .rect(big, big)
        .extrude(z_hi + 100 - z_split)
        .val()
    )
    # The flange: a lip on each half at the split, the bolts through both.
    lip = hull_of_circles(
        [(x, y, r + s["wall"] + s["flange_width"]) for x, y, r in cavity]
        + [(x, y, r + s["flange_width"]) for x, y, r in bosses]
    )
    t_f = s["flange_thickness"]
    lower = lower.fuse(
        prism(lip, z_split - t_f, z_split).cut(prism(inner, z_split - t_f - 1, z_split + 1))
    ).clean()
    upper = upper.fuse(
        prism(lip, z_split, z_split + t_f).cut(prism(inner, z_split - 1, z_split + t_f + 1))
    ).clean()
    bolt_line = hull_of_circles(
        [(x, y, r + s["wall"] + s["flange_bolt_axis"]) for x, y, r in cavity]
        + [(x, y, r + s["flange_bolt_axis"]) for x, y, r in bosses]
    )
    bolts = _along(bolt_line, s["bolt_pitch"])
    for c in bolts:
        lower = lower.cut(cylinder(c, z_split - t_f - 1, z_split + 1, s["bolt_hole"]))
        upper = upper.cut(cylinder(c, z_split - 1, z_split + t_f + 1, s["bolt_hole"]))
    lower, upper = lower.clean(), upper.clean()
    say(f"halves built: {len(bolts)} bolts on the flange")

    names = {
        "motor_side": _name_faces(
            lower, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes
        ),
        "cover": _name_faces(upper, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for half, shape in (("motor_side", lower), ("cover", upper)):
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{stem}_{half}.step"))
        shape.exportBrep(str(OUT / f"{stem}_{half}.brep"))
    mass = {
        half: shape.Volume() * s["density"]
        for half, shape in (("motor_side", lower), ("cover", upper))
    }
    result = {
        "stem": stem,
        "ribs": ribs or [],
        "settings": s,
        "z": {"lo": z_lo, "hi": z_hi, "split": z_split},
        "bearings": bearings,
        "mounts": mounts,
        "motor_holes": motor_holes,
        "bolts": bolts,
        "inner_outline": inner,
        "outer_outline": outer,
        "mass_kg": {**mass, "total": sum(mass.values())},
        "faces": {half: {str(k): v for k, v in n.items()} for half, n in names.items()},
        "refused": [f"{k}: {v}" for k, v in sorted(chain.refused.items())],
    }
    (OUT / f"{stem}.json").write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    roles = {half: _count(n) for half, n in names.items()}
    say(
        f"mass {result['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f}); faces {roles}"
    )
    return result


def _along(polygon, pitch):
    """Points spaced about `pitch` apart round a closed polygon."""
    edges = list(zip(polygon, polygon[1:] + polygon[:1], strict=True))
    lengths = [math.dist(a, b) for a, b in edges]
    total = sum(lengths)
    n = max(4, round(total / pitch))
    step = total / n
    out, walked, i = [], 0.0, 0
    target = 0.0
    for (a, b), length in zip(edges, lengths, strict=True):
        while target <= walked + length and len(out) < n:
            t = (target - walked) / length if length else 0.0
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            target += step
        walked += length
        i += 1
    return out


def _rib(rib: dict, outer, z_lo: float, z_hi: float):
    """A rib: a plate of its thickness along the path a-b, standing its height off the end wall
    it names (1 mm sunk into the wall so the fuse is clean), clipped to the housing's outline."""
    (ax, ay), (bx, by) = rib["a"], rib["b"]
    length = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / length, (bx - ax) / length
    t = rib["thickness"] / 2
    poly = [
        (ax + nx * t, ay + ny * t),
        (bx + nx * t, by + ny * t),
        (bx - nx * t, by - ny * t),
        (ax - nx * t, ay - ny * t),
    ]
    if rib["face"] == "+z":
        z0, z1 = z_hi - 1.0, z_hi + rib["height"]
    else:
        z0, z1 = z_lo - rib["height"], z_lo + 1.0
    solid = prism(poly, z0, z1).intersect(prism(outer, z_lo - 500, z_hi + 500))
    return solid, {"poly": poly, "z": (z0, z1)}


def _in_poly(poly, x, y) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _name_faces(
    shape, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes=()
) -> dict[int, str]:
    """Each face's role, from the exact geometry: a cylinder's radius and axis, a plane's place."""
    out = {}
    tol = 0.05
    for k, face in enumerate(shape.Faces()):
        kind = face.geomType()
        role = "wall"
        centre = face.Center()
        for box in rib_boxes:
            grown = box["poly"]
            if box["z"][0] - tol <= centre.z <= box["z"][1] + tol and _in_poly(
                grown, centre.x, centre.y
            ):
                role = "rib"
        if kind == "CYLINDER":
            surf = BRepAdaptor_Surface(face.wrapped).Cylinder()
            r = surf.Radius()
            loc = surf.Location()
            x, y = loc.X(), loc.Y()
            box = face.BoundingBox()
            for b in bearings:
                if math.dist((x, y), b["axis"]) < tol and abs(r - b["D"] / 2) < tol:
                    if box.zmin >= b["z"][0] - tol and box.zmax <= b["z"][1] + tol:
                        role = f"seat:{b['shaft']}:{b['side']}"
            for i, c in enumerate(bolts):
                if math.dist((x, y), c) < tol and abs(r - s["bolt_hole"] / 2) < tol:
                    role = f"bolt:{i}"
            for i, m in enumerate(mounts):
                if math.dist((x, y), m["centre"]) < tol and abs(r - s["mount_hole"] / 2) < tol:
                    role = f"mount:{i}"
            for i, c in enumerate(motor_holes):
                if math.dist((x, y), c) < tol and abs(r - s["bolt_hole"] / 2) < tol:
                    role = f"motor:{i}"
        elif kind == "PLANE":
            box = face.BoundingBox()
            if abs(box.zmin - z_split) < tol and abs(box.zmax - z_split) < tol:
                role = "split"
        out[k] = role
    return out


def _count(names: dict[int, str]) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for role in names.values():
        key = role.split(":")[0]
        kinds[key] = kinds.get(key, 0) + 1
    return kinds


if __name__ == "__main__":
    build(*sys.argv[1:2])
