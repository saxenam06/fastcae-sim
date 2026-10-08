"""The contract's validator (spec §7): every refusal names its rule, the entry, and why.

Rules, in four groups:
    schema         the contract must load: types, units, required entries (pydantic's errors)
    provenance.*   every assumption an entry points to is listed
    stage.*        posed carries no physics; derived and frozen carry interfaces and physics,
                   every physics value derived by its tool; a frozen contract carries its own hash
    consistency.*  dimensions; ratio; centre distances; the offset; seats inside the space;
                   power against torque; unique names; references to seats; unit axes;
                   bearings against their seats

The bound (can any design meet this?) needs topology optimisation and is not checked here.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from zenryx.contract.canonical import spec_hash
from zenryx.contract.entry import Entry
from zenryx.contract.involute import working_centre_distance
from zenryx.contract.model import GearStage, HousingDesignSpec
from zenryx.contract.units import Quantity, Vector

CENTRE_DISTANCE_TOLERANCE_MM = 0.1  # published centre distances are rounded to 0.1-1 mm
POWER_TOLERANCE = 0.02
UNIT_VECTOR_TOLERANCE = 1e-6


class Refusal(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule: str
    entry: str
    reason: str


def _walk(obj: Any, path: str) -> Iterator[tuple[str, Entry]]:
    """Every Entry in the contract, with its dotted path."""
    if isinstance(obj, Entry):
        yield path, obj
        return
    if isinstance(obj, BaseModel):
        for name in type(obj).model_fields:
            yield from _walk(getattr(obj, name), f"{path}.{name}" if path else name)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            yield from _walk(item, f"{path}[{i}]")


def _canonical(entry: Entry) -> tuple[Any, str] | None:
    if isinstance(entry.value, (Quantity, Vector)):
        return entry.value.to_canonical()
    return None


def _scalar(entry: Entry | None) -> float | None:
    """A quantity's canonical value, or an integer count; None if absent."""
    if entry is None:
        return None
    if isinstance(entry.value, Quantity):
        return entry.value.to_canonical()[0]
    if isinstance(entry.value, int) and not isinstance(entry.value, bool):
        return float(entry.value)
    return None


# --- dimensions --------------------------------------------------------------------------------

# the canonical unit each kind of entry must have, by the last part of its path
_DIMENSIONS: dict[str, str] = {
    "torque": "N*mm",
    "speed": "rad/s",
    "at_speed": "rad/s",
    "power": "W",
    "total_ratio": "1",
    "ratio_tolerance": "1",
    "input_output_offset": "mm",
    "service_life": "s",
    "normal_module": "mm",
    "pressure_angle": "rad",
    "helix_angle": "rad",
    "face_width_pinion": "mm",
    "face_width_gear": "mm",
    "profile_shift_pinion": "1",
    "profile_shift_gear": "1",
    "centre_distance": "mm",
    "outer_diameter": "mm",
    "width": "mm",
    "box_min": "mm",
    "box_max": "mm",
    "clearance": "mm",
    "centre": "mm",
    "origin": "mm",
    "axis": "1",
    "normal": "1",
    "direction": "1",
    "diameter": "mm",
    "stock": "mm",
    "bolt_hole_diameter": "mm",
    "bolt_pitch_circle": "mm",
    "spigot_diameter": "mm",
    "bolt_circle": "mm",
    "force": "N",
    "mesh_misalignment_share": "1",
    "centre_distance_share": "1",
    "ovalisation_share": "1",
    "limit": "rad",
    "order_separation": "1",
    "order_check_speeds": "rad/s",
    "model_margin": "1",
    "draft_inside": "rad",
    "draft_outside": "rad",
    "draft_min_depth": "mm",
    "min_wall": "mm",
    "max_wall": "mm",
    "machining_stock": "mm",
    "youngs_modulus": "MPa",
    "poisson_ratio": "1",
    "density": "t/mm3",
    "expansion": "1/K",
}


# entries that hold three components: positions, directions and forces
_VECTOR_FIELDS = frozenset(
    {"box_min", "box_max", "centre", "origin", "axis", "normal", "direction", "force"}
)


def _field_name(path: str) -> str:
    last = path.rsplit(".", 1)[-1]
    return last.split("[", 1)[0]


def _check_dimensions(spec: HousingDesignSpec) -> list[Refusal]:
    out = []
    for path, entry in _walk(spec, ""):
        field = _field_name(path)
        expected = _DIMENSIONS.get(field)
        if expected is not None:
            is_vector = isinstance(entry.value, Vector)
            if field in _VECTOR_FIELDS and not is_vector:
                out.append(
                    Refusal(
                        rule="consistency.shape",
                        entry=path,
                        reason="needs three components (a vector in the contract's frame)",
                    )
                )
                continue
            if field not in _VECTOR_FIELDS and is_vector:
                out.append(
                    Refusal(
                        rule="consistency.shape",
                        entry=path,
                        reason="needs a single value, not a vector",
                    )
                )
                continue
        canonical = _canonical(entry)
        if expected is None or canonical is None:
            continue
        if canonical[1] != expected:
            out.append(
                Refusal(
                    rule="consistency.dimension",
                    entry=path,
                    reason=f"needs a unit of {expected}, got {entry.value.unit}",
                )
            )
    return out


# --- provenance and stages -------------------------------------------------------------------


def _check_assumptions(spec: HousingDesignSpec) -> list[Refusal]:
    listed = {a.id for a in spec.assumptions}
    out = []
    for path, entry in _walk(spec, ""):
        p = entry.provenance
        if p.kind == "assumption" and p.assumption_id not in listed:
            out.append(
                Refusal(
                    rule="provenance.assumption_listed",
                    entry=path,
                    reason=f"assumption {p.assumption_id} is not in the assumptions list",
                )
            )
    return out


def _check_stage(spec: HousingDesignSpec) -> list[Refusal]:
    out = []
    if spec.stage == "posed" and spec.physics is not None:
        out.append(
            Refusal(
                rule="stage.posed",
                entry="physics",
                reason="a posed contract carries no physics cases; derive them and set the "
                "stage to derived",
            )
        )
    if spec.stage in ("derived", "frozen"):
        for name in ("interfaces", "physics"):
            if getattr(spec, name) is None:
                out.append(
                    Refusal(
                        rule="stage.derived_needs_physics",
                        entry=name,
                        reason=f"a {spec.stage} contract needs its {name}",
                    )
                )
    if spec.physics is not None:
        for path, entry in _walk(spec.physics, "physics"):
            if not entry.stamped():
                out.append(
                    Refusal(
                        rule="stage.physics_is_derived",
                        entry=path,
                        reason="a physics value is derived by its versioned tool, never typed",
                    )
                )
    if spec.stage == "frozen":
        if spec.frozen_hash != spec_hash(spec):
            out.append(
                Refusal(
                    rule="stage.frozen_hash",
                    entry="frozen_hash",
                    reason="the hash does not match the contract's content",
                )
            )
    elif spec.frozen_hash is not None:
        out.append(
            Refusal(
                rule="stage.frozen_hash",
                entry="frozen_hash",
                reason="only a frozen contract carries a hash",
            )
        )
    return out


# --- consistency ------------------------------------------------------------------------------


def _stage_geometry(stage: GearStage) -> tuple[int, int, float, float, float, float, float] | None:
    z1, z2 = _scalar(stage.z_pinion), _scalar(stage.z_gear)
    mn = _scalar(stage.normal_module)
    alpha, beta = _scalar(stage.pressure_angle), _scalar(stage.helix_angle)
    if None in (z1, z2, mn, alpha, beta):
        return None
    x1 = _scalar(stage.profile_shift_pinion) or 0.0
    x2 = _scalar(stage.profile_shift_gear) or 0.0
    return int(z1), int(z2), mn, alpha, beta, x1, x2


def _check_gear_train(spec: HousingDesignSpec) -> list[Refusal]:
    req = spec.requirement
    out = []
    ratios = []
    centre_distances = []
    for i, stage in enumerate(req.stages):
        geometry = _stage_geometry(stage)
        z1, z2 = _scalar(stage.z_pinion), _scalar(stage.z_gear)
        if z1 and z2:
            ratios.append(z2 / z1)
        a_given = _scalar(stage.centre_distance)
        if a_given is not None:
            centre_distances.append(a_given)
        if geometry is not None and a_given is not None:
            a = working_centre_distance(*geometry)
            if abs(a - a_given) > CENTRE_DISTANCE_TOLERANCE_MM:
                out.append(
                    Refusal(
                        rule="consistency.centre_distance",
                        entry=f"requirement.stages[{i}].centre_distance",
                        reason=f"the gears give {a:.3f} mm; the contract states {a_given:.3f} mm "
                        f"(tolerance {CENTRE_DISTANCE_TOLERANCE_MM} mm)",
                    )
                )
    if ratios and len(ratios) == len(req.stages):
        product = math.prod(ratios)
        ratio = _scalar(req.total_ratio)
        tolerance = _scalar(req.ratio_tolerance) or 1e-9
        if ratio is not None and abs(product - ratio) > tolerance * ratio:
            out.append(
                Refusal(
                    rule="consistency.ratio",
                    entry="requirement.total_ratio",
                    reason=f"the stages give {product:.4f}; the contract states {ratio:.4f} "
                    f"± {tolerance:.2%}",
                )
            )
    offset = _scalar(req.input_output_offset)
    if offset is not None and len(centre_distances) == 2:
        a1, a2 = centre_distances
        if not (abs(a1 - a2) - 1e-6 <= offset <= a1 + a2 + 1e-6):
            out.append(
                Refusal(
                    rule="consistency.offset",
                    entry="requirement.input_output_offset",
                    reason=f"two stages of {a1:.2f} and {a2:.2f} mm cannot reach an offset of "
                    f"{offset:.2f} mm (it must lie between {abs(a1 - a2):.2f} and {a1 + a2:.2f})",
                )
            )
    return out


def _check_power(spec: HousingDesignSpec) -> list[Refusal]:
    req = spec.requirement
    out = []
    for i, power in enumerate(req.powers):
        p, omega = _scalar(power.power), _scalar(power.at_speed)
        if p is None or not omega:
            continue
        expected = p / omega * 1e3  # W / (rad/s) = N·m = 1e3 N·mm
        for j, torque in enumerate(req.torques):
            t = _scalar(torque.torque)
            if torque.shaft != power.shaft or t is None:
                continue
            if abs(t - expected) > POWER_TOLERANCE * expected:
                out.append(
                    Refusal(
                        rule="consistency.power",
                        entry=f"requirement.torques[{j}].torque",
                        reason=f"powers[{i}] gives {expected / 1e3:.2f} N·m at its speed; the "
                        f"torque is {t / 1e3:.2f} N·m",
                    )
                )
    return out


def _check_interfaces(spec: HousingDesignSpec) -> list[Refusal]:
    out = []
    faces = spec.interfaces
    if faces is None:
        return out
    groups = {
        "seats": faces.seats,
        "split_faces": faces.split_faces,
        "mount_pads": faces.mount_pads,
        "motor_flanges": faces.motor_flanges,
        "ports": faces.ports,
    }
    seen: dict[str, str] = {}
    for group, items in groups.items():
        for i, item in enumerate(items):
            where = f"interfaces.{group}[{i}].name"
            if item.name in seen:
                out.append(
                    Refusal(
                        rule="consistency.unique_names",
                        entry=where,
                        reason=f"the name {item.name!r} is already used at {seen[item.name]}",
                    )
                )
            else:
                seen[item.name] = where
    for path, entry in _walk(faces, "interfaces"):
        if _field_name(path) in ("axis", "normal") and isinstance(entry.value, Vector):
            length = math.sqrt(sum(v * v for v in entry.value.values))
            if abs(length - 1.0) > UNIT_VECTOR_TOLERANCE:
                out.append(
                    Refusal(
                        rule="consistency.unit_vector",
                        entry=path,
                        reason=f"an axis or normal must have length 1, not {length:.6f}",
                    )
                )
    seats = {s.name: s for s in faces.seats}
    if spec.physics is not None:
        for c, case in enumerate(spec.physics.load_cases):
            for s, load in enumerate(case.seat_loads):
                if load.seat not in seats:
                    out.append(
                        Refusal(
                            rule="consistency.seat_reference",
                            entry=f"physics.load_cases[{c}].seat_loads[{s}].seat",
                            reason=f"no seat is named {load.seat!r}",
                        )
                    )
    for b, bearing in enumerate(spec.requirement.bearings):
        seat = seats.get(bearing.seat)
        if seat is None:
            out.append(
                Refusal(
                    rule="consistency.seat_reference",
                    entry=f"requirement.bearings[{b}].seat",
                    reason=f"no seat is named {bearing.seat!r}",
                )
            )
            continue
        od, bore = _scalar(bearing.outer_diameter), _scalar(seat.diameter)
        if od is not None and bore is not None and abs(od - bore) > 1e-3:
            out.append(
                Refusal(
                    rule="consistency.bearing_seat",
                    entry=f"requirement.bearings[{b}].outer_diameter",
                    reason=f"the bearing's outer diameter {od:.3f} mm does not fit its seat's "
                    f"{bore:.3f} mm",
                )
            )
    space = spec.requirement.installation_space
    corners_are_vectors = (
        space.box_min is not None
        and space.box_max is not None
        and isinstance(space.box_min.value, Vector)
        and isinstance(space.box_max.value, Vector)
    )
    if space.kind == "box" and corners_are_vectors:
        low, _ = space.box_min.value.to_canonical()
        high, _ = space.box_max.value.to_canonical()
        for i, seat in enumerate(faces.seats):
            if not isinstance(seat.centre.value, Vector):
                continue
            centre, _ = seat.centre.value.to_canonical()
            if not all(lo <= c <= hi for lo, c, hi in zip(low, centre, high, strict=True)):
                out.append(
                    Refusal(
                        rule="consistency.seat_inside_space",
                        entry=f"interfaces.seats[{i}].centre",
                        reason=f"the seat's centre {centre} lies outside the installation space "
                        f"{low} to {high}",
                    )
                )
    return out


def _check_tilt_limits(spec: HousingDesignSpec) -> list[Refusal]:
    """The judge needs a tilt limit for every seat, so for every bearing type in the contract."""
    limited = {t.bearing_type for t in spec.limits.bearing_tilt}
    return [
        Refusal(
            rule="consistency.tilt_limit",
            entry=f"requirement.bearings[{b}].type",
            reason=f"no tilt limit is given for {bearing.type} bearings",
        )
        for b, bearing in enumerate(spec.requirement.bearings)
        if bearing.type not in limited
    ]


def validate(spec: HousingDesignSpec) -> list[Refusal]:
    """Every rule's refusals; an empty list means the contract is accepted."""
    refusals: list[Refusal] = []
    refusals += _check_dimensions(spec)
    refusals += _check_assumptions(spec)
    refusals += _check_stage(spec)
    refusals += _check_gear_train(spec)
    refusals += _check_power(spec)
    refusals += _check_interfaces(spec)
    refusals += _check_tilt_limits(spec)
    return refusals


def load_and_validate(
    source: str | Path | dict[str, Any],
) -> tuple[HousingDesignSpec | None, list[Refusal]]:
    """Load a contract (a JSON file, a JSON string or a dict) and validate it."""
    try:
        if isinstance(source, dict):
            spec = HousingDesignSpec.model_validate(source)
        else:
            text = Path(source).read_text(encoding="utf-8") if _is_path(source) else source
            spec = HousingDesignSpec.model_validate_json(text)
    except ValidationError as error:
        return None, [
            Refusal(
                rule="schema",
                entry=".".join(str(part) for part in e["loc"]),
                reason=e["msg"],
            )
            for e in error.errors()
        ]
    return spec, validate(spec)


def _is_path(source: str | Path) -> bool:
    if isinstance(source, Path):
        return True
    return not source.lstrip().startswith("{")
