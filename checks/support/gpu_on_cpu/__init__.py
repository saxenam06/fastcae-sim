"""The GPU libraries on the CPU, for the checks only (LOP-33): `cupy`, `cupyx.scipy.sparse` and
nvmath's `DirectSolver`, so the optimiser's and FE's GPU paths run where there is no card and the
moved code can be compared with the prototype's on the same inputs.

`use()` puts the stand-ins first on `sys.path`; a check calls it before importing the code it runs.
A process that already imported the real CuPy keeps it."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def use() -> None:
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
