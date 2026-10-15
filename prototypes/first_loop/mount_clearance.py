"""PROTOTYPE (LOP-20) - each mount's bracket room against the housing: its clearance to the shell's
outside (the inside grown by the least wall) and to the split flange's outer edge (the joint's
outline), in plan, and the outward move that gives it `MARGIN` past the flange's edge. It placed
the contract's mounts (A20) on 10 October 20:47; `checks/gearbox/test_spaces.py` now holds them so.

Run: .venv/Scripts/python.exe prototypes/first_loop/mount_clearance.py
"""

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.spaces import spaces  # noqa: E402

MARGIN = 3.0  # mm past the flange's edge
spec, refusals = load_and_validate(ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json")
assert not refusals, refusals
sp = spaces(spec, complete_chain(spec))
outline = np.asarray(sp.joint_outline, float)


def to_outline(p):
    """The signed distance from point p to the joint's outline in plan (negative inside) and the
    outward direction at its nearest point."""
    a, b = outline, np.roll(outline, -1, axis=0)
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0.0, 1.0)
    near = a + t[:, None] * ab
    d = np.hypot(*(p - near).T)
    k = int(np.argmin(d))
    from matplotlib.path import Path as Polygon

    inside = Polygon(outline).contains_point(p)
    direction = (p - near[k]) / max(d[k], 1e-12)
    return (-d[k] if inside else d[k]), (-direction if inside else direction)


for m, name in zip(sp.mounts, [mm.name for mm in spec.requirement.mounts], strict=True):
    c = np.asarray(m.centre, float)
    r_b = next(b.radius for b in sp.brackets if b.name.startswith(name))
    shell = min(math.hypot(c[0] - s.centre[0], c[1] - s.centre[1]) - s.radius for s in sp.shell) - r_b
    d_out, n_out = to_outline(c)
    flange = d_out - r_b
    move = max(0.0, MARGIN - flange)
    new = c + move * n_out if move else c
    print(f"{name}: centre ({c[0]:.1f}, {c[1]:.1f}), bracket room r {r_b:g}: clearance to the shell {shell:+.1f} mm, "
          f"to the flange's edge {flange:+.1f} mm; move {move:.1f} mm outward to ({new[0]:.1f}, {new[1]:.1f})")
