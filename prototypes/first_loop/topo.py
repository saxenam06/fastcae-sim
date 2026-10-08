"""PROTOTYPE (LOP-3) - not product code: topology optimisation outside a frozen shell.

A voxel model of the packaging space (the contract's volumes) with:
- **frozen solid:** the shell built before (convex or lobed form), from the same construction rules,
  voxel by voxel: its walls and end walls, bosses, flange lips, mounts, the motor flange;
- **kept clear:** the gears' cavity, the bores and the shafts, and the room the outside needs: the
  motor beyond the motor-side face, the half-shafts beyond the output's faces, a tool's access to
  every flange bolt and mount;
- **free (the design space):** the rest of the packaging space, outside the shell.
The loads are LOP-2's: each seat's force over its bore's nodes, the motor's reaction on its ring;
the mounts' holes are held. SIMP (p = 3), a density filter (radius 1.5 voxels), optimality
criteria under a mass budget; each iteration solved by a cuDSS double factor, both cases at once.

The objective (the agent's formulation choice):
- `compliance`: the two cases' compliance (the usual first run);
- `tilt`: a smooth maximum (p-norm, p = 6) of every seat's tilt over its line (0.75 x the
  contract's limit for its bearing type) in both cases: the measure the contract binds on. Its
  gradient by one adjoint solve per iteration on the same factor.
The result is a hypothesis: the CAD, meshed and solved, is the judge (fastcae's lesson).

Run: uv run python prototypes/first_loop/topo.py <shell_stem> <objective> <budget_kg> [voxel_mm]
     [iterations]   (e.g. lobed tilt 1.0 6 40; outputs data/first_loop/topo_<...>.npz/.json/.png)
"""

from __future__ import annotations

import json
import os
import math
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastcae_fe import _mtlayer, release  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import hull_of_circles  # noqa: E402

OUT = ROOT / "data" / "first_loop"
# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))
YOUNG, POISSON, DENSITY = 69_000.0, 0.33, 2.6e-6  # MPa, -, kg/mm³
PENAL, E_MIN, FILTER, P_NORM = 3.0, 1e-6, 1.5, 6.0


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def inside(polygon, x, y):
    """Point-in-polygon (even-odd), vectorised over x, y."""
    poly = np.asarray(polygon)
    xs, ys = poly[:, 0], poly[:, 1]
    xs2, ys2 = np.roll(xs, -1), np.roll(ys, -1)
    result = np.zeros(x.shape, dtype=bool)
    for x1, y1, x2, y2 in zip(xs, ys, xs2, ys2, strict=True):
        cond = (y1 > y) != (y2 > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xin = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        result ^= cond & (x < xin)
    return result


def hex_stiffness(h: float) -> np.ndarray:
    """An 8-node hexahedron's 24x24 stiffness, a cube of side h, 2x2x2 Gauss points."""
    lam = YOUNG * POISSON / ((1 + POISSON) * (1 - 2 * POISSON))
    mu = YOUNG / (2 * (1 + POISSON))
    d = np.zeros((6, 6))
    d[:3, :3] = lam
    d[np.arange(3), np.arange(3)] += 2 * mu
    d[np.arange(3, 6), np.arange(3, 6)] = mu
    corners = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)], float) * 2 - 1
    g = 1 / math.sqrt(3)
    ke = np.zeros((24, 24))
    for gx in (-g, g):
        for gy in (-g, g):
            for gz in (-g, g):
                dn = np.zeros((8, 3))
                for a, (xi, yi, zi) in enumerate(corners):
                    dn[a] = [
                        xi * (1 + yi * gy) * (1 + zi * gz),
                        yi * (1 + xi * gx) * (1 + zi * gz),
                        zi * (1 + xi * gx) * (1 + yi * gy),
                    ]
                dn *= 0.125 * (2 / h)
                b = np.zeros((6, 24))
                for a in range(8):
                    gxa, gya, gza = dn[a]
                    b[0, 3 * a] = gxa
                    b[1, 3 * a + 1] = gya
                    b[2, 3 * a + 2] = gza
                    b[3, 3 * a], b[3, 3 * a + 1] = gya, gxa
                    b[4, 3 * a + 1], b[4, 3 * a + 2] = gza, gya
                    b[5, 3 * a], b[5, 3 * a + 2] = gza, gxa
                ke += b.T @ d @ b * (h / 2) ** 3
    return ke


def build_model(stem: str, h: float):
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(CONTRACT)
    chain = complete_chain(spec)
    s = info["settings"]
    z_lo, z_hi, z_split = info["z"]["lo"], info["z"]["hi"], info["z"]["split"]
    end = s.get("end_wall", s["wall"])
    clearance = 40.0
    pods = info.get("pods") or [
        {
            "shaft": None,
            "outer": info["outer_outline"],
            "inner": info["inner_outline"],
            "z": (z_lo, z_hi),
        }
    ]
    points = [pt for p in pods for pt in p["outer"]]
    pack = np.asarray(hull_of_circles([(x, y, clearance) for x, y in points[::3]], segments=24))
    lo = np.array([pack[:, 0].min(), pack[:, 1].min(), z_lo - clearance])
    hi = np.array([pack[:, 0].max(), pack[:, 1].max(), z_hi + clearance])
    n = np.ceil((hi - lo) / h).astype(int)
    xc = lo[0] + h * (np.arange(n[0]) + 0.5)
    yc = lo[1] + h * (np.arange(n[1]) + 0.5)
    zc = lo[2] + h * (np.arange(n[2]) + 0.5)
    X, Y, Z = np.meshgrid(xc, yc, zc, indexing="ij")
    x, y, z = X.ravel(), Y.ravel(), Z.ravel()

    def rho(c):
        return np.hypot(x - c[0], y - c[1])

    in_pack = inside(pack, x, y) & (z >= lo[2]) & (z <= hi[2])
    in_outer = np.zeros(x.shape, dtype=bool)
    in_cavity = np.zeros(x.shape, dtype=bool)
    # A voxel is wall where it touches the wall, not only where its centre falls in it: a wall
    # thinner than a voxel would otherwise break into pieces. So the outer test takes any of a
    # voxel's four corners (end view) and the cavity test all four, and the cavity stops half a
    # voxel short of each end wall.
    half = h / 2
    corners = [(x + dx, y + dy) for dx in (-half, half) for dy in (-half, half)]
    for p in pods:
        z0, z1 = p["z"]
        out_any = np.zeros(x.shape, dtype=bool)
        in_all = np.ones(x.shape, dtype=bool)
        for cx_, cy_ in corners:
            out_any |= inside(p["outer"], cx_, cy_)
            in_all &= inside(p["inner"], cx_, cy_)
        in_outer |= out_any & (z >= z0 - half) & (z <= z1 + half)
        in_cavity |= in_all & (z - half > z0 + end) & (z + half < z1 - end)
    pod_z = {p["shaft"]: p["z"] for p in pods}
    shell = in_outer & ~in_cavity
    bosses = np.zeros(x.shape, dtype=bool)
    hard = np.zeros(x.shape, dtype=bool)
    for b in info["bearings"]:
        r = rho(b["axis"])
        z0, z1 = b["z"]
        plo, phi = pod_z.get(b["shaft"], (z_lo, z_hi))
        if b["side"] == "-z":
            bosses |= (r <= b["D"] / 2 + s["boss"]) & (z >= plo) & (z <= z1)
            hard |= (r < b["D"] / 2 - s["shoulder"]) & (z > plo + end) & (z < z0)
        else:
            bosses |= (r <= b["D"] / 2 + s["boss"]) & (z >= z0) & (z <= phi)
            hard |= (r < b["D"] / 2 - s["shoulder"]) & (z > z1) & (z < phi - end)
        hard |= (r < b["D"] / 2) & (z >= z0) & (z <= z1)
        if b["sealed"]:
            hard |= (r < b["d"] / 2 + s["seal_radial"]) & ((z < z0) if b["side"] == "-z" else (z > z1))
    shell |= bosses
    clear = in_cavity & ~bosses
    for p in pods:  # the flange lips at the split
        lip = hull_of_circles([(xx, yy, s["flange_width"]) for xx, yy in p["outer"][::3]], segments=24)
        shell |= inside(lip, x, y) & (np.abs(z - z_split) <= s["flange_thickness"])
    for m in info["mounts"]:
        r = rho(m["centre"])
        shell |= (r <= s["mount_diameter"] / 2) & (z >= m["z"][0]) & (z <= m["z"][1])
        clear |= (r < s["mount_diameter"] / 2 + 4) & ((z < m["z"][0]) | (z > m["z"][1]))
    inp = next(b["axis"] for b in info["bearings"] if b["shaft"] == "input")
    out_axis = next(b["axis"] for b in info["bearings"] if b["shaft"] == "output")
    ring_in, ring_out = s["motor_ring"]
    z_motor = info["z"].get("motor", z_lo)
    r_in = rho(inp)
    t_ring = s["motor_ring_thickness"]
    shell |= (r_in >= ring_in / 2) & (r_in <= ring_out / 2) & (z >= z_motor - t_ring) & (z <= z_motor)
    if info.get("pods"):  # the lobed form's flange plate for the motor
        shell |= (r_in <= ring_out / 2) & (z >= z_motor) & (z <= z_motor + end)
    clear |= (r_in < ring_out / 2 + 15) & (z < z_motor - t_ring)  # the motor
    clear |= (rho(out_axis) < 45) & ((z < z_lo) | (z > z_hi))  # the half-shafts' joints
    for c in info["bolts"]:
        clear |= (rho(c) < 11) & (np.abs(z - z_split) > s["flange_thickness"]) & (np.abs(z - z_split) < 45)
    clear |= hard
    shell &= ~hard
    design = in_pack & ~shell & ~clear
    kind = np.full(x.shape, -1, dtype=np.int8)  # -1 not modelled, 0 design, 1 frozen
    kind[design] = 0
    kind[shell] = 1
    return {"info": info, "spec": spec, "chain": chain, "h": h, "lo": lo, "n": n, "kind": kind,
            "inp": inp, "z_motor": z_motor}  # fmt: skip


def rotation_rows(xyz: np.ndarray, ids: np.ndarray, n_dof: int) -> sp.csr_matrix:
    """(3, n_dof): a node set's best-fit rotation (RBE3, uniform weights), as fe.py reads it."""
    p = xyz[ids]
    r = p - p.mean(axis=0)
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    a_inv = np.linalg.inv(a)
    skew = np.zeros((len(ids), 3, 3))
    skew[:, 0, 1], skew[:, 0, 2] = -r[:, 2], r[:, 1]
    skew[:, 1, 0], skew[:, 1, 2] = r[:, 2], -r[:, 0]
    skew[:, 2, 0], skew[:, 2, 1] = -r[:, 1], r[:, 0]
    rot = np.einsum("ab,nbc->nac", a_inv, skew)
    rows, cols, vals = [], [], []
    for a_ in range(3):
        for c_ in range(3):
            rows += [a_] * len(ids)
            cols += list(3 * ids + c_)
            vals += list(rot[:, a_, c_])
    return sp.csr_matrix((vals, (rows, cols)), shape=(3, n_dof))


def solve_model(model, budget_kg: float, iterations: int, objective: str):
    import cupy as cp
    import cupyx.scipy.sparse as csp
    from nvmath.sparse.advanced import (
        DirectSolver,
        DirectSolverMatrixType,
        ExecutionCUDA,
        HybridMemoryModeOptions,
    )

    h, n, lo, kind = model["h"], model["n"], model["lo"], model["kind"]
    info, chain, spec = model["info"], model["chain"], model["spec"]
    elem = np.flatnonzero(kind >= 0)
    frozen = kind[elem] == 1
    ijk = np.stack(np.unravel_index(elem, n), axis=1)
    offsets = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)])
    corner = ijk[:, None, :] + offsets[None, :, :]
    node_key = np.ravel_multi_index(corner.reshape(-1, 3).T, n + 1)
    used, inverse = np.unique(node_key, return_inverse=True)
    conn = inverse.reshape(-1, 8)
    xyz = lo + h * np.stack(np.unravel_index(used, n + 1), axis=1)
    n_nodes = len(used)
    n_dof = 3 * n_nodes
    say(f"voxels {h:g} mm: {len(elem):,} elements ({frozen.sum():,} frozen shell, {(~frozen).sum():,} free), {n_dof:,} unknowns")
    ke = hex_stiffness(h)
    dof = (3 * conn[:, :, None] + np.arange(3)[None, None, :]).reshape(-1, 24)
    rows = np.repeat(dof, 24, axis=1).ravel()
    cols = np.tile(dof, (1, 24)).ravel()

    s = info["settings"]
    f = np.zeros((n_dof, 2))
    cases = [c for c in chain.loads if c.name in ("peak drive", "peak reverse")]
    seat_ids = {}
    # A seat's nodes are the frozen shell's own: a node held only by near-empty design voxels
    # would swing freely and read as a tilt.
    on_shell = np.zeros(n_nodes, dtype=bool)
    on_shell[np.unique(conn[frozen])] = True
    for b in info["bearings"]:
        r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
        ids = np.flatnonzero(on_shell & (np.abs(r - b["D"] / 2) <= 0.75 * h) & (xyz[:, 2] >= b["z"][0] - 0.5 * h) & (xyz[:, 2] <= b["z"][1] + 0.5 * h))
        assert len(ids) > 8, (b["shaft"], b["side"], len(ids))
        seat_ids[(b["shaft"], b["side"])] = ids
    for j, case in enumerate(cases):
        for seat in case.seats:
            ids = seat_ids[(seat.shaft, seat.side)]
            for k in range(3):
                f[3 * ids + k, j] += seat.force[k] / len(ids)
        r_vec = xyz[:, :2] - np.asarray(model["inp"])
        r_len = np.hypot(r_vec[:, 0], r_vec[:, 1])
        ring_in, ring_out = s["motor_ring"]
        ids = np.flatnonzero((r_len >= ring_in / 2) & (r_len <= ring_out / 2) & (xyz[:, 2] <= model["z_motor"] - s["motor_ring_thickness"] + 0.5 * h))
        tau = case.motor_torque
        denom = (r_len[ids] ** 2).sum()
        f[3 * ids, j] += -tau * r_vec[ids, 1] / denom
        f[3 * ids + 1, j] += tau * r_vec[ids, 0] / denom
    held = []
    for m in info["mounts"]:
        r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
        held.append(np.flatnonzero((r <= s["mount_hole"] / 2 + 0.75 * h) & (xyz[:, 2] >= m["z"][0]) & (xyz[:, 2] <= m["z"][1])))
    held = np.unique(np.concatenate(held))
    fixed = np.zeros(n_dof, dtype=bool)
    for k in range(3):
        fixed[3 * held + k] = True
    free = np.flatnonzero(~fixed)
    # The seats' rotation rows and lines (rad), for the tilt objective and the record.
    limits = {t.bearing_type: value_in(t.limit, "rad") for t in spec.limits.bearing_tilt}
    margin = value_in(spec.limits.model_margin, "1")
    types = {(b.shaft, b.side.value): b.type for b in spec.requirement.shaft_layout.bearings}
    seats = []
    for key, ids in seat_ids.items():
        rr = rotation_rows(xyz, ids, n_dof)[:, free]
        seats.append((key, rr, (1 - margin) * limits[types[key]]))
    say(f"{objective} objective; {len(held)} nodes held at the mounts; {len(seats)} seats watched")

    free_e = np.flatnonzero(~frozen)
    from scipy.spatial import cKDTree

    tree = cKDTree(ijk[free_e].astype(float))
    pairs = tree.sparse_distance_matrix(tree, FILTER, output_type="coo_matrix")
    w = np.maximum(0.0, FILTER - pairs.data)
    hmat = sp.coo_matrix((w, (pairs.row, pairs.col)), shape=(len(free_e), len(free_e))).tocsr()
    hmat = hmat + sp.eye(len(free_e)) * FILTER
    hs = np.asarray(hmat.sum(axis=1)).ravel()

    target = budget_kg / DENSITY / h**3
    x = np.full(len(free_e), min(0.5, target / len(free_e)))
    history = []
    options = {"sparse_system_type": DirectSolverMatrixType.SPD, "multithreading_lib": _mtlayer()}
    execution = ExecutionCUDA(hybrid_memory_mode_options=HybridMemoryModeOptions(hybrid_memory_mode=True))
    rhs = f[free]
    for it in range(1, iterations + 1):
        t0 = time.time()
        phys = (hmat @ x) / hs
        dens = np.ones(len(elem))
        dens[free_e] = phys
        e_scale = E_MIN + dens**PENAL * (1 - E_MIN)
        vals = (e_scale[:, None] * ke.ravel()[None, :]).ravel()
        k = sp.coo_matrix((vals, (rows, cols)), shape=(n_dof, n_dof)).tocsr()
        kff = k[free][:, free]
        release()
        a = csp.csr_matrix(kff)
        b = cp.asfortranarray(cp.asarray(rhs))
        with DirectSolver(a, b, options=options, execution=execution) as solver:
            solver.plan()
            solver.factorize()
            uf = cp.asnumpy(solver.solve()).reshape(rhs.shape)
            ratios = {}
            if objective == "tilt":
                grad = np.zeros_like(uf)
                total = 0.0
                for key, rr, line in seats:
                    for c in range(2):
                        th = rr @ uf[:, c]
                        tilt = math.hypot(th[0], th[1])
                        ratio = tilt / line
                        ratios[(key, c)] = ratio
                        total += ratio**P_NORM
                        if tilt > 0:
                            # d(ratio^p)/du = p ratio^(p-1) / line * (th_x R_x + th_y R_y) / tilt
                            coef = P_NORM * ratio ** (P_NORM - 1) / line / tilt
                            grad[:, c] += coef * (th[0] * rr[0].toarray().ravel() + th[1] * rr[1].toarray().ravel())
                solver.reset_operands(b=cp.asfortranarray(cp.asarray(grad)))
                lam = cp.asnumpy(solver.solve()).reshape(rhs.shape)
        a = b = None
        release()
        u = np.zeros((n_dof, 2))
        u[free] = uf
        ue = u[dof]
        if objective == "tilt":
            lf = np.zeros((n_dof, 2))
            lf[free] = lam
            le = lf[dof]
            mixed = np.einsum("eic,ij,ejc->e", le, ke, ue)  # lambda' k_e u, summed over the cases
            value = total ** (1.0 / P_NORM)
            dc = -PENAL * dens ** (PENAL - 1) * (1 - E_MIN) * mixed
        else:
            energy = np.einsum("eic,ij,ejc->e", ue, ke, ue)
            value = float((e_scale * energy).sum())
            dc = -PENAL * dens ** (PENAL - 1) * (1 - E_MIN) * energy
            for key, rr, line in seats:
                for c in range(2):
                    th = rr @ uf[:, c]
                    ratios[(key, c)] = math.hypot(th[0], th[1]) / line
        dcf = hmat.T @ (dc[free_e] / hs)
        dv = hmat.T @ (np.ones(len(free_e)) / hs)
        lo_l, hi_l, move = 1e-30, 1e30, 0.2
        while hi_l / lo_l > 1 + 1e-4:
            mid = math.sqrt(lo_l * hi_l)
            cand = np.clip(x * np.sqrt(np.maximum(-dcf, 0) / (mid * dv)), np.maximum(0.001, x - move), np.minimum(1.0, x + move))
            if ((hmat @ cand) / hs).sum() > target:
                lo_l = mid
            else:
                hi_l = mid
        change = float(np.abs(cand - x).max())
        x = cand
        worst = max(ratios.items(), key=lambda kv: kv[1])
        history.append({"iteration": it, "objective": value, "change": change, "worst_tilt_ratio": worst[1], "worst_seat": f"{worst[0][0][0]} {worst[0][0][1]} case {worst[0][1]}", "seconds": time.time() - t0})
        say(f"it {it:3d}: {objective} {value:,.4g}, change {change:.3f}, worst tilt {worst[1]:.2f}x its line at {worst[0][0][0]} {worst[0][0][1]} (voxel model), {time.time() - t0:.1f} s")
        if it > 10 and change < 0.01:
            break
    phys = (hmat @ x) / hs
    return {"phys": phys, "free_e": free_e, "elem": elem, "frozen": frozen, "ijk": ijk, "history": history, "n_dof": n_dof}


def picture(model, result, path: Path, title: str):
    import pyvista as pv

    h, lo = model["h"], model["lo"]
    pv.OFF_SCREEN = True
    plotter = pv.Plotter(shape=(1, 2), window_size=(1600, 700), off_screen=True)

    def blocks(mask_e):
        ijk = result["ijk"][mask_e]
        if len(ijk) == 0:
            return None
        grid = pv.ImageData(dimensions=tuple(model["n"] + 1), spacing=(h, h, h), origin=tuple(lo))
        flags = np.zeros(model["n"], dtype=np.uint8)
        flags[tuple(ijk.T)] = 1
        grid.cell_data["on"] = flags.ravel(order="F")
        return grid.threshold(0.5, scalars="on").extract_surface(algorithm="dataset_surface")

    shell = blocks(result["frozen"])
    solid = np.zeros(len(result["elem"]), dtype=bool)
    solid[result["free_e"][result["phys"] > 0.5]] = True
    added = blocks(solid)
    for col, view in enumerate(((0.6, -0.5, 0.8), (-0.6, -0.5, -0.8))):
        plotter.subplot(0, col)
        if shell is not None:
            plotter.add_mesh(shell, color=(0.75, 0.76, 0.78), opacity=0.35)
        if added is not None:
            plotter.add_mesh(added, color=(0.90, 0.55, 0.15))
        plotter.view_vector(view, viewup=(0.0, -1.0, 0.0))
        side = "the cover's side" if col == 0 else "the motor's side"
        plotter.add_text(f"{title}: material added (orange, density > 0.5), seen from {side}", font_size=9)
    plotter.screenshot(str(path))


def main(shell: str, objective: str, budget: float, h: float = 6.0, iterations: int = 40) -> None:
    t0 = time.time()
    model = build_model(shell, h)
    result = solve_model(model, budget, iterations, objective)
    stem = f"topo_{shell}_{objective}_{budget:g}kg_{h:g}mm"
    np.savez_compressed(OUT / f"{stem}.npz", phys=result["phys"], free_e=result["free_e"], elem=result["elem"], frozen=result["frozen"], ijk=result["ijk"], lo=model["lo"], n=model["n"], h=h)
    (OUT / f"{stem}.json").write_text(json.dumps({"shell": shell, "objective": objective, "budget_kg": budget, "voxel_mm": h, "history": result["history"], "unknowns": result["n_dof"], "seconds": time.time() - t0}, indent=1), encoding="utf-8")
    picture(model, result, OUT / f"{stem}.png", f"{shell}, {objective}, {budget:g} kg")
    say(f"done in {time.time() - t0:.0f} s; {stem}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], float(a[2]), float(a[3]) if len(a) > 3 else 6.0, int(a[4]) if len(a) > 4 else 40)
