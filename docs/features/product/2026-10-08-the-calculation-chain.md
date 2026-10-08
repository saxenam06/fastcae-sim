# The calculation chain: from the contract's inputs to a graded design

**Date.** 8 October 2026, 21:15. Written at the engineer's request, plainly, with the first contract's numbers (Ivanov 2018).

**In one paragraph.** The contract is the question. It fixes:
- what the housing must carry: the torques and speeds;
- where it must hold the gears and bearings: the gear train and the packaging;
- what it must not break: the pass criteria;
- how it is made: the process.

From those few binding inputs, a chain of deterministic tools works out everything else, one step after another. Each tool's outputs become the next tool's inputs. Nothing derived is typed by hand, and every value carries where it came from.

The chain has two halves:
- **The first half** turns the inputs into a frozen task: the seats where the bearings sit, and the forces on them under every load case.
- **The second half** runs for every design a campaign makes: it builds the housing around those seats, tests it under those forces, and grades it against the pass criteria.

The first three steps are built today; the rest is planned, with its method chosen and its checks named. The Contract page shows the same nine steps, with the same numbers, each with what it takes in and gives out.

---

## 1. The most binding inputs

| Input | Ivanov's value | Why it binds | From |
|---|---|---|---|
| **The gear train** | 25/51 and 23/81 teeth; modules 1.85 and 2.05 mm; 18° normal pressure angle; 30° helix; profile shifts; face widths | Fixes the gears' sizes, the ratio (7.1843, step 2), the forces at each mesh, and how far apart the shafts sit (82.917 and 125.037 mm, step 1). The ratio and the centre distances are therefore calculated, not inputs; Ivanov's 7.184 and 83 / 125 mm are only the check (the engineer, 22:57) | Ivanov 2018 |
| **The packaging** | 165 mm from input to output | Fixes the angle between the stages, and so where every bearing seat sits in the plane | the user (proposed: Hofstetter's offset) |
| **The torques** | 150 N·m peak, in drive, reverse and regeneration | The loads the housing carries | Ivanov 2018 (regeneration assumed) |
| **The speeds** | 6,000 rpm cruise; 8,673 rpm maximum | The gear frequencies the housing must not ring at; bearing life | Ivanov 2018; the user's 160 km/h top speed |
| **The service life** | 944 h | How big the bearings must be | borrowed from Hofstetter 2018 |
| **The process and material** | sand casting (proposed); EN AC-42100 T6, E 69 GPa, ν 0.33, 2,600 kg/m³ | What shapes are allowed; how stiff the metal is | Ivanov 2018; the user |
| **The pass criteria** | the housing's 50 % share of the gear tolerances (grade N6); bearing tilt 0.5 / 0.8 / 1.0 mrad; modes at least 3 % from the gear frequencies at 6,000 and 8,673 rpm; a 25 % margin; least mass | What every design must meet | JGMA, Shigley, Marano 2021 |

**The most binding of all are the gear train and the packaging.** Together they put the six bearing seats where they are, and every design must keep those seats exactly. Next come the torques, which load the seats, and the pass criteria, which judge how far the seats may move.

## 2. First half: from the inputs to a frozen task (the load tool)

| # | Step | Method (source) | Takes in | Gives out | Feeds | State |
|---|---|---|---|---|---|---|
| 1 | **Gear geometry** | Involute geometry (DIN 3960, ISO 21771) | teeth, module, pressure angle, helix, profile shifts | working pressure angles (23.6° and 22.8°); base and working diameters; working centre distances 82.92 and 125.04 mm, checked against the published 83 and 125: ✓ | 3, 4, 6, the validator | **built** |
| 2 | **Speeds and gear frequencies** | Through the tooth ratios; teeth × speed / 60 (Shigley) | teeth, the input speeds | ratio 7.1843 (checked against the published 7.184); shaft speeds 6,000 / 2,941 / 835 rpm at cruise; mesh frequencies 2,500 and 1,127 Hz at cruise | 7, 9, the contract's mesh orders | **built** |
| 3 | **Where the shafts sit** | The triangle of the three axes (law of cosines) | the working centre distances from 1, the 165 mm packaging | 103.1° at the intermediate shaft, so the three shafts' positions in the plane | 6, 8 | **built** |
| 4 | **Gear forces** | At the working pitch circle and pressure angle (Shigley's form, extended to profile shift; confirmed by drivetrainhub) | the torque in each case; the geometry from 1 | at 150 N·m, stage 1: 5,499 N tangential, 2,399 N radial, 3,243 N axial; stage 2: 11,066, 4,657 and 6,490 N (preview, worked with our geometry code). Directions per case | 6 | planned (GBX-1) |
| 5 | **Spacing along each shaft** | Face widths, bearing widths and gaps (Shigley §18-4; Łódź Ch. 3) | the face widths; the bearing widths from 7 (a first guess at first); the gaps (assumed) | where each gear and bearing sits along its shaft | 6, 8 | planned (GBX-2) |
| 6 | **Bearing loads** | Each shaft a beam on two bearings, with the axial force's moment (JTEKT eq. 5-29). For the tapered pair, each bearing's induced axial force is 0.5·Fr/Y (Machine Design 2005; NSK) | the forces from 4; the positions from 5; the working radii from 1 | the force on each of the six seats in each load case: radial in two planes, and axial | 7, 8, and the judge's loads | planned (GBX-2) |
| 7 | **Bearing sizes** | Rating life L10 = (C/P)^p (the catalogue method, via Shigley and Łódź; ISO 281 is the standard) | the seat loads from 6; the speeds from 2; the 944 h; the types (Hofstetter's pattern) | each seat's bearing, and its outer diameter and width (ISO 15) | 8, and back to 5 if a size changed | planned (GBX-3) |
| 8 | **Derive and freeze** | The contract's rules: every derived value stamped with its tool, version and inputs | everything above | the seats (centre, axis, diameter, width, stock); the load cases with their seat forces; the mesh orders. The validator accepts the contract as derived, then it freezes, and its hash becomes the task's name | the second half | planned (GBX-4); freezing is built |
| 9 | **The pass lines in numbers** | The gear tolerance times the housing's share (JGMA 1102-01); tilt by bearing type (Shigley Table 7-2); bands round the gear frequencies (Marano 2021) | the gear sizes and grade N6; the bearing types from 7; the frequencies from 2 and the check speeds | the µm per face width, the mrad, and the frequency bands every design must meet | the verdict | planned (the judge, PHY) |

**One loop.** Steps 5, 6 and 7 depend on one another:
- the bearings' widths set the spacing (5);
- the spacing sets the loads (6);
- the loads set the bearings' sizes (7).

So the tool starts from a first guess and goes round until the sizes stop changing, usually in two or three passes. Shigley's case study says the same: the design is iterative.

## 3. Second half: from a frozen task to a graded design (every campaign step)

| # | Step | Method | Takes in | Gives out | Feeds | State |
|---|---|---|---|---|---|---|
| 10 | **The idea** | The agent's hypothesis: what to change, why, the gain expected, what would prove it wrong | the evidence from the last design (margins, where it is soft), the budget left | a change to try | 11 | planned (AGT-1) |
| 11 | **The geometry** | The machined core in CadQuery, built from the seats (8); the structure grown in field space; the two joined | the seats, the space, the process, the idea | one housing | 12 | planned (GEO-1) |
| 12 | **Castability** | The process's rules: walls, draft, no undercuts | the housing, the process | pass, or where it breaks the rules | 13, or back to 10 | planned (PRC) |
| 13 | **Statics** | FE under each load case, with the seat forces from 6 applied | the meshed housing, the load cases | how far each seat moves and tilts; each mesh's misalignment | 15 | planned (PHY-1) |
| 14 | **Modes** | FE eigenvalues | the meshed housing, the material | the natural frequencies and mode shapes | 15 | planned (PHY-3) |
| 15 | **The verdict** | Each result against its pass line from 9, with the 25 % margin | 13, 14, and the mass | pass or fail; the worst margin; the mass; the rung | 10 (the next step); the data | planned (PHY) |
| 16 | **The record** | Each step kept with what was seen, tried, made and graded | 10-15 | datapoints (graded designs, decisions) and tasks cut from them | the Data tab, and learning | planned (DAT-1) |

## 4. The chain on one line

```
inputs ─▶ 1 geometry ─▶ 2 speeds & frequencies ─┐
       └▶ 3 where the shafts sit ───────────────┤
          4 gear forces ─▶ 5 spacing ⇄ 6 bearing loads ⇄ 7 bearing sizes
                                         └──────▶ 8 derived & frozen task ─▶ 9 pass lines
   every campaign step: 10 idea ─▶ 11 geometry ─▶ 12 castability ─▶ 13 statics + 14 modes
                                  ─▶ 15 verdict ─▶ 16 the record ─▶ back to 10
```

**How each step is trusted.**
- The built steps are checked against published numbers: the agricultural gearbox's and Ivanov's centre distances.
- The load tool is checked in four ways: against Shigley's, Łódź's and the textbook example's worked answers; by exact invariants (force × radius gives back the torque, and every shaft balances); by an independent FE beam; and by injected faults. See the [load tool's plan](../gearbox/2026-10-08-load-tool-plan.md).
- The judge is verified on its own reference cases before it judges anything.
