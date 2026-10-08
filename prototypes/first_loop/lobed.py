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
                "outer": hull_of_circles([(cx, cy, r + wall) for cx, cy, r in cavity] + bosses),
                "z": tuple(stack.ends),
            }
        )
    z_lo = min(p["z"][0] for p in pods)
    z_hi = max(p["z"][1] for p in pods)
    body = fuse([prism(p["outer"], *p["z"]) for p in pods])
    body = body.cut(fuse([prism(p["inner"], p["z"][0] + end, p["z"][1] - end) for p in pods]))
    pod_of = {p["shaft"]: p for p in pods}
    for b in bearings:
        z0, z1 = b["z"]
        lo, hi = pod_of[b["shaft"]]["z"]
        if b["side"] == "-z":
            body = body.fuse(cylinder(b["axis"], lo, z1, b["D"] + 2 * s["boss"]))
        else:
            body = body.fuse(cylinder(b["axis"], z0, hi, b["D"] + 2 * s["boss"]))
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
    body = body.fuse(ring)
    # Mounts on the outline's extremes, each on the motor-side end of the pod it stands on.
    points = [(pt, p) for p in pods for pt in p["outer"]]
    cx = sum(pt[0] for pt, _ in points) / len(points)
    cy = sum(pt[1] for pt, _ in points) / len(points)
    mounts = []
    for direction in ((-1.0, -0.6), (1.0, -0.4), (0.15, 1.0)):
        n = math.hypot(*direction)
        ux, uy = direction[0] / n, direction[1] / n
        far, pod = max(points, key=lambda q: (q[0][0] - cx) * ux + (q[0][1] - cy) * uy)
        centre = (far[0] + ux * s["mount_diameter"] * 0.25, far[1] + uy * s["mount_diameter"] * 0.25)
        z0 = pod["z"][0] + 8.0
        z1 = z0 + s["mount_length"]
        body = body.fuse(cylinder(centre, z0, z1, s["mount_diameter"]))
        mounts.append({"centre": centre, "z": (z0, z1), "normal": (ux, uy, 0.0), "pod": pod["shaft"]})
    body = body.clean()
    # Seats, shoulders, seal bores, holes.
    for b in bearings:
        z0, z1 = b["z"]
        lo, hi = pod_of[b["shaft"]]["z"]
        body = body.cut(cylinder(b["axis"], z0, z1, b["D"]))
        if b["side"] == "-z" and z0 > lo + end + 0.5:
            body = body.cut(cylinder(b["axis"], lo + end, z0 + 1e-3, b["D"] - 2 * s["shoulder"]))
        elif b["side"] == "+z" and z1 < hi - end - 0.5:
            body = body.cut(cylinder(b["axis"], z1 - 1e-3, hi - end, b["D"] - 2 * s["shoulder"]))
        if b["sealed"]:
            seal = b["d"] + 2 * s["seal_radial"]
            if b["side"] == "-z":
                body = body.cut(cylinder(b["axis"], lo - t_ring - 1.0, z0 + 1e-3, seal))
            else:
                body = body.cut(cylinder(b["axis"], z1 - 1e-3, hi + 1.0, seal))
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

    # The split across the shafts, as the convex form's.
    first = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear" and p.name.startswith("s1")]
    second = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear" and p.name.startswith("s2")]
    z_split = (max(p.z_max for p in first) + min(p.z_min for p in second)) / 2
    for p in pods:
        assert p["z"][0] < z_split < p["z"][1], f"the split misses the {p['shaft']} pod"
    big = 2000.0
    lower = body.intersect(cq.Workplane("XY", origin=(0, 0, z_lo - 100)).rect(big, big).extrude(z_split - z_lo + 100).val())
    upper = body.intersect(cq.Workplane("XY", origin=(0, 0, z_split)).rect(big, big).extrude(z_hi + 100 - z_split).val())
    t_f = s["flange_thickness"]
    lips = [hull_of_circles([(cx_, cy_, r + wall + s["flange_width"]) for cx_, cy_, r in p["cavity"]] + [(bx, by, r + s["flange_width"]) for bx, by, r in p["bosses"]]) for p in pods]
    cavity_cut = fuse([prism(p["inner"], z_split - t_f - 1, z_split + t_f + 1) for p in pods])
    lower = lower.fuse(fuse([prism(lip, z_split - t_f, z_split) for lip in lips]).cut(cavity_cut)).clean()
    upper = upper.fuse(fuse([prism(lip, z_split, z_split + t_f) for lip in lips]).cut(cavity_cut)).clean()
    bolts = []
    for i, p in enumerate(pods):
        line = hull_of_circles([(cx_, cy_, r + wall + s["flange_bolt_axis"]) for cx_, cy_, r in p["cavity"]] + [(bx, by, r + s["flange_bolt_axis"]) for bx, by, r in p["bosses"]])
        for c in convex._along(line, s["bolt_pitch"]):
            covered = any(_in_poly(q["outer"], *c) for j, q in enumerate(pods) if j != i)
            near = any(math.dist(c, other) < 0.6 * s["bolt_pitch"] for other in bolts)
            if not covered and not near:
                bolts.append(c)
    for c in bolts:
        lower = lower.cut(cylinder(c, z_split - t_f - 1, z_split + 1, s["bolt_hole"]))
        upper = upper.cut(cylinder(c, z_split - 1, z_split + t_f + 1, s["bolt_hole"]))
    lower, upper = lower.clean(), upper.clean()
    say(f"lobed halves built: {len(bolts)} bolts on the flange")

    names = {
        "motor_side": convex._name_faces(lower, bearings, bolts, mounts, motor_holes, z_split, s),
        "cover": convex._name_faces(upper, bearings, bolts, mounts, motor_holes, z_split, s),
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
