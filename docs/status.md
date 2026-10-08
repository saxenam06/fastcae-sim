# Status: the board

**Updated:** 2026-10-08 11:50 by Claude.
- **The overnight build is done** (03:29). PLT-2 (Python project, venv, checks, CI) and CON-1 (contract schema v0) work locally.
- **The first variant** (a prototype, not a feature, in `prototypes/first_variant/`) runs end to end: 3.57 kg, one watertight body, seven pictures in `data/prototypes/first_variant/`.
- **This morning** the data and learning side was designed in discussion; the Data feature now has its page.
- **The web UI (PLT-4) works locally** (10:38-11:50). It follows the product from the contract through campaigns, hypotheses, designs and grades to the datapoints. The contracts are shown in full; everything downstream is laid out and blank until the agent, the geometry and the judge exist. 109 checks pass.
- **Nothing is committed.**

See [the build record](features/product/2026-10-08-decisions-and-build-record.md).

Every feature of zenryx: where it stands, who works on it, what comes next. Each feature's page holds the detail. How the board is kept is in [CLAUDE.md](../CLAUDE.md).

## Features

| Feature | Key | State | Now | Next | Who |
|---|---|---|---|---|---|
| [Product](features/product/status.md) | PRD | The plan of record. The contract's direction was decided on 8 October: published requirements; a verdict built from standards, with published values as a plausibility band; replayable graded tasks; GRC not used | PRD-3 (the engineer's questions before P0), under way | - | Manasvi |
| [Platform](features/platform/status.md) | PLT | PLT-2 (Python project, venv, checks, CI) works locally. PLT-4 (the web UI) works locally: five tabs from the contract to the datapoints (Flow, Contracts, Campaigns, Designs, Data), the contracts shown in full, the rest laid out blank; in PowerShell, `cd web` then `npm.cmd run dev` opens it on port 5190. Uncommitted; CI not yet run | PLT-2 and PLT-4, done locally | PLT-3: the runner and its guards | Claude |
| [Physics and the judge](features/physics/status.md) | PHY | Nothing built | - | PHY-1 (the FE solve): the cuDSS static solve copied from fastcae, with its parity test | - |
| [Contract](features/contract/status.md) | CON | CON-1 (contract schema v0) works locally: schema, validator, hash, three example contracts; its 83 checks pass (109 in all). Uncommitted; awaiting the engineer's review | CON-1, done locally | CON-2: check the examples' open points (bearing dimensions, the offset reading, A8) | Claude |
| [Data](features/data/status.md) | DAT | Designed in discussion (8 October): one contract is one task; the four axes; the datapoint kinds; campaigns cut into decision records, snapshot tasks and preference pairs; 20 task types; LLM fine-tuning and physics AI. Nothing built | - | DAT-1 (the record schema), once the engineer agrees the proposals | - |

## Planned features (a page each when their first PBI starts)

| Feature | Key | What | Phase |
|---|---|---|---|
| Gearbox domain | GBX | The EV two-stage archetype: the front-end (ratio split, gear sizing, shaft statics → bearing reactions), its ranges and regimes | P1 |
| Geometry | GEO | The CadQuery machined core, the design domain and keep-outs, the field-space shell and member grammar, realisation by B-rep or SDF | P1 |
| Optimise | OPT | Voxel topology optimisation with its filters, the relaxed bound, member sizing, the acquisition of FE proofs | P1 |
| Process | PRC | Process profiles (aluminium high-pressure die casting first, since 8 October), checks on the built part, the qualification rung | P1 |
| Campaign and agent | AGT | Campaign state, hypotheses, the deterministic arms, the agent's tools and brief | P2 |
| Benchmark | BEN | The registered protocol, the arms, the controls, the reports | P2 |
| Learning | LRN | The KPI model and ranker, the failure predictor, the field surrogate; later, LLM fine-tuning (data design §7-8) | P3 |
