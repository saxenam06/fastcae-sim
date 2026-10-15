# The first loop: what it teaches

**Date.** 9 October 2026, 01:54 (the engineer's brief) to 04:45. **What it is.** One housing for the EV two-stage reducer, taken all the way through:
- the contract completed;
- a plain shell and wall, judged by FE;
- topology optimisation, its result read into ribs, the ribs built into the CAD, judged again;
- round again, three times: 16 designs, 19 FE judgements, 3 optimisations.

The scripts are a prototype in `prototypes/first_loop/`. The numbers are in `data/first_loop/grades.json`; git ignores `data/`, so the tables here and on [the loop's page](status.md) are the record. This note says what the loop showed about the tools the product needs, and where an agent's judgement belongs.

## 1. The flow, as it ran

| Step | Tool (prototype) | In | Out | Time |
|---|---|---|---|---|
| The contract completed | `zenryx.domains.gearbox` (GBX-1-4) | the posed contract | seats, loads, bearings; frozen | 2 s |
| The design space | `zenryx.domains.gearbox.volumes` (PLT-8) | the completed round | parts, packaging space, design space | 2 s |
| The shell and wall | `shell.py` (convex) / `lobed.py` (lobed) | the round, the settings | two halves, every face named, the mass | 4-6 s |
| The FE judgement | `fe.py` (fastcae's TET10 and cuDSS, copied) | the halves | each seat's motion, the shafts' lines, modes, the mass | 25 s (8 mm) - 110 s (6 mm) |
| Topology optimisation | `topo.py` (voxel SIMP, cuDSS each iteration) | the shell frozen, the packaging space | a density field | 3-4 min |
| Reading | `read.py` (a scored fan; the field's skeleton) | the field | rib paths, heights, thicknesses | 2 s |
| Ribs built | `shell.py` / `lobed.py` with `ribs` | the paths | the CAD with ribs | 5-8 s |
| The grade | `grade.py` | every FE result | the contract's lines, pass or fail | 1 s |

A design goes from an idea to its grade in about a minute; an optimisation adds four.

## 2. The iterations

The lines are the contract's:
- each seat's tilt within 0.75 times its bearing type's limit (the 25 % model margin; tapered 0.375, cylindrical 0.6, ball 0.75 mrad);
- the gear orders at least 3 % from every mode at 6,000 rpm;
- the design to beat: the example's reference housing, 7.73 kg, its bearing beds moving at most 52 µm forward and 138 µm in reverse.

The tilt is the worst seat's over its line, and it must reach 1. It is given two ways:
- **Shaft:** the seat's tilt against its shaft's line, through the shaft's two seats. This is the housing's share of what the bearing sees, and the grade takes it.
- **Own:** the seat's own rotation, which the night graded first (section 3, point 9).

All on 8 mm meshes; against 6 mm the noise is 1-2 %.

| Round | Design | What changed | kg | Drive µm | Reverse µm | Own | Shaft | Orders |
|---|---|---|---|---|---|---|---|---|
| 0 | `shell` (6 mm) | the plain convex shell, 6 mm walls | 7.23 | 246 | 366 | 8.80 | 11.10 | clash |
| 1 | `ribs_fan` | + ribs: the 1 kg compliance optimisation, read as a fan | 7.68 | 192 | 253 | 4.10 | 5.90 | clear |
| 1 | `ribs_skel` | + ribs: the same field, read by its skeleton | 7.63 | 223 | 189 | 5.16 | 6.57 | clash |
| 2 | `end10` | end walls 10 mm, no ribs | 8.06 | 132 | 176 | 3.54 | 4.59 | clear |
| 2 | `fan_tall` | the fan's ribs twice as tall | 8.14 | 170 | 197 | 3.33 | 5.17 | clear |
| 2 | `ribs2_fan` | + ribs: the 2 kg optimisation, fan | 8.16 | 138 | 201 | 3.12 | 4.79 | clear |
| 2 | `ribs2_skel` | + ribs: the 2 kg optimisation, skeleton | 8.05 | 163 | 182 | 5.49 | 6.62 | clash |
| 2 | `end10_fan` | end walls 10 mm + the fan | 8.52 | 118 | 152 | 2.62 | 3.73 | clear |
| 2 | **`lobed`** | **the lobed form**: a pod per shaft, stepped end walls | **6.66** | 218 | 323 | **4.45** | **5.92** | clear |
| 2 | `lobed_e10` | lobed, end walls 10 mm | 7.49 | 106 | 156 | 2.42 | 3.36 | clash |
| 2 | `lobed_e10_b12` | lobed, end walls 10 mm, bosses 12 mm | 8.04 | 95 | 130 | 2.01 | 2.88 | clash |
| 3 | `lobed_tilt1` | lobed + ribs: the 1 kg **tilt** optimisation, skeleton | 6.99 | 207 | 300 | 3.95 | 5.54 | clear |
| 3 | `lobed_e10_tilt1` | lobed, end walls 10 mm + the tilt ribs | 7.83 | 97 | 143 | 2.05 | 2.99 | clash |
| 3 | `hyp_e6` | lobed + a designer's radial ribs round the intermediate's bosses | 6.75 | 215 | 321 | 4.00 | 5.13 | clear |
| 3 | `hyp_e10` | the same on 10 mm end walls | 7.58 | 106 | 155 | 2.35 | 3.29 | clash |
| 3 | `mounts_cover_e10` | `lobed_e10` with the third mount on the cover (A20) | 7.49 | 112 | 147 | 2.74 | 3.42 | clash |
| 3 | `lobed_e10_cosine` | `lobed_e10`, the seats loaded by the plan's cosine (D6a) | 7.49 | 98 | 134 | 2.34 | 3.28 | clash |
| 3 | **`whatif_hand_e10`** | `lobed_e10`'s form and settings on a what-if contract, **stage 2's pinion right-handed**, with that contract's own bearings | 7.50 | 121 | **134** | **1.65** | **2.77** | clash |
| 3 | `lobed_e10_m6` | `lobed_e10` on a 6 mm mesh | 7.49 | 107 | 158 | 2.44 | 3.36 | clash |

**Nothing passes.** As the contract stands, the best under the reference's mass is `lobed_e10`, 7.49 kg: its worst seat is 3.4 times its line against its shaft (2.4 by its own rotation), and the 6 mm mesh confirms it. The forward displacement is nowhere near the reference's: 95 µm at best against 52. The reverse one comes under 138 µm only with 12 mm bosses (above the mass), with the cosine load, or in the what-if.

## 3. What worked, and what did not

1. **The shell's form is the strongest lever.** The lobed form follows each shaft with stepped end walls. Against a convex box round all three shafts, it weighs 0.57 kg less and halves the tilt with no rib (5.92 against 11.10). In the convex form each boss is a long tube to a flat end plate that all three shafts share.
2. **The binding seats are set by the inputs as much as by the housing.**
   - Both stages' pinions are left-handed, so the intermediate's two gears have opposite hands and their thrusts add. About 12 kN reaches one of its seats in each case: 11.7 kN on +z in drive, 12.2 kN on −z in reverse.
   - The what-if gives both the same hand (stage 2's pinion right-handed). `lobed_e10`'s form and settings, built on its own completed round, weigh the same. That round chooses its own bearings: a 30205 instead of a 30210 on the intermediate's +z seat, and the output's two swapped. The worst seat falls 18 % against the shaft (3.36 → 2.77) and 32 % by its own rotation (2.42 → 1.65), and the reverse displacement comes under the reference's.
   - The tapered seats' line, the lower end of Shigley's 0.5-1.2 mrad less the margin, is the tightest of all.
   - These are the engineer's to set. The input's +z roller and the output's balls bind too, though, so the housing must change as well.
3. **The optimisation solves the problem it is given.**
   - With compliance as its objective it put most of its metal round the output, the most heavily loaded shaft, but the contract binds at the intermediate.
   - With the seats' tilt over their lines as the objective (by an adjoint on the same factor), it put its metal on the lobes' rims and side walls and in the waist between them.
   - In the voxel model the worst seat fell from 0.98 to 0.38 of its line. Read into ribs and judged on the CAD, the fall was 11 % by the seat's own rotation (4.45 → 3.95) and 6 % against the shaft. The ribs held 0.33 kg of the 1 kg, and the material on the side walls had no reader.
   - None of the three optimisations converged in its 40 iterations.
4. **The reading matters as much as the field.** Two readings of one field differed by 11-26 % in tilt and by 34 % in reverse displacement, and neither was better in both: the fan was better in tilt, the skeleton in reverse.
5. **More end-wall metal pays, then flattens.**
   - On the convex shell, the first 0.45 kg of ribs took 47 % off the tilt, and 10 mm end walls (0.83 kg) took 59 %.
   - On the lobed shell, 10 mm end walls took 43 % for 0.83 kg. The next 0.34-0.55 kg, whether ribs from the tilt optimisation or 12 mm bosses, took 11-14 %.
6. **The voxel model ranks, it never judges.** It read the plain lobed shell's worst seat at 0.98 of its line with 6 mm voxels, and at 0.53 with 8 mm. The CAD's FE reads 4.45 by the same measure, so the voxel model is 4.5-8 times too stiff in tilt, more so the coarser the voxels. A voxelised wall is thicker than the wall, and linear hexahedra lock in bending. The model names the same seat worst (the intermediate's −z), but every claim above is the CAD's, meshed and solved (fastcae's lesson, met again).
7. **The FE practice holds.** The engineer's whole-seat coupling and the plan's cosine load differ by 3 % in tilt (2.34 against 2.42; 3.28 against 3.36) and by 8-14 % in displacement. The verdict does not hang on the choice.
8. **A designer's hunch can be wrong in the same way an optimiser's can.** Radial ribs round the intermediate's bosses gave 10-13 % on 6 mm end walls and 2-3 % on 10 mm. Those seats tilt with the whole stepped end wall they share with the output's large lobe, not locally.
9. **The grade must measure what the limit means.**
   - The tilt limits are a bearing's misalignment: the angle between its shaft and its seat. The night graded each seat's own rotation first, which also counts a rigid turn of the whole housing, and misses the shaft's line tilting as its two seats move.
   - Against its shaft, every design's worst seat reads 21-68 % worse. The ranking barely moves: the first seven keep their order.
   - The shafts' own bending adds to this: it already uses 4 % (input), 27-30 % (intermediate) and 20-24 % (output) of the limits.

## 4. The tools the product needs

From what the loop had to build, and what broke. Each goes to its feature when the product takes it up: the shell and wall, the design space and the rib builder to Geometry (GEO); the FE judge and the grader to Physics (PHY); the optimiser and the reader to Optimise (OPT).

- **The shell-and-wall tool:**
  - its form as a choice: convex, or lobed by shaft;
  - its settings (walls, end walls, bosses, flange, sump), each with its source;
  - the outside interfaces (the motor's flange plate, the mounts) from the contract;
  - every face named by its role, from the exact geometry.

  It must refuse a disconnected solid: the motor's ring once floated free of a narrow lobe.
- **The FE judge**, the engineer's practice:
  - distributing couplings at the seats, the mounts and the halves' bolts, the bolts tied at one point on the split plane;
  - statics and modes;
  - each seat's rigid fit, and its tilt against its shaft's line;
  - an equilibrium check on every solve (it caught a stray bolt moment);
  - the couplings as exact constraints, so that the single-precision factor refines. The night's penalties stalled it, and the prototype's fallback to a double factor broke the engineer's rule: single precision only, so that the factor fits the card.
- **The design space and the optimiser:**
  - voxels that keep thin walls whole (a cell is wall where it touches the wall);
  - the objective as a choice: compliance, or the seats' tilt against their shafts over their lines, by an adjoint. The night's adjoint took the seat's own rotation;
  - budgets, and enough iterations to converge;
  - a mask for a local cycle, and the bound;
  - its error against the CAD measured at its voxel size.
- **The reader:**
  - a height map on each face, stepped faces included;
  - candidates as a scored fan, or the skeleton with each rib as wide as its band;
  - the material off the end faces (the side walls, the waists between lobes), which tonight's reader leaves unread.
- **The rib builder:** plates on a face along a path, on the face's own pod and clipped to it, kept out of the room the motor, the half-shafts and the tools need.
- **The grader:** the contract's lines; a table across designs; the noise as a tie.
- **What-if runs:** the same tools on a variant contract (`LOOP_CONTRACT`), so that a requirement's effect on the housing can be shown to the engineer.

## 5. Where the agent's judgement belongs

Every choice the loop made by hand is one an agent will make:
- **The form:** convex or lobed. The largest gain of the night, and no optimiser proposed it.
- **The formulation:** which measure binds (read from the grade), so which objective; the budget; the whole space or a sub-space.
- **The reading:** which method, which threshold, how wide a rib. Two readings of one field differed by up to a quarter.
- **The levers and their ranges:** end walls, bosses, ribs' heights; when to stop adding metal.
- **The diagnosis:**
  - which seat binds and why: thrust bending the end wall out of its plane, a boss on a long tube, a cover hung off its flange;
  - which hypotheses that rules out (the designer's radial ribs);
  - when a tool's answer is wrong rather than the design: a singular stiffness, a voxel model several times too stiff, a floating ring, a grade that measured the seat's rotation where the limit means the bearing's misalignment.
- **The questions for the engineer:** a requirement found to drive the housing (the helix hands), a limit at the strict end of its range (the tapered tilt), a placement only assumed (the mounts), a budget the contract leaves unsaid (the shaft's and the housing's shares of one misalignment).

The tools are deterministic and fast (a design a minute). The night's gains came from the choices made between the runs.

## 6. What would open the space

In order of what the loop measured:
1. **The helix hands:** stage 2's pinion right-handed, if the source allows. With `lobed_e10`'s form on that contract's own round, the worst seat falls from 3.36 to 2.77 of its line against the shaft, and the reverse displacement comes under the reference's. The intermediate's −z seat in reverse stays the worst.
2. **The tapered seats' line, which alone does not open it.** At the upper end of Shigley's range less the margin (0.9 mrad), `lobed_e10`'s intermediate seats would read 1.3-1.4. The output's +z ball (2.16) and the input's +z roller (2.08) would then bind.
3. **The misalignment budget:** how the one limit is shared between the shaft's own slope and the housing. Whatever the shafts take is gone from the housing's line. The engineer's to set.
4. **The mass:** the reference's 7.73 kg is the design to beat. Above it, `lobed_e10_b12` (8.04 kg) reaches 2.88 against the shaft, and the trend flattens.
5. **Structure the loop has not tried:**
   - ribs on the side walls and in the waists between the lobes (the tilt optimisation put its metal there);
   - a stiffer intermediate lobe;
   - another bearing arrangement for the intermediate;
   - a local optimisation cycle round the binding seats;
   - the tilt objective taken against the shafts.
