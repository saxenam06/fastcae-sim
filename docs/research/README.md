# Research log

**This repository's notes:**

| Date | File | Contents |
|---|---|---|
| 2026-10-04 | [2026-10-04-mechanical-ai-company.md](2026-10-04-mechanical-ai-company.md) | Company, CEO, open roles, application process |
| 2026-10-04 | [2026-10-04-ai-cae-landscape.md](2026-10-04-ai-cae-landscape.md) | AI-CAE agents, benchmarks, datasets, representations, competitors, gaps |
| 2026-10-04 | [2026-10-04-windows-tooling.md](2026-10-04-windows-tooling.md) | Which Python CAD / FEM / agent tools install on native Windows |
| 2026-10-04 | [../archive/design/2026-10-04-fastcae-audit-for-mekint.md](../archive/design/2026-10-04-fastcae-audit-for-mekint.md) | Read-only audit of `C:\Work\fastcae` and `C:\Work\fastcae-agent` against the post: public face, physics, agent, data; claims to correct; proposed order (*verified* in code, on disk and in git, file:line cited). Archived; fastcae keeps the committed copy |
| 2026-10-05 | [2026-10-05-cad-generation-and-bracket-datasets.md](2026-10-05-cad-generation-and-bracket-datasets.md) | Bracket datasets (SimJEB, DeepJEB, DeepJEB++, the GE challenge spec); approaches to CAD generation and which suits us |
| 2026-10-05 | [2026-10-05-perplexity-deep-research-prompt.md](2026-10-05-perplexity-deep-research-prompt.md) | Prompt for Perplexity Deep Research: research instructions plus the problem brief (`../archive/problem_bracket.md`). Save Perplexity's report here when it returns |
| 2026-10-05 | [2026-10-05-deepwheel.md](2026-10-05-deepwheel.md) | DeepWheel (arXiv 2504.11347): pipeline, physics, licence, what it lacks; wheels against brackets as our part family. Paper facts *verified* from the arXiv HTML |
| 2026-10-08 | [2026-10-08-job-descriptions-against-zenryx.md](2026-10-08-job-descriptions-against-zenryx.md) | MEKINT's Research Engineer post and a micro1-style AI-training post: what datapoints each creates, where zenryx stands on every requirement (done, partly, not yet), and the fastest ways to close the gaps that matter |
| 2026-10-08 | [2026-10-08-housing-sources-round-2.md](2026-10-08-housing-sources-round-2.md) | Seven sources the engineer sent on 8 October evening, read for one question: which gives the binding inputs and derives the rest, the housing included, by equations? **Maciejczyk and Zdziennicki 2011 (TU Łódź)** does: one industrial reducer from 22 kW to its gear case, the case's walls, bosses, flanges and bolts from the centre distance and bearing bores. That is the rule-based arm. Shigley Ch. 18 is the load chain, the template for GBX-1. Ivanov 2018 (KTH/AVL) is an EV reducer with full gear data (a fourth contract candidate). The KIT DAGA 2024 NVH dataset and Dhumal 2026 are CC BY-NC-ND. Each with its licence (*verified*) |
| 2026-10-07 | [2026-10-07-housing-papers-for-the-contract.md](2026-10-07-housing-papers-for-the-contract.md) | Nine housing sources read for CON-1 (contract schema v0): which give a requirement, a head-to-head, band values or methods. Hofstetter 2018 for the package-level requirement; the agricultural EV gearbox (Kim 2024, Son 2019/2020) as the two-stage head-to-head with measured mass and modes; Jäger & Linde 2025 for the planetary one; Cognitive Design Systems as the casting competitor |

**Verification status.** Items marked *verified* were fetched and read directly in the main session. Everything else came from research subagents and must be checked against the source before it is cited anywhere public (README, report, résumé, outreach). Several 2026 arXiv items are known only at abstract level.

**fastcae's research library,** read in place at `../../../fastcae/docs/research/` ([index](../../../fastcae/docs/research/README.md)). Its five reports of 6-7 October are the evidence the plan rests on:

| Report | What it covers |
|---|---|
| [Geometry and CAD technologies](../../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md) | What fastcae measured about each geometry technology; the engineer's 26 rules; the recommended stack |
| [Lessons from the plans](../../../fastcae/docs/research/2026-10-06-plans-lessons.md) | 56 binding decisions, 34 pitfalls, 25 contradictions |
| [Gearbox-housing engineering](../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md) | Judging at the bearing seats; fits under temperature; EV NVH; the gear-force front-end; typical values |
| [AM for metal housings](../../../fastcae/docs/research/2026-10-06-am-housings-rules-and-cases.md) | LPBF rules; NASA and ISO/ASTM qualification; printed housings; cost against casting |
| [AI technology for the platform](../../../fastcae/docs/research/2026-10-06-ai-technology-for-the-platform.md) | What is learnable; surrogates; agents with measured results; the order of learned models |

The sources those reports downloaded stay out of git, in a session scratchpad. Each report cites its sources by URL, so they can be fetched again (fastcae memory note `research-sources-2026-10-06`).
