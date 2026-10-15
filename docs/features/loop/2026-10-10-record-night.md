# The night of 10 October: a housing drawn from the optimiser (LOP-17)

*For the engineer, morning of 10 October. Where things stand, what was built overnight, what it measured. Times IST. Updated 08:02.*

## In short

- **The night's housing, `outcome_robust_b32`:** the optimiser's field drawn as organic CAD with exact machined interfaces (`data/first_loop/look_outcome_robust_b32.png`, sent 08:01 with the gallery).
  - 11.6 kg. Castable along the contract's pulls: no closed voids, 4-5 % of the surface read undercut, and that is the facets' scatter.
  - **FE: +shaft 1.37 × its line,** with two mounts held. That is the stiffest design of the whole loop, ahead of the best hand-made one (`box1_fl`, 1.40 × at 9.9 kg, which cannot be cast: 22 closed voids, 2,406 cm² undercut).
  - **It does not pass:** 1.4 times its line, and 3.9 kg over the 7.73 kg target.
- **The optimiser now tells the truth.** Its check of the field as metal or air says what FE then reads of the drawn CAD, within 5 %: 1.43 against 1.37 for this one, 1.58 against 1.59 for the one before.
  - The night's first field had promised 0.087. As metal or air it read 5.65, because about 1,250 grey voxels had balanced each seat's two ends.
  - The cure was the robust formulation (Wang, Lazarov & Sigmund 2011): the field must hold eroded, nominal and dilated at once. Then a sharper projection (β 32).
- **What stands between it and a pass:**
  - **The drawing adds 3.9 kg** that the optimiser never placed: the skin drawn at 6 mm where the model counts 4, the joint's band, the margins round the interfaces, the bolt columns, and a closing that merges near-touching sheets.
  - **The honest optimum at 7.73 kg** reads 1.4 × the line as metal or air. Even at β 32 its last 5 % of grey carries a fourfold credit (0.39 with it, 1.43 without), so the optimiser should next work on the binary design itself.
  - **The mounts:** the objective loads none, so the optimiser joins two of the three only by chance. That is yours to decide (below).

## What was asked

At 02:12 the engineer was leaving for the day: "tomorrow morning I really want this solved properly. I want to see in CAD the new housing design based upon this, all this information which we have given in the research papers regarding the topology optimization". At 02:07 they brought Virostko et al. 2026, a generative design of a gear body: [the paper, read](../../research/2026-10-10-generative-design-gear-wheels.md). Earlier that night they had said:
- 00:45: the field-read CAD "still seems like coming from the generator";
- 01:48: "U have to identify shapes from the optimisation direction … no where close to what we saw from the production housing … I don't see u have a clear strategy on how to get intelligent creative design which are physics aware".

## The method: generative design, as the paper's tool does it

1. **The generator is the optimiser** (`topo_free.py`): the housing from its interfaces, nothing drawn by hand.
   - **Preserved:** each bearing's seat ring, the cavity's skin (one cup per half), the motor's ring, the mounts.
   - **Obstacles:** the gears' rooms with their clearances, the motor beyond its flange, the half-shafts' joints, the mounts' bolts.
   - **Loads:** every seat in peak drive and peak reverse at once. The paper found one load case alone too few.
   - **Objective:** the worst seat's misalignment over its line, at a given mass, by GCMMA (every seat and case a constraint).
   - **The model is honest:** the halves are joined at the bolts only, and the skin counts as the contract's 4 mm wall.
2. **The manufacturing route is a design variable,** as in the paper:
   - `cast`: every column of each half one piece along the pull;
   - `split` (new tonight): the same, anchored at the joint, so that the fill runs from the split out to the last metal, as a mould parted at the joint needs;
   - `free`: additive, no such rule.
3. **Each outcome is drawn as CAD the way generative-design tools draw theirs** (`outcome_cad.py`). The optimiser's field is the shape:
   - **The organic body:** smoothed, remeshed into even facets and sewn into a solid;
   - **The interfaces exact:** the seats bored, the motor's face and bore machined, the mounts, a boss at each bolt the body holds;
   - **The inside exact:** the cup's cavity.

   Every interface is made solid a margin past its size, and every kept-clear space empty a margin past its boundary, before the smoothing. So each exact cut runs through metal or air and never grazes the smooth skin: an as-cast skin with machined faces, as a casting has.
4. **Judged unchanged:** castability (`castable.py`), FE (`fe.py`, TET10, single precision, bolted halves), the grade (`grade.py`), pictures (`look.py`).

## The outcomes, judged

Every outcome is drawn by `outcome_cad.py`, and every one meshes and fills with tets. FE is `fe.py` at 8 mm TET10, judged by `grade.py`; "+shaft" is the worst seat's misalignment against its line, as the contract reads it.

| Design | From the field of | Mass | Bolts | Mounts held | Undercut (motor side / cover), voids | **+shaft × line** | Housing alone | Peak µm | First mode |
|---|---|---|---|---|---|---|---|---|---|
| `outcome_split_7.73` | split 7.73 (grey) | 10.21 kg | 10 of 14 | 1 | 3.7 / 5.3 %, none | 1.45 | 1.61 | 2,633 | 73 Hz |
| `outcome_split_7.73b` | the same, the blades cured | 10.77 kg | 9 of 14 | 2 | not run | 1.69 | 1.88 | 148 | 186 Hz |
| `outcome_robust_7.73` | robust split 7.73 | 10.58 kg | 8 of 14 | 2 | 5.0 / 4.8 %, none | 1.95 | 2.14 | 168 | 201 Hz |
| `outcome_robust_7.73c` | the same, its cover drawn at the light blur | 11.53 kg | 9 of 14 | 2 | 5.0 / 4.1 %, none | 1.59 | 1.71 | 127 | 189 Hz |
| **`outcome_robust_b32`** | the robust field sharpened to β 32 | **11.64 kg** | 10 of 14 | 2 | 5.1 / 4.3 %, none | **1.37** | 1.55 | 115 | 189 Hz |
| `box1_fl` (9 October) | hand-made | 9.92 kg | | 3 | 25 / 17 %, 22 closed voids | 1.40 | 1.43 | 53 | 808 Hz |
| `grammar4` (9 October) | the trade's grammar | 7.50 kg | | 3 | castable | 6.36 | 6.54 | 192 | 927 Hz |

- **One mount flattered the first outcome.** The split field's CAD hung from one mount (73 Hz, 2.6 mm peak). Holding two, the same field reads 1.69, not 1.45. At two mounts the robust field reads 1.59 against the split field's 1.69, at 0.8 kg more.
- **The undercut is the facets' scatter.** Walls drawn along the pull have facets tilting a few degrees either way, and there are no closed voids. The contract's pull directions are kept by filling every column from the split out to its last metal.
- **The robust outcomes' one order clash:** a mode at 1,095-1,110 Hz lies within 3 % of the second mesh's 1,127 Hz.
- **Pictures:** `data/first_loop/look_outcome_robust_b32.png` and the gallery `data/first_loop/gallery.png` (grammar4, box1_fl, split b, robust c, robust b32), both sent 08:01. The outcomes are on the Designs page, and their fields on the Optimisation tab.

## Why the first outcome read 17 times its field

The optimiser had promised 0.087 × line for split 7.73's field; its CAD read 1.45 in FE. To split the loss between the drawing and the model, `prototypes/first_loop/voxel_vs_fe.py` solves the optimiser's own voxel model on several shapes:

| Shape, in the optimiser's own model | Worst seat (× line) | Metal (free voxels) |
|---|---|---|
| The field, as optimised (with its grey voxels) | **0.087** | 9,213 (in density) |
| The same field, metal where it is 0.3 or more | 4.10 | 9,340 |
| … 0.5 or more | **5.65** | 9,148 |
| … 0.7 or more | 6.34 | 9,014 |
| The CAD, voxelised | 4.44 | 12,630 |
| The CAD plus the field's metal it lost | 2.18 | 13,603 |
| **The CAD in FE** (`fe.py`, for comparison) | **1.45** | |

- **The field's number was never a shape.** Moving 6 % of its metal, the grey part, multiplies its worst seat by 50 to 70.
- **It is not the shaft's lean being cancelled:** in the grey field the housing's own tilt is already small (0.1-0.47 × line) at every seat. The grey voxels act as tuning springs. A seat's tilt is the difference between its two ends' movements, and partly stiff voxels balanced the two ends.
- **The drawing is not the main loss.** The CAD reads better than the thresholded field (4.44 against 5.65) with more metal, and FE reads it better still (1.45). A likely reason for FE's better reading, not yet measured: the CAD draws the cup's skin a full voxel (6 mm) thick, where the model counts it as the 4 mm wall (in bending (4/6)³ = 0.30 of a voxel), and the voxelised CAD keeps the model's skin. The same 2 mm costs about 0.7 kg of the CAD's excess mass.

## The cure: the robust formulation

`topo_free.py 7.73 6 100 --route split --robust 0.15 --robust-p 16 --ramp 0`, started at 05:32 from split 7.73's field at β 8 and done at 07:11; outputs `data/first_loop/topofree_misalignment_bound_7.73kg_6mm_projected_cup_bolts_skin4_split_robust0.15.*`.
- **Three projections of the same filtered field:** eroded (threshold 0.65), nominal (0.5), dilated (0.35). Every seat's ratio in each case is bounded in all three, and the mass is the nominal's. A voxel balanced near the threshold flips to air in the eroded design and to metal in the dilated one, so no tuning by grey voxels holds in all three.
- **The shift of 0.15** keeps a plate one voxel thick (6 mm, which a casting can hold) in all three designs. A strut one voxel square, which the drawing erases anyway, holds only in the dilated one. At 0.2 every 6 mm plate would vanish from the eroded design.
- **Each seat and case's three ratios are one constraint, their p-norm** (p = 16, at most 7 % over the worst, on the safe side). With the three as 36 separate constraints, MMA's subproblem slowed from 11 s to 77 s an iteration as the three converged: near-duplicate constraints make its dual system nearly singular. The run was resumed from iteration 20 so (06:09); MMA then took 5-10 s.
- **Every bound run now ends with the binary check:** the nominal field at 0.5, all metal or air, read by the same model.

What it gave, in the optimiser's own model (`voxel_vs_fe.py`):

| The robust field | Worst seat (× line) |
|---|---|
| as optimised (10 % grey, β 16) | 0.265 (eroded 0.342, dilated 0.237) |
| metal or air, cut at 0.3 / 0.5 / 0.7 | 1.41 / **1.58** / 2.04 |
| blurred 0.6 and contoured 0.45 (the drawing's light rung) | 1.76 |
| blurred 0.7 and contoured 0.5 (its heavy rung) | 4.17 |
| **its CAD `outcome_robust_7.73c`, in FE** | **1.59** |

- **The binary check predicts FE.** 1.58 in the optimiser's model, 1.59 in FE. For split 7.73's field the same check read 5.65 against FE's 1.69. The model misjudges thin members, and the robust field has few.
- **As metal or air the robust field is honest across the thresholds** (1.4-2.0, against 4.1-6.3), but it is not below the line. Ten per cent of it is still grey at β 16, and the gap between 0.265 and 1.58 is that grey's credit.
- **The drawing's heavy rung erases thin members.** The first drawing's cover took it, as its light rung was not watertight, and read 1.95 in FE. A rung with a two-voxel closing came first in the second drawing (`c`): 1.59.

## How the outcome became CAD (what failed on the way)

| Step | First try | What it did | Now |
|---|---|---|---|
| Surface from the field | marching cubes alone | about 3,500 of 24,000 triangles slivers | marching cubes, Taubin's smoothing, then pymeshlab's isotropic remeshing: even triangles of about 6 mm, watertight |
| Remeshing | gmsh's STL reparametrisation | refused: the surface has genus 18 | pymeshlab (installed into `.venv` for this prototype, not in `uv.lock`) |
| Another extraction | VTK's surface nets | not watertight | dropped |
| The kept-clear spaces cut exactly | the smooth skin grazed by the cuts | the motor side would not mesh | interfaces solid and kept-clear spaces empty a margin past them, before smoothing: every cut through metal or air |
| The skin's thickness | blur 0.7 voxel, contour 0.5 | walls 2.5-3.5 mm, under the 4 mm least wall | a ladder: blur 0.6 with contour 0.45 first, then heavier ones until the surface is watertight and its solid valid |
| Two sheets a voxel apart | the ladder's next rung, a heavier blur | it erased thin members: the robust field's cover read 4.17 × line in the optimiser's model, against 1.76 at the light rung; finer triangles (5, 4 mm) and closing every hole did not mend the light rung | a rung with a two-voxel closing before the heavier blur: the sheets merge into one plate (the robust cover +1 kg; a 6-12 mm slot would need a fragile core anyway) |
| Edge-only contacts | contoured as they are | the cover's surface pinched, not watertight: 162 pieces in the booleans | a morphological closing before contouring |
| The bolts | an exact boss fused at each bolt | bosses floating where the field has no metal | a bolt is used where the body holds 60 % of its boss; its seat faced flat, room for a hex key over it (Ø16, 25 mm) |
| The bolts' sockets | cut against the smooth wall beside each boss | blades round 6 of the 10 bolts: two thirds of all folds over 120° | each socket inside a column of metal a margin past its cut: 591 folds to 186 on the motor side, 484 to 249 on the cover; the bolts stand in columns, as the trade draws them (+0.5 kg) |
| The mounts' ends | cleared 4 mm past the boss, inside the column's engulf | a 2 mm ring at each end | cleared 12 mm past it |
| The flange | grammar4's whole plate | 1.9 kg more, and 15 % of the motor side undercut | a band round the cup's rim, two voxels past the cavity, a flange thick each side |
| Along the pull | the smoothed field as it is | 6 % of each half undercut (the contract's pull directions are a hard rule) | each column filled from the split out to its last metal: struts stand on the flange as webs, mounts as columns |
| The least wall | a voxel of metal round the cup | on 6 mm voxels it doubled the walls (the motor side 6.27 kg) | only on voxels under 6 mm |
| A draft on the facets | each vertex moved 3° along its normal | the surface folded (2,037 self-crossing faces) | off |
| Exact surfaces (a "relief") | the footprint raised, capped by a B-spline | hills (the cover 9.9 kg), and an empty boolean | dropped |

## The night's runs

| Run | Route, mass | Result (the voxel model) |
|---|---|---|
| Run 1 | cast, 7.73 kg | stopped at iteration 90 for the anchored run (resumable); 0.21 × line, 69 % grey. At β 2 → 4 it read 7.6 × line afresh, against 0.015 a moment before: the first sign of grey flattery |
| Split 7.73 | split, 7.73 kg | 0.087 × line at β 16, 9 % grey; as metal or air 5.65 (above) |
| Robust split 7.73 | split, 7.73 kg, robust 0.15 | 0.265 × line at β 16, 10 % grey; as metal or air 1.58 (above) |
| Robust split 7.73 at β 32 | the same, sharper | done 07:51, converged at iteration 11 (`..._split_b32_robust0.15`): eroded 0.349, nominal 0.390, dilated 0.312, 5 % grey; **as metal or air 1.43**; its CAD in FE 1.37 |

The queue's other runs (split 9 kg, free 7.73 kg) were stopped at 05:30: without the robust formulation they would have made fields of the same kind.

## For the engineer to decide

- **Load cases for the mounts.** The objective loads only the seats, so the optimiser joins a mount only where it happens to help them. Here it joined one or two of the three, and how many changes the verdict: the same field reads 1.45 with one mount held and 1.69 with two. A load case through the mounts (the motor's mass under the vehicle's accelerations) would make it join all three, and make the comparison with `box1_fl`'s three mounts fair. Load cases are yours to set.
- **The mass.** The drawn CAD is 3.8 kg over the field's 7.73 kg. My next step, unless you choose otherwise: draw the skin at the contract's 4 mm (`cup.py`'s exact cup with the organic body on it), and the interfaces' margins and the band no larger than meshing needs. The mass the optimiser places is then the mass the casting has.
- **Whether a pass is reachable at 7.73 kg.** The honest optimum there reads 1.4 × the line as metal or air. My next step for the optimiser: optimise the binary design itself, a final phase where the projection is a step and the gradient comes from the eroded and dilated neighbours, so that no grey is left to give credit. If that still stands above the line, the next levers are the layout the contract fixes (the bearing spans, the split's place) and the mass target, both yours.
- **Commit:** everything since 9 October 04:49 is uncommitted, by your word.
