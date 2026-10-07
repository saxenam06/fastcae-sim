# Status: the board

**Updated:** 2026-10-07 11:48 by Claude

Every feature of zenryx: where it stands, who works on it, what comes next. Each feature's page holds the detail. How the board is kept is in [CLAUDE.md](../CLAUDE.md).

## Features

| Feature | Key | State | Now | Next | Who |
|---|---|---|---|---|---|
| [Product](features/product/status.md) | PRD | The plan of record: every decision taken (7 October); nothing built | - | PRD-3 the engineer's questions before P0 | Manasvi |
| [Platform](features/platform/status.md) | PLT | The repository is set up (PLT-1 done): CLAUDE.md, the board, the docs; no code yet | - | PLT-2 the Python project, its own venv, `checks/` and CI | Claude |
| [Physics and the judge](features/physics/status.md) | PHY | Nothing built | - | PHY-1 the cuDSS static solve copied from fastcae, with its parity test | - |
| [Contract](features/contract/status.md) | CON | Nothing built | - | CON-1 `HousingDesignSpec` v0 and its validator | - |

## Planned features (a page each when their first PBI starts)

| Feature | Key | What | Phase |
|---|---|---|---|
| Gearbox domain | GBX | The EV two-stage archetype: the front-end (ratio split, gear sizing, shaft statics → bearing reactions), its ranges and regimes | P1 |
| Geometry | GEO | Core templates in CadQuery, the design domain and keep-outs, the member grammar, realisation by B-rep or SDF | P1 |
| Optimise | OPT | Voxel topology optimisation with its filters, the relaxed bound, member sizing, the acquisition of FE proofs | P1 |
| Process | PRC | Process profiles (LPBF AlSi10Mg first), checks on the built part, the qualification rung | P1 |
| Campaign and agent | AGT | Campaign state, hypotheses, the deterministic arms, the agent's tools and brief | P2 |
| Data | DAT | The record tree, the crosswalk, manifests, the formats | P0-P3 |
| Benchmark | BEN | The registered protocol, the arms, the controls, the reports | P2 |
| Learning | LRN | The KPI model and ranker, the failure predictor, the field surrogate | P3 |
