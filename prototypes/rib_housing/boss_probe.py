"""What solid bearing bosses buy the rib model (LOP-34; a prototype): the tilts and beds over their
lines with (a) every free cube solid, (b) ribs alone (x = 0.6), (c) the same ribs with every cube
in the boss zone (within 0.625 D + 5 mm of a bearing's axis, the handbook's boss) solid, (d) that
zone solid alone. `boss_probe.py [voxel mm]`."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import field as fieldmod  # noqa: E402
import housing  # noqa: E402
import ribmodel  # noqa: E402


def boss_zone(vox, hf) -> np.ndarray:
    """Each free cube: is its column within 0.625 D + 5 mm of a bearing's axis of its half?"""
    info = vox.model["info"]
    split = info["z"]["split"]
    zone_col = np.zeros(len(hf.col_len_mm), bool)
    for grp in hf.groups:
        below = grp.half == "motor_side"
        for b in info["bearings"]:
            if (0.5 * (b["z"][0] + b["z"][1]) < split) != below:
                continue
            r = np.hypot(grp.xy[:, 0] - b["axis"][0], grp.xy[:, 1] - b["axis"][1])
            zone_col[grp.cols[r < 0.625 * b["D"] + 5.0]] = True
    return zone_col[hf.col]


def main() -> None:
    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    vox, model = housing.product_model(voxel, out=housing.OUT / f"v{voxel:g}")
    rm = ribmodel.RibModel(vox)
    hf = fieldmod.HousingField(vox, housing.column_groups(vox), rm.c_local, rm.c_iso)
    boss = boss_zone(vox, hf)
    zone = fieldmod.solid_zone(vox)
    print(f"the bosses' zone {int(boss.sum()):,} free cubes; with the mounts' corridors {int(zone.sum()):,}")
    a3 = hf.a**3 * hf.density
    print(f"the boss zone: {int(zone.sum()):,} of {len(zone):,} free cubes ({zone.sum() * a3:.2f} kg if solid)")
    x = hf.start(0.6)
    c, pc = hf.stiffness(x)
    hf.align(rm.energy(rm.analyse(c, adjoints=False)["q"]), pc)
    c_ribs, pc = hf.stiffness(x)
    ribs_kg = hf.mass(pc)
    solid = np.broadcast_to(rm.c_iso, c_ribs.shape)
    cases = {
        "every free cube solid": (solid.copy(), len(zone) * a3),
        "ribs alone": (c_ribs, ribs_kg),
        "ribs and the solid zones full": (np.where(zone[:, None, None], rm.c_iso, c_ribs), ribs_kg + zone.sum() * a3),
        "the solid zones full alone": (np.where(zone[:, None, None], rm.c_iso, ribmodel.ERSATZ * rm.c_iso),
                                      zone.sum() * a3),
    }
    for name, (c, kg) in cases.items():
        out = rm.analyse(c, adjoints=False)
        print(f"{name} ({kg:.2f} kg placed): tilts {np.round(out['ratios'], 2)}, beds {np.round(out['beds'], 2)}",
              flush=True)


if __name__ == "__main__":
    main()
