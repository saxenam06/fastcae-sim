"""The FE judgement of a drawn housing (moved from `prototypes/first_loop/fe.py`: `judge`,
`mesh_tetgen`, `tetrahedralize_guarded`, `tetgen_skipped`, `TetGenRefused`, `tet_shape`, `oriented`,
`skin_nodes`, `on_cylinder`, `rbe3_loads`, `rigid_fit`, `lumped_mass`; LOP-33). Only the final
workflow's path: the mesh route's halves, the engineer's rigid couplings, the bearings' loads spread
as RBE3 does, the modes with their shapes. The material is the contract's.

Each half's watertight surface is coarsened to triangles of about `SURFACE_EDGE` mm and filled by
TetGen's quality tets (TET4, then straight-sided TET10); each bearing's seat surface is rigid with
its bearing's centre, where its load acts; each bolt's two holes are one rigid body at its point on
the split (the halves joined there and nowhere else); each mount's hole is held. The couplings are
eliminated exactly (u = T q) and T' K T factored once in single precision (`physics.factor`), every
answer refined to double. Per load case: every seat's displacement and tilt (its nodes' best-fit
rigid motion), the shafts' tilts and the reactions; then the mass and the first modes against the
gear orders. Writes `fe_<design>.json`, `fe_<design>.npz` (the mesh and the displacements) and
`fe_<design>_modes.npz` (each mode's shape by node).
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from zenryx.contract.validate import load_and_validate
from zenryx.domains.gearbox.chain import complete_chain
from zenryx.domains.gearbox.forces import value_in
from zenryx.domains.gearbox.housing import mesh as mr
from zenryx.domains.gearbox.housing import say
from zenryx.host import kill_tree
from zenryx.physics import couplings as cpl
from zenryx.physics.factor import SingleFactor, modes
from zenryx.physics.tet10 import quadratic, release, stiffness

TOL = 0.25  # mm: how near a node must lie to a coupled surface
# mm: the FE surface's triangles. 9 mm until 11 October 08:45; since then 7 mm (LOP-23): a design of
# 4 mm ribs read 63.5 µm at its worst bed on 9 mm triangles, 51.3 on 7 and 50.1 on 6 (the decimation
# keeps the mass but flattens a thin rib's section).
SURFACE_EDGE = 7.0
LAST_SURFACE = 5.0  # mm: the asked surface's last rung (`mesh_tetgen`)
SIZE = 8.0  # mm: the largest tet is a regular one of edge 1.5 SIZE
KEEP_TRIES = 3  # coarsenings at one size, each keeping fine the places TetGen named (`mesh_tetgen`)
# a tet's shape (`tet_shape`: 1 regular, 0 flat) under which the single factor breaks down
# (CLAUDE.md)
FLAT_TET = 1e-6
COARSER = (
    9.0,
    11.0,
)  # mm: the surfaces tried, at the last of `QUALITY_LADDER`, when its tets still pass `MESHED_MOST`
TET_RATIO, TET_DIHEDRAL = (
    2.0,
    12.0,
)  # TetGen's quality: radius-edge ratio at most, dihedral angle at least (degrees)
QUALITY_LADDER = (
    (TET_RATIO, TET_DIHEDRAL),
    (3.0, 10.0),
    (4.0, 8.0),
)  # tried in turn while the tets pass `MESHED_MOST`
# unknowns a mesh may have: the 8 GB card's single factor holds about 2.18 M (CLAUDE.md), and the
# assembly's host memory set the same (2.04 M asked 12.5 GB of a 16 GB laptop). A larger card or
# host is given its own, measured there first, only on the engineer's word.
MESHED_MOST = 2_180_000
TETGEN_SECONDS = 240  # s: a TetGen call past this is taken as refused
CASES = ("peak drive", "peak reverse")
SHAFTS = ("input", "intermediate", "output")
ORDER_GAP = 0.03  # a mode within 3 % of a gear order clashes (the contract)
MODE_COUNT = 12

_TETGEN_CHILD = (
    "import sys, numpy as np, tetgen\n"
    "z = np.load(sys.argv[1])\n"
    "try:\n"
    "    tg = tetgen.TetGen(z['v'], z['f'].astype(np.int32))\n"
    "    n, t = tg.tetrahedralize(order=1, minratio=float(z['q0']), mindihedral=float(z['q1']), "
    "maxvolume=float(z['vol']), quality=True, verbose=0)[:2]\n"
    "except RuntimeError as e:\n"
    "    print(e); sys.exit(3)\n"
    "np.savez(sys.argv[2], nodes=n, tets=t)\n"
)

# TetGen's own report of the triangles it skips as self-intersecting (switch d), run in its own
# folder: it writes them as `tetgen-tmpfile_skipped.face` and `.node`; their centres are kept fine
# by `mesh_tetgen`
_TETGEN_DETECT = (
    "import sys, os, numpy as np, tetgen\n"
    "z = np.load(sys.argv[1])\n"
    "os.chdir(sys.argv[3])\n"
    "try:\n"
    "    tetgen.TetGen(z['v'], z['f'].astype(np.int32)).tetrahedralize(switches='pdQ')\n"
    "except Exception:\n"
    "    pass\n"
    "c = []\n"
    "if os.path.exists('tetgen-tmpfile_skipped.face') and "
    "os.path.exists('tetgen-tmpfile_skipped.node'):\n"
    "    nd = {}\n"
    "    with open('tetgen-tmpfile_skipped.node') as fh:\n"
    "        for ln in list(fh)[1:]:\n"
    "            p = ln.split()\n"
    "            if len(p) >= 4 and not ln.lstrip().startswith('#'):\n"
    "                nd[int(p[0])] = [float(p[1]), float(p[2]), float(p[3])]\n"
    "    with open('tetgen-tmpfile_skipped.face') as fh:\n"
    "        for ln in list(fh)[1:]:\n"
    "            p = ln.split()\n"
    "            if len(p) >= 4 and not ln.lstrip().startswith('#'):\n"
    "                q = [nd.get(int(i)) for i in p[1:4]]\n"
    "                if all(x is not None for x in q):\n"
    "                    c.append(np.mean(q, axis=0))\n"
    "np.save(sys.argv[2], np.asarray(c, float).reshape(-1, 3))\n"
)


class TetGenRefused(RuntimeError):
    """TetGen refused a surface; `centres` the places it named (its skipped triangles' centres), if
    any."""

    def __init__(self, message: str, centres: np.ndarray | None = None):
        super().__init__(message)
        self.centres = (
            np.zeros((0, 3)) if centres is None else np.asarray(centres, float).reshape(-1, 3)
        )


def tetgen_skipped(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """The centres of the triangles TetGen skips as self-intersecting (its switch d), in a child
    process."""
    with tempfile.TemporaryDirectory(prefix="tgd_") as tmp:
        src, dst = Path(tmp) / "in.npz", Path(tmp) / "skipped.npy"
        np.savez(src, v=np.asarray(verts, float), f=np.asarray(faces, np.int64))
        try:
            subprocess.run(
                [sys.executable, "-c", _TETGEN_DETECT, str(src), str(dst), tmp],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=TETGEN_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return np.zeros((0, 3))
        return np.load(dst) if dst.exists() else np.zeros((0, 3))


def tetrahedralize_guarded(
    verts: np.ndarray, faces: np.ndarray, quality: tuple[float, float], regular: float
) -> tuple[np.ndarray, np.ndarray]:
    """TetGen's quality tets in a child process: TetGen hung on one cover for 8 minutes and crashed
    in its own code on others, taking FE with it without a word (12 October); a crash, a hang past
    `TETGEN_SECONDS` or a refusal is a RuntimeError, so the ladder goes on."""
    with tempfile.TemporaryDirectory(prefix="tg_") as tmp:
        src, dst = Path(tmp) / "in.npz", Path(tmp) / "out.npz"
        np.savez(
            src,
            v=np.asarray(verts, float),
            f=np.asarray(faces, np.int64),
            q0=quality[0],
            q1=quality[1],
            vol=regular,
        )
        p = subprocess.Popen(
            [sys.executable, "-c", _TETGEN_CHILD, str(src), str(dst)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            out, _ = p.communicate(timeout=TETGEN_SECONDS)
        except subprocess.TimeoutExpired:
            kill_tree(p.pid)
            raise RuntimeError(f"TetGen ran past {TETGEN_SECONDS} s") from None
        if p.returncode != 0 or not dst.exists():
            msg = (
                (out or "").strip().splitlines()[-1]
                if (out or "").strip()
                else f"TetGen crashed (code {p.returncode})"
            )
            # where it names its faces (self-intersections), the places for the mesher to keep fine
            raise TetGenRefused(
                msg, tetgen_skipped(verts, faces) if "self-intersect" in msg else None
            )
        with np.load(dst) as z:  # closed before the folder goes (Windows keeps an open file)
            return np.array(z["nodes"], float), np.array(z["tets"], np.int64)


def mesh_tetgen(
    path: Path, size: float, quality: tuple[float, float], surface: float, last: float | None
) -> tuple[np.ndarray, np.ndarray]:
    """TET4 of one half drawn as a watertight triangle mesh: its surface coarsened to triangles of
    about `surface` mm (`mesh.coarse`), then TetGen's quality tets (a largest volume from `size`).
    When TetGen refuses the coarsened surface or makes a flat tet, it is coarsened again: first
    keeping fine the places TetGen named (up to `KEEP_TRIES` times), then a little coarser and a
    little finer, since where a decimation folds depends on its target, then at `last` mm if
    given."""
    t0 = time.time()
    raw = mr.load(path)
    regular = (1.5 * size) ** 3 / (
        6.0 * math.sqrt(2.0)
    )  # the largest tet: a regular one of edge 1.5 `size`
    ladder = tuple(
        dict.fromkeys(
            (
                surface,
                round(1.07 * surface, 2),
                round(0.93 * surface, 2),
                *(() if last is None else (last,)),
            )
        )
    )
    keep = np.zeros((0, 3))
    last_err, done = None, False
    for edge, k_try in [(e_, k_) for e_ in ladder for k_ in range(KEEP_TRIES)]:
        if k_try and not len(keep):
            continue  # nothing named: the next size
        verts, faces = mr.coarse(raw, edge, keep_near=keep)
        target = len(faces)
        try:
            nodes, tets = tetrahedralize_guarded(verts, faces, quality, regular)
        except RuntimeError as e:
            named = getattr(e, "centres", np.zeros((0, 3)))
            last_err = e
            if len(named):
                keep = np.vstack([keep, named])
                say(
                    f"{path.stem}: TetGen refused the surface at {edge:g} mm triangles ({e}); "
                    f"{len(named)} places it named kept fine, coarsened again"
                )
            else:
                say(
                    f"{path.stem}: TetGen refused the surface at {edge:g} mm triangles ({e}); "
                    "coarsened again"
                )
            continue
        flat = float(tet_shape(np.asarray(nodes, float), np.asarray(tets, np.int64)).min())
        if (
            flat < FLAT_TET and edge != ladder[-1]
        ):  # one flat tet stops the single factor (CLAUDE.md)
            say(
                f"{path.stem}: a flat tet (shape {flat:.2g}) at {edge:g} mm triangles; coarsened "
                "again"
            )
            continue
        done = True
        break
    if not done:
        if last_err is not None:
            raise last_err
        raise RuntimeError("no surface TetGen accepted")
    nodes, tets = np.asarray(nodes, float), np.asarray(tets, np.int64)
    say(
        f"{path.stem}: TetGen, {target:,} surface triangles, {len(tets):,} tets, worst shape "
        f"{float(tet_shape(nodes, tets).min()):.3g}, {time.time() - t0:.1f} s"
    )
    return nodes, tets


def tet_shape(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Each TET4's shape measure, 12·(3V)^(2/3) / Σ edge²: 1 for the regular tet, 0 for a flat
    one."""
    p = nodes[tets]
    a, b, c, d = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    vol = np.abs(np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a)) / 6.0
    s2 = sum((e * e).sum(axis=1) for e in (b - a, c - a, d - a, c - b, d - b, d - c))
    return 12.0 * (3.0 * vol) ** (2.0 / 3.0) / s2


def oriented(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    a, b, c, d = (nodes[tets[:, i]] for i in range(4))
    neg = np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a) < 0
    out = tets.copy()
    out[neg, 1], out[neg, 2] = tets[neg, 2], tets[neg, 1]
    return out


def skin_nodes(tets10: np.ndarray) -> np.ndarray:
    """The nodes on the mesh's outer surface (corner and mid-side), from the tets' unshared
    faces."""
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


def rbe3_loads(x: np.ndarray, ids: np.ndarray, point, force) -> np.ndarray:
    """Nodal forces (n, 3) spreading a force at `point` over the nodes so that the force and its
    moment balance (RBE3, uniform weights)."""
    p = x[ids]
    c = p.mean(axis=0)
    r = p - c
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    theta = np.linalg.solve(a, np.cross(np.asarray(point) - c, np.asarray(force)))
    return np.asarray(force)[None, :] / len(ids) + np.cross(theta[None, :], r)


def rigid_fit(x, u, ids):
    p, d = x[ids], u[ids]
    c = p.mean(axis=0)
    r = p - c
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    theta = np.linalg.solve(a, np.cross(r, d).sum(axis=0))
    return d.mean(axis=0), theta, c


def _volumes(h: dict) -> np.ndarray:
    x = h["nodes"][h["tets"][:, :4]]
    return (
        np.abs(
            np.einsum("ij,ij->i", np.cross(x[:, 1] - x[:, 0], x[:, 2] - x[:, 0]), x[:, 3] - x[:, 0])
        )
        / 6
    )


def lumped_mass(halves: dict, n_dof: int, density: float) -> np.ndarray:
    """The HRZ lumped mass per unknown: a TET10's corner nodes take 6/216 and its mid-side nodes
    32/216 of its mass."""
    mass = np.zeros(n_dof)
    weights = np.r_[np.full(4, 6 / 216), np.full(6, 32 / 216)]
    for h in halves.values():
        nodal = np.zeros(len(h["nodes"]))
        np.add.at(nodal, h["tets"], (_volumes(h) * density)[:, None] * weights[None, :])
        for c in range(3):
            mass[h["offset"] + 3 * np.arange(len(nodal)) + c] = nodal
    return mass


def _mesh(info: dict, out: Path, size: float, surface: float) -> tuple[dict, int, float]:
    """Both halves' TET10, made again at the next of `QUALITY_LADDER` while they pass `MESHED_MOST`,
    then from a coarser surface (`COARSER`)."""
    t0 = time.time()
    for surf, quality in [(surface, q) for q in QUALITY_LADDER] + [
        (s_, QUALITY_LADDER[-1]) for s_ in COARSER
    ]:
        halves, offset = {}, 0
        for half in ("motor_side", "cover"):
            nodes4, tets4 = mesh_tetgen(
                out / info["files"][half],
                size,
                quality,
                surf,
                LAST_SURFACE if surf == surface else None,
            )
            nodes, tets10 = quadratic(nodes4, oriented(nodes4, tets4))
            halves[half] = {
                "nodes": nodes,
                "tets": tets10,
                "skin": skin_nodes(tets10),
                "offset": offset,
            }
            offset += 3 * len(nodes)
            say(f"{half}: {len(tets10):,} TET10, {len(nodes):,} nodes")
        say(
            f"meshed in {time.time() - t0:.0f} s; {offset:,} unknowns (TetGen's radius-edge "
            f"{quality[0]:g}, dihedral {quality[1]:g}°"
            + (f", the surface at {surf:g} mm" if surf != surface else "")
            + ")"
        )
        if offset <= MESHED_MOST:
            return halves, offset, surf
    raise RuntimeError(
        f"{offset:,} unknowns, past the single factor's {MESHED_MOST:,}: mesh coarser"
    )


def judge(
    design: str, out: Path, contract: Path, size: float = SIZE, surface: float = SURFACE_EDGE
) -> dict:
    """The design's FE judgement (`fe_<design>.json`)."""
    info = json.loads((out / f"{design}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(contract)
    chain = complete_chain(spec)
    material = spec.manufacturing.material
    young, poisson = value_in(material.youngs_modulus, "MPa"), value_in(material.poisson_ratio, "1")
    density = value_in(material.density, "t/mm3")
    z_split = info["z"]["split"]
    s = info["settings"]
    t0 = time.time()
    halves, n_dof, surface_used = _mesh(info, out, size, surface)

    def half_of(z: float) -> str:
        return "motor_side" if z < z_split else "cover"

    # The seats: each bearing's seat nodes, in the half that holds it.
    seats = {}
    for b in info["bearings"]:
        half = half_of(0.5 * (b["z"][0] + b["z"][1]))
        h = halves[half]
        ids = on_cylinder(h["nodes"], h["skin"], b["axis"], b["D"] / 2, *b["z"])
        assert len(ids) > 20, f"too few seat nodes for {b['shaft']} {b['side']}: {len(ids)}"
        seats[(b["shaft"], b["side"])] = (half, ids, b)
    # Loads: the chain's seat forces per case, at the bearings' centres.
    cases = [c for c in chain.loads if c.name in CASES]
    f = np.zeros((n_dof, len(cases)))
    for j, case in enumerate(cases):
        for sf in case.seats:
            half, ids, b = seats[(sf.shaft, sf.side)]
            h = halves[half]
            loads = rbe3_loads(
                h["nodes"], ids, (*b["axis"], 0.5 * (b["z"][0] + b["z"][1])), sf.force
            )
            for k in range(3):
                np.add.at(f[:, j], h["offset"] + 3 * ids + k, loads[:, k])
    say(f"loads: {len(cases)} cases")

    t1 = time.time()
    blocks = []
    for half in ("motor_side", "cover"):
        h = halves[half]
        n = len(h["tets"])
        blocks.append(
            stiffness(h["nodes"], h["tets"], np.full(n, young), np.full(n, poisson), gpu=True)
        )
        release()
    k = sp.block_diag(blocks, format="csr")
    say(f"stiffness assembled in {time.time() - t1:.0f} s: {k.nnz:,} entries")
    # The rigid couplings (the engineer, 13 October 22:40-22:47).
    mounts = []
    bolts = 0
    lo, hi = halves["motor_side"], halves["cover"]
    t_f = s["flange_thickness"]
    xyz_all = np.zeros((n_dof // 3, 3))
    for h in halves.values():
        xyz_all[h["offset"] // 3 : h["offset"] // 3 + len(h["nodes"])] = h["nodes"]
    groups = []
    for (shaft, side), (half, ids, b) in seats.items():
        groups.append(
            {
                "nodes": halves[half]["offset"] // 3 + ids,
                "ref": (*b["axis"], 0.5 * (b["z"][0] + b["z"][1])),
                "name": f"the {shaft} {side} seat",
            }
        )
    for m in info["mounts"]:
        h = halves[half_of(0.5 * (m["z"][0] + m["z"][1]))]
        ids = on_cylinder(h["nodes"], h["skin"], m["centre"], s["mount_hole"] / 2, *m["z"])
        groups.append({"nodes": h["offset"] // 3 + ids, "fixed": True, "name": m["name"]})
        mounts.append((h, ids))
    for c in info["bolts"]:
        a = on_cylinder(lo["nodes"], lo["skin"], c, s["bolt_hole"] / 2, z_split - t_f, z_split)
        b_ = on_cylinder(hi["nodes"], hi["skin"], c, s["bolt_hole"] / 2, z_split, z_split + t_f)
        if len(a) < 6 or len(b_) < 6:
            continue
        groups.append(
            {
                "nodes": np.r_[lo["offset"] // 3 + a, hi["offset"] // 3 + b_],
                "ref": (c[0], c[1], z_split),
                "name": f"bolt {bolts + 1}",
            }
        )
        bolts += 1
    tee, tinfo = cpl.rigid_transform(xyz_all, groups)
    rigid = cpl.check_rigid(tee, xyz_all, groups, tinfo)
    if rigid > 1e-9:
        raise RuntimeError(f"the rigid couplings' transform is not rigid: {rigid:.1e}")
    eliminated = n_dof - tinfo["n_master"]
    k_red = (tee.T @ k @ tee).tocsr()
    k_red = (0.5 * (k_red + k_red.T)).tocsr()
    say(
        f"rigid couplings: {len(seats)} seats with their bearings' centres, {bolts} bolts each one "
        "rigid body through both halves, "
        f"{len(mounts)} mounts' holes held; {eliminated:,} unknowns eliminated, {k_red.shape[0]:,} "
        "remain"
    )

    t2 = time.time()
    factor = SingleFactor(k_red)
    say(f"single factor ({factor.kind}) in {factor.factor_s:.0f} s")
    columns = []
    steps_most, residual_worst = 0, 0.0
    try:
        for j in range(f.shape[1]):
            x_red, steps, residual = factor.solve(tee.T @ f[:, j])
            columns.append(tee @ x_red)
            steps_most, residual_worst = max(steps_most, steps), max(residual_worst, residual)
    except RuntimeError:
        factor.close()
        raise
    u_all = np.stack(columns, axis=1)
    solve_info = {
        "solver": f"cuDSS single {factor.kind}, refined; couplings eliminated",
        "factor_s": factor.factor_s,
        "refine_steps": steps_most,
        "residual": residual_worst,
        "eliminated": int(eliminated),
    }
    say(
        f"solved in {time.time() - t2:.0f} s (at most {steps_most} refining steps, residual "
        f"{residual_worst:.1e})"
    )

    result = {
        "stem": design,
        "load_model": "rbe3",
        "couplings": "kinematic",
        "size_mm": size,
        "surface_mm": surface_used,
        "unknowns": n_dof,
        "cases": {},
    }
    for j, case in enumerate(cases):
        u = u_all[:, j]
        res = {"seats": {}, "reactions": {}, "shafts": {}}
        for (shaft, side), (half, ids, _b) in seats.items():
            hh = halves[half]
            uu = u[hh["offset"] : hh["offset"] + 3 * len(hh["nodes"])].reshape(-1, 3)
            mean, theta, _c = rigid_fit(hh["nodes"], uu, ids)
            res["seats"][f"{shaft} {side}"] = {
                "displacement_mm": float(np.linalg.norm(mean)),
                "radial_mm": float(np.hypot(mean[0], mean[1])),
                "tilt_mrad": float(1000 * np.hypot(theta[0], theta[1])),
                "u": mean.tolist(),
                "theta": theta.tolist(),
                "nodes": int(len(ids)),
            }
        for shaft in SHAFTS:
            a_, b_ = res["seats"][f"{shaft} -z"], res["seats"][f"{shaft} +z"]
            za = next(
                bb["z"] for bb in info["bearings"] if bb["shaft"] == shaft and bb["side"] == "-z"
            )
            zb = next(
                bb["z"] for bb in info["bearings"] if bb["shaft"] == shaft and bb["side"] == "+z"
            )
            span = 0.5 * (zb[0] + zb[1]) - 0.5 * (za[0] + za[1])
            du = np.array(b_["u"]) - np.array(a_["u"])
            res["shafts"][shaft] = {
                "tilt_mrad": float(1000 * math.hypot(du[0], du[1]) / span),
                "span_mm": span,
            }
        # The mounts' reactions: the constraint forces K u - f, nonzero only at the coupled nodes
        # (the bolts' cancel pairwise), summed over each mount's hole as a force and a moment about
        # the origin; with the loads they balance.
        g = k @ u - f[:, j]
        force, moment = np.zeros(3), np.zeros(3)
        for h, ids in mounts:
            gi = g[h["offset"] + 3 * ids[:, None] + np.arange(3)[None, :]]
            force += gi.sum(axis=0)
            moment += np.cross(h["nodes"][ids], gi).sum(axis=0)
        applied_f = np.array([f[0::3, j].sum(), f[1::3, j].sum(), f[2::3, j].sum()])
        applied_m = np.zeros(3)
        for h in halves.values():
            fh = f[h["offset"] : h["offset"] + 3 * len(h["nodes"]), j].reshape(-1, 3)
            applied_m += np.cross(h["nodes"], fh).sum(axis=0)
        res["reactions"] = {
            "force_N": force.tolist(),
            "moment_Nmm": moment.tolist(),
            "applied_force_N": applied_f.tolist(),
            "applied_moment_Nmm": applied_m.tolist(),
        }
        res["largest_mm"] = float(np.abs(u).reshape(-1, 3).max())
        result["cases"][case.name] = res
    result["mass_kg"] = float(sum(_volumes(h).sum() for h in halves.values())) * density * 1000.0
    t3 = time.time()
    try:
        lumped = lumped_mass(halves, n_dof, density)
        m_red = (tee.T @ sp.diags(lumped) @ tee).tocsr()
        result["modes_hz"], vecs = modes(k_red, m_red, factor, MODE_COUNT)
        shape = (tee @ vecs).reshape(-1, 3, vecs.shape[1])
        np.savez_compressed(
            out / f"fe_{design}_modes.npz",
            hz=np.asarray(result["modes_hz"]),
            node_mass=lumped[0::3].astype(np.float32),
            magnitude=np.sqrt((shape**2).sum(axis=1)).astype(np.float16),
        )
        del shape, vecs
    finally:
        factor.close()
    say(
        f"modes in {time.time() - t3:.0f} s: {', '.join(f'{v:.0f}' for v in result['modes_hz'])} Hz"
    )
    # Against the gear orders at the rated speed (the contract: at least 3 % apart).
    meshes = [
        (st.name, int(st.z_pinion.value) * chain.speeds[st.pinion_shaft] / 60.0)
        for st in spec.requirement.stages
    ]
    result["mesh_hz"] = dict(meshes)
    result["order_clashes"] = [
        f"{v:.0f} Hz within 3 % of {name}'s {hz:.0f} Hz"
        for v in result["modes_hz"]
        for name, hz in meshes
        if abs(v - hz) / hz < ORDER_GAP
    ]
    say(
        f"mesh frequencies {', '.join(f'{n} {hz:.0f} Hz' for n, hz in meshes)}; clashes: "
        f"{result['order_clashes'] or 'none'}"
    )
    result["solve"] = {
        k_: (v if isinstance(v, (int, float, str)) else str(v)) for k_, v in solve_info.items()
    }
    result["seconds"] = time.time() - t0
    (out / f"fe_{design}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    np.savez_compressed(
        out / f"fe_{design}.npz",
        **{f"{half}_nodes": h["nodes"] for half, h in halves.items()},
        **{f"{half}_tets": h["tets"] for half, h in halves.items()},
        **{f"{half}_offset": np.array(h["offset"]) for half, h in halves.items()},
        u=u_all,
    )
    for name, res in result["cases"].items():
        worst = max(res["seats"].items(), key=lambda kv: kv[1]["displacement_mm"])
        tilt = max(res["seats"].items(), key=lambda kv: kv[1]["tilt_mrad"])
        rm = np.array(res["reactions"]["moment_Nmm"]) / 1000
        am = np.array(res["reactions"]["applied_moment_Nmm"]) / 1000
        say(
            f"{name}: worst seat {worst[0]} {worst[1]['displacement_mm'] * 1000:.1f} um; worst "
            f"tilt {tilt[0]} {tilt[1]['tilt_mrad']:.3f} mrad; "
            f"mounts' moment {np.round(rm, 1)} N·m against the loads' {np.round(am, 1)} N·m"
        )
    say(f"mass from the mesh {result['mass_kg']:.2f} kg; {result['seconds']:.0f} s in all")
    return result
