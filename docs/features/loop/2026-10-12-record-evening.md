# The evening of 12 October: the empty start (LOP-27)

**12 October 2026, 23:50.** Where to start after a compaction. Every number below is from the designs' own records in `data/first_loop/` (flow, grade, castability, oil-tight). Nothing has been committed since 9 October, by the engineer's word.

## 1. Where things stand

- **The direction, set by the engineer (19:30-20:22):**
  - the design space is fixed in every iteration (D16);
  - no fixed shell: the empty start;
  - one world for the whole as-cast housing, so no crisp CAD shell is mixed with organic metal.
- **The baseline** (the engineer, 22:27: "I am liking this baseline") is `empty1_5.5kg`: the empty start, the optimiser's plan smoothing at 6 mm, drawn plainly.
  - **Grade:** 5.82 kg; worst seat 37.9 µm (52.2 to beat); tilt 0.997 ×; 742 Hz; no clash; oil-tight; undercut 0.62 / 0.20 %.
  - **Views:** `data/first_loop/empty1_5.5kg_cover_view.png` and `empty1_5.5kg_motor_side_view.png`.
  - **Its run:** `topofree_compliance_tilt_5.5kg_4mm_projected_band24_cup_bolts_split_contract_drive_empty1_5.5kg_empty_hf6_single_flange_beds_sf1.15`.
- **What the engineer likes in it:** clear, straight members (the ribs on the cover's big lobe, the mounts' arms), "revealing patterns clearly".
- **What is left:** lumpy patches where several loads meet:
  - the cover's web between the intermediate and output bearings;
  - on the motor side, round the intermediate lobe.
- **The approach to test** (the engineer and a reviewer, 22:53-23:02): the optimiser discovers the layout in a first pass; then passes clean one area at a time.
  - A tool lists the candidates: "this nearly straight member could be a straight rib", "this patch between two bosses could be a flat web".
  - The agent picks one. Its columns are glued into that clean form (still sized by the optimiser, re-run over the whole housing).
  - FE keeps or undoes it against the best so far.
  - Keep alternatives, not one greedy line. Keep three options a region: a conventional feature, a freeform shape, or the original.
  - Before any agent is built: **three cases** (§2) to learn which direction works.
- **The cases are done** (23:44; §2): the blobs' metal is needed (case 1b); a thickness cap knots it (case 2); a clean form inside the optimiser works as a mechanism, but one flat web was the wrong form (case 3). Nothing is running.
  - **`case1b` is case 1 done right.** The first case 1 held the beds at a factor of 1.5, the baseline 1.15: two changes at once. It needed 4.63 kg of free metal against the baseline's 4.48.
  - **Case 3's web:** `web_form.py <run> intermediate output` wrote `junction_web1_cols.npz`: 286 end-wall columns of the cover glued into one height, the bridge between the two bearings less their bosses (`data/first_loop/junction_web1.png`).
- **The decision for the engineer:** run case 3 again with a sloped web (§2's end), or another direction.

## 2. The three cases (`prototypes/first_loop/junction_cases.sh`)

Each has the baseline's settings and one change. Each is judged by:
- the circled areas in the same views;
- the patch's metal and thickest section (`lump_maps.py`);
- the whole housing: weight, the bearings' lines, modes, castability, oil-tightness.

| Case | Design | Change | Question | How to read it |
|---|---|---|---|---|
| 1 | `case1_least_5.5kg` | `--objective mass_tilt --safety-beds 1.5`: the least metal that meets every line (the reviewer's first choice, "B") | Is the blobs' metal needed? | They shrink: it was spare metal parked to fill the 5.5 kg budget, and a lighter target fixes it. They stay: the bearings need it, and its shape is the question |
| 2 | `case2_max12_5.5kg` | `--max-member 12`, `LOOP_MEMBER_P=40`: no member thicker than 12 mm in any one place ("A") | Does a thickness cap turn blobs into ribs? | With the fixed shell (12 October afternoon) it made knots between the seats and cost about 10 % at the beds |
| 3 | `case3_web_5.5kg` | `--height-volumes junction_web1_cols.npz`: the cover's patch between the intermediate and output bearings glued into one flat web, its thickness the optimiser's, everything else free | Does a clean form cost stiffness? | A few percent at most and clean: the step loop and the agent are worth building. A lot: the representation is the limit (a 3D implicit one next) |

**Measured so far** (23:22; the baseline `empty1_5.5kg`: 5.82 kg, 37.9 µm, 0.997 ×, 742 Hz, members up to 28.9 / 28.4 mm):
- **`case1_least_5.5kg`** (least metal, beds held at 1.5, two changes at once): 5.95 kg, 35.3 µm, tilt 0.941 ×, 709 Hz, no clash; passes; oil-tight; undercut 0.68 / 0.22 %.
  - Its members are bigger, up to 34 / 32 mm: the stricter beds asked for more metal. It is not the clean test; `case1b` is.
- **`case2_max12_5.5kg`** (the 12 mm cap): 5.83 kg, 40.4 µm (+7 %), tilt 0.988 ×, 760 Hz, **a clash at 2549 Hz** (s1's 2500); oil-tight; undercut 0.92 / 0.22 %.
  - The members are down to 18.5 / 17.2 mm (the lump gate is 16).
  - **Look:** the cover's patch flatter. The motor side busier: the blobs split into a network of thinner bars with small holes, round the intermediate lobe and by the lower mount.
  - The cap thins the members but does not make clean forms: it moves the blob into a knotted network, as on 12 October afternoon.
- **`case1b_least_5.5kg`** (the least metal, the baseline's own factors, the clean case 1): 5.37 kg (−0.45), 51.0 µm, **tilt 1.043 ×**, 646 Hz, **two clashes** (1160 Hz by s2's 1127, 2543 by s1's 2500). Oil-tight; undercut 0.55 / 0.19 %.
  - **The optimiser placed 4.06 kg against the baseline's 4.48**, every line binding in its model (tilt 1.012, beds 1.0005). FE read the tilt 3 % past the factor's cover: lean designs flatter the model, as on 11 October.
  - **Look:** plainer, the cover's ribs and patch smaller. The largest section anywhere stayed 28.8 mm (at the bearings' collars), so the patch's own numbers come from `lump_maps.py`.
- **`case3_web_5.5kg`** (the patch as one flat web): its optimiser's model passed (tilt 0.995, beds 0.95 of the safe lines). Its first drawing lost mount-3 (`the body holds 2 of the layout's 3 mounts`), so FE held it on two mounts: 119.8 µm, a first mode of 114 Hz. That is not the design's judgement.
  - **Cause:** the re-optimisation thinned mount-3's arm to a link read near 0.4-0.45, and the surface keeps its largest piece, so the lug and the arm's stub were dropped silently.
  - **Fixed:**
    - `propose.py` now stops when a drawing loses a mount;
    - `LOOP_MEMBER_LEVEL` reads the members lower (at 0.4 all three mounts hold).
- **`case3_web_l40_5.5kg`** (the same run drawn at 0.4, all three mounts held) against **`empty1_l40_5.5kg`** (the baseline drawn the same way):
  - **The baseline at 0.4:** 5.93 kg, 38.0 µm, tilt 0.945 ×, 747 Hz, two clashes (1103 Hz by s2's 1127, 2498 by s1's 2500); oil-tight; undercut 0.66 / 0.22 %.
    - Reading 0.4 instead of 0.5 moved its modes about 2 % and turned "no clash" into two. **A clash within the 3 % band is inside the drawing's noise:** it does not separate designs here.
  - **Case 3 at 0.4:** 5.89 kg, **47.1 µm (+24 %)**, tilt **1.005 ×** (fails by 0.5 %), **a first mode of 487 Hz (−35 %)**, three clashes; oil-tight; undercut 0.55 / 0.20 %.
  - **What the optimiser made of the web:** one slab about **31 mm thick** off the inside over the whole patch (the free run's strap was 5-13 mm thick, with a peak of 59 mm by the intermediate bearing's boss). The cover's patch holds 84 cm³ against 49 (`lump_maps_cover_empty1_l40_5.5kg_vs_case3_web_l40_5.5kg.png`).
  - **Where the metal came from** (the same 1,724 cm³ placed; each run's metal summed by part, `mode_shape.parts`): the cover round the output and intermediate bearings +52 cm³; paid for by the motor side's output bearing −12, **mount-3's bracket −10 (−21 %)**, **mount-2's −10 (−15 %)**, the input bearing's surroundings −18, the flange and walls −8.
    - **Why the brackets:** each mount's hole is held fully (its best-fit rigid motion zero, in the optimiser and in FE), and only the peak drive is applied. Any one mount could hold the housing, so when metal is short a bracket's arm looks spare. The engineer (23:51): "a missing semantic knowledge". The optimiser knows columns, one load and the lines; it does not know a bracket must stay a bracket, or that a wall panel should stay one smooth surface.
    - Case 2's waves and holes (the engineer's second picture, its motor side) are its cap's: no 12 mm ball more than 60 % metal, so wherever metal wants to be thicker it must leave gaps.
  - **The first mode** (`mode_shape.py`): the cover's intermediate and output bores rocking (26 % and 23 % of its energy), the motor side's output bore 19 %.
  - **Look:** the cover's patch is one clean plateau, but a thick one. The motor side is as the baseline's.
  - **The reading:** one thickness for the whole patch must be as deep as its most loaded line, so it fills the whole patch to that depth. The mechanism works (the optimiser sized the form; drawn, it held the mounts); this form is the wrong one.

**The cases' verdict** (23:44; the sheet `data/first_loop/cases_four.png`):
1. **The least metal (case 1b):** the blobs are mostly needed. The patches shrank only about 10 %; the lighter design fails the tilt and clashes.
2. **The 12 mm cap (case 2):** the stiffness holds (40.4 µm, 0.988 ×) and the patches are 19-34 % smaller, but the blob becomes a knotted network. A cap is not a form.
3. **One flat web (case 3):** clean, but too costly: the seats 24 % softer, the first mode a third lower. The form has to follow the load: deep along the line between the bores, shallow to the sides.
- **So the direction worth exploring is case 3's mechanism** (a clean form inside the optimiser, FE keeping or undoing it), with forms that follow the load. FE undid the first form, which is what the step loop would do.
- **The next variant (proposed, not run):** the same patch with its thickness falling off from the line between the two bearings to its edges (`law` 1: a root height on the line, a tip at the edge, both the optimiser's). It can become a ridge with sloping sides, or stay flat.

**A reviewer's notes on the cases** (the engineer, 23:16), applied when reading them:
- **Case 1:** if the housing comes out lighter but the blobs stay, find where the metal was taken from before concluding. If no lighter design is feasible, that is a limit of the structure or of the search.
- **Case 2:** check the cap does not weaken legitimate bosses. Only the seats' rings, the mounts and the bolts' bosses are fixed; the optimiser's own bosses round the bearings are free metal under the cap.
- **Case 3:** is the most telling for the agent. One failed web does not separate "the wrong interpretation" from "too narrow a representation".
  - Next variants: a sloped web (a root and a tip height, `law` 1), its extent as a variable, transitions at its ends.
  - At run time an agent calls the same mechanism ("make a web between these anchors"); the tools build it, the optimiser sizes it, FE judges it.
- **Claims:** be careful about uniqueness. TO-Agents and a 2025 multi-agent CAD-FEA-optimisation framework exist (cited by the reviewer, not yet read). The value to prove is choosing what to try next, changing a region's representation, learning from failures and taking the engineer's words as input.

## 3. Every design tonight

| Design | What | kg | Worst seat µm | Tilt × | First mode | Clash | Undercut motor / cover | Oil-tight | Look |
|---|---|---|---|---|---|---|---|---|---|
| `it1_free_5.5kg` (benchmark, 11 October) | the shell fixed | 5.63 | 36.8 | 0.93 | 773 | none | 0.74 / 0.20 % | TIGHT | organic metal laid on a crisp shell |
| **`empty1_5.5kg` (the baseline)** | the empty start, plan smoothing 6 mm | 5.82 | 37.9 | 0.997 | 742 | none | 0.62 / 0.20 % | TIGHT | one body; clear members; octagons and steps |
| `empty1_faithful_5.5kg` | rho2sdf smoothing, 4 mm samples, exact | 5.67 | 39.8 | 0.972 | 729 | none | 4.71 / 4.18 % | TIGHT | the same facets, rippled |
| `empty1_s8_5.5kg` | the same, 8 mm samples | 5.79 | - | - | - | - | 6.92 / 4.95 % | **LEAKS** | a wall opened |
| `empty1_r4_5.5kg` | the same, 4 mm, damped fit (ridge 0.3) | 5.76 | - | - | - | - | 1.69 / 1.02 % | TIGHT | as the plain |
| `empty2_hf12_5.5kg` | plan smoothing 12 mm | 5.71 | 51.2 | **1.022** | 552 | none | 0.59 / 0.25 % | TIGHT | ribs merged into lumps |
| `empty2_exact_5.5kg` | 12 mm, the least walls drawn exact | 5.47 | 51.2 | **1.015** | 566 | 2475 Hz | 0.60 / 0.20 % | TIGHT | round lobes; lumps |
| `empty1_exact_5.5kg` | 6 mm, the least walls exact (fixed) | 5.50 | 42.0 | 0.980 | 754 | 2455 Hz | 0.62 / 0.18 % | TIGHT | round lobes; the bearing tubes thinner; the cover's patch stands out |
| `case1_least_5.5kg` | case 1 with the beds at 1.5 (two changes) | 5.95 | 35.3 | 0.941 | 709 | none | 0.68 / 0.22 % | TIGHT | bigger members (34 / 32 mm) |
| `case1b_least_5.5kg` | case 1: the least metal | 5.37 | 51.0 | **1.043** | 646 | 1160, 2543 Hz | 0.55 / 0.19 % | TIGHT | plainer; patches 10 % smaller |
| `case2_max12_5.5kg` | case 2: the 12 mm cap | 5.83 | 40.4 | 0.988 | 760 | 2549 Hz | 0.92 / 0.22 % | TIGHT | patches 19-34 % smaller; a knotted network |
| `case3_web_5.5kg` | case 3: one flat web (drawn at 0.5) | 5.71 | 119.8 | - | 114 | - | 0.55 / 0.21 % | TIGHT | **lost mount-3 in the drawing: not the design's** |
| `empty1_l40_5.5kg` | the baseline drawn at 0.4 | 5.93 | 38.0 | 0.945 | 747 | 1103, 2498 Hz | 0.66 / 0.22 % | TIGHT | as the baseline, a little fuller |
| `case3_web_l40_5.5kg` | case 3 drawn at 0.4 | 5.89 | 47.1 | **1.005** | 487 | 1120, 2440, 2568 Hz | 0.55 / 0.20 % | TIGHT | the cover's patch one clean plateau, 31 mm thick |

Sheets sent to the engineer:
- `compare_empty_start.png`;
- `compare_smoothing.png`;
- `compare_exact_walls.png`;
- `compare_row1_exact.png`;
- `lump_maps_cover.png`, `lump_maps_motor_side.png`;
- the baseline's two views;
- `cases_four.png` (the cases against the baseline) and `lump_maps_cover_empty1_l40_5.5kg_vs_case3_web_l40_5.5kg.png`.

## 4. What tonight taught

1. **Freeing the shell cost almost nothing** at the same budget (37.9 against 36.8 µm). It removed the clash between a crisp CAD shell and organic metal ("two worlds"): the optimiser thickens the wall itself where it needs stiffness, instead of laying paint on a fixed one.
2. **Smoothing after the run keeps the stiffness and mass but not the look.**
   - The roughness is the voxels' own layout: the 4 mm columns, and the rooms voxelised into polygons.
   - A faithful method keeps that layout by design; exact interpolation ripples into undercuts.
   - Coarser samples open the 4 mm walls (the oil-tight gate caught it).
3. **Smoothing inside the optimiser (12 mm plan) merges neighbouring ribs into lumps** and costs stiffness: tilt fails by 2 %, the first mode falls 190 Hz.
4. **The exact walls give round lobes and bosses at no stiffness cost,** but they must keep the optimiser's thickness at the bearing tubes. Drawn at the 4 mm least wall, the tubes came out about 6 → 4 mm (`tube_probe.py`): the seats 11 % softer, and the patch beside them now standing proud.
5. **The plain drawing's walls are 3 mm in places,** under the 4 mm least wall. The 2 mm drawing grid puts a face on a cell's face; a 1 mm grid would give 3.5-4.5 mm.
6. **The lumps where loads meet are the optimiser's own metal,** in row 1 too.
   - On the cover: a broad strap about 50 mm wide and 5-13 mm thick, tying the intermediate and output bearings that the gears push apart.
   - It is not held down by the height limit: 1 of its 39 columns reaches the space's top (`web_band_check.py`).
7. **A mode near the stage-1 order (2455-2500 Hz) lands by chance** in some drawings: the modes are not in the optimiser. Drawing the baseline at 0.4 instead of 0.5 moved its modes 2 % and gave it two clashes.
8. **The patches' metal carries load, and its form is the question** (the cases, §2). Taking it away fails the lines; capping its thickness knots it; one flat thickness costs a quarter of the seats' stiffness. A clean form has to follow the load path.
9. **A drawing can drop a mount silently:** the surface keeps its largest piece, and a thin arm read at 0.5 parts from it. `propose.py` now stops on it.
10. **The wrinkles are the optimiser's, not the drawing's** (`roughness.py`, 13 October 00:20; the reviewer's diagnostic). On each run's 4 mm columns, the outer surface's bending, sqrt(s_xx² + s_yy² + 2 s_xy²), over the rooms' end walls (median / 90th percentile, 1/m):

    | Design, half | The optimiser's heights | Its voxels | The drawing |
    |---|---|---|---|
    | baseline, cover | 50 / 1147 | 0 / 1000 | 62 / 686 |
    | baseline, motor side | 245 / 1104 | 177 / 982 | 91 / 573 |
    | case 2, motor side | 299 / 1558 | 250 / 1519 | 111 / 937 |
    | case 3, cover | 10 / 748 | 0 / 771 | 53 / 476 |

    - The drawing bends less than the optimiser's surface, never more: the wrinkles are in the field, where a penalty can act.
    - The voxels are the optimiser's heights rounded to whole 4 mm blocks (at the run's last sharpness each voxel is metal or air): the 4 mm staircase the drawings show. A bending penalty will not remove it; drawing from the optimiser's continuous heights, or finer voxels, would.
    - **A rib's sides bend most of all** (the bright lines in `roughness_empty1_5.5kg.png`): a bending penalty must be off where ribs are wanted, or it flattens the ribs the engineer likes.
    - Case 2's motor side bends 22 % more than the baseline's (its cap's waves); case 3's cover patch is flat inside, bending only at its edges.

## 5. Next, in order

1. **A region-weighted bending penalty in the optimiser** (the engineer, 13 October 00:03, with a reviewer's two notes; proposed, not decided):
   - the penalty: each column's bending of the outer surface, sqrt(s_xx² + s_yy² + 2 s_xy²) squared and summed with a weight a region (the slope is free, so a web may stay thick in the middle and thin at its sides), its stencils within one base, as in `roughness.py`; heights affine in the variables, so its gradient is two sparse products;
   - set as a limit, not a weight: the region's bending at most a share of the baseline's (weak, medium, strong: 50, 25 and 10 %), as the mass and the lines are limits;
   - the first test: case 3's region (the cover's patch between the intermediate and output bearings), so the hard form (one height) and the soft rule (calm, free to slope) are compared on the same patch; everything else as the baseline; FE at the same drawing level; read by `roughness.py`, `lump_maps.py`, `metal_by_part.py` and the grade;
   - in the reviewer's order: the penalty alone first, then the brackets' protection, then the junctions;
   - not global: rib sides bend most, so a global penalty would flatten the ribs.
2. **Roles for regions, the semantic knowledge the optimiser lacks** (the engineer, 23:51; proposed, not decided):
   - **a bracket's role:** each mount kept working, by a requirement of its own (a least stiffness at its point, as mount brackets are specified) or a least arm the tools lay from the lug to the wall. Either is the engineer's call (a new requirement, or a path the optimiser no longer chooses);
   - **a wall panel's role:** one thickness a panel, off the main load paths;
   - **a load path's role:** case 3 again with a sloped web (`law` 1: the root height on the line between the two bearings, the tip at the patch's edge; about 8 minutes).
2. **The exact walls with the bearing tubes at the optimiser's own thickness** (about 6 mm, round): the stiffness back, the patch sunk again.
3. **A 1 mm drawing grid,** so 4 mm walls are 3.5-4.5 mm.
4. **The modes in the optimiser,** so no clash lands by chance.
5. **If case 3 (or 1) shows the way:**
   - the candidate tool (straight members and junctions, from the first pass);
   - the step loop (keep alternatives; re-optimise globally);
   - then the agent.
6. **The clean, FE-proven shape:** reconstructed in the mesh, then built as CAD (D14).

## 6. Tools and commands

- **The empty start:** `propose.py <d> --budget 5.5 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.15 --empty`.
  - The pieces: `topo_free.py --empty` (`build_free(empty=True)`, `least_heights`) and `topo.Voxels` (each wall's least height under the optimiser's own, never gated).
  - The derivative check: `topo_gradcheck.py 10 4 3 --empty` (PASS, 2.5e-4).
  - Runs save `height_min` since 21:11; `exact_walls._height_min` rebuilds it for older runs.
- **The drawings:**
  - plain (the baseline);
  - `LOOP_EXACT_WALLS=1` (`exact_walls.py`): the least walls from the exact inside;
  - `LOOP_FAITHFUL=<mm>[:<ridge>]` (`mesh_route.faithful`, Ježek et al. 2025);
  - `LOOP_MEMBER_LEVEL=<level>` reads the members at that level (0.4 held case 3's thin mount arm); compare designs drawn at the same level.
- **The gates:** `oiltight.py <design> [--open x,y,z]`; flow E in `propose.py`; `propose.py` stops when the drawing holds fewer mounts than the layout.
- **The junction cases:** `web_form.py <run> <shaft a> <shaft b>` glues a patch into one web (`<label>_cols.npz`); `junction_cases.sh "case1 case2 case3"`; `mode_shape.py <design> --all` says where each mode lives.
- **The comparisons** (copied from the session's scratchpad):
  - `lump_maps.py <cover|motor_side>`: the metal off the inside, by design and difference;
  - `look_sheet.py <out> <image> "<label>" ...`: a comparison sheet;
  - `split_view.py <design> "<caption>" "<caption>"`: a design's two views.
- **The reading of tonight's papers:**
  - [rho2sdf](../../research/2026-10-12-smooth-extraction-rho2sdf.md);
  - [the reviewer's direction and five papers](../../research/2026-10-12-reviewer-direction-and-five-papers.md);
  - [the plan of the empty start](2026-10-12-empty-start.md).
