"""PROTOTYPE - not product code, not the judge.

Ivanov 2018's two meshes at 150 N·m: the forces by the simple (standard-gear) formulas and by the
base-circle form that holds for profile-shifted gears, to size the difference the load tool's plan
must handle (docs/features/gearbox/2026-10-08-load-tool-plan.md, §4). GBX-1 builds the tool itself,
with its checks. This script prints its numbers and writes nothing.

Run: uv run python prototypes/helical_forces/forces.py
"""

import math

from zenryx.contract.involute import inv, inv_inverse

T_IN = 150_000.0  # N·mm at the input
STAGES = [
    ("stage 1", 25, 51, 1.85, 30.0, 0.43672, 0.57199922),
    ("stage 2", 23, 81, 2.05, 30.0, 0.431143, 0.56857692),
]
AN = math.radians(18.0)

torque = T_IN
for name, z1, z2, mn, beta_deg, x1, x2 in STAGES:
    beta = math.radians(beta_deg)
    at = math.atan(math.tan(AN) / math.cos(beta))
    awt = inv_inverse(inv(at) + 2 * (x1 + x2) * math.tan(AN) / (z1 + z2), guess=at)
    bb = math.atan(math.tan(beta) * math.cos(at))
    d1 = z1 * mn / math.cos(beta)
    db1 = d1 * math.cos(at)
    # Simple formulas (Shigley, Lodz, Ivanov §2.2): at the reference circle, standard angles.
    ft_s = 2 * torque / d1
    fr_s = ft_s * math.tan(AN) / math.cos(beta)
    fa_s = ft_s * math.tan(beta)
    # Base-circle form: the transverse force along the line of action is T / r_b, split at the
    # working pressure angle; the axial part follows the base helix. Equal to the simple form at
    # x = 0.
    fbt = 2 * torque / db1
    ft_w, fr_w, fa_w = fbt * math.cos(awt), fbt * math.sin(awt), fbt * math.tan(bb)
    print(
        f"{name}: input-side torque {torque / 1000:.1f} N·m; alpha_t {math.degrees(at):.3f}, "
        f"alpha_wt {math.degrees(awt):.3f} deg"
    )
    print(f"  simple : Ft {ft_s:8.1f}  Fr {fr_s:8.1f}  Fa {fa_s:8.1f} N")
    print(f"  shifted: Ft {ft_w:8.1f}  Fr {fr_w:8.1f}  Fa {fa_w:8.1f} N")
    print(
        f"  change : Ft {100 * (ft_w / ft_s - 1):+.1f} %  Fr {100 * (fr_w / fr_s - 1):+.1f} %  "
        f"Fa {100 * (fa_w / fa_s - 1):+.1f} %"
    )
    # Check: the tangential force times the working pitch radius gives back the torque.
    rw1 = db1 / 2 / math.cos(awt)
    print(f"  check  : Ft x r_w = {ft_w * rw1 / 1000:.3f} N·m (torque {torque / 1000:.3f})")
    torque *= z2 / z1  # the next stage's pinion carries the wheel's torque
