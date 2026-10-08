# The first loop, start to end

One housing taken all the way, once: from the completed contract to a plain shell and wall, topology optimisation, ribs, the CAD joined, meshed, coupled, loaded, solved and graded against the contract. It is a prototype (`prototypes/first_loop/`), built to learn what the product's tools must be and where the agent's judgement belongs, before any agent is built (the engineer, 9 October 01:54).

**PBI key:** LOP · **State:** LOP-1 and LOP-2 done; LOP-3 (topology optimisation) and LOP-4 (ribs) in their second iteration: 11 designs judged. The best under the reference housing's 7.73 kg is the lobed shell with 10 mm end walls (7.49 kg, the worst tilt 2.4 times its line); nothing passes yet. Next: the optimisation aimed at the seats' tilt · **Updated:** 2026-10-09 04:08 by Claude
**Code:** `prototypes/first_loop/` (a prototype: nothing in `src/` imports it; its outputs go to `data/first_loop/`, which git ignores)

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| LOP-3 | Topology optimisation in the design space: on the whole space first, then on sub-spaces at the weak places; every iteration's settings and result kept | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-09 03:40 | Starting: a voxel SIMP over the design space outside the frozen shell, the seats loaded and the mounts held as in LOP-2 |

## Next

| PBI | Goal | Done when |
|---|---|---|
| LOP-4 | Ribs from the optimisation's result, joined to the shell; meshed, solved and graded again; iterated until the contract is met or the budget ends | A graded design and the record of its iterations |
| LOP-5 | What the loop teaches: how many iterations, what changed, which strategies worked; the tools the product needs and where the agent's judgement belongs | The write-up in this folder, and the next PBIs on the board |

## What runs

- **The plain housing** (`shell.py`, LOP-1): from the completed contract's round (the layout, the selected bearings) and its volumes:
  - walls of 6 mm round the gears' cavity (the hull of every gear and the differential grown by A19), with a sump 26 mm under the output gear;
  - end walls, and a boss round each bearing from its seat to its end wall, with the seat and a 3 mm shoulder;
  - seal bores where a shaft leaves (A17);
  - two halves split across the shafts at z = 14.35 mm, midway between the stages, each with an M8 flange lip (Łódź Table 9.1: 24 mm wide, 9 mm thick per half) and 11 bolts;
  - three mount bosses on the motor-side half (A20) and the motor flange's ring round the input (A25);
  - every face named by its role from the exact geometry: seats, bolts, mounts, motor bolts, the split face, walls. STEP and BREP per half, with the face names, in `data/first_loop/`.
- **The FE judgement** (`fe.py`, LOP-2), the engineer's practice:
  - each half meshed by gmsh (TET4, then straight-sided TET10, as fastcae does);
  - each bearing's force spread over its whole seat (RBE3, uniform weights);
  - the mounts held, and the halves tied at each bolt (at one point on the split plane), by distributing couplings: a stiff penalty on the coupled nodes' RBE3 reference motion;
  - the motor's reaction torque on its flange's bolt holes;
  - fastcae-v1's TET10 stiffness and cuDSS solve, copied verbatim (`fastcae_fe.py`); the double factor where the single one does not refine past the penalties;
  - the read-out: each seat's displacement and tilt (its nodes' best-fit rigid motion), each shaft's tilt, the mounts' reactions against the loads, the mass, and the first 12 modes (Lanczos on a cuDSS factor, lumped HRZ mass) against the mesh frequencies at 6,000 rpm.
- **Pictures:** `picture.py` (the halves by face role), `deformed.py` (the displacement on the deformed halves).

## Rules in force

- The pass lines are the contract's: the bearing tilt limits with the 25 % model margin (tapered 0.375, cylindrical 0.6, ball 0.75 mrad); modes at least 3 % from the mesh frequencies at the rated 6,000 rpm (2,500 and 1,127 Hz); least mass among passing designs. The design to beat is the example's reference housing: 7.73 kg, its bearing beds displaced at most 52 µm forward and 138 µm in reverse.
- A difference inside the measured mesh noise (about 1-2 %, below) is a tie.
- **The machine:** one heavy job at a time; the GPU kept at most about 6 GB of its 8 (checked with `nvidia-smi` first); at least 4 GB of RAM free before a mesh or a solve; meshes well under the card's ceiling of about 412,667 TET10. VS Code must stay open (the engineer, 9 October 02:12).

## Measured

- **The plain housing, 6 mm mesh** (9 October 03:38, LAPTOP-IR8VEG53; 854,424 unknowns; 61 s): 7.23 kg.
  - Peak drive: the worst seat output −z, 246 µm; the worst tilt output +z, 3.72 mrad. Peak reverse: output +z 366 µm; intermediate −z 3.30 mrad. Every seat's tilt is 2-10 times its limit.
  - The flat end walls bend like plates: the cover's +z wall bulges round the intermediate's and the output's seats (`data/first_loop/fe_shell.png`).
  - Modes 838, 934, 993, 1,114, 1,300 … Hz: **1,114 Hz sits within 3 % of stage 2's 1,127 Hz**, as the reference housing's own first mode did.
  - Equilibrium: the mounts react (0, 0, 1,077.7) N·m against the loads' (0, 0, −1,077.7): the output's torque, as it must be, and no stray moment.
- **Iteration 1: the 1 kg optimisation, read two ways** (9 October 03:44-03:51, 8 mm meshes):
  - The optimisation (`topo.py 1.0 6 40`: 6 mm voxels, 207 s, compliance −28 %) put its metal in a frame round the output's +z boss on the cover and a crescent beside the intermediate's −z boss on the motor side (`topo_1kg_6mm.png`).
  - Reading A, a fan (`read.py`: straight paths between bosses and mounts and radial every 15°, scored by the material under them): 23 ribs, 7.68 kg: drive 192 µm, reverse 253 µm, the worst tilt 4.1 times its line, the order clash gone.
  - Reading B, the skeleton (the material's skeleton, each rib as wide as the band under it): 17 ribs, 7.63 kg: drive 223 µm, reverse 189 µm, the worst tilt 5.2 times its line; still a clash at 1,136 Hz.
  - So 0.4 kg of end-wall ribs halves the worst tilt, and the reading matters as much as the optimisation: the two readings of one field differ by 25 % in tilt and 34 % in reverse. Neither nears the line.
- **Iteration 2: more metal, and the shell's form** (03:51-04:08, 8 mm meshes; `grade.py`'s table, `data/first_loop/grades.json`; "tilt" is the worst seat's tilt over its line, 0.75 × the contract's limit):

  | Design | kg | Drive µm | Reverse µm | Tilt | Orders |
  |---|---|---|---|---|---|
  | Convex shell, plain | 7.23 | 246 | 366 | 8.80 | clash |
  | Convex + fan ribs (1 kg optimisation) | 7.68 | 192 | 253 | 4.10 | clear |
  | Convex + skeleton ribs (1 kg) | 7.63 | 223 | 189 | 5.16 | clash |
  | Convex, end walls 10 mm | 8.06 | 132 | 176 | 3.54 | clear |
  | Convex + fan ribs twice as tall | 8.14 | 170 | 197 | 3.33 | clear |
  | Convex + fan ribs (2 kg optimisation) | 8.16 | 138 | 201 | 3.12 | clear |
  | Convex + skeleton ribs (2 kg) | 8.05 | 163 | 182 | 5.49 | clash |
  | Convex, end walls 10 mm + fan ribs | 8.52 | 118 | 152 | 2.62 | clear |
  | **Lobed shell, plain** (`lobed.py`) | **6.66** | 218 | 323 | **4.45** | clear |
  | Lobed, end walls 10 mm | 7.49 | 106 | 156 | 2.42 | clash |
  | Lobed, end walls 10 mm, bosses 12 mm | 8.04 | 95 | 130 | 2.01 | clash |

  - **The shell's form is a stronger lever than any reading:** the lobed form (a pod per shaft, each end wall stepped to its own shaft's end, a round flange plate for the motor) halves the convex form's tilt with no rib and 0.57 kg less.
  - **The binding seats are the intermediate's tapered pair** (the tightest line, 0.375 mrad) and the input's +z roller. The compliance objective puts its metal round the heavily loaded output instead: the optimisation solves the wrong problem until its objective is each seat's tilt over its line.
- **The mesh noise:** 8 mm against 6 mm: the worst displacements 242.4 against 246.1 µm (1.5 %) and 362.9 against 366.0 µm (0.9 %); the tilt 3.69 against 3.72 mrad; the first mode 842 against 838 Hz. The 8 mm mesh (531,552 unknowns, 25 s) ranks designs.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| One loop, start to end, before the agent | Complete the whole flow once in a prototype; learn from it how the agent should work and where its judgement belongs. Do not build the agent yet | 2026-10-09 01:54, the engineer |
| The two halves split across the shafts | One plane square to the shafts; each shaft has a bearing in each half | 2026-10-09 02:12, the engineer |
| Supports and joints | The mount bosses held fixed through distributing couplings; the halves joined at each bolt by distributing couplings; each bearing's loads through a distributing coupling over its whole seat (Physics) | 2026-10-09 02:12-02:15, the engineer |
| The mounts are an input | Their positions come from the vehicle (its mounting system's hardpoints) and are given in the contract. The example gives none, so three are assumed and labelled | 2026-10-09 02:16, the engineer |

## Open

- **The mounts and the motor flange are placed by the prototype** (A20, A25): three bosses on the motor-side half, the flange's ring round the input. They go into the contract as inputs when the loop is done.
- **The whole-seat coupling pulls the unloaded half of each seat** (the topology review's lesson from the example's source): to measure once against a cosine over the loaded half (D6a) on the baseline.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|
| LOP-2 | The plain housing judged by FE, the engineer's practice: the measures above | 2026-10-09 | 7ca5e28 |
| LOP-1 | The plain shell and wall in two halves, 7.23 kg, every face named | 2026-10-09 | 7ca5e28 |

## Docs

- The engineer's brief of 9 October 01:54 is this page's Decisions and Next.
- The reviews it rests on: [the spaces inside a reducer](../../research/2026-10-09-spaces-inside-a-reducer.md); [how housing topology optimisation is done](../../research/2026-10-09-housing-topology-optimisation-practice.md); [fastcae's code, mapped for the loop](../../research/2026-10-09-fastcae-code-map-for-the-loop.md).
