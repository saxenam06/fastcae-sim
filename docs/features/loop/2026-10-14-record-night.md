# The night of 13-14 October: the first mode held inside the optimisation, and a smoother drawing

**14 October 2026, 04:20.** LOP-29. The engineer left at 02:28-02:33 with this brief:

1. Get a run whose first eigenvalue is raised, at least above about 250 Hz in the optimiser, with the low modes of the mounts gone.
2. Then apply the best smoothing that loses none of the optimiser's metal, so that a smooth shape comes out that a CAD designer can read.
3. Keep it manufacturable: two halves, metal added only along the pull. It need not be organic, but it should be smooth, nice and attractive.

Their earlier words of the evening (00:13-02:26) fixed the set-up:

- **The fixed set:** one 4 mm shell round the whole gearbox, split in two at the split plane; the halves bolted on the sealing land; the mounts. Nothing else is fixed: no bearing towers and no seats' rings.
- **Loads and supports:** loads on the bearing bores, the halves tied at the bolt holes, the housing held at the mounts.
- **No plan mixing** (`--height-field 4`): baseline 2's set-up. "No baseline1 going forward."
- **The housing's first mode at least 500 Hz** (01:17). "Goal is that structure should hold limit of given first mode inside optimisation" (02:02). "Or try to maximise first mode if 500 is not reachable" (02:26).

## 1. The result

**`baseline2_fm500f` passes every graded FE line, with the first-mode floor held by the optimiser itself.**

| Line | FE | Limit |
|---|---|---|
| Worst seat, peak drive | 36.1 µm | 52.2 µm to beat |
| Tilt, worst seat against its line | 0.685 | 1.0 |
| First mode | 824 Hz (the optimiser's own: 769 Hz) | 500 Hz |
| Gear orders | the nearest modes 996 and 1383 Hz round s2's 1127; 2340 and 2912 round s1's 2500 | no mode within 3 % |
| Mass | 4.39 kg | 7.73 kg |
| Oil-tight | yes | |

- **The mounts:** after the first mode was raised, each mount carries a clear, strong arm: a branched arm to mount-1, a closed frame to mount-2, and a two-legged frame to mount-3.
- **The cover:** straight rib-like members radiate from the output bore.
- **Castability fails:** undercut 152 / 38 cm² (motor side / cover), thinner than 4 mm 295 / 169 cm², the largest member section 21.5 / 24 mm. See §4.
- **Pictures:** `data/first_loop/steps_baseline2_fm500f.png` (the optimisation, the drawing and FE), and `data/first_loop/night_comparison.png` (every design of the night side by side, each with its numbers).

**How it was run:** `LOOP_SMOOTH=30 LOOP_KEEP_CLEAR_OK=1 bash prototypes/first_loop/fm500_run.sh baseline2_fm500f --beta-most 4 --safety 1.5`.

- **The set-up:** baseline 2's (no mixing, the 4 mm shell fixed, no towers, members only 8 mm proud, the least metal under 7.73 kg, the orders' gaps 12 %).
- **The first-mode floor:** each of the lowest six modes at least 500 Hz.
- **The sharpness:** capped at 4.
- **The margin:** every tilt and bed held at 1/1.5.
- **The drawing:** 30 Taubin passes.
- **Times:** the optimisation settled at iteration 101 in 721 s; the whole proposal took 869 s.

## 2. How it got there: every run, with the step it taught

| Design | What changed | The optimiser's own lowest modes | FE | What it taught |
|---|---|---|---|---|
| `baseline1` | 6 mm mixing, no floor | 36-228 Hz | 47.8 µm, tilt 0.90, 664 Hz: passes | the false low modes appear |
| `baseline2` | no mixing, no floor | 27-170 Hz | 47.0 µm, 599 Hz; a mode at 1097 Hz by s2: fails | two mount lugs left loose; their false modes filled the 14 modes read, so the gaps never saw the real one |
| `baseline2_fm500` | the floor on the lowest mode, 500 Hz, held at 560 | 47 Hz at the end | could not mesh | held while grey (500-600 Hz to iteration 48), lost when the doubled sharpness cut mount-3's lug loose |
| `baseline2_fm500b` | the sharpness raised only while the modes hold, by √2 | swung 300-570 Hz | stopped at 98 | a cluster of local modes takes turns at the bottom: one floor chases one at a time |
| `baseline2_fm500c` | the floor on each of the lowest six, held at 500 | 124 Hz (β 11.3, 200 iterations) | 84.3 µm, 452 Hz: fails | held to β 4, lost past it; the model read this shape twice as stiff as FE (mount-3 joined by a one-cube link) |
| `baseline2_fm500d` | the sharpness capped at 4 | 214 Hz | could not mesh; drawn smooth (Taubin 10): 55.0 µm, tilt 1.14, 547 Hz: fails | the first design over 500 Hz in FE; the model about 1.4 times optimistic on the stiffness |
| `baseline2_fm500e` | every line held at 1/1.5 | 180-331 Hz | 43.2 µm, tilt 0.68, 786 Hz, 1151 Hz by s2: fails on the orders | the margin covers the model's optimism; the false modes still blind the gaps |
| `baseline2_fm500e_t30` | the same field, Taubin 30 | | 42.6 µm, tilt 0.69, 812 Hz, orders clear: passes | the smoothing moved the mode out of the band: luck |
| **`baseline2_fm500f`** | **loose metal massless in the optimiser's modes** | **769, 862, 942 Hz** | **36.1 µm, tilt 0.69, 824 Hz, orders clear: passes** | **the false modes gone; the run settles in half the time** |
| `baseline2_fm500g` | `baseline2_fm500f`'s set-up, the sharpness to 16 (no cap) | 766, 835, 966 Hz | 41.1 µm, tilt 0.95, 787 Hz; a mode at 2551 Hz by s1's 2500: fails on the orders | the cap is no longer needed for the floor; but above about 2 kHz the model's modes run up to about 15 % off FE's (its nearest to s1 2108 and 2798 Hz, FE's 2224 and 2551), so the 12 % gap does not guarantee FE's 3 % |

## 3. What was built, and what it fixed

1. **The least heights counted frozen voxels only at a run's start** (`topo_free.least_heights`, since the empty start of 12 October). A seat's ring partway up a column pushed the shell 20-26 mm past the walls behind every bearing. Fixed: each free voxel gets the share of it the span covers.
2. **The drawing's sealing land covered the inside too** (`exact_walls.least_sdf`, `least_density`). The shell under the cover's big gear room was drawn 8 mm, not 4. Fixed: the band outside the inside.
3. **No seats' rings with the fixed shell** (the engineer). All six rings' cubes stay fixed as the shell's.
4. **The first mode's floor** (`topo_free.py --first-mode 500`, `--first-margin`; `topo.mode_gaps(..., floor=)`) on each of the lowest `FLOOR_MODES` = 6 modes. The grade's `first mode` line (500 Hz).
5. **The sharpening waits for the mode limits** and steps by √2 (`topo.BETA_STEP_MODES`). The forced step after 25 iterations stays as the fallback; `--beta-most 4` caps it.
6. **Loose metal massless in the optimiser's modes** (`topo.Voxels.loose`, `LOOSE_MASS` = 1e-6; `LOOP_LOOSE_MASS=1` the old way). Loose metal is metal in either half joined face to face to nothing but its own piece, which the drawing drops. Checked on `baseline2_fm500e`'s field: its metal-or-air modes went from 180-331 Hz to 809, 879, 978 Hz, against FE's 786.
7. **The drawing's cube check counts the loose metal apart** (`outcome_cad.cube_fidelity`'s `loose`). A crumb joined to nothing is the optimiser's, not the drawing's loss.
8. **The objective `modes_tilt`** (built, not run): the lowest six modes' smooth minimum raised, with the budget a ceiling and every line held. It is the fallback if a floor is out of reach.
9. **FE refused the floor designs' motor sides.** The drawn surface pinched, in a ring round the input bore at its pocket's floor (z -46), where the bore's exact cut meets the floor. Coarsening left slivers that TetGen calls crossings; every repair tried failed. **Taubin's smoothing before the cuts (`LOOP_SMOOTH=10` or 30) moves the floor off the cut, and the surface meshes.**
10. **The smoothing:**
    - `LOOP_SMOOTH_KEEP=<mm>` (the cubes' distance blurred, each cube's centre held by a 2.5 mm ball) barely changes the look at 2 or 4 mm.
    - Taubin's `LOOP_SMOOTH=30` rounds the members visibly and keeps the cube check (1 lost of 6,923 in `baseline2_fm500f`).
    - At 60 passes the cube check still holds, but FE cannot mesh the result: the thin members' faces draw together, and the
      coarsened surface crosses itself (`baseline2_fm500f_t60`). So 30 passes is the practical limit of Taubin's smoothing on
      this housing.
11. **Tools:**
    - `steps_view.py <design>` draws the steps done so far;
    - `compare_sheet.py <out> <design>[:<title>] ...` puts designs side by side, two to a row, with their numbers;
    - `protected_view.py [--towers]` pictures the fixed set exact;
    - `fm500_run.sh <design> [topo_free arguments]` runs the night's set-up.

## 4. What is open (for the engineer)

1. **Castability fails, and the smoothing adds to it.** On `baseline2_fm500e` the undercut grew from 107 / 14 cm² at 10 passes to 143 / 42 at 30. Taubin's smoothing is three-dimensional: it waves the members' vertical sides, and part of each side then faces against the pull. Before the smoothing, most undercut and thin areas sat on the mounts' lugs (the brackets' rooms cut round them) and on the 4 mm walls read at the check's 4 mm limit (`castable_baseline1.png`).
   - **The proposal:** a 2.5D smoothing fitted to this housing. Each half's members are columns along the pull, so the members' outline would be smoothed in plan and their tops smoothed, with the sides kept vertical: castable by construction, smooth, and holding every cube. It is not built.
2. **The optimiser reads thin members too stiff.** It is not the element: Wilson's incompatible modes read 0.985 of beam theory one cube thick. It is the resolution: 4 mm cubes are a coarse mesh for members and links 4-8 mm wide, and for a one-cube link above all.
   - `baseline2_fm500c` read twice as stiff as FE (`model_vs_fe.py`: 40 against 84 µm on the same shape).
   - The 1/1.5 margin covers it in `baseline2_fm500f` (36 µm in FE against 52.2), at the cost of about 0.2 kg more metal.
   - **Lasting remedies:** members at least two cubes wide where they carry load, margins learned from FE, or a finer model.
3. **The smoothing that keeps the material flow** (the engineer, 01:45). The papers in the library:
   - Amroune et al. 2022 (lofting along each member's skeleton from its own sections; the L-bracket within 3-4 %);
   - Wang & Ma 2026 (Catmull-Clark along the skeleton);
   - Ježek et al. 2025 (a smooth surface keeping the volume);
   - the paper the engineer recalled, probably Xia, Shi, Wang & Liu 2010 (*A level set based method for the optimization of cast part*, Structural and Multidisciplinary Optimization), not yet read.
4. **The sharpness cap is no longer needed** now that loose metal is massless. `baseline2_fm500g` sharpened to 16 and held the floor and the gaps in its own model. But FE found a mode at 2551 Hz in s1's band. Above about 2 kHz the model's local modes of thin members run up to about 15 % off FE's: the resolution again (open item 2).
   - **Remedies:** a wider gap for s1 (about 20 %), or members wide enough for the model to read them true.
   - Its tilt also came nearer its line (0.95 against `baseline2_fm500f`'s 0.69).

## 5. Decided next (the engineer, 14 October 12:00-12:12)

- **Kept:** the first-mode limit on the lowest six modes, the gentle sharpening, the safety margin 1.5, and the massless rule for metal joined to nothing (a free body's modes are not the housing's).
- **To be made unnecessary:** the drawing's smoothing and the thin members. The optimiser should form clean members itself; then the loose metal, the fake modes, the model's error on thin members and the 30-60 passes question go at the root.
- **Step 1, next: the minimum member width in plan.** Members at least two cubes (8 mm) wide where they carry metal, as the 8 mm height rule: members between 8 and 16 mm wide, about production's ribs.
- **Not now:**
  - robust design (the run time);
  - the connectivity rule (detached pieces stay massless, and the fraying bits are attached);
  - the outline limit (no visible effect on 12 October);
  - features sized by the optimiser (D17, later);
  - the level-set method (later): the engineer's paper is Shuvo et al. 2026, *Automated level-set topology optimization with conforming meshes and damage-informed morphological refinement*, CMAME 461, 119252 ([our note](../../research/2026-10-12-reviewer-papers/05-cmame-2026-shuvo-conforming-level-set.md), from its figures);
  - castability (to discuss).
- **12:35: the baseline holds only agreed settings.** The sharpness cap, Taubin's smoothing and the kept-clear check's override are out until the engineer says, and no setting goes in without asking. `baseline2_fm500f` passed with the first two, so the agreed baseline has no passing run yet. [The problem and the approach](2026-10-14-problem-and-approach.md) lists the agreed settings, what each bought, what is unsolved, and the next step.

## 6. Where the files are

- **Designs:** `data/first_loop/baseline2_fm500f*` (the drawn halves `.ply`/`.stl`, `fe_*.json`, `castable_*.json`, `flow_*.json`, `look_face_*.png`, `steps_*.png`).
- **Runs:** the run records `data/first_loop/topofree_mass_tilt_7.73kg_4mm_..._baseline2_fm500*`, with the optimisation logs `optimise_baseline2_fm500*.log`.
- **Comparisons:**
  - `night_comparison.png`;
  - `compare_smooth.png` (baselines 1 and 2 as cubes, smoothed 2 mm and 4 mm);
  - `plate_over_opening.png`;
  - `protected_regions.png` (the fixed set);
  - `model_vs_fe_baseline2_fm500c.log` and `model_vs_fe_baseline2_fm500e.log`.
- **Nothing is committed.** Everything since 9 October waits for the engineer's word.
