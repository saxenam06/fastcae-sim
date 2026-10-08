"""Solids by geometric kind, built with CadQuery (OCP), and their tessellation.

Everything is in millimetres in the contract's frame, z along the shafts. A solid's faces keep
the order OCP gives them; the tessellation tags every triangle with the index of the solid it
came from, so the viewer can colour, hide or show each solid on its own.
"""

from __future__ import annotations

import math

import cadquery as cq
import numpy as np

Point = tuple[float, float]


def cylinder(centre: Point, z0: float, z1: float, diameter: float) -> cq.Shape:
    """A cylinder along z from z0 to z1."""
    if z1 <= z0 or diameter <= 0:
        raise ValueError("a cylinder needs z1 > z0 and a positive diameter")
    return (
        cq.Workplane("XY", origin=(0, 0, z0))
        .center(*centre)
        .circle(diameter / 2)
        .extrude(z1 - z0)
        .val()
    )


def ring(centre: Point, z0: float, z1: float, outer: float, inner: float) -> cq.Shape:
    """A ring (a tube) along z: outer and inner diameters."""
    if not 0 < inner < outer:
        raise ValueError("a ring needs 0 < inner < outer")
    return (
        cq.Workplane("XY", origin=(0, 0, z0))
        .center(*centre)
        .circle(outer / 2)
        .circle(inner / 2)
        .extrude(z1 - z0)
        .val()
    )


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


def prism(outline: list[Point], z0: float, z1: float) -> cq.Shape:
    """An outline extruded along z from z0 to z1."""
    return cq.Workplane("XY", origin=(0, 0, z0)).polyline(outline).close().extrude(z1 - z0).val()


def fuse(shapes: list[cq.Shape]) -> cq.Shape:
    """One solid from many (a union)."""
    if not shapes:
        raise ValueError("nothing to fuse")
    out = shapes[0]
    if len(shapes) > 1:
        out = out.fuse(*shapes[1:]).clean()
    return out


def tessellate(
    shapes: list[cq.Shape], tolerance: float = 0.25, angular: float = 0.35
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Triangles of every shape: vertices (n, 3), triangles (m, 3), the shape index of each
    triangle (m,), and each triangle's CAD face (m,), so normals are averaged within a face."""
    vertices, triangles, owner, faces = [], [], [], []
    base = 0
    face_count = 0
    for index, shape in enumerate(shapes):
        for face in shape.Faces():
            points, tris = face.tessellate(tolerance, angular)
            if not tris:
                continue
            vertices.extend((p.x, p.y, p.z) for p in points)
            triangles.extend((a + base, b + base, c + base) for a, b, c in tris)
            owner.extend([index] * len(tris))
            faces.extend([face_count] * len(tris))
            base += len(points)
            face_count += 1
    return (
        np.asarray(vertices, dtype=np.float64).reshape(-1, 3),
        np.asarray(triangles, dtype=np.int64).reshape(-1, 3),
        np.asarray(owner, dtype=np.int64),
        np.asarray(faces, dtype=np.int64),
    )
