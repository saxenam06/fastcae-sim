"""How much metal a height-field run piles round each bearing bore (LOP-24, the bore experiment; the
engineer, 11 October 22:47: "a solution to the spill done directly on the bearing bore"). For each bore
of each half: in the annulus from its wall out to its trade boss radius plus 40 mm, the share of the
plan under a member (a column at least 4 mm high), the members' mean height, and the metal by angle in
24 sectors (where the run's own spokes would go). Prints a line a bore and its sectors' heights.

    bore_spill.py <run>"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
MEMBER = 4.0
SECTORS = 24


def main(run: str) -> list[dict]:
    lay = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    ch = shh.column_heights(run)
    h, lo = ch["h"], ch["lo"]
    x0, y0 = float(lo[0]), float(lo[1])
    rows = []
    for half, side in (("motor_side", "-z"), ("cover", "+z")):
        big = ndi.zoom(ch[half], h, order=3)
        X, Y = np.meshgrid(x0 + np.arange(big.shape[0]) + 0.5, y0 + np.arange(big.shape[1]) + 0.5, indexing="ij")
        for b in (b for b in lay["bearings"] if b["side"] == side):
            r = np.hypot(X - b["axis"][0], Y - b["axis"][1])
            ang = np.arctan2(Y - b["axis"][1], X - b["axis"][0])
            r_in, r_out = b["D"] / 2.0, float(b["boss_r"]) + 40.0
            ann = (r >= r_in) & (r <= r_out)
            member = big >= MEMBER
            covered = float((member & ann).sum()) / max(int(ann.sum()), 1)
            k = ((ang + np.pi) / (2 * np.pi) * SECTORS).astype(int) % SECTORS
            sect = np.array([float(np.where(ann & (k == s), big, 0.0).sum()) / max(int((ann & (k == s)).sum()), 1) for s in range(SECTORS)])
            # the boss (the seat's wall out to the boss radius, the contract's) against the ring beyond it, over the gear's wall
            boss = (r >= r_in) & (r <= float(b["boss_r"]))
            beyond = (r > float(b["boss_r"])) & (r <= r_out)
            vol = np.where(member, big, 0.0)
            rows.append({"half": half, "shaft": b["shaft"], "side": side, "D": b["D"], "boss_r": b["boss_r"], "covered": covered,
                         "mean_mm": float(big[member & ann].mean()) if (member & ann).any() else 0.0, "sectors_mm": sect.round(1).tolist(),
                         "boss_covered": float((member & boss).sum()) / max(int(boss.sum()), 1),
                         "beyond_covered": float((member & beyond).sum()) / max(int(beyond.sum()), 1),
                         "beyond_share": float(vol[beyond].sum()) / max(float(vol[ann].sum()), 1e-9)})  # fmt: skip
    for r in rows:
        top = np.argsort(r["sectors_mm"])[::-1][:6]
        deg = sorted(int(round(-180 + 360 * (s + 0.5) / SECTORS)) for s in top)
        print(f"{r['half']}: the {r['shaft']} bore (D {r['D']:.0f}, boss {r['boss_r']:.1f}): covered {100 * r['covered']:.0f} %, mean "
              f"height {r['mean_mm']:.1f} mm; the six fullest directions {deg}°; the boss {100 * r['boss_covered']:.0f} % covered, "
              f"beyond it {100 * r['beyond_covered']:.0f} %, holding {100 * r['beyond_share']:.0f} % of the metal")  # fmt: skip
    return rows


if __name__ == "__main__":
    main(sys.argv[1])
