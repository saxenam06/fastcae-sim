"""The housing's model with rib cubes (LOP-34; a prototype).

The product's voxel model (`housing.voxels.Voxels`) unchanged but for the free cubes: the fixed cubes
keep the product's element (Wilson's incompatible modes, isotropic), assembled once; every free cube
is a rib cube, its 6 x 6 stiffness given per step (the toy's laminate, `prototypes/rib_field/model.py`)
and its element matrix the sum of 36 basis matrices of the plain hexahedron in the product's corner
order. The halves, the rigid couplings (u = T q), the peak drive, every seat's tilt over its line and
every bed over its line are the product's (`vox.seats`, `vox.bed_rows`, `vox.lean_of`). Solved by
PARDISO in double precision on the CPU; the adjoints of every measure on the same factor.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rib_field"))

import model as toymodel  # noqa: E402

# the product's corner order (`voxels.Voxels`): i fastest, then j, then k
CORNERS = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)], float) * 2 - 1
ERSATZ = 1e-4  # a rib cube's floor of isotropic stiffness (its plates take nothing across)


def hex_strain(a: float) -> tuple[np.ndarray, float]:
    """The plain hexahedron's strain matrices at the 2 x 2 x 2 Gauss points (8, 6, 24), corners in the
    product's order, and each point's weight times the Jacobian."""
    g = 1.0 / math.sqrt(3.0)
    bg = np.zeros((8, 6, 24))
    for p, (xi, eta, zeta) in enumerate(CORNERS * g):
        dn = np.stack(
            [
                CORNERS[:, 0] * (1 + CORNERS[:, 1] * eta) * (1 + CORNERS[:, 2] * zeta),
                CORNERS[:, 1] * (1 + CORNERS[:, 0] * xi) * (1 + CORNERS[:, 2] * zeta),
                CORNERS[:, 2] * (1 + CORNERS[:, 0] * xi) * (1 + CORNERS[:, 1] * eta),
            ],
            axis=1,
        ) / 8.0 * (2.0 / a)
        gx, gy, gz = dn[:, 0], dn[:, 1], dn[:, 2]
        b = bg[p]
        b[0, 0::3], b[1, 1::3], b[2, 2::3] = gx, gy, gz
        b[3, 1::3], b[3, 2::3] = gz, gy
        b[4, 0::3], b[4, 2::3] = gz, gx
        b[5, 0::3], b[5, 1::3] = gy, gx
    return bg, (a / 2.0) ** 3


class RibModel:
    def __init__(self, vox, say=print):
        t0 = time.time()
        self.vox = vox
        m = vox.model
        self.a = a = float(m["h"])
        spec = m["spec"]
        from zenryx.domains.gearbox.forces import value_in

        mat = spec.manufacturing.material
        e, nu = value_in(mat.youngs_modulus, "MPa"), value_in(mat.poisson_ratio, "1")
        self.c_iso = toymodel.isotropic(e, nu)
        self.c_local = toymodel.rib_local(e, nu)
        self.bg, self.w = hex_strain(a)
        self.basis = np.einsum("gpa,gqb->pqab", self.bg, self.bg).reshape(36, 576) * self.w
        n_dof = vox.n_dof
        dof = vox.dof
        free = vox.free_e
        fixed = np.flatnonzero(vox.frozen)
        # the fixed cubes, the product's element, once
        rows = np.repeat(dof[fixed], 24, axis=1).ravel()
        cols = np.tile(dof[fixed], (1, 24)).ravel()
        vals = np.broadcast_to(vox.ke.ravel(), (len(fixed), 576)).ravel()
        k_fixed = sp.coo_matrix((vals, (rows, cols)), shape=(n_dof, n_dof)).tocsr()
        # the free cubes' pattern, once: each entry's place in the CSR data
        rows = np.repeat(dof[free], 24, axis=1).ravel().astype(np.int64)
        cols = np.tile(dof[free], (1, 24)).ravel().astype(np.int64)
        keys = rows * n_dof + cols
        uniq, self.scatter = np.unique(keys, return_inverse=True)
        r_u, c_u = uniq // n_dof, uniq % n_dof
        indptr = np.searchsorted(r_u, np.arange(n_dof + 1))
        self.k_free_pattern = (indptr, c_u.astype(np.int32), len(uniq))
        self.k_fixed = k_fixed
        self.n_dof = n_dof
        self.free = free
        self.dof_free = dof[free]
        self.T = vox.T.tocsr()
        self.TT = self.T.T.tocsr()
        self.rhs = vox.rhs
        self.solver = None
        say(f"the rib model: {len(fixed):,} fixed cubes (the product's element), {len(free):,} rib "
            f"cubes, {vox.n_q:,} unknowns ({time.time() - t0:.0f} s)")

    def stiffness(self, c_free: np.ndarray) -> sp.csr_matrix:
        ke = c_free.reshape(len(c_free), 36) @ self.basis
        indptr, indices, nnz = self.k_free_pattern
        data = np.bincount(self.scatter, weights=ke.ravel(), minlength=nnz)
        k = sp.csr_matrix((data, indices, indptr), shape=(self.n_dof, self.n_dof))
        return k + self.k_fixed

    def energy(self, q: np.ndarray) -> np.ndarray:
        """(rib cubes, 6, 6): u_e' K^(pq) u_e summed over the cases (the strains' energy tensor)."""
        u = np.asarray(self.T @ q)
        s = np.zeros((len(self.free), 6, 6))
        for c in range(u.shape[1]):
            eps = np.einsum("gpa,ea->egp", self.bg, u[self.dof_free, c])
            s += np.einsum("egp,egq->epq", eps, eps) * self.w
        return s

    def analyse(self, c_free: np.ndarray, adjoints: bool = True) -> dict:
        """Every case solved, every seat's tilt ratio and bed ratio (the product's measures), and,
        with `adjoints`, each measure's derivative by every rib cube's 6 x 6 stiffness (`d_ratio`,
        `d_bed`: (measures, rib cubes, 6, 6))."""
        import pypardiso

        t0 = time.time()
        vox = self.vox
        k = self.stiffness(c_free)
        kr = (self.TT @ k @ self.T).tocsr()
        kr = (0.5 * (kr + kr.T)).tocsr()
        t1 = time.time()
        solver = pypardiso.PyPardisoSolver()
        solver.set_matrix_type(11)  # real nonsymmetric LU: robust on the reduced matrix
        # factorised once and recorded, so the adjoints' solve reuses it (`solve` alone factorises
        # every call: it never records the matrix it factorised)
        solver.factorize(kr)
        q = np.asarray(solver.solve(kr, self.rhs)).reshape(vox.n_q, -1)
        t2 = time.time()
        ratios, rhs_t, beds, rhs_b = [], [], [], []
        for key, line, l1, l2 in vox.seats:
            for c in range(vox.n_cases):
                lx, ly = vox.lean_of[(key, c)]
                v1 = float((l1 @ q[:, c])[0]) - lx
                v2 = float((l2 @ q[:, c])[0]) - ly
                tilt = math.hypot(v1, v2)
                ratios.append(tilt / line)
                g = (v1 * l1.toarray().ravel() + v2 * l2.toarray().ravel()) / (max(tilt, 1e-30) * line)
                rhs_t.append((g, c))
        for key, c in vox.bed_keys:
            mv = vox.bed_rows[key]
            mb = np.asarray(mv @ q[:, c]).ravel()
            size = float(np.linalg.norm(mb))
            beds.append(size / vox.bed_line[c])
            rhs_b.append((np.asarray(mv.T @ mb).ravel() / (max(size, 1e-30) * vox.bed_line[c]), c))
        out = {"q": q, "ratios": np.array(ratios), "beds": np.array(beds),
               "compliance": float((self.rhs * q).sum()), "clock": {"assemble": t1 - t0, "solve": t2 - t1}}
        if adjoints:
            t3 = time.time()
            u = np.asarray(self.T @ q)
            ue = u[self.dof_free]  # (rib cubes, 24, cases)
            lam_rhs = np.column_stack([r for r, _ in rhs_t + rhs_b])
            lam = np.asarray(solver.solve(kr, lam_rhs)).reshape(vox.n_q, -1)
            lam_full = np.asarray(self.T @ lam)
            cases = [c for _, c in rhs_t + rhs_b]
            eps_u = [np.einsum("gpa,ea->egp", self.bg, ue[:, :, c]) for c in range(ue.shape[2])]
            d = np.empty((lam.shape[1], len(self.free), 6, 6))
            for i in range(lam.shape[1]):
                le = lam_full[self.dof_free, i]
                eps_l = np.einsum("gpa,ea->egp", self.bg, le)
                # d measure / d C_e = - lambda_e' K^(pq) u_e
                d[i] = -np.einsum("egp,egq->epq", eps_l, eps_u[cases[i]]) * self.w
            n_t = len(rhs_t)
            out["d_ratio"], out["d_bed"] = d[:n_t], d[n_t:]
            out["clock"]["adjoints"] = time.time() - t3
        solver.free_memory(everything=True)
        out["clock"]["total"] = time.time() - t0
        return out
