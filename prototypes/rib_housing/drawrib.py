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
rib's where cos(phase) >= cos(pi rho), so each rib is rho x SPACING thick; under `T_DRAW`
thick or `rules.H_LEAST` tall none, and a piece shorter than `L_LEAST` (its area under L_LEAST x
T_DRAW) dropped. Each rib's free end is its column's height past the column's base, on one scale
from the split (as the product's `E`), its edge rounded (`round_inter`). The solid zones (bosses and
brackets) are drawn as the product draws a column: its outline where its height holds metal, its
free end its height.
"""

from __future__ import annotations

import json
import os
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
END_SLOPE = 1.0  # a rib's height past its least, a mm from where it ends (its end tapered)
LUG_JOIN = 2.0  # mm: how far inside a lug's radius the members reach (they join its side)
LUG_INSET = 1.5  # mm: near a lug the members end this far inside its end planes
LUG_NEAR = 8.0  # mm: past a lug's radius, how far "near" reaches
# mm: a rib thinner than this is not drawn: the field's own least (`field.T_MIN`, the recipe's 8 mm
# least width), under which a rib carries nothing in the model. (`h2`'s field held 3 mm: its ribs'
# median was 4.6 mm, and FE's 7 mm surface folded them; `rib_h2t4` drew them from 4 mm.)
T_DRAW = float(os.environ.get("RIB_T_DRAW", fieldmod.T_MIN))
PLAN_OUT: Path | None = None  # where `rib_sdf` writes each half's plan reading (`plan_<design>_<half>.npz`)
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
    # each column on the split (beside the side walls) or on a wall: no unmodelled cell between the
    # split and its base (the product's `run_columns`)
    n = np.asarray(vox.model["n"], int)
    ks = int(vox.model["k_split"])
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[vox.elem] = 0
    off = np.concatenate([np.zeros(tuple(n[:2]) + (1,), np.int64),
                          np.cumsum(kind.reshape(tuple(n)) < 0, axis=2)], axis=2)
    k0 = np.where(half == 1, ks, base + 1)
    k1 = np.where(half == 1, base, ks)
    on_split = (off[ij[:, 0], ij[:, 1], np.maximum(k1, k0)] - off[ij[:, 0], ij[:, 1], k0]) == 0
    zone_len = np.zeros(n_cols)  # how far from its base a column's solid zone reaches (mm)
    np.maximum.at(zone_len, hf.col[hf.in_zone], (hf.pos[hf.in_zone] + 1.0) * hf.a)
    return {
        "on_split": on_split,
        "zone_len": zone_len,
        "run_of_group": [int(g.name.rsplit("run", 1)[1]) for g in hf.groups],
        "ij": ij,
        "half": half,
        "base": base,
        "group": hf.group_of_col.copy(),
        "theta": pc["theta"],
        "rho": np.stack([f["raw"] for f in pc["fam"]]),  # drawn at its raw thickness (from T_DRAW)
        "h": np.stack([f["h"] for f in pc["fam"]]),
        "hs": hs,
        "zone": zone,
        "round_mm": 3.0,
        "spacing": fieldmod.SPACING,
        "holding": int((np.stack([f["h"] for f in pc["fam"]]).max(axis=0) >= rules.H_LEAST).sum()),
        "columns": int(n_cols),
        "pc": pc,
        "discs": fieldmod.zone_discs(vox),
        "lugs": [{"half": "motor_side" if m["z"][1] <= vox.model["info"]["z"]["split"] else "cover",
                  "centre": list(m["centre"]),
                  "r": vox.model["info"]["settings"]["mount_diameter"] / 2 - LUG_JOIN,
                  "r_full": vox.model["info"]["settings"]["mount_diameter"] / 2,
                  "z": list(m["z"])}
                 for m in vox.model["info"]["mounts"]],
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
    """The rib pieces kept: each at least `L_LEAST` x `T_DRAW` in area."""
    from scipy.ndimage import label

    lab, n = label(mask)
    if not n:
        return mask
    area = np.bincount(lab.ravel(), minlength=n + 1) * step * step
    keep = area >= L_LEAST * T_DRAW
    keep[0] = False
    return keep[lab]


def _smoothed(z_end: np.ndarray, a: np.ndarray, step: float, smooth_mm: float, smooth_range: float) -> np.ndarray:
    """A free end smoothed in plan within its member (and twice the smoothing past its outline),
    steps taller than `smooth_range` kept: the product's bilateral filter and settings."""
    from zenryx.domains.gearbox.housing.columns import bilateral

    near = a > -2.0 * smooth_mm
    if smooth_mm <= 0 or not near.any():
        return z_end
    return np.where(near, bilateral(z_end, near, smooth_mm / step, smooth_range), z_end)


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
    PX, PY = np.meshgrid(xs, ys, indexing="ij")
    CI, CJ = np.meshgrid((xs - lo[0]) / h - 0.5, (ys - lo[1]) / h - 0.5, indexing="ij")
    at = [CI, CJ]
    cell_i = np.clip(np.floor(CI + 0.5).astype(int), 0, n[0] - 1)
    cell_j = np.clip(np.floor(CJ + 0.5).astype(int), 0, n[1] - 1)
    rnd = float(cols["round_mm"])
    # each lug's core kept the product's own (members join its side, LUG_JOIN deep): filled by the
    # members, its end faces met the brackets' rooms' exact cuts at its hole's rim, and FE's
    # coarsening folded the rim there (`rib_h2t4`, mount-1)
    off_lugs = np.full(PX.shape, 1e6)
    for lug in cols["lugs"]:
        if lug["half"] == half:
            off_lugs = np.minimum(off_lugs, np.hypot(PX - lug["centre"][0], PY - lug["centre"][1]) - lug["r"])
    spacing = float(cols["spacing"])
    sig = OUTLINE_SIGMA / h
    report = []
    plan = {"x": xs, "y": ys, "fam": np.zeros(PX.shape, np.int8), "rib_h": np.zeros(PX.shape, np.float32),
            "solid": np.zeros(PX.shape, bool), "solid_h": np.zeros(PX.shape, np.float32),
            "theta": np.full(PX.shape, np.nan, np.float32), "area": np.zeros(PX.shape, bool)}
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
        # each point's base: its family's (on the split outside the cup's outline, on a wall inside
        # it: the product's parting on `footprint`), so the cliff between them follows the outline,
        # not the columns' staircase
        fam_c = np.where(cols["on_split"][sel], 1, 2)
        own_fam = grid(fam_c, 0)[cell_i, cell_j]
        fam_f = np.where(footprint, 2, 1)
        has = {c: bool((fam_c == c).any()) for c in (1, 2)}
        fam_f = np.where(((fam_f == 1) & has[1]) | ((fam_f == 2) & has[2]), fam_f, own_fam)
        base_f = np.zeros(PX.shape, np.int64)
        for c in (1, 2):
            if has[c]:
                bc = _carried(grid(np.where(fam_c == c, cols["base"][sel], np.nan).astype(float)))
                base_f = np.where(fam_f == c, np.rint(bc[cell_i, cell_j]).astype(np.int64), base_f)
        o_base = (h * ((ks - 1) - base_f)) if lower else (h * (base_f - ks))  # mm from the split
        face = (lo[2] + h * (base_f + 1)) if lower else (lo[2] + h * base_f)

        def by_fam(v, keep=None, fam_c=fam_c, fam_f=fam_f, has=has, grid=grid):
            """A column quantity read at the points from its own family's columns only."""
            out_ = np.zeros(PX.shape)
            for c in (1, 2):
                if has[c]:
                    m_ = (fam_c == c) if keep is None else (fam_c == c) & keep
                    if m_.any():
                        g_ = map_coordinates(_carried(grid(np.where(m_, v, np.nan))), at, order=1)
                        out_ = np.where(fam_f == c, g_, out_)
            return out_
        th = cols["theta"][sel]
        v2 = [map_coordinates(_carried(grid(np.cos(2 * th))), at, order=1),
              map_coordinates(_carried(grid(np.sin(2 * th))), at, order=1)]
        theta = 0.5 * np.arctan2(v2[1], v2[0])
        plan["theta"] = np.where(area, theta, plan["theta"])
        plan["area"] |= area
        ribs_g = 0
        for k in range(2):
            rho = map_coordinates(_carried(grid(cols["rho"][k][sel])), at, order=1)
            hk = by_fam(cols["h"][k][sel])
            phase, _ = toydraw.stripes(theta + k * np.pi / 2, area, spacing, step)
            # the rib's side as a smooth distance (mm, positive inside): half its thickness less the
            # distance from its centre-line (the phase's zero, `spacing` a turn), its ends where it
            # thins under `T_DRAW` or drops under `H_LEAST`; the group's outline cuts it
            d_mid = spacing * np.abs(np.angle(np.exp(1j * phase))) / (2.0 * np.pi)
            a_k = 0.5 * np.clip(rho, 0.0, 1.0) * spacing - d_mid
            gate = np.minimum(rho * spacing - T_DRAW, hk - rules.H_LEAST)
            a_k = np.minimum(a_k, gate)
            # a rib's end tapers: near where it ends its height falls to the least
            # height at a slope of one (a full-height narrow tip read as a shard)
            from scipy.ndimage import distance_transform_edt

            d_end = distance_transform_edt(gate > 0) * step
            hk = np.minimum(hk, rules.H_LEAST + END_SLOPE * d_end)
            a_k = np.where(area, a_k, np.minimum(a_k, -step))
            a_k = np.minimum(a_k, off_lugs)
            rib = _pieces(a_k > 0, step)
            a_k = np.where((a_k > 0) & ~rib, -step, a_k)  # the short pieces dropped
            ribs_g += int(rib.sum())
            plan["fam"] = np.where(rib, plan["fam"] | (1 << k), plan["fam"]).astype(np.int8)
            plan["rib_h"] = np.where(rib, np.maximum(plan["rib_h"], hk), plan["rib_h"])
            if not rib.any():
                continue
            e_end = o_base + hk
            z_end = (zsp - e_end) if lower else (zsp + e_end)
            z_end = _smoothed(z_end, a_k, step, smooth_mm, smooth_range)
            gx_, gy_ = np.gradient(z_end, step, step)
            slope = np.sqrt(1.0 + gx_ * gx_ + gy_ * gy_)[:, :, None]
            zdist = ((z_end[:, :, None] - zz) if lower else (zz - z_end[:, :, None])) / slope
            f_k = round_inter(-a_k[:, :, None], zdist, rnd)
            if cols["run_of_group"][g] > 1:  # a run past another: from its own first cube
                f_k = np.maximum(f_k, (zz - face[:, :, None]) if lower else (face[:, :, None] - zz))
            part = np.minimum(part, f_k.astype(np.float32))
        # the solid zones: the product's column drawing, each column its height of solid metal
        zsel = sel[cols["zone"][sel]]
        solid_n = 0
        if len(zsel):
            # a column holds solid from half a cube (the product's columns), its height within its zone
            hs_eff = np.minimum(cols["hs"][sel], cols["zone_len"][sel])
            held = cols["zone"][sel] & (hs_eff >= 0.5 * h)
            # the outline: where the columns' heights, read cubic between the columns (the zone's
            # other columns at none), reach half a cube: a smooth line, not the columns' steps
            level = grid(np.where(cols["zone"][sel], hs_eff, 0.0), 0.0)
            solid = (map_coordinates(level, at, order=3, mode="nearest") >= 0.5 * h) & area
            # (an opening by the least width here cut the thin collars that join the lugs: not used)
            solid = fill_diagonals(solid[:, :, None])[:, :, 0]
            solid_n = int(solid.sum())
            if solid.any():
                # the outline: the holding columns' within the zones' exact discs (a boss's circle)
                a_zone = np.full(solid.shape, -1e6)
                for dsc in cols["discs"]:
                    if dsc["half"] == half:
                        a_zone = np.maximum(a_zone, dsc["r"] - np.hypot(PX - dsc["centre"][0], PY - dsc["centre"][1]))
                a_s = np.minimum(np.minimum(_signed(solid, step), a_zone), off_lugs)
                hsf = by_fam(hs_eff, keep=held)
                plan["solid"] |= a_s > 0
                plan["solid_h"] = np.where(a_s > 0, np.maximum(plan["solid_h"], hsf), plan["solid_h"])
                e_end = o_base + hsf
                z_end = (zsp - e_end) if lower else (zsp + e_end)
                z_end = _smoothed(z_end, a_s, step, smooth_mm, smooth_range)
                gx_, gy_ = np.gradient(z_end, step, step)
                slope = np.sqrt(1.0 + gx_ * gx_ + gy_ * gy_)[:, :, None]
                zdist = ((z_end[:, :, None] - zz) if lower else (zz - z_end[:, :, None])) / slope
                f_s = round_inter(-a_s[:, :, None], zdist, rnd)
                if cols["run_of_group"][g] > 1:
                    f_s = np.maximum(f_s, (zz - face[:, :, None]) if lower else (face[:, :, None] - zz))
                part = np.minimum(part, f_s.astype(np.float32))
        report.append(f"group {int(g)}: {len(sel):,} columns, rib area {ribs_g * step * step / 100:.0f} cm2, "
                      f"solid area {solid_n * step * step / 100:.0f} cm2")
    # near each lug the members end LUG_INSET inside its end planes: ended at the brackets' rooms'
    # cuts they lay 0.05 mm off the lug's own exact end faces, and FE's coarsening folded the two
    # (`rib_h2f`, mount-1's hole rim)
    for lug in cols["lugs"]:
        if lug["half"] != half:
            continue
        near = np.hypot(PX - lug["centre"][0], PY - lug["centre"][1]) < lug["r_full"] + LUG_NEAR
        if near.any():
            slab = np.maximum(zz - (lug["z"][1] - LUG_INSET), (lug["z"][0] + LUG_INSET) - zz).astype(np.float32)
            part = np.where(near[:, :, None], np.maximum(part, slab), part)
    out[:, :, side] = part
    if PLAN_OUT is not None:
        np.savez_compressed(PLAN_OUT.parent / f"plan_{PLAN_OUT.name}_{half}.npz", **plan)
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
    global PLAN_OUT
    PLAN_OUT = housing.OUT / design
    pdraw.draw(stem, design, housing.OUT, housing.CONTRACT, pdraw.DrawSettings.from_env(env))


if __name__ == "__main__":
    main()
