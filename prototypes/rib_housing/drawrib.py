"""The housing's rib field drawn through the product's own drawing (LOP-34; a prototype).

`drawrib.py <label> [<design>] [--voxel=<mm>]` reads `optimise.py`'s state
(`data/rib_housing/<label>.npz`), writes it as a run of the product's format (`rib_<label>.npz` and
`.json`: each free cube's metal share as `phys`), then calls `zenryx.domains.gearbox.housing.draw.draw`
with the members' signed distance (`columns.members_sdf`) replaced by the ribs' (`rib_sdf`), so the
least walls, the protected interfaces, the fillets, the kept-clear cuts, the exact cuts and the files
are the product's own. Nothing in `src/` changes: the two names are replaced in the drawing module's
namespace for this process only.

The ribs, per column group and family (the de-homogenisation, the toy's `draw.py`): on the drawing's
fine plan grid the directions, shares and heights read from the columns; a stripe pattern along the
directions `SPACING` mm apart (`prototypes/rib_field/draw.stripes`, Knöppel et al. 2015); a point a
rib's where cos(phase) >= cos(pi rho), so each rib is rho x SPACING thick; under `rules.T_LEAST`
thick or `rules.H_LEAST` tall none, and a piece shorter than `L_LEAST` (its area under L_LEAST x
T_LEAST) dropped. Each rib's free end is its column's height past the column's base, on one scale
from the split (as the product's `E`), its edge rounded (`round_inter`). The solid zones (bosses and
brackets) are drawn as the product draws a column: its outline where its height holds metal, its
free end its height.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import field as fieldmod  # noqa: E402
import housing  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rib_field"))
import draw as toydraw  # noqa: E402
import model as toymodel  # noqa: E402
import rules  # noqa: E402

L_LEAST = 20.0  # mm: a shorter rib piece is not drawn (the toy's gate)
OUTLINE_SIGMA = 3.0  # mm: a group's and a solid zone's outline blurred (the product's LOOP_VOXEL_SMOOTH)


def rebuild(label: str, voxel: float):
    """The model, the field and its state (`optimise.py`'s `<label>.npz`)."""
    from zenryx.domains.gearbox.forces import value_in

    vox, model = housing.product_model(voxel)
    mat = model["spec"].manufacturing.material
    e, nu = value_in(mat.youngs_modulus, "MPa"), value_in(mat.poisson_ratio, "1")
    hf = fieldmod.HousingField(vox, housing.column_groups(vox), toymodel.rib_local(e, nu), toymodel.isotropic(e, nu))
    z = np.load(housing.OUT / f"{label}.npz")
    x = z["x"]
    for g in hf.groups:
        g.theta0 = z[f"theta0_{g.name}"]
    return vox, model, hf, x


def columns_of(vox, hf, x) -> dict:
    """Every column's half, plan cell, base cube, group and fields, for `rib_sdf`."""
    _, pc = hf.stiffness(x)
    so = pc["solid"]
    n_cols = len(hf.col_len_mm)
    ijk = vox.ijk[vox.free_e]
    base = np.full(n_cols, -1, np.int64)
    first = hf.pos == 0
    base[hf.col[first]] = ijk[first, 2]
    ij = np.zeros((n_cols, 2), np.int64)
    ij[hf.col] = ijk[:, :2]
    half = np.zeros(n_cols, np.int8)
    for grp in hf.groups:
        half[grp.cols] = 1 if grp.half == "cover" else 0
    hs = np.zeros(n_cols)
    hs[hf.zcols] = so["hs"]
    zone = np.zeros(n_cols, bool)
    zone[hf.zcols] = True
    zone_len = np.zeros(n_cols)  # how far from its base a column's solid zone reaches (mm)
    np.maximum.at(zone_len, hf.col[hf.in_zone], (hf.pos[hf.in_zone] + 1.0) * hf.a)
    return {
        "zone_len": zone_len,
        "run_of_group": [int(g.name.rsplit("run", 1)[1]) for g in hf.groups],
        "ij": ij,
        "half": half,
        "base": base,
        "group": hf.group_of_col.copy(),
        "theta": pc["theta"],
        "rho": np.stack([f["rho"] for f in pc["fam"]]),
        "h": np.stack([f["h"] for f in pc["fam"]]),
        "hs": hs,
        "zone": zone,
        "round_mm": 3.0,
        "spacing": fieldmod.SPACING,
        "holding": int((np.stack([f["h"] for f in pc["fam"]]).max(axis=0) >= rules.H_LEAST).sum()),
        "columns": int(n_cols),
        "pc": pc,
    }


def _carried(a: np.ndarray) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt

    if np.isnan(a).all():
        return np.zeros_like(a)
    _, (ia, ja) = distance_transform_edt(np.isnan(a), return_indices=True)
    return a[ia, ja]


def _signed(mask: np.ndarray, step: float) -> np.ndarray:
    """The true plan distance from a mask's outline (mm, positive inside)."""
    from scipy.ndimage import distance_transform_edt

    if not mask.any():
        return np.full(mask.shape, -1e6)
    d_in = distance_transform_edt(mask) * step
    d_out = distance_transform_edt(~mask) * step
    return np.where(mask, d_in - 0.5 * step, -(d_out - 0.5 * step))


def _pieces(mask: np.ndarray, step: float) -> np.ndarray:
    """The rib pieces kept: each at least `L_LEAST` x `rules.T_LEAST` in area."""
    from scipy.ndimage import label

    lab, n = label(mask)
    if not n:
        return mask
    area = np.bincount(lab.ravel(), minlength=n + 1) * step * step
    keep = area >= L_LEAST * rules.T_LEAST
    keep[0] = False
    return keep[lab]


def rib_sdf(cols, half, f, xs, ys, zs, footprint, smooth_mm, smooth_range) -> np.ndarray:
    """The half's ribs and solid zones as a signed distance (mm, positive outside), on the drawing's
    grid: `columns.members_sdf`'s place and contract."""
    from scipy.ndimage import gaussian_filter, map_coordinates

    from zenryx.domains.gearbox.housing.columns import fill_diagonals
    from zenryx.domains.gearbox.housing.walls import round_inter

    h, lo, n = float(f["h"]), np.asarray(f["lo"], float), [int(v) for v in f["n"]]
    ks = int(f["k_split"])
    zsp = lo[2] + h * ks  # the split on the model's grid
    lower = half == "motor_side"
    xs, ys, zs = (np.asarray(v, float) for v in (xs, ys, zs))
    step = float(xs[1] - xs[0])
    side = zs < zsp if lower else zs >= zsp
    zz = zs[side][None, None, :]
    out = np.full((len(xs), len(ys), len(zs)), np.inf, np.float32)
    part = np.full((len(xs), len(ys), int(side.sum())), np.inf, np.float32)
    CI, CJ = np.meshgrid((xs - lo[0]) / h - 0.5, (ys - lo[1]) / h - 0.5, indexing="ij")
    at = [CI, CJ]
    cell_i = np.clip(np.floor(CI + 0.5).astype(int), 0, n[0] - 1)
    cell_j = np.clip(np.floor(CJ + 0.5).astype(int), 0, n[1] - 1)
    rnd = float(cols["round_mm"])
    spacing = float(cols["spacing"])
    sig = OUTLINE_SIGMA / h
    report = []
    for g in np.unique(cols["group"][cols["half"] == (0 if lower else 1)]):
        sel = np.flatnonzero(cols["group"] == g)
        ii, jj = cols["ij"][sel, 0], cols["ij"][sel, 1]

        def grid(v, fill=np.nan, ii=ii, jj=jj):
            a = np.full(n[:2], fill, float)
            a[ii, jj] = v
            return a

        present = grid(1.0, 0.0)
        area = map_coordinates(gaussian_filter(present, sig), at, order=1) / np.maximum(
            map_coordinates(gaussian_filter(np.ones(n[:2]), sig), at, order=1), 1e-9) >= 0.5
        base_c = _carried(grid(cols["base"][sel].astype(float)))
        base_f = np.rint(base_c[cell_i, cell_j]).astype(np.int64)
        o_base = (h * ((ks - 1) - base_f)) if lower else (h * (base_f - ks))  # mm from the split
        face = (lo[2] + h * (base_f + 1)) if lower else (lo[2] + h * base_f)
        th = cols["theta"][sel]
        v2 = [map_coordinates(_carried(grid(np.cos(2 * th))), at, order=1),
              map_coordinates(_carried(grid(np.sin(2 * th))), at, order=1)]
        theta = 0.5 * np.arctan2(v2[1], v2[0])
        ribs_g = 0
        for k in range(2):
            rho = map_coordinates(_carried(grid(cols["rho"][k][sel])), at, order=1)
            hk = map_coordinates(_carried(grid(cols["h"][k][sel])), at, order=1)
            phase, _ = toydraw.stripes(theta + k * np.pi / 2, area, spacing, step)
            rib = (np.cos(phase) >= np.cos(np.pi * np.clip(rho, 0.0, 1.0))) & area
            rib &= (rho * spacing >= rules.T_LEAST) & (hk >= rules.H_LEAST)
            rib = fill_diagonals(_pieces(rib, step)[:, :, None])[:, :, 0]
            ribs_g += int(rib.sum())
            if not rib.any():
                continue
            e_end = o_base + hk
            z_end = (zsp - e_end) if lower else (zsp + e_end)
            gx_, gy_ = np.gradient(z_end, step, step)
            slope = np.sqrt(1.0 + gx_ * gx_ + gy_ * gy_)[:, :, None]
            zdist = ((z_end[:, :, None] - zz) if lower else (zz - z_end[:, :, None])) / slope
            f_k = round_inter(-_signed(rib, step)[:, :, None], zdist, rnd)
            if cols["run_of_group"][g] > 1:  # a run past another: from its own first cube
                f_k = np.maximum(f_k, (zz - face[:, :, None]) if lower else (face[:, :, None] - zz))
            part = np.minimum(part, f_k.astype(np.float32))
        # the solid zones: the product's column drawing, each column its height of solid metal
        zsel = sel[cols["zone"][sel]]
        solid_n = 0
        if len(zsel):
            hs_c = grid(np.where(cols["zone"][sel], np.minimum(cols["hs"][sel], cols["zone_len"][sel]), np.nan))
            holds = grid((cols["zone"][sel] & (cols["hs"][sel] >= max(rules.H_LEAST, 0.5 * h))).astype(float), 0.0)
            zone_m = grid(cols["zone"][sel].astype(float), 0.0)
            num = map_coordinates(gaussian_filter(holds, sig), at, order=1)
            den = map_coordinates(gaussian_filter(np.maximum(zone_m, present), sig), at, order=1)
            solid = (num / np.maximum(den, 1e-9) >= 0.5) & area
            solid = fill_diagonals(solid[:, :, None])[:, :, 0]
            solid_n = int(solid.sum())
            if solid.any():
                hsf = map_coordinates(_carried(hs_c), at, order=1)
                e_end = o_base + hsf
                z_end = (zsp - e_end) if lower else (zsp + e_end)
                gx_, gy_ = np.gradient(z_end, step, step)
                slope = np.sqrt(1.0 + gx_ * gx_ + gy_ * gy_)[:, :, None]
                zdist = ((z_end[:, :, None] - zz) if lower else (zz - z_end[:, :, None])) / slope
                f_s = round_inter(-_signed(solid, step)[:, :, None], zdist, rnd)
                part = np.minimum(part, f_s.astype(np.float32))
        report.append(f"group {int(g)}: {len(sel):,} columns, rib area {ribs_g * step * step / 100:.0f} cm2, "
                      f"solid area {solid_n * step * step / 100:.0f} cm2")
    out[:, :, side] = part
    from zenryx.domains.gearbox.housing import say

    for r in report:
        say(f"{half}: {r}")
    return out


def write_run(label: str, vox, model, hf, x, cols) -> str:
    """The state as a run of the product's format in `housing.OUT`; its stem."""
    pc = cols["pc"]
    so, u = pc["solid"], pc["u"]
    share = so["g"] + u * sum(f["g"] * f["rho"][hf.col] for f in pc["fam"])
    phys = np.clip(share, 0.0, 1.0)
    stem = f"rib_{label}"
    np.savez_compressed(
        housing.OUT / f"{stem}.npz",
        phys=phys,
        x=phys,
        free_e=vox.free_e,
        elem=vox.elem,
        frozen=vox.frozen,
        ijk=vox.ijk,
        lo=model["lo"],
        n=model["n"],
        h=float(model["h"]),
        k_split=model["k_split"],
        beta=0.0,
        height_min=np.asarray(model["height_min"], np.float32),
        solid=so["g"],
    )
    ribs_kg, solid_kg = hf.masses(pc)
    record = {
        "layout": "contract",
        "objective": "mass_tilt (the rib field)",
        "budget_kg": model["budget_kg"],
        "frozen_kg": model["frozen_kg"],
        "voxel_mm": float(model["h"]),
        "empty": True,
        "protect": True,
        "towers": False,
        "rib_field": label,
        "placed_kg": {"ribs": ribs_kg, "solid": solid_kg},
    }
    (housing.OUT / f"{stem}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return stem


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    label = args[0]
    design = args[1] if len(args) > 1 else f"rib_{label}_drawn"
    voxel = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--voxel=")), 4.0))
    vox, model, hf, x = rebuild(label, voxel)
    cols = columns_of(vox, hf, x)
    stem = write_run(label, vox, model, hf, x, cols)
    from zenryx.domains.gearbox.housing import draw as pdraw

    so_g = cols["pc"]["solid"]["g"]
    placed = np.zeros(int(np.prod(model["n"])), bool)
    placed[vox.elem[vox.free_e]] = so_g >= 0.5
    placed = placed.reshape(tuple(int(v) for v in model["n"]))
    pdraw.run_columns = lambda z, sigma, rnd: cols  # noqa: ARG005
    pdraw.members_sdf = rib_sdf
    pdraw.extra_placed = lambda z: placed  # noqa: ARG005  (the solid zones' cubes, for the cube check)
    env = housing.recipe()["env"]
    if not (housing.OUT / "contract.json").exists():
        shutil.copy(housing.ROOT / "data" / "first_loop" / "contract.json", housing.OUT / "contract.json")
    pdraw.draw(stem, design, housing.OUT, housing.CONTRACT, pdraw.DrawSettings.from_env(env))


if __name__ == "__main__":
    main()
