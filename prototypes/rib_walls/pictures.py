"""A drawn walls design pictured by the product's own pictures (LOP-34, the restart; a prototype):
`pictures.py <design> [<folder>]` writes `look_<design>.png` (each half from four cameras) and
`look_face_<design>.png` (each half's outside nearly along the pull) into the folder
(`data/rib_walls` by default)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    from zenryx.domains.gearbox.housing import look

    design = sys.argv[1]
    folder = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "rib_walls"
    print(look.look(design, folder))
    print(look.look(design, folder, face=True))


if __name__ == "__main__":
    main()
