"""PROTOTYPE - not product code, not the judge.

Plan Part C, Task 9: the machined core of the main housing half in CadQuery (exact B-rep),
from derived.json (Task 8) and the shell's outline at the split face (outline.json, Task 10's
first step). It is the as-machined state: bores at the bearing outside diameter, holes at their
finished sizes. The machining stock (0.25 mm, NADCA 2015) is recorded, not modelled.

Features (sizes are prototype choices, labelled; none comes from the contract):
- three back-wall seat rings: bore = bearing OD over the bearing width, a 4 mm shoulder beyond
  it (a shaft passage through it at the input and output; closed at the intermediate seat),
  8 mm radial wall at the top, the outside drafted 2 deg along +z;
- the split-face bolt bosses: d18 mm, d9 mm M8 clearance holes, 12 mm tall, along the shell's
  outline at most 80 mm apart, drafted;
- the motor-flange ring around the input seat on the outside of the back wall: female spigot
  d110 mm, 6 blind d9 mm holes on a d130 mm circle;
- one mount pad, 60 x 40 x 12 mm with two d11 mm blind holes, on the +x end wall near the output
  axis (assumption A4); its back follows the cavity 1 mm outside it, so it cannot reach the gears.
Outputs: core.step, core.stl, core.json. The STEP is re-imported and its volume compared.
"""

from __future__ import annotations

import json
import math
import sys
import time

import cadquery as cq
import params as P
from layout import load_layout

Z = cq.Vector(0, 0, 1)


def frustum(cx, cy, z0, z1, r0, r1):
    """Solid of revolution about a z-parallel axis: radius r0 at z0, r1 at z1."""
    if abs(r0 - r1) < 1e-9:
        return cq.Solid.makeCylinder(r0, z1 - z0, cq.Vector(cx, cy, z0), Z)
    return cq.Solid.makeCone(r0, r1, z1 - z0, cq.Vector(cx, cy, z0), Z)


def cylinder(cx, cy, z0, z1, r):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(cx, cy, z0), Z)


def seat_ring(s):
    outer = frustum(s.cx, s.cy, s.z0, s.ring_top, float(s.r_ring(s.z0)), s.r_ring_top)
    ring = outer.cut(cylinder(s.cx, s.cy, s.z0 - 1.0, s.z1, s.D / 2))
    if s.through:
        ring = ring.cut(cylinder(s.cx, s.cy, s.z1 - 0.5, s.ring_top + 1.0, s.r_shoulder_hole))
    return ring


def motor_flange(lay):
    cx, cy = lay.flange_c
    zb, zf, tan = lay.z_flange_bottom, lay.z_flange, lay.tan
    h = zf - zb
    outer = frustum(cx, cy, zb, zf, lay.flange_r_out, lay.flange_r_out - h * tan)
    # the pocket inside the ring is open toward +z, so its wall widens along +z (draft); cast
    # 1 mm inside the machined spigot, which is then cut with a clear shoulder
    r_pocket = lay.flange_r_spigot - P.FLANGE_POCKET_UNDERSIZE
    inner = frustum(cx, cy, zb - 1.0, zf + 1.0, r_pocket - (h + 1.0) * tan, r_pocket + tan)
    ring = outer.cut(inner)
    ring = ring.cut(cylinder(cx, cy, zf - lay.flange_spigot_depth, zf + 1.0, lay.flange_r_spigot))
    holes = []
    # the intermediate axis falls midway between two holes, so no hole nears its bore
    ix, iy = lay.axes["intermediate"]
    a0 = math.degrees(math.atan2(iy - cy, ix - cx)) + 180.0 / lay.flange_bolts
    for k in range(lay.flange_bolts):
        a = math.radians(a0 + k * 360.0 / lay.flange_bolts)
        hx, hy = cx + lay.flange_r_bolt * math.cos(a), cy + lay.flange_r_bolt * math.sin(a)
        holes.append([hx, hy])
        ring = ring.cut(cylinder(hx, hy, zf - P.FLANGE_HOLE_DEPTH, zf + 1.0, lay.flange_hole_r))
    return ring, holes


def mount_pad(lay):
    x_face = lay.pad_face_x
    x_back = x_face - 25.0
    z0, z1 = lay.pad_z
    hy0, hy1 = lay.pad_half_y, float(lay.pad_half_y_at(z1))
    pad = (
        cq.Workplane("YZ", origin=(x_back, 0, 0))
        .polyline([(-hy0, z0), (hy0, z0), (hy1, z1), (-hy1, z1)])
        .close()
        .extrude(x_face - x_back)
        .val()
    )
    g4 = next(g for g in lay.gears if g.name == "g4")
    r_at = [float(lay.output_cavity_radius(z)) + 1.0 for z in (0.0, lay.z_wall_in)]
    cone = cq.Solid.makeCone(r_at[0], r_at[1], lay.z_wall_in, cq.Vector(g4.cx, g4.cy, 0.0), Z)
    pad = pad.cut(cone)
    for hz in lay.pad_hole_z:
        hole = cq.Solid.makeCylinder(
            lay.pad_hole_r,
            P.PAD_HOLE_DEPTH + 1.0,
            cq.Vector(x_face - P.PAD_HOLE_DEPTH, 0.0, hz),
            cq.Vector(1, 0, 0),
        )
        pad = pad.cut(hole)
    return pad


def boss(bx, by, tan):
    r0 = P.BOSS_DIAMETER / 2
    b = frustum(bx, by, 0.0, P.BOSS_HEIGHT, r0, r0 - P.BOSS_HEIGHT * tan)
    return b.cut(cylinder(bx, by, -1.0, P.BOSS_HEIGHT + 1.0, P.BOSS_HOLE / 2))


def clear_seats(shape, lay):
    """Keep every back-wall bore and shaft passage clear of a feature that reaches over it."""
    for s in lay.back:
        shape = shape.cut(cylinder(s.cx, s.cy, s.z0 - 1.0, s.z1, s.D / 2))
        if s.through:
            shape = shape.cut(
                cylinder(s.cx, s.cy, s.z1 - 0.5, s.ring_top + 50.0, s.r_shoulder_hole)
            )
    return shape


def build(lay, bosses):
    parts = {"seat rings": [seat_ring(s) for s in lay.back]}
    fl, flange_holes = motor_flange(lay)
    parts["motor flange"] = [clear_seats(fl, lay)]
    parts["mount pad"] = [clear_seats(mount_pad(lay), lay)]
    parts["bolt bosses"] = [boss(bx, by, lay.tan) for bx, by in bosses]
    solids = [s for v in parts.values() for s in v]
    core = solids[0].fuse(*solids[1:]).clean()
    return core, parts, flange_holes


def keepout_intrusion(core, lay):
    """Volume of the core inside the gears' keep-outs (should be zero)."""
    total = 0.0
    for g in lay.gears:
        z0, z1 = g.z_keepout
        total += core.intersect(cylinder(g.cx, g.cy, z0, z1, g.r_keepout)).Volume()
    return total


def main():
    t0 = time.time()
    lay = load_layout()
    outline = json.loads((P.OUT / "outline.json").read_text(encoding="utf-8"))
    core, parts, flange_holes = build(lay, outline["bosses"])
    vol = core.Volume()
    if not core.isValid():
        raise RuntimeError("the core B-rep is not valid")

    step = P.OUT / "core.step"
    stl = P.OUT / "core.stl"
    cq.exporters.export(core, str(step))
    cq.exporters.export(core, str(stl), tolerance=0.03, angularTolerance=0.1)
    back = cq.importers.importStep(str(step)).val()
    vol_back = back.Volume()
    rel = abs(vol_back - vol) / vol
    intr = keepout_intrusion(core, lay)

    rings = []
    for s in lay.back:
        rings.append(
            {
                "shaft": s.shaft,
                "bearing": s.bearing,
                "centre_xy": [round(s.cx, 3), round(s.cy, 3)],
                "bore_diameter": {"value": s.D, "unit": "mm", "provenance": P.CATALOGUE},
                "bore_z": {
                    "value": [round(s.z0, 3), round(s.z1, 3)],
                    "unit": "mm",
                    "provenance": P.PROTO,
                },
                "ring_top_z": {"value": round(s.ring_top, 3), "unit": "mm", "provenance": P.PROTO},
                "ring_wall_at_top": {"value": P.RING_WALL, "unit": "mm", "provenance": P.PROTO},
                "shoulder": {"value": P.SHOULDER, "unit": "mm", "provenance": P.PROTO},
                "shoulder_hole_diameter": {
                    "value": None if s.r_shoulder_hole is None else round(2 * s.r_shoulder_hole, 3),
                    "unit": "mm",
                    "provenance": P.PROTO,
                    "note": "(d + D) / 2; closed if None",
                },
            }
        )
    report = {
        "PROTOTYPE": "plan Part C, Task 9; not product code, not the judge",
        "state": "as machined (bores at the bearing OD); machining stock 0.25 mm recorded only",
        "volume_mm3": round(vol, 3),
        "step_reimport_volume_mm3": round(vol_back, 3),
        "step_reimport_relative_difference": rel,
        "step_reimport_ok": rel <= 1e-6,
        "valid_brep": True,
        "solids": len(core.Solids()),
        "keepout_intrusion_mm3": round(intr, 6),
        "seat_rings": rings,
        "bolt_bosses": {
            "count": len(outline["bosses"]),
            "points": outline["bosses"],
            "diameter": P.BOSS_DIAMETER,
            "hole": P.BOSS_HOLE,
            "height": P.BOSS_HEIGHT,
            "provenance": P.PROTO,
        },
        "motor_flange": {
            "centre_xy": list(lay.flange_c),
            "face_z": lay.z_flange,
            "spigot_diameter": 2 * lay.flange_r_spigot,
            "bolt_circle_diameter": 2 * lay.flange_r_bolt,
            "holes": [[round(a, 3), round(b, 3)] for a, b in flange_holes],
            "hole_diameter": 2 * lay.flange_hole_r,
            "hole_depth": P.FLANGE_HOLE_DEPTH,
            "outside_diameter": 2 * lay.flange_r_out,
            "provenance": P.PROTO,
        },
        "mount_pad": {
            "face_x": lay.pad_face_x,
            "z": list(lay.pad_z),
            "half_width_y": lay.pad_half_y,
            "holes_z": lay.pad_hole_z,
            "hole_diameter": 2 * lay.pad_hole_r,
            "hole_depth": P.PAD_HOLE_DEPTH,
            "provenance": P.PROTO + " / " + P.A4,
        },
        "files": {"step": str(step), "stl": str(stl)},
        "time_s": round(time.time() - t0, 1),
    }
    (P.OUT / "core.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(
        f"core: {report['solids']} solids, volume {vol / 1e3:.2f} cm3; STEP re-import "
        f"difference {rel:.1e} ({'ok' if rel <= 1e-6 else 'NOT ok'}); keep-out intrusion "
        f"{intr:.3g} mm3; {report['time_s']} s"
    )
    print(f"  core.step, core.stl, core.json -> {P.OUT}")
    if rel > 1e-6:
        raise RuntimeError("STEP re-import changed the volume")
    return report


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
