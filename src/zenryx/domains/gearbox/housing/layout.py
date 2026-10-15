"""The housing's layout from the contract (moved from `prototypes/first_loop/contract_layout.py`:
`record`, `fixed_kg`, `main`; LOP-33). The product's description of the set-up
(`zenryx.domains.gearbox.spaces`) written as the record the optimiser and the drawing read
(`contract.json`): the bearings, the mounts and their brackets' room, the bolts, the exits, the
split flange and its sealing land, the inside's outline, and the settings, every one the contract's.
The fixed metal's exact mass is weighed (`fixed_exact_kg`), so the optimiser's budget is the
drawing's own remainder.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import cup as cupmod
from zenryx.domains.gearbox.housing.shell import fixed_metal
from zenryx.domains.gearbox.spaces import Hypothesis, spaces

# a bolt head's socket beyond each flange face, its diameter and depth (mm): an M8 cap head (13 mm)
# and a hex key's room
BOLT_SOCKET = [16.0, 25.0]


def record(contract: Path, hypothesis: Hypothesis | None = None) -> dict:
    spec, refusals = load_and_validate(contract)
    if spec is None:
        raise ValueError(f"{contract.name} does not load: {refusals}")
    chain = complete_chain(spec)
    sp = spaces(spec, chain, hypothesis)
    req, made = spec.requirement, spec.manufacturing
    joint = made.joint
    sealed = {(e.shaft, e.side.value) for e in req.shaft_layout.sealed_ends}
    m0 = req.mounts[0] if req.mounts else None
    settings = {
        "wall": sp.wall,
        "bolt_hole": value_in(joint.hole_diameter, "mm"),
        "bolt_boss": value_in(joint.boss_diameter, "mm"),
        "bolt_socket": list(BOLT_SOCKET),
        "flange_thickness": value_in(joint.flange_thickness, "mm"),
        "land_width": value_in(joint.land_width, "mm"),
        "mount_diameter": value_in(m0.diameter, "mm") if m0 else None,
        "mount_hole": value_in(m0.hole_diameter, "mm") if m0 else None,
        "density": value_in(made.material.density, "t/mm3") * 1e3,  # kg/mm³
        "draft": math.degrees(value_in(made.draft_inside, "rad"))
        if made.draft_inside is not None
        else 0.0,
    }
    bearings = []
    for st in chain.layout.shafts:
        for p in st.parts:
            if p.kind != "bearing":
                continue
            side = p.name.rsplit(" ", 1)[-1]
            choice = chain.bearings.get((st.shaft, side))
            bearings.append(
                {
                    "shaft": st.shaft,
                    "side": side,
                    "axis": list(st.axis),
                    "D": p.diameter,
                    "d": choice.bearing.d if choice else p.diameter / 2,
                    "z": [p.z_min, p.z_max],
                    "sealed": (st.shaft, side) in sealed,
                    "designation": choice.bearing.designation if choice else "guess",
                }
            )
    ends = [st.ends for st in chain.layout.shafts]
    pod = {c.name: "motor_side" if c.z1 <= sp.split_z else "cover" for c in sp.mounts}
    return {
        "stem": "contract",
        "form": "contract",
        "source": "zenryx.domains.gearbox.spaces from " + contract.name,
        "hypothesis": {
            "split": (hypothesis or Hypothesis()).split,
            "inside": "cup",
            "wall_mm": sp.wall,
            "bolts": "even",
        },
        "settings": settings,
        "z": {
            "lo": min(e[0] for e in ends),
            "hi": max(e[1] for e in ends),
            "split": sp.split_z,
            "motor": None,
        },
        "bearings": bearings,
        "mounts": [
            {
                "name": c.name,
                "centre": list(c.centre),
                "z": [c.z0, c.z1],
                "normal": [0.0, 0.0, 1.0],
                "pod": pod[c.name],
            }
            for c in sp.mounts
        ],
        "brackets": [
            {"name": c.name, "centre": list(c.centre), "radius": c.radius, "z": [c.z0, c.z1]}
            for c in sp.brackets
        ],
        "bolts": [list(c.centre) for c in sp.bolts],
        "exits": [
            {
                "name": c.name,
                "kind": "seal" if " seal " in c.name else "joint",
                "centre": list(c.centre),
                "radius": c.radius,
                "z": [c.z0, c.z1],
            }
            for c in sp.exits
        ],
        "motor_holes": [],
        "outline": [list(p) for p in sp.outline],
        "z_range": list(sp.z_range),
        "bolt_line": [list(p) for p in sp.bolt_line],
        "joint_outline": [list(p) for p in sp.joint_outline],
        "flange": {
            "land_width": settings["land_width"],
            "thickness": settings["flange_thickness"],
            "z": [sp.flange[0].z0, sp.flange[0].z1],
            "outer": [
                {"name": c.name, "centre": list(c.centre), "radius": c.radius} for c in sp.flange
            ],
            "inner": [
                {"name": c.name, "centre": list(c.centre), "radius": c.radius}
                for c in sp.flange_inside
            ],
        },
    }


def fixed_kg(rec: dict, contract: Path) -> dict:
    """The fixed metal's mass, each half, as the drawing holds it exact (`shell.fixed_metal`)."""
    spec, _ = load_and_validate(contract)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(
        chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm")
    )
    s = rec["settings"]
    out = {}
    for half in ("motor_side", "cover"):
        metal = fixed_metal(rec, all_rooms, rec["z"]["split"], half, s["wall"], s["draft"])
        out[half] = metal.Volume() * s["density"]
    out["total"] = sum(out.values())
    return out


def write(contract: Path, out: Path) -> Path:
    """The layout record, `out/contract.json`."""
    rec = record(contract)
    rec["fixed_exact_kg"] = fixed_kg(rec, contract)
    print(
        f"the fixed metal, exact: {rec['fixed_exact_kg']['total']:.3f} kg "
        f"(motor side {rec['fixed_exact_kg']['motor_side']:.3f}, cover "
        f"{rec['fixed_exact_kg']['cover']:.3f})"
    )
    target = out / "contract.json"
    target.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return target
