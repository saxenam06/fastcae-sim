"""PROTOTYPE (LOP-2) - not product code: the FE judgement of a two-half housing.

The engineer's FE practice (9 October 02:12-02:15):
- each bearing's load enters through a distributing coupling from the bearing's centre to every
  node of its seat (RBE3 weights, uniform): the force spread so force and moment balance;
- the two halves are joined at each bolt by distributing couplings: the two holes' best-fit rigid
  motions (RBE3 reference motions) are made equal;
- the mount bosses are held fixed through distributing couplings: each hole's best-fit rigid
  motion is zero;
- the motor's reaction torque acts on the motor flange's bolt holes, spread as RBE3 does.
A coupling's equation is imposed by a stiff penalty on the coupled nodes' mean translation and
best-fit rotation, so the stiffness stays symmetric positive definite for cuDSS's Cholesky.

The mesh: each half by gmsh (TET4, then straight-sided TET10 as fastcae does), the coupled nodes
found on the mesh's skin from the exact geometry (shell.json's seats, holes and bolts). The solve:
fastcae-v1's TET10 stiffness and cuDSS factor (fastcae_fe.py, copied), single precision refined to
double. The answer per load case: every seat's displacement and tilt (its nodes' best-fit rigid
motion), the shafts' tilts, the reactions (they must balance the loads), and the mass.

Run: uv run python prototypes/first_loop/fe.py [stem] [size_mm]     (default: shell 6)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import gmsh
import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastcae_fe import _factor_and_solve, quadratic, release, stiffness  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402

OUT = ROOT / "data" / "first_loop"
CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
YOUNG, POISSON, DENSITY = 69_000.0, 0.33, 2.6e-9  # MPa, -, t/mm³: the contract's EN AC-42100 T6
PENALTY_T = 1.0e9  # N/mm on a coupling's mean translation
PENALTY_R = 1.0e11  # N·mm/rad on its best-fit rotation
TOL = 0.25  # mm: how near a node must lie to a coupled surface


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


# --- the mesh ------------------------------------------------------------------------------------


def mesh_half(brep: Path, size: float) -> tuple[np.ndarray, np.ndarray]:
    """TET4 of one half by gmsh: nodes (n, 3) and tets (m, 4), 0-based."""
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.occ.importShapes(str(brep))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 1.2)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.model.mesh.generate(3)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        types, _, elem_nodes = gmsh.model.mesh.getElements(3)
        k = list(types).index(4)
        tets = np.asarray(elem_nodes[k], dtype=np.int64).reshape(-1, 4)
        index = np.full(int(tags.max()) + 1, -1, dtype=np.int64)
        index[tags] = np.arange(len(tags))
        return np.asarray(coords).reshape(-1, 3), index[tets]
    finally:
        gmsh.finalize()


def oriented(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    a, b, c, d = (nodes[tets[:, i]] for i in range(4))
    neg = np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a) < 0
    out = tets.copy()
    out[neg, 1], out[neg, 2] = tets[neg, 2], tets[neg, 1]
    return out


def skin_nodes(tets10: np.ndarray) -> np.ndarray:
    """The nodes on the mesh's outer surface (corner and mid-side), from the tets' unshared faces."""
    faces = np.array(
        [[0, 2, 1, 6, 5, 4], [0, 1, 3, 4, 8, 7], [1, 2, 3, 5, 9, 8], [0, 3, 2, 7, 9, 6]]
    )
    tri = tets10[:, faces].reshape(-1, 6)
    key = np.sort(tri[:, :3], axis=1)
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    outer = tri[counts[inverse.reshape(-1)] == 1]
    return np.unique(outer.ravel())


def on_cylinder(nodes, ids, centre, radius, z0, z1):
    p = nodes[ids]
    rho = np.hypot(p[:, 0] - centre[0], p[:, 1] - centre[1])
    keep = (np.abs(rho - radius) < TOL) & (p[:, 2] >= z0 - TOL) & (p[:, 2] <= z1 + TOL)
    return ids[keep]


# --- couplings -----------------------------------------------------------------------------------


def _skew(r: np.ndarray) -> np.ndarray:
    m = np.zeros((len(r), 3, 3))
    m[:, 0, 1], m[:, 0, 2] = -r[:, 2], r[:, 1]
    m[:, 1, 0], m[:, 1, 2] = r[:, 2], -r[:, 0]
    m[:, 2, 0], m[:, 2, 1] = -r[:, 1], r[:, 0]
    return m


def fit_rows(x: np.ndarray, ids: np.ndarray, offset: int, n_dof: int, point=None):
    """The rows that read a node set's best-fit rigid motion at a reference point (the set's
    centroid unless given): its translation there (3) and its rotation (3), as sparse (6, n_dof)
    - the RBE3 reference motion with uniform weights. Two sets tied at one point exchange forces
    there, so the tie adds no moment of its own."""
    p = x[ids]
    c = p.mean(axis=0)
    ref = c if point is None else np.asarray(point, dtype=float)
    r = p - c
    n = len(ids)
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    a_inv = np.linalg.inv(a)
    # rotation: theta = A^-1 sum r_i x u_i, with r x u = skew(r) u
    rot = np.einsum("ab,nbc->nac", a_inv, _skew(r))  # (n, 3, 3): theta's row, node, dof
    # translation at the reference: u_bar + theta x (ref - c) = u_bar - skew(ref - c) theta
    lever = _skew((ref - c)[None, :])[0]
    trans = np.eye(3)[None, :, :] / n - np.einsum("ab,nbc->nac", lever, rot)
    rows, cols, vals = [], [], []
    for block, first in ((trans, 0), (rot, 3)):
        for a_ in range(3):
            for c_ in range(3):
                rows += [first + a_] * n
                cols += list(offset + 3 * ids + c_)
                vals += list(block[:, a_, c_])
    return sp.csr_matrix((vals, (rows, cols)), shape=(6, n_dof)), ref


def rbe3_loads(x: np.ndarray, ids: np.ndarray, point, force, moment=(0.0, 0.0, 0.0)) -> np.ndarray:
    """Nodal forces (n, 3) spreading a force at `point` and a moment over the nodes so that the
    force and its moment balance (RBE3, uniform weights)."""
    p = x[ids]
    c = p.mean(axis=0)
    r = p - c
    n = len(ids)
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    m = np.cross(np.asarray(point) - c, np.asarray(force)) + np.asarray(moment)
    theta = np.linalg.solve(a, m)
    return np.asarray(force)[None, :] / n + np.cross(theta[None, :], r)


def rigid_fit(x, u, ids):
    p, d = x[ids], u[ids]
    c = p.mean(axis=0)
    r = p - c
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    theta = np.linalg.solve(a, np.cross(r, d).sum(axis=0))
    return d.mean(axis=0), theta, c


# --- the modes -----------------------------------------------------------------------------------


def modes(halves: dict, k: sp.csr_matrix, n_dof: int, count: int = 12) -> list[float]:
    """The housing's first natural frequencies (Hz) as held: Lanczos in shift-invert about zero
    (scipy's eigsh) on a cuDSS factor of the stiffness, with a lumped mass (HRZ: a TET10's corner
    nodes take 6/216 and its mid-side nodes 32/216 of its mass)."""
    import cupy as cp
    import cupyx.scipy.sparse as csp
    from fastcae_fe import _mtlayer
    from nvmath.sparse.advanced import (
        DirectSolver,
        DirectSolverMatrixType,
        ExecutionCUDA,
        HybridMemoryModeOptions,
    )
    from scipy.sparse.linalg import LinearOperator, eigsh

    mass = np.zeros(n_dof)
    weights = np.r_[np.full(4, 6 / 216), np.full(6, 32 / 216)]
    for h in halves.values():
        x = h["nodes"][h["tets"][:, :4]]
        vol = (
            np.abs(
                np.einsum(
                    "ij,ij->i", np.cross(x[:, 1] - x[:, 0], x[:, 2] - x[:, 0]), x[:, 3] - x[:, 0]
                )
            )
            / 6
        )
        nodal = np.zeros(len(h["nodes"]))
        np.add.at(nodal, h["tets"], (vol * DENSITY)[:, None] * weights[None, :])
        for c in range(3):
            mass[h["offset"] + 3 * np.arange(len(nodal)) + c] = nodal
    release()
    a = csp.csr_matrix(k.astype(np.float64))
    b = cp.asfortranarray(cp.zeros((n_dof, 1)))
    options = {"sparse_system_type": DirectSolverMatrixType.SPD, "multithreading_lib": _mtlayer()}
    execution = ExecutionCUDA(
        hybrid_memory_mode_options=HybridMemoryModeOptions(hybrid_memory_mode=True)
    )
    try:
        with DirectSolver(a, b, options=options, execution=execution) as solver:
            solver.plan()
            solver.factorize()

            def apply(v: np.ndarray) -> np.ndarray:
                solver.reset_operands(b=cp.asfortranarray(cp.asarray(v.reshape(-1, 1))))
                return cp.asnumpy(solver.solve()).reshape(-1)

            op = LinearOperator((n_dof, n_dof), matvec=apply, dtype=np.float64)
            values = eigsh(k, k=count, M=sp.diags(mass), sigma=0.0, OPinv=op, which="LM",
                           return_eigenvectors=False)  # fmt: skip
    finally:
        a = b = None
        release()
    return sorted(float(np.sqrt(max(v, 0.0)) / (2 * math.pi)) for v in values)


# --- the judgement -------------------------------------------------------------------------------


def judge(stem: str = "shell", size: float = 6.0) -> dict:
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(CONTRACT)
    chain = complete_chain(spec)
    z_split = info["z"]["split"]
    t0 = time.time()

    halves = {}
    offset = 0
    for half in ("motor_side", "cover"):
        nodes4, tets4 = mesh_half(OUT / f"{stem}_{half}.brep", size)
        tets4 = oriented(nodes4, tets4)
        nodes, tets10 = quadratic(nodes4, tets4)
        halves[half] = {
            "nodes": nodes,
            "tets": tets10,
            "skin": skin_nodes(tets10),
            "offset": offset,
        }
        offset += 3 * len(nodes)
        say(f"{half}: {len(tets10):,} TET10, {len(nodes):,} nodes")
    n_dof = offset
    say(f"meshed in {time.time() - t0:.0f} s; {n_dof:,} unknowns")

    def half_of(z: float) -> str:
        return "motor_side" if z < z_split else "cover"

    # The seats: each bearing's seat nodes, in the half that holds it.
    seats = {}
    for b in info["bearings"]:
        h = halves[half_of(0.5 * (b["z"][0] + b["z"][1]))]
        ids = on_cylinder(h["nodes"], h["skin"], b["axis"], b["D"] / 2, *b["z"])
        assert len(ids) > 20, f"too few seat nodes for {b['shaft']} {b['side']}: {len(ids)}"
        seats[(b["shaft"], b["side"])] = (half_of(0.5 * (b["z"][0] + b["z"][1])), ids, b)
    # Loads: the chain's seat forces per case, at the bearings' centres; the motor's reaction.
    cases = [c for c in chain.loads if c.name in ("peak drive", "peak reverse")]
    f = np.zeros((n_dof, len(cases)))
    for j, case in enumerate(cases):
        for s in case.seats:
            half, ids, b = seats[(s.shaft, s.side)]
            h = halves[half]
            point = (*b["axis"], 0.5 * (b["z"][0] + b["z"][1]))
            loads = rbe3_loads(h["nodes"], ids, point, s.force)
            for k in range(3):
                np.add.at(f[:, j], h["offset"] + 3 * ids + k, loads[:, k])
        # the motor's reaction on its flange's bolt holes, about the input's axis
        h = halves["motor_side"]
        z_lo = info["z"]["lo"]
        ring = info["settings"]["motor_ring_thickness"]
        motor_ids = np.concatenate(
            [
                on_cylinder(
                    h["nodes"],
                    h["skin"],
                    c,
                    info["settings"]["bolt_hole"] / 2,
                    z_lo - ring,
                    z_lo + 6,
                )
                for c in info["motor_holes"]
            ]
        )
        input_axis = next(b["axis"] for b in info["bearings"] if b["shaft"] == "input")
        loads = rbe3_loads(
            h["nodes"],
            motor_ids,
            (*input_axis, z_lo - ring / 2),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, case.motor_torque),
        )
        for k in range(3):
            np.add.at(f[:, j], h["offset"] + 3 * motor_ids + k, loads[:, k])
    say(f"loads: {len(cases)} cases; motor flange {len(motor_ids)} nodes")

    # Stiffness of both halves, then the couplings' penalties.
    t1 = time.time()
    blocks = []
    for half in ("motor_side", "cover"):
        h = halves[half]
        n = len(h["tets"])
        blocks.append(
            stiffness(h["nodes"], h["tets"], np.full(n, YOUNG), np.full(n, POISSON), gpu=True)
        )
        release()
    k = sp.block_diag(blocks, format="csr")
    say(f"stiffness assembled in {time.time() - t1:.0f} s: {k.nnz:,} entries")
    weights = sp.diags([PENALTY_T] * 3 + [PENALTY_R] * 3)
    penalty = sp.csr_matrix((n_dof, n_dof))
    mounts = []
    h = halves["motor_side"]
    for m in info["mounts"]:
        ids = on_cylinder(
            h["nodes"], h["skin"], m["centre"], info["settings"]["mount_hole"] / 2, *m["z"]
        )
        rows, c = fit_rows(h["nodes"], ids, h["offset"], n_dof)
        penalty = penalty + rows.T @ weights @ rows
        mounts.append((rows, c, len(ids)))
    bolts = 0
    lo, hi = halves["motor_side"], halves["cover"]
    t_f = info["settings"]["flange_thickness"]
    for c in info["bolts"]:
        a = on_cylinder(
            lo["nodes"], lo["skin"], c, info["settings"]["bolt_hole"] / 2, z_split - t_f, z_split
        )
        b_ = on_cylinder(
            hi["nodes"], hi["skin"], c, info["settings"]["bolt_hole"] / 2, z_split, z_split + t_f
        )
        if len(a) < 6 or len(b_) < 6:
            continue
        # Both holes' rigid motions read at the bolt's point on the split plane: tied there.
        point = (c[0], c[1], z_split)
        ra, _ = fit_rows(lo["nodes"], a, lo["offset"], n_dof, point)
        rb, _ = fit_rows(hi["nodes"], b_, hi["offset"], n_dof, point)
        link = ra - rb
        penalty = penalty + link.T @ weights @ link
        bolts += 1
    k = (k + penalty).tocsr()
    say(f"couplings: {len(mounts)} mounts held, {bolts} bolts joining the halves")

    t2 = time.time()
    # One case at a time: the copied refinement resets the right-hand side column by column, and
    # cuDSS keeps the shape it was planned with.
    columns = []
    for j in range(f.shape[1]):
        x, solve_info = _factor_and_solve(k, f[:, j], gpu=True)
        columns.append(x)
        release()
    u_all = np.stack(columns, axis=1)
    say(
        f"solved in {time.time() - t2:.0f} s ({solve_info.get('solver')}, residual {solve_info.get('residual'):.1e})"
    )

    result = {"stem": stem, "size_mm": size, "unknowns": n_dof, "cases": {}}
    for j, case in enumerate(cases):
        u = u_all[:, j]
        out = {"seats": {}, "reactions": {}, "shafts": {}}
        for (shaft, side), (half, ids, b) in seats.items():
            hh = halves[half]
            uu = u[hh["offset"] : hh["offset"] + 3 * len(hh["nodes"])].reshape(-1, 3)
            mean, theta, c = rigid_fit(hh["nodes"], uu, ids)
            out["seats"][f"{shaft} {side}"] = {
                "displacement_mm": float(np.linalg.norm(mean)),
                "radial_mm": float(np.hypot(mean[0], mean[1])),
                "tilt_mrad": float(1000 * np.hypot(theta[0], theta[1])),
                "u": mean.tolist(),
                "theta": theta.tolist(),
                "nodes": int(len(ids)),
            }
        for shaft in ("input", "intermediate", "output"):
            a_, b_ = out["seats"][f"{shaft} -z"], out["seats"][f"{shaft} +z"]
            za = next(
                bb["z"] for bb in info["bearings"] if bb["shaft"] == shaft and bb["side"] == "-z"
            )
            zb = next(
                bb["z"] for bb in info["bearings"] if bb["shaft"] == shaft and bb["side"] == "+z"
            )
            span = 0.5 * (zb[0] + zb[1]) - 0.5 * (za[0] + za[1])
            du = np.array(b_["u"]) - np.array(a_["u"])
            out["shafts"][shaft] = {
                "tilt_mrad": float(1000 * math.hypot(du[0], du[1]) / span),
                "span_mm": span,
            }
        # The mounts' reactions: the penalty forces on each hole's mean motion and rotation, as a
        # force and a moment about the origin; with the loads they must balance.
        force = np.zeros(3)
        moment = np.zeros(3)
        for rows, c, _n in mounts:
            r6 = -(weights @ (rows @ u))
            force += r6[:3]
            moment += r6[3:] + np.cross(c, r6[:3])
        applied_f = np.array([f[0::3, j].sum(), f[1::3, j].sum(), f[2::3, j].sum()])
        applied_m = np.zeros(3)
        for h in halves.values():
            n_h = len(h["nodes"])
            fh = f[h["offset"] : h["offset"] + 3 * n_h, j].reshape(-1, 3)
            applied_m += np.cross(h["nodes"], fh).sum(axis=0)
        out["reactions"] = {
            "force_N": force.tolist(),
            "moment_Nmm": moment.tolist(),
            "applied_force_N": applied_f.tolist(),
            "applied_moment_Nmm": applied_m.tolist(),
        }
        out["largest_mm"] = float(np.abs(u).reshape(-1, 3).max())
        result["cases"][case.name] = out
    volume = 0.0
    for h in halves.values():
        x = h["nodes"][h["tets"][:, :4]]
        volume += float(
            np.abs(
                np.einsum(
                    "ij,ij->i", np.cross(x[:, 1] - x[:, 0], x[:, 2] - x[:, 0]), x[:, 3] - x[:, 0]
                )
            ).sum()
            / 6
        )
    result["mass_kg"] = volume * DENSITY * 1000.0
    t3 = time.time()
    result["modes_hz"] = modes(halves, k, n_dof)
    say(
        f"modes in {time.time() - t3:.0f} s: {', '.join(f'{v:.0f}' for v in result['modes_hz'])} Hz"
    )
    # Against the gear orders at the rated speed (the contract: at least 3 % apart).
    speeds = chain.speeds
    meshes = []
    for s in spec.requirement.stages:
        rpm = speeds[s.pinion_shaft]
        meshes.append((s.name, int(s.z_pinion.value) * rpm / 60.0))
    result["mesh_hz"] = {name: hz for name, hz in meshes}
    near = []
    for v in result["modes_hz"]:
        for name, hz in meshes:
            if abs(v - hz) / hz < 0.03:
                near.append(f"{v:.0f} Hz within 3 % of {name}'s {hz:.0f} Hz")
    result["order_clashes"] = near
    say(
        f"mesh frequencies {', '.join(f'{n} {hz:.0f} Hz' for n, hz in meshes)}; clashes: {near or 'none'}"
    )
    result["solve"] = {
        k_: (v if isinstance(v, (int, float, str)) else str(v)) for k_, v in solve_info.items()
    }
    result["seconds"] = time.time() - t0
    (OUT / f"fe_{stem}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    np.savez_compressed(
        OUT / f"fe_{stem}.npz",
        **{f"{half}_nodes": h["nodes"] for half, h in halves.items()},
        **{f"{half}_tets": h["tets"] for half, h in halves.items()},
        **{f"{half}_offset": np.array(h["offset"]) for half, h in halves.items()},
        u=u_all,
    )
    for name, out in result["cases"].items():
        worst = max(out["seats"].items(), key=lambda kv: kv[1]["displacement_mm"])
        tilt = max(out["seats"].items(), key=lambda kv: kv[1]["tilt_mrad"])
        rm = np.array(out["reactions"]["moment_Nmm"]) / 1000
        am = np.array(out["reactions"]["applied_moment_Nmm"]) / 1000
        say(
            f"{name}: worst seat {worst[0]} {worst[1]['displacement_mm'] * 1000:.1f} um; worst tilt "
            f"{tilt[0]} {tilt[1]['tilt_mrad']:.3f} mrad; mounts' moment {np.round(rm, 1)} N·m "
            f"against the loads' {np.round(am, 1)} N·m"
        )
    say(f"mass from the mesh {result['mass_kg']:.2f} kg; {result['seconds']:.0f} s in all")
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    judge(args[0] if args else "shell", float(args[1]) if len(args) > 1 else 6.0)
