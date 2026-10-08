"""The Contract page's result: the volumes the product's contract fixes, for its 3D view (PLT-8).

    uv run python -m zenryx.api.volumes

writes web/src/records/volumes.json beside the snapshot: the parts (gears, shafts, bearings, the
differential), the packaging space and the design space, each tessellated
(zenryx.geometry.solids) and packed as FCMESH03 (zenryx.api.mesh) in base64, with what each layer
holds and its volume. A check fails when the file is stale: run this after any contract change.
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

# Each layer: its role, its words, its colour (RGB 0-1), drawn solid or see-through.
LAYERS: tuple[tuple[str, str, tuple[float, float, float], str], ...] = (
    ("gear", "Gears", (0.80, 0.55, 0.20), "solid"),
    ("shaft", "Shafts", (0.45, 0.47, 0.52), "solid"),
    ("bearing", "Bearing bores", (0.20, 0.45, 0.75), "solid"),
    ("carrier", "Differential", (0.55, 0.35, 0.60), "solid"),
    ("packaging", "Packaging space", (0.55, 0.60, 0.65), "ghost"),
    ("design_space", "Design space", (0.18, 0.62, 0.42), "ghost"),
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


def build(path: Path = CONTRACTS[0]) -> dict[str, Any]:
    spec, refusals = load_and_validate(path)
    if spec is None:
        raise ValueError(f"{path.name} does not load: {refusals}")
    chain = complete_chain(spec)
    space = volumes(spec, chain)
    layers = []
    for role, label, colour, draw in LAYERS:
        if draw == "solid":
            members = [i for i, v in enumerate(space.parts) if v.role == role]
            if not members:
                continue
            cm3 = sum(space.parts[i].solid.Volume() for i in members) / 1000.0
            names = [space.parts[i].name for i in members]
        else:
            members = []
            solid = space.packaging.solid if role == "packaging" else space.design.solid
            cm3 = solid.Volume() / 1000.0
            names = [label.lower()]
        layers.append(
            {
                "id": role,
                "label": label,
                "colour": list(colour),
                "draw": draw,
                "faces": members,
                "names": names,
                "litres": round(cm3 / 1000.0, 3),
            }
        )
    box = space.packaging.solid.BoundingBox()
    return {
        "schema": 1,
        "contract": spec.task.id,
        "layers": layers,
        "meshes": {
            "parts": _packed([v.solid for v in space.parts]),
            "packaging": _packed([space.packaging.solid]),
            "design_space": _packed([space.design.solid]),
        },
        "bbox": _view_box(box),
        "faces": len(space.parts),
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
