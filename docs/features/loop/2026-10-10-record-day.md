# 10 October, day and evening: the contract's set-up, a fast optimiser, and housings that look and work like housings (GBX-5, LOP-18 to LOP-20)

*For the next session, Claude or a person, and for the engineer. Where everything stands, every trial of the day with its numbers, what each one taught, and how to carry on. Times IST. Written 22:40, the last design's result added 23:03. The night before is in [the night's record](2026-10-10-record-night.md).*

## In short

- **The question, in the engineer's words (20:45):** "given some mount positions from the user (realistic positions) and the gear, bearing and shaft requirements, what's the optimal housing design?" And the shapes must be realistic (18:16-18:31): "we want a physics-aware version for our case: realistic shapes, taking loads optimally".
- **The method that works**, end to end in about 40 minutes at 6 mm:
  1. **The contract fixes the inputs, once,** before any run (the engineer, 20:46: "once you have decided, don't change it during the optimisation").
  2. **A stiff design first:** topology optimisation on compliance, both load cases, robust, with the casting rules as constraints. Those are the mould's pull, the least member and the new **greatest member**, so the metal forms walls, plates and ribs, never lumps.
  3. **Then the tilt held,** starting from that stiff design: the same compliance objective, with every bearing's tilt in both cases a constraint (`compliance_tilt`).
  4. **The skin drawing,** after the engineer's pictures (organic design, then a skin, then the housing). It takes the wall round the inside, the joint's sealing land with its bolt bosses, the mounts, and the optimiser's members exactly as placed, all blended into one cast body. The bores, faces and holes are then cut exact.
  5. **FE and the grade** on both cases. On the UI, a table compares every design with the reference.
- **The last design, `outcome_skin_6mm_tilt`** (23:03): 7.45 kg; the tilt held in the optimiser passes in drive (0.97 ×) and comes down to 1.31 × in reverse; the beds 63 / 59 µm (drive just over the reference's 52, reverse well under its 138); two mode clashes near 2,500 Hz; not yet castable. No design passes every line yet.
- **The design before it, `outcome_skin_6mm_both`** (21:27): **7.47 kg** against the reference's 7.73. Its bearing beds move **42 / 71 µm** (drive / reverse) against the reference's 52 / 138. It fails the tilt (1.36 × / **1.76 ×** its line), one mode clash (2,426 Hz near 2,500) and castability (thin areas, facet undercut). The day's last run, `outcome_skin_6mm_tilt`, holds the tilt in the optimiser.
- **Everything since 04:49 is uncommitted and not pushed** (the engineer's word, 09:57). 213 checks pass, plus one new; ruff is clean.

## Where everything stands (22:40)

**The contract and its set-up (GBX-5,** [gearbox page](../gearbox/status.md)**):**
- **One description** (`zenryx.domains.gearbox.spaces`): the elements are the keep-outs. They are the gears, the shafts with their exits (seal bores, Ø90 half-shaft joint rooms), the bearing bores, the differential, and the mounts with their brackets' rooms. One shell: the inside run from each room's far end to the split, a uniform wall (at least the contract's 4 mm), one cup per half.
- **No motor flange:** the vehicle holds the motor, which drives the input through a flexible coupling. So the mounts hold (i − 1)·T_in = 927.7 N·m.
- **The agent's hypothesis:** the split's place (between the stages), the bolt pattern (13 bolts on the bolt line, at most 80 mm apart), the wall. The joint rules are the process's (A26).
- **The mounts (A20), moved at 20:47:** (−170.2, −52.7), (176.4, 62.9) and (35.1, 280.9) mm. Each lug stands 3 mm past the split flange's edge, so the vehicle's bracket and bolt clear the housing.
  - They had come from before the shell existed. Mount-2's bracket room sat 11 mm inside the wall, mount-3's 16.5 mm inside the flange. Both the mounts and the shell were Claude's, and they contradicted each other.
  - `checks/gearbox/test_spaces.py::test_every_brackets_room_clears_the_housing` now holds them so.
- **The Contract page** shows three groups (the contract, what the agent decides, what the optimiser is given), each as exact volumes or as the optimiser's voxels.

**The tools as they stand** (`prototypes/first_loop/`; CLAUDE.md lists them):
- `topo_free.py`:
  - `--objective compliance_gcmma` (the stiff design) and `compliance_tilt --robust-p 16` (the tilt held: start it with `--start <stiff run> --beta0 8 --ramp 0`);
  - `--max-member <mm>` (the greatest member; 12 at 6 mm, 20 at 10 mm);
  - `--fast` (GPU assembly, kept factor, GPU MMA subproblem);
  - `--trade` (the trade's bearing bosses and joint band frozen; tried and set aside).
- `outcome_cad.py <run> <design> skin`, the skin drawing, and `outcome_chain.sh <run> <design> skin`. The chain draws, checks castability, pictures the organic shape and the CAD (`look.py`), runs FE, grades, and exports to the UI.
- The UI's Designs page: a comparison table over the 3D view on both tabs (optimised and parametric). It shows the optimiser's budget (fixed and placed), the drawn mass, the beds, the worst tilt, the first mode and castability, each with the grade's verdict, and the reference last (`names.summary_of`).
- Analysis:
  - `tilt_by_case.py` (the grade's tilt split by case);
  - `mass_where.py` (where a CAD holds more or less metal than its field, with a picture);
  - `mount_clearance.py`;
  - `greatest_check.py`;
  - `voxel_vs_fe.py`.
- `grammar.py` draws the trade's styles on today's contract, through one switch, `motor_on_housing()`, and the contract's mounts, exits and joint rules: `contract_avl`, `contract_kalyani`, `contract_zf`.

**The designs judged today** (all FE on TET10 meshes, single factor, residuals 10⁻¹¹; "tilt" is the worst seat against its line, with the shaft's lean):

| Design | How it was made | Drawn | Beds, drive / reverse | Tilt, drive / reverse | First mode | Castable |
|---|---|---|---|---|---|---|
| `outcome_compliance_10mm` | compliance, peak drive, 10 mm, whole field smoothed | 11.79 kg | 24 / 51 µm | 0.73 / 1.42 | 828 Hz, clear | no (1.5-1.6 % undercut, knife edges) |
| `outcome_compliance_6mm` | the same at 6 mm | 10.39 | 23 / 55 | 0.89 / 1.51 | 764, 2 clashes | no (6-7 %) |
| `outcome_skin_6mm_max12` | greatest member 12 mm, skin drawing with the trade's bosses | 11.24 | **22 / 42** | **0.67 / 1.32** | 739, 1 clash | no |
| `outcome_skin_6mm_contract` | the same field, the contract's set-up only | 9.61 | 29 / 54 | 0.81 / 1.53 | 697, 1 clash | no |
| **`outcome_skin_6mm_tilt`** | the tilt held (`compliance_tilt`) from the stiff design, members drawn as optimised | **7.45** | 63 / **59** | **0.97** / 1.31 | 630, 2 clashes | no (7.5-8.0 %; 330-352 cm² under 4 mm) |
| **`outcome_skin_6mm_both`** | both cases, mounts moved, mass-keeping drawing | **7.47** | **42 / 71** | 1.36 / **1.76** | 655, 1 clash | no (6-7 %; 290-366 cm² under 4 mm) |
| `contract_avl` | the grammar's AVL style, no optimisation | 6.52 | 115 / 184 | 6.37 | 669, 2 clashes | pull fails only on ≤ 0.01 cm² |
| `contract_kalyani` | Kalyani's style | 6.11 | 143 / 226 | 6.63 | 693, clear | the same |
| `contract_zf` | ZF's style (its line patterns not drawn) | 5.90 | 160 / 276 | 10.40 | 697, 1 clash | the same |
| the reference housing | | 7.73 | 52 / 138 | not given | | |

## The trials of the day, in order

| Time | What was tried | Setting | What it gave | What it taught |
|---|---|---|---|---|
| 12:49-14:17 | **GBX-5, the contract complete** (the engineer's review of the Contract page) | the elements as keep-outs; one shell; no motor flange; mounts, exits, joint rules into the contract | the set-up from one description, exact and as voxels | the elements *are* the kept-clear spaces; no separate rooms |
| 14:57-15:21 | the night's bound chain on the contract (LOP-18) | misalignment bound, 6 mm | 15-19 s an iteration; stage 1 still grey (binary 6,955 ×) | too slow to be a loop's step |
| 15:06-15:25 | **LOP-19, the optimiser fast** (after Träff et al. 2023: 65.5 M elements in 2 h on one GPU) | the stiffness assembled on the GPU into a fixed pattern, cuDSS refactorised in place, MMA's subproblem on the GPU | the same answers (5e-11, 1.9e-14), **about 5 × faster**: 3-4.5 s an iteration at 6 mm, 1 s at 10 mm | the time was in assembly, a fresh plan per factor and a Python subproblem |
| 15:25-15:44 | a fast p-norm misalignment chain | 6 mm, staged | binary 10.2 × at 2.8 kg; a killed stage restarted itself beside the next (two GPU jobs, 23 min) | chains: retry exit 127 only within seconds of the start; stop chains by their process trees |
| 15:58-16:02 | one robust run with doubling sharpness (`--settle`) | 10 mm, p-norm, peak drive | 122 s; binary 3.09 × | one run instead of three stages |
| 16:06 | why its seats moved 2.35-5.43 mm | its field solved as metal or air | **the core floated:** 98.7 % of the motion a rigid swing on one strut; mount-3 touched by no metal | the relative misalignment cannot see a rigid motion |
| 16:11-16:28 | **compliance the objective** (the engineer, after the papers' review) | 10 mm, peak drive, robust | 131 s; binary 1.38 ×; all three mounts tied; drawn and judged in 15 min | the papers' objective holds the core; the first design end to end |
| 16:32-16:56 | the same at 6 mm | | 888 s; binary 1.06 ×; CAD 10.36 kg, the same envelope | the voxel size does not make the shape |
| 16:40-17:05 | the explainer: their approach against ours | | [the page](2026-10-10-field-to-housing/field-to-housing.html) | ours was a smoothed envelope; theirs, members turned into a skin and ribs by a designer |
| 17:00 | the tilt split by case (`tilt_by_case.py`) | | both designs **pass in peak drive and fail only in peak reverse**, the case the optimiser never saw | optimise every case of the requirement |
| 18:33-18:35 | **the greatest member**, tested (Guest 2009; Wu, Aage, Westermann & Sigmund 2018) | 10 mm, 20 mm | the share held at 0.6; plates and webs instead of a lump; compliance 916 against 915 as metal or air | ribs come at almost no stiffness |
| 18:36-18:52 | the same at 6 mm | 12 mm | 974 s; binary 1.10 ×; compliance 738 against 716 without the rule | |
| 18:52-19:04 | **the skin drawing**, first version | the exact wall, the trade's bearing bosses, bolt columns, the joint's band, the members | `outcome_skin_6mm_max12`: **the first housing that looks like one**; the stiffest at the beds (22 / 42); 11.24 kg | the shapes come from drawing the members on a skin, not from smoothing everything |
| 19:05-19:25 | `--trade`: the trade's bosses and band frozen in the optimiser | | 5.78 kg frozen, 1.95 to place; binary 1.71 ×, compliance 1,066 (44 % softer); its drawing stopped | the trade's bosses spend metal where the loads do not ask; the engineer: the set-up is the contract's |
| 19:22-19:24 | the engineer: "I hope it's not the motor flange… we fixed the contract already" | | "flange" had meant the split flange | say *the split flange (where the halves bolt)* and *the bearing bosses*; never "frozen" without what |
| 19:27-19:38 | the redraw on the contract's set-up alone | | `outcome_skin_6mm_contract`: 9.61 kg; 29 / 54; reverse tilt 1.53 | the trade's bosses had bought the seats' stiffness (1.6 kg: 1.32 against 1.53) |
| 19:33-19:39 | the engineer: "how much weight the optimisation gets, compared with the previous iterations, on the UI" | | the Designs page's comparison table | every run gets 7.73 kg in all; the drawings came out 9.6-11.8 |
| 19:46-21:01 | **where the CAD's extra mass is** (`mass_where.py`, and the drawing weighed piece by piece) | the field and the CAD on one 2 mm grid | first read as the members' fattening (+0.84 kg) and the wall (+0.76); then, weighed piece by piece, **the joint's band: 1.5-1.9 kg** | see below: two faults in the band |
| 18:21-20:09 | the grammar on today's contract (a helper agent) | AVL, Kalyani, ZF | 5.9-6.5 kg, realistic, **4-5 times softer** at the seats (tilt 6.4-10.4) | placement matters more than style |
| 20:45-20:47 | **the mounts moved**, the contract fixed | | all three bracket rooms 3 mm past the flange's edge, 26 mm off the wall | decide the inputs before the optimisation; the check guards it |
| 20:49-21:16 | **both load cases** on the fixed contract | 6 mm, compliance, max 12 | 1,571 s; binary 1.24 × (the drive-only field read 1.51 in reverse) | |
| 21:16-21:27 | the mass-keeping drawing | the band a sealing land, the wall round both halves' inside, the members read at the level that keeps the mass | `outcome_skin_6mm_both`: **7.47 kg, beats the reference's beds**; tilt 1.76 in reverse; 290-366 cm² under 4 mm | keeping the mass by reading the members thinner (0.569) made them softer than optimised and thinner than the least wall |
| 22:11-22:27 | **the tilt held** (the engineer: "yes, and try one more time") | 10 mm, both cases, 7.2 kg | from nothing: tilt 0.95 × but compliance 5,301 (the stiff design's 2,797), its budget unspent; **from the stiff design: 0.99 × at 3,458**, the budget spent | a tilt constraint from nothing floats the core again; start it from a stiff design |
| 22:28-23:03 | **the day's last design**, `outcome_skin_6mm_tilt` | 6 mm, `compliance_tilt`, both cases, 7.2 kg, from the stiff 6 mm field; members drawn as optimised | field: tilt 0.96 ×, 4.75 kg placed; CAD **7.45 kg**; FE beds 63 / 59 µm, tilt **0.97 × drive (passes)**, 1.31 × reverse (the housing alone 0.96), 630 Hz with two clashes | the tilt held halves the excess at the same mass, at the cost of the drive beds (42 → 63 µm); the voxel model reads the tilt 35 % low |

## What the day taught

**The optimiser**
1. **A relative tilt lets the core float,** whether it is the objective (16:06) or a constraint started from nothing (22:15). The seat's tilt is measured against its shaft's chord, so a core that swings as one body reads no tilt. The cure is compliance as the objective, holding the core, and a tilt constraint only from a stiff start (`--start`).
2. **Optimise every load case the requirement holds.** The designs optimised on peak drive alone passed the tilt in drive and failed in reverse (1.32-1.53). Both cases share one factor, so the second costs one more solve a step. With the robust formulation, a step took 8 s instead of 4.4 at 6 mm.
3. **The greatest member turns lumps into walls, plates and webs** for about 3 % of the stiffness. It is a local volume constraint on the dilated design (`topo.greatest_share`, a ball's metal share at most 0.6). At 6 mm voxels it lets a 12 mm wall through and stops an 18 mm one.
4. **Fast enough for a loop:** 2-4 min at 10 mm, 15-26 min at 6 mm, 40 min end to end. Explore at 10 mm and finish at 6.
5. **The binary check is honest about the field, and the drawing is another object.** Judge designs by FE at equal drawn mass. A drawing heavier than its field makes FE look better than the field; one with thinner members makes it look worse (1.24 field, 1.76 FE).

**The drawing**

6. **Smoothing the whole field gives an envelope,** 2.7-4 kg over the budget. The 4 mm skin is drawn as a whole voxel, and every member melts into one body.
7. **The skin drawing gives a housing's look:** the exact wall, only the placed members, one blur for fillets, exact cuts. It shows a thin wall, a rib network with pockets, bosses, mount lugs and a flange with bolt bosses.
8. **The joint's band was the hidden weight,** 1.5-1.9 kg, from two faults.
   - Each half's band covered the joint's outline less only its own inside, so 9 mm plates closed the other half's opening across the split. The cure is to build the wall round both halves' inside, as the optimiser's skin is.
   - The outline is a convex hull, so the band filled the waists between the lobes. The cure is a 10 mm sealing land round the inside, with the bolts' bosses on it, as the trade's flanges are.
9. **Draw the members as optimised (0.5)** and give the optimiser the drawing's fixed extras less, about 0.5 kg. Reading at 0.4 fattened them by 1-2 mm a side (+0.84 kg). Reading higher to keep the mass thinned them below their optimised size and toward the least wall.
10. **A closing before the cast** lets the surface close at the lightest blur, so the wall keeps its thickness.

**Shapes and realism**

11. **The trade's styles without the field's placement are 4-5 times softer.** A realistic look is the grammar's; where the metal goes must be the optimiser's.
12. **The trade's bearing bosses (1.25·D + 10 mm) bought real stiffness.** About 1.6 kg took the reverse tilt from 1.53 to 1.32. But they are not in the agreed set-up, and frozen in the optimiser they cost 44 % of the stiffness.

**The contract, and working with the engineer**

13. **The inputs are fixed before the optimisation and never changed during it.** The contract's assumptions must agree with each other: the mounts came from before the shell existed and cut into it.
14. **Words matter.** "Flange" alone was read as the motor flange the engineer had removed. "Frozen" alone was read as changing the contract.
15. **Ask plainly, one question, only for the engineer's decisions:** load cases, objectives, contract values. Otherwise decide, say what was decided, and carry on (the engineer, 20:41: "ask your question plainly; I'm not understanding where you are and what you need from me").
16. **The engineer wants both realism and physics,** the optimiser's members drawn the way the trade draws a housing, compared with the reference at equal mass, with pictures and the UI's table.

**The machine**

17. **One heavy job at a time, helper agents included.** A helper's regression build reached 5.9 GB beside a CAD build and left 0.5 GB free; it was stopped.
18. **Stop a chain by its process trees** (`taskkill /F /T`): stopping the background task ends only its wrapper.
19. **A headless phone screenshot needs a 390 px iframe:** Edge will not make a window under about 500 px.

## How to carry on

- **A contract change:**
  1. `checks/data/contracts/make_examples.py`
  2. `python -m zenryx.api.snapshot`
  3. `python -m zenryx.api.volumes`
  4. `prototypes/first_loop/contract_layout.py`
  5. `setup_export.py`
  6. the checks

  Then no field from before the change can be redrawn. Their records name the layout "contract", and `data/first_loop/contract.json` has changed under them (20:47).
- **The method, as commands** (6 mm; the names are the run's stems):
  1. The stiff design: `topo_free.py 7.2 6 200 --objective compliance_gcmma --route split --robust 0.15 --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12`
  2. The tilt held: `topo_free.py 7.2 6 140 --objective compliance_tilt --robust-p 16 --route split --robust 0.15 --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12 --start <stiff run> --beta0 8 --ramp 0`
  3. `outcome_chain.sh <run> <design> skin`. It draws, checks, pictures, runs FE, grades and exports.
  4. `names.py`, then `npm run build` in `web/`.
- **Before any heavy job:** free memory over 6 GB, nothing else on the GPU, one job at a time.

## Open, and next

1. **The tilt's last 31 % in reverse, and the drive beds.**
   - The voxel model reads the tilt 35 % low against FE on the drawn CAD (0.96 against 1.31). Hold it with a margin, or optimise the binary design itself.
   - Holding the tilt cost the drive beds (42 → 63 µm, over the reference's 52). A bed displacement constraint should sit beside the tilt.
2. **Castability.**
   - The pull rule fails on 6-7 % of the surface, mostly the facets of walls drawn at the contract's 0° draft.
   - The least wall fails on thin members and knife edges where the split cuts the smoothed skin.
3. **The modes:** every skin design has one mode within 3 % of a mesh frequency (2,426-2,575 Hz near 2,500; sometimes 1,094-1,154 near 1,127). The first mode's own place could become a constraint.
4. **The realistic finish (the method's step 2):** the optimiser's members read into the grammar's clean ribs (straight between hard points, rounded tops, filleted roots).
5. **A run's record should carry its layout,** not the layout's name, so that a field can always be redrawn.
6. **Commit**, on the engineer's word.
