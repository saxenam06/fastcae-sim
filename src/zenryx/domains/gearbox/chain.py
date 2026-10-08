"""Steps 5 to 8 together: the layout, the bearing loads, the shaft sections and the bearing
selection go round until they agree (GBX-3; the calculation chain, docs/features/product/
2026-10-08-the-calculation-chain.md).

The bearings' widths set the layout, the layout sets the loads, the loads set the shaft sections,
and the loads and the sections set the bearings, whose widths go back to the layout. From a first
guess the round settles in two or three passes (Shigley Ch. 18's case study says the same).

Each seat's bearing is chosen for the life the contract asks at the drive case (the engineer,
9 October 00:50) and the shaft's speed at the rated input speed.
"""

from __future__ import annotations

from dataclasses import dataclass

from zenryx.contract.model import HousingDesignSpec
from zenryx.contract.train import shaft_speeds
from zenryx.domains.gearbox.bearings import Choice, select
from zenryx.domains.gearbox.forces import CaseForces, case_forces, value_in
from zenryx.domains.gearbox.layout import Layout, place
from zenryx.domains.gearbox.loads import CaseLoads, seat_loads
from zenryx.domains.gearbox.shafts import ShaftSection, sections

TOOL = "zenryx.domains.gearbox.chain"
VERSION = "0.1.0"

FIRST_GUESS = (20.0, 80.0)  # a bearing's width and outside Ø before any is selected, mm
MOST_PASSES = 8


@dataclass(frozen=True)
class Chain:
    """What steps 4 to 8 give together, once they agree. A seat no catalogue bearing
    serves is in `refused`, with the reason; the contract cannot be completed then."""

    forces: list[CaseForces]
    layout: Layout
    loads: list[CaseLoads]
    sections: list[ShaftSection]
    bearings: dict[tuple[str, str], Choice]
    passes: int
    drive_case: str
    speeds: dict[str, float]
    refused: dict[tuple[str, str], str]


def _speeds(spec: HousingDesignSpec) -> dict[str, float]:
    """Each shaft's speed (rev/min) at the rated input speed."""
    req = spec.requirement
    rated = next(s for s in req.speeds if s.kind == "rated")
    rpm = value_in(rated.speed, "rad/s") * 60.0 / (2.0 * 3.141592653589793)
    teeth = [(int(s.z_pinion.value), int(s.z_gear.value)) for s in req.stages]
    names = [req.stages[0].pinion_shaft] + [s.gear_shaft for s in req.stages]
    return dict(zip(names, shaft_speeds(rpm, teeth), strict=True))


def complete_chain(spec: HousingDesignSpec) -> Chain:
    """Steps 4 to 8 for a contract, gone round until the selected bearings stop changing."""
    req = spec.requirement
    forces = case_forces(spec)
    drive = next(
        (c for c, t in zip(forces, req.torques, strict=True) if t.direction == "drive"), None
    )
    if drive is None:
        raise ValueError("the bearings' life is taken at the drive case; the contract has none")
    hours = value_in(req.service_life, "s") / 3600.0
    speeds = _speeds(spec)
    types = {(b.shaft, b.side.value): b.type for b in req.shaft_layout.bearings}
    sizes = {key: FIRST_GUESS for key in types}
    chosen: dict[tuple[str, str], Choice] = {}
    refused: dict[tuple[str, str], str] = {}
    passes = 0
    while True:
        passes += 1
        if passes > MOST_PASSES:
            raise ArithmeticError(
                f"the layout and the bearings did not agree in {MOST_PASSES} passes"
            )
        layout = place(spec, sizes)
        ys = {
            key: c.bearing.Y
            for key, c in chosen.items()
            if c.bearing.type == "tapered_roller" and c.bearing.Y
        }
        loads = seat_loads(spec, layout, forces, y_factors=ys)
        bores = {key: c.bearing.d for key, c in chosen.items()}
        shafts = sections(spec, layout, forces, loads, bores)
        needed = {(s.shaft, side): s.bore_needed[side] for s in shafts for side in ("-z", "+z")}
        drive_loads = loads[forces.index(drive)]
        new: dict[tuple[str, str], Choice] = {}
        refused = {}
        for (shaft, side), kind in types.items():
            seat = drive_loads.seat(shaft, side)
            try:
                new[(shaft, side)] = select(
                    kind, needed[(shaft, side)], seat.radial, seat.axial, speeds[shaft], hours
                )
            except ValueError as why:  # no bearing serves: keep the last size, say why
                refused[(shaft, side)] = str(why)
                if (shaft, side) in chosen:
                    new[(shaft, side)] = chosen[(shaft, side)]
        same = (
            bool(chosen)
            and new.keys() == chosen.keys()
            and all(new[k].bearing.designation == chosen[k].bearing.designation for k in new)
        )
        chosen = new
        sizes = {**sizes, **{k: (c.bearing.width, c.bearing.D) for k, c in chosen.items()}}
        if same or (refused and passes > 1):
            break
    return Chain(forces, layout, loads, shafts, chosen, passes, drive.name, speeds, refused)
