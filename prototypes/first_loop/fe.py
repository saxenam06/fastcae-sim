"""PROTOTYPE (LOP-2) - not product code: the FE judgement of a two-half housing.

The engineer's FE practice (9 October 02:12-02:15):
- each bearing's load enters through a distributing coupling from the bearing's centre to every
  node of its seat (RBE3 weights, uniform): the force spread so force and moment balance;
- the two halves are joined at each bolt by distributing couplings: the two holes' best-fit rigid
  motions (RBE3 reference motions) are made equal;
- the mount bosses are held fixed through distributing couplings: each hole's best-fit rigid
  motion is zero;
- the motor's reaction torque acts on the motor flange's bolt holes, spread as RBE3 does.
A coupling's equations (the coupled nodes' mean translation and best-fit rotation, six per
coupling) hold exactly: six unknowns of each coupled set are eliminated in favour of the rest, and
the stiffness is reduced to the masters, T' K T, which stays symmetric positive definite with K's
own conditioning. No penalty, so the single-precision factor refines; no double factor (the
engineer, 3 October: the factor must fit the card).

The mesh: each half by gmsh (TET4, then straight-sided TET10 as fastcae does), the coupled nodes
found on the mesh's skin from the exact geometry (shell.json's seats, holes and bolts). The solve:
fastcae-v1's TET10 stiffness (fastcae_fe.py, copied) and one cuDSS factor in single precision,
kept for the load cases and the modes, every answer refined to double by conjugate gradients.
The answer per load case: every seat's displacement and tilt (its nodes' best-fit rigid motion),
the shafts' tilts, the reactions (they must balance the loads), and the mass.

Run: uv run python prototypes/first_loop/fe.py [stem] [size_mm]     (default: shell 6)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import gmsh
import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastcae_fe import REFINE_MOST, REFINE_TOL, quadratic, release, stiffness  # noqa: E402
from hostenv import kill_tree, python_exe  # noqa: E402

from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402

OUT = ROOT / "data" / "first_loop"
# The contract judged: the product's, unless LOOP_CONTRACT names a what-if variant of it.
CONTRACT = Path(os.environ.get("LOOP_CONTRACT", ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"))
YOUNG, POISSON, DENSITY = 69_000.0, 0.33, 2.6e-9  # MPa, -, t/mm³: the contract's EN AC-42100 T6
TOL = 0.25  # mm: how near a node must lie to a coupled surface
MESH_3D = int(os.environ.get("LOOP_MESH3D", "10"))  # gmsh's 3D algorithm: 10 HXT, 1 Delaunay
GMRES_MOST = 480  # the most GMRES steps after conjugate gradients stall (8 restarts of 60)
SCALE = os.environ.get("LOOP_SCALE", "1") != "0"  # the stiffness scaled by its diagonal before factoring
# How a seat takes its bearing's load: "rbe3", the engineer's whole-seat distributing coupling,
# or "cosine", the plan's D6a for comparison (LOOP_LOADS=cosine).
LOAD_MODEL = os.environ.get("LOOP_LOADS", "rbe3")
# A diagnostic, never a design: the stiffness of a region scaled (LOOP_STIFF="end:100,side:1"),
# to measure how much of the misalignment each region's compliance causes - the ceiling of what
# stiffening it can give. Regions: boss, end, side, flange, motor, mount (`regions`).
STIFF = {
    k: float(v)
    for k, v in (p.split(":") for p in os.environ.get("LOOP_STIFF", "").split(",") if p)
}
# LOOP_MODES=0 skips the modal solve (for diagnostics).
WITH_MODES = os.environ.get("LOOP_MODES", "1") != "0"
# The modes' shapes kept (LOP-24, the plan's step 3: a clashing mode identified by its shape):
# `fe_<stem>_modes.npz`, each mode's displacement magnitude at every node, mass-normalised
# (`mode_shape.py` reads it); LOOP_MODE_SHAPES=0 keeps the frequencies alone
MODE_SHAPES = os.environ.get("LOOP_MODE_SHAPES", "1") != "0"


def regions(info: dict, nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Each element's region by its centroid, from the CAD record: a boss (within its bearing's
    boss radius, along the boss), an end wall (within a pod's end-wall thickness of its end
    face), the flange (beyond the pods' outlines, at the split), the motor's plate and ring, a
    mount, or else a side wall."""
    from matplotlib.path import Path as MplPath

    c = nodes[tets[:, :4]].mean(axis=1)
    out = np.full(len(c), "side", dtype=object)
    s = info["settings"]
    pods = info.get("pods") or []
    inside_any = np.zeros(len(c), dtype=bool)
    for p in pods:
        inside = MplPath(np.asarray(p["outer"])).contains_points(c[:, :2])
        inside_any |= inside
        t_lo = p.get("thick", {}).get("-z", s.get("end_wall", s["wall"])) if isinstance(p.get("thick"), dict) else s.get("end_wall", s["wall"])
        t_hi = p.get("thick", {}).get("+z", s.get("end_wall", s["wall"])) if isinstance(p.get("thick"), dict) else s.get("end_wall", s["wall"])
        lo, hi = p["z"]
        out[inside & (c[:, 2] < lo + t_lo + 0.5)] = "end"
        out[inside & (c[:, 2] > hi - t_hi - 0.5)] = "end"
    z_split = info["z"]["split"]
    t_f = s["flange_thickness"]
    out[(~inside_any) & (np.abs(c[:, 2] - z_split) < t_f + 0.5)] = "flange"
    for m in info["mounts"]:
        near = np.hypot(c[:, 0] - m["centre"][0], c[:, 1] - m["centre"][1]) < s["mount_diameter"] / 2 + 0.5
        out[near & (c[:, 2] > m["z"][0] - 0.5) & (c[:, 2] < m["z"][1] + 0.5)] = "mount"
    # The motor's plate and ring: only on a design with a flange (the contract's layout has none,
    # the engineer, 10 October 13:21: the vehicle holds the motor)
    if "motor_ring" in s and info["z"].get("motor") is not None:
        z_motor = info["z"]["motor"]
        axis_in = next(b["axis"] for b in info["bearings"] if b["shaft"] == "input")
        ring_out = s["motor_ring"][1] / 2
        r_in = np.hypot(c[:, 0] - axis_in[0], c[:, 1] - axis_in[1])
        out[(c[:, 2] < z_motor + s.get("end_wall", s["wall"]) + 0.5) & (r_in < ring_out + 0.5) & (out != "end")] = "motor"
    for b in info["bearings"]:
        r = np.hypot(c[:, 0] - b["axis"][0], c[:, 1] - b["axis"][1])
        boss = r < b["D"] / 2 + s["boss"] + 0.5
        if b["side"] == "-z":
            along = c[:, 2] < b["z"][1] + 0.5
        else:
            along = c[:, 2] > b["z"][0] - 0.5
        out[boss & along] = "boss"
    return out


def say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


# --- the mesh ------------------------------------------------------------------------------------


def mesh_half(brep: Path, size: float) -> tuple[np.ndarray, np.ndarray]:
    """TET4 of one half by gmsh: nodes (n, 3) and tets (m, 4), 0-based.

    gmsh straight from the B-rep. Its slivers are born on the narrow faces the booleans leave
    (fastcae's lesson, 29 September): a design with many of them (ribs inside the housing, a dense
    lattice) gives a stiffness the single-precision factor cannot refine. Delaunay with Netgen's
    optimiser (fastcae's volume step) did not cure it and crashed on `lobed_e10` (9 October
    11:16); the cure is fastcae's face-by-face surface mesher (PHY)."""
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.occ.importShapes(str(brep))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 1.2)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.Algorithm3D", MESH_3D)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.model.mesh.generate(3)
        nodes, tets = _gmsh_tets()
        # A flat tet makes the stiffness singular, and the single factor cannot refine. Avtec's
        # mesh held one (20:43) where a side rib's face meets a corner fillet's tangent line.
        # Netgen's optimiser, run only then, takes it out (its worst tet 0 -> 0.059, 17 % more
        # tets); a mesh without one is left exactly as it was.
        worst = float(tet_shape(nodes, tets).min())
        if worst < FLAT_TET:
            gmsh.model.mesh.optimize("Netgen", force=True)
            nodes, tets = _gmsh_tets()
            say(f"{brep.stem}: a flat tet ({worst:.1e}); Netgen's optimiser gives {float(tet_shape(nodes, tets).min()):.3f}, {len(tets):,} tets")
        return nodes, tets
    finally:
        gmsh.finalize()


FLAT_TET = 1e-3  # the tet shape measure under which a tet counts as flat
STL_ANGLE = 30.0  # degrees: a watertight STL is cut into patches at edges sharper than this (`mesh_stl`)


# mm: the FE surface's triangles (`mesh_tetgen`). 9 mm until 11 October 08:45 (at 6 mm the drive
# design of 02:20 took 695,000 tets, 3.4 M unknowns, past the factor's 2.18 M); since then 7 mm
# (LOP-23): a design of 4 mm ribs read 63.5 µm at its worst bed on 9 mm triangles, 51.3 on 7 and
# 50.1 on 6, and its tilt 1.11, 1.02 at 6: the decimation keeps the mass but flattens a thin rib's
# section, so the coarse surface judged it soft. A design of 6 mm members read 32.8 and 33.1 µm.
SURFACE_EDGE = 7.0
# LOOP_SURFACE_EDGE (mm) judges a design on another surface; its results then go to
# fe_<stem>_surf<edge>.json, beside the default judgement
SURFACE_ASKED = float(os.environ.get("LOOP_SURFACE_EDGE", SURFACE_EDGE))
# (LOP-29, the engineer 13 October 22:40-22:47) the couplings: "kinematic" (rigid: each seat with its bearing's centre, where
# its load acts; each bolt's two holes one rigid body; each mount's hole held rigidly; `couplings.py`, the optimiser's too), or
# "distributing" (RBE3 ties of the holes' best-fit motions, every judgement before 13 October 23:00)
COUPLING = os.environ.get("LOOP_COUPLING", "kinematic")
SUFFIX = os.environ.get("LOOP_FE_SUFFIX", "")  # a judgement written beside the design's own, for a check
# the surface coarsened again at the next while TetGen refuses it or makes a flat tet (`mesh_tetgen`):
# first a little coarser and a little finer, since where a decimation folds depends on its target
SURFACE_LADDER = tuple(dict.fromkeys((SURFACE_ASKED, round(1.07 * SURFACE_ASKED, 2), round(0.93 * SURFACE_ASKED, 2), 5.0)))
KEEP_TRIES = 3  # (15 October) coarsenings at one size, each keeping fine the places TetGen named (`mesh_tetgen`)
FLAT_TET = 1e-6  # a tet's shape (`tet_shape`: 1 regular, 0 flat) under which the single factor breaks down (CLAUDE.md)
COARSER = (9.0, 11.0)  # mm: the surfaces tried, at the last of `QUALITY_LADDER`, when its tets still pass `MESHED_MOST`
# the 8 GB card's single-precision factor holds about this many unknowns (CLAUDE.md); a larger card (a RunPod worker,
# PLT-12) is given its own by `LOOP_CEILING_DOF`, measured there first: the default stays the laptop's
CEILING_DOF = int(os.environ.get("LOOP_CEILING_DOF", 2_180_000))
TET_RATIO, TET_DIHEDRAL = 2.0, 12.0  # TetGen's quality: radius-edge ratio at most, dihedral angle at least (degrees)
QUALITY_LADDER = ((TET_RATIO, TET_DIHEDRAL), (3.0, 10.0), (4.0, 8.0))  # tried in turn while the tets pass `MESHED_MOST` (`judge`)
# unknowns a mesh made by TetGen may have: the assembly's host memory, not the factor, set it (2.04 M asked
# 12.5 GB of a 16 GB laptop and failed, 11 October 04:54; 1.61 M ran)
MESHED_MOST = int(os.environ.get("LOOP_MESHED_MOST", 2_180_000))  # a worker with more host memory: `LOOP_MESHED_MOST` (PLT-12)


TETGEN_SECONDS = 240  # s: a TetGen call past this is taken as refused
_TETGEN_CHILD = (
    "import sys, numpy as np, tetgen\n"
    "z = np.load(sys.argv[1])\n"
    "try:\n"
    "    tg = tetgen.TetGen(z['v'], z['f'].astype(np.int32))\n"
    "    n, t = tg.tetrahedralize(order=1, minratio=float(z['q0']), mindihedral=float(z['q1']), maxvolume=float(z['vol']), quality=True, verbose=0)[:2]\n"
    "except RuntimeError as e:\n"
    "    print(e); sys.exit(3)\n"
    "np.savez(sys.argv[2], nodes=n, tets=t)\n"
)


# (15 October 03:15) TetGen's own report of the triangles it skips as self-intersecting (switch d), run in its own folder:
# it writes them as `tetgen-tmpfile_skipped.face` and `.node`; their centres saved for `mesh_tetgen` to keep fine
_TETGEN_DETECT = (
    "import sys, os, numpy as np, tetgen\n"
    "z = np.load(sys.argv[1])\n"
    "os.chdir(sys.argv[3])\n"
    "try:\n"
    "    tetgen.TetGen(z['v'], z['f'].astype(np.int32)).tetrahedralize(switches='pdQ')\n"
    "except Exception:\n"
    "    pass\n"
    "c = []\n"
    "if os.path.exists('tetgen-tmpfile_skipped.face') and os.path.exists('tetgen-tmpfile_skipped.node'):\n"
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
    """TetGen refused a surface; `centres` the places it named (its skipped triangles' centres), if any."""

    def __init__(self, message: str, centres: np.ndarray | None = None):
        super().__init__(message)
        self.centres = np.zeros((0, 3)) if centres is None else np.asarray(centres, float).reshape(-1, 3)


def tetgen_skipped(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """The centres of the triangles TetGen skips as self-intersecting (its switch d), in a child process."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory(prefix="tgd_") as tmp:
        src, dst = Path(tmp) / "in.npz", Path(tmp) / "skipped.npy"
        np.savez(src, v=np.asarray(verts, float), f=np.asarray(faces, np.int64))
        py = python_exe()
        try:
            subprocess.run([str(py), "-c", _TETGEN_DETECT, str(src), str(dst), tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=TETGEN_SECONDS)  # fmt: skip
        except subprocess.TimeoutExpired:
            return np.zeros((0, 3))
        return np.load(dst) if dst.exists() else np.zeros((0, 3))


def tetrahedralize_guarded(verts: np.ndarray, faces: np.ndarray, quality: tuple[float, float], regular: float) -> tuple[np.ndarray, np.ndarray]:
    """TetGen's quality tets in a child process (12 October 05:20): TetGen hung on one cover for 8 minutes
    (`prod14_asis`) and crashed in its own code on others, taking FE with it without a word (`prod17_asis`,
    `fa9_bar3`); a crash, a hang past `TETGEN_SECONDS` or a refusal is a RuntimeError, so the ladder goes on."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory(prefix="tg_") as tmp:
        src, dst = Path(tmp) / "in.npz", Path(tmp) / "out.npz"
        np.savez(src, v=np.asarray(verts, float), f=np.asarray(faces, np.int64), q0=quality[0], q1=quality[1], vol=regular)
        py = python_exe()
        p = subprocess.Popen([str(py), "-c", _TETGEN_CHILD, str(src), str(dst)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            out, _ = p.communicate(timeout=TETGEN_SECONDS)
        except subprocess.TimeoutExpired:
            kill_tree(p.pid)
            raise RuntimeError(f"TetGen ran past {TETGEN_SECONDS} s") from None
        if p.returncode != 0 or not dst.exists():
            msg = (out or "").strip().splitlines()[-1] if (out or "").strip() else f"TetGen crashed (code {p.returncode})"
            # (15 October 03:15) where it names its faces (self-intersections), the places for the mesher to keep fine
            raise TetGenRefused(msg, tetgen_skipped(verts, faces) if "self-intersect" in msg else None)
        with np.load(dst) as z:  # closed before the folder goes (Windows keeps an open file)
            return np.array(z["nodes"], float), np.array(z["tets"], np.int64)


def mesh_tetgen(path: Path, size: float, ready: bool = False, quality: tuple[float, float] = (TET_RATIO, TET_DIHEDRAL),
                surface: float | None = None) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
    """TET4 of one half drawn as a watertight triangle mesh (`mesh_route.py`; 11 October): its
    surface simplified by manifold3d (edges under 0.05 mm collapsed: the booleans' slivers),
    decimated by quadric edge collapses (pymeshlab, topology kept) to triangles of about
    `SURFACE_EDGE`, then TetGen's quality tets (radius-edge ratio `TET_RATIO`, dihedral at least
    `TET_DIHEDRAL`, a largest volume from `size`). gmsh's routes failed on this surface: its
    reparametrisation of marching cubes' patches ("Wrong topology of boundary mesh") or crawled,
    and the surface sewn into a B-rep kept faces 0.000 mm wide (11 October 01:46-02:07). On
    `outcome_skin_6mm_onerun`'s motor side: 134,870 tets, worst shape 0.0137, in 2 s.
    `ready`: the surface is already FE's (`ribbed_cad.mesh_body`: coarse parts joined exactly),
    taken as it is: the coarsening folded a ribbed design's bare 4 mm walls (03:50).
    When TetGen refuses the coarsened surface, it is coarsened again to the next of
    `SURFACE_LADDER`: the 10 mm scout's surface crossed itself where pymeshlab's test saw no
    crossing (05:24), and where a coarsening folds depends on its target."""
    import mesh_route as mr

    t0 = time.time()
    raw = mr.load(path)
    regular = (1.5 * size) ** 3 / (6.0 * math.sqrt(2.0))  # the largest tet: a regular one of edge 1.5 `size`
    ladder = SURFACE_LADDER if surface is None else tuple(dict.fromkeys((surface, round(1.07 * surface, 2), round(0.93 * surface, 2))))
    # (15 October 03:15) the places TetGen names when it refuses (`TetGenRefused.centres`), kept fine in the next coarsening
    # at the same size, up to KEEP_TRIES times: `spl8`'s motor side refused every size from 4 to 7 mm over a long sliver by
    # mount-3's bracket and three-in-a-line triangles by mount-1's lug, where a deep member meets the exact parts
    keep = np.zeros((0, 3))
    attempts = [(e_, k_) for e_ in ((None,) if ready else ladder) for k_ in range(1 if ready else KEEP_TRIES)]
    last_err, done = None, False
    for edge, k_try in attempts:
        if k_try and not len(keep):
            continue  # nothing named: the next size
        verts, faces = (np.asarray(raw.vertices, float), np.asarray(raw.faces, np.int64)) if ready else mr.coarse(raw, edge, keep_near=keep)
        target = len(faces)
        try:
            nodes, tets = tetrahedralize_guarded(verts, faces, quality, regular)
        except RuntimeError as e:
            named = getattr(e, "centres", np.zeros((0, 3)))
            last_err = e
            if ready:
                raise
            if len(named):
                keep = np.vstack([keep, named])
                say(f"{path.stem}: TetGen refused the surface at {edge:g} mm triangles ({e}); {len(named)} places it named kept fine, coarsened again")
            else:
                say(f"{path.stem}: TetGen refused the surface at {edge:g} mm triangles ({e}); coarsened again")
            continue
        # One flat tet stops the single factor (CLAUDE.md): outcome_env20_4mm_6.0kg's motor side at 7
        # mm triangles held one (11 October 08:45)
        flat = float(tet_shape(np.asarray(nodes, float), np.asarray(tets, np.int64)).min())
        if flat < FLAT_TET and not ready and edge != ladder[-1]:
            say(f"{path.stem}: a flat tet (shape {flat:.2g}) at {edge:g} mm triangles; coarsened again")
            continue
        done = True
        break
    if not done:
        if last_err is not None:
            raise last_err
        raise RuntimeError("no surface TetGen accepted")
    nodes, tets = np.asarray(nodes, float), np.asarray(tets, np.int64)
    say(f"{path.stem}: TetGen, {target:,} surface triangles, {len(tets):,} tets, worst shape {float(tet_shape(nodes, tets).min()):.3g}, {time.time() - t0:.1f} s")
    return nodes, tets


def mesh_stl(stl: Path, size: float) -> tuple[np.ndarray, np.ndarray]:
    """TET4 of one half drawn as a watertight triangle mesh by gmsh's reparametrisation (kept for
    the record; it failed on the mesh route's surfaces, `mesh_tetgen` is used): gmsh cuts the
    surface into patches at its sharp edges (`STL_ANGLE`: the machined cuts' rims), gives each a
    parametrisation, meshes them afresh at `mesh_half`'s sizes, then the volume; the flat-tet cure
    as `mesh_half`'s. Its own triangles (marching cubes' at 2 mm, some skinny) are never kept."""
    import trimesh

    # The indexed copy beside the STL keeps manifold3d's topology: from the STL gmsh rejoins the
    # triangles by position, and where two sheets touch at a point that made a vertex no patch
    # could be parametrised at ("Wrong topology of boundary mesh", 11 October 01:46)
    ply = stl.with_suffix(".ply")
    surface = trimesh.load(str(ply if ply.exists() else stl), process=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(stl.stem)
        entity = gmsh.model.addDiscreteEntity(2)
        n_v = len(surface.vertices)
        gmsh.model.mesh.addNodes(2, entity, list(range(1, n_v + 1)), np.asarray(surface.vertices, float).ravel().tolist())
        gmsh.model.mesh.addElementsByType(entity, 2, [], (np.asarray(surface.faces, np.int64) + 1).ravel().tolist())
        gmsh.model.mesh.classifySurfaces(math.radians(STL_ANGLE), True, True, math.radians(180.0))
        gmsh.model.mesh.createGeometry()
        surfaces = [e[1] for e in gmsh.model.getEntities(2)]
        loop = gmsh.model.geo.addSurfaceLoop(surfaces)
        gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 1.2)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay on the patches
        gmsh.option.setNumber("Mesh.Algorithm3D", MESH_3D)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.model.mesh.generate(3)
        nodes, tets = _gmsh_tets()
        worst = float(tet_shape(nodes, tets).min())
        if worst < FLAT_TET:
            gmsh.model.mesh.optimize("Netgen", force=True)
            nodes, tets = _gmsh_tets()
            say(f"{stl.stem}: a flat tet ({worst:.1e}); Netgen's optimiser gives {float(tet_shape(nodes, tets).min()):.3f}, {len(tets):,} tets")
        return nodes, tets
    finally:
        gmsh.finalize()


def _gmsh_tets() -> tuple[np.ndarray, np.ndarray]:
    """The current gmsh model's nodes (n, 3) and TET4 (m, 4), 0-based."""
    tags, coords, _ = gmsh.model.mesh.getNodes()
    types, _, elem_nodes = gmsh.model.mesh.getElements(3)
    k = list(types).index(4)
    tets = np.asarray(elem_nodes[k], dtype=np.int64).reshape(-1, 4)
    index = np.full(int(tags.max()) + 1, -1, dtype=np.int64)
    index[tags] = np.arange(len(tags))
    return np.asarray(coords).reshape(-1, 3), index[tets]


def tet_shape(nodes: np.ndarray, tets: np.ndarray) -> np.ndarray:
    """Each TET4's shape measure, 12·(3V)^(2/3) / Σ edge²: 1 for the regular tet, 0 for a flat one."""
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


COUPLED_MOST = 300  # nodes a coupling reads its set's rigid motion from


def spread(nodes, ids, most: int = COUPLED_MOST):
    """At most `most` of a coupled node set, spread over it (one a cell of a grid grown until few
    enough are left). Eliminating a coupling ties its six slave unknowns to every other unknown of
    its set, so the reduced stiffness holds a dense block over the set: a ribbed design's holes,
    meshed finely, made 1.2 billion entries and asked 18 GB (11 October 04:57). A best-fit rigid
    motion reads as well from a few hundred nodes spread over the hole."""
    if len(ids) <= most:
        return ids
    p = nodes[ids]
    cell = 0.5
    while True:
        key = np.floor((p - p.min(axis=0)) / cell).astype(np.int64)
        _, first = np.unique(key, axis=0, return_index=True)
        if len(first) <= most:
            return ids[np.sort(first)]
        cell *= 1.25


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


def cosine_loads(x: np.ndarray, ids: np.ndarray, axis, force) -> np.ndarray:
    """The plan's D6a, for comparison with the engineer's whole-seat coupling: the radial force as
    a pressure over the seat's loaded half, normal to the bore and growing as the cosine of the
    angle from the load's direction; the axial force spread evenly over the seat. Nothing pulls
    the unloaded half."""
    p = x[ids]
    radial = np.array([force[0], force[1]])
    size = float(np.hypot(*radial))
    out = np.zeros((len(ids), 3))
    out[:, 2] = force[2] / len(ids)
    if size == 0:
        return out
    e = radial / size
    n = p[:, :2] - np.asarray(axis)[None, :]
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    cos = n @ e
    w = np.where(cos > 0, cos, 0.0)
    # The pressure's resultant along the load: sum of w_i (n_i . e) = sum of w_i cos_i.
    scale = size / float((w * cos).sum())
    out[:, :2] = scale * w[:, None] * n
    return out


def rigid_fit(x, u, ids):
    p, d = x[ids], u[ids]
    c = p.mean(axis=0)
    r = p - c
    a = np.einsum("i,jk->jk", (r * r).sum(1), np.eye(3)) - r.T @ r
    theta = np.linalg.solve(a, np.cross(r, d).sum(axis=0))
    return d.mean(axis=0), theta, c


# --- the constraints, eliminated -----------------------------------------------------------------


def eliminate(blocks: list, n_dof: int) -> tuple[sp.csr_matrix, np.ndarray]:
    """u = T u_m: every coupling's six rows C u = 0 solved for six slave unknowns of its own node
    set, the six whose columns a pivoted QR finds best conditioned; every other unknown is a master.
    The couplings touch disjoint node sets, so the slaves are distinct. Returns T (n_dof, n_master)
    and the slave unknowns. No penalty: the constraints hold exactly, and the reduced stiffness
    T' K T keeps K's conditioning, so a single-precision factor refines."""
    from scipy.linalg import qr

    slave_rows: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for c in blocks:
        c = c.tocsr()
        support = np.unique(c.indices)
        d = c[:, support].toarray()
        _, r, piv = qr(d, pivoting=True, mode="economic")
        assert abs(r[5, 5]) > 1e-9 * abs(r[0, 0]), "a coupling's six rows are not independent"
        s_cols, m_cols = piv[:6], piv[6:]
        x = -np.linalg.solve(d[:, s_cols], d[:, m_cols])
        for i, s in enumerate(support[s_cols]):
            assert s not in slave_rows, "two couplings share a slave unknown"
            slave_rows[int(s)] = (support[m_cols], x[i])
    slaves = np.array(sorted(slave_rows), dtype=int)
    is_slave = np.zeros(n_dof, dtype=bool)
    is_slave[slaves] = True
    for m, _ in slave_rows.values():
        assert not is_slave[m].any(), "a coupling's master is another coupling's slave"
    col_of = np.cumsum(~is_slave) - 1
    masters = np.flatnonzero(~is_slave)
    rows = [masters]
    cols = [col_of[masters]]
    vals = [np.ones(len(masters))]
    for s, (m, x) in slave_rows.items():
        rows.append(np.full(len(m), s))
        cols.append(col_of[m])
        vals.append(x)
    t = sp.csr_matrix(
        (np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
        shape=(n_dof, n_dof - len(slaves)),
    )
    return t, slaves


class SingleFactor:
    """A cuDSS factor of a symmetric positive definite stiffness in single precision, kept for as
    many right-hand sides as the judgement needs (the load cases, then the modes' Lanczos
    iterations); each answer refined to double by conjugate gradients with the factor as their
    preconditioner (fastcae's practice, copied in `fastcae_fe._refined`). Single precision on
    purpose: the factor must fit the card (the engineer, 3 October). There is no double factor and
    no fallback to one; a stiffness this factor cannot precondition fails."""

    def __init__(self, k: sp.csr_matrix):
        import cupy as cp
        import cupyx.scipy.sparse as csp
        from fastcae_fe import _mtlayer
        from nvmath.sparse.advanced import (
            DirectSolver,
            DirectSolverMatrixType,
            ExecutionCUDA,
            HybridMemoryModeOptions,
        )

        self.k = k
        self.cp = cp
        self.kind = None
        self.gmres_most = GMRES_MOST
        # The stiffness scaled by its diagonal (S K S, S = diag(K)^-1/2) before it is factored:
        # a sliver element or a stiff rib makes K's entries span many decades, which a single-
        # precision factor rounds away; scaled, every diagonal entry is 1 and the factor is a
        # far better preconditioner. The refinement still works on K itself, in double.
        self.scale = 1.0 / np.sqrt(k.diagonal()) if SCALE else np.ones(k.shape[0])
        scaled = sp.diags(self.scale) @ k @ sp.diags(self.scale)
        release()
        self.a = csp.csr_matrix(scaled.astype(np.float32))
        self.b = cp.asfortranarray(cp.zeros((k.shape[0], 1), dtype=np.float32))
        execution = ExecutionCUDA(
            hybrid_memory_mode_options=HybridMemoryModeOptions(hybrid_memory_mode=True)
        )
        # Cholesky first; where its single-precision rounding breaks a pivot, LDL^T with pivoting,
        # still in single precision (fastcae's FACTORS, without the double one).
        for kind in ("SPD", "SYMMETRIC"):
            options = {
                "sparse_system_type": getattr(DirectSolverMatrixType, kind),
                "multithreading_lib": _mtlayer(),
            }
            self.solver = DirectSolver(self.a, self.b, options=options, execution=execution)
            t0 = time.time()
            self.solver.plan()
            self.solver.factorize()
            cp.cuda.Device().synchronize()
            self.factor_s = time.time() - t0
            probe = self.backsolve(np.ones(k.shape[0]))
            if np.all(np.isfinite(probe)):
                self.kind = kind
                break
            self.solver.free()
        if self.kind is None:
            self.close()
            raise RuntimeError("every single-precision factor broke down: the stiffness is singular")

    def backsolve(self, r: np.ndarray) -> np.ndarray:
        """K^-1 r by the scaled single factor: S (S K S)^-1 S r."""
        cp = self.cp
        rs = self.scale * np.asarray(r, dtype=np.float64).reshape(-1)
        self.solver.reset_operands(b=cp.asfortranarray(cp.asarray(rs.reshape(-1, 1), dtype=np.float32)))
        return self.scale * cp.asnumpy(self.solver.solve()).astype(np.float64).reshape(-1)

    def solve(self, f: np.ndarray, tol: float = REFINE_TOL, most: int = REFINE_MOST):
        """k x = f for one right-hand side, refined to the relative residual `tol` in at most
        `most` conjugate-gradient steps. Returns (x, steps, residual); raises when it does not
        get there."""
        b = np.asarray(f, dtype=np.float64).reshape(-1)
        scale = max(float(np.linalg.norm(b)), 1e-300)
        x = self.backsolve(b)
        r = b - self.k @ x
        steps = 0
        if float(np.linalg.norm(r)) > tol * scale:
            z = self.backsolve(r)
            p = z.copy()
            rz = float(r @ z)
            while steps < most:
                kp = self.k @ p
                alpha = rz / float(p @ kp)
                x = x + alpha * p
                r = r - alpha * kp
                steps += 1
                if float(np.linalg.norm(r)) <= tol * scale:
                    break
                z = self.backsolve(r)
                rz_new = float(r @ z)
                p = z + (rz_new / rz) * p
                rz = rz_new
        residual = float(np.linalg.norm(r)) / scale
        if (not np.isfinite(residual) or residual > 100 * tol) and self.gmres_most:
            # Conjugate gradients stall when the single factor, on a mesh with many slivers, is
            # no longer quite positive definite. GMRES takes any preconditioner: the same single
            # factor, restarted every 60 steps; the answer is still judged by K x = f in double.
            from scipy.sparse.linalg import LinearOperator, gmres

            n = self.k.shape[0]
            m = LinearOperator((n, n), matvec=self.backsolve, dtype=np.float64)
            start = x if np.all(np.isfinite(x)) else self.backsolve(b)
            count = [0]

            def tick(_):
                count[0] += 1

            x, _ = gmres(self.k, b, x0=start, M=m, rtol=tol, atol=0.0, restart=60,
                         maxiter=self.gmres_most // 60, callback=tick, callback_type="pr_norm")  # fmt: skip
            residual = float(np.linalg.norm(b - self.k @ x)) / scale
            steps += count[0]
        if not np.isfinite(residual) or residual > 100 * tol:
            raise RuntimeError(
                f"the single-precision factor did not refine: residual {residual:.1e} after "
                f"{steps} steps"
            )
        return x, steps, residual

    def close(self) -> None:
        if getattr(self, "solver", None) is not None:
            self.solver.free()
            self.solver = None
        self.a = self.b = None
        release()


# --- the modes -----------------------------------------------------------------------------------


def lumped_mass(halves: dict, n_dof: int) -> np.ndarray:
    """The HRZ lumped mass per unknown: a TET10's corner nodes take 6/216 and its mid-side nodes
    32/216 of its mass."""
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
    return mass


def modes(k_red: sp.csr_matrix, m_red: sp.csr_matrix, factor: SingleFactor, count: int = 12, vectors: bool = False):
    """The housing's first natural frequencies (Hz) as held: Lanczos in shift-invert about zero
    (scipy's eigsh) on the reduced stiffness and mass, every inner solve by the single factor
    refined to 1e-7 (the frequencies need no more). With `vectors`, (the frequencies, the modes'
    reduced vectors in the same order, mass-normalised)."""
    from scipy.sparse.linalg import LinearOperator, eigsh

    n = k_red.shape[0]
    op = LinearOperator(
        (n, n), matvec=lambda v: factor.solve(v, tol=1e-7, most=REFINE_MOST)[0], dtype=np.float64
    )
    out = eigsh(k_red, k=count, M=m_red, sigma=0.0, OPinv=op, which="LM", tol=1e-6,
                return_eigenvectors=vectors)  # fmt: skip
    if not vectors:
        return sorted(float(np.sqrt(max(v, 0.0)) / (2 * math.pi)) for v in out)
    values, vecs = out
    order = np.argsort(values)
    return [float(np.sqrt(max(v, 0.0)) / (2 * math.pi)) for v in values[order]], vecs[:, order]


# --- the judgement -------------------------------------------------------------------------------


def judge(stem: str = "shell", size: float = 6.0) -> dict:
    info = json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    spec, _ = load_and_validate(CONTRACT)
    chain = complete_chain(spec)
    z_split = info["z"]["split"]
    t0 = time.time()

    # A design drawn as meshes (the mesh route, 11 October) is a watertight STL a half, filled by
    # TetGen; when its tets pass the factor's ceiling at TetGen's quality, they are made again at
    # the next of `QUALITY_LADDER` (a ribbed design's thin ribs and bare walls: 2.82 M unknowns at
    # radius-edge 2, 04:36; flow B's designs fit at the first)
    # and when they pass it at every quality, from a coarser surface (`COARSER`; a ribbed CAD's FE
    # body, its ribs and terraces, held 31,060 triangles a half at 7 mm: 2.23 M unknowns at
    # radius-edge 4, 11 October 10:30)
    surface_used = SURFACE_ASKED
    for surface, quality in [(None, q) for q in QUALITY_LADDER] + [(s_, QUALITY_LADDER[-1]) for s_ in COARSER]:
        halves = {}
        offset = 0
        meshed = False
        for half in ("motor_side", "cover"):
            source = OUT / (info.get("files") or {}).get(half, f"{stem}_{half}.brep")
            meshed = source.suffix == ".stl"
            nodes4, tets4 = mesh_tetgen(source, size, ready=info.get("fe_mesh") == "ready", quality=quality, surface=surface) if meshed else mesh_half(source, size)
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
        say(f"meshed in {time.time() - t0:.0f} s; {n_dof:,} unknowns" + (f" (TetGen's radius-edge {quality[0]:g}, dihedral {quality[1]:g}°" + (f", the surface at {surface:g} mm" if surface else "") + ")" if meshed else ""))
        surface_used = surface or SURFACE_ASKED
        if n_dof <= MESHED_MOST or not meshed:
            break
    if n_dof > (MESHED_MOST if meshed else CEILING_DOF):  # refused at once: past it the factor ran out after 10 minutes (11 October 02:19)
        raise RuntimeError(f"{n_dof:,} unknowns, past the single factor's {CEILING_DOF:,}: mesh coarser")

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
            if LOAD_MODEL == "cosine":
                loads = cosine_loads(h["nodes"], ids, b["axis"], s.force)
            else:
                loads = rbe3_loads(h["nodes"], ids, point, s.force)
            for k in range(3):
                np.add.at(f[:, j], h["offset"] + 3 * ids + k, loads[:, k])
        # the motor's reaction on its flange's bolt holes, about the input's axis: only where the
        # design has a flange and the load tool puts a torque on it (the contract's motor is the
        # vehicle's: no holes, no torque)
        motor_ids = np.zeros(0, dtype=int)
        if not info.get("motor_holes") or "motor_ring_thickness" not in info["settings"] or not case.motor_torque:
            continue
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
        young = np.full(n, YOUNG)
        if STIFF:
            region = regions(info, h["nodes"], h["tets"])
            h["region"] = region
            for name, factor_ in STIFF.items():
                # "end" scales both halves' end walls; "cover.end" only the cover's.
                where, _, kind = name.rpartition(".")
                if where in ("", half):
                    young[region == kind] *= factor_
            counts = {r: int((region == r).sum()) for r in ("boss", "end", "side", "flange", "motor", "mount")}
            say(f"{half} regions {counts}; scaled {STIFF}")
        blocks.append(stiffness(h["nodes"], h["tets"], young, np.full(n, POISSON), gpu=True))
        release()
    k = sp.block_diag(blocks, format="csr")
    say(f"stiffness assembled in {time.time() - t1:.0f} s: {k.nnz:,} entries")
    # The couplings' equations, six rows each, to be eliminated: the mounts' holes held (their
    # best-fit rigid motion zero), the halves tied at each bolt.
    constraints = []
    mounts = []
    bolts = 0
    lo, hi = halves["motor_side"], halves["cover"]
    t_f = info["settings"]["flange_thickness"]
    if COUPLING == "kinematic":
        import couplings as cpl

        xyz_all = np.zeros((n_dof // 3, 3))
        for h in halves.values():
            xyz_all[h["offset"] // 3 : h["offset"] // 3 + len(h["nodes"])] = h["nodes"]
        groups = []
        for (shaft, side), (half, ids, b) in seats.items():
            groups.append({"nodes": halves[half]["offset"] // 3 + ids, "ref": (*b["axis"], 0.5 * (b["z"][0] + b["z"][1])), "name": f"the {shaft} {side} seat"})
        for m in info["mounts"]:
            h = halves[half_of(0.5 * (m["z"][0] + m["z"][1]))]
            ids = on_cylinder(h["nodes"], h["skin"], m["centre"], info["settings"]["mount_hole"] / 2, *m["z"])
            groups.append({"nodes": h["offset"] // 3 + ids, "fixed": True, "name": m["name"]})
            mounts.append((h, ids, None))
        for c in info["bolts"]:
            a = on_cylinder(lo["nodes"], lo["skin"], c, info["settings"]["bolt_hole"] / 2, z_split - t_f, z_split)
            b_ = on_cylinder(hi["nodes"], hi["skin"], c, info["settings"]["bolt_hole"] / 2, z_split, z_split + t_f)
            if len(a) < 6 or len(b_) < 6:
                continue
            groups.append({"nodes": np.r_[lo["offset"] // 3 + a, hi["offset"] // 3 + b_], "ref": (c[0], c[1], z_split), "name": f"bolt {bolts + 1}"})
            bolts += 1
        tee, tinfo = cpl.rigid_transform(xyz_all, groups)
        rigid = cpl.check_rigid(tee, xyz_all, groups, tinfo)
        if rigid > 1e-9:
            raise RuntimeError(f"the rigid couplings' transform is not rigid: {rigid:.1e}")
        eliminated = n_dof - tinfo["n_master"]
        coupling_note = (f"rigid couplings: {len(seats)} seats with their bearings' centres, {bolts} bolts each one rigid body through both "
                         f"halves, {len(mounts)} mounts' holes held")  # fmt: skip
    else:
        for m in info["mounts"]:
            h = halves[half_of(0.5 * (m["z"][0] + m["z"][1]))]
            ids = on_cylinder(
                h["nodes"], h["skin"], m["centre"], info["settings"]["mount_hole"] / 2, *m["z"]
            )
            ids = spread(h["nodes"], ids)
            rows, c = fit_rows(h["nodes"], ids, h["offset"], n_dof)
            constraints.append(rows)
            mounts.append((h, ids, c))
        for c in info["bolts"]:
            a = on_cylinder(
                lo["nodes"], lo["skin"], c, info["settings"]["bolt_hole"] / 2, z_split - t_f, z_split
            )
            b_ = on_cylinder(
                hi["nodes"], hi["skin"], c, info["settings"]["bolt_hole"] / 2, z_split, z_split + t_f
            )
            if len(a) < 6 or len(b_) < 6:
                continue
            a, b_ = spread(lo["nodes"], a), spread(hi["nodes"], b_)
            # Both holes' rigid motions read at the bolt's point on the split plane: tied there.
            point = (c[0], c[1], z_split)
            ra, _ = fit_rows(lo["nodes"], a, lo["offset"], n_dof, point)
            rb, _ = fit_rows(hi["nodes"], b_, hi["offset"], n_dof, point)
            constraints.append(ra - rb)
            bolts += 1
        tee, slaves = eliminate(constraints, n_dof)
        eliminated = len(slaves)
        coupling_note = f"distributing couplings: {len(mounts)} mounts held, {bolts} bolts joining the halves"
    k_red = (tee.T @ k @ tee).tocsr()
    k_red = (0.5 * (k_red + k_red.T)).tocsr()
    say(f"{coupling_note}; {eliminated:,} unknowns eliminated, {k_red.shape[0]:,} remain")

    t2 = time.time()
    factor = SingleFactor(k_red)
    say(f"single factor ({factor.kind}) in {factor.factor_s:.0f} s")
    columns = []
    steps_most, residual_worst = 0, 0.0
    for j in range(f.shape[1]):
        try:
            x_red, steps, residual = factor.solve(tee.T @ f[:, j])
        except RuntimeError:
            # Say where the stiffness is nearly loose before failing: the unrefined answer's
            # largest motions sit on the piece that is barely held.
            u0 = (tee @ factor.backsolve(tee.T @ f[:, j])).reshape(-1, 3)
            size = np.linalg.norm(u0, axis=1)
            for half, h in halves.items():
                part = size[h["offset"] // 3 : h["offset"] // 3 + len(h["nodes"])]
                worst = np.argsort(part)[-5:]
                say(f"not refined; {half}'s largest unrefined motions {part[worst].round(3)} mm at "
                    f"{h['nodes'][worst].round(1).tolist()}")  # fmt: skip
            factor.close()
            raise
        columns.append(tee @ x_red)
        steps_most, residual_worst = max(steps_most, steps), max(residual_worst, residual)
    u_all = np.stack(columns, axis=1)
    solve_info = {
        "solver": f"cuDSS single {factor.kind}, refined; couplings eliminated",
        "factor_s": factor.factor_s,
        "refine_steps": steps_most,
        "residual": residual_worst,
        "eliminated": int(eliminated),
    }
    say(
        f"solved in {time.time() - t2:.0f} s (at most {steps_most} refining steps, "
        f"residual {residual_worst:.1e})"
    )

    out_stem = stem if LOAD_MODEL == "rbe3" else f"{stem}_{LOAD_MODEL}"
    if SURFACE_ASKED != SURFACE_EDGE:
        out_stem += f"_surf{SURFACE_ASKED:g}"
    if STIFF:
        out_stem += "_stiff_" + "_".join(f"{k}{v:g}" for k, v in STIFF.items())
    if COUPLING != "kinematic":
        out_stem += "_rbe3"
    out_stem += SUFFIX
    result = {"stem": out_stem, "load_model": LOAD_MODEL, "couplings": COUPLING, "size_mm": size, "surface_mm": surface_used, "unknowns": n_dof, "cases": {}}
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
        # The mounts' reactions: the constraint forces K u - f, nonzero only at the coupled nodes
        # (the bolts' cancel pairwise), summed over each mount's hole as a force and a moment
        # about the origin; with the loads they must balance.
        g = k @ u - f[:, j]
        force = np.zeros(3)
        moment = np.zeros(3)
        for h, ids, _c in mounts:
            gi = g[h["offset"] + 3 * ids[:, None] + np.arange(3)[None, :]]
            force += gi.sum(axis=0)
            moment += np.cross(h["nodes"][ids], gi).sum(axis=0)
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
    try:
        if WITH_MODES:
            lumped = lumped_mass(halves, n_dof)
            m_red = (tee.T @ sp.diags(lumped) @ tee).tocsr()
            if MODE_SHAPES:
                result["modes_hz"], vecs = modes(k_red, m_red, factor, vectors=True)
                shape = (tee @ vecs).reshape(-1, 3, vecs.shape[1])
                np.savez_compressed(OUT / f"fe_{out_stem}_modes.npz",
                                    hz=np.asarray(result["modes_hz"]), node_mass=lumped[0::3].astype(np.float32),
                                    magnitude=np.sqrt((shape**2).sum(axis=1)).astype(np.float16))  # fmt: skip
                del shape, vecs
            else:
                result["modes_hz"] = modes(k_red, m_red, factor)
        else:
            result["modes_hz"] = []
    finally:
        factor.close()
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
    (OUT / f"fe_{out_stem}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    np.savez_compressed(
        OUT / f"fe_{out_stem}.npz",
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
