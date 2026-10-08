# Plan: the Ivanov 2018 contract (CON-3)

**Date.** 8 October 2026, 19:31. Asked for by the engineer at 19:26: "a plan using all the information we have … to finalise the contract with Ivanov as the base paper and other information from the best available sources."

**Status.** Nothing is built.

**Decided at 19:37 (the engineer):**
- Ivanov is the first contract.
- The maximum input speed comes from a 160 km/h top speed (B3).
- Hofstetter's bearing arrangement (B7) and 944 h life (B4) are borrowed, labelled.

**Decided at 19:43 (the engineer):**
- **Packaging is the user's input.** The input-output offset replaces assumption B9 (see the interfaces table), and each packaging choice is its own contract.
- **The originals cannot be had,** so the contract is written from the copy read: step 2 below is dropped.
- **The product's decisions are being rethought,** so the process is chosen afresh (§2, Manufacturing), with an attractive end result as an aim.

**Still open:** the process, and the first packaging.

**The sources** are read in [the round-2 research note](../../research/2026-10-08-housing-sources-round-2.md).

---

## 1. The idea

- **The base: Ivanov 2018**, a KTH master's thesis commissioned by AVL. It gives a real EV reducer's gear train and duty, and a published housing to compete with.
- **The rest from the best available source, each value labelled** with its provenance: Hofstetter 2018, our standards (Shigley, JGMA, Marano, NADCA), and the Łódź handbook's method for the bearings.
- **What stays out of the contract:** Łódź's housing rules (walls, bosses, flanges, bolts). They are an answer, so they build the rival design (§5), never the contract.

**Why this contract is a strong one.** The published design has a documented vibration defect.
- Its first free mode is 1,127 Hz.
- At the 6,000 rpm cruise, stage 2's gear-mesh frequency is 23 × (6,000 × 25/51) / 60 = 1,127.5 Hz.
- The thesis notes the coincidence itself ("the 1st mode frequency coincides with a force 1x component … there will be a need to redesign").
- Our order-separation limit (3 %) fails that design. So the task reads plainly: carry the gears and loads, and do not ring at cruise, with less metal than 7.7 kg.

## 2. Entry by entry: where each value comes from

**Provenance:** pub = published in Ivanov unless named; std = a standard or guideline; asm = an assumption, listed for the engineer; der = computed by a tool.

### Requirement (gear-train style)

| Entry | Value | Source | Kind |
|---|---|---|---|
| Total ratio | 7.184 | Ivanov §3.2; (51/25)·(81/23) = 7.1843 checks | pub |
| Ratio tolerance | 0.1 % | ours | asm B1 |
| Peak drive torque, input | 150 N·m | Ivanov §3.3.2 (AVL's maximum transfer; the motor curve reaches 165 N·m) | pub |
| Reverse torque, input | 150 N·m at 2,000 rpm | Ivanov §3.4 (its KISSsoft case) | pub |
| Regeneration torque, input | 150 N·m | as drive, the same rule as Hofstetter's A1 | asm B2 |
| Cruise speed, input | 6,000 rpm (110 km/h on a 245/45 R19 tyre) | Ivanov §3.3.1 | pub |
| Maximum speed, input | from a top speed the engineer chooses: 160 km/h gives about 8,670 rpm on the same tyre | ours | asm B3 |
| Service life | 944 h | borrowed from Hofstetter 2018 Table 2, a similar passenger-EV reducer; Ivanov gives none | asm B4 |
| Gear material | SS 2511 (pinions); stage 2's wheel reads "Casted Iron" | Ivanov Figs. 24-25; confirm in the original | pub |
| Gear quality | N6 (JGMA) | none published; as Hofstetter's A2 | asm B5 |
| Stage 1 | 25/51 teeth; mn 1.85 mm; αn 18°; β 30°; hands left/right; x 0.43672 / 0.57199922; b 16.5 / 15.5 mm; a 83 mm | Ivanov Fig. 24 | pub; β recovered, see below |
| Stage 2 | 23/81 teeth; mn 2.05 mm; αn 18°; β 30°; hands left/right; x 0.431143 / 0.56857692; b 25.625 / 22.25 mm; a 125 mm | Ivanov Fig. 25 | pub, with β as asm B6 |
| The six bearings: types | input: deep-groove ball + cylindrical roller; intermediate: a tapered pair; output: a deep-groove ball pair | Hofstetter 2018's arrangement, borrowed as a pattern | asm B7 |
| The six bearings: sizes | chosen by life from the loads: Łódź Ch. 4-5 (ball bearings) and the standard L10 method for rollers, then ISO 15 dimensions | to do (§3, step 3) | asm B7, until GBX-1 derives them |
| Installation space | the gears' envelope plus 20 mm | as Hofstetter's A3 | asm B8 |

**The helix angles.**
- The copy read garbles both cells: stage 1 reads "30 mm", stage 2 reads "0000".
- Our involute geometry recovers them from the published teeth, module, pressure angle, profile shifts and centre distances: 30.10° and 29.97°.
- At exactly 30° the stages run at 82.917 mm and 125.037 mm, inside the validator's 0.1 mm tolerance.
- So the contract writes 30° for both: stage 1 as published (its "30" is legible), stage 2 as an assumption (B6) until the original confirms it.

### Interfaces (the derived stage: computed by GBX-1, the load tool)

| Entry | Source | Kind |
|---|---|---|
| The three shafts' positions in the plane | **The engineer's packaging input** (decided 19:43): the input-output offset. It enters the requirement as `input_output_offset`, with provenance engineer. With 83 and 125 mm it fixes the angle at the intermediate shaft: offset² = 83² + 125² − 2·83·125·cos θ. The gears only bound it: the input shaft must clear the output wheel (tip radius 99.1 mm), so the offset is at least about 125 mm; at most 208 mm (all in line). **Proposed variants, each its own contract:**<br>- about 130 mm, compact (θ ≈ 74°);<br>- **165 mm, Hofstetter's published EV offset (θ ≈ 103°), proposed first;**<br>- 208 mm, in line (θ = 180°).<br>Which side of the line the intermediate shaft sits on is a further choice, taken by default as above the line | engineer (was B9) |
| The spacing along each shaft | face widths (published) + bearing widths + gaps; the layout method of Łódź Ch. 3 and Shigley §18-4 | der, with the gaps asm B10 |
| Bearing seats: diameter, width, stock | from the bearings chosen; stock 0.25 mm (NADCA) | der |
| Split faces | Ivanov §3.1: three parts (the flange, the motor side, the back side), so two split planes | pub (the count); asm B11 (where they sit) |
| Mount pads | Ivanov: the frame's mounting bosses, fixed in his FE; their number and positions are not given | asm B12 |
| Motor flange | Ivanov §3.5: the motor sits on the flange alone, and the flange carries its 150 N·m reaction | pub (the role); asm B13 (spigot, bolt circle) |
| Ports | Ivanov §3.1: oil inlet and outlet on the back side | pub (where); asm B14 (sizes) |

### Physics (the derived stage: computed by GBX-1, never typed)

- **Load cases:**
  - drive, 150 N·m at 6,000 rpm (Ivanov's abusive forward case);
  - reverse, 150 N·m at 2,000 rpm;
  - regeneration (B2);
  - the motor's 150 N·m reaction on the flange.
- **The seat loads** come from the helical gear forces: Ft = 2T/d, Fr = Ft·tan αn / cos β, Fa = Ft·tan β (Ivanov §2.2, Shigley Ch. 13). Then two-support statics with the axial force's moment, from the layout.
- **Mesh orders** come from the teeth: 25 on the input; 23 × 25/51 = 11.27 on the intermediate.
- **A check of GBX-1:** Shigley Ch. 18's worked numbers, as the answer key. Brauer 2017's or Ivanov's simulated bearing forces too, if the originals tabulate them.

### Limits (ours, from standards: the same as the Hofstetter contract)

| Entry | Value | Source |
|---|---|---|
| The housing's share of each gear tolerance | 50 % | A6 rule (asm B15) |
| Bearing tilt | 0.5 / 0.8 / 1.0 mrad (tapered / cylindrical / ball) | Shigley Table 7-2, lower end |
| Order separation | 3 % | Marano et al. 2021 |
| Order-check speeds | 6,000 rpm (cruise) and the maximum (B3) | asm B16 |
| Model margin | 25 % | as the spec (§4.5) |
| Objective | least mass | - |
| Stress | recorded, not judged. Ivanov used the alloy's yield, 230 MPa, as his line | open: the safety factor is the engineer's |

### Manufacturing: the process, chosen afresh

The product's decisions are being rethought (the engineer, 19:43), so the choice does not lean on D3. It is judged on three things: how attractive the end result can be, a fair comparison with the published design, and the sources we have.

| | Sand casting, with 3D-printed sand moulds and cores | Metal printing (LPBF, AlSi10Mg) | High-pressure die casting |
|---|---|---|---|
| **How attractive the result can be** | High: cores allow hollow and organic members; printed moulds lift most draft limits | Highest: free organic shapes, lattices, thin members. Porsche printed an e-drive housing whose honeycomb stiffened and damped the walls (fastcae AM report) | Lowest: thin, even walls that all pull straight out of a steel die, so it looks like a ribbed shell |
| **Fair against Ivanov's 7.7 kg** | **Yes:** his housing is sand-cast EN AC-42100 T6 | No | No |
| **Where it is used** | Prototypes and small series of real housings | Prototypes, motorsport, small series | Mass production; die casting wins by a wide margin at e-drive volumes (fastcae AM report) |
| **Material** | Ivanov's AC-42100 T6: E 69 GPa, ν 0.33, yield 230 MPa, UTS 290 MPa (Rm ≥ 230 MPa, ROTH, in fastcae's AM report) | AlSi10Mg (fastcae AM report) | A die-casting alloy (a sourced card still to choose) |
| **Rules we have** | Tolerances from 0.76 mm (fastcae AM report). **The printed-mould design rules still need a public source:** least wall, junctions, core support, sand removal | Walls, overhangs, powder escape, NASA's risk score and rungs (fastcae AM report) | NADCA: drafts 2° / 1°, 0.25 mm stock; our 4 mm least wall (D7, the FE budget) |
| **Caveats** | Thicker walls than die casting; rougher surfaces; the rules research | Costly per part; build size; supports and powder removal; qualification | Looks conventional; not like for like |

**Proposed: sand casting.**
- It is the only one that is both attractive and a fair fight with the published design.
- The same contract can later be run in die casting and in printing. That makes a process set: counterfactual pairs that change one requirement each.
- Before the contract is written, the printed-mould rules need their source (a short research task).

### References: the plausibility band (from Ivanov; never limits)

- **Mass:** 7.732 kg (three sand-cast parts; CAD, at 2.6 g/cm³).
- **Free modes of the initial design:** the first elastic mode at 1,127 Hz, on stage 2's mesh frequency at cruise; mode 13 at 2,851 Hz; mode 16 at 3,159 Hz. With the ribs removed: 1,189 and 1,337 Hz.
  - Caveat: his three parts are bonded together, so his modes read high, as he says.
- **Displacement of the bearing beds' centres** (his Fig. 51; artificial peak combinations):
  - forward: 0.0384, 0.0079, 0.0349, 0.0085, 0.0111, 0.0522 mm (slots 1-6);
  - reverse: 0.1076, 0.1236, 0.0672, 0.110, 0.0219, 0.1380 mm.
- **Stress:** far below 230 MPa, but for one singular element.

## 3. The steps

1. **The engineer decides** (§4).
2. **Dropped at 19:43: the originals cannot be had.** This step stays only as a record of what they would have checked. **Get the originals.**
   - What: Ivanov's thesis from KTH's DiVA, Brauer 2017 ("High Speed Electric Vehicle Transmission", Karlstad University) from Karlstad's DiVA, and Nilsson 2013 (Chalmers), Ivanov's source for the motor curve.
   - Who: DiVA refuses connections from Claude's session, so the engineer downloads them into `Downloads`, as with the KIT dataset. They stay out of git.
   - Then re-read: the helix angles, the gear materials, the bearings, the figures of the layout (the stage angle, the bearing slots, the mounts), and any tabulated bearing forces.
3. **Write the posed contract** (CON-3), `ivanov2018_posed.json`, through `make_examples.py`.
   - Every value carries its source, and the assumptions B1-B16 are listed with their reasons.
   - The bearing sizes come from a documented life calculation on hand-computed seat loads, until GBX-1 derives them.
   - Done when the validator accepts it, the example checks pass, and the snapshot and the UI show it.
4. **Derive it with GBX-1** (the load tool, P1): the layout and the seats, the seat loads per case, the mesh orders.
   - GBX-1 is checked first against Shigley Ch. 18's numbers, the published worked examples, an independent FE cross-check and fault injection, as planned.
5. **Freeze it.** The hash names the task, and campaigns can start.
6. **Build the rival design** (a separate PBI, for the benchmark): Łódź Ch. 9's rules, adapted.
   - The adaptations: two stages (each wall sized from its own centre distance), helical gears, and an aluminium wall floor set to the contract's least wall.

**Effort.** Step 3 takes about half a day, as Hofstetter's did. Step 4 waits for GBX-1, in P1.

## 4. Decisions for the engineer

1. **Make Ivanov 2018 the first contract,** in place of Hofstetter (decision 11)? Hofstetter stays as the second.
2. **The process:** A, die casting (recommended), or B, sand casting.
3. **The top speed** for the maximum input speed (B3): 160 km/h gives about 8,670 rpm.
4. **The borrowed values:** Hofstetter's bearing arrangement (B7) and its 944 h life (B4).
5. **Mixing sources:** accept that the contract mixes sources, each labelled. Such a contract describes Ivanov's gearbox, with gaps filled. It is not a claim about AVL's actual housing.

## 5. Caveats

- **The layout angle (B9)** is not a published number. If neither original gives it, our seats will differ from AVL's, and comparing against his 7.7 kg assumes his layout.
- **The bearings (B7)** are our selection unless Brauer 2017 names AVL's.
- **The thesis is a student's,** with AVL's data passed through. The copy read is a Scribd upload. Treat it with moderate confidence until checked against the KTH original.
- **His FE bonds the three parts and the bearing rings** (TIE constraints). His stiffness and modes read high, so his band is optimistic.
- **Łódź's rules suit a simpler gearbox:** one stage, belt-driven, sand-cast iron. The rival design needs the adaptations of step 6, and those adaptations are ours.
