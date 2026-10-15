"""PROTOTYPE support (LOP-2): fastcae's TET10 stiffness and its cuDSS solve, copied verbatim.

Copied from fastcae's tag, function by function, unchanged:
- fastcae-v1:src/fastcae/simulate/fem.py: EDGES, quadratic;
- fastcae-v1:src/fastcae/simulate/solve.py: QA, QB, QUAD, ON_HOST_DOF, _gradients,
  _shape_gradients, _elasticity, _b_matrix, stiffness, _mtlayer, SINGLE, REFINE_TOL,
  REFINE_MOST, _factor_and_solve, FACTORS, _direct, _refined;
- fastcae-v1:src/fastcae/simulate/gpu.py: release;
- fastcae-v1:src/fastcae/simulate/solve.py (11 October, for the Designs page's stress contours): NODE_L,
  nodal_stress, von_mises.
The one change: _direct imported `release` from `.gpu`; here it is the function below, in the same
module (the import line removed). PHY-1 copies them into src/zenryx/physics/ with a parity check on
a reference mesh; until then the first loop's prototype runs these.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp

EDGES = np.array([[0, 1], [1, 2], [2, 0], [0, 3], [1, 3], [2, 3]])


def quadratic(nodes: np.ndarray, tets: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """TET10 from TET4: a node at the middle of every edge, shared by the tets round it - straight
    edges."""
    edges = np.sort(tets[:, EDGES].reshape(-1, 2), axis=1)
    unique, inverse = np.unique(edges, axis=0, return_inverse=True)
    middle = 0.5 * (nodes[unique[:, 0]] + nodes[unique[:, 1]])
    return np.vstack([nodes, middle]), np.hstack([tets, len(nodes) + inverse.reshape(-1, 6)])


QA, QB = 0.5854101966249685, 0.1381966011250105


QUAD = np.array([[QA, QB, QB, QB], [QB, QA, QB, QB], [QB, QB, QA, QB], [QB, QB, QB, QA]])


ON_HOST_DOF = 1_600_000


def _gradients(xp, x):  # type: ignore[no-untyped-def]
    """∇L0..∇L3 of each tetrahedron (m, 4, 3), and its volume."""
    jac = xp.stack([x[:, 1] - x[:, 0], x[:, 2] - x[:, 0], x[:, 3] - x[:, 0]], axis=2)
    inv = xp.linalg.inv(jac)
    g = xp.empty((len(x), 4, 3))
    g[:, 1:] = inv
    g[:, 0] = -inv.sum(axis=1)
    return g, xp.abs(xp.linalg.det(jac)) / 6.0


def _shape_gradients(xp, g, lam):  # type: ignore[no-untyped-def]
    """∇N of the ten nodes at points of barycentric coordinates ``lam`` (p, 4): (m, p, 10, 3)."""
    lam = xp.asarray(lam)
    gn = xp.empty((g.shape[0], lam.shape[0], 10, 3))
    gn[:, :, :4] = (4.0 * lam[None, :, :, None] - 1.0) * g[:, None, :, :]
    for k, (a, b) in enumerate(EDGES):
        gn[:, :, 4 + k] = 4.0 * (
            lam[None, :, b, None] * g[:, None, a] + lam[None, :, a, None] * g[:, None, b]
        )
    return gn


def _elasticity(xp, young, poisson):  # type: ignore[no-untyped-def]
    """The 6x6 isotropic elasticity matrix per element (m, 6, 6), engineering shears xy yz zx."""
    young, poisson = xp.asarray(young), xp.asarray(poisson)
    lam = young * poisson / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    d = xp.zeros((len(young), 6, 6))
    d[:, :3, :3] = lam[:, None, None]
    for i in range(3):
        d[:, i, i] += 2 * mu
        d[:, 3 + i, 3 + i] = mu
    return d


def _b_matrix(xp, gn):  # type: ignore[no-untyped-def]
    """B (m, p, 6, 30) from shape gradients: xx yy zz, then xy yz zx."""
    m, p = gn.shape[:2]
    bm = xp.zeros((m, p, 6, 30))
    gx, gy, gz = gn[..., 0], gn[..., 1], gn[..., 2]
    bm[:, :, 0, 0::3] = gx
    bm[:, :, 1, 1::3] = gy
    bm[:, :, 2, 2::3] = gz
    bm[:, :, 3, 0::3], bm[:, :, 3, 1::3] = gy, gx
    bm[:, :, 4, 1::3], bm[:, :, 4, 2::3] = gz, gy
    bm[:, :, 5, 0::3], bm[:, :, 5, 2::3] = gz, gx
    return bm


def stiffness(
    nodes: np.ndarray,
    tets: np.ndarray,
    young: np.ndarray,
    poisson: np.ndarray,
    gpu: bool = True,
    chunk: int = 20_000,
) -> sp.csr_matrix:
    """The global stiffness over every node's three translations, element matrices B'DB computed a
    chunk at a time - on the GPU when there is one - and summed into one CSR."""
    if gpu:
        import cupy as xp
        import cupyx.scipy.sparse as xsp
    else:
        xp, xsp = np, sp
    n = 3 * len(nodes)
    on_host = not gpu or n > ON_HOST_DOF
    quad = QUAD
    xyz = xp.asarray(nodes)
    total = None
    for start in range(0, len(tets), chunk):
        t = xp.asarray(tets[start : start + chunk])
        g, volume = _gradients(xp, xyz[t[:, :4]])
        gn = _shape_gradients(xp, g, quad)
        bm = _b_matrix(xp, gn)
        d = _elasticity(xp, young[start : start + chunk], poisson[start : start + chunk])
        m = len(t)
        db = xp.einsum("mij,mqjk->mqik", d, bm)
        ke = xp.einsum("mqji,mqjk->mik", bm, db) * (volume / 4.0)[:, None, None]
        dof = (3 * t[:, :, None] + xp.arange(3)[None, None, :]).reshape(m, 30)
        rows = xp.repeat(dof, 30, axis=1).ravel()
        cols = xp.tile(dof, (1, 30)).ravel()
        block = xsp.coo_matrix((ke.ravel(), (rows, cols)), shape=(n, n)).tocsr()
        if gpu and on_host:
            block = block.get()
            xp.get_default_memory_pool().free_all_blocks()
        total = block if total is None else total + block
        del ke, bm, gn, db, block
    if gpu and not on_host:
        total = total.get()  # type: ignore[union-attr]
    if gpu:
        # CuPy keeps freed blocks for reuse; cuDSS allocates outside that pool and needs them back.
        xp.get_default_memory_pool().free_all_blocks()
    return total  # type: ignore[return-value]


def _mtlayer() -> str | None:
    """cuDSS's threading layer, shipped beside it: without it, its reordering runs on one core."""
    try:
        import nvidia
    except ImportError:
        return None
    for base in nvidia.__path__:
        for pattern in ("cudss_mtlayer*.dll", "libcudss_mtlayer_gomp.so*"):
            for found in Path(base).rglob(pattern):
                return str(found)
    return None


SINGLE = True
"""Factor the stiffness in single precision and bring the answer to double's by conjugate gradients
in double, the single factor as their preconditioner: the factor takes half the card's memory. In
double the target's mesh (1.63 M unknowns) was at the edge of what the card factors, and heavier
designs pass it."""


REFINE_TOL = 1.0e-10
"""The relative residual the refined answer reaches, as the double factor's answer does."""


REFINE_MOST = 60
"""The most refining steps; a stiffness the single factor cannot precondition this well fails."""


def _factor_and_solve(
    k: sp.csr_matrix,
    f: np.ndarray,
    gpu: bool,
    device_limit: str | None = None,
    single: bool | None = None,
) -> tuple[np.ndarray, dict]:
    """``k x = f`` - ``f`` one right-hand side or several, as columns. ``device_limit`` caps the
    card memory cuDSS may use (\"3GiB\"): what does not fit is kept in host memory. ``single``
    (default :data:`SINGLE`) factors in single precision and refines the answer to double.

    A single-precision Cholesky can meet a pivot its rounding has made non-positive and break down,
    where the stiffness itself is sound: its answer is then not a number. The factor is then made
    again as LDL^T with pivoting in single precision, refined the same way, and last as Cholesky in
    double (:data:`FACTORS`). Every answer is the true stiffness's: a single factor only
    preconditions the refinement."""
    if not gpu:
        from scipy.sparse.linalg import spsolve

        x = spsolve(k.tocsc(), f)
        return x, {
            "solver": "scipy",
            "residual": float(np.linalg.norm(k @ x - f) / max(np.linalg.norm(f), 1e-300)),
        }
    single = SINGLE if single is None else single
    rhs = f if f.ndim == 2 else f.reshape(-1, 1)
    tried = []
    for precision, kind in FACTORS if single else FACTORS[-1:]:
        x, info = _direct(k, rhs, precision, kind, device_limit)
        tried.append(info["solver"])
        if np.all(np.isfinite(x)):
            break
    x = x.reshape(f.shape)
    residual = float(np.linalg.norm(k @ x - f) / max(np.linalg.norm(f), 1e-300))
    # an answer that is not a number reads past every tolerance - NaN is greater than nothing - so
    # it is named here, before anything is read from it
    if not np.isfinite(residual):
        raise RuntimeError(
            "the solve's answer is not a number: every factor broke down ("
            + ", ".join(tried)
            + ") - the stiffness is singular"
        )
    if info["refined"] and residual > 100 * REFINE_TOL:
        raise RuntimeError(
            f"the single-precision factor did not refine to double: residual {residual:.1e} after "
            f"{info['refine_steps']} steps"
        )
    return x, {**info, "residual": residual, "factors_tried": tried}


FACTORS = (("single", "SPD"), ("single", "SYMMETRIC"), ("double", "SPD"))
"""The factors tried in turn while the one before gives no answer: Cholesky in single precision,
LDL^T with pivoting in single precision - both refined to double - and Cholesky in double."""


def _direct(
    k: sp.csr_matrix, rhs: np.ndarray, precision: str, kind: str, device_limit: str | None
) -> tuple[np.ndarray, dict]:
    """``k x = rhs`` by cuDSS, the stiffness factored as ``kind`` (a cuDSS matrix type: ``SPD``,
    Cholesky; ``SYMMETRIC``, LDL^T with pivoting) in ``precision``; a single factor's answer
    refined to double by conjugate gradients (:func:`_refined`) where it is a number at all."""
    import cupy as cp
    import cupyx.scipy.sparse as csp
    from nvmath.sparse.advanced import (
        DirectSolver,
        DirectSolverMatrixType,
        ExecutionCUDA,
        HybridMemoryModeOptions,
    )

    single = precision == "single"
    dtype = np.float32 if single else np.float64
    release()
    a = csp.csr_matrix(k.astype(dtype))
    # Right-hand sides column by column in memory, as cuDSS reads them.
    b = cp.asfortranarray(cp.asarray(rhs, dtype=dtype))
    options = {
        "sparse_system_type": getattr(DirectSolverMatrixType, kind),
        "multithreading_lib": _mtlayer(),
    }
    hybrid = {"hybrid_memory_mode": True}
    if device_limit:
        hybrid["hybrid_device_memory_limit"] = device_limit
    execution = ExecutionCUDA(hybrid_memory_mode_options=HybridMemoryModeOptions(**hybrid))
    steps = 0
    try:
        with DirectSolver(a, b, options=options, execution=execution) as solver:
            t0 = time.time()
            solver.plan()
            cp.cuda.Device().synchronize()
            plan = time.time() - t0
            t0 = time.time()
            solver.factorize()
            cp.cuda.Device().synchronize()
            factor = time.time() - t0
            t0 = time.time()
            x = cp.asnumpy(solver.solve()).astype(np.float64).reshape(rhs.shape)
            if single and np.all(np.isfinite(x)):

                def factored(r: np.ndarray) -> np.ndarray:
                    solver.reset_operands(b=cp.asfortranarray(cp.asarray(r, dtype=dtype)))
                    return cp.asnumpy(solver.solve()).astype(np.float64).reshape(r.shape)

                x, steps = _refined(k, rhs, x, factored)
            cp.cuda.Device().synchronize()
            solve_s = time.time() - t0
    finally:
        # Whether it solved or ran out: the card handed back, for the next build or solve.
        a = b = None
        release()
    names = {"SPD": "", "SYMMETRIC": " LDLT"}
    return x, {
        "solver": ("cuDSS single" + names[kind] + ", refined") if single else "cuDSS" + names[kind],
        "plan_s": plan,
        "factor_s": factor,
        "backsolve_s": solve_s,
        "refine_steps": steps,
        "refined": single,
    }


def _refined(
    k: sp.csr_matrix, f: np.ndarray, x0: np.ndarray, factored: Any
) -> tuple[np.ndarray, int]:
    """Conjugate gradients in double for ``k x = f``, column by column, from ``x0``, the single
    factor (``factored``, r -> its solve) as the preconditioner, to :data:`REFINE_TOL`. Returns
    the answer and the most steps any column took."""
    x = np.array(x0, float, copy=True)
    most = 0
    for j in range(f.shape[1]):
        b = f[:, j]
        xj = x[:, j]
        r = b - k @ xj
        tol = REFINE_TOL * max(float(np.linalg.norm(b)), 1e-300)
        steps = 0
        if float(np.linalg.norm(r)) > tol:
            z = factored(r[:, None])[:, 0]
            p = z.copy()
            rz = float(r @ z)
            while steps < REFINE_MOST:
                kp = k @ p
                alpha = rz / float(p @ kp)
                xj = xj + alpha * p
                r = r - alpha * kp
                steps += 1
                if float(np.linalg.norm(r)) <= tol:
                    break
                z = factored(r[:, None])[:, 0]
                rz_new = float(r @ z)
                p = z + (rz_new / rz) * p
                rz = rz_new
        x[:, j] = xj
        most = max(most, steps)
    return x, most


def release() -> None:
    """Every block freed on the card, handed back to it: CuPy's pools emptied, the device's own
    pool trimmed, Warp's pool told to keep nothing and synchronised so it lets go, and dead arrays
    collected first."""
    gc.collect()
    if "cupy" in sys.modules:
        import cupy as cp

        cp.get_default_memory_pool().free_all_blocks()
        cp.get_default_pinned_memory_pool().free_all_blocks()
        runtime = cp.cuda.runtime
        try:
            for device in range(runtime.getDeviceCount()):
                with cp.cuda.Device(device):
                    cp.cuda.Device(device).synchronize()
                    runtime.memPoolTrimTo(runtime.deviceGetDefaultMemPool(device), 0)
        except runtime.CUDARuntimeError:
            pass  # no card, or one without stream-ordered pools: nothing is kept there
    if "warp" in sys.modules:
        import warp as wp

        if wp.is_cuda_available():
            for device in wp.get_cuda_devices():
                if wp.is_mempool_enabled(device):
                    # Past this many bytes kept, the pool gives memory back at a synchronize.
                    wp.set_mempool_release_threshold(device, 0)
                wp.synchronize_device(device)


# --- copied 11 October (fastcae-v1:src/fastcae/simulate/solve.py), unchanged ---

NODE_L = np.vstack([np.eye(4), 0.5 * (np.eye(4)[EDGES[:, 0]] + np.eye(4)[EDGES[:, 1]])])


def nodal_stress(
    nodes: np.ndarray,
    tets: np.ndarray,
    young: np.ndarray,
    poisson: np.ndarray,
    u: np.ndarray,
    n_nodes: int,
    chunk: int = 50_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Stress at every node (SIXX SIYY SIZZ SIXY SIXZ SIYZ) averaged over the elements round it, and
    von Mises likewise averaged from each element's own value there."""
    total = np.zeros((n_nodes, 6))
    vm_total = np.zeros(n_nodes)
    count = np.zeros(n_nodes)
    for start in range(0, len(tets), chunk):
        t = tets[start : start + chunk]
        g, _ = _gradients(np, nodes[t[:, :4]])
        gn = _shape_gradients(np, g, NODE_L)  # (m, 10 points, 10 nodes, 3)
        ue = u[t]  # (m, 10, 3)
        grad = np.einsum("mpnj,mni->mpij", gn, ue)
        eps = 0.5 * (grad + grad.transpose(0, 1, 3, 2))
        e, nu = young[start : start + chunk, None], poisson[start : start + chunk, None]
        lam = e * nu / ((1 + nu) * (1 - 2 * nu))
        mu = e / (2 * (1 + nu))
        tr = eps[..., 0, 0] + eps[..., 1, 1] + eps[..., 2, 2]
        s = np.empty(eps.shape[:2] + (6,))
        for i in range(3):
            s[..., i] = 2 * mu * eps[..., i, i] + lam * tr
        s[..., 3] = 2 * mu * eps[..., 0, 1]
        s[..., 4] = 2 * mu * eps[..., 0, 2]
        s[..., 5] = 2 * mu * eps[..., 1, 2]
        vm = von_mises(s)
        np.add.at(total, t.ravel(), s.reshape(-1, 6))
        np.add.at(vm_total, t.ravel(), vm.ravel())
        np.add.at(count, t.ravel(), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return total / count[:, None], vm_total / count


def von_mises(s: np.ndarray) -> np.ndarray:
    """Von Mises of stresses given as (..., 6): xx yy zz xy xz yz."""
    xx, yy, zz, xy, xz, yz = (s[..., i] for i in range(6))
    return np.sqrt(
        0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3.0 * (xy**2 + yz**2 + xz**2)
    )
