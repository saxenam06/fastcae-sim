# Status: the board

**Updated:** 2026-10-09 03:20 by Claude.
- **For the engineer's morning: the night of 9 October** (the brief of 01:54; Claude works alone). In order:
  1. **Done, 02:25:** the product's contract is the "EV two-stage reducer" and names no paper (CON-4); committed with the night's earlier work in 577de20, not pushed.
  2. The contract completed: **GBX-1 done** (mesh forces and moments, ac34e4c); **GBX-2 done** (layout with the differential, clearances, seat loads, 4a3ba35); **GBX-3 and GBX-4 built** (f79760c: shaft sections, bearing selection, the round, and completing and freezing a contract). The EV reducer waits on one seat: no catalogue bearing lasts on the intermediate's +z seat because the two left-handed pinions' thrusts add; with stage 2's pinion right-handed it completes and freezes clean (questions on the Gearbox page). The stage between posed and frozen is now called "completed".
  3. **PLT-8 done** (60f6d84): the Contract page's "The result" shows the volumes in 3D (gears, shafts, bearings, the differential, the packaging space 21.5 L, the design space 18.7 L), a chip per volume, "Design space only". fastcae's WebGL2 renderer copied: no new dependency.
  4. **Two reviews done** (4c7c14f, c6bc94a): the spaces inside a reducer (the differential, the sump, the split flange, the motor flange and the mounts now in the contract or next); how housing topology optimisation is iterated (the loop LOP follows its recipe).
  5. The first loop (LOP): plain shell and wall, topology optimisation, ribs, mesh, couplings, loads, solve, grade.
- **Where the code stands:** one branch, `product/end-to-end`, not pushed. The contract schema, its validator and the product's contract (CON); the web UI, five pages, the Contract page showing what is given and what is calculated (PLT); the load tool planned (GBX). 151 checks pass.
- **Earlier:** the overnight build of 8 October (PLT-2, CON-1, the first-variant prototype in `prototypes/first_variant/`); the web UI (PLT-4, PLT-6); the calculation chain; PLT-7.

See [the build record](features/product/2026-10-08-decisions-and-build-record.md).

Every feature of zenryx: where it stands, who works on it, what comes next. Each feature's page holds the detail. How the board is kept is in [CLAUDE.md](../CLAUDE.md).

## Features

| Feature | Key | State | Now | Next | Who |
|---|---|---|---|---|---|
| [Product](features/product/status.md) | PRD | The plan of record. The contract's direction was decided on 8 October: published requirements; a verdict built from standards, with published values as a plausibility band; replayable graded tasks; GRC not used | PRD-3 (the engineer's questions before P0), under way | - | Manasvi |
| [Platform](features/platform/status.md) | PLT | PLT-2 (Python project, venv, checks, CI) works locally. PLT-4 and PLT-6 (the web UI) work locally: five tabs, one clean product page each, in the order the work runs (Contract, Campaigns, Designs, Data, Flow). The Contract page shows the EV two-stage reducer: its inputs, the calculations with their methods, the criteria and the design to beat; the rest is laid out blank. In PowerShell, `cd web` then `npm.cmd run dev` opens it on port 5190. Committed (feca5c1, ca44539, 9acf466, 61e51c8), not pushed; CI not yet run. PLT-7: the Contract page says what is given and what is calculated, step by step; an input is only what can be chosen freely (the engineer, 22:57). Committed (e32000d, cefd868, 17cdbf2); the ten-step chain, the contracts without paper figures and the gap-driven layout on the Bearings and layout card (the gaps, the sealed shaft ends, the least clearances), committed in 577de20 | PLT-2, PLT-4, PLT-6 and PLT-7, done locally | PLT-3: the runner and its guards | Claude |
| [Physics and the judge](features/physics/status.md) | PHY | Nothing built. Decided: the FE model's practice (distributed couplings for bolts; bearing loads spread over each seat with the bearing's stiffness) and the 25 % model margin, kept for now (the engineer, 9 October 00:57 and 01:06) | - | PHY-1 (the FE solve): the cuDSS static solve copied from fastcae, with its parity test | - |
| [Contract](features/contract/status.md) | CON | CON-1 (contract schema v0) works locally: schema, validator, hash, example contracts. CON-3 and CON-4: the EV two-stage reducer, posed, the product's one contract, naming no paper (9 October 02:25). Its 112 checks pass (151 in all). Committed (f51aba1, 840c486, 9acf466, 577de20), not pushed: no value its inputs fix (`consistency.redundant`), the shaft layout (A13-A19) and one order-check speed (9 October 01:06); the process and the first packaging taken at 02:12; awaiting the engineer's review | CON-1 and CON-3, done locally | CON-2: check the examples' open points (bearing dimensions, the offset reading, A8) | Claude |
| [Data](features/data/status.md) | DAT | Designed in discussion (8 October): one contract is one task; the four axes; the datapoint kinds; campaigns cut into decision records, snapshot tasks and preference pairs; 20 task types; LLM fine-tuning and physics AI. Nothing built | - | DAT-1 (the record schema), once the engineer agrees the proposals | - |
| [Gearbox domain](features/gearbox/status.md) | GBX | The load tool planned (8 October): helical, profile-shifted mesh forces; spacing along the shafts; bearing reactions with axial moments; bearing sizes by L10 life. Each step takes its equations from its best source, and the low-confidence points were searched and confirmed. The plan committed (bbcdbac), not pushed; nothing built. The layout is gap-driven (9 Oct 00:06), with an interactive explainer of the gaps (`docs/features/gearbox/2026-10-09-gaps-along-a-shaft.html`). Decided on 9 October: the base-circle forces; bearing life 944 h at the drive case; the shaft steel as an assumption; a maker's catalogue; a seal allowance per shaft end and the clearances calculated in step 5 | GBX-1 and GBX-2 done; GBX-3 and GBX-4 built (f79760c); the EV reducer waits on its +z intermediate bearing | the bearing table checked and extended | Claude |
| [The first loop](features/loop/status.md) | LOP | One housing taken start to end as a prototype: plain shell and wall, topology optimisation, ribs, mesh, couplings, loads, solve, grade (the engineer, 9 October 01:54). Planned; it waits on the completed contract | - | LOP-1 (the design space, the plain shell and wall, named faces) | Claude |

## Planned features (a page each when their first PBI starts)

| Feature | Key | What | Phase |
|---|---|---|---|
| Geometry | GEO | The CadQuery machined core, the design domain and keep-outs, the field-space shell and member grammar, realisation by B-rep or SDF | P1 |
| Optimise | OPT | Voxel topology optimisation with its filters, the relaxed bound, member sizing, the acquisition of FE proofs | P1 |
| Process | PRC | Process profiles (aluminium high-pressure die casting first, since 8 October), checks on the built part, the qualification rung | P1 |
| Campaign and agent | AGT | Campaign state, hypotheses, the deterministic arms, the agent's tools and brief | P2 |
| Benchmark | BEN | The registered protocol, the arms, the controls, the reports | P2 |
| Learning | LRN | The KPI model and ranker, the failure predictor, the field surrogate; later, LLM fine-tuning (data design §7-8) | P3 |
