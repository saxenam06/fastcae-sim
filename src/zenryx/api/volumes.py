"""The Contract page's result: the elements the product's contract fixes and the spaces they leave,
for its 3D view (PLT-8; consolidated for GBX-5, the engineer, 10 October 13:47-13:52).

    uv run python -m zenryx.api.volumes

writes web/src/records/volumes.json beside the snapshot. Three groups of layers, each derived
from those above it (the engineer, 10 October 14:00):
- **the contract:** gears, shafts, bearing bores, the differential, the mounts (solid; a shaft's
  exits and a mount's bracket room see-through with it) and the packaging space;
- **what the agent decides,** its first hypothesis (`spaces.Hypothesis`, the first loop's
  defaults, also listed in words): the split flange at the split's place, the shell (the inside and
  its wall), the bolts;
- **what the optimiser is given:** the design space, the packaging space less all of the above.

Each layer names its solids in the parts mesh (`faces`) and its see-through meshes (`ghosts`).
The meshes are tessellated (zenryx.geometry.solids) and packed as FCMESH03 (zenryx.api.mesh) in
base64. A check fails when the file is stale: run this after any contract change.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import numpy as np

from zenryx.api.mesh import encode, face_smoothed_normals
from zenryx.api.snapshot import CONTRACTS, ROOT
from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.volumes import volumes
from zenryx.geometry.solids import tessellate

OUT = ROOT / "web" / "src" / "records" / "volumes.json"

GROUPS = (
    ("contract", "The contract", "your requirements, and what the tools work out from them"),
    ("hypothesis", "What the agent decides", "its first hypothesis: the first loop's defaults"),
    ("given", "What the optimiser is given", "the packaging space less everything above"),
)

# Each layer: its id (a part's role), its group, its words, its colour (RGB 0-1).
LAYERS: tuple[tuple[str, str, str, tuple[float, float, float]], ...] = (
    ("gear", "contract", "Gears", (0.80, 0.55, 0.20)),
    ("shaft", "contract", "Shafts", (0.45, 0.47, 0.52)),
    ("bearing", "contract", "Bearing bores", (0.20, 0.45, 0.75)),
    ("carrier", "contract", "Differential", (0.55, 0.35, 0.60)),
    ("mount", "contract", "Mounts", (0.15, 0.58, 0.62)),
    ("packaging", "contract", "Packaging space", (0.55, 0.60, 0.65)),
    ("split", "hypothesis", "Split flange", (0.60, 0.30, 0.85)),
    ("shell", "hypothesis", "Shell", (0.70, 0.72, 0.76)),
    ("bolt", "hypothesis", "Bolts", (0.92, 0.76, 0.20)),
    ("design_space", "given", "Design space", (0.18, 0.62, 0.42)),
)


# The viewer's camera keeps z up. The picture is turned so the shafts (the contract's z) lie
# horizontal, along the viewer's y, and the contract's +y points down, so the output sits low: a
# rotation for the picture only, (x, y, z) -> (x, z, -y).
VIEW = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])


def _packed(shapes) -> str:
    vertices, triangles, owner, faces = tessellate(shapes)
    vertices = vertices @ VIEW.T
    normals = face_smoothed_normals(vertices, triangles, faces)
    return base64.b64encode(encode(vertices, triangles, owner, normals=normals)).decode("ascii")


def _view_box(box) -> list[float]:
    corners = np.array(
        [
            [x, y, z]
            for x in (box.xmin, box.xmax)
            for y in (box.ymin, box.ymax)
            for z in (box.zmin, box.zmax)
        ]
    )
    turned = corners @ VIEW.T
    return [round(float(v), 3) for v in (*turned.min(axis=0), *turned.max(axis=0))]


def _litres(shapes) -> float:
    return round(sum(s.Volume() for s in shapes) / 1e6, 3)


def _hypothesis(spec, space) -> list[dict[str, str]]:
    """The structural hypothesis the volumes were drawn for, in words."""
    sp = space.spaces
    least = spec.manufacturing.min_wall.value.value
    joint = spec.manufacturing.joint
    rows = [
        {"label": "Split", "value": f"between the stages, z = {sp.split_z:.2f} mm"},
        {"label": "Inside", "value": "one cup per half: every part's room run to the split"},
        {
            "label": "Wall",
            "value": f"{sp.wall:g} mm, uniform"
            + (" (the contract's least)" if abs(sp.wall - least) < 1e-9 else ""),
        },
    ]
    if joint is not None:
        pitch = joint.max_pitch.value.value
        rows.append(
            {
                "label": "Flange",
                "value": f"{joint.flange_thickness.value.value:g} mm each side of the split: a "
                f"sealing land {joint.land_width.value.value:g} mm round the inside, the bolts' "
                f"Ø{joint.boss_diameter.value.value:g} bosses on it (the process's rules)",
            }
        )
        rows.append(
            {
                "label": "Bolts",
                "value": f"{len(sp.bolts)}, evenly round the inside at most {pitch:g} mm apart; "
                "the halves joined only there",
            }
        )
    return rows


def _notes(spec, space) -> dict[str, str]:
    sp = space.spaces
    req = spec.requirement
    gaps = req.shaft_layout
    wall = f"{sp.wall:g} mm"
    return {
        "gear": "tip Ø over the face width; the inside keeps the least clearances round them "
        f"({gaps.min_radial_clearance.value.value:g} mm at the tips, "
        f"{gaps.min_axial_clearance.value.value:g} mm at the sides)",
        "shaft": "between the end faces; see-through where they leave: each seal's bore, and "
        "the half-shafts' joints beyond the output's ends",
        "bearing": "each bearing's outside Ø over its width",
        "carrier": "the differential's case",
        "mount": f"{len(sp.mounts)} bosses for the vehicle (assumed); see-through, the room of "
        "the vehicle's bracket and bolt beyond both faces, as far as the boss is long",
        "bolt": f"{len(sp.bolts)} bolts where the halves meet, at most "
        f"{spec.manufacturing.joint.max_pitch.value.value:g} mm apart round the inside (the "
        "process's rule)"
        if spec.manufacturing.joint is not None
        else "no joint rules in the contract",
        "shell": f"the inside (every part's room, run to the split: the parts go in from there) "
        f"and its least wall, {wall}",
        "split": f"where the halves meet, between the stages at z = {sp.split_z:.2f} mm (the "
        "design's choice): the flange, a sealing land round the inside, a flange deep each side "
        "(the process's rules)"
        if sp.flange
        else f"where the halves meet, between the stages at z = {sp.split_z:.2f} mm (the "
        "design's choice)",
        "packaging": "the layout's envelope grown by the installation clearance, and the mounts",
        "design_space": "the packaging space less every element: where the optimiser adds metal",
    }


def build(path: Path = CONTRACTS[0]) -> dict[str, Any]:
    spec, refusals = load_and_validate(path)
    if spec is None:
        raise ValueError(f"{path.name} does not load: {refusals}")
    chain = complete_chain(spec)
    space = volumes(spec, chain)
    reach = {role: [v for v in space.reach if v.role == role] for role in ("shaft", "mount")}
    ghosts = {
        "shaft": [("shaft_reach", reach["shaft"])],
        "mount": [("mount_reach", reach["mount"])],
        "shell": [("shell", [space.wall])],
        "split": [("split", [space.split])],
        "packaging": [("packaging", [space.packaging])],
        "design_space": [("design_space", [space.design])],
    }
    notes = _notes(spec, space)
    meshes = {"parts": _packed([v.solid for v in space.parts])}
    layers = []
    for role, group, label, colour in LAYERS:
        members = [i for i, v in enumerate(space.parts) if v.role == role]
        own = [(key, [v.solid for v in vols]) for key, vols in ghosts.get(role, []) if vols]
        if not members and not own:
            continue
        for key, shapes in own:
            meshes[key] = _packed(shapes)
        solids = [space.parts[i].solid for i in members] or [s for _, shapes in own for s in shapes]
        layers.append(
            {
                "id": role,
                "group": group,
                "label": label,
                "colour": list(colour),
                "faces": members,
                "ghosts": [key for key, _ in own],
                "names": [space.parts[i].name for i in members] or [label.lower()],
                "litres": _litres(solids),
                # the split drawn as a plane only where the contract has no joint rules (no flange)
                "plane": role == "split" and not space.spaces.flange,
                "note": notes[role],
            }
        )
    box = space.packaging.solid.BoundingBox()
    return {
        "schema": 2,
        "contract": spec.task.id,
        "groups": [{"id": g, "label": label, "sub": sub} for g, label, sub in GROUPS],
        "hypothesis": _hypothesis(spec, space),
        "layers": layers,
        "meshes": meshes,
        "bbox": _view_box(box),
        "faces": len(space.parts),
        "split_z": round(space.spaces.split_z, 3),
        "incomplete": [
            f"{shaft} {side}: {why}" for (shaft, side), why in sorted(chain.refused.items())
        ],
    }


def text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=1, sort_keys=True) + "\n"


def main() -> None:
    body = text(build())
    OUT.write_text(body, encoding="utf-8")
    print(f"wrote {OUT} ({len(body.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    main()
