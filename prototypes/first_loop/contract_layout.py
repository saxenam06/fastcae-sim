"""PROTOTYPE (GBX-5) - the layout record the loop's scripts read, written from the product's own
description of the set-up (`zenryx.domains.gearbox.spaces`) instead of the generator's.

The loop's voxel model (`topo_free.build_free`), its set-up export and its CAD drawing read a
layout record, `data/first_loop/<layout>.json`. Until 10 October that was `grammar4`, the
generator's design: its mounts, bolts, split, seals and the motor's ring. Now the contract holds
the mounts (A20), the seals' section (A16), the half-shafts' joints (A27) and the joint's rules
(A26), with no motor flange (the engineer, 10 October 13:21), and the split and the bolts come from
a hypothesis (`spaces.Hypothesis`, the first loop's defaults). This writes them as the record
`contract`, in grammar4's format where the scripts share it, so `layout="contract"` gives the
optimiser exactly what the Contract page draws. Earlier runs keep `layout="grammar4"`.

Keys beyond grammar4's: `exits` (each shaft's way out: its seal's bore, a half-shaft's joint),
`brackets` (the vehicle's bracket room beyond each mount's faces), `bosses_fixed` in the settings
(the bolts' bosses held as metal), `flange` (the split flange, the contract's since 11 October:
its land's width and depth, the circles whose union less the inner ones is the sealing land) and
`land_width` in the settings. No `motor_ring` setting and no motor holes: there is no motor flange.
The bolt line follows the rooms' outline through the waists (`spaces`, 11 October), not their hull.

Run after any contract change: .venv/Scripts/python.exe prototypes/first_loop/contract_layout.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.domains.gearbox.spaces import Hypothesis, spaces  # noqa: E402

CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
TARGET = ROOT / "data" / "first_loop" / "contract.json"
GRAMMAR = ROOT / "data" / "first_loop" / "grammar4.json"


def record(path: Path = CONTRACT, hypothesis: Hypothesis | None = None) -> dict:
    spec, refusals = load_and_validate(path)
    if spec is None:
        raise ValueError(f"{path.name} does not load: {refusals}")
    chain = complete_chain(spec)
    sp = spaces(spec, chain, hypothesis)
    req, made = spec.requirement, spec.manufacturing
    joint = made.joint
    sealed = {(e.shaft, e.side.value) for e in req.shaft_layout.sealed_ends}
    # The generator's own settings stay for what the contract does not say (the drawing's draft,
    # fillets, lip): its recipe, not an interface.
    generator = json.loads(GRAMMAR.read_text(encoding="utf-8"))["settings"] if GRAMMAR.exists() else {}
    for key in ("motor_ring", "motor_bolt_circle", "motor_bolts", "motor_ring_thickness", "motor_room", "motor_clear", "spokes_motor"):
        generator.pop(key, None)
    m0 = req.mounts[0] if req.mounts else None
    settings = {
        **generator,
        "wall": sp.wall,
        "seal_radial": value_in(req.shaft_layout.seal_section, "mm"),
        "bolt_hole": value_in(joint.hole_diameter, "mm"),
        "bolt_boss": value_in(joint.boss_diameter, "mm"),
        # (LOP-29) a bolt head's socket beyond each flange face, Ø and depth (mm): the head (an M8 cap head is Ø13) and a hex
        # key's room; the drawing's since 11 October (`outcome_cad.SOCKET`), the optimiser's since 13 October
        "bolt_socket": [16.0, 25.0],
        "flange_bolt_axis": value_in(joint.bolt_offset, "mm"),
        "bolt_pitch": value_in(joint.max_pitch, "mm"),
        "flange_thickness": value_in(joint.flange_thickness, "mm"),
        "land_width": value_in(joint.land_width, "mm"),
        "mount_diameter": value_in(m0.diameter, "mm") if m0 else None,
        "mount_hole": value_in(m0.hole_diameter, "mm") if m0 else None,
        "mount_length": value_in(m0.length, "mm") if m0 else None,
        "bracket_room": value_in(m0.bracket_room, "mm") if m0 and m0.bracket_room else None,
        "density": value_in(made.material.density, "t/mm3") * 1e3,  # kg/mm³, as grammar4's
        "bosses_fixed": True,
    }
    # The drawing's draft is the contract's (A11; 0° inside and out), not the generator's 1.5°,
    # which drew the exact cup 0.26 kg heavier than the contract asks (11 October 00:33).
    if made.draft_inside is not None:
        settings["draft"] = math.degrees(value_in(made.draft_inside, "rad"))
    bearings = []
    for st in chain.layout.shafts:
        for p in st.parts:
            if p.kind != "bearing":
                continue
            side = p.name.rsplit(" ", 1)[-1]
            choice = chain.bearings.get((st.shaft, side))
            bearings.append({
                "shaft": st.shaft, "side": side, "axis": list(st.axis), "D": p.diameter,
                "d": choice.bearing.d if choice else p.diameter / 2, "z": [p.z_min, p.z_max],
                "sealed": (st.shaft, side) in sealed,
                "designation": choice.bearing.designation if choice else "guess",
                "boss_r": (settings.get("boss_k", 1.25) * p.diameter + settings.get("boss_c", 10.0)) / 2,
            })  # fmt: skip
    ends = [st.ends for st in chain.layout.shafts]
    return {
        "stem": "contract",
        "form": "contract",
        "source": "zenryx.domains.gearbox.spaces from " + path.name,
        "hypothesis": {"split": sp_split(hypothesis), "inside": "cup", "wall_mm": sp.wall, "bolts": "even"},
        "settings": settings,
        "z": {"lo": min(e[0] for e in ends), "hi": max(e[1] for e in ends), "split": sp.split_z, "motor": None},
        "bearings": bearings,
        "mounts": [{"name": c.name, "centre": list(c.centre), "z": [c.z0, c.z1], "normal": [0.0, 0.0, 1.0], "pod": "motor_side" if c.z1 <= sp.split_z else "cover"} for c in sp.mounts],
        "brackets": [{"name": c.name, "centre": list(c.centre), "radius": c.radius, "z": [c.z0, c.z1]} for c in sp.brackets],
        "bolts": [list(c.centre) for c in sp.bolts],
        "exits": [{"name": c.name, "kind": "seal" if " seal " in c.name else "joint", "centre": list(c.centre), "radius": c.radius, "z": [c.z0, c.z1]} for c in sp.exits],
        "motor_holes": [],
        "outline": [list(p) for p in sp.outline],
        "z_range": list(sp.z_range),
        "bolt_line": [list(p) for p in sp.bolt_line],
        "joint_outline": [list(p) for p in sp.joint_outline],
        "flange": {"land_width": settings["land_width"], "thickness": settings["flange_thickness"], "z": [sp.flange[0].z0, sp.flange[0].z1],
                   "outer": [{"name": c.name, "centre": list(c.centre), "radius": c.radius} for c in sp.flange],
                   "inner": [{"name": c.name, "centre": list(c.centre), "radius": c.radius} for c in sp.flange_inside]} if sp.flange else None,
    }  # fmt: skip


def sp_split(hypothesis: Hypothesis | None) -> str:
    return (hypothesis or Hypothesis()).split


def fixed_kg(rec: dict, path: Path = CONTRACT) -> dict:
    """The fixed metal's mass, each half, as the skin drawing draws it exact (`outcome_cad.fixed_metal`:
    the cup's wall, the split flange, the bolts' bosses, the mounts, less the inside and the holes).
    The optimiser's fixed voxels weigh this (`topo_free.build_free`'s `flange`): its 6 mm cubes alone
    counted the wall 0.24 kg light, so the drawing came out heavier than the budget (11 October 00:33)."""
    sys.path.insert(0, str(HERE))
    import cup as cupmod
    import outcome_cad

    spec, _ = load_and_validate(path)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    all_rooms = cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))
    s = rec["settings"]
    out = {}
    for half in ("motor_side", "cover"):
        metal = outcome_cad.fixed_metal(rec, all_rooms, rec["z"]["split"], half, s["wall"], s.get("draft", 0.0))
        out[half] = metal.Volume() * s["density"]
    out["total"] = sum(out.values())
    return out


def main() -> Path:
    rec = record()
    if rec.get("flange"):
        rec["fixed_exact_kg"] = fixed_kg(rec)
        print(f"the fixed metal, exact: {rec['fixed_exact_kg']['total']:.3f} kg "
              f"(motor side {rec['fixed_exact_kg']['motor_side']:.3f}, cover {rec['fixed_exact_kg']['cover']:.3f})")
    TARGET.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return TARGET


if __name__ == "__main__":
    main()
