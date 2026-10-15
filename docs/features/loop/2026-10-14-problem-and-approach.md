# The problem now, the baseline, and the way to clean members

**14 October 2026, 12:50.** LOP-29. For the engineer's review, at their request of 12:35: the problem, how far we are, the baseline and what each of its settings bought, what is still unsolved, and the approach. Every run behind the numbers is in [the night's record](2026-10-14-record-night.md).

**In short.** `baseline2_fm500f` passes every FE line, but it passed with two settings that are now out of the baseline: the sharpness cap and the drawing's smoothing. Most of what is still unsolved has one root: **nothing stops the optimiser from making a member one cube (4 mm) wide.** One-cube members cause three things:

- the model reads them too stiff;
- they leave metal loose;
- they draw as slivers.

Each setting added overnight patches one of those symptoms. The proposal is to give the optimiser the length rule it lacks, a least member width in plan of 8 mm, fix the drawing's one defect at the input bore, and measure what that makes unnecessary.

## 1. The problem we are solving

From the gearbox's functional interfaces, design its housing by topology optimisation as two cast halves, pulled apart along the shafts. The housing must meet these lines:

| Line | Limit |
|---|---|
| Worst seat, peak drive | at most 52.2 µm (the reference) |
| Each bearing's tilt against its line | at most 1.0 |
| Modes | none within 3 % of a gear order (s2 1127 Hz, s1 2500 Hz) |
| Mass | at most 7.73 kg (the reference) |
| First mode | at least 500 Hz |
| Oil-tight | yes |

It must also be castable: metal only along the pull, no undercuts, walls at least 4 mm and sections at most 16 mm. It must come out as clean, smooth members that a CAD designer can follow. The optimiser proposes; FE on the drawn housing judges.

## 2. How far we have reached

`baseline2_fm500f` (the night of 14 October) passes every graded FE line:

| Line | FE | Limit |
|---|---|---|
| Worst seat | 36.1 µm | 52.2 µm |
| Tilt | 0.685 | 1.0 |
| First mode | 824 Hz (the optimiser's own: 769 Hz) | 500 Hz |
| Gear orders | nearest 996 and 1383 Hz round s2; 2340 and 2912 Hz round s1 | none within 3 % |
| Mass | 4.39 kg | 7.73 kg |
| Oil-tight | yes | |

- **Castability fails:**
  - undercut: 152 / 38 cm² (motor side / cover);
  - thinner than 4 mm: 295 / 169 cm²;
  - largest member section: 21.5 / 24.2 mm, against 16 mm.
- **It passed with two settings now out of the baseline:** the sharpness cap and Taubin's 30 passes (§3, "Out"). The agreed baseline alone has no passing run yet.

## 3. The baseline: its settings, and what each bought

The baseline is `bash prototypes/first_loop/fm500_run.sh <design>`, holding only these settings. A new one goes in only with the engineer's OK (12:35).

| What | Setting | Agreed | What it bought |
|---|---|---|---|
| **Set-up** | | | |
| The empty start; members added only on top of the shell | `--empty --shell-fixed` | 13 Oct 22:53–22:58 | Plain 4 mm walls everywhere, oil-tight by construction. The walls are planar, as production's are, not blobs |
| The fixed set: one 4 mm shell, the sealing land with the bolts' bosses, the mounts' lugs. Loads on the bearing bores. The same set in the optimiser, the drawing and FE | `--protect` | 14 Oct 00:13–00:28 | One description everywhere: 2.92 kg exact, 2.89 kg drawn, 3.32 kg in cubes (the cubes make a staircase on the curved walls) |
| No towers, no seats' rings | `--no-towers` | 13 Oct 23:49; 14 Oct 00:26 | About 3.3 kg fixed, against about 5.2 kg with the towers. The optimiser builds round each seat itself |
| A26 (split flange): 8 mm each half, in whole cubes | `flange_whole` | 13 Oct 18:38–18:42 | The model's false flange flaps (150–330 Hz) gone |
| A20 (mount rooms): only as tall as the mount | the layout | 13 Oct 20:31 | The rooms no longer run up the whole housing and eat its design space |
| Rigid couplings in the optimiser and FE | `kinematic` | 13 Oct 22:40–22:47 | The model meets FE: 51.0 µm and tilt 0.644 against FE's 51.9 and 0.642 (`lop29_clear`). With the old couplings it was 44 against 74 |
| The optimiser keeps clear what the drawing keeps clear | `drawing_clear` | 13 Oct 20:12 | Metal standing where the drawing keeps clear: 6.8 % before, 0.07 % now |
| **Optimiser** | | | |
| The least metal with every tilt and bed held; 7.73 kg only a ceiling | `mass_tilt` | 13 Oct 22:58–23:27 | 4.39 kg, 43 % under the reference |
| 4 mm cubes; peak drive only | `--voxel 4` | 13 Oct; 11 Oct | A run settles in about 12 minutes (fm500f: 101 iterations, 721 s) |
| No plan mixing | `--height-field 4` | 14 Oct 01:44 | More, distinct ribs (baseline 2 against baseline 1) |
| Height limit 24 mm off the shell; thickest member about 16 mm | `--band 24 --max-member 16`, p 40 | 13 Oct | Members, not lumps, in the optimiser (at p 12 the rule never bound). The drawn sections still reach 17–24 mm where members meet |
| A member counts only once it stands 8 mm proud | `LOOP_LEAST_MEMBER=8` | 13 Oct 22:53–22:58 | No paint: no thin layers spread over the walls |
| Gear-order gaps ±12 % | `--modes 0.12` | 13 Oct | fm500f's modes clear of both orders in FE (nearest 6 % from s1) |
| First mode at least 500 Hz, held inside the optimisation on the lowest six modes | `--first-mode 500` | 14 Oct 01:17, 02:02; six modes 12:12 | FE's first mode 824 Hz (599 Hz in baseline 2 without it), and a strong arm to every mount |
| Gentle sharpening: √2 steps, only while the mode limits hold | in the code | 14 Oct 12:12 | The floor holds through the sharpening. Doubling it had cut mount-3's lug loose, 560 → 178 Hz at once (`fm500`) |
| Safety 1.5 on every tilt and bed | `--safety 1.5` | 14 Oct 12:12 | Covers the model's optimism, for about 0.2 kg. At 1.25 `fm500d` failed (55.0 µm, tilt 1.14); at 1.5 `fm500e` passed the statics (43.2 µm, tilt 0.68) |
| Metal joined to nothing is massless in the modes | in the code | 14 Oct 12:12 | The false low modes gone: on fm500e's field they rose from 180–331 Hz to 809–978 Hz, against FE's 786. The run settles in half the time |
| **Drawing and grade** | | | |
| The drawing keeps every cube, checked before FE | `keep_cubes` | 13 Oct 20:12 | The drawing is the optimiser's field: fm500f lost 1 cube of 6,923. Before, the field's blur dropped thin members |
| Exact faces for the shell, the land, the bosses and the lugs | `exact_faces`, `exact_walls` | 11 and 13 Oct | 4 mm walls drawn 4 mm. A wall drawn 4.9 mm had tipped a seat (1.05 in FE; drawn at 4.0, 0.89) |
| The grade: worst seat 52.2 µm, tilt 1.0, orders 3 %, 7.73 kg, first mode 500 Hz, oil-tight | `grade.py` | first mode 14 Oct 01:17 | |

Three settings from 11 October are unchanged:

- one height per column, so each half casts along its pull;
- each mount's arm free to find its own path;
- the casting rule anchored at the split.

Three switches set only how a run executes:

- castability after FE, for memory;
- the memory guard;
- the GPU's fast path.

**Out until the engineer says (12:35):**

| Setting | In fm500f | Why it is out |
|---|---|---|
| The sharpness capped at 4 (`--beta-most 4`) | yes | Added in the night when the sharpening broke the modes. Without it (`fm500g`), the floor held, but FE found a mode at 2551 Hz, 2 % from s1's 2500 |
| Taubin's smoothing, 30 passes (`LOOP_SMOOTH=30`) | yes | Added so FE could mesh the motor side. It moves the shape away from the optimiser's, and it adds undercuts: on `fm500e`, 107 / 14 cm² at 10 passes and 143 / 42 at 30, against about 85–100 / 2–4 unsmoothed |
| The kept-clear check's override (`LOOP_KEEP_CLEAR_OK=1`) | yes, not needed | fm500f stood 0.07 % where the drawing keeps clear; the check's limit is 0.5 % |

## 4. What is still unsolved

1. **The agreed baseline has no passing run.**
   - Without the cap, `fm500g` fails s1 in FE.
   - Without the smoothing, FE could not mesh the floor designs' motor sides.
2. **The optimiser reads thin members too stiff.** Its 4 mm cubes are a coarse mesh for members 4–8 mm wide, above all a one-cube link.
   - `fm500c` read 40 µm where FE read 84 on the same shape (mount-3 held by a one-cube link).
   - `fm500d` read about 1.4 times too stiff.
   - Above about 2 kHz, its modes run up to about 15 % off FE's. `fm500g` put its nearest modes to s1 at 2108 and 2798 Hz; FE put them at 2224 and 2551. So its 12 % gap at s1 does not guarantee FE's 3 %.
   - The safety 1.5 covers the statics, for about 0.2 kg.
3. **Loose metal.** fm500f's field had 21 cubes joined to nothing (0.3 %), fm500g's 14. The massless rule stops them making false modes, but they are there.
4. **The drawing pinches.**
   - **At the input bore:** a ring of near-zero thickness round the bore at its pocket's floor (z −46), where the drawn surface meets the bore's exact cut. FE's mesher refuses it. It appeared only in the floor designs; the smoothing hid it.
   - **Round mount-1's arm:** slivers where the arm is thin.
5. **Castability fails, on three rules** (unsmoothed / Taubin 30):
   - **Undercuts:** about 85–100 cm² on the motor side in every design, mostly round the mounts' lugs, where the brackets' rooms cut the columns from the side; Taubin raises it to about 150.
   - **Thinner than 4 mm:** about 200–215 / 115–140 cm², rising to about 300 / 160–190. The cause is the 4 mm walls read at the check's own 4 mm limit, and members one cube wide. The motor side's least thickness is 0.12–0.15 mm: pinches.
   - **Sections over 16 mm:** 17–24 mm, where members meet.
6. **The look is blocky.** Each 4 mm cube is drawn whole, so outlines are staircases, and thin spikes and crumbs show.

## 5. The problem we are now dealing with

The optimiser already has three length rules:

- a least height: a member counts only once it stands 8 mm proud;
- a greatest height: 24 mm off the shell;
- a greatest thickness: about 16 mm.

**It has no least width in plan.** Nothing stops a member, or the link to a mount, from being one cube (4 mm) wide, so it makes them wherever they are cheap. That one gap drives most of §4:

| One-cube members cause | Which shows as | And was patched by |
|---|---|---|
| A coarse mesh for the model | the model too stiff; the s1 miss (§4.2) | the safety 1.5; the cap |
| A lug hanging on a one-cube thread; crumbs left behind | loose metal, false low modes (§4.3) | the massless rule |
| The sharpening snapping a one-cube link | the first-mode floor lost at once | the gentle sharpening; the cap |
| Slivers and pinches in the drawing | FE refusing to mesh (§4.4, partly) | Taubin's smoothing |
| Faces under 4 mm | castability's thin areas (§4.5, partly) | |
| Spikes and crumbs | the look (§4.6, partly) | Taubin's smoothing |

Four things are not from this root, and need their own fixes:

- **The input bore's pinch.** The drawn floor lands on an exact cut. Whether wider members alone would avoid it is not known.
- **The undercuts round the mounts' lugs.** The brackets' rooms cut the columns from the side. This is for the castability discussion.
- **The 4 mm walls read at the check's 4 mm limit.** This is the check's tolerance.
- **The 4 mm staircase.** This is the grid itself.

## 6. The approach

### Option 1 (recommended, next): the least member width in plan, and the drawing's defect at the input bore

**(a) The optimiser:** a column's height counts only up to the height that the fullest 2 × 2 block of columns round it reaches. This is a morphological opening of the heights (Sigmund 2007).

- A member one cube wide then carries nothing and weighs nothing, so the optimiser stops making it.
- Every member is at least 2 cubes (8 mm) wide and, by the existing rule, at most about 16 mm: production's range for ribs.
- A member is the optimiser's metal alone. The fixed parts don't count toward its width, so no member is narrower than 8 mm, even where it meets a boss, a lug or a wall.
- It takes one switch, `--least-width 8`, with a smooth minimum and maximum so the gradients flow. Its derivatives are checked by `topo_gradcheck.py`.
- **This is a new setting: it needs the engineer's go.**

**(b) The drawing:** find why the drawn floor lands exactly on the input bore's cut, and keep it a clearance off, as the drawing already keeps 2 mm clear round the kept-clear spaces. This is a fix, not a setting. Without it FE may refuse the motor side again, and the run would have no FE verdict.

**Then one run:** the agreed baseline with (a), drawn with (b), and nothing else.

- About an hour to build and check.
- About 15 minutes to run.
- About 10 minutes to draw and judge.

**How we will know,** each measured against fm500f and fm500g:

- **No one-cube member:** a census of the field.
- **No loose metal:**
  - the drawing's check counts no loose cubes;
  - with the massless rule switched off for a check, the optimiser's lowest modes match FE's.
- **The model near FE:**
  - `model_vs_fe.py` within about 10 % on every seat;
  - the modes round s1 inside the 12 % gap.
- **FE meshes the drawing with no smoothing.**
- **Castability:** the thin areas and the least thickness shrink.
- **Every FE line passes.**

**What it would make unnecessary, if it works** (each change only on the engineer's word):

- The massless rule idles; it stays as a guard.
- The sharpening can go back to doubling, so runs are faster.
- The safety can come down toward 1.25, for about 0.2 kg less metal.
- The smoothing and the cap stay out.

**What it will not fix:**

- the 4 mm staircase look;
- the undercuts round the lugs;
- the sections over 16 mm where members meet. Cleaner junctions may shrink them.

**Risks:**

- **Corner contacts.** Two 8 mm members can still touch at a corner only: a hinge in the model, a pinch in the drawing. If the run shows any, the same rule is extended to close them.
- **Slower settling.** Morphology filters can slow an optimiser's settling (Sigmund 2007). The fallback is the same rule as a constraint: the metal in members narrower than 8 mm at most 1 % of the placed metal.
- **Coarse widths.** On 4 mm cubes, widths come in steps of 4 mm: 8, 12 and 16.

### Option 2 (after option 1, larger): members as production's features, sized by the optimiser (D17)

This starts from option 1's clean free run.

- **The agent** reads the member families from the library: ribs, webs, the arms to the mounts, collars round the bores.
- **The optimiser** sizes each member: its place, width and height. Parts are built: `--height-features`, the primitive library and `member_map.py`.
- **The drawing** builds them as exact, smooth CAD along the pull: plates with rounded tops and fillets.

This removes the staircase and the drawing's smoothing for good, and gives shapes castable by construction that a designer can take. It is days of work, and the engineer put it later (12:12). Option 1 comes first because D17 needs a clean free run to read.

**Not proposed now:**

- **The level-set method** (Shuvo et al. 2026). It gives smooth boundaries, but it is a different optimiser on a conforming tet mesh solved every iteration: hours a run on this laptop. Our tet meshing is the fragile step.
- **Robust design.** The run time.

## 7. What the engineer is asked

1. The go for option 1 (a): the new setting, a least member width in plan of 8 mm (two cubes).
2. The go for option 1 (b): the drawing's fix at the input bore.

Then the one run, judged as §6 says.

## 8. The result of option 1 (a) (14 October, 16:01)

`baseline2_lw8` is the agreed baseline with the least member width in plan of 8 mm (`fm500_run.sh baseline2_lw8 --least-width 8`; the engineer, 13:42: "lets try a"). It ran with no smoothing, no sharpness cap (it sharpened to 16) and no override.

Its first part stopped at iteration 128, in the optimiser's mode solve. A 22-cube piece of metal joined to nothing had left the single factor nearly singular: it refined in 16 steps with the piece and 4 without, and the piece changed nothing else. So that metal now takes 10⁻⁶ of its stiffness as well as of its mass (`topo.LOOSE_STIFF`; the engineer, 15:37: "Ok"), and the run resumed from iteration 120.

**It passes every graded FE line:**

| Line | `baseline2_lw8` | `baseline2_fm500f` | Limit |
|---|---|---|---|
| Worst seat | 34.4 µm | 36.1 µm | 52.2 µm |
| Tilt | 0.694 | 0.685 | 1.0 |
| First mode | 678 Hz | 824 Hz | 500 Hz |
| Gear orders | nearest 1021 and 1296 Hz round s2; 2411 and 2637 Hz round s1 | clear | none within 3 % |
| Mass | 4.94 kg | 4.39 kg | 7.73 kg |
| Oil-tight | yes | yes | |

**Against §6's checks:**

- **One-cube members gone.** Metal one cube wide fell from 48 % to 3.4 % of the motor side's placed cubes and from 31 % to 2.5 % of the cover's. Corner-only contacts fell from 520 + 230 to 48 + 17. The members are two cubes wide along the same paths (`width_census_lw8.png`).
- **FE meshes the drawing with no smoothing.** The pinch at the input bore did not come back, so the drawing's fix (b) is not needed.
- **The model is near FE** (`model_vs_fe_baseline2_lw8.log`).
  - Statics: the optimiser's own field reads 35.2 µm and tilt 0.669, FE 34.4 µm and 0.694, within 2-4 %. On `fm500e` the field had read 35 µm where FE read 43.
  - Modes: the drawing in the optimiser's model reads within 2-9 % of FE from 650 Hz to 2.6 kHz, against up to 15 % before.
  - The optimiser's own field reads its modes 10-18 % under FE's: the drawing fills about 12 % more cubes at the members' edges.
- **Loose metal remains.** 58 cubes on the motor side are joined to nothing, against 133 in fm500f. With the loose rules switched off for the check, they give false modes at 16-255 Hz. So the rule stays, and it works.
- **Castability is better but still fails.**
  - Undercut: 84 / 3 cm², against 152 / 38 (motor side / cover).
  - Thinner than 4 mm: 189 / 112 cm², against 295 / 169.
  - What is left: the undercut round the mounts' lugs, the 4 mm walls read at the check's own limit, member sections of 26 / 24 mm against 16 where members meet, and a least thickness of 0.16 mm.

**The cost:** 0.55 kg more metal than fm500f. Its one-cube members were stiffness the model over-rated.

**What it made unnecessary:**

- the smoothing, the cap and the override: none was used, and FE meshed;
- the drawing's fix (b).

**Still needed:** the massless rule, now with the stiffness.

**Open, for the engineer:**

- The safety of 1.5 now stands against a model within 4 % of FE on the statics. A lower safety would win back metal.
- The look: 4 mm steps.
- Castability.

**Pictures:** `compare_lw8.png` (fm500f and lw8 side by side, with their numbers), `look_face_baseline2_lw8.png`, `width_census_lw8.png`.

## 9. Next: the optimiser in spline space (the engineer, 14 October 17:27)

Two outside suggestions were weighed (the engineer, 17:18):

- **A smooth 2.5D implicit optimiser:** B-spline level-set outline and height fields, a drafted body growing along the pull, explicit least sizes for solid and gap, a connectivity rule, a fine immersed FE grid and mode tracking.
- **A reconstruction of lw8** by contours and lofts, and a survey of design spaces: B-spline fields, level sets, moving morphable components, explicit rib layouts.

**Taken:** the first's target, built in stages on the existing model.

- Smooth B-spline fields per half replace the per-column heights:
  - an outline field: metal where it is positive;
  - two height fields: one for columns on the end walls, one for columns on the split. Every member stands at least 8 mm proud by construction.
- Each 4 mm column samples them at its centre. The model, the couplings, the loads, the modes and GCMMA stay as validated on lw8.
- The 8 mm least width applies to the outline field, through the 2 x 2 opening.
- The drawing builds the members from the same fields, smoothly interpolated, in place of holding cubes.

**Order:** the code is checked on lw8 with a quick fit (fit, draw, FE), then the optimiser runs from the empty start.

**Not taken now, and why:**

- **A fine 1-2 mm immersed FE grid.** 2 mm is about 3.3 M unknowns against the card's 2.18 M. And with members at least 8 mm wide, the 4 mm model is within 4 % of FE on the statics and 2-9 % on the modes.
- **Robust eroded and dilated design:** the run time (the engineer, 12:12).
- **Moving morphable components.** The result depends on the starting components, and it conflicts with the optimiser forming the members. They are kept for reading members at the CAD hand-over.
- **Reconstruction alone.** That is smoothing after the fact again; its fit is the check here.
- **A general 3D level set.** It gains nothing for a part cast along one pull, and would take hours a run here.
- **The safety at 1.25 (step 0):** not taken.

**Later, if needed:**

- a connectivity rule in place of the massless rule;
- modes tracked by their shape;
- the outline and height fields as the CAD hand-over's curves and surfaces.

## Source

- Sigmund O. (2007). Morphology-based black and white filters for topology optimization. *Structural and Multidisciplinary Optimization* 33, 401–424. doi:10.1007/s00158-006-0087-x. The opening filter (erode, then dilate) gives the solid members a least length.
