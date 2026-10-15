"""The housing's set-up for the rib field, from the contract (LOP-34; a prototype): the layout record
written by the product's own stage, the product's model built as the final recipe builds it, and its
size printed: cubes, columns, column groups (half x run), unknowns. `setup_probe.py [voxel mm]`."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import housing  # noqa: E402


def main() -> None:
    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    t0 = time.time()
    vox, model = housing.product_model(voxel)
    hh = vox.height
    col, pos = hh["col"], hh["pos"]
    groups = housing.column_groups(vox)
    print(f"built in {time.time() - t0:.0f} s")
    print(f"cubes {len(vox.elem):,} (fixed {int(vox.frozen.sum()):,}, free {len(vox.free_e):,}); "
          f"unknowns {vox.n_q:,}; columns {hh['n_cols']:,}; the longest {hh['L']:.0f} cubes")
    print(f"fixed metal {model['frozen_kg']:.2f} kg; seats {len(vox.seats)}; beds {len(vox.bed_keys)}")
    for g in groups:
        print(f"group {g['name']}: {len(g['cols']):,} columns, plan box x {g['lo'][0]:.0f}..{g['hi'][0]:.0f}, "
              f"y {g['lo'][1]:.0f}..{g['hi'][1]:.0f} mm, longest {int(pos[np.isin(col, g['cols'])].max()) + 1}")


if __name__ == "__main__":
    main()
