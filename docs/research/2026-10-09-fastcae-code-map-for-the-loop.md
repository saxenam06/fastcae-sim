# fastcae's code, mapped for the first loop

**Date.** 9 October 2026, 02:29. A read-only map of `C:\Work\fastcae` (tag `fastcae-v1`) made by a subagent for the first loop (LOP) and the design-space view (PLT-8): what can be copied, where it is, what it needs. The working folder's `src`, `ui`, `bench` and `tools` equal the tag; **`tests/` and `_archived_code/` are untracked**, so they are copied from the folder, not the tag.

Resolved versions there (its `uv.lock`): cadquery-ocp 7.9.3.1.1 (OCP used directly, no CadQuery API), gmsh 4.15.2, pymeshfix 0.18.1, libigl 2.6.3, trimesh 5.1.0 with embreex, warp-lang 1.17.0, cupy-cuda12x 14.2.0, nvmath-python 1.0.0, nvidia-cudss-cu12 0.8.0.10, ortools 9.15, shapely 2.1.2, vtk 9.6.2, h5py, fastapi 0.141 with uvicorn. Numbers below are from the same laptop (RTX 5060 Laptop 8 GB, 16 GB RAM).

## 1. The 3D viewer: raw WebGL2, no library

- `ui/package.json`: react and react-dom 19.2 only; vite 7.3.6, typescript 5.9.3. No three.js.
- **CAD view** `ui/src/render/renderer.ts`, `class Renderer(canvas, mesh, faceCount)`:
  - an indexed mesh, the CAD face id a uint vertex attribute; face state (selected, frozen, hovered, exterior) in an RGBA8 texture, so a change is a small texture write;
  - `pick(x, y) -> faceId | null` by an id render at half resolution;
  - colour modes `surface | frozen | exterior | paint`, `setFacePaint` per face; `setOverlay(mesh)` for a design's new faces; **`setGhosts` draws see-through volumes**; `setLines` for rib outlines; `setVoxelLayers`; **`setHidden(faces)`**; `setSection` (a clip plane with a hatched cut);
  - turntable camera, Z up: `orbit`, `pan`, `zoom`, `frame(bbox)`, `focusBox`.
- **FE view** `ui/src/render/fe.ts`, `class FeRenderer(canvas, camera)`: `setSkin`, `setValues(values, vectors)` (deformed shape), `setGroupColours`, `setSlice`, **`setGlyphs`** (supports, couplings and loads as arrows, arcs and pyramids); modes `patches | contour | difference | plain`; 48 banded contours; element edges from barycentric coordinates.
- **React** `ui/src/stage/`: `Stage.tsx` (one renderer per mesh; left-drag orbit, middle or shift-drag pan, wheel zoom, hover pick once a frame), `FeStage.tsx` with `CameraLink`, `Legend.tsx` (`typicalRange`, 0.5-99.5 percentile), `Section.tsx`, `sectionPlane.ts`, `HoverCard.tsx`.
- **Chips that hide and show:** `ui/src/designs/Designs.tsx` (`LegendChip`, `legendKey(tab, what)`), `ui/src/optimize/Optimize.tsx` (`ChangePanel`), `ui/src/input/MeshSetup.tsx` (edges, groups, supports·couplings·loads; colours `FE_COLOURS`).
- **How geometry reached the browser:** API routes as binary `octet-stream`, never static files, no GLB or STL. Formats: `FCMESH03` (`src/fastcae/api/mesh.py encode(vertices, triangles, face_id, normals=None, standing=None)`: magic, u32 nVert, u32 nTri, f32 positions, i8 normals ×4, u32 face id per vertex, u32 indices, optional u8 standing), `FCSKIN01` and `FCVALS01` (`api/simulate.py`), `FCSECT01` (`simulate/section.py`). The browser keeps buffers in a 600 MB LRU (`ui/src/api/client.ts fetchBuffer`).
- **Triangles from the CAD:** `src/fastcae/input/geometry/brep.py tessellate(shape, deflection_mm=None, angle_deg=20, weld_tol_mm=1e-3)`; OCP `BRepMesh_IncrementalMesh`, chord tolerance the model diagonal × 2.5e-4 clamped to 0.01-1 mm; face id = TopExp order.

## 2. The CAD build (OCP)

- `member/spec.py MemberSpec(a, b, pull, bend, base, heights, thickness=25, draft_deg, extend, caps, sink, hosts, kind='web'|'plate', flange, …)`: one rib as numbers; `hosts` names the CAD face each end attaches to.
- `member/solid.py solid(spec, spacing_mm=2.0)` (B-spline rails, ruled faces, sewn, `MakeSolid`; a T-section is web + flange) and `trimmed(spec, shape, part)`.
- `generate/cad.py fuse(base, plates) -> Fused`: every rib in one boolean first, then one by one; a 1 µm fuzzy retry; ShapeFix on flagged faces; UnifySameDomain on new faces only; checks that no solid was dropped. `write(shape, step_path, brep_path)`.
- Measured: ribs built and trimmed in 12-23 s; the fuse 14-47 s.
- **No face-to-role map in the CAD.** Generic kinds come from `input/geometry/atlas.py` and `input/features.py detect` (bore, boss, hole, hole pattern, planar group, fillet); roles came from the solver deck (`space/interfaces.py deck_roles`). zenryx builds its own CAD, so it can name every face by role as it makes it.

## 3. Meshing: gmsh, face by face

- `src/fastcae/simulate/face_mesh.py mesh(brep, work, size=25, smallest=4, per_turn=8, near, far, keep, fillets, rounded) -> (nodes, tets4, stats)`; CLI `python -m fastcae.simulate.face_mesh <brep> <work>` with `work/sizes.json`.
  - Each face meshed alone (unrolled where gmsh cannot parametrise it; closed faces opened at their seam); 8 elements a turn on curved edges, 12 on rounds; weld 0.1 mm; edges under 3 mm collapsed but never within 0.3 mm of a face the deck uses; MeshFix only if the surface is still open; gmsh 3D fill and the Netgen optimiser.
  - **A hidden external dependency:** `_fill` loads `write_stl` from `C:\Work\agenticCAE\src\fastcae\mesh\surface.py`. Replace it when copying.
- `simulate/tetmesh.py finish(nodes, tets) -> FEMesh`: TET10 with straight mid-side nodes. `simulate/fem.py FEMesh` (`.skin`, `.tet10`, `group_nodes`).
- Sizes (`generate/solve.py mesh_sizes`): 25 mm within 60 mm of added metal and loaded groups, 50 mm elsewhere; the mesher runs in a subprocess with a 10-minute limit.
- **Loads and supports are tagged after meshing, by CAD face:** `simulate/carry.py anchor`, `carry(…, tolerance=2.0)` (a boundary triangle joins a group when its nearest CAD face is the group's and all corners lie within 2 mm).
- Gates: at most 415,000 TET10; no inverted tets; at most 0.08 % below quality 0.1; reactions within 2 % of the loads. Measured: about 60 s a design without fillets; production's mesh 350,939 TET10; fillet steps peaked near 13 GB of RAM.

## 4. The FE model

- Decks: Code_Aster only (`simulate/aster.py`: `parse_comm`, `interpret`, `write_comm`, `write_mail`, `run` in WSL). `simulate/setup.py`: `Held`, `Rigid`, `Distributing`, `NodalLoad`, `SurfaceLoad`, `Output`, `Setup`.
- In the earlier deck: each loaded seat an RBE3 from a reference node on the bore axis to the seat's nodes, uniform weights, the forces on the reference node; each flange bolt a rigid coupling to a reference node held in translation. No cosine distribution anywhere.
- **The static solve** `simulate/solve.py solve(mesh, setup, gpu=True, …) -> Solution(u, rotation, stress, von_mises, reactions, …)`:
  - TET10 assembled with CuPy in chunks;
  - rigid couplings as rigid-body constraints (`u = Tq + u0`);
  - **distributing couplings add no stiffness:** the load is spread so force and moment balance, and the reference's motion is read back by a rigid fit (`rigid_fit`);
  - cuDSS through `nvmath.sparse.advanced.DirectSolver`, hybrid memory: a single-precision Cholesky refined in double by preconditioned CG to 1e-10, then single LDLᵀ, then double; CPU fallback `spsolve`; `simulate/gpu.release()` frees the card.
- Results at the seats: `simulate/signals.py` (seat tilt and spin from `cylinder_axis`, reactions, largest displacement, p99.9 von Mises).
- **No modal solve.**
- Parity: `tests/test_simulate.py` with `tests/data/deckprobe/` (a TET10 bar with a rigid and a distributing coupling, against Code_Aster, agreement under 1e-9); untracked, so copied from the folder.
- Measured: cuDSS 13.1 s against Code_Aster 56.6 s at 1.06 M unknowns (field error 3.3e-10, 5.2 GB on the card); the single-precision factor solved 2.18 M unknowns in 15 s (40 s with assembly).

## 5. Topology optimisation

- **What ran works on whole ribs, not free voxels:** a 10 mm cube model (`generate/paths.py Model`, Warp FEM, `.gradient`: strain energy and a P-norm-8 displacement with its adjoint); a CuPy float32 multigrid (`generate/multigrid.py Hierarchy`, Galerkin coarse levels, Chebyshev smoother); ribs drawn onto the cubes by geometry projection (`generate/fins.py draw`); SIMP on rib presences with optimality criteria (`loop/relax.py relax`, penalty 1→2→3); CP-SAT rounds to legal designs (`round_legal`, one worker). One topology move took 20-40 min.
- Archived (untracked `_archived_code/`): voxel BESO (`designs/optimise.py`), plates by geometry projection with MMA (`ribs/plates.py`, `generate/mma.py`), a ground structure (`ribs/network.py`).
- **What was found:**
  - the cube model ranks designs, never judges them: it reads 1.0-2.4× stiffer than the real mesh;
  - free-density layouts lost their metal when made into parts: plates read off BESO kept 51-70 % of the optimised metal, and only 10-24 of 48 fused; free density reached −74 % on voxels, but as blobs; geometry projection gained 58 % on voxels, then 25 of 30 plates were rejected at the fuse;
  - topology over a rib library reached 87.9 % of the goal; its best legal design solved at 85.7 %;
  - 152 designs solved, the best −52 % on the robust measure, but none of 29 tested held up when the load case changed;
  - with more rib families, the agent met the goal at its fourth FE solve.
- Where written: fastcae's `docs/research/2026-10-06-geometry-technology-lessons.md` §1, `2026-09-26-capability-inventory.md`, `docs/archive/designs-voxel.md`, `docs/features/ribs/design-generation.md`, `docs/features/optimize/benchmark-2026-10-02.md`.

## 6. Mounts, two halves, bolted joints

- Nothing in fastcae's code models two halves, contact or bolt preload; the part was one piece, and bolts were rigid couplings to held points.
- **The support model matters more than the solver:** clamping the holes instead of the rigid couplings moved the worst seat tilt from 2.07′ to 1.25′ (−40 %) (`bench/solvers/RESULTS.md`).
- Related: `input/features.py` (bolt circles), `space/interfaces.py` (the joint's clamped faces), `space/volumes/keepouts.py` (room for each hole's tool, and a lid in front of faces the deck holds or loads). Research: fastcae's `2026-10-06-gearbox-housing-engineering.md` §1.6 (bolted joints, VDI 2230), §1.9 (mounting), §6.3 (applying bearing loads).

## What this means for zenryx's first loop

- **PLT-8 copies the WebGL2 renderer** (`renderer.ts`, `Stage.tsx`, the legend chips) instead of adding three.js: proven here, no new dependency, and its ghosts, hidden faces and per-face paint are what a volume per chip needs. Its FE view (`fe.ts`) shows the loop's results later. three.js stays approved (the engineer, 9 October 02:12) if the copy falls short.
- **The solve copies `simulate/solve.py`** with its parity test (PHY-1), and adds what zenryx's FE practice needs (the engineer, 02:12-02:15): mounts held through distributing couplings and the halves joined at their bolts by distributing couplings, as constraint equations on the coupled nodes' averaged motion; and a modal solve on the same factor (PHY-3).
- **zenryx names its faces as it builds them**, so loads and supports are tagged by role, not found by geometry afterwards.
- **Free-density optimisation read off into plates lost most of its gain at fastcae.** The loop should take that into account (see the topology-optimisation review of the same day).
