# Product

zenryx designs housings from requirements. A gearbox's functional interfaces, loads, package, targets and one manufacturing process go in. Housings come out that are FE-proven and pass the process's rules, each labelled with its rung, together with the whole campaign: every hypothesis, decision and physical consequence. A general platform; the first family is an EV two-stage reducer housing. This page holds the plan of record every other feature follows, and its decisions.

**PBI key:** PRD · **State:** the plan and its decisions written, for the engineer's review; nothing built · **Updated:** 2026-10-07 11:15 by Claude
**Code:** none - the plan and decisions the other features follow

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| PRD-1 | The engineer's review of the plan: decisions D2-D13, and the changes proposed from the Q&A record (Open) | Manasvi · - · - | 2026-10-07 | The engineer is reading [decisions.md](decisions.md); D1 is decided. Next: the engineer's answers, then PRD-2 |

## Next

| PBI | Goal | Done when |
|---|---|---|
| PRD-2 | The engineer's decisions and the accepted changes folded into the plan | [plan.md](plan.md)'s sections and its section 15 say what was decided, with the date |

## What runs

Nothing yet. The plan's phase P0 (the judge, the contract) starts once PRD-1 ends.

## Rules in force

- **The claim:** every design carries its rung: simulation-feasible, process-rule-feasible, process-simulated, prototype-validated or production-qualified. Never "production-ready". The plan, section 7.
- **Derived physics is computed, never written:** by deterministic, versioned tools; the deterministic evaluator decides PASS or FAIL. The plan, sections 2-4.
- **A general core:** nothing in the core names a part; domain roles live in domain modules.
- **Independence from fastcae:** nothing imported; code copied from `fastcae-v1` with a parity test each. See [CLAUDE.md](../../../CLAUDE.md).

## Measured

Carried from fastcae (`C:\Work\fastcae`), the numbers the plan rests on:
- the 8 GB card's single-precision ceiling, 412,667 TET10 (2.18 M unknowns) solved in 15 s, 40 s with assembly;
- fastcae's re-mesh noise, 0.98 % on displacement and 1.32 % on strain energy.

Sources: fastcae's simulate page, and the plan, section 5.3.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| Where the product lives (D1) | **This repository, `fastcae-sim`, the package `zenryx`, independent of fastcae.**<br>- Nothing is imported. Code is copied from fastcae's tag `fastcae-v1` where needed, each copy with a parity test; the rest is built from scratch.<br>- fastcae stays the rib application, frozen.<br>- A long-lived branch in fastcae was weighed and not taken: only a separate repository makes the two independent by construction. | 2026-10-07 09:11-11:03, the engineer |

## Open

- **Decisions D2-D13** wait for the engineer: the family, the process, SDF regions as geometry, the CAD, the physics, the verdict's measures, the least member, the benchmark, compute, the agent's model, the material rule, when to show the work, the topology engine. See [decisions.md](decisions.md).
- **Changes proposed from the engineer's Q&A record** (Claude, 7 October 08:53). The record is [Complete_Agentic_Gearbox_Housing_QA_and_Implementation.md](../../../../fastcae/docs/inputs/plans/Complete_Agentic_Gearbox_Housing_QA_and_Implementation.md). These changes wait for the engineer's word before the plan is edited.
  - **Adopt:**
    1. The hypothesis as the agent's unit of work: a physical claim, its formulation, expected effect, falsifying test, budget and status. The plan's "formulation" goes inside it.
    2. Candidate failure against hypothesis failure: deeper optimisation, sensitivity, the Pareto frontier, comparison across hypotheses at fair budgets. Each hypothesis gets its own budget and its own bound on the screen; code computes its status, and the agent allocates the FE budget.
    3. Sensitivity and intervention records as first-class data, nearly free from the member grammar's adjoint, with FE checking a few.
    4. A deterministic regime report after the baseline solve: which interface measure binds, strain-energy shares by region, modal proximity, fit margin.
    5. The structural reasoning ontology (5-10 regimes, physics heuristics only, written before any run) as a P0 artifact. It is the rule set of the adaptive no-LLM arm and the agent's knowledge alike. Lessons learned from runs stay in product mode.
    6. The kill criterion stated plainly: if the agent does not beat the adaptive algorithmic arm in P2, it is not fundamental, and P3's data runs on that arm.
    7. A learned hypothesis prior (regime → the hypothesis that paid), at one label per campaign; product mode or arm 4 only.
  - **Correct:**
    - "bearing_displacement ≤ 40 µm" → relative seat tilt per face width, and centre-distance change.
    - The 900 Hz first mode → a Campbell check.
    - `verified: true` → a rung.
    - "Feasibility model first" → a calibrated KPI model and ranker first.
    - The agent at phase 7, after the dataset → built in P2 beside the deterministic arms.
    - Five V1 hypotheses with lattice → four.
    - An LLM-stated confidence → recorded, while code computes the status.
  - **Net effect:** sections 3, 8, 9 and 11 change; P0 gains the ontology and the regime report (about +2-3 days).
- **Before P1, the engineer's limits for the first archetype:**
  - the housing's share of each stage's misalignment budget (no public source gives it);
  - the bearing type at each seat;
  - the modal criterion (which orders, which speed band);
  - the safety factors;
  - the margin over model uncertainty.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|
| - | The plan and the decision record, written in fastcae (its PRD-8) on five research reports and moved here | 2026-10-06/07 | fastcae 391ad27, bb16927, 6719dc2 |

## Docs

- [plan.md](plan.md): the plan of record.
- [decisions.md](decisions.md): every open decision, with its options, evidence, consequences, gains and losses.
- The evidence, in fastcae's library: [the research index](../../../../fastcae/docs/research/README.md), its five reports of 6-7 October, and [the inputs](../../../../fastcae/docs/inputs/README.md).
