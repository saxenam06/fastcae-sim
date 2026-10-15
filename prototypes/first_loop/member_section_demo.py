"""PROTOTYPE (LOP-30) - an illustration, not a result: why the spline space's members look blocky (the engineer, 14 October
19:45: "why this would still look blocky"), and the section rule that would change it.

The same control points (the outline field on 6 mm knots, the heights on 12 mm, as `topo.spline_setup` lays them) drawn
two ways. Now: the outline pushed straight along the pull to its height, so every member's section is a box (vertical
sides, a flat top, sharp edges at the top and the root), and an arm must hang from the split or stand on the end wall.
Proposed: the section's form in the rule itself (the top edges rounded, the roots filleted, a radius each) and, for an
arm, a start field: where each column's metal starts, chosen as well as where it ends. Both keep one metal interval along the pull at every point, so castable by
construction. The paths and sizes here are set by hand to show the rule; in a run the optimiser sets them.

    member_section_demo.py [--round 4] [--fillet 4] [--out member_section_demo.png]

Writes the picture into data/first_loop.
"""

import argparse
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402
from scipy.interpolate import BSpline  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
RANGE = 8.0  # the outline field's coefficients, mm (topo.SPLINE_RANGE)


def basis(x, lo, hi, s):
    """The cubic B-splines on knots s apart covering [lo, hi], at x."""
    m = int(np.ceil((hi - lo) / s - 1e-9))
    t = lo + s * np.arange(-3, m + 4)
    return BSpline.design_matrix(np.clip(x, t[3], t[-4]), t, 3).toarray()


def fit(target, xs, ys, s, clip=None):
    """A field's control points on knots s apart (least squares to a target on the plan grid), and the field they give."""
    bx, by = basis(xs, xs[0], xs[-1], s), basis(ys, ys[0], ys[-1], s)
    c = np.linalg.pinv(bx) @ target @ np.linalg.pinv(by).T
    if clip is not None:
        c = np.clip(c, -clip, clip)
    return (bx @ c @ by.T).astype(np.float32)


def distance_in(phi, h):
    """The outline field as a distance inside its zero line, mm (its value over its slope)."""
    gx, gy = np.gradient(phi, h)
    return phi / np.maximum(np.hypot(gx, gy), 0.3)


def round_inter(a, b, r):
    """Two solids' common part with the edge where they meet rounded to r (signed distances, positive outside)."""
    return np.minimum(-r, np.maximum(a, b)) + np.hypot(np.maximum(r + a, 0), np.maximum(r + b, 0))


def round_union(a, b, r):
    """Two solids joined with a fillet of radius r where they meet."""
    return np.maximum(r, np.minimum(a, b)) - np.hypot(np.maximum(r - a, 0), np.maximum(r - b, 0))


def surface(f, origin, h):
    g = pv.ImageData(dimensions=f.shape, spacing=(h, h, h), origin=origin)
    g.point_data["f"] = np.ascontiguousarray(f).ravel(order="F")
    return g.contour([0.0], scalars="f")


def shot(mesh, camera, size=(1100, 820)):
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    pl.add_mesh(mesh, color="#cfcfcf", smooth_shading=True, specular=0.35, ambient=0.3)
    pl.camera_position = camera
    img = pl.screenshot(return_img=True)
    pl.close()
    return img


def rib_scene(r, rf):
    """A rib across a wall, standing along the pull (+z): an S in plan, wider toward its ends, higher in its middle."""
    h = 0.4
    xs, ys, zs = (np.arange(lo, hi + 1e-9, h, dtype=np.float32) for lo, hi in ((-64, 64), (-44, 44), (-7, 30)))
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    sx = np.linspace(-46.0, 46.0, 1500)
    d, i = cKDTree(np.column_stack([sx, 11.0 * np.sin(np.pi * sx / 60.0)])).query(np.column_stack([X.ravel(), Y.ravel()]))
    w = 4.5 + 2.0 * (sx[i] / 46.0) ** 2  # the half-width
    phi = fit(np.clip(w - d, -RANGE, RANGE).reshape(X.shape), xs, ys, 6.0, RANGE)
    t = fit((12.0 + 8.0 * np.exp(-((sx[i] / 30.0) ** 2))).reshape(X.shape), xs, ys, 12.0)
    A, T, Z = distance_in(phi, h)[:, :, None], t[:, :, None], zs[None, None, :]
    wall = np.maximum(np.maximum(np.abs(X) - 60.0, np.abs(Y) - 40.0)[:, :, None], np.maximum(Z, -4.0 - Z))
    now = np.minimum(np.maximum(np.maximum(-A, Z - T), -2.0 - Z), wall)
    new = round_union(np.maximum(round_inter(-A, Z - T, r), -2.0 - Z), wall, rf)
    ix = int(np.argmin(np.abs(xs - 30.0)))  # the S's crest: a cut along y there is square to the rib
    return {
        "origin": (xs[0], ys[0], zs[0]),
        "h": h,
        "now": now,
        "new": new,
        "cut": (ys, zs, now[ix], new[ix]),
    }


def bracket_scene(r, rf):
    """A two-legged bracket from a side wall (outside x > 0; the split at z = 0, the housing below) to a lug at mid-height."""
    h = 0.5
    xs, ys, zs = (np.arange(lo, hi + 1e-9, h, dtype=np.float32) for lo, hi in ((-8, 82), (-52, 52), (-80, 4)))
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    P = np.column_stack([X.ravel(), Y.ravel()])
    lug, r_o, r_i, z_top, z_bot = np.array([62.0, 0.0]), 13.0, 6.5, -30.0, -55.0
    s = np.linspace(0.0, 1.0, 1500)[:, None]
    inside, along = [], []
    for sgn in (1.0, -1.0):
        p0, p1 = np.array([0.0, 32.0 * sgn]), np.array([30.0, 22.0 * sgn])
        curve = (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s**2 * lug
        d, i = cKDTree(curve).query(P)
        inside.append(7.0 - 2.5 * s[i, 0] - d)  # 14 mm wide at the wall, 9 at the lug
        along.append(s[i, 0])
    k = np.argmax(np.stack(inside), axis=0)
    phi_t = np.clip(np.max(np.stack(inside), axis=0), -RANGE, RANGE).reshape(X.shape)
    sa = np.where(k == 0, along[0], along[1]).reshape(X.shape)
    phi = np.minimum(fit(phi_t, xs, ys, 6.0, RANGE), X + 2.5)  # buried in the wall past x = -2.5
    A, Z = distance_in(phi, h)[:, :, None], zs[None, None, :]
    t_now = fit(40.0 + 16.0 * sa, xs, ys, 12.0)[:, :, None]  # now: hanging from the split to this depth
    top = fit(6.0 + 24.0 * sa**1.3, xs, ys, 12.0)[:, :, None]  # proposed: the arm's top, its depth below the split
    bot = fit(64.0 - 9.0 * sa, xs, ys, 12.0)[:, :, None]  # and its underside
    wall = np.maximum(np.maximum(X[:, :, None], -4.0 - X[:, :, None]), np.maximum(np.abs(Y)[:, :, None] - 50.0, np.maximum(Z, -76.0 - Z)))
    rho = np.hypot(X - lug[0], Y - lug[1])[:, :, None]
    boss = np.maximum(rho - r_o, np.maximum(Z - z_top, z_bot - Z))
    now = np.minimum(np.minimum(np.maximum(-A, np.maximum(-t_now - Z, Z)), wall), boss)
    arm = round_inter(round_inter(-A, -bot - Z, r), Z + top, r)
    new = round_union(round_union(arm, wall, rf), boss, rf)
    now, new = np.maximum(now, r_i - rho), np.maximum(new, r_i - rho)  # the lug's bore, machined
    return {
        "origin": (xs[0], ys[0], zs[0]),
        "h": h,
        "now": now,
        "new": new,
        "side": (xs, zs, (now < 0).any(axis=1), (new < 0).any(axis=1)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=float, default=4.0, help="the members' top edges, mm")
    ap.add_argument("--fillet", type=float, default=4.0, help="their roots, mm")
    ap.add_argument("--out", default="member_section_demo.png", help="the picture, in data/first_loop")
    a = ap.parse_args()
    r, rf = a.round, a.fillet
    rib = rib_scene(r, rf)
    cam_rib = [(-75.0, -150.0, 105.0), (0.0, 0.0, 6.0), (0.0, 0.0, 1.0)]
    img = {f"rib_{k}": shot(surface(rib[k], rib["origin"], rib["h"]), cam_rib) for k in ("now", "new")}
    cut = rib["cut"]
    del rib
    br = bracket_scene(r, rf)
    cam_br = [(150.0, -165.0, 25.0), (34.0, 0.0, -36.0), (0.0, 0.0, 1.0)]
    img.update({f"br_{k}": shot(surface(br[k], br["origin"], br["h"]), cam_br) for k in ("now", "new")})
    side = br["side"]
    del br

    fig = plt.figure(figsize=(21, 13.5))
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 0.78], wspace=0.04, hspace=0.16)
    wrap = lambda s: textwrap.fill(s, 62)  # noqa: E731
    titles = {
        "rib_now": "NOW. A rib is its outline in plan pushed straight along the pull to its height: a box section "
        "(vertical sides, a flat top, sharp edges at the top and the root), however smooth the outline.",
        "rib_new": f"PROPOSED. The same control points; the rule gives the section its form: the top edges rounded "
        f"(r {r:g} mm), the root filleted (r {rf:g} mm).",
        "br_now": "NOW. An arm must hang from the split (or stand on the end wall), so a bracket to a lug at "
        "mid-height is a deep slab from the split down past the lug.",
        "br_new": "PROPOSED. A start field too (where each column's metal starts): each arm has its own top and bottom, deep at the wall, "
        "slim at the lug, rounded, filleted into the wall and the lug.",
    }
    for j, key in enumerate(("rib_now", "rib_new", "br_now", "br_new")):
        ax = fig.add_subplot(gs[j // 2, j % 2])
        ax.imshow(img[key][40:-40, 60:-60])
        ax.set_axis_off()
        ax.set_title(wrap(titles[key]), fontsize=11.5, loc="left")
    ys, zs, now_c, new_c = cut
    ax = fig.add_subplot(gs[0, 2])
    ax.contourf(ys, zs, new_c.T, levels=[-1e9, 0.0], colors=["#9ecae1"])
    ax.contour(ys, zs, now_c.T, levels=[0.0], colors="k", linewidths=1.6)
    ax.set_xlim(-5, 27)
    ax.set_ylim(-5, 21)
    ax.set_aspect("equal")
    ax.set_xlabel("across the rib, mm")
    ax.set_ylabel("along the pull, mm")
    ax.set_title(wrap("Across the rib: now (black line), proposed (blue). The rounded top and the fillets come from "
                      "the rule, not from smoothing afterwards."), fontsize=11.5, loc="left")  # fmt: skip
    ax.annotate(f"round r {r:g}", (14.6, 13.6), (17.5, 17.5), arrowprops={"arrowstyle": "->"}, fontsize=10)
    ax.annotate(f"fillet r {rf:g}", (17.0, 1.0), (20.0, 6.0), arrowprops={"arrowstyle": "->"}, fontsize=10)
    xs, zs, now_s, new_s = side
    ax = fig.add_subplot(gs[1, 2])
    ax.contourf(xs, zs, new_s.T.astype(float), levels=[0.5, 1.5], colors=["#9ecae1"])
    ax.contour(xs, zs, now_s.T.astype(float), levels=[0.5], colors="k", linewidths=1.6)
    ax.axhline(0.0, color="#c0392b", lw=1.0, ls="--")
    ax.text(40.0, 1.2, "the split", color="#c0392b", fontsize=10)
    ax.text(-3.5, -40.0, "side wall", rotation=90, fontsize=10, va="center")
    ax.text(62.0, -60.0, "lug", fontsize=10, ha="center")
    ax.set_xlim(-8, 80)
    ax.set_ylim(-78, 6)
    ax.set_aspect("equal")
    ax.set_xlabel("out from the side wall, mm")
    ax.set_ylabel("along the pull, mm")
    ax.set_title(wrap("The bracket from the side: now (black line), proposed (blue)."), fontsize=11.5, loc="left")
    fig.suptitle("Why the members look blocky, and the rule that changes it. An illustration: the paths and sizes are set "
                 "by hand to show the rule; in a run the optimiser sets every one.", fontsize=14, x=0.5, y=0.995)  # fmt: skip
    path = OUT / a.out
    fig.savefig(path, dpi=90, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
