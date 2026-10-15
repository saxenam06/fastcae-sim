# The overnight campaign of 13 October: a clean housing for a CAD engineer (LOP-28)

**13 October 2026, 00:20 (rewritten 18:32).** Where to start after a compaction. The engineer left at 00:16 and handed over the campaign: "use all the information given to you so far and go step by step... perform all iterations step by step.. and learn from the previous one and then plan next iteration until we achieve a good production quality shape that we can hand over to CAD engineer." Before it: [the evening's record](2026-10-12-record-evening.md) (the empty start, the baseline, the three junction cases, the bending measure). Every number below is from the designs' own records in `data/first_loop/`. Nothing is committed.

## 1. The goal and the rules

- **The goal:** one housing a CAD engineer can start from. It must:
  - pass every graded line: the worst seat at most 52.2 µm, the tilt at most 1.0 × its line, no mode within 3 % of a gear order;
  - weigh no more than the reference (7.73 kg);
  - be oil-tight and castable along the pull;
  - look like a production casting: calm panels, clear ribs, whole brackets, no wrinkles, no lumps.
  - Its rung is said as it is (simulation-feasible, process-rule-feasible), never "production-ready".
- **The reference and fallback:** `empty1_5.5kg` (the engineer, 12 October 22:27), unchanged: 5.82 kg, 37.9 µm, tilt 0.997 ×, 742 Hz, no clash, oil-tight.
- **The order** (a reviewer's, pasted by the engineer at 00:16):
  1. a new baseline with region-aware rules, at the same mass, loads, design space and objective;
  2. the sloped web on top of it, the rules kept active, the brackets protected, the whole housing re-optimised;
  3. targeted refinements where the evidence points (case 1: where taking metal away threatens the bearings; case 2: local thickness control, not a global cap);
  4. **the least mass with every rule active, not optional** (the engineer, 00:18: "is the minimum mass not part of the optimisation... that would kill mass iterations"; 00:19: "Minimise mass but without compromising with the objective"): `--objective mass_tilt` replaces stepping the budget down. Its lines then bind, so the factor of safety is raised until FE confirms every line (case 1b failed the tilt by 4 % at 1.15): the mass comes down, the stiffness, the alignment and the shape rules do not;
  5. one final geometry, validated, drawn as cleanly as the tools can, handed over.
- **Three rules** (the reviewer's):
  - one major change at a time;
  - never trade validity for looks: the best validated design stays until a challenger beats it;
  - do not over-regularise: clean the broad panels, keep the brackets working, leave the ribs free.
- **Mine:**
  - **No new load case** without the engineer: the brackets are protected by a least metal each, not by mount loads (the bump load waits for the engineer's word and values).
  - **One heavy job at a time:** free memory and the GPU checked before each run.
  - **No commit.**

## 2. How each iteration is judged

- **The numbers:** the grade (kg, worst seat, tilt, first mode, clashes), oil-tightness, castability (undercut, the largest member section against the 16 mm lump gate).
- **The shape:**
  - `roughness.py`: the outer surface's bending, sqrt(s_xx² + s_yy² + 2 s_xy²), by region, on the optimiser's heights and on the drawing;
  - `metal_by_part.py`: where the metal moved, by bore, mount, flange and walls;
  - `lump_maps.py`: the patches' metal off the inside;
  - `look.py <design> face`: the pictures along the pull.
- **Clashes within the 3 % band are inside the drawing's noise** (12 October: the baseline drawn at 0.4 gained two), so they never decide between designs alone.
- **Compare designs drawn at the same member level.**

## 3. Iterations

(Each: what was seen, the hypothesis, the one change, the settings, the result, the lesson, the next.)

### The tools built for it (00:20-00:31)

- **The semantic rules in the optimiser** (`topo.py`; `topo_free.py --bending <regions.npz> --brackets <brackets.npz>`), one GCMMA constraint each, on the one design of the compliance and p-norm loops:
  - **a bending limit by region** (`bending_operator`, `bending_value`): on the columns' continuous heights (`Voxels.column_heights`, read through a soft cap at each column's length), the second differences s_xx, s_yy, s_xy wherever all nine columns of the stencil stand on one base; each region's weighted mean of one of two measures at most its bound:
    - **the bending**, s_xx² + s_yy² + 2 s_xy²: a calm patch, free to slope, with no steps, ribs or ripples;
    - **the double curvature** (13 October 00:27), (s_xx s_yy − s_xy²)²: zero on every surface that curves one way at a time (planes, slopes, straight and curved ribs, round collars: what production castings are built from), large on bumps, dents, saddles and wrinkles. It came from a conflict measured at 00:20: a rib's sides bend most of all, so the bending alone on the large panels would flatten the ribs the engineer likes.
  - **each bracket's least metal**: the free voxels round each mount (`mode_shape.parts`), their metal at least a floor.
- **The regions** (`semantic_regions.py <reference run> --label <l>`), all from the contract's geometry, never a run's metal (D16):
  - the bridges between two bearings of a half (`--bridge <half>:<a>:<b>:<bound>[:bend|dev]`);
  - each half's rings round its bosses, 15 mm past each boss (`--bosses`);
  - each half's end walls outside the rings and bridges (`--panels`);
  - weights fading to 0 over 10 mm outside each region; bounds in 1/m, or a share of the reference run's own (`0.3x`);
  - the brackets' floors a share of the reference's metal round each mount (`--brackets 1.0`).
- **The derivative check** (`topo_gradcheck.py 10 4 2 --semantic`): PASS, the worst relative error 1.4·10⁻⁴; the new measures 4·10⁻⁸ to 7·10⁻⁷.
- **The surface from the optimiser's continuous heights** (`LOOP_HEIGHT_DRAW=1`, `outcome_cad.continuous_depth`, 00:35): the voxels round each column's height to whole 4 mm (the staircase the drawings show), so each first-run column's top is taken before the rounding (its base plus its height, capped at its own length), interpolated bilinearly between the columns' centres onto the 2 mm grid, and drawn by the height-field drawing (`height_field`: castable along the pull by construction), the voxels' own depth where a column is wholly frozen (the seats' rings, the bolts' bosses). Tried on 11 October from cells (the cells' rounding brought the steps back) and dropped then for the mounts' lugs (runs past a bracket's room, drawn apart); to be measured on the baseline.
- **The runner** (`campaign_run.sh <design> <propose.py's arguments>`): the proposal under `memory_guard.py` (the run ended if the available memory stays under 900 MB; it was 3.3 GB with the engineer's editor, browser and snipping tool open), then the faces along the pull.

### Iteration 1: the region-aware baseline (`sem1_5.5kg`, step 1)

- **Saw:** the baseline's lumps where loads meet (the bridges between the intermediate and output bearings, both halves), bumpy collars round the bosses, wrinkles on the motor side's panels; case 3 showed a clean form there takes metal from the brackets.
- **Hypothesis:** bounding each region's own kind of roughness, with each bracket's metal held, cleans the look at a small cost in stiffness, because the lumps' metal can be reshaped (case 1b: it is needed, not spare).
- **The one change:** the semantic rules, every other setting the baseline's (5.5 kg, compliance with every tilt and bed held at 1/1.15 of its line, peak drive, the 24 mm band, 4 mm voxels, the 6 mm plan filter, the empty start).
- **The regions (`s1`)**, measured on the baseline:

  | Region | Rule | Columns (inside / fade) | The baseline's (1/m) | The bound (1/m) |
  |---|---|---|---|---|
  | cover, intermediate-output bridge | bending | 292 / 125 | 1454 | 436 (0.3 ×) |
  | motor side, intermediate-output bridge | bending | 283 / 116 | 1601 | 480 (0.3 ×) |
  | cover, bosses' rings | double curvature | 1355 / 812 | 1521 | 761 (0.5 ×) |
  | cover, panels | double curvature | 1950 / 596 | 384 | 192 (0.5 ×) |
  | motor side, bosses' rings | double curvature | 1638 / 786 | 1161 | 581 (0.5 ×) |
  | motor side, panels | double curvature | 1248 / 542 | 449 | 225 (0.5 ×) |

  The brackets' floors: mount-1 51.8, mount-2 64.7, mount-3 50.6 cm³ (the baseline's own).
- **Command:** `campaign_run.sh sem1_5.5kg --budget 5.5 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.15 --empty --bending s1_regions.npz --brackets s1_brackets.npz`; started 00:31 (task `b7h8epk31`).
- **Expected:** the seats a few percent softer than 37.9 µm, the tilt held, the bridges calmer and the bosses rounder.
- **Result** (00:38; `campaign_compare.py empty1_5.5kg sem1_5.5kg`, `compare_sem1_5.5kg.png`):

  | | kg | Worst seat µm | Tilt × | First mode | Clashes | Undercut motor / cover | Largest member mm | Oil-tight |
  |---|---|---|---|---|---|---|---|---|
  | `empty1_5.5kg` | 5.82 | 37.9 | 0.997 | 742 | none | 0.62 / 0.20 % | 28.9 / 28.4 | yes |
  | `sem1_5.5kg` | 5.73 | 40.7 (+7 %) | **0.922** | 746 | 2456, 2533 Hz (s1's 2500) | 0.89 / 0.24 % | 28.8 / 28.1 | yes |

  - **In the optimiser's model** (the binary check): compliance 1306 → 1316 N·mm (+0.8 %), the tilt 0.998 of its line, the worst bed 0.87 → 0.89. Every region settled at its bound (the bridges −70 %, the rings and panels −50 %); mount-3's bracket on its floor, the others over theirs.
  - **The metal moved little** (1,723 of 1,724 cm³ placed): the cover's input bore −9, the motor side's output bore −6; the intermediate bore's surroundings +6 and +8; no bracket lost metal.
  - **The clashes** are the stage-1 order's band again, where a mode lands by chance in some drawings (the evening's lesson 7).
  - **The look barely changed:** the drawing rounds every column to whole 4 mm voxels, and that staircase hides the calmer heights underneath. Drawn from the continuous heights next (`LOOP_HEIGHT_DRAW=1`), the reference too, for a fair comparison (task `boyytimt1`, 00:39).
- **Lesson:** the semantic rules cost the optimiser almost nothing (+0.8 % compliance; FE's tilt even improved), so they can be stronger; their effect is invisible until the drawing stops rounding the heights.

### The drawing from the continuous heights (00:39-00:50)

- **Two faults found and fixed:**
  - a continuous depth landing exactly on a cell's centre (the sealing land's least height, 9 mm, where the optimiser added nothing) put marching cubes' vertices nanometres apart; the vertex merge tore the surface, and the motor side's body was dropped (`sem1h_5.5kg`'s first drawing lost two mounts). Every margin within 20 µm of a node is now nudged off it (`height_field`);
  - a column's height counts its free voxels only, so a frozen seat's ring inside the column must be passed over: base + h t cut the cover's output seat's ring short (`empty1h_5.5kg`'s first drawing: that seat 315 µm). `roughness.tops` now gives each column's true top (`top_true`).
- **The baseline drawn so** (`empty1h_5.5kg`): 5.64 kg, 39.8 µm, tilt **1.061 ×**, 772 Hz, a clash at 2459 Hz; undercut 0.20 / 0.08 % (a third of the voxel drawing's). Lighter than the voxel drawing (5.82 kg) and nearer the model's own 5.50 kg, so the model's flattery shows more: the tilt 6 % over its line.
- **The look is not better** (`smooth_vs_voxels.png`): the staircase goes, but sharp cliffs stand along the voxelised rooms' outlines.

### The engineer's correction (00:50): protect the functional geometry first

- **The engineer** (circling the whole of both halves of `compare_sem1_5.5kg.png`): "I don't think there is an improvement... we should stop trying to make the whole surface smoother and instead prevent the optimiser from deforming surfaces that have a defined engineering purpose." A cylindrical bearing seat stays cylindrical; a flat mounting or sealing surface stays flat; the optimiser free to add material round them. Hard geometric preservation first, soft shape penalties second (after Humphry, Ebrahimi, Morris & Butscher 2025: protected interfaces keep their form while the rest evolves). The semantic curvature penalties are paused.
- **What the empty start protected until now:** the bores, the mounts' holes and faces, the bolts' holes and the split face are cut exact in every drawing; but only a 4 mm ring round each seat was fixed in the optimiser. The bosses round the bearings and the sealing flange were the optimiser's lumpy voxel metal, the lugs and bolts' bosses the grid's 2 mm steps.
- **The protected interfaces** (`topo_free.py --empty --protect`, `build_free(..., protect=True)`; `outcome_cad.exact_interfaces`), at the layout's own dimensions:
  - each bearing's boss: the layout's cylinder (`boss_r`, 1.25·D + 10) along its seat; in the optimiser the voxels wholly inside it;
  - the sealing land (A26: 10 mm round the inside, 9 mm each half) and the bolts' Ø 20 bosses on it, each voxel at the share it fills, as the fixed-shell set-up held them;
  - the mounts' lugs (Ø 36);
  - all of them fused exact (CadQuery cylinders and the land's circles) over the field's metal, whose grid copies stand 2 mm under their faces; the frozen voxels drawn only where free metal stands on them.

### Iteration 2: the protected interfaces (`prot1_5.5kg`, P1)

- **Hypothesis:** with the functional geometry exact and fixed, the field only adds ribs, webs and transitions round it, so the bosses and the flange read as designed and the members between them come out cleaner.
- **The one change:** `--protect`; everything else `empty1_5.5kg`'s (5.5 kg, compliance with every tilt and bed at 1/1.15 of its line, peak drive, band 24, 4 mm, the 6 mm plan filter); no semantic penalties.
- **Set-up:** 2.62 kg fixed (the baseline 1.02): the bosses 10,695 voxels, the land and bolts' bosses 6,306, the mounts 1,536; 2.88 kg to place; the walls' least metal about 2.00 kg.
- **Command:** `campaign_run.sh prot1_5.5kg --budget 5.5 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.15 --empty --protect`; started 00:56 (task `b5i1p93b8`).
- **Result** (01:03; `compare_prot1_5.5kg.png`):

  | | kg | Worst seat µm | Tilt × | First mode | Clashes | Undercut motor / cover | Oil-tight |
  |---|---|---|---|---|---|---|---|
  | `empty1_5.5kg` | 5.82 | 37.9 | 0.997 | 742 | none | 0.62 / 0.20 % | yes |
  | `prot1_5.5kg` | 6.17 | 48.9 | **1.131** | 611 | none | **3.83 / 5.66 %** | **no** (at the output seat's outer end) |

  - **In the model:** it could not hold the lines within the budget: 3.23 kg placed against 2.88 (+12 %), the compliance 1599 N·mm against the reference's 1306 (+22 %), the tilt and beds at their lines.
  - **The look is what the engineer asked for at the interfaces:** crisp circular bosses round the bores, crisp lugs and bolts' bosses.
  - **Three faults:**
    - the layout's bosses (Ø 1.25·D + 10) are wider than some lobes; their ends overhung open air (the undercut faces at z −21 on the motor side and 57 on the cover, the bosses' ends);
    - frozen voxels drawn only under the run's metal left a 2 mm gap past the output seat's boss (the leak);
    - the bosses took 1.6 kg the optimiser had used better elsewhere: the bores' surroundings lost 30-110 cm³ each of free metal, the brackets 22-29 cm³ each.
- **Lesson:** protect the interfaces at the size the part can carry: a boss no wider than its lobe, and drawn so the inside stays closed.

### Iteration 3: the protected interfaces, bosses clipped to their lobes (`prot2_5.5kg`)

- **The one change from P1:** each boss clipped in plan to its half's lobes (each room grown by the least wall), in the optimiser and in the exact drawing; the drawing keeps every frozen voxel the exact parts do not cover (`outcome_cad.protected_voxels`).
- **Command:** as P1 (`--empty --protect`); started 01:06 (task `bfufi09bi`).
- **Result:** 2.14 kg fixed (the bosses 7,666 voxels, from 10,695), 3.36 kg to place. **In the model** it held the lines only 6 % over its free budget (3.55 kg placed), the compliance 1571 N·mm (+20 %). **The drawing failed:** it lost mount-2, and it still leaked at the motor side's output seat.
  - **Mount-2's bracket starved:** 65 → 13 cm³ of free metal (`metal_by_part.py`); every bore's surroundings lost 20-55 cm³. The protected bosses squeeze a fixed budget, and the optimiser pays from the brackets, as case 3's web did.
  - **The leak:** the drawing's "covered by the exact parts" mask (`protected_voxels`) reached half a voxel past each boss's ends, so the frozen seat ring's end voxels, which close the bore's end, were dropped. Fixed: the mask covers the seat's length only.
- **Lesson:** protected interfaces at a fixed budget take metal from the unprotected functions (the brackets); protect the brackets' function with them, and let the mass follow.

### Iteration 4: the functional package at the least mass (`prot3_least`)

- **Three changes from P2, taken together** (P2 could not hold the lines at 5.5 kg; the engineer, 00:19: "minimise mass but without compromising with the objective"):
  - each bracket's metal at least the reference's (51.8, 64.7, 50.6 cm³; `p3_brackets.npz`, written on P2's voxels with `semantic_regions.py --bracket-floors`), the brackets' functional protection;
  - the least metal that holds every tilt and bed (`--objective mass_tilt`), 7.0 kg a ceiling only;
  - the lines held at 1/1.25 of themselves (`--safety 1.25`; the least-metal case 1b read the tilt 4 % over at 1.15).
  - If it fails, they are taken apart.
- **Command:** `campaign_run.sh prot3_least --budget 7.0 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.25 --empty --protect --brackets p3_brackets.npz --objective mass_tilt`; started 01:13 (task `biko00an8`).
- **In the model** (01:17): the least metal 3.71 kg placed with 2.14 kg fixed, 5.85 kg in all; the tilt 0.997 and the beds 1.002 of their lines at 1/1.25; every bracket on its floor.
- **FE was stopped by the memory guard** (01:18): the drawing with the CAD-fused interfaces meshed to 1.96 M unknowns, and the modes took the available memory to 390 MB.

### The engineer's instructions at leaving (01:20-01:30)

- **The brief** (01:2x): "I need a nice solution out of here, such that it can be handed over to a CAD designer who can clearly find patterns and can draw it in field mesh, and also draw the final production housing in the field mesh... The shapes can also be of many types, and only optimizer can as closely as can tell or convey the shapes of the members, the better it can be... So you're on your own until the morning. Keep a good track... if you need to do web search... do a targeted search."
- **"Why did u build those regions in cad … you should have built it in field only"; "Everything all protected regions should be in field only."** The CAD fusion (`exact_interfaces`) mixed the two worlds again; it is removed. The protected interfaces are now a density in the same field as the run's metal (`exact_walls.interface_density`), from their exact shapes, contoured once with everything else; only the machined faces (bores, holes, the split face) are cut exact.
- **01:30:** "There is no expectation to build the cad as of now… if we can achieve a production quality housing geometry that meets the goal and can be delivered to a cad designer who gets clear direction about the features and members to be drawn where and in what shape then that's sufficient." The deliverable: the field-mesh housing, every line by FE, and a map of its features and members (where, what shape, what size).

### P3 drawn in the field (`prot3f`, `LOOP_EXACT_WALLS=1`)

- **Result:** 6.12 kg, worst seat 39.6 µm, **tilt 1.256 ×** (the cover's input seat, 0.431 mrad), 669 Hz, a clash at 2492 Hz; undercut 0.67 / 0.18 %; oil-tight; 3 of 3 mounts, 13 bolts; 1.12 M unknowns.
- **The look is the closest to a production casting so far** (`compare_prot3f.png`): round lobes, round bosses blended into the walls, one smooth body.
- **Why the input seat is soft (01:36):** the rooms (`cupmod.pieces`) include each bearing's own pocket, from the split to its seat, so "the lobe" round a seat standing past its gear room is the pocket grown by the wall: clipped to it, the cover's input boss (r 37.5) became a 4 mm tube (r 26-30), and so did most others.
- **The fix:** each boss a castable tower: the layout's cylinder from a least wall past its seat's outer end down to the split (the rooms cut exact after), in the optimiser (`build_free`'s `protect`) and in the field (`interface_density`) alike; no clipping (the column fill from the split already prevents an overhang in the field drawing).
- **Memory:** FE beside castability peaks near the machine's limit with the engineer's applications open; `campaign_run.sh` takes `GUARD_FLOOR`/`GUARD_STRIKES` (600 MB, 4 strikes for the larger meshes).
- **P3 with voxel walls** (`prot3v`, the same run): 6.61 kg, 39.0 µm, tilt 1.036 × (the input seat 0.326 mrad against 0.431 drawn with the exact walls), 656 Hz, a clash at 2568 Hz. The exact walls cost about a fifth of that seat's tilt, and even the heavier voxel drawing misses by 4 %.

### Iteration 5: the bosses as castable towers (`prot4_least`)

- **The one change from P3:** each boss the layout's full cylinder from a wall past its seat's outer end down to the split, in the optimiser and in the field; drawn in the field (`LOOP_EXACT_WALLS=1`); the brackets' floors built in the run from its own voxels (`--brackets floors:51.8,64.7,50.6`).
- **Set-up:** 3.67 kg fixed (the bosses 17,654 voxels), the walls' least metal about 1.05 kg.
- **In the model:** 2.50 kg placed, 6.17 kg in all, the lines at 1/1.25.
- **Result** (`compare_prot4_least.png`): **6.91 kg, 36.6 µm, tilt 1.036 ×** (the cover's input seat, 0.347 mrad), 717 Hz, clashes at 1114 Hz (s2's 1127) and 2526 Hz (s1's 2500); undercut 1.29 / 0.14 %; oil-tight; 1.33 M unknowns.
- **The look:** the most production-like so far: the cover's lobes round, its bosses blended into them like cast cans, a few straight ribs on the big lobe, the flange and bolts' bosses clean; the motor side's bosses round, the arms to the brackets still the optimiser's rough members.
- **The modes cannot be held by the optimiser's model** (`model_modes.py`, new): its spectrum starts with four equal local modes at 412 Hz, against FE's 717-3071 Hz (ratios 0.57 to 0.21): the voxel model's local flaps, as on 12 October. The clashing modes (`mode_shape.py`) are global (the bores rocking: the cover's output and intermediate bores, the motor side's output bore). They are moved by design moves judged in FE.
- **The cover's input seat** is read 26-30 % softer by FE than by the model in every lean drawing (P3f, P3v, P4): its own factor of safety, learned from FE, `LOOP_SAFETY_SEATS="input +z=1.4"` (`topo.Voxels`: a seat's own factor), the rest at 1.25.

### Production's rules against ours (the engineer, 01:54: "compare the pictures... what are those basic rules which they follow, which ours are not following, and if you constrain, then it starts creating clean patterns")

Read from the engineer's pictures (the sheets `compare_production_faces.png`, `compare_production_night.png`: Nissan's two-stage reducer case, Anhui Gaojian's HPDC housing face-on, the 17 pictures of 11 October) and the research notes ([9 October](../../research/2026-10-09-production-housings-against-ours.md), [11 October](../../research/2026-10-11-production-ev-housings-against-the-ribbed-cad.md)):

| Production's rule | Ours (P4-P5) | The constraint that says it | State |
|---|---|---|---|
| One smooth shell round the gears, its walls plain between the ribs | walls thickened in waves between members ("paint") | **plain walls:** metal beyond a wall's least height either none or a member at least 6 mm tall (`LOOP_WALL_GATE=6`, `topo.Voxels._wall_extra`) | R1, queued |
| Every surface curves one way at most: plain panels, round lobes and bosses, ribs with flat walls (straight, or arcs round a boss) | domes, dents, saddles and loops where loads meet | **one-way curvature everywhere:** the double curvature, (s_xx s_yy − s_xy²)², at most half the reference's on every surface (`semantic_regions.py --everywhere 0.5x`, `--bending`) | R2, queued |
| Ribs thin (4-6 mm, thinner than the wall), low (10-25 mm), one thickness a family | members 13-14 mm wide (median), up to 67-86 | **thin, spaced members:** at most 8 mm wide in plan, 20 mm apart (the plan rule, `--plan-gap 20 --plan-width 8`; it counts all metal, so it must count only the metal beyond each wall's least height in the empty start) | R3, to adapt |
| Hard points first: a thick round boss at each bore, bolts' bosses at a pitch, lugs | held (`--protect`, in the field) | the protected interfaces | in force |
| Every rib ends on something (a boss, a ring, a node, the rim) | members end in the open, or blend | follows from R1-R3 (a thin member that ends in the open carries nothing, so the optimiser removes it) | to see |
| Low members, hugging the shell | held (24 mm envelope) | `--band 24` | in force |
| Gussets at every overhang (bolts' bosses, lugs) | arms to the lugs; few gussets | open | - |

What each rule leaves free: where the members go, how many, their directions and heights; the optimiser still finds the load paths (the engineer, 11 October 13:07: no set patterns).

### Iterations 6-7: a seat's own factor, learned from FE (`prot5_least`, `prot6_least`)

- **P5** gave the cover's input seat its own factor (1.4): 6.93 kg, 35.9 µm, tilt 1.038 ×, clashes at 1135 and 2546 Hz. The input seat improved 8 %, the worst ratio did not move.
- **Why** (`seat_ratios.py`, new: each seat's misalignment by FE and by the model, against the true line): the governing seat is the motor side's **intermediate** seat, not the input's. FE reads it 1.29-1.30 × the model in the protected least-mass designs (1.15 in the reference); the input seat was at 0.92-0.96. The FE log's "worst tilt" is a seat's own rotation, not the graded misalignment: read the grade's ratio, not the log's.
- **P6** (`LOOP_SAFETY_SEATS="intermediate -z=1.4"`, the rest 1.25), 01:56-02:02: **6.94 kg, 36.8 µm, tilt 0.961 ×, 690 Hz, oil-tight, undercut 1.23 / 0.14 %; one clash: 2498 Hz at s1's 2500.** Every line passes but that mode. The intermediate seat: FE 0.961, the model 0.714 (FE / model 1.35).
- **The clashing mode** (`mode_shape.py prot6_least --all`): mode 8 at 2498 Hz, the cover's output bore 25 %, its intermediate bore 23 %, the motor side's input bore 20 %; mode 9 at 2611 Hz the cover's output bore 31 %. Stiffening the cover between those bores moves both up; mode 8 must reach 2575 Hz (+3.1 %). Kept for the final design (the rules reshape that region first).

### Rule 1: plain walls (`rule1_wall`, P6 + `LOOP_WALL_GATE=6`)

- **Derivative check** (`LOOP_WALL_GATE=6 topo_gradcheck.py 10 4 2 --empty`): PASS, 5.8·10⁻⁴.
- **Result** (`compare_rule1_wall.png`): 6.96 kg, **48.2 µm (+31 %)**, tilt 0.923 ×, 595 Hz, two clashes; undercut 1.22 / 0.15 %; oil-tight. The double curvature everywhere −2 % (cover), −9 % (motor side).
- **The look did not change:** the exact-walls drawing already takes only the whole voxels of metal beyond each least wall (`exact_walls.extra_placed`), so a thin layer of paint never reaches the drawing. The gate only made the members harder to grow (the seats 31 % softer).
- **Dropped.**

### Rule 2: one-way curvature everywhere (`rule2_dev`, P6 + `--bending dev1_regions.npz`)

- **The regions** (`semantic_regions.py <P5's run> --label dev1 --everywhere 0.5x`): every first-run column of each half, the double curvature at most half P5's (295 /m on the cover, 325 on the motor side).
- **Result** (`compare_rule2_dev.png`): 6.97 kg, 36.8 µm, tilt 0.955 ×, 693 Hz, one clash; undercut 1.24 / 0.12 %; oil-tight. In the model the limits bind (−50 % and −53 %), at no cost (compliance 1400.5 N·mm).
- **The look is nearly the same as P6's.** The double curvature lives in the heights; what reads as loops and blobs is the members' layout in plan (where the metal stands and how wide it spreads), drawn from whole voxels. A rule on the heights cannot change it; a rule on the plan can.
- **Kept** (free, and it calms the heights), but not the lever for the look.

### Rule 3: thin, spaced members (`rule3_thin`, P6 + `--plan-gap 20 --plan-width 8`)

- **The plan rule in the empty start** (`topo.plan_share`'s mask, new): only the metal beyond each wall's least height counts as a member, so a bare wall is none.
- **Stopped at iteration 98** (02:25): the plan share stuck at 0.63 against its 0.5, with 3.21 kg placed (P6: 2.54) and every line at its bound. At the least mass, with the bosses held as towers and the brackets on their floors, the members that carry the brackets and bridges cannot be 8 mm wide and 20 mm apart and still hold the lines; the run would have gone to its last iteration infeasible.
- **Lesson:** production's thin ribs are not a least-mass optimum for one static case; they come with spare mass (and with noise and other cases the optimiser does not see). Tried again only at a fixed budget with room to spare, if at all.

### Candidate 1 (`final1`): P6 + one-way curvature + a floor on the cover's bridge

- **The design move on the mode:** at least 100 cm³ on the cover's intermediate-output bridge (`LOOP_FLOORS="cover:intermediate:output:100"`; P6 had 77.4 cm³ there, walls included).
- **Result:** 7.00 kg, 37.2 µm, **tilt 1.001 ×** (the intermediate seat; FE / model 1.40), 695 Hz, **the mode at 2508 Hz** (+0.4 % only); oil-tight; undercut 1.25 / 0.10 %.
- **Lesson:** the floor added 23 cm³ to the bridge and moved the mode 10 Hz; it needs 77 Hz (+3.1 %). Mode 8 is the cover's big end-wall panel flexing between its output and intermediate bosses: a panel mode. Production stiffens such panels with radial ribs from the boss to the rim.
- **Next moves:** the intermediate seat's factor to 1.5 (the model's flattery there grew to 1.40); production's panel spokes as the design move on the mode (`LOOP_PANEL_SPOKES="30:6:10"`, `exact_walls.spoke_density`, in the field: every 30° from each boss across the end walls, 6 mm thick, 10 mm proud), first drawn on P6's run (`p6spk`, queued after `rule3b_thin`).

### Production's panel spokes, drawn on P6 (`p6spk`)

- **The move:** P6's run drawn again with spokes every 30° from each boss across the end walls, 6 mm thick, 10 mm proud, in the field (`LOOP_PANEL_SPOKES="30:6:10"`).
- **Result:** 7.32 kg (+0.38), 36.6 µm, **tilt 1.192 ×** (the intermediate seat, from 0.961), 679 Hz, **the mode at 2533 Hz** (+1.4 %; mode 9 +6.7 %).
- **Lesson:** spokes the optimiser did not know about stiffen one side more than the other, and a seat's misalignment is relative to its shaft's chord: the tilt got worse. They must be fixed in the optimisation, so it sizes everything else round them. Mode 8 lives on the cover: spokes there.

### Candidate 2 (`final2`): the cover's spokes fixed in the optimisation

- **Changes from P6:** production's panel spokes on the cover (every 30°, 6 mm, 12 mm proud) fixed with the protected interfaces (`topo_free._spokes`, `LOOP_PANEL_SPOKES="30:6:12" LOOP_SPOKE_HALVES=cover`) and drawn in the field; the intermediate seat at 1/1.5 (its FE / model 1.40 in `final1`); 7.2 kg a ceiling.
- **The one-way curvature is left off:** its regions are per column, and the fixed spokes take 58 columns out of the field (10,039 against 10,097); it had changed neither the numbers nor the look.
- **Set-up:** 4.00 kg fixed (the spokes 2,556 voxels, the bosses 19,637). Started 02:41 (task `b7azabq43`).
- **Result** (`compare_final2.png`, `member_map_final2.png`): **7.22 kg, 40.6 µm, tilt 0.896 ×, 587 Hz, oil-tight, undercut 1.22 / 0.12 %; one mode at 2440 Hz, 15 Hz inside s1's band** (−2.4 %; the band ends at 2425). Mode 5 at 1166 Hz, 0.4 % clear of s2's band. Every other line passes, the tilt with margin (the intermediate seat FE 0.896, FE / model 1.34).
- **The look:** the cover carries production's wheel of spokes round its output boss across the big lobe, and spokes on its intermediate and input lobes (as the Nissan reducer case of the engineer's pictures); the motor side keeps the optimiser's own members (arms to the three lugs, the bridge network).
- **The modes** (`mode_shape.py final2 --all`): mode 8 (2440 Hz) 21 % the motor side's input bore, 19 % the cover's output bore, 17 % its intermediate bore, 11 % mount-3; mode 5 (1166 Hz) 21 % the cover's intermediate bore, 16 % the motor side's output bore, 14 % its input bore.

### Candidate 3 (`final3`): the cover's spokes 14 mm tall

- **Result:** 7.25 kg, 42.7 µm, tilt 0.898 ×, 518 Hz, **mode 8 still at 2440 Hz**; oil-tight. The spokes' height does not move mode 8: the cover panel is not where it is decided.

### The mode's last moves (`mode_queue.sh`, running from 02:53, task `bg884b1f1`)

- `final4`: the spokes on both halves (the motor side's input bore carries 21 % of the mode);
- `final5`: a lighter housing (every line at 1/1.2, the intermediate seat still at 1/1.5);
- `final6`: mount-3's bracket at least 70 cm³ (it carries 11 % of the mode).

| Variant | kg | Worst seat µm | Tilt × | First mode | Mode 8 (s1's band 2425-2575) | Mode 5 (s2's band 1093-1161) | Oil-tight |
|---|---|---|---|---|---|---|---|
| `final2` (the cover's spokes) | 7.22 | 40.6 | 0.896 | 587 | **2440** | 1166 | yes |
| `final3` (spokes 14 mm) | 7.25 | 42.7 | 0.898 | 518 | **2440** | 1172 | yes |
| `final4` (spokes on both halves) | 7.67 | 37.4 | 0.841 | 586 | **2508** | 1087 | yes |
| `final5` (every line at 1/1.2) | 7.16 | 46.7 | 0.952 | 487 | **2438** | 1222 | yes |
| `final6` (mount-3 at 70 cm³) | 7.25 | 41.4 | 0.926 | 562 | **2433** | 1237 | yes |
| `final7` (mount-3 at 110 cm³) | 7.35 | 36.2 | 0.942 | 714 | 2581 (clear, +3.2 %) | 1014 / 1279 (clear) | yes |
| `final8` (mount-3 at 150 cm³) | 7.48 | 33.8 | 0.887 | 742 | 2587 (clear) | **1102** (mode 4, −2.2 %) | yes |

- **Read:** with the cover's spokes, mode 8 sits at 2433-2440 Hz whatever else changes; the motor side's spokes lift it 70 Hz; more metal on mount-3's bracket lowers it (7 Hz for 19 cm³): a tuning mass. Every other line passes in all five.
- **Then** (`mode_queue2.sh`, 03:12-03:23): mount-3's bracket at 110 cm³ (`final7`) and 150 cm³ (`final8`).

### `final7`: every graded line passes (03:17)

- **Set-up:** `final2`'s with mount-3's bracket at least 110 cm³. Command: `GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.5" LOOP_PANEL_SPOKES=30:6:12 LOOP_SPOKE_HALVES=cover campaign_run.sh final7 --budget 7.4 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --empty --protect --objective mass_tilt --safety 1.25 --brackets floors:51.8,64.7,110`.
- **Result:** **7.35 kg** (motor side 4.05, cover 3.29; 7.73 to beat), **worst seat 36.2 µm** (52.2), **tilt 0.942 ×** (the intermediate seat; FE / model 1.41), **first mode 714 Hz, no mode within 3 % of an order** (modes 714, 752, 951, 1014, 1279, 1511, 1919, **2581**, 2804, 2914 Hz), **oil-tight**, undercut 1.30 / 0.52 %, 3 of 3 mounts, 13 bolts.
- **The mode:** the heavier bracket rearranged the spectrum: mode 8 moved up past the band, to 2581 Hz, 6 Hz above its top (2575). The margin is thin: the CAD's own fillets and draft will move it, so the CAD is to be judged again (the hand-over says so).

### `final8`: mount-3's bracket at 150 cm³ (03:22)

- **Result:** 7.48 kg (motor side 4.14, cover 3.32), 33.8 µm, tilt 0.887 ×, first mode 742 Hz, mode 8 at 2587 Hz (clear of s1), **but mode 4 at 1102 Hz, 2.2 % under s2's 1127 Hz: it fails the orders**; oil-tight, undercut 1.36 / 0.53 %.
- **Lesson:** the bracket's mass moves the whole spectrum, not one mode. 70 cm³ lowered mode 8, 110 cm³ lifted it past s1's band, 150 cm³ pulled mode 4 down into s2's. The window is narrow, and the CAD's draft and fillets will move the modes as much: the modes are the CAD's to confirm by FE. **`final7` is the hand-over.**

### Rule 3 again, with room (`rule3b_thin`, stopped)

- The stiffest housing at a fixed 7.2 kg (compliance, every line at 1/1.25, the intermediate seat at 1/1.4) with members at most 8 mm wide and 20 mm apart, the protected interfaces, the brackets' floors and the one-way curvature (`rules_queue3.sh`, started after `final1`).
- **Stopped at iteration 55** (02:37): the plan share stalled at 0.65 (from 0.74) against its 0.5, every line at its bound. With 0.4 kg more than the least mass it is still infeasible: the bridges and arms on this layout need members wider than 8 mm or closer than 20 mm. Thin production ribs would need a different layout (their own load paths), not a rule on this one.

### After the hand-over: the lumps at the junctions (`final9`, from 03:33)

- **Seen:** `final7`'s motor side is calm on its lobes, but its members bunch where loads meet: the bridge network between the bosses (M2, 35 mm wide where its branches meet), mount-3's bracket (spindly legs and a stray fin round its 110 cm³ floor), and a blob by the cover's lowest bolts.
- **The note's first experiment** (the engineer's paste, 01:58: preserve the functional surfaces; cap the local accumulation of metal; calm the floors; least and greatest member sizes). The surfaces are protected, the floors' curvature and the plain walls were tried (Rules 1-2); **the cap on local accumulation is the one not yet tried with the height field** (every height-field run since 11 October had `--max-member 0`).
- **The one change from `final7`:** `--max-member 16` (`topo.greatest_share`: in a ball round each free voxel at most 0.6 placed metal, so no section much over 16 mm; the frozen bosses, spokes and lugs not counted). The hypothesis: the wide junctions split into ribs, and the bracket's floor is spread as ribs, not legs.

- **Result** (03:41): the cap did not bind. The p-mean of the balls' shares (p 12) read 0.566 against 0.6 at the end; the field is `final7`'s (2.551 kg placed against 2.554, the same compliance, 1381.1 N·mm). Drawn and judged: 7.35 kg, 35.7 µm, tilt 0.989 ×, 715 Hz, oil-tight, undercut 1.30 / 0.44 %, **but mode 8 at 2563 Hz, 2.5 % over s1: a clash.**
- **Lesson 1, the modes:** a near-identical field (the same compliance, 3 g less placed metal) moved mode 8 by 18 Hz (2581 → 2563). `final7`'s 3.2 % margin on s1 is within the drawing's noise. Mode 8 is a global mode of the bearing bores (`mode_shape.py final7 --all`: 24 % the cover's output bore, 20 % the motor side's input bore, 17 % the cover's intermediate bore, 9 % mount-3), so no local move holds it; the CAD's modes decide.
- **Lesson 2, the lumps** (`ball_shares.py`, the scratchpad): at 16 mm, 669 metal voxels' balls hold over 0.6 and 238 over 0.7 (the worst 0.89), all at the junctions: the motor side's bridge between the intermediate and output bosses (x 0-40, y 40), by mount-3 and the cover's top network (x 20-40, y 240), and the cover's network by the bolts (x 60-80, y 0-20). The p-mean at p 12 averages them away; at p 40 it reads 0.739.
- **Next** (`final10`, from 03:43): the same cap read near its worst ball (`LOOP_MEMBER_P=40`, as the rule's docstring advises for knots).

### `final10`: the cap read near its worst ball (03:48)

- **The one change from `final7`:** `--max-member 16` with `LOOP_MEMBER_P=40`.
- **In the optimiser:** the cap bound and held (0.587 against 0.6) at no cost: 2.545 kg placed (`final7` 2.554), the compliance 0.6 % higher.
- **Result** (`compare_final10.png`, `motor_7_vs_10.png`, `cover_7_vs_10.png`): **every graded line passes**: 7.35 kg (motor side 4.06, cover 3.27), 35.1 µm, tilt 0.954 ×, first mode 725 Hz, no mode within 3 % of an order (mode 8 at 2580 Hz, +3.2 %; mode 4 at 1078 Hz, −4.4 % from s2), oil-tight, undercut 1.25 / 0.40 % (`final7` 1.30 / 0.52), the largest member sections 24.0 / 31.1 mm (`final7` 28.8 / 33.8).
- **The look:** the junctions are thinner: the blob by the cover's lowest bolts is smaller, and the motor side's bridge between the bosses reads more as ribs. Mount-3's bracket is worse: the cap spread its 110 cm³ floor into thin struts, a truss rather than a production lug.
- **Verdict:** `final10` beats `final7` on the lumps and the undercut at the same mass, with every line passing. **It is the hand-over** (the page republished at the same link).

### Is the designer's reading safe to draw? (`final10r`, `final10ra`, `final10rn`, `final10rz`, 04:02-04:19)

- **The test** (`reading_field.py <design> [--keep <kinds>] [--label <l>]`): the reading put back into `final10`'s field and judged as any design. Under each run's footprint each column holds the run's height (tapered from the median of its first third to that of its last), nothing elsewhere. The least walls, the protected features with 2 mm round them and the spokes stay; every member a lug meets gets a web from the split down to the lug's far end (the lug hangs 33-63 mm under the split with its bolt's room clear above it: without it mount-3 parted from the body, three tries).
- **Results** (worst seat µm, tilt ×, first mode Hz; `final10` 35.1, 0.954, 725):
  - every member as straight runs (`final10r`, 7.18 kg): 151.5, 1.445, 269: mount-3's bracket lost its depth, and the output's bores hang on it;
  - the arms kept as the field has them (`final10ra`, 7.28 kg): 53.9, 1.158, 623;
  - the arms and the networks kept (`final10rn`, 7.34 kg): 53.7, 1.092, 620;
  - every member kept, only the crumbs gone, the lugs' webs added (`final10rz`, 7.44 kg): **33.6, 0.920, 733, every line passes**.
- **Lesson:** the crumbs do not matter; the ribs', webs' and gussets' heights do. Read at their medians they lose a third of the housing's stiffness at the output's bores: a rib's depth peaks near the bosses (C3: 8 mm median, 24 mm at most), and its bending stiffness goes with the cube of it. The reading gives the layout (where, which way, how wide); the heights must come from the field (the mesh), or a rule that keeps the deep parts.
- **The runs at their deep heights** (`--deep`: each run as tall as the 90th percentile of its metal's heights, 04:22):
  - ribs, webs and gussets so, the arms and networks as the field has them (`final10rp`): 7.65 kg, **31.8 µm, tilt 0.933 ×**, 753 Hz; a mode at 1113 Hz, 1.2 % under s2: every static line holds for 0.30 kg;
  - every member so (`final10rd`): 8.09 kg (over the reference), 30.3 µm, 0.848 ×, 845 Hz; a mode at 1129 Hz.
- **The drawing rule, measured:** ribs, webs and gussets as the reading's straight runs at their deep height; arms and networks as the field mesh has them (deepest at the lugs and where the members meet); a web from each lug over the lug's length. The modes move with every change: the CAD's are judged again. The reading's picture and table say it member by member (`member_map.AS_FIELD`), and the page shows the seven tests (`reading_tests_final10.json`).

### The thinner drawing, and more margin on the tilt (`final10_l50`, `final11`, from 04:36)

- **`final10`'s own field drawn at member level 0.5** (the standard at 4 mm voxels is 0.45, which keeps the one-voxel members 0.5 loses: `outcome_cad.member_level`): 7.23 kg, 36.8 µm, **tilt 1.013 ×, mode 8 at 2548 Hz (inside s1's band)**. Drawn thinner, the tilt reads 6 % higher and mode 8 1.2 % lower: `final10`'s margins (the tilt 4.6 %, s1 0.2 % past the band's edge) rest on its thin members, which the CAD must keep.
- **`final11`** (every line at 1/1.3, 04:44): 7.42 kg, 34.0 µm, tilt 0.935 ×, 730 Hz, oil-tight, undercut 1.16 / 0.39 %; **mode 8 at 2624 Hz, 5.0 % clear of s1, but mode 4 at 1098 Hz, inside s2's band** (2.6 % under 1127). The two orders pull against each other: stiffening lifts every mode, mode 8 out of s1's band and mode 4 into s2's. Between them nothing is clear by more than a thinner drawing moves the modes (1 %), so the way out is past s2's band: mode 4 above 1161 Hz (+7.7 % on `final10`'s 1078).
- **`final12`** (every line at 1/1.45, 04:50): 7.63 kg, 32.2 µm, tilt 0.911 ×, 755 Hz, oil-tight, undercut 1.19 / 0.37 %; **mode 8 at 2718 Hz, 8.7 % clear of s1; mode 4 at 1154 Hz, still 0.6 % inside s2's band.**

| Every line at | kg | Worst seat µm | Tilt × | Mode 4 (s2's band 1093-1161) | Mode 8 (s1's band 2425-2575) |
|---|---|---|---|---|---|
| 1/1.25 (`final10`) | 7.35 | 35.1 | 0.954 | 1078 (clear, −4.4 %) | 2580 (clear, +3.2 %) |
| 1/1.3 (`final11`) | 7.42 | 34.0 | 0.935 | **1098** | 2624 (+5.0 %) |
| 1/1.45 (`final12`) | 7.63 | 32.2 | 0.911 | **1154** | 2718 (+8.7 %) |

- **Read:** stiffening lifts every mode: mode 8 leaves s1's band, mode 4 crosses s2's. Mode 8 is now clear on stiffness, so mount-3's 110 cm³ tuning mass has no job left.
- **`final13`** (`final12` with mount-3's floor at its reference 50.6 cm³, 04:56): 7.47 kg, **58.2 µm, first mode 372 Hz**, tilt 0.990 ×, mode 8 at 2484 Hz. Without its floor mount-3's bracket is thin struts again: the model flatters them, and FE finds the output's bores hanging on them (as the reading test found, 04:09). **The floor is structural, not only a tuning mass.**
- **Where the modes stand** (`mode_shape.py final12 --all`): modes 3, 4 and 8 are global modes of the bores (mode 4: the output's bores 40 %, the cover's intermediate 19 %; mode 3: the motor side's output 32 %). Stiffening moves them together. To clear s2, mode 4 must pass 1161 Hz while mode 3 stays under 1093; with margin that costs mass up to the 7.73 kg line (at 1/1.5 about 7.70 kg), and leaves nothing for the CAD's fillets and draft. **The chase stops here: `final10` stays the hand-over** (7.35 kg leaves 0.38 kg for them). `final12` is the stiffer alternative: every static line with margin (tilt 0.911 ×), mode 8 clear by 8.7 %, mode 4 0.6 % inside s2's band.

### Production's gusseted lugs (`final14`, `final15`, from 05:02)

- **Seen:** the brackets were the motor side's least production-like part (a truss of struts round mount-3's floor), and the floor is structural (`final13`). The reading's test found a web from each lug over its length stiffened the housing (`final10rz`).
- **The one change from `final10`:** the bracket floors replaced by production's gusseted lugs fixed in the optimisation (`LOOP_LUG_WEBS=8:25`, `exact_walls.lug_webs`, `lug_web_density`): two webs 8 mm thick from each lug to its half's nearest room's wall (25 mm either side of the nearest point, or 0.6 of the lug's reach), from the lug's far end to the split, the bolts' rooms kept clear. 6 webs, 5,344 voxels; the fixed metal 4.61 kg (4.00). The webs to mount-2 and mount-3 run 130 mm, to the motor side's output room (its piece there is 61 mm in radius).
- **Result** (`final14`, 05:09; `motor_10_vs_14.png`): 7.40 kg, 33.6 µm, **tilt 1.030 ×** (the motor side's intermediate seat: FE / model 1.54), **first mode 868 Hz** (725), **no mode near an order, by wide margins** (s2: 972 and 1449 Hz, −13.8 and +28.6 %; s1: 2026 and 2788 Hz, −19 and +11.5 %), oil-tight, **undercut 1.07 / 0.16 %**, the least placed metal of the night (2.00 kg).
- **The look:** mount-3 and mount-2 carry clean triangular brackets (two straight webs from each lug to the output lobe, a pocket between them), mount-1 a compact lug, the junctions between the bosses calmer: the motor side reads as production's.
- **Lesson:** a stiff mounting moves every mode far from the orders at once; the modes the overnight chased one at a time were the brackets' softness.
- **`final15`** (the intermediate seat at 1/1.65, 05:15): 7.46 kg, 33.2 µm, **tilt 1.003 ×**, 876 Hz, no mode near an order, oil-tight, undercut 1.08 / 0.17 %. The seat's FE / model grew with its factor (1.54 → 1.65): the model finds stiffness there that FE does not, so the seat's own factor alone barely moves FE.
- **`final16`** (every line at 1/1.3, the intermediate seat at 1/1.65, 05:21): **every graded line passes**: 7.50 kg (motor side 4.19), 32.6 µm, tilt 0.963 ×, first mode 883 Hz, **the nearest modes 14.1 % from s2 and 12.1 % from s1**, oil-tight, undercut 1.08 / 0.20 %. Command: `LOOP_LUG_WEBS=8:25 LOOP_MEMBER_P=40 GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.65" LOOP_PANEL_SPOKES=30:6:12 LOOP_SPOKE_HALVES=cover campaign_run.sh final16 --budget 7.6 --voxel 4 -- --max-member 16 --band 24 --height-field 6 --empty --protect --objective mass_tilt --safety 1.3`.
- **Its own field drawn at member level 0.5** (`final16_l50`): 7.39 kg, 33.8 µm, tilt 1.018 ×, the modes still clear (the nearest 10.9 % from s1): only the tilt leans on the thin members (round the motor side's intermediate seat).
- **The drawing rule on its field** (`final16rp`: ribs, webs and gussets at their deep heights, arms and networks as the field): 7.73 kg, 32.2 µm, tilt 0.907 ×, modes clear: every line with margin, but at the reference's mass.
- **Verdict: `final16` is the hand-over** (05:28; the page republished at the same link). Against `final10`: the modes robust (12-14 % from the orders against 0.2 %), production's brackets, less undercut, 0.15 kg heavier.
- **More margin on the tilt?** (`final17`, every line at 1/1.35, 05:39): 7.59 kg, 31.6 µm, tilt 0.944 ×, 884 Hz, the modes clear; its own field at member level 0.5 (`final17_l50`) reads the tilt at 1.000 ×. Each step of the factor buys less (from 1/1.25 to 1/1.3 the tilt fell 4 %, to 1/1.35 2 %): the model finds stiffness at the motor side's intermediate seat that FE does not (FE / model 1.54-1.65), so the lever there is that seat's own support, read in FE, not more safety. `final16` stays the hand-over (lighter, every line passing); `final17` is on the page as the alternative.
- **The seat's own support** (`final18`, 05:50): `final16` with a floor of 60 cm³ on the motor side's bridge between the input and intermediate bosses (24 cm³ there in `final16`, against 99 on the intermediate-output side; `bridge_metal`, the scratchpad): 7.61 kg, 32.8 µm, **tilt 0.917 ×** (FE / model 1.51, from 1.59), 877 Hz, the modes clear. Drawn thinner (`final18_l50`): tilt 1.012 ×. The bridge buys 4.6 % of tilt for 0.11 kg where the factor bought 2 % for 0.09; thin members still carry the last margin.

## 4. What the campaign has taught

1. **Protecting the functional geometry gives the look the penalties could not.** The semantic curvature limits halved the surfaces' bending in the optimiser's own heights at no cost, but the drawings barely changed; holding the bearings' bosses as round towers, the sealing land, the bolts' bosses and the lugs (in the field, never as CAD) made the housing read as designed at once.
2. **Everything in one field.** Fusing CAD solids onto the field (P1-P2) mixed the two worlds, overhung the lobes, leaked, and meshed past FE's memory; the same features as densities from their exact shapes, contoured once with the rest, came out oil-tight, castable and an ordinary size for FE.
3. **What reads as loops and blobs is the members' layout in plan, not their heights.** Rules on the heights (plain walls, one-way curvature) changed little; a rule on the plan (thin, spaced members) is the right kind, but on this layout it is infeasible: the bridges and arms that carry the bearings need wider members.
4. **The optimiser's model flatters one seat more than the rest,** and which one is read from FE's grade, not from its log (`seat_ratios.py`): the motor side's intermediate seat, 1.15 × in the reference, 1.29-1.40 × in the protected least-mass designs. A seat's own factor of safety, learned from FE, closes it.
5. **The optimiser cannot hold the modes:** its voxel model's spectrum is spurious local flaps (`model_modes.py`). The modes are moved by design moves judged in FE: production's panel spokes (fixed in the optimisation, else they spoil the tilt), and a bracket's mass as a tuning mass.
6. **Production's panel spokes fixed on the cover give the housing production's look** (a wheel round the output boss) at about 0.3 kg, with every bearing line kept.
7. **A bracket's mass tunes the modes in a narrow window.** Mount-3's least metal at 70, 110 and 150 cm³ moved the whole spectrum: only 110 cleared both orders, by 3.2 % on s1. The CAD will move the modes as much, so they are judged again on the CAD; a mode margin inside the optimiser needs the flange's partly filled voxels given their true stiffness first (its voxel model's modes are their local flaps).
8. **A cap on the metal's local accumulation must be read near its worst ball.** At p 12 the greatest member averaged the junctions away and never bound (`final9`); at p 40 it held them at no cost in mass (`final10`). It thins the junctions, but a floor of metal it spreads into struts.
9. **Thin members carry margin.** Drawn at member level 0.5, which loses the one-voxel (4 mm) members the standard 0.45 keeps, a field read the tilt 6-10 % higher and its modes about 1 % lower. The seats lean on thin members the CAD must keep; a pass by less than that is a pass at the pipeline's standard drawing, judged again on the CAD.
10. **Two gear orders pull against each other.** Stiffening lifts every mode: mode 8 left s1's band as mode 4 entered s2's (1/1.25 to 1/1.45). Holding both with margin needs a modal constraint in the optimiser (its model's modes are local flaps of the flange's partly filled voxels until their stiffness is made proportional to their filling) or design moves aimed at one mode, judged in FE.
11. **A bracket's floor is structural.** The least-mass optimiser makes thin bracket struts that its model flatters; without mount-3's floor the output's bores hung on them (`final13`: 58 µm, 372 Hz).
12. **The brackets' form decides the modes.** Production's gusseted lugs (two webs from each lug to its room's wall, over the lug's length) in place of the floors lifted every mode (first 725 → 868-883 Hz) and cleared both orders by 12 % and more: the modes chased all night were the brackets' softness. The look improved at the same stroke.

## 5. The hand-over

**The design handed over: `final16`** (05:28; every graded line passes, the modes 12-14 % from the gear orders; §3): `final10` with production's gusseted lugs in place of the bracket floors, every line at 1/1.3 and the intermediate seat at 1/1.65. `final7` was handed over first (03:26), then `final10` (03:52). Simulation-feasible and process-rule-feasible, drawn as one field mesh; not CAD and not production-ready (no draft, no fillets).

- **The page for the CAD designer:** [Reducer Housing Hand-over](https://claude.ai/artifact/CXK9wU4soMc9MNmSpxKDWL) (an Artifact, private: share it from the page's Share menu before the designer can open it). Written by `handover_page.py final16` (`data/first_loop/handover_final16.html`; `final7`'s and `final10`'s beside it), every number from the design's own records:
  - the graded lines against their targets, each gear order's nearest mode and its margin (s1: 2804 Hz, +12.1 %; s2: 968 Hz, −14.1 %), oil-tightness, the undercut, the mass by half;
  - each half along its pull, the four views, and the members' map;
  - **the designer's reading** (`member_reading_final16.png`; first on `final10`, 03:59-04:30): each member's centre-line simplified to straight runs (within 6 mm), each as wide as the metal nearest it; ribs, webs and gussets labelled width × deep height (their 90th percentile), arms and networks hatched (drawn as the field has them); the runs' ends, widths and heights in the members' json and md;
  - **what holds when drawn differently**: its own field at member level 0.5, the drawing rule on its field, and `final10`'s reading at median heights, each with what it shows;
  - the protected features with their sizes (the bearing bosses as towers, the sealing land, the bolts' bosses, the lugs, the cover's panel spokes);
  - the members (`member_map.py final16`: the cover 11, the motor side 5), each with its kind, ends, length, width, height off the wall, shape and what it meets, and a key to the kinds;
  - how the shape was found (the run's own settings), and the drawing directions.
- **The field mesh:** `data/first_loop/final16_cover.stl` and `final16_motor_side.stl`, each with its indexed `.ply`; the members in `member_map_final16.json` and `.md`.
- **Open, for the engineer:**
  - **the tilt leans on thin members** round the motor side's intermediate seat (`final16` 0.963 ×; drawn thinner, at member level 0.5, 1.018 ×): the CAD keeps them. `final18` (a floor on that side's input-intermediate bridge) holds the tilt at 0.917 × for 0.11 kg. The modes are far from the orders in every drawing. The CAD is judged again. `final10` (7.35 kg) and `final12` (7.63 kg) are the earlier designs, with thin mode margins;
  - **the motor side reads less like production than the cover:** its arms to the lugs and the bridge network between the bosses (M2) are the optimiser's own, and the brackets are production's gusseted lugs since `final16`; the motor side's spokes (`final4`) cost 0.45 kg and left mode 8 in s1's band;
  - **only the peak drive is applied and every mount's hole is held fully:** the brackets are kept by their least metal, not by loads; the mounts' own load cases (a bump) wait for the engineer's word and values;
  - **the production look costs 1.5 kg against the empty start's baseline** (`empty1_5.5kg`: 5.82 kg, every line passing, organic): `final10` holds 4.00 kg fixed against its 1.02. The bearing towers are 2.96 kg of it, 1.18 kg standing between the seats and the split (the motor side's input 0.43 kg, the cover's intermediate 0.38 kg: their rooms are narrower than their bosses). They stand because each half is cast with its parting at the split face (a column outside a room fills from the split). A stepped parting line, or a core from the split side, could take about a kilogram: the process profile is the engineer's to change (the page says so to the designer);
  - **a plan rule for thin, spaced members is infeasible on this layout** (`rule3b_thin`);
  - **the campaign on the Campaigns page:** `lop28`, 15 moves and 25 FE runs (`lop28_log.py`, then `campaign_export.py lop28`);
  - nothing is committed.
