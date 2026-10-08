"""The snapshot: everything the web UI shows, built from the records (PLT-4, the web UI).

The UI reads one JSON payload. It holds every contract with its entries in words, the validator's
verdict, what freezing the contract now would say, and the records the agent and the judge will
make - empty lists until they exist, their shapes provisional until the record schema (DAT-1).

The payload is deterministic: no timestamp, contracts in id order. The committed copy is checked
for staleness the way the example contracts are.

    uv run python -m zenryx.api.snapshot            # writes web/src/records/snapshot.json
    uv run python -m zenryx.api.snapshot --check    # exits 1 when that file is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from zenryx import __version__
from zenryx.contract.canonical import freeze, spec_hash
from zenryx.contract.entry import Entry
from zenryx.contract.model import HousingDesignSpec
from zenryx.contract.units import Quantity, Vector
from zenryx.contract.validate import Refusal, load_and_validate, validate

SCHEMA = "zenryx.snapshot/0.1"

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIRS = (ROOT / "checks" / "data" / "contracts",)
OUT = ROOT / "web" / "src" / "records" / "snapshot.json"

LAYERS = ("requirement", "interfaces", "physics", "limits", "manufacturing")

# The validator's rules in a few words each, in the order it runs them (validate.py). A check
# fails when a rule is added there and not here.
RULES: tuple[tuple[str, str], ...] = (
    (
        "schema",
        "the contract loads: every field known, its type and unit, required entries present",
    ),
    ("consistency.shape", "points and directions have three components; scalars have one"),
    ("consistency.dimension", "every quantity has the dimension its field needs"),
    ("provenance.assumption_listed", "every assumption an entry points to is listed"),
    ("stage.posed", "a posed contract carries no physics cases"),
    (
        "stage.derived_needs_physics",
        "a derived or frozen contract carries its interfaces and physics",
    ),
    (
        "stage.physics_is_derived",
        "every physics value is derived by its versioned tool, never typed",
    ),
    ("stage.frozen_hash", "only a frozen contract carries a hash, and it matches the content"),
    (
        "consistency.centre_distance",
        "each stage's gears give its centre distance (profile shift in)",
    ),
    ("consistency.ratio", "the stages' ratios give the total ratio within its tolerance"),
    ("consistency.offset", "two stages' centre distances can reach the input-output offset"),
    ("consistency.power", "power equals torque times speed on the same shaft, within 2 %"),
    ("consistency.unique_names", "every interface has a name of its own"),
    ("consistency.unit_vector", "every axis and normal has length 1"),
    ("consistency.seat_reference", "every bearing and seat load names a seat that exists"),
    ("consistency.bearing_seat", "each bearing's outer diameter fits its seat"),
    ("consistency.seat_inside_space", "every seat's centre lies inside the installation space"),
    ("consistency.tilt_limit", "every bearing type in the contract has a tilt limit"),
)

# A field's name in words. Fields not listed read as their name with spaces.
WORDS: dict[str, str] = {
    "z_pinion": "pinion teeth",
    "z_gear": "gear teeth",
    "helix_hand_pinion": "pinion helix hand",
    "face_width_pinion": "pinion face width",
    "face_width_gear": "gear face width",
    "profile_shift_pinion": "pinion profile shift",
    "profile_shift_gear": "gear profile shift",
    "input_output_offset": "input-output offset",
    "box_min": "box, lower corner",
    "box_max": "box, upper corner",
    "stock": "machining stock",
    "bolt_count": "bolts",
    "order": "mesh order",
    "mesh_misalignment_share": "housing's share of the misalignment tolerance",
    "centre_distance_share": "housing's share of the centre-distance tolerance",
    "ovalisation_share": "housing's share of the ovalisation tolerance",
    "limit": "tilt limit",
    "order_check_speeds": "order-check speed",
    "direction": "pull direction",
    "draft_inside": "draft, inside surfaces",
    "draft_outside": "draft, outside surfaces",
    "draft_min_depth": "draft applies from depth",
    "min_wall": "least wall",
    "max_wall": "greatest wall",
    "youngs_modulus": "Young's modulus",
    "poisson_ratio": "Poisson's ratio",
    "expansion": "thermal expansion",
}

# Where an entry sits on the sheet: its layer's field, grouped where several belong together.
GROUPS: dict[str, str] = {
    "requirement.torques": "torques",
    "requirement.speeds": "speeds",
    "requirement.powers": "power",
    "requirement.total_ratio": "ratio",
    "requirement.ratio_tolerance": "ratio",
    "requirement.input_output_offset": "layout",
    "requirement.service_life": "duty",
    "requirement.gear_material": "gears",
    "requirement.gear_quality": "gears",
    "requirement.stages": "gear stages",
    "requirement.bearings": "bearings",
    "requirement.installation_space": "installation space",
    "interfaces.seats": "bearing seats",
    "interfaces.split_faces": "split faces",
    "interfaces.mount_pads": "mount pads",
    "interfaces.motor_flanges": "motor flanges",
    "interfaces.ports": "ports",
    "physics.load_cases": "load cases",
    "physics.mesh_orders": "mesh orders",
    "limits.mesh_misalignment_share": "the housing's shares",
    "limits.centre_distance_share": "the housing's shares",
    "limits.ovalisation_share": "the housing's shares",
    "limits.bearing_tilt": "bearing tilt",
    "limits.order_separation": "gear orders",
    "limits.order_check_speeds": "gear orders",
    "limits.model_margin": "margin",
    "manufacturing.pull_directions": "pull directions",
    "manufacturing.draft_inside": "draft",
    "manufacturing.draft_outside": "draft",
    "manufacturing.draft_min_depth": "draft",
    "manufacturing.min_wall": "walls and stock",
    "manufacturing.max_wall": "walls and stock",
    "manufacturing.machining_stock": "walls and stock",
    "manufacturing.material": "material",
}


def _words(field: str) -> str:
    return WORDS.get(field, field.replace("_", " "))


def _num(x: float) -> str:
    """A number as an engineer writes it: six significant digits, no trailing zeros, and no
    exponent between 1e-4 and 1e9 (944 h is 3398400 s, not 3.3984e+06 s)."""
    if x == 0:
        return "0"
    if 1e-4 <= abs(x) < 1e9:
        decimals = max(5 - math.floor(math.log10(abs(x))), 0)
        text = f"{x:.{decimals}f}"
        return text.rstrip("0").rstrip(".") if "." in text else text
    return f"{x:.6g}"


def _with_unit(number: str, unit: str) -> str:
    """A pure number (unit "1") is written without its unit."""
    return number if unit == "1" else f"{number} {unit}"


def _value_text(value: Any) -> str:
    if isinstance(value, Quantity):
        return _with_unit(_num(value.value), value.unit)
    if isinstance(value, Vector):
        return _with_unit(f"({', '.join(_num(v) for v in value.values)})", value.unit)
    return "-" if value is None else str(value)


def _canonical_text(value: Any) -> str | None:
    if isinstance(value, Quantity):
        number, unit = value.to_canonical()
        return _with_unit(_num(number), unit)
    if isinstance(value, Vector):
        numbers, unit = value.to_canonical()
        return _with_unit(f"({', '.join(_num(v) for v in numbers)})", unit)
    return None


def _tag(item: BaseModel) -> str:
    """What names one item of a list: a torque by its kind and direction, a bearing by its seat."""
    get = item.__dict__.get
    if get("direction") is not None and get("shaft") is not None:  # a torque
        return f"{get('kind')} {get('direction')}, {get('shaft')} shaft"
    if get("designation") is not None and get("seat") is not None:  # a bearing
        return f"{get('designation').value} at {get('seat')}"
    if get("bearing_type") is not None:
        return str(get("bearing_type")).replace("_", " ")
    if get("seat") is not None:  # a seat load
        return f"at {get('seat')}"
    if get("stage") is not None and get("shaft") is not None:  # a mesh order
        return f"{get('stage')}, {get('shaft')} shaft"
    if get("kind") is not None and get("shaft") is not None:  # a speed or a power
        return f"{get('kind')}, {get('shaft')} shaft"
    for name in ("name", "part"):
        if get(name) is not None:
            return str(get(name))
    return ""


def _walk(
    obj: Any, path: str, tags: tuple[str, ...]
) -> Iterator[tuple[str, Entry, tuple[str, ...]]]:
    """Every entry under obj with its dotted path, and the tags of the list items above it."""
    if isinstance(obj, Entry):
        yield path, obj, tags
    elif isinstance(obj, BaseModel):
        for name in type(obj).model_fields:
            yield from _walk(getattr(obj, name), f"{path}.{name}" if path else name, tags)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            named = isinstance(item, BaseModel) and not isinstance(item, Entry)
            tag = _tag(item) if named else str(i + 1)
            yield from _walk(item, f"{path}[{i}]", (*tags, tag) if tag else tags)


def _entry(path: str, entry: Entry, tags: tuple[str, ...]) -> dict[str, Any]:
    layer, _, rest = path.partition(".")
    first = rest.split(".")[0].split("[")[0]
    field = path.rsplit(".", 1)[-1].split("[")[0]
    label = _words(field)
    if tags:
        label = f"{label} · {' · '.join(tags)}"
    provenance = entry.provenance.model_dump(exclude_none=True)
    return {
        "path": path,
        "layer": layer,
        "group": GROUPS.get(f"{layer}.{first}", _words(first)),
        "label": label,
        "value": _value_text(entry.value),
        "canonical": _canonical_text(entry.value),
        "provenance": provenance,
        "authority": entry.authority,
        "kind": entry.kind,
        "bounds": [_value_text(b) for b in entry.bounds] if entry.bounds else None,
    }


def _refusals(refusals: Sequence[Refusal]) -> list[dict[str, str]]:
    return [r.model_dump() for r in refusals]


def _items(spec: HousingDesignSpec) -> list[dict[str, str]]:
    """The named things a design must keep or carry, for the contract's Binding page."""
    req = spec.requirement
    out = [
        {"kind": "torque", "name": _tag(t), "path": f"requirement.torques[{i}]", "detail": ""}
        for i, t in enumerate(req.torques)
    ]
    out += [
        {
            "kind": "gear stage",
            "name": s.name,
            "path": f"requirement.stages[{i}]",
            "detail": f"{s.pinion_shaft} → {s.gear_shaft}",
        }
        for i, s in enumerate(req.stages)
    ]
    out += [
        {
            "kind": "bearing",
            "name": b.designation.value if isinstance(b.designation.value, str) else str(i),
            "path": f"requirement.bearings[{i}]",
            "detail": f"{b.type.replace('_', ' ')} at {b.seat}",
        }
        for i, b in enumerate(req.bearings)
    ]
    if spec.interfaces is not None:
        faces = spec.interfaces
        groups = (
            ("bearing seat", "seats", lambda x: f"{x.shaft} shaft, shoulder {x.shoulder}"),
            ("split face", "split_faces", lambda x: ""),
            ("mount pad", "mount_pads", lambda x: f"{x.support} support"),
            ("motor flange", "motor_flanges", lambda x: ""),
            ("port", "ports", lambda x: x.role),
        )
        for kind, field, detail in groups:
            out += [
                {
                    "kind": kind,
                    "name": x.name,
                    "path": f"interfaces.{field}[{i}]",
                    "detail": detail(x),
                }
                for i, x in enumerate(getattr(faces, field))
            ]
    if spec.physics is not None:
        out += [
            {
                "kind": "load case",
                "name": case.name,
                "path": f"physics.load_cases[{i}]",
                "detail": ", ".join(load.seat for load in case.seat_loads),
            }
            for i, case in enumerate(spec.physics.load_cases)
        ]
    return out


def _scenarios(spec: HousingDesignSpec) -> list[dict[str, str]]:
    """The tests a design of this contract will be judged under: the evaluation axis it implies."""
    out = [
        {
            "kind": "static",
            "name": f"{t.direction} at {t.kind} torque",
            "from": f"requirement.torques[{i}]",
        }
        for i, t in enumerate(spec.requirement.torques)
    ]
    out += [
        {
            "kind": "orders",
            "name": f"gear orders at {_value_text(speed.value)}",
            "from": f"limits.order_check_speeds[{i}]",
        }
        for i, speed in enumerate(spec.limits.order_check_speeds)
    ]
    mounts = spec.interfaces.mount_pads if spec.interfaces is not None else []
    out.append({"kind": "modal", "name": "free-free modes", "from": "limits.order_separation"})
    out.append(
        {
            "kind": "modal",
            "name": "mounted modes" if mounts else "mounted modes, once the mounts are placed",
            "from": "interfaces.mount_pads" if mounts else "limits.order_separation",
        }
    )
    return out


def _contract(file: Path, root: Path) -> dict[str, Any]:
    raw = json.loads(file.read_text(encoding="utf-8"))
    spec, refusals = load_and_validate(file)
    rel = file.resolve().relative_to(root).as_posix()
    if spec is None:
        return {
            "id": file.stem,
            "file": rel,
            "loaded": False,
            "refusals": _refusals(refusals),
            "json": json.dumps(raw, indent=2, ensure_ascii=False),
        }
    try:
        freeze_refusals = validate(freeze(spec))
    except Exception as error:  # a contract that cannot even be copied frozen says why
        freeze_refusals = [Refusal(rule="stage.frozen_hash", entry="", reason=str(error))]
    task = spec.task
    return {
        "id": task.id,
        "file": rel,
        "loaded": True,
        "title": task.title,
        "family": task.family,
        "level": task.level,
        "priorities": list(task.priorities),
        "budget_fe_proofs": task.budget_fe_proofs,
        "budget_hours": task.budget_hours,
        "stage": spec.stage,
        "style": spec.requirement.style,
        "process": spec.manufacturing.process,
        "material": spec.manufacturing.material.name,
        "space": spec.requirement.installation_space.kind,
        "verdict_rule_version": spec.limits.verdict_rule_version,
        "objective": spec.limits.objective,
        "stress": spec.limits.stress,
        "hash": spec_hash(spec),
        "frozen_hash": spec.frozen_hash,
        "refusals": _refusals(refusals),
        "freeze": {"ready": not freeze_refusals, "refusals": _refusals(freeze_refusals)},
        "entries": [_entry(p, e, t) for p, e, t in _walk(spec, "", ())],
        "items": _items(spec),
        "scenarios": _scenarios(spec),
        "assumptions": [a.model_dump() for a in spec.assumptions],
        "references": [r.model_dump() for r in spec.references],
        "json": json.dumps(raw, indent=2, ensure_ascii=False),
    }


def build(contract_dirs: Sequence[Path] = CONTRACT_DIRS, root: Path = ROOT) -> dict[str, Any]:
    """The payload, from every contract under contract_dirs."""
    files = sorted(f for d in contract_dirs for f in Path(d).glob("*.json"))
    contracts = sorted((_contract(f, root.resolve()) for f in files), key=lambda c: c["id"])
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "zenryx": __version__,
        "contract_schema": HousingDesignSpec.model_fields["schema_version"].annotation.__args__[0],
        "rules": [{"id": rule, "words": words} for rule, words in RULES],
        "contracts": contracts,
        # What the agent, the judge and the engineer will make. Empty until they exist.
        "records": {
            "campaigns": [],
            "episodes": [],
            "candidates": [],
            "evaluations": [],
            "decisions": [],
            "choices": [],
            "pairs": [],
            "snapshot_tasks": [],
            "preference_pairs": [],
        },
    }
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload["hash"] = "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()
    return payload


def text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true", help="exit 1 if the file is stale")
    args = parser.parse_args(argv)
    fresh = text(build())
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        if current != fresh:
            print(f"{args.out} is stale: run uv run python -m zenryx.api.snapshot", file=sys.stderr)
            return 1
        print(f"{args.out} is current")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(fresh, encoding="utf-8", newline="\n")
    print(f"wrote {args.out} ({len(fresh):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
