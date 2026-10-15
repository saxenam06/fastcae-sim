"""Complete a posed contract: write the load tool's results into it (GBX-4, the chain's step 9).

"Complete" is the engineer's word (9 October 01:54): the contract is posed with the user's
requirements; the load tool completes it with what it calculated; then it is frozen as the task.

What goes in, every value stamped with this tool, its version and the posed contract's hash
(derived physics is computed, never typed):
- **interfaces.seats:** one per selected bearing: its centre on the shaft's axis at the bearing's
  support, the axis along z, its diameter the bearing's outside Ø, its width the bearing's, the
  shoulder on the side away from the gears, the machining stock, and the bearing and its type;
- **interfaces.mount_pads** and **interfaces.motor_flanges:** the requirement's, as given;
- **physics.load_cases:** each case's seat forces, and, where the motor bolts to the housing, its
  reaction torque on the flange (a motor the vehicle holds puts none on the housing);
- **physics.mesh_orders:** each mesh's teeth per revolution of its pinion's shaft.

A contract the round cannot complete (a seat no catalogue bearing serves) is refused with why.
"""

from __future__ import annotations

from zenryx.contract.canonical import spec_hash
from zenryx.contract.entry import Entry, Provenance
from zenryx.contract.model import (
    CylindricalSeat,
    HousingDesignSpec,
    InterfaceMoment,
    Interfaces,
    LoadCase,
    MeshOrder,
    PhysicsCases,
    SeatLoad,
)
from zenryx.contract.units import Quantity, Vector
from zenryx.domains.gearbox.chain import Chain, complete_chain

TOOL = "zenryx.domains.gearbox.complete"
VERSION = "0.1.0"


def seat_name(shaft: str, side: str) -> str:
    """A seat's name: its shaft and its end ("input:zneg", "output:zpos")."""
    return f"{shaft}:{'zneg' if side == '-z' else 'zpos'}"


def complete(spec: HousingDesignSpec, chain: Chain | None = None) -> HousingDesignSpec:
    """The completed contract (stage "completed"), or ValueError where it cannot be completed."""
    if spec.stage != "posed":
        raise ValueError(f"only a posed contract is completed, not a {spec.stage} one")
    chain = chain or complete_chain(spec)
    if chain.refused:
        why = "; ".join(f"{seat_name(*k)}: {v}" for k, v in sorted(chain.refused.items()))
        raise ValueError(f"the contract cannot be completed: {why}")
    stamp = Provenance(kind="derived", tool=TOOL, tool_version=VERSION, input_hash=spec_hash(spec))

    def derived(value) -> Entry:
        return Entry(value=value, provenance=stamp, authority="engineer_locked", kind="derived")

    def mm(x: float) -> Quantity:
        return Quantity(value=round(x, 6), unit="mm")

    stock = spec.manufacturing.machining_stock.value
    seats = []
    for (shaft, side), choice in sorted(chain.bearings.items()):
        stack = chain.layout.stack(shaft)
        part = stack.bearing(side)
        x, y = stack.axis
        b = choice.bearing
        seats.append(
            CylindricalSeat(
                name=seat_name(shaft, side),
                shaft=shaft,
                centre=derived(Vector(values=(x, y, part.centre), unit="mm")),
                axis=derived(Vector(values=(0.0, 0.0, 1.0), unit="1")),
                diameter=derived(mm(b.D)),
                width=derived(mm(b.width)),
                shoulder="-axis" if side == "-z" else "+axis",
                stock=derived(stock),
                bearing=derived(b.designation),
                bearing_type=b.type,
            )
        )
    req = spec.requirement
    flange = req.motor_flange
    cases = []
    for case in chain.loads:
        moments = []
        if flange is not None:
            moments.append(
                InterfaceMoment(
                    interface=flange.name,
                    moment=derived(
                        Vector(values=(0.0, 0.0, round(case.motor_torque, 6)), unit="N*mm")
                    ),
                )
            )
        cases.append(
            LoadCase(
                name=case.name.replace(" ", "_"),
                seat_loads=[
                    SeatLoad(
                        seat=seat_name(s.shaft, s.side),
                        force=derived(Vector(values=tuple(round(v, 6) for v in s.force), unit="N")),
                    )
                    for s in case.seats
                ],
                interface_moments=moments,
            )
        )
    orders = [
        MeshOrder(
            stage=s.name,
            shaft=s.pinion_shaft,
            order=derived(Quantity(value=float(s.z_pinion.value), unit="1")),
        )
        for s in req.stages
    ]
    interfaces = Interfaces(
        seats=seats,
        mount_pads=list(req.mounts),
        motor_flanges=[flange] if flange is not None else [],
    )
    return spec.model_copy(
        update={
            "stage": "completed",
            "interfaces": interfaces,
            "physics": PhysicsCases(load_cases=cases, mesh_orders=orders),
        }
    )
