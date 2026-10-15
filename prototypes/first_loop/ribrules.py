"""PROTOTYPE (LOP-15) - the rules for clean ribs, after fastcae's (docs/research/
2026-10-09-fastcae-rib-rules.md), read on the plan of the face a rib stands on.

fastcae's rules are multiples of its root fillet R (10 mm on 25 mm ribs: R ≈ 0.4 × the rib, as
production's R5-10 on 20-25 mm ribs). Here R = 3 mm: the production drawing's "all non-specified
radii R3.0" fastcae quotes, and 0.5 × the 6 mm wall of the reducer handbooks' (0.5-1.5)·δ. So:
- **an end on a hard point.** Each end lies on a boss's ring, a wall, the rim, the motor's ring or
  hub, or another rib: never in the open. It arrives there at ARRIVE_DEG or steeper (fastcae's 45°
  in force), on the hard point's own outline;
- **crossings** at CROSS_DEG or steeper, and only in the middle third of both ribs (fastcae's 60°
  and 1/3), unless one of them is a ring (a rim, a boss ring), which a rib takes as a wall;
- **ends apart:** two ends on one hard point stand END_GAP apart, centre to centre (fastcae's
  T/2 + R + R + T/2);
- **clearance:** where two ribs run alongside, within SLOT_DEG of parallel, their faces stand
  CLEAR apart (fastcae's 2 R, read face to face);
- **heights:** an end's top stands FLUSH under the top of what it meets (fastcae's flush = R, in
  force), and every rib stands at least LEAST tall (2 R).
Rib tops are rounded by EDGE = (thickness - 2) / 2, at most 2.5 mm, so a 2 mm flat is left and the
two rounds never meet (fastcae's tip guard, t ≥ 2r + 2).

The selection keeps, in priority order, every rib that breaks no rule against the ribs kept before
it. That is greedy; fastcae chose its set by CP-SAT, which this repository does not carry (OR-Tools
is not among its dependencies). Pockets (fastcae's 55 mm, here 17) are not yet read.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

R_ROOT = 3.0  # mm
ARRIVE_DEG = 45.0
CROSS_DEG = 60.0
CROSS_SHARE = 1.0 / 3.0
FLUSH = R_ROOT
LEAST = 2.0 * R_ROOT
CLEAR = 2.0 * R_ROOT
SLOT_DEG = 30.0
BEND = 8.0  # a curved rib turns no tighter than BEND x its thickness in plan (fastcae's 200 mm on 25 mm ribs)


def tightest_radius(points: np.ndarray) -> float:
    """The least radius of the circle through three neighbouring stations of a path, in plan."""
    pts = _resample(np.asarray(points, float), 4.0)
    least = math.inf
    for a, b, c in zip(pts[:-2], pts[1:-1], pts[2:], strict=True):
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        cross = abs(float((b - a)[0] * (c - a)[1] - (b - a)[1] * (c - a)[0]))
        if cross > 1e-9:
            least = min(least, ab * bc * ca / (2.0 * cross))
    return least


def end_gap(t1: float, t2: float) -> float:
    return t1 / 2 + R_ROOT + R_ROOT + t2 / 2


def edge_round(thickness: float) -> float:
    return min(2.5, (thickness - 2.0) / 2.0)


@dataclass
class Anchor:
    """What a rib's end meets: a circle (a boss's ring, the motor's ring or hub) or a polyline (a
    wall's outline, the rim), with the height its top stands off the face."""

    kind: str
    circle: tuple[float, float, float] | None = None
    line: np.ndarray | None = None
    top: float | None = None
    name: str = ""

    def tangent_at(self, p: np.ndarray) -> np.ndarray:
        if self.circle is not None:
            cx, cy, _ = self.circle
            rad = p - np.array([cx, cy])
            return np.array([-rad[1], rad[0]]) / max(np.linalg.norm(rad), 1e-9)
        seg = _nearest_segment(self.line, p)
        d = self.line[seg + 1] - self.line[seg]
        return d / max(np.linalg.norm(d), 1e-9)


@dataclass
class Rib:
    name: str
    face: str  # the face it stands on: "lo" (the motor side's end face), "hi" (the cover's), "side"
    points: np.ndarray  # (m, 2), its middle line in plan
    width: float
    height: float  # off its face
    kind: str  # "spoke", "side", "fan", "line", "rim", "ring", "wheel", "ear", "delta"
    priority: int
    ends: tuple[Anchor | None, Anchor | None] = (None, None)
    chain: str = ""  # ribs of one chain (a spoke and the side rib it turns into) are not judged against each other
    build: dict = field(default_factory=dict)  # how grammar.py draws it
    refused: list = field(default_factory=list)

    @property
    def is_ring(self) -> bool:
        return self.kind in ("rim", "ring")

    def length(self) -> float:
        return float(np.linalg.norm(np.diff(self.points, axis=0), axis=1).sum())


def _nearest_segment(line: np.ndarray, p: np.ndarray) -> int:
    a, b = line[:-1], line[1:]
    ab = b - a
    t = np.clip(np.einsum("ij,ij->i", p - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
    d = np.linalg.norm(a + t[:, None] * ab - p, axis=1)
    return int(np.argmin(d))


def _direction(points: np.ndarray, end: int) -> np.ndarray:
    """The rib's direction leaving its end `end` (0 or 1), pointing along the rib."""
    if end == 0:
        d = points[min(1, len(points) - 1)] - points[0]
    else:
        d = points[-2] - points[-1]
    return d / max(np.linalg.norm(d), 1e-9)


def arrival_deg(rib: Rib, end: int) -> float | None:
    anchor = rib.ends[end]
    if anchor is None:
        return None
    p = rib.points[0] if end == 0 else rib.points[-1]
    t = anchor.tangent_at(p)
    d = _direction(rib.points, end)
    return math.degrees(math.asin(min(1.0, abs(float(d[0] * t[1] - d[1] * t[0])))))


def _crossings(a: np.ndarray, b: np.ndarray):
    """Every crossing of two polylines: (point, fraction along a, fraction along b, angle deg)."""
    out = []
    la = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(a, axis=0), axis=1))])
    lb = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(b, axis=0), axis=1))])
    for i in range(len(a) - 1):
        p, r = a[i], a[i + 1] - a[i]
        for j in range(len(b) - 1):
            q, s = b[j], b[j + 1] - b[j]
            den = r[0] * s[1] - r[1] * s[0]
            if abs(den) < 1e-12:
                continue
            t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
            u = ((q[0] - p[0]) * r[1] - (q[1] - p[1]) * r[0]) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                ang = math.degrees(math.asin(min(1.0, abs(den) / (np.linalg.norm(r) * np.linalg.norm(s)))))
                out.append((p + t * r, (la[i] + t * np.linalg.norm(r)) / la[-1], (lb[j] + u * np.linalg.norm(s)) / lb[-1], ang))
    return out


def _alongside(a: Rib, b: Rib, skip_near: list[np.ndarray]) -> float | None:
    """The least face-to-face gap where a runs alongside b within SLOT_DEG of parallel, away from
    their crossings and shared ends; None if they never do."""
    least = None
    pts = _resample(a.points, 4.0)
    for k in range(len(pts)):
        p = pts[k]
        if any(np.linalg.norm(p - c) < 2 * (a.width + b.width) + 2 * R_ROOT for c in skip_near):
            continue
        seg = _nearest_segment(b.points, p)
        q0, q1 = b.points[seg], b.points[seg + 1]
        d_b = (q1 - q0) / max(np.linalg.norm(q1 - q0), 1e-9)
        d_a = pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]
        d_a = d_a / max(np.linalg.norm(d_a), 1e-9)
        if math.degrees(math.acos(min(1.0, abs(float(d_a @ d_b))))) > SLOT_DEG:
            continue
        t = np.clip(float((p - q0) @ (q1 - q0)) / max(float((q1 - q0) @ (q1 - q0)), 1e-12), 0, 1)
        gap = float(np.linalg.norm(q0 + t * (q1 - q0) - p)) - (a.width + b.width) / 2
        least = gap if least is None else min(least, gap)
    return least


def _resample(points: np.ndarray, step: float) -> np.ndarray:
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(math.ceil(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(t, s, points[:, 0]), np.interp(t, s, points[:, 1])])


def own_rules(rib: Rib) -> list[str]:
    """What a rib breaks on its own: an end in the open, a shallow arrival, too low, an end over
    what it meets."""
    out = []
    if rib.is_ring:
        return out
    for end in (0, 1):
        anchor = rib.ends[end]
        if anchor is None:
            out.append(f"end {end} meets nothing")
            continue
        if anchor.kind == "corner":  # a side rib's end over the corner: carried on by its chain's spoke
            continue
        ang = arrival_deg(rib, end)
        if ang is not None and ang < ARRIVE_DEG:
            out.append(f"end {end} arrives at {ang:.0f}° on {anchor.name or anchor.kind} (at least {ARRIVE_DEG:.0f}°)")
        if anchor.top is not None and rib.height > anchor.top - FLUSH + 1e-6 and not (anchor.kind == "rib" and abs(rib.height - anchor.top) < 0.5):
            # (a T between ribs of one height is a junction: their rounded tops merge)
            out.append(f"end {end} stands {rib.height:.0f} mm against {anchor.name or anchor.kind}'s {anchor.top:.0f} (at least {FLUSH:.0f} under)")
    if rib.height < LEAST - 1e-6:
        out.append(f"{rib.height:.0f} mm tall (at least {LEAST:.0f})")
    if len(rib.points) > 2:
        bend = tightest_radius(rib.points)
        if bend < BEND * rib.width:
            out.append(f"turns at a {bend:.0f} mm radius (at least {BEND * rib.width:.0f})")
    return out


def pair_rules(a: Rib, b: Rib) -> list[str]:
    """What two ribs on one face break together."""
    if a.face != b.face or (a.chain and a.chain == b.chain and "side" in (a.kind, b.kind)):
        return []  # a side rib and the spoke it turns into are one rib round the corner
    out = []
    near = []
    for p, fa, fb, ang in _crossings(a.points, b.points):
        near.append(p)
        if a.is_ring or b.is_ring:
            if ang < ARRIVE_DEG:
                out.append(f"crosses {b.name if a.is_ring else a.name}'s ring at {ang:.0f}°")
            continue
        at_end = min(fa, 1 - fa) < 0.02 or min(fb, 1 - fb) < 0.02  # an end on the other: a T
        if at_end:
            if ang < ARRIVE_DEG:
                out.append(f"meets {b.name} at {ang:.0f}°")
            continue
        if ang < CROSS_DEG:
            out.append(f"crosses {b.name} at {ang:.0f}° (at least {CROSS_DEG:.0f}°)")
        elif min(fa, 1 - fa) < CROSS_SHARE or min(fb, 1 - fb) < CROSS_SHARE:
            out.append(f"crosses {b.name} outside the middle third of both")
    for ea in (0, 1):
        for eb in (0, 1):
            if a.is_ring or b.is_ring or a.ends[ea] is None or b.ends[eb] is None or a.ends[ea].kind == "corner":
                continue
            pa, pb = (a.points[0] if ea == 0 else a.points[-1]), (b.points[0] if eb == 0 else b.points[-1])
            if a.ends[ea].name and a.ends[ea].name == b.ends[eb].name:
                near.append(pa)
                gap = float(np.linalg.norm(pa - pb))
                if gap < end_gap(a.width, b.width):
                    out.append(f"its end stands {gap:.0f} mm from {b.name}'s on {a.ends[ea].name} (at least {end_gap(a.width, b.width):.0f})")
    if not (a.is_ring or b.is_ring):
        gap = _alongside(a, b, near)
        if gap is not None and gap < CLEAR:
            out.append(f"runs {gap:.1f} mm from {b.name}, face to face (at least {CLEAR:.0f})")
    return out


def select(candidates: list[Rib]) -> tuple[list[Rib], list[Rib]]:
    """The ribs kept, in priority order, each against every rule with those kept before it; and
    the ribs refused, each with its reasons."""
    kept, refused = [], []
    for rib in sorted(candidates, key=lambda r: (-r.priority, r.name)):
        why = own_rules(rib)
        if not why:
            for other in kept:
                why += pair_rules(rib, other)
                if why:
                    break
        if why:
            rib.refused = why
            refused.append(rib)
        else:
            kept.append(rib)
    return kept, refused
