"""PROTOTYPE (LOP-30) - the spline space explained in one picture (the engineer, 14 October 19:32: "pictorial representation
of the fields and two fields and where we are"):
A. one half in plan (the motor side, from the real set-up): where the outline field lives, and the two height fields'
   regions (the members standing on the split; those standing on the end walls);
B. a close-up: the 4 mm cubes, the 4 points each cube is read at, the outline's control points (6 mm), the heights' (12 mm);
C. a section through the half: how the fields build a member (the outline its sides, the height its top, from its base);
D. along a line across members: the outline field, where it is positive, and each cube's share of metal;
E. where we are.

Run: .venv/Scripts/python.exe prototypes/first_loop/spline_explain.py   (writes data/first_loop/spline_explain.png)"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from scipy.interpolate import BSpline  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE.parents[1] / "data" / "first_loop"

C_SPLIT, C_WALL, C_PHI, C_CUBE = "#f0a040", "#9b59b6", "#1f5fbf", "#bbbbbb"


def main() -> Path:
    import topo
    from topo_free import build_free

    model = build_free(4.0, band=24.0, flange=True, mount_reach="disc", height_field=4.0, empty=True, protect=True, flange_whole=True,
                       drawing_clear=True, couplings="kinematic", shell_fixed=True, towers=False)  # fmt: skip
    kind, n, ks = model["kind"], model["n"], int(model["k_split"])
    elem = np.flatnonzero(kind >= 0)
    free_e = np.flatnonzero(kind[elem] == 0)
    col, pos, pts, layer = topo.height_columns(kind, n, ks, elem, free_e)
    base = np.full(len(pts), -1, np.int64)
    kz = elem[free_e] % int(n[2])
    base[col[pos == 0]] = kz[pos == 0]
    h = 4.0
    sp_ = topo.spline_setup({"phi_mm": 6.0, "h_mm": 12.0, "gap_mm": 8.0}, kind, n, ks, pts, layer, base, model["lo"], h, 2.0, 8.0)
    lo = np.asarray(model["lo"], float)
    half = 0  # the motor side
    sel = np.flatnonzero(sp_["half"] == half)
    cxy = lo[:2] + h * (pts[sel] + 0.5)
    fam = sp_["on_split"][sel]

    def knots(fd):
        nx, ny = fd["shape"]
        ia, ja = np.unravel_index(fd["kept"], (nx, ny))
        return np.column_stack([fd["origin"][0] + fd["spacing"] * (ia - 1), fd["origin"][1] + fd["spacing"] * (ja - 1)])

    fo = next(fd for fd in sp_["fields"] if fd["kind"] == "outline" and fd["half"] == half)
    fs = next(fd for fd in sp_["fields"] if fd["kind"] == "height" and fd["half"] == half and fd["family"] == "split")
    fw = next(fd for fd in sp_["fields"] if fd["kind"] == "height" and fd["half"] == half and fd["family"] == "wall")
    ko, ksp, kwl = knots(fo), knots(fs), knots(fw)

    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0])
    # A. the regions in plan
    ax = fig.add_subplot(gs[0, 0])
    ax.scatter(cxy[fam, 0], cxy[fam, 1], s=4, marker="s", c=C_SPLIT, label=f"members standing on the split ({int(fam.sum()):,} columns)")
    ax.scatter(cxy[~fam, 0], cxy[~fam, 1], s=4, marker="s", c=C_WALL, label=f"members standing on the end walls ({int((~fam).sum()):,})")
    ax.set_aspect("equal")
    ax.set_title("A. The motor side seen along the pull: where metal may go\n(white: the gear rooms' inside and the fixed parts, never designed)",
                 fontsize=11)  # fmt: skip
    ax.legend(loc="lower left", fontsize=9, markerscale=3)
    zx, zy = 40.0, 40.0  # the close-up's window (mm)
    zw = 48.0
    ax.add_patch(Rectangle((zx, zy), zw, zw, fill=False, ec="k", lw=1.5))
    ax.annotate("B", (zx + zw, zy + zw), fontsize=12, weight="bold")
    # B. the close-up: cubes, points, control points
    ax = fig.add_subplot(gs[0, 1])
    in_win = (cxy[:, 0] > zx - 2) & (cxy[:, 0] < zx + zw + 2) & (cxy[:, 1] > zy - 2) & (cxy[:, 1] < zy + zw + 2)
    for (x0, y0), f_ in zip(cxy[in_win] - 2.0, fam[in_win], strict=True):
        ax.add_patch(Rectangle((x0, y0), 4.0, 4.0, fc=(C_SPLIT if f_ else C_WALL), alpha=0.18, ec=C_CUBE, lw=0.6))
    q = sp_["q"]
    sub = lo[:2] + (h / q) * (sp_["sub_ij"] + 0.5)
    sw = (sub[:, 0] > zx) & (sub[:, 0] < zx + zw) & (sub[:, 1] > zy) & (sub[:, 1] < zy + zw) & (sp_["sub_half"] == half)
    ax.scatter(sub[sw, 0], sub[sw, 1], s=5, c="#444", label="the 4 points each 4 mm cube is read at (2 mm apart)")
    kow = (ko[:, 0] > zx) & (ko[:, 0] < zx + zw) & (ko[:, 1] > zy) & (ko[:, 1] < zy + zw)
    ax.scatter(ko[kow, 0], ko[kow, 1], s=60, c=C_PHI, marker="+", lw=1.6, label="the outline's control points, every 6 mm")
    for kk, cc, lab in ((ksp, C_SPLIT, "a height field's control points, every 12 mm (on the split)"),
                        (kwl, C_WALL, "a height field's control points, every 12 mm (on the end walls)")):  # fmt: skip
        w_ = (kk[:, 0] > zx) & (kk[:, 0] < zx + zw) & (kk[:, 1] > zy) & (kk[:, 1] < zy + zw)
        ax.scatter(kk[w_, 0], kk[w_, 1], s=170, facecolors="none", edgecolors=cc, lw=2.0, label=lab)
    ax.set_xlim(zx, zx + zw)
    ax.set_ylim(zy, zy + zw)
    ax.set_aspect("equal")
    ax.set_title(f"B. Close-up {zw:.0f} x {zw:.0f} mm: the grey squares are the optimiser's 4 mm cubes\n(it computes stiffness on them; the shape "
                 "itself is the smooth fields)", fontsize=11)  # fmt: skip
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.04), fontsize=8.5, ncol=1)
    # C. a section: how the fields build members
    ax = fig.add_subplot(gs[0, 2])
    ax.axhline(0, color="k", lw=1.2)
    ax.text(2, 3, "the split (the two halves meet here)", fontsize=9)
    ax.add_patch(Rectangle((40, -100), 4, 100, fc="#888"))  # the side wall
    ax.add_patch(Rectangle((44, -104), 96, 4, fc="#888"))  # the end wall
    ax.text(70, -80, "gear room\n(inside)", ha="center", fontsize=9, color="#555")
    ax.text(150, -103, "4 mm shell (fixed)", fontsize=8.5, va="center")
    ax.add_patch(Rectangle((14, -46), 14, 46, fc=C_SPLIT, ec="k"))  # a member on the split
    ax.annotate("", (34, -46), (34, 0), arrowprops={"arrowstyle": "<->", "color": C_SPLIT, "lw": 2})
    ax.text(-4, -60, "height field on the split:\nhow far the member reaches\nfrom the split", fontsize=9, color="#b06a00")
    ax.add_patch(Rectangle((80, -122), 16, 18, fc=C_WALL, ec="k"))  # a member on the end wall
    ax.annotate("", (101, -122), (101, -104), arrowprops={"arrowstyle": "<->", "color": C_WALL, "lw": 2})
    ax.text(104, -128, "height field on the end walls:\nhow far the member stands\nout of the end wall (8 mm at least)", fontsize=9,
            color="#6c3483")  # fmt: skip
    ax.annotate("", (14, 8), (28, 8), arrowprops={"arrowstyle": "<->", "color": C_PHI, "lw": 2})
    ax.annotate("", (80, -96), (96, -96), arrowprops={"arrowstyle": "<->", "color": C_PHI, "lw": 2})
    ax.text(-4, 14, "the outline field: where each member is in plan, its sides", fontsize=9, color=C_PHI)
    ax.annotate("pull\n(the mould\nopens this way)", (170, -40), (170, 0), ha="center", fontsize=9,
                arrowprops={"arrowstyle": "->", "lw": 2})  # fmt: skip
    ax.set_xlim(-10, 190)
    ax.set_ylim(-140, 25)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("C. A cut through the motor side: the fields build each member\n(metal from its base to its height, between its sides)",
                 fontsize=11)  # fmt: skip
    # D. along a line: the outline field and each cube's share
    ax = fig.add_subplot(gs[1, 0:2])
    vals = np.array([-8, -8, -7, -2, 6, 8, 5, -3, -8, -8, -6, 2, 7, 8, 8, 6, -1, -8, -8], float)
    m = len(vals) - 3
    t = 6.0 * np.arange(-3, m + 4)
    xl = np.linspace(t[3], t[m + 3], 1500)
    curve = BSpline.design_matrix(xl, t, 3).toarray() @ vals
    ax.plot(xl, curve, color=C_PHI, lw=2.4, label="the outline field along a line (any value from -8 to +8 mm)")
    ax.scatter(t[1 : len(vals) + 1], vals, color=C_PHI, s=26, zorder=5, label="its control points, 6 mm apart")
    ax.fill_between(xl, 0, curve, where=curve > 0, color="#f5c6b8", alpha=0.7, label="positive: metal")
    ax.axhline(0, color="k", lw=0.9)
    cubes = np.arange(xl[0], xl[-1] - 3.99, 4.0)
    for x0 in cubes:
        pts2 = np.array([x0 + 1.0, x0 + 3.0])
        inside = np.interp(pts2, xl, curve) > 0
        share = inside.mean()
        ax.add_patch(Rectangle((x0, -13.5), 4.0, 3.0, fc=plt.cm.Greys(0.15 + 0.7 * share), ec="#666", lw=0.5))
        ax.scatter(pts2, [-12.0, -12.0], s=10, c=["#c0392b" if v else "#7f8c8d" for v in inside], zorder=6)
    ax.text(xl[0], -16.5, "the 4 mm cubes below, each read at its points (red inside, grey outside): a cube's metal is its share of "
            "points inside (dark full, light half, white none)", fontsize=9)  # fmt: skip
    ax.set_ylim(-18, 11)
    ax.set_xlabel("mm across members")
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("D. One line across two members: the outline field is a smooth curve; where it is positive is metal, its zero "
                 "crossings are the members' edges", fontsize=11)  # fmt: skip
    # E. where we are
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    steps = [
        ("lw8: cubes, members 8 mm wide", "passes FE (34 µm, 678 Hz, 4.94 kg); blocky", "#d5f5e3", "done"),
        ("The smooth space: these fields", "built; derivatives checked", "#d5f5e3", "done"),
        ("First smooth run (baseline2_spl)", "failed: mount-3 lost (bug), wavy, holes, blades", "#fadbd8", "failed"),
        ("Fixes", "mounts can't vanish; optimiser and drawing\nread the same 4 points a cube", "#d5f5e3", "done"),
        ("Tidy rules", "least gap 8 mm; outline length capped", "#d5f5e3", "done"),
        ("Next: one run from empty", "cap 3.0 m; ~25 min + FE; waiting your go", "#fef9e7", "next"),
        ("Then: brackets' bottom field", "metal may start above the split", "#eeeeee", "later"),
    ]
    for k, (title, note, colr, state) in enumerate(steps):
        y = 0.93 - k * 0.135
        ax.add_patch(FancyBboxPatch((0.02, y - 0.1), 0.96, 0.115, boxstyle="round,pad=0.01", fc=colr, ec="#888", transform=ax.transAxes))
        ax.text(0.05, y - 0.02, title, fontsize=10.5, weight="bold", transform=ax.transAxes, va="center")
        ax.text(0.05, y - 0.065, note, fontsize=9, transform=ax.transAxes, va="center")
        ax.text(0.95, y - 0.02, state, fontsize=9, ha="right", transform=ax.transAxes, va="center", style="italic")
    ax.set_title("E. Where we are", fontsize=11)
    fig.suptitle("The design space now: per half, ONE outline field (where metal is, in plan) and TWO height fields (how tall: members on the "
                 "split, members on the end walls)", fontsize=13.5)  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out = OUT / "spline_explain.png"
    fig.savefig(out, dpi=90)
    plt.close(fig)
    print(out)
    return out


if __name__ == "__main__":
    main()
