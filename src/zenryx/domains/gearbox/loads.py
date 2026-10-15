"""The loads each bearing puts into its seat, in every load case (GBX-2, the chain's step 6).

**Each shaft is a rigid body on its two bearings** (statics in both planes, with the axial
force's moment; JTEKT eq. 5-29, Shigley Ch. 3 and 7). The mesh forces of GBX-1 act at their pitch
points, at the gears' mid-faces from the layout. The two bearings take the radial forces at their
supports; the torque about the shaft passes on to the next mesh or out of the housing.

**The axial force** goes as the arrangement says (`shaft_layout.bearings`, Shigley Ch. 11):
- a locating bearing takes all of the shaft's thrust, either way; a floating one none;
- a pair whose bearings each take the thrust towards their own end ("own_side": an adjusted
  tapered pair, or a cross-located ball pair): each bearing carries at least its induced axial
  force, 0.5·Fr/Y for a tapered bearing and none for a ball bearing (Machine Design 2005; NSK's
  catalogue), and the pair's two axial loads differ by the shaft's thrust.

**What the housing feels:** each seat takes the opposite of its bearing's reaction on the shaft:
its radial force, and its axial force where its bearing takes thrust. The wheels' torque leaves
through the output and never reaches the housing. The motor's reaction depends on who holds it
(`requirement.motor_held_by`):
- held by the vehicle, the motor drives the input through a flexible coupling and the housing
  carries none of its torque (the EV reducer's contract, the engineer, 10 October 13:21); the
  mounts hold the housing against the output's torque less the input's, (i - 1) × T_in;
- bolted to the housing at its flange, the stator pushes back on the housing with the opposite of
  the motor's torque, about the input's axis, and the mounts hold i × T_in.

The supports sit at the bearings' centres. A tapered bearing's effective load centre lies off its
centre by its catalogue's offset; GBX-3 refines that once a bearing is selected.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from zenryx.contract.model import HousingDesignSpec
from zenryx.domains.gearbox.forces import CaseForces, GearLoad, Vector3
from zenryx.domains.gearbox.layout import Layout

TOOL = "zenryx.domains.gearbox.loads"
VERSION = "0.1.0"

# The induced-force factor's Y for a tapered roller bearing before one is selected: a usual value
# for the 302 and 320 series (the selection replaces it with the bearing's own).
FIRST_GUESS_Y = 1.6


@dataclass(frozen=True)
class SeatLoad:
    """What one bearing seat carries in one load case (N, in the contract's frame): the force on
    the housing at the support, its radial size, and its axial part (signed along z)."""

    shaft: str
    side: str
    z: float
    force: Vector3
    radial: float
    axial: float


@dataclass(frozen=True)
class CaseLoads:
    """One load case on the housing: every seat's load, and the motor's reaction torque on the
    housing (N·mm, signed about +z, at the input's axis; 0 when the vehicle holds the motor)."""

    name: str
    seats: tuple[SeatLoad, ...]
    motor_torque: float
    input_shaft: str

    def seat(self, shaft: str, side: str) -> SeatLoad:
        return next(s for s in self.seats if s.shaft == shaft and s.side == side)


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def shaft_seats(
    shaft: str,
    loads: list[tuple[GearLoad, float]],
    supports: tuple[float, float],
    roles: dict[str, tuple[str, str]],
    y_factors: dict[str, float] | None = None,
) -> tuple[SeatLoad, SeatLoad]:
    """One shaft's two seat loads. `loads` are its gears' loads, each with the z of its mid-face;
    `supports` the z of its -z and +z bearings' supports; `roles` each side's (bearing type, axial
    role); `y_factors` a tapered bearing's Y by side."""
    za, zb = supports
    span = zb - za
    if span <= 0:
        raise ValueError(f"{shaft}: its +z support must lie beyond its -z support")
    force = [0.0, 0.0, 0.0]
    moment = [0.0, 0.0, 0.0]  # about the -z support, on the shaft's axis
    for g, z in loads:
        shifted = _cross((0.0, 0.0, z - za), g.force)
        for k in range(3):
            force[k] += g.force[k]
            moment[k] += g.moment[k] + shifted[k]
    # Radial: the +z support's reaction balances the moments in the two planes; the -z support's
    # balances what is left of the force.
    rb = (-moment[1] / span, moment[0] / span)
    ra = (-force[0] - rb[0], -force[1] - rb[1])
    radial = {"-z": math.hypot(*ra), "+z": math.hypot(*rb)}

    # Axial: the shaft's thrust, shared as the arrangement says. on_housing is the axial force each
    # seat takes, signed along z.
    thrust = force[2]
    on_housing = {"-z": 0.0, "+z": 0.0}
    locating = [side for side, (_, role) in roles.items() if role == "locating"]
    if locating:
        on_housing[locating[0]] = thrust  # the shaft's push goes into the housing there
    elif set(roles) == {"-z", "+z"} and all(role == "own_side" for _, role in roles.values()):

        def induced(side: str) -> float:
            if roles[side][0] != "tapered_roller":
                return 0.0
            return 0.5 * radial[side] / (y_factors or {}).get(side, FIRST_GUESS_Y)

        fa, fb = induced("-z"), induced("+z")
        # Bearing -z takes thrust towards -z, bearing +z towards +z; the shaft balances when the
        # +z bearing's axial load is the -z bearing's plus the thrust. Each carries at least its
        # induced force.
        if fa + thrust >= fb:
            load_a, load_b = fa, fa + thrust
        else:
            load_a, load_b = fb - thrust, fb
        on_housing = {"-z": -load_a, "+z": load_b}
    else:
        raise ValueError(
            f"{shaft}: its bearings take the thrust as {roles}; give one locating bearing, or "
            "two that each take their own side"
        )
    return tuple(
        SeatLoad(shaft, side, z, (-r[0], -r[1], on_housing[side]), radial[side], on_housing[side])
        for side, r, z in (("-z", ra, za), ("+z", rb, zb))
    )


def seat_loads(
    spec: HousingDesignSpec,
    layout: Layout,
    cases: list[CaseForces],
    y_factors: dict[tuple[str, str], float] | None = None,
    supports: dict[tuple[str, str], float] | None = None,
) -> list[CaseLoads]:
    """The seat loads in every case. `y_factors` gives a tapered bearing's Y and `supports` a
    bearing's support z (its effective load centre), keyed by (shaft, side), once it is selected;
    until then a usual Y and the bearing's centre stand in."""
    arrangement = {
        (b.shaft, b.side.value): (b.type, b.axial.value)
        for b in spec.requirement.shaft_layout.bearings
    }
    y_factors = y_factors or {}
    supports = supports or {}
    planes = dict(layout.planes)
    on_housing = spec.requirement.motor_on_housing()
    out = []
    for case in cases:
        on: dict[str, list[tuple[GearLoad, float]]] = {}
        for mesh in case.meshes:
            for g in (mesh.pinion, mesh.gear):
                on.setdefault(g.shaft, []).append((g, planes[mesh.stage]))
        seats: list[SeatLoad] = []
        for stack in layout.shafts:
            s = stack.shaft
            za = supports.get((s, "-z"), stack.bearing("-z").centre)
            zb = supports.get((s, "+z"), stack.bearing("+z").centre)
            roles = {
                side: arrangement[(s, side)] for side in ("-z", "+z") if (s, side) in arrangement
            }
            ys = {side: y_factors[(s, side)] for side in ("-z", "+z") if (s, side) in y_factors}
            seats += shaft_seats(s, on.get(s, []), (za, zb), roles, ys)
        motor = -case.input_torque if on_housing else 0.0
        out.append(
            CaseLoads(case.name, tuple(seats), motor, spec.requirement.stages[0].pinion_shaft)
        )
    return out
