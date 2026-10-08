# Product

zenryx designs housings from requirements. A gearbox's functional interfaces, loads, package, targets and one manufacturing process go in. Housings come out that are FE-proven and pass the process's rules, each labelled with its rung, together with the whole campaign: every hypothesis, decision and physical consequence. A general platform; the first family is an EV two-stage reducer housing. This page holds the plan of record every other feature follows, and its decisions.

**PBI key:** PRD · **State:** the plan of record. PRD-3 (the engineer's questions before P0) is under way: the direction for the contract is decided (Decisions, first row) · **Updated:** 2026-10-08 01:40 by Claude
**Code:** none - the plan and decisions the other features follow

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| PRD-3 | The engineer's questions before P0, answered, and anything they change folded in. Under way: the direction and the first contract are decided (Decisions, first two rows) | The engineer says P0 may start |
| PRD-4 | **First pass done locally (8 Oct, about 02:40, uncommitted):** plan.md Status, §0, §7, §11, §12 and §15, and decisions.md D3 and D4, carry the 8 October changes. Left: the engineer's review. Fold the 7-8 October decisions into the plan and decisions.md, as PRD-2 did. That means: published requirements; the standards-based verdict with a band; replayable tasks; die casting (D3); D4 widened; the geometry split; GRC dropped | plan.md sections 0, 4, 5, 7, 11, 12, 14 and 15, and decisions.md D3 and D4, say what the Decisions table says |

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
| The direction for CON-1 (contract schema v0), from PRD-3 (the engineer's questions before P0) | - **Level:** L1 (fixed interfaces); the contract is built first.<br>- **Inputs:** published requirements, with no CAD start. The requirement comes package-level, as in Hofstetter 2018, or as a given gear train.<br>- **Proof:** the verdict built from standards and guidelines (gear alignment, bearing tilt, order separation, buildability, package). Published values form a plausibility band: a design inside the published range is the achievement. No paper is picked just for a head-to-head (the engineer, 8 Oct 01:50). This replaces the 22:50 "head-to-head plus band".<br>- **GRC** is not the target, and its deck is not used for the load check either. The load tool is built from published equations and checked by worked examples, an independent FE cross-check and fault injection (plan §4.3).<br>- **Tasks:** every problem is a replayable graded task, with any geometry accepted as an attempt (contract page) | 2026-10-07 21:38 to 2026-10-08 01:37, the engineer |
| The first contract, the process, the geometry split | - **The first requirement:** Hofstetter et al. 2018 (Magna, two-stage EV reducer), Table 2: 165 mm total centre distance, ratio 9.32 ± 1 %, 366 N·m nominal input, 15,000 rpm maximum input, 944 h, 20MnCr5; Table 3: the benchmark's bearings. The others (the agricultural EV gearbox, Jäger & Linde, Marano) give band values only.<br>- **D3 (first process) re-taken: aluminium high-pressure die casting** with NADCA's rules, in place of LPBF. Printing makes the most creative demo, but casting is the series process and where the competitor works.<br>- **D4 (SDF-built printed regions count) widened to cast surfaces.** As-cast tolerances are tenths of a millimetre; only machined faces must be exact. Still gated in P1 against the B-rep route.<br>- **The geometry split:** CadQuery builds only the machined core (seats with stock, the split face with bolts and sealing face, mount pads, motor flange, ports). The closed shell and all structure are generated in field space with the casting rules, then joined by a mesh boolean.<br>- **Defaults** come from standards and the research, each labelled as an assumption; the engineer may override them. The housing's share of the misalignment tolerance defaults to half | 2026-10-08 02:02, the engineer |
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

- [2026-10-08-decisions-and-build-record.md](2026-10-08-decisions-and-build-record.md): PRD-3's record. The 13 decisions of 7-8 October in order, where every doc is, the overnight build's progress, and how to resume.
- [plan.md](plan.md): the plan of record.
- [decisions.md](decisions.md): every decision, with its options, evidence, consequences, gains and losses.
- The evidence, in fastcae's library: [the research index](../../../../fastcae/docs/research/README.md), its five reports of 6-7 October, and [the inputs](../../../../fastcae/docs/inputs/README.md).
