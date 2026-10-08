"""PROTOTYPE - not product code, not the judge.

Shared parameters for the first housing variant, plan Part C (Tasks 8-11) of
docs/features/contract/2026-10-08-plan-contract-v0-and-first-variant.md.

Every number here is labelled with where it came from:
- "rule of thumb"      a sizing habit, not a rating or a standard;
- "prototype choice"   a size picked tonight so the route can be seen working;
- "assumption A<n>"    an entry of the spec's assumptions list (spec section 4.8);
- "standard: ..."      a standard's clause (NADCA 2015 here).
PROVENANCE below repeats the labels in a form run.py copies into summary.json.
"""

from __future__ import annotations

import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "data" / "prototypes" / "first_variant"

# The stamp every derived value carries (plan Task 8: "stamped frontend-prototype version 0.1").
TOOL = "frontend-prototype"
TOOL_VERSION = "0.1"
DERIVED = f"derived: {TOOL} {TOOL_VERSION}"

# Provenance strings, used verbatim in derived.json and summary.json.
PUB_T2 = "published: Hofstetter 2018 Table 2"
PUB_T3 = "published: Hofstetter 2018 Table 3"
CATALOGUE = (
    "catalogue: ISO 15 dimension series as maker catalogues list it "
    "(to be checked against a maker's catalogue)"
)
ROT = "rule of thumb"
PROTO = "prototype choice"
NADCA = "standard: NADCA 2015 section 4A"
SPEC_D7 = "spec D7 (least member, the FE budget on this laptop)"
A1 = "assumption A1"
A3 = "assumption A3"
A4 = "assumption A4"
A5 = "assumption A5"
A7 = "assumption A7"
DENSITY_LABEL = "card from Kim et al. 2024 via the spec; prototype"

# ---------------------------------------------------------------- Task 8: layout
GEAR_GAP = 5.0  # mm: split face -> stage 1 -> stage 2 axial gaps (prototype choice, the brief)

# ---------------------------------------------------------------- Task 10: keep-outs
GEAR_RADIAL_CLEARANCE = 5.0  # mm over the tip cylinder (prototype choice, the brief)
GEAR_AXIAL_CLEARANCE = 3.0  # mm beyond each gear face (prototype choice, the brief)
SHAFT_DIAMETER_EXTRA = 3.0  # mm: shaft keep-out diameter = bearing bore + 3 mm (prototype choice)

# ---------------------------------------------------------------- Task 10: shell
SHELL_GAP = 5.0  # mm, gap g between the keep-out union and the shell (prototype choice)
SHELL_WALL = 5.0  # mm, wall t (prototype choice; above the 4 mm minimum wall)
MIN_WALL = 4.0  # mm (spec D7)
DRAFT_DEG = 2.0  # deg on inside and outside cast faces (NADCA 2015 4A asks >= 2 in, >= 1 out)
DRAFT_CHECK_DEG = 1.0  # deg: the draft map flags cast faces below this slope (the brief)
CAVITY_BLEND = 15.0  # mm, smooth-min radius rounding the outline's necks (prototype choice)
LIP_WIDTH = 10.0  # mm, sealing flange beyond the wall at the split face; it reaches the bolt
# boss centres and carries them (prototype choice)
LIP_HEIGHT = 8.0  # mm (prototype choice)

# ---------------------------------------------------------------- Task 10: structure
MEMBER_BLEND = 6.0  # mm, smooth-union blend radius (the brief)
BRIDGE_THICKNESS = 8.0  # mm at the back-wall face, tapering with the draft (prototype choice)
WEB_THICKNESS = 7.0  # mm (prototype choice)
RIB_THICKNESS = 6.0  # mm (prototype choice; members 6-8 mm, above the 4 mm minimum)
WEB_STANDOFF = 12.0  # mm, web height off the wall it runs along (prototype choice)
RIB_LENGTH = 35.0  # mm, radial reach of a seat-ring rib beyond the ring (prototype choice)
RIBS_PER_RING = 4  # (the brief: 3-4 per ring)
PROXY_UNDERSIZE = 0.3  # mm: the field's copy of a core feature sits inside the exact one

# ---------------------------------------------------------------- Task 10: grid
VOXEL = 1.5  # mm (the brief; coarsen to 2.0 if memory requires)
VOXEL_FALLBACK = 2.0
ENVELOPE_GROWTH = 20.0  # mm (assumption A3)
CHECK_VOXEL = 1.0  # mm, voxel of the thickness and void checks on the joined housing

# ---------------------------------------------------------------- Task 9: core
RING_WALL = 8.0  # mm radial wall of a seat ring, at its top (the brief)
SHOULDER = 4.0  # mm shoulder beyond the bearing (the brief)
MACHINING_STOCK = 0.25  # mm (NADCA 2015 "normal minimum machining allowance"); recorded only
BOSS_DIAMETER = 18.0  # mm (prototype choice, the brief)
BOSS_HOLE = 9.0  # mm, M8 clearance (prototype choice, the brief)
BOSS_HEIGHT = 12.0  # mm (prototype choice, the brief)
BOSS_MAX_PITCH = 80.0  # mm along the outline (prototype choice, the brief)
BOSS_BEYOND_WALL = 10.0  # mm: hole centre outside the wall's outer surface, so an M8 head or
# socket clears the wall (prototype choice; 5 mm left no room for the head)
BOLT_HEAD_CLEARANCE_R = 8.0  # mm radius kept free above each boss for the bolt head and washer
# (prototype choice; a field keep-out)
FLANGE_SPIGOT_D = 110.0  # mm, female pilot (prototype choice, the brief)
FLANGE_SPIGOT_DEPTH = 5.0  # mm (prototype choice)
FLANGE_BOLT_CIRCLE_D = 130.0  # mm (prototype choice, the brief)
FLANGE_BOLTS = 6  # (prototype choice, the brief)
FLANGE_HOLE = 9.0  # mm (prototype choice)
FLANGE_HOLE_DEPTH = 12.0  # mm, blind so it cannot reach the gear space (prototype choice)
FLANGE_OD = 150.0  # mm (prototype choice: holes on 130 with 5.5 mm edge distance)
FLANGE_POCKET_UNDERSIZE = 1.0  # mm: the cast pocket wall sits 1 mm inside the machined spigot,
# so the spigot is machined with a clear 1 mm shoulder rather than a 0.2 mm sliver (prototype)
PAD_HEIGHT_Z = 60.0  # mm along z (prototype choice, the brief: 60 x 40 x 12)
PAD_WIDTH_Y = 40.0  # mm along y
PAD_THICKNESS = 12.0  # mm along x
PAD_HOLE = 11.0  # mm (prototype choice, the brief)
PAD_HOLE_DEPTH = 9.0  # mm, blind (prototype choice)
PAD_HOLE_PITCH = 36.0  # mm between the two holes, along z (prototype choice)
PAD_CENTRE_Z = 55.0  # mm (prototype choice: mid-depth of the main housing)
PAD_PROUD = 8.0  # mm, pad face beyond the drafted wall at the pad's lower edge (prototype choice)
CUT_OVERSIZE = 0.02  # mm: machining cutters sit just outside the core's exact faces, in radius
# and in depth, so no cutter face is coplanar with a core face (modelling tolerance)

# ---------------------------------------------------------------- Task 11
DENSITY_KG_PER_MM3 = 2.66e-6  # 2.66 g/cm3 (card from Kim et al. 2024 via the spec; prototype)


def tan_draft() -> float:
    return math.tan(math.radians(DRAFT_DEG))


PROVENANCE = {
    "gear stations: 5 mm gaps split face -> stage 1 -> stage 2": PROTO,
    "keep-out: gear tip + 5 mm radial, 3 mm axial": PROTO,
    "keep-out: shaft = bearing bore + 3 mm (diameter), between its seats": PROTO,
    "keep-out: the bearings' own volumes": PROTO,
    "shell gap 5 mm, wall 5 mm (min wall 4 mm, D7)": PROTO,
    "draft 2 deg on inside and outside cast faces": NADCA,
    "draft map threshold 1 deg": PROTO,
    "cavity outline necks rounded with a 15 mm smooth-min": PROTO,
    "sealing lip 10 mm wide, 8 mm tall at the split face": PROTO,
    "bolt hole centres 10 mm outside the wall; r 8 mm head clearance kept free": PROTO,
    "member blend radius 6 mm": PROTO,
    "member thickness: bridges 8, webs 7, ribs 6 mm (tapering with the draft)": PROTO,
    "web standoff 12 mm; ring ribs reach 35 mm; 4 ribs per ring": PROTO,
    "voxel 1.5 mm (field), 1.0 mm (thickness and void checks)": PROTO,
    "installation space = layout envelope grown by 20 mm": A3,
    "seat ring wall 8 mm, shoulder 4 mm": PROTO,
    "machining stock 0.25 mm (recorded, not modelled in the mesh)": "standard: NADCA 2015",
    "bolt bosses d18 / hole d9 (M8) / 12 mm tall / <= 80 mm apart along the outline": PROTO,
    "motor flange: spigot d110 x 5, 6 x d9 x 12 deep on d130, OD 150": PROTO,
    "mount pad 60 x 40 x 12 mm, 2 x d11 x 9 deep, on the +x end wall": PROTO + " / " + A4,
    "pull direction +z, normal to the split face": A7,
    "density 2.66 g/cm3": DENSITY_LABEL,
}
