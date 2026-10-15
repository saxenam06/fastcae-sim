"""PROTOTYPE (LOP-9) - the housing in the trade's grammar, castable by construction.

The engineer's 36 pictures of production housings (9 October 12:48) share one grammar; the study
`docs/research/2026-10-09-production-housings-against-ours.md` sets it out with its sources. This
builder draws it, in the trade's order, for the completed contract's gear train (the AVL family's):

1. **one silhouette:** the exact convex hull of the gear rooms' circles grown by the wall, in arcs
   and tangent lines (never a polygon, which left hairline faces on the bosses' cylinders); where
   the motor bolts to the housing, the input's circle grown to hold the motor's ring, so that
   nothing overhangs the split flange;
2. **one shell of one thickness per half,** drawn along the half's pull direction with a draft, its
   corners filleted (R = T inside, R + T outside, NADCA G-6-2):
   - the motor side a cup down to one flat motor face;
   - the cover a drum over the second stage, and a bridge over its two bearings;
3. **bearing bosses of 1.25·D + 10 mm** (ITMO 2014), their outer faces standing 0.5·δ proud;
4. **the split flange:** a lip, with Ø20 bolt bosses on it at an even pitch (the process's joint
   rules, `manufacturing.joint`, where the contract gives them);
5. **the mounts:** the contract's (A20), each a boss along the shafts over its own length with its
   bolt's hole, tied to the outside wall from the side by a web (or merged with the wall where it
   touches it), its bracket's room beyond both faces kept empty; a contract without mounts gets
   the grammar's own, as columns from the motor face up to the flange;
6. **the motor's ring** (A25), with a wheel of spokes inside it, only where the contract has the
   motor on the housing (`motor_on_housing`); otherwise the input's seal has a boss of its own;
7. **ribs between hard points only:**
   - each rib keeps a constant height off the housing's outside;
   - it runs over the end face, round the filleted corner and down the side wall to a bolt boss;
   - or it runs from boss to boss, or from a mount to its nearest boss;
   - every rib is 0.8·δ thick, and low under the motor's flange face (where there is one);
   - none enters a mount's bracket room or a half-shaft's joint room;
8. **the shafts' exits kept clear:** each seal's bore, and beyond the output's ends the half-shafts'
   joints (A27), as `zenryx.domains.gearbox.spaces` gives them;
9. **everything drawn along the pull,** so that both halves come out of their moulds
   (`castable.py` proves it).

Run: uv run python prototypes/first_loop/grammar.py [stem]
Writes data/first_loop/<stem>_<half>.step and .brep, and <stem>.json, as lobed.py does, for fe.py.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import ribrules as rr  # noqa: E402  (LOP-15: fastcae's rules for clean ribs)
import shell as convex  # noqa: E402  (the contract's path, the shared settings, the face names)
from lobed import HEAL_MM, _surface_meshes  # noqa: E402  (the proven heal's limit and its mesh test)
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.domains.gearbox.spaces import spaces as contract_spaces  # noqa: E402  (the contract's fixed volumes)
from zenryx.geometry.solids import cylinder, fuse  # noqa: E402

OUT = ROOT / "data" / "first_loop"
# The settings of the motor's flange (A25): left out of a design whose motor the vehicle holds, so
# that fe.py applies no motor region and no motor torque (as `contract_layout.py` leaves them out).
MOTOR_KEYS = ("motor_ring", "motor_bolt_circle", "motor_bolts", "motor_ring_thickness", "motor_room", "motor_clear", "spokes_motor")

# The grammar's own values, each with where it comes from (the study, section 5.4). The rest
# (bolts, mounts, the motor's interface, seals, density) are shell.py's SETTINGS.
GRAMMAR = {
    "wall": 6.0,  # mm, one thickness everywhere: ribs, never thick walls (ITMO 2014); least 4 (D7)
    "draft": 1.5,  # deg, outside and inside alike, so the wall keeps its thickness (2° NNGASU 2010)
    "corner_in": 6.0,  # mm: an L-corner's inside radius R = T (NADCA 2021, G-6-2)
    "corner_out": 12.0,  # mm: its outside radius R + T (NADCA 2021, G-6-2)
    "rib": 5.0,  # mm: 0.8 × the wall (ITMO 2014; NNGASU 2010; Giesserei-Lexikon)
    "rib_height": 15.0,  # mm off an end face
    "rib_side": 10.0,  # mm off a side wall: lower there, as the trade's side ribs are
    "rib_low": 10.0,  # mm: the most a rib stands under the motor's flange face (its ring is 12)
    "motor_room": 104.0,  # mm: the motor's radius (Ø204, the spaces review) plus 2 mm
    "boss_k": 1.25,  # a bearing boss's outside Ø = 1.25·D + 10 mm (ITMO 2014; NPTEL 1.2-1.5·D)
    "boss_c": 10.0,
    "proud": 3.0,  # mm: boss faces stand 0.5·δ proud of their wall (ITMO 2014)
    "lip": 8.0,  # mm: the flange's sealing band beyond the outside wall
    "bolt_pitch": 80.0,  # mm, about 10·d for M8 (Henkel's FIPG guide; Dunaev ≈ 10·d)
    "bolt_boss": 20.0,  # mm: a bolt boss's Ø for M8 (2.5·d)
    "spokes_motor": 8,  # spokes of the wheel inside the motor's ring
    "motor_clear": 3.0,  # mm: the input's circle beyond the motor's ring, so it never overhangs
    "boss": 15.0,  # mm: the bosses' mean radial wall, for fe.py's region map (diagnostics only)
}


# The recipe (LOP-12): the choices a designer makes, which the agent will make. Each has a small
# vocabulary; a style preset is one set of values (every-style note, section 3). Patterns that
# would run across the pull on a side wall (ZF's crossed ribs, Avtec's level ribs) are put on the
# end faces instead, where they come out of the mould: the style adapts to the process.
RECIPE = {
    "outline": {"family": "hull"},  # "hull"; "lobed" with a "blend" radius (each gear's drum shows);
    #                                 "box" with a "corner" radius (a rounded box round them all)
    "levels": "flat",  # the motor side: "flat" (one face, the deepest stack's end), or "drums" (a
    #                    base at the shallowest, a drum per deeper shaft to its own end)
    "cover": "bridge",  # "bridge": a drum over stage 2 and a bridge over its bearings; "towers": a
    #                     tower per bearing; "flat": one deep face
    "spokes": "nearest",  # ribs from bosses to the walls under the bolts: "nearest", "two" (a truss), "none"
    "delta": True,  # ribs boss to boss along the lines of centres
    "ears": True,  # a rib from each mount to its nearest boss
    "wheel": {"spokes": 8, "ring": False},  # inside the motor's ring; ring: an inner ring halfway out
    "pattern": None,  # on the end faces' flat parts: {"kind": "lines", "angles": [deg], "pitch": mm}
    #                   or {"kind": "fan", "around": [shaft], "count": n, "bend": deg}
    "rim": False,  # a rib round the end faces' flat parts, for a pattern's ribs to end on
    "motor_ring": "plain",  # "plain", or "scalloped": a boss round each of its bolts
}

# The six families of the engineer's 36 pictures (the study, section 2), as recipes: the massing
# (outline, levels, cover) first, then the ribs; "settings" overrides the grammar's sizes.
PRESETS = {
    "avl": {"outline": {"family": "hull"}, "levels": "flat", "cover": "bridge",
            "spokes": "two", "delta": True, "ears": True, "wheel": {"spokes": 8, "ring": False}},
    "batom": {"outline": {"family": "hull"}, "levels": "drums", "cover": "towers",
              "spokes": "nearest", "delta": False, "wheel": {"spokes": 12, "ring": True},
              "settings": {"rib_height": 20.0}},
    "kalyani": {"outline": {"family": "lobed", "blend": 45.0}, "levels": "drums", "cover": "bridge",
                "spokes": "none", "delta": False, "rim": True, "motor_ring": "scalloped",
                "pattern": {"kind": "fan", "around": ["output", "intermediate"], "count": 12, "bend": 40},
                "settings": {"rib_height": 22.0, "rib": 6.0}},
    "zf": {"outline": {"family": "lobed", "blend": 30.0}, "levels": "drums", "cover": "towers",
           "spokes": "none", "rim": True,
           "pattern": {"kind": "lines", "angles": [45, -45], "pitch": 60},
           "settings": {"rib_height": 26.0, "rib": 6.0, "side_pitch": 34.0, "rib_side": 12.0}},
    "avtec": {"outline": {"family": "box", "corner": 50.0}, "levels": "flat", "cover": "flat",
              "spokes": "none", "delta": False, "rim": True,
              "pattern": {"kind": "lines", "angles": [0, 90], "pitch": 48},
              "settings": {"rib_height": 18.0, "side_pitch": 40.0}},
    # The ribs where an optimisation's field put them (LOP-16), on Kalyani's massing.
    "field": {"outline": {"family": "lobed", "blend": 45.0}, "levels": "drums", "cover": "bridge",
              "spokes": "none", "delta": False, "ears": True, "rim": False, "motor_ring": "scalloped",
              "pattern": {"kind": "field", "run": "topofree_misalignment_7.73kg_6mm_projected"},
              "settings": {"rib_height": 22.0, "rib": 6.0}},
    # Stage 2's ribs (the band 30 mm off the skin, LOP-16 run 3), on the same massing.
    "field_band": {"outline": {"family": "lobed", "blend": 45.0}, "levels": "drums", "cover": "bridge",
                   "spokes": "none", "delta": False, "ears": True, "rim": False, "motor_ring": "scalloped",
                   "pattern": {"kind": "field", "run": "topofree_misalignment_7.73kg_5mm_projected_band30"},
                   "settings": {"rib_height": 22.0, "rib": 6.0}},
    "punch": {"outline": {"family": "lobed", "blend": 90.0}, "levels": "drums", "cover": "bridge",
              "spokes": "none", "delta": False, "ears": True, "rim": False,
              "pattern": {"kind": "fan", "around": ["intermediate", "output"], "count": 5, "bend": 85},
              "settings": {"rib_height": 12.0, "rib_side": 6.0}},
}  # fmt: skip


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


# --- the silhouette: the exact convex hull of circles ------------------------------------------


def hull_runs(circles):
    """The circles on the convex hull of circles (x, y, r), anticlockwise, each with the angles of
    its outward normal where its arc starts and ends. Found by the support function sampled every
    0.1°, then each switch solved exactly: (c_b - c_a)·n = r_a - r_b."""
    n = 3600
    owner = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ux, uy = math.cos(a), math.sin(a)
        owner.append(max(range(len(circles)), key=lambda j: circles[j][0] * ux + circles[j][1] * uy + circles[j][2]))
    start = next((k for k in range(n) if owner[k] != owner[k - 1]), None)
    if start is None:
        return [(owner[0], 0.0, 2 * math.pi)]
    seq = owner[start:] + owner[:start]
    runs, k0 = [], 0
    for k in range(1, n + 1):
        if k == n or seq[k] != seq[k0]:
            runs.append((seq[k0], (start + k) % n))  # its circle, and the next run's first sample
            k0 = k
    switch = []
    for i, (a_idx, k_next) in enumerate(runs):
        b_idx = runs[(i + 1) % len(runs)][0]
        guess = 2 * math.pi * (k_next - 0.5) / n
        (xa, ya, ra), (xb, yb, rb) = circles[a_idx], circles[b_idx]
        length = math.hypot(xb - xa, yb - ya)
        phi = math.atan2(yb - ya, xb - xa)
        c = max(-1.0, min(1.0, (ra - rb) / length))
        roots = (phi + math.acos(c), phi - math.acos(c))
        switch.append(min(roots, key=lambda r: abs(math.remainder(r - guess, 2 * math.pi))))
    return [(runs[i][0], switch[i - 1], switch[i]) for i in range(len(runs))]


def hull_wire(circles, z: float) -> cq.Wire:
    """The hull as one wire at height z: an arc on every circle that reaches it, a tangent line
    from each to the next."""
    runs = hull_runs(circles)
    if len(runs) == 1:
        x, y, r = circles[runs[0][0]]
        return cq.Wire.makeCircle(r, cq.Vector(x, y, z), cq.Vector(0, 0, 1))
    edges = []
    for i, (j, a0, a1) in enumerate(runs):
        x, y, r = circles[j]
        while a1 <= a0:
            a1 += 2 * math.pi

        def p(a, x=x, y=y, r=r):
            return cq.Vector(x + r * math.cos(a), y + r * math.sin(a), z)

        edges.append(cq.Edge.makeThreePointArc(p(a0), p(0.5 * (a0 + a1)), p(a1)))
        xn, yn, rn = circles[runs[(i + 1) % len(runs)][0]]
        q = cq.Vector(xn + rn * math.cos(a1), yn + rn * math.sin(a1), z)
        if (q - p(a1)).Length > 1e-6:
            edges.append(cq.Edge.makeLine(p(a1), q))
    return cq.Wire.assembleEdges(edges)


def lobed_wire(circles, z: float, blend: float, keep=None) -> cq.Wire:
    """The circles joined as lobes, so each gear's drum shows: each circle's arc, and between
    neighbours on the hull a concave arc of radius `blend` touching both (the closing of their
    union by a disc of that radius); a tangent line where two lie too far apart for it. `keep`
    (one per neighbour pair) carries the base outline's decisions to its offsets."""
    runs, centres = blend_centres(circles, blend, keep)
    if len(runs) == 1:
        return hull_wire(circles, z)
    m = len(runs)
    edges = []
    for i in range(m):
        j = runs[i][0]
        x, y, r = circles[j]
        before, after = centres[i - 1], centres[i]
        a0 = math.atan2(before[1] - y, before[0] - x) if before else runs[i][1]
        a1 = math.atan2(after[1] - y, after[0] - x) if after else runs[i][2]
        while a1 <= a0:
            a1 += 2 * math.pi

        def p(a, x=x, y=y, r=r):
            return cq.Vector(x + r * math.cos(a), y + r * math.sin(a), z)

        edges.append(cq.Edge.makeThreePointArc(p(a0), p(0.5 * (a0 + a1)), p(a1)))
        xn, yn, rn = circles[runs[(i + 1) % m][0]]
        if after:
            an = math.atan2(after[1] - yn, after[0] - xn)
            ta, tb = p(a1), cq.Vector(xn + rn * math.cos(an), yn + rn * math.sin(an), z)
            ux, uy = 0.5 * (ta.x + tb.x) - after[0], 0.5 * (ta.y + tb.y) - after[1]
            length = math.hypot(ux, uy)
            mid = cq.Vector(after[0] + blend * ux / length, after[1] + blend * uy / length, z)
            edges.append(cq.Edge.makeThreePointArc(ta, mid, tb))
        else:
            q = cq.Vector(xn + rn * math.cos(a1), yn + rn * math.sin(a1), z)
            if (q - p(a1)).Length > 1e-6:
                edges.append(cq.Edge.makeLine(p(a1), q))
    return cq.Wire.assembleEdges(edges)


def blend_centres(circles, blend: float, keep=None):
    """The hull's runs, and for each neighbour pair its blend circle's centre, or None for a
    tangent line. Decided on the base outline (a blend must stay clear of every other circle) and
    carried to the offsets by `keep`: decided afresh at each offset, the outside could take a
    waist where the cavity took a line, and the wall there became a pocket (Punch's, 20:46)."""
    runs = hull_runs(circles)
    if len(runs) == 1:
        return runs, [None]
    m = len(runs)
    centres = []  # each neighbour pair's blend circle's centre, or None
    for i in range(m):
        ja, a1 = runs[i][0], runs[i][2]
        jb = runs[(i + 1) % m][0]
        (xa, ya, ra), (xb, yb, rb) = circles[ja], circles[jb]
        d = math.hypot(xb - xa, yb - ya)
        big_a, big_b = ra + blend, rb + blend
        if d >= big_a + big_b or d <= abs(big_a - big_b):
            centres.append(None)
            continue
        along = (big_a * big_a - big_b * big_b + d * d) / (2 * d)
        off = math.sqrt(max(big_a * big_a - along * along, 0.0))
        ex, ey = (xb - xa) / d, (yb - ya) / d
        mx, my = xa + along * ex, ya + along * ey
        nx, ny = math.cos(a1), math.sin(a1)  # the hull's outward normal there
        centre = max(((mx - off * ey, my + off * ex), (mx + off * ey, my - off * ex)), key=lambda q: (q[0] - mx) * nx + (q[1] - my) * ny)
        # Only where the blend stays clear of every other circle: between two circles far apart
        # a large blend swings inward through a third (the input and the sump through the output's
        # gear, 20:27), and the outline crosses itself; a tangent line joins them instead.
        if keep is None:
            clear = all(math.dist(centre, (xk, yk)) >= rk + blend - 1e-6 for k, (xk, yk, rk) in enumerate(circles) if k not in (ja, jb))
        else:
            clear = keep[i]
        centres.append(centre if clear else None)
    return runs, centres


class Outline:
    """A silhouette made of circles. "hull" joins neighbours by tangent lines; "lobed" by concave
    arcs of radius `blend`, each gear's drum showing. A box is a hull of four corner circles
    (`box_of`). Growing it by d grows the circles and shrinks the blends, as an offset does, and
    keeps the base outline's decision of which waists are blended (`keep`)."""

    def __init__(self, circles, family: str = "hull", blend: float = 60.0, keep=None):
        self.circles, self.family, self.blend = [tuple(c) for c in circles], family, blend
        if family == "lobed" and keep is None:
            keep = [c is not None for c in blend_centres(self.circles, blend)[1]]
        self.keep = keep

    def grow(self, d: float) -> "Outline":
        return Outline(grown(self.circles, d), self.family, max(self.blend - d, 4.0), self.keep)

    def wire(self, z: float) -> cq.Wire:
        return lobed_wire(self.circles, z, self.blend, self.keep) if self.family == "lobed" else hull_wire(self.circles, z)

    def points(self, step: float = 2.0) -> list[tuple[float, float]]:
        w = self.wire(0.0)
        n = max(64, int(w.Length() / step))
        return [(w.positionAt(k / n).x, w.positionAt(k / n).y) for k in range(n)]


def box_of(circles, corner: float):
    """Four corner circles of radius `corner` whose hull is a rounded box round all the circles."""
    x0, x1 = min(x - r for x, _, r in circles) + corner, max(x + r for x, _, r in circles) - corner
    y0, y1 = min(y - r for _, y, r in circles) + corner, max(y + r for _, y, r in circles) - corner
    return [(x0, y0, corner), (x1, y0, corner), (x1, y1, corner), (x0, y1, corner)]


def hull_points(circles, step: float = 2.0) -> list[tuple[float, float]]:
    """The hull as a polygon, a point every `step` mm: for tests and pictures, never for CAD."""
    w = hull_wire(circles, 0.0)
    n = max(64, int(w.Length() / step))
    return [(w.positionAt(k / n).x, w.positionAt(k / n).y) for k in range(n)]


def grown(circles, by: float):
    return [(x, y, r + by) for x, y, r in circles]


def drafted(circles, z0: float, z1: float, draft: float, fillet: float = 0.0) -> cq.Shape:
    """The hull of `circles` (or an Outline) drawn from z0 to z1, narrowing towards z1 by the
    draft (deg), the edges of its far face filleted."""
    wire = circles.wire(z0) if isinstance(circles, Outline) else hull_wire(circles, z0)
    plane = cq.Plane(origin=(0, 0, z0), xDir=(1, 0, 0), normal=(0, 0, 1 if z1 > z0 else -1))
    solid = cq.Workplane(plane).add(wire).toPending().extrude(abs(z1 - z0), taper=draft).val()
    if fillet > 0:
        far = [e for e in solid.Edges() if abs(e.BoundingBox().zmin - z1) < 1e-3 and abs(e.BoundingBox().zmax - z1) < 1e-3]
        solid = solid.fillet(fillet, far)
    return solid


def round_steps(solid: cq.Shape, z: float, drums, s) -> cq.Shape:
    """A stepped motor side's base face rounded: its outside edge by `corner_out`, the foot of
    each drum standing out of it by `corner_in`. Cosmetic: a fillet OCC refuses is left sharp,
    and the casting does not mind."""
    edges = [e for e in solid.Edges() if abs(e.BoundingBox().zmin - z) < 1e-3 and abs(e.BoundingBox().zmax - z) < 1e-3]

    def at_drum(e):
        c = e.positionAt(0.5)
        return any(abs(math.dist((c.x, c.y), (x, y)) - r) < 1.0 for x, y, r in drums)

    for radius, picked in ((s["corner_in"], [e for e in edges if at_drum(e)]), (s["corner_out"], [e for e in edges if not at_drum(e)])):
        if not picked:
            continue
        try:
            out = solid.fillet(radius, picked)
        except Exception as error:  # noqa: BLE001 - OCC's refusal leaves the step sharp
            say(f"  a step left sharp ({type(error).__name__})")
            continue
        # Kept only if the solid stays one valid solid of about its volume: a fillet OCC made but
        # left corrupt broke the later cavity cut into seven pieces (Punch's, 20:28).
        if out.isValid() and len(out.Solids()) == 1 and abs(out.Volume() - solid.Volume()) < 0.03 * solid.Volume():
            probe = out.cut(cylinder((0.0, 0.0), z - 1.0, z + 1.0, 1.0e4))
            if not probe.wrapped.IsNull() and probe.isValid():
                solid = out
                continue
        say("  a step left sharp (its fillet came out corrupt)")
    return solid


# --- features --------------------------------------------------------------------------------


def standing(centre, z_face: float, s: int, radius: float, height: float, sunk: float = 1.0) -> cq.Shape:
    """A round boss standing `height` off a face at z_face, outward along s (+1 or -1), sunk into
    the wall so that the fuse is clean."""
    z0, z1 = (z_face - sunk, z_face + height) if s > 0 else (z_face - height, z_face + sunk)
    return cylinder(centre, z0, z1, 2 * radius)


def strip(a, b, width: float, z0: float, z1: float) -> cq.Shape:
    """A plate of `width` along the path a-b, from z0 to z1: a rib's footprint."""
    (ax, ay), (bx, by) = a, b
    length = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / length * width / 2, (bx - ax) / length * width / 2
    poly = [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)]
    return cq.Workplane("XY", origin=(0, 0, z0)).polyline(poly).close().extrude(z1 - z0).val(), poly


def strip_along(points, width: float, z0: float, z1: float):
    """A plate of `width` along a polyline (a curved rib), from z0 to z1."""
    left, right = [], []
    for i, (x, y) in enumerate(points):
        (xa, ya), (xb, yb) = points[max(i - 1, 0)], points[min(i + 1, len(points) - 1)]
        length = math.hypot(xb - xa, yb - ya)
        nx, ny = -(yb - ya) / length * width / 2, (xb - xa) / length * width / 2
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    poly = left + right[::-1]
    return cq.Workplane("XY", origin=(0, 0, z0)).polyline(poly).close().extrude(z1 - z0).val(), poly


def spline_strip(points, width: float, z0: float, z1: float) -> cq.Shape:
    """A curved rib's footprint with smooth sides, a spline each side offset by width/2, from z0
    to z1: 8 edges where a polyline's has one per station, and so no lap faces (21:30)."""
    left, right = [], []
    for i, (x, y) in enumerate(points):
        (xa, ya), (xb, yb) = points[max(i - 1, 0)], points[min(i + 1, len(points) - 1)]
        length = math.hypot(xb - xa, yb - ya)
        nx, ny = -(yb - ya) / length * width / 2, (xb - xa) / length * width / 2
        left.append(cq.Vector(x + nx, y + ny, z0))
        right.append(cq.Vector(x - nx, y - ny, z0))
    edges = [cq.Edge.makeSpline(left), cq.Edge.makeLine(left[-1], right[-1]), cq.Edge.makeSpline(right[::-1]), cq.Edge.makeLine(right[0], left[0])]
    face = cq.Face.makeFromWires(cq.Wire.assembleEdges(edges))
    return cq.Solid.extrudeLinear(face, cq.Vector(0, 0, z1 - z0))


def pill_wire(origin: cq.Vector, tangent: cq.Vector, up: cq.Vector, width: float, height: float, sink: float = 1.0) -> cq.Wire:
    """A rib's section in the plane square to `tangent` at `origin`: `width` across, from `sink`
    under the surface to `height` off it along `up`, its top a semicircle of half the width (a
    full round, drawn: no fillet is built after, LOP-15)."""
    t = tangent.normalized()
    u = up.normalized()
    b = t.cross(u).normalized()
    r = width / 2

    def p(a, v):
        return origin + b * a + u * v

    return cq.Wire.assembleEdges([
        cq.Edge.makeLine(p(-r, -sink), p(r, -sink)),
        cq.Edge.makeLine(p(r, -sink), p(r, height - r)),
        cq.Edge.makeThreePointArc(p(r, height - r), p(0, height), p(-r, height - r)),
        cq.Edge.makeLine(p(-r, height - r), p(-r, -sink)),
    ])  # fmt: skip


def _pill_sweep(edges, up: cq.Vector, width: float, height: float, planar_binormal: bool = False) -> cq.Shape:
    """The pill section swept along the path; the corrected Frenet frame keeps its top off the
    surface round the corner (22:50). A straight run leaves that frame undefined, and OCC's sweep
    fails, or crashes the process: a spoke from a boss round the same centre as the wall it climbs
    (10 of contract_avl's 21 ribs, 19:38-19:42). With `planar_binormal` a path that lies in one
    plane is swept with the binormal held square to that plane, which gives the same section, and
    the corrected Frenet frame is used only for the others."""
    path = cq.Wire.assembleEdges(edges)
    profile = pill_wire(path.startPoint(), path.tangentAt(0), up, width, height)
    if planar_binormal:
        pts = np.array([[p.x, p.y, p.z] for p in (path.positionAt(t) for t in np.linspace(0.0, 1.0, 41))])
        _, _, axes = np.linalg.svd(pts - pts.mean(axis=0))
        if np.abs((pts - pts.mean(axis=0)) @ axes[-1]).max() < 0.05:
            from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
            from OCP.gp import gp_Dir

            builder = BRepOffsetAPI_MakePipeShell(path.wrapped)
            builder.SetMode(gp_Dir(*axes[-1]))
            builder.Add(profile.wrapped, False, False)
            builder.Build()
            if not builder.IsDone():
                raise ValueError("the sweep in its plane failed")
            builder.MakeSolid()
            return cq.Shape.cast(builder.Shape())
    return cq.Solid.sweep(profile, [], path, makeSolid=True, isFrenet=False)


def _face_edges(pts, z_f: float, end_tangent=None):
    vs = [cq.Vector(float(x), float(y), z_f) for x, y in pts]
    if len(vs) == 2:
        return [cq.Edge.makeLine(vs[0], vs[1])]
    start = (vs[1] - vs[0]).normalized()
    end = end_tangent if end_tangent is not None else (vs[-1] - vs[-2]).normalized()
    return [cq.Edge.makeSpline(vs, tangents=[start, end])]


def face_rib(pts, z_f: float, up: float, width: float, height: float, planar_binormal: bool = False) -> cq.Shape:
    """A rib on a flat end face at z_f, standing `height` off it along `up` (+1 or -1)."""
    return _pill_sweep(_face_edges(pts, z_f), cq.Vector(0, 0, up), width, height, planar_binormal)


def chain_rib(pts, z_f: float, up: float, n, width: float, height: float, z_split: float, draft: float, corner: float, flange: float,
              planar_binormal: bool = False) -> cq.Shape:  # fmt: skip
    """A rib over its end face, round the corner's fillet (tangent to the face and to the drafted
    wall) and down the wall into the flange's lip, 2 mm deep: one sweep, no joint. `pts` end where
    the round begins, arriving square to the wall along `n`. Stopped 10 mm down the wall, each
    rib's end left the wall above it and the lip under it in its shadow: 23 cm² of undercut on
    Kalyani's motor side, 11 on its cover (23:02)."""
    d = math.radians(draft)
    v = -up  # from the face towards the split
    nn = cq.Vector(n[0], n[1], 0).normalized()
    z = cq.Vector(0, 0, 1)
    c0 = cq.Vector(float(pts[-1][0]), float(pts[-1][1]), z_f)
    centre = c0 + z * (v * corner)
    r_end = nn * math.cos(d) - z * (v * math.sin(d))
    a1 = centre + r_end * corner
    mid = centre + (z * (-v) + r_end).normalized() * corner
    w_dir = (nn * math.sin(d) + z * (v * math.cos(d))).normalized()
    z_lip = z_split + up * (flange - 2.0)  # 2 mm into the lip's face
    run = abs(z_lip - a1.z) / math.cos(d)
    edges = _face_edges(pts, z_f, end_tangent=nn) + [cq.Edge.makeThreePointArc(c0, mid, a1), cq.Edge.makeLine(a1, a1 + w_dir * run)]
    return _pill_sweep(edges, z * up, width, height, planar_binormal)


def ring_pill(pts, z_f: float, up: float, width: float, height: float) -> cq.Shape:
    """A closed ring rib with a full-round top, round the circle the points lie on."""
    pts = np.asarray(pts, float)
    centre = pts[:-1].mean(axis=0)
    radius = float(np.linalg.norm(pts[0] - centre))
    circle = cq.Edge.makeCircle(radius, cq.Vector(centre[0], centre[1], z_f), cq.Vector(0, 0, 1))
    return _pill_sweep([circle], cq.Vector(0, 0, up), width, height)


def fit_picture(stem: str, plan, offered: list, kept: list, outline) -> None:
    """The field's plan on each end face with the ribs read on it: kept in red, offered on the
    metal but refused in grey (data/first_loop/<stem>_fit.png)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs, ys, pitch = plan["xs"], plan["ys"], float(plan["h"])
    names = {r.name for r in kept}
    wall = np.array(outline.points(4.0) + outline.points(4.0)[:1])
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    for ax, (face, key, title) in zip(axes, (("hi", "cover_beyond", "Cover"), ("lo", "motor_side_beyond", "Motor side")), strict=True):
        m = plan[key]
        extent = (xs[0] - pitch / 2, xs[-1] + pitch / 2, ys[0] - pitch / 2, ys[-1] + pitch / 2)
        image = ax.imshow(np.where(m > 0, m, np.nan).T, origin="lower", cmap="viridis", extent=extent)
        ax.plot(wall[:, 0], wall[:, 1], color="0.35", lw=1.0)
        for o in offered:
            if o["face"] == face and o["share"] >= 0.5 and o["name"] not in names:
                ax.plot(o["points"][:, 0], o["points"][:, 1], color="0.55", lw=0.6)
        for r in kept:
            if r.face == face:
                ax.plot(r.points[:, 0], r.points[:, 1], color="red", lw=2.2)
        ax.set_title(f"{title}: the field's metal past the skin (mm); ribs kept red ({sum(r.face == face for r in kept)}), refused grey", fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlabel("x, mm")
        ax.set_ylabel("y, mm")
        fig.colorbar(image, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(OUT / f"{stem}_fit.png", dpi=110)
    plt.close(fig)


def along_wire(circles, pitch: float, z: float = 0.0):
    """Points spaced evenly at about `pitch` round the hull (or an Outline), each with its
    outward normal."""
    w = circles.wire(z) if isinstance(circles, Outline) else hull_wire(circles, z)
    n = max(4, math.ceil(w.Length() / pitch))
    out = []
    for k in range(n):
        t = (k + 0.5) / n
        p, d = w.positionAt(t), w.tangentAt(t)
        out.append(((p.x, p.y), (d.y, -d.x)))  # anticlockwise: the outward normal is to the right
    return out


def _inside(poly, p) -> bool:
    """Whether p lies inside the closed polygon `poly` (the even-odd rule)."""
    x_, y_ = p
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, list(poly[1:]) + list(poly[:1]), strict=True):
        if (y1 > y_) != (y2 > y_) and x_ < (x2 - x1) * (y_ - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def path_distance(pts, c) -> float:
    """The least distance from the point c to the polyline `pts`."""
    p, c = np.asarray(pts, float), np.asarray(c, float)
    if len(p) == 1:
        return float(np.linalg.norm(p[0] - c))
    a, ab = p[:-1], np.diff(p, axis=0)
    t = np.clip(np.einsum("ij,ij->i", c - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0.0, 1.0)
    return float(np.min(np.linalg.norm(a + t[:, None] * ab - c, axis=1)))


def signed_gap(poly, p) -> float:
    """p's distance from the closed polygon `poly`: positive outside it, negative inside."""
    d = path_distance(list(poly) + [poly[0]], p)
    return -d if _inside(poly, p) else d


def nearest_on(outline: Outline, p, step: float = 0.25):
    """The point of the outline (in plan) nearest to p, the outline's outward normal there, and p's
    signed distance from it (positive outside)."""
    w = outline.wire(0.0)
    n = max(400, int(w.Length() / step))
    best = None
    for k in range(n):
        q = w.positionAt(k / n)
        d = math.hypot(q.x - p[0], q.y - p[1])
        if best is None or d < best[0]:
            best = (d, k / n, np.array([q.x, q.y]))
    d, t, q = best
    tg = w.tangentAt(t)
    normal = np.array([tg.y, -tg.x]) / max(math.hypot(tg.x, tg.y), 1e-12)  # anticlockwise: outward to the right
    return q, normal, (d if float((np.asarray(p, float) - q) @ normal) > 0 else -d)


def bolt_stations(wire: cq.Wire, pitch: float, avoid) -> tuple[list[float], list[float]]:
    """The bolts' places along the bolt line `wire`, as shares of its length, at most `pitch` apart
    and none inside a keep-out circle ((x, y), radius) of `avoid`: a bolt each side of every
    keep-out, as near as it allows, and evenly in between. Also the gaps (mm) across a keep-out
    wider than `pitch` (none while the joint's rule holds)."""
    length = wire.Length()
    n = max(720, int(length / 0.25))
    pts = np.array([(v.x, v.y) for v in (wire.positionAt(k / n) for k in range(n))])
    free = np.ones(n, bool)
    for (cx, cy), r in avoid:
        free &= np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) >= r
    if free.all():
        k = math.ceil(length / pitch)
        return [(i + 0.5) / k for i in range(k)], []
    first = int(np.argmin(free))  # a blocked sample: the free runs start after it
    runs, run = [], []
    for i in ((first + j) % n for j in range(n)):
        if free[i]:
            run.append(i)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    stations = []
    for run in runs:
        span = (len(run) - 1) / n * length
        m = math.ceil(span / pitch - 1e-9) if span > 1e-9 else 0
        stations += [((run[0] + (len(run) - 1) * j / m) % n) / n for j in range(m + 1)] if m else [run[0] / n]
    stations.sort()
    gaps = [((stations[(i + 1) % len(stations)] - t) % 1.0) * length for i, t in enumerate(stations)]
    return stations, [g for g in gaps if g > pitch + 1e-6]


def tie_wire(c, u, r_m: float, t: float, reach: float, r_boss: float, r_wall: float, stub: float, z: float) -> cq.Wire:
    """A mount's boss and its web in plan, at height z: the boss's circle (centre c, radius r_m), a
    web `t` wide from it along the unit vector u to `reach` from c, and there a stub `stub` deep
    across the web's end. The web's roots are rounded, R = r_boss at the boss and r_wall at the stub
    (drawn, never filleted after the fuse). The stub lies inside the wall, so the rounds at the
    wall cross its drafted skin instead of running tangent to it (a cusp, which gmsh fills with a
    flat tet)."""
    c = np.asarray(c, float)
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.array([-u[1], u[0]])

    def at(a, b):
        p = c + a * u + b * v
        return cq.Vector(float(p[0]), float(p[1]), z)

    def arc(centre, p0, p1, radius):
        """The short arc of the circle (centre, radius) from p0 to p1, each as (along u, along v)."""
        d = np.subtract(p0, centre) / radius + np.subtract(p1, centre) / radius
        mid = np.asarray(centre, float) + radius * d / np.linalg.norm(d)
        return cq.Edge.makeThreePointArc(at(*p0), at(*mid), at(*p1))

    h = t / 2
    a_b = math.sqrt((r_m + r_boss) ** 2 - (h + r_boss) ** 2)  # the boss's rounds' centres, along u
    k = r_m / (r_m + r_boss)  # where they touch the boss, as a share of their centres' place
    a_w = reach - r_wall  # the wall's rounds' centres, along u
    w = h + r_wall + 1.0  # the stub's half-width
    return cq.Wire.assembleEdges([
        arc((a_b, h + r_boss), (k * a_b, k * (h + r_boss)), (a_b, h), r_boss),
        cq.Edge.makeLine(at(a_b, h), at(a_w, h)),
        arc((a_w, h + r_wall), (a_w, h), (reach, h + r_wall), r_wall),
        cq.Edge.makeLine(at(reach, h + r_wall), at(reach, w)),
        cq.Edge.makeLine(at(reach, w), at(reach + stub, w)),
        cq.Edge.makeLine(at(reach + stub, w), at(reach + stub, -w)),
        cq.Edge.makeLine(at(reach + stub, -w), at(reach, -w)),
        cq.Edge.makeLine(at(reach, -w), at(reach, -h - r_wall)),
        arc((a_w, -h - r_wall), (reach, -h - r_wall), (a_w, -h), r_wall),
        cq.Edge.makeLine(at(a_w, -h), at(a_b, -h)),
        arc((a_b, -h - r_boss), (a_b, -h), (k * a_b, -k * (h + r_boss)), r_boss),
        cq.Edge.makeThreePointArc(at(k * a_b, -k * (h + r_boss)), at(-r_m, 0.0), at(k * a_b, k * (h + r_boss))),
    ])  # fmt: skip


def _volume_meshes(shape: cq.Shape) -> bool:
    """Whether gmsh fills the half with tets as `fe.py` will (its `mesh_half`, 8 mm). A surface
    that meshes can still hold two coincident faces, which only the volume mesh finds:
    `style_field_band`'s FE failed on "two overlapping facets" after its surface test had passed
    (23:43)."""
    import tempfile

    from fe import mesh_half

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "half.brep"
        shape.exportBrep(str(path))
        try:
            mesh_half(path, 8.0)
            return True
        except Exception:  # noqa: BLE001 - gmsh's refusal is the answer
            return False


def meshable(shape: cq.Shape, name: str) -> cq.Shape:
    """The half healed, then checked whole: `_meshable_surface`'s heal, and gmsh's volume mesh,
    said in the log (a half that does not fill with tets would fail the FE)."""
    out = _meshable_surface(shape, name)
    say(f"{name}: {'fills with tets' if _volume_meshes(out) else 'does NOT fill with tets (the FE would fail)'}")
    return out


def _meshable_surface(shape: cq.Shape, name: str) -> cq.Shape:
    """The half as gmsh will mesh it: its strip and spot faces under HEAL_MM healed away (OCC's
    ShapeFix_FixSmallFace, then the same-domain faces unified: lobed.py's repair, which trades
    sub-millimetre detail for elements a single-precision factor can use). The heal is kept only
    if the solid stays one valid solid of the same volume and its surface meshes; otherwise the
    half is kept as built. Healing only the halves that failed to mesh left Avtec's 0.03 mm
    faces, and its factor did not refine (20:43)."""
    from OCP.ShapeFix import ShapeFix_FixSmallFace, ShapeFix_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

    try:
        fix = ShapeFix_FixSmallFace()
        fix.Init(shape.wrapped)
        fix.SetPrecision(HEAL_MM)
        fix.SetMaxTolerance(2 * HEAL_MM)
        fix.Perform()
        whole = ShapeFix_Shape(fix.FixShape())
        whole.Perform()
        unify = ShapeUpgrade_UnifySameDomain(whole.Shape(), True, True, True)
        unify.Build()
        out = cq.Shape.cast(unify.Shape())
    except Exception as error:  # noqa: BLE001 - OCC's heal can raise (StdFail_NotDone, Kalyani's cover, 22:44)
        say(f"{name}: the heal failed ({type(error).__name__}); kept as built, which {'meshes' if _surface_meshes(shape) else 'does NOT mesh'}")
        return shape
    solids = out.Solids()
    if len(solids) != 1 or not out.isValid() or abs(out.Volume() - shape.Volume()) > 0.005 * shape.Volume():
        why = f"solids {len(solids)}, valid {out.isValid()}"
    elif not _surface_meshes(solids[0]):
        why = "its surface does not mesh"
    else:
        say(f"{name}: healed, faces {len(shape.Faces())} -> {len(out.Faces())}, volume {(out.Volume() / shape.Volume() - 1) * 100:+.2f} %; meshes")
        return solids[0]
    say(f"{name}: the heal is refused ({why}); kept as built, which {'meshes' if _surface_meshes(shape) else 'does NOT mesh'}")
    return shape


def build(stem: str = "grammar", overrides: dict | None = None, recipe: dict | None = None) -> dict:
    s = {**convex.SETTINGS, **GRAMMAR, **(overrides or {})}
    rc = {**RECIPE, **(recipe or {})}
    say(f"recipe: {json.dumps(rc)}")
    spec, refusals = load_and_validate(convex.CONTRACT)
    assert refusals == [], refusals
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial = value_in(gaps.min_radial_clearance, "mm")
    axial = value_in(gaps.min_axial_clearance, "mm") if getattr(gaps, "min_axial_clearance", None) else 3.0
    sealed = {(e.shaft, e.side.value) for e in gaps.sealed_ends}
    # Today's contract (10 October), each part read where the contract gives it, the grammar's own
    # choice standing where it does not: who holds the motor; the process's joint rules (A26); the
    # seals' section (A16); the mounts with their brackets' rooms (A20) and each shaft's way out, the
    # seals' bores and the half-shafts' joints (A27), as the Contract page draws them (`spaces`).
    motor = spec.requirement.motor_on_housing()  # False: the vehicle holds the motor (the engineer, 13:21)
    if not motor:
        for key in MOTOR_KEYS:
            s.pop(key, None)
    joint = spec.manufacturing.joint
    if joint is not None:
        s.update({
            "bolt_hole": value_in(joint.hole_diameter, "mm"), "bolt_boss": value_in(joint.boss_diameter, "mm"),
            "flange_bolt_axis": value_in(joint.bolt_offset, "mm"), "flange_thickness": value_in(joint.flange_thickness, "mm"),
            "bolt_pitch": min(s["bolt_pitch"], value_in(joint.max_pitch, "mm")),
        })  # fmt: skip
    if gaps.seal_section is not None:
        s["seal_radial"] = value_in(gaps.seal_section, "mm")
    sp = contract_spaces(spec, chain)
    brackets = list(sp.brackets)  # the vehicle's bracket and bolt beyond each mount's faces
    joint_at = {tuple(e.name.split(" joint ")): e for e in sp.exits if " joint " in e.name}  # (shaft, side): its room
    if sp.mounts:
        m0 = spec.requirement.mounts[0]
        s.update({"mount_diameter": 2 * sp.mounts[0].radius, "mount_hole": 2 * sp.mounts[0].inner,
                  "mount_length": sp.mounts[0].z1 - sp.mounts[0].z0})  # fmt: skip
        if m0.bracket_room is not None:
            s["bracket_room"] = value_in(m0.bracket_room, "mm")
    say(f"contract: motor {'on the housing' if motor else 'held by the vehicle (no flange)'}; "
        f"{len(sp.mounts)} mounts of its own; joint rooms at {sorted(joint_at)}")
    wall, draft = s["wall"], s["draft"]
    stacks = {st.shaft: st for st in chain.layout.shafts}
    axis = {sh: st.axis for sh, st in stacks.items()}

    # The bearings, as lobed.py reads them (fe.py's seats are these bores).
    bearings = []
    for st in chain.layout.shafts:
        for p in st.parts:
            if p.kind != "bearing":
                continue
            side = p.name.rsplit(" ", 1)[-1]
            choice = chain.bearings.get((st.shaft, side))
            bearings.append({
                "shaft": st.shaft, "side": side, "axis": st.axis, "D": p.diameter,
                "d": choice.bearing.d if choice else p.diameter / 2, "z": (p.z_min, p.z_max),
                "sealed": (st.shaft, side) in sealed,
                "designation": choice.bearing.designation if choice else "guess",
                "boss_r": (s["boss_k"] * p.diameter + s["boss_c"]) / 2,
            })  # fmt: skip
    bearing = {(b["shaft"], b["side"]): b for b in bearings}

    # The split, between the stages (the engineer, 02:12).
    first = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear" and p.name.startswith("s1")]
    second = [p for st in chain.layout.shafts for p in st.parts if p.kind == "gear" and p.name.startswith("s2")]
    z_split = (max(p.z_max for p in first) + min(p.z_min for p in second)) / 2

    # 1. The silhouette: every gear's and the carrier's room, the bosses, the motor's ring.
    def room_r(shaft):
        return max([p.diameter / 2 + radial for p in stacks[shaft].parts if p.kind in ("gear", "carrier")] + [0.0])

    circles = []
    for sh in ("input", "intermediate", "output"):
        r = max(room_r(sh) + wall, max(b["boss_r"] for b in bearings if b["shaft"] == sh))
        if sh == "input" and motor:  # grown to hold the motor's ring
            r = max(r, s["motor_ring"][1] / 2 + s["motor_clear"])
        circles.append((*axis[sh], r))
    out_tip = max(p.diameter for p in stacks["output"].parts if p.kind == "gear")

    def sump_circle(depth):
        return (axis["output"][0], axis["output"][1] + out_tip / 2 + depth - 25.0, 25.0 + wall)

    # The sump under the output gear, `sump` deep unless that would bring it within the flange's
    # lip and 1 mm of a mount's bracket room: then only as deep as that allows, and none where it
    # would no longer stand past the gear's own wall (its least clearance).
    depth = s["sump"]
    while brackets and depth > 0 and any(math.dist(sump_circle(depth)[:2], b.centre) - sump_circle(depth)[2] < b.radius + s["lip"] + 1.0 for b in brackets):
        depth -= 0.5
    if depth == s["sump"] or depth > radial:
        circles.append(sump_circle(depth))
    if depth < s["sump"]:
        say(f"the sump: {max(depth, 0.0):.1f} mm under the output gear, not {s['sump']:.0f}, to keep clear of the mounts' bracket rooms"
            f"{'; left out (no deeper than the gear room)' if depth <= radial else ''}")
    # The silhouette's family (the recipe): the hull; lobes, each gear's drum showing with
    # concave waists between; or a rounded box.
    form = rc["outline"] if rc["levels"] != "rooms" else {"family": "hull"}  # rooms: grammar4's flange, bolts and mounts, as the optimiser had them
    if form["family"] == "box":
        outline = Outline(box_of(circles, form.get("corner", 45.0)), "hull")
    else:
        outline = Outline(circles, form["family"], form.get("blend", 60.0))
    inner = outline.grow(-wall)
    say(f"silhouette: {form['family']} of {[(round(x), round(y), round(r, 1)) for x, y, r in circles]}")
    conflicts = []  # what the contract asks that this housing cannot give, measured
    if brackets:
        poly_out, poly_in = outline.points(1.0), inner.points(1.0)
        for b in brackets:
            if not b.name.endswith("+z"):
                continue  # one line per mount
            into_wall = b.radius - signed_gap(poly_out, b.centre)
            if into_wall > 0:
                into_room = b.radius - signed_gap(poly_in, b.centre)
                conflicts.append(f"{b.name.rsplit(' ', 2)[0]}'s bracket room reaches {into_wall:.1f} mm into the housing's wall"
                                 + (f" and {into_room:.1f} mm past it, into the housing's inside" if into_room > 0 else ""))  # fmt: skip
                say(f"  CONFLICT: {conflicts[-1]}")

    if rc["levels"] == "rooms":
        # 2. The shells as the optimiser's own skin (LOP-16, `cup.py`; the engineer, 01:20): every
        # part's room from its far end to the split, its wall all round. No drum, bridge or tower
        # of the generator's: what the optimiser placed outside the skin is the field's (below).
        import cup as cupmod

        ends = {st.shaft: st.ends for st in chain.layout.shafts}
        shafts = ("input", "intermediate", "output")
        circle_of = dict(zip(shafts, circles[:3], strict=True))
        shrink = math.tan(math.radians(draft))
        t_f = s["flange_thickness"]
        h = s["rib_height"]
        hollow_of = {}

        def drum_circle(sh, start):
            x, y, r = circle_of[sh]
            return (x, y, r - abs(z_split - start) * shrink)

        all_rooms = cupmod.rooms(chain, radial, axial)
        lo_p, hi_p = cupmod.pieces(all_rooms, z_split, "motor_side"), cupmod.pieces(all_rooms, z_split, "cover")

        def seat_far(ps, b):
            return next(p["far"] for p in ps if p["kind"] == "bore" and p["shaft"] == b["shaft"] and tuple(p["z"]) == tuple(b["z"]))

        face_lo = {b["shaft"]: seat_far(lo_p, b) - wall for b in bearings if b["side"] == "-z"}
        z_face = face_lo["input"]
        lo_outer, lo_cavity, _ = cupmod.cup(all_rooms, z_split, "motor_side", wall, draft)
        hi_outer, hi_cavity, _ = cupmod.cup(all_rooms, z_split, "cover", wall, draft)
        z_base, drum_lo = z_face, []  # the mounts stand from the motor face, as grammar4's
        up_bearings = [b for b in bearings if b["side"] == "+z"]
        top_of = {b["shaft"]: seat_far(hi_p, b) + wall for b in up_bearings}
        z_top, z_drum, bridge = max(top_of.values()), min(top_of.values()), []
        say(f"the optimiser's skin: motor faces {[(sh, round(v, 2)) for sh, v in face_lo.items()]}; cover tops {[(sh, round(v, 2)) for sh, v in top_of.items()]}; split {z_split:.2f}")
    else:
        # 2. The shells. The motor side: a cup to the deepest stack's end ("flat"), or a base to the
        # shallowest with a drum per deeper shaft down to its own end ("drums"), so that each
        # bearing's wall stands at its bearing's depth.
        ends = {st.shaft: st.ends for st in chain.layout.shafts}
        shafts = ("input", "intermediate", "output")
        circle_of = dict(zip(shafts, circles[:3], strict=True))
        z_face = min(e[0] for e in ends.values())
        if rc["levels"] == "drums":
            z_base = max(ends[sh][0] for sh in shafts)
            drum_lo = [sh for sh in shafts if ends[sh][0] < z_base - 2.0]
        else:
            z_base, drum_lo = z_face, []
        face_lo = {sh: ends[sh][0] if sh in drum_lo else z_base for sh in shafts}
        shrink = math.tan(math.radians(draft))
        # The cover: a drum over the second stage, its inside face the axial clearance past the
        # stage's gears; over the cover's bearings a bridge, or a tower each, to their stacks' ends.
        z_drum = max(p.z_max for p in second) + axial + wall
        if rc["cover"] == "flat":  # one deep face over everything, up to the stacks' ends
            z_drum = max(e[1] for e in ends.values())
        up_bearings = [b for b in bearings if b["side"] == "+z" and b["z"][0] > z_drum - wall]
        bridge = [(*b["axis"], b["boss_r"]) for b in up_bearings]
        z_top = max(ends[b["shaft"]][1] for b in up_bearings) if up_bearings else z_drum
        top_of = {b["shaft"]: (ends[b["shaft"]][1] if rc["cover"] == "towers" else z_top) for b in up_bearings}
        say(f"motor faces {[(sh, round(face_lo[sh], 2)) for sh in shafts]}; split {z_split:.2f}; drum face {z_drum:.2f}; tops {top_of}")

        def drum_circle(sh, start):
            """A drum's circle where it starts, on the base's drafted wall line."""
            x, y, r = circle_of[sh]
            return (x, y, r - abs(z_split - start) * shrink)

        t_f = s["flange_thickness"]
        h = s["rib_height"]
        lo_outer = drafted(outline, z_split, z_base, draft, 0.0 if drum_lo else s["corner_out"])
        lo_cavity = drafted(inner, z_split + 2.0, z_base + wall, draft, 0.0 if drum_lo else s["corner_in"])
        hollow_of = {}
        for sh in drum_lo:
            start = z_base + wall  # from inside the base's end wall
            x, y, r0 = drum_circle(sh, start)
            lo_outer = lo_outer.fuse(drafted([(x, y, r0)], start, face_lo[sh], draft, s["corner_out"]))
            # The drum's hollow starts exactly on the base cavity's cone (which starts 2 mm past the
            # split): 0.026 mm wider, the two cones did not merge and left a skin that closed each
            # drum's hollow off (Batom's, Punch's, 20:46).
            r_hollow = circle_of[sh][2] - wall - abs(z_split + 2.0 - (start + 1.0)) * shrink
            hollow_of[sh] = (drafted([(x, y, r_hollow)], start + 1.0, face_lo[sh] + wall, draft, s["corner_in"]), (x, y, r_hollow))
            lo_cavity = lo_cavity.fuse(hollow_of[sh][0])
        if drum_lo:
            lo_outer = round_steps(lo_outer.clean(), z_base, [(drum_circle(sh, z_base)) for sh in drum_lo], s)
        hi_outer = drafted(outline, z_split, z_drum, draft, s["corner_out"])
        hi_cavity = drafted(inner, z_split - 2.0, z_drum - wall, draft, s["corner_in"])
        if up_bearings:
            hollows = []
            if rc["cover"] == "towers":
                for b in up_bearings:
                    circ = [(*b["axis"], b["boss_r"])]
                    hi_outer = hi_outer.fuse(drafted(circ, z_drum - wall, top_of[b["shaft"]], draft, s["corner_out"]))
                    hollows.append(drafted(grown(circ, -wall), z_drum - wall - 2.0, top_of[b["shaft"]] - wall, draft, s["corner_in"]))
            else:
                hi_outer = hi_outer.fuse(drafted(bridge, z_drum - wall, z_top, draft, s["corner_out"]))
                hollows.append(drafted(grown(bridge, -wall), z_drum - wall - 2.0, z_top - wall, draft, s["corner_in"]))
            inside = fuse(hollows)
            # The hollow stops a wall short of every boss under the drum's face, so that the face
            # stays whole over it (where it opened over the input's boss, a pocket was left).
            for b in bearings:
                if b["side"] == "+z" and b not in up_bearings:
                    inside = inside.cut(cylinder(b["axis"], z_drum - wall - 3.0, z_top, 2 * (b["boss_r"] + 0.5)))
            hi_cavity = hi_cavity.fuse(inside)
    say(f"cups: motor side {lo_outer.Volume() / 1e3:.0f} cm3 outside, cover {hi_outer.Volume() / 1e3:.0f}")

    def boolean(op, a, b, what):
        """a op b; on OCC's failure (a null shape), again with a fuzzy tolerance, else a cut is
        skipped and an intersection gives nothing; said either way."""
        for tol in (None, 0.01):
            try:
                out = getattr(a, op)(b, tol=tol) if tol else getattr(a, op)(b)
                if not out.wrapped.IsNull() and out.Solids():
                    if tol:
                        say(f"  {what}: {op} needed a fuzzy tolerance")
                    return out
            except Exception:  # noqa: BLE001 - OCC's failure is retried or reported below
                pass
        say(f"  {what}: {op} failed")
        return a if op == "cut" else None

    # 4. The flange: a lip, and the bolt bosses on it at an even pitch. Where a mount's bracket room
    # crosses the flange (the vehicle's, A20), a bolt stands each side of it, its boss 1 mm clear,
    # and evenly between; the lip stops at the room's circle.
    flange_brackets = [b for b in brackets if b.z0 < z_split + t_f and b.z1 > z_split - t_f]
    if flange_brackets:
        bolt_wire = outline.grow(s["flange_bolt_axis"]).wire(0.0)
        bolt_t, too_wide = bolt_stations(bolt_wire, s["bolt_pitch"], [(b.centre, b.radius + s["bolt_boss"] / 2 + 1.0) for b in flange_brackets])
        bay_t = [(t0 + ((t1 - t0) % 1.0) / 2) % 1.0 for t0, t1 in zip(bolt_t[-1:] + bolt_t[:-1], bolt_t, strict=True)]
        bolt_line = []
        for t_ in bolt_t:
            p_, tg = bolt_wire.positionAt(t_), bolt_wire.tangentAt(t_)
            bolt_line.append(((p_.x, p_.y), (tg.y, -tg.x)))
        for g_ in too_wide:
            conflicts.append(f"two bolts stand {g_:.0f} mm apart across a bracket's room (the joint's rule: at most {s['bolt_pitch']:.0f})")
            say(f"  CONFLICT: {conflicts[-1]}")
    else:
        bolt_line = along_wire(outline.grow(s["flange_bolt_axis"]), s["bolt_pitch"])
        bay_t = [k / len(bolt_line) for k in range(len(bolt_line))]
    bolts = [c for c, _ in bolt_line]
    lip_lo = drafted(outline.grow(s["lip"]), z_split, z_split - t_f, 0.0)
    lip_hi = drafted(outline.grow(s["lip"]), z_split, z_split + t_f, 0.0)
    notch_cuts = []  # (centre, radius): the lip cut by each bracket's room it enters, at least 1 mm deep
    if flange_brackets:
        lip_poly = outline.grow(s["lip"]).points(1.0)
        for b in flange_brackets:
            into = b.radius - signed_gap(lip_poly, b.centre)
            if into > 0:
                notch_cuts.append((b.centre, b.radius + max(0.0, 1.0 - into)))
    for centre_, r_cut in notch_cuts:
        lip_lo = boolean("cut", lip_lo, cylinder(centre_, z_split - t_f - 1.0, z_split + 1.0, 2 * r_cut), "the lip at a bracket's room")
        lip_hi = boolean("cut", lip_hi, cylinder(centre_, z_split - 1.0, z_split + t_f + 1.0, 2 * r_cut), "the lip at a bracket's room")
    lower = lo_outer.fuse(lip_lo)
    upper = hi_outer.fuse(lip_hi)
    for c in bolts:
        lower = lower.fuse(cylinder(c, z_split - t_f, z_split, s["bolt_boss"]))
        upper = upper.fuse(cylinder(c, z_split, z_split + t_f, s["bolt_boss"]))
    say(f"flange: {len(bolts)} bolts at {s['bolt_pitch']:.0f} mm or less")

    # 5. The mounts (A20).
    poly = outline.points()
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)

    def face_at(c):
        """The motor side's face under a point: a drum's own, or the base's."""
        for sh in drum_lo:
            x, y, r = circle_of[sh]
            if math.dist(c, (x, y)) < r - 1.0:
                return face_lo[sh]
        return z_base

    shrink_ = math.tan(math.radians(draft))
    mounts = []
    ties = []  # each contract mount's web in plan, (from, to), for the ribs to keep off

    def contract_mount(cyl, zone):
        """One of the contract's mounts: its boss along the shafts over its own length, tied to the
        outside wall from the side, never a column into its bracket's room.
        - Standing off the wall: a web of the ribs' thickness from the boss to the nearest point of
          the wall, as long as the boss, its roots rounded (`tie_wire`); where the wall's rounds
          would not fit, a plain web.
        - Touching the wall: the boss merges with it.
        Where the web or the boss lies under the flange's lip or within 1 mm of the wall, it carries
        on up to the split (`zone`: the lip short of the brackets' rooms, and a band 1 mm out from
        the wall to half the wall in), so that no face of it looks up at the lip or at the drafted
        wall above, which no mould could leave. Returns the solid and how it is tied."""
        if cyl.z1 > z_split:
            raise ValueError(f"{cyl.name}: only a mount on the motor side's half is drawn yet")
        c = np.asarray(cyl.centre, float)
        r_m, z0, z1 = cyl.radius, cyl.z0, cyl.z1
        q, n_out, gap = nearest_on(outline, c)
        u = -n_out  # from the boss towards the wall
        v = np.array([-u[1], u[0]])
        t_w = s["rib"]
        # How far the wall's skin lies inside the outline at the boss's far end: the draft, and the
        # end face's rounded corner where the boss ends within it.
        z_f = face_at(tuple(q + u * 30.0))
        corner, up_ = s["corner_out"], z0 - z_f
        recede = 0.0 if up_ >= corner else (corner if up_ <= 0 else corner - math.sqrt(corner**2 - (corner - up_) ** 2))
        skin = (z_split - z0) * shrink_ + recede
        # The stub's face, half a millimetre inside that skin all along its width (the wall curves
        # away from the web's line, `allow`, or towards it, `towards`).
        pts_ = np.asarray(outline.points(0.5)) - c
        a_, b_ = pts_ @ u, pts_ @ v
        near_side = (a_ > 0) & (a_ < gap + 40.0)
        allow = towards = 0.0
        width_out = t_w / 2 + 2 * rr.R_ROOT + 3.0  # past the stub's half-width, whatever round it takes
        for side in (-1.0, 1.0):
            sel = near_side & (np.abs(b_ - side * width_out) < 1.0)
            if sel.any():
                allow = max(allow, float(a_[sel].max()) - gap)
                towards = max(towards, gap - float(a_[sel].min()))
        g_l = skin + 0.5 + allow
        r_wall = max(2 * rr.R_ROOT, g_l + 1.0)  # the wall's rounds start at least 1 mm out from the wall
        reach = gap + g_l
        cavity_skin = wall + (z_split + 2.0 - z1) * shrink_  # the inside's skin, inside the outline, at the boss's near end
        stub = min(1.0, cavity_skin - 0.5 - g_l - towards)  # buried in the wall, half a millimetre short of the inside
        a_b = math.sqrt((r_m + rr.R_ROOT) ** 2 - (t_w / 2 + rr.R_ROOT) ** 2)
        if gap < r_m + 1.0:
            how = "merged with the wall"
        elif stub >= 0.6 and reach - r_wall - a_b >= 1.0:
            how = "web"
        else:
            how = "plain web"
        e_plain = min(wall / 2 + skin, cavity_skin - 1.0)

        def plan_prism(za, zb):
            if how == "web":
                wire = tie_wire(c, u, r_m, t_w, reach, rr.R_ROOT, r_wall, stub, za)
                plane = cq.Plane(origin=(0, 0, za), xDir=(1, 0, 0), normal=(0, 0, 1))
                return cq.Workplane(plane).add(wire).toPending().extrude(zb - za).val()
            body_ = cylinder(tuple(c), za, zb, 2 * r_m)
            if how == "plain web":
                body_ = body_.fuse(strip(tuple(c), tuple(q + u * e_plain), t_w, za, zb)[0])
            return body_

        body = plan_prism(z0, z1)
        if how == "merged with the wall":
            # Over a boss merged with the wall, a plate across the band, its ends square to the
            # wall 2 mm past the boss's chord: cut to the boss's own circle, its two ends met its
            # outer face in 64° edges, which the least-wall check read as 0.27 mm of metal
            # (contract_avl's mount-2, 19:46).
            half_chord = math.sqrt(max(r_m**2 - (gap - 1.0) ** 2, 0.0)) + 2.0
            above = strip(tuple(q + u * -3.0), tuple(q + u * (wall / 2 + 2.0)), 2 * half_chord, z1, z_split)[0]
        else:
            above = plan_prism(z1, z_split)
        raised = boolean("intersect", above, zone, f"{cyl.name}'s tie up to the flange")
        if raised is not None and raised.Volume() > 1.0:
            body = boolean("fuse", body, raised, f"{cyl.name}'s tie") or body
        if how != "merged with the wall":
            ties.append((c, q + u * min(g_l, wall / 2), z0, z_split))
        return body, how, gap

    if sp.mounts:
        # The contract's (A20): each a boss along the shafts over its own length with its bolt's
        # hole, tied to the wall from the side (`contract_mount`); the bracket's room beyond both
        # its faces stays empty for the vehicle's bracket and bolt.
        z_lo_ = min(c.z1 for c in sp.mounts) - 1.0
        zone = drafted(outline.grow(s["lip"]), z_lo_, z_split + 1.0, 0.0)
        for centre_, r_cut in notch_cuts:
            zone = boolean("cut", zone, cylinder(centre_, z_lo_ - 1.0, z_split + 2.0, 2 * r_cut), "the ties' zone")
        zone = boolean("fuse", zone, drafted(outline.grow(1.0), z_lo_, z_split + 1.0, 0.0), "the ties' zone") or zone
        zone = boolean("cut", zone, drafted(outline.grow(-wall / 2), z_lo_ - 1.0, z_split + 2.0, 0.0), "the ties' zone")
        for cyl in sp.mounts:
            body, how, gap = contract_mount(cyl, zone)
            lower = boolean("fuse", lower, body, cyl.name) or lower
            mounts.append({"name": cyl.name, "centre": tuple(cyl.centre), "z": (cyl.z0, cyl.z1), "normal": (0.0, 0.0, 1.0),
                           "pod": "motor_side", "diameter": 2 * cyl.radius, "hole": 2 * cyl.inner, "tie": how,
                           "off_wall_mm": round(gap - cyl.radius, 2)})  # fmt: skip
        say(f"mounts (the contract's): {[(m['name'], tuple(round(v) for v in m['centre']), m['tie']) for m in mounts]}")
    else:
        # The grammar's own: columns from the motor face up to the flange, each with its hole along
        # the shafts; the vehicle's bolt engages the lowest `mount_length`.
        for direction in ((-1.0, -0.6), (1.0, -0.4), (0.15, 1.0)):
            n_ = math.hypot(*direction)
            ux, uy = direction[0] / n_, direction[1] / n_
            far = max(poly, key=lambda q: (q[0] - cx) * ux + (q[1] - cy) * uy)
            centre = (far[0] + ux * s["mount_diameter"] * 0.25, far[1] + uy * s["mount_diameter"] * 0.25)
            foot = face_at(centre)
            lower = lower.fuse(cylinder(centre, foot, z_split, s["mount_diameter"]))
            mounts.append({"centre": centre, "z": (foot + 8.0, foot + 8.0 + s["mount_length"]), "normal": (ux, uy, 0.0), "pod": "motor_side"})
        say(f"mounts: {[tuple(round(v) for v in m['centre']) for m in mounts]}")

    # 6. The motor's ring (A25) on the motor face, round the input: only where the motor bolts to
    # the housing. Today's vehicle holds the motor, which drives the input through a flexible
    # coupling: no ring, no scallops, no wheel inside it.
    t_ring = s["motor_ring_thickness"] if motor else 0.0
    if motor:
        r_ring = s["motor_ring"][1] / 2
        # It reaches up into the cup's rounded corner (the cavity, cut later, takes back what lies
        # inside), so no shelf of it is left under the fillet, where no mould could reach.
        # Scalloped (Kalyani's): a narrower ring, a boss round each of its bolts standing out of it.
        r_ring_out = r_ring - (7.0 if rc["motor_ring"] == "scalloped" else 0.0)
        ring = (
            cq.Workplane("XY", origin=(0, 0, z_face - t_ring)).center(*axis["input"])
            .circle(r_ring_out).circle(s["motor_ring"][0] / 2).extrude(t_ring + s["corner_out"] + 1.0).val()
        )  # fmt: skip
        if rc["motor_ring"] == "scalloped":
            for k in range(s["motor_bolts"]):
                a = 2 * math.pi * k / s["motor_bolts"]
                c = (axis["input"][0] + s["motor_bolt_circle"] / 2 * math.cos(a), axis["input"][1] + s["motor_bolt_circle"] / 2 * math.sin(a))
                ring = ring.fuse(cylinder(c, z_face - t_ring, z_face + s["corner_out"] + 1.0, 2 * (r_ring - s["motor_bolt_circle"] / 2)))
        lower = lower.fuse(ring)

    # 3. The bosses outside (LOP-15). Where ribs meet a bearing's boss on an end face, the boss
    # stands FLUSH over the ribs' tops (fastcae's flush rule: an end's top stands under the top of
    # what it grips; the engineer, 21:42: ribs "higher than bore"). A bore through the wall gets a
    # tube round its seal's bore; a closed seat, a ring at its boss's radius with its 0.5·δ pad
    # inside. With the motor on the housing, its hub stands as tall as the motor's ring and the
    # intermediate's pad on the motor face is left out: the motor's ring stands over it (a 0.08 mm
    # lens of it showed past the ring's bore, 21:12). Without it, the input's seal has a boss as
    # proud as the others, and the intermediate's seat its pad where it stands on one level of the
    # face. Where a half-shaft's joint needs its room beyond an end face (A27), no boss or pad
    # stands in it: on the motor face a ring round the room, as proud, takes the ribs.
    seal_r = {b["shaft"] + b["side"]: (b["d"] + 2 * s["seal_radial"]) / 2 + 8.0 for b in bearings}
    t_rib = s["rib"]
    boss_up = h + rr.FLUSH  # how far a boss stands off its end face where ribs meet it
    low = t_ring - rr.FLUSH  # how far a rib stands under the motor's flange (where there is one)
    # The output's ring hugs the joint's room, 1 mm clear of it and a rib thick: at the bearing's
    # boss radius it stood so near the drum's wall that every fan left it at 6° (Kalyani, 19:54).
    r_joint_ring = joint_at[("output", "-z")].radius + 1.0 + t_rib if ("output", "-z") in joint_at else None
    if r_joint_ring is not None:
        ring_o = cylinder(axis["output"], face_lo["output"] - boss_up, face_lo["output"] + 1.0, 2 * r_joint_ring)
        lower = lower.fuse(ring_o.cut(cylinder(axis["output"], face_lo["output"] - boss_up - 1.0, face_lo["output"] + 2.0, 2 * (r_joint_ring - t_rib))))
    else:
        lower = lower.fuse(cylinder(axis["output"], face_lo["output"] - boss_up, face_lo["output"] + 1.0, 2 * seal_r["output-z"]))
    if motor:
        lower = lower.fuse(standing(axis["input"], face_lo["input"], -1, seal_r["input-z"], t_ring))
    else:
        lower = lower.fuse(cylinder(axis["input"], face_lo["input"] - boss_up, face_lo["input"] + 1.0, 2 * seal_r["input-z"]))
        b_i = bearing.get(("intermediate", "-z"))
        if b_i is not None and not b_i["sealed"]:
            r_pad = b_i["boss_r"] - t_rib
            on_level = all(math.dist(b_i["axis"], drum_circle(sh, z_base)[:2]) > drum_circle(sh, z_base)[2] + r_pad + s["corner_in"] + 1.0 for sh in drum_lo)
            if on_level and math.dist(b_i["axis"], axis["input"]) - seal_r["input-z"] - r_pad >= 2 * rr.R_ROOT:
                lower = lower.fuse(standing(b_i["axis"], face_lo["intermediate"], -1, r_pad, s["proud"]))
    if bridge:
        for b in up_bearings:
            if (b["shaft"], "+z") in joint_at:
                continue  # the half-shaft's joint has its room beyond the face
            r_pad = seal_r[b["shaft"] + "+z"] if b["sealed"] else b["D"] / 2 - 6.0
            upper = upper.fuse(standing(b["axis"], top_of[b["shaft"]], +1, r_pad, s["proud"]))
    for b in bearings:
        if b["side"] == "+z" and b not in up_bearings:
            upper = upper.fuse(standing(b["axis"], z_drum, +1, b["boss_r"] - t_rib, s["proud"]))
            boss_ring = cylinder(b["axis"], z_drum - 1.0, z_drum + boss_up, 2 * b["boss_r"])
            upper = upper.fuse(boss_ring.cut(cylinder(b["axis"], z_drum - 2.0, z_drum + boss_up + 1.0, 2 * (b["boss_r"] - t_rib))))
    say("bosses outside, the motor's hub" if motor else "bosses outside, the input's seal boss")

    # 7. Ribs (LOP-15). Candidates between hard points, each knowing what its two ends meet; the
    # rules (`ribrules`: fastcae's, at R = 3 mm) choose those that stand. Each kept rib is drawn,
    # cut to its room, its top rounded, and all are fused at once. A rib that enters the motor's
    # footprint stands `low` along its whole length, so no step is left in its top.
    h_side = s["rib_side"]
    lo_room = drafted(outline.grow(h_side), z_split, z_base - h, draft, s["corner_out"] + h_side)
    for sh in drum_lo:
        start = z_base + wall
        x, y, r0 = drum_circle(sh, start)
        lo_room = lo_room.fuse(drafted([(x, y, r0 + h_side)], start, face_lo[sh] - h, draft, s["corner_out"] + h_side))
    lo_room = lo_room.cut(lo_outer)
    hi_room = drafted(outline.grow(h_side), z_split, z_drum + h, draft, s["corner_out"] + h_side).cut(hi_outer)
    if motor:
        under_motor = cylinder(axis["input"], z_face - 600.0, z_face + 1.0, 2 * s["motor_room"])
        low_slab = cylinder(axis["input"], z_face - low, z_face + 600.0, 2000.0)  # everything above `low` off the motor face
    rib_boxes = []
    lo_face, hi_face = (z_face - h - 1, z_base + 1), (z_drum - 1, z_drum + h + 1)
    r_hub = seal_r["input-z"]
    shafts = ("input", "intermediate", "output")

    def boss_anchor(centre, r, top, name):
        return rr.Anchor("boss", circle=(centre[0], centre[1], r), top=top, name=name)

    if r_joint_ring is not None:
        out_boss = boss_anchor(axis["output"], r_joint_ring, boss_up, "the output's ring")
    else:
        out_boss = boss_anchor(axis["output"], seal_r["output-z"], boss_up, "the output's boss")
    if motor:
        r_rim_in = s["motor_ring"][0] / 2
        hub_a = boss_anchor(axis["input"], r_hub, t_ring, "the motor's hub")
        ring_in_a = rr.Anchor("ring", circle=(*axis["input"], r_rim_in), top=t_ring, name="the motor's ring")
        ring_out_a = rr.Anchor("ring", circle=(*axis["input"], r_ring_out), top=t_ring, name="the motor's ring")
        motor_anchors = [ring_out_a, hub_a]
    else:
        hub_a = boss_anchor(axis["input"], r_hub, boss_up, "the input's seal boss")
        motor_anchors = [hub_a]
    mount_a = [rr.Anchor("mount", circle=(*m["centre"], m.get("diameter", s["mount_diameter"]) / 2), name=m.get("name", f"mount {i}"))
               for i, m in enumerate(mounts)]  # fmt: skip
    wall_a = rr.Anchor("wall", line=np.array(outline.points(4.0) + outline.points(4.0)[:1]), name="the wall")
    flat_poly = np.array(outline.grow(-(s["corner_out"] + 3.0)).points(4.0))  # the end faces' flat part, inside the corners' round

    def inside_polygon(poly, p):
        x_, y_ = p
        hit = False
        for (x1, y1), (x2, y2) in zip(poly, np.roll(poly, -1, axis=0), strict=True):
            if (y1 > y_) != (y2 > y_) and x_ < (x2 - x1) * (y_ - y1) / (y2 - y1) + x1:
                hit = not hit
        return hit
    # the cover's bosses: towers, the bridge, or rings on the face
    hi_boss = {}
    for b in bearings:
        if b["side"] != "+z":
            continue
        if b in up_bearings and rc["cover"] in ("towers", "rooms"):
            hi_boss[b["shaft"]] = boss_anchor(b["axis"], b["boss_r"], top_of[b["shaft"]] - z_drum, f"the {b['shaft']}'s tower")
        elif b in up_bearings:
            hi_boss[b["shaft"]] = rr.Anchor("boss", line=np.array(hull_points(bridge, 4.0) + hull_points(bridge, 4.0)[:1]), top=z_top - z_drum, name="the bridge")
        else:
            hi_boss[b["shaft"]] = boss_anchor(b["axis"], b["boss_r"], boss_up, f"the {b['shaft']}'s boss")
    # the motor face's: the output's boss; the input's hub and the motor's ring stand for the input
    # and the intermediate (whose seat lies under the motor's flange). Without a flange the input's
    # seal boss is the input's, and the intermediate's seat has no boss ribs could end on.
    if motor:
        lo_boss = {"output": out_boss, "input": ring_out_a, "intermediate": ring_out_a}
    else:
        lo_boss = {"output": out_boss, "input": hub_a, "intermediate": None}

    def exit_point(anchor, towards, start):
        """Where a rib leaving `start` (inside the anchor) towards `towards` leaves the anchor's outline."""
        d = np.asarray(towards, float) - np.asarray(start, float)
        d /= max(np.linalg.norm(d), 1e-9)
        if anchor.circle is not None:
            cx, cy, r = anchor.circle
            f = np.asarray(start, float) - np.array([cx, cy])
            bq = float(f @ d)
            t = -bq + math.sqrt(max(bq * bq - (float(f @ f) - r * r), 0.0))
            return np.asarray(start, float) + d * t
        line = anchor.line
        best = None
        for i in range(len(line) - 1):
            p, q = line[i], line[i + 1]
            s_ = q - p
            den = d[0] * s_[1] - d[1] * s_[0]
            if abs(den) < 1e-12:
                continue
            w = p - np.asarray(start, float)
            t = (w[0] * s_[1] - w[1] * s_[0]) / den
            u = (w[0] * d[1] - w[1] * d[0]) / den
            if t > 0 and 0 <= u <= 1 and (best is None or t < best):
                best = t
        return np.asarray(start, float) + d * (best if best is not None else 0.0)

    def centre_of(anchor, shaft):
        return np.asarray(axis[shaft], float)

    cands = []

    def add(name, face, pts, kind, priority, ends, chain="", z=None, height=None, curved=False, rooms="face"):
        pts = np.asarray(pts, float)
        cands.append(rr.Rib(name, face, pts, t_rib, height if height is not None else h, kind, priority, ends, chain,
                            {"z": z, "curved": curved, "rooms": rooms}))  # fmt: skip

    def enters_motor(pts):
        """Whether the rib enters the motor flange's footprint (never, without a flange)."""
        return motor and bool(np.min(np.hypot(np.asarray(pts)[:, 0] - axis["input"][0], np.asarray(pts)[:, 1] - axis["input"][1])) < s["motor_room"] + t_rib)

    def fan_path(anchor, shaft, wall_pt, normal, lean_deg):
        """A curved spoke from a boss to the wall under a bolt: it leaves the boss leaning by
        `lean_deg` from square to it, and arrives at the wall square (a cubic, its control points
        on the tangents)."""
        # One circular arc from the boss to the wall, arriving square to it: its curvature is set
        # by where the bay lies (straight out, a straight rib; off to the side, a gentle curve).
        # The cubic with a fixed lean looped wherever the bay lay to the side: radii of 3-33 mm,
        # and Kalyani's cover kept 3 of its fans (23:06). It leaves the boss turned by
        # `lean_deg` round it, the style's swirl.
        c = centre_of(anchor, shaft)
        w = np.asarray(wall_pt, float)
        n_ = np.asarray(normal, float)
        if anchor.line is not None:
            # An outline (the bridge): the rib leaves it square, from its point nearest the wall,
            # and curves to arrive square at the wall (a cubic on the two normals). Aimed from a
            # shaft's axis, fans met the bridge's straight sides at 9-43° (23:07).
            line = anchor.line
            seg = rr._nearest_segment(line, w)
            q0, q1 = line[seg], line[seg + 1]
            t = float(np.clip((w - q0) @ (q1 - q0) / max(float((q1 - q0) @ (q1 - q0)), 1e-12), 0.0, 1.0))
            p0 = q0 + t * (q1 - q0)
            tang = (q1 - q0) / max(np.linalg.norm(q1 - q0), 1e-9)
            t0 = np.array([tang[1], -tang[0]])
            if float(t0 @ (p0 - line[:-1].mean(axis=0))) < 0:
                t0 = -t0  # outward
            # Leaving midway between the outline's normal and the wall's halves the turn it must
            # make between them (square from the bridge, they turned at 19-44 mm, 23:08); the
            # arrival rule (45°) still reads it.
            mid_dir = t0 + n_
            if np.linalg.norm(mid_dir) > 1e-6:
                t0 = mid_dir / np.linalg.norm(mid_dir)
            length = float(np.linalg.norm(w - p0))
            ts = np.linspace(0.0, 1.0, 13)[:, None]
            p1, p2 = p0 + t0 * length / 3, w - n_ * length / 3
            pts = (1 - ts) ** 3 * p0 + 3 * (1 - ts) ** 2 * ts * p1 + 3 * (1 - ts) * ts**2 * p2 + ts**3 * w
            return np.vstack([p0 - t0 * 2.0, pts])
        phi = math.atan2(w[1] - c[1], w[0] - c[0])
        lean = math.radians(lean_deg)
        p0 = exit_point(anchor, c + 1000.0 * np.array([math.cos(phi - lean), math.sin(phi - lean)]), c)
        m = np.array([-n_[1], n_[0]])
        chord = w - p0
        denom = 2.0 * float(m @ chord)
        if abs(denom) < 1e-6 * float(chord @ chord):
            pts = np.array([p0 + t * chord for t in np.linspace(0.0, 1.0, 13)])
        else:
            k = -float(chord @ chord) / denom
            o = w + k * m
            a0 = math.atan2(p0[1] - o[1], p0[0] - o[0])
            a1 = math.atan2(w[1] - o[1], w[0] - o[0])
            if float(np.array([-math.sin(a1), math.cos(a1)]) @ n_) > 0:  # travelling anticlockwise at the wall
                while a1 < a0:
                    a1 += 2 * math.pi
            else:
                while a1 > a0:
                    a1 -= 2 * math.pi
            pts = np.array([o + abs(k) * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(a0, a1, 13)])
        t0 = (pts[1] - pts[0]) / max(np.linalg.norm(pts[1] - pts[0]), 1e-9)
        return np.vstack([p0 - t0 * 2.0, pts])  # buried 2 mm into the boss at its start

    # Bays: the wall midway between neighbouring bolts. A rib climbs the wall only there, clear of
    # the bolts' tools (fastcae's kept-clear tool space, 1.8 × the hole's radius across and three
    # diameters past its end: a rib on a bolt's line blocks its head and the socket, 22:45).
    bay_wire = outline.grow(s["flange_bolt_axis"]).wire(0.0)
    bays = []
    for t_ in bay_t:
        p_, tg = bay_wire.positionAt(t_), bay_wire.tangentAt(t_)
        nx, ny = tg.y, -tg.x
        bays.append(((p_.x - nx * s["flange_bolt_axis"], p_.y - ny * s["flange_bolt_axis"]), (nx, ny)))
    d_rad = math.radians(draft)

    def corner_start(face, wall_pt, n):
        """Where the end face's flat ends and the corner's round begins, on the line square to the
        wall at `wall_pt` (the wall's outside at the split), and the face's level there."""
        z_f = z_drum if face == "hi" else face_at((wall_pt[0] - n[0] * 30.0, wall_pt[1] - n[1] * 30.0))
        v = 1.0 if face == "lo" else -1.0  # from the face towards the split
        z_end = z_f + v * s["corner_out"] * (1 - math.sin(d_rad))
        c0_n = -abs(z_split - z_end) * math.tan(d_rad) - s["corner_out"] * math.cos(d_rad)
        return np.array([wall_pt[0] + n[0] * c0_n, wall_pt[1] + n[1] * c0_n]), z_f

    take = {"nearest": 1, "two": 2, "none": 0}[rc["spokes"]]
    for bi, (wall_pt, n) in enumerate(bays):
        for sh in sorted(shafts, key=lambda sh_: math.dist(wall_pt, axis[sh_]))[:take]:
            for face, anchor in (("lo", lo_boss[sh]), ("hi", hi_boss.get(sh))):
                if anchor is None:
                    continue
                c0, z_f = corner_start(face, wall_pt, n)
                pts = fan_path(anchor, sh, c0, n, 0.0)
                add(f"spoke {face} {sh} {bi}", face, pts, "spoke", 40, (anchor, wall_a), f"bay {face} {bi}",
                    height=low if face == "lo" and enters_motor(pts) else h)  # fmt: skip
                cands[-1].build.update({"chain": (z_f, n), "wall_pt": wall_pt})
    if rc["delta"]:  # boss to boss along the lines of centres
        for face, (sa, sb) in (("lo", ("intermediate", "output")), ("hi", ("input", "intermediate"))):
            a_anchor = (lo_boss if face == "lo" else hi_boss).get(sa)
            b_anchor = (lo_boss if face == "lo" else hi_boss).get(sb)
            if a_anchor is None or b_anchor is None or a_anchor is b_anchor:
                continue
            pa = exit_point(a_anchor, axis[sb], axis[sa])
            pb = exit_point(b_anchor, axis[sa], axis[sb])
            d = (pb - pa) / max(np.linalg.norm(pb - pa), 1e-9)
            pts = [pa - 2.0 * d, pb + 2.0 * d]
            add(f"delta {face}", face, pts, "delta", 30, (a_anchor, b_anchor), height=low if face == "lo" and enters_motor(pts) else h)
    if rc["ears"]:  # each mount to its nearest boss on the motor face
        for i, m in enumerate(mounts):
            sh = min((sh_ for sh_ in ("intermediate", "output") if lo_boss.get(sh_) is not None), key=lambda sh_: math.dist(m["centre"], axis[sh_]))
            anchor = lo_boss[sh]
            pa = exit_point(anchor, m["centre"], axis[sh])
            pm = exit_point(mount_a[i], axis[sh], m["centre"])
            d = (pm - pa) / max(np.linalg.norm(pm - pa), 1e-9)
            pts = [pa - 2.0 * d, pm + 2.0 * d]
            add(f"ear {i}", "lo", pts, "ear", 35, (anchor, mount_a[i]), height=low if enters_motor(pts) else h)
    # The wheel inside the motor's ring: spokes from the hub to the ring, and a ring halfway out
    # (only with the motor's flange).
    for k in range(rc["wheel"]["spokes"] if motor else 0):
        a = 2 * math.pi * (k + 0.5) / rc["wheel"]["spokes"]
        u = np.array([math.cos(a), math.sin(a)])
        p0 = np.asarray(axis["input"]) + u * (r_hub - 2.0)
        p1 = np.asarray(axis["input"]) + u * (r_rim_in + 2.0)
        add(f"wheel {k}", "lo", [p0, p1], "wheel", 45, (hub_a, ring_in_a), height=low)
    if motor and rc["wheel"].get("ring"):
        r_mid = 0.5 * (r_hub + r_rim_in)
        circ = [np.asarray(axis["input"]) + r_mid * np.array([math.cos(t), math.sin(t)]) for t in np.linspace(0, 2 * math.pi, 73)]
        add("wheel ring", "lo", circ, "ring", 44, (None, None), height=low)
    # Fans (Kalyani's, Punch's): curved chains from a boss to the bays, `count` of them, each
    # leaning off square at its boss by half the pattern's bend (at most 90° less the arrival
    # angle) and arriving square at its wall.
    pattern = rc["pattern"]
    if pattern and pattern["kind"] == "fan":
        lean = min(pattern["bend"] / 2.0, 90.0 - rr.ARRIVE_DEG)
        for sh in pattern["around"]:
            for face in ("lo", "hi"):
                anchor = (lo_boss if face == "lo" else hi_boss).get(sh)
                if anchor is None or anchor.kind == "ring":
                    continue  # on the motor face the motor's ring stands over the intermediate's seat
                order = sorted(range(len(bays)), key=lambda i: math.atan2(bays[i][0][1] - axis[sh][1], bays[i][0][0] - axis[sh][0]))
                count = min(pattern["count"], len(order))
                for j in range(count):
                    bi = order[(j * len(order)) // count]
                    wall_pt, n = bays[bi]
                    c0, z_f = corner_start(face, wall_pt, n)
                    pts = fan_path(anchor, sh, c0, n, lean)
                    add(f"fan {face} {sh} {bi}", face, pts, "fan", 38, (anchor, wall_a), f"bay {face} {bi}",
                        height=low if face == "lo" and enters_motor(pts) else h)  # fmt: skip
                    cands[-1].build.update({"chain": (z_f, n), "wall_pt": wall_pt})

    # Ribs chosen by an optimiser's field (LOP-16). Every rib the grammar draws from its own
    # parameters is laid on the field's plan (`topo_read.py`: the metal standing past the skin's end
    # face): a spoke from each boss to each bay (leaving the boss square, or turned 15° or 30° round
    # it), a rib from boss to boss, a ring round a bearing every voxel out from a pocket's width
    # past its boss. One is offered where most of its length lies on that metal, as tall as the
    # metal there, the best covered first; the rules judge it as any other, and the field's mass
    # bounds how many stand (after the selection). The field's own ridges, traced and carried on to
    # hard points, kept 3 of 26 (00:21): their ends lay in the open, on the field's closed loops or
    # inside a boss, and they turned at 7-33 mm where the rules ask 48 (archived). Shapes from
    # parameters, never traced (the engineer, 23 September).
    offered = []
    if pattern and pattern["kind"] == "field":
        plan = np.load(OUT / f"{pattern['run']}_plan.npz")
        xs_, ys_, pitch = plan["xs"], plan["ys"], float(plan["h"])
        tall = min(h, 5 * t_rib)
        pocket = 17.0  # mm, the least pocket between a boss and a ring round it (ribrules' note)

        def metal_on(face, pts):
            """The field's metal past the skin's face under each point, mm (0 off the field)."""
            m = plan["cover_beyond" if face == "hi" else "motor_side_beyond"]
            i = np.round((pts[:, 0] - xs_[0]) / pitch).astype(int)
            j = np.round((pts[:, 1] - ys_[0]) / pitch).astype(int)
            on_grid = (i >= 0) & (i < len(xs_)) & (j >= 0) & (j < len(ys_))
            out = np.zeros(len(pts))
            out[on_grid] = m[i[on_grid], j[on_grid]]
            return out

        def hard_points(face):
            pool = [a_ for a_ in (lo_boss if face == "lo" else hi_boss).values() if a_ is not None] + (motor_anchors + mount_a if face == "lo" else [])
            return list({a_.name: a_ for a_ in pool}.values())

        def blocked(face, pts, own):
            """Whether the rib's middle (past its 3 mm ends) runs through a hard point other than
            its own two ends."""
            p = rr._resample(np.asarray(pts, float), 2.0)[2:-2]
            for a_ in hard_points(face):
                if any(o is not None and a_.name == o.name for o in own):
                    continue
                if a_.circle is not None:
                    if (np.hypot(p[:, 0] - a_.circle[0], p[:, 1] - a_.circle[1]) < a_.circle[2] + t_rib / 2).any():
                        return True
                elif any(inside_polygon(a_.line, q) for q in p):
                    return True
            return False

        def offer(name, face, pts, kind, ends, chain_n=None, z=None):
            pts = np.asarray(pts, float)
            m = metal_on(face, rr._resample(pts, pitch / 2))
            on = m >= pitch - 1e-6  # a voxel or more of metal past the face
            share = float(on.mean())
            offered.append({"name": name, "face": face, "points": pts, "share": share})
            if share < 0.5 or blocked(face, pts, ends):
                return  # most of it would stand where the optimiser put no metal, or it runs through a boss
            height = low if face == "lo" and enters_motor(pts) else float(np.clip(np.median(m[on]), rr.LEAST, tall))
            add(name, face, pts, kind, int(round(30 * share)), ends, z=z, height=height)
            cands[-1].build.update({"share": share})
            if chain_n is not None:
                cands[-1].build.update({"chain": chain_n})

        def shaft_at(a_):
            """The shaft whose axis a circle's centre is."""
            return min(shafts, key=lambda sh_: math.dist(axis[sh_], a_.circle[:2]))

        def inner_point(a_, towards):
            """A point inside the hard point to leave it from: a circle's centre; inside the bridge,
            the axis of its bearing nearest `towards`."""
            if a_.circle is not None:
                return np.asarray(a_.circle[:2], float)
            inside = [np.asarray(axis[b["shaft"]], float) for b in up_bearings if inside_polygon(a_.line, axis[b["shaft"]])]
            return min(inside, key=lambda c: math.dist(c, towards))

        for face in ("lo", "hi"):
            starts = list({a_.name: a_ for a_ in (lo_boss if face == "lo" else hi_boss).values() if a_ is not None}.values())
            for anchor in starts:
                sh = shaft_at(anchor) if anchor.circle is not None else None
                for bi, (wall_pt, n) in enumerate(bays):
                    c0, z_f = corner_start(face, wall_pt, n)
                    for lean in ((0.0,) if anchor.line is not None else (-30.0, -15.0, 0.0, 15.0, 30.0)):
                        pts = fan_path(anchor, sh or "input", c0, n, lean)
                        offer(f"field spoke {face} {anchor.name} {bi} {lean:+.0f}", face, pts, "spoke", (anchor, wall_a), chain_n=(z_f, n))
            for ia, a_ in enumerate(starts):
                for b_ in starts[ia + 1 :]:
                    ca = inner_point(a_, b_.circle[:2] if b_.circle is not None else b_.line[:-1].mean(axis=0))
                    cb = inner_point(b_, ca)
                    pa, pb = exit_point(a_, cb, ca), exit_point(b_, ca, cb)
                    if np.linalg.norm(pb - pa) < 3 * t_rib:
                        continue
                    d = (pb - pa) / np.linalg.norm(pb - pa)
                    offer(f"field delta {face} {a_.name} to {b_.name}", face, [pa - 2.0 * d, pb + 2.0 * d], "delta", (a_, b_))
            for b in bearings:
                if b["side"] != ("-z" if face == "lo" else "+z") or b in up_bearings:
                    continue  # a bearing under the bridge or a tower is held by it
                own = [a_ for a_ in hard_points(face) if a_.circle is not None and math.dist(a_.circle[:2], axis[b["shaft"]]) < 1.0]
                if not own:
                    continue  # the intermediate's seat on the motor face: under the motor's ring
                r = max(a_.circle[2] for a_ in own) + pocket + t_rib / 2
                while True:
                    circ = np.array([np.asarray(axis[b["shaft"]]) + r * np.array([math.cos(t), math.sin(t)]) for t in np.linspace(0, 2 * math.pi, 73)])
                    if not all(inside_polygon(flat_poly, q) for q in circ):
                        break  # past the end face's flat
                    levels = {round(face_at(tuple(q)), 1) for q in circ} if face == "lo" else {z_drum}
                    if len(levels) == 1:
                        offer(f"field ring {face} {b['shaft']} {r:.0f}", face, circ, "ring", (None, None), z=levels.pop())
                    r += pitch

    # A rib on the motor side keeps to one level of its end face: one run from a drum's face onto
    # the base would step its top down with the face, a square section in the open.
    stepping = []
    if drum_lo:
        for r in cands:
            if r.face == "lo" and r.kind not in ("wheel", "ring"):
                levels = {round(face_at(tuple(p)), 1) for p in rr._resample(r.points, 4.0)}
                if len(levels) > 1:
                    r.refused = ["runs over a step between the end face's levels"]
        stepping = [r for r in cands if r.refused]
        cands = [r for r in cands if not r.refused]
    # The contract's keep-outs (10 October): no rib in a mount's bracket room (A20) or a half-shaft's
    # joint room (A27), nor into a mount's web. A rib's reach in plan is its line and, for a chain
    # round the corner, its run down the wall standing its height off it; along the shafts, from its
    # face to its top, or to the flange for a chain.
    kept_out = []
    if brackets or joint_at:

        def reach_of(r):
            pts = np.asarray(r.points, float)
            chain_ = r.build.get("chain")
            if r.face == "hi":
                z_f = z_drum
            elif r.build.get("z") is not None:
                z_f = r.build["z"]
            else:
                z_f = face_at(tuple(pts[len(pts) // 2])) if r.kind not in ("wheel", "ring") else face_lo["input"]
            if chain_:
                n_ = np.asarray(chain_[1], float)
                w_pt = np.asarray(r.build.get("wall_pt", pts[-1] + n_ * (s["corner_out"] + abs(z_split - chain_[0]) * shrink_)), float)
                pts = np.vstack([pts, w_pt, w_pt + n_ * r.height])
            if r.face == "hi":
                return pts, (z_split if chain_ else z_f - 1.0, z_f + r.height)
            return pts, (z_f - r.height, z_split if chain_ else z_f + 1.0)

        def keep_out(r):
            pts, (za, zb) = reach_of(r)
            for b in brackets:
                if b.z0 < zb and b.z1 > za and path_distance(pts, b.centre) < b.radius + r.width / 2 + 1.0:
                    return f"enters {b.name.rsplit(' ', 2)[0]}'s bracket room"
            for (sh_, side_), e in joint_at.items():
                if e.z0 < zb and e.z1 > za and path_distance(pts, e.centre) < e.radius + r.width / 2 + 1.0:
                    return f"enters the {sh_}'s half-shaft joint room ({side_})"
            dense = rr._resample(pts, 1.0) if len(pts) > 1 else pts
            for a_, b_, za_t, zb_t in ties:
                if za_t < zb and zb_t > za and min(path_distance([a_, b_], p) for p in dense) < (t_rib + r.width) / 2 + rr.CLEAR:
                    return "runs into a mount's web"
            return None

        for r in cands:
            why = keep_out(r)
            if why:
                r.refused = [why]
        kept_out = [r for r in cands if r.refused]
        cands = [r for r in cands if not r.refused]
        say(f"ribs kept out of the contract's rooms: {len(kept_out)} ({', '.join(sorted({r.refused[0] for r in kept_out}))})")
    kept, refused = rr.select(cands)
    refused += stepping + kept_out
    # A rib that ends on another (a T) stands only with it.
    while True:
        names = {r.name for r in kept}
        orphans = [r for r in kept if any(a is not None and a.kind == "rib" and a.name not in names for a in r.ends)]
        if not orphans:
            break
        for r in orphans:
            r.refused = ["the rib it ends on was refused"]
        kept = [r for r in kept if r not in orphans]
        refused += orphans
    # As much metal as the optimiser's field and no more, so that the reading and the field are
    # compared at one mass: the field's ribs stand in priority order until the housing would pass
    # the field's mass; those after are refused.
    field_record = None
    if pattern and pattern["kind"] == "field":
        field_kg = json.loads((OUT / f"{pattern['run']}.json").read_text(encoding="utf-8"))["budget_kg"]
        shell_kg = (lower.cut(lo_cavity).Volume() + upper.cut(hi_cavity).Volume()) * s["density"]

        def rib_kg(r):
            section = r.width * (r.height - r.width / 2 + 1.0) + math.pi * r.width**2 / 8  # the pill, sunk 1 mm
            run = r.length() + (abs(z_split - r.build["chain"][0]) if r.build.get("chain") else 0.0)
            return section * run * s["density"]

        spent, past = shell_kg, []
        for r in kept:  # in priority order
            if "share" in r.build and (past or spent + rib_kg(r) > field_kg):
                r.refused = [f"past the field's {field_kg:.2f} kg"]
                past.append(r)
            else:
                spent += rib_kg(r)
        kept = [r for r in kept if r not in past]
        refused += past
        field_record = {
            "field_kg": field_kg,
            "shell_kg": round(shell_kg, 3),
            "ribs_kg": round(spent - shell_kg, 3),
            "offered": len(offered),
            "mostly_on_the_metal": sum(o["share"] >= 0.5 for o in offered),
            "kept": sum("share" in r.build for r in kept),
        }
        say(f"field: {field_record}")
        fit_picture(stem, plan, offered, kept, outline)
    say(f"ribs: {len(kept)} of {len(kept) + len(refused)} candidates kept; refused {len(refused)}")
    for r in refused[:12]:
        say(f"  refused {r.name}: {r.refused[0]}")

    def draw(r):
        """The kept rib, swept with its section's top a full round (`pill`): over its end face from
        what it meets, and a chain on round the corner and 10 mm down the wall. No fillet is
        built after: rounded rib by rib and fused, each 2 mm flat left a sliver where ribs met, and
        Kalyani's cover would not mesh (22:33)."""
        up = 1.0 if r.face == "hi" else -1.0
        pts = np.asarray(r.points, float)
        if r.face == "hi":
            z_f = z_drum
        elif r.build.get("z") is not None:
            z_f = r.build["z"]  # a field's ring, on the one level it was offered on
        else:
            z_f = face_at(tuple(pts[len(pts) // 2])) if r.kind not in ("wheel", "ring") else face_lo["input"]
        for a_, b_ in zip(pts[:-1], pts[1:], strict=True):
            rib_boxes.append({"poly": strip(tuple(a_), tuple(b_), r.width, z_f, z_f + up * r.height)[1], "z": tuple(sorted((z_f - up, z_f + up * r.height)))})
        chain = r.build.get("chain")
        try:
            # (straight runs, which the corrected Frenet frame cannot sweep, swept in their plane:
            # only without the motor's flange, so a design with one is drawn exactly as before)
            if chain:
                return chain_rib(pts, chain[0], up, chain[1], r.width, r.height, z_split, draft, s["corner_out"], t_f, not motor)
            if r.is_ring:
                return ring_pill(pts, z_f, up, r.width, r.height)
            return face_rib(pts, z_f, up, r.width, r.height, not motor)
        except Exception as error:  # noqa: BLE001 - a sweep OCC refuses leaves the rib out, said
            say(f"  {r.name}: not drawn ({type(error).__name__})")
            return None

    def fused_valid(half, solids, what):
        """The half with its ribs, all in one boolean; if that leaves the solid invalid, rib by rib,
        each kept only if the solid stays one valid solid (Kalyani's cover came out invalid, and
        gmsh then hung on it, 22:53)."""
        if not solids:
            return half
        say(f"  {what}: fusing {len(solids)} at once")
        whole = boolean("fuse", half, fuse([b for _, b in solids]), what)
        if whole is not None and whole.isValid() and len(whole.Solids()) == 1:
            return whole
        say(f"  {what}: the fuse of all at once is invalid; rib by rib")
        for r_name, b in solids:
            trial = boolean("fuse", half, b, r_name)
            if not (trial is not None and trial.isValid() and len(trial.Solids()) == 1):
                # A field body's smooth top meets the skin's faces at a grazing angle: the plain
                # fuse came out invalid; fused with a 0.01 mm fuzz and healed it is one valid
                # solid (the cover of style_field_skin, 01:36). The volume mesh still judges it.
                from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
                from OCP.ShapeFix import ShapeFix_Shape
                from OCP.TopTools import TopTools_ListOfShape

                args_, tools_ = TopTools_ListOfShape(), TopTools_ListOfShape()
                args_.Append(half.wrapped)
                tools_.Append(b.wrapped)
                op = BRepAlgoAPI_Fuse()
                op.SetArguments(args_)
                op.SetTools(tools_)
                op.SetFuzzyValue(0.01)
                op.Build()
                if op.IsDone():
                    fix = ShapeFix_Shape(op.Shape())
                    fix.Perform()
                    trial = cq.Shape.cast(fix.Shape())
                    if trial.isValid() and len(trial.Solids()) == 1:
                        say(f"  {r_name}: fused with a 0.01 mm fuzz and healed")
            if trial is not None and trial.isValid() and len(trial.Solids()) == 1:
                half = trial
            else:
                why = "the boolean failed" if trial is None else ("invalid" if not trial.isValid() else f"{len(trial.Solids())} solids")
                say(f"  {r_name}: left out (it breaks the solid: {why}; itself valid {b.isValid()}, {b.Volume() / 1e3:.0f} cm3)")
                if os.environ.get("GRAMMAR_KEEP"):  # the refused piece and what it met, for a look
                    b.exportBrep(str(OUT / f"{stem}_refused_{r_name.replace(' ', '_')}.brep"))
                    half.exportBrep(str(OUT / f"{stem}_refused_{r_name.replace(' ', '_')}_onto.brep"))
        return half

    lo_solids, hi_solids = [], []
    for r in kept:
        b = draw(r)
        if b is None:
            continue
        if not b.isValid():
            say(f"  {r.name}: its sweep is invalid; left out")
            continue
        (lo_solids if r.face == "lo" else hi_solids).append((r.name, b))
    lower = fused_valid(lower, lo_solids, "the motor side's ribs")
    upper = fused_valid(upper, hi_solids, "the cover's ribs")
    rib_record = {"kept": [{"name": r.name, "face": r.face, "kind": r.kind, "height": r.height} for r in kept],
                  "refused": [{"name": r.name, "why": r.refused} for r in refused], "field": field_record}  # fmt: skip
    say(f"ribs: motor side {len(lo_solids)}, cover {len(hi_solids)} drawn")

    # The field's own metal (LOP-16, `field_body.py`; the engineer, 00:45: the ribs chosen among
    # the generator's still looked "like coming from the generator"): on each end face, the metal
    # the optimiser placed past its skin, in terraces raised along the pull.
    body_record = None
    if pattern and pattern["kind"] == "body":
        import field_body as fb
        from matplotlib.path import Path as Polygon

        plan = np.load(OUT / f"{pattern['run']}_plan.npz")
        xs_, ys_, pitch = plan["xs"], plan["ys"], float(plan["h"])
        X, Y = np.meshgrid(xs_, ys_, indexing="ij")
        on_flat = Polygon(flat_poly).contains_points(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
        clear_of_motor = np.hypot(X - axis["input"][0], Y - axis["input"][1]) > s["motor_room"] + pitch if motor else np.ones(X.shape, bool)
        planes_hi = [z_drum, z_drum + boss_up, z_drum + s["proud"], z_top, *top_of.values(), *(t + s["proud"] for t in top_of.values())]
        planes_lo = [z_base, z_face - t_ring, *face_lo.values(), face_lo["output"] - boss_up, *(f - s["proud"] for f in face_lo.values())]
        made = {"cover": [], "motor_side": []}
        form_ = pattern.get("form", "terraces")

        def field_metal(height, allowed, base, z_level, outward, planes):
            if form_ == "dunes":
                return fb.dunes(height, xs_, ys_, allowed, base, z_level, outward, draft)
            return [body for _, _, body in fb.terraces(height, xs_, ys_, allowed, base, z_level, outward, draft, planes)]

        if rc["levels"] == "rooms":
            # On the optimiser's own skin the field's metal stands where the field put it: each
            # column from the split to the field's reach, over the skin's columns drawn in a voxel
            # (the cavity, cut after, takes back the rooms), the motor's footprint left to it.
            from scipy import ndimage

            # Terraces, not smooth tops: on the skin's stepped faces a smooth top grazed a face and
            # left a 0.27 mm² sliver, and the cover would not mesh (01:37). A terrace's top is a
            # plane kept 2 mm off every face the skin has, and its side meets them square. They
            # start a step under the skin's nearest face: lower ones would lie inside it.
            planes_skin = [z_split, z_split - t_f, z_split + t_f, *face_lo.values(), *top_of.values(), z_face - t_ring,
                           face_lo["output"] - boss_up, *(t + s["proud"] for t in top_of.values())]  # fmt: skip
            for half_, outward_ in (("cover", 1.0), ("motor_side", -1.0)):
                skin_ = ndimage.binary_erosion(plan[f"{half_}_skin"], iterations=1)
                height = np.where(plan[f"{half_}_beyond"] > 0, np.abs(plan[f"{half_}_reach"] - z_split), np.nan)
                allowed = skin_ & (clear_of_motor if half_ == "motor_side" else True)
                nearest = min(abs(v - z_split) for v in (top_of.values() if half_ == "cover" else face_lo.values()))
                # raised from 1 mm inside the half: from the split plane itself, each terrace's
                # foot lay on the flange's face, and two of the cover's fused only with a fuzz,
                # after which the bolts' holes would not cut (01:38)
                made[half_] += [body for _, _, body in fb.terraces(height, xs_, ys_, allowed, z_split + outward_ * 1.0, z_split, outward_, draft, planes_skin, first=nearest - fb.STEP)]
            zones_ = []
        else:
            height = np.where(plan["cover_beyond"] > 0, plan["cover_reach"] - z_drum, np.nan)
            made["cover"] += field_metal(height, on_flat, z_drum - wall / 2, z_drum, +1.0, planes_hi)
        # The motor side, level by level: the base, and each drum's face, a voxel clear of the
        # drum's wall on both sides, so that no terrace's outline runs along it.
        zones = []
        inside_any = np.zeros(X.shape, bool)
        for sh in drum_lo if rc["levels"] != "rooms" else []:
            xd, yd, rd = drum_circle(sh, z_base)
            dist = np.hypot(X - xd, Y - yd)
            zones.append((sh, face_lo[sh], dist < drum_circle(sh, face_lo[sh])[2] - pitch))
            inside_any |= dist < rd + pitch
        if rc["levels"] != "rooms":
            zones.append(("base", z_base, ~inside_any))
        for _, z_level, zone in zones:
            height = np.where(plan["motor_side_beyond"] > 0, z_level - plan["motor_side_reach"], np.nan)
            made["motor_side"] += field_metal(height, on_flat & clear_of_motor & zone, z_level + wall / 2, z_level, -1.0, planes_lo)
        lower = fused_valid(lower, [(f"terrace {k}", b) for k, b in enumerate(made["motor_side"])], "the motor side's field metal")
        upper = fused_valid(upper, [(f"terrace {k}", b) for k, b in enumerate(made["cover"])], "the cover's field metal")
        body_record = {"run": pattern["run"], "form": form_, "bodies": {half: len(v) for half, v in made.items()}, "step_mm": fb.STEP if form_ == "terraces" else None}
        say(f"field metal ({form_}): {body_record['bodies']} bodies")

    # The cavities, then the bosses inside, kept out of every moving part's room.
    lower = lower.cut(lo_cavity)
    upper = upper.cut(hi_cavity)
    rooms = fuse([
        cylinder(st.axis, p.z_min - axial, p.z_max + axial, p.diameter + 2 * radial)
        for st in chain.layout.shafts for p in st.parts if p.kind in ("gear", "carrier")
    ])  # fmt: skip
    # Each bearing goes in from the split: its outside Ø, from its seat to the split, stays clear
    # of every other boss (the intermediate's tube overhung the input's seat by 0.5 mm, 19:12).
    fitting = {
        id(b): cylinder(b["axis"], *sorted((b["z"][1] if b["side"] == "-z" else b["z"][0], z_split)), b["D"] + 1.0)
        for b in bearings
    }
    for b in bearings if rc["levels"] != "rooms" else []:  # rooms: the skin's wall round each bore is its seat
        z0, z1 = b["z"]
        r_in = b["boss_r"] - (1.5 if b in up_bearings else 0.0)  # inside a bridge's drafted wall
        if b["side"] == "-z":
            tube = cylinder(b["axis"], face_lo[b["shaft"]] + wall - 1.0, z1, 2 * r_in)
            # Where a deeper drum's hollow passes under this boss, the boss stands on that drum's
            # floor: a seat's floor hung over a hollow is a shelf no core can leave (the
            # intermediate's, over the input's and the output's drums: 40 cm² on every drum
            # design, 20:55).
            for d, (hollow, (xh, yh, rh)) in hollow_of.items():
                if face_lo[d] < face_lo[b["shaft"]] - 1e-6 and math.dist(b["axis"], (xh, yh)) < rh + r_in:
                    column = boolean("intersect", cylinder(b["axis"], face_lo[d] + wall - 1.0, face_lo[b["shaft"]] + wall, 2 * r_in), hollow, f"the {b['shaft']}'s column")
                    if column is not None and column.Volume() > 1.0:
                        tube = tube.fuse(column)
        elif b in up_bearings:
            tube = cylinder(b["axis"], z0, top_of[b["shaft"]] - wall + 1.0, 2 * r_in)
        else:
            tube = cylinder(b["axis"], z0, z_drum - wall + 1.0, 2 * r_in)
        tube = tube.cut(rooms)
        for other in bearings:
            if other is not b and other["side"] == b["side"]:
                tube = tube.cut(fitting[id(other)])
        # Where the boss is the silhouette itself (its circle the shaft's, with no motor's ring to
        # grow it), the drafted outside runs inside the tube's cylinder away from the split: the
        # tube is cut to it, or it stood up to 1.7 mm proud below the split, a ledge at its top and
        # a 0.3 mm sliver (the input's, contract_avl, 19:33).
        if b["side"] == "-z" and circle_of[b["shaft"]][2] < r_in + (z_split - (face_lo[b["shaft"]] + wall - 1.0)) * shrink + 0.5:
            tube = boolean("intersect", tube, lo_outer, f"the {b['shaft']}'s boss inside the drafted wall") or tube
        if b["side"] == "-z":
            lower = lower.fuse(tube)
        else:
            upper = upper.fuse(tube)
    say("bosses inside")

    # A half-shaft's joint room starts at its shaft's own end face (A27): where the housing's end
    # face stands beyond that (one flat face at the deepest stack's end), it is recessed to it, and
    # the seat's shoulder stands a wall in from there.
    recess = {}
    for (sh_, side_) in joint_at:
        if side_ == "-z" and face_lo.get(sh_, ends[sh_][0]) < ends[sh_][0] - 1e-6:
            recess[(sh_, side_)] = ends[sh_][0]
        if side_ == "+z" and top_of.get(sh_, z_drum) > ends[sh_][1] + 1e-6:
            recess[(sh_, side_)] = ends[sh_][1]

    # Seats, shoulders and seal bores; holes.
    for b in bearings:
        z0, z1 = b["z"]
        # The seat runs to the end wall's inside face where the bearing all but touches it (the
        # wall is then its shoulder); otherwise a shoulder ring stands between, cut from that face
        # exactly, so no sub-millimetre step is left in the wall.
        if b["side"] == "-z":
            wall_in = max(face_lo[b["shaft"]], recess.get((b["shaft"], "-z"), -math.inf)) + wall
            close = z0 - wall_in < 2.0
            lower = lower.cut(cylinder(b["axis"], wall_in if close else z0, z1 + 1e-3, b["D"]))
            if not close:
                lower = lower.cut(cylinder(b["axis"], wall_in, z0 + 1e-3, b["D"] - 2 * s["shoulder"]))
            if b["sealed"]:
                reach_out = 300.0 if body_record else max(t_ring, boss_up) + 2.0  # through the field's metal too
                lower = lower.cut(cylinder(b["axis"], face_lo[b["shaft"]] - reach_out, z0 + 1e-3, b["d"] + 2 * s["seal_radial"]))
        else:
            top = top_of[b["shaft"]] if b in up_bearings else z_drum
            wall_in = min(top, recess.get((b["shaft"], "+z"), math.inf)) - wall
            close = wall_in - z1 < 2.0
            upper = upper.cut(cylinder(b["axis"], z0 - 1e-3, wall_in if close else z1, b["D"]))
            if not close:
                upper = upper.cut(cylinder(b["axis"], z1 - 1e-3, wall_in, b["D"] - 2 * s["shoulder"]))
            if b["sealed"]:
                upper = upper.cut(cylinder(b["axis"], z1 - 1e-3, top + (300.0 if body_record else s["proud"] + 2.0), b["d"] + 2 * s["seal_radial"]))
    # Every bearing's path in from the split, cut clear at the end: whatever stands in it would
    # stop the bearing going in (a lump of the bridge did, 19:20).
    for b in bearings:
        if b["side"] == "-z":
            lower = lower.cut(fitting[id(b)])
        else:
            upper = upper.cut(fitting[id(b)])
    for (sh_, side_), level in recess.items():
        e = joint_at[(sh_, side_)]
        if side_ == "-z":
            lower = lower.cut(cylinder(e.centre, level - 600.0, level, 2 * e.radius))
        else:
            upper = upper.cut(cylinder(e.centre, level, level + 600.0, 2 * e.radius))
        say(f"the {sh_}'s end face recessed to its own end at {level:.2f} for the half-shaft's joint ({side_})")
    for c in bolts:
        lower = lower.cut(cylinder(c, z_split - t_f - 1.0, z_split + 1.0, s["bolt_hole"]))
        upper = upper.cut(cylinder(c, z_split - 1.0, z_split + t_f + 1.0, s["bolt_hole"]))
    for m in mounts:
        if "name" in m:  # the contract's: through its boss
            lower = lower.cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, m["hole"]))
        else:
            lower = lower.cut(cylinder(m["centre"], z_face - 1.0, z_split + 1.0, s["mount_hole"]))
    motor_holes = []
    for k in range(s["motor_bolts"] if motor else 0):
        a = 2 * math.pi * k / s["motor_bolts"]
        c = (axis["input"][0] + s["motor_bolt_circle"] / 2 * math.cos(a), axis["input"][1] + s["motor_bolt_circle"] / 2 * math.sin(a))
        lower = lower.cut(cylinder(c, z_face - t_ring - 1.0, z_face, s["bolt_hole"]))
        motor_holes.append(c)
    lower, upper = lower.clean(), upper.clean()

    def one_body(shape, name):
        solids = sorted(shape.Solids(), key=lambda x: x.Volume(), reverse=True)
        if len(solids) > 1:
            say(f"{name}: {len(solids) - 1} loose pieces dropped, {sum(x.Volume() for x in solids[1:]) / 1e3:.1f} cm3")
            return solids[0]
        return solids[0] if solids else shape

    lower, upper = one_body(lower, "motor side"), one_body(upper, "cover")
    lower, upper = meshable(lower, "motor side"), meshable(upper, "cover")
    say(f"halves: motor side valid {lower.isValid()}, {len(lower.Faces())} faces; cover valid {upper.isValid()}, {len(upper.Faces())} faces")

    # What stands in the contract's rooms, measured on the halves (cm³): nothing, unless the
    # contract's own volumes overlap, as a bracket's room crossing the wall round a gear room does.
    occupied = {}
    for c_ in list(sp.brackets) + list(sp.exits):
        room = cylinder(c_.centre, c_.z0, c_.z1, 2 * c_.radius)
        for half, shape in (("motor_side", lower), ("cover", upper)):
            bb = shape.BoundingBox()
            if (c_.z1 <= bb.zmin or c_.z0 >= bb.zmax or c_.centre[0] - c_.radius >= bb.xmax or c_.centre[0] + c_.radius <= bb.xmin
                    or c_.centre[1] - c_.radius >= bb.ymax or c_.centre[1] + c_.radius <= bb.ymin):
                continue
            try:
                v = sum(x.Volume() for x in shape.intersect(room).Solids())
            except Exception:  # noqa: BLE001 - an intersection OCC refuses is said, not guessed
                v = float("nan")
            if not v < 10.0:  # mm³ (a NaN is said too)
                occupied[f"{c_.name}, {half}"] = round(v / 1e3, 2)
    say(f"in the contract's rooms (cm3): {occupied or 'nothing'}")

    names = {
        "motor_side": convex._name_faces(lower, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes),
        "cover": convex._name_faces(upper, bearings, bolts, mounts, motor_holes, z_split, s, rib_boxes),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for half, shape in (("motor_side", lower), ("cover", upper)):
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{stem}_{half}.step"))
        shape.exportBrep(str(OUT / f"{stem}_{half}.brep"))
    mass = {half: shape.Volume() * s["density"] for half, shape in (("motor_side", lower), ("cover", upper))}
    result = {
        "stem": stem,
        "form": "grammar",
        "recipe": rc,
        "ribs": [],
        "rib_rules": rib_record,
        "field_metal": body_record,
        "settings": s,
        "z": {"lo": z_face, "hi": z_top, "split": z_split, "motor": z_face if motor else None, "drum": z_drum},
        "contract": {
            "motor_on_housing": motor,
            "mounts": "the contract's" if sp.mounts else "the grammar's",
            "rooms_occupied_cm3": occupied,  # the housing inside a bracket's or an exit's room
            "conflicts": conflicts,
        },
        "pods": [],
        "silhouette": circles,
        "bridge": bridge,
        "bearings": bearings,
        "mounts": mounts,
        "motor_holes": motor_holes,
        "bolts": bolts,
        "inner_outline": inner.points(),
        "outer_outline": poly,
        "mass_kg": {**mass, "total": sum(mass.values())},
        "faces": {half: {str(k): v for k, v in n.items()} for half, n in names.items()},
    }
    (OUT / f"{stem}.json").write_text(json.dumps(result, indent=1, default=list), encoding="utf-8")
    say(f"mass {result['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f})")
    return result


if __name__ == "__main__":
    # grammar.py [stem] [preset | field:<run>]: a preset's name (PRESETS) builds that style's
    # recipe; field:<run> builds the recipe read from an optimisation's field (topo_read.py),
    # its form as well as its ribs, with no preset (the engineer, 23:41).
    stem_ = sys.argv[1] if len(sys.argv) > 1 else "grammar"
    preset = sys.argv[2] if len(sys.argv) > 2 else None
    if preset and preset.startswith("field:"):
        chosen = json.loads((OUT / f"{preset[6:]}_read.json").read_text(encoding="utf-8"))["recipe"]
    elif preset and preset.startswith("skin:"):
        # The optimiser's own skin (cup.py) with the field's metal on it (field_body.dunes).
        run_ = preset[5:]
        chosen = {
            "outline": {"family": "hull"}, "levels": "rooms", "cover": "rooms", "spokes": "none", "delta": False,
            "ears": False, "wheel": {"spokes": 0, "ring": False}, "rim": False, "motor_ring": "plain",
            "pattern": {"kind": "body", "run": run_, "form": "dunes"}, "settings": {"rib_height": 12.0, "rib": 6.0},
        }  # fmt: skip
    elif preset and preset.split(":")[0] in ("body", "dunes"):
        # The field's own metal on the parts the optimiser was given (field_body.py): the outline
        # read from the field, each gear room at its own depth, a plain tower round each raised
        # bearing, and nothing else of the generator's; the metal in terraces (body:<run>) or with
        # smooth tops (dunes:<run>).
        form_, run_ = preset.split(":", 1)
        read_ = json.loads((OUT / f"{run_}_read.json").read_text(encoding="utf-8"))["recipe"]
        chosen = {
            "outline": read_["outline"], "levels": "drums", "cover": "towers", "spokes": "none", "delta": False,
            "ears": False, "wheel": {"spokes": 0, "ring": False}, "rim": False, "motor_ring": "plain",
            "pattern": {"kind": "body", "run": run_, "form": "dunes" if form_ == "dunes" else "terraces"},
            "settings": {"rib_height": 12.0, "rib": 6.0},
        }  # fmt: skip
    else:
        chosen = PRESETS[preset] if preset else {}
    build(stem_, overrides=chosen.get("settings"), recipe={k: v for k, v in chosen.items() if k != "settings"})
