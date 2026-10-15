"""PROTOTYPE (LOP-30) - why baseline2_spl2's drawing lost mount-3, as a side-view sketch (the engineer, 14 October 21:33: "I
didn't understand this"). Not to scale. The arm hangs from the split; above the lug a space is kept clear (the vehicle's
bracket); so the arm's last piece reaches the lug from under that space, and its metal starts there, not at the split.
The drawing guessed each column's start from where it stands (outside the shell: at the split), found no metal starting at
the split under the clear space, and drew nothing there; the lug came loose.

    mount3_bug_explain.py

Writes data/first_loop/mount3_bug_explain.png.
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
GREY, METAL, CLEAR, BAD = "#bdbdbd", "#9ecae1", "#fde0dd", "#c0392b"


def scene(ax, drawn_post: bool, title: str):
    ax.add_patch(Rectangle((-6, -80), 6, 80, color=GREY))  # the shell's side wall
    ax.text(-3, -70, "shell", rotation=90, ha="center", va="center", fontsize=9)
    ax.axhline(0, color=BAD, lw=1.2, ls="--")
    ax.text(96, 1.5, "the split", color=BAD, ha="right", fontsize=10)
    ax.add_patch(Rectangle((52, -64), 40, 30, color=GREY))  # the lug
    ax.text(72, -49, "mount-3's lug", ha="center", va="center", fontsize=10)
    ax.add_patch(Rectangle((48, -34), 48, 31, color=CLEAR, ec=BAD, ls="--", lw=1.2))  # the kept-clear space above it
    ax.text(72, -18.5, "kept clear\n(the vehicle's bracket)", ha="center", va="center", fontsize=9.5, color=BAD)
    ax.add_patch(Rectangle((0, -46), 48, 46, color=METAL))  # the arm, hanging from the split
    ax.text(24, -23, "the arm\n(starts at the split)", ha="center", va="center", fontsize=10)
    if drawn_post:
        ax.add_patch(Rectangle((44, -52), 8, 18, color=METAL, ec="#08519c", lw=1.5))  # its last piece, under the clear space
    else:
        ax.add_patch(Rectangle((44, -52), 8, 18, fill=False, ec=BAD, lw=2, ls=":"))
        ax.text(48, -58, "not drawn", color=BAD, ha="center", va="top", fontsize=10, weight="bold")
    ax.set_xlim(-10, 100)
    ax.set_ylim(-82, 6)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(textwrap.fill(title, 54), fontsize=11.5, loc="left")


def main():
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.4))
    scene(axes[0], False, "BEFORE THE FIX. The arm's last piece (outlined) is under the kept-clear space, so its metal starts "
                          "there, not at the split. The drawing guessed 'outside the shell, so it starts at the split', found "
                          "no such metal there and drew nothing: the lug hung loose, 'mount-3 lost'.")  # fmt: skip
    scene(axes[1], True, "AFTER THE FIX. Where the guess finds nothing, the drawing takes the column's own start. The last "
                         "piece is drawn and joins the arm to the lug. The optimiser's result had it all along.")  # fmt: skip
    fig.suptitle("Side view at mount-3 (a sketch, not to scale)", fontsize=14)
    fig.tight_layout()
    path = OUT / "mount3_bug_explain.png"
    fig.savefig(path, dpi=90, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
