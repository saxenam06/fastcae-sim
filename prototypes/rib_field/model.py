"""The rib-direction field's toy model (LOP-34; a prototype: nothing in `src/` imports it).

A flat wall of hexahedra with a band of cubes above it, in which the ribs stand. A rib cube's
stiffness is that of thin plates standing along the pull (z) and running along a direction theta in
plan, at a share rho of the cube: a laminate of metal and air, so the plane-stress stiffness in the
plates' own plane (along theta and along z) and nothing across them. It is scaled by the share of the
cube's height the ribs reach. Every cube's element matrix is a sum of 36 basis matrices, one per pair
of Voigt components (`hex_basis`), so a cube of any stiffness costs one product.

Voigt order (xx, yy, zz, yz, xz, xy), shear strains as engineering strains.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

# a hexahedron's corners in its own coordinates, the order its nodes are numbered in
CORNERS = np.array(
    [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]],
    float,
)
ERSATZ = 1e-6  # the stiffness of air, as a share of the metal's


def hex_strain(a: float) -> tuple[np.ndarray, float]:
    """For a cube of edge `a`: the strain-displacement matrices at the 2 x 2 x 2 Gauss points (8, 6,
    24) and each point's weight times the Jacobian."""
    g = 1.0 / np.sqrt(3.0)
    pts = CORNERS * g
    bg = np.zeros((8, 6, 24))
    for p, (xi, eta, zeta) in enumerate(pts):
        dn = np.stack(
            [
                CORNERS[:, 0] * (1 + CORNERS[:, 1] * eta) * (1 + CORNERS[:, 2] * zeta),
                CORNERS[:, 1] * (1 + CORNERS[:, 0] * xi) * (1 + CORNERS[:, 2] * zeta),
                CORNERS[:, 2] * (1 + CORNERS[:, 0] * xi) * (1 + CORNERS[:, 1] * eta),
            ],
            axis=1,
        ) / 8.0 * (2.0 / a)  # (8 nodes, 3): dN/dx
        gx, gy, gz = dn[:, 0], dn[:, 1], dn[:, 2]
        b = bg[p]
        b[0, 0::3], b[1, 1::3], b[2, 2::3] = gx, gy, gz
        b[3, 1::3], b[3, 2::3] = gz, gy
        b[4, 0::3], b[4, 2::3] = gz, gx
        b[5, 0::3], b[5, 1::3] = gy, gx
    return bg, (a / 2.0) ** 3


def hex_basis(a: float) -> np.ndarray:
    """(36, 576): row 6 p + q is the element matrix of a cube whose stiffness is 1 at (p, q) alone,
    so K_e = C_e.ravel() @ basis."""
    bg, w = hex_strain(a)
    kb = np.einsum("gpa,gqb->pqab", bg, bg) * w
    return kb.reshape(36, 576)


def isotropic(e: float, nu: float) -> np.ndarray:
    lam, mu = e * nu / ((1 + nu) * (1 - 2 * nu)), e / (2 * (1 + nu))
    c = np.zeros((6, 6))
    c[:3, :3] = lam
    c[[0, 1, 2], [0, 1, 2]] += 2 * mu
    c[[3, 4, 5], [3, 4, 5]] = mu
    return c


def rib_local(e: float, nu: float) -> np.ndarray:
    """A plate lying in the plane of its own x (along the rib) and z (along the pull): plane stress
    in that plane, nothing across it (its local y)."""
    q = e / (1 - nu * nu)
    c = np.zeros((6, 6))
    c[0, 0] = c[2, 2] = q
    c[0, 2] = c[2, 0] = nu * q
    c[4, 4] = e / (2 * (1 + nu))  # the xz shear: in the plate's plane
    return c


def strain_rotation(theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n, 6, 6): the rib's local strains from the global ones, its axes t = (c, s, 0) along the rib,
    n = (-s, c, 0) across it and z; and its derivative by theta."""
    c, s = np.cos(theta), np.sin(theta)
    t = np.zeros((len(theta), 6, 6))
    d = np.zeros_like(t)
    # local tt
    t[:, 0, 0], t[:, 0, 1], t[:, 0, 5] = c * c, s * s, c * s
    d[:, 0, 0], d[:, 0, 1], d[:, 0, 5] = -2 * c * s, 2 * c * s, c * c - s * s
    # local nn
    t[:, 1, 0], t[:, 1, 1], t[:, 1, 5] = s * s, c * c, -c * s
    d[:, 1, 0], d[:, 1, 1], d[:, 1, 5] = 2 * c * s, -2 * c * s, -(c * c - s * s)
    # local zz
    t[:, 2, 2] = 1.0
    # local nz (yz): n . (gyz, gxz)
    t[:, 3, 3], t[:, 3, 4] = c, -s
    d[:, 3, 3], d[:, 3, 4] = -s, -c
    # local tz (xz)
    t[:, 4, 3], t[:, 4, 4] = s, c
    d[:, 4, 3], d[:, 4, 4] = c, -s
    # local tn (xy)
    t[:, 5, 0], t[:, 5, 1], t[:, 5, 5] = -2 * c * s, 2 * c * s, c * c - s * s
    d[:, 5, 0], d[:, 5, 1], d[:, 5, 5] = -2 * (c * c - s * s), 2 * (c * c - s * s), -4 * c * s
    return t, d


def rib_tensor(theta: np.ndarray, local: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(n, 6, 6): the rib's stiffness in global axes, T' C T, and its derivative by theta."""
    t, d = strain_rotation(np.asarray(theta, float))
    c = np.einsum("nqp,qr,nrs->nps", t, local, t)
    dc = np.einsum("nqp,qr,nrs->nps", d, local, t)
    return c, dc + dc.transpose(0, 2, 1)


class Grid:
    """A box of cubes: `nx` x `ny` in plan, `nz` high, of edge `a`; element e = i + nx (j + ny k),
    node n = i + (nx + 1) (j + (ny + 1) k)."""

    def __init__(self, nx: int, ny: int, nz: int, a: float):
        self.nx, self.ny, self.nz, self.a = nx, ny, nz, a
        i, j, k = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
        i, j, k = (v.transpose(2, 1, 0).ravel() for v in (i, j, k))
        self.i, self.j, self.k = i, j, k
        ox = ((CORNERS[:, 0] + 1) / 2).astype(int)
        oy = ((CORNERS[:, 1] + 1) / 2).astype(int)
        oz = ((CORNERS[:, 2] + 1) / 2).astype(int)
        self.nodes_of = (
            (i[:, None] + ox) + (nx + 1) * ((j[:, None] + oy) + (ny + 1) * (k[:, None] + oz))
        )
        n = (nx + 1) * (ny + 1) * (nz + 1)
        ni, nj, nk = np.meshgrid(np.arange(nx + 1), np.arange(ny + 1), np.arange(nz + 1), indexing="ij")
        self.xyz = (
            np.stack([v.transpose(2, 1, 0).ravel() for v in (ni, nj, nk)], axis=1).astype(float) * a
        )
        assert len(self.xyz) == n
        self.centre = np.stack([(i + 0.5) * a, (j + 0.5) * a, (k + 0.5) * a], axis=1)


class Assembler:
    """The global stiffness of a set of a grid's elements, each with its own 6 x 6 stiffness."""

    def __init__(self, grid: Grid, elements: np.ndarray):
        self.grid, self.elements = grid, np.asarray(elements)
        self.basis = hex_basis(grid.a)
        self.bg, self.w = hex_strain(grid.a)
        nodes = grid.nodes_of[self.elements]
        self.dof = (3 * nodes[:, :, None] + np.arange(3)).reshape(len(self.elements), 24)
        self.n = 3 * len(grid.xyz)
        self.rows = np.repeat(self.dof, 24, axis=1).ravel()
        self.cols = np.tile(self.dof, (1, 24)).ravel()

    def stiffness(self, c: np.ndarray) -> sp.csr_matrix:
        ke = c.reshape(len(c), 36) @ self.basis
        return sp.coo_matrix((ke.ravel(), (self.rows, self.cols)), shape=(self.n, self.n)).tocsr()

    def energy(self, u: np.ndarray) -> np.ndarray:
        """(n elements, 6, 6): u_e' K^(pq) u_e summed over the columns of u (the load cases): the
        derivative of the compliance by each element's stiffness is minus this."""
        if u.ndim == 1:
            u = u[:, None]
        s = np.zeros((len(self.elements), 6, 6))
        for c in range(u.shape[1]):
            ue = u[self.dof, c]  # (n, 24)
            eps = np.einsum("gpa,ea->egp", self.bg, ue)
            s += np.einsum("egp,egq->epq", eps, eps) * self.w
        return s
