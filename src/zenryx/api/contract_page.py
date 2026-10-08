"""The contract page: what the user gives, what the tools calculate and by which method, the pass
criteria, and the published design to beat. Each item is a few words long, and its source is a
short label.

The page is a product's form, not a document. It shows a value, its unit, and where the value came
from in two words. The full citation stays in the contract and goes on hover. The inputs hold only
what is given or assumed. The calculations are the calculation chain's steps
(docs/features/product/2026-10-08-the-calculation-chain.md), each with what it takes in and what
it gives out. A step whose tool is not built yet still shows the method it will use, pre-selected,
and the PBI that builds it, so the whole method is visible from the start. Results come only from
zenryx's own functions, never typed in.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from zenryx.contract.entry import Entry, Provenance
from zenryx.contract.involute import MeshGeometry, mesh_geometry
from zenryx.contract.model import GearStage, HousingDesignSpec
from zenryx.contract.train import mesh_frequency, ratio, shaft_speeds, stage_angle
from zenryx.contract.units import Quantity, Vector

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


# The gear data that fix a stage's centre distance by involute geometry.
GEAR_DATA = (
    "z_pinion",
    "z_gear",
    "normal_module",
    "pressure_angle",
    "helix_angle",
    "profile_shift_pinion",
    "profile_shift_gear",
)

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


def _locator(citation: str) -> str:
    """Where in its source a value stands, from the citation's last part: "Fig. 24", "Table 2"."""
    found = re.search(r",\s*((?:Fig|Table|Appendix|Section|§|p|pp|Eq)\.?\s*[\w.–-]+)\s*$", citation)
    return found.group(1) if found else ""


def _prov_key(prov: Provenance) -> tuple[str | None, ...]:
    """What makes two values come from the same place; a note on one of them does not count."""
    return (prov.kind, prov.citation, prov.assumption_id, prov.who, prov.tool)


def _gear_table(spec: HousingDesignSpec) -> dict[str, Any] | None:
    """The gear train, a column a stage. Each column names where it comes from, down to the figure
    or table; a cell carries its own source only where it differs from its column's."""
    stages = spec.requirement.stages
    if not stages:
        return None

    def entries(stage: GearStage, field: str) -> tuple[Entry | None, Entry | None]:
        pairs = {
            "teeth": (stage.z_pinion, stage.z_gear),
            "shift": (stage.profile_shift_pinion, stage.profile_shift_gear),
            "width": (stage.face_width_pinion, stage.face_width_gear),
            "helix": (stage.helix_angle, None),
        }
        return pairs[field] if field in pairs else (getattr(stage, field), None)

    def cell(stage: GearStage, field: str) -> dict[str, Any]:
        got = _pair(*entries(stage, field), spec)
        if field == "helix" and stage.helix_hand_pinion is not None and got["value"] != "-":
            got["value"] += f" (pinion {stage.helix_hand_pinion.value})"
        return got

    rows = [
        ("Teeth (pinion / gear)", "teeth"),
        ("Normal module", "normal_module"),
        ("Normal pressure angle", "pressure_angle"),
        ("Helix angle", "helix"),
        ("Profile shift (pinion / gear)", "shift"),
        ("Face width (pinion / gear)", "width"),
    ]
    # Gear data that fix the centre distance make it step 1's output; only otherwise is it an input.
    if not all(_gear_data_complete(s) for s in stages):
        rows.append(("Centre distance", "centre_distance"))
    sources: list[dict[str, str]] = []
    columns: list[list[dict[str, Any]]] = []
    for stage in stages:
        provs = [
            next((e.provenance for e in entries(stage, field) if e is not None), None)
            for _, field in rows
        ]
        # The column's own source: the one most of its cells share (the first, on a tie).
        keys = Counter(_prov_key(p) for p in provs if p is not None)
        common = keys.most_common(1)[0][0] if keys else None
        head = {"source": "", "kind": "", "title": ""}
        if common is not None:
            first = next(p for p in provs if p is not None and _prov_key(p) == common)
            head = source(first, spec)
            if first.kind in ("published", "standard", "measured") and first.citation:
                where = _locator(first.citation)
                label = f"{head['source']}, {where}" if where else head["source"]
                head = {**head, "source": label, "title": first.citation}
        sources.append(head)
        column = []
        for (_, field), prov in zip(rows, provs, strict=True):
            got = cell(stage, field)
            got["own"] = prov is not None and _prov_key(prov) != common
            column.append(got)
        columns.append(column)
    return {
        "columns": [f"Stage {i + 1}" for i in range(len(stages))],
        "sources": sources,
        "rows": [
            {"label": label, "cells": [column[r] for column in columns]}
            for r, (label, _) in enumerate(rows)
        ],
    }


def _assumption(spec: HousingDesignSpec, what: str):
    return next((a for a in spec.assumptions if a.what.startswith(what)), None)


def inputs(spec: HousingDesignSpec) -> list[dict[str, Any]]:
    """What the user gives, grouped: the duty, the gear train, the packaging, the bearings, the
    process and material. Only what is given or assumed: anything calculated from these is a
    step's output under the calculations."""
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

    # The teeth fix the ratio: then it is step 2's output, set against the contract's figure.
    train = []
    teeth = req.stages and all(s.z_pinion is not None and s.z_gear is not None for s in req.stages)
    if not teeth:
        train.append(_row("Ratio", req.total_ratio, spec, "requirement.total_ratio"))
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
    # The material's properties come with it; they are not chosen apart from it.
    process.append(
        {
            **_row("Material", card.youngs_modulus, spec, "manufacturing.material"),
            "value": card.name.split(" (")[0],
            "detail": f"E {_text(card.youngs_modulus.value)} · ν {_text(card.poisson_ratio.value)}"
            f" · {_text(card.density.value)}",
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


def _deg(angle: float) -> str:
    """An angle in radians, written in degrees to three decimals."""
    return f"{math.degrees(angle):.3f}°"


def _mm_pair(pair: tuple[float, float]) -> str:
    """A pinion's length and its gear's, to a hundredth of a millimetre."""
    return f"{pair[0]:.2f} / {pair[1]:.2f} mm"


def _given(name: str) -> dict[str, Any]:
    """What a step takes from the inputs."""
    return {"name": name, "step": None}


def _from(name: str, step: int) -> dict[str, Any]:
    """What a step takes from another step's output. In the spacing loop (steps 5, 6 and 7) that
    is a later step's, from its first guess."""
    return {"name": name, "step": step}


def _gear_data_complete(stage: GearStage) -> bool:
    """True when the stage's gear data fix its centre distance by involute geometry. Then the
    centre distance is step 1's output, not an input; the validator alone holds any figure the
    contract carries for it to its 0.1 mm."""
    return all(getattr(stage, f) is not None for f in GEAR_DATA)


def _geometry(spec: HousingDesignSpec) -> list[MeshGeometry] | None:
    """Each stage's mesh geometry; None while a stage lacks some of its gear data."""
    stages = spec.requirement.stages
    if not stages or not all(_gear_data_complete(s) for s in stages):
        return None
    out = []
    for s in stages:
        z1, z2, mn, alpha, beta, x1, x2 = (_scalar(getattr(s, f)) for f in GEAR_DATA)
        out.append(mesh_geometry(int(z1), int(z2), mn, alpha, beta, x1, x2))
    return out


def _geometry_table(geometry: list[MeshGeometry]) -> dict[str, Any]:
    """Step 1's output: a row a quantity, a column a stage."""
    rows = [
        ("Transverse pressure angle", lambda g: _deg(g.transverse_pressure_angle)),
        ("Working pressure angle", lambda g: _deg(g.working_pressure_angle)),
        ("Reference Ø (pinion / gear)", lambda g: _mm_pair(g.reference_diameters)),
        ("Base Ø (pinion / gear)", lambda g: _mm_pair(g.base_diameters)),
        ("Working pitch Ø (pinion / gear)", lambda g: _mm_pair(g.working_pitch_diameters)),
        ("Working centre distance", lambda g: f"{g.working_centre_distance:.3f} mm"),
    ]
    return {
        "columns": [f"Stage {i + 1}" for i in range(len(geometry))],
        "rows": [{"label": label, "cells": [cell(g) for g in geometry]} for label, cell in rows],
    }


def _speeds_table(spec: HousingDesignSpec) -> dict[str, Any] | None:
    """Step 2's output: the total ratio the teeth give, the shaft speeds and the mesh frequencies
    at the rated input speed."""
    req = spec.requirement
    teeth = [
        (int(s.z_pinion.value), int(s.z_gear.value))
        for s in req.stages
        if s.z_pinion is not None and s.z_gear is not None
    ]
    if not teeth or len(teeth) != len(req.stages):
        return None
    rows = [{"label": "Total ratio", "cells": [_num(ratio(teeth), 5)]}]
    rated = next((s for s in req.speeds if s.kind == "rated"), None)
    if rated is not None:
        rpm = _scalar(rated.speed) * 60 / (2 * math.pi)  # rad/s back to rev/min
        speeds = shaft_speeds(rpm, teeth)
        names = ["input"] + [s.gear_shaft for s in req.stages]
        each = " · ".join(f"{n} {_num(v, 4)}" for n, v in zip(names, speeds, strict=True))
        rows.append({"label": "Shaft speeds (rpm)", "cells": [each]})
        freqs = [mesh_frequency(z_p, speeds[i]) for i, (z_p, _) in enumerate(teeth)]
        each = " · ".join(f"stage {i + 1} {_num(f, 4)} Hz" for i, f in enumerate(freqs))
        rows.append({"label": "Mesh frequencies", "cells": [each]})
    return {"columns": [], "rows": rows}


def _shafts_table(spec: HousingDesignSpec, distances: list[float | None]) -> dict[str, Any] | None:
    """Step 3's output: the angle at the intermediate shaft that the offset and the two centre
    distances fix."""
    offset = _scalar(spec.requirement.input_output_offset)
    if offset is None or len(distances) != 2 or None in distances:
        return None
    try:
        angle = stage_angle(distances[0], distances[1], offset)
    except ValueError:  # an offset the two stages cannot reach; the validator refuses it
        return None
    cell = f"{_num(angle, 4)}° at the intermediate shaft"
    return {"columns": [], "rows": [{"label": "Shaft angle", "cells": [cell]}]}


def calculations(spec: HousingDesignSpec) -> list[dict[str, Any]]:
    """The calculation chain's steps 1-9, from the inputs to the pass lines. Each has its method
    pre-selected, what it takes in (an input, or another step's output) and what it gives out.
    Steps 1-3 are computed here by zenryx's functions; the others name the PBI that builds them."""
    out: list[dict[str, Any]] = []

    def step(number, quantity, method, by, function, takes_in, gives, table=None, plan=""):
        out.append(
            {
                "step": number,
                "quantity": quantity,
                "method": method,
                "by": by,
                "function": function,
                "status": "computed" if table is not None else "planned",
                "takes_in": takes_in,
                "gives": gives,
                "table": table,
                "plan": "" if table is not None else plan,
            }
        )

    geometry = _geometry(spec)
    step(
        1,
        "Gear geometry",
        "Involute geometry",
        "DIN 3960 · ISO 21771",
        "zenryx.contract.involute.mesh_geometry",
        [
            _given("teeth"),
            _given("normal module"),
            _given("normal pressure angle"),
            _given("helix angle"),
            _given("profile shifts"),
        ],
        "each stage's pressure angles and diameters, and the centre distance it runs at",
        _geometry_table(geometry) if geometry else None,
        plan="needs the gear data",
    )
    step(
        2,
        "Speeds and gear frequencies",
        "Through the tooth ratios",
        "Shigley",
        "zenryx.contract.train.ratio · shaft_speeds · mesh_frequency",
        [_given("teeth"), _given("rated input speed")],
        "the total ratio, each shaft's speed, each mesh's frequency",
        _speeds_table(spec),
        plan="needs the teeth",
    )
    # The shafts sit at the centre distances the gears run at (step 1); only where the gear data
    # do not fix them is a centre distance an input.
    if geometry:
        distances = [g.working_centre_distance for g in geometry]
        shafts_in = [_from("working centre distances", 1), _given("input-output offset")]
    else:
        distances = [_scalar(s.centre_distance) for s in spec.requirement.stages]
        shafts_in = [_given("centre distances"), _given("input-output offset")]
    step(
        3,
        "Where the shafts sit",
        "Triangle of the three axes",
        "law of cosines",
        "zenryx.contract.train.stage_angle",
        shafts_in,
        "the angle between the two stages, and so the three shafts' places in the plane",
        _shafts_table(spec, distances),
        plan="needs the offset",
    )
    step(
        4,
        "Gear forces",
        "Helical forces at the working pitch circle",
        "Shigley · ISO 6336",
        "the load tool (GBX-1)",
        [
            _given("peak drive, reverse and regeneration torques"),
            _given("helix angle"),
            _from("base Ø", 1),
            _from("working pressure angle", 1),
            _from("transverse pressure angle", 1),
        ],
        "the tangential, radial and axial force at each mesh, in every load case",
        plan="GBX-1",
    )
    step(
        5,
        "Spacing along each shaft",
        "Face widths, bearing widths and gaps",
        "Maciejczyk & Zdziennicki · Shigley",
        "the load tool (GBX-2)",
        [
            _given("face widths"),
            _given("gaps between gears and bearings (to be assumed)"),
            _from("bearing widths", 7),
        ],
        "where each gear and bearing sits along its shaft",
        plan="GBX-2",
    )
    step(
        6,
        "Bearing loads",
        "Two-support statics with the axial force's moment",
        "JTEKT · NSK",
        "the load tool (GBX-2)",
        [
            _from("working pitch Ø (the axial force's lever)", 1),
            _from("shaft angle (the forces' directions)", 3),
            _from("tangential, radial and axial forces", 4),
            _from("gear and bearing positions on each shaft", 5),
        ],
        "each seat's radial and axial force, in every load case",
        plan="GBX-2",
    )
    step(
        7,
        "Bearing sizes",
        "Rating life L10",
        "ISO 281 · Maciejczyk & Zdziennicki",
        "the load tool (GBX-3)",
        [
            _given("service life"),
            _given("bearing arrangement"),
            _from("shaft speeds", 2),
            _from("each seat's radial and axial force", 6),
        ],
        "each seat's bearing, and so its outside diameter and width",
        plan="GBX-3",
    )
    step(
        8,
        "Derive and freeze",
        "Every derived value stamped with its tool, version and inputs",
        "the contract's rules",
        "the load tool (GBX-4)",
        [
            _from("shaft angle", 3),
            _from("bearing positions on each shaft", 5),
            _from("each seat's radial and axial force", 6),
            _from("each seat's bearing, its outside Ø and width", 7),
        ],
        "the seats and load cases, stamped; the task frozen with its hash",
        plan="GBX-4",
    )
    step(
        9,
        "The pass lines in numbers",
        "Gear tolerance × the housing's share",
        "JGMA 1102-01 · Shigley · Marano 2021",
        "the judge (PHY)",
        [
            _given("the housing's share"),
            _given("bearing tilt limits"),
            _given("order separation"),
            _given("gear quality"),
            _given("face widths"),
            _from("reference Ø", 1),
            _from("mesh frequencies", 2),
            _from("each seat's bearing type", 7),
        ],
        "the alignment, tilt and frequency limits every design is judged by",
        plan="PHY, the judge",
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
