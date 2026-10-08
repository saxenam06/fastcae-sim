"""The contract page: what the user gives, what the tools calculate and by which method, the pass
criteria, and the published design to beat. Each item is a few words long, and its source is a
short label.

The page is a product's form, not a document. It shows a value, its unit, and where the value came
from in two words. The full citation stays in the contract and goes on hover. A calculation whose
tool is not built yet still shows the method it will use, pre-selected, and says it is planned, so
the whole method is visible from the start. Results come only from zenryx's own functions, never
typed in.
"""

from __future__ import annotations

import re
from typing import Any

from zenryx.contract.entry import Entry, Provenance
from zenryx.contract.involute import working_centre_distance
from zenryx.contract.model import GearStage, HousingDesignSpec
from zenryx.contract.train import mesh_frequency, ratio, shaft_speeds, stage_angle
from zenryx.contract.units import Quantity, Vector
from zenryx.contract.validate import CENTRE_DISTANCE_TOLERANCE_MM

# Short names for the sources the contracts cite, by how their citation starts.
SHORT: tuple[tuple[str, str], ...] = (
    ("Ivanov 2018", "Ivanov 2018"),
    ("Hofstetter", "Hofstetter 2018"),
    ("Kim et al. 2024", "Kim 2024"),
    ("Son et al. 2020", "Son 2020"),
    ("NADCA", "NADCA"),
    ("Shigley", "Shigley"),
    ("Marano", "Marano 2021"),
    ("Gutierrez Santiago", "Gutierrez Santiago 2023"),
    ("ISO 15", "ISO 15"),
    ("fastcae research", "worked example"),
    ("chosen for the example", "example"),
)

PROCESS = {
    "high_pressure_die_casting": "High-pressure die casting",
    "sand_casting": "Sand casting",
    "laser_powder_bed_fusion": "Metal printing (LPBF)",
}

BEARING = {
    "deep_groove_ball": "deep-groove ball",
    "cylindrical_roller": "cylindrical roller",
    "tapered_roller": "tapered roller",
    "spherical_roller": "spherical roller",
    "angular_contact_ball": "angular-contact ball",
    "needle_roller": "needle roller",
}


# A bearing type in one word, for the tilt line.
TILT_WORD = {
    "tapered_roller": "tapered",
    "cylindrical_roller": "cylindrical",
    "deep_groove_ball": "ball",
    "spherical_roller": "spherical",
    "angular_contact_ball": "angular-contact",
    "needle_roller": "needle",
}


def _num(x: float, digits: int = 4) -> str:
    """A number for the page: up to `digits` significant figures, thousands grouped."""
    text = f"{x:,.{max(digits - len(str(int(abs(x)))), 0)}f}" if abs(x) >= 1 else f"{x:.{digits}g}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _unit(unit: str) -> str:
    """A unit as the page writes it after a number: degrees as °, a pure number as nothing."""
    return {"1": "", "deg": "°"}.get(unit, f" {unit}")


def _number(value: Quantity) -> str:
    # Small pure numbers (profile shifts, ratios) to five figures; the rest to six.
    return _num(value.value, 5 if abs(value.value) < 1 else 6)


def _text(value: Any) -> str:
    if isinstance(value, Quantity):
        return f"{_number(value)}{_unit(value.unit)}"
    if isinstance(value, Vector):
        inner = ", ".join(_num(v, 4) for v in value.values)
        return f"({inner}){_unit(value.unit)}"
    return "-" if value is None else str(value)


def source(prov: Provenance, spec: HousingDesignSpec) -> dict[str, str]:
    """Where a value came from: a short label, its kind, and the full text for the hover."""
    if prov.kind in ("published", "standard", "measured"):
        cite = prov.citation or ""
        label = next((short for start, short in SHORT if cite.startswith(start)), "")
        if not label:
            match = re.match(r"([A-Z][\w'-]+)(?: et al\.)?.*?(\d{4})", cite)
            label = f"{match.group(1)} {match.group(2)}" if match else cite[:24]
        title = cite + (f" ({prov.note})" if prov.note else "")
    elif prov.kind == "assumption":
        found = next((a for a in spec.assumptions if a.id == prov.assumption_id), None)
        label = "assumed"
        title = (
            f"{found.id}: {found.what}, {found.value}. {found.why}" if found else "an assumption"
        )
    elif prov.kind == "engineer":
        label = "you"
        title = f"{prov.who}, {prov.when}" + (f": {prov.note}" if prov.note else "")
    else:
        label = "calculated"
        title = f"{prov.tool} {prov.tool_version}"
    return {"source": label, "kind": prov.kind, "title": title}


def _row(label: str, entry: Entry | None, spec: HousingDesignSpec, path: str) -> dict[str, Any]:
    if entry is None:
        return {"label": label, "value": "-", "source": "", "kind": "", "title": "", "path": path}
    return {
        "label": label,
        "value": _text(entry.value),
        "path": path,
        **source(entry.provenance, spec),
    }


def _pair(a: Entry | None, b: Entry | None, spec: HousingDesignSpec) -> dict[str, str]:
    """A pinion's value and its gear's, in one cell."""
    if a is None and b is None:
        return {"value": "-", "source": "", "kind": "", "title": ""}
    present = [e for e in (a, b) if e is not None]
    units = {e.value.unit for e in present if isinstance(e.value, Quantity)}
    if len(present) == 2 and len(units) == 1:
        # Both in the same unit: the numbers, then the unit once (16.5 / 15.5 mm).
        unit = _unit(units.pop())
        value = " / ".join(_number(e.value) for e in present) + unit
    else:
        value = " / ".join(_text(e.value) for e in present)
    first = source(present[0].provenance, spec)
    return {**first, "value": value}


def _gear_table(spec: HousingDesignSpec) -> dict[str, Any] | None:
    stages = spec.requirement.stages
    if not stages:
        return None

    def cell(stage: GearStage, field: str) -> dict[str, str]:
        if field == "teeth":
            return _pair(stage.z_pinion, stage.z_gear, spec)
        if field == "shift":
            return _pair(stage.profile_shift_pinion, stage.profile_shift_gear, spec)
        if field == "width":
            return _pair(stage.face_width_pinion, stage.face_width_gear, spec)
        if field == "helix":
            got = _pair(stage.helix_angle, None, spec)
            if stage.helix_hand_pinion is not None and got["value"] != "-":
                got["value"] += f" (pinion {stage.helix_hand_pinion.value})"
            return got
        return _pair(getattr(stage, field), None, spec)

    rows = [
        ("Teeth (pinion / gear)", "teeth"),
        ("Normal module", "normal_module"),
        ("Pressure angle", "pressure_angle"),
        ("Helix angle", "helix"),
        ("Profile shift (pinion / gear)", "shift"),
        ("Face width (pinion / gear)", "width"),
        ("Centre distance", "centre_distance"),
    ]
    return {
        "columns": [f"Stage {i + 1}" for i in range(len(stages))],
        "rows": [
            {"label": label, "cells": [cell(s, field) for s in stages]} for label, field in rows
        ],
    }


def _assumption(spec: HousingDesignSpec, what: str):
    return next((a for a in spec.assumptions if a.what.startswith(what)), None)


def inputs(spec: HousingDesignSpec) -> list[dict[str, Any]]:
    """What the user gives, grouped: the duty, the gear train, the packaging, the bearings, the
    process and material."""
    req, mfg = spec.requirement, spec.manufacturing
    duty = []
    for i, t in enumerate(req.torques):
        shaft = "" if t.shaft == "input" else f" ({t.shaft})"
        duty.append(
            _row(
                f"{t.kind.capitalize()} {t.direction} torque{shaft}",
                t.torque,
                spec,
                f"requirement.torques[{i}].torque",
            )
        )
    for i, s in enumerate(req.speeds):
        duty.append(
            _row(
                f"{s.kind.capitalize()} {s.shaft} speed",
                s.speed,
                spec,
                f"requirement.speeds[{i}].speed",
            )
        )
    for i, p in enumerate(req.powers):
        duty.append(
            _row(f"{p.kind.capitalize()} power", p.power, spec, f"requirement.powers[{i}].power")
        )
    if req.service_life is not None:
        duty.append(_row("Service life", req.service_life, spec, "requirement.service_life"))

    train = [_row("Ratio", req.total_ratio, spec, "requirement.total_ratio")]
    if req.ratio_tolerance is not None:
        train[0]["value"] += f" ± {_text(req.ratio_tolerance.value)}"
    train.append(_row("Gear material", req.gear_material, spec, "requirement.gear_material"))
    train.append(_row("Gear quality", req.gear_quality, spec, "requirement.gear_quality"))

    space = req.installation_space
    packaging = []
    if req.input_output_offset is not None:
        packaging.append(
            _row(
                "Input-output offset",
                req.input_output_offset,
                spec,
                "requirement.input_output_offset",
            )
        )
        # The angle the offset gives, beside it: the same input seen as the shafts' angle.
        distances = [_scalar(s.centre_distance) for s in req.stages]
        offset = _scalar(req.input_output_offset)
        if len(distances) == 2 and None not in distances and offset is not None:
            angle = stage_angle(distances[0], distances[1], offset)
            packaging.append(
                {
                    "label": "Shaft angle",
                    "value": f"{_num(angle, 4)}°",
                    "source": "calculated",
                    "kind": "derived",
                    "title": "at the intermediate shaft, from the offset and the two centre "
                    "distances (zenryx.contract.train.stage_angle)",
                    "path": "",
                }
            )
    if space.kind == "layout_envelope":
        packaging.append(
            _row(
                "Clearance round the gears",
                space.clearance,
                spec,
                "requirement.installation_space.clearance",
            )
        )
    else:
        packaging.append(
            _row(
                "Space, lower corner", space.box_min, spec, "requirement.installation_space.box_min"
            )
        )
        packaging.append(
            _row(
                "Space, upper corner", space.box_max, spec, "requirement.installation_space.box_max"
            )
        )

    bearings = [
        {
            **_row(b.seat, b.designation, spec, f"requirement.bearings[{i}].designation"),
            "value": f"{b.designation.value} · {BEARING.get(b.type, b.type)}",
        }
        for i, b in enumerate(req.bearings)
    ]
    if not bearings:
        chosen = _assumption(spec, "the bearings")
        if chosen is not None:
            bearings.append(
                {
                    "label": "Arrangement",
                    "value": chosen.value,
                    "source": "assumed",
                    "kind": "assumption",
                    "title": f"{chosen.id}: {chosen.value}. {chosen.why}",
                    "path": "",
                }
            )
        bearings.append(
            {
                "label": "Sizes",
                "value": "from the loads, by L10 life",
                "source": "calculated",
                "kind": "derived",
                "title": "the load tool (GBX-1), planned",
                "path": "",
            }
        )

    card = mfg.material
    proposed = _assumption(spec, "the process")
    process = [
        {
            "label": "Process",
            "value": PROCESS.get(mfg.process, mfg.process),
            "source": "assumed" if proposed else "you",
            "kind": "assumption" if proposed else "engineer",
            "title": f"{proposed.id}: {proposed.value}. {proposed.why}" if proposed else "",
            "path": "manufacturing.process",
            "options": list(PROCESS.values()),
        }
    ]
    process.append(
        {
            **_row("Material", card.youngs_modulus, spec, "manufacturing.material"),
            "value": card.name.split(" (")[0],
        }
    )
    properties = (
        f"E {_text(card.youngs_modulus.value)} · ν {_text(card.poisson_ratio.value)}"
        f" · {_text(card.density.value)}"
    )
    process.append(
        {
            **_row("Properties", card.youngs_modulus, spec, "manufacturing.material"),
            "value": properties,
        }
    )
    process.append(_row("Least wall", mfg.min_wall, spec, "manufacturing.min_wall"))
    if mfg.draft_inside is not None and mfg.draft_outside is not None:
        draft = _row(
            "Draft (inside / outside)", mfg.draft_inside, spec, "manufacturing.draft_inside"
        )
        draft["value"] = f"{_text(mfg.draft_inside.value)} / {_text(mfg.draft_outside.value)}"
        process.append(draft)
    process.append(
        _row("Machining stock", mfg.machining_stock, spec, "manufacturing.machining_stock")
    )
    if mfg.pull_directions:
        pull = _row(
            "Pull directions",
            mfg.pull_directions[0].direction,
            spec,
            "manufacturing.pull_directions[0].direction",
        )
        # The note's first words only ("along the shafts"); the rest waits on hover.
        note = (mfg.pull_directions[0].direction.provenance.note or "as given").split(" (")[0]
        pull["value"] = f"{len(mfg.pull_directions)} parts, {note}"
        process.append(pull)

    groups = [
        {"group": "Duty", "rows": duty},
        {"group": "Gear train", "rows": train, "table": _gear_table(spec)},
        {"group": "Packaging", "rows": packaging},
        {"group": "Bearings", "rows": bearings},
        {"group": "Process and material", "rows": process},
    ]
    return [g for g in groups if g["rows"] or g.get("table")]


def _scalar(entry: Entry | None) -> float | None:
    if entry is None or not isinstance(entry.value, Quantity | int):
        return None
    if isinstance(entry.value, int):
        return float(entry.value)
    return entry.value.to_canonical()[0]


def calculations(spec: HousingDesignSpec) -> list[dict[str, Any]]:
    """What the tools calculate from the inputs, each with its method pre-selected. Computed where
    zenryx has the function today; planned, with the tool that will make it, where it has not."""
    req = spec.requirement
    stages = req.stages
    teeth = [
        (int(s.z_pinion.value), int(s.z_gear.value))
        for s in stages
        if s.z_pinion is not None and s.z_gear is not None
    ]
    out: list[dict[str, Any]] = []

    def calc(quantity, method, by, function, result=None, planned=None):
        out.append(
            {
                "quantity": quantity,
                "method": method,
                "by": by,
                "function": function,
                "status": "computed" if result is not None else "planned",
                "result": result if result is not None else (planned or "planned"),
            }
        )

    checks = []
    for i, s in enumerate(stages):
        values = [
            _scalar(getattr(s, f))
            for f in ("z_pinion", "z_gear", "normal_module", "pressure_angle", "helix_angle")
        ]
        given = _scalar(s.centre_distance)
        if None in values or given is None:
            continue
        x1 = _scalar(s.profile_shift_pinion) or 0.0
        x2 = _scalar(s.profile_shift_gear) or 0.0
        z1, z2, mn, alpha, beta = values
        a = working_centre_distance(int(z1), int(z2), mn, alpha, beta, x1, x2)
        ok = "✓" if abs(a - given) <= CENTRE_DISTANCE_TOLERANCE_MM else "✗"
        checks.append(f"stage {i + 1}: {_num(a, 5)} mm (given {_num(given, 5)}) {ok}")
    if checks:
        calc(
            "Gear mesh check",
            "Involute geometry",
            "DIN 3960 · ISO 21771",
            "zenryx.contract.involute.working_centre_distance",
            " · ".join(checks),
        )

    if teeth and len(teeth) == len(stages):
        r = ratio(teeth)
        target = _scalar(req.total_ratio)
        tolerance = _scalar(req.ratio_tolerance) or 0.0
        ok = "" if target is None else (" ✓" if abs(r - target) <= tolerance * target else " ✗")
        given = f" (given {_num(target, 5)})" if target else ""
        calc(
            "Total ratio",
            "Product of the stages' tooth ratios",
            "",
            "zenryx.contract.train.ratio",
            f"{_num(r, 5)}{given}{ok}",
        )

    offset = _scalar(req.input_output_offset)
    distances = [_scalar(s.centre_distance) for s in stages]
    if offset is not None and len(distances) == 2 and None not in distances:
        angle = stage_angle(distances[0], distances[1], offset)
        calc(
            "Shaft angle",
            "Triangle of the three axes",
            "law of cosines",
            "zenryx.contract.train.stage_angle",
            f"{_num(angle, 4)}° at the intermediate shaft",
        )

    rated = next((s for s in req.speeds if s.kind == "rated"), None)
    if rated is not None and teeth:
        rpm = _scalar(rated.speed) * 60 / (2 * 3.141592653589793)  # rad/s back to rev/min
        speeds = shaft_speeds(rpm, teeth)
        names = ["input"] + [s.gear_shaft for s in stages]
        calc(
            "Shaft speeds",
            "Through the tooth ratios",
            "",
            "zenryx.contract.train.shaft_speeds",
            " · ".join(f"{n} {_num(v, 4)}" for n, v in zip(names, speeds, strict=True)) + " rpm",
        )
        freqs = [mesh_frequency(z_p, speeds[i]) for i, (z_p, _) in enumerate(teeth)]
        calc(
            "Mesh frequencies",
            "Teeth × shaft speed",
            "Shigley",
            "zenryx.contract.train.mesh_frequency",
            " · ".join(f"stage {i + 1} {_num(f, 4)} Hz" for i, f in enumerate(freqs))
            + f" at {_num(rpm, 4)} rpm",
        )

    planned = "the load tool (GBX-1)"
    calc(
        "Gear forces",
        "Helical gear forces",
        "Shigley · ISO 6336",
        planned,
        planned="planned · GBX-1",
    )
    calc(
        "Shaft spacing",
        "Face widths, bearing widths and gaps",
        "Maciejczyk & Zdziennicki · Shigley",
        planned,
        planned="planned · GBX-1",
    )
    calc(
        "Bearing loads",
        "Two-support statics with the axial force's moment",
        "JTEKT",
        planned,
        planned="planned · GBX-1",
    )
    calc(
        "Bearing sizes",
        "Rating life L10",
        "ISO 281 · Maciejczyk & Zdziennicki",
        planned,
        planned="planned · GBX-1",
    )
    calc(
        "Alignment limit",
        "Gear tolerance × the housing's share",
        "JGMA 1102-01",
        "the judge (PHY)",
        planned="planned · the judge",
    )
    return out


def criteria(spec: HousingDesignSpec) -> list[dict[str, str]]:
    """What a design must meet: the verdict, each line with its standard."""
    lim = spec.limits
    tilt = " · ".join(
        f"{TILT_WORD.get(t.bearing_type, t.bearing_type)} {_text(t.limit.value)}"
        for t in lim.bearing_tilt
    )
    speeds = " and ".join(_text(s.value) for s in lim.order_check_speeds)
    share = source(lim.mesh_misalignment_share.provenance, spec)
    return [
        {
            "label": "The housing's share of the gear tolerances",
            "value": f"{_text(lim.mesh_misalignment_share.value)} of alignment, centre distance, "
            "ovalisation",
            **share,
        },
        {
            "label": "Bearing tilt",
            "value": tilt,
            **source(lim.bearing_tilt[0].limit.provenance, spec),
        },
        {
            "label": "Order separation",
            "value": f"at least {_text(lim.order_separation.value)} at {speeds}",
            **source(lim.order_separation.provenance, spec),
        },
        {
            "label": "Model margin",
            "value": _text(lim.model_margin.value),
            **source(lim.model_margin.provenance, spec),
        },
        {
            "label": "Objective",
            "value": "least mass among passing designs",
            "source": "",
            "kind": "",
            "title": "",
        },
        {"label": "Stress", "value": "recorded, not judged", "source": "", "kind": "", "title": ""},
    ]


def to_beat(spec: HousingDesignSpec) -> list[dict[str, str]]:
    """The published design, as a plausibility band. A published mode that sits within the order
    separation of a mesh frequency at a check speed is pointed out: that design would fail."""
    req = spec.requirement
    teeth = [
        (int(s.z_pinion.value), int(s.z_gear.value))
        for s in req.stages
        if s.z_pinion is not None and s.z_gear is not None
    ]
    separation = _scalar(spec.limits.order_separation) or 0.03
    meshes = []
    if teeth and len(teeth) == len(req.stages):
        for check in spec.limits.order_check_speeds:
            rpm = _scalar(check) * 60 / (2 * 3.141592653589793)
            speeds = shaft_speeds(rpm, teeth)
            meshes += [
                (i + 1, rpm, mesh_frequency(z_p, speeds[i])) for i, (z_p, _) in enumerate(teeth)
            ]
    out = []
    for ref in spec.references:
        note = ""
        if "mode" in ref.quantity:
            for found in re.findall(r"(\d+(?:\.\d+)?) Hz", ref.value):
                f = float(found)
                hit = next(
                    ((s, rpm, m) for s, rpm, m in meshes if abs(f - m) / m < separation), None
                )
                if hit:
                    note = (
                        f"{_num(f, 4)} Hz sits on stage {hit[0]}'s mesh frequency at "
                        f"{_num(hit[1], 4)} rpm ({_num(hit[2], 4)} Hz): it fails order separation"
                    )
                    break
        label = next(
            (short for start, short in SHORT if ref.source.startswith(start)), ref.source[:24]
        )
        out.append(
            {
                "quantity": ref.quantity,
                "value": ref.value,
                "source": label,
                "title": f"{ref.source}. {ref.conditions} ({ref.confidence})",
                "note": note,
            }
        )
    return out


def build(spec: HousingDesignSpec) -> dict[str, Any]:
    return {
        "inputs": inputs(spec),
        "calculations": calculations(spec),
        "criteria": criteria(spec),
        "to_beat": to_beat(spec),
    }
