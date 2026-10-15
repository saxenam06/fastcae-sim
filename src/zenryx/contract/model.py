"""The layers of the contract (spec §4): task, requirement, interfaces, physics cases, limits,
manufacturing profile, the published reference band and the assumptions list.

Interfaces are named by geometric kind (cylindrical seat, split face, mount pad, motor flange,
port); what a seat is for (an input shaft's bearing) lives in the contract's data, never in code.
Every model forbids extra fields, so nothing beyond the schema - an answer, a result - can be
carried in a contract.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenryx.contract.entry import Entry

Stage = Literal["posed", "completed", "frozen"]
RequirementStyle = Literal["package", "gear_train"]
BearingType = Literal[
    "deep_groove_ball",
    "cylindrical_roller",
    "tapered_roller",
    "angular_contact_ball",
    "spherical_roller",
]
Name = Annotated[str, Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_.:/-]*$")]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskInfo(_Model):
    """What the task is, and what an attempt may spend."""

    id: Name
    title: str = Field(min_length=1)
    family: str = Field(min_length=1)
    level: Literal["L1"]
    priorities: list[str] = []
    budget_fe_proofs: int = Field(gt=0)
    budget_hours: float = Field(gt=0)


class TorqueSpec(_Model):
    """A torque, with the shaft it acts on, its kind and its direction."""

    shaft: Name
    kind: Literal["peak", "nominal", "continuous", "maximum"]
    direction: Literal["drive", "regeneration", "reverse"]
    torque: Entry


class SpeedSpec(_Model):
    shaft: Name
    kind: Literal["maximum", "base", "rated"]
    speed: Entry


class PowerSpec(_Model):
    """A power, with its shaft, its kind and the speed it is stated at."""

    shaft: Name
    kind: Literal["peak", "nominal", "continuous", "rated"]
    power: Entry
    at_speed: Entry | None = None


class GearStage(_Model):
    """One gear stage. Empty in a package-style contract until the front-end derives it."""

    name: Name
    pinion_shaft: Name
    gear_shaft: Name
    z_pinion: Entry | None = None
    z_gear: Entry | None = None
    normal_module: Entry | None = None
    pressure_angle: Entry | None = None
    helix_angle: Entry | None = None
    helix_hand_pinion: Entry | None = None
    face_width_pinion: Entry | None = None
    face_width_gear: Entry | None = None
    profile_shift_pinion: Entry | None = None
    profile_shift_gear: Entry | None = None
    centre_distance: Entry | None = None


class BearingSpec(_Model):
    """A bearing by its designation, and the seat that hosts it."""

    seat: Name
    designation: Entry
    type: BearingType
    outer_diameter: Entry | None = None
    width: Entry | None = None


class ShaftEnd(_Model):
    """One end of a shaft, by the shaft's name and its side along the shafts ("-z" or "+z"). Where
    the shaft leaves the housing, `room` is the diameter of what it joins beyond the end face (a
    half-shaft's joint), which the housing keeps out of to the packaging space's end."""

    shaft: Name
    side: Entry
    room: Entry | None = None


class BearingPlace(_Model):
    """One bearing of the arrangement: its shaft, its end ("-z" or "+z"), its type, and how it
    takes the shaft's axial force: "locating" (all of it, either way), "floating" (none), or
    "own_side" (the thrust towards its own end, as each bearing of an adjusted tapered pair or of
    a cross-located pair does)."""

    shaft: Name
    side: Entry
    type: BearingType
    axial: Entry


class ShaftCarrier(_Model):
    """A carrier a shaft's gear rides on between the shaft's two bearings, such as a differential
    case. It fixes the bearings' spacing (centre to centre) and keeps the room of its body, a
    cylinder of its diameter between the bearings; the gear sits beside the bearing at one end."""

    name: Name
    shaft: Name
    bearing_spacing: Entry
    diameter: Entry
    gear_beside: Entry
    # The hubs its bearings sit on: their least diameter (the half-shafts pass through them).
    hub_diameter: Entry | None = None


class ShaftMaterial(_Model):
    """The shafts' steel, for their sections (GBX-3): its yield and stiffness, and the design
    factor the peak torques are taken with."""

    name: str = Field(min_length=1)
    yield_strength: Entry
    youngs_modulus: Entry
    design_factor: Entry


class ShaftLayout(_Model):
    """How the gears and bearings are spaced along each shaft: by gaps (the engineer, 9 Oct
    00:06). The load tool (GBX-2) stacks each shaft from a datum: the space behind a bearing, the
    bearing, the gap, the gear (with the gap to a second gear on the same shaft), the gap, the
    bearing, the space behind. The positions follow; the bearings' widths come from their
    selection, so the stack goes round with it.

    The space behind a bearing depends on its end (the engineer, 9 Oct 01:06): a closed bore needs
    only the wall behind it; where the shaft leaves the housing it needs a seal and its seat. The
    least clearances are what the check holds parts to: along the shafts, for parts on different
    shafts that overlap seen along the shafts; and radially, from a gear's tips to the wall."""

    bearing_to_gear: Entry
    behind_bearing: Entry
    behind_bearing_sealed: Entry | None = None
    sealed_ends: list[ShaftEnd] = []
    gear_to_gear: Entry | None = None
    min_axial_clearance: Entry | None = None
    min_radial_clearance: Entry | None = None
    # A seal's radial section, (outside Ø - bore) / 2: at a sealed end the shaft leaves through a
    # bore of its least bore plus twice this, fitted from outside.
    seal_section: Entry | None = None
    # On the shaft two stages share: the side ("-z" or "+z") its first-stage gear sits on.
    first_stage_side: Entry | None = None
    bearings: list[BearingPlace] = []
    carriers: list[ShaftCarrier] = []


class InstallationSpace(_Model):
    """The space the housing must stay inside: a box, or the layout's envelope plus a clearance."""

    kind: Literal["box", "layout_envelope"]
    box_min: Entry | None = None
    box_max: Entry | None = None
    clearance: Entry | None = None

    @model_validator(mode="after")
    def _complete(self) -> InstallationSpace:
        if self.kind == "box" and (self.box_min is None or self.box_max is None):
            raise ValueError("a box installation space needs box_min and box_max")
        if self.kind == "layout_envelope" and self.clearance is None:
            raise ValueError("a layout_envelope installation space needs its clearance")
        return self


_STAGE_NEEDS = ("z_pinion", "z_gear", "normal_module", "pressure_angle", "helix_angle")


class Requirement(_Model):
    """The engineer's input: the duty, the ratio, the gear train or the package, the bearings.

    Only what can be chosen freely (the engineer, 8 October). The ratio is a requirement only
    where no teeth are given; the teeth fix it otherwise. A stage's centre distance is an input
    only where its gear data do not fix it (the validator's consistency.redundant)."""

    style: RequirementStyle
    torques: list[TorqueSpec] = Field(min_length=1)
    speeds: list[SpeedSpec] = []
    powers: list[PowerSpec] = []
    total_ratio: Entry | None = None
    ratio_tolerance: Entry | None = None
    input_output_offset: Entry | None = None
    # The input shaft's sense of rotation in forward drive, "+z" or "-z" (the right-hand rule about
    # the shafts' axis). It sets the forces' directions, not their sizes.
    forward_rotation: Entry | None = None
    service_life: Entry | None = None
    gear_material: Entry | None = None
    shaft_material: ShaftMaterial | None = None
    gear_quality: Entry | None = None
    stages: list[GearStage] = []
    bearings: list[BearingSpec] = []
    shaft_layout: ShaftLayout | None = None
    # The outside interfaces the vehicle and the motor give (the engineer, 9 Oct 02:16).
    mounts: list[MountPad] = []
    # Who holds the motor's stator: "vehicle" (the motor drives the input shaft through a flexible
    # coupling and the housing carries none of its torque; then no flange) or "housing" (it bolts
    # to the housing at `motor_flange`, which then takes the motor's reaction torque). Unset, the
    # flange's presence says it.
    motor_held_by: Entry | None = None
    motor_flange: MotorFlange | None = None
    installation_space: InstallationSpace

    @model_validator(mode="after")
    def _style(self) -> Requirement:
        if self.style == "package" and self.input_output_offset is None:
            raise ValueError("a package-style requirement needs the input_output_offset")
        if self.style == "gear_train":
            if not self.stages:
                raise ValueError("a gear_train-style requirement needs its stages")
            for stage in self.stages:
                missing = [n for n in _STAGE_NEEDS if getattr(stage, n) is None]
                if missing:
                    raise ValueError(f"gear_train stage {stage.name!r} needs {', '.join(missing)}")
        return self

    @model_validator(mode="after")
    def _motor(self) -> Requirement:
        held = None if self.motor_held_by is None else self.motor_held_by.value
        if held not in (None, "vehicle", "housing"):
            raise ValueError(f"motor_held_by is 'vehicle' or 'housing', not {held!r}")
        if held == "housing" and self.motor_flange is None:
            raise ValueError("a motor held by the housing needs its motor_flange")
        if held == "vehicle" and self.motor_flange is not None:
            raise ValueError("a motor held by the vehicle has no motor_flange on the housing")
        return self

    def motor_on_housing(self) -> bool:
        """Whether the motor's stator bolts to the housing, so the housing takes its torque."""
        if self.motor_held_by is not None:
            return self.motor_held_by.value == "housing"
        return self.motor_flange is not None


class CylindricalSeat(_Model):
    """A machined bore that hosts a bearing."""

    name: Name
    shaft: Name
    centre: Entry
    axis: Entry
    diameter: Entry
    width: Entry
    shoulder: Literal["+axis", "-axis"]
    stock: Entry
    # The bearing the load tool selected for it (GBX-3), and that bearing's type.
    bearing: Entry | None = None
    bearing_type: BearingType | None = None


class SplitFace(_Model):
    """A machined plane where two housing parts meet, with its bolt pattern."""

    name: Name
    origin: Entry
    normal: Entry
    bolt_count: Entry
    bolt_hole_diameter: Entry
    bolt_pitch_circle: Entry | None = None


class MountPad(_Model):
    """A boss that holds the housing in the vehicle: the vehicle's bracket bolts to it. Its centre
    is the middle of the boss on its bolt's axis, and its normal that axis, square to the boss's
    machined faces at both ends; its size the boss's diameter and its length along the axis, and
    the bolt's hole. `bracket_room` is the diameter the vehicle's bracket and bolt take beyond
    both faces, as far as the boss is long (the engineer, 13 October: no higher)."""

    name: Name
    centre: Entry
    normal: Entry
    support: Literal["fixed", "elastic"]
    stiffness: Entry | None = None
    diameter: Entry | None = None
    length: Entry | None = None
    hole_diameter: Entry | None = None
    bracket_room: Entry | None = None

    @model_validator(mode="after")
    def _stiffness(self) -> MountPad:
        if self.support == "elastic" and self.stiffness is None:
            raise ValueError("an elastic mount pad needs its stiffness")
        return self


class MotorFlange(_Model):
    name: Name
    centre: Entry
    axis: Entry
    spigot_diameter: Entry
    bolt_count: Entry
    bolt_circle: Entry


class Port(_Model):
    name: Name
    centre: Entry
    axis: Entry
    diameter: Entry
    role: Literal["fill", "drain", "breather"]


class Interfaces(_Model):
    """The machined core: fixed at L1."""

    seats: list[CylindricalSeat] = Field(min_length=1)
    split_faces: list[SplitFace] = []
    mount_pads: list[MountPad] = []
    motor_flanges: list[MotorFlange] = []
    ports: list[Port] = []


class SeatLoad(_Model):
    seat: Name
    force: Entry


class InterfaceMoment(_Model):
    """A moment on an interface (N·mm, a vector in the contract's frame), such as the motor's
    reaction torque on its flange."""

    interface: Name
    moment: Entry


class LoadCase(_Model):
    name: Name
    seat_loads: list[SeatLoad] = Field(min_length=1)
    interface_moments: list[InterfaceMoment] = []


class MeshOrder(_Model):
    """A gear-mesh order: excitations per revolution of the named shaft."""

    stage: Name
    shaft: Name
    order: Entry


class PhysicsCases(_Model):
    """Derived by the front-end, every value stamped with its tool."""

    load_cases: list[LoadCase] = Field(min_length=1)
    mesh_orders: list[MeshOrder] = []


class TiltLimit(_Model):
    bearing_type: BearingType
    limit: Entry


class Limits(_Model):
    """What must hold, and the rule an attempt is graded by (fixed before any attempt)."""

    verdict_rule_version: str = Field(min_length=1)
    mesh_misalignment_share: Entry
    centre_distance_share: Entry
    ovalisation_share: Entry
    bearing_tilt: list[TiltLimit] = Field(min_length=1)
    order_separation: Entry
    # The duty speed the gear orders are checked at, by its kind ("rated", "maximum", "base"): the
    # criterion points at the duty's speed instead of copying it (the engineer, 9 Oct 01:06).
    order_check_at: Entry
    model_margin: Entry
    objective: Literal["least_mass"]
    stress: Literal["recorded"]


class PullDirection(_Model):
    part: Name
    direction: Entry


class JointRules(_Model):
    """How a multi-part housing's parts are bolted where they meet: the process's rules, whatever
    the joint's place (a design's choice). The parts meet on a flange `flange_thickness` deep on
    each side of the joint: a sealing land `land_width` wide round the inside, and the bolts'
    bosses on it. The bolts stand round the inside, their axes `bolt_offset` outside its least
    wall, evenly at most `max_pitch` apart; each through a hole of `hole_diameter` in a boss of
    `boss_diameter`."""

    hole_diameter: Entry
    boss_diameter: Entry
    bolt_offset: Entry
    max_pitch: Entry
    flange_thickness: Entry
    land_width: Entry


class MaterialCard(_Model):
    name: str = Field(min_length=1)
    youngs_modulus: Entry
    poisson_ratio: Entry
    density: Entry
    expansion: Entry | None = None


_CASTING = ("high_pressure_die_casting", "sand_casting")


class ManufacturingProfile(_Model):
    process: Literal["high_pressure_die_casting", "sand_casting", "laser_powder_bed_fusion"]
    pull_directions: list[PullDirection] = []
    draft_inside: Entry | None = None
    draft_outside: Entry | None = None
    draft_min_depth: Entry | None = None
    min_wall: Entry
    max_wall: Entry | None = None
    machining_stock: Entry
    material: MaterialCard
    joint: JointRules | None = None

    @model_validator(mode="after")
    def _casting_rules(self) -> ManufacturingProfile:
        if self.process in _CASTING:
            if not self.pull_directions:
                raise ValueError(f"{self.process} needs its pull directions")
            if self.draft_inside is None or self.draft_outside is None:
                raise ValueError(f"{self.process} needs draft_inside and draft_outside")
        return self


class ReferenceValue(_Model):
    """A published value the designs are set against: band, not limit."""

    source: str = Field(min_length=1)
    quantity: str = Field(min_length=1)
    value: str = Field(min_length=1)
    conditions: str = Field(min_length=1)
    confidence: str = Field(min_length=1)


class Assumption(_Model):
    id: str = Field(pattern=r"^A\d+$")
    what: str = Field(min_length=1)
    value: str = Field(min_length=1)
    why: str = Field(min_length=1)
    varied: bool


class HousingDesignSpec(_Model):
    """The contract: one housing design problem at L1, every value with its provenance."""

    schema_version: Literal["0.1"]
    stage: Stage
    task: TaskInfo
    requirement: Requirement
    interfaces: Interfaces | None = None
    physics: PhysicsCases | None = None
    limits: Limits
    manufacturing: ManufacturingProfile
    references: list[ReferenceValue] = []
    assumptions: list[Assumption] = []
    frozen_hash: str | None = None
