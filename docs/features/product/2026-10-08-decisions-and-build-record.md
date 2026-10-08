# PRD-3: the engineer's questions, the decisions, and the overnight build

**What this is.** The record of the session of 7-8 October 2026 (from 20:20 IST) in which the engineer asked their questions before P0. It covers:
- every decision, in order;
- where each document is;
- the build started overnight, and how far it got;
- how to resume.

It exists because the session may be compacted (the engineer, 02:11).

---

## 1. Status now

**8 October, 11:50.**
- **The overnight build is done** (03:29). From 08:43 to 09:37 the engineer and Claude discussed the data and learning side; that discussion is documented (§2a).
- **The web UI (PLT-4) works locally** (10:38-11:50, decision 14). It follows the product from the contract through campaigns, hypotheses, designs and grades to the datapoints. The three contracts are shown in full; everything downstream is laid out and blank. In PowerShell, `cd web` then `npm.cmd run dev` opens it at http://localhost:5190; plain `npm` is refused by the default execution policy. Its design is [the UI design](../platform/2026-10-08-ui-design.md).
- **Committed on `product/end-to-end`, not pushed** (18:30-18:37), in five commits: feca5c1 (PLT-2, the Python project), f51aba1 (CON-1, the contract), cb0c4b3 (the prototype), 71bfc84 (PRD-3 and PRD-4, these docs), ca44539 (PLT-4, the web UI). The engineer has yet to answer four things:
  - the review of the contract spec and code;
  - assumptions A1-A8;
  - the motor-flange layout;
  - when to commit. Everything goes on one branch, `product/end-to-end`, until the workflow runs end to end (decision 15).

**The overnight build:**
- **Part A, PLT-2 (Python project, venv, checks, CI), is done locally.**
- **Part B, CON-1 (contract schema v0), is done locally:** 93 checks pass.
- **Part C, the first variant (prototype),** in `prototypes/first_variant/`, with outputs in `data/prototypes/first_variant/`. **Done:**
- `uv run python prototypes/first_variant/run.py` runs end to end in about 60 s and gives one watertight housing half: **3.57 kg**, 390 × 333 × 131 mm.
- **Clean on four checks:** nothing intrudes into the gears', bearings' or shafts' space; it is closed except at the split face and the shaft passages; it has no voids; draft is under 1° on only 0.17 % of the cast area.
- **Thickness:** 1.9 % of the area reads under 4 mm. That is the bolt-boss walls (4.1-4.5 mm) and the 4 mm shoulders, read through a ±1 mm voxel copy.
- **Pictures and README:** seven pictures in `data/prototypes/first_variant/`; the README is `prototypes/first_variant/README.md`.
- **Open for the engineer:**
  - the motor flange, raised by the subagent to clear the intermediate seat (its Ø110 spigot cleared that bore by only 0.8 mm in plan);
  - 11.6 cm³ of bolt bosses outside the A3 box;
  - no FE yet.
- CLAUDE.md is updated: how to build and check; GRC no longer used.
- **PRD-4** (fold the decisions into the plan) is done in its first pass. plan.md now carries the 8 October changes in its Status, §0, §7, §11, §12 and §15. decisions.md marks D3 re-taken and D4 widened.
- **Committed on `product/end-to-end`** (the five commits above), not pushed.

## 2. The decisions, in order

All were taken by the engineer; times are IST. **Bold** marks those that change the plan.

| # | When | Decision | Recorded in |
|---|---|---|---|
| 1 | 7 Oct 20:38 | **Target L1 (fixed interfaces), and build the contract, CON-1 (contract schema v0), first** | product page |
| 2 | 7 Oct 21:38 | **The GRC housing is not the design target.** "The whole idea is to see how our agentic data generation factory can create plausible designs possibly competing with the measurements and numbers published." The factory starts from published requirements, with no CAD | product page |
| 3 | 7 Oct 22:50 | "Compete" to mean both a head-to-head and a plausibility band. Replaced by #9 | - |
| 4 | 7 Oct 23:05 | Working rule: every id gets a short name in brackets, e.g. "D2 (first product family)" | Claude's memory |
| 5 | 8 Oct 00:14-00:42 | The requirements catalogue was written (15 engineer questions, the inputs, what the tools derive, 12 load cases, the gaps). The agent's inputs (the problem plus the evidence) are separate from the requirements (the exam). The product framing: one factory with two entry points (an existing part, or a requirement); LLM fine-tuning comes later, as a speed-up, and is not the product | contract page, Docs |
| 6 | 8 Oct 01:25 | **Every problem is a replayable graded task.** The contract is the question, with no answers; the frozen judge is the grader; anyone may attempt it; references and attempts are kept | contract page, Decisions |
| 7 | 8 Oct 01:32 | **An attempt hands in any geometry**: STEP, or a closed mesh for printed shapes, plus the process and the build or pull direction. Our recipe is optional | contract page, Decisions |
| 8 | 8 Oct 01:37 | **GRC is dropped from the load-tool checks too.** The load tool is built from published equations and checked against published worked examples (JTEKT eq. 5-29), an independent FE cross-check and fault injection, then the published band | plan §4.3, §14; product page |
| 9 | 8 Oct 01:50 | **No head-to-head on a single paper.** The proof is the verdict built from standards and guidelines. Published values form a plausibility band, and a design inside the published range is the achievement | product page |
| 10 | 8 Oct 01:46 and 02:02 | Defaults come from standards and the research, each labelled as an assumption. The housing's share of the misalignment tolerance defaults to half (A6) | spec §4.5 |
| 11 | 8 Oct 02:02 | **The first contract is Hofstetter et al. 2018** (Table 2: 165 mm, 9.32 ± 1 %, 366 N·m nominal input, 15,000 rpm, 944 h, 20MnCr5; Table 3: bearings). **D3 (first process) is re-taken: aluminium high-pressure die casting, with NADCA's rules.** **D4 is widened to cast surfaces.** **The geometry split: CadQuery builds only the machined core; the shell and structure are generated in field space and joined by a mesh boolean** | product page; decisions.md D3 |
| 12 | 8 Oct 02:06 | Overnight, while the engineer is away: the environment (PLT-2), the contract (CON-1), and one variant from the contract (a CadQuery core plus a field-space shell and structure), to see in the morning. Where the information is complete, go ahead. No commits or pushes | this file |
| 13 | 8 Oct 02:11 | Document everything; Claude works on its own | this file |
| 14 | 8 Oct 10:38 | **The UI is built as the end-to-end product,** starting from the contract: how each contract leads into campaigns, hypotheses, designs and grades, the agent's reasoning and next step, and the datapoints all of it becomes. fastcae's UI is copied for its design. A prototype's trials are not part of it. What does not exist yet stays blank, to be filled once the agent works | platform page, Decisions; [the UI design](../platform/2026-10-08-ui-design.md) |
| 15 | 8 Oct 18:20 | One branch for now: every PBI's work goes on `product/end-to-end` until the workflow runs end to end. Branches per PBI come back after that | CLAUDE.md (Branches); platform page, Decisions |
| 16 | 8 Oct 19:37 | **The first contract re-taken: Ivanov 2018** (KTH thesis for AVL; an EV two-stage helical reducer with full gear data), in place of Hofstetter, which becomes the second. The maximum input speed comes from a 160 km/h top speed. Hofstetter's bearing arrangement and 944 h life are borrowed, labelled. The process (die casting, D3) stands, its impact asked again | contract page, Decisions; product page; plan §0 and §12; [the Ivanov plan](../contract/2026-10-08-plan-ivanov2018-contract.md) |

**Still open** (none blocks tonight):
- Record the engineer's accept and reject choices? Proposed yes, for the data feature (DAT).
- The stress safety factor: no source yet; stress is recorded, not judged, in v0.
- Assumptions A1-A7 of the first contract (spec §4.8), each the engineer's to change: peak torques, gear grade N6, the installation space, the supports, the order-check speeds, the housing's share, the pull direction.
- The die-casting alloy of e-drive housings (not confirmed; the card from Kim et al. 2024 is used).
- The other papers (the agricultural EV gearbox, Jäger & Linde, Marano, Jixie chuandong) give band values only.

## 2a. The morning discussion, 8 October 08:43-09:37

These were questions and explanations on the data and learning side. No decision was taken; the proposals await the engineer. Each topic is documented in the [data design](../data/2026-10-08-data-tasks-and-learning-design.md) or the [job-description note](../../research/2026-10-08-job-descriptions-against-zenryx.md).

| When | The engineer asked | What was worked out | Documented in |
|---|---|---|---|
| 08:43 | Explain plainly what has been done | The direction, the three overnight builds, what is not done, what is needed | §1 above |
| 08:52 | Does every design task have its own contract, or does one contract with hypotheses make many tasks? | One contract is one task. Hypotheses and designs are attempts within it. New tasks come only from a changed requirement (variants, counterfactual pairs, priorities). The agent never changes the contract | data design §2 |
| 09:01 | Industry has variants of 4-5 housing families (the engineer's example: Mercedes-Benz rear axles HAG 183, 197, 205, 206). On which 1,000-10,000 datapoints would a rear-axle customer's models train? At least 20 examples | Five kinds of datapoint (contract, graded design, decision, engineer's choice, counterfactual pair). 23 examples for four hypothetical families. Four families give about 160 contracts, 10,000 graded designs and 14,000 decisions. A rear axle needs a hypoid load module | data design §1, §4 |
| 09:10 | Do torques and mode shapes cut through the datapoint axis, or sit on the evaluation axis? | Four axes: task, attempt, evaluation, result. The required torque is a task input; applied torques are evaluations, nearly free by unit-load superposition; mode shapes are results. Splits are by contract or family | data design §3 |
| 09:16 | What data does LLM fine-tuning use? | Decision records, not physics numbers. Imitation, preference and reinforcement learning with the grader | data design §7 |
| 09:22 | Two job descriptions (MEKINT; an AI-training role): what datapoints do they create, and where do we stand? | Their datapoints. A requirement-by-requirement table (done, partly, not yet). Five fastest gap-closers, starting with PHY-1 (the judge's FE solve) | job-description note |
| 09:29 | 20 clear data tasks; the fine-tuning process step by step; physics AI briefly | 20 task types with their graders; the seven steps of fine-tuning; the physics-model order and scorecard | data design §6-8 |
| 09:35 | Are the hypotheses and trials inside a campaign logged as separate datapoints and tasks? | Yes. Every step is a decision record. A decisive step can be frozen as a stand-alone task, with only what was known then. Alternatives make preference pairs. Same-campaign steps stay in one split | data design §5 |
| 09:37 | Document all the discussions and the current status | This section; the data feature's page and design; the research note; the board | - |

**Proposals awaiting the engineer** (data design §9):
- DAT-1, the record schema;
- DAT-2, snapshot tasks;
- DAT-3, recording the engineer's choices;
- DAT-4, the task export.

## 3. Where everything is

| What | Where |
|---|---|
| The board | [docs/status.md](../../status.md) |
| The plan of record (§4.3 and §14 updated tonight; the rest is to be folded in by PRD-4) | [plan.md](plan.md) |
| The decisions with their reasons (D3 re-taken tonight) | [decisions.md](decisions.md); the product page's Decisions, first two rows |
| The requirements catalogue (every row cited) | [../contract/requirements-catalogue.md](../contract/requirements-catalogue.md) |
| The papers read tonight, and Cognitive Design Systems (the competitor, an agent on Claude through MCP) | [../../research/2026-10-07-housing-papers-for-the-contract.md](../../research/2026-10-07-housing-papers-for-the-contract.md) |
| **The spec: the contract v0 design** | [../contract/2026-10-08-contract-v0-design.md](../contract/2026-10-08-contract-v0-design.md) |
| **The implementation plan** (Tasks 1-11) | [../contract/2026-10-08-plan-contract-v0-and-first-variant.md](../contract/2026-10-08-plan-contract-v0-and-first-variant.md) |
| The contract's decisions (replayable tasks; any geometry) | [../contract/status.md](../contract/status.md) |
| **The data and learning design** (8 Oct morning): tasks against attempts, the four axes, the datapoint kinds and 23 examples, cutting campaigns into tasks, 20 task types, LLM fine-tuning and physics AI | [../data/2026-10-08-data-tasks-and-learning-design.md](../data/2026-10-08-data-tasks-and-learning-design.md); the feature page [../data/status.md](../data/status.md) |
| The two job descriptions against zenryx | [../../research/2026-10-08-job-descriptions-against-zenryx.md](../../research/2026-10-08-job-descriptions-against-zenryx.md) |
| The first variant (prototype): how it works, its numbers, its pictures | [../../../prototypes/first_variant/README.md](../../../prototypes/first_variant/README.md); pictures in `data/prototypes/first_variant/` |
| The sources: PDFs and texts, out of git | `C:\Users\saxen\AppData\Local\Temp\claude\c--Work-fastcae-sim\2c7e1a14-cefc-44cf-904a-2eeeb2762236\scratchpad\papers\` (tonight's) and `...\c--Work-fastcae\f5baeb4a-...\scratchpad\` (`jl_2025.txt`, `pdf\hofstetter2018.txt`) |
| **The web UI** (PLT-4): its design, and the code | [../platform/2026-10-08-ui-design.md](../platform/2026-10-08-ui-design.md); `web/` (the UI), `src/zenryx/api/snapshot.py` (what it reads) |
| Claude's START HERE | memory `zenryx-start-here.md` |

## 4. The build, overnight: progress

Rewritten as each task finishes. The plan's tasks are the units.

| Part | Task | State | Notes |
|---|---|---|---|
| A, PLT-2 (Python project, venv, checks, CI) | 1. Project, venv, environment checks, CI file | **done locally, by 02:20** | `uv sync --all-extras` builds `.venv` from `uv.lock`. `uv run pytest checks -q` gives 10 passed: CadQuery builds an exact box, and gmsh, manifold3d, scikit-image, trimesh and pyvista import. Ruff check and format are clean. `.github/workflows/checks.yml` is written but has not run, since nothing is pushed. Versions: cadquery 2.8.0 on OCP 7.9.3.1.1, gmsh 4.15.2, manifold3d 3.5.4, scikit-image 0.26, trimesh 5.1, pyvista 0.49, pydantic 2.13, pytest 9.1, ruff 0.16 |
| B, CON-1 (contract schema v0) | 2. Units | **done by 02:30** | `src/zenryx/contract/units.py`: Quantity, Vector, one alias table, refusals list the allowed units; 16 tests |
| | 3. Entries | **done by 02:30** | `entry.py`: provenance rules (citation; tool, version and hash; assumption id; who and when); derived kind ⇔ derived provenance; bounded authority needs bounds; extra fields refused; 9 tests |
| | 4. Layers and the contract model | **done by 02:30** | `model.py`: every layer of spec §4; style rules (package needs the offset; gear_train needs its stages); casting needs pull directions and draft; a bare number is not a value; 11 tests. Test builders are in `checks/contract/builders.py` |
| | 5. Canonical JSON and hash | **done by 02:30** | `canonical.py`: canonical units, 12 significant digits, sorted keys, the hash excludes itself; `freeze()`; 7 tests. 53 checks pass in all |
| | 6. Validator | **done by 02:30** | `validate.py` with `involute.py`: schema, provenance, stage and consistency rules, each refusal with its rule, entry and reason; 19 + 3 tests |
| | 7. The example contracts (Hofstetter, the agricultural gearbox, the textbook case) | **done by 02:30** | `checks/data/contracts/make_examples.py` writes the three JSON files. Kim 2024 Tables 1 and 3 and Hofstetter Tables 2 and 3 were re-read from the PDFs with pypdf; the readings match. The agricultural gearbox's published centre distances follow from its gears (56.94 against 57, 96.99 against 97 mm). 13 tests. **CON-1 is done locally: 93 checks pass** |
| C, the first variant (prototype) | 8. Front-end sketch: layout and seat loads | **done by 02:42** (subagent) | `data/prototypes/first_variant/derived.json`.<br>- **Layout:** 25/65 and 23/82 give 9.270, inside 9.32 ± 1 %. a1 = 95.78 mm, a2 = 139.67 mm; the intermediate axis is at (51.2, 81.0) mm; the housing is 124.7 mm deep.<br>- **Independent statics check** (Claude, a scratchpad script): the seat forces on the housing sum to zero (within 0.1 N), and their moment about the shafts is ±3,026.7 N·m = (i − 1)·366 N·m, as the gearbox engineering report's §1.9 says.<br>- **Finding:** regeneration and reverse give identical static seat loads, since both reverse the torque. They differ only in rotation, which matters for noise, not for statics. So one of the two can be dropped from the static cases.<br>- **Largest seat load:** 29.9 kN at the output's back-wall bearing (6012), in regeneration |
| | 9. The CadQuery machined core | **done by 02:51** (subagent) | `core.step`, re-imported by Claude: 18 valid solids, 373 cm³ (about 1.0 kg). The three back-wall seat rings with the motor-flange ring; one mount pad; 14 Ø18 bolt bosses on the split plane |
| | 10. The shell and structure in field space | **done by 02:51** (subagent) | 1.5 mm voxels (286 × 210 × 99), 3.5 s, peak 362 MB. The shell and structure mesh is watertight, with 452k triangles and 1.30 L. **No enclosed voids.** Shell: 5 mm wall, 5 mm gap to the gears, 2° draft |
| | 11. Join, export, pictures | **done, 03:25** (subagent); **reproduced by Claude at 03:27 and 03:29** (identical summary except run times; about 60 s, peak 2.1 GB); lint fixed by ruff --fix and format | **The housing:** 3.58 kg at 2.66 g/cm³, 390 × 333 × 131 mm, 421,930 triangles, **watertight** (fixed after Claude's 02:56 report).<br>**Pictures** (in `data/prototypes/first_variant/`, each looked at by Claude):<br>- `layout.png`: gears, keep-outs, the drafted outline, bosses, flange, pad, the 165 mm offset;<br>- `iso.png`;<br>- `split_face.png`: the cavity with the gears as glass, and the back wall from outside;<br>- `section.png`: folded through the three seat axes;<br>- `thickness.png`;<br>- `draft.png`;<br>- `route.png`: core → field → joined.<br>**Measured:**<br>- wall thickness at least 2.83 mm, p5 4.5, median 5.0 mm; **1.9 % of the area is under the 4 mm minimum**, at the Ø18 bolt bosses and the seat-bore lips (the core's prototype sizes);<br>- draft under 1° on 0.38 % of the cast area;<br>- **taper direction checked by Claude on the mesh:** the walls narrow by about 36 mm per m of height from the split face to the back wall (about 2.1°), so it is widest at the rim, as a die-cast cup must be;<br>- the intermediate seat is a blind pocket, and the input and output bores go through |

## 5. What comes next: towards the agent that drives the factory

The engineer named agent development as the next step (02:06). The plan's order holds (§12): the agent needs a judge, a front-end and a geometry route to act through. Each item below is a PBI, and none is started.

1. **The judge, PHY-1 to PHY-4 (P0):**
   - copy the cuDSS static solve from `fastcae-v1`, with its parity test (a licence-clean reference mesh);
   - the analytic verification set and fault injection;
   - modes by shift-invert Lanczos;
   - the interface measures at the seats.

   The agent never computes a number, so this comes first.
2. **The load front-end, GBX-1 (P1):** from a contract's requirement, the ratio split, gear sizing, layout and seat loads. It must pass plan §4.3's three checks: worked examples, an independent FE cross-check, fault injection. The prototype's `frontend.py` is a first sketch of this; it is not that tool.
3. **The geometry route, GEO-1 (P1):** the CadQuery machined core built from a derived contract's interfaces, the field-space shell and members, and the join. The prototype shows the first look.
4. **Discovery, OPT-1 (P1):** voxel SIMP over the design domain, the relaxed bound and the casting filters.
5. **The agent, AGT (P2):**
   - the campaign state (plan §8.1);
   - the hypothesis record, with its status computed by code;
   - typed tools (§8.2): read, campaign-level, design-level and proof;
   - the deterministic acquisition that chooses which candidates get an FE proof;
   - the brief, holding rules only;
   - the fixed-workflow and heuristic arms beside it, and the kill criterion.

**What the engineer is asked in the morning:**
- review the spec and the code of CON-1;
- confirm or change assumptions A1-A8;
- say whether to commit, with the branches proposed below;
- look at the variant's pictures;
- choose the next PBI (the plan says PHY-1).

**Commits proposed** (none made):
- `platform/PLT-2-python-project`: pyproject, lock, `src/zenryx/__init__.py`, `checks/test_environment.py`, CI;
- `contract/CON-1-contract-v0`: `src/zenryx/contract/`, `checks/contract/`, `checks/data/contracts/`, the spec, the plan and the catalogue;
- `product/PRD-3-engineer-questions`: the docs of the session (record, decisions, plan §, research note, board, CLAUDE.md);
- the prototype separately, if the engineer wants it kept.

## 6. How to resume after a compaction

1. Read §1 and §4 of this file, then the implementation plan. Continue from the first task not marked done.
2. Run `uv run pytest checks -q` in `C:\Work\fastcae-sim` to see what passes.
3. Keep the rules:
   - no commits and no pushes without the engineer;
   - write files with the Write or Edit tool, never a Bash heredoc or PowerShell Set-Content;
   - one heavy job at a time, free memory checked first;
   - nothing from GRC, nothing imported from fastcae;
   - every id gets a short name.
4. When a task finishes:
   - mark it here;
   - rewrite the feature page it belongs to (Platform or Contract), and the board;
   - rewrite the START HERE memory.
5. In the morning, give the engineer a summary:
   - what runs;
   - where the pictures are (`data/prototypes/first_variant/`);
   - what is not checked (the prototype's front-end and its bearing dimensions);
   - the commits proposed, one per PBI on its branch.
