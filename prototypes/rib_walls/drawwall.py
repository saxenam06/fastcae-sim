"""The rib field on the walls drawn through the product's own drawing (LOP-34, the restart; a
prototype). `drawwall.py <label> [<design>] [--voxel=<mm>] [--state=<npz>]`.

Reads `optimise.py`'s state (`data/rib_walls/<label>.npz`, or `--state`), writes it as a run of the
product's format (`run_<label>.npz` and `.json`: each free cube's metal share as `phys`), then calls
`zenryx.domains.gearbox.housing.draw.draw` with the members' signed distance replaced by the walls'
(`wall_sdf`): the least walls, the protected interfaces, the root fillets (4 mm), the kept-clear
cuts, the exact cuts and the files are the product's own. Nothing in `src/` changes.

What is drawn, each part castable along the pull by construction (a deeper section within a
shallower one):

- **the end walls' ribs:** over the half's footprint in plan (its rooms and the plate under the other
  half's opening, each at its outer face), each family a stripe pattern along its direction
  `SPACING` mm apart (Knöppel et al. 2015, the toy's `draw.stripes`, per connected piece), each rib
  its thickness, standing its height off the face along the pull; under `T_DRAW` thick or
  `H_LEAST` tall none, its height tapering to its ends (`END_SLOPE`), a piece shorter than
  `L_LEAST` dropped; its free edges rounded `ROUND` mm;
- **the side walls' fins:** outside the footprint, radial in plan at family 0's stripe pattern round
  the outline, each its thickness and its height out from its wall (read at the split above its foot,
  as the model reads it), from the flange down to where its wall ends;
- **the ring bosses** round each bearing on its end wall (their outer radius and height), and **each
  lug's two webs** (their thickness and spread) over the lug's height, from the lug to the wall.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "rib_housing"))
sys.path.insert(0, str(HERE.parents[0] / "rib_field"))
sys.path.insert(0, str(HERE))  # first: rib_housing has an optimise.py too
import draw as toydraw  # noqa: E402
import housing  # noqa: E402
import model as toymodel  # noqa: E402
import optimise  # noqa: E402
import surface  # noqa: E402
import toy  # noqa: E402
import wallfield as wfm  # noqa: E402

OUT = optimise.OUT
T_DRAW = wfm.T_MIN + 0.5 * wfm.T_RAMP  # mm: the model carries half of a rib this thick
H_LEAST = 8.0  # mm: a lower rib is not drawn (twice the root fillet; the recipe's least member)
L_LEAST = 20.0  # mm: a shorter rib piece is not drawn (the toy's gate)
END_SLOPE = 1.0  # a rib's height past its least, a mm from where it ends (its end tapered)
ROUND = 3.0  # mm: the free edges' radius


def rebuild(label: str, voxel: float, state: Path | None = None):
    """The model's set-up, the field and the state."""
    from zenryx.domains.gearbox.forces import value_in

    vox, model = housing.product_model(voxel, out=optimise.model_dir(voxel))
    layout = json.loads((optimise.model_dir(voxel) / "contract.json").read_text(encoding="utf-8"))
    rooms = surface.rooms_of(vox)
    cm = surface.map_cubes(vox, layout, rooms)
    mat = model["spec"].manufacturing.material
    e, nu = value_in(mat.youngs_modulus, "MPa"), value_in(mat.poisson_ratio, "1")
    wf = wfm.WallField(vox, cm, layout, toymodel.rib_local(e, nu), toymodel.isotropic(e, nu), rooms)
    z = np.load(state or OUT / f"{label}.npz")
    wf.theta0 = z["theta0"]
    return vox, model, layout, rooms, wf, z["x"]


def _components(mask: np.ndarray, least: int = 50):
    from scipy.ndimage import label

    lab, n = label(mask)
    for k in range(1, n + 1):
        part = lab == k
        if part.sum() >= least:
            yield part


def stripes(theta: np.ndarray, mask: np.ndarray, step: float) -> np.ndarray:
    """The stripe pattern's phase over the mask, each connected piece solved on its own (one
    eigenvector over several pieces sits in one of them)."""
    phase = np.zeros(theta.shape)
    for part in _components(mask):
        ph, _ = toydraw.stripes(theta, part, wfm.SPACING, step)
        phase = np.where(part, ph, phase)
    return phase


def _pieces(mask: np.ndarray, step: float, least_area: float) -> np.ndarray:
    from scipy.ndimage import label

    lab, n = label(mask)
    if not n:
        return mask
    area = np.bincount(lab.ravel(), minlength=n + 1) * step * step
    keep = area >= least_area
    keep[0] = False
    return keep[lab]


def rib_plan(theta, t, h, mask, step, least_area):
    """A family's ribs in plan: their signed distance across (mm, positive inside) and their heights,
    gated, ended and filtered."""
    from scipy.ndimage import distance_transform_edt

    phase = stripes(theta, mask, step)
    d_mid = wfm.SPACING * np.abs(np.angle(np.exp(1j * phase))) / (2.0 * np.pi)
    a = 0.5 * t - d_mid
    gate = np.where(mask, np.minimum(t - T_DRAW, h - H_LEAST), -1.0)
    a = np.minimum(a, gate)
    d_end = distance_transform_edt(gate > 0) * step
    h = np.minimum(h, H_LEAST + END_SLOPE * d_end)
    a = np.where(mask, a, -step)
    rib = _pieces(a > 0, step, least_area)
    a = np.where((a > 0) & ~rib, -step, a)
    return a, h, rib


def plan_fields(ctx: dict, half: str, xs, ys) -> dict:
    """Everything the half's drawing reads in plan: its footprint and end faces' level, each end-wall
    family's ribs, the fins round it, the bosses and the webs."""
    wf, x, layout, rooms = ctx["wf"], ctx["x"], ctx["layout"], ctx["rooms"]
    from zenryx.domains.gearbox.housing import cup as cupmod

    lower = half == "motor_side"
    split, wall = float(layout["z"]["split"]), float(layout["settings"]["wall"])
    step = float(xs[1] - xs[0])
    PX, PY = np.meshgrid(xs, ys, indexing="ij")
    other = "cover" if lower else "motor_side"
    pcs = []
    for which in (half, other):
        for pc in cupmod.pieces(rooms, split, which):
            far = pc["far"] if which == half else split
            z_lo, z_hi = sorted((far, split))
            pcs.append((float(pc["axis"][0]), float(pc["axis"][1]), float(pc["r"]) + wall, z_lo - wall, z_hi + wall))
    foot_print = np.zeros(PX.shape, bool)
    zw = np.full(PX.shape, np.inf if lower else -np.inf)
    d_out = np.full(PX.shape, np.inf)  # the plan distance out from the footprint
    near_c = np.zeros(PX.shape + (2,))
    near_r = np.zeros(PX.shape)
    for cx, cy, R, zlo, zhi in pcs:
        rho = np.hypot(PX - cx, PY - cy)
        inside = rho <= R
        foot_print |= inside
        zw = np.where(inside, np.minimum(zw, zlo) if lower else np.maximum(zw, zhi), zw)
        closer = rho - R < d_out
        d_out = np.where(closer, rho - R, d_out)
        near_c[closer] = (cx, cy)
        near_r = np.where(closer, R, near_r)
    out = {"pcs": pcs, "F": foot_print, "zw": zw, "d_out": d_out, "PX": PX, "PY": PY}
    # the end walls: the fields at each plan point's face
    cells = np.flatnonzero(foot_print.ravel())
    foot = np.column_stack([PX.ravel()[cells], PY.ravel()[cells], zw.ravel()[cells]])
    s0, r0, s1, r1, tau = wf.values_at(x, half, foot)
    th0 = wf.theta0_at(half, foot)
    tcap = wf.thickness_cap(foot)[0]
    theta = th0 + math.pi * (tau - 0.5)

    def grid(v, fill=0.0):
        g = np.full(PX.size, fill)
        g[cells] = v
        return g.reshape(PX.shape)

    least = L_LEAST * T_DRAW
    out["fam"] = []
    for k, (sg, rr) in enumerate(((s0, r0), (s1, r1))):
        t = sg * tcap
        cap, _ = toy.smin(wfm.H_MOST, wfm.TALL * t)
        a, h, rib = rib_plan(grid(theta + k * math.pi / 2), grid(t), grid(rr * cap), foot_print, step, least)
        out["fam"].append({"a": a, "h": h, "rib": rib, "t": grid(t), "theta": grid(theta + k * math.pi / 2)})
    # the fins: outside the footprint, within the tallest rib's reach, read at the split above their
    # foot on the outline
    ring = (~foot_print) & (d_out <= wfm.H_MOST + 2 * step)
    rcells = np.flatnonzero(ring.ravel())
    u = np.column_stack([PX.ravel()[rcells] - near_c[..., 0].ravel()[rcells],
                         PY.ravel()[rcells] - near_c[..., 1].ravel()[rcells]])
    un = u / np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
    ffoot = np.column_stack([near_c[..., 0].ravel()[rcells], near_c[..., 1].ravel()[rcells]]) \
        + un * near_r.ravel()[rcells][:, None]
    read = np.column_stack([ffoot, np.full(len(rcells), split)])
    s0f, r0f, *_ = wf.values_at(x, half, read)
    tf = s0f * wf.thickness_cap(read)[0]
    capf, _ = toy.smin(wfm.H_MOST, wfm.TALL * tf)

    def rgrid(v, fill=0.0):
        g = np.full(PX.size, fill)
        g[rcells] = v
        return g.reshape(PX.shape)

    radial = rgrid(np.arctan2(un[:, 1], un[:, 0]))
    a, h, rib = rib_plan(radial, rgrid(tf), rgrid(r0f * capf), ring, step, wfm.T_MIN * H_LEAST)
    out["fins"] = {"a": a, "h": h, "rib": rib, "t": rgrid(tf), "ring": ring}
    # the bosses and the webs
    out["bosses"] = []
    for i, b in enumerate(wf.bosses):
        if b["half"] != half:
            continue
        xr, xh = wf.boss_x(x, i)
        out["bosses"].append({"name": b["name"], "axis": b["axis"],
                              "R": b["r0"] + wfm.BOSS_GROW[0] + wfm.BOSS_GROW[1] * float(xr),
                              "h": wfm.BOSS_TALL[0] + wfm.BOSS_TALL[1] * float(xh)})
    out["webs"] = []
    mounts = {m["name"]: m for m in layout["mounts"]}
    for i, w in enumerate(wf.webs):
        if w["half"] != half:
            continue
        xt, xa = wf.web_x(x, i)
        alpha = wfm.WEB_SPREAD[0] + w["span"] * float(xa)
        for sgn in (1.0, -1.0):
            out["webs"].append({"name": w["name"], "centre": w["centre"], "psi": w["phi0"] + sgn * alpha,
                                "t": wfm.WEB_MOST * float(xt), "r_lug": w["r_lug"], "l_cap": w["l_cap"],
                                "z": mounts[w["name"]]["z"]})
    return out


def wall_sdf(ctx, half, f, xs, ys, zs, footprint, smooth_mm, smooth_range) -> np.ndarray:  # noqa: ARG001
    """The half's ribs, fins, bosses and webs as one signed distance (mm, positive outside) on the
    drawing's grid: `columns.members_sdf`'s place and contract."""
    from zenryx.domains.gearbox.housing import say
    from zenryx.domains.gearbox.housing.walls import round_inter

    layout = ctx["layout"]
    lower = half == "motor_side"
    split, wall = float(layout["z"]["split"]), float(layout["settings"]["wall"])
    xs, ys, zs = (np.asarray(v, float) for v in (xs, ys, zs))
    step = float(xs[1] - xs[0])
    pf = plan_fields(ctx, half, xs, ys)
    ctx.setdefault("plans", {})[half] = pf
    PX, PY = pf["PX"], pf["PY"]
    out = np.full((len(xs), len(ys), len(zs)), np.inf, np.float32)
    side = np.flatnonzero(zs < split) if lower else np.flatnonzero(zs >= split)
    F, zw = pf["F"], pf["zw"]
    fins = pf["fins"]
    boss_rho = [np.hypot(PX - b["axis"][0], PY - b["axis"][1]) for b in pf["bosses"]]
    webs = []
    for w in pf["webs"]:
        u = np.array([math.cos(w["psi"]), math.sin(w["psi"])])
        p0, p1 = PX - w["centre"][0], PY - w["centre"][1]
        along = p0 * u[0] + p1 * u[1]
        cross = np.abs(p0 * u[1] - p1 * u[0])
        webs.append((w, np.maximum(cross - 0.5 * w["t"], np.maximum(w["r_lug"] - 2.0 - along, along - w["l_cap"]))))
    for kz in side:
        zc = zs[kz]
        sl = np.full(PX.shape, np.inf)
        # the end walls' ribs and the bosses, off their face along the pull
        y_e = np.where(F, (zw - zc) if lower else (zc - zw), np.inf)
        into = -y_e - wall  # no deeper than the wall's inner face
        for fam in pf["fam"]:
            if fam["rib"].any():
                sl = np.minimum(sl, np.maximum(round_inter(-fam["a"], y_e - fam["h"], ROUND), into))
        for b, rho in zip(pf["bosses"], boss_rho, strict=True):
            sl = np.minimum(sl, np.maximum(round_inter(rho - b["R"], y_e - b["h"], ROUND), into))
        # the fins: out from the walls at this level, from the flange down to where their wall ends
        y_s = np.full(PX.shape, np.inf)
        for cx, cy, R, zlo, zhi in pf["pcs"]:
            if zlo <= zc <= zhi:
                y_s = np.minimum(y_s, np.hypot(PX - cx, PY - cy) - R)
        if fins["rib"].any():
            f_s = np.maximum(round_inter(-fins["a"], y_s - fins["h"], ROUND), -y_s - wall)
            sl = np.minimum(sl, np.where(fins["ring"], f_s, np.inf))
        # the webs, over their lug's height
        for w, plan_d in webs:
            dz = max(w["z"][0] - zc, zc - w["z"][1])
            sl = np.minimum(sl, round_inter(plan_d, np.full(PX.shape, dz), ROUND))
        out[:, :, kz] = sl
    rib_area = sum(int(fm["rib"].sum()) for fm in pf["fam"]) * step * step / 100.0
    say(f"{half}: end-wall ribs over {rib_area:.0f} cm2 of plan (families {[int(fm['rib'].sum()) for fm in pf['fam']]} "
        f"cells), fins over {int(fins['rib'].sum()) * step * step / 100.0:.0f} cm2, "
        f"bosses {[(b['name'], round(b['R'], 1), round(b['h'], 1)) for b in pf['bosses']]}, "
        f"webs {[(w['name'], round(w['t'], 1), round(math.degrees(w['psi']), 1)) for w in pf['webs']]}")
    np.savez_compressed(OUT / f"plan_{ctx['design']}_{half}.npz", F=F, zw=zw, xs=xs, ys=ys,
                        **{f"rib{k}": fm["rib"] for k, fm in enumerate(pf["fam"])},
                        **{f"h{k}": fm["h"] for k, fm in enumerate(pf["fam"])},
                        **{f"theta{k}": fm["theta"] for k, fm in enumerate(pf["fam"])},
                        fin=fins["rib"], fin_h=fins["h"])
    return out


def write_run(label: str, vox, model, wf, x) -> tuple[str, dict]:
    """The state as a run of the product's format in `OUT`; its stem and the cubes' fields."""
    _, pc = wf.stiffness(x)
    share = pc["s"] + (1.0 - pc["s"]) * sum(f["g"] * f["rho"] for f in pc["fam"])
    phys = np.clip(share, 0.0, 1.0)
    stem = f"run_{label}"
    np.savez_compressed(OUT / f"{stem}.npz", phys=phys, x=phys, free_e=vox.free_e, elem=vox.elem,
                        frozen=vox.frozen, ijk=vox.ijk, lo=model["lo"], n=model["n"], h=float(model["h"]),
                        k_split=model["k_split"], beta=0.0, height_min=np.asarray(model["height_min"], np.float32),
                        solid=pc["s"])
    ribs_kg, solid_kg = wf.masses(pc)
    record = {"layout": "contract", "objective": "mass_tilt (the rib field on the walls)",
              "budget_kg": model["budget_kg"], "frozen_kg": model["frozen_kg"], "voxel_mm": float(model["h"]),
              "empty": True, "protect": True, "towers": False, "rib_walls": label,
              "placed_kg": {"ribs": ribs_kg, "features": solid_kg}}
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return stem, pc


def main() -> None:
    import os
    import shutil

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    label = args[0]
    design = args[1] if len(args) > 1 else f"walls_{label}"
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    voxel = float(opt.get("voxel", 4.0))
    state = Path(opt["state"]) if "state" in opt else None
    vox, model, layout, rooms, wf, x = rebuild(label, voxel, state)
    stem, pc = write_run(label, vox, model, wf, x)
    from zenryx.domains.gearbox.housing import draw as pdraw

    placed = np.zeros(int(np.prod(model["n"])), bool)
    placed[vox.elem[vox.free_e]] = pc["s"] >= 0.5
    placed = placed.reshape(tuple(int(v) for v in model["n"]))
    ctx = {"wf": wf, "x": x, "layout": layout, "rooms": rooms, "design": design,
           "holding": int((pc["s"] >= 0.5).sum()), "columns": int(len(pc["s"]))}
    pdraw.run_columns = lambda z, sigma, rnd: ctx  # noqa: ARG005
    pdraw.members_sdf = wall_sdf
    pdraw.extra_placed = lambda z: placed  # noqa: ARG005  (the features' cubes, for the cube check)
    env = dict(housing.recipe()["env"])
    if os.environ.get("RIB_DRAW_FINE"):  # the drawing's grid (mm) in place of the recipe's LOOP_DRAW_FINE
        env["LOOP_DRAW_FINE"] = os.environ["RIB_DRAW_FINE"]
    if not (OUT / "contract.json").exists():
        shutil.copy(optimise.model_dir(voxel) / "contract.json", OUT / "contract.json")
    pdraw.draw(stem, design, OUT, housing.CONTRACT, pdraw.DrawSettings.from_env(env))


if __name__ == "__main__":
    main()
