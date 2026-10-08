# zenryx docs

The directory: every document of this repository is reachable from here. Start with the board, [status.md](status.md). How the work is organised is in [CLAUDE.md](../CLAUDE.md).

## The board and the features

| Feature | Status page | Its other documents |
|---|---|---|
| The board | [status.md](status.md) | Every feature's state, who works on it, what comes next |
| Product | [features/product/status.md](features/product/status.md) | The plan of record, [plan.md](features/product/plan.md); the decisions with their evidence, [decisions.md](features/product/decisions.md); the record of the 7-8 October session, its decisions and the overnight build, [2026-10-08-decisions-and-build-record.md](features/product/2026-10-08-decisions-and-build-record.md) |
| Platform | [features/platform/status.md](features/platform/status.md) | The repository, the Python project, checks and CI, the runner, the API and UI. The web UI's design, from the contract to the datapoints: [2026-10-08-ui-design.md](features/platform/2026-10-08-ui-design.md) |
| Physics and the judge | [features/physics/status.md](features/physics/status.md) | Mesh, statics, modes, the uniform-temperature case, interface measures, the deterministic verdict, the verification set |
| Contract | [features/contract/status.md](features/contract/status.md) | The design contract: provenance, authority and kind on every entry, units, frames, the validator. Its spec [2026-10-08-contract-v0-design.md](features/contract/2026-10-08-contract-v0-design.md); the implementation plan [2026-10-08-plan-contract-v0-and-first-variant.md](features/contract/2026-10-08-plan-contract-v0-and-first-variant.md); the [requirements catalogue](features/contract/requirements-catalogue.md) |
| Data | [features/data/status.md](features/data/status.md) | The record of every task and attempt, and the tasks made from it: [2026-10-08-data-tasks-and-learning-design.md](features/data/2026-10-08-data-tasks-and-learning-design.md) (tasks against attempts, the four axes, the datapoint kinds, 20 task types, LLM fine-tuning, physics AI) |
| The first variant (a prototype, not a feature) | [../prototypes/first_variant/README.md](../prototypes/first_variant/README.md) | One die-cast housing half from Hofstetter's requirement: the CadQuery core, the field-space shell and members, the join, the pictures |

A new feature starts from [features/_template.md](features/_template.md).

## Research and inputs

| Where | What |
|---|---|
| [research/](research/README.md) | This repository's notes: the AI-in-CAE landscape, the mechanical-AI company, Windows tooling, CAD generation and bracket datasets, DeepWheel; the housing papers read for the contract, and Cognitive Design Systems (7 October); two job descriptions read against zenryx (8 October) |
| `../fastcae/docs/research/` ([index](../../fastcae/docs/research/README.md)) | fastcae's research library. Its reports of 6-7 October are the plan's evidence: [geometry](../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md), [plans](../../fastcae/docs/research/2026-10-06-plans-lessons.md), [gearbox engineering](../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md), [AM](../../fastcae/docs/research/2026-10-06-am-housings-rules-and-cases.md), [AI](../../fastcae/docs/research/2026-10-06-ai-technology-for-the-platform.md) |
| `../fastcae/docs/inputs/` ([index](../../fastcae/docs/inputs/README.md)) | Documents from outside: the engineer's plans of 6 October, the reviewer's suggestions and links, the Q&A record, earlier plans and strategies |

## The archive

[archive/](archive/) holds this repository's plans of 4-5 October, superseded by the plan of 7 October. They are a gearbox housing generated in FreeCAD and benchmarked on GRC, a sheet-metal bracket, and their design briefs.
