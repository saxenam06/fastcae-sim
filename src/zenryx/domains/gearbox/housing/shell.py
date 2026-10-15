"""What the contract fixes of each half, exact (moved from `prototypes/first_loop/outcome_cad.py`:
`exact_shell`, `fixed_metal`; LOP-33): the layout weighs it, so the optimiser's fixed voxels weigh
what the drawing's fixed metal will (its budget is the drawing's own remainder)."""

from __future__ import annotations

import cadquery as cq

from zenryx.domains.gearbox.housing import cup as cupmod
from zenryx.domains.gearbox.housing import say
from zenryx.geometry.solids import cylinder, fuse


def exact_shell(
    layout: dict, all_rooms: list[dict], z_split: float, half: str, wall: float, draft: float
) -> cq.Shape:
    """The cup's outside (the inside grown by the least wall); over the other half's wider opening,
    its rooms grown by the wall a wall thick at the split; the split flange's sealing land and the
    bolts' bosses on it, a flange thick; in the motor side, the mounts. Solid through the inside."""
    s = layout["settings"]
    fl = layout["flange"]
    lower = half == "motor_side"
    outside, _, _ = cupmod.cup(all_rooms, z_split, half, wall, draft)
    parts = [outside]
    plate = (z_split - wall, z_split) if lower else (z_split, z_split + wall)
    other = "cover" if lower else "motor_side"
    parts += [
        cylinder(p["axis"], *plate, 2 * (p["r"] + wall))
        for p in cupmod.pieces(all_rooms, z_split, other)
    ]
    t_f = fl["thickness"]
    zf = (z_split - t_f, z_split) if lower else (z_split, z_split + t_f)
    land = fuse([cylinder(c["centre"], *zf, 2 * c["radius"]) for c in fl["outer"]])
    land = land.cut(
        fuse(
            [cylinder(c["centre"], zf[0] - 1.0, zf[1] + 1.0, 2 * c["radius"]) for c in fl["inner"]]
        )
    )
    parts.append(land)
    parts += [cylinder(c, *zf, s["bolt_boss"]) for c in layout["bolts"]]
    if lower:
        parts += [
            cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"])
            for m in layout["mounts"]
        ]
    shell = fuse(parts).clean()
    say(
        f"{half}: the exact shell (the {wall:g} mm wall, the split flange, the "
        f"bosses{', the mounts' if lower else ''}): "
        f"{len(shell.Faces())} faces, valid {shell.isValid()}"
    )
    return shell


def fixed_metal(
    layout: dict, all_rooms: list[dict], z_split: float, half: str, wall: float, draft: float
) -> cq.Shape:
    """The half's fixed metal as the CAD holds it: `exact_shell` less the inside, the bearings'
    seats at their bores, the shafts' exits and the bolts' and mounts' holes."""
    s = layout["settings"]
    lower = half == "motor_side"
    metal = exact_shell(layout, all_rooms, z_split, half, wall, draft).cut(
        cupmod.cup(all_rooms, z_split, half, wall, draft)[1]
    )
    t_f = layout["flange"]["thickness"]
    for b in layout["bearings"]:
        if (b["side"] == "-z") == lower:
            metal = metal.cut(cylinder(b["axis"], b["z"][0], b["z"][1], b["D"]))
    for e in layout.get("exits") or []:
        if (e["z"][1] <= z_split) == lower:
            metal = metal.cut(
                cylinder(e["centre"], e["z"][0] - 1.0, e["z"][1] + 1.0, 2 * e["radius"])
            )
    for c in layout["bolts"]:
        metal = metal.cut(cylinder(c, z_split - t_f - 1.0, z_split + t_f + 1.0, s["bolt_hole"]))
    for m in layout["mounts"] if lower else []:
        metal = metal.cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
    return metal.clean()
