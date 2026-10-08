"""PROTOTYPE (LOP-3) - not product code: topology optimisation outside the plain shell.

A voxel model of the packaging space (the contract's volumes) with:
- **frozen solid:** the plain shell of LOP-1 (its walls, end walls, bosses, flange lips, mounts and
  the motor ring), from the same construction rules, voxel by voxel;
- **kept clear:** the gears' cavity, the bores and the shafts, and the room the outside needs: the
  motor beyond the motor-side face, the half-shafts beyond the output's faces, a tool's access to
  every flange bolt and mount;
- **free (the design space):** the rest of the packaging space, outside the shell.
The loads are LOP-2's: each seat's force over its bore's nodes, the motor's reaction on its ring;
the mounts' holes are held. SIMP (p = 3), a density filter (radius 1.5 voxels), optimality criteria
under a mass budget; each iteration solved by a cuDSS double factor, both load cases at once. The
objective is the two cases' compliance. The result is a hypothesis: the CAD, meshed and solved, is
the judge (fastcae's lesson).

Run: uv run python prototypes/first_loop/topo.py [budget_kg] [voxel_mm] [iterations]
     (default: 1.0 6 40; outputs data/first_loop/topo_<budget>kg.npz/.json/.png)
"""

from __future__ import annotations

import json
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

OUT = ROOT / "data" / "first_loop"
CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
YOUNG, POISSON, DENSITY = 69_000.0, 0.33, 2.6e-6  # MPa, -, kg/mm³
PENAL, E_MIN, FILTER = 3.0, 1e-6, 1.5


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
                dn *= 0.125 * (2 / h)  # d/dx = (2/h) d/dxi
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


def build_model(h: float):
    info = json.loads((OUT / "shell.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(CONTRACT)
    chain = complete_chain(spec)
    s = info["settings"]
    z_lo, z_hi, z_split = info["z"]["lo"], info["z"]["hi"], info["z"]["split"]
    clearance = 40.0
    outline = np.asarray(info["outer_outline"])
    # The packaging space (the volumes' prism): the outer outline grown by the clearance, as a hull.
    sys.path.insert(0, str(ROOT / "src"))
    from zenryx.geometry.solids import hull_of_circles

    pack = np.asarray(hull_of_circles([(x, y, clearance) for x, y in outline[::3]], segments=24))
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
    in_outer = inside(outline, x, y) & (z >= z_lo) & (z <= z_hi)
    inner = np.asarray(info["inner_outline"])
    wall = s.get("end_wall", s["wall"])
    in_cavity = inside(inner, x, y) & (z > z_lo + wall) & (z < z_hi - wall)
    shell = in_outer & ~in_cavity
    # The bosses stand inside the cavity (fused after it is cut, as in the CAD); what no metal may
    # fill (`hard`) is cut from the shell too.
    bosses = np.zeros(x.shape, dtype=bool)
    hard = np.zeros(x.shape, dtype=bool)
    for b in info["bearings"]:
        r = rho(b["axis"])
        z0, z1 = b["z"]
        if b["side"] == "-z":
            bosses |= (r <= b["D"] / 2 + s["boss"]) & (z >= z_lo) & (z <= z1)
            hard |= (r < b["D"] / 2 - s["shoulder"]) & (z > z_lo + wall) & (z < z0)
        else:
            bosses |= (r <= b["D"] / 2 + s["boss"]) & (z >= z0) & (z <= z_hi)
            hard |= (r < b["D"] / 2 - s["shoulder"]) & (z > z1) & (z < z_hi - wall)
        hard |= (r < b["D"] / 2) & (z >= z0) & (z <= z1)
        if b["sealed"]:
            hard |= (r < b["d"] / 2 + s["seal_radial"]) & (
                (z < z0) if b["side"] == "-z" else (z > z1)
            )
    shell |= bosses
    clear = in_cavity & ~bosses
    # flange lips (in the outline grown by the flange's width, at the split)
    lip = np.asarray(
        hull_of_circles([(xx, yy, s["flange_width"]) for xx, yy in outline[::3]], segments=24)
    )
    shell |= inside(lip, x, y) & (np.abs(z - z_split) <= s["flange_thickness"])
    # mounts, the motor ring
    for m in info["mounts"]:
        r = rho(m["centre"])
        shell |= (r <= s["mount_diameter"] / 2) & (z >= m["z"][0]) & (z <= m["z"][1])
        clear |= (r < s["mount_diameter"] / 2 + 4) & ((z < m["z"][0]) | (z > m["z"][1]))  # tool
    inp = next(b["axis"] for b in info["bearings"] if b["shaft"] == "input")
    out_axis = next(b["axis"] for b in info["bearings"] if b["shaft"] == "output")
    ring_in, ring_out = s["motor_ring"]
    r_in = rho(inp)
    shell |= (
        (r_in >= ring_in / 2)
        & (r_in <= ring_out / 2)
        & (z >= z_lo - s["motor_ring_thickness"])
        & (z <= z_lo)
    )
    clear |= (r_in < ring_out / 2 + 15) & (z < z_lo - s["motor_ring_thickness"])  # the motor
    clear |= (rho(out_axis) < 45) & ((z < z_lo) | (z > z_hi))  # the half-shafts' joints
    for c in info["bolts"]:
        clear |= (
            (rho(c) < 11)
            & (np.abs(z - z_split) > s["flange_thickness"])
            & (np.abs(z - z_split) < 45)
        )
    clear |= hard
    shell &= ~hard
    design = in_pack & ~shell & ~clear
    kind = np.full(x.shape, -1, dtype=np.int8)  # -1 not modelled, 0 design, 1 frozen
    kind[design] = 0
    kind[shell] = 1
    return {
        "info": info,
        "chain": chain,
        "h": h,
        "lo": lo,
        "n": n,
        "kind": kind,
        "centres": np.stack([x, y, z], axis=1),
        "inp": inp,
    }


def solve_model(model, budget_kg: float, iterations: int):
    import cupy as cp
    import cupyx.scipy.sparse as csp
    from nvmath.sparse.advanced import (
        DirectSolver,
        DirectSolverMatrixType,
        ExecutionCUDA,
        HybridMemoryModeOptions,
    )

    h, n, lo, kind = model["h"], model["n"], model["lo"], model["kind"]
    info, chain = model["info"], model["chain"]
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
    say(
        f"voxels {h:g} mm: {len(elem):,} elements ({frozen.sum():,} frozen shell, {(~frozen).sum():,} free), {n_dof:,} unknowns"
    )
    ke = hex_stiffness(h)
    dof = (3 * conn[:, :, None] + np.arange(3)[None, None, :]).reshape(-1, 24)
    rows = np.repeat(dof, 24, axis=1).ravel()
    cols = np.tile(dof, (1, 24)).ravel()

    # Loads: each seat's force over the shell's nodes on its bore; the motor's moment on its ring.
    s = info["settings"]
    f = np.zeros((n_dof, 2))
    cases = [c for c in chain.loads if c.name in ("peak drive", "peak reverse")]
    for j, case in enumerate(cases):
        for seat in case.seats:
            b = next(
                bb
                for bb in info["bearings"]
                if bb["shaft"] == seat.shaft and bb["side"] == seat.side
            )
            r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
            ids = np.flatnonzero(
                (np.abs(r - b["D"] / 2) <= 0.75 * h)
                & (xyz[:, 2] >= b["z"][0] - 0.5 * h)
                & (xyz[:, 2] <= b["z"][1] + 0.5 * h)
            )
            assert len(ids) > 8, (seat.shaft, seat.side, len(ids))
            for k in range(3):
                f[3 * ids + k, j] += seat.force[k] / len(ids)
        r_vec = xyz[:, :2] - np.asarray(model["inp"])
        r_len = np.hypot(r_vec[:, 0], r_vec[:, 1])
        ring_in, ring_out = s["motor_ring"]
        z_lo = info["z"]["lo"]
        ids = np.flatnonzero(
            (r_len >= ring_in / 2)
            & (r_len <= ring_out / 2)
            & (xyz[:, 2] <= z_lo - s["motor_ring_thickness"] + 0.5 * h)
        )
        tau = case.motor_torque
        denom = (r_len[ids] ** 2).sum()
        f[3 * ids, j] += -tau * r_vec[ids, 1] / denom
        f[3 * ids + 1, j] += tau * r_vec[ids, 0] / denom
    # Supports: the mounts' holes held.
    held = []
    for m in info["mounts"]:
        r = np.hypot(xyz[:, 0] - m["centre"][0], xyz[:, 1] - m["centre"][1])
        held.append(
            np.flatnonzero(
                (r <= s["mount_hole"] / 2 + 0.75 * h)
                & (xyz[:, 2] >= m["z"][0])
                & (xyz[:, 2] <= m["z"][1])
            )
        )
    held = np.unique(np.concatenate(held))
    fixed = np.zeros(n_dof, dtype=bool)
    for k in range(3):
        fixed[3 * held + k] = True
    free = np.flatnonzero(~fixed)
    say(f"loads on the seats and the motor ring; {len(held)} nodes held at the mounts")

    # The density filter (radius FILTER voxels) over the free elements.
    free_e = np.flatnonzero(~frozen)
    centres = ijk[free_e].astype(float)
    from scipy.spatial import cKDTree

    tree = cKDTree(centres)
    pairs = tree.sparse_distance_matrix(tree, FILTER, output_type="coo_matrix")
    w = np.maximum(0.0, FILTER - pairs.data)
    hmat = sp.coo_matrix((w, (pairs.row, pairs.col)), shape=(len(free_e), len(free_e))).tocsr()
    hmat = hmat + sp.eye(len(free_e)) * FILTER  # the element itself
    hs = np.asarray(hmat.sum(axis=1)).ravel()

    vol_e = h**3
    target = budget_kg / DENSITY / vol_e  # free voxels' worth of metal
    x = np.full(len(free_e), min(0.5, target / len(free_e)))
    history = []
    options = {"sparse_system_type": DirectSolverMatrixType.SPD, "multithreading_lib": _mtlayer()}
    execution = ExecutionCUDA(
        hybrid_memory_mode_options=HybridMemoryModeOptions(hybrid_memory_mode=True)
    )
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
        a = b = None
        release()
        u = np.zeros((n_dof, 2))
        u[free] = uf
        ue = u[dof]  # (elements, 24, 2)
        energy = np.einsum("eic,ij,ejc->e", ue, ke, ue)  # summed over the two cases
        compliance = float((e_scale * energy).sum())
        dc = -PENAL * dens ** (PENAL - 1) * (1 - E_MIN) * energy
        dcf = hmat.T @ (dc[free_e] / hs)
        dv = hmat.T @ (np.ones(len(free_e)) / hs)
        # optimality criteria with a bisection on the volume's multiplier
        lo_l, hi_l, move = 1e-9, 1e9, 0.2
        while hi_l / lo_l > 1 + 1e-4:
            mid = math.sqrt(lo_l * hi_l)
            cand = np.clip(
                x * np.sqrt(np.maximum(-dcf, 0) / (mid * dv)),
                np.maximum(0.001, x - move),
                np.minimum(1.0, x + move),
            )
            if ((hmat @ cand) / hs).sum() > target:
                lo_l = mid
            else:
                hi_l = mid
        change = float(np.abs(cand - x).max())
        x = cand
        seat_u = {}
        for seat in cases[0].seats:
            bb = next(
                b_
                for b_ in info["bearings"]
                if b_["shaft"] == seat.shaft and b_["side"] == seat.side
            )
            r = np.hypot(xyz[:, 0] - bb["axis"][0], xyz[:, 1] - bb["axis"][1])
            ids = np.flatnonzero(
                (np.abs(r - bb["D"] / 2) <= 0.75 * h)
                & (xyz[:, 2] >= bb["z"][0] - 0.5 * h)
                & (xyz[:, 2] <= bb["z"][1] + 0.5 * h)
            )
            seat_u[f"{seat.shaft} {seat.side}"] = [
                float(1000 * np.linalg.norm(u[3 * ids[:, None] + np.arange(3), c].mean(axis=0)))
                for c in (0, 1)
            ]
        worst = max(max(v) for v in seat_u.values())
        history.append(
            {
                "iteration": it,
                "compliance": compliance,
                "change": change,
                "worst_seat_um": worst,
                "seconds": time.time() - t0,
            }
        )
        say(
            f"it {it:3d}: compliance {compliance:,.0f} N·mm, change {change:.3f}, worst seat {worst:.0f} µm (voxel model), {time.time() - t0:.1f} s"
        )
        if it > 10 and change < 0.01:
            break
    phys = (hmat @ x) / hs
    return {
        "phys": phys,
        "free_e": free_e,
        "elem": elem,
        "frozen": frozen,
        "ijk": ijk,
        "history": history,
        "seat_um": seat_u,
        "n_dof": n_dof,
    }


def picture(model, result, path: Path, budget: float):
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
        return grid.threshold(0.5, scalars="on").extract_surface()

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
        plotter.add_text(
            f"material the optimisation adds (orange, density > 0.5), {budget:g} kg budget\n"
            + ("seen from the cover's side" if col == 0 else "seen from the motor's side"),
            font_size=9,
        )
    plotter.screenshot(str(path))


def main(budget: float = 1.0, h: float = 6.0, iterations: int = 40) -> None:
    t0 = time.time()
    model = build_model(h)
    result = solve_model(model, budget, iterations)
    stem = f"topo_{budget:g}kg_{h:g}mm"
    np.savez_compressed(
        OUT / f"{stem}.npz",
        phys=result["phys"],
        free_e=result["free_e"],
        elem=result["elem"],
        frozen=result["frozen"],
        ijk=result["ijk"],
        lo=model["lo"],
        n=model["n"],
        h=h,
    )
    (OUT / f"{stem}.json").write_text(
        json.dumps(
            {
                "budget_kg": budget,
                "voxel_mm": h,
                "history": result["history"],
                "seat_um": result["seat_um"],
                "unknowns": result["n_dof"],
                "seconds": time.time() - t0,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    picture(model, result, OUT / f"{stem}.png", budget)
    say(f"done in {time.time() - t0:.0f} s; {stem}.png")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(
        float(args[0]) if args else 1.0,
        float(args[1]) if len(args) > 1 else 6.0,
        int(args[2]) if len(args) > 2 else 40,
    )
