# The first loop, 9 October, 20:00 to midnight: what was done, found and decided

The account after [noon to evening](2026-10-09-record-noon-to-evening.md). Written at 23:58 at the engineer's request ("document the current status cleanly with all the major findings and where we are exactly"). Everything here is uncommitted on `product/end-to-end`, by the engineer's word, and not pushed. The loop's page ([status](status.md)) holds the PBIs; this record holds the story and the numbers.

## Where we are, exactly (23:58; checked again at 00:18)

**00:18:** track 2's helper has written MMA (`prototypes/first_loop/mma.py`, with its test `mma_check.py`, 00:07-00:08) and is wiring it and the other fixes into `topo.py`, `topo_free.py` and `topo_setup.py` (edited 00:15-00:17); its report is pending. Track 1 stands where it stood at 23:55 (the reader rewritten, run 3 re-read): the recipe reading is next.

**Two tracks are under way** (the engineer, 23:52: "ok go"):

- **Track 1: the optimiser's housing drawn as a real casting.** The whole housing comes from the optimisation field, with no style preset. The enclosure is the field's skin, each end face sits at its gear room's own depth, and rings, bosses and ribs go where the field put metal. Then castability, FE, and the interpretation penalty. Claude does this one.
  - **Done:** the field reader is rewritten (`prototypes/first_loop/topo_read.py`). A skeleton's junction clusters count as one node, closed loops are traced, straight runs are joined through junctions, a leftover branch ends as a T on the rib it meets, and an arc round a bearing is recognised as a ring. Run 3 re-read: the cover gives 25 lines (13 with T-ends, 10 closed, a ring round the output's bearing at r 50.6 over 101°); the motor side gives 17 (8 T-ends, 5 closed).
  - **Next:**
    1. the recipe read from the field, with a reason for each choice: the cover's form (towers or a bridge), drums on the motor side, a lobed outline, a wheel in the motor's ring only if the field put metal there, ears where it struts to the mounts;
    2. `grammar.py` draws the field's rings closed round their bearings and takes the read recipe;
    3. the build's mesh check extended to a volume mesh;
    4. then build, `castable.py`, `fe.py`, and the penalty: the voxel model's 0.12-0.13 against the CAD's FE.
- **Track 2: an optimiser whose numbers can be trusted.** A helper agent works in `topo.py`, `topo_free.py`, `topo_setup.py` and a new `mma.py`, with short smoke runs only. Its tasks, in order:
  1. the inside one cup per half (no frozen walls inside at the split);
  2. the bound formulation by MMA (minimise z with every seat's ratio ≤ z), so runs settle;
  3. the halves joined only at the bolts;
  4. the skin weighed as 4 mm.

  It returns the command for overnight runs at 6, 7.73 and 9 kg.
- **Nothing heavy runs** beyond the helper's smoke runs.
- **For the engineer to decide:**
  - whether to commit now (no push);
  - the motor's mass and acceleration load cases (one mount was never tied in, since no load case asks it to carry anything);
  - the bolting, through-bolts or tapped holes in one half, which decides whether ribs may reach the flange under the bolts;
  - (from before) A8, the intermediate's bearing arrangement.

## The major findings of the evening

1. **The massing moves the stiffness far more than the ribs.** The six style presets got their own massing (lobed, hull or box outline; drums; towers, bridge or flat cover). Misalignment then spans 4.08-9.13, against 5.1-6.5 when the six shared one shell with different ribs.
2. **Hand-drawn style patterns do not fit clean rib rules.** With fastcae's rules, Kalyani kept 15 of its 47 ribs. It came out clean, castable and meshing, but softer: 6.86 at 6.98 kg, against 4.32 at 8.20 kg. The ribs should come from the load paths (the optimiser), and the rules draw them.
3. **CAD fillets on fused ribs make slivers; swept, fully rounded ribs do not.** Rounding each rib by fillet left a 2 mm flat that slivered at every junction: Kalyani's cover had 0.05-0.08 mm faces and would not mesh. A pill section (its top a true semicircle) swept along the rib needs no fillet operation. The faces fell to 194-225 per half (from 410-470), and they mesh. It agrees with fastcae: 0 of 42 CAD fillets built on fused seams.
4. **Every earlier design put side ribs under the bolts' heads.** The bolt holes run through both lips, and a rib on a bolt's line blocks the head and the socket (fastcae's tool-space rule). Ribs now meet the wall in the bays between bolts, and run down into the lip.
5. **The optimiser broke the single-precision rule.** `topo.py` factored each iteration in double precision (LOP-3's three runs used it). It now uses `fe.py`'s single factor, refined.
6. **The voxel element locked in bending.** A cantilever of 6 mm cubes reads 0.626 of beam theory with the plain hexahedron, and 0.985 with Wilson's incompatible modes (now the element).
7. **The old voxelisation doubled the walls:** the "a voxel is wall where it touches" rule made the lobed shell 12.3 kg against the CAD's 6.66. So even with the new element, the voxel model reads it at 1.35 against the CAD's 5.64. The free model now draws its skin as exactly one voxel.
8. **Topology optimisation from the interfaces alone finds the load paths.**
   - **The set-up:** the packaging space less every gear, bearing, shaft, the differential's case and the seal bores, with clearances; a thin oil-tight skin, the motor's ring and the mounts frozen; the grade's own misalignment as the objective; a casting filter and a projection to solid and void.
   - **What it finds:** buttresses at the mounts, rings round every seat, a bridge or wheel over the cover's bearings, a belt round the input's lobe.
   - **The catch:** in the whole package it stacks blocks of 78-108 mm (run 2). In a 30 mm band it draws a wheel round the output's bearing (run 3).
9. **The runs cycle; they do not converge.** The objective flips every iteration as the worst seat swaps between two bearings: a smoothed maximum (p-norm) driven by optimality criteria under a fixed move limit. The cure is a bound formulation solved by MMA (track 2).
10. **The voxel model flatters in three ways** (a fourth was its element, fixed):
    - the halves are glued along the split, where the CAD bolts them;
    - the skin, one voxel of 5-6 mm, holds 3.2-3.7 kg of the 7.73 kg budget (Zhou et al. 2004: a non-design base holding a third of the material cost 28 % stiffness);
    - the skin closes each gear room off, so frozen walls stand inside the housing at the split (found at 23:50 in `topo_setup.py`'s slices).
11. **Resolution binds.** A member needs at least three elements (OptiStruct), so 6 mm voxels draw nothing under about 18 mm. The field says where and how much, not how thick.
12. **The interpretation penalty must be measured.** In a published cast two-stage reducer housing (Slavov & Konsulova-Bakalova 2019), the topology concept promised 28.65 % less mass and the casting gave 7.33 %.
13. **The first casting drawn from a field failed.** `style_field_band` was Kalyani's body with the field's ribs: the rules kept 11 of 44, mostly the preset's own wheel spokes. The cover had 12.4 cm² of undercut and 23 cm² under 4 mm, and the FE failed (gmsh: two overlapping facets). Its causes:
    - the field's rings were refused by the bend rule;
    - the spokes that ended on those rings were left with nothing to meet;
    - the body came from a preset. The engineer (23:41): "didnt we say that we will start only from the shape fixed by the shafts, bearings, gears".
14. **One flat tet stops the single factor.** Avtec's FE failed on a tet of zero volume, where a side rib's face met a fillet's tangent line. `fe.py` now runs Netgen's optimiser only when a mesh holds a flat tet.
15. **An optimiser leaves a mount unused when no load case needs it** (the smoothed field showed a floating mount).

## The numbers

**The six presets, judged at 21:16** (FE at 8 mm, single precision; the reference 7.73 kg, 52/138 µm):

| Preset | Outline · levels · cover | kg | Bearing beds µm | Misalignment | First mode |
|---|---|---|---|---|---|
| ZF | lobed 30 · drums · towers | 9.13 | 86 / 103 | 4.08 | 1,012 Hz |
| Kalyani | lobed 45 · drums · bridge | 8.20 | 92 / 122 | 4.32 | 1,012 |
| AVL | hull · flat · bridge | 7.88 | 115 / 158 | 5.33 | 965 |
| Punch | lobed 90 · drums · bridge | 7.14 | 163 / 192 | 6.17 | 929 |
| Avtec | box 50 · flat · flat | 11.89 | 219 / 297 | 6.85 | 622 |
| Batom | hull · drums · towers | 7.41 | 219 / 215 | 9.13 | 851 |

**Kalyani by the clean-rib rules (23:11):** 6.98 kg, 150/231 µm, misalignment 6.86. Castable at the check's resolution: 0.5 / 0.0 cm² undercut, no voids, 0.3 cm² under 4 mm. The factor was Cholesky (SPD) in 7 refining steps.

**The topology runs from the interfaces** (`prototypes/first_loop/topo_free.py`; on the Designs page's Optimisation tab):

| Run | Set-up | Iterations | Grey | Voxel model's worst seat | Note |
|---|---|---|---|---|---|
| 1 | whole package, 6 mm | 100 | 54 % | 0.20 | not converged |
| 2 | + projection to solid and void | 240 | 8 % | 0.13 | cycles at the end (0.159 ↔ 0.196) |
| 3 | stage 2: a 30 mm band, 5 mm, damped | 240 | 3 % | 0.12-0.13 | cycles; a wheel round the output's bearing |

The voxel model's numbers rank; they do not judge. The CAD's FE judges, and none of these has a CAD judged yet.

## What was built (all prototypes, `prototypes/first_loop/`, and the UI)

- **`grammar.py`:**
  - the recipe holds the massing (outline, levels, cover);
  - the drums' fixes (the hollow on the base's cone; a boss over a deeper drum stands on its floor);
  - the lobed outline keeps its blends across offsets;
  - the heal always on, and guarded;
  - fastcae's rules through `ribrules.py`;
  - swept pill ribs (`pill_wire`, `chain_rib`, `face_rib`, `ring_pill`);
  - bays between bolts; ribs running down into the lip;
  - a step rule for the drums; arc fans;
  - the fuse checked rib by rib;
  - a `field` pattern that takes an optimisation field's lines.
- **`ribrules.py`:** fastcae's rules at a root fillet of 3 mm (flush 3, least height 6, arrival ≥ 45°, crossings ≥ 60° in the middle third, ends 11 mm apart, clearance 6, bend ≥ 8 × thickness), with T-ends between ribs. Each refusal names its rule.
- **`topo.py`:** the single factor, the Wilson element, the misalignment objective, an optional casting filter, a projection with continuation, damping.
- **`topo_free.py`:** the model from the interfaces, the casting filter with its exact adjoint (checked to 7·10⁻⁹), the band option.
- **The readers and pictures:**
  - `topo_read.py`: the plan maps and the rib lines;
  - `topo_smooth.py`: the organic route, marching cubes plus smoothing (a picture of the map, not a candidate);
  - `topo_setup.py`: the set-up in slices;
  - `topo_export.py`: the runs for the UI.
- **`fe.py`:** Netgen's optimiser only when a mesh holds a flat tet. **`castable.py`:** lists the faces that hold an undercut. **`gallery.py`, `view_export.py`, `grade.py`:** ignore results older than their design's build.
- **The UI (PLT-10):** the Designs view has a second page, **Optimisation**, which shows each run in 3D: frozen grey, placed green, the parts inside, toggles and opacity, its facts and its objective's history.

## The research read this evening

| Report | What it adds |
|---|---|
| [fastcae's rules for clean ribs](../../research/2026-10-09-fastcae-rib-rules.md) | about 88 rules with path:line; fillets rolled on the mesh, never in the CAD |
| [topology optimisation in practice](../../research/2026-10-09-topology-optimisation-in-practice.md) (ours, 63 sources) | the cycling and its cure; the model's flatteries; at least three elements a member; readings compared at equal mass; the rib graph by geometry projection as the second stage |
| [EV reducer housings](../../research/topology_optimisation_ev_reducer_housing_research.md) (the engineer's, an outside tool) | staged practice (Li, Kim & Jeswiet; Pu 2026); a second run only for a named question; Kabus & Pedersen 2012 on misalignment; a mass-against-tilt Pareto curve |
| [castings](../../research/topology-optimisation-in-practice-castings.md) (the engineer's, an outside tool) | Slavov 2019's interpretation penalty; Kim 2024; Eyckens 2021; OptiStruct's `DTPL`; the minimum length scale |
| [this morning's note](../../research/2026-10-09-housing-topology-optimisation-practice.md) | how housing topology optimisation is done in practice |

The plan they agree on: concept → interpretation into CAD → FE → sizing, with a second optimisation only for a measure that still fails, in a sub-space, with the ribs as the variables. It is written as LOP-16's next steps on the [loop's page](status.md). The first entry of zenryx's [differentiators](../product/differentiators.md) comes from it: the interpretation step done many times overnight, every reading judged at equal mass.

## The engineer's questions, and the answers given

| Time | Question | Answer |
|---|---|---|
| 20:16 | "I still don't see drastic difference" | the presets shared one shell: the recipe now holds the massing |
| 21:17 | fastcae's rib constraints; fillets on rib tops | LOP-15: the rules read and carried over; swept, fully rounded ribs |
| 21:42 | ribs "not even touching the bore and ending anywhere … higher than bore" | every rib between hard points; the bosses stand over the ribs |
| 21:45 | which ribs are required? does topology optimisation remove ribs? | load paths and panels, confirmed by FE; topology optimisation removes as well as adds; a rib's gain per gram |
| 21:46-21:48 | topology optimisation from the contract's surfaces alone, and on misalignment? | not done before (LOP-3 froze a shell); now LOP-16 |
| 22:20 | the optimisation results on the Designs page | PLT-10, the Optimisation tab |
| 22:36 | did it converge and reach the goal? | no; the goal only in a flattering voxel model |
| 22:51 | is it iterative; CAD back into the voxels; another design space? | yes, staged; the second run as a band (run 3) |
| 23:16 | topology, topography, size, shape | explained; sizing next, topography later |
| 23:41 | why start from a preset's shape? | it was wrong: track 1 reads the whole housing from the field |
| 23:49 | how was it set up? | the packaging space less the gears', bearings', shafts', differential's and seals' volumes; the skin, the motor's ring and the mounts frozen (the slices in `data/first_loop/topofree_setup.png`) |
