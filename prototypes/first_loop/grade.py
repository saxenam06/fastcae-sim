"""PROTOTYPE (LOP) - grade every design the loop judged, against the contract's pass lines. The grade itself is
`zenryx.workflow.grade` (LOP-33: the tilt against each bearing's line, the worst bed, peak drive alone, the orders, the
first mode, the mass); this writes data/first_loop/grades.json and prints the table, as before.

Run: uv run python prototypes/first_loop/grade.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "data" / "first_loop"

from zenryx.contract.validate import load_and_validate  # noqa: E402, F401  (tilt_by_case.py reads it here)
from zenryx.workflow.grade import (  # noqa: E402, F401  (REFERENCE, GRADED_CASES, FIRST_MODE_HZ, shaft_tilt_mrad: read here by other prototypes)
    FIRST_MODE_HZ,
    GRADED_CASES,
    REFERENCE,
    grade_all,
    shaft_tilt_mrad,
    table,
)

# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))


def main() -> None:
    grades, stale = grade_all(OUT, CONTRACT)
    print(table(grades, stale), end="")


if __name__ == "__main__":
    main()
