"""PROTOTYPE - not product code, not the judge.

Plan Part C, Task 8: a first sketch of the load front-end, from Hofstetter et al. 2018's
requirement (Table 2) to a layout, the main housing's seats and three load cases of seat loads.

It has NOT passed the plan's three load checks (spec 4.3); its sizing is by rule of thumb and
is not a gear rating. Output: data/prototypes/first_variant/derived.json, every value labelled
with its provenance ("published: Hofstetter 2018 Table 2", "rule of thumb", "assumption A1",
"derived: frontend-prototype 0.1", ...).

Frame (prototype): input axis at the origin, output axis at +x, axes along z; the split face
between the main housing and the cover is z = 0; the main housing is 0 <= z <= L and its back
wall (z = L side) carries the three far seats; the motor sits outside the back wall.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys

import numpy as np
import params as P


def q(value, unit, provenance, note=None):
    """One labelled value."""
    d = {"value": value, "unit": unit, "provenance": provenance}
    if note:
        d["note"] = note
    return d


def r3(v, nd=3):
    return [round(float(x), nd) for x in v]


# --------------------------------------------------------------------------- inputs

REQUIREMENT = {
    "input_output_offset": q(
        165.0,
        "mm",
        P.PUB_T2,
        "'Total center distance', read as the straight-line offset between the input and "
        "output axes (spec 4.2; to be checked against the paper's Fig. 4)",
    ),
    "total_ratio": q(9.32, "1", P.PUB_T2),
    "ratio_tolerance": q(1.0, "%", P.PUB_T2),
    "input_torque_nominal": q(366.0, "N*m", P.PUB_T2),
    "max_input_speed": q(15000.0, "rpm", P.PUB_T2),
    "gear_material": q("20MnCr5", None, P.PUB_T2),
}

# Ratio split and sizing: rule of thumb (the brief), not a rating.
STAGE_CHOICES = [
    {
        "name": "stage1",
        "z_pinion": 25,
        "z_gear": 65,
        "normal_module": 2.0,
        "helix_deg": 20.0,
        "pressure_deg": 20.0,
        "x_pinion": 0.0,
        "x_gear": 0.0,
        "hand_pinion": "right",
        "overlap_ratio": 2.0,
    },
    {
        "name": "stage2",
        "z_pinion": 23,
        "z_gear": 82,
        "normal_module": 2.5,
        "helix_deg": 20.0,
        "pressure_deg": 20.0,
        "x_pinion": 0.0,
        "x_gear": 0.0,
        "hand_pinion": "left",
        "overlap_ratio": 2.0,
    },
]
HAND_NOTE = (
    "helix hands: stage-1 pinion right, wheel left; stage-2 pinion left, wheel right, so "
    "the two gears on the intermediate shaft push opposite ways (rule of thumb)"
)

# Hofstetter 2018 Table 3 benchmark bearings; boundary dimensions from the ISO 15 series.
BEARINGS = {
    "6206": {"type": "deep groove ball", "d": 30.0, "D": 62.0, "B": 16.0},
    "NU205": {"type": "cylindrical roller (NU)", "d": 25.0, "D": 52.0, "B": 15.0},
    "32010 X": {"type": "tapered roller", "d": 50.0, "D": 80.0, "B": 20.0},
    "6012": {"type": "deep groove ball", "d": 60.0, "D": 95.0, "B": 18.0},
    "6011": {"type": "deep groove ball", "d": 55.0, "D": 90.0, "B": 18.0},
}
# shaft -> (cover-side bearing, back-wall bearing, locating rule)
SHAFT_BEARINGS = {
    "input": ("NU205", "6206", "back wall"),
    "intermediate": ("32010 X", "32010 X", "by thrust"),
    "output": ("6011", "6012", "back wall"),
}
# Shoulder hole through the back-wall seat (a shaft passes) or closed (prototype choice).
SHOULDER_HOLE = {
    "input": "through (to the motor)",
    "intermediate": "closed",
    "output": "through (to the drive shaft)",
}

CASES = [
    {
        "name": "peak_drive",
        "sign": +1.0,
        "provenance": P.A1,
        "note": "peak drive = nominal 366 N*m (A1), +z on the input shaft",
    },
    {
        "name": "peak_regeneration",
        "sign": -1.0,
        "provenance": P.A1,
        "note": "same magnitude, reversed (A1)",
    },
    {
        "name": "reverse",
        "sign": -1.0,
        "provenance": P.A1,
        "note": "same magnitude, reversed (A1); in this frictionless quasi-static model it gives "
        "the same seat loads as regeneration, since only the torque's sign enters",
    },
]


# --------------------------------------------------------------------------- sizing


def size_stage(s):
    mn = s["normal_module"]
    beta = math.radians(s["helix_deg"])
    d_p = mn * s["z_pinion"] / math.cos(beta)
    d_g = mn * s["z_gear"] / math.cos(beta)
    b = s["overlap_ratio"] * math.pi * mn / math.sin(beta)  # Hofstetter's overlap-ratio rule
    return {
        "d_pinion": d_p,
        "d_gear": d_g,
        "da_pinion": d_p + 2 * mn,
        "da_gear": d_g + 2 * mn,
        "face_width": b,
        "centre_distance": 0.5 * (d_p + d_g),
        "ratio": s["z_gear"] / s["z_pinion"],
    }


def intermediate_axis(a1, a2, offset):
    """Triangle vertex at distance a1 from the input (0,0) and a2 from the output (offset,0)."""
    if not abs(a1 - a2) <= offset <= a1 + a2:
        raise ValueError("the two stages cannot reach the offset (|a1-a2| <= offset <= a1+a2)")
    x = (a1 * a1 - a2 * a2 + offset * offset) / (2 * offset)
    y = math.sqrt(max(a1 * a1 - x * x, 0.0))
    return np.array([x, y])  # on the +y side


# --------------------------------------------------------------------------- statics


def mesh_forces(torque_on_driver, c_drv, c_drn, r_drv, z_mesh, beta, alpha_n, hand_drv):
    """Tooth forces at the pitch point, in the global frame (N, N*mm).

    torque_on_driver: torque (about +z) the driver's shaft applies to the driver.
    The tangential force on the driven gear points along t = z x e (e from the driver's axis
    to the driven gear's axis) with the torque's sign; the radial force on each gear points
    from the pitch point toward its own axis; the axial force follows the helix hand
    (right hand: F_ax = -tan(beta) * (F . t_ccw)); action = -reaction.
    """
    e = (c_drn - c_drv) / np.linalg.norm(c_drn - c_drv)
    t = np.array([-e[1], e[0]])
    p = np.array([*(c_drv + r_drv * e), z_mesh])
    ft = torque_on_driver / r_drv  # signed, along t, on the driven gear
    fr = abs(ft) * math.tan(alpha_n) / math.cos(beta)
    f_drv_tan = -ft * t
    comp = float(f_drv_tan @ t)
    fax = -math.tan(beta) * comp if hand_drv == "right" else math.tan(beta) * comp
    f_drv = np.array([f_drv_tan[0] - fr * e[0], f_drv_tan[1] - fr * e[1], fax])
    f_drn = -f_drv
    return p, f_drv, f_drn, {"Ft": abs(ft), "Fr": fr, "Fa": abs(fax)}


def torque_about_axis(p, f, c):
    """z-moment of force f at point p about the axis through c (2D)."""
    rx, ry = p[0] - c[0], p[1] - c[1]
    return rx * f[1] - ry * f[0]


def two_support(loads, c, z_a, z_b, locating):
    """Bearing reactions on a shaft with supports A (cover, z_a) and B (back wall, z_b).

    loads: list of (point, force). The x-y moments include the axial forces' moment
    Fa * d/2 (JTEKT eq. 5-29) because they are taken from the full 3D lever arms.
    locating: "A", "B" or "by thrust" (the bearing the net thrust pushes into).
    Returns (R_A, R_B) acting ON THE SHAFT.
    """
    a = np.array([c[0], c[1], z_a])
    f_tot = np.zeros(3)
    m_a = np.zeros(3)
    for p, f in loads:
        f_tot += f
        m_a += np.cross(np.asarray(p) - a, f)
    span = z_b - z_a
    r_b = np.array([-m_a[1] / span, m_a[0] / span, 0.0])
    r_a = np.array([-f_tot[0] - r_b[0], -f_tot[1] - r_b[1], 0.0])
    if locating == "by thrust":
        locating = "B" if f_tot[2] > 0 else "A"
    if locating == "B":
        r_b[2] = -f_tot[2]
    else:
        r_a[2] = -f_tot[2]
    return r_a, r_b, locating


# --------------------------------------------------------------------------- main


def derive():
    req = REQUIREMENT
    stages = [dict(s, **size_stage(s)) for s in STAGE_CHOICES]
    s1, s2 = stages
    ratio = s1["ratio"] * s2["ratio"]
    target, tol = req["total_ratio"]["value"], req["ratio_tolerance"]["value"] / 100
    if not abs(ratio - target) <= tol * target:
        raise ValueError(f"ratio {ratio:.4f} outside {target} +/- {tol:.1%}")

    offset = req["input_output_offset"]["value"]
    c_in = np.array([0.0, 0.0])
    c_out = np.array([offset, 0.0])
    c_int = intermediate_axis(s1["centre_distance"], s2["centre_distance"], offset)
    axes = {"input": c_in, "intermediate": c_int, "output": c_out}

    # ---- axial stations (prototype choice: 5 mm gaps; stage 2 nearer the back wall)
    g, t = P.SHELL_GAP, P.SHELL_WALL
    s1_z = (P.GEAR_GAP, P.GEAR_GAP + s1["face_width"])
    s2_z = (s1_z[1] + P.GEAR_GAP, s1_z[1] + P.GEAR_GAP + s2["face_width"])
    z_keepout_top = s2_z[1] + P.GEAR_AXIAL_CLEARANCE
    z_wall_in = z_keepout_top + g  # back wall inner face
    z_wall_out = z_wall_in + t  # back wall outer face

    gears = [
        {
            "name": "g1",
            "stage": "stage1",
            "role": "pinion",
            "shaft": "input",
            "z": s1["z_pinion"],
            "d": s1["d_pinion"],
            "da": s1["da_pinion"],
            "hand": "right",
        },
        {
            "name": "g2",
            "stage": "stage1",
            "role": "wheel",
            "shaft": "intermediate",
            "z": s1["z_gear"],
            "d": s1["d_gear"],
            "da": s1["da_gear"],
            "hand": "left",
        },
        {
            "name": "g3",
            "stage": "stage2",
            "role": "pinion",
            "shaft": "intermediate",
            "z": s2["z_pinion"],
            "d": s2["d_pinion"],
            "da": s2["da_pinion"],
            "hand": "left",
        },
        {
            "name": "g4",
            "stage": "stage2",
            "role": "wheel",
            "shaft": "output",
            "z": s2["z_gear"],
            "d": s2["d_gear"],
            "da": s2["da_gear"],
            "hand": "right",
        },
    ]
    for gr in gears:
        st = s1 if gr["stage"] == "stage1" else s2
        gr["face"] = s1_z if gr["stage"] == "stage1" else s2_z
        gr["b"] = st["face_width"]
        gr["mn"] = st["normal_module"]
        gr["centre"] = axes[gr["shaft"]]

    # ---- seats: cover side z in [-B, 0]; back wall from its inner face, shoulder beyond
    seats = []
    for shaft, (near, far, loc) in SHAFT_BEARINGS.items():
        c = axes[shaft]
        bn, bf = BEARINGS[near], BEARINGS[far]
        seats.append(
            {
                "name": f"{shaft}_cover",
                "shaft": shaft,
                "side": "cover (not built)",
                "bearing": near,
                "z0": -bn["B"],
                "z1": 0.0,
                "shoulder": "-z",
                **bn,
            }
        )
        seats.append(
            {
                "name": f"{shaft}_back",
                "shaft": shaft,
                "side": "back wall (main housing)",
                "bearing": far,
                "z0": z_wall_in,
                "z1": z_wall_in + bf["B"],
                "shoulder": "+z",
                **bf,
            }
        )
        for s in seats[-2:]:
            s["centre"] = np.array([c[0], c[1], 0.5 * (s["z0"] + s["z1"])])
            s["locating"] = (loc == "back wall" and s["side"].startswith("back")) or None
    ring_tops = {s["shaft"]: s["z1"] + P.SHOULDER for s in seats if s["shoulder"] == "+z"}
    L = max(ring_tops.values())

    # ---- loads, three cases
    t_in = req["input_torque_nominal"]["value"] * 1000.0  # N*mm
    beta1 = math.radians(s1["helix_deg"])
    beta2 = math.radians(s2["helix_deg"])
    an1 = math.radians(s1["pressure_deg"])
    an2 = math.radians(s2["pressure_deg"])
    z_m1 = 0.5 * (s1_z[0] + s1_z[1])
    z_m2 = 0.5 * (s2_z[0] + s2_z[1])
    seat_by = {s["name"]: s for s in seats}
    cases_out = []
    for case in CASES:
        T = case["sign"] * t_in
        p1, f_g1, f_g2, mag1 = mesh_forces(
            T, c_in, c_int, s1["d_pinion"] / 2, z_m1, beta1, an1, "right"
        )
        t_int = torque_about_axis(p1, f_g2, c_int)  # what gear 2 gives the intermediate shaft
        p2, f_g3, f_g4, mag2 = mesh_forces(
            t_int, c_int, c_out, s2["d_pinion"] / 2, z_m2, beta2, an2, "left"
        )
        t_out = -torque_about_axis(p2, f_g4, c_out)  # torque the output delivers out
        # torque balance checks (z-moments)
        chk_in = T + torque_about_axis(p1, f_g1, c_in)
        chk_int = t_int + torque_about_axis(p2, f_g3, c_int)
        assert abs(chk_in) < 1e-6 * t_in and abs(chk_int) < 1e-6 * t_in

        shafts_loads = {
            "input": [(p1, f_g1)],
            "intermediate": [(p1, f_g2), (p2, f_g3)],
            "output": [(p2, f_g4)],
        }
        seat_loads, shaft_rows = [], []
        for shaft, loads in shafts_loads.items():
            sa, sb = seat_by[f"{shaft}_cover"], seat_by[f"{shaft}_back"]
            loc_rule = SHAFT_BEARINGS[shaft][2]
            loc = "B" if loc_rule == "back wall" else "by thrust"
            ra, rb, used = two_support(loads, axes[shaft], sa["centre"][2], sb["centre"][2], loc)
            f_sum = sum(f for _, f in loads)
            assert np.allclose(ra + rb + f_sum, 0.0, atol=1e-6 * t_in)
            for seat, r in ((sa, ra), (sb, rb)):
                f_h = -r  # force the shaft puts on the housing at this seat
                seat_loads.append(
                    {
                        "seat": seat["name"],
                        "bearing": seat["bearing"],
                        "force_on_housing": q(
                            r3(f_h, 1), "N", P.DERIVED, "global frame; shaft -> bearing -> housing"
                        ),
                        "radial": q(round(float(np.hypot(f_h[0], f_h[1])), 1), "N", P.DERIVED),
                        "axial": q(round(float(f_h[2]), 1), "N", P.DERIVED),
                        "magnitude": q(round(float(np.linalg.norm(f_h)), 1), "N", P.DERIVED),
                    }
                )
            shaft_rows.append(
                {
                    "shaft": shaft,
                    "thrust_to": (f"{shaft}_back" if used == "B" else f"{shaft}_cover"),
                    "net_axial_on_shaft": round(float(f_sum[2]), 1),
                }
            )
        cases_out.append(
            {
                "name": case["name"],
                "provenance": case["provenance"],
                "note": case["note"],
                "input_torque": q(round(T / 1000.0, 3), "N*m", case["provenance"]),
                "intermediate_torque": q(round(t_int / 1000.0, 3), "N*m", P.DERIVED),
                "output_torque": q(round(t_out / 1000.0, 3), "N*m", P.DERIVED),
                "mesh": [
                    {
                        "stage": "stage1",
                        "pitch_point": r3(p1),
                        "Ft": round(mag1["Ft"], 1),
                        "Fr": round(mag1["Fr"], 1),
                        "Fa": round(mag1["Fa"], 1),
                        "force_on_g1": r3(f_g1, 1),
                        "force_on_g2": r3(f_g2, 1),
                    },
                    {
                        "stage": "stage2",
                        "pitch_point": r3(p2),
                        "Ft": round(mag2["Ft"], 1),
                        "Fr": round(mag2["Fr"], 1),
                        "Fa": round(mag2["Fa"], 1),
                        "force_on_g3": r3(f_g3, 1),
                        "force_on_g4": r3(f_g4, 1),
                    },
                ],
                "shafts": shaft_rows,
                "seat_loads": seat_loads,
            }
        )

    # ---- interfaces placed by the front-end (prototype choices; A4 for the pad)
    tan_d = P.tan_draft()
    g4 = gears[3]
    r_ko4 = g4["da"] / 2 + P.GEAR_RADIAL_CLEARANCE
    pad_z = (P.PAD_CENTRE_Z - P.PAD_HEIGHT_Z / 2, P.PAD_CENTRE_Z + P.PAD_HEIGHT_Z / 2)
    wall_out_at_pad = c_out[0] + r_ko4 + g + t + (z_wall_in - pad_z[0]) * tan_d
    pad_face_x = wall_out_at_pad + P.PAD_PROUD
    # The motor flange (OD 150) reaches over the intermediate seat ring (its bore edge is only
    # ~56 mm from the input axis), so its face sits above every ring under its footprint by the
    # spigot recess depth + 1 mm; the recess then never cuts a seat (prototype choice).
    z_flange = ring_tops["input"]
    for s in seats:
        if s["shoulder"] != "+z":
            continue
        r_ring_base = s["D"] / 2 + P.RING_WALL + (s["B"] + P.SHOULDER) * tan_d
        if np.linalg.norm(s["centre"][:2] - c_in) < P.FLANGE_OD / 2 + r_ring_base:
            z_flange = max(z_flange, ring_tops[s["shaft"]] + P.FLANGE_SPIGOT_DEPTH + 1.0)
    interfaces = {
        "split_face": {
            "origin": q([0.0, 0.0, 0.0], "mm", P.PROTO),
            "normal": q([0, 0, -1], "1", P.PROTO),
            "bolt_hole_diameter": q(P.BOSS_HOLE, "mm", P.PROTO),
            "bolt_points": q(
                None, "mm", P.PROTO, "placed along the shell outline by field.py (outline.json)"
            ),
        },
        "motor_flange": {
            "centre": q(
                r3([c_in[0], c_in[1], z_flange]),
                "mm",
                P.PROTO,
                "around the input seat, on the outside of the back wall",
            ),
            "axis": q([0, 0, 1], "1", P.PROTO),
            "spigot_diameter": q(P.FLANGE_SPIGOT_D, "mm", P.PROTO),
            "spigot_depth": q(P.FLANGE_SPIGOT_DEPTH, "mm", P.PROTO),
            "bolt_circle_diameter": q(P.FLANGE_BOLT_CIRCLE_D, "mm", P.PROTO),
            "bolt_count": q(P.FLANGE_BOLTS, "1", P.PROTO),
            "bolt_hole_diameter": q(P.FLANGE_HOLE, "mm", P.PROTO),
            "outside_diameter": q(P.FLANGE_OD, "mm", P.PROTO),
            "z_bottom": q(round(z_wall_out - 2.0, 3), "mm", P.PROTO),
            "support": q("clamped", None, P.A4),
        },
        "mount_pad": {
            "centre": q(
                r3([pad_face_x - P.PAD_THICKNESS / 2, 0.0, P.PAD_CENTRE_Z]),
                "mm",
                P.A4,
                "one torque-reaction pad on the +x end wall, near the output",
            ),
            "face_x": q(round(pad_face_x, 3), "mm", P.PROTO),
            "normal": q([1, 0, 0], "1", P.A4),
            "size_z_y_x": q([P.PAD_HEIGHT_Z, P.PAD_WIDTH_Y, P.PAD_THICKNESS], "mm", P.PROTO),
            "hole_diameter": q(P.PAD_HOLE, "mm", P.PROTO),
            "hole_z": q(
                [P.PAD_CENTRE_Z - P.PAD_HOLE_PITCH / 2, P.PAD_CENTRE_Z + P.PAD_HOLE_PITCH / 2],
                "mm",
                P.PROTO,
            ),
            "support": q("fixed", None, P.A4),
        },
    }

    # ---- installation space (A3): the layout's envelope grown by 20 mm, as a box
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)

    def grow(c, r, z0, z1):
        lo[:] = np.minimum(lo, [c[0] - r, c[1] - r, z0])
        hi[:] = np.maximum(hi, [c[0] + r, c[1] + r, z1])

    for gr in gears:
        grow(gr["centre"], gr["da"] / 2, *gr["face"])
    for s in seats:
        grow(s["centre"], s["D"] / 2, s["z0"], s["z1"])
    grow(c_in, P.FLANGE_OD / 2, z_wall_out - 2.0, z_flange)
    grow([pad_face_x - P.PAD_THICKNESS / 2, 0.0], 0.0, *pad_z)
    hi[0] = max(hi[0], pad_face_x)
    lo[1] = min(lo[1], -P.PAD_WIDTH_Y / 2)
    space_lo, space_hi = lo - P.ENVELOPE_GROWTH, hi + P.ENVELOPE_GROWTH

    # ---- excitation (A5 check speeds)
    order1 = s1["z_pinion"]
    order2 = s2["z_pinion"] * s1["z_pinion"] / s1["z_gear"]
    excitation = {
        "mesh_orders_per_input_rev": {
            "stage1": q(order1, "1", P.DERIVED),
            "stage2": q(round(order2, 4), "1", P.DERIVED),
        },
        "check_speeds_rpm": q([7500.0, 15000.0], "rpm", P.A5),
        "mesh_frequencies_hz": {
            str(n): {"stage1": round(order1 * n / 60, 1), "stage2": round(order2 * n / 60, 1)}
            for n in (7500, 15000)
        },
    }

    # ---- input hash (what this derivation read)
    inputs = {
        "requirement": req,
        "stages": STAGE_CHOICES,
        "bearings": BEARINGS,
        "shaft_bearings": SHAFT_BEARINGS,
        "cases": CASES,
        "rules": {
            "gear_gap": P.GEAR_GAP,
            "radial": P.GEAR_RADIAL_CLEARANCE,
            "axial": P.GEAR_AXIAL_CLEARANCE,
            "g": g,
            "t": t,
            "shoulder": P.SHOULDER,
            "draft": P.DRAFT_DEG,
        },
    }
    blob = json.dumps(inputs, sort_keys=True, separators=(",", ":"), default=str)
    input_hash = "sha256:" + hashlib.sha256(blob.encode()).hexdigest()

    def gear_row(gr):
        return {
            "name": gr["name"],
            "stage": gr["stage"],
            "role": gr["role"],
            "shaft": gr["shaft"],
            "teeth": q(gr["z"], "1", P.ROT),
            "normal_module": q(gr["mn"], "mm", P.ROT),
            "helix_hand": q(gr["hand"], None, P.ROT, HAND_NOTE),
            "pitch_diameter": q(round(gr["d"], 4), "mm", P.DERIVED, "d = mn z / cos(beta)"),
            "tip_diameter": q(round(gr["da"], 4), "mm", P.DERIVED, "da = d + 2 mn (x = 0)"),
            "face_width": q(
                round(gr["b"], 4),
                "mm",
                P.DERIVED,
                "b = 2 pi mn / sin(beta) (Hofstetter's overlap-ratio rule, eps = 2)",
            ),
            "axial_station": q(r3(gr["face"]), "mm", P.PROTO, "z of the two faces"),
            "centre": q(r3(gr["centre"]), "mm", P.DERIVED),
        }

    def stage_row(s):
        return {
            "name": s["name"],
            "z_pinion": q(s["z_pinion"], "1", P.ROT),
            "z_gear": q(s["z_gear"], "1", P.ROT),
            "ratio": q(round(s["ratio"], 6), "1", P.DERIVED),
            "normal_module": q(s["normal_module"], "mm", P.ROT),
            "helix_angle": q(s["helix_deg"], "deg", P.ROT),
            "pressure_angle": q(s["pressure_deg"], "deg", P.ROT),
            "profile_shift_pinion": q(s["x_pinion"], "1", P.ROT),
            "profile_shift_gear": q(s["x_gear"], "1", P.ROT),
            "face_width": q(round(s["face_width"], 4), "mm", P.DERIVED),
            "centre_distance": q(round(s["centre_distance"], 4), "mm", P.DERIVED),
        }

    def seat_row(s):
        return {
            "name": s["name"],
            "shaft": s["shaft"],
            "side": s["side"],
            "bearing": q(s["bearing"], None, P.PUB_T3),
            "bearing_type": q(s["type"], None, P.PUB_T3),
            "bore_d": q(s["d"], "mm", P.CATALOGUE),
            "centre": q(r3(s["centre"]), "mm", P.DERIVED),
            "axis": q([0.0, 0.0, 1.0], "1", P.DERIVED),
            "diameter": q(s["D"], "mm", P.CATALOGUE, "seat diameter = bearing outside diameter"),
            "width": q(s["B"], "mm", P.CATALOGUE),
            "z_range": q(r3([s["z0"], s["z1"]]), "mm", P.PROTO),
            "shoulder": q(s["shoulder"], None, P.PROTO),
            "shoulder_hole": q(
                SHOULDER_HOLE[s["shaft"]] if s["shoulder"] == "+z" else None, None, P.PROTO
            ),
            "locating": q(
                bool(s["locating"])
                if s["shaft"] != "intermediate"
                else "the side the thrust pushes into",
                None,
                P.PROTO,
            ),
            "machining_stock": q(
                P.MACHINING_STOCK,
                "mm",
                "standard: NADCA 2015",
                "recorded; not modelled in the prototype mesh",
            ),
        }

    derived = {
        "PROTOTYPE": (
            "prototype front-end sketch (plan Part C, Task 8); not product code, not "
            "the judge; has not passed the plan's three load checks"
        ),
        "stamp": {"tool": P.TOOL, "tool_version": P.TOOL_VERSION, "input_hash": input_hash},
        "frame": {
            "origin": "input axis on the split face",
            "z": "along the shafts, toward the back wall and the motor",
            "x": "toward the output axis",
            "note": (
                "the spec's default frame points +z away from the motor; here the "
                "motor sits on the back wall at +z (the brief), so +z points toward "
                "it (prototype choice)"
            ),
        },
        "requirement": req,
        "ratio_check": {
            "total_ratio": q(round(ratio, 6), "1", P.DERIVED),
            "inside_tolerance": abs(ratio - target) <= tol * target,
        },
        "offset_check": {
            "a1": round(s1["centre_distance"], 4),
            "a2": round(s2["centre_distance"], 4),
            "ok": abs(s1["centre_distance"] - s2["centre_distance"])
            <= offset
            <= s1["centre_distance"] + s2["centre_distance"],
        },
        "stages": [stage_row(s) for s in stages],
        "gears": [gear_row(gr) for gr in gears],
        "axes": {
            k: q(r3(v), "mm", P.DERIVED if k == "intermediate" else P.PUB_T2 + " (offset)")
            for k, v in axes.items()
        },
        "seats": [seat_row(s) for s in seats],
        "housing": {
            "split_z": q(0.0, "mm", P.PROTO),
            "L": q(
                round(L, 3),
                "mm",
                P.PROTO,
                "5 + b1 + 5 + b2 + 3 + g + max(B) + shoulder: the deepest back-wall seat's "
                "shoulder face",
            ),
            "gear_keepout_top_z": q(round(z_keepout_top, 3), "mm", P.PROTO),
            "back_wall_inner_z": q(
                round(z_wall_in, 3), "mm", P.PROTO, "keep-out top + shell gap g"
            ),
            "back_wall_outer_z": q(round(z_wall_out, 3), "mm", P.PROTO, "inner + wall t"),
            "seat_ring_tops_z": {k: q(round(v, 3), "mm", P.PROTO) for k, v in ring_tops.items()},
            "pull_direction": q([0, 0, 1], "1", P.A7),
            "process": q(
                "aluminium high-pressure die casting", None, "engineer, 8 Oct (D3 re-taken)"
            ),
        },
        "interfaces": interfaces,
        "installation_space": {
            "kind": "box around the layout's envelope (gears' tip cylinders over their faces, "
            "bearings, motor-flange disc, mount pad), grown by 20 mm",
            "lo": q(r3(space_lo), "mm", P.A3),
            "hi": q(r3(space_hi), "mm", P.A3),
            "clearance": q(P.ENVELOPE_GROWTH, "mm", P.A3),
        },
        "load_cases": cases_out,
        "excitation": excitation,
        "not_checked": [
            "the front-end has not passed the plan's three load checks (spec 4.3)",
            "the sizing is by rule of thumb, not a gear rating (no ISO 6336)",
            "bearing boundary dimensions are to be checked against a maker's catalogue",
            "supports are the bearings' mid-widths; the tapered bearings' pressure centres "
            "and their induced axial forces are ignored",
            "the 165 mm offset reading is to be checked against Hofstetter's Fig. 4",
        ],
    }
    return derived


def main():
    P.OUT.mkdir(parents=True, exist_ok=True)
    d = derive()
    path = P.OUT / "derived.json"
    path.write_text(json.dumps(d, indent=1), encoding="utf-8")
    print(f"derived.json -> {path}")
    print(
        f"  ratio {d['ratio_check']['total_ratio']['value']:.4f}; intermediate axis "
        f"{d['axes']['intermediate']['value']}; L = {d['housing']['L']['value']} mm"
    )
    for c in d["load_cases"][:1]:
        for s in c["seat_loads"]:
            print(
                f"  {c['name']:>18} {s['seat']:>18} {s['bearing']:>8} "
                f"F = {s['force_on_housing']['value']} N  |F| = {s['magnitude']['value']} N"
            )
    return d


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
