"""Rigid (kinematic) couplings, one rule for FE and the optimiser's model (moved whole from
`prototypes/first_loop/couplings.py`, LOP-29; LOP-33) (the engineer, 13 October 22:40-22:47:
"kinematic coupling in both FE and optimizer... in the mounts' holes... in the bearing bores, with
the loads applied at the centre... the same in both"):
- each bearing's seat: the seat's surface nodes move as one rigid body with a node at the bearing's
  centre, where its load is applied and its motion read;
- each bolt: both halves' hole surfaces move as one rigid body with a node at the bolt's point on
  the split, which ties the halves there and nowhere else;
- each mount: its hole's surface held rigidly, fixed.

The couplings are eliminated exactly (no penalty: a single-precision factor refines): u = T q, where
q holds every uncoupled node's three motions, then each free coupling's centre's six (three
translations, three rotations, radians); a coupled node's motion is its centre's, u_i = u_c + theta
x (x_i - x_c); a fixed set's nodes have none. The reduced stiffness is T' K T, the loads T' f plus
whatever acts on a centre directly.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def skew(r: np.ndarray) -> np.ndarray:
    """(n, 3, 3): each r's cross-product matrix, skew(r) v = r x v."""
    m = np.zeros((len(r), 3, 3))
    m[:, 0, 1], m[:, 0, 2] = -r[:, 2], r[:, 1]
    m[:, 1, 0], m[:, 1, 2] = r[:, 2], -r[:, 0]
    m[:, 2, 0], m[:, 2, 1] = -r[:, 1], r[:, 0]
    return m


def rigid_transform(xyz: np.ndarray, groups: list[dict]) -> tuple[sp.csr_matrix, dict]:
    """T (3 n_nodes, n_q) for rigid couplings: `groups` each {"nodes": node indices, "ref": (x, y,
    z) its centre, or "fixed": True, "name": ...}, on disjoint node sets. Returns T and {"n_q",
    "n_master", "ref_col": {group index: the first of its centre's six columns}, "masters": the
    uncoupled nodes}."""
    n_nodes = len(xyz)
    owner = np.full(n_nodes, -1)
    for g, grp in enumerate(groups):
        ids = np.asarray(grp["nodes"], dtype=np.int64)
        if len(ids) == 0:
            raise ValueError(f"the coupling {grp.get('name', g)!r} holds no node")
        clash = ids[owner[ids] >= 0]
        if len(clash):
            raise ValueError(
                f"the coupling {grp.get('name', g)!r} shares {len(clash)} nodes with "
                f"{groups[owner[clash[0]]].get('name')!r}"
            )
        owner[ids] = g
    masters = np.flatnonzero(owner < 0)
    n_master = 3 * len(masters)
    q_node = np.full(n_nodes, -1)
    q_node[masters] = np.arange(len(masters))
    rows = [(3 * masters[:, None] + np.arange(3)[None, :]).ravel()]
    cols = [(3 * q_node[masters][:, None] + np.arange(3)[None, :]).ravel()]
    vals = [np.ones(n_master)]
    ref_col, col = {}, n_master
    for g, grp in enumerate(groups):
        if grp.get("fixed"):
            continue
        ref_col[g] = col
        ids = np.asarray(grp["nodes"], dtype=np.int64)
        r = xyz[ids] - np.asarray(grp["ref"], float)[None, :]
        for k in range(3):  # the translation: u_i,k = u_c,k
            rows.append(3 * ids + k)
            cols.append(np.full(len(ids), col + k))
            vals.append(np.ones(len(ids)))
        rot = -skew(r)  # theta x r_i = -r_i x theta = -skew(r_i) theta
        for k in range(3):
            for m in range(3):
                v = rot[:, k, m]
                nz = v != 0.0
                rows.append(3 * ids[nz] + k)
                cols.append(np.full(int(nz.sum()), col + 3 + m))
                vals.append(v[nz])
        col += 6
    t = sp.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(3 * n_nodes, col),
    )
    return t, {"n_q": col, "n_master": n_master, "ref_col": ref_col, "masters": masters}


def check_rigid(t: sp.csr_matrix, xyz: np.ndarray, groups: list[dict], info: dict) -> float:
    """The largest departure from a rigid motion of any free coupling's nodes under random centre
    motions (should be ~1e-15 of the motion), and that a fixed set's nodes do not move: the
    transform's own check."""
    rng = np.random.default_rng(0)
    q = np.zeros(info["n_q"])
    q[: info["n_master"]] = rng.normal(size=info["n_master"])
    for c in info["ref_col"].values():
        q[c : c + 6] = rng.normal(size=6) * np.r_[1.0, 1.0, 1.0, 1e-3, 1e-3, 1e-3]
    u = (t @ q).reshape(-1, 3)
    worst = 0.0
    for g, grp in enumerate(groups):
        ids = np.asarray(grp["nodes"], dtype=np.int64)
        if grp.get("fixed"):
            worst = max(worst, float(np.abs(u[ids]).max()))
            continue
        c = info["ref_col"][g]
        uc, th = q[c : c + 3], q[c + 3 : c + 6]
        r = xyz[ids] - np.asarray(grp["ref"], float)[None, :]
        expect = uc[None, :] + np.cross(th[None, :], r)
        worst = max(worst, float(np.abs(u[ids] - expect).max()))
    return worst
