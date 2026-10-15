"""PROTOTYPE (LOP-30) - the spline map's fields fitted to a height-field run's own field: the check of the spline code on a
design FE has passed, before the optimiser runs in spline space (the engineer, 14 October 17:27: "Build the spline code,
check it on lw8 with the quick fit, then run the optimiser in spline space from the empty start").

- The outline field: fitted to the signed distance (mm) of the run's member columns (a column holding at least 1.5 voxels
  of metal), each level of each half on its own (as `topo.least_width_blocks` reads them), by least squares pulled to
  "no metal" where no column reads a coefficient.
- Each height field (the columns on the split, those on a wall): fitted to its member columns' heights, and lightly to
  the least member's where a column holds none.
- Written as a run of its own, `<run>_fit<outline>x<height>` (its field `.npz` with each column's fields, `spl_*`, and its
  record, the run's with `spline` and `fitted_from`), which `propose.py <design> --run <it>` draws from the fields
  (`outcome_cad.spline_members`) and judges.

It reports the cubes the fit keeps, loses and adds against the run, and the optimiser's own model on both (statics).

Run: .venv/Scripts/python.exe prototypes/first_loop/spline_fit.py <design or run> <outline mm>:<height mm> [--beta <b>]"""

from __future__ import annotations

import faulthandler
import json
import sys
import time
from pathlib import Path

import numpy as np

faulthandler.dump_traceback_later(180, repeat=True)  # a step stuck on the GPU shows where (14 October 18:03)
from scipy.ndimage import distance_transform_edt
from scipy.sparse.linalg import lsqr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

OUT = HERE.parents[1] / "data" / "first_loop"
METAL_VOX = 0.5  # a column holding metal is a member's: a run one voxel long holds one (round mount-1, between the split and the mount's room)


def run_of(name: str) -> str:
    p = OUT / f"{name}.json"
    if p.exists():
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("outcome_of"):
            return rec["outcome_of"]
    return name


def outline_target(pts: np.ndarray, half: np.ndarray, base: np.ndarray, metal: np.ndarray, h: float, rng_mm: float) -> np.ndarray:
    """Each column's signed distance (mm, positive inside) to the edge of the member columns of its own level and half,
    the edge half a cell past the last member column; clipped to the outline field's range."""
    target = np.zeros(len(pts))
    ii, jj = pts[:, 0].astype(int), pts[:, 1].astype(int)
    for key in set(zip(half.tolist(), base.tolist(), strict=True)):
        sel = np.flatnonzero((half == key[0]) & (base == key[1]))
        i0, j0 = ii[sel].min() - 1, jj[sel].min() - 1
        img = np.zeros((ii[sel].max() - i0 + 2, jj[sel].max() - j0 + 2), bool)
        img[ii[sel] - i0, jj[sel] - j0] = metal[sel]
        inside = distance_transform_edt(img)  # cells to the nearest cell without a member
        outside = distance_transform_edt(~img)
        d = np.where(img, inside - 0.5, -(outside - 0.5)) * h
        target[sel] = d[ii[sel] - i0, jj[sel] - j0]
    return np.clip(target, -rng_mm, rng_mm)


def main(name: str, spec: str, beta: float = 16.0) -> dict:
    import topo
    from grade import REFERENCE
    from topo_free import build_free

    t0 = time.time()
    run = run_of(name)
    rr = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    h = float(z["h"])
    phi_mm, h_mm = (float(v) for v in spec.split(":"))
    model = build_free(h, band=rr.get("band_mm"), flange=bool(rr.get("flange")), mount_reach=rr.get("mount_reach") or "disc",
                       height_field=(rr.get("height_field") or {}).get("radius_mm"), empty=bool(rr.get("empty")),
                       protect=bool(rr.get("protect")), flange_whole=bool(rr.get("flange_whole")), drawing_clear=bool(rr.get("drawing_clear")),
                       couplings=rr.get("couplings") or "glue", shell_fixed=bool(rr.get("shell_fixed")), towers=bool(rr.get("towers", True)))  # fmt: skip
    model["least_height_mm"] = rr.get("least_height_mm")
    model["least_width_mm"] = rr.get("least_width_mm")
    model["spline"] = {"phi_mm": phi_mm, "h_mm": h_mm}
    model["cases"] = tuple(rr.get("cases") or ("peak drive",))
    model["beds_mm"] = {"peak drive": REFERENCE["peak drive"] / 1000.0}
    vox = topo.Voxels(model)
    if len(vox.elem) != len(z["elem"]) or not np.array_equal(vox.elem, z["elem"]):
        raise SystemExit(f"{run}: its model built again does not give its voxels")
    hh, sp_ = vox.height, vox.spline
    phys_run = np.asarray(z["phys"], float)
    col_t = np.asarray(hh["C"] @ phys_run).ravel()  # each column's metal, voxels
    metal = col_t >= METAL_VOX
    rng_mm = sp_["range"]
    # the outline field: least squares on the signed distance, pulled to "no metal" (-range) where little reads it
    target = outline_target(hh["pts"], sp_["half"], sp_["base"], metal, h, rng_mm)
    # light damping: where few columns read a coefficient (an arm's last columns beside a mount's lug, which holds none)
    # damping 0.05 pulled the field under zero and cut every arm from its lug (14 October 18:10); and a few rounds that
    # raise the target where a member column still reads no metal
    goal = target.copy()
    for _ in range(6):
        c_shift = lsqr(sp_["B_phi"], goal + rng_mm, damp=1e-3, atol=1e-10, btol=1e-10, iter_lim=50000)[0]
        c_phi = np.clip(c_shift - rng_mm, -rng_mm, rng_mm)
        fitted = sp_["B_phi"] @ c_phi
        short = metal & (fitted < 0.5)
        if not short.any():
            break
        goal[short] += 1.0
    topo.say(f"the outline field: {int((metal & (fitted <= 0)).sum())} member columns read no metal, "
             f"{int((~metal & (fitted > 0)).sum())} others read metal")  # fmt: skip
    x_phi = 0.5 * (c_phi / rng_mm + 1.0)
    # the height fields: the member columns' heights alone (a column without a member holds nothing whatever its height:
    # pulled to the least member's there, the fields lowered the mounts' tall, narrow arms short of their lugs)
    span = hh["L"] - sp_["least"]
    want = np.clip((col_t - sp_["least"]) / span, 0.0, 1.0)
    rows_m = np.flatnonzero(metal)
    topo.say("the outline field fitted")
    x_h = np.clip(lsqr(sp_["B_h"][rows_m], want[rows_m], damp=0.02, atol=1e-10, btol=1e-10, iter_lim=20000)[0], 0.0, 1.0)
    topo.say("the height fields fitted")
    x = np.concatenate([x_phi, x_h])
    dens = vox.physical(x, beta)
    topo.say("the fit's field made")
    phys_fit = dens[vox.free_e]
    a_run, a_fit = phys_run >= 0.5, phys_fit >= 0.5
    cube_kg = topo.DENSITY * h**3
    cols_fit = vox.spline_columns(x, beta)
    fit_metal = (sp_["B_phi"] @ c_phi) > 0
    report = {"run": run, "spline": model["spline"], "beta": beta,
              "columns": {"members_run": int(metal.sum()), "members_fit": int((cols_fit["phi"] > 0).sum()),
                          "outline_sign_agrees": float(np.mean(fit_metal == metal))},
              "cubes": {"run": int(a_run.sum()), "fit": int(a_fit.sum()), "kept": int((a_run & a_fit).sum()),
                        "lost": int((a_run & ~a_fit).sum()), "added": int((~a_run & a_fit).sum())},
              "placed_kg": {"run": round(float(a_run.sum()) * cube_kg, 3), "fit": round(float(a_fit.sum()) * cube_kg, 3)},
              "coefficients": {"outline": sp_["n_phi"], "height": sp_["n_h"], "columns": len(hh["pts"])}}  # fmt: skip
    # the optimiser's own model on both, all metal or air at 0.5 (statics)
    for label, field in (("run", a_run), ("fit", a_fit)):
        d_ = np.ones(len(vox.elem))
        d_[vox.free_e] = field.astype(float)
        topo.say(f"the model on the {label}'s field: {int(field.sum()):,} cubes")
        out = vox.analyse(d_, "compliance_bound", adjoints=False)
        vox.release(out)
        beds = [float(v) * REFERENCE["peak drive"] for v in out["bed_vector"]]
        report[f"model_{label}"] = {"worst_seat_um": round(max(beds), 2), "worst_tilt": round(float(out["ratio_vector"].max()), 4)}
    stem = f"{run}_fit{phi_mm:g}x{h_mm:g}"
    extra = {"height_min": z["height_min"]} if "height_min" in z.files else {}
    extra.update({f"spl_{k}": v for k, v in cols_fit.items()})
    np.savez_compressed(OUT / f"{stem}.npz", phys=phys_fit, x=x, free_e=z["free_e"], elem=z["elem"], frozen=z["frozen"], ijk=z["ijk"],
                        lo=z["lo"], n=z["n"], h=h, k_split=z["k_split"], beta=beta, **extra)  # fmt: skip
    rec = dict(rr)
    rec.update({"spline": model["spline"], "fitted_from": run, "fit": report, "seconds": time.time() - t0, "history": [], "binary": None,
                "objective": f"fit to {run}"})  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    report["stem"] = stem
    print(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    args = sys.argv[1:]
    b_ = 16.0
    if "--beta" in args:
        k = args.index("--beta")
        b_ = float(args[k + 1])
        args = args[:k] + args[k + 2 :]
    main(args[0], args[1], b_)
