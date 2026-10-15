"""PROTOTYPE (LOP-30) - the outline field explained (the engineer, 14 October 20:30: "And what's an outline field?").
Four panels: its control points in plan (one every 6 mm, a number in mm each); the smooth terrain they make, metal
wherever it stands above zero, the members' outline its coastline; one line across a rib, each control point's bump and
their sum, and what raising one point does; and the rib that the outline, the height field and the section rule give
together. The rib is `field_shapes.py`'s forking rib (RIBS 2), its control points set by hand.

    outline_field_explain.py

Writes data/first_loop/outline_field_explain.png.
"""

import textwrap

import matplotlib

matplotlib.use("Agg")
import field_shapes as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import member_section_demo as msd  # noqa: E402
import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

R = msd.RANGE
BOSSES = ((-48.0, 0.0, 22.0), (55.0, 38.0, 9.0), (55.0, -38.0, 9.0), (62.0, 0.0, 9.0))  # the forking rib's, for context


def terrain(xs, ys, phi, lift=3.0):
    """The outline field as a terrain (its height `lift` times its value), the sea at zero, the coastline in black."""
    k = 4
    X, Y = np.meshgrid(xs[::k], ys[::k], indexing="ij")
    v = np.clip(phi[::k, ::k], -R, R)
    land = pv.StructuredGrid(X, Y, lift * v)
    land.point_data["v"] = v.ravel(order="F")
    flat = pv.StructuredGrid(X, Y, np.full_like(X, 0.3))
    flat.point_data["v"] = v.ravel(order="F")
    coast = flat.contour([0.0], scalars="v")
    pl = pv.Plotter(off_screen=True, window_size=(1100, 820))
    pl.set_background("white")
    pl.add_mesh(land, scalars="v", cmap="coolwarm", clim=[-R, R], smooth_shading=True, show_scalar_bar=False, ambient=0.3)
    sea = pv.Plane(center=(float(X.mean()), float(Y.mean()), 0.0), i_size=float(np.ptp(X)), j_size=float(np.ptp(Y)))
    pl.add_mesh(sea, color="#9ecae1", opacity=0.45)
    pl.add_mesh(coast, color="black", line_width=5)
    pl.camera_position = [(-120.0, -230.0, 170.0), (5.0, 0.0, 0.0), (0, 0, 1)]
    img = pl.screenshot(return_img=True)
    pl.close()
    return img


def across(ax):
    """One line across a rib: control points 6 mm apart, each one's cubic bump, their sum, and one point raised."""
    y = np.linspace(0.0, 54.0, 1081)
    B = msd.basis(y, 0.0, 54.0, 6.0)
    at = 6.0 * (np.arange(B.shape[1]) - 1.0)
    v = np.array([-8.0, -8.0, -8.0, -8.0, -1.0, 7.0, 7.0, -1.0, -8.0, -8.0, -8.0, -8.0])
    raised = v.copy()
    raised[7] += 6.0

    def edges(c):
        f = B @ c
        cross = np.flatnonzero(np.diff(np.sign(f)) != 0)
        z = [y[i] - f[i] * (y[i + 1] - y[i]) / (f[i + 1] - f[i]) for i in cross]
        return f, z

    f0, z0 = edges(v)
    f1, z1 = edges(raised)
    for j in range(len(v)):
        ax.plot(y, B[:, j] * v[j], color="#9e9e9e", lw=0.8)
    ax.fill_between(y, 0.0, f0, where=f0 > 0, color="#fcbba1", label="metal (field above zero)")
    ax.plot(y, f0, color="#c0392b", lw=2.6, label="the field: the bumps' sum")
    ax.plot(y, f1, color="#c0392b", lw=1.8, ls="--", label="the same, one point raised 6 mm")
    ax.stem(at, v, linefmt="k-", markerfmt="ko", basefmt=" ")
    ax.plot(at[7], raised[7], marker="o", mfc="white", mec="k", ms=9)
    ax.annotate("", (at[7], raised[7] - 0.3), (at[7], v[7] + 0.3), arrowprops={"arrowstyle": "->", "lw": 1.5})
    ax.axhline(0.0, color="k", lw=1.0)
    ax.set_xlim(0.0, 54.0)
    ax.set_ylim(-9.5, 9.5)
    ax.set_xlabel("across the rib, mm")
    ax.set_ylabel("the outline field's value, mm")
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    w0, w1 = z0[1] - z0[0], z1[1] - z1[0]
    ax.annotate("", (z0[0], -3.2), (z0[1], -3.2), arrowprops={"arrowstyle": "<->"})
    ax.text(0.5 * (z0[0] + z0[1]), -4.6, f"{w0:.1f} mm", ha="center", fontsize=10)
    ax.annotate("", (z1[0], -6.0), (z1[1], -6.0), arrowprops={"arrowstyle": "<->", "ls": "--"})
    ax.text(0.5 * (z1[0] + z1[1]) + 3.0, -7.4, f"{w1:.1f} mm with the point raised", ha="center", fontsize=10)
    return w0, w1


def main():
    f, origin, h, (at, c, xs, ys, phi) = fs.tree(4.0, 4.0)
    rib = msd.shot(msd.surface(f, origin, h), [(-70.0, -185.0, 150.0), (4.0, 0.0, 6.0), (0, 0, 1)])
    del f
    land = terrain(xs, ys, phi)
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(2, 2, wspace=0.08, hspace=0.2)
    wrap = lambda t: textwrap.fill(t, 88)  # noqa: E731

    ax = fig.add_subplot(gs[0, 0])
    gx, gy = np.meshgrid(at[0], at[1], indexing="ij")
    keep = (gx >= xs[0]) & (gx <= xs[-1]) & (gy >= ys[0]) & (gy <= ys[-1])
    sc = ax.scatter(gx[keep], gy[keep], c=np.clip(c[keep], -R, R), cmap="coolwarm", vmin=-R, vmax=R, s=28)
    ax.contour(xs, ys, phi.T, levels=[0.0], colors="k", linewidths=1.6)
    for bx, by, ro in BOSSES:
        ax.add_patch(plt.Circle((bx, by), ro, fill=False, color="#777777", lw=1.2, ls="--"))
    ax.set_aspect("equal")
    ax.set_xlabel("mm")
    ax.set_ylabel("mm")
    fig.colorbar(sc, ax=ax, shrink=0.75, label="a control point's number, mm")
    ax.set_title(wrap("1. THE CONTROL POINTS. A grid over the plan (seen along the pull), one point every 6 mm, each "
                      "holding one number between -8 and +8 mm: red above zero, blue below. The optimiser chooses these "
                      "numbers. Black: the outline they give; dashed: the bosses (fixed parts)."), fontsize=12, loc="left")  # fmt: skip

    ax = fig.add_subplot(gs[0, 1])
    ax.imshow(land[60:-60, 40:-40])
    ax.set_axis_off()
    ax.set_title(wrap("2. THE FIELD THEY MAKE: A SMOOTH TERRAIN. Each point lifts or lowers the terrain round it, "
                      "smoothly. Metal wherever the terrain stands above sea level (zero: the blue sheet); the coastline "
                      "(black) is the members' outline, seen from above."), fontsize=12, loc="left")  # fmt: skip

    ax = fig.add_subplot(gs[1, 0])
    w0, w1 = across(ax)
    ax.set_title(wrap(f"3. ACROSS ONE RIB. Each control point (black stem) adds one smooth bump (grey), 24 mm wide; their "
                      f"sum (red) is the field. It crosses zero at the rib's two edges: {w0:.1f} mm wide. Raise one point "
                      f"by 6 mm and that edge moves out smoothly: {w1:.1f} mm. No steps, no wiggles finer than the 6 mm "
                      "spacing."), fontsize=12, loc="left")  # fmt: skip

    ax = fig.add_subplot(gs[1, 1])
    ax.imshow(rib[30:-30, 50:-50])
    ax.set_axis_off()
    ax.set_title(wrap("4. THE RIB. The outline field says where the metal is, seen from above; the height field says how "
                      "tall it stands (where it ends); the section rule rounds its top and fillets its root."), fontsize=12, loc="left")  # fmt: skip
    fig.suptitle("The outline field: where the members are, seen from above", fontsize=16, y=0.995)
    path = msd.OUT / "outline_field_explain.png"
    fig.savefig(path, dpi=85, bbox_inches="tight")
    print(path, f"{w0:.1f} -> {w1:.1f} mm")


if __name__ == "__main__":
    main()
