"""PROTOTYPE (LOP-33) - the moved optimiser's model (`zenryx.domains.gearbox.housing.voxels`) on a finished run's own
field, against the binary check that run recorded: the same field at 0.5, all metal or air, must read the same worst
tilt, worst bed, compliance and modes, if the model is the run's. No optimisation: one analysis with its modes.

    model_parity.py <run stem> [<folder>]      (the folder holding <run>.json, <run>.npz and contract.json;
                                                default data/first_loop)

Run where the run's layout record (`contract.json`) is the one it was made on."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.housing.optimise import CASES, MEMBER_ALPHA  # noqa: E402
from zenryx.domains.gearbox.housing.setup import build  # noqa: E402
from zenryx.domains.gearbox.housing.voxels import MODE_COUNT, PENAL, Voxels  # noqa: E402
from zenryx.workflow.grade import GRADED_CASES, REFERENCE  # noqa: E402

CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"


def main(stem: str, folder: Path) -> None:
    rec = json.loads((folder / f"{stem}.json").read_text(encoding="utf-8"))
    z = np.load(folder / f"{stem}.npz")
    spec, _ = load_and_validate(CONTRACT)
    layout = json.loads((folder / "contract.json").read_text(encoding="utf-8"))
    h = float(rec["voxel_mm"])
    model = build(layout, spec, h, float(rec["band_mm"]), float(rec["height_field"]["radius_mm"]))
    model.update(cases=CASES, safety=float(rec["safety"]), least_height_mm=float(rec["least_height_mm"]),
                 least_width_mm=float(rec["least_width_mm"]), beds_mm={c: REFERENCE[c] / 1000.0 for c in CASES if c in GRADED_CASES},
                 modes=rec["modes"], max_member={**rec["max_member"], "alpha": MEMBER_ALPHA})  # fmt: skip
    vox = Voxels(model)
    same = len(vox.elem) == len(z["elem"]) and np.array_equal(vox.elem, z["elem"]) and np.array_equal(vox.free_e, z["free_e"])
    print(f"the model's voxels the run's: {same} ({len(vox.elem):,} elements, the run's {len(z['elem']):,})")
    if not same:
        return
    dens = np.ones(len(vox.elem))
    dens[vox.free_e] = (np.asarray(z["phys"]) >= 0.5).astype(float)
    b = vox.with_modes(vox.analyse(dens, PENAL, adjoints=False))
    vox.release(b)
    ref = rec["binary"]
    rows = [("worst tilt (x its line)", float(b["ratio_vector"].max()), ref["worst"]),
            ("worst bed (x the design to beat's)", float(b["bed_vector"].max()), ref["bed_worst"]),
            ("compliance (N mm)", float(b["value"]), ref["value"])]  # fmt: skip
    rows += [(f"mode {i + 1} (Hz)", float(v), r) for i, (v, r) in enumerate(zip(b["modes_hz"], ref["modes_hz"], strict=False))]
    for name, v, r in rows:
        print(f"  {name:36s} {v:12.5g}   the run's {r:12.5g}   {100 * (v - r) / abs(r):+.3f} %")
    print(f"  ({MODE_COUNT} modes read)")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "first_loop")
