"""PROTOTYPE (LOP-30) - why the housing's drawing still looks blocky beside `field_shapes.py`'s pictures (the engineer,
14 October 21:03: "why it's still blocky ... compare it with images u gave to me before"). The same section rule (round 4,
fillet 4) on one flat wall, three causes taken apart:
- the shape: `field_shapes.py`'s forking rib (curved, tapering, branching) against a straight rib of one width and height,
  as `spline_example.py`'s was made by hand;
- the drawing's grid: 0.5 mm (the pictures') against 2 mm (the housing's drawing: the optimiser's own points);
- the wall's level: the straight rib again, on a wall stepping 8 mm under it, its height measured from each column's own
  level (as the housing's members are) and from one smooth surface.

    blocky_causes.py

Writes data/first_loop/blocky_causes.png.
"""

import textwrap

import matplotlib

matplotlib.use("Agg")
import field_shapes as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import member_section_demo as msd  # noqa: E402
import numpy as np  # noqa: E402

R = msd.RANGE
BOSSES = [(-48.0, 0.0, 22.0, 14.0, 22.0), (55.0, 38.0, 9.0, 4.5, 14.0), (55.0, -38.0, 9.0, 4.5, 14.0), (62.0, 0.0, 9.0, 4.5, 14.0)]
BOX = ((-76.0, 78.0), (-54.0, 54.0))
CAM = [(-70.0, -185.0, 150.0), (4.0, 0.0, 6.0), (0, 0, 1)]


def fork():
    return [
        {"c": fs.bezier((-30, 0), (-5, 0)), "w": (7.0, 6.0), "t": (18.0, 16.0)},
        {"c": fs.bezier((-5, 0), (22, 14), (52, 36)), "w": (6.0, 4.0), "t": (16.0, 10.0)},
        {"c": fs.bezier((-5, 0), (16, -10), (30, -17)), "w": (6.0, 5.0), "t": (16.0, 13.0)},
        {"c": fs.bezier((30, -17), (44, -26), (52, -36)), "w": (5.0, 4.0), "t": (13.0, 10.0)},
        {"c": fs.bezier((30, -17), (46, -10), (58, 0)), "w": (5.0, 4.0), "t": (13.0, 10.0)},
    ]


def straight():
    return [{"c": fs.bezier((-30, 0), (58, 0)), "w": (5.0, 5.0), "t": (16.0, 16.0)}]


def stepped(r, rf, h, smooth_top):
    """The straight rib on a wall whose outer face steps 8 mm down at x = 10 (two rooms' end walls): its height measured
    from each column's own level (the top steps too), or its free end one smooth surface over both."""
    xs, ys, zs = fs.grid((*BOX, (-15.0, 30.0)), h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    phi_t, v = fs.members_targets(straight(), X, Y)
    phi = fs.fit_c(np.clip(phi_t, -R, R), xs, ys, 6.0, R)[0]
    A, Z = msd.distance_in(phi, h)[:, :, None], zs[None, None, :]
    face = np.where(X < 10.0, 0.0, -8.0)  # the wall's outer face, stepping 8 mm
    if smooth_top:  # one free end over both levels: the higher level's height, held across the step
        top = fs.fit_c(np.full(X.shape, 16.0), xs, ys, 12.0)[0][:, :, None]
    else:
        top = (face + fs.fit_c(v["t"], xs, ys, 12.0)[0])[:, :, None]
    (x0, x1), (y0, y1) = BOX
    plate = np.maximum(np.maximum(X - (x1 - 4.0), (x0 + 4.0) - X), np.maximum(Y - (y1 - 4.0), (y0 + 4.0) - Y))[:, :, None]
    F = face[:, :, None]
    wall = np.maximum(plate, np.maximum(Z - F, (F - 4.0) - Z))
    f = msd.round_union(np.maximum(msd.round_inter(-A, Z - top, r), (F - 2.0) - Z), wall, rf)
    for bx, by, ro, _, hb in BOSSES[:1] + BOSSES[3:]:
        rho = np.hypot(X - bx, Y - by)[:, :, None]
        f = msd.round_union(f, np.maximum(rho - ro, np.maximum(Z - hb, -12.0 - Z)), rf)
    for bx, by, _, ri, _ in BOSSES[:1] + BOSSES[3:]:
        f = np.maximum(f, ri - np.hypot(X - bx, Y - by)[:, :, None])
    return f, (xs[0], ys[0], zs[0]), h


def main():
    r = rf = 4.0
    panels = [
        ("A. The pictures' shape on the pictures' grid (0.5 mm): curved, tapering, branching.",
         lambda: fs.wall_shape(fork(), BOSSES, BOX, r, rf, h=0.5)[:3]),
        ("B. The same rib on the housing's grid (2 mm, the optimiser's own points): the same shape, its 4 mm rounds drawn as "
         "two facets.", lambda: fs.wall_shape(fork(), BOSSES, BOX, r, rf, h=2.0)[:3]),
        ("C. A straight rib of one width and height (as the housing example was made by hand), on the fine grid: a box with "
         "rounded edges, whatever the grid.", lambda: fs.wall_shape(straight(), BOSSES[:1] + BOSSES[3:], BOX, r, rf, h=0.5)[:3]),
        ("D. The straight rib on a wall stepping 8 mm (two rooms' end walls), its height from each column's own level, as the "
         "housing's members are measured: its top steps too (the housing example's two blocks).",
         lambda: stepped(r, rf, 0.5, smooth_top=False)),
        ("E. The same, its free end one smooth surface over both levels: no step.", lambda: stepped(r, rf, 0.5, smooth_top=True)),
    ]  # fmt: skip
    fig, axes = plt.subplots(2, 3, figsize=(24, 13))
    for ax, (title, build) in zip(axes.ravel(), panels, strict=False):
        f, origin, h = build()
        img = msd.shot(msd.surface(f, origin, h), CAM)
        del f
        ax.imshow(img[60:-60, 60:-60])
        ax.set_axis_off()
        ax.set_title(textwrap.fill(title, 62), fontsize=12, loc="left")
    axes.ravel()[-1].set_axis_off()
    axes.ravel()[-1].text(0.0, 0.5, textwrap.fill(
        "What makes the housing's drawing look blocky, each alone (the section rule on in every panel):\n"
        "1. the shape: straight, one width, one height (C) against curved, tapering, branching (A): the optimiser's to choose;\n"
        "2. the grid: the housing is drawn on the optimiser's 2 mm points (B): the same fields can be drawn finer;\n"
        "3. the levels: each column's height is measured from its own wall level, so a member's top steps where the wall "
        "does (D against E).", 52), fontsize=13, va="center", transform=axes.ravel()[-1].transAxes)  # fmt: skip
    fig.suptitle("Why the housing's drawing looks blocky beside the pictures", fontsize=16, y=0.995)
    fig.tight_layout()
    path = msd.OUT / "blocky_causes.png"
    fig.savefig(path, dpi=80, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
