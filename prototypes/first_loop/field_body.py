"""PROTOTYPE (LOP-16) - an optimiser's field drawn as the housing's own metal, castable along the pull.

The engineer, 10 October 00:45, on the field-read housing whose ribs the field had chosen among the
generator's: "this cad doesn't seem to be like field driven. It still seems like coming from the
generator". So the generator now gives only what the optimiser was not free to change: each gear
room's cup at its own depth, the flange and its bolts, the seats, the motor's ring, the mounts, and
a plain tower round each of the cover's raised bearings. Over that, on each end face, the metal the
field placed past its skin is drawn where the field put it:
- the field's height over the face, per column (`topo_read.py`'s `reach`), smoothed over a voxel;
- cut in terraces every 10 mm, each terrace one smooth closed outline (a periodic spline, holes as
  their own loops) raised along the half's pull from inside the end wall to its level;
- its sides drafted 1.5°, the outline drawn in by the draft at the top and the loft ruled between.
All terraces rise from one base, so their outlines draw in alike and stay nested: the contours of
one smoothed height never cross. The optimiser kept each column one interval along the pull, so the
terraces, stacked from the face, cast as the field does.

Kept out (each a reason the field cannot overrule): the end face's rounded edge (a terrace stands
on the flat only, or its underside hangs over the round); the motor's footprint (the motor sits
there); each tower's, boss's and drum's wall stands in its own level band, so no outline is drawn
along it (an outline along a cylinder leaves hairline faces, CLAUDE.md's sliver rule). Terrace tops
are kept 2 mm or more off every plane the generator draws (the sliver rule's planes).
"""

from __future__ import annotations

import math

import cadquery as cq
import numpy as np
from matplotlib.path import Path as Polygon
from scipy import ndimage
from skimage import measure

STEP = 10.0  # mm between terraces
GAP = 2.0  # mm, the least distance between a terrace's top and another plane
LEAST_AREA = 60.0  # mm², the smallest outline drawn (about 2.4 voxels of 5 mm)


def _signed_area(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def _resample_closed(xy: np.ndarray, step: float) -> np.ndarray:
    ring = np.vstack([xy, xy[:1]])
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))])
    n = max(8, int(math.ceil(s[-1] / step)))
    t = np.linspace(0.0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, ring[:, 0]), np.interp(t, s, ring[:, 1])])


def loops(field: np.ndarray, xs: np.ndarray, ys: np.ndarray, level: float, step: float | None = 4.0) -> list[tuple[np.ndarray, list[np.ndarray]]]:
    """The closed outlines of {field ≥ level}, in mm: (outer, [holes]), each running with the metal
    on its left, about `step` mm between points (None: the contour as traced, which never crosses
    itself; resampled, a narrow neck can be cut across)."""
    pitch = float(xs[1] - xs[0])
    pad = np.pad(field, 1, constant_values=-1e9)  # every contour closes
    polys = []
    for c in measure.find_contours(pad, level):
        xy = np.column_stack([xs[0] + (c[:, 0] - 1) * pitch, ys[0] + (c[:, 1] - 1) * pitch])
        if len(xy) < 6 or np.linalg.norm(xy[0] - xy[-1]) > 1e-6:
            continue
        xy = xy[:-1]
        if abs(_signed_area(xy)) >= LEAST_AREA:
            polys.append(xy)
    paths = [Polygon(p) for p in polys]
    depth = [sum(paths[j].contains_point(tuple(polys[i][0])) for j in range(len(polys)) if j != i) for i in range(len(polys))]
    out = []
    for i in range(len(polys)):
        if depth[i] % 2:
            continue
        holes = [polys[j] for j in range(len(polys)) if depth[j] == depth[i] + 1 and paths[i].contains_point(tuple(polys[j][0]))]
        outer = polys[i] if _signed_area(polys[i]) > 0 else polys[i][::-1]
        holes = [hl if _signed_area(hl) < 0 else hl[::-1] for hl in holes]
        out.append((outer, holes) if step is None else (_resample_closed(outer, step), [_resample_closed(hl, step) for hl in holes]))
    return out


def _drawn_in(points: np.ndarray, d: float) -> np.ndarray:
    """The closed loop moved d into the metal on its left, point by point."""
    t = np.roll(points, -1, axis=0) - np.roll(points, 1, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    return points + d * np.column_stack([-t[:, 1], t[:, 0]])


def _spline(points: np.ndarray, z: float, params: list[float]) -> cq.Wire:
    return cq.Wire.assembleEdges([cq.Edge.makeSpline([cq.Vector(float(x), float(y), z) for x, y in points], periodic=True, parameters=params)])


def _side(points: np.ndarray, z0: float, z1: float, d: float) -> cq.Shape:
    """One loop's drafted side, ruled between the loop at z0 and the loop drawn in by d at z1: both
    splines take the base loop's parameters, so each ruling joins a point to its own drawn-in
    point (with their own chord lengths the rulings slewed round the loop and leant the sides past
    the draft: 15.7 cm² of undercut on the first build's cover, 01:00)."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections

    ring = np.vstack([points, points[:1]])
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))])
    params = list(s / s[-1])
    # OCC's own matching of the two loops (CheckCompatibility, on in CadQuery's makeLoft) moves
    # their seams and re-spaces them by length, and slewed the rulings again: 22.4 cm² (01:14).
    loft = BRepOffsetAPI_ThruSections(True, True)
    loft.CheckCompatibility(False)
    loft.AddWire(_spline(points, z0, params).wrapped)
    loft.AddWire(_spline(_drawn_in(points, d), z1, params).wrapped)
    loft.Build()
    return cq.Shape.cast(loft.Shape())


def raised(outer: np.ndarray, holes: list[np.ndarray], z0: float, z1: float, draft: float) -> cq.Shape | None:
    """The outline raised from z0 to z1, drawn in by the draft toward z1; None if OCC refuses it
    or the draft closes it."""
    d = abs(z1 - z0) * math.tan(math.radians(draft))
    try:
        body = _side(outer, z0, z1, d)
        for hl in holes:
            body = body.cut(_side(hl, z0, z1, d))
    except Exception:  # noqa: BLE001 - a refused loft leaves the terrace out, said by the caller
        return None
    return body if body.isValid() and body.Volume() > 1.0 else None


def clear_of(z: float, planes: list[float], outward: float) -> float:
    """z moved outward until it stands GAP or more off every plane."""
    for _ in range(20):
        near = [p for p in planes if abs(z - p) < GAP]
        if not near:
            return z
        z = max(near) + GAP if outward > 0 else min(near) - GAP
    return z


def dunes(height: np.ndarray, xs: np.ndarray, ys: np.ndarray, allowed: np.ndarray, base: float, z_face: float, outward: float, draft: float, least: float = 6.0, sigma: float = 1.5):
    """The field's metal on one zone of an end face as smooth bodies: each region where the
    smoothed height reaches `least` (its outline drafted, as a terrace's), topped by one smooth
    surface through the field's height (at least `least` over the face, so no lens thinner than a
    rib is left), fitted as a B-spline over the whole grid. A height over the face, so every column
    is one interval along the pull: castable as the field is. Returns [solid]."""
    soft = ndimage.gaussian_filter(ndimage.binary_erosion(allowed, iterations=2).astype(float), 1.0)
    field = ndimage.gaussian_filter(np.where(np.isfinite(height), height, 0.0), sigma) * soft
    if float(field.max()) < least:
        return []
    # The floor at `least` is softened too: with its kink left in, the fit swung ±500 mm (01:16).
    top = z_face + outward * ndimage.gaussian_filter(np.maximum(field, least), 1.0)
    grid = [[cq.Vector(float(x), float(y), float(top[i, j])) for j, y in enumerate(ys)] for i, x in enumerate(xs)]
    surface = cq.Face.makeSplineApprox(grid, tol=0.5, maxDeg=3)
    box = surface.BoundingBox()
    if box.zmin < float(top.min()) - 5.0 or box.zmax > float(top.max()) + 5.0:
        return []  # the fit left the field's own range: no smooth top
    reach = float(np.abs(top - base).max()) + 20.0
    under = cq.Solid.extrudeLinear(surface, cq.Vector(0.0, 0.0, -outward * reach))  # from the surface back past the base
    out = []
    for outer, holes in loops(field, xs, ys, least):
        prism = raised(outer, holes, base, z_face + outward * (float(field.max()) + 10.0), draft)
        if prism is None:
            continue
        try:
            body = prism.intersect(under)
        except Exception:  # noqa: BLE001 - a refused intersection leaves the region out
            continue
        if body.isValid() and body.Volume() > 1.0:
            out.append(body)
    return out


def terraces(height: np.ndarray, xs: np.ndarray, ys: np.ndarray, allowed: np.ndarray, base: float, z_face: float, outward: float, draft: float, planes: list[float], first: float = 0.0):
    """The terraces of one zone of an end face: its field height (mm past the face at z_face, per
    column) smoothed over a voxel and kept to the allowed columns (drawn in by two voxels, then
    softened, so no outline reaches a kept-out band), cut every STEP from `first` on; each raised
    from `base` (inside the end wall) to its level. Returns [(level mm, top z, solid)]."""
    soft = ndimage.gaussian_filter(ndimage.binary_erosion(allowed, iterations=2).astype(float), 1.0)
    field = ndimage.gaussian_filter(np.where(np.isfinite(height), height, 0.0), 1.0) * soft
    out = []
    level = STEP / 2 + STEP * max(0, math.floor((first - STEP / 2) / STEP))
    while level < float(field.max()):
        top = clear_of(z_face + outward * (level + STEP / 2), planes, outward)
        for outer, holes in loops(field, xs, ys, level):
            body = raised(outer, holes, base, top, draft)
            if body is not None:
                out.append((level, top, body))
        level += STEP
    return out
