"""The rooms each half of the housing holds, and the cup drawn round them (moved from
`prototypes/first_loop/cup.py`: `rooms`, `pieces`, `_cone`, `cup`; LOP-33).

Every part's room, taken in plan from its far end in the half to the split: each gear and the
carrier grown by the least radial and axial clearances; each bearing at its outside diameter over
its width; each shaft at its least bore through its end walls. The half's inside is their union and
its outside the wall's thickness out from it, drafted toward the split (the contract's draft). A
bore is cast `STOCK` under its size and machined after. Concentric ends within `SNAP_Z` and radii
within `SNAP_R` are made one, so no step under 2 mm and no ring under 1 mm is drawn.
"""

from __future__ import annotations

import math

import cadquery as cq

from zenryx.geometry.solids import fuse

STOCK = 1.0  # mm machined off a cast bore
SNAP_Z = 2.0  # mm
SNAP_R = 1.0  # mm


def rooms(chain, radial: float, axial: float) -> list[dict]:
    """Every part's room: shaft, kind ('gear' or 'bore'), axis, radius, z range."""
    out = []
    for st in chain.layout.shafts:
        least = []
        for p in st.parts:
            if p.kind in ("gear", "carrier"):
                out.append(
                    {
                        "shaft": st.shaft,
                        "kind": "gear",
                        "axis": tuple(st.axis),
                        "r": p.diameter / 2 + radial,
                        "z": (p.z_min - axial, p.z_max + axial),
                    }
                )
            elif p.kind == "bearing":
                out.append(
                    {
                        "shaft": st.shaft,
                        "kind": "bore",
                        "axis": tuple(st.axis),
                        "r": p.diameter / 2,
                        "z": (p.z_min, p.z_max),
                    }
                )
                choice = chain.bearings.get((st.shaft, p.name.rsplit(" ", 1)[-1]))
                least.append(choice.bearing.d if choice else 0.5 * p.diameter)
        out.append(
            {
                "shaft": st.shaft,
                "kind": "bore",
                "axis": tuple(st.axis),
                "r": min(least) / 2,
                "z": tuple(st.ends),
            }
        )
    return out


def pieces(all_rooms: list[dict], z_split: float, half: str) -> list[dict]:
    """The rooms that reach into a half, each with its far end there, near ends and radii snapped
    per axis."""
    lower = half == "motor_side"
    out = []
    for rm in all_rooms:
        z0, z1 = rm["z"]
        if (lower and z0 < z_split) or (not lower and z1 > z_split):
            out.append({**rm, "far": z0 if lower else z1})
    deeper = min if lower else max
    for a in out:
        for b in out:
            if a is b or math.dist(a["axis"], b["axis"]) > 1e-6:
                continue
            if abs(a["far"] - b["far"]) < SNAP_Z:
                a["far"] = b["far"] = deeper(a["far"], b["far"])
            if a["kind"] == b["kind"] and abs(a["r"] - b["r"]) < SNAP_R:
                a["r"] = b["r"] = max(a["r"], b["r"])
    return out


def _cone(axis, z_from: float, z_to: float, r_from: float, r_to: float) -> cq.Shape:
    """A truncated cone along z from z_from (radius r_from) to z_to (radius r_to); a cylinder when
    the radii are one (no draft)."""
    lo, hi = (z_from, z_to) if z_from < z_to else (z_to, z_from)
    r_lo, r_hi = (r_from, r_to) if z_from < z_to else (r_to, r_from)
    base = cq.Vector(axis[0], axis[1], lo)
    if abs(r_lo - r_hi) < 1e-9:
        return cq.Solid.makeCylinder(r_lo, hi - lo, base, cq.Vector(0, 0, 1))
    return cq.Solid.makeCone(r_lo, r_hi, hi - lo, base, cq.Vector(0, 0, 1))


def cup(
    all_rooms: list[dict], z_split: float, half: str, wall: float, draft: float
) -> tuple[cq.Shape, cq.Shape, list[dict]]:
    """The half's outside and its cavity (the cavity run 2 mm past the split, for a clean cut), and
    the pieces they were drawn from."""
    t = math.tan(math.radians(draft))
    lower = half == "motor_side"
    outward = -1.0 if lower else 1.0
    split_side = z_split - outward * 2.0  # 2 mm past the split, into the other half
    outs, cavs = [], []
    ps = pieces(all_rooms, z_split, half)
    for p in ps:
        far, ax = p["far"], p["axis"]
        run = abs(z_split - far)
        if p["kind"] == "gear":
            r_far, r_split = p["r"], p["r"] + run * t  # widening toward the split
        else:
            r_split = p["r"] - STOCK  # cast under its bore, narrowing away from the split
            r_far = r_split - run * t
        cavs.append(_cone(ax, far, split_side, r_far, r_split + 2.0 * t))
        # the outside: the wall all round and past the far end, on the same draft
        r_out_far = (p["r"] if p["kind"] == "bore" else r_far) + wall
        outs.append(
            _cone(ax, far + outward * wall, z_split, r_out_far, r_out_far + (run + wall) * t)
        )
    return fuse(outs).clean(), fuse(cavs).clean(), ps
