"""PROTOTYPE (LOP-30) - the start field explained (the engineer, 14 October 20:20: "What's this underside field, I'm not
understanding"). A side view of one bracket arm, from a side wall to a lug at mid-height, cut into columns along the pull.
Today each column's metal starts at a fixed surface (the split, for a member outside the shell) and the height field
chooses only where it ends. With a start field the optimiser chooses where it starts as well. And the one rule that keeps
it castable: one piece of metal in each column.

    start_field_explain.py

Writes data/first_loop/start_field_explain.png.
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
GREY, METAL, BAR, START, END, SPLIT = "#bdbdbd", "#c6dbef", "#2171b5", "#2ca02c", "#e67e22", "#c0392b"
COLUMNS = (6.0, 18.0, 30.0, 42.0)


def scene(ax, land=True):
    """The side wall (outer face x = 0), the split (z = 0, the housing below), the sealing land, the lug and its bore."""
    ax.add_patch(Rectangle((-4.0, -76.0), 4.0, 76.0, color=GREY, zorder=1))
    if land:
        ax.add_patch(Rectangle((-4.0, -8.0), 14.0, 8.0, color=GREY, zorder=1))
    ax.add_patch(Rectangle((49.0, -55.0), 26.0, 25.0, color=GREY, zorder=1))
    ax.add_patch(Rectangle((55.5, -55.0), 13.0, 25.0, fill=False, ls="--", ec="#777777", zorder=2))
    ax.axhline(0.0, color=SPLIT, lw=1.3, ls="--", zorder=0)
    ax.text(77.0, 1.5, "the split", color=SPLIT, ha="right", fontsize=10)
    ax.text(-2.0, -66.0, "side wall", rotation=90, ha="center", va="center", fontsize=9)
    ax.text(62.0, -42.5, "lug", ha="center", va="center", fontsize=10)
    ax.set_xlim(-8.0, 80.0)
    ax.set_ylim(-80.0, 7.0)
    ax.set_aspect("equal")
    ax.set_xlabel("out from the side wall, mm")
    ax.set_ylabel("along the pull, mm")


def arm(ax, x, top, bottom, start_fixed):
    ax.fill_between(x, top, bottom, color=METAL, zorder=1.5)
    for xc in COLUMNS:
        i = int(np.argmin(np.abs(x - xc)))
        ax.plot([xc, xc], [-78.0, 5.0], color="#999999", lw=0.8, ls=":", zorder=2)
        ax.plot([xc, xc], [top[i], bottom[i]], color=BAR, lw=5, solid_capstyle="butt", zorder=3)
        if start_fixed:
            ax.plot(xc, top[i], marker="s", color="k", ms=8, zorder=4)
        else:
            ax.plot(xc, top[i], marker="o", color=START, ms=10, zorder=4)
        ax.plot(xc, bottom[i], marker="o", color=END, ms=10, zorder=4)


def main():
    x = np.linspace(0.0, 56.0, 400)
    s = x / 62.0
    fig, axes = plt.subplots(1, 3, figsize=(21, 7.6), gridspec_kw={"width_ratios": [1, 1, 0.95], "wspace": 0.18})
    wrap = lambda t: textwrap.fill(t, 58)  # noqa: E731

    ax = axes[0]
    scene(ax)
    arm(ax, x, np.zeros_like(x), -(26.0 + 30.0 * s), start_fixed=True)
    ax.set_title(wrap("TODAY: two fields. The outline field says which columns (dotted) hold metal; the height field "
                      "says where it ends (orange). Where it starts is fixed: at the split (black). So an arm is joined "
                      "to the split all along its length: a slab hanging down to the lug."), fontsize=11.5, loc="left")  # fmt: skip

    ax = axes[1]
    scene(ax)
    rise = np.clip((x - 10.0) / 46.0, 0.0, 1.0)  # under the land (x < 10) the arm starts at the land
    arm(ax, x, -(8.0 + 22.0 * rise**1.2), -(46.0 + 9.0 * s), start_fixed=False)
    ax.annotate("joined to the land", (6.0, -8.0), (16.0, 3.0), fontsize=9.5, arrowprops={"arrowstyle": "->"})
    ax.set_title(wrap("WITH A START FIELD: three fields. One more number at each point, on the same 12 mm knots: where "
                      "the metal starts (green). The optimiser chooses both ends, at least 8 mm apart, so the arm can "
                      "leave the wall at any height and meet the lug at mid-height, shaped above and below."), fontsize=11.5, loc="left")  # fmt: skip

    ax = axes[2]
    for dx, ok in ((0.0, False), (44.0, True)):
        ax.add_patch(Rectangle((dx - 4.0, -76.0), 4.0, 76.0, color=GREY))
        ax.add_patch(Rectangle((dx - 4.0, -8.0), 18.0, 8.0, color=GREY))
        top = -8.0 if ok else -16.0
        ax.add_patch(Rectangle((dx, -44.0), 34.0, 44.0 + top, color=METAL))
        xc = dx + 8.0
        ax.plot([xc, xc], [-78.0, 5.0], color="#999999", lw=0.8, ls=":")
        ax.plot([xc, xc], [0.0, -8.0], color=BAR, lw=5, solid_capstyle="butt")
        ax.plot([xc, xc], [top, -44.0], color=BAR, lw=5, solid_capstyle="butt")
        if not ok:
            ax.add_patch(Rectangle((dx, -16.0), 14.0, 8.0, color="#fde0dd", zorder=0.5))
            ax.annotate("air trapped between\nthe land and the arm", (xc + 3.0, -12.0), (dx + 22.0, -26.0), fontsize=9.5,
                        arrowprops={"arrowstyle": "->"})  # fmt: skip
        ax.text(dx + 17.0, -52.0, "one piece: cast" if ok else "two pieces:\nneeds a core", ha="center", va="top",
                fontsize=11, color="#1a7f37" if ok else SPLIT, weight="bold")  # fmt: skip
        ax.annotate("", (dx + 26.0, 6.0), (dx + 26.0, -2.0), arrowprops={"arrowstyle": "->", "lw": 1.6})
        ax.annotate("", (dx + 26.0, -76.0), (dx + 26.0, -68.0), arrowprops={"arrowstyle": "->", "lw": 1.6})
    ax.text(40.0, 9.5, "the upper mould half pulls up", ha="center", fontsize=9.5)
    ax.text(40.0, -79.5, "the lower mould half pulls down", ha="center", fontsize=9.5, va="top")
    ax.axhline(0.0, color=SPLIT, lw=1.3, ls="--", zorder=0)
    ax.set_xlim(-8.0, 84.0)
    ax.set_ylim(-84.0, 12.0)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(wrap("THE ONE RULE: one piece of metal in each column, so the mould's two halves can pull away up and "
                      "down. Where the sealing land (or the shell) stands above an arm, the arm must start at it; "
                      "elsewhere its start is free. On the end walls a rib keeps starting at the wall."), fontsize=11.5, loc="left")  # fmt: skip

    handles = [
        plt.Line2D([], [], marker="s", color="k", ls="", ms=8, label="where the metal starts: fixed at the split (today)"),
        plt.Line2D([], [], marker="o", color=START, ls="", ms=10, label="where it starts: chosen (the start field)"),
        plt.Line2D([], [], marker="o", color=END, ls="", ms=10, label="where it ends: chosen (the height field)"),
        plt.Line2D([], [], color=BAR, lw=5, label="the metal in one column"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=11, frameon=False, bbox_to_anchor=(0.5, -0.02))
    path = OUT / "start_field_explain.png"
    fig.savefig(path, dpi=90, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
