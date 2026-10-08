# Status: the board

**Updated:** 2026-10-09 04:50 by Claude.
- **For the engineer's morning: the night of 9 October** (the brief of 01:54; Claude worked alone). All of it is committed on `product/end-to-end`, not pushed. In order:
  1. **The contract names no paper** (CON-4, 577de20): it is the "EV two-stage reducer", and the example's origin is named in the docs only.
  2. **The contract completes and freezes** (GBX-1 to GBX-4 done: ac34e4c, 4a3ba35, f79760c, 9860879):
     - the mesh forces and moments;
     - the gap-driven layout with the differential, and its clearances;
     - the seat loads;
     - the shaft sections;
     - the bearings by L10, from a catalogue checked against SKF.

     The stage between posed and frozen is called "completed".
  3. **The volumes in 3D on the Contract page** (PLT-8, 60f6d84): gears, shafts, bearings, the differential, the packaging space (21.5 L) and the design space (18.7 L), a chip per volume, "Design space only". fastcae's WebGL2 renderer was copied rather than adding three.js, so there is no new dependency.
  4. **Two reviews** (4c7c14f, c6bc94a): the spaces inside a reducer; how housing topology optimisation is iterated.
  5. **The first loop, start to end** (LOP-1 to LOP-6 done). One housing went from the completed contract through a shell and wall, FE, topology optimisation, ribs and FE again, in three rounds: 16 designs, 19 FE judgements, 3 optimisations.
     - **Nothing passes as the contract stands.** The best under the reference's 7.73 kg is the lobed form with 10 mm end walls: 7.49 kg, its worst bearing seat 3.4 times its line.
     - [What it teaches](features/loop/2026-10-09-first-loop-what-it-teaches.md): the shell's form is the strongest lever, and no optimiser proposed it.
     - The compliance objective aims at the wrong seats.
     - The voxel model is 4.5-8 times too stiff, so it ranks and never judges.
     - The reading of a field matters as much as the field.
     - The grade must measure the bearing's misalignment, the seat against its shaft: 21-68 % stricter than the seat's own rotation, which the night graded until 04:35.
- **Questions for the engineer** (each on its page):
  1. Is stage 2's pinion left-handed in the source? Then the intermediate's thrusts add. With the same hand, its +z bearing shrinks from 90 to 52 mm outside, and the housing's worst seat tilts 18 % less (Gearbox, the loop).
  2. Is the bearing life taken at the peak torque? It sizes the bearings large (Gearbox).
  3. The tapered seats' limit at the lower end of Shigley's range (0.5 mrad), and the 25 % margin applied as 0.75 × the limit (the loop).
  4. How is one misalignment limit shared between the shaft's own slope, which already uses 4-30 % of it, and the housing (the loop, Physics)?
  5. The mounts (A20) and the motor flange (A25): the loop placed them; GBX-5 puts them in the contract as labelled assumptions.
  6. The packaging margin A3 was raised from 20 to 40 mm, for the wall, the flange and ribs (Contract).
  7. The park lock and the oil level (the spaces review).
  8. When to push.
- **Where the code stands:** one branch, `product/end-to-end`, not pushed; 201 checks pass. The contract, its validator and the product's contract (CON); the load tool that completes it (GBX); the web UI's five pages, the Contract page with the volumes in 3D (PLT); the loop's prototype in `prototypes/first_loop/` (LOP).
- **Earlier:** the overnight build of 8 October (PLT-2, CON-1, the first-variant prototype in `prototypes/first_variant/`); the web UI (PLT-4, PLT-6); the calculation chain; PLT-7.

See [the build record](features/product/2026-10-08-decisions-and-build-record.md).

Every feature of zenryx: where it stands, who works on it, what comes next. Each feature's page holds the detail. How the board is kept is in [CLAUDE.md](../CLAUDE.md).

## Features

| Feature | Key | State | Now | Next | Who |
|---|---|---|---|---|---|
| [Product](features/product/status.md) | PRD | The plan of record. The contract's direction was decided on 8 October: published requirements; a verdict built from standards, with published values as a plausibility band; replayable graded tasks; GRC not used | PRD-3 (the engineer's questions before P0), under way | - | Manasvi |
| [Platform](features/platform/status.md) | PLT | PLT-2 (Python project, venv, checks, CI) works locally. PLT-4 and PLT-6 (the web UI) work locally: five tabs, one clean product page each, in the order the work runs (Contract, Campaigns, Designs, Data, Flow). The Contract page shows the EV two-stage reducer: its inputs, the calculations with their methods, the criteria and the design to beat; the rest is laid out blank. In PowerShell, `cd web` then `npm.cmd run dev` opens it on port 5190. Committed (feca5c1, ca44539, 9acf466, 61e51c8), not pushed; CI not yet run. PLT-7: the Contract page says what is given and what is calculated, step by step; an input is only what can be chosen freely (the engineer, 22:57). Committed (e32000d, cefd868, 17cdbf2); the ten-step chain, the contracts without paper figures and the gap-driven layout on the Bearings and layout card (the gaps, the sealed shaft ends, the least clearances), committed in 577de20. PLT-8: the Contract page's result shows the volumes in 3D, each toggled, down to the design space alone (60f6d84) | PLT-2, PLT-4, PLT-6, PLT-7 and PLT-8, done locally | PLT-3: the runner and its guards | Claude |
| [Physics and the judge](features/physics/status.md) | PHY | Nothing built. Decided: the FE model's practice (distributed couplings for bolts; bearing loads spread over each seat with the bearing's stiffness) and the 25 % model margin, kept for now (the engineer, 9 October 00:57 and 01:06) | - | PHY-1 (the FE solve): the cuDSS static solve copied from fastcae, with its parity test | - |
| [Contract](features/contract/status.md) | CON | CON-1 (contract schema v0) works locally: schema, validator, hash, example contracts. CON-3 and CON-4: the EV two-stage reducer, posed, the product's one contract, naming no paper (9 October 02:25). Its checks pass (201 in all). Committed (f51aba1, 840c486, 9acf466, 577de20), not pushed: no value its inputs fix (`consistency.redundant`), the shaft layout (A13-A19) and one order-check speed (9 October 01:06); the process and the first packaging taken at 02:12; awaiting the engineer's review | CON-1 and CON-3, done locally | CON-2: check the examples' open points (bearing dimensions, the offset reading, A8) | Claude |
| [Data](features/data/status.md) | DAT | Designed in discussion (8 October): one contract is one task; the four axes; the datapoint kinds; campaigns cut into decision records, snapshot tasks and preference pairs; 20 task types; LLM fine-tuning and physics AI. Nothing built | - | DAT-1 (the record schema), once the engineer agrees the proposals | - |
| [Gearbox domain](features/gearbox/status.md) | GBX | GBX-1 to GBX-4 done: the mesh forces and moments (the base-circle form), the gap-driven layout with the differential and its clearances, the seat loads, the shaft sections, and the bearings by L10 life from a catalogue checked against SKF; a contract completes and freezes. The EV reducer completes and freezes clean. Committed (ac34e4c, 4a3ba35, f79760c, 9860879), not pushed. Decided on 9 October: the base-circle forces; bearing life 944 h at the drive case; the shaft steel as an assumption; a maker's catalogue; a seal allowance per shaft end and the clearances calculated | - | GBX-5: the mounts and the motor flange as the contract's inputs | Claude |
| [The first loop](features/loop/status.md) | LOP | LOP-1 to LOP-6 done: one housing taken start to end as a prototype (the engineer, 9 October 01:54), in three rounds: 16 designs, 19 FE judgements, 3 optimisations. Nothing passes as the contract stands; the best under the reference's mass weighs 7.49 kg, its worst bearing seat 3.4 times its line. [What it teaches](features/loop/2026-10-09-first-loop-what-it-teaches.md): the tools the product needs and where the agent's judgement belongs | - | LOP-7: the second round, after the engineer's answers | Claude |

## Planned features (a page each when their first PBI starts)

| Feature | Key | What | Phase |
|---|---|---|---|
| Geometry | GEO | The CadQuery machined core, the design domain and keep-outs, the field-space shell and member grammar, realisation by B-rep or SDF | P1 |
| Optimise | OPT | Voxel topology optimisation with its filters, the relaxed bound, member sizing, the acquisition of FE proofs | P1 |
| Process | PRC | Process profiles (aluminium high-pressure die casting first, since 8 October), checks on the built part, the qualification rung | P1 |
| Campaign and agent | AGT | Campaign state, hypotheses, the deterministic arms, the agent's tools and brief | P2 |
| Benchmark | BEN | The registered protocol, the arms, the controls, the reports | P2 |
| Learning | LRN | The KPI model and ranker, the failure predictor, the field surrogate; later, LLM fine-tuning (data design §7-8) | P3 |
