"""Plan geometry, seen along the shafts: the convex hull of circles, the outline of their union,
and points spaced evenly round a closed outline. Pure Python, so a tool that needs only the
numbers needs no CAD kernel (`zenryx.geometry.solids` builds the solids from them)."""

from __future__ import annotations

import math

Point = tuple[float, float]


def hull_of_circles(circles: list[tuple[float, float, float]], segments: int = 96) -> list[Point]:
    """The convex hull of circles (x, y, r) as a polygon, anticlockwise: each circle sampled at
    `segments` points, then Andrew's monotone chain."""
    points = []
    for x, y, r in circles:
        for k in range(segments):
            a = 2 * math.pi * k / segments
            points.append((x + r * math.cos(a), y + r * math.sin(a)))
    points = sorted(set((round(px, 6), round(py, 6)) for px, py in points))
    if len(points) < 3:
        raise ValueError("a hull needs at least three points")

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[Point] = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Point] = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def outline_of_circles(
    circles: list[tuple[float, float, float]], step_deg: float = 1.0
) -> list[Point]:
    """The outer boundary of the union of circles (x, y, r) as a polygon, anticlockwise: traced arc
    by arc from its leftmost point, along each circle every `step_deg` degrees until it enters
    another circle, then on along that one from where they cross. Unlike the hull it follows the
    waists between the circles, so every point of it lies on one of them."""
    cs = [(x, y, r) for x, y, r in circles if r > 0]
    if not cs:
        raise ValueError("an outline needs a circle")

    def at(i: int, a: float) -> Point:
        x, y, r = cs[i]
        return (x + r * math.cos(a), y + r * math.sin(a))

    def entered(i: int, p: Point) -> int | None:
        for j, (x, y, r) in enumerate(cs):
            if j != i and math.hypot(p[0] - x, p[1] - y) < r - 1e-9:
                return j
        return None

    step = math.radians(step_deg)
    start = min(range(len(cs)), key=lambda k: cs[k][0] - cs[k][2])
    s = math.pi  # the leftmost point of the leftmost circle lies on the outline: start there
    turn = 2 * math.pi
    i, a = start, s
    out: list[Point] = [at(i, a)]
    for _ in range(int(2 * turn / step) * len(cs) + 8):
        b = a + step
        j = entered(i, at(i, b))
        end = b
        if j is not None:  # the arc enters circle j: the last angle still outside every other
            lo, hi = a, b
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if entered(i, at(i, mid)) is None:
                    lo = mid
                else:
                    hi = mid
            end = lo
        if i == start and math.floor((end - s) / turn) > math.floor((a - s) / turn):
            return out  # back round to the start
        p = at(i, end)
        out.append(p)
        if j is None:
            a = b
        else:
            i, a = j, math.atan2(p[1] - cs[j][1], p[0] - cs[j][0])
    raise RuntimeError("the outline did not close")


def perimeter(outline: list[Point]) -> float:
    """The length round a closed outline."""
    return sum(math.dist(outline[i - 1], outline[i]) for i in range(len(outline)))


def spaced(outline: list[Point], pitch: float, least: int = 4) -> list[Point]:
    """Points evenly round a closed outline, at most `pitch` apart along it: n = max(least,
    ceil(length / pitch)) of them, the k-th (k + 1/2) / n of the way round from its first point."""
    if pitch <= 0:
        raise ValueError("the pitch must be positive")
    total = perimeter(outline)
    n = max(least, math.ceil(total / pitch))
    targets = [(k + 0.5) / n * total for k in range(n)]
    out: list[Point] = []
    run, i = 0.0, 0
    closed = [*outline, outline[0]]
    for t in targets:
        while run + math.dist(closed[i], closed[i + 1]) < t:
            run += math.dist(closed[i], closed[i + 1])
            i += 1
        a, b = closed[i], closed[i + 1]
        f = (t - run) / max(math.dist(a, b), 1e-12)
        out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
    return out
