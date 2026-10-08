# The first loop, start to end

One housing taken all the way, once: from the completed contract to a plain shell and wall, topology optimisation, ribs, the CAD joined, meshed, coupled, loaded, solved and graded against the contract. It is a prototype (`prototypes/first_loop/`), built to learn what the product's tools must be and where the agent's judgement belongs, before any agent is built (the engineer, 9 October 01:54).

**PBI key:** LOP · **State:** LOP-1 to LOP-6 done: one loop complete, start to end, in three rounds (16 designs, 19 FE judgements, 3 optimisations). Nothing passes as the contract stands. The best under the reference housing's 7.73 kg is the lobed shell with 10 mm end walls: 7.49 kg, its worst seat 3.4 times its line against its shaft (2.4 by the seat's own rotation), confirmed on a 6 mm mesh. The write-up: [what the first loop teaches](2026-10-09-first-loop-what-it-teaches.md). Next: LOP-7, after the engineer's answers · **Updated:** 2026-10-09 04:45 by Claude
**Code:** `prototypes/first_loop/` (a prototype: nothing in `src/` imports it; its outputs go to `data/first_loop/`, which git ignores)

## Now

Nothing in Now, and no run is going. LOP-7 waits on the engineer's answers (Open).

## Next

| PBI | Goal | Done when |
|---|---|---|
| LOP-7 | The second round, after the engineer's answers on the helix hands, the tapered seats' line and the misalignment budget: ribs on the side walls and gussets between the lobes, read from the field; a local optimisation cycle round the binding seats | A graded design per lever, against `lobed_e10` |

After the loop, its tools go into the product, each in its own feature when its first PBI starts: the shell and wall and the design space (Geometry, GEO), the FE judge (Physics, PHY-1), the optimiser and the reader (Optimise, OPT).

## What runs

- **The plain housing** (`shell.py`, LOP-1), from the completed contract's round (the layout, the selected bearings) and its volumes:
  - walls of 6 mm round the gears' cavity (the hull of every gear and the differential grown by A19), with a sump 26 mm under the output gear;
  - flat end walls, and a boss round each bearing from its seat to its end wall, with the seat and a 3 mm shoulder;
  - seal bores where a shaft leaves (A17);
  - two halves split across the shafts at z = 14.35 mm, midway between the stages, each with an M8 flange lip (Łódź Table 9.1: 24 mm wide, 9 mm thick per half) and 11 bolts;
  - three mount bosses on the motor-side half (A20) and the motor flange's ring round the input (A25);
  - every face named by its role from the exact geometry: seats, bolts, mounts, motor bolts, the split face, walls. STEP and BREP per half, with the face names, in `data/first_loop/`.
- **The lobed housing** (`lobed.py`): one pod per shaft (the hull of that shaft's gear keep-outs and bosses, grown by the wall), each spanning its own shaft's length, so the end walls step; the flange lip round the pods' union; the motor's flange as a round plate on the input's pod. Settings by override (`end_wall`, `boss`, …); ribs on a pod's end faces; the mounts' half by override.
- **The FE judgement** (`fe.py`, LOP-2), the engineer's practice:
  - each half meshed by gmsh (TET4, then straight-sided TET10, as fastcae does);
  - each bearing's force spread over its whole seat (RBE3, uniform weights), or by the plan's cosine over the loaded half (D6a) with `LOOP_LOADS=cosine`;
  - the mounts held, and the halves tied at each bolt (at one point on the split plane), by distributing couplings: a stiff penalty on the coupled nodes' RBE3 reference motion;
  - the motor's reaction torque on its flange's bolt holes;
  - fastcae-v1's TET10 stiffness and cuDSS solve, copied verbatim (`fastcae_fe.py`); the double factor where the single one does not refine past the penalties;
  - the read-out: each seat's displacement and its rotation (its nodes' best-fit rigid motion), each shaft's line, the mounts' reactions against the loads, the mass, and the first 12 modes (Lanczos on a cuDSS factor, lumped HRZ mass) against the mesh frequencies at 6,000 rpm.
- **The optimisation** (`topo.py`, LOP-3): voxel SIMP in the packaging space outside the frozen shell:
  - a voxel is wall where any of its corners is inside the wall, so thin walls stay whole;
  - hexahedra, a density filter of 1.5 voxels, optimality criteria with a move limit of 0.2, cuDSS each iteration;
  - the objective is a choice: compliance, or the seats' tilt over their lines (a p-norm, p = 6, its gradient by an adjoint on the same factor);
  - a budget in kg; 40 iterations.
- **The reading** (`read.py`): a fan of straight candidate paths, scored by the material under them; or the field's skeleton, each rib as wide as its band. The heights come from the material over each end face, stepped faces included.
- **A designer's hypothesis** (`hypothesis.py`): radial ribs round chosen shafts' bosses, for a hunch to be judged like any reading.
- **The grade** (`grade.py`): every FE result against the contract's lines, to `grades.json` and a table.
- **What-ifs:** `LOOP_CONTRACT` names a variant contract, which every script then reads; for example `data/first_loop/whatif_same_hand.json`, stage 2's pinion right-handed.
- **Pictures:** `picture.py` (the halves by face role), `deformed.py` (the displacement on the deformed halves), and a PNG per optimisation and reading.

## Rules in force

- The pass lines are the contract's:
  - the bearing tilt limits with the 25 % model margin, applied as FE value ≤ 0.75 × limit (tapered 0.375, cylindrical 0.6, ball 0.75 mrad);
  - modes at least 3 % from the mesh frequencies at the rated 6,000 rpm (2,500 and 1,127 Hz);
  - least mass among passing designs.

  The design to beat is the example's reference housing: 7.73 kg, its bearing beds displaced at most 52 µm forward and 138 µm in reverse.
- A difference inside the measured mesh noise (1-2 %, below) is a tie. The 8 mm mesh ranks designs.
- The voxel optimisation ranks; only the CAD, meshed and solved, judges.
- Every design's settings and results are kept: `data/first_loop/<stem>.json` (the CAD's) and `fe_<stem>.json` (the judgement's).
- **The machine:**
  - one heavy job at a time;
  - the GPU kept at most about 6 GB of its 8 (checked with `nvidia-smi` first);
  - at least 4 GB of RAM free before a mesh or a solve;
  - meshes well under the card's ceiling of about 412,667 TET10;
  - VS Code must stay open (the engineer, 9 October 02:12).

## Measured

All on 9 October, LAPTOP-IR8VEG53, 8 mm meshes unless noted. "Own" is the worst seat's rotation over its line. "Shaft" is the worst seat's tilt relative to its shaft's line over its line: the housing's share of what the bearing sees (LOP-6).

| Round | Design | What it is | kg | Drive µm | Reverse µm | Own | Shaft | Orders |
|---|---|---|---|---|---|---|---|---|
| 0 | `shell` (6 mm) | the plain convex shell | 7.23 | 246 | 366 | 8.80 | 11.10 | clash |
| 1 | `ribs_fan` | + ribs from the 1 kg compliance optimisation, read as a fan | 7.68 | 192 | 253 | 4.10 | 5.90 | clear |
| 1 | `ribs_skel` | + the same field read by its skeleton | 7.63 | 223 | 189 | 5.16 | 6.57 | clash |
| 2 | `end10` | end walls 10 mm | 8.06 | 132 | 176 | 3.54 | 4.59 | clear |
| 2 | `fan_tall` | the fan's ribs twice as tall | 8.14 | 170 | 197 | 3.33 | 5.17 | clear |
| 2 | `ribs2_fan` | + ribs from the 2 kg optimisation, fan | 8.16 | 138 | 201 | 3.12 | 4.79 | clear |
| 2 | `ribs2_skel` | + the 2 kg field, skeleton | 8.05 | 163 | 182 | 5.49 | 6.62 | clash |
| 2 | `end10_fan` | end walls 10 mm + the fan | 8.52 | 118 | 152 | 2.62 | 3.73 | clear |
| 2 | `lobed` | the lobed form, plain | 6.66 | 218 | 323 | 4.45 | 5.92 | clear |
| 2 | `lobed_e10` | lobed, end walls 10 mm | 7.49 | 106 | 156 | 2.42 | 3.36 | clash |
| 2 | `lobed_e10_b12` | lobed, end walls 10 mm, bosses 12 mm | 8.04 | 95 | 130 | 2.01 | 2.88 | clash |
| 3 | `lobed_tilt1` | lobed + ribs from the 1 kg tilt optimisation, skeleton | 6.99 | 207 | 300 | 3.95 | 5.54 | clear |
| 3 | `lobed_e10_tilt1` | lobed, end walls 10 mm + the tilt ribs | 7.83 | 97 | 143 | 2.05 | 2.99 | clash |
| 3 | `hyp_e6` | lobed + radial ribs round the intermediate's bosses | 6.75 | 215 | 321 | 4.00 | 5.13 | clear |
| 3 | `hyp_e10` | the same on 10 mm end walls | 7.58 | 106 | 155 | 2.35 | 3.29 | clash |
| 3 | `mounts_cover_e10` | `lobed_e10`, the third mount on the cover | 7.49 | 112 | 147 | 2.74 | 3.42 | clash |
| 3 | `lobed_e10_cosine` | `lobed_e10`, the seats loaded by the cosine (D6a) | 7.49 | 98 | 134 | 2.34 | 3.28 | clash |
| 3 | `whatif_hand_e10` | `lobed_e10`'s form and settings on a what-if contract (stage 2's pinion right-handed), with that contract's own bearings | 7.50 | 121 | 134 | 1.65 | 2.77 | clash |
| 3 | `lobed_e10_m6` | `lobed_e10` on a 6 mm mesh | 7.49 | 107 | 158 | 2.44 | 3.36 | clash |

- **The plain housing** (6 mm, 854,424 unknowns, 61 s): its flat end walls bend like plates (`fe_shell.png`). A mode at 1,114 Hz sits within 3 % of stage 2's 1,127 Hz, as the reference housing's own first mode did. Equilibrium holds on every solve: the mounts react (0, 0, 1,077.7) N·m against the loads' (0, 0, −1,077.7), the output's torque.
- **The mesh noise:** 8 mm against 6 mm, on the plain shell: 1.5 % and 0.9 % in the worst displacements, 0.8 % in tilt; on `lobed_e10`: 106/156 against 107/158 µm, 2.42 against 2.44. Ties.
- **The binding seats of `lobed_e10`** (shaft-relative tilt over its line):
  - the intermediate's tapered pair: 3.36 (−z, drive), 3.09 (+z, reverse), 2.91 (−z, reverse);
  - the output's +z ball: 2.16 (drive);
  - the input's +z roller: 2.08 (drive);
  - the output's −z ball: 1.71 (reverse).

  The seat's own rotation understates the misalignment: in every judgement the worst seat reads 21-68 % worse against its shaft, because at most seats the seats' displacements tilt the shaft's line against the seat's own rotation. The ranking barely moves: the first seven designs keep their order.
- **The optimisations** (40 iterations each, about 5 s per iteration). None converged: the last iteration still changed a density by 0.10-0.20, against the move limit of 0.2.

  | Run | Shell | Objective | Budget | Voxel | Unknowns | s | Start → end (voxel model) |
  |---|---|---|---|---|---|---|---|
  | `topo_1kg_6mm` | convex | compliance | 1 kg | 6 mm | 255,636 | 205 | compliance 7,744 → 3,789; worst seat 219 → 122 µm |
  | `topo_2kg_6mm` | convex | compliance | 2 kg | 6 mm | 255,636 | 206 | 7,632 → 2,531; 214 → 44 µm |
  | `topo_lobed_tilt_1kg_6mm` | lobed | the seats' tilt | 1 kg | 6 mm | 270,147 | 244 | objective 1.01 → 0.44; worst seat's own tilt 0.98 → 0.38 of its line |

  **The voxel model is 4.5-8 times too stiff in tilt.** The plain lobed shell reads 0.98 of its line with 6 mm voxels and 0.53 with 8 mm; the CAD's FE reads 4.45. The tilt optimisation's 61 % gain in the voxel model became 11 % in the CAD (`lobed` 4.45 → `lobed_tilt1` 3.95). Its ribs as read held 0.33 kg of the 1 kg, and its side-wall material had no reader.
- **What the night measured**, in short (the write-up has the reasoning):
  - the lobed form halves the convex form's tilt with 0.57 kg less;
  - thicker end walls pay on either form;
  - the compliance objective aims at the output, while the contract binds at the intermediate;
  - the helix hand is a lever of the inputs: −32 % in the seat's own rotation, −18 % against the shaft;
  - the cosine load and the whole-seat coupling differ by 3 % in tilt;
  - the third mount on the cover does not help the tilt (+13 % own, +2 % against the shaft), though it lifts the first mode from 869 to 994 Hz;
  - a designer's radial ribs round the intermediate's bosses gave 10-13 % on 6 mm end walls and 2-3 % on 10 mm.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| One loop, start to end, before the agent | Complete the whole flow once in a prototype; learn from it how the agent should work and where its judgement belongs. Do not build the agent yet | 2026-10-09 01:54, the engineer |
| The two halves split across the shafts | One plane square to the shafts; each shaft has a bearing in each half | 2026-10-09 02:12, the engineer |
| Supports and joints | The mount bosses held fixed through distributing couplings; the halves joined at each bolt by distributing couplings; each bearing's loads through a distributing coupling over its whole seat (Physics) | 2026-10-09 02:12-02:15, the engineer |
| The mounts are an input | Their positions come from the vehicle (its mounting system's hardpoints) and are given in the contract. The example gives none, so three are assumed and labelled | 2026-10-09 02:16, the engineer |

## Open

- **Which tilt the contract's limit applies to.** The limits are Shigley's ranges for a bearing's misalignment: the angle between the shaft and the bearing's seat. The housing's share is the seat's tilt against its shaft's line, which the grade takes from LOP-6 on. The shaft's own bending slope adds to it. The completed contract sizes each shaft so that slope alone is within the limit, and the slopes use 4 % (input), 27-30 % (intermediate) and 20-24 % (output) of their limits. How the one limit is shared between the shaft and the housing is the engineer's to set (Physics).
- **For the engineer, from the loop:**
  - stage 2's helix hand (the what-if's effect above);
  - the tapered seats' line at the lower end of Shigley's 0.5-1.2 mrad;
  - the margin applied as 0.75 × the limit.
- **The mounts and the motor flange are placed by the prototype** (A20, A25): three bosses on the motor-side half, the flange's ring round the input. They go into the contract as inputs.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|
| LOP-6 | The tilt a bearing sees: `grade.py` grades each seat's tilt against its shaft's line and prints the seat's own rotation beside it; every design 21-68 % worse, the ranking kept | 2026-10-09 | this commit |
| LOP-5 | [What the first loop teaches](2026-10-09-first-loop-what-it-teaches.md): the iterations, what worked, the tools the product needs, where the agent's judgement belongs, what would open the space | 2026-10-09 | this commit |
| LOP-4 | Ribs read from the fields and built into the CAD, judged again; three rounds, 16 designs, 19 judgements; nothing passes as the contract stands | 2026-10-09 | e524ea9, this commit |
| LOP-3 | Three optimisations over the whole design space: compliance at 1 and 2 kg, the seats' tilt at 1 kg (by an adjoint); the local cycle moves to LOP-7 | 2026-10-09 | e524ea9, this commit |
| LOP-2 | The plain housing judged by FE, the engineer's practice: the measures above | 2026-10-09 | 7ca5e28, c7fbd59 |
| LOP-1 | The plain shell and wall in two halves, 7.23 kg, every face named | 2026-10-09 | 7ca5e28 |

## Docs

- [What the first loop teaches](2026-10-09-first-loop-what-it-teaches.md): the iterations, what worked, the tools the product needs, where the agent's judgement belongs.
- The engineer's brief of 9 October 01:54 is this page's Decisions and Next.
- The reviews it rests on: [the spaces inside a reducer](../../research/2026-10-09-spaces-inside-a-reducer.md); [how housing topology optimisation is done](../../research/2026-10-09-housing-topology-optimisation-practice.md); [fastcae's code, mapped for the loop](../../research/2026-10-09-fastcae-code-map-for-the-loop.md).
