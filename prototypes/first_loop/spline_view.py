"""PROTOTYPE (LOP-30) - the spline space pictured (the engineer, 14 October 18:50: "how many control points ... how much
variation can happen between them and how do we assure that we get smooth shapes instead of wiggly wobbly shapes").

Four panels, from a spline run's own set-up and its latest field (its checkpoint, or its finished field):
1. one half in plan: the 4 mm cubes' columns, the outline field's control points (its knots) and the height fields';
2. the outline field there, coloured by its value (mm), its zero line (the members' outline) drawn over it;
3. along one line: the control points, each one's cubic bell, their sum (the field) and where it crosses zero, beside
   the same values as 4 mm cubes would hold them;
4. what the knots allow: the narrowest member (two control points up among the rest down) and the tightest bend, and a
   random field's outline on the knots against the same randomness on the cubes.

Run: .venv/Scripts/python.exe prototypes/first_loop/spline_view.py <design or run stem> [--half motor_side|cover]
Writes data/first_loop/spline_view_<design>.png"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.interpolate import BSpline  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE.parents[1] / "data" / "first_loop"


def field_grid(fd: dict, coef_kept: np.ndarray, fill: float, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """A field's values on the plan grid xs x ys (mm): its full coefficient grid (the kept ones, `fill` elsewhere)."""
    nx, ny = fd["shape"]
    full = np.full(nx * ny, fill)
    full[fd["kept"]] = coef_kept
    full = full.reshape(nx, ny)
    mats = []
    for a, pts in enumerate((xs, ys)):
        m = fd["shape"][a] - 3
        t = fd["origin"][a] + fd["spacing"] * np.arange(-3, m + 4)
        mats.append(BSpline.design_matrix(np.clip(pts, t[3], t[m + 3]), t, 3).toarray())
    return mats[0] @ full @ mats[1].T


def main(name: str, half: str = "motor_side") -> Path:
    import topo
    from topo_free import build_free

    rec_p = OUT / f"{name}.json"
    run = json.loads(rec_p.read_text(encoding="utf-8")).get("outcome_of", name) if rec_p.exists() else name
    rr_p = OUT / f"{run}.json"
    if rr_p.exists():
        rr = json.loads(rr_p.read_text(encoding="utf-8"))
        spec = rr["spline"]
        lwm = float(rr.get("least_width_mm") or 0.0)
        lhm = float(rr.get("least_height_mm") or 0.0)
        x = np.load(OUT / f"{run}.npz")["x"]
        where = "its finished field"
    else:  # a run under way: its checkpoint, the set-up from its stem
        ck = next(OUT.glob(f"*{name}*_checkpoint.npz"))
        stem = ck.name[: -len("_checkpoint.npz")]
        a_, b_ = stem.rsplit("_spl", 1)[1].split("_")[0].split("x")
        spec, lwm, lhm = {"phi_mm": float(a_), "h_mm": float(b_)}, 8.0 if "_lw8" in stem else 0.0, 8.0 if "_lm8" in stem else 0.0
        z_ = np.load(ck)
        x = z_["x"]
        where = f"its field at iteration {int(z_['iteration'])} (beta {float(z_['beta']):g}), the run under way"
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
    sp_ = topo.spline_setup(spec, kind, n, ks, pts, layer, base, model["lo"], h, lhm / h, lwm)
    hv = 0 if half == "motor_side" else 1
    fo = next(fd for fd in sp_["fields"] if fd["kind"] == "outline" and fd["half"] == hv)
    fh = [fd for fd in sp_["fields"] if fd["kind"] == "height" and fd["half"] == hv]
    rng_mm = sp_["range"]
    c_phi = rng_mm * (2.0 * x[: sp_["n_phi"]] - 1.0)
    lo = np.asarray(model["lo"], float)
    sel = np.flatnonzero(sp_["half"] == hv)
    cxy = lo[:2] + h * (pts[sel] + 0.5)

    def knots_xy(fd):
        nx, ny = fd["shape"]
        ia, ja = np.unravel_index(fd["kept"], (nx, ny))
        # a coefficient's bell peaks at its knot: origin + spacing (a - 1) (the knots run from origin - 3 spacing)
        return np.column_stack([fd["origin"][0] + fd["spacing"] * (ia - 1), fd["origin"][1] + fd["spacing"] * (ja - 1)])

    fig = plt.figure(figsize=(19, 13))
    # 1. the control points over the cubes' columns
    ax = fig.add_subplot(2, 2, 1)
    ko, n_cols_half = knots_xy(fo), len(sel)
    ax.scatter(cxy[:, 0], cxy[:, 1], s=2.0, c="#c8c8c8", marker="s", label=f"the 4 mm cubes' columns ({n_cols_half:,})")
    ax.scatter(ko[:, 0], ko[:, 1], s=3.0, c="#1f5fbf", label=f"the outline's control points, every {spec['phi_mm']:g} mm ({len(ko):,})")
    nh = 0
    for fd, col_ in zip(fh, ("#e07b00", "#b0006a"), strict=False):
        kh = knots_xy(fd)
        nh += len(kh)
        ax.scatter(kh[:, 0], kh[:, 1], s=14.0, facecolors="none", edgecolors=col_, linewidths=0.8,
                   label=f"the heights' control points, every {spec['h_mm']:g} mm, columns {'on the split' if fd['family'] == 'split' else 'on a wall'} ({len(kh):,})")  # fmt: skip
    ax.set_aspect("equal")
    ax.set_title(f"{half.replace('_', ' ')}: {len(ko) + nh:,} control points shape the added metal (the cube space had one height per "
                 f"column, {n_cols_half:,})", fontsize=10)  # fmt: skip
    ax.legend(loc="lower left", fontsize=7, markerscale=2.5)
    # 2. the outline field and its zero line
    ax = fig.add_subplot(2, 2, 2)
    xs = np.arange(cxy[:, 0].min() - 6, cxy[:, 0].max() + 6, 1.0)
    ys = np.arange(cxy[:, 1].min() - 6, cxy[:, 1].max() + 6, 1.0)
    phi = field_grid(fo, c_phi[fo["offset"] : fo["offset"] + len(fo["kept"])], -rng_mm, xs, ys)
    inside = np.zeros((len(xs), len(ys)), bool)
    ii = np.clip(((cxy[:, 0] - xs[0]) // 1).astype(int), 0, len(xs) - 1)
    jj = np.clip(((cxy[:, 1] - ys[0]) // 1).astype(int), 0, len(ys) - 1)
    for di in range(-2, 3):
        for dj in range(-2, 3):
            inside[np.clip(ii + di, 0, len(xs) - 1), np.clip(jj + dj, 0, len(ys) - 1)] = True
    shown = np.where(inside, phi, np.nan)
    im = ax.imshow(shown.T, origin="lower", extent=(xs[0], xs[-1], ys[0], ys[-1]), cmap="RdBu_r", vmin=-rng_mm, vmax=rng_mm)
    ax.contour(xs, ys, np.where(inside, phi, -rng_mm).T, levels=[0.0], colors="k", linewidths=0.9)
    fig.colorbar(im, ax=ax, fraction=0.035, label="the outline field (mm): metal where positive")
    ax.set_aspect("equal")
    ax.set_title(f"the outline field, {where}; black: its zero line, the members' outline (before the 8 mm opening)", fontsize=10)
    # 3. along one line: the bells and their sum
    ax = fig.add_subplot(2, 2, 3)
    sp_mm = spec["phi_mm"]
    vals = np.array([-8, -8, -6, 3, 7, 5, -4, -8, -3, 6, 8, 8, 2, -7, -8, -8], float)
    m = len(vals) - 3
    t = sp_mm * np.arange(-3, m + 4)
    xl = np.linspace(t[3], t[m + 3], 1200)
    bm = BSpline.design_matrix(xl, t, 3).toarray()
    for k in range(len(vals)):
        ax.plot(xl, bm[:, k] * vals[k], color="#9ab", lw=0.7)
    curve = bm @ vals
    ax.plot(xl, curve, color="#1f5fbf", lw=2.2, label="the field: each point the sum of the four bells over it")
    knot_x = t[1 : len(vals) + 1]
    ax.scatter(knot_x, vals, color="#1f5fbf", zorder=5, s=28, label=f"the control points, {sp_mm:g} mm apart (any value -8..+8 mm)")
    cube_x = np.arange(t[3], t[m + 3], 4.0)
    cube_v = np.interp(cube_x + 2.0, xl, curve)
    ax.step(np.r_[cube_x, cube_x[-1] + 4.0], np.r_[np.sign(cube_v) * 9.5, np.sign(cube_v[-1]) * 9.5], where="post", color="#999",
            lw=1.0, label="4 mm cubes: in or out, a step at every cube")  # fmt: skip
    ax.axhline(0, color="k", lw=0.8)
    zc = xl[np.flatnonzero(np.diff(np.sign(curve)))]
    ax.scatter(zc, np.zeros_like(zc), marker="|", s=300, color="k", zorder=6, label="where the field crosses zero: the outline")
    ax.fill_between(xl, 0, curve, where=curve > 0, color="#f2b8a8", alpha=0.6)
    ax.set_xlabel("mm along a line across members")
    ax.set_ylabel("mm")
    ax.set_title("between control points the field is a blend of four cubic bells: it bends, never steps; its slope and curvature "
                 "are continuous everywhere", fontsize=10)  # fmt: skip
    ax.legend(fontsize=7, loc="lower right")
    # 4. what the knots allow, against the cubes
    ax = fig.add_subplot(2, 2, 4)
    rng = np.random.default_rng(3)
    ng = 14
    c_rand = rng.normal(0.0, 6.0, (ng + 3, ng + 3))
    c_rand[6:8, 3:13] = 7.0  # two rows of control points up: the narrowest member
    tt = sp_mm * np.arange(-3, ng + 4)
    gx = np.linspace(tt[3], tt[ng + 3], 600)
    bg = BSpline.design_matrix(gx, tt, 3).toarray()
    fld = bg @ c_rand @ bg.T
    cell = 4.0
    ci = np.arange(0, gx[-1], cell) + cell / 2
    bc = BSpline.design_matrix(np.clip(ci, tt[3], tt[ng + 3]), tt, 3).toarray()
    cubes = (bc @ c_rand @ bc.T) > 0
    noise = cubes ^ (rng.random(cubes.shape) < 0.08)  # the cube space: any cube in or out on its own
    ax.imshow(noise.T, origin="lower", extent=(0, len(ci) * cell, 0, len(ci) * cell), cmap="Greys", alpha=0.35)
    ax.contour(gx, gx, fld.T, levels=[0.0], colors="#1f5fbf", linewidths=1.8)
    ax.set_aspect("equal")
    ax.set_title(f"grey: what 4 mm cubes allow, any cube in or out (steps, crumbs, one-cube links); blue: what {sp_mm:g} mm control\n"
                 f"points allow, a random field's outline: smooth curves, bends no tighter than about one spacing; the straight band\n"
                 f"is two rows of control points up, about {1.9 * sp_mm:.0f} mm wide: the narrowest member the 8 mm opening keeps", fontsize=9)  # fmt: skip
    fig.suptitle(f"The spline space ({spec['phi_mm']:g} mm outline, {spec['h_mm']:g} mm heights): {len(ko) + nh:,} control points on the "
                 f"{half.replace('_', ' ')}, every member's outline a smooth curve", fontsize=13)  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = OUT / f"spline_view_{name}.png"
    fig.savefig(out, dpi=95)
    plt.close(fig)
    print(out)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    hf_ = "motor_side"
    if "--half" in args:
        k = args.index("--half")
        hf_ = args[k + 1]
        args = args[:k] + args[k + 2 :]
    main(args[0], hf_)
