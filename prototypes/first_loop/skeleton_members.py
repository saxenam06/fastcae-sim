"""Generator B of approach 2 (LOP-25; the engineer's plan of 12 October, `zenryx_new_plan.md` §4): the field's
members rebuilt along their skeleton, with variable sections, in place of the field's own surface.

A half's members (the field's metal, less what the contract fixes, on the drawing's 2 mm grid) are read in plan:
each column's metal is one run along the pull (the height field's), so the members are their footprint in plan
and each column's run. The footprint is cleaned (opened and closed, islands under `ISLAND` cells dropped) and
thinned to its skeleton (skimage); the skeleton's terminal branches shorter than `prune` mm are pruned; each
branch between its junctions and ends is smoothed (a moving average, its ends kept) and resampled every
`STEP` mm. At each point the member's half-width is the footprint's own (its distance to the edge) times
`scale`, at least `LEAST_HALF` mm and at most half of `cap` mm when `cap` is set, and its run is the median
of the column runs near it. The member is the hull of consecutive vertical cylinders (each the half-width
round the point, spanning the run): sides along the pull, so it casts as the field did; a junction is where
branches' cylinders meet. The union is the half's members; `outcome_cad.build_mesh` fuses it with the exact
shell and cuts it as any drawing (LOOP_SKELETON="scale:prune:cap", e.g. "1.0:20:0")."""

import numpy as np

ISLAND = 12  # cells: a footprint piece smaller than this is dropped
STEP = 4.0  # mm between a branch's sampled points
LEAST_HALF = 2.5  # mm: a member at least 5 mm wide
SEGMENTS = 20  # a cylinder's facets


def skeleton_graph(skel: np.ndarray) -> tuple[list[list[tuple[int, int]]], np.ndarray]:
    """The skeleton's branches: each an ordered list of cells between nodes (an end or a junction), and
    the degree of every skeleton cell (its 8-neighbours on the skeleton)."""
    from scipy.ndimage import convolve

    k = np.ones((3, 3), int)
    k[1, 1] = 0
    deg = convolve(skel.astype(int), k, mode="constant") * skel
    nodes = skel & (deg != 2)
    seen = np.zeros_like(skel, bool)
    branches = []
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    ni, nj = skel.shape

    def neighbours(c):
        i, j = c
        for di, dj in nb:
            a, b = i + di, j + dj
            if 0 <= a < ni and 0 <= b < nj and skel[a, b]:
                yield (a, b)

    for start in zip(*np.nonzero(nodes)):
        for first in neighbours(start):
            if seen[first] and not nodes[first]:
                continue
            path = [start, first]
            prev, cur = start, first
            while not nodes[cur]:
                seen[cur] = True
                nxt = [c for c in neighbours(cur) if c != prev and c not in path[-3:]]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                path.append(cur)
            key = tuple(sorted((path[0], path[-1]))) + (len(path),)
            if key not in {tuple(sorted((b[0], b[-1]))) + (len(b),) for b in branches}:
                branches.append(path)
    for start in zip(*np.nonzero(skel & ~seen & ~nodes)):  # loops with no node on them
        if seen[start]:
            continue
        path, prev, cur = [start], None, start
        while True:
            seen[cur] = True
            nxt = [c for c in neighbours(cur) if c != prev and not seen[c]]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            path.append(cur)
        if len(path) > 3:
            branches.append(path + [path[0]])
    return branches, deg


def prune(skel: np.ndarray, length_cells: float, rounds: int = 3) -> np.ndarray:
    """The skeleton with its terminal branches shorter than `length_cells` removed (an end to a junction)."""
    skel = skel.copy()
    for _ in range(rounds):
        branches, deg = skeleton_graph(skel)
        cut = False
        for b in branches:
            a, z = b[0], b[-1]
            ends = [deg[a] == 1, deg[z] == 1]
            if sum(ends) == 1 and len(b) < length_cells:  # a twig: one end free, the other at a junction
                for c in (b[:-1] if ends[0] else b[1:]):
                    skel[c] = False
                cut = True
        if not cut:
            break
    from skimage.morphology import skeletonize

    return skeletonize(skel)


def members_body(own: np.ndarray, lo, h: float, scale: float = 1.0, prune_mm: float = 20.0, cap_mm: float = 0.0, inside=None):
    """The half's members (a manifold3d Manifold) rebuilt along the skeleton of their footprint in plan. With
    `inside` (the plan cells within the shell's outline), the members over the end walls and those beside the
    side walls are read apart: in one footprint they merge into one broad piece whose skeleton's widths fill
    everything (12.1 kg, 12 October 01:36)."""
    import manifold3d as mf

    if inside is not None:
        parts = []
        for keep in (inside, ~inside):
            part = own & keep[:, :, None]
            if part.any():
                parts.append(members_body(part, lo, h, scale, prune_mm, cap_mm))
        return mf.Manifold.batch_boolean(parts, mf.OpType.Add) if parts else mf.Manifold()
    from scipy.ndimage import binary_closing, binary_opening, distance_transform_edt, label
    from skimage.morphology import skeletonize

    has = own.any(axis=2)
    if not has.any():
        return mf.Manifold()
    kk = np.arange(own.shape[2])[None, None, :]
    z0 = np.where(own, kk, 10**6).min(axis=2)
    z1 = np.where(own, kk, -1).max(axis=2)
    foot = binary_closing(binary_opening(has, np.ones((2, 2), bool)), np.ones((3, 3), bool)) & has | has
    lab, n_lab = label(foot)
    if n_lab:
        sizes = np.bincount(lab.ravel())
        keep = sizes >= ISLAND
        keep[0] = False
        foot = keep[lab]
    edt = distance_transform_edt(foot) * h
    skel = prune(skeletonize(foot), prune_mm / h)
    branches, _ = skeleton_graph(skel)
    # the run of a column with metal near each foot cell: its nearest metal column's
    near_i, near_j = np.nonzero(has)
    from scipy.spatial import cKDTree

    tree = cKDTree(np.column_stack([near_i, near_j]))
    solids = []
    for b in branches:
        cells = np.asarray(b, float)
        if len(cells) < 2:
            continue
        # smoothed (a moving average, its ends kept), then sampled every STEP mm
        w = 2
        sm = cells.copy()
        for t in range(1, len(cells) - 1):
            a0, a1 = max(0, t - w), min(len(cells), t + w + 1)
            sm[t] = cells[a0:a1].mean(axis=0)
        seg = np.hypot(*np.diff(sm, axis=0).T) * h
        s = np.r_[0.0, np.cumsum(seg)]
        count = max(2, int(np.ceil(s[-1] / STEP)) + 1)
        at = np.linspace(0.0, s[-1], count)
        pi = np.interp(at, s, sm[:, 0])
        pj = np.interp(at, s, sm[:, 1])
        ci = np.clip(np.rint(pi).astype(int), 0, own.shape[0] - 1)
        cj = np.clip(np.rint(pj).astype(int), 0, own.shape[1] - 1)
        half = np.maximum(LEAST_HALF, scale * edt[ci, cj])
        if cap_mm > 0:
            half = np.minimum(half, 0.5 * cap_mm)
        _, idx = tree.query(np.column_stack([ci, cj]), k=min(5, len(near_i)))
        idx = np.atleast_2d(idx)
        lo_k = np.median(z0[near_i[idx], near_j[idx]], axis=1)
        hi_k = np.median(z1[near_i[idx], near_j[idx]], axis=1)
        zb = lo[2] + h * lo_k
        zt = lo[2] + h * (hi_k + 1.0)
        prev = None
        for t in range(len(at)):
            x = lo[0] + h * (pi[t] + 0.5)
            y = lo[1] + h * (pj[t] + 0.5)
            height = max(float(zt[t] - zb[t]), h)
            cyl = mf.Manifold.cylinder(height, float(half[t]), float(half[t]), SEGMENTS).translate((x, y, float(zb[t])))
            if prev is not None:
                solids.append(mf.Manifold.batch_hull([prev, cyl]))
            prev = cyl
        if len(at) == 1:
            solids.append(prev)
    if not solids:
        return mf.Manifold()
    return mf.Manifold.batch_boolean(solids, mf.OpType.Add)
