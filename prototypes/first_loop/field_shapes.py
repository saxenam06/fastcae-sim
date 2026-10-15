"""PROTOTYPE (LOP-30) - what shapes the spline space's fields can make (the engineer, 14 October 19:59: "Show me some
interesting shapes that can be obtained from the current fields space"): two rib layouts and two brackets, each drawn from control points on the
optimiser's own knots (the outline field every 6 mm within +-8 mm, the heights every 12 mm; members at least 8 mm wide,
8 mm apart and 8 mm high) with the proposed section rule (top edges rounded, roots filleted; `member_section_demo.py`).
The control points are set by hand to sketch each shape; in a run the optimiser sets them. The second bracket uses the
proposed start field (where each column's metal starts, today fixed at the split or the wall); the others use the current two fields alone. Every shape keeps
one metal interval along the pull at every point, so a two-part mould casts it.

    field_shapes.py [--round 4] [--fillet 4] [--out field_shapes.png]

Writes the picture into data/first_loop.
"""

import argparse
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import member_section_demo as msd  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

R = msd.RANGE
SIDE = ((-8.0, 84.0), (-54.0, 54.0), (-80.0, 4.0))  # the brackets' scene: x out from the side wall, y along it, z the pull
LUG = (62.0, 0.0, 13.0, 6.5, -30.0, -55.0)  # its centre, outer and bore radii, top and bottom


def grid(box, h):
    return [np.arange(lo, hi + 1e-9, h, dtype=np.float32) for lo, hi in box]


def bezier(*pts, n=1200):
    """A Bezier curve on its control points, sampled n times."""
    s = np.linspace(0.0, 1.0, n)[:, None]
    p = [np.broadcast_to(np.asarray(q, float), (n, 2)) for q in pts]
    while len(p) > 1:
        p = [(1 - s) * a + s * b for a, b in zip(p[:-1], p[1:], strict=True)]
    return p[0]


def members_targets(members, X, Y):
    """The members' union sketched in plan: how far each point lies inside (mm), and its height from the member it is in.
    Each member is a curve with its half-width and height running linearly from its start to its end."""
    P = np.column_stack([X.ravel(), Y.ravel()])
    best, height = np.full(len(P), -1e9), np.zeros(len(P))
    for m in members:
        d, i = cKDTree(m["c"]).query(P)
        s = i / (len(m["c"]) - 1.0)
        inside = m["w"][0] + (m["w"][1] - m["w"][0]) * s - d
        take = inside > best
        best = np.where(take, inside, best)
        height = np.where(take, m["t"][0] + (m["t"][1] - m["t"][0]) * s, height)
    return best.reshape(X.shape), {"t": height.reshape(X.shape)}


def fit_c(target, xs, ys, s, clip=None):
    """A field's control points on knots s apart set to sketch a target: the field they give, their values and places."""
    bx, by = msd.basis(xs, xs[0], xs[-1], s), msd.basis(ys, ys[0], ys[-1], s)
    c = np.linalg.pinv(bx) @ target @ np.linalg.pinv(by).T
    if clip is not None:
        c = np.clip(c, -clip, clip)
    at = (xs[0] + s * (np.arange(c.shape[0]) - 1.0), ys[0] + s * (np.arange(c.shape[1]) - 1.0))
    return (bx @ c @ by.T).astype(np.float32), c, at


def wall_shape(members, bosses, box, r, rf, h=0.5, z_top=30.0):
    """Ribs standing on a 4 mm wall (its outer face z = 0, the pull +z), with bosses (x, y, outer r, bore r, height)."""
    xs, ys, zs = grid((*box, (-7.0, z_top)), h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    phi_t, v = members_targets(members, X, Y)
    phi, c, at = fit_c(np.clip(phi_t, -R, R), xs, ys, 6.0, R)
    t = fit_c(v["t"], xs, ys, 12.0)[0]
    A, T, Z = msd.distance_in(phi, h)[:, :, None], t[:, :, None], zs[None, None, :]
    (x0, x1), (y0, y1) = box
    plate = np.maximum(np.maximum(X - (x1 - 4.0), (x0 + 4.0) - X), np.maximum(Y - (y1 - 4.0), (y0 + 4.0) - Y))
    f = msd.round_union(np.maximum(msd.round_inter(-A, Z - T, r), -2.0 - Z), np.maximum(plate[:, :, None], np.maximum(Z, -4.0 - Z)), rf)
    for bx, by, ro, _, hb in bosses:
        rho = np.hypot(X - bx, Y - by)[:, :, None]
        f = msd.round_union(f, np.maximum(rho - ro, np.maximum(Z - hb, -4.0 - Z)), rf)
    for bx, by, _, ri, _ in bosses:
        f = np.maximum(f, ri - np.hypot(X - bx, Y - by)[:, :, None])  # the bores, machined
    return f, (xs[0], ys[0], zs[0]), h, (at, c, xs, ys, phi)


def side_shape(make, r, rf, h=0.5):
    """A bracket outside a side wall (its outer face x = 0; the split z = 0, the housing below), with the sealing land along
    the split and a lug at mid-height. With the current fields the bracket hangs from the split to its depth (flat at the
    split, its free edge rounded); with the start field each arm runs between where it starts and where it ends, both chosen."""
    xs, ys, zs = grid(SIDE, h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    phi_t, v = make(X, Y)
    phi, c, at = fit_c(np.clip(phi_t, -R, R), xs, ys, 6.0, R)
    phi = np.minimum(phi, X + 2.5)  # buried in the wall past x = -2.5
    A, Z = msd.distance_in(phi, h)[:, :, None], zs[None, None, :]
    T = fit_c(v["t"], xs, ys, 12.0)[0][:, :, None]
    if "b" in v:
        B = fit_c(v["b"], xs, ys, 12.0)[0][:, :, None]
        arm = msd.round_inter(msd.round_inter(-A, -T - Z, r), Z + B, r)
    else:
        arm = np.maximum(msd.round_inter(-A, -T - Z, r), Z)
    Xc, Yc = X[:, :, None], Y[:, :, None]
    along = np.abs(Yc) - 50.0
    wall = np.maximum(np.maximum(Xc, -4.0 - Xc), np.maximum(along, np.maximum(Z, -76.0 - Z)))
    land = np.maximum(np.maximum(Xc - 10.0, -4.0 - Xc), np.maximum(along, np.maximum(Z, -8.0 - Z)))
    lx, ly, ro, ri, zt, zb = LUG
    rho = np.hypot(X - lx, Y - ly)[:, :, None]
    f = msd.round_union(msd.round_union(msd.round_union(arm, wall, rf), land, rf), np.maximum(rho - ro, np.maximum(Z - zt, zb - Z)), rf)
    return np.maximum(f, ri - rho), (xs[0], ys[0], zs[0]), h, (at, c, xs, ys, phi)


def spider(r, rf):
    """Five curved spokes from a bearing boss, wide and tall at the boss, slimmer and lower outward, tied by a ring."""
    members = []
    for k in range(5):
        rho = np.linspace(20.0, 62.0, 1200)
        th = np.deg2rad(90.0 + 72.0 * k) + np.deg2rad(28.0) * ((rho - 20.0) / 42.0) ** 1.2
        members.append({"c": np.column_stack([rho * np.cos(th), rho * np.sin(th)]), "w": (6.5, 4.0), "t": (20.0, 10.0)})
    ang = np.linspace(0.0, 2.0 * np.pi, 2400)
    members.append({"c": np.column_stack([46.0 * np.cos(ang), 46.0 * np.sin(ang)]), "w": (4.0, 4.0), "t": (12.0, 12.0)})
    return wall_shape(members, [(0.0, 0.0, 24.0, 15.0, 24.0)], ((-74.0, 74.0), (-74.0, 74.0)), r, rf)


def tree(r, rf):
    """One rib from a bearing boss forking twice to three bolt bosses, each branch tapering in width and height."""
    members = [
        {"c": bezier((-30, 0), (-5, 0)), "w": (7.0, 6.0), "t": (18.0, 16.0)},
        {"c": bezier((-5, 0), (22, 14), (52, 36)), "w": (6.0, 4.0), "t": (16.0, 10.0)},
        {"c": bezier((-5, 0), (16, -10), (30, -17)), "w": (6.0, 5.0), "t": (16.0, 13.0)},
        {"c": bezier((30, -17), (44, -26), (52, -36)), "w": (5.0, 4.0), "t": (13.0, 10.0)},
        {"c": bezier((30, -17), (46, -10), (58, 0)), "w": (5.0, 4.0), "t": (13.0, 10.0)},
    ]
    bosses = [(-48.0, 0.0, 22.0, 14.0, 22.0), (55.0, 38.0, 9.0, 4.5, 14.0), (55.0, -38.0, 9.0, 4.5, 14.0), (62.0, 0.0, 9.0, 4.5, 14.0)]
    return wall_shape(members, bosses, ((-76.0, 78.0), (-54.0, 54.0)), r, rf)


def hanging_fork(r, rf):
    """The current fields: two curved arms from the wall forking into one stem at the lug, each deepening toward the lug."""

    def make(X, Y):
        return members_targets(
            [
                {"c": bezier((-3, 30), (22, 22), (40, 1)), "w": (6.0, 5.0), "t": (26.0, 40.0)},
                {"c": bezier((-3, -30), (22, -22), (40, -1)), "w": (6.0, 5.0), "t": (26.0, 40.0)},
                {"c": bezier((38, 0), (62, 0)), "w": (6.0, 7.0), "t": (40.0, 56.0)},
            ],
            X,
            Y,
        )

    return side_shape(make, r, rf)


def web_window(r, rf):
    """The start field: a web from the land to the lug with a window, its top rising toward the lug, its belly fullest
    at the wall's middle."""

    def make(X, Y):
        xx = np.clip(X, 0.0, 62.0)
        web = np.where(X <= 62.0, 34.0 - 21.0 * xx / 62.0 - np.abs(Y), -1e3)
        web = np.maximum(web, LUG[2] - np.hypot(X - LUG[0], Y - LUG[1]))
        window = (np.sqrt(((X - 27.0) / 13.0) ** 2 + (Y / 8.0) ** 2) - 1.0) * 8.0
        top = 8.0 + 22.0 * (np.clip(X - 12.0, 0.0, 50.0) / 50.0) ** 1.3  # joined to the land's underside next to the wall
        under = top + 16.0 + 12.0 * (1.0 - xx / 62.0) * (1.0 - np.clip(np.abs(Y) / 34.0, 0.0, 1.0) ** 2)
        return np.minimum(web, window), {"t": under, "b": top}

    return side_shape(make, r, rf)


def plan_panel(ax, info, title, side=False):
    at, c, xs, ys, phi = info
    gx, gy = np.meshgrid(at[0], at[1], indexing="ij")
    keep = (gx >= xs[0]) & (gx <= xs[-1]) & (gy >= ys[0]) & (gy <= ys[-1])
    ax.scatter(gx[keep], gy[keep], c=np.clip(c[keep], -R, R), cmap="coolwarm", vmin=-R, vmax=R, s=7, linewidths=0)
    ax.contour(xs, ys, phi.T, levels=[0.0], colors="k", linewidths=1.2)
    if side:
        ax.axvline(0.0, color="#555555", lw=2.5)
        ax.add_patch(plt.Circle(LUG[:2], LUG[2], fill=False, color="#555555", lw=1.2, ls="--"))
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(textwrap.fill(title, 34), fontsize=10, loc="left")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=float, default=4.0, help="the members' free edges, mm")
    ap.add_argument("--fillet", type=float, default=4.0, help="their roots, mm")
    ap.add_argument("--out", default="field_shapes.png", help="the picture, in data/first_loop")
    a = ap.parse_args()
    r, rf = a.round, a.fillet
    shapes = [
        ("RIBS 1. A web round a bearing boss: five curved spokes, wide and tall at the boss, slimmer and lower outward, "
         "tied by a ring. The two current fields.", spider, [(-95.0, -175.0, 150.0), (0.0, 0.0, 6.0), (0, 0, 1)], False),
        ("RIBS 2. One rib from a bearing boss forking twice to three bolt bosses, every branch tapering in width and "
         "height. The two current fields.", tree, [(-70.0, -185.0, 150.0), (4.0, 0.0, 6.0), (0, 0, 1)], False),
        ("BRACKET 1. Hanging from the split (the two current fields): two curved arms fork into one stem at the lug, "
         "each deepening toward it; the free edges rounded. Left from the side, right from below.", hanging_fork,
         [[(75.0, -300.0, -80.0), (32.0, 0.0, -32.0), (0, 0, 1)], [(30.0, -10.0, -230.0), (30.0, 0.0, -30.0), (1, 0, 0)]], True),
        ("BRACKET 2. With a start field (where each column's metal starts, chosen too): a web from the land to the lug with a window, its top rising toward the "
         "lug, its belly fullest at the wall. Left from above, right from below.", web_window,
         [[(195.0, -205.0, 100.0), (32.0, 0.0, -30.0), (0, 0, 1)], [(30.0, -10.0, -230.0), (30.0, 0.0, -30.0), (1, 0, 0)]], True),
    ]  # fmt: skip
    fig = plt.figure(figsize=(25, 12.5))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 0.4, 1, 0.4], wspace=0.03, hspace=0.12)
    for j, (title, build, camera, side) in enumerate(shapes):
        f, origin, h, info = build(r, rf)
        mesh = msd.surface(f, origin, h)
        del f
        if isinstance(camera[0][0], tuple):  # two views side by side
            img = np.hstack([msd.shot(mesh, cam, size=(600, 820))[30:-30, 20:-20] for cam in camera])
        else:
            img = msd.shot(mesh, camera)[30:-30, 50:-50]
        ax = fig.add_subplot(gs[j // 2, 2 * (j % 2)])
        ax.imshow(img)
        ax.set_axis_off()
        ax.set_title(textwrap.fill(title, 70), fontsize=12, loc="left")
        plan_panel(fig.add_subplot(gs[j // 2, 2 * (j % 2) + 1]), info,
                   "Its outline's control points, 6 mm apart (red metal, blue air); black: the outline they give", side)  # fmt: skip
    fig.suptitle(textwrap.fill(
        "Shapes the fields can make, from control points on the optimiser's own knots (the outline every 6 mm, the heights "
        f"every 12 mm; members at least 8 mm wide, 8 mm apart, 8 mm high), drawn with the section rule (round r {r:g}, "
        f"fillet r {rf:g}). One metal interval along the pull at every point: a two-part mould casts each. The control "
        "points are set by hand to sketch each shape; in a run the optimiser sets them.", 190), fontsize=13.5, y=1.0)  # fmt: skip
    path = msd.OUT / a.out
    fig.savefig(path, dpi=85, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
