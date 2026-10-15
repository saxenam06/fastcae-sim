"""PROTOTYPE (LOP-17) - an optimisation's outcome drawn as the housing's CAD, the way generative
design draws its outcomes (Fusion 360 in Virostko et al. 2026: the outcome's body, its preserve
geometry exact; docs/research/2026-10-10-generative-design-gear-wheels.md).

The engineer, 10 October 02:12: "I want to see in CAD the new housing design based upon this".
The optimiser's field is the shape; nothing of the generator's massing is drawn:
1. **the organic body,** per half: the field's metal with the gear rooms filled (so that only the
   outside comes from the field), carried two voxels past the split, smoothed a little, its 0.5
   level found by marching cubes, smoothed by Taubin's filter, remeshed by gmsh into even
   triangles of about 6 mm, sewn into a solid, and cut flat at the split;
2. **the interfaces exact,** as the optimiser froze them (`topo_free.py`): the motor's ring with
   its face and bore, the mounts' bosses with their ends, each bearing's seat ring with its
   shoulder, a boss at each bolt the body reaches; each drawn a little larger than its voxels, so
   that no exact face runs along the smoothed one (CLAUDE.md's sliver rule);
3. **the inside exact:** the cup's cavity (`cup.py`: every room from its far end to the split),
   the seats bored to their size, each bearing's path in from the split, the seals' bores, the
   bolts', mounts' and motor's holes; and what the optimiser kept clear (the motor beyond its
   flange, the half-shafts' joints, the mounts' ends) cut flat.
Written as grammar.py's are (`data/first_loop/<stem>_<half>.brep/.step`, `<stem>.json` with the
layout's bearings, bolts, mounts and the faces' names), so castable.py, fe.py, grade.py and look.py
judge it unchanged. The contract's process is printed sand moulds, which need no draft; the
optimiser's casting filter (route "cast") kept every column of each half one piece along the pull.

Run: .venv/Scripts/python.exe prototypes/first_loop/outcome_cad.py <run stem> <design stem>
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import cup as cupmod  # noqa: E402
import field_body as fb  # noqa: E402  (closed outlines, drafted lofts)
import grammar  # noqa: E402  (meshable, say, OUT)
import shell as convex  # noqa: E402
from zenryx.contract.validate import load_and_validate  # noqa: E402
from zenryx.domains.gearbox.chain import complete_chain  # noqa: E402
from zenryx.domains.gearbox.forces import value_in  # noqa: E402
from zenryx.geometry.solids import cylinder, fuse  # noqa: E402

OUT = grammar.OUT
LAYOUT = "grammar4"  # the layout the optimiser was given (its bolts, mounts and motor's holes)
MARGIN = 6.0  # mm, an exact interface stands this far past the voxels it replaces
SOCKET = (16.0, 25.0)  # mm, the room over a bolt's head for a hex key (an M8 cap head is Ø13): Ø22 for 60 mm thinned the walls beside the bolts (02:59)
# mm past a mount's boss, the room kept clear at its ends: past the column's engulf (MARGIN) by
# the smoothing's reach (±3 mm) and more. At 4 mm, inside the engulf, its cuts left a 2 mm ring at
# each end of the mount (outcome_split_7.73, 05:40).
MOUNT_ROOM = 12.0
REMESH = 6.0  # mm, the organic surface's triangles
# The organic surface's rungs, tried in turn until it is watertight and its solid valid: (blur in
# voxels, contour, triangles in mm, closing in voxels). A wider closing comes before a heavier blur
# (`organic_half`); finer triangles did not help (6, 5 and 4 mm all stayed open, 07:22).
LADDER = ((0.6, 0.45, 6.0, 1), (0.6, 0.45, 6.0, 2), (0.65, 0.45, 6.0, 2), (0.7, 0.5, 6.0, 1), (0.85, 0.5, 6.0, 1))
DRAFT = 0.0  # deg, a lean on the organic walls: off (3° along each vertex normal folded the motor side, 2,037 self-crossing faces, 03:13)
say = grammar.say


def field_of(stem: str) -> dict:
    z = np.load(OUT / f"{stem}.npz")
    n, lo, h = z["n"].astype(int), z["lo"].astype(float), float(z["h"])
    rho = np.zeros(int(np.prod(n)))
    rho[z["elem"][z["frozen"].astype(bool)]] = 1.0
    rho[z["elem"][z["free_e"]]] = np.maximum(rho[z["elem"][z["free_e"]]], z["phys"])
    return {"rho": rho.reshape(n), "n": n, "lo": lo, "h": h, "k_split": int(z["k_split"])}


def rooms_mask(f: dict, all_rooms: list[dict], z_split: float, half: str) -> np.ndarray:
    """The voxels inside the half's cup (every room's footprint from its far end to the split)."""
    n, lo, h = f["n"], f["lo"], f["h"]
    xs, ys, zs = (lo[i] + h * (np.arange(n[i]) + 0.5) for i in range(3))
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    inside = np.zeros(tuple(n), bool)
    for p in cupmod.pieces(all_rooms, z_split, half):
        span = (Z >= p["far"]) & (Z <= z_split) if half == "motor_side" else (Z <= p["far"]) & (Z >= z_split)
        inside |= span & (np.hypot(X - p["axis"][0], Y - p["axis"][1]) <= p["r"])
    return inside


def organic_half(f: dict, half: str, filled: np.ndarray, work: Path) -> cq.Shape:
    """The half's metal (the rooms filled) as one smooth solid, carried past the split: the
    smoothed field's 0.5 level by marching cubes (watertight), Taubin's smoothing, then
    pymeshlab's isotropic remeshing into even triangles of about REMESH mm. Marching cubes alone
    leaves slivers beside fat triangles; gmsh could not reparametrise a surface of genus 18 to
    remesh it, and VTK's surface nets were not watertight (02:31)."""

    from scipy.ndimage import binary_closing, generate_binary_structure

    lo, h, ks = f["lo"], f["h"], f["k_split"]
    metal0 = np.maximum(f["rho"], filled.astype(float)) >= 0.5

    def prepared(closing: int) -> np.ndarray:
        """The half's metal closed over `closing` voxels, carried past the split.
        A morphological closing first: metal touching only along an edge or at a corner pinched
        the contour into edges shared by four faces, the surface was not watertight, and the
        cover's body came out invalid and broke in its booleans (outcome_split_7.73, 04:48). Over
        two voxels it also merges two sheets a voxel apart into one plate: across such a slot the
        blurred contour's sheets met, and no mend closed them (the robust field's cover, 07:27)."""
        metal = binary_closing(np.pad(metal0, closing), structure=generate_binary_structure(3, 1), iterations=closing)
        rho = metal[closing:-closing, closing:-closing, closing:-closing].astype(float)
        if half == "cover":
            rho[:, :, :ks] = 0.0
            for k in (ks - 1, ks - 2):
                rho[:, :, k] = rho[:, :, ks]  # carried past the split, then cut flat there
        else:
            rho[:, :, ks:] = 0.0
            for k in (ks, ks + 1):
                rho[:, :, k] = rho[:, :, ks - 1]
        return rho

    # A lighter blur first, contoured a little under half, so a wall one voxel thick keeps more of
    # its voxel (blurred over 0.7 and contoured at 0.5, a 5 mm skin came out 2.5-3.5 mm,
    # outcome_run3, 02:47); then heavier ones, until the surface is watertight and its solid valid.
    # Finer triangles before a heavier blur: the remesher's 6 mm triangles relax through each
    # other where two sheets of metal lie a voxel apart, and the heavier blur erases the field's
    # thin members. The robust field's cover fell to 0.7/0.5, which alone reads 4.17 × its line
    # in the optimiser's model against 1.76 at 0.6/0.45 (`voxel_vs_fe.py`, 07:18).
    for sigma, level, length, closing in LADDER:
        rho = prepared(closing)
        tm = _surface(rho, lo, h, ks, sigma, level, half, length)
        solid = _sewn(tm, work / f"{half}_organic.stl") if tm.is_watertight else None
        ok = solid is not None and solid.isValid() and solid.Volume() > 0
        e = tm.vertices[tm.faces]
        sq = sum((np.linalg.norm(e[:, i] - e[:, (i + 1) % 3], axis=1) ** 2) for i in range(3))
        shape_q = 4.0 * math.sqrt(3.0) * tm.area_faces / sq  # 1 equilateral, 0 flat
        say(f"{half}: closing {closing}, blur {sigma}, contour {level}, triangles of {length:g} mm: {len(tm.faces):,} triangles, watertight {tm.is_watertight}, shape worst {shape_q.min():.2f}"
            + (f"; the organic body {len(solid.Faces()):,} faces, {abs(solid.Volume()) / 1e3:.0f} cm3, valid {solid.isValid()}" if solid is not None else ""))  # fmt: skip
        if ok:
            return solid
    raise RuntimeError(f"{half}: no watertight, valid organic body at any setting")


def _surface(rho, lo, h, ks, sigma, level, half, length=None):
    """The field's contour at `level` after a blur over `sigma` voxels, smoothed by Taubin's
    filter, remeshed into even triangles of about `length` mm (by default `REMESH`), its
    self-crossings and non-manifold edges mended."""
    import pymeshlab
    import pyvista as pv
    import trimesh
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes

    field = gaussian_filter(np.pad(rho, 2), sigma=sigma)
    verts, faces, _, _ = marching_cubes(field, level=level, spacing=(h, h, h))
    verts += lo - 2 * h + 0.5 * h
    tm = trimesh.Trimesh(verts, faces, process=True, validate=True)
    tm = max(tm.split(only_watertight=False), key=lambda m: m.area)
    smooth = pv.wrap(tm).smooth_taubin(n_iter=40, pass_band=0.05)
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(np.asarray(smooth.points), smooth.faces.reshape(-1, 4)[:, 1:]))
    length = REMESH if length is None else length
    ms.meshing_isotropic_explicit_remeshing(iterations=8, targetlen=pymeshlab.PureValue(length), featuredeg=60.0)
    for attempt in range(3):
        # A fold where two sheets of the smoothed field touch: its faces taken out, the edges and
        # vertices left non-manifold mended, the hole closed and that patch remeshed. A mend that
        # fails leaves the surface as it was, said; the checks after judge it.
        ms.compute_selection_by_self_intersections_per_face()
        crossed = ms.current_mesh().selected_face_number()
        if not crossed:
            break
        before = ms.current_mesh_id()
        ms.add_mesh(ms.current_mesh(), "kept")  # a copy to return to
        try:
            ms.set_current_mesh(before)
            ms.meshing_remove_selected_vertices_and_faces()
            ms.meshing_repair_non_manifold_edges()
            ms.meshing_repair_non_manifold_vertices()
            ms.meshing_close_holes(maxholesize=400)
            ms.meshing_isotropic_explicit_remeshing(iterations=4, targetlen=pymeshlab.PureValue(length), featuredeg=60.0)
            say(f"{half}: {crossed} self-crossing faces taken out and the holes closed (try {attempt + 1})")
        except pymeshlab.PyMeshLabException as error:
            say(f"{half}: {crossed} self-crossing faces could not be mended ({str(error).splitlines()[0]})")
            ms.set_current_mesh(before + 1)
            break
    try:
        ms.meshing_repair_non_manifold_edges()
        ms.meshing_repair_non_manifold_vertices()
        ms.meshing_close_holes(maxholesize=400)
    except pymeshlab.PyMeshLabException:
        pass
    m = ms.current_mesh()
    tm = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)
    if not tm.is_watertight:
        # Said, and left to the ladder's next rung (a wider closing). Closing every hole, even by a
        # patch crossing itself, never made such a surface watertight (the robust field's cover,
        # 07:27), and on the TOBS field's cover pymeshlab crashed in it (exit 139, 11:56).
        faces_per_edge = np.bincount(tm.edges_unique_inverse, minlength=len(tm.edges_unique))
        say(f"{half}: blur {sigma}: not watertight, {int((faces_per_edge == 1).sum())} open edges and {int((faces_per_edge > 2).sum())} shared by more than two faces")
    trimesh.repair.fix_normals(tm)
    return tm


def _sewn(tm, path: Path):
    """The watertight surface sewn into a solid, or None."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
    from OCP.ShapeFix import ShapeFix_Solid
    from OCP.StlAPI import StlAPI_Reader
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS, TopoDS_Shape

    tm.export(str(path))
    shape = TopoDS_Shape()
    StlAPI_Reader().Read(shape, str(path))
    sew = BRepBuilderAPI_Sewing(1e-3)
    sew.Add(shape)
    sew.Perform()
    exp = TopExp_Explorer(sew.SewedShape(), TopAbs_SHELL)
    shells = []
    while exp.More():
        shells.append(TopoDS.Shell_s(exp.Current()))
        exp.Next()
    if not shells:
        return None
    shells.sort(key=lambda s_: -cq.Shape.cast(s_).Area())
    fix = ShapeFix_Solid(BRepBuilderAPI_MakeSolid(shells[0]).Solid())
    fix.Perform()
    return cq.Shape.cast(fix.Solid())


FORM = "organic"  # "organic": the smoothed field's facets; "relief": exact surfaces over the filled columns (its smoothing spread the ribs into hills: the cover 9.9 kg, 03:20); "skin": below

# --- LOP-20: the skin form -------------------------------------------------------------------------
# The engineer, 10 October 18:31: "how it was done in the pictures, from the organic design to the
# skin and then the nice housing shape" (SEW's six steps: the outer limit, the plane cuts, the
# wall's offset, a new skin over the members, the housing). The skin is the cup's own exact wall,
# the interfaces are the trade's, and of the field only what the optimiser placed is drawn: the
# organic form drew the whole field, its 4 mm skin a whole voxel thick (6-10 mm of metal), which
# made one thick envelope 2.7-4 kg over the budget (outcome_compliance_6mm, 10mm).
# mm, the skin form's grid; (LOP-30, 14 October) LOOP_DRAW_FINE=<mm> draws finer, a spline run's fields read between the
# optimiser's points (`spline_members`): on 2 mm a 4 mm round is two facets
FINE = float(os.environ.get("LOOP_DRAW_FINE", "2.0"))
# The drawing keeps the optimiser's mass (the engineer, 10 October 19:46: "why is the CAD heavier
# than the optimisation?"; measured on outcome_skin_6mm_contract, 9.59 kg against 7.73: the
# members read at 0.40-0.45, 1-2 mm fatter each side, +0.84 kg; the wall drawn 5 mm, modelled 4,
# +0.76 kg; the exact cavity against the voxels', +0.34 kg). So the wall is the model's and a
# little for the facets' wander, the surface is read at 0.5 (which keeps a member's thickness),
# and the members are read at the level that gives back the optimiser's mass (`keep_mass_level`).
SKIN_WALL = 4.4  # mm, the skin's wall as drawings before 11 October drew it: the model's (the contract's least, 4 mm) and 0.4 for the facets
# Since 11 October (the engineer, 10 October 23:48-23:55: "four mm is four mm"; "the 4 mm wall should
# be drawn exactly in CAD, as its surface is known from the contract"): what the contract fixes is
# drawn exact (`exact_shell`: the cup's wall at the least wall, the split flange's sealing land with
# the bolts' bosses on it, the mounts), and only the optimiser's members are smoothed. On the
# smoothing's grid those parts stand `SKIN_BURY` under their exact faces, so the members' roots
# blend into them there and the smooth surface never grazes an exact face.
SKIN_BURY = 2.0  # mm
PROUD = 3.0  # mm, a bearing boss's face past its end wall (grammar.py's 0.5·δ)
FINE_MARGIN = float(os.environ.get("LOOP_FINE_MARGIN", "2.0"))  # mm, a kept-clear space emptied this far past its boundary before the blur
FLANGE_LAND = 10.0  # mm from the inside's edge: the joint's sealing land (the wall and a sealant's bead), the bolts' bosses on it
MEMBER_BLUR = 0.5  # voxels: the members made fair on their own grid
MEMBER_LEVEL = 0.5  # the level the fair members are read at when the drawing does not keep the mass: their voxels' own size
# The highest level the mass is kept at: a member one voxel thick, blurred over half a voxel, is
# 0.72 of its voxel thick there (4.3 mm at 6 mm), still over the contract's least wall
MEMBER_LEVEL_MOST = 0.57
# Read the members at the level that gives back the optimiser's mass: off since 10 October 22:15.
# Kept, it read outcome_skin_6mm_both's at 0.569, thinner than optimised, and FE's tilt came out
# 1.76 against its field's 1.24; now the members are drawn as optimised (0.5), and the optimiser is
# given the drawing's fixed extras less (about 0.5 kg) so the drawing lands at the target.
KEEP_MASS = False
DRAW_BOSSES = False  # the trade's bearing bosses (1.25·D + 10 mm) drawn on top of the field: not in the agreed set-up
# mm, the roots' fillet (LOP-23; `skin_metal`): 4 mm since 11 October 09:20, the trade's R 1-1.25 x
# the thinner leg at a 4 mm wall (outcome_env24_6.5kg drawn with it: 7.24 kg against 6.98, beds 33.5
# against 33.1 µm, tilt 0.71 against 0.70); LOOP_ROOT_FILLET=0 redraws a design as it was before
ROOT_FILLET = float(os.environ.get("LOOP_ROOT_FILLET", "4"))
# (LOP-29, the engineer 13 October 20:12: "do option 1") the drawing keeps every metal cube of the optimiser's field, and the
# drawn halves are checked to hold every one (a drawing that loses more than KEEP_LOST_MOST of them stops before FE)
KEEP_CUBES = os.environ.get("LOOP_KEEP_CUBES", "1") != "0"
# (LOP-29, 14 October 01:14) the kept cubes drawn smooth: their signed distance blurred over this many mm (flat faces stay,
# the steps round), a 2.5 mm ball round each cube's centre always inside, so every cube's centre stays in the drawn half
SMOOTH_KEEP = float(os.environ.get("LOOP_SMOOTH_KEEP", "0"))
KEEP_LOST_MOST = 0.005
# (LOP-29, 13 October 20:50) an empty start's exact walls and interfaces drawn with their faces at their true place: their
# cells' copy a cell inside the faces, the faces themselves a ramp in the contour (`exact_walls.ramp`); a 4 mm wall had
# come out 3-5 mm on the 2 mm cells (4.9 under the intermediate gear room tipped that seat, `lop29_keep`)
EXACT_FACES = os.environ.get("LOOP_EXACT_FACES", "1") != "0"
# Each half drawn as a height field along its pull (`height_field`, LOP-23): off unless
# LOOP_HEIGHT_FIELD=1. On outcome_ribsfieldfins24_6.3kg's field (11 October 09:50-09:58) the body
# came out castable (0.02-0.03 % undercut, against 1.05 and 0.37 %), but the mounts' lugs, with a
# bracket's room above and below, are runs that never reach the split: folded in, the mounts came
# off; drawn apart as the grid's contour, their junctions leaned 1-3° (1.43 % undercut) and FE's
# coarsening folded the surface. The lugs want their own castable form (open).
HEIGHT_FIELD = os.environ.get("LOOP_HEIGHT_FIELD", "0") != "0"
# Each member drawn clean (LOP-23, `clean_members.py`; the engineer, 11 October 14:36-14:38: "still
# very lumpy... not the quality of design"): the field's members as smoothed ribs of production
# widths with rounded tops, broad parts as pads, tiny islands dropped, in place of their voxels'
# shape. Off unless LOOP_CLEAN_MEMBERS=1; LOOP_CLEAN_MEMBERS=ribs builds the field's layout as clean
# ribs instead (`clean_ribs.py`: its centre-lines as fair curves, one width and height a rib).
CLEAN_MEMBERS = os.environ.get("LOOP_CLEAN_MEMBERS", "0")
# The members' surface smoothed before it joins the exact shell (LOP-23, 11 October 15:55: the
# published reconstructions, Synera's, INTES's (Wagner & Wulf, NAFEMS 2023) and AMRTO's (Ren et al.
# 2025), all smooth the optimiser's own shape, then fit it): Taubin's smoothing, this many passes
# (it keeps the volume where Laplace's shrinks it). Off (0) unless LOOP_SMOOTH is set.
SMOOTH_PASSES = int(os.environ.get("LOOP_SMOOTH", "0"))
# The members' surface from the metal's signed distance smoothed over this many mm (`mesh_route.
# contour_sdf`; Ježek et al. 2025) in place of the cells' blur; off (0) unless LOOP_SDF is set.
SDF_SIGMA = float(os.environ.get("LOOP_SDF", "0"))
# The surface smooth and faithful (LOP-27, `mesh_route.faithful`; Ježek et al. 2025): the plain contour's
# distance sampled this many mm apart (the optimiser's voxel), interpolated by Gaussians, the volume kept;
# off (0) unless LOOP_FAITHFUL is set
_faithful = (os.environ.get("LOOP_FAITHFUL", "0") or "0").split(":")
FAITHFUL = float(_faithful[0])
FAITHFUL_RIDGE = float(_faithful[1]) if len(_faithful) > 1 else 0.0  # "<mm>:<ridge>": a damped fit, not an exact interpolation
# An empty start's least walls drawn from the exact inside, smooth, in the same field as the optimiser's metal
# (LOP-27, `exact_walls.py`; the engineer, 12 October 21:10): off unless LOOP_EXACT_WALLS is set
EXACT_WALLS = os.environ.get("LOOP_EXACT_WALLS", "0") != "0"
# An empty start's outer surface from the optimiser's own continuous heights (LOP-28, 13 October 00:35; `continuous_depth`):
# each column's top, its base plus its height before the voxels round it to whole 4 mm, laid between the columns' centres
# and drawn by the height-field drawing (`height_field`), so the staircase of whole voxels goes (`roughness.py`: the
# wrinkles are the optimiser's, the staircase the voxels'). Off unless LOOP_HEIGHT_DRAW is set.
HEIGHT_DRAW = os.environ.get("LOOP_HEIGHT_DRAW", "0") != "0"
# Approach 2's generator B (LOP-25, 12 October): the members rebuilt along their skeleton in plan, each a smooth
# member of variable width and its own run along the pull (`skeleton_members.py`); "scale:prune mm:cap mm"
SKELETON = tuple(float(v) for v in os.environ["LOOP_SKELETON"].split(":")) if os.environ.get("LOOP_SKELETON") else None
# The shell and a volume run's features drawn as one smooth solid in production's forms (LOP-24/25, 12 October 02:00;
# `implicit_draw.py`): "rib mm:fillet mm:round mm:grid mm"
IMPLICIT = tuple(float(v) for v in os.environ["LOOP_IMPLICIT"].split(":")) if os.environ.get("LOOP_IMPLICIT") else None
# Production's parts (LOP-26, Refine: `parts.py`, a reading or a run's optimised parts) drawn on the exact, filleted shell
# as one smooth solid (`implicit_draw.parts_body`): the parts file; its fillet, round and grid as LOOP_IMPLICIT's or 4:3:1.25
PARTS = os.environ.get("LOOP_PARTS") or None
# A member-like free run's members drawn clean (LOP-25, the plan's generator B: `clean_draw.py`, `implicit_draw.members_body`)
CLEAN = os.environ.get("LOOP_CLEAN", "0") != "0"
HEIGHT_SIGMA = 1.0  # cells (`FINE`): the depths smoothed in plan
CARRY = 3.0  # cells past the split, cut flat after (as the grid's contour carried them)
# (blur in cells, contour, triangles in mm); the finer triangles where 5 mm ones crossed themselves over
# thin members and no blur closed the surface (outcome_skin_6mm_onerun's motor side, 11 October 01:27)
SKIN_LADDER = ((1.0, 0.5, 5.0), (1.25, 0.5, 5.0), (1.5, 0.5, 5.0), (1.25, 0.5, 3.5), (1.25, 0.5, 2.5))


def protected_voxels(stem: str, layout: dict) -> np.ndarray:
    """(LOP-28) The run's voxels the protected interfaces cover (`exact_walls.interface_density`, grown by half a voxel): round each bore out
    to its boss along its seat, the two layers at the split within the sealing land and the bolts' bosses, the mounts. Their
    frozen voxels are drawn only under the run's metal; every other frozen voxel (a seat's ring past its boss) is drawn."""
    z = np.load(OUT / f"{stem}.npz")
    n, lo, h, ks = z["n"].astype(int), z["lo"].astype(float), float(z["h"]), int(z["k_split"])
    X, Y, Z = np.meshgrid(*(lo[i] + h * (np.arange(n[i]) + 0.5) for i in range(3)), indexing="ij")
    s, fl = layout["settings"], layout["flange"]
    out = np.zeros(tuple(n), bool)
    z_split = float(layout["z"]["split"])
    wall = float(s["wall"])
    for b in layout["bearings"]:  # each boss's tower, from a wall past its seat's outer end to the split (`interface_density`)
        r = np.hypot(X - b["axis"][0], Y - b["axis"][1])
        span = (Z >= b["z"][0] - wall) & (Z < z_split) if b["side"] == "-z" else (Z >= z_split) & (Z <= b["z"][1] + wall)
        out |= (r <= float(b["boss_r"]) + h / 2) & span
    split = np.zeros(tuple(n), bool)
    split[:, :, max(ks - 1, 0) : ks + 1] = True
    d_out = np.min([np.hypot(X - c["centre"][0], Y - c["centre"][1]) - c["radius"] for c in fl["outer"]], axis=0)
    near_land = d_out <= h / 2
    for c in layout["bolts"]:
        near_land |= np.hypot(X - c[0], Y - c[1]) <= s["bolt_boss"] / 2 + h / 2
    out |= near_land & split
    for m in layout["mounts"]:
        out |= (np.hypot(X - m["centre"][0], Y - m["centre"][1]) <= s["mount_diameter"] / 2 + h / 2) & (Z >= m["z"][0] - h / 2) & (Z <= m["z"][1] + h / 2)
    return out


def members_of(stem: str, all_frozen: bool = False, protected: np.ndarray | None = None) -> dict:
    """The run's placed metal (its free voxels at 0.5 or more) on its own grid, each member with
    the frozen voxels it stands on (a face away), so that drawn on a thinner skin it still
    reaches the wall: carried down through its own skin voxel, never spread along the skin. With
    `all_frozen` (the empty start, LOP-27: no exact shell to stand on) every frozen voxel too: the
    seats' rings, the mounts and the bolts' bosses are the field's metal like the rest."""
    from scipy.ndimage import binary_dilation, generate_binary_structure

    z = np.load(OUT / f"{stem}.npz")
    n = z["n"].astype(int)
    placed = np.zeros(int(np.prod(n)), bool)
    frozen = np.zeros(int(np.prod(n)), bool)
    placed[z["elem"][z["free_e"]]] = z["phys"] >= 0.5
    frozen[z["elem"][z["frozen"].astype(bool)]] = True
    placed, frozen = placed.reshape(n), frozen.reshape(n)
    # A run on production's rib network (LOP-23): its filled pieces drawn clean (`network_draw`),
    # and only its corridors' metal (the mounts' arms) drawn as the field's own
    import network_draw

    net = network_draw.pieces(stem)
    if net is not None:  # the arms keep their metal a voxel into the network, where they root
        placed &= binary_dilation(net["corridor"], structure=generate_binary_structure(3, 1))
    under = frozen if all_frozen else frozen & binary_dilation(placed, structure=generate_binary_structure(3, 1))
    if protected is not None:  # LOP-28: every frozen voxel but those the exact interfaces cover, which only under the metal
        under = (frozen & ~protected) | (frozen & protected & binary_dilation(placed, structure=generate_binary_structure(3, 1)))
    return {"placed": placed | under, "network": net}


def cube_fidelity(placed: np.ndarray, f: dict, halves: dict, organic: dict, parts: dict, z_split: float, gate: bool = True) -> dict:
    """(LOP-29) How many of the run's metal cubes (`placed`, on its own grid) the drawn halves hold, each cube's centre tested
    inside its half's drawn mesh. A cube not held is the drawing's loss, or the optimiser's metal in a space the drawing keeps
    clear: held before the exact cuts (the contract's holes, bores, exits, the bolts' sockets), or with a part in a kept-clear
    space (`skin_parts`' `clear`: the exits, the vehicle's brackets, the sockets, each FINE_MARGIN wider). More than
    KEEP_LOST_MOST of either stops the drawing, as FE would judge less metal than the optimiser counted (`lop29_modes` lost
    10 %, 13 October 19:58); the second is the set-up's to fix, and LOOP_KEEP_CLEAR_OK=1 draws a run made before anyway."""
    import pyvista as pv

    import mesh_route as mr

    def inside(body, pts: np.ndarray) -> np.ndarray:
        tm = mr.to_trimesh(body)
        surf = pv.PolyData(np.asarray(tm.vertices), np.hstack([np.full((len(tm.faces), 1), 3), np.asarray(tm.faces)]).ravel())
        sel = pv.PolyData(pts).select_enclosed_points(surf, tolerance=1e-6, check_surface=False)  # as `model_vs_fe.inside_drawing`
        return np.asarray(sel["SelectedPoints"]).astype(bool)

    from scipy.ndimage import label

    h, lo = float(f["h"]), np.asarray(f["lo"], float)
    ijk = np.argwhere(placed)
    # the run's own loose metal: placed cubes outside their half's largest face-joined piece of metal (the fixed cubes too)
    metal = np.asarray(f["rho"]) >= 0.5
    joined = np.zeros(metal.shape, bool)
    ks_ = int(f["k_split"])
    for sl in (np.s_[:, :, :ks_], np.s_[:, :, ks_:]):
        lab, k = label(metal[sl])
        if k:
            sizes = np.bincount(lab.ravel())
            sizes[0] = 0
            joined[sl] = lab == int(np.argmax(sizes))
    loose_cube = ~joined[tuple(ijk.T)] if len(ijk) else np.zeros(0, bool)
    centres = lo[None, :] + h * (ijk + 0.5)
    offs = 0.25 * h * np.array([[a, b, c] for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)], float)  # a point in each octant of a cube
    own, clear, loose = 0, 0, 0
    for half, body in halves.items():
        mine = centres[:, 2] < z_split if half == "motor_side" else centres[:, 2] >= z_split
        if not mine.any():
            continue
        pts = centres[mine]
        lost = ~inside(body, pts)
        loose_here = lost & loose_cube[mine]
        loose += int(loose_here.sum())
        lost &= ~loose_here
        if not lost.any():
            continue
        kept_clear = inside(organic[half], pts[lost])
        grid = parts[half]["clear"]
        lo_f = np.asarray(parts[half].get("lo", lo), float)  # (LOP-30) the half's own fine grid (a spline run's is shifted)
        for o in offs:
            idx = np.floor((pts[lost] + o - lo_f) / FINE).astype(int)
            ok = np.all((idx >= 0) & (idx < np.asarray(grid.shape)), axis=1)
            kept_clear[ok] |= grid[tuple(idx[ok].T)]
        clear += int(kept_clear.sum())
        own += int((~kept_clear).sum())
    n = max(len(centres), 1)
    out = {"cubes": int(len(centres)), "lost": own, "lost_share": own / n, "kept_clear": clear, "kept_clear_share": clear / n,
           "loose": loose, "loose_share": loose / n}
    say(f"the drawing holds {len(centres) - own - clear - loose:,} of the run's {len(centres):,} metal cubes: {own:,} lost by the drawing "
        f"({100 * out['lost_share']:.2f} %), {clear:,} in spaces it keeps clear ({100 * out['kept_clear_share']:.2f} %), "
        f"{loose:,} loose in the run's own field, joined to nothing ({100 * out['loose_share']:.2f} %)")  # fmt: skip
    if not gate:  # (LOP-30) a spline run: its cubes are a share each (the smooth outline's), not whole: read, not a gate
        return out
    if out["lost_share"] > KEEP_LOST_MOST:
        raise SystemExit(f"the drawing lost {own:,} of the run's {len(centres):,} metal cubes: FE would judge less than the optimiser placed")
    if out["kept_clear_share"] > KEEP_LOST_MOST and os.environ.get("LOOP_KEEP_CLEAR_OK", "0") == "0":
        raise SystemExit(f"the optimiser placed {clear:,} of its {len(centres):,} metal cubes in spaces the drawing keeps clear (the contract's "
                         "holes and exits, the vehicle's brackets, the bolts' sockets): the set-up must keep them clear")  # fmt: skip
    return out


def boss_r(b: dict) -> float:
    """A bearing boss's outside radius: the trade's 1.25·D + 10 mm (grammar.py's, ITMO 2014)."""
    return (grammar.GRAMMAR["boss_k"] * b["D"] + grammar.GRAMMAR["boss_c"]) / 2


def spline_cols_of(run: str) -> dict | None:
    """(LOP-30) A spline run's columns and the fields each read (`topo.Voxels.spline_columns`, saved as `spl_*`), or None.
    Since 14 October 19:15 the outline is saved at its points (`spl_sub_phi`); a run saved before (one value a column,
    `spl_phi`) is refused, not drawn from its cubes. (Until 20:55 this looked for `spl_phi` alone, so every spline run
    saved since 19:15 was drawn from its cubes, silently: `spline_example` among them.)"""
    z = np.load(OUT / f"{run}.npz")
    if "spl_sub_phi" in z.files:
        out = {k[4:]: z[k] for k in z.files if k.startswith("spl_")}
        if os.environ.get("LOOP_DRAW_SECTION") == "0":  # (a check) drawn without the section rule's round and fillets
            out.pop("sub_a", None)
            out.pop("round_mm", None)
        return out
    if "spl_phi" in z.files:
        raise ValueError(f"{run} is a spline run saved before 14 October 19:15 (its outline a value a column): the drawing reads points")
    return None


def voxel_cols_as_spline(run: str, sigma_mm: float, round_mm: float) -> dict:
    """(LOP-30; the engineer, 15 October 12:21: "can we do something like in voxel space also") A plain height-field run
    (`--height-field`, no spline) drawn as a spline run is (`spline_members_pts`): no new optimisation, the run's own
    columns and heights. Each column's height is its cubes' densities summed along it (the metal the model holds); the
    outline in plan is where a column holds metal, blurred over `sigma_mm` among the columns of its half, level and family
    (each a group of its own, so nothing bleeds across the cup's wall) and read at its middle: the 4 mm squares' staircase
    a smooth curve, a member two columns wide still two columns wide. An empty column's height is carried from the nearest
    metal (NaN here), so a member's top does not droop to its empty neighbours. The free edges rounded `round_mm`."""
    from scipy.ndimage import gaussian_filter

    import topo

    z = np.load(OUT / f"{run}.npz")
    n = np.asarray(z["n"], int)
    elem, frozen, free_e = z["elem"], z["frozen"].astype(bool), z["free_e"]
    k_split, h = int(z["k_split"]), float(z["h"])
    kind = np.full(int(np.prod(n)), -1, np.int8)
    kind[elem] = 0
    kind[elem[frozen]] = 1
    col, pos, pts, layer = topo.height_columns(kind, n, k_split, elem, free_e)
    n_cols = len(pts)
    kz = elem[free_e] % int(n[2])
    base = np.full(n_cols, -1, np.int64)
    base[col[pos == 0]] = kz[pos == 0]
    half = (np.asarray(layer, np.int64) // 10_000).astype(np.int8)
    ii, jj = pts[:, 0].astype(int), pts[:, 1].astype(int)
    grid = kind.reshape(tuple(n))  # each column's family as `topo.spline_setup` reads it
    off = np.concatenate([np.zeros(tuple(n[:2]) + (1,), np.int64), np.cumsum(grid < 0, axis=2)], axis=2)
    k0 = np.where(half == 1, k_split, base + 1)
    k1 = np.where(half == 1, base, k_split)
    on_split = (off[ii, jj, np.maximum(k1, k0)] - off[ii, jj, k0]) == 0
    t = np.bincount(col, weights=np.asarray(z["phys"], float), minlength=n_cols)  # voxels of metal a column
    # half a cube of metal or more: a run one cube long (above a mount's room, under the land) holds a plate one cube thick,
    # part of a bracket's path (at more than one cube, mount-1's plate and neck to its lug were lost, `lw8s_fine`)
    metal = t >= 0.5
    # each plan cell's stack of columns in the drawing's order (`spline_members_pts`: from the split outward)
    lay_of = np.zeros(n_cols, np.int64)
    for hf_ in (0, 1):
        sel = np.flatnonzero(half == hf_)
        seen: dict = {}
        for k in sel[np.argsort(-base[sel] if hf_ == 0 else base[sel], kind="stable")]:
            key = (ii[k], jj[k])
            lay_of[k] = seen.get(key, 0)
            seen[key] = lay_of[k] + 1
    q = 2
    sa, sb = (v.ravel() for v in np.meshgrid(np.arange(q), np.arange(q), indexing="ij"))
    sub_col = np.repeat(np.arange(n_cols), q * q)
    sub_ij = np.column_stack([q * ii[sub_col] + np.tile(sa, n_cols), q * jj[sub_col] + np.tile(sb, n_cols)])
    sub_phi = np.zeros(len(sub_col))
    sig = sigma_mm / (h / q)
    # averaged over the group's own columns alone (normalised), so a member reaching the design space's edge keeps its
    # width there. Tried (15 October 12:34-12:40): the shell's fixed metal read as metal pulled the empty columns beside
    # it inside the outline at their neighbours' height (pins round every rim, `lw8s2_fine`); everything outside but the
    # shell read as empty took 0.09 kg off and changed nothing seen (`lw8s3_fine`)
    shape = (q * int(n[0]), q * int(n[1]))
    for key in {(int(a), int(b), bool(c)) for a, b, c in zip(half, lay_of, on_split, strict=True)}:
        mine = (half == key[0]) & (lay_of == key[1]) & (on_split == key[2])
        pts_m = mine[sub_col]
        present = np.zeros(shape)
        filled = np.zeros(shape)
        present[sub_ij[pts_m, 0], sub_ij[pts_m, 1]] = 1.0
        filled[sub_ij[pts_m, 0], sub_ij[pts_m, 1]] = metal[sub_col[pts_m]].astype(float)
        num, den = gaussian_filter(filled, sig), gaussian_filter(present, sig)
        at = (sub_ij[pts_m, 0], sub_ij[pts_m, 1])
        sub_phi[pts_m] = num[at] / np.maximum(den[at], 1e-9) - 0.5
    say(f"{run[:60]}...: drawn as a spline run, {int(metal.sum()):,} of {n_cols:,} columns holding metal, the outline blurred "
        f"over {sigma_mm:g} mm, the free edges rounded {round_mm:g} mm")  # fmt: skip
    plan_sdf = None
    if VOXEL_FAIR:  # (15 October 13:55) the members faired in plan (`voxel_fair.fair_group`), each layer's distance on the
        # drawing's own plan grid (SPLINE_PLAN_SUB), the families' joined; the drawing reads it in place of its binary outline
        import voxel_fair as vf

        along_, iso_, band_ = (VOXEL_FAIR + [2.0, 2.5][len(VOXEL_FAIR) - 1 :])[:3]
        r_ = int(round(h / SPLINE_PLAN_SUB))
        plan_sdf = {}
        for hf_ in (0, 1):
            for lay_ in sorted({int(v) for v in lay_of[half == hf_]}):
                # both families' metal as one outline (a member crossing the cup's outline is one member: faired by family,
                # each part drew back from the line between them and cut a slit along it); the families set the heights
                mine = (half == hf_) & (lay_of == lay_) & metal
                met_c = np.zeros(tuple(n[:2]), bool)
                met_c[ii[mine], jj[mine]] = True
                plan_sdf[(hf_, lay_)] = vf.fair_group(np.kron(met_c, np.ones((r_, r_), bool)), SPLINE_PLAN_SUB, iso_, along_,
                                                      band_).astype(np.float32)  # fmt: skip
        say(f"the members faired in plan: along each member {along_:g} mm, every way {iso_:g} mm, within {band_:g} mm of the "
            "columns' outline")  # fmt: skip
    # each column's free end on one scale, voxels out from the split (as a `--top` spline run's `E`), so a node between
    # columns of different bases reads a free end, not one column's base with another's length: read as lengths, a node by
    # a seat's ring took the ring's base (z 82) with a split column's length (76 mm), a stick to z 162 (`lw8s8_fine`)
    o_base = np.where(half == 0, (k_split - 1) - base, base - k_split).astype(float)
    return {"ij": pts.astype(np.int32), "half": half, "base": base.astype(np.int32), "on_split": on_split,
            "E": np.where(metal, o_base + t, np.nan).astype(np.float32), "o_base": o_base.astype(np.float32),
            "t": np.where(metal, t, np.nan).astype(np.float32), "sub_ij": sub_ij.astype(np.int32), "sub_col": sub_col.astype(np.int32),
            "sub_phi": sub_phi.astype(np.float32), "sub_q": np.int32(q), "least": np.float32(0.0), "top_sharp": np.float32(2.0),
            "cap_sharp": np.float32(2.0), "pts_path": np.int8(1), "round_mm": np.float32(round_mm),
            "least_island_mm2": np.float32(h * h), **({"plan_sdf": plan_sdf, "fair_tops": VOXEL_FAIR[0]} if plan_sdf is not None else {})}  # fmt: skip


SPLINE_DRAW_RAMP = 1.0  # (LOP-30) mm of the outline field over which the drawing's plan density rises from 0 to 1
SPLINE_PLAN_SUB = 0.5  # (LOP-30) mm: the plan grid on which the members' true distance from their outline is measured
# (LOP-30, the engineer 15 October 01:30) LOOP_DRAW_SMOOTH=<mm>: a spline run's outline drawn as a cubic curve through its
# points and each member's free end smoothed over that many mm in plan (`spline_members_pts`); 0, as the model holds them
DRAW_SMOOTH = float(os.environ.get("LOOP_DRAW_SMOOTH", "0"))
# (LOP-30, the engineer 15 October 12:21) LOOP_VOXEL_SMOOTH=<mm>: a plain height-field run (voxels) drawn as a spline run is,
# its plan outline blurred over that many mm (`voxel_cols_as_spline`), its free edges rounded LOOP_VOXEL_ROUND mm and its
# roots filleted LOOP_VOXEL_FILLET mm; 0, drawn from its cubes as before
VOXEL_SMOOTH = float(os.environ.get("LOOP_VOXEL_SMOOTH", "0"))
# (LOP-30, 15 October 12:55) LOOP_DRAW_SMOOTH_RANGE=<mm>: the free ends smoothed edge-preservingly (a bilateral filter,
# `_bilateral`): two places' heights averaged as much less as they differ by more than about this many mm, so the cubes'
# 4 mm steps are smoothed and a real step kept (a 60 mm deep arm beside a 4 mm plate at mount-1's lug: averaged plainly,
# the arm's foot rose off the lug, `lw8s4_fine`); 0, the plain Gaussian
DRAW_SMOOTH_RANGE = float(os.environ.get("LOOP_DRAW_SMOOTH_RANGE", "0"))


def _bilateral(z: np.ndarray, mask: np.ndarray, sig_s: float, sig_r: float) -> np.ndarray:
    """(LOP-30) A plan grid's heights `z` smoothed over `sig_s` nodes among the `mask` nodes, each neighbour weighed down by
    how far its height differs (Gaussian over `sig_r`, the heights' units): the bilateral filter (Tomasi & Manduchi 1998)."""
    r = int(np.ceil(2.0 * sig_s))
    nx, ny = z.shape
    zp = np.pad(np.where(mask, z, 0.0), r)
    mp = np.pad(mask.astype(float), r)
    num = np.zeros(z.shape)
    den = np.zeros(z.shape)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            d2 = dx * dx + dy * dy
            if d2 > r * r:
                continue
            zs = zp[r + dx : r + dx + nx, r + dy : r + dy + ny]
            w = mp[r + dx : r + dx + nx, r + dy : r + dy + ny] * math.exp(-0.5 * d2 / (sig_s * sig_s))
            w = w * np.exp(-0.5 * ((zs - z) / sig_r) ** 2)
            num += w * zs
            den += w
    return np.where(den > 1e-12, num / np.maximum(den, 1e-12), z)
VOXEL_ROUND = float(os.environ.get("LOOP_VOXEL_ROUND", "3"))
VOXEL_FILLET = float(os.environ.get("LOOP_VOXEL_FILLET", "4"))
# (LOP-30, the engineer 15 October 13:49: "straighten the features ... remove this vertical edgy stretchy shapes")
# LOOP_VOXEL_FAIR="<along mm>[:<every way mm>[:<held near fixed metal, mm>]]": with LOOP_VOXEL_SMOOTH, the members' plan
# outline faired (`voxel_fair.fair_group`) and read by the drawing as a distance; empty, the blurred outline as before
VOXEL_FAIR = [float(v) for v in os.environ.get("LOOP_VOXEL_FAIR", "").split(":") if v.strip()]


def spline_members_pts(spl: dict, half: str, f: dict, xs, ys, zs, footprint: np.ndarray | None = None) -> np.ndarray:
    """(LOP-30; the engineer 14 October 22:43-23:01: production-quality members, "smooth nice but shaped by optimiser") A
    spline run's members drawn as the model holds them with each point's own height (`topo.Voxels._spline_pts`), as a
    signed distance (mm, positive outside), each layer:
    - in plan, the true distance from the members' outline: the outline field's points read on a SPLINE_PLAN_SUB grid
      (linear between them), split into inside and outside, and the Euclidean distance either side of the line;
    - the free end: with the smooth top (F1) each family's free end `E` read cubic between the columns and the height
      past the node's own level `least + softplus(E - level - least)`, as the model; with the section window (F2) at
      most its cap (read linear between the points) by the model's smooth minimum;
    - the two joined with the section rule's round (`exact_walls.round_inter`), or sharp without it.
    The families part on the cup's outline on the first runs, as `spline_members`, a node falling back to its own
    column's family where its parted family has no column on its layer."""
    from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

    import exact_walls as ew

    h, lo, n = float(f["h"]), np.asarray(f["lo"], float), [int(v) for v in f["n"]]
    ks = int(f["k_split"])
    lower = half == "motor_side"
    sel = np.flatnonzero(spl["half"] == (0 if lower else 1))
    ij, base, fam = spl["ij"][sel].astype(int), spl["base"][sel], spl["on_split"][sel]
    t_col = spl["t"][sel]
    e_col = spl["E"][sel] if "E" in spl else None
    least, t_sharp, c_sharp = float(spl["least"]), float(spl["top_sharp"]), float(spl["cap_sharp"])
    rnd = float(spl["round_mm"]) if "round_mm" in spl else 0.0
    q = int(spl.get("sub_q", 2))
    step = h / q
    sub_of = {int(c): k for k, c in enumerate(sel)}
    sub_keep = np.array([int(c) in sub_of for c in spl["sub_col"]])
    sub_ij, sub_phi = spl["sub_ij"][sub_keep].astype(int), spl["sub_phi"][sub_keep]
    sub_cap = spl["sub_cap"][sub_keep] if "sub_cap" in spl else None
    sub_k = np.array([sub_of[int(c)] for c in spl["sub_col"][sub_keep]], np.int64)
    order = np.argsort(-base) if lower else np.argsort(base)
    layer = np.zeros(len(sel), np.int64)
    seen: dict = {}
    for k in order:
        key = (int(ij[k, 0]), int(ij[k, 1]))
        layer[k] = seen.get(key, 0)
        seen[key] = layer[k] + 1

    def carried(a: np.ndarray) -> np.ndarray:
        if np.isnan(a).all():
            return np.zeros_like(a)
        _, (ia, ja) = distance_transform_edt(np.isnan(a), return_indices=True)
        return a[ia, ja]

    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    CI, CJ = np.meshgrid((xs - lo[0]) / h - 0.5, (ys - lo[1]) / h - 0.5, indexing="ij")  # in columns
    cell_i = np.clip(np.floor(CI + 0.5).astype(int), 0, n[0] - 1)
    cell_j = np.clip(np.floor(CJ + 0.5).astype(int), 0, n[1] - 1)
    PI, PJ = np.meshgrid((xs - lo[0]) / step - 0.5, (ys - lo[1]) / step - 0.5, indexing="ij")  # in points
    n_sub = (q * n[0], q * n[1])
    ss = SPLINE_PLAN_SUB
    m_s = (int(np.ceil(n[0] * h / ss)), int(np.ceil(n[1] * h / ss)))
    xs_s, ys_s = lo[0] + ss * (np.arange(m_s[0]) + 0.5), lo[1] + ss * (np.arange(m_s[1]) + 0.5)
    SI, SJ = np.meshgrid((xs_s - lo[0]) / step - 0.5, (ys_s - lo[1]) / step - 0.5, indexing="ij")  # the fine plan grid, in points
    own_si = np.clip(np.floor(SI + 0.5).astype(int), 0, n_sub[0] - 1)
    own_sj = np.clip(np.floor(SJ + 0.5).astype(int), 0, n_sub[1] - 1)
    NI, NJ = np.meshgrid((xs - lo[0]) / ss - 0.5, (ys - lo[1]) / ss - 0.5, indexing="ij")  # the nodes, on the fine plan grid
    zz = np.asarray(zs)[None, None, :]
    out = np.full((len(xs), len(ys), zz.shape[2]), np.inf, np.float32)
    for lay in range(int(layer.max()) + 1 if len(layer) else 0):
        mine = layer == lay
        grid_base = np.full(n[:2], -1, np.int64)
        grid_fam = np.zeros(n[:2], np.int8)
        grid_v = {True: np.full(n[:2], np.nan), False: np.full(n[:2], np.nan)}  # each family's E (or t), by column
        for k in np.flatnonzero(mine):
            i_, j_ = ij[k]
            grid_base[i_, j_], grid_fam[i_, j_] = base[k], 1 if fam[k] else 2
            grid_v[bool(fam[k])][i_, j_] = e_col[k] if e_col is not None else t_col[k]
        pts_l = mine[sub_k]
        phi_g = np.full(n_sub, np.nan)
        phi_g[sub_ij[pts_l, 0], sub_ij[pts_l, 1]] = sub_phi[pts_l]
        has_g = np.isfinite(phi_g)
        # the true distance from the outline (mm, positive inside), on the fine plan grid, then at the nodes; with the
        # smoothing (DRAW_SMOOTH) the outline a cubic curve through the points: straight between them, a tall face showed
        # each kink as a groove its whole height (the engineer, 15 October 01:24: "why ... edgy and staircasy")
        phi_s = map_coordinates(carried(phi_g), [SI, SJ], order=3 if DRAW_SMOOTH > 0 else 1, mode="nearest")
        inside = (phi_s > 0.0) & has_g[own_si, own_sj]
        inside = fill_diagonals(inside[:, :, None])[:, :, 0]  # (15 October 03:25) no corner-only contact in the outline
        if spl.get("least_island_mm2"):
            # (15 October 13:10) specks of outline smaller than a column dropped: where the interpolated outline field just
            # rises above zero by the design space's edges, each speck took its nearest member's height, a stick 1-2 mm
            # thick and 40-60 mm tall (`lw8s7_fine`, eight on the cover)
            from scipy.ndimage import label as _label

            lab, n_lab = _label(inside)
            if n_lab:
                size = np.bincount(lab.ravel(), minlength=n_lab + 1) * ss * ss
                inside &= size[lab] >= float(spl["least_island_mm2"])
        d_in = distance_transform_edt(inside) * ss
        d_out = distance_transform_edt(~inside) * ss
        a_s = np.where(inside, d_in - 0.5 * ss, -(d_out - 0.5 * ss))
        faired = spl.get("plan_sdf")
        if faired is not None and (0 if lower else 1, lay) in faired:  # (15 October) the faired plan distance (`voxel_fair`)
            a_s = faired[(0 if lower else 1, lay)]
        a_f = map_coordinates(a_s, [NI, NJ], order=1, mode="nearest")
        own_fam = grid_fam[cell_i, cell_j]
        if footprint is not None and lay == 0:
            fam_f = np.where(own_fam > 0, np.where(footprint, 2, 1), 0)
        else:
            fam_f = own_fam
        present = {1: bool((grid_fam == 1).any()), 2: bool((grid_fam == 2).any())}
        fam_f = np.where(((fam_f == 1) & present[1]) | ((fam_f == 2) & present[2]), fam_f, own_fam)
        base_by = {}
        for code_ in (1, 2):
            gb = np.where(grid_fam == code_, grid_base.astype(float), np.nan)
            base_by[code_] = np.rint(carried(gb)).astype(np.int64)[cell_i, cell_j]
        base_f = np.where(fam_f == 1, base_by[1], base_by[2])
        v_f = np.where(fam_f == 1, map_coordinates(carried(grid_v[True]), [CI, CJ], order=3, mode="nearest"),
                       map_coordinates(carried(grid_v[False]), [CI, CJ], order=3, mode="nearest"))  # fmt: skip
        if e_col is not None:  # F1: the height past the node's own level, as the model's
            o_base_f = ((ks - 1) - base_f) if lower else (base_f - ks)
            t_f = least + np.logaddexp(0.0, t_sharp * (v_f - o_base_f - least)) / t_sharp
        else:
            t_f = v_f
        if sub_cap is not None:  # F2: at most the window's cap, by the model's smooth minimum
            cap_g = np.full(n_sub, np.nan)
            cap_g[sub_ij[pts_l, 0], sub_ij[pts_l, 1]] = sub_cap[pts_l]
            cap_f = map_coordinates(carried(cap_g), [PI, PJ], order=1, mode="nearest")
            m_ = np.minimum(t_f, cap_f)
            t_f = m_ - np.log(np.exp(-c_sharp * (t_f - m_)) + np.exp(-c_sharp * (cap_f - m_))) / c_sharp
        out_plan = -np.where(fam_f > 0, a_f, -np.inf)[:, :, None]
        face2 = lo[2] + h * (base_f + 1) if lower else lo[2] + h * base_f
        z_end = face2 - h * t_f if lower else face2 + h * t_f  # each node's free end (mm)
        if DRAW_SMOOTH > 0:
            # (the engineer, 15 October 01:30: "why can't we simply interpolate or smooth that area out ... after it's been
            # obtained from the optimizer") each member's free end smoothed over DRAW_SMOOTH mm in plan, within the member
            # and its family: where a top is tied to its floor (its cap, its least height), it had copied the 4 mm cells'
            # floor steps. FE judges the smoothed shape, as every drawing
            sig = DRAW_SMOOTH / float(xs[1] - xs[0]) if len(xs) > 1 else 1.0
            z_s = z_end.copy()
            for code_ in (1, 2):
                m_ = ((fam_f == code_) & (a_f > -2.0 * DRAW_SMOOTH)).astype(float)
                if m_.any() and DRAW_SMOOTH_RANGE > 0:  # (15 October) the steps kept, the cubes' ripples smoothed
                    z_s = np.where(m_ > 0, _bilateral(z_end, m_ > 0, sig, DRAW_SMOOTH_RANGE), z_s)
                elif m_.any():
                    num = gaussian_filter(np.where(m_ > 0, z_end, 0.0), sig)
                    den = gaussian_filter(m_, sig)
                    z_s = np.where((m_ > 0) & (den > 1e-6), num / np.maximum(den, 1e-6), z_s)
                if m_.any() and spl.get("fair_tops"):  # (15 October) the tops' cliffs straightened along their contours
                    import voxel_fair as vf

                    z_s = vf.fair_tops(z_s, m_ > 0, float(xs[1] - xs[0]) if len(xs) > 1 else 1.0, float(spl["fair_tops"]))
            z_end = z_s
        face = face2[:, :, None]
        zdist = (z_end[:, :, None] - zz) if lower else (zz - z_end[:, :, None])
        if DRAW_SMOOTH > 0:
            # the distance to a sloped top: the height over the slope's secant (first order), so the contour's ramp spans a
            # cell on a steep top too (the plain height there aliased into horizontal stripes on the 1 mm grid)
            gx_, gy_ = np.gradient(z_end, float(xs[1] - xs[0]) if len(xs) > 1 else 1.0, float(ys[1] - ys[0]) if len(ys) > 1 else 1.0)
            zdist = zdist / np.sqrt(1.0 + gx_ * gx_ + gy_ * gy_)[:, :, None]
        f_l = ew.round_inter(out_plan, zdist, rnd) if rnd > 0 else np.maximum(out_plan, zdist)
        if lay:  # a run past another: from its own first voxel
            f_l = np.maximum(f_l, (zz - face) if lower else (face - zz))
        out = np.minimum(out, f_l.astype(np.float32))
    return out


def spline_members(spl: dict, half: str, f: dict, xs, ys, zs, footprint: np.ndarray | None = None) -> np.ndarray:
    """(LOP-30) A spline run's members on the drawing's grid, from the fields each column read: the outline field and each
    family's heights (the columns on the split, those on a wall) interpolated smoothly (cubic) between the columns'
    centres, each family's values carried to its region's edge first so that nothing rings there; the metal where the
    outline is positive, from the column's level out to its height. The plan density rises over SPLINE_DRAW_RAMP of the
    field (a gentle one, the whole range, let the cube centres' hold raise ridges a millimetre high every 4 mm), the
    height's density linearly, so the contour at 0.5 falls on the field's zero and the top. With `footprint` (each plan
    node inside the cup's outline, its wall's mid-line) the families part on the cup's exact outline, not cell by cell
    (cell by cell, the cover's side gusset came out striped).

    With the section rule (a run with `--section`: its points' distances inside the outline, `sub_a`, and the round's
    radius, `round_mm`) it returns the members' signed distance instead (mm, positive outside): each layer the outline's
    distance and the free end's, their edge rounded to the radius (`exact_walls.round_inter`), as the optimiser rounds it
    (`topo.section_drop`); the caller joins it to the exact parts with the fillets."""
    from scipy.ndimage import distance_transform_edt, map_coordinates

    import exact_walls as ew

    if "pts_path" in spl:  # (LOP-30, F1-F2) each point's own height (`spline_members_pts`)
        return spline_members_pts(spl, half, f, xs, ys, zs, footprint=footprint)
    section = float(spl["round_mm"]) if ("sub_a" in spl and "round_mm" in spl) else 0.0
    h, lo, n = float(f["h"]), np.asarray(f["lo"], float), [int(v) for v in f["n"]]
    lower = half == "motor_side"
    sel = np.flatnonzero(spl["half"] == (0 if lower else 1))
    ij, t, base, fam = spl["ij"][sel].astype(int), spl["t"][sel], spl["base"][sel], spl["on_split"][sel]
    # (LOP-30, 19:15) the outline field's opened values at each cube's points: the drawing's own plan nodes (FINE = h / q)
    q = int(spl.get("sub_q", 2))
    between = abs(q * FINE - h) > 1e-6  # the drawing's nodes finer than the points (`LOOP_DRAW_FINE`): read between them
    if between and FINE > h / q:
        raise ValueError(f"the drawing's grid ({FINE:g} mm) is coarser than the spline run's points ({h / q:g} mm)")
    sub_of = {int(c): k for k, c in enumerate(sel)}  # a column of the half: its place in sel
    sub_keep = np.array([int(c) in sub_of for c in spl["sub_col"]])
    sub_ij, sub_phi = spl["sub_ij"][sub_keep].astype(int), spl["sub_phi"][sub_keep]
    sub_a = spl["sub_a"][sub_keep] if section else None
    sub_k = np.array([sub_of[int(c)] for c in spl["sub_col"][sub_keep]], np.int64)  # each point's column, in sel's order
    # a plan cell may hold several runs (past a mount's room or its lug): each its layer, the run nearest the split first
    order = np.argsort(-base) if lower else np.argsort(base)
    layer = np.zeros(len(sel), np.int64)
    seen: dict = {}
    for k in order:
        key = (int(ij[k, 0]), int(ij[k, 1]))
        layer[k] = seen.get(key, 0)
        seen[key] = layer[k] + 1

    def carried(a: np.ndarray) -> np.ndarray:
        """The grid's values carried to its empty cells from the nearest filled one (no edge to ring at)."""
        if np.isnan(a).all():
            return np.zeros_like(a)
        _, (ia, ja) = distance_transform_edt(np.isnan(a), return_indices=True)
        return a[ia, ja]

    ci = (np.asarray(xs) - lo[0]) / h - 0.5
    cj = (np.asarray(ys) - lo[1]) / h - 0.5
    CI, CJ = np.meshgrid(ci, cj, indexing="ij")
    cell_i = np.clip(np.floor(CI + 0.5).astype(int), 0, n[0] - 1)
    cell_j = np.clip(np.floor(CJ + 0.5).astype(int), 0, n[1] - 1)
    if between:  # each node's place among the points (h / q apart, the first h / 2q past lo) and its own (nearest) point
        n_sub = (q * n[0], q * n[1])
        PI, PJ = np.meshgrid((np.asarray(xs) - lo[0]) / (h / q) - 0.5, (np.asarray(ys) - lo[1]) / (h / q) - 0.5, indexing="ij")
        own_i = np.clip(np.floor(PI + 0.5).astype(int), 0, n_sub[0] - 1)
        own_j = np.clip(np.floor(PJ + 0.5).astype(int), 0, n_sub[1] - 1)

        def on_nodes(si_: np.ndarray, sj_: np.ndarray, vals: np.ndarray) -> np.ndarray:
            """Points' values read at the nodes: cubic between the points, each point's value carried to the empty ones
            first (no edge to ring at); none (-inf) where a node's own point is missing."""
            g = np.full(n_sub, np.nan)
            g[si_, sj_] = vals
            read = map_coordinates(carried(g), [PI, PJ], order=3, mode="nearest")
            return np.where(np.isfinite(g)[own_i, own_j], read, -np.inf)

    zz = np.asarray(zs)[None, None, :]
    out = np.full((len(ci), len(cj), zz.shape[2]), np.inf if section else 0.0, np.float32)
    n_plan = (len(ci), len(cj))
    for lay in range(int(layer.max()) + 1 if len(layer) else 0):
        mine = layer == lay
        grid_t = {True: np.full(n[:2], np.nan), False: np.full(n[:2], np.nan)}
        grid_base = np.full(n[:2], -1, np.int64)
        grid_fam = np.zeros(n[:2], np.int8)  # 0 no column, 1 on the split, 2 on a wall
        for k in np.flatnonzero(mine):
            i_, j_ = ij[k]
            grid_base[i_, j_], grid_fam[i_, j_] = base[k], 1 if fam[k] else 2
            grid_t[bool(fam[k])][i_, j_] = t[k]
        # the outline field at this layer's points, each a plan node of the drawing's grid (none: no metal there); on a
        # finer grid read between them (`on_nodes`)
        pts_l = mine[sub_k]
        si, sj = sub_ij[pts_l, 0], sub_ij[pts_l, 1]
        if between:
            phi_f = on_nodes(si, sj, sub_phi[pts_l])
            if section:
                a_f = on_nodes(si, sj, sub_a[pts_l])
        else:
            phi_f = np.full(n_plan, -np.inf)
            ok_ = (si < n_plan[0]) & (sj < n_plan[1])
            phi_f[si[ok_], sj[ok_]] = sub_phi[pts_l][ok_]
            if section:  # each node's distance inside the outline, mm (none: far outside)
                a_f = np.full(n_plan, -np.inf)
                a_f[si[ok_], sj[ok_]] = sub_a[pts_l][ok_]
        own_fam = grid_fam[cell_i, cell_j]
        if footprint is not None and lay == 0:  # the runs from the split and from the end walls parted on the cup's exact outline
            fam_f = np.where(own_fam > 0, np.where(footprint, 2, 1), 0)
        else:  # (14 October 21:35) a run past a mount's room or its lug: each column's own family
            fam_f = own_fam
        present = {1: bool((grid_fam == 1).any()), 2: bool((grid_fam == 2).any())}
        # a node whose outline's family has no column on this layer takes its own column's: past mount-3's room the arm's
        # columns stand on a level of their own (no family on the split there), so the parting by the cup's outline drew
        # nothing of them and the drawing lost the lug (baseline2_spl2, 21:28)
        fam_f = np.where(((fam_f == 1) & present[1]) | ((fam_f == 2) & present[2]), fam_f, own_fam)
        base_by = {}
        for code_ in (1, 2):  # each family's level carried to its region's edge, so a node takes its own family's
            gb = np.where(grid_fam == code_, grid_base.astype(float), np.nan)
            base_by[code_] = np.rint(carried(gb)).astype(np.int64)[cell_i, cell_j]
        base_f = np.where(fam_f == 1, base_by[1], base_by[2])
        t_f = np.where(fam_f == 1, map_coordinates(carried(grid_t[True]), [CI, CJ], order=3, mode="nearest"),
                       map_coordinates(carried(grid_t[False]), [CI, CJ], order=3, mode="nearest"))  # fmt: skip
        if section:  # the section rule: the outline's distance and the free end's, their edge rounded (positive outside)
            out_plan = -np.where((fam_f > 0) & np.isfinite(a_f), a_f, -np.inf)[:, :, None]
            if lower:
                face = (lo[2] + h * (base_f + 1))[:, :, None]
                f_l = ew.round_inter(out_plan, (face - h * t_f[:, :, None]) - zz, section)
                if lay:  # a run past another: from its own first voxel
                    f_l = np.maximum(f_l, zz - face)
            else:
                face = (lo[2] + h * base_f)[:, :, None]
                f_l = ew.round_inter(out_plan, zz - (face + h * t_f[:, :, None]), section)
                if lay:
                    f_l = np.maximum(f_l, face - zz)
            out = np.minimum(out, f_l.astype(np.float32))
            continue
        u = np.where((fam_f > 0) & np.isfinite(phi_f), np.clip(0.5 + phi_f / (2.0 * SPLINE_DRAW_RAMP), 0.0, 1.0), 0.0)
        if lower:  # the motor side's columns run from the split downward: the level's split-side face, then t voxels down
            face = (lo[2] + h * (base_f + 1))[:, :, None]
            z_den = np.clip(0.5 + (zz - (face - h * t_f[:, :, None])) / (2.0 * FINE), 0.0, 1.0)
            if lay:  # a run past another: from its own first voxel, not over what lies between
                z_den = np.minimum(z_den, np.clip(0.5 + (face - zz) / (2.0 * FINE), 0.0, 1.0))
        else:
            face = (lo[2] + h * base_f)[:, :, None]
            z_den = np.clip(0.5 + (face + h * t_f[:, :, None] - zz) / (2.0 * FINE), 0.0, 1.0)
            if lay:
                z_den = np.minimum(z_den, np.clip(0.5 + (zz - face) / (2.0 * FINE), 0.0, 1.0))
        out = np.maximum(out, np.minimum(u[:, :, None], z_den).astype(np.float32))
    return out


def skin_parts(f: dict, mem: dict, layout: dict, all_rooms: list[dict], z_split: float, half: str, empty: bool = False, towers: bool = True,
               protect: bool = False, spline: dict | None = None) -> dict:  # fmt: skip
    """What a half of the skin drawing holds whatever level its members are read at, on a `FINE`
    grid: the cup's rooms (`cavity`, filled for the exact cut after) with the wall round them
    (`SKIN_WALL`) and the interfaces the set-up has (`fixed`); the optimiser's members as a fair
    field (`members`: blurred over `MEMBER_BLUR` voxels and read between the voxels' centres,
    trilinear; taken voxel by voxel they stood as 6 mm blocks, which the fine blur only rounded at
    the corners); the kept-clear spaces (`clear`). `skin_metal` reads them at a level.

    `empty` (LOP-27, an empty start's run): no wall round the rooms and no sealing land, which are
    the field's own metal; the mounts and the bolts' bosses at their full size on the grid, as no
    exact shell is fused on after (one field for every as-cast surface)."""
    from matplotlib.path import Path as Polygon
    from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

    s = layout["settings"]
    lower = half == "motor_side"
    members_sdf = None  # (LOP-30) a spline run's members as a signed distance, with the section rule
    h, lo, n = f["h"], f["lo"], f["n"]
    n_f = np.ceil(n * h / FINE).astype(int)
    # the fine grid's origin: its cells' centres at lo_f + (i + 1/2) FINE; a spline run's points (`spline_members`) are
    # its plan nodes (each cube's points h / 4 off its centre: FINE = h / 2)
    lo_f = np.asarray(lo, float)
    xs, ys, zs = (lo_f[i] + FINE * (np.arange(n_f[i]) + 0.5) for i in range(3))
    # (LOP-30) finer than 2 mm in single precision: a half at 1 mm is 36 M nodes
    X, Y, Z = np.meshgrid(*((v.astype(np.float32) for v in (xs, ys, zs)) if FINE < 2.0 else (xs, ys, zs)), indexing="ij")
    ks = int(np.searchsorted(zs, z_split))  # the first cell above the split
    side = (Z < z_split) if lower else (Z >= z_split)
    # 1. the skin: the half's cup (filled, for the exact cut after) and the wall round the whole
    # inside, both halves' rooms, as the optimiser's skin is: across the split, over the other
    # half's opening, the half's wall is the wall, not the flange's band (whose 9 mm plates over
    # each opening carried 1.9 kg of outcome_skin_6mm_contract's 9.59)
    fine_grid = {"n": n_f, "lo": lo_f, "h": FINE}
    cavity = rooms_mask(fine_grid, all_rooms, z_split, half)
    union = cavity | rooms_mask(fine_grid, all_rooms, z_split, "cover" if lower else "motor_side")
    d_cav = distance_transform_edt(~union) * FINE
    # the exact parts (`exact_shell`) stand `SKIN_BURY` under their faces here; the plate over the
    # other half's wider opening is the exact shell's alone: buried 2 mm deep it was a 2 mm slab,
    # which the blur broke open (outcome_skin_6mm_drive's motor side, 11 October 01:01)
    # (LOP-28) an empty start's protected interfaces are fused exact after, so their grid copies stand under their faces too
    bury = SKIN_BURY if layout.get("flange") and (protect or not empty) else 0.0
    wall_here = s["wall"] - bury if bury else SKIN_WALL
    if empty:  # the walls are the field's: only the rooms, filled for the exact cut after
        metal = cavity.copy()
    elif bury:
        d_own = distance_transform_edt(~cavity) * FINE
        metal = cavity | ((d_own <= wall_here + 0.5 * FINE) & ~union)
    else:
        metal = cavity | ((d_cav <= wall_here + 0.5 * FINE) & ~union)
    # 2. the members the optimiser placed, each with the skin voxel it stands on (`members_of`),
    # as a fair field: a member one voxel thick peaks at 0.68, a lone voxel at 0.31
    at = np.meshgrid(*(((c - lo[i]) / h - 0.5) for i, c in enumerate((xs, ys, zs))), indexing="ij")
    if spline is not None:  # (LOP-30) a spline run's members from its fields, smooth (`spline_members`); no cube held
        px_, py_ = np.meshgrid(xs, ys, indexing="ij")
        footprint = np.zeros(px_.shape, bool)  # inside the cup's outline, to its wall's mid-line: the families' parting
        for pc in cupmod.pieces(all_rooms, z_split, half):
            footprint |= np.hypot(px_ - pc["axis"][0], py_ - pc["axis"][1]) <= float(pc["r"]) + 0.5 * s["wall"]
        members = spline_members(spline, half, f, xs, ys, zs, footprint=footprint)
        if "sub_a" in spline or "pts_path" in spline:  # the section rule: the members' signed distance, joined below with fillets
            members_sdf, members = members, np.zeros(members.shape, np.float32)
        keep_cells = np.zeros(members.shape, bool)
    else:
        smooth = gaussian_filter(mem["placed"].astype(float), sigma=MEMBER_BLUR)
        members = map_coordinates(smooth, at, order=1, mode="constant").astype(np.float32)
        # (LOP-29) the cells inside the run's own metal cubes (the nearest cube's), kept by the contour (`mesh_route.contour`)
        keep_cells = map_coordinates(mem["placed"].astype(float), at, order=0, mode="constant") > 0.5
    keep_soft = None
    if SMOOTH_KEEP > 0:  # (LOP-29) the kept cubes as a smooth density: their blurred signed distance, each centre's ball held
        import exact_walls as ew

        d_cubes = (distance_transform_edt(~keep_cells) - distance_transform_edt(keep_cells)) * FINE
        d_cubes = gaussian_filter(d_cubes, sigma=SMOOTH_KEEP / FINE)
        ijk_ = np.argwhere(mem["placed"])
        centres = np.asarray(lo, float) + h * (ijk_ + 0.5) if len(ijk_) else np.zeros((0, 3))
        d_centre = np.full(keep_cells.shape, np.inf, np.float32)
        if len(centres):
            from scipy.spatial import cKDTree

            pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
            d_centre = cKDTree(centres).query(pts, distance_upper_bound=4.0 * h)[0].reshape(keep_cells.shape).astype(np.float32)
        # the ball 2.5 mm: the eight cells round a centre stand 1.7 mm from it, so a smaller one never showed (lost 4.8 %)
        keep_soft = np.maximum(ew.ramp(d_cubes, FINE), ew.ramp(d_centre - 2.5, FINE))
    del at
    if mem.get("network") is not None:  # the network's filled pieces drawn clean (LOP-23, `network_draw`)
        import network_draw

        own = distance_transform_edt(~cavity) * FINE
        ribs = network_draw.clean(mem["network"], half, X[:, :, 0], Y[:, :, 0], own, cavity, side)
        members = np.maximum(members, ribs.astype(np.float32))
    exact_sdf = None  # (LOP-29) the exact parts' faces, for the contour's ramp (`EXACT_FACES`)
    if empty and EXACT_WALLS and EXACT_FACES:
        import exact_walls as ew

        exact_sdf = ew.least_sdf(X, Y, Z, layout, all_rooms, z_split, half)
        if protect:
            exact_sdf = np.minimum(exact_sdf, ew.interface_sdf(X, Y, Z, layout, all_rooms, z_split, half, towers=towers))
        if members_sdf is not None:  # (LOP-30) the section rule's fillets: the members joined to the exact parts, rounded
            fil = float(spline.get("fillet_mm") or 0.0)
            joined = ew.round_union(members_sdf, exact_sdf, fil) if fil > 0 else np.minimum(members_sdf, exact_sdf)
            members = np.maximum(members, ew.ramp(joined, FINE))
            members_sdf = None
        members = np.maximum(members, ew._density(exact_sdf + FINE))  # the cells' copy, a cell inside the faces
    elif empty and EXACT_WALLS:  # LOP-27: the least walls from the exact inside, in the same field (`exact_walls.least_density`)
        import exact_walls as ew

        members = np.maximum(members, ew.least_density(X, Y, Z, layout, all_rooms, z_split, half))
    if members_sdf is not None:  # (LOP-30) no exact faces to join: the members' own rounded edges alone
        import exact_walls as ew

        members = np.maximum(members, ew.ramp(members_sdf, FINE))
        members_sdf = None
    if empty and protect and exact_sdf is None:  # LOP-28: the protected interfaces from their exact geometry, in the same field (`exact_walls.interface_density`)
        import exact_walls as ew

        members = np.maximum(members, ew.interface_density(X, Y, Z, layout, all_rooms, z_split, half, towers=towers))
    if empty and os.environ.get("LOOP_PANEL_SPOKES"):  # LOP-28: production's panel spokes, "<pitch deg>:<thickness mm>:<height mm>", in the field
        import exact_walls as ew

        spec_ = os.environ.get("LOOP_PANEL_SPOKES_MOTOR", os.environ["LOOP_PANEL_SPOKES"]) if half == "motor_side" else os.environ["LOOP_PANEL_SPOKES"]
        pitch_, thick_, high_ = (float(v) for v in spec_.split(":"))
        if half in [v.strip() for v in os.environ.get("LOOP_SPOKE_HALVES", "cover,motor_side").split(",")]:
            members = np.maximum(members, ew.spoke_density(X, Y, Z, layout, all_rooms, z_split, half, pitch_, thick_, high_))
    if empty and os.environ.get("LOOP_LUG_WEBS"):  # LOP-28: production's gusseted lugs, "<thickness mm>:<spread mm>", in the field
        import exact_walls as ew

        w_thick, w_spread = (float(v) for v in os.environ["LOOP_LUG_WEBS"].split(":"))
        members = np.maximum(members, ew.lug_web_density(X, Y, Z, layout, all_rooms, z_split, half, w_thick, w_spread))
    # 3. the interfaces the set-up has: the mounts, and the joint's flange over its outline (the
    # process's joint rules, A26), which holds the bolts' bosses. The trade's bearing bosses only
    # with DRAW_BOSSES: they are not in the agreed set-up (the engineer, 10 October 19:24: "we
    # fixed the contract already"), and drawn on top of the field they made 11.19 kg.
    t_f = s["flange_thickness"]
    for b in layout["bearings"] if DRAW_BOSSES else []:
        if (b["side"] == "-z") != lower:
            continue
        z0, z1 = b["z"]
        r_b = np.hypot(X - b["axis"][0], Y - b["axis"][1])
        span = (Z >= z0 - SKIN_WALL - PROUD) & (Z <= z1) if lower else (Z >= z0) & (Z <= z1 + SKIN_WALL + PROUD)
        metal |= (r_b <= boss_r(b)) & span
    centre_of = {m["name"]: m["centre"] for m in layout["mounts"]}
    for m in layout["mounts"] if lower else []:
        r_m = np.hypot(X - m["centre"][0], Y - m["centre"][1])
        metal |= (r_m <= s["mount_diameter"] / 2 - bury) & (Z >= m["z"][0] + bury) & (Z <= m["z"][1] - bury)
    # (the bolts' bosses are the flange's band below: the joint's outline holds them)
    outline = Polygon(np.asarray(layout["joint_outline"], float))
    plan = outline.contains_points(np.column_stack([X[:, :, 0].ravel(), Y[:, :, 0].ravel()])).reshape(X.shape[:2])
    # The joint's face: a sealing land round the whole inside at the split (the contract's width
    # since 11 October, `FLANGE_LAND` before), and each bolt's boss on it (the set-up's own,
    # fixed), a flange thick each side; nothing else of the joint's outline, a convex hull whose
    # band filled the waists between the lobes with 9 mm plates the optimiser never had (1.5 kg);
    # its metal there is its own, drawn as members.
    land_width = layout["flange"]["land_width"] if layout.get("flange") else FLANGE_LAND
    foot = union[:, :, ks - 1] | union[:, :, ks]  # the whole inside at the split
    land = (distance_transform_edt(~foot) * FINE <= land_width - bury + 0.5 * FINE) & ~foot
    if empty and not protect:  # the sealing land is the field's (its least height); the bolts' bosses alone are fixed
        land = np.zeros_like(foot)
    for c in layout["bolts"]:
        land |= np.hypot(X[:, :, 0] - c[0], Y[:, :, 0] - c[1]) <= s["bolt_boss"] / 2 - bury
    metal |= (land & plan)[:, :, None] & (np.abs(Z - z_split) <= t_f - bury) & side
    # 4. the kept-clear spaces: the exits (each seal's bore, the half-shafts' joints) and the
    # vehicle's bracket beyond each end of each mount
    clear = np.zeros(X.shape, bool)
    # (LOP-30, 15 October 03:30) the same spaces as a signed distance (mm, positive outside, a cylinder's the larger of its
    # radial and its axial distance): a spline drawing's members are cut by it smoothly, where emptied cell by cell the
    # cells' staircase and the members' smooth face left hairline flags along each bolt's socket that TetGen refused
    clear_sdf = np.full(X.shape, np.inf, np.float32)

    def cyl_sdf(cx_, cy_, r_, z0_, z1_):
        return np.maximum(np.hypot(X - cx_, Y - cy_) - r_, np.maximum(z0_ - Z, Z - z1_)).astype(np.float32)

    for e in layout.get("exits") or []:
        r_e = np.hypot(X - e["centre"][0], Y - e["centre"][1])
        clear |= (r_e < e["radius"] + FINE_MARGIN) & (Z >= e["z"][0]) & (Z <= e["z"][1])
        clear_sdf = np.minimum(clear_sdf, cyl_sdf(e["centre"][0], e["centre"][1], e["radius"], e["z"][0], e["z"][1]))
    for b in layout.get("brackets") or []:
        cx, cy = b.get("centre") or centre_of[b["name"].split(" bracket")[0]]
        clear |= (np.hypot(X - cx, Y - cy) < b["radius"] + FINE_MARGIN) & (Z >= b["z"][0]) & (Z <= b["z"][1])
        clear_sdf = np.minimum(clear_sdf, cyl_sdf(cx, cy, b["radius"], b["z"][0], b["z"][1]))
    # each bolt's head and a hex key's room over it (`SOCKET`), off the flange's face: no column
    # of metal round it, as the organic drawing stood one (0.7 kg on outcome_skin_6mm_max12)
    d_sock, h_sock = s.get("bolt_socket") or SOCKET  # (LOP-29) the layout's, the optimiser's too
    for c in layout["bolts"]:
        r_c = np.hypot(X - c[0], Y - c[1])
        beyond = (Z < z_split - t_f) & (Z >= z_split - t_f - h_sock) if lower else (Z > z_split + t_f) & (Z <= z_split + t_f + h_sock)
        clear |= (r_c < d_sock / 2 + FINE_MARGIN) & beyond
        z0_s, z1_s = (z_split - t_f - h_sock, z_split - t_f) if lower else (z_split + t_f, z_split + t_f + h_sock)
        clear_sdf = np.minimum(clear_sdf, cyl_sdf(c[0], c[1], d_sock / 2, z0_s, z1_s))
    if bury and not empty:
        # With the exact shell, its exact cuts run through it and the filled cup: the grid keeps
        # its kept-clear spaces out of the cup and its wall, where cleared they left rings 2 mm
        # thick round each exit that the blur broke open (outcome_skin_6mm_drive, 01:03)
        clear &= ~(d_own <= s["wall"] + FINE_MARGIN)
    exact = None
    if exact_sdf is not None:
        import exact_walls as ew

        exact = np.where(side & ~clear, ew.ramp(exact_sdf, FINE), 0.0).astype(np.float32)
    return {"half": half, "lo": lo_f, "n_f": n_f, "ks": ks, "side": side, "cavity": cavity, "fixed": metal & side, "spline": spline is not None,
            "members": members, "clear": clear, "clear_sdf": clear_sdf, "keep": keep_cells & side & ~cavity & ~clear, "exact": exact,
            "keep_soft": None if keep_soft is None else np.where(side & ~cavity & ~clear, keep_soft, 0.0).astype(np.float32)}  # fmt: skip


def skin_metal(p: dict, level: float) -> np.ndarray:
    """A half's metal with its members read at `level`: closed over one cell (metal that met only
    at an edge or a corner left the surface open, outcome_skin_6mm_contract's motor side, 19:27),
    every column one piece from the split out to its last metal (the contract's pull), and the
    kept-clear spaces emptied."""
    from scipy.ndimage import binary_closing, generate_binary_structure

    from scipy.ndimage import binary_dilation

    kk = np.arange(p["n_f"][2])[None, None, :]
    lower = p["half"] == "motor_side"

    def depth(fixed: np.ndarray) -> np.ndarray:
        """Each column's metal from the split out, in cells: the half cast along its pull."""
        metal = fixed | ((p["members"] >= level) & p["side"] & ~p["cavity"])
        metal = binary_closing(np.pad(metal, 1), structure=generate_binary_structure(3, 1))[1:-1, 1:-1, 1:-1]
        metal &= ~p["clear"] & p["side"]
        if lower:
            return p["ks"] - np.where(metal, kk, p["n_f"][2]).min(axis=2)
        return np.where(metal, kk, p["ks"] - 1).max(axis=2) - p["ks"] + 1

    held = depth(p["fixed"])
    if ROOT_FILLET > 0:
        # The roots filleted (LOP-23; the trade's R 1-1.25 x the thinner leg, `docs/research/
        # 2026-10-09-production-housings-against-ours.md` §5.4): a ball of radius ROOT_FILLET
        # rolled over the half's outside, the exact parts at their faces (the grid's own stand
        # `SKIN_BURY` under them: dilated back by a cell), fills every concave corner with an arc.
        # Only where metal stands already: past the flange's edge the split is no floor.
        from scipy.ndimage import grey_closing

        face = depth(binary_dilation(p["fixed"], structure=generate_binary_structure(3, 1)) & p["side"])
        r = ROOT_FILLET / FINE
        k = int(np.ceil(r))
        i, j = np.mgrid[-k : k + 1, -k : k + 1]
        ball = np.where(i**2 + j**2 <= r * r, np.sqrt(np.maximum(r * r - i**2 - j**2, 0.0)) - r, -1e6)
        rolled = grey_closing(face.astype(float), structure=ball)
        filled = (face > 0) & (rolled > face + 1e-6)
        held = np.where(filled, np.maximum(held, np.ceil(rolled - 1e-6)), held)
    if lower:
        metal = (kk >= (p["ks"] - held)[:, :, None]) & (kk < p["ks"])
    else:
        metal = (kk <= (p["ks"] + held - 1)[:, :, None]) & (kk >= p["ks"])
    return metal & ~p["clear"]


def fill_diagonals(metal: np.ndarray, most: int = 12) -> np.ndarray:
    """(LOP-30, 15 October 03:20) The cells made metal where two metal cells touch only along an edge or at a corner (a
    2 x 2 square with two opposite cells metal and the others air, in any of the three planes, or a 2 x 2 x 2 cube with
    one body diagonal metal), one cell a contact, until none is left. A spline drawing's members are their plan
    outline's distance (`spline_members_pts`) extruded along the pull, so a corner-only contact in the outline's mask
    became a line the member's whole height long, two sheets touching there: TetGen refused every spline drawing since
    the smooth top (`spl8`'s motor side, 39 faces on 19 such lines, "two segments exactly intersect"). A 2D mask is
    passed as (n, m, 1)."""
    m = np.asarray(metal, bool).copy()
    for _ in range(most):
        changed = 0
        for a0, a1 in ((0, 1), (0, 2), (1, 2)):
            b = np.moveaxis(m, (a0, a1), (0, 1))  # a view: writing it writes m
            p00, p11, p10, p01 = b[:-1, :-1], b[1:, 1:], b[1:, :-1], b[:-1, 1:]
            d1 = p00 & p11 & ~p10 & ~p01
            d2 = p10 & p01 & ~p00 & ~p11
            changed += int(d1.sum()) + int(d2.sum())
            p10 |= d1  # one cell of each contact: the square closed
            p00 |= d2
        # a body diagonal: two cells sharing a corner only, the six others of their cube air
        for s0, s1, s2 in ((0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)):
            sl = [slice(None, -1), slice(1, None)]
            c_a = m[sl[s0], sl[s1], sl[s2]]
            c_b = m[sl[1 - s0], sl[1 - s1], sl[1 - s2]]
            cube = np.zeros(c_a.shape, np.int32)
            for i in (0, 1):
                for j in (0, 1):
                    for k in (0, 1):
                        cube += m[sl[i], sl[j], sl[k]]
            lone = c_a & c_b & (cube == 2)
            changed += int(lone.sum())
            m[sl[1 - s0], sl[s1], sl[s2]] |= lone  # a cell beside the first, sharing a face with each
        if not changed:
            break
    return m


def keep_mass_level(parts: dict, target_mm3: float) -> float:
    """The level the members are read at so that both halves' metal outside the inside is the
    optimiser's own (`target_mm3`): a bisection, the metal falling as the level rises."""

    def volume(level: float) -> float:
        return sum(float((skin_metal(p, level) & ~p["cavity"]).sum()) for p in parts.values()) * FINE**3

    low, high = 0.15, MEMBER_LEVEL_MOST
    v_low, v_high = volume(low), volume(high)
    if not v_high <= target_mm3 <= v_low:
        level = low if target_mm3 > v_low else high
        say(f"the members read at {level:g}: the drawing's metal {v_high / 1e3:.0f} cm3 at {MEMBER_LEVEL_MOST:g} (no thinner, for the least wall), "
            f"the optimiser's {target_mm3 / 1e3:.0f} cm3; the rest is the exact geometry's")  # fmt: skip
        return level
    for _ in range(12):
        mid = 0.5 * (low + high)
        if volume(mid) > target_mm3:
            low = mid
        else:
            high = mid
    level = 0.5 * (low + high)
    say(f"the members read at {level:.3f}, so the drawing's metal is the optimiser's {target_mm3 / 1e3:.0f} cm3 (at {MEMBER_LEVEL:g}: {volume(MEMBER_LEVEL) / 1e3:.0f} cm3)")
    return level


def skin_half(p: dict, level: float, work: Path) -> cq.Shape:
    """The half as the engineer's pictures draw a housing from an organic design: the cup's exact
    wall, the interfaces the set-up has and the optimiser's members (`skin_parts`), read at
    `level` (`skin_metal`), carried past the split, then blurred once (the fillets) and contoured
    at 0.5 as `organic_half` does."""
    half, lo, ks = p["half"], p["lo"], p["ks"]
    lower = half == "motor_side"
    metal = skin_metal(p, level)
    rho = metal.astype(float)
    for k in (ks, ks + 1, ks + 2) if lower else (ks - 1, ks - 2, ks - 3):  # carried past the split, cut flat there after
        rho[:, :, k] = rho[:, :, ks - 1 if lower else ks]
    n_f = p["n_f"]
    say(f"{half}: the skin form on {n_f[0]} x {n_f[1]} x {n_f[2]} cells of {FINE:g} mm, its members read at {level:.3f}: "
        f"{(metal & ~p['cavity']).sum() * FINE**3 / 1e3:.0f} cm3 of metal")  # fmt: skip
    for sigma, contour, length in SKIN_LADDER:
        tm = _surface(rho, lo, FINE, ks, sigma, contour, half, length)
        solid = _sewn(tm, work / f"{half}_skin.stl") if tm.is_watertight else None
        ok = solid is not None and solid.isValid() and solid.Volume() > 0
        say(f"{half}: blur {sigma} cells, contour {contour}, triangles of {length:g} mm: {len(tm.faces):,} triangles, watertight {tm.is_watertight}"
            + (f"; the body {len(solid.Faces()):,} faces, {abs(solid.Volume()) / 1e3:.0f} cm3, valid {solid.isValid()}" if solid is not None else ""))  # fmt: skip
        if ok:
            return solid
    raise RuntimeError(f"{half}: no watertight, valid skin at any setting")


def _meshable_fast(shape: cq.Shape, name: str) -> cq.Shape:
    """`grammar.meshable`, its heal tried only where it has work: a face narrower than its
    HEAL_MM (2·area/perimeter, CLAUDE.md's sliver rule). The heal took 1.5-2 min a half and was
    refused in both halves of outcome_skin_6mm_drive (11 October 01:07-01:09), which had no such
    face; a half without one is checked by gmsh's volume mesh alone (`grammar._volume_meshes`)."""
    from lobed import HEAL_MM

    least = math.inf
    for face in shape.Faces():
        per = sum(e.Length() for e in face.Edges())
        if per > 0:
            least = min(least, 2.0 * face.Area() / per)
    if least < HEAL_MM:
        say(f"{name}: its narrowest face {least:.3f} mm, under {HEAL_MM:g}: healed first")
        return grammar.meshable(shape, name)
    say(f"{name}: its narrowest face {least:.2f} mm (heal at {HEAL_MM:g}): no heal; "
        f"{'fills with tets' if grammar._volume_meshes(shape) else 'does NOT fill with tets (the FE would fail)'}")  # fmt: skip
    return shape


def exact_shell(layout: dict, all_rooms: list[dict], z_split: float, half: str, wall: float, draft: float) -> cq.Shape:
    """What the contract fixes of a half, exact (since 11 October; the engineer, 10 October 23:55:
    the wall "should be drawn exactly in CAD as its known surface right from the contract"): the
    cup's outside, the inside grown by the least wall (`cup.cup`, on the inside's own draft); over
    the other half's wider opening, its rooms grown by the wall a wall thick at the split (the wall
    round both halves' insides, as the optimiser's skin is); the split flange, its sealing land
    round the inside (the layout's `flange`, from `spaces`) and the bolts' bosses on it, a flange
    thick; in the motor side, the mounts. Solid through the inside: the cavity is cut after."""
    s = layout["settings"]
    fl = layout["flange"]
    lower = half == "motor_side"
    outside, _, _ = cupmod.cup(all_rooms, z_split, half, wall, draft)
    parts = [outside]
    plate = (z_split - wall, z_split) if lower else (z_split, z_split + wall)
    parts += [cylinder(p["axis"], *plate, 2 * (p["r"] + wall)) for p in cupmod.pieces(all_rooms, z_split, "cover" if lower else "motor_side")]
    t_f = fl["thickness"]
    zf = (z_split - t_f, z_split) if lower else (z_split, z_split + t_f)
    land = fuse([cylinder(c["centre"], *zf, 2 * c["radius"]) for c in fl["outer"]])
    land = land.cut(fuse([cylinder(c["centre"], zf[0] - 1.0, zf[1] + 1.0, 2 * c["radius"]) for c in fl["inner"]]))
    parts.append(land)
    parts += [cylinder(c, *zf, s["bolt_boss"]) for c in layout["bolts"]]
    if lower:
        parts += [cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]) for m in layout["mounts"]]
    shell = fuse(parts).clean()
    say(f"{half}: the exact shell (the {wall:g} mm wall, the split flange, the bosses{', the mounts' if lower else ''}): "
        f"{len(shell.Faces())} faces, valid {shell.isValid()}")  # fmt: skip
    return shell


def fixed_metal(layout: dict, all_rooms: list[dict], z_split: float, half: str, wall: float, draft: float) -> cq.Shape:
    """The half's fixed metal as the CAD will hold it: `exact_shell` less the inside, the bearings'
    seats at their bores, the shafts' exits and the bolts' and mounts' holes. Its mass is what the
    optimiser's fixed voxels weigh (`contract_layout.py` writes it; `topo_free.build_free`'s
    `flange`), so that the budget it spends is the CAD's own remainder."""
    s = layout["settings"]
    lower = half == "motor_side"
    metal = exact_shell(layout, all_rooms, z_split, half, wall, draft).cut(cupmod.cup(all_rooms, z_split, half, wall, draft)[1])
    t_f = layout["flange"]["thickness"]
    for b in layout["bearings"]:
        if (b["side"] == "-z") == lower:
            metal = metal.cut(cylinder(b["axis"], b["z"][0], b["z"][1], b["D"]))
    for e in layout.get("exits") or []:
        if (e["z"][1] <= z_split) == lower:
            metal = metal.cut(cylinder(e["centre"], e["z"][0] - 1.0, e["z"][1] + 1.0, 2 * e["radius"]))
    for c in layout["bolts"]:
        metal = metal.cut(cylinder(c, z_split - t_f - 1.0, z_split + t_f + 1.0, s["bolt_hole"]))
    for m in layout["mounts"] if lower else []:
        metal = metal.cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
    return metal.clean()


def _params(points: np.ndarray) -> list[float]:
    """A closed loop's chord-length parameters, 0 to 1, for a periodic spline through it."""
    ring = np.vstack([points, points[:1]])
    s_ = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))])
    return list(s_ / s_[-1])


def relief_half(f: dict, half: str, draft: float) -> cq.Shape:
    """The half, its columns filled from the split out to their last metal, as exact surfaces:
    the footprint's smooth outline (and its holes) raised along the pull, drawn in by the draft
    going out, and capped by one B-spline surface through the columns' heights, smoothed over a
    voxel and a half. A height over each point of the footprint and walls drawn in going out: cast
    along the pull by construction, and no facets. Drawn from the facets of the smoothed field,
    the walls' facets tilted 1-5° either way and the pull test read 4-5 % undercut (03:07); a 3°
    lean put on the facets folded them (03:13)."""
    from scipy.ndimage import distance_transform_edt, gaussian_filter

    n, lo, h, ks = f["n"], f["lo"], f["h"], f["k_split"]
    lower = half == "motor_side"
    out = -1.0 if lower else 1.0
    z_split_vox = lo[2] + h * ks
    metal = f["rho"] >= 0.5
    kk = np.arange(n[2])[None, None, :]
    if lower:
        far = np.where(metal & (kk < ks), kk, n[2]).min(axis=2)
        foot = far < n[2]
        height = np.where(foot, lo[2] + h * far, np.nan)  # the far face of its last voxel
    else:
        far = np.where(metal & (kk >= ks), kk, -1).max(axis=2)
        foot = far >= 0
        height = np.where(foot, lo[2] + h * (far + 1), np.nan)
    xs = lo[0] + h * (np.arange(n[0]) + 0.5)
    ys = lo[1] + h * (np.arange(n[1]) + 0.5)
    # the heights carried past the footprint by the nearest one inside, so the smoothing and the
    # fit see no cliff at its edge
    _, (ii, jj) = distance_transform_edt(~foot, return_indices=True)
    filled = height[ii, jj]
    top = gaussian_filter(filled, 1.5)
    grid = [[cq.Vector(float(x), float(y), float(top[i, j])) for j, y in enumerate(ys)] for i, x in enumerate(xs)]
    surface = cq.Face.makeSplineApprox(grid, tol=0.5, maxDeg=3)
    box = surface.BoundingBox()
    if box.zmin < float(top.min()) - 5.0 or box.zmax > float(top.max()) + 5.0:
        raise RuntimeError(f"{half}: the surface's fit left the heights' range ({box.zmin:.0f}..{box.zmax:.0f})")
    reach = float(np.nanmax(np.abs(height - z_split_vox))) + 5.0
    slab = cq.Solid.extrudeLinear(surface, cq.Vector(0.0, 0.0, -out * (reach + 40.0)))  # from the cap back past the split
    soft = gaussian_filter(foot.astype(float), 1.0)
    base = z_split_vox - out * 2 * h  # two voxels past the split, cut flat there after
    pieces = []
    for outer, holes in fb.loops(soft, xs, ys, 0.5):
        # The walls straight along the pull (the contract's draft is 0°, A11): exact, so the pull
        # test reads them as along it. Drawn in by the draft over a whole half's depth, a long
        # footprint pinched at its narrow necks and the motor side's loft failed (03:18).
        try:
            face = cq.Face.makeFromWires(fb._spline(outer, base, _params(outer)), [fb._spline(hl, base, _params(hl)) for hl in holes])
            prism = cq.Solid.extrudeLinear(face, cq.Vector(0.0, 0.0, out * (reach + 2 * h)))
        except Exception:  # noqa: BLE001 - an outline OCC refuses is left out, said below
            say(f"{half}: an outline of {len(outer)} points refused")
            continue
        piece = prism.intersect(slab)
        if piece.isValid() and piece.Volume() > 1000.0:
            pieces.append(piece)
    if not pieces:
        raise RuntimeError(f"{half}: no relief drawn")
    body = pieces[0]
    for p in pieces[1:]:
        body = body.fuse(p)
    say(f"{half}: the relief, {len(pieces)} piece(s), {len(body.Faces())} faces, {body.Volume() / 1e3:.0f} cm3, valid {body.isValid()}")
    return body


ROUTE = "mesh"  # the skin drawing's booleans: "mesh" (manifold3d on watertight meshes, `mesh_route.py`; 11 October) or "brep" (OCC)


def contour_pieces(rho: np.ndarray, lo, sigma: float, level: float) -> list:
    """Every watertight piece of a grid's contour (`mesh_route.contour` keeps the largest only): the
    mounts' rims past their brackets' rooms, one a mount."""
    import trimesh
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes

    field = gaussian_filter(np.pad(rho.astype(float), 2), sigma=sigma)
    if field.max() <= level:
        return []
    verts, faces, _, _ = marching_cubes(field, level=level, spacing=(FINE, FINE, FINE))
    verts += np.asarray(lo) - 2 * FINE + 0.5 * FINE
    tm = trimesh.Trimesh(verts, faces[:, ::-1], process=True)
    out = []
    for piece in tm.split(only_watertight=True):
        if piece.volume < 0:
            piece.invert()
        if piece.volume > 1.0:  # mm³
            out.append(piece)
    return out


def split_run(metal: np.ndarray, ks: int, lower: bool) -> np.ndarray:
    """Each column's metal in one run from the split out (the motor side's from its top cell down,
    the cover's from its bottom cell up)."""
    run = np.zeros_like(metal)
    if lower:
        run[:, :, :ks] = np.cumprod(metal[:, :, ks - 1 :: -1], axis=2)[:, :, ::-1].astype(bool)
    else:
        run[:, :, ks:] = np.cumprod(metal[:, :, ks:], axis=2).astype(bool)
    return run


def height_field(metal: np.ndarray, p: dict, z_split: float, lower: bool, depth_cells: np.ndarray | None = None):
    """A half's metal (`skin_metal`: each column one run from the split out) as one watertight
    surface castable along its pull by construction (LOP-23, 11 October 09:50). Each column's depth
    off the split is smoothed in plan over `HEIGHT_SIGMA` cells (the depths' sum, the volume, kept),
    and the surface is the zero of the least of three margins: past the smoothed far surface, short
    of a slab carried `CARRY` cells past the split (cut flat after), and inside the footprint (where
    the smoothed depth is half a cell or more). Each region meets a line along the pull in one
    interval, so their meet does too: no overhang. The blurred grid's contour bulged sideways where
    two columns stepped, and the rays read 0.4-1.1 % of each half undercut there (09:27).

    Only each column's run from the split is drawn so: a column's metal past a kept-clear space (the
    vehicle's bracket over a mount, wider than its boss) is a second run, which the caller draws as
    the grid's contour (`lower_runs`); folded into one run, the mounts' rims went and all three
    mounts came off (09:50)."""
    import trimesh
    from scipy.ndimage import gaussian_filter
    from skimage.measure import marching_cubes

    raw = split_run(metal, p["ks"], lower).sum(axis=2).astype(float)  # cells
    if depth_cells is not None:
        # a height-field run's own continuous depths (LOP-23, `smooth_heights`), not whole cells:
        # the surface follows the optimiser's heights to a fraction of a cell
        depth = np.asarray(depth_cells, float)
    else:
        # smoothed with the kept-clear columns weighted out (the brackets' rooms, the exits, the
        # sockets): blurred across a bracket's room, an arm's depth rose short of its mount (09:54)
        w = (~p["clear"].any(axis=2)).astype(float)
        depth = gaussian_filter(raw * w, sigma=HEIGHT_SIGMA) / np.maximum(gaussian_filter(w, sigma=HEIGHT_SIGMA), 1e-6)
        depth = np.where(w > 0, depth, raw)
    nz = metal.shape[2]
    zc = p["lo"][2] + FINE * (np.arange(nz) + 0.5)  # the cells' centres
    s = (z_split - zc) / FINE if lower else (zc - z_split) / FINE  # cells off the split into the half
    margin = np.minimum(depth[:, :, None] - s[None, None, :], s[None, None, :] + CARRY)
    margin = np.minimum(margin, (depth - 0.5)[:, :, None])
    # no surface within 20 µm of a node: a continuous depth landing on a cell's centre (the sealing land's least height,
    # 9 mm, where the optimiser added nothing) put vertices nanometres apart, which the vertex merge joined, tearing the
    # surface open, and the half's body was dropped (sem1h_5.5kg, 13 October 00:41; a 1e-6 nudge was not enough)
    margin = np.where(np.abs(margin) < 1e-2, np.where(margin >= 0, 1e-2, -1e-2), margin)
    field = np.pad(margin, 2, constant_values=-1.0)
    verts, faces, _, _ = marching_cubes(field, level=0.0, spacing=(FINE, FINE, FINE))
    verts += np.asarray(p["lo"]) - 2 * FINE + 0.5 * FINE
    tm = trimesh.Trimesh(verts, faces[:, ::-1], process=True)
    pieces = tm.split(only_watertight=True)
    tm = max(pieces, key=lambda m: m.volume) if len(pieces) else tm
    if tm.volume < 0:
        tm.invert()
    return tm


def continuous_depth(tops: dict, p: dict, half: str, raw: np.ndarray) -> np.ndarray:
    """(LOP-28, `HEIGHT_DRAW`) Each fine plan cell's depth off the split, in cells, from the run's continuous heights
    (`roughness.tops`' `top_true`: each first-run column's height counted over its own free voxels, any frozen voxels
    between them passed over, its run's frozen voxels beyond kept) interpolated bilinearly between the columns' centres
    over the columns that have one; where fewer than half the neighbours do (the fully frozen columns: the bolts'
    bosses), the voxels' own depth `raw`."""
    from scipy.ndimage import map_coordinates

    h, lo, n = tops["h"], tops["lo"], tops["n"]
    top = tops["top_true"]  # mm off the split: the height over the column's own free voxels, its frozen ones kept
    sel = (tops["half"] == (1 if half == "cover" else 0)) & (tops["run"] == 1) & np.isfinite(top)
    c_map, v_map = np.zeros((n[0], n[1])), np.zeros((n[0], n[1]))
    c_map[tops["pts"][sel, 0], tops["pts"][sel, 1]] = top[sel]
    v_map[tops["pts"][sel, 0], tops["pts"][sel, 1]] = 1.0
    gi = (p["lo"][0] + FINE * (np.arange(p["n_f"][0]) + 0.5) - lo[0]) / h - 0.5
    gj = (p["lo"][1] + FINE * (np.arange(p["n_f"][1]) + 0.5) - lo[1]) / h - 0.5
    at = np.meshgrid(gi, gj, indexing="ij")
    num = map_coordinates(c_map * v_map, at, order=1, mode="constant")
    den = map_coordinates(v_map, at, order=1, mode="constant")
    return np.where(den >= 0.5, num / np.maximum(den, 1e-6) / FINE, raw)


def member_level(h: float, wall: float) -> float:
    """The level the mesh route reads the members at (LOP-23): `MEMBER_LEVEL`, unless a member one
    voxel thick read there would be drawn thinner than the least wall. Blurred over `MEMBER_BLUR`
    voxels, such a member peaks at 0.79 with 0.11 beside it, so at 0.5 it is drawn 0.84 of its
    voxel thick: 5.0 mm at 6 mm voxels, but 3.4 mm at 4 mm, under the contract's 4 mm. Then it is
    read at the level that draws it its voxel's thickness, 0.45 (a thicker member grows by 0.07 of
    a voxel each side)."""
    from scipy.ndimage import gaussian_filter1d

    impulse = np.zeros(9)
    impulse[4] = 1.0
    blurred = gaussian_filter1d(impulse, MEMBER_BLUR)
    peak, beside = blurred[4], blurred[5]
    drawn = 2.0 * (peak - MEMBER_LEVEL) / (peak - beside) * h
    return MEMBER_LEVEL if drawn >= wall else 0.5 * (peak + beside)


def build_mesh(run: str, stem: str) -> dict:
    """The skin drawing (FORM "skin") by the mesh route (`mesh_route.py`): each half's members the
    blurred grid's contour by marching cubes, fused with the exact shell, cut flat at the split and
    by every exact cut `build` makes (the contract's exits, the brackets' rooms, the bolts' sockets,
    the cavity, the bearings' bores and their paths in, the mounts' and the bolts' holes), all as
    watertight meshes by manifold3d. Writes `<stem>_<half>.stl` and `<stem>_organic_<half>.stl`
    (before the exact cuts) and their records."""
    import time as _time

    import mesh_route as mr

    t0 = _time.time()
    layout = json.loads((OUT / f"{layout_of(run)}.json").read_text(encoding="utf-8"))
    s = layout["settings"]
    if not layout.get("flange"):
        raise ValueError("the mesh route draws the contract's layout of 11 October (its `flange`)")
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial, axial = value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm")
    z_split, wall, draft = layout["z"]["split"], s["wall"], s.get("draft", 0.0)
    bearings, bolts, mounts = layout["bearings"], layout["bolts"], layout["mounts"]
    brackets = {b["name"]: b for b in layout.get("brackets", [])}
    t_f = s["flange_thickness"]
    f = field_of(run)
    all_rooms = cupmod.rooms(chain, radial, axial)
    run_rec = OUT / f"{run}.json"
    # LOP-27, the empty start: the run's walls are its own metal, drawn from the field with everything else; no exact shell fused on
    empty = bool(json.loads(run_rec.read_text(encoding="utf-8")).get("empty")) if run_rec.exists() else False
    protect = bool(json.loads(run_rec.read_text(encoding="utf-8")).get("protect")) if run_rec.exists() else False  # LOP-28
    towers = bool(json.loads(run_rec.read_text(encoding="utf-8")).get("towers", True)) if run_rec.exists() else True  # LOP-29
    if empty and (IMPLICIT or PARTS or CLEAN or SKELETON or HEIGHT_FIELD or CLEAN_MEMBERS != "0"):
        raise ValueError("an empty start's run is drawn from its field alone: no implicit, parts, clean, skeleton or height-field drawing")
    tops = None
    if HEIGHT_DRAW:  # LOP-28: the surface from the run's continuous heights (`continuous_depth`)
        if not empty or EXACT_WALLS or FAITHFUL > 0 or SDF_SIGMA > 0:
            raise ValueError("LOOP_HEIGHT_DRAW draws an empty start's run alone (no exact walls, faithful or SDF drawing with it)")
        import roughness

        tops = roughness.tops(run)
    # (LOP-28) a protected run's frozen voxels under its exact interfaces drawn only where its metal stands on them; the
    # rest (a seat's ring past its boss) drawn, so the inside stays closed (prot1_5.5kg leaked at the output seat's end)
    mem = members_of(run, all_frozen=empty and not protect, protected=protected_voxels(run, layout) if (empty and protect) else None)
    if empty and EXACT_WALLS:  # the run's metal beyond its least walls; the walls are drawn exact (`exact_walls`)
        import exact_walls as ew

        mem = {"placed": ew.extra_placed(run), "network": None}
    spline = spline_cols_of(run)  # (LOP-30) a spline run is drawn from its fields (`spline_members`)
    voxel_note = None
    if spline is None and VOXEL_SMOOTH > 0:  # (LOP-30, 15 October) a height-field run drawn as a spline run (`voxel_cols_as_spline`)
        spline = voxel_cols_as_spline(run, VOXEL_SMOOTH, VOXEL_ROUND)
        voxel_note = {"plan_sigma_mm": VOXEL_SMOOTH, "round_mm": VOXEL_ROUND, "fillet_mm": VOXEL_FILLET, "fair": VOXEL_FAIR or None}
    if spline is not None and not (empty and EXACT_WALLS):
        raise ValueError("a spline run is drawn on the empty start with its walls exact (LOOP_EXACT_WALLS=1)")
    if spline is not None and run_rec.exists():  # (LOP-30) the section rule's fillet, from the run's own record
        spline["fillet_mm"] = float((json.loads(run_rec.read_text(encoding="utf-8")).get("spline") or {}).get("fillet_mm") or 0.0)
    if voxel_note is not None:
        spline["fillet_mm"] = VOXEL_FILLET
    parts: dict = {}  # (LOP-30) each half's grids made in its turn and freed after it (`LOOP_DRAW_FINE`: 36 M nodes a half at 1 mm)
    level = member_level(float(f["h"]), wall)
    if os.environ.get("LOOP_MEMBER_LEVEL"):  # LOP-27: read the members lower so a one-voxel link survives (case3_web_5.5kg lost mount-3's arm at 0.5)
        level = float(os.environ["LOOP_MEMBER_LEVEL"])
    clean_note = None
    if CLEAN_MEMBERS != "0":  # each member drawn clean (`clean_members.py`) or the layout as ribs (`clean_ribs.py`)
        import clean_members
        import clean_ribs
        import smooth_heights

        builder = {"ribs": clean_ribs, "heights": smooth_heights}.get(CLEAN_MEMBERS, clean_members)
        clean_note = {"how": CLEAN_MEMBERS if CLEAN_MEMBERS in ("ribs", "heights") else "members"}
        level = 0.5
    halves, organic, kept_of, held = {}, {}, {}, list(mounts)
    faithful_note = {}
    for half in ("motor_side", "cover"):
        p = parts[half] = skin_parts(f, mem, layout, all_rooms, z_split, half, empty=empty, protect=protect, towers=towers, spline=spline)
        if CLEAN_MEMBERS != "0":
            p["members"], clean_note[half] = builder.members_field(run, p, half, SKIN_BURY, FINE)
        t1 = _time.time()
        lower = half == "motor_side"
        metal = skin_metal(p, level)
        rho = metal.astype(float)
        ks = p["ks"]
        for k in (ks, ks + 1, ks + 2) if lower else (ks - 1, ks - 2, ks - 3):  # carried past the split, cut flat after
            rho[:, :, k] = rho[:, :, ks - 1 if lower else ks]
        if p.get("spline"):
            # (LOP-30) the members from the spline fields as they are (linear in the outline field and the height, so the
            # contour falls on their zero and their top), the fixed parts blurred as the plain drawing blurs them, the
            # kept-clear spaces emptied, the exact faces held; no cube held, no smoothing after
            from scipy.ndimage import gaussian_filter

            if p.get("clear_sdf") is not None:
                # (15 October 03:30) the members cut by the kept-clear spaces smoothly, FINE_MARGIN past them (their
                # signed distance's ramp, `skin_parts`); the fixed parts emptied cell by cell as before (a bolt's socket
                # starts at its boss's underside, the head's seat, which a smooth margin would have eaten)
                import exact_walls as ew

                own = np.where(p["side"] & ~p["cavity"], np.minimum(p["members"], ew.ramp(FINE_MARGIN - p["clear_sdf"], FINE)), 0.0)
                fixed_s = gaussian_filter(p["fixed"].astype(np.float32), sigma=SKIN_LADDER[0][0])
                # the fixed parts' blurred copy cut smoothly at the spaces themselves (no margin): emptied cell by cell it
                # left flags at the bolts' bosses' rims on the 1 mm grid (`spl8f`'s cover); their exact faces, the
                # head's seat among them, are the exact faces' ramp below (`held_up`)
                fixed_s = np.minimum(fixed_s, ew.ramp(-p["clear_sdf"], FINE)) if p.get("exact") is not None else np.where(p["clear"], 0.0, fixed_s)
                rho_s = np.maximum(fixed_s, own)
            else:
                own = np.where(p["side"] & ~p["cavity"] & ~p["clear"], p["members"], 0.0)
                rho_s = np.maximum(gaussian_filter(p["fixed"].astype(np.float32), sigma=SKIN_LADDER[0][0]), own)
                rho_s[p["clear"]] = 0.0
            held_up = np.zeros(rho_s.shape, np.float32) if p.get("exact") is None else p["exact"].copy()
            for k in (ks, ks + 1, ks + 2) if lower else (ks - 1, ks - 2, ks - 3):
                rho_s[:, :, k] = rho_s[:, :, ks - 1 if lower else ks]
                held_up[:, :, k] = held_up[:, :, ks - 1 if lower else ks]
            rho_s = np.maximum(rho_s, held_up)
            # the model reads the outline on these very nodes (each cube's share in plan its points' share inside), so the
            # drawing holds what the model holds without holding cube centres (which raised ridges every 4 mm). A node
            # exactly at the level makes marching cubes' triangles degenerate and the surface leaky
            rho_s[np.abs(rho_s - 0.5) < 1e-6] = 0.5 + 1e-5
            surface = mr.contour(rho_s, p["lo"], FINE, 0.0, 0.5)
            if SMOOTH_PASSES:  # (15 October 14:10) Taubin's passes on the spline drawing too (the exact cuts follow)
                import trimesh

                trimesh.smoothing.filter_taubin(surface, lamb=0.5, nu=0.53, iterations=SMOOTH_PASSES)
            body = mr.from_trimesh(surface)
        elif CLEAN:  # LOP-25: the run's members drawn clean on the exact shell (`implicit_draw.members_body`)
            import implicit_draw as idr

            body = idr.members_body(run, half, layout, all_rooms, z_split, wall, *(IMPLICIT[1:] if IMPLICIT else (4.0, 3.0, 1.25)))
        elif PARTS:  # LOP-26: production's parts, the optimiser's own, on the exact shell (`implicit_draw.parts_body`)
            import implicit_draw as idr

            body = idr.parts_body(PARTS, half, layout, all_rooms, z_split, wall, *(IMPLICIT[1:] if IMPLICIT else (4.0, 3.0, 1.25)))
        elif IMPLICIT:  # LOP-24/25: the shell and its features one smooth solid in production's forms (`implicit_draw.py`)
            import implicit_draw as idr

            body = idr.half_body(run, half, layout, all_rooms, z_split, wall, *IMPLICIT)
        elif HEIGHT_FIELD or tops is not None:
            depth_cells = None
            if tops is not None:  # LOP-28: the empty start's tops from its continuous heights, the voxels' where none
                p["depth_cont"] = continuous_depth(tops, p, half, split_run(metal, ks, lower).sum(axis=2).astype(float))
            if p.get("depth_cont") is not None:
                # the run's continuous depths where its members stand, the shell's own elsewhere, then
                # the roots' fillets rolled over them as a continuous map (`skin_metal`'s ball)
                from scipy.ndimage import grey_closing

                fixed_run = split_run(p["fixed"], ks, lower)  # the grid's fixed parts stand SKIN_BURY under their exact faces
                shell = np.where(fixed_run.any(axis=2), fixed_run.sum(axis=2) + (0.0 if empty else SKIN_BURY / FINE), 0.0)
                depth_cells = np.maximum(p["depth_cont"], shell)
                if ROOT_FILLET > 0:
                    r = ROOT_FILLET / FINE
                    k = int(np.ceil(r))
                    i, j = np.mgrid[-k : k + 1, -k : k + 1]
                    ball = np.where(i**2 + j**2 <= r * r, np.sqrt(np.maximum(r * r - i**2 - j**2, 0.0)) - r, -1e6)
                    rolled = grey_closing(depth_cells, structure=ball)
                    depth_cells = np.where(depth_cells > 0, np.maximum(depth_cells, rolled), depth_cells)
            body = mr.from_trimesh(height_field(metal, p, z_split, lower, depth_cells))
            rest = metal & ~split_run(metal, ks, lower)  # the runs past a kept-clear space: the mounts' rims
            if rest.sum() > 8:
                for piece in contour_pieces(rest, p["lo"], SKIN_LADDER[0][0], SKIN_LADDER[0][1]):
                    body = body + mr.from_trimesh(piece)
        elif SKELETON:  # LOP-25, approach 2's generator B: the members rebuilt along their skeleton (`skeleton_members.py`)
            import skeleton_members as sk

            fixed_here = np.zeros(rho.shape, bool)
            fixed_here[..., : p["fixed"].shape[2]] = p["fixed"]
            # the plan cells within the shell's outline (its rooms' outsides): the end walls' members read apart from the side walls'
            gx = p["lo"][0] + FINE * (np.arange(rho.shape[0]) + 0.5)
            gy = p["lo"][1] + FINE * (np.arange(rho.shape[1]) + 0.5)
            px_, py_ = np.meshgrid(gx, gy, indexing="ij")
            inside = np.zeros(rho.shape[:2], bool)
            for pc in cupmod.pieces(all_rooms, z_split, half):
                inside |= np.hypot(px_ - pc["axis"][0], py_ - pc["axis"][1]) <= float(pc["r"]) + wall
            body = sk.members_body((rho >= 0.5) & ~fixed_here, p["lo"], FINE, *SKELETON, inside=inside)
        else:
            if SDF_SIGMA > 0:
                # the members' webs thinner than about two cells and their pinholes taken out first: the
                # smoothing thinned them further and FE's coarsening folded them (the mounts' arms,
                # outcome_hfsdf_4mm_7.0kg, 16:15); the fixed parts as they are (the exact shell covers them)
                from scipy.ndimage import binary_closing, binary_opening, generate_binary_structure

                six = generate_binary_structure(3, 1)
                fixed_here = np.zeros(rho.shape, bool)
                fixed_here[..., : p["fixed"].shape[2]] = p["fixed"]
                own = (rho >= 0.5) & ~fixed_here
                own = binary_opening(binary_closing(own, six), six)
                surface = mr.contour_sdf(((rho >= 0.5) & fixed_here) | own, p["lo"], FINE, SDF_SIGMA)
            elif FAITHFUL > 0:  # LOP-27: smooth between the voxels' centres, unmoved at them, the volume kept
                surface, faithful_note[half] = mr.faithful(rho, p["lo"], FINE, FAITHFUL, SKIN_LADDER[0][0], SKIN_LADDER[0][1], ridge=FAITHFUL_RIDGE)
                say(f"{half}: drawn faithful and smooth: {faithful_note[half]}")
            else:
                held_up = p["keep"].astype(np.float32) if KEEP_CUBES else np.zeros(rho.shape, np.float32)
                if KEEP_CUBES and p.get("keep_soft") is not None:  # (LOP-29) the cubes held smooth (`LOOP_SMOOTH_KEEP`)
                    held_up = p["keep_soft"]
                if p.get("exact") is not None:  # (LOP-29) the exact faces' ramp, carried past the split as rho is
                    held_up = np.maximum(held_up, p["exact"])
                    for k in (ks, ks + 1, ks + 2) if lower else (ks - 1, ks - 2, ks - 3):
                        held_up[:, :, k] = held_up[:, :, ks - 1 if lower else ks]
                surface = mr.contour(rho, p["lo"], FINE, SKIN_LADDER[0][0], SKIN_LADDER[0][1], keep=held_up if held_up.any() else None)
            if SMOOTH_PASSES:
                import trimesh

                trimesh.smoothing.filter_taubin(surface, lamb=0.5, nu=0.53, iterations=SMOOTH_PASSES)
            body = mr.from_trimesh(surface)
        if not (IMPLICIT or PARTS or CLEAN or empty):  # the implicit body holds its shell, rounded and filleted; the empty start has none
            body = body + mr.from_shape(exact_shell(layout, all_rooms, z_split, half, wall, draft))
        body = body ^ mr.half_space(z_split, keep_below=lower)  # cut flat at the split
        organic[half] = body
        cuts = []
        for e in layout.get("exits") or []:
            z0, z1 = e["z"]
            if (z1 <= z_split) == lower:
                cuts.append(mr.cylinder(e["centre"], z0 - 1.0, z1 + 1e-3, 2 * e["radius"]) if lower else mr.cylinder(e["centre"], z0 - 1e-3, z1 + 1.0, 2 * e["radius"]))
        for m in mounts:  # the vehicle's bracket and bolt beyond both faces: the layout's rooms (as tall as the mount, 13 October)
            for end in ("-z", "+z"):
                room = brackets[f"{m['name']} bracket {end}"]
                cuts.append(mr.cylinder(m["centre"], room["z"][0], room["z"][1], 2 * room["radius"]))
        cuts.append(mr.from_shape(cupmod.cup(all_rooms, z_split, half, wall, draft)[1]))  # the inside, exact
        for b in bearings:
            if (b["side"] == "-z") != lower:
                continue
            z0, z1 = b["z"]
            cuts.append(mr.cylinder(b["axis"], z0, z1, b["D"]))
            cuts.append(mr.cylinder(b["axis"], *sorted((z1 if lower else z0, z_split)), b["D"] + 1.0))  # its path in from the split
        for m in mounts if lower else []:
            cuts.append(mr.cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
        # A bolt joins the halves where the body holds most of its boss; its head's seat and a hex
        # key's room cut, its hole through
        kept = []
        for c in bolts:
            boss = mr.cylinder(c, z_split - t_f, z_split, s["bolt_boss"]) if lower else mr.cylinder(c, z_split, z_split + t_f, s["bolt_boss"])
            if mr.volume_of(body ^ boss) > 0.6 * mr.volume_of(boss):
                kept.append(c)
                d_s, h_s = s.get("bolt_socket") or SOCKET  # (LOP-29) the layout's
                cuts.append(mr.cylinder(c, z_split - t_f - h_s, z_split - t_f, d_s) if lower else mr.cylinder(c, z_split + t_f, z_split + t_f + h_s, d_s))
                cuts.append(mr.cylinder(c, z_split - t_f - 1.0, z_split + t_f + 1.0, s["bolt_hole"]))
        import manifold3d as mf

        body = body - mf.Manifold.batch_boolean(cuts, mf.OpType.Add)
        body, dropped = mr.largest(body)
        if dropped:
            say(f"{half}: {dropped / 1e3:.1f} cm3 of loose pieces dropped")
        if lower:
            held = []
            for m in mounts:
                ring = mr.cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]) - mr.cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"])
                if mr.volume_of(body ^ ring) > 0.6 * mr.volume_of(ring):
                    held.append(m)
        halves[half], kept_of[half] = body, kept
        tm = mr.to_trimesh(body)
        tm.export(str(OUT / f"{stem}_{half}.stl"))
        tm.export(str(OUT / f"{stem}_{half}.ply"))  # indexed: manifold3d's own topology, for FE (`fe.mesh_stl`)
        mr.to_trimesh(organic[half]).export(str(OUT / f"{stem}_organic_{half}.stl"))
        say(f"{half}: by the mesh route in {_time.time() - t1:.1f} s: {len(tm.faces):,} triangles, watertight {tm.is_watertight}, "
            f"{mr.volume_of(body) / 1e3:.0f} cm3, {len(kept)} of {len(bolts)} bolts' bosses held")  # fmt: skip
        parts[half] = {"clear": p["clear"], "lo": p["lo"]}  # what the cube check reads; the half's grids freed
        p = metal = rho = None
    fidelity = cube_fidelity(mem["placed"], f, halves, organic, parts, z_split, gate=spline is None) if KEEP_CUBES else None
    both = set(map(tuple, kept_of["motor_side"])) & set(map(tuple, kept_of["cover"]))
    bolts_used = [list(c) for c in bolts if tuple(c) in both]
    if len(held) < len(mounts):
        say(f"{stem}: the body holds {len(held)} of the layout's {len(mounts)} mounts")
    mass = {half: mr.volume_of(body) * s["density"] for half, body in halves.items()}
    record = {**layout, "stem": stem, "form": "outcome", "drawing": "one field" if empty else "skin", "route": "mesh", "skin_bosses": False, "empty": empty,
              "skin": {"wall_mm": None if empty else s["wall"], "exact": not empty, "grid_bury_mm": 0.0 if empty else SKIN_BURY, "members_level": level,
                       "keeps_mass": False, "root_fillet_mm": ROOT_FILLET,
                       "network_drawn": mem.get("network") is not None, "clean_members": clean_note, "smooth_passes": SMOOTH_PASSES, "sdf_sigma_mm": SDF_SIGMA,
                       "faithful_mm": FAITHFUL, "faithful": faithful_note or None, "exact_walls": bool(empty and EXACT_WALLS),
                       "height_draw": tops is not None, "protect": bool(empty and protect), "panel_spokes": os.environ.get("LOOP_PANEL_SPOKES") or None, "spoke_halves": os.environ.get("LOOP_SPOKE_HALVES", "cover,motor_side") if os.environ.get("LOOP_PANEL_SPOKES") else None, "panel_spokes_motor": os.environ.get("LOOP_PANEL_SPOKES_MOTOR") or None, "lug_webs": os.environ.get("LOOP_LUG_WEBS") or None,
                       "keep_cubes": KEEP_CUBES and spline is None, "fidelity": fidelity, "exact_faces": bool(EXACT_FACES and empty and EXACT_WALLS),
                       "spline": spline is not None, "grid_mm": FINE, "draw_smooth_mm": DRAW_SMOOTH, "voxel_smooth": voxel_note,
                       "draw_smooth_range_mm": DRAW_SMOOTH_RANGE},  # fmt: skip
              "outcome_of": run, "ribs": [], "bolts": bolts_used, "mounts": held, "mounts_layout": mounts,
              "mass_kg": {**mass, "total": sum(mass.values())}, "faces": {},
              "files": {half: f"{stem}_{half}.stl" for half in halves}, "seconds": _time.time() - t0}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1, default=list), encoding="utf-8")
    mass_o = {half: mr.volume_of(body) * s["density"] for half, body in organic.items()}
    shown = {**record, "stem": f"{stem}_organic", "form": "organic", "organic_of": stem, "mass_kg": {**mass_o, "total": sum(mass_o.values())},
             "files": {half: f"{stem}_organic_{half}.stl" for half in organic}}  # fmt: skip
    (OUT / f"{stem}_organic.json").write_text(json.dumps(shown, indent=1, default=list), encoding="utf-8")
    say(f"{stem}: {record['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f}); "
        f"bolts joining the halves {len(bolts_used)} of {len(bolts)}; drawn in {record['seconds']:.0f} s")  # fmt: skip
    return record


def layout_of(run: str) -> str:
    """The layout record the run was given: its record's `layout` (the contract's since 10
    October 14:00, written by contract_layout.py; grammar4 before)."""
    record = OUT / f"{run}.json"
    return json.loads(record.read_text(encoding="utf-8")).get("layout", LAYOUT) if record.exists() else LAYOUT


def build(run: str, stem: str) -> dict:
    layout = json.loads((OUT / f"{layout_of(run)}.json").read_text(encoding="utf-8"))
    s = layout["settings"]
    # The contract's layout (GBX-5): no motor flange, and its own exits (each seal's bore and the
    # half-shafts' joints) and the vehicle's bracket room at each mount, as the optimiser had them.
    flanged = "motor_ring" in s
    exits, brackets = layout.get("exits"), {b["name"]: b for b in layout.get("brackets", [])}
    spec, _ = load_and_validate(convex.CONTRACT)
    chain = complete_chain(spec)
    gaps = spec.requirement.shaft_layout
    radial, axial = value_in(gaps.min_radial_clearance, "mm"), value_in(gaps.min_axial_clearance, "mm")
    z_split, wall, draft = layout["z"]["split"], s["wall"], s.get("draft", 1.5)
    bearings, bolts, mounts, motor_holes = layout["bearings"], layout["bolts"], layout["mounts"], layout["motor_holes"]
    axis = {st.shaft: tuple(st.axis) for st in chain.layout.shafts}
    ends = {st.shaft: st.ends for st in chain.layout.shafts}
    z_face = min(e[0] for e in ends.values())
    t_ring, (ring_in, ring_out) = (s["motor_ring_thickness"], s["motor_ring"]) if flanged else (0.0, (0.0, 0.0))
    f = field_of(run)
    all_rooms = cupmod.rooms(chain, radial, axial)
    # Every interface solid a voxel past its exact size, every kept-clear space empty a voxel past
    # its boundary, before the smoothing: the exact cuts then run through solid metal or through
    # empty space, never along the smooth surface (the motor side of outcome_run3 would not mesh
    # where the cut of the motor's room grazed it, 02:39). The surfaces left are as a casting's
    # are: the skin as cast, the faces and bores machined.
    n, lo, h = f["n"], f["lo"], f["h"]
    X, Y, Z = np.meshgrid(*(lo[i] + h * (np.arange(n[i]) + 0.5) for i in range(3)), indexing="ij")
    clear = np.zeros(tuple(n), bool)
    solid = np.zeros(tuple(n), bool)
    if flanged:
        r_in = np.hypot(X - axis["input"][0], Y - axis["input"][1])
        clear |= (r_in < ring_out / 2 + 15.0 + MARGIN) & (Z < z_face - t_ring - h)
        solid |= (r_in >= ring_in / 2 - MARGIN) & (r_in <= ring_out / 2 + MARGIN) & (Z >= z_face - t_ring - h) & (Z <= z_face + MARGIN)
    if exits is None:
        r_out = np.hypot(X - axis["output"][0], Y - axis["output"][1])
        clear |= (r_out < 45.0 + MARGIN) & ((Z < ends["output"][0]) | (Z > ends["output"][1]))
    else:
        # each exit from its end face outward, a margin wider (not deeper: its end face is wall)
        for e in exits:
            r_e = np.hypot(X - e["centre"][0], Y - e["centre"][1])
            clear |= (r_e < e["radius"] + MARGIN) & (Z >= e["z"][0]) & (Z <= e["z"][1])
    for m in mounts:
        r_m = np.hypot(X - m["centre"][0], Y - m["centre"][1])
        room = brackets[f"{m['name']} bracket -z"]["radius"] if brackets else s["mount_diameter"] / 2 + MOUNT_ROOM
        clear |= (r_m < room + MARGIN) & ((Z < m["z"][0] - h) | (Z > m["z"][1] + h))
        solid |= (r_m <= s["mount_diameter"] / 2 + MARGIN) & (Z >= m["z"][0] - h) & (Z <= m["z"][1] + h)
    for b in bearings:
        r_b = np.hypot(X - b["axis"][0], Y - b["axis"][1])
        solid |= (r_b <= b["D"] / 2 + 3.0 + MARGIN) & (Z >= b["z"][0] - 3.0 - h) & (Z <= b["z"][1] + 3.0 + h)
    for c in bolts:
        r_c = np.hypot(X - c[0], Y - c[1])
        solid |= (r_c <= s["bolt_boss"] / 2 + MARGIN / 2) & (np.abs(Z - z_split) <= s["flange_thickness"] + h)
        # The socket's room over the boss (cut exact below) inside metal too, a margin past its
        # cut: cut against the smooth wall beside the boss, it left blades round 6 of the 10
        # bolts, two thirds of all the folds over 120° (outcome_split_7.73, 05:40). The bolts so
        # stand in columns, as the trade's housings draw them.
        solid |= (r_c <= SOCKET[0] / 2 + MARGIN) & (np.abs(Z - z_split) <= s["flange_thickness"] + SOCKET[1] + h)
    # The joint's sealing face: a band round the cup's rim, two voxels wide past the cavity (its
    # wall and a ledge), a flange thick each side; an interface as the seats are (the paper's
    # preserved rim). grammar4's whole flange plate, its outline grown by its lip, weighed 1.9 kg
    # more and shadowed the optimiser's struts under it: 15 % of the motor side undercut (02:59).
    from scipy.ndimage import binary_dilation

    k_split = f["k_split"]
    footprint = rooms_mask(f, all_rooms, z_split, "motor_side")[:, :, k_split - 1] | rooms_mask(f, all_rooms, z_split, "cover")[:, :, k_split]
    band = binary_dilation(footprint, iterations=2)
    solid |= band[:, :, None] & (np.abs(Z - z_split) <= s["flange_thickness"])
    halves, organic = {}, {}
    mem = members_of(run) if FORM == "skin" else None
    parts, level = {}, None
    if FORM == "skin":
        parts = {half: skin_parts(f, mem, layout, all_rooms, z_split, half) for half in ("motor_side", "cover")}
        level = MEMBER_LEVEL
        if KEEP_MASS:  # the optimiser's whole mass, its budget (`topo_free.py`'s record)
            budget = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))["budget_kg"]
            level = keep_mass_level(parts, budget / s["density"])
    with tempfile.TemporaryDirectory() as tmp:
        for half in ("motor_side", "cover"):
            lower = half == "motor_side"
            room = rooms_mask(f, all_rooms, z_split, half)
            rho = np.maximum(f["rho"], room.astype(float))
            rho[clear] = 0.0
            rho[solid] = 1.0
            # The least wall: a voxel of metal all round the cup, whatever the field put there. The
            # optimiser's one-voxel skin, its rooms rounded to the voxels' centres and the cavity
            # drafted, came out 2.5-7.5 mm, and 113-147 cm² of each half lay under the contract's
            # 4 mm (outcome_run3, 02:53).
            from scipy.ndimage import binary_dilation as grow

            if h < 6.0 - 1e-6:  # a 5 mm skin; on 6 mm voxels the layer doubled the walls (outcome_split_7.73's motor side 6.27 kg, 05:05)
                rho[grow(room, iterations=1) & ~clear] = 1.0
            # Along the pull, each column of the half one piece from the split out to its last
            # metal, then the kept-clear spaces emptied again: the contract's pull directions are a
            # hard rule, and the smoothed field's overhangs left 6 % of each half undercut
            # (outcome_run3, 02:53). The optimiser's struts and belts so stand on the flange as
            # webs and gussets, its mounts as columns, as the trade's housings draw them.
            metal = rho >= 0.5
            ks = f["k_split"]
            kk = np.arange(n[2])[None, None, :]
            if lower:
                far = np.where(metal & (kk < ks), kk, n[2]).min(axis=2)
                column = (kk >= far[:, :, None]) & (kk < ks)
            else:
                far = np.where(metal & (kk >= ks), kk, -1).max(axis=2)
                column = (kk <= far[:, :, None]) & (kk >= ks)
            rho = np.where(column & ~clear, 1.0, 0.0)
            if FORM == "skin":
                body = skin_half(parts[half], level, Path(tmp))
                if layout.get("flange"):  # the contract's parts exact, the members fused on (11 October)
                    body = body.fuse(exact_shell(layout, all_rooms, z_split, half, wall, draft)).clean()
            elif FORM == "relief":
                body = relief_half({**f, "rho": rho}, half, draft)
            else:
                body = organic_half({**f, "rho": rho}, half, np.zeros(tuple(n), bool), Path(tmp))
            # cut flat at the split
            body = body.cut(cylinder((0.0, 0.0), z_split, z_split + 2000.0, 4000.0) if lower else cylinder((0.0, 0.0), z_split - 2000.0, z_split, 4000.0))
            # the organic shape itself, before any exact interface: shown on its own (the engineer,
            # 10 October 14:49: "show me the organic shape in the UI and then the CAD")
            organic[half] = body
            # what the optimiser kept clear, cut flat (through empty space, or through the
            # interfaces' solid where a face is machined): the motor beyond its flange's face, the
            # half-shafts' joints, the mounts' ends
            if lower and flanged:
                body = body.cut(cylinder(axis["input"], z_face - t_ring - 600.0, z_face - t_ring, ring_out + 30.0))
            if exits is None:
                body = body.cut(cylinder(axis["output"], ends["output"][1], ends["output"][1] + 600.0, 90.0) if not lower
                                else cylinder(axis["output"], ends["output"][0] - 600.0, ends["output"][0], 90.0))  # fmt: skip
            else:
                for e in exits:  # the contract's exits, exact (each seal's bore and a half-shaft's joint)
                    z0, z1 = e["z"]
                    if (z1 <= z_split) == lower:
                        body = body.cut(cylinder(e["centre"], z0 - 1.0, z1 + 1e-3, 2 * e["radius"]) if lower else cylinder(e["centre"], z0 - 1e-3, z1 + 1.0, 2 * e["radius"]))
            if brackets:
                for m in mounts:  # the vehicle's bracket and bolt beyond both faces, through both halves
                    d_b = 2 * brackets[f"{m['name']} bracket -z"]["radius"]
                    body = body.cut(cylinder(m["centre"], m["z"][0] - 600.0, m["z"][0], d_b))
                    body = body.cut(cylinder(m["centre"], m["z"][1], m["z"][1] + 600.0, d_b))
            else:
                for m in mounts if lower else []:
                    body = body.cut(cylinder(m["centre"], m["z"][0] - 600.0, m["z"][0], s["mount_diameter"] + 2 * MOUNT_ROOM))
                    body = body.cut(cylinder(m["centre"], m["z"][1], z_split + 1.0, s["mount_diameter"] + 2 * MOUNT_ROOM))
            # A bolt joins the halves where the body holds most of its boss (an organic boss is
            # rounded at its rim, so not all of the exact cylinder: 9 in 10 kept only 2 of 14 on
            # outcome_run3, 02:44); its head's seat is faced flat and its socket's room cleared,
            # 60 mm out from the flange's face (the trade's kept-clear tool space).
            kept_bolts = []
            t_f = s["flange_thickness"]
            for c in bolts:
                boss = cylinder(c, z_split - t_f, z_split, s["bolt_boss"]) if lower else cylinder(c, z_split, z_split + t_f, s["bolt_boss"])
                if body.intersect(boss).Volume() > 0.6 * boss.Volume():
                    kept_bolts.append(c)
                    # the head's seat faced flat, and room over it for a hex key (`SOCKET`)
                    d_s, h_s = SOCKET
                    body = body.cut(cylinder(c, z_split - t_f - h_s, z_split - t_f, d_s) if lower else cylinder(c, z_split + t_f, z_split + t_f + h_s, d_s))
            # the inside exact
            body = body.cut(cupmod.cup(all_rooms, z_split, half, wall, draft)[1])
            for b in bearings:
                if (b["side"] == "-z") != lower:
                    continue
                z0, z1 = b["z"]
                body = body.cut(cylinder(b["axis"], z0, z1, b["D"]))
                body = body.cut(cylinder(b["axis"], *sorted((z1 if lower else z0, z_split)), b["D"] + 1.0))  # its path in from the split
                if b["sealed"] and exits is None:  # (the contract's seals are among its exits, cut above)
                    seal = cylinder(b["axis"], z0 - 300.0, z0 + 1e-3, b["d"] + 2 * s["seal_radial"]) if lower else cylinder(b["axis"], z1 - 1e-3, z1 + 300.0, b["d"] + 2 * s["seal_radial"])
                    body = body.cut(seal)
            if lower:
                if flanged:
                    body = body.cut(cylinder(axis["input"], z_face - t_ring - 1.0, z_face + 3.0, ring_in))  # the motor's spigot
                    for c in motor_holes:
                        body = body.cut(cylinder(c, z_face - t_ring - 1.0, z_face + 40.0, s["bolt_hole"]))
                for m in mounts:
                    body = body.cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
            for c in kept_bolts:
                body = body.cut(cylinder(c, z_split - s["flange_thickness"] - 1.0, z_split + s["flange_thickness"] + 1.0, s["bolt_hole"]))
            solids = sorted(body.Solids(), key=lambda x: x.Volume(), reverse=True)
            if len(solids) > 1:
                say(f"{half}: {len(solids) - 1} loose pieces dropped, {sum(x.Volume() for x in solids[1:]) / 1e3:.1f} cm3")
            body = _meshable_fast(solids[0], "motor side" if lower else "cover")
            if lower:
                # A mount the optimiser left unjoined to the body was dropped with the loose
                # pieces; fe.py holds only the mounts the body holds (with all three in the record,
                # outcome_split_7.73's stiffness was singular, 05:12).
                held = []
                for m in mounts:
                    ring = cylinder(m["centre"], m["z"][0], m["z"][1], s["mount_diameter"]).cut(cylinder(m["centre"], m["z"][0] - 1.0, m["z"][1] + 1.0, s["mount_hole"]))
                    if body.intersect(ring).Volume() > 0.6 * ring.Volume():
                        held.append(m)
            halves[half] = (body, kept_bolts)
    both = set(map(tuple, halves["motor_side"][1])) & set(map(tuple, halves["cover"][1]))
    bolts_used = [list(c) for c in bolts if tuple(c) in both]
    if len(held) < len(mounts):
        say(f"{stem}: the body holds {len(held)} of the layout's {len(mounts)} mounts; the optimiser joined no other (its objective asks no mount to carry load)")
    names = {half: convex._name_faces(shape, bearings, bolts_used, mounts, motor_holes, z_split, s, []) for half, (shape, _) in halves.items()}
    for half, (shape, _) in halves.items():
        cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{stem}_{half}.step"))
        shape.exportBrep(str(OUT / f"{stem}_{half}.brep"))
    mass = {half: shape.Volume() * s["density"] for half, (shape, _) in halves.items()}
    record = {**layout, "stem": stem, "form": "outcome", "drawing": FORM, "skin_bosses": DRAW_BOSSES if FORM == "skin" else None,
              "skin": ({"wall_mm": s["wall"], "exact": True, "grid_bury_mm": SKIN_BURY, "members_level": level, "keeps_mass": KEEP_MASS, "root_fillet_mm": ROOT_FILLET}
                       if layout.get("flange") else {"wall_mm": SKIN_WALL, "members_level": level, "keeps_mass": KEEP_MASS}) if FORM == "skin" else None,
              "outcome_of": run, "ribs": [], "bolts": bolts_used,
              "mounts": held, "mounts_layout": mounts, "mass_kg": {**mass, "total": sum(mass.values())},
              "faces": {half: {str(k): v for k, v in nm.items()} for half, nm in names.items()}}  # fmt: skip
    (OUT / f"{stem}.json").write_text(json.dumps(record, indent=1, default=list), encoding="utf-8")
    say(f"{stem}: {record['mass_kg']['total']:.2f} kg (motor side {mass['motor_side']:.2f}, cover {mass['cover']:.2f}); bolts joining the halves {len(bolts_used)} of {len(bolts)}")
    # The organic shape as a design of its own (`<stem>_organic`), for the Designs page
    # (`view_export.py <stem>_organic`): the smoothed field, each half cut flat at the split.
    for half, shape in organic.items():
        shape.exportBrep(str(OUT / f"{stem}_organic_{half}.brep"))
    mass_o = {half: shape.Volume() * s["density"] for half, shape in organic.items()}
    shown = {**record, "stem": f"{stem}_organic", "form": "organic", "organic_of": stem, "mass_kg": {**mass_o, "total": sum(mass_o.values())}}
    (OUT / f"{stem}_organic.json").write_text(json.dumps(shown, indent=1, default=list), encoding="utf-8")
    say(f"{stem}_organic: the organic shape alone, {shown['mass_kg']['total']:.2f} kg")
    return record


if __name__ == "__main__":
    if len(sys.argv) > 3:  # the drawing: organic (default), relief, or skin (LOP-20)
        FORM = sys.argv[3]
    if len(sys.argv) > 4:  # the skin drawing's route: mesh (default) or brep
        ROUTE = sys.argv[4]
    if FORM == "skin" and ROUTE == "mesh":
        build_mesh(sys.argv[1], sys.argv[2])
    else:
        build(sys.argv[1], sys.argv[2])
