"""The housing's walls as the surfaces its ribs stand on (LOP-34, the rib field on the walls; a
prototype: nothing in `src/` imports it).

Each half's shell is the contract's cup (`zenryx.domains.gearbox.housing.cup.pieces`: every room
from its far end in the half to the split, grown by the least wall), with the plate over the other
half's wider opening at the split, exactly as the product's least walls (`walls.least_sdf`, without
the sealing land and the seals' seats). Its signed distance is evaluated at any points
(`shell_sdf`). Every free cube of the product's model is mapped to its wall: its distance out from
the shell `d`, the wall's outward normal `n` there (the distance's gradient) and a tangent frame
(`e1`, `e2` = n x e1): on a face across the pull (an end wall, the plate under the other half's
rooms) e1 is +x, in plan; on a face along the pull (a side wall) e1 is the pull, so a rib at angle
0 there runs along the pull. A rib at angle theta runs along t = cos(theta) e1 + sin(theta) e2,
stands along n, and is thick along m = n x t.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "prototypes" / "rib_housing"))

ACROSS = 0.7  # |n_z| at least this: a face across the pull (in-plan frame); else along it


def rooms_of(vox) -> list[dict]:
    from zenryx.domains.gearbox.chain import complete_chain
    from zenryx.domains.gearbox.forces import value_in
    from zenryx.domains.gearbox.housing import cup as cupmod

    spec = vox.model["spec"]
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    return cupmod.rooms(chain, value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm"))


def shell_sdf(p: np.ndarray, layout: dict, all_rooms: list[dict], half: str) -> np.ndarray:
    """The half's shell's signed distance (mm, positive outside) at points p (N, 3)."""
    from zenryx.domains.gearbox.housing import cup as cupmod
    from zenryx.domains.gearbox.housing.walls import capped

    wall = float(layout["settings"]["wall"])
    z_split = float(layout["z"]["split"])
    other = "cover" if half == "motor_side" else "motor_side"
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    d = np.full(len(p), np.inf)
    for which in (half, other):
        for pc in cupmod.pieces(all_rooms, z_split, which):
            far = pc["far"] if which == half else z_split
            z_lo, z_hi = sorted((far, z_split))
            d = np.minimum(d, capped(x, y, z, pc["axis"], pc["r"], z_lo, z_hi))
    return d - wall


def frames(n: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each point's tangent frame (e1, e2) and kind (True: across the pull) from its normal."""
    across = np.abs(n[:, 2]) >= ACROSS
    ref = np.where(across[:, None], np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    e1 = ref - (ref * n).sum(axis=1, keepdims=True) * n
    e1 /= np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-12)
    e2 = np.cross(n, e1)
    return e1, e2, across


def map_cubes(vox, layout: dict, all_rooms: list[dict], eps: float = 0.25) -> dict:
    """Every free cube's wall: its half, distance out `d`, the foot point on the shell, the normal
    and the tangent frame there, and whether that face lies across the pull."""
    m = vox.model
    h, lo = float(m["h"]), np.asarray(m["lo"], float)
    split = float(layout["z"]["split"])
    c = lo + (vox.ijk[vox.free_e] + 0.5) * h
    lower = c[:, 2] < split
    d = np.zeros(len(c))
    grad = np.zeros((len(c), 3))
    for half, sel in (("motor_side", lower), ("cover", ~lower)):
        p = c[sel]
        d[sel] = shell_sdf(p, layout, all_rooms, half)
        for k in range(3):
            dp = np.zeros(3)
            dp[k] = eps
            grad[sel, k] = (shell_sdf(p + dp, layout, all_rooms, half) - shell_sdf(p - dp, layout, all_rooms, half)) / (2 * eps)
    n = grad / np.maximum(np.linalg.norm(grad, axis=1, keepdims=True), 1e-12)
    foot = c - d[:, None] * n
    e1, e2, across = frames(n)
    return {"centre": c, "lower": lower, "d": d, "n": n, "foot": foot, "e1": e1, "e2": e2,
            "across": across, "grad_norm": np.linalg.norm(grad, axis=1)}


def main() -> None:
    """The mapping's check and picture: `surface.py [voxel mm]`."""
    import json

    import housing

    voxel = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    vox, model = housing.product_model(voxel)
    layout = json.loads((housing.OUT / "contract.json").read_text(encoding="utf-8"))
    rooms = rooms_of(vox)
    cm = map_cubes(vox, layout, rooms)
    d, g = cm["d"], cm["grad_norm"]
    print(f"{len(d):,} free cubes; distance out from the shell: {np.percentile(d, [0, 5, 50, 95, 100]).round(1)} mm; "
          f"|grad| {np.percentile(g, [1, 50, 99]).round(3)} (a true distance reads 1)")
    for half, sel in (("motor_side", cm["lower"]), ("cover", ~cm["lower"])):
        print(f"{half}: {int(sel.sum()):,} cubes, {int((cm['across'] & sel).sum()):,} over faces across the pull "
              f"(end walls, the plate under the other half), {int((~cm['across'] & sel).sum()):,} beside faces along it "
              f"(side walls); {int(((d < -0.5) & sel).sum())} inside the shell")
    out = ROOT / "data" / "rib_walls"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"walls_{voxel:g}.npz", **{k: v for k, v in cm.items()})
    picture(cm, out / f"walls_{voxel:g}.png")


def picture(cm: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(20, 10))
    for k, (half, sel) in enumerate((("cover", ~cm["lower"]), ("motor_side", cm["lower"]))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        c = cm["centre"][sel]
        col = np.where(cm["across"][sel], "tab:blue", "tab:orange")
        ax.scatter(c[:, 0], c[:, 1], c[:, 2], s=1.5, c=col, alpha=0.5)
        f = cm["foot"][sel][::7]
        t = cm["e1"][sel][::7]
        ax.quiver(f[:, 0], f[:, 1], f[:, 2], t[:, 0], t[:, 1], t[:, 2], length=6, color="k", linewidth=0.3)
        ax.view_init(elev=28 if half == "cover" else -28, azim=-60)
        ax.set_title(f"the {half.replace('_', ' ')}'s design space: blue over faces across the pull, orange beside "
                     f"faces along it; black strokes: e1 (a rib at angle 0)")
        ax.set_box_aspect((1, 1, 0.6))
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    print(path)


if __name__ == "__main__":
    main()
