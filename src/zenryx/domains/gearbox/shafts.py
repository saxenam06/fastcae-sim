"""The shaft sections, for strength and stiffness (GBX-3, the chain's step 7).

**Strength** (Shigley Ch. 7, the distortion-energy criterion for a solid round section under
bending M and torque T at the peak case, with the design factor n):

    d = (32·n / (π·Sy) · sqrt(M² + 0.75·T²))^(1/3)

- At a bearing seat the bending is nil (it is a support), so the torque through it sets the bore it
  needs: the motor's torque where the input leaves the housing; half the output's torque through
  each hub of a carrier whose half-shafts leave both ends; none on a shaft whose ends are closed.
  A carrier's hubs are at least their given diameter.
- At a gear, the bending and the torque there set the shaft's least diameter.

**Stiffness:** the shaft between its bearings as a beam of one diameter (the larger of the gears'
and the bores' needs), simply supported at the bearings, loaded by the mesh forces and the axial
forces' moments. Its slopes at the bearings and the gears, integrated from the moment diagram, are
set against the contract's tilt limit for each bearing's type and Shigley Table 7-2's 0.5 mrad for
a gear. A shaft that slopes too much is made stiffer, a millimetre at a time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from zenryx.contract.model import HousingDesignSpec
from zenryx.domains.gearbox.forces import CaseForces, value_in
from zenryx.domains.gearbox.layout import Layout
from zenryx.domains.gearbox.loads import CaseLoads

TOOL = "zenryx.domains.gearbox.shafts"
VERSION = "0.1.0"

GEAR_SLOPE_LIMIT = 0.0005  # rad, Shigley Table 7-2 (gears)
STEPS = 400  # points along a span for the slope integration


@dataclass(frozen=True)
class ShaftSection:
    """One shaft's needs (mm, N·mm, rad): the bore each seat needs for strength, each gear's least
    diameter, the beam's diameter for stiffness, and its worst slopes over the load cases."""

    shaft: str
    bore_needed: dict[str, float]
    torque_at_seat: dict[str, float]
    gear_diameter_needed: dict[str, float]
    diameter: float
    slope_at_bearing: dict[str, float]
    slope_at_gear: dict[str, float]
    # Per load case, the shaft's lean (dx/dz, dy/dz) at each bearing against the chord between its
    # bearings, at the diameter chosen: what the bearing's misalignment adds to the housing's.
    lean_at_bearing: dict[str, dict[str, tuple[float, float]]]


def _strength(n: float, sy: float, bending: float, torque: float) -> float:
    return (32.0 * n / (math.pi * sy) * math.sqrt(bending**2 + 0.75 * torque**2)) ** (1.0 / 3.0)


def _end_torques(spec: HousingDesignSpec, shaft: str, case: CaseForces) -> dict[str, float]:
    """The torque leaving through each end of a shaft: the input's at the end the motor drives,
    the output's halved over the ends its half-shafts leave by, none at a closed end."""
    req = spec.requirement
    leaving = [e.side.value for e in req.shaft_layout.sealed_ends if e.shaft == shaft]
    torques = dict(case.shaft_torques)
    out = {"-z": 0.0, "+z": 0.0}
    if shaft == req.stages[0].pinion_shaft:
        side = leaving[0] if leaving else "-z"
        out[side] = abs(case.input_torque)
    elif shaft == req.stages[-1].gear_shaft and leaving:
        for side in leaving:
            out[side] = abs(torques[shaft]) / len(leaving)
    return out


def _moments_along(points, za: float, zb: float, seat_a, loads_on):
    """The bending moment's two components at each z of `points`, from what lies on the -z side
    of the section: the -z support's reaction and the gears' forces and couples."""
    out = []
    ra = (-seat_a.force[0], -seat_a.force[1])  # the bearing's reaction on the shaft
    for z in points:
        mx = my = 0.0
        # reaction at za: r = (0, 0, za - z), F = (ra_x, ra_y, 0)
        dz = za - z
        mx += -dz * ra[1]
        my += dz * ra[0]
        for g, zg in loads_on:
            if zg >= z:
                continue
            dzg = zg - z
            arm = (g.point[0] - g.centre[0], g.point[1] - g.centre[1], dzg)
            f = g.force
            mx += arm[1] * f[2] - arm[2] * f[1]
            my += arm[2] * f[0] - arm[0] * f[2]
        out.append((mx, my))
    return out


def _slope_planes(za, zb, moments, ei):
    """The integrals of each moment component over EI along a simply supported span, the constant
    set so that the deflection returns to zero at the +z support."""
    n = len(moments)
    h = (zb - za) / (n - 1)
    out = []
    for plane in (0, 1):
        k = [m[plane] / ei for m in moments]
        theta = [0.0]
        for i in range(1, n):
            theta.append(theta[-1] + 0.5 * (k[i - 1] + k[i]) * h)
        y = [0.0]
        for i in range(1, n):
            y.append(y[-1] + 0.5 * (theta[i - 1] + theta[i]) * h)
        # y(zb) = theta_a·L + y_end = 0 sets the slope at the -z support.
        theta_a = -y[-1] / (zb - za)
        out.append([theta_a + t for t in theta])
    return out


def _slope_vectors(za, zb, moments, ei) -> list[tuple[float, float]]:
    """The shaft's lean (dx/dz, dy/dz) at each point, against the chord between its bearings: the
    direction its deflected axis points. With the moments taken from the -z side as
    `_moments_along` does, EI·x'' = -M_y and EI·y'' = +M_x, so the lean is (-∫M_y/EI, +∫M_x/EI)."""
    planes = _slope_planes(za, zb, moments, ei)
    return [(-my, mx) for mx, my in zip(planes[0], planes[1], strict=True)]


def _slopes(za, zb, moments, ei):
    """The slope's size along a simply supported span from its moment diagram (two planes)."""
    return [math.hypot(a, b) for a, b in _slope_vectors(za, zb, moments, ei)]


def sections(
    spec: HousingDesignSpec,
    layout: Layout,
    cases: list[CaseForces],
    loads: list[CaseLoads],
    bores: dict[tuple[str, str], float] | None = None,
) -> list[ShaftSection]:
    """Every shaft's section needs over all load cases. `bores` gives each seat's selected bore,
    the beam's least diameter between the bearings."""
    material = spec.requirement.shaft_material
    if material is None:
        raise ValueError("the shaft sections need the contract's shaft_material")
    sy = value_in(material.yield_strength, "MPa")
    e = value_in(material.youngs_modulus, "MPa")
    n = value_in(material.design_factor, "1")
    carriers = {c.shaft: c for c in spec.requirement.shaft_layout.carriers}
    limits = {t.bearing_type: value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
    types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
    planes = dict(layout.planes)
    bores = bores or {}
    out = []
    for stack in layout.shafts:
        s = stack.shaft
        za, zb = stack.bearing("-z").centre, stack.bearing("+z").centre
        bore_needed = {"-z": 0.0, "+z": 0.0}
        seat_torque = {"-z": 0.0, "+z": 0.0}
        gear_needed: dict[str, float] = {}
        per_case = []
        for case, cl in zip(cases, loads, strict=True):
            ends = _end_torques(spec, s, case)
            for side in ("-z", "+z"):
                seat_torque[side] = max(seat_torque[side], ends[side])
                bore_needed[side] = max(bore_needed[side], _strength(n, sy, 0.0, ends[side]))
            named = [
                (f"{m.stage} {g.member}", g, planes[m.stage])
                for m in case.meshes
                for g in (m.pinion, m.gear)
                if g.shaft == s
            ]
            loads_on = [(g, z) for _, g, z in named]
            seat_a = cl.seat(s, "-z")
            moments = _moments_along([z for _, _, z in named], za, zb, seat_a, loads_on)
            for (name, g, _), (mx, my) in zip(named, moments, strict=True):
                # The gear's own torque is the most the shaft carries beside it.
                d = _strength(n, sy, math.hypot(mx, my), abs(g.moment[2]))
                gear_needed[name] = max(gear_needed.get(name, 0.0), d)
            per_case.append((named, loads_on, seat_a))
        if s in carriers and carriers[s].hub_diameter is not None:
            hub = value_in(carriers[s].hub_diameter, "mm")
            bore_needed = {k: max(v, hub) for k, v in bore_needed.items()}
        diameter = max(
            [*gear_needed.values(), *(bores.get((s, k), bore_needed[k]) for k in ("-z", "+z"))]
        )
        diameter = math.ceil(diameter)
        # Stiffen until no bearing or gear slopes beyond its limit, in any case.
        points = [za + (zb - za) * i / (STEPS - 1) for i in range(STEPS)]
        while True:
            inertia = math.pi * diameter**4 / 64.0
            worst_b = {"-z": 0.0, "+z": 0.0}
            worst_g: dict[str, float] = {}
            for named, loads_on, seat_a in per_case:
                slope = _slopes(
                    za, zb, _moments_along(points, za, zb, seat_a, loads_on), e * inertia
                )
                worst_b["-z"] = max(worst_b["-z"], slope[0])
                worst_b["+z"] = max(worst_b["+z"], slope[-1])
                for name, _, zg in named:
                    i = min(range(STEPS), key=lambda j: abs(points[j] - zg))
                    worst_g[name] = max(worst_g.get(name, 0.0), slope[i])
            within = all(
                worst_b[side] <= limits.get(types.get((s, side), ""), math.inf)
                for side in ("-z", "+z")
            ) and all(v <= GEAR_SLOPE_LIMIT for v in worst_g.values())
            if within or diameter > 200:
                break
            diameter += 1
        lean = {}
        for (_named, loads_on, seat_a), case in zip(per_case, cases, strict=True):
            vectors = _slope_vectors(
                za, zb, _moments_along(points, za, zb, seat_a, loads_on), e * inertia
            )
            lean[case.name] = {"-z": vectors[0], "+z": vectors[-1]}
        out.append(
            ShaftSection(
                shaft=s,
                bore_needed=bore_needed,
                torque_at_seat=seat_torque,
                gear_diameter_needed=gear_needed,
                diameter=float(diameter),
                slope_at_bearing=worst_b,
                slope_at_gear=worst_g,
                lean_at_bearing=lean,
            )
        )
    return out
