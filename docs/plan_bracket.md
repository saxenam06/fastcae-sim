# fastcae-sim: the plan for sheet-metal brackets

**Date:** 5 October 2026.

**Status:** draft for review. Once approved, it becomes the plan of record and replaces
[plan_gearbox.md](plan_gearbox.md). From then on, where another document disagrees with it, this one holds.

**Who:** Manasvi Saxena, with Claude.

**Built from:**
- the bracket discussion of 4–5 October;
- the engineer's reference architecture,
  [design/bracket_ai_design_system_dataset_physics_ai_llm_runtime.md](design/bracket_ai_design_system_dataset_physics_ai_llm_runtime.md);
- the [problem statement](design/2026-10-05-problem-statement.md);
- the [research notes](research/README.md).

All numbers in examples are illustrative unless marked as measured.

---

## 1. Goal

**In one sentence:** an agentic system that turns an engineer's plain-language request into verified,
manufacturable sheet-metal brackets, and turns every iteration into verified data that trains physics AI and the
agent itself.

**Three deliverables, all in full:**
1. **Design agent:** request → verified brackets, with the physics explained.
2. **Agentic data-generation pipeline:** agents decide what to generate and how; tested tools build and judge.
3. **Learning:** physics AI (fast predictors, embeddings, a design proposer) and a fine-tuned LLM, fed back into 1
   and 2.

**What "solved" means.** All six must hold:

1. **Request → verified brackets.**
   - The request set (§6.6) and held-out request types are answered with brackets that pass the sheet-metal rules.
   - Each bracket is proven by FE against the vibration, shock, static and thermal requirements.
   - Each comes with its margins, assumptions and model validity.
2. **Physics first.**
   - Before designing, the agent states the governing numbers, the binding requirement and the mechanism.
   - Its hand models are checked against FE, with the error measured.
3. **An agentic pipeline that earns its keep.** At equal compute, it beats a scripted pipeline on the measures in
   §7, step 9. The dataset regenerates from one config.
4. **Learning that pays off.**
   - The physics-AI predictor has a measured false-pass rate on held-out request types.
   - After training, the agent needs measurably fewer rounds, or less cost, to reach a verified design.
5. **A real-world anchor.** At least three agent designs are made and tap-tested, with the measured first mode shown
   next to the prediction.
6. **Reproducible claims.** Every claim can be rebuilt from a commit and a config.

## 2. Motivation

Brackets are among the most common parts in vehicles, aircraft and machines. They are still designed by hand, late
in a program, around packaging changes, and in many variants. Vibration fatigue of brackets is a classic field
failure.

No tool today does all of the following:
- turns an engineer's plain-language request into manufacturable designs;
- verifies them against the requirements and explains them with physics;
- learns from each iteration.

Public bracket datasets cannot teach this (§3.3). The full problem is in the
[problem statement](design/2026-10-05-problem-statement.md).

**The work this plan answers.** These are the three responsibilities of Mechanical AI's *Research Engineer,
Mechanical Intelligence* role; the full vision is quoted in plan_gearbox.md §2:

> "Build agentic data-generation pipelines for high-fidelity, manufacturing-grade synthetic designs with
> embedding-friendly representations for neural network training."

> "Build modular tool interfaces and execution protocols for agentic design systems, spanning structural, fluid,
> heat-transfer, and aerothermodynamic analysis, as well as synthetic geometry generation through automated CAD
> operations."

> "Build and train state-of-the-art mechanical design agents that translate imagination into real-world designs by
> autonomously characterizing physical elements and governing principles."

## 3. Why brackets

### 3.1 Brackets against ribs on the GRC housing

| | Sheet-metal bracket | GRC ribs in design volumes |
|---|---|---|
| Can be shown publicly now | Yes: synthetic, entirely ours | No. It needs NLR's written OK; the drawings say "not to be reproduced"; it is a commercial Jahnel-Kestermann design |
| Understood in 5 seconds | Yes: every engineer has designed one | By drivetrain and heavy-industry engineers; others need it explained |
| Visual | The whole part changes; a gallery of concepts; mode-shape animations; an unfolded flat pattern | A big part with colourful FE, but the ribs are inside and designs differ subtly |
| Live demo | Yes: seconds per design | No: minutes per solve and 9–13 GB per mesh |
| Credibility | Judged against a real standard, but synthetic | Strongest: measured against the OEM's own design |
| Differentiation | Crowded: generative-design vendors all show brackets | Rare |
| Customers | Huge volume: automotive suppliers, EV, avionics, robotics, telecom | Fewer, high-value castings |
| FreeCAD fit | Natural: SheetMetal workbench, unfold → DXF, drawings, editable tree | Little added: the ribs are already OpenCascade code |
| MEKINT fit | Brackets are on their list; vibration and heat cover their dynamic and thermal must-haves | Transmissions are on their list, but the work is statics only today |
| Effort to a strong demo | New build (§7) | Mostly built, but it cannot be shown |

### 3.2 Closing the bracket's two weak rows

**Credibility:**
- real parts, tap-tested (§1, item 5);
- every grader check matched against exact answers and against CalculiX, and the comparisons published;
- a cross-solver check against DeepJEB's published Altair results (an open decision, §9);
- qualification against a vibration standard.

**Differentiation.** Others show organic, 3D-printed shapes under static loads. We show:
- sheet metal you can order today (a flat pattern, bend rules, a laser-ready DXF);
- vibration, fatigue, shock and heat qualified to a standard;
- the agent's physics reasoning on screen;
- a gallery of genuinely different concepts;
- measured real parts.

**The GRC work** stays in fastcae. Request NLR's written OK now, because it takes time. Until then, GRC-derived
results are shown to no one. Once approved, they are the strongest credibility piece.

### 3.3 Existing bracket datasets, and the gap

Details and sources are in [research/2026-10-05-cad-generation-and-bracket-datasets.md](research/2026-10-05-cad-generation-and-bracket-datasets.md).

| | SimJEB (2021) | DeepJEB (2024) | DeepJEB++ (June 2026) |
|---|---|---|---|
| Designs | 381, from human entries to the GE challenge | 2,138, generated from 263 SimJEB seeds | 15,360, generated from fewer than 400 seeds |
| Labels | 4 static load cases | 4 static load cases + first 2 free-free modes | Mass, stress, displacement |
| Licence | CC0, but the CAD is non-commercial (GrabCAD) | Open Data Commons Attribution | Not yet released |

**The gap.** All three are titanium brackets for additive manufacturing under static loads. None has:
- sheet metal;
- random vibration, fatigue or thermal results;
- plain-language requests;
- editable feature programs;
- design lineage;
- agent decision traces.

## 4. What we are building

1. **A specification given as numbers:**
   - fixed bolt and payload locations;
   - loads and environment;
   - envelope, process and objective.

   There are no design volumes and no CAD to attach; CAD is optional, for complicated surroundings. This is the
   convention of the GE Jet Engine Bracket Challenge behind SimJEB and DeepJEB.
2. **Designs as sheet-metal feature programs** (the "design DNA"). FreeCAD's SheetMetal workbench builds them into
   editable models, STEP files and laser-ready flat patterns.
3. **A grader.** Sheet-metal rules, FE, physics checks, validity and a trust label. It is the only authority on
   whether a design passes.
4. **Three intelligence layers,** from the reference architecture:
   - design generation and search;
   - physics AI;
   - the engineering LLM agent.

   The LLM never learns physics, and physics AI never runs the workflow.
5. **Agentic data generation.** Five agent roles decide what to generate and how. Deterministic tools build and
   judge.
6. **Learning:**
   - physics AI (fast predictor, mesh model, embeddings, design proposer);
   - validity maps;
   - a fine-tuned LLM.

## 5. Principles

- **Verified only inside a resolved project context.** A design is called verified only when the engineer's request,
  the program's context and the specification are all present. A concept mode may work from rough numbers; its
  results list their assumptions and are never labelled verified.
- **FE is the authority.** Physics AI screens and ranks; FE proves. The LLM chooses strategy, and the optimiser
  chooses numbers.
- **Nothing unverified becomes training truth.** Only results with a VALID trust label are used for training, and
  runtime results join the training pool only after full verification.
- **Agents act only through typed tools.** Their own code enters only through the gate (§6.3).
- **Rules live in a retrieval layer, not in model weights.** This covers standards, manufacturing rules and material
  data, so a rule change needs no retraining.
- **The LLM sees a compact engineering state**, such as hot spots, the dominant mode region and the weak connection,
  never raw FE tensors.
- **Every claim is reproducible.** One commit, one config, manifests with every setting.
- **An independent build.** fastcae-sim does not depend on fastcae or any other repository. It refers to their
  learnings and cites them: design decisions, pitfalls, measured results. Code is copied only when a step needs it,
  at the smallest unit that does the job:
  - a function or a module;
  - a whole file only when the whole file is needed;
  - never a directory or a repository in bulk.

  Every copied piece records its origin (repository, path, commit) and comes with a test in this repository. Where
  its behaviour must match the original, that test is a parity test (§6.10).

## 6. How it works

### 6.1 The specification

```
structure     face orientation; bolt holes (positions, size)
payload       mass, centre of gravity, footprint, its bolt pattern, power
environment   vibration profile, shock, static g-loads, ambient     ← mostly from the program context
requirements  first mode, fatigue damage, shock margin, temperature, mass or cost limits
space         envelope box; keep-out boxes
process       sheet material, gauges, bend radius, joining methods
objective     minimum mass | minimum cost
```

- **Every value carries its source:** the request text, the program context, a datasheet or a default.
- **Program-context profiles** (body electronics, engine-mounted, truck, and so on) hold the standards, environments
  and rules. They live in the retrieval layer.
- **What is missing cannot be claimed.** If shock is not specified, the result cannot claim shock qualification.

### 6.2 The design representation (design DNA)

| Representation | What it is | Used by |
|---|---|---|
| **A. Feature program** | Concept, parameters and an ordered list of operations, with lineage (parent → child) | Agents, the optimiser, the proposer |
| **B. CAD** | FreeCAD `.FCStd` (editable tree), STEP, flat-pattern DXF | Manufacturing checks, FE, the engineer. The source of truth for geometry |
| **C. Mesh graph and point cloud** | Nodes and elements with materials, boundary conditions and loads | Physics AI |

**The sheet-metal grammar.** Every operator has preconditions, parameters, constraints and a result:

| Kind | Operators |
|---|---|
| Structural | add or remove flange · side walls · gusset or dart · bead · close the section · change the load path |
| Thickness | change gauge · local doubler |
| Geometry | move hole · flange length · bend angle and radius · bend relief · lightening hole · hem |
| Joining | spot-weld, clinch or rivet seam |
| Isolation | isolator mounts at the bolts |

### 6.3 Generation

**The approach is agentic parametric generation with physics in the loop.** The agent never draws free-form geometry.
It edits feature programs through typed tools, and FreeCAD builds them.

LLM-written CAD code is unreliable for exact specifications. In RealCADBench (Sept 2026), 9 frontier models writing
FreeCAD code from industrial requirements reached 57–81 % executability and 0.28–0.54 solid IoU. Topology
optimisation suits printing and casting rather than sheet metal.

**Design sources (populations):**

| Source | What it adds |
|---|---|
| A. Space-filling (Sobol, Latin hypercube) | Even coverage, good designs and bad |
| B. Engineering mutations | Meaningful single changes from a parent |
| C. Combinations | Several operators together |
| D. Boundary cases | Designs near manufacturing, resonance, stress and thermal limits |
| E. Negative designs | Designs meant to fail: the shape of the infeasible space |
| F. Optimiser paths | High performers, and the path from poor to good |
| G. Agent designs | Concepts and strategies with reasoning traces |
| H. Invented features | New operators written by the agent, through the gate |
| I. Learned proposer (later) | Nearly-right feature programs proposed from the specification |

**Bead placement is guided by physics** in the spirit of topography optimisation: beads go where the strain energy
of the failing mode is concentrated, then they are snapped to beads that can actually be formed.

**The gate for invented features:**
1. The feature runs in a sandboxed process.
2. It is tested on a plain sheet, then on brackets.
3. It passes the sheet-metal rules, including a valid flat pattern.
4. The engineer approves it.

After the gate it becomes a new operator, and the factory can sweep it.

**A quality-diversity archive** (MAP-Elites) keeps the best design of each kind in every cell. For example, the cells
can be payload mass × frequency target × concept.

### 6.4 The grader

**The pipeline:**
1. build;
2. check geometry and sheet-metal rules (failures get structured records);
3. mesh;
4. place interfaces and boundary conditions;
5. set up the load cases;
6. solve and post-process;
7. run the physics checks and validity flags;
8. assign the **trust label** (VALID / QUESTIONABLE / INVALID);
9. give a verdict against the specification.

**Physics in version 1:**
- modal analysis;
- random vibration from base excitation;
- fatigue (Steinberg or Dirlik, plus Miner);
- shock;
- static g-loads;
- bolted joints (simplified VDI 2230);
- thermal, at L0 and L1 (an open decision, §9).

**Boundary conditions:**
- clamped zones at the bolts (washer footprint plus compression cone);
- the payload coupled to a mass at its centre of gravity (RBE2- or RBE3-type);
- base excitation entering at the clamped zones;
- heat input through the payload contact;
- convection and radiation from free faces.

**A ladder of models**, each with validity limits that are measured from the data:

| Level | Models | Used for |
|---|---|---|
| L0 | Single mass + Miles, beam and plate formulas, a thermal resistance network | Governing numbers, screening, the binding requirement, in milliseconds |
| L1 | FE: modal superposition, random response, fatigue, steady conduction | Grading, in seconds |
| L2 | Refined FE, cross-checked with CalculiX | The gold set and finalists |

**Physics checks on every run:**
- mass equals the CAD mass;
- six rigid-body modes in the free-free run;
- reactions under 1 g equal the weight;
- effective masses add up to the total mass;
- mesh convergence on a sample;
- units.

**Fault injection** keeps testing the checks themselves.

### 6.5 The agents

The same five roles work at runtime and in the data factory:

| Role | At runtime | In the data factory |
|---|---|---|
| **Spec agent** | Request → specification; asks only the questions that block | Writes requests: paraphrases, incomplete requests, edits, hard cases |
| **Campaign agent** | Plans the campaign: concepts, variables, evaluation order, when to stop | **Curator:** plans each batch from coverage, predictor uncertainty and failures (active learning) |
| **Design agent** | Concepts, mutations, strategy (stiffen, move the mass, isolate) | Designs into gaps. As the **inventor**, writes new features through the gate |
| **Diagnosis agent** | Explains failures from the compact engineering state and picks the fix strategy | **Quality checker:** investigates quarantined runs and anomalies, and proposes fixes |
| **Evidence agent** | The report: requirement → value → margin → model → assumptions | The dataset card; every claim with its evidence |

**Deterministic tools** do everything else: the builder, the validator, the mesher, the solvers, the checks, the
optimiser and the database.

**Active learning.** The curator sends new FE runs where they teach the most:
- where the predictor is uncertain;
- near a constraint boundary;
- where designs are physically or geometrically novel;
- near a promising optimum;
- where predictors disagree.

### 6.6 The dataset

**One record per design:**
- design: id, parent, feature program, CAD, geometry hash;
- analysis: load cases, boundary conditions, mesh, solver, convergence, verification;
- physics: scalars, modes, random and fatigue results, thermal, fields;
- verdict: pass or fail, failure mode, confidence, trust label;
- lineage: operator, parameters, parent results;
- agent trace;
- the request, with its paraphrases.

Worked examples are in the [walkthrough](design/2026-10-05-end-to-end-walkthrough.md).

**Four layers of physics output:**
1. global scalars;
2. modal and NVH results (frequencies, effective masses, RMS response);
3. thermal results;
4. full fields (displacement, stress, mode shapes, temperature).

**Requests that differ.** Examples of the range:
- a complete, stiffness-driven request;
- a long overhang with welding banned;
- a cost objective where heat is the binding limit;
- isolation, the opposite strategy;
- a severe engine profile with material and bolt limits;
- an edit of an earlier request;
- an incomplete request, where the right response is questions.

Each request is stored with 3–5 paraphrases, all checked to resolve to the same specification.

**Design pairs and deltas.** These teach what a change does:
- parent → child;
- failed → repaired;
- trade-off pairs;
- the same geometry under a different load case;
- the same concept under a different process.

**Hindsight relabelling.** A design that fails one specification is stored as a valid answer to the looser
specification it does meet.

**Multi-fidelity funnel:** many designs at L0, most at L1, and a **gold set** at L2.

**Honest tests.** Test sets hold out whole request types. They are frozen before any generation.

**First-release targets:**
- about 300 synthetic project contexts;
- about 10,000 designs verified at L1, and about 500 at L2;
- 500–2,000 agent trajectories, set by the token budget.

### 6.7 Training

**Physics AI**, trained in stages: static → modal → random vibration → thermal → coupled.

| Model | Learns | Used for |
|---|---|---|
| Fast scalar predictor | Feature program + geometry descriptors + specification → mass, f1–fN, effective masses, RMS g, fatigue damage, stress, temperature, pass/fail | Screening thousands of candidates |
| Mesh model (graph network) | Mesh graph + boundary conditions + loads → displacement, stress, mode shapes, temperature. Modes are matched before computing the loss | Fields, hot spots, diagnosis |
| Embedding | All designs | Similar-design search, novelty, detecting unfamiliar designs |
| Design proposer | Relabelled specification → feature-program pairs | Nearly-right starting designs |
| Validity maps | L0 against L1 against L2 on every design | Evidence-based rules for when each model can be trusted |

**How training is done:**
- the data loss plus physics-consistency losses (equilibrium, the eigenproblem, energy);
- training on deltas as well as absolute values;
- ensembles for uncertainty;
- a domain gate: outside the validated domain, a design goes to FE.

**The LLM:**
- **Capabilities:**
  - extracting the specification, and detecting what is missing;
  - planning the campaign;
  - choosing tools;
  - diagnosing failures;
  - knowing when not to trust physics AI.
- **Stages:**
  1. supervised fine-tuning on requests, states and actions, diagnoses and recoveries;
  2. preference tuning (a good action against a merely plausible one);
  3. trajectory training;
  4. optionally, reinforcement learning, **with the reward computed from verified physics, never from physics-AI
     predictions**.
- **Model:** a small open-weight model with LoRA, on a paid cloud GPU.
- **Evaluation:** on held-out tasks, against the Claude-driven agent.

### 6.8 Runtime

1. **Request.** Plain language, plus a short form showing the numbers extracted from it.
2. **Specification check.** Gaps are filled from the program context and flagged. Only the questions that block are
   asked. What is missing is not claimed.
3. **Characterise.** The governing numbers and the binding requirement. Example: required stiffness
   k = m(2πf)² ≈ 1.9 kN/mm, and a thermal budget of 20 K over 15 W = 1.3 K/W.
4. **Campaign.** Concepts with their physics reasons, and the reasons any are ruled out.
5. **Generate.** Candidates with their lineage, through the validator.
6. **Screen.** Physics AI with uncertainty and the domain gate.
7. **Select.** A mix of the best predicted, uncertain, novel, near-boundary and diverse candidates.
8. **FE (L1).** Then diagnosis, then a design change: the LLM picks the strategy and the optimiser picks the numbers.
   Steps 5–8 repeat.
9. **Verify the finalists (L2)** and build the evidence package.
10. **Export.** The FreeCAD file with its editable tree, STEP, flat DXF, a TechDraw drawing and the report.

Runtime results join the training pool only after verification.

### 6.9 Showing creativity and innovation

1. **Concept atlas.** One request fills a live gallery of genuinely different passing brackets.
2. **The invention moment.**
   - The archive shows an empty region.
   - The agent explains mechanism → principle → feature, and writes the feature.
   - The feature passes the gate and FE, and joins the library.
   - The factory fills the region with it.
3. **Beads placed by physics.** The strain energy of mode 1 is shown, beads are placed along it, and the frequency
   jumps. A rule-of-thumb bead is shown next to it for comparison.
4. **Strategy, not just shape.** For the IMU request, the agent isolates instead of stiffening, and explains why.
5. **Novel-and-better scoreboard.** Feasibility, performance and novelty, measured.
6. **Rules nobody wrote down.** Patterns mined from the dataset.
7. **Real parts.** Tap-tested, with the measured first mode shown next to the prediction.
8. **From request to a laser-ready DXF in minutes.**

### 6.10 Reuse from other repositories

This follows the independent-build principle (§5).

**Referred to, not copied:** fastcae's lessons. Examples:
- solver parity practice;
- re-meshing noise as the floor for claims;
- the hypothesis-before-solve, reflection-after pattern;
- the guards against running out of memory.

They are cited where they shape a decision here.

**Candidates to copy, each only if a step needs it.** From the list in plan_gearbox.md §9:
- physics-check functions;
- the manifest and lineage writer;
- the solver-deck writer, for cross-checks;
- the agent-harness pattern;
- the GPU solver, only if solid elements are chosen in step 4.

Each piece is copied at the smallest unit, with its origin recorded and a parity test.

**Not needed:** the rib library, CP-SAT rib repair, and any code specific to the GRC housing.

## 7. The plan

Days are working days and are estimates.

| # | Step | Done when | Days |
|---|---|---|---|
| 0 | **Decisions and engineering data sources:** version-1 scope; vibration profiles, fatigue curves, sheet-metal rules, damping, contact and convection values | Scope written here; every engineering number has a source we're allowed to use | 1–2 |
| 1 | **Repository, environment, FreeCAD spike:** uv, Python 3.12, CI; FreeCAD with SheetMetal running headless in its own process; the reuse rule (§5, §6.10) written into the repository's `CLAUDE.md` so every session follows it | 200 random feature programs build to `.FCStd`, STEP and flat DXF, with recompute time and failure rate measured | 2–3 |
| 2 | **Specification schema and program context** | The seven example requests resolve to valid specifications | 1–2 |
| 3 | **Builder v1:** the sheet-metal grammar, interfaces built from the specification's numbers, regions named on creation | At least 95 % of space-filling programs build; CAD mass equals FE mass; flat patterns are valid | 4–6 |
| 4 | **Grader v1 and verification:** shell or solid elements decided by benchmark first | <ul><li>Exact-answer benchmarks pass</li><li>CalculiX agrees on 20 brackets: frequencies within about 1 %, stresses within a few percent</li><li>100 % of injected faults caught</li><li>Trust labels assigned</li><li>Time per design measured</li></ul> | 7–10 |
| 5 | **Characterise and L0 models** | Each hand model's error against FE is measured and stored | 2–3 |
| 6 | **Agent-ready:** MCP tools, records and provenance, the agent harness with five roles, budgets and traces, request generation | <ul><li>A scripted client builds and grades through the tools alone</li><li>The dataset regenerates from its config</li><li>One full agent session runs within budget</li><li>Paraphrases are checked automatically</li></ul> | 5–7 |
| 7 | **Rehearsal:** held-out sets, the scripted baseline and its measures, a pilot | <ul><li>Held-out sets frozen</li><li>Measures computed automatically</li><li>Pilot of 5 requests done</li><li>The engineer audits 50 random records</li></ul> | 3–4 |
| 8 | **The design agent, with real parts** | <ul><li>The seven requests are answered with verified designs and a concept gallery</li><li>Three designs are made and tap-tested</li></ul> | 4–6, plus fabrication lead time (order at step 6) |
| 9 | **Agentic data generation at scale, against the scripted pipeline** | <ul><li>Equal-budget comparison reported on: coverage, distinct concepts, predictor error on held-out types, novel-and-better designs, bad labels caught</li><li>Dataset v1 released with its card</li></ul> | 3–5, plus runs |
| 10 | **Physics AI v1 and active learning** | <ul><li>Predictors scored on held-out types, with the false-pass rate measured</li><li>Active learning beats random sampling at an equal FE budget</li></ul> | 6–8 |
| 11 | **LLM fine-tuning** | Supervised fine-tuning and preference tuning done; evaluated against the Claude agent on held-out tasks | 5–8, plus GPU time |
| | **Total** | | **about 43–64 days, i.e. 7–11 weeks** |

**Milestones:**
- **M1, the foundation** (after step 7, about weeks 4–6): agents generate their first verified data.
- **M2, the public demo** (after step 9, about weeks 6–8): the design agent with real parts, and the agentic-versus-scripted result.
- **M3, learning** (after step 11, about weeks 7–11): trained predictors and a fine-tuned agent, measured against
  the baseline.

**When to apply:** at the end of step 8. Steps 9–11 then become follow-ups that show pace.

**Order of risk.** Three risks come first:
- **FreeCAD SheetMetal running headless** (step 1);
- **shell versus solid elements for thin sheet** (the start of step 4);
- **usable engineering data sources** (step 0).

**Running alongside, without blocking:**
- the physical-test kit: a fixture, a 1.2 kg dummy mass, an accelerometer, a fabricator;
- the request to NLR;
- the vibration-standard purchase decision.

## 8. Risks

| Risk | How it is handled |
|---|---|
| FreeCAD SheetMetal is slow or fragile headless | Spike first (step 1). Typed failure records. A CadQuery builder as a fallback, only behind a parity test |
| Thin sheet is inaccurate or slow in FE | Benchmark shells against solids at the start of step 4, against exact answers and CalculiX |
| Engineering data cannot be used legally | Every number needs a source (step 0). ISO 16750-3 is a paid standard; MIL-STD-810H is public |
| "Synthetic" weakens credibility | CalculiX parity, exact-answer benchmarks, an optional DeepJEB cross-check, real parts tap-tested |
| Crowded space | The differentiation list in §3.2, shown, not claimed |
| The agents don't beat the scripted pipeline | The equal-budget comparison decides. Budgets are capped |
| The agent games the predictor | The reward comes from verified physics only. Winners are re-checked at L2 |
| Self-training drift | Only VALID records train models. Runtime data joins only after verification |
| LLM token cost | Budgets per role. Trajectory counts are set by budget |
| Laptop memory and compute | Small models first. Cloud batch later |
| The plan drifts | Each step ends on a measured result. This document is updated at each milestone |

## 9. Decisions

| Decision | When |
|---|---|
| Sheet-metal brackets (structural mechanics and NVH) for the public demo. The GRC ribs stay in fastcae until NLR gives its written OK | 5 Oct 2026 |
| All three deliverables in full, including LLM fine-tuning | 5 Oct 2026 |
| FreeCAD (SheetMetal) as the builder. CadQuery only as a fallback batch builder behind a parity test | 5 Oct 2026 |
| The specification is given as numbers: no design volume, CAD optional | 5 Oct 2026 |
| Verified designs only inside a resolved project context. Concept mode is labelled not verified | 5 Oct 2026 |
| An independent build. Other repositories' learnings are referred to. Their code is copied only when needed, at the smallest unit (function, module, or a whole file only when needed), never in bulk, with its origin recorded and a test | 5 Oct 2026 |

**Open. Each has a recommendation; confirm or change on review:**
1. **The generation approach and sources** in §6.3. *Recommended.*
2. **The engineer's architecture as the reference** (three layers, trust labels, active learning, staged training,
   design pairs). *Recommended; this plan already follows it.*
3. **Thermal in version 1.** *Recommended at L0 and L1 (steady conduction). It covers MEKINT's thermal must-have at
   low cost.*
4. **Shell or solid elements.** *Decided by benchmark at the start of step 4.*
5. **A DeepJEB cross-solver check.** *Recommended: static load cases, about 50 designs.*
6. **Vibration profiles.** Buy ISO 16750-3, or use MIL-STD-810H, which is public, plus published values.
7. **Licences.** *Recommended: Apache-2.0 for code and CC BY 4.0 for data.*

## 10. Documents in this repository

| Document | Status |
|---|---|
| [plan_bracket.md](plan_bracket.md) | **This plan: draft for review** |
| [plan_gearbox.md](plan_gearbox.md) | The previous plan, for gearbox housings (5 October) |
| [design/bracket_ai_design_system_dataset_physics_ai_llm_runtime.md](design/bracket_ai_design_system_dataset_physics_ai_llm_runtime.md) | The engineer's reference architecture, followed by this plan |
| [design/2026-10-05-problem-statement.md](design/2026-10-05-problem-statement.md) | The problem, with no solution |
| [design/2026-10-05-end-to-end-walkthrough.md](design/2026-10-05-end-to-end-walkthrough.md) | Worked examples of the dataset, training and runtime (numbers illustrative) |
| [design/2026-10-05-ui-flow.md](design/2026-10-05-ui-flow.md) | The runtime UI, screen by screen. It assumes attached CAD; for brackets the "reading CAD" screen becomes the specification form (§6.1) |
| [design/2026-10-04-agentic-data-factory-brief.md](design/2026-10-04-agentic-data-factory-brief.md) | The earlier reasoning for the bracket thread |
| [research/](research/README.md) | Company, landscape, tooling, CAD generation and bracket datasets |
| [design/2026-10-04-fastcae-audit-for-mekint.md](design/2026-10-04-fastcae-audit-for-mekint.md), [design/2026-10-05-recipes-not-a-menu-design.md](design/2026-10-05-recipes-not-a-menu-design.md) | The GRC thread |
