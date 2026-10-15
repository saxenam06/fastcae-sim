# The loop's record: the night of 11 October

Where everything stands, what was tried and what it taught, written as it happens, so that a new session (or a compaction) loses nothing. The loop's page ([status.md](status.md), LOP-20 to LOP-22) holds the state; this page holds the night's account. The day before: [2026-10-10-record-day.md](2026-10-10-record-day.md).

## Where the night ends (for the engineer, morning of 11 October)

- **Goal 1, the pipeline fast: met.** A judged design in about 5 minutes (`propose.py`, flow B), or 3 minutes as a 10 mm scout, where the evening's method took about 50.
- **The Designs page as agreed:** the designs by flow on the left with their numbers marked, the chosen design's own tabs in the centre, the step's card on the right. Every flow tried is there: A (the CAD route), B (the mesh route), C (the ribbed CAD), and tonight's variations.
- **Goal 2, production-like CAD: a first version** (`ribbed_cad.py`, flow C): exact B-rep with ribs, pads, posts and struts on the contract's exact shell. It is the lightest (7.33 kg) and the most castable (undercut 0.2 %), passes the beds and the modes, and is softer at the intermediate seat (tilt 1.20 ×).
- **Goal 3, the agents' role: written** ([the agents' role](../product/2026-10-11-the-agents-role.md)), from the night's failures, cures and the engineer's corrections.
- **The closest designs yet:** budgets of 7.0, 7.2 and 7.4 kg (flow B). Each drawn at 7.21-7.63 kg passes the mass, the beds (23-29 µm) and the tilt (0.74-0.77 ×). Each fails only a mode at 1,145-1,149 Hz, within 3 % of stage 2's order, plus castability by the strict rule. That mode doesn't move with the budget; a mode margin in the optimiser is the next move.
- **The first design-agent moves** are tried and recorded as hypotheses: strengthening the ribbed CAD's failing seat was falsified (tilt 1.195 → 1.192 ×).
- **Waiting for the engineer:**
  - whether to commit tonight's work (nothing committed since the morning of 10 October);
  - the review of flow C and of the agents' role.

## The engineer's goals for the night (01:26-01:38)

In this order:

1. **The end-to-end pipeline fast:** a judged design in a few minutes, so that the engineer and the agents can go back and forth on designs ("if each end-to-end process takes 50 minutes, it's the end of the story").
2. **Production-like CAD from the optimisation's design:** the published housings' drawing steps as tools (an envelope over the members trimmed by the flange plane and the end faces, the exact 4 mm wall as the pockets' floors, the members' centre-lines as rib paths, ribs up to the envelope at most 12 mm thick, pockets between), compared with the current skin drawing.
3. **The agents' role, from evidence:** after the whole pipeline runs and its failures and the cases that need a person are known: how agents become native to the process, take manual work off people, and help them reason beyond their first ideas; every run as data for training agents.

And the UI the engineer agreed (LOP-21): the Designs page with the designs on the left, the design's process step by step in the centre, the step's card on the right.

## The plan, in order (01:42)

1. **Fast pipeline** (target: 5 min at 6 mm, 2 min at 10 mm). The optimisation's adjoints in one batch and its sharpening trimmed; the drawing's booleans on watertight triangle meshes (surface-mesh boolean fusion: the agreed option 2 of 25 September) with FE meshing the result; no heal without a sliver; the exact cuts in one boolean; the halves in parallel; castability beside FE; pictures off the critical path; one `propose` command with each stage's time.
2. **The UI (LOP-21)** as agreed.
3. **Production-like CAD** (the grammar from the field) and its comparison with the skin drawing.
4. **Robustness and the agents' role:** variations through the pipeline, every failure mode catalogued, then the role written from what the runs show.
5. **Documentation** at every failure, fix, result and decision.

## What stands at 01:42

- **The optimisation (LOP-20):** one run, the stiffness the objective, every seat's tilt and bearing bed held from iteration 1, peak drive alone, one design, MMA's dual subproblem, stopping once settled: **194 s** at 6 mm (was about 50 minutes at 22:28 the evening before, two runs, both cases, three designs). Its metal-or-air check: compliance 789.8 N·mm, tilt 0.926 ×, the worst bed 0.58 × the reference's, 4.80 kg placed.
- **The design judged, `outcome_skin_6mm_drive`** (the two stages' field, drawn with the exact wall): beds **21.4 µm** (the reference 52.2), tilt **0.73 ×**, first mode **768 Hz, no clash**; 7.97 kg (0.24 over 7.73), castability fails (undercut 6.5 and 5.9 %). The first design to pass the beds, the tilt and the modes.
- **The pipeline's times** (`outcome_skin_6mm_drive`, 11 October 01:04-01:15): optimisation 3.2 min, drawing 5.5 min (of it about 3.5 min the exact booleans and a heal refused in both halves), castability 1.0, FE 1.5, pictures 1.5: **about 13 minutes**.

## Trials and failures, as they came

| When | What | Result | What it taught |
|---|---|---|---|
| 00:27, 00:35 | the method on the new set-up, both cases, three designs | stopped: first for the fixed mass and the draft, then for the load case | the contract's draft is 0° (A11), not the generator's 1.5°; the voxels alone counted the fixed metal 0.07 kg light (2.86 against 2.93); peak drive alone (the engineer, again) |
| 00:55-01:01 | two stages, drive, one design, primal-dual MMA | stiff: settled at 70, 280 s, binary 1.02 ×, 792 N·mm; tilt held: settled at 19, 71 s, binary 0.999 ×, 791 | holding the tilt cost nothing; the settle rule ends runs at 70, not 200 |
| 01:01, 01:03 | the skin drawing with the exact wall | the motor side never watertight | the grid's buried wall made thin slabs (the plate over the other half's opening; rings round the exits): the plate left to the exact shell, the grid's clearances kept out of the cup and wall |
| 01:04-01:09 | the drawing again | 7.96 kg, 13 of 13 bolts, both halves mesh | |
| 01:05 | MMA's subproblem by its dual (`mma_dual.py`) | the exact optimum (the primal-dual converges onto it as its barrier is cut), a tenth of the time | |
| 01:13 | FE and the grade of `outcome_skin_6mm_drive` | beds, tilt, modes pass; mass and castability fail | |
| 01:15-01:22 | one run (tilt and beds from iteration 1) against two stages, both with the dual | one run: 231 s, 789.8 N·mm, 0.926 ×; two stages: 197 s, 793.1, 0.998 × | no floating core when the beds are held; the one run is the better design |
| 01:22-01:26 | every gradient row back through the filters in one pass | the same design, 231 → 194 s | |
| 01:26-01:40 | the one run's field drawn | the motor side not watertight at 5 mm triangles; at 2.5 mm watertight but 114,000 faces: 3 min to sew, 7 min of exact cuts, faces 0.000 mm wide, a heal begun; stopped | **the skin drawing's route (a smoothed field, remeshed, sewn into a B-rep, cut by OCC) is too slow and too fragile for a pipeline of minutes**; thin members break it; the cure is the mesh route or the grammar |

## Goal 1: the pipeline in minutes (from 01:43)

| When | What | Result | What it taught |
|---|---|---|---|
| 01:43-01:45 | **the mesh route** (`mesh_route.py`; `outcome_cad.py <run> <design> skin mesh`): the members' surface by marching cubes alone (no smoothing, no remeshing), the exact shell and every exact cut tessellated or as manifold3d cylinders, every boolean manifold3d's | **the one run's field drawn in 10 s** (the OCC route: 5.5 min, and on this field not at all); both halves watertight, 13 of 13 bolts; **8.02 kg** (0.29 over 7.73) | the booleans are no longer the cost; marching cubes alone never folds |
| 01:46 | FE from the STL, through gmsh's reparametrisation (`fe.mesh_stl`) | "Wrong topology of boundary mesh for parametrization" at 30, 40 and 60° | STL keeps no shared vertices: gmsh rejoins them by position |
| 01:48-01:58 | the same from an indexed copy (`.ply`, manifold3d's topology kept) | gmsh still meshing after 10 minutes on 179,000 triangles; stopped | gmsh's reparametrisation of marching cubes' fine surface is too slow |
| 01:59 | quadric decimation to 30,000 faces (pymeshlab, topology kept) | watertight, 0 self-crossings, volume kept (1,650.0 against 1,649.9 cm³), 1.8 s | the fine surface coarsens safely |
| 02:00 | gmsh on it: a discrete volume (no tets made); reparametrised (the same topology error) | fails | gmsh's surface-to-volume paths do not take this surface |
| 02:02 | the decimated surface sewn into a B-rep (`outcome_cad._sewn`) for FE's own B-rep mesher | sewn valid, 30,000 faces, 13.6 s; **its narrowest face 0.000 mm**: gmsh's HXT failed | near-degenerate triangles from the booleans' intersections survive the decimation: the sliver rule again; next: manifold3d's `simplify` (collapses edges under a tolerance) before the decimation, and an even remesh after it |

| 02:03-02:07 | manifold3d's `simplify` (0.05 mm) before the decimation; with and without an even remesh | without: faces 0.002 mm wide, gmsh crashed (access violation); with a 4 mm remesh: 8 self-crossings, sewing 95 s, 1,379 faces under 0.5 mm, gmsh meshed it (136,627 tets) | sewing triangles into a B-rep is itself slow and makes the slivers: FE should take the triangles directly |
| 02:08-02:20 | **TetGen** (`tetgen` 0.8.4, installed into `.venv`, not in `uv.lock`, as pymeshlab) straight from the decimated surface (`fe.mesh_tetgen`) | at 6 mm surface triangles 695,000 tets, 3.4 M unknowns: the factor failed after 10 minutes (now refused at once: `fe.CEILING_DOF`); at **9 mm: 152,000 and 94,000 tets, no flat tet (worst 0.0027), 2 s a half** | quality tets from the surface itself; the triangles' size sets the count |
| 02:21 | **the same field by both routes** (`outcome_skin_6mm_drive` by OCC, `outcome_mesh_6mm_drive` by the mesh route) | drawing 5.5 min against **10 s**; FE 1.5 min against **62 s** (meshing 45 s against 5 s); mass 7.97 / 7.99 kg; beds 21.4 / 22.7 µm (+6 %); tilt 0.221 / 0.222 mrad; first mode 768 / 761 Hz; the third mode 1,147 Hz now within 3 % of 1,127 (a clash the OCC mesh did not show: within the meshes' noise) | **the mesh route is validated**: the same judgement within a few per cent, in a tenth of the time |
| 02:23 | the one run's design (`outcome_skin_6mm_onerun`) judged by the mesh route | FE 74 s: beds **22.1 µm**, tilt **0.206 mrad** (the two stages' 0.222), first mode 754 Hz, **the third at 1,123 Hz, within 3 % of 1,127: a clash**; 8.03 kg | the modes are the grade's one line the optimiser does not hold: a frequency constraint, or a variation, is the agent's next move |

| 02:24-02:27 | castability, the pictures and the UI's export from the meshes (`castable.py`, `look.py`, `view_export.py` read a mesh-route half's `.ply`/`.stl`); the grade | castability 55 s: **undercut 0.9 and 1.1 %** (the OCC route's facets read 6.5 and 5.9 % on the two stages' field), no voids, 93 and 15 cm² under 4 mm; pictures 8 s | the OCC route's smoothed facets leaned against the pull; marching cubes on a field cast along the pull, and exact 0° walls, do not |
| 02:28-02:33 | **flow B end to end** (`propose.py outcome_b_6mm_drive`: the optimisation, the drawing, FE beside castability, the grade, the pictures, the UI's records; `flow_<design>.json` holds each stage's time) | **307 s**: optimisation 205 s, drawing 12 s, FE and castability at once 76 s, the rest 14 s | **goal 1 met: a judged design in about 5 minutes** (13 minutes by the OCC route at 01:15; about 50 minutes by the evening's method). Left for speed: the adjoints in one batch (about 20 s), fewer modes (12 to 8: about 10 s), the sharpening's schedule |

## The UI (LOP-21, 02:36-03:04)

| When | What | Result | What it taught |
|---|---|---|---|
| 02:36-02:45 | the Designs page as agreed: the designs by flow on the left, the flow's steps as tabs in the centre, the step's card on the right (`Process.tsx`, `FeView.tsx`; records by `process_export.py`) | built; flows A and B with their own tabs | |
| 02:45-02:50 | the FE view and the design view in a headless screenshot | both stayed at their "…" placeholder, at a 20, 30 and 90 s budget | Edge's `--screenshot` captures before a lazily loaded view arrives (its DOM dump, at the same budget, held the canvas): **`web/tools/shot.mjs`** drives Edge over its DevTools pipe and waits for the views |
| 02:50 | the pages checked step by step | FE's legend unstyled (its sheet not copied); both flows' designs named alike; flow B's run and flow A's stiff stage missing from the Optimisation tab | the legend's rules copied from fastcae-v1's `simulate.css`; `names.py` says "tilt and beds held, one run" or "from a stiff run", and "· mesh" or "· CAD"; `propose.py` exports its run and its flow's tabs itself |
| 02:56-03:00 | the Grade step; the times; the Set-up | the grade's lines in a table (each value, its limit, its verdict; castability with them); a stage drawn as two tabs keeps its time on the first ("the same stage as…"), castability says it ran beside FE; Set-up opens on the optimiser's voxels (`setup.json` re-exported: it was older than the layout) | |
| 03:00-03:04 | phone width (390 px) | the shell kept three columns: the stage vanished | the shell's phone layout (`shell.css`, at the end): the columns stacked, the page scrolling as one; `zenryx.css` pinned a stage's scroll to its body, which the phone rule now releases |

## Goal 2: production-like CAD from the field (LOP-22, 03:05-05:15)

The field read first with views (`field_and_cad.py`, now reading mesh-route designs; a plan of each column's run and how far it stands proud). It holds two kinds of member:
- **deep ribs and webs:** one or two voxels wide in plan, 20-100 mm proud. They form networks: across the cover's lobes and round the intermediate seat, and a lattice round the motor side's output lobe with spokes to the mounts.
- **pads:** wide in plan, 6-12 mm proud. The end wall thickened (the cover's output lobe, round the motor side's input).

So `ribbed_cad.py <run> <design>` draws, as exact B-rep:
- the deep members as ribs along their centre-lines (smooth splines), each as thick as its members' own area over its length (6-12 mm), topped by the envelope over the members' ends;
- the shallow members as flat-topped pads;
- posts where ribs meet, and a strut into each mount the members reach;
- all on the contract's exact shell, pockets down to its 4 mm wall, then every exact cut.

| When | What | Result | What it taught |
|---|---|---|---|
| 03:16 | the first build | the cover lost, 3 cm³ left; a 0.006 mm face | OCC's cut of many tools at once, and posts as wide as their ribs (tangent sides) |
| 03:21 | the fuse checked | shell + ribs + pads in one fuse: 185 cm³ of 3,700, called valid | OCC's fuse of several parts at once fails silently where their feet share the joint's plane: a pair at a time, each checked by volume; the feet 2 mm past the split, the half cut flat there |
| 03:26-03:42 | the mounts | 1, then 2, then 3 of 3 held | a centre-line stops half a member short of what it meets: free ends carried on; the volume check's tolerance refused parts apart (relative now); a strut squarely into each mount the members reach |
| 03:43-04:01 | FE on the B-rep's tessellation | TetGen: "self-intersections" | the B-rep's slivers fold when coarsened: FE's mesh joined from the parts by manifold3d; the coarsening keeps faces near any crossing out of it (`mesh_route.coarse`, unchanged on flow B's meshes) |
| 04:01-04:15 | TetGen on that | "repair_tet", "recoversubfaces"; flat tets without the dihedral bound | features under 0.1 mm stop TetGen however set |
| 04:15 | the ribs reworked | each a plate under its own ruled top along the envelope, only where 3 mm or more proud, kept 1.5 mm off every cylinder, posts 1 mm proud, pads flat | the B-rep's thin faces fell, but 29-37 remain where exact parts meet: the B-rep's quality measure |
| 04:22-04:37 | FE's body on a grid | each part filled on one 1.5 mm grid along the pull (`mesh_route.occupancy`), contoured, the machined faces cut exact: no crossings | keeping ribs 1.5 mm off walls left slots of air 1-2 mm wide (no sand fills them; tiny tets): a rib within 4 mm of the shell's metal joins it |
| 04:36 | FE | 2.82 M unknowns at TetGen's default, 1.83 M at radius-edge 3 (`fe.QUALITY_LADDER`) | **6.89 kg, beds 40.7 µm, tilt 1.30 ×** |
| 04:41 | the pads | the cover's 34 cm² pad over its output lobe had been left out (its spline outline crossed itself) | pads as polygons: **7.24 kg, beds 32.9 µm, tilt 1.13 ×** |
| 04:50-05:07 | the ribs' thickness | the members averaged 12 mm (150 cm² over 124 cm), the ribs drawn 6-8 at the median width: now their area over their length | FE at 2.04 M unknowns asked 18 GB: eliminating a coupling fills the reduced stiffness densely over its node set; the sets spread to 300 nodes (`fe.spread`) |
| 05:07 | **the judgement** | **7.33 kg, beds 31.1 µm, tilt 1.20 × at the intermediate −z seat, 792 Hz, no clash; undercut on the B-rep 0.20 and 0.18 %, 155 and 97 cm² under 4 mm** | |

**The three flows on the same set-up** (A's field is the two stages'; B's and C's the one run's):

| | Flow A, the CAD route | Flow B, the mesh route | Flow C, the ribbed CAD |
|---|---|---|---|
| The drawing | the field smoothed, sewn into a B-rep, cut exact (OCC) | marching cubes, booleans on meshes | ribs and pads read from the field, exact B-rep (OCC) |
| What it gives | a B-rep of 25,000 facets | meshes (no CAD) | **CAD: 400-700 analytic and spline faces, STEP** |
| End to end | 13.8 min | 4.9 min | 8.9 min (its drawing 2.8 min, FE 1.8) |
| Mass (≤ 7.73) | 7.97 kg | 8.03 kg | **7.33 kg** |
| Beds, drive (≤ 52.2) | 21.4 µm | 22.1 µm | 31.1 µm |
| Worst tilt (≤ 1) | 0.73 × | 0.70 × | **1.20 ×** |
| First mode, clashes | 768 Hz, none | 754 Hz, 1,123 near 1,127 | 792 Hz, none |
| Undercut | 6.5 / 5.9 % | 0.9 / 1.1 % | **0.20 / 0.18 %** |
| Under 4 mm | 86 / 9 cm² | 93 / 15 cm² | 155 / 97 cm² |
| Faces under 0.5 mm | many, 0.000 mm | (meshes) | 29-37 a half |

**What it teaches:** the ribbed CAD is the first CAD a designer could take on (exact walls, upright ribs, pockets, posts, struts), the lightest and the most castable, but it is softer at the intermediate seat. Ribs of one thickness on the members' centre-lines don't carry what the optimiser's organic members carry round that seat. The next moves are an agent's: which ribs to strengthen or add at the failing seat, judged by FE (a sizing loop over the ribs' thicknesses and heights), or the organic members kept round the seats and ribs elsewhere.

## Goal 3: the agents' role (from 05:15)

Written from the night's evidence, beside the plan of record and the two job descriptions: [the agents' role](../product/2026-10-11-the-agents-role.md) (PRD-5).
- The view as of now, in seven points.
- The pipeline as it runs.
- The night's failures, each with who cured it, and the engineer's ten corrections with what each became.
- The five seams where agents become native (the formulation, the reading, the failed line, the broken run, the engineer) and the hypotheses an agent would put now.
- Four datasets, and five proposed changes to the plan.

**Variations through the pipeline, as its evidence** (`propose.py`, flow B, one after another from 05:16; background task `byb650lg9`, this laptop):
- `outcome_v_7.2kg`, a lighter budget (311 s end to end; settled at iteration 78; metal or air: tilt 1.000 ×, bed 0.67 ×, 4.27 kg placed). **The closest design yet: 7.45 kg (passes 7.73), beds 28.2 µm (passes), tilt 0.77 × (passes); fails only the modes: 1,149 Hz within 3 % of stage 2's 1,127 Hz order** (1.95 % off). Castability: undercut 0.8 and 1.1 %, 91 and 24 cm² under 4 mm. The clash is the agent's next move: a small budget sweep (the mode moves with the mass's distribution) or a mode margin in the optimiser.
- `outcome_v_10mm`, a 10 mm scout: **175 s end to end** (the optimisation 71 s, settled at iteration 117; metal or air: tilt 0.85 ×, 5.15 kg placed); its FE failed (TetGen: "self-intersections", where pymeshlab's own test saw none): `fe.mesh_tetgen` now coarsens again finer when TetGen refuses (`SURFACE_LADDER`, 9, 7, 5 mm); its FE runs again.
- `outcome_v_max9`, members at most 9 mm: 405 s; beds 21.6 µm, tilt 0.70 ×, but 8.15 kg and two clashes (1,128 Hz against stage 2's 1,127; 2,551 against stage 1's 2,500).
- **A trait of the family:** every flow B design has a mode within 3 % of stage 2's order: 1,123, 1,128, 1,149 Hz. The optimiser never sees the modes; the ribbed CAD's straddle the order (1,087 and 1,176 Hz). A mode margin is the agent's lever.

**Then, 05:31-05:47** (background task `bl08zjzpj`, this laptop), the first design-agent moves, each a hypothesis with what would prove it wrong:

| Move | Result | What it taught |
|---|---|---|
| Flow C with the intermediate −z seat strengthened (`outcome_c_6mm_seat`: the ribs within 60 mm of its axis at 12 mm, raised 6 mm; `propose.py --drawing ribs --strengthen intermediate,-z,60,6`) | tilt **1.192 ×** against 1.195; 7.43 kg (+0.10); a new clash at 2,432 Hz | **falsified:** the seat does not tilt because its ribs are thin or low; the cause lies elsewhere (the path to the mounts, or the other half), so the next reading compares the field and the CAD round the seat's paths (`voxel_vs_fe.py`, `mass_where.py`) before strengthening anything |
| Budget 7.4 kg (`outcome_v_7.4kg`) | 7.63 kg, beds 23.4 µm, tilt 0.735 ×, a mode at **1,145 Hz** | three lines pass |
| Budget 7.0 kg (`outcome_v_7.0kg`) | 7.21 kg, beds 28.8 µm, tilt 0.77 ×, a mode at **1,148 Hz** | three lines pass |
| FE again for the 10 mm scout | TetGen refused the motor side at 9, 7 and 5 mm triangles, though pymeshlab finds no crossing, no non-manifold vertex or edge, one watertight body | **open:** a surface TetGen refuses that the other tests pass; next, TetGen's own intersection report to find its faces |

**The sweep's lesson:** at 7.0, 7.2, 7.4 and 7.73 kg the mode near stage 2's order sits at 1,123-1,149 Hz. The budget moves the mass but not that mode: mass is not the lever. A mode margin in the formulation is (the eigenvalue's derivative as a GCMMA constraint), or a reading checked against the orders before FE.

## The flows tried (for the Designs page's tabs, the engineer's word of 02:08)

- **Flow A, "the CAD route"** (until 01:15; `outcome_skin_6mm_drive`): the optimisation (two stages, then one), the skin drawing in OCC (the smoothed field remeshed and sewn into a B-rep, fused with the exact shell, cut exact one boolean at a time, healed), FE from the B-rep (gmsh), castability on the B-rep. About 13 minutes; failed on thin members.
- **Flow B, "the mesh route"** (from 01:45; `outcome_skin_6mm_onerun`, `outcome_b_6mm_drive`): the optimisation in one run, the members by marching cubes, every boolean manifold3d's, FE's tets by TetGen from the mesh, castability on the mesh beside FE. About 5 minutes. No B-rep.
- **Flow C, "the ribbed CAD"** (from 05:07; `outcome_c_6mm_drive`): flow B's field read in plan (`ribbed_cad.py`), drawn as exact B-rep (ribs, pads, posts, struts on the exact shell, pockets down to its wall), FE on the CAD filled on a 1.5 mm grid with its machined faces exact, castability on the B-rep. About 9 minutes.

## Open, the engineer's

- Commits: everything since the morning of 10 October is uncommitted; asked 01:42 whether to commit at milestones.
- The order of the night's goals (asked 01:42).
