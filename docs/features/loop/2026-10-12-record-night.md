# The loop's record: the night of 12 October

Where everything stands, what was tried and what it taught, written as it happens, so that a new session (or a compaction) loses nothing. The loop's page ([status.md](status.md), LOP-24 and LOP-25) holds the state; this page holds the night's account. The night before: [2026-10-11-record-night.md](2026-10-11-record-night.md).

## The engineer's goal for the night (01:52-01:54)

> "In the end, I want to get a production housing, a housing which looks like a production, which nice bracket shapes, mounting bracket shapes, nice ribs, nice patterns, and beating the target as well. So, and it should be inspired by the optimization, and it should be inspired by the physics, and it should be load aware, physics aware."

Also asked:

- **Judge the pictures against production's** (the photos the engineer gave: ZF, Kalyani, Punch, Rawsuns, the Nature paper's figure), and adapt until the housing is of the same kind.
- **Fillets on the 4 mm shell itself:** it looked edgy.
- **A short web search when stuck.**

"Beating the target" means every graded line passes by FE at no more than the reference's 7.73 kg:

- the worst seat's displacement under 52.2 µm;
- the worst tilt under its line;
- no mode within 3 % of a gear order.

Earlier the same night (01:07) the engineer asked for two things: complete approach 1 (design volumes from the flow), then approach 2 (`zenryx_new_plan.md`: generators A/B/C, about 12 candidates), with everything on the UI.

## The line of work: production's forms from the flow

The free run (the benchmark's optimisation, `it1_free_5.5kg`) says where the metal goes. In plan, mapped against every layout below (`metal_by_volume.py` in the session's scratchpad), its metal does three things:

1. **It ties the bearing seats together** across the end wall between the bores, at the band's full height. The gears push the meshing shafts' seats apart, and the tie carries that in-plane.
2. **It lays a belt beside the side walls** along the split: the joint's stiff band.
3. **It rings the bores and runs out to the bolts and the mounts.**

Production's housings show the same things as clean forms:

- bosses round the bores;
- bridges between the bosses;
- ribs from the bosses to the bolts and the mounts;
- gussets round the flange;
- gusseted lugs.

So the design space is laid out as those forms, where the flow runs (`section_forms.py --ribs-from lines`):

- **Seat to seat:** the hull of the two bosses (`--bridges`).
- **Seat to bolt, seat to mount, mount to bolt:** a straight strip, kept while at least 45 % of its columns hold the free run's metal.
- **Each bore:** an annulus (`--ring`).
- **Beside the side walls:** radial gussets every 24 mm round each room (`--belt gussets`).
- **Everything else:** held empty (`topo.volume_map`'s -2).

The optimiser (least metal, every tilt and bed held with margins) sizes them. The drawing (`implicit_draw.py`, `LOOP_IMPLICIT`) draws them as one smooth solid on the contract's exact, filleted shell.

## Trials, as they came

| When | Layout and run | Model | Drawn and judged by FE | What it taught |
|---|---|---|---|---|
| 02:00 | `sf3` (ribs along the flow's skeleton, rings), `sf_4` | 5.81 kg | `sf4_field` (the field drawn as voxels): 5.93 kg, **every line passes**, organic | the rest was left free by mistake (`volume_map`'s -1), and the free columns carried much of it |
| 02:05-02:27 | the smooth drawings of `sf_4`: `prod2`-`prod5` | | 111-156 µm, tilt about 2 × | they drew the ribs and rings only and left out the free columns' metal |
| 02:30 | `sf4` (the same ribs and rings, the rest held empty), `sf_5` | 7.79 kg, the cover's beds 1.40 × | | the free metal carried the beds |
| 02:41 | `prod6_asis`: `sf_4` with the wall's thickening drawn (`thickening`: every non-rib column's metal, in whole voxels, each piece of continuous wall one smooth solid) | | 7.28 kg, 32.9 µm, tilt 0.84 ×, a clash at 2492 Hz | faithful; but heavy (the features stood on the voxel skin's face, now on the exact shell's, `exact_faces`) and organic, the free metal like melted wax |
| 02:46 | `ln1` (25 straight ribs between the hard points, 6 rings), `ln_1` | every rib at 24 mm, the beds 2.6 × | | ribs alone cannot replace the free run's tie between the seats |
| 02:50 | `ln2` (+ bridges), `ln_2` | 7.79 kg, 1.53 / 1.94 × | | closer; still missing the belt beside the side walls |
| 02:55 | `ln3` (+ the belt and lugs as volumes of one height), `ln_3` | **8.84 kg**, meets every line | | one height a region costs metal: 5.91 kg placed where `sf_4` placed 2.88 |
| 03:00 | `ln4` (the end faces regular, the belt free), `ln_4` | 7.10 kg | `prod7`: TetGen refused (1,243 slivers where exact cuts grazed the smooth features: `cleared` keeps every feature 2 mm short of the kept-clear spaces); `prod8_asis`: 7.12 kg, **52.4 µm against 52.2**, tilt 0.85 × | the input and intermediate seats pushed 40 µm apart radially: the boss sections as rings took the room between the bores and the input's ring was left at nothing |
| 03:17 | `ln5` (8 mm annulus rings, bridges each boss's radius + 24 mm, gussets; each form one height or a root and a tip), `ln_5` | **9.25 kg**, 1.11 / 1.08 × | | the rings one height each: 2.64 kg where `sf_4` had 0.55 |
| 03:25 | `ln6` = the same plan, **each form's columns free** (`--free-forms`: the metal can only make the forms), `ln_6` | 7.61 kg | **`prod9_asis`: 7.71 kg, 41.8 µm, tilt 0.81 ×, 744 Hz; one clash, 2575 Hz, exactly 3 % from s1's 2500** | the regular plan with free heights is nearly enough; the drawing of it is faithful (the model's beds 0.79 of the target, FE 0.81) |
| 03:32 | `prod10`/`prod11`: each end wall's form drawn as production draws it (a boss's face flat, a bridge's top a plane, a rib's top straight; `form_tops`, its metal kept) | | `prod11`: 52.8 µm, tilt 1.12 × | **the optimiser's heights vary where the load asks: flattening them costs a quarter of the stiffness**; off (`LOOP_FORM_FIT=1` keeps it) |
| 03:42 | `prod12`: exact outlines (round bosses, straight strips) | | 8.12 kg, tilt 1.06 × | spreads the metal; off (`LOOP_EXACT_FORMS=1`) |
| 03:50 | `prod13`: `prod9`'s drawing with production's gusseted lugs (two 8 mm webs from each lug to the shell) | | 7.76 kg, 42.4 µm, tilt 0.85 ×; **clashes 1117 (s2's 1127) and 2443** | the brackets look right; the modes move with them |
| 03:56 | `ln_7`: `ln6` at margins 1.15 / 1.25 | **6.34 kg** | `prod14`: TetGen hung on the cover (ended by its tree; 0.16 mm lips: `LEAST_H` 3 mm); `prod15`: past the single factor's 2.18 M unknowns even on 9 and 11 mm surfaces | the lighter, more fragmented forms carry much more surface |
| 04:17 | `ln_8`: `ln6`, the plan filter 12 mm (the heights smoother by construction) | 6.52 kg | `prod16_asis`: 6.81 kg (judged on a 9 mm surface), 48.8 µm, tilt 1.04 ×; clashes 1109 and 2548 | |

## What the night taught

1. **The free run's "spill" is structure.** Held empty, the beds fail; the metal between the bores is the seats' tie, and the belt beside the side walls is the joint's band. A production layout must have forms where they are.
2. **One height a form costs about twice the metal** (`ln_3`, `ln_5`). The optimiser's heights vary inside each form where the load asks.
3. **A regular plan with free heights inside it works** (`ln_6`): the metal can only make bosses, bridges, ribs and gussets, sized column by column, and the drawing of it is faithful.
4. **The modes are now the blocker.** In this family a mode of the cover's end wall sits between 1040 and 1170 Hz, against the 1127 Hz order's band of 1093-1161, and another near 2500 Hz. The bands cover about 9 % of the 680-3000 Hz span: with 12 modes most designs clash by chance. Designs that passed had that mode just outside the band (`prod9` 1169, `sf3_ribs` 1093, `hp2` 1091). A mode margin belongs in the optimiser; until then, a family of variants judged by FE.
5. **The drawing's rules learned:**
   - every feature stands on the exact shell's outer face, not the voxel skin's;
   - each stops 2 mm short of every space the exact cuts take;
   - an end wall's piece ends at the side wall's face, while a piece beside a side wall runs 3 mm into it;
   - nothing under 3 mm is drawn;
   - a rib is one plate with one top line;
   - every mount gets a gusseted lug unless 20 cm³ of drawn metal already holds it.

## After 04:25: the family, the judge's robustness, the modes

| When | What | Result | What it taught |
|---|---|---|---|
| 04:25-04:47 | a family (`family_queue.py`, scratchpad; `data/first_loop/family.jsonl`): `ln6` at margins 1.2 / 1.3, the plan filter 12, 6 and 9 mm (6.86-7.11 kg in the model), each with webs and bars | **none judged:** the 12 mm ones' covers crossed themselves when coarsened (the wide filter lays the metal in 3-6 mm layers); the 6 and 9 mm ones' TetGen refused or crashed | the lighter designs carry much more thin surface |
| 04:48 | the drawing's own decimation | it had folded `fa9_web`'s surface; now guarded (the decimation with the fewest crossings kept) | marching cubes never crosses itself, a decimation can |
| 04:55 | `mesh_route.coarse` | 8 rounds, each keeping a wider region out round the crossings (was 5) | |
| 05:03 | an opening of the solid by 1.25 mm (`OPEN_R`) | bumpy at the grid's scale; FE's mesh 4.4 M unknowns (`prod17`); off | |
| 05:12 | `prod18_asis` (`ln6`, bars, nothing under 3 mm) | 7.737 kg (5 g over), 44.2 µm, tilt 0.88 ×, **clashes 1149 and 2542 Hz** (`prod9`: 1169 and 2574.62, inside by 0.4 Hz) | the modes move a few % with any drawing change; the free benchmark's own sit 1-3 % from the bands' edges: passing by a drawing's luck would not be a design |
| 05:20 | **the judge's TetGen in a child process** (`fe.tetrahedralize_guarded`) | a crash (0xC0000374), a refusal or 240 s is a refusal, and the ladder goes on | it had hung on `prod14` and crashed silently on `prod17` and `fa9_bar3` |
| 05:30 | the optimiser's own model's modes for `ln_6` (scratchpad `model_modes.py`: shift-invert Lanczos on its stiffness, lumped masses) | **150-330 Hz against FE's 744-3031**, local flaps of the flange's partial voxels at the split, whatever SIMP's penalty | a mode margin in the optimiser needs the flange's contact modelled first |
| 05:37-05:44 | **production's panel ribs** (`LOOP_PANEL_RIBS=1`, `panel_ribs`: radial ribs 6 mm thick, 10 mm high, every 30°, from each boss across the end walls' bare panels): `prod19_asis` (`ln6`, bars) | **the mode by s2's order 1149 → 1206 Hz, clear**; 40.8 µm; the cover's end face spoked like production's; but 7.84 kg, the next mode at 2501 Hz, the tilt 1.07 × on the 9 mm fallback | the noise-and-vibration rule moves the cover's modes; it costs about 0.1 kg |
| 05:50 | the lighter `fa_6` with bars and panel ribs: `prod20_asis` (meshes now at 7 mm) | **7.21 kg, 43.8 µm, the s2 band clear**; the tilt 1.07 ×; a mode at 2487 Hz | the light designs' thin form columns, drawn thinner than the model's whole voxels, lose tilt |
| 05:55-06:02 | thin columns raised to 3 mm (`prod21`); the forms in the model's whole voxels (`prod22`, `LOOP_FORM_VOXELS`) | the surface's steps ran FE past its ceiling, or onto the 9 mm fallback with 11 of 13 bolts: no judgement | |
| 06:08 | `fa_6` with every form column over 1.5 mm drawn as it is (`prod23`, `LOOP_LEAST_H=1.5 LOOP_FORM_VOXELS=0`) | 3.66 M unknowns at 7 mm, TetGen crashed on the coarser covers (caught): no judgement | the light designs' thin columns: left out they cost the tilt, drawn they defeat the mesher |
| 06:12 | `ln_6` with 5 mm spokes, a ring rib across them (`LOOP_PANEL_RING=1`) and slimmer bars (`LOOP_BAR_W=0.56`): `prod24` | 7.83 kg, 42.9 µm, **tilt 1.10 ×, three clashes**, the first mode 692 Hz (745 with full bars) | the mounts' brackets carry the tilt and the modes: slimmer bars softened both |
| 06:15 | the search stopped | | the remaining variants would be a draw on the modes, not a design |

## Where the night ends (for the engineer, the morning of 12 October)

**Closest so far (pictures beside production's: `data/first_loop/compare_production_night.png`):**

| Design | Mass (≤ 7.73 kg) | Worst seat (≤ 52.2 µm) | Tilt (≤ 1.00 ×) | Modes | Look |
|---|---|---|---|---|---|
| `prod9_asis` (`ln_6`, bars) | 7.71 ✓ | 41.8 ✓ | 0.81 ✓ | 2574.62 Hz, 0.4 Hz inside s1's band ✗ | gussets round the flange, bosses, lugs; the cover's broad end wall bare; the forms' tops torn |
| `prod19_asis` (`ln_6`, bars, panel ribs) | 7.84 ✗ | 40.8 ✓ | 1.07 on the 9 mm fallback | s2 clear (1206), 2501 Hz ✗ | **spoked end faces as production's**, gussets, bosses, lugs |
| `prod20_asis` (`fa_6`, bars, panel ribs) | 7.21 ✓ | 43.8 ✓ | 1.07 ✗ | s2 clear, 2487 Hz ✗ | spoked end faces as production's |

**Judged against the photos:**

- The spoked cover is close to production's end faces: a central boss, straight radial ribs to the rim, the bolt bosses round the flange.
- So are the gussets round the flange and the lugs on their arms.
- What still reads as an optimiser's is the intermediate lobe and the region between the bores: partial forms with torn tops, where production is regular everywhere.

**What blocks "beating the target":**

- **The modes,** one in s1's band, every time. A design that clears it by a drawing's luck would not survive a casting's tolerance. The cure is a mode margin in the optimiser, and that needs its voxel model's flange modelled first (the model's own modes are local flange flaps).
- **The lighter designs' tilt** (the thin form columns).

**Next, in order:**

1. The flange's contact in the voxel model, then a mode margin (shift-invert near each order's band on the factor the optimiser already has; each mode's sensitivity φᵀ(dK − ω² dM)φ).
2. The panel rule as forms the optimiser sizes, not drawn after it.
3. The forms' tops regular without the stiffness they cost (the optimiser's own laws, sized with the margin).

**On the UI:**

- the campaign `lop24-prod` on the Campaigns page: 14 moves, each with its design space in 3D;
- every design on the Designs page.

**Nothing committed.**
