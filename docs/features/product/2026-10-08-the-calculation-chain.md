# The calculation chain: from the contract's inputs to a graded design

**Date.** 8 October 2026, 21:15; brought up to date on 9 October at 01:23. Written at the engineer's request, plainly, with the first contract's numbers (Ivanov 2018).

**In one paragraph.** The contract is the question. It fixes:
- what the housing must carry: the torques and speeds;
- where it must hold the gears and bearings: the gear train and the packaging;
- what it must not break: the pass criteria;
- how it is made: the process.

From those few binding inputs, a chain of deterministic tools works out everything else, one step after another. Each tool's outputs become the next tool's inputs. Nothing derived is typed by hand, and every value carries where it came from.

The chain has two halves:
- **The first half** turns the inputs into a frozen task: the seats where the bearings sit, and the forces on them under every load case.
- **The second half** runs for every design a campaign makes: it builds the housing around those seats, tests it under those forces, and grades it against the pass criteria.

The first three steps are built today; the rest is planned, with its method chosen and its checks named. The Contract page shows the same ten steps, with the same numbers, each with what it takes in and gives out.

---

## 1. The most binding inputs

| Input | Ivanov's value | Why it binds | From |
|---|---|---|---|
| **The gear train** | 25/51 and 23/81 teeth; modules 1.85 and 2.05 mm; 18° normal pressure angle; 30° helix; profile shifts; face widths | Fixes the gears' sizes, the ratio (7.1843, step 2), the forces at each mesh, and how far apart the shafts sit (82.917 and 125.037 mm, step 1). The ratio and the centre distances are therefore calculated, not inputs (the engineer, 22:57). Ivanov's 7.184 and 83 / 125 mm verified the tools once, in `checks/`, and are not part of the contract (23:37) | Ivanov 2018 |
| **The packaging** | 165 mm from input to output | Fixes the angle between the stages, and so where every bearing seat sits in the plane | the user (proposed: Hofstetter's offset) |
| **The torques** | 150 N·m peak, in drive, reverse and regeneration | The loads the housing carries | Ivanov 2018 (regeneration assumed) |
| **The speeds** | 6,000 rpm cruise; 8,673 rpm maximum | The gear frequencies the housing must not ring at, checked at the 6,000 rpm cruise alone (the engineer, 9 October 01:06); bearing life | Ivanov 2018; the user's 160 km/h top speed |
| **The service life** | 944 h, taken at the drive case | How big the bearings must be | borrowed from Hofstetter 2018 |
| **The layout along the shafts** | the bearing arrangement; 12.7 mm from a bearing to its gear, 6.35 mm behind a bearing in a closed bore, 12.7 mm between two gears on one shaft; 11 mm behind a bearing where its shaft leaves the housing (the input's motor end, both of the output's ends); at least 3 mm along the shafts between parts that overlap end-on, and 8.25 mm from the gear tips to the wall | Where each seat sits along its shaft, how long the shafts are, and how close the wall may come to the gears | assumed, each labelled: Shigley's Fig. 18-2; a radial shaft seal's width; Łódź Ch. 9 (the engineer, 9 October 00:06 and 01:06) |
| **The process and material** | sand casting (proposed); EN AC-42100 T6, E 69 GPa, ν 0.33, 2,600 kg/m³ | What shapes are allowed; how stiff the metal is | Ivanov 2018; the user |
| **The pass criteria** | the housing's 50 % share of the gear tolerances (grade N6); bearing tilt 0.5 / 0.8 / 1.0 mrad; modes at least 3 % from the gear frequencies at the 6,000 rpm cruise; a 25 % model margin (kept, 01:06); least mass | What every design must meet | JGMA, Shigley, Marano 2021 |

**The most binding of all are the gear train and the packaging.** Together they put the six bearing seats where they are, and every design must keep those seats exactly. Next come the torques, which load the seats, and the pass criteria, which judge how far the seats may move.

## 2. First half: from the inputs to a frozen task (the load tool)

| # | Step | Method (source) | Takes in | Gives out | Feeds | State |
|---|---|---|---|---|---|---|
| 1 | **Gear geometry** | Involute geometry (DIN 3960, ISO 21771) | teeth, module, pressure angle, helix, profile shifts | working pressure angles (23.6° and 22.8°); base and working diameters; tip diameters (58.72 / 114.76 and 60.31 / 198.17 mm); working centre distances 82.92 and 125.04 mm | 3, 4, 5, 6, 12 | **built** |
| 2 | **Speeds and gear frequencies** | Through the tooth ratios; teeth × speed / 60 (Shigley) | teeth, the input speeds | ratio 7.1843; shaft speeds 6,000 / 2,941 / 835 rpm at cruise; mesh frequencies 2,500 and 1,127 Hz at cruise | 8, 10, the contract's mesh orders | **built** |
| 3 | **Where the shafts sit** | The triangle of the three axes (law of cosines); circles on different shafts compared end-on | the working centre distances and tip diameters from 1, the 165 mm packaging | 103.1° at the intermediate shaft, so the three shafts' positions in the plane; the parts that overlap seen along the shafts (Ivanov's stage-1 gear and output gear, by 31.4 mm) | 5, 6, 9 | **built** |
| 4 | **Gear forces** | The base-circle form: Fbt = 2T/db, then Ft = Fbt·cos αwt, Fr = Fbt·sin αwt, Fa = Fbt·tan βb, which is Shigley's form at the working pitch circle and pressure angle, extended to profile shift (the engineer, 9 October 00:57; confirmed by drivetrainhub) | the torque in each case; the geometry from 1 | at 150 N·m, stage 1: 5,499 N tangential, 2,399 N radial, 3,243 N axial; stage 2: 11,066, 4,657 and 6,490 N (preview, worked with our geometry code). Directions per case | 6, 7 | planned (GBX-1) |
| 5 | **Layout along each shaft** | A stack of widths and gaps from a datum: the gaps are the inputs, the positions follow (the engineer, 9 Oct 00:06; Shigley §18-4; Łódź Ch. 3; [research](../../research/2026-10-08-bearing-positions.md)) | the face widths; the bearing arrangement; the gaps (12.7 mm bearing to gear, 6.35 mm behind a bearing in a closed bore, 12.7 mm between two gears; assumed from Shigley's Fig. 18-2); 11 mm for a seal behind a bearing on each shaft end that leaves the housing; the least clearances (3 mm along the shafts, 8.25 mm from the tips to the wall); the overlaps from 3; the bearing widths from 8 (a first guess at first) | each gear's and bearing's centre along its shaft, from the datum; every clearance between parts that overlap end-on, calculated and checked against its least value (a layout that breaks one is refused with the pair and the shortfall) | 6, 7, 9, 12 | planned (GBX-2) |
| 6 | **Bearing loads** | Each shaft a beam on its bearings, with the axial force's moment (JTEKT eq. 5-29). For the tapered pair, each bearing's induced axial force is 0.5·Fr/Y (Machine Design 2005; NSK) | the forces from 4; the centres from 5; the working radii from 1; the directions from 3 | the force on each of the six seats in each load case: radial in two planes, and axial | 7, 8, and the judge's loads | planned (GBX-2) |
| 7 | **Shaft sections** | Strength in bending and torsion, and stiffness: deflection and slope at the gears and bearings (Shigley Ch. 7; Łódź Ch. 3) | the torques; the forces from 4; the centres from 5; the reactions from 6; the shaft material (a common gear steel, labelled as an assumption; the engineer, 9 October 00:50) | each shaft's diameter at its seats and gears, and its deflection and slope there | 8 | planned (GBX-3) |
| 8 | **Bearing selection** | The rating life L10 = (C/P)^p with the loads, together with the bore that fits the shaft, the radial and axial capacity and the arrangement (Shigley Ch. 11; Łódź; ISO 281 is the standard) | the seat loads from 6; the speeds from 2; the 944 h at the drive case; the arrangement; the shaft diameters from 7 | each seat's bearing from a maker's public catalogue, cited: its bore, width and outside diameter (ISO 15), and a tapered one's load centre | 9, and back to 5 if a width changed | planned (GBX-3) |
| 9 | **Derive and freeze** | The contract's rules: every derived value stamped with its tool, version and inputs | everything above | the seats (centre, axis, diameter, width, stock); the load cases with their seat forces; the mesh orders. The validator accepts the contract as derived, then it freezes, and its hash becomes the task's name | the second half | planned (GBX-4); freezing is built |
| 10 | **The pass lines in numbers** | The gear tolerance times the housing's share (JGMA 1102-01); tilt by bearing type (Shigley Table 7-2); bands round the gear frequencies (Marano 2021) | the gear sizes and grade N6; the bearing types from 8; the frequencies from 2 at the one check speed, the 6,000 rpm cruise | the µm per face width, the mrad, and the frequency bands every design must meet | the verdict | planned (the judge, PHY) |

**One loop.** Steps 5 to 8 depend on one another:
- the bearings' widths set the layout (5);
- the layout sets the loads (6);
- the loads set the shaft sections (7);
- the loads and the shaft's diameter set the bearings (8), whose widths go back to 5.

So the tool starts from a first guess and goes round until the layout and the selected bearings agree, usually in two or three passes. Shigley's case study says the same: the design is iterative, and the bearings it selected came out close to the widths it guessed.

**What the layout is.** The order of the gears and bearings on each shaft, the bearing arrangement (which bearings take the axial load, and whether the shaft is located at one end and floats at the other or held by an adjusted pair, like Ivanov's tapered pair), and the gaps that leave room for shoulders, retaining rings, the housing wall and a puller, with a seal's room where a shaft leaves the housing. Choosing it is engineering design. Once it is chosen, the coordinates follow from a stack-up, and the clearances follow from the coordinates: they are calculated and checked, never assumed.

## 3. Second half: from a frozen task to a graded design (every campaign step)

| # | Step | Method | Takes in | Gives out | Feeds | State |
|---|---|---|---|---|---|---|
| 11 | **The idea** | The agent's hypothesis: what to change, why, the gain expected, what would prove it wrong | the evidence from the last design (margins, where it is soft), the budget left | a change to try | 12 | planned (AGT-1) |
| 12 | **The geometry** | The machined core in CadQuery, built from the seats (9); the structure grown in field space; the two joined | the seats, the space, the process, the idea; a keep-out round each gear (its tip diameter from 1 plus the least clearance to the wall from 5) | one housing | 13 | planned (GEO-1) |
| 13 | **Castability** | The process's rules: walls, draft, no undercuts | the housing, the process | pass, or where it breaks the rules | 14, or back to 11 | planned (PRC) |
| 14 | **Statics** | FE under each load case, with the seat forces from 6 applied | the meshed housing, the load cases | how far each seat moves and tilts; each mesh's misalignment | 16 | planned (PHY-1) |
| 15 | **Modes** | FE eigenvalues | the meshed housing, the material | the natural frequencies and mode shapes | 16 | planned (PHY-3) |
| 16 | **The verdict** | Each result against its pass line from 10, with the 25 % model margin | 14, 15, and the mass | pass or fail; the worst margin; the mass; the rung | 11 (the next step); the data | planned (PHY) |
| 17 | **The record** | Each step kept with what was seen, tried, made and graded | 11-16 | datapoints (graded designs, decisions) and tasks cut from them | the Data tab, and learning | planned (DAT-1) |

## 4. The chain on one line

```
inputs ─▶ 1 geometry ─▶ 2 speeds & frequencies ─┐
       └▶ 3 where the shafts sit ───────────────┤
          4 gear forces ─▶ 5 layout ⇄ 6 bearing loads ⇄ 7 shaft sections ⇄ 8 bearing selection
                                         └──────▶ 9 derived & frozen task ─▶ 10 pass lines
   every campaign step: 11 idea ─▶ 12 geometry ─▶ 13 castability ─▶ 14 statics + 15 modes
                                  ─▶ 16 verdict ─▶ 17 the record ─▶ back to 11
```

**How each step is trusted.**
- The built steps are checked against published numbers once, in `checks/`: Kim's and Ivanov's centre distances, their ratios. A contract carries no paper figure for a calculated value (the engineer, 8 October 23:37).
- The load tool is checked in four ways: against Shigley's, Łódź's and the textbook example's worked answers; by exact invariants (force × radius gives back the torque, and every shaft balances); by an independent FE beam; and by injected faults. See the [load tool's plan](../gearbox/2026-10-08-load-tool-plan.md).
- The judge is verified on its own reference cases before it judges anything.
