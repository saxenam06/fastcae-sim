"""A height-field design's members in plan, against production's ribs (LOP-23, 11 October 17:58; the
engineer's 17 production pictures). Per half, from the run's own continuous heights
(`smooth_heights.column_heights`):
- coverage: the share of the shell's plan (the inside seen along the pull) under a member at least
  4 mm high;
- width: twice the distance to the member's edge, read on its centre-line (skeleton);
- height: the member's height off its base, on its centre-line.

`member_census.py <height-field run>` prints them (production's ribs: 4-6 mm thick, on about
10-25 % of a face)."""

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import smooth_heights as shh  # noqa: E402
import topo_free as tf  # noqa: E402
import json  # noqa: E402

RUN = sys.argv[1]
ch = shh.column_heights(RUN)
h = ch["h"]
rec = json.loads((shh.OUT / f"{RUN}.json").read_text(encoding="utf-8"))
skin = rec["skin"]["wall_mm"] if rec["skin"]["mass_share"] < 1.0 else None
model = tf.build_free(h, layout=rec.get("layout", tf.LAYOUT), band=rec.get("band_mm"), skin=skin, cavity=rec.get("cavity", "cup"),
                      route=rec.get("route", "split"), flange=bool(rec.get("flange")), mount_reach=rec.get("mount_reach") or "corridor",
                      height_field=rec["height_field"]["radius_mm"])  # fmt: skip
k_split = model["k_split"]
rooms = model["masks"]["rooms"]
for half, sl in (("motor_side", slice(0, k_split)), ("cover", slice(k_split, None))):
    m4 = ch[half]
    shell = np.asarray(rooms).reshape(tuple(model["n"]))[:, :, sl].any(axis=2)  # the inside's plan: the shell's footprint
    member = m4 >= 4.0
    # fine plan grid for widths (1 mm), the heights zoomed cubically as the drawing does
    z = h / 1.0
    big = ndi.zoom(m4, z, order=3)
    big_shell = ndi.zoom(shell.astype(float), z, order=1) > 0.5
    big_member = big >= 4.0
    dist = ndi.distance_transform_edt(big_member) * 1.0
    sk = skeletonize(big_member)
    widths = 2.0 * dist[sk]
    heights = big[sk]
    cov = (big_member & big_shell).sum() / max(big_shell.sum(), 1)
    over = (big_member & ~big_shell).sum() * 1.0 / 100.0  # cm² beyond the shell's footprint
    lab, nlab = ndi.label(big_member)
    print(f"{half}: shell footprint {big_shell.sum() / 100:.0f} cm²; members cover {100 * cov:.0f} % of it, "
          f"{over:.0f} cm² outside it; {nlab} separate members")
    for name, v in (("width", widths), ("height", heights)):
        q = np.percentile(v, [10, 50, 90])
        print(f"  {name} on the centre-lines: 10 % {q[0]:.0f} mm, median {q[1]:.0f}, 90 % {q[2]:.0f}, max {v.max():.0f}")
    hh = big[big_member & big_shell]
    print(f"  height over the shell's footprint: median {np.median(hh):.0f} mm, at the band (≥ 22 mm) {100 * (hh >= 22).mean():.0f} %")
