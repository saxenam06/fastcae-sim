# Product

zenryx designs housings from requirements. A gearbox's functional interfaces, loads, package, targets and one manufacturing process go in. Housings come out that are FE-proven and pass the process's rules, each labelled with its rung, together with the whole campaign: every hypothesis, decision and physical consequence. A general platform; the first family is an EV two-stage reducer housing. This page holds the plan of record every other feature follows, and its decisions.

**PBI key:** PRD · **State:** the plan of record, every decision taken (7 October); nothing built; the engineer's questions come before P0 · **Updated:** 2026-10-07 11:48 by Claude
**Code:** none - the plan and decisions the other features follow

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| PRD-3 | The engineer's questions before P0, answered, and anything they change folded in | The engineer says P0 may start |

## What runs

Nothing yet. The plan's phase P0 (the judge, the contract) starts after the engineer's questions (PRD-3).

## Rules in force

- **The claim:** every design carries its rung: simulation-feasible, process-rule-feasible, process-simulated, prototype-validated or production-qualified. Never "production-ready". The plan, section 7.
- **Derived physics is computed, never written:** by deterministic, versioned tools; the deterministic evaluator decides PASS or FAIL. The plan, sections 2-4.
- **The agent's unit of work is a hypothesis:** a physical reason in front of each formulation. Code keeps its budget and computes its status. The plan, section 3.
- **The kill criterion:** if the agent does not beat the adaptive rule-based arm at equal budget in P2, it is not fundamental. The plan, 11.1.
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
| D2-D13 ([decisions.md](decisions.md)) | **Each as recommended:**<br>- the family: an EV two-stage reducer, both housing parts designed;<br>- the process: LPBF AlSi10Mg with machined interfaces;<br>- printed regions built through an SDF count as real geometry, gated in P1;<br>- the core in CadQuery;<br>- the physics: statics and modes in P1, a uniform temperature and park lock in P2, cosine seat loads;<br>- the verdict: interface measures in µm and mrad;<br>- the least member: 4 mm, the voxels discovering and the members carrying the sizes;<br>- the benchmark: four arms and a pre-registered pass mark;<br>- compute: the laptop, then the cloud for 1,000 problems;<br>- the agent: Claude Code;<br>- the material rule for two materials deferred;<br>- showing the work: after P1;<br>- the topology engine: fastcae's cube model, extended | 2026-10-07 11:41, the engineer |
| The engineer's Q&A record | **Adopted:** the hypothesis as the agent's unit of work, with its bookkeeping by code; the kill criterion.<br>**Accepted:** the seven corrections.<br>**Not now:** the ontology (LLM reasoning first; textbook knowledge only if that reasoning stops producing good designs), sensitivity records, a learned hypothesis prior | 2026-10-07 11:41, the engineer |
| Where the product lives (D1) | **This repository, `fastcae-sim`, the package `zenryx`, independent of fastcae.**<br>- Nothing is imported. Code is copied from fastcae's tag `fastcae-v1` where needed, each copy with a parity test; the rest is built from scratch.<br>- fastcae stays the rib application, frozen.<br>- A long-lived branch in fastcae was weighed and not taken: only a separate repository makes the two independent by construction. | 2026-10-07 09:11-11:03, the engineer |

## Open

- **The engineer's questions before P0:** to come, in a session opened in this repository (PRD-3).
- **Before P1, the engineer's limits for the first archetype:**
  - the housing's share of each stage's misalignment budget (no public source gives it);
  - the bearing type at each seat;
  - the modal criterion (which orders, which speed band);
  - the safety factors;
  - the margin over model uncertainty.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|
| PRD-2 | The engineer's decisions and the accepted changes folded into the plan: sections 0, 3, 5.3, 6.1, 8, 9, 10, 11, 12, 15 and 16, and decisions.md marked decided; merged into `main` | 2026-10-07 | the commit that records this row |
| PRD-1 | The engineer's review: D2-D13 accepted as recommended; from the Q&A record, the hypothesis and the kill criterion adopted, the corrections accepted, the ontology and the rest deferred | 2026-10-07 | - (a decision) |
| - | The plan and the decision record, written in fastcae (its PRD-8) on five research reports and moved here | 2026-10-06/07 | fastcae 391ad27, bb16927, 6719dc2 |

## Docs

- [plan.md](plan.md): the plan of record.
- [decisions.md](decisions.md): every decision, with its options, evidence, consequences, gains and losses.
- The evidence, in fastcae's library: [the research index](../../../../fastcae/docs/research/README.md), its five reports of 6-7 October, and [the inputs](../../../../fastcae/docs/inputs/README.md).
