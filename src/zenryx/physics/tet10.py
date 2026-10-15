"""TET10 elements: the quadratic mesh from TET4 and its stiffness (LOP-33).

Origin: fastcae-v1, through `prototypes/first_loop/fastcae_fe.py`, unchanged but for what the final
workflow does not call:
- fastcae-v1:src/fastcae/simulate/fem.py: EDGES, quadratic;
- fastcae-v1:src/fastcae/simulate/solve.py: QA, QB, QUAD, ON_HOST_DOF, _gradients, _shape_gradients,
  _elasticity, _b_matrix, stiffness, _mtlayer (here `mtlayer`), NODE_L, and of nodal_stress and
  von_mises the von Mises alone (here `nodal_von_mises`, for the Designs page's contours);
- fastcae-v1:src/fastcae/simulate/gpu.py: release, without its Warp branch (nothing here uses Warp).
Parity: `prototypes/first_loop/housing_parity.py fe` (the judgement against the prototype's).
"""

from __future__ import annotations

import gc
import sys
from pathlib import Path

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
    xyz = xp.asarray(nodes)
    total = None
    for start in range(0, len(tets), chunk):
        t = xp.asarray(tets[start : start + chunk])
        g, volume = _gradients(xp, xyz[t[:, :4]])
        gn = _shape_gradients(xp, g, QUAD)
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


NODE_L = np.vstack([np.eye(4), 0.5 * (np.eye(4)[EDGES[:, 0]] + np.eye(4)[EDGES[:, 1]])])


def nodal_von_mises(
    nodes: np.ndarray,
    tets: np.ndarray,
    young: float,
    poisson: float,
    u: np.ndarray,
    chunk: int = 50_000,
) -> np.ndarray:
    """Von Mises at every node, averaged from each element's own value there (fastcae-v1's
    `nodal_stress`, its von Mises alone, the material one throughout)."""
    n_nodes = len(nodes)
    vm_total = np.zeros(n_nodes)
    count = np.zeros(n_nodes)
    lam = young * poisson / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    for start in range(0, len(tets), chunk):
        t = tets[start : start + chunk]
        g, _ = _gradients(np, nodes[t[:, :4]])
        gn = _shape_gradients(np, g, NODE_L)  # (m, 10 points, 10 nodes, 3)
        grad = np.einsum("mpnj,mni->mpij", gn, u[t])
        eps = 0.5 * (grad + grad.transpose(0, 1, 3, 2))
        tr = eps[..., 0, 0] + eps[..., 1, 1] + eps[..., 2, 2]
        xx, yy, zz = (2 * mu * eps[..., i, i] + lam * tr for i in range(3))
        xy, xz, yz = 2 * mu * eps[..., 0, 1], 2 * mu * eps[..., 0, 2], 2 * mu * eps[..., 1, 2]
        vm = np.sqrt(
            0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3.0 * (xy**2 + yz**2 + xz**2)
        )
        np.add.at(vm_total, t.ravel(), vm.ravel())
        np.add.at(count, t.ravel(), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return vm_total / count


def mtlayer() -> str | None:
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


def release() -> None:
    """Every block freed on the card, handed back to it: CuPy's pools emptied, the device's own pool
    trimmed, and dead arrays collected first."""
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
