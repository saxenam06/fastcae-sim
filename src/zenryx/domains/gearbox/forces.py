"""The forces and moments at each gear mesh, in every load case (GBX-1).

**The base-circle form,** which holds for profile-shifted helical gears (the load tool's plan,
docs/features/gearbox/2026-10-08-load-tool-plan.md, §1-2; the engineer, 9 October 00:57). The torque
T on a pinion is carried along the line of action at its base circle:

    Fbt = 2 T / db1                     the transmitted force, in the transverse plane
    Ft  = Fbt cos(alpha_wt)             tangential, at the working pitch circle
    Fr  = Fbt sin(alpha_wt)             radial, pushing the two gears apart
    Fa  = Fbt tan(beta_b)               axial, along the base helix

with alpha_wt the working transverse pressure angle and beta_b the base helix angle
(tan beta_b = tan beta cos alpha_t). Ft times the working pitch radius gives back the torque, and
at zero profile shift the form is the textbook one: Ft = 2T/d, Fr = Ft tan(alpha_n)/cos(beta),
Fa = Ft tan(beta) (Shigley Ch. 13).

**Directions, in the contract's frame:** z along the shafts; the end view in x-y, the axes where
`zenryx.contract.train.axis_positions` puts them. Torques are signed about +z (the right-hand rule).
- The pitch point P lies on the line of centres, at the pinion's working pitch radius from it.
- Tangential: the force on the pinion resists the torque that drives its shaft, and the gear gets
  the opposite force. The gear's shaft therefore turns the other way, with z2/z1 of the torque.
- Radial: on each gear, from P towards its own axis.
- Axial: a flank lies along its tooth's helix, so the axial part of the force on a gear is
  -h · f_theta · tan(beta_w), with h = +1 for a right hand and -1 for a left, f_theta the
  tangential force along the gear's own +theta, and tan(beta_w) = tan(beta) dw/d. This is the
  hand rule for thrust: curl the fingers of the driver's own hand (right for a right-hand helix)
  in its sense of rotation, and the thumb gives the driver's thrust.
- Each gear's moment about its own centre on its axis, at its mid-face: the torque about z, and
  the axial force's moment Fa · rw in the plane. The layout (GBX-2) sets the mid-face's z.

**Load cases:** one per torque in the contract. The torque's sense comes from its direction and
the input's sense of rotation in forward drive (`requirement.forward_rotation`): drive turns the
input forwards; reverse drives it backwards and regeneration brakes it, so both reverse the torque.
Reverse and regeneration at the same torque therefore load the teeth alike.

Derived physics is computed, never typed: what this gives goes into a contract only through the
load tool's own stamp (GBX-4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from zenryx.contract.involute import mesh_geometry
from zenryx.contract.model import GearStage, HousingDesignSpec
from zenryx.contract.train import axis_positions

TOOL = "zenryx.domains.gearbox.forces"
VERSION = "0.1.0"

Point = tuple[float, float]
Vector3 = tuple[float, float, float]

# A torque's sense against the input's forward rotation: drive turns it forwards; reverse drives
# it backwards and regeneration brakes it, so both act against the forward rotation.
SENSE = {"drive": 1.0, "reverse": -1.0, "regeneration": -1.0}


@dataclass(frozen=True)
class GearLoad:
    """What one gear of a mesh carries: the force at the pitch point (N) and its moment about the
    gear's own centre (N·mm): the torque about z and the axial force's moment in the plane."""

    shaft: str
    member: str
    centre: Point
    point: Point
    force: Vector3
    moment: Vector3


@dataclass(frozen=True)
class MeshForces:
    """One mesh in one load case: the magnitudes (N) and what each of its two gears carries."""

    stage: str
    transmitted: float
    tangential: float
    radial: float
    axial: float
    pinion_torque: float
    pinion: GearLoad
    gear: GearLoad


@dataclass(frozen=True)
class CaseForces:
    """One load case: the input's torque (N·mm, signed about +z), each mesh, and the torque each
    shaft passes on between its meshes (signed about +z)."""

    name: str
    input_torque: float
    meshes: tuple[MeshForces, ...]
    shaft_torques: tuple[tuple[str, float], ...]


def _cross(a: Vector3, b: Vector3) -> Vector3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def mesh_forces(
    stage: str,
    z: tuple[int, int],
    normal_module: float,
    pressure_angle: float,
    helix_angle: float,
    shifts: tuple[float, float],
    pinion_hand: str,
    torque: float,
    centres: tuple[Point, Point],
    shafts: tuple[str, str] = ("pinion", "gear"),
) -> MeshForces:
    """The forces of one helical mesh. `torque` drives the pinion's shaft (N·mm, signed about +z);
    angles in radians, lengths in mm; `centres` are the pinion's and the gear's axes in the end
    view, a working centre distance apart; `pinion_hand` is "left" or "right"."""
    geometry = mesh_geometry(z[0], z[1], normal_module, pressure_angle, helix_angle, *shifts)
    alpha_t = geometry.transverse_pressure_angle
    alpha_wt = geometry.working_pressure_angle
    beta_b = math.atan(math.tan(helix_angle) * math.cos(alpha_t))
    db1 = geometry.base_diameters[0]
    rw1, rw2 = (d / 2 for d in geometry.working_pitch_diameters)
    tan_beta_w = (
        math.tan(helix_angle)
        * geometry.working_pitch_diameters[0]
        / (geometry.reference_diameters[0])
    )

    transmitted = 2 * abs(torque) / db1
    tangential = transmitted * math.cos(alpha_wt)
    radial = transmitted * math.sin(alpha_wt)
    axial = transmitted * math.tan(beta_b)

    (px, py), (gx, gy) = centres
    distance = math.hypot(gx - px, gy - py)
    if abs(distance - geometry.working_centre_distance) > 1e-6 * distance:
        raise ValueError(
            f"{stage}: its axes are {distance:.4f} mm apart, not the working centre distance "
            f"{geometry.working_centre_distance:.4f} mm"
        )
    ux, uy = (gx - px) / distance, (gy - py) / distance  # from the pinion's axis to the gear's
    point = (px + rw1 * ux, py + rw1 * uy)
    tx, ty = -uy, ux  # the pinion's +theta at the pitch point: z × u

    # Tangential, signed along the pinion's +theta: it resists the torque that drives the pinion.
    f_theta_pinion = -torque / rw1
    # Axial: -h · f_theta · tan(beta_w), each gear's f_theta along its own +theta; the gear's
    # +theta at the pitch point is the pinion's reversed, and its hand is the other one.
    hand = {"right": 1.0, "left": -1.0}[pinion_hand]
    a_pinion = -hand * f_theta_pinion * tan_beta_w
    f_on_pinion = (
        f_theta_pinion * tx - radial * ux,
        f_theta_pinion * ty - radial * uy,
        a_pinion,
    )
    f_on_gear = (-f_on_pinion[0], -f_on_pinion[1], -f_on_pinion[2])

    def load(shaft: str, member: str, centre: Point, force: Vector3) -> GearLoad:
        arm = (point[0] - centre[0], point[1] - centre[1], 0.0)
        return GearLoad(shaft, member, centre, point, force, _cross(arm, force))

    return MeshForces(
        stage=stage,
        transmitted=transmitted,
        tangential=tangential,
        radial=radial,
        axial=axial,
        pinion_torque=torque,
        pinion=load(shafts[0], "pinion", centres[0], f_on_pinion),
        gear=load(shafts[1], "gear", centres[1], f_on_gear),
    )


def _value(entry, unit: str) -> float:
    value, canonical = entry.value.to_canonical()
    if canonical != unit:
        raise ValueError(f"expected {unit}, got {canonical}")
    return value


def _stage_data(stage: GearStage) -> dict:
    needed = (
        "z_pinion",
        "z_gear",
        "normal_module",
        "pressure_angle",
        "helix_angle",
        "profile_shift_pinion",
        "profile_shift_gear",
        "helix_hand_pinion",
    )
    missing = [n for n in needed if getattr(stage, n) is None]
    if missing:
        raise ValueError(f"stage {stage.name!r} needs {', '.join(missing)} for its forces")
    return {
        "z": (int(stage.z_pinion.value), int(stage.z_gear.value)),
        "normal_module": _value(stage.normal_module, "mm"),
        "pressure_angle": _value(stage.pressure_angle, "rad"),
        "helix_angle": _value(stage.helix_angle, "rad"),
        "shifts": (
            _value(stage.profile_shift_pinion, "1"),
            _value(stage.profile_shift_gear, "1"),
        ),
        "pinion_hand": str(stage.helix_hand_pinion.value),
    }


def shaft_axes(spec: HousingDesignSpec) -> dict[str, Point]:
    """Each shaft's axis in the end view (mm): one stage on the x axis; two stages placed by the
    packaging offset (`train.axis_positions`, the intermediate shaft at the origin)."""
    stages = spec.requirement.stages
    data = [_stage_data(s) for s in stages]
    distances = [
        mesh_geometry(
            d["z"][0],
            d["z"][1],
            d["normal_module"],
            d["pressure_angle"],
            d["helix_angle"],
            *d["shifts"],
        ).working_centre_distance
        for d in data
    ]
    if len(stages) == 1:
        return {stages[0].pinion_shaft: (-distances[0], 0.0), stages[0].gear_shaft: (0.0, 0.0)}
    if len(stages) == 2:
        if stages[0].gear_shaft != stages[1].pinion_shaft:
            raise ValueError("the second stage's pinion must sit on the first stage's gear shaft")
        offset = spec.requirement.input_output_offset
        if offset is None:
            raise ValueError("two stages need the input-output offset to place their axes")
        first, middle, last = axis_positions(distances[0], distances[1], _value(offset, "mm"))
        return {
            stages[0].pinion_shaft: first,
            stages[0].gear_shaft: middle,
            stages[1].gear_shaft: last,
        }
    raise NotImplementedError("trains of more than two stages need more packaging inputs")


def case_forces(spec: HousingDesignSpec) -> list[CaseForces]:
    """Every load case's mesh forces, one case per torque the contract gives (it must act on the
    first stage's pinion shaft)."""
    req = spec.requirement
    stages = req.stages
    if not stages:
        raise ValueError("the forces need the gear train's stages")
    rotation = req.forward_rotation.value if req.forward_rotation is not None else "+z"
    forward = {"+z": 1.0, "-z": -1.0}[rotation]
    axes = shaft_axes(spec)
    data = [_stage_data(s) for s in stages]
    cases = []
    for t in req.torques:
        if t.shaft != stages[0].pinion_shaft:
            raise ValueError(f"a torque on {t.shaft!r}: the forces start from the input's torque")
        if t.direction not in SENSE:
            raise ValueError(f"no sense of rotation is known for a {t.direction!r} torque")
        torque_in = forward * SENSE[t.direction] * abs(_value(t.torque, "N*mm"))
        driving = torque_in
        meshes = []
        passed = [(stages[0].pinion_shaft, torque_in)]
        for stage, d in zip(stages, data, strict=True):
            mesh = mesh_forces(
                stage.name,
                d["z"],
                d["normal_module"],
                d["pressure_angle"],
                d["helix_angle"],
                d["shifts"],
                d["pinion_hand"],
                driving,
                (axes[stage.pinion_shaft], axes[stage.gear_shaft]),
                (stage.pinion_shaft, stage.gear_shaft),
            )
            meshes.append(mesh)
            driving = mesh.gear.moment[2]  # the mesh turns the gear's shaft; it drives the next
            passed.append((stage.gear_shaft, driving))
        cases.append(
            CaseForces(
                name=f"{t.kind} {t.direction}",
                input_torque=torque_in,
                meshes=tuple(meshes),
                shaft_torques=tuple(passed),
            )
        )
    return cases
