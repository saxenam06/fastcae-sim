# Gearbox domain

The gearbox's physics before any housing exists. From a contract's gear train, torques and packaging it works out:
- the forces at each mesh;
- the spacing along each shaft;
- the loads each bearing puts into its seat, for every load case;
- the bearing sizes, and the mesh orders.

It completes a posed contract, so that it can be frozen. The judge applies these seat loads to every design.

**PBI key:** GBX · **State:** GBX-5 in work (14:17): the contract complete, no motor flange, the set-up from one description. GBX-1 to GBX-4 done: the mesh forces and moments, the layout and its clearances, the seat loads, the shaft sections, the bearing selection, and completing and freezing a contract. The EV reducer completes and freezes clean on the catalogue checked against SKF (9860879). The life at the peak torque confirmed, and the helix hands kept as published (the engineer, 09:09). GBX-6 built and checked, uncommitted: each shaft's lean at its bearings per load case, which the loop's grade adds to the housing's tilt. All on `product/end-to-end`, not pushed · **Updated:** 2026-10-11 00:40 by Claude
**Code:** `src/zenryx/domains/gearbox/` (`forces.py`, `layout.py`, `loads.py`, `shafts.py`, `bearings.py`, `chain.py`, `complete.py`, the catalogue in `data/bearings.json`); checks in `checks/gearbox/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| GBX-6 | Each shaft's lean at its bearings per load case, a vector against the chord between its bearings, so that a bearing's misalignment is the housing's share plus the shaft's (the engineer, 9 October 09:57: the two add, no split by rule) | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-09 10:08 | Built: `shafts.ShaftSection.lean_at_bearing` (`_slope_vectors`: (−∫M_y/EI, +∫M_x/EI) from the −z side's moments); 2 checks (a centrally loaded beam's lean at both supports, sign and size; the chain keeps it for every case, its worst equal to the stiffening loop's slope); 202 checks pass. To commit on the engineer's word |
| GBX-5 | **The contract complete, and one description of the set-up** (the engineer, 10 October 12:49-14:00): the contract's elements, the agent's hypothesis, and what the optimiser is given, derived from both, drawn exactly and as the optimiser's voxels. The elements are the keep-out volumes, with no separate kept-clear rooms. **No motor flange:** the vehicle holds the motor, which drives the input through a flexible coupling | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-10 13:41 | **14:17: built; 212 checks pass, ruff clean, the page looked at** (uncommitted):<br>- the contract model: a mount's size, hole and bracket room; `motor_held_by`; a shaft end's `room` (a half-shaft's joint); `seal_section`; the process's `manufacturing.joint`. The EV reducer holds them: the mounts A20, the seal A16, the joint A26, the half-shafts' joints A27, the motor the engineer's (13:21); the validator checks their units and the mounts' normals;<br>- the load tool: the motor's reaction only where the housing holds the motor, so the mounts hold (i − 1)·T_in (checked each way);<br>- NEW `zenryx.geometry.plan` (the hull of circles, points spaced round an outline) and `zenryx.domains.gearbox.spaces`: every element from the contract and a `Hypothesis` (the split between the stages, one cup per half, the least wall, 13 bolts evenly at ≤ 80 mm), with checks (`checks/gearbox/test_spaces.py`: the split, the cup, the seals, the bolts' pitch, the mounts inside the packaging, the wall never under the least, the design space meeting no element). It caught two slips of the prototype's: the input's seal on the shaft's least bore (25 mm, not the 45 mm at its end), and two mounts outside the packaging space (now in its hull);<br>- `volumes.py` 0.2 and the export (schema 2, three groups; the design space 16.27 L, was 18.68);<br>- the loop: `prototypes/first_loop/contract_layout.py` writes the layout record `contract` from `spaces`; `topo_free.build_free` takes it by default (exits, brackets, the bolts' bosses held fixed, no motor ring; 16.47 L free, 2.43 kg fixed), and earlier runs keep `grammar4`; `topo.py` puts a motor torque only on a ring.<br>**Next:** `outcome_cad.py` and `fe.py` on the contract's layout (no ring, spigot or motor holes); the earlier designs judged again without the motor torque, and a new run on the contract's layout (both heavy: the engineer's word) |

## Next

| PBI | Goal | Done when |
|---|---|---|

## What runs

- **The mesh forces and moments** (`zenryx.domains.gearbox.forces`, GBX-1):
  - `case_forces(spec)` gives one load case per torque in the contract: its signed input torque, each mesh, and the torque each shaft passes on. The torque's sense comes from its direction and the input's forward rotation (`requirement.forward_rotation`; A21 assumes +z): drive turns the input forwards, reverse and regeneration act against it, so they load the teeth alike.
  - `mesh_forces(...)` is one mesh: the base-circle form Fbt = 2T/db1, Ft = Fbt·cos αwt, Fr = Fbt·sin αwt, Fa = Fbt·tan βb; on each gear the force at the pitch point as a vector in the contract's frame, and its moment about the gear's own centre (the torque about z and the axial force's moment Fa·rw in the plane).
  - `shaft_axes(spec)` places each shaft's axis in the end view (one stage on the x axis; two by the packaging offset).
  - The Contract page's step 4 shows the sizes, the force on each pinion in every case, and the gear's moment.
- **The layout** (`layout.place`, GBX-2): the gap-driven stack from the first mesh plane (z = 0); the second plane the gear-to-gear gap beyond it on the shared shaft (`first_stage_side`); a plain shaft's bearings the bearing-to-gear gap beyond its gears; a carrier's (the differential's) bearings its spacing apart, the gear beside one of them; the housing's inner faces the space behind each bearing (sealed or closed). Every two parts on different shafts that overlap end-on are checked along the shafts against the least axial clearance; a breach is reported with its shortfall.
- **The seat loads** (`loads.seat_loads`, GBX-2): each shaft a rigid body on its two bearings with the axial forces' moments; the thrust by the arrangement (locating, floating, or each bearing its own side with a tapered bearing's induced 0.5·Fr/Y); each seat takes the opposite of its bearing's reaction. The motor's reaction reaches the housing only where the housing holds the motor (`motor_held_by`): the EV reducer's vehicle holds it, so the mounts hold (i − 1)·T_in; a flanged motor's stator would put −T_in on the housing, and the mounts would hold i·T_in.
- **The shaft sections** (`shafts.sections`, GBX-3): the bore each seat needs from the torque through it (distortion energy, design factor 2, A24), at least the differential's hub; each gear's least diameter; a uniform beam between the bearings stiffened until no slope passes the contract's tilt limit (0.5 mm/m at a gear). Each section also keeps the shaft's lean at both bearings for every load case, as a vector against the chord between its bearings (GBX-6). On the EV reducer the shafts' own slopes use 4 % (input), 27-30 % (intermediate) and 20-24 % (output) of their bearings' limits.
- **The bearing selection** (`bearings.select`, GBX-3): the catalogue's bearings of the arrangement's type with the bore needed; L10 at the drive case and the rated speed at least the contract's 944 h; the smallest outside Ø, then the narrowest. A seat none serves is refused with its loads. The catalogue's 56 rows are checked against SKF's public product data; its tapered rows are SKF Explorer bearings.
- **The round** (`chain.complete_chain`): layout, loads, sections and selection until the bearings stop changing (2 passes for the EV reducer). The Contract page's steps 5-8 show it.
- **Completing a contract** (`complete.complete`, GBX-4): the seats (centre, axis, outside Ø, width, shoulder, stock, the bearing and its type), the load cases (seat forces, and the motor's reaction on its flange) and the mesh orders, each stamped with the tool and the posed contract's hash; the mounts and the motor flange copied from the requirement. The stage becomes "completed" (the engineer's word, 01:54); `freeze` then makes the task.
- What it builds on:
  - `zenryx.contract.involute.mesh_geometry`: a shifted pair's pressure angles, its reference, base, working pitch and tip diameters, and its working centre distance (committed in e32000d; the tip diameters since 01:06, uncommitted). GBX-1's forces start from its working pressure angle and base diameters;
  - `zenryx.contract.train`: the ratio, shaft speeds, mesh frequencies, and the shaft angle from the packaging offset; since 01:06 the axes' end-view positions (`axis_positions`) and how far two circles on different shafts overlap end-on (`end_view_overlap`), for step 5's clearance check;
  - the contract's `shaft_layout`: the gaps, the seal allowance and the sealed shaft ends, and the least clearances (the contract page lists them).

## Rules in force

- Derived physics is computed, never typed: every value the tool writes is stamped with the tool, its version and the input hash (CLAUDE.md).
- Paid standards (ISO 6336, ISO 281) never enter the repository. Their public formulas are taken from textbooks and catalogues.

## Measured

- **GBX-1's checks pass** (13, 9 October 02:39): the textbook form at zero shift (to 1e-12); equal and opposite forces; Ft·rw gives back the torque; the radial force pushes the gears apart; the hand rule for thrust; the axial force's moment Fa·rw; every shaft passes its torque on; reverse and regeneration alike; the forward rotation mirrors the directions only.
- **A published worked example is reproduced:** drivetrainhub's notebook (z 15/45, mn 2.5 mm, αn 20°, β 20°, a 80 mm, 100 N·m) gives Ft 5,000.0 N and Fr 1,971.1 N, and the tool gives the same to 0.05 N. Its Fa 1,819.9 N is Ft·tan β; the tool's Fa = Ft·tan βw is 0.23 % higher for that pair, the known difference between the two conventions.
- **The EV reducer at 150 N·m:** stage 1 Ft 5,499 · Fr 2,399 · Fa 3,243 N (Fbt 6,000 N); stage 2 Ft 11,066 · Fr 4,657 · Fa 6,490 N (Fbt 12,006 N), on 306 N·m into the intermediate pinion; 1,078 N·m out of the output.
- **GBX-2's checks pass** (13, 02:52): the stack rules; the differential's 96 mm; the overlap rule with an injected breach; a too-short carrier refused; the textbook example's Fr/2 ∓ (d/2)·Fa/L; every shaft in balance; the seats' forces cancel and, with the motor's reaction, twist the housing by −i·T_in; the tapered pair's induced forces.
- **GBX-3's checks pass** (10, 03:01): the rating life and the equivalent loads against their formulas; the smallest lasting bearing chosen; a refusal; the distortion-energy diameter; a centrally loaded beam's slope P·L²/(16EI) to 0.2 %; the round settles and every seat lasts or says why not.
- **The EV reducer's round, on the checked catalogue** (9 October 04:46; 2 passes, no refusal). The contract completes and freezes clean (sha256:7c2abca3…).

  | Seat | Bearing | d/D × B (mm) | P (N) | L10 (h) |
  |---|---|---|---|---|
  | input −z | 6309 | 45/100 × 25 | 6,794 | 1,498 |
  | input +z | NU 205 ECP | 25/52 × 15 | 2,975 | 8,037 |
  | intermediate −z | 30205 | 25/52 × 16.25 | 6,416 | 2,149 |
  | intermediate +z | 30210 | 50/90 × 21.75 | 18,643 | 1,206 |
  | output −z | 6309 | 45/100 × 25 | 13,233 | 1,457 |
  | output +z | 6209 | 45/85 × 19 | 8,047 | 1,656 |

  The intermediate's seats take Fr 6,416 and 5,525 N with Fa −2,005 and 11,738 N in drive, and Fr 10,674 and 6,873 N with Fa −12,188 and 2,455 N in reverse (−z, then +z). All six end-on overlaps clear by at least 13.2 mm.
- **The hand of stage 2's pinion changes the intermediate's bearings** (the what-if, 04:46). With stage 2's pinion right-handed, the round takes 3 passes:
  - the intermediate's +z seat takes Fa 1,606 N in drive and a 30205 (52 mm outside) instead of a 30210 (90 mm), lasting 4,505 h;
  - its −z seat takes a 30206 (1,320 h);
  - the output's two bearings swap sides (6209 at −z, 6309 at +z), since the output gear's thrust turns.

  The first loop built the same housing form on that round: its worst bearing seat tilts 18 % less against its shaft (loop page).
- **The life at the peak torque sizes the bearings large:** the 944 h is taken at the 150 N·m drive case (the engineer, 00:50), so the input's locating bearing is a 6309. A duty cycle or a nominal torque would give smaller bearings and a smaller housing.
- **The intermediate shaft's two axial forces add:** with both pinions left-handed, the stage-1 gear (right-handed) and the stage-2 pinion (left-handed) both push the intermediate shaft towards +z in drive, 3,243 + 6,490 = 9,733 N. With the same hand on the intermediate's two gears they would partly cancel (6,490 − 3,243 = 3,247 N), which is how designers usually choose the hands.
- **Profile shift matters for this gear train:** at 150 N·m the radial mesh force is +13.8 % (stage 1) and +10.4 % (stage 2) above the textbook formula; tangential −2.1 % and −1.6 %; axial unchanged.
  - The torque check (Ft × working radius) holds exactly.
  - Source: the prototype `prototypes/helical_forces/forces.py` (on `zenryx.contract.involute`), 8 October 21:00; rerun at 21:30 with the same numbers.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| **The split flange is an element; the bolts follow the inside's outline** | `spaces.flange`: every room's circle grown by the land, a flange deep each side of the split, less the rooms (`flange_inside`); the design space keeps out of it. The bolt line and the joint's outline follow the rooms' outline through the waists at the rules' offset (`plan.outline_of_circles`), not their hull: on the hull a waist's bolt stood clear of the land (the new check `test_the_split_flange_is_a_sealing_land_round_the_inside`); still 13 bolts | 2026-10-11 00:20, Claude, from the engineer's word that the flange is the contract's (23:47) |
| **The mounts stand clear of the housing (A20)** | The vehicle's hardpoints are inputs, kept realistic: each mount's lug 3 mm past the split flange's edge, so its bracket and bolt (Ø44 beyond both faces, up the whole housing) touch neither the shell nor the flange: mount-1 (-170.2, -52.7), mount-2 (176.4, 62.9), mount-3 (35.1, 280.9) mm. The first loop's places, kept from before the contract had a shell and a flange, put mount-2's room 11 mm into the wall and mount-3's 16.5 mm into the flange (both of Claude's: the mounts and the shell). Fixed once, before the optimisation; `checks/gearbox/test_spaces.py` keeps it so | 2026-10-10 20:45-20:47, the engineer |
| How sources are combined | Each step from the source that gives it best and still holds for helical gears, starting from what all sources agree on, each step with its confidence | 2026-10-08 20:59, the engineer |
| Mesh forces of shifted gears: the base-circle form | Fbt = 2T/db, then Ft = Fbt·cos αwt, Fr = Fbt·sin αwt, Fa = Fbt·tan βb (plan §4); for Ivanov the radial force is 10-14 % above the textbook form. drivetrainhub confirms it | 2026-10-09 00:57, the engineer |
| Bearing life, shaft material, bearing table | Bearing life 944 h (A4), taken at the drive case throughout. The shaft material is a common gear steel, labelled as an assumption. The bearings come from a maker's public catalogue, cited | 2026-10-09 00:50, the engineer |
| **The life at the peak torque** | Confirmed: the 944 h at the peak drive torque (150 N·m), each shaft at its speed at the rated input speed (6,000 rpm) | 2026-10-09 09:09, the engineer |
| **The helix hands as the source gives them** | Both pinions left-handed, as published; a value the source gives clearly is not changed. The same-hand run stays a what-if | 2026-10-09 09:29, the engineer |
| **The layout is gap-driven** | The gaps are the layout's inputs, held in the contract with the bearing arrangement (`requirement.shaft_layout`): bearing to gear, behind each bearing, between two gears on one shaft. Step 5 places the gears and bearings from them, centres from a datum, and the round (steps 5-8) changes only the bearings' widths, so the positions follow | 2026-10-09 00:06, the engineer |
| **One order-check speed: 6,000 rpm** | The mesh orders are checked against the housing's modes at the rated speed alone, the cruise, at least 3 % apart. The criterion names the duty's speed (`order_check_at: rated`) | 2026-10-09 01:06, the engineer |
| **The seal allowance per shaft end; the clearances calculated** | Where a shaft leaves the housing, the bearing has a seal's space behind it (11 mm, A16) on the ends the contract names (input −z, output −z and +z, A17); the intermediate's bores are closed, so its bearings keep the closed-bore space. Step 5 calculates every clearance from the layout: along the shafts between parts on different shafts that overlap end-on (at least A18's 3 mm; Ivanov's stage-1 gear and output gear overlap by 31.4 mm), and from the gear tips to the wall (at least A19's 8.25 mm). Taken before GBX-1 | 2026-10-09 01:06, the engineer |
| Where confidence is low, search | A targeted web search for that point only, the finding recorded with its source. Helical gearboxes are a proven trade, so the information exists. Done for the shifted-gear convention and the tapered pair (plan §3a) | 2026-10-08 21:02, the engineer |
| **No motor flange; the vehicle holds the motor** | The motor drives the input shaft through a flexible coupling; the housing has no flange and carries none of the motor's torque ("not important to prove the product") | 2026-10-10 13:21, the engineer |
| **The elements are the keep-out volumes** | Gears, shafts, bearing bores, the differential, the mounts: the design space keeps out of them, with no separate kept-clear rooms. A shaft's exit (its seal's bore, a half-shaft's joint) is part of the shaft, a bracket's room part of its mount; the cavity, the wall and the seat rings are one shell, a uniform wall (a parameter, at least the contract's 4 mm) round the inside | 2026-10-10 13:45-13:51, the engineer |
| **Who decides the split and the bolts** | The process is the user's (two halves across the shafts); the joint's rules are the process's (assumed, A26); where the split lies and the bolts' pattern are the agent's hypothesis, which a tool turns into positions | 2026-10-10 13:52, proposed by Claude, building it so |
| **The set-up shown in three groups** | The contract → what the agent decides (its hypothesis) → what the optimiser is given, each derived from those above | 2026-10-10 14:00, the engineer |

## Open

- **The helix hands are as published and stay so.** The example's source gives both pinions left-handed and both gears right-handed (Ivanov 2018, Figs. 24 and 25, read from a copy). So the intermediate shaft's two gears have opposite hands, and their axial forces add (9.7 kN in drive) instead of partly cancelling (3.2 kN), against the usual practice of handing a shaft's gears so that their thrusts oppose. The other papers give no hands: Kim et al. 2024 gives full gear data without them, Hofstetter et al. 2018 gives no gear data, and the housing optimisation studies start from bearing forces computed elsewhere. The same-hand what-if (a 52 mm bearing instead of 90 mm, the housing's worst seat 18 % less) stays a what-if: what the product can show a user about a requirement that drives the housing.
- **The layout's values, as assumed** (A13-A19 in the Ivanov contract):
  - 12.7 mm between a bearing and its gear and 6.35 mm behind a bearing in a closed bore, both from Shigley's Fig. 18-2, an industrial gearbox, so likely generous;
  - 12.7 mm between the intermediate shaft's two gears, and 3 mm least clearance along the shafts: no source yet;
  - 11 mm behind a bearing where its shaft leaves (an 8 mm radial shaft seal and 3 mm for its seat), and 8.25 mm from the gear tips to the wall (Łódź's (1.1-1.2)·δ).

  Tighter, sourced values for an EV reducer are wanted ([research](../../research/2026-10-08-bearing-positions.md)).
- **Proposed:** the bearings' speed limits checked at the duty's maximum, 8,673 rpm. The order check now uses the rated speed alone, and a bearing must still run at the top speed.
- Equilibrium does not place the bearings; it judges a layout, through its reactions. The bearing arrangement is chosen per shaft: locating and floating, or an adjusted pair like Ivanov's intermediate tapered one. Not one rule for all.
- **Bearing selection needs a bearing table:** ISO 15 dimensions, public, and a maker's dynamic ratings C, cited. The life and loads constrain the choice with the bore, the capacity and the arrangement.
- **The shaft sections are now step 7** (the engineer, 23:37): strength and stiffness; their material is an assumption to add.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|
| GBX-4 | Completing and freezing a contract (`complete.complete`): the seats with their bearings, the load cases with the motor's reaction, the mesh orders, each stamped with the tool and the posed contract's hash; the stage "completed"; the EV reducer completes and freezes clean; 7 checks | 2026-10-09 | f79760c, 9860879 |
| GBX-3 | The shaft sections (strength by distortion energy, stiffness by the slopes), the bearing selection by L10 from a catalogue checked against SKF, and the round of steps 5-8; 10 checks | 2026-10-09 | f79760c, 9860879 |
| GBX-2 | The layout along each shaft from the gaps and the differential, the end-on clearance check, and the seat loads with the arrangement's thrust and the motor's reaction; the contract's structured arrangement (A8), A22 and A23; 13 checks | 2026-10-09 | 4a3ba35 |
| GBX-1 | The mesh forces and moments in every load case (`zenryx.domains.gearbox.forces`): the base-circle form, the directions on each gear in the contract's frame, each gear's moment; the input's forward rotation as a contract input (A21, `consistency.rotation`); step 4 computed on the Contract page; 13 checks, a published example among them | 2026-10-09 | ac34e4c |

## Docs

- [2026-10-08-load-tool-plan.md](2026-10-08-load-tool-plan.md): the load tool's equations, sources and checks.
- [2026-10-09-gaps-along-a-shaft.html](2026-10-09-gaps-along-a-shaft.html): an interactive explainer of the layout's gaps, made for the engineer (9 Oct 00:22), published privately at https://claude.ai/artifact/QouM3otg2WGmEeJM8LYUDJ. It covers what fills a gap; how the span sets the bending; overhung gears; the seat's material; oil and heat; where the housing puts material; the round of steps 5-8; and (since 01:02) the three shafts. That last section shows Ivanov's end view to scale, where the output wheel overlaps the stage-1 wheel by 31 mm, the side view, and a live clearance check of every pair that overlaps. Its numbers come from simple beam formulas on Ivanov's input shaft, for intuition only.
