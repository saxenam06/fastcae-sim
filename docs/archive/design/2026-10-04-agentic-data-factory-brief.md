# Project brief: agentic design and data factory for vibration-qualified brackets

*Status: draft for review, 2026-10-04. It records the reasoning so far and the proposed direction. This is not yet the spec.*

## Summary

We are building an open-source system for **sheet-metal mounting brackets** that must pass **vibration (NVH) and
structural requirements**. It delivers three capabilities, **all of them full deliverables**:

1. **Design agent.** An engineer's request goes in. Out comes a checked, manufacturable design with a STEP file,
   a flat pattern and an engineering report.
2. **Agentic data factory.** The same tools run at scale. An AI agent steers generation towards what the dataset is
   missing, including genuinely new designs. The output is a dataset of manufacturable designs with physics labels,
   machine-learning-ready representations and the agent's decision logs.
3. **Learning.** Embeddings, fast predictors, validity maps and an agent benchmark, trained or measured on the
   dataset and fed back into 1 and 2.

All three stand on one foundation: a **physics grader**. It evaluates any bracket design and reports *where* and
*by how much* it fails. It uses models whose validity limits are known, checked against exact answers and an independent solver.
**Generators** feed designs into all three, with increasing freedom, from parametric templates up to agent-invented features.

The project exists to get you hired as **Research Engineer, Mechanical Intelligence** at Mechanical AI (MEKINT).
It is a working, small-scale version of the system that job builds.

---

## 1. Where this started: the goal

- **Your goal:** apply to Mechanical AI's *Research Engineer, Mechanical Intelligence* role.
- **What we found about the company** (verified; see `docs/research/`):
  - It is a seed-stage startup of about 3 people in Pittsburgh. The seed round closed in April 2026, and four roles are open.
  - **CEO: Jinwook Lee.** He has a PhD in Aerospace Engineering from MIT and designed turbomachinery components for SpaceX's Raptor engine.
  - The application form takes only name, phone, email and résumé. There is no cover letter.
- **Conclusion:** a résumé alone carries very little signal. The strongest lever is **proof of work**: a working system
  that already does a slice of the job. Link it at the top of the résumé and send it directly to the founders.

## 2. What the job actually asks for

| Job posting says | What it means in practice |
|---|---|
| "Agentic data-generation pipelines for high-fidelity, manufacturing-grade synthetic designs" | Software that produces large numbers of realistic, manufacturable designs with trustworthy physics labels |
| "…with embedding-friendly representations for neural network training" | Each design stored in forms neural networks can learn from (parameters, CAD programs, point clouds, meshes) |
| "Modular tool interfaces and execution protocols" (structural, fluid, thermal, aerothermal, CAD) | The agent's "hands and eyes": reliable, typed tools for CAD and analysis that catch their own errors |
| "Build and train mechanical design agents… characterizing physical elements and governing principles" | Agents that reason from physics, plus data and graders that can train them |
| Must-have: "identifying governing parameters and establishing appropriate reduced-order models" | Knowing which simple model is valid, when it breaks, and proving it |

Reading the four open roles together suggests MEKINT's architecture: an LLM agent with sub-agents calling CAD
and analysis tools, a synthetic-design data engine (the CAD Engineer role "builds CAD templates for synthetic designs"),
and their own models trained on that data.

## 3. Your fit and the quality bar

- **Your background:** mechanical FEA, structural dynamics, multibody dynamics, NVH, AI and agentic AI, now moving into
  physics AI and agent-driven CAE. Structural dynamics and NVH are built on reduced-order thinking (modal reduction,
  Craig-Bampton, SDOF and Miles' equation, effective mass), which is exactly the must-have.
- **Your requirement:** *"best and proper way; no academic demos."* So the bar is:
  - **Verified solvers.** Checked against exact answers and an independent solver, automatically on every change.
  - **Simplified models with stated validity limits.** Their error is measured against full analysis across the dataset.
  - **Real requirements:**
    - real standards (ISO 16750-3 vibration and shock);
    - real manufacturing rules (sheet metal);
    - sourced material data.
  - **Production software:**
    - typed tool inputs that carry units;
    - reproducible runs;
    - tests, continuous integration and documentation.

## 4. What the research showed: where the gaps are

*From a research sub-agent. Individual papers still need checking before they are cited publicly.*

- **Access to tools is not the gap; reliability is.** Several projects already wrap FreeCAD, CalculiX or Ansys for agents.
  Published studies keep finding that agent-run simulations **run but are physically wrong**, and nothing flags it.
- **No benchmark checks whether an agent picks a valid simplified model** and moves to a fuller one when the
  assumptions break.
- **No open dataset of 3D CAD parts with vibration-mode labels and the CAD program attached.** Existing bracket
  datasets (SimJEB, DeepJEB) are static-only or come from a single family on commercial solvers.

These gaps shape what the project emphasizes: physics checks built into the tools, validity limits, modal and
random-vibration labels, and open, program-level data.

## 5. Choosing the problem

| Option | Verdict |
|---|---|
| **A. Electronics mounting brackets** under vibration, shock and thermal requirements | **Chosen.** Your home ground (structural, NVH). Rich in CAD geometry, so a strong fit for synthetic design data. Every design can be solved at full detail on a laptop |
| B. E-drive mount system (multibody, hydraulic mounts) | Mostly tuning mount positions and stiffnesses; weak on CAD and geometry data |
| C. Many shallow part families using textbook formulas | Looks like an academic demo, which is exactly what we want to avoid |
| D. High-speed rotor and bearings | Directly relevant to the CEO's turbomachinery background. **Kept as a possible second family**, because the framework does not depend on the part family |

**Decision (yours): brackets, focused on structural mechanics and NVH. The design agent, the data factory and the
learning layer are all full deliverables; none is a side feature.**
Trade-off accepted: there is no direct turbomachinery link to the CEO in the first release.

## 6. Core ideas settled in discussion

### 6.1 Build time vs runtime
- **Build time (you and me):**
  - I write the code, tests and documentation.
  - You are the lead engineer: you approve the physics, the criteria and the results.
- **Runtime (afterwards):**
  1. the **design agent** answers one engineering request at a time;
  2. the **data factory** runs the same tools in batch, thousands of times, without a human;
  3. **learning** on that data, which produces fast predictors, validity maps and a benchmark, feeds back into 1 and 2.

### 6.2 The grader is the core asset; nobody supplies "true solutions"
- A design problem has many valid answers and no single correct one. What *can* be made reliable is the
  **evaluation of a given design**.
- The grader returns, for every check: **value, limit, margin, the model used, and whether that model was valid**,
  plus sensitivities. That tells the agent where it failed, by how much, and which parameters matter.
- **Your expertise goes into making the grader correct:** the physics, the criteria, the validity limits, and the
  checks against exact answers and independent solvers. If the grader is wrong, everything trained on it learns the wrong thing at scale.

**What the bracket grader contains:**
- **Physics:**
  - modes and effective mass;
  - random vibration (response PSD, then RMS acceleration and stress, then fatigue with Steinberg or Dirlik plus Miner's rule);
  - shock;
  - quasi-static g-loads;
  - bolted joints (simplified VDI 2230);
  - heat path from the module to the chassis;
  - sheet-metal manufacturing rules.
- **Damping:** swept as an assumption, not guessed.
- **Model ladder and validity limits:**
  - **Single-mass model plus Miles' equation.** Valid only if mode 1 dominates the effective mass, modes are well
    separated, and the input spectrum is flat near resonance.
  - **Modal superposition FE (L1).** Needs enough modes (≥ 90 % effective mass, up to 1.5× the top input frequency)
    and a rigid module (octave rule).
  - **Steinberg fatigue** applies only to narrow-band response; otherwise **Dirlik** is used.
- **Checks:**
  - exact answers: cantilever and Leissa plate modes, Kirsch stress concentration, Miles, Dirlik versus rainflow counting;
  - CalculiX as an independent solver;
  - physics invariants on every run: mass, six rigid-body modes, equilibrium, energy balance;
  - fault injection: we deliberately break inputs and prove the checks catch it.

### 6.3 What the dataset is for

| Data | Used for |
|---|---|
| Design → performance (good **and** bad designs) | Fast predictors, embeddings, maps of where simple models hold |
| Request → valid design (labelled backwards: every working design answers the requirements it meets) | Training models that propose designs from a request |
| Benchmark task → best-known design | Scoring how close an agent gets |
| Agent attempts → failures → fixes | Training agents to adapt; the grader acts as the reward |

Failed designs are not waste. Prediction models need them to learn where failure is, and agents need them to learn recovery.

### 6.4 Producing good designs without hand-designing each one
- Random designs are mostly bad, so the generator works the way an engineer does:
  1. a first-principles first guess (e.g. required stiffness k = m(2πf)², then a plate formula, then the thickness);
  2. variations around that guess;
  3. an optimizer that pushes a share of designs to top performance;
  4. extra samples near the pass/fail boundary;
  5. a slice designed by the agent.
- **Speed funnel:** fast models screen many designs in milliseconds, L1 grades thousands, and L2 checks a sample.

### 6.5 Templates
- A **template** is a small CAD program for a family of parts. You set knobs (thickness, flange lengths, bolt
  pattern, beads) and it:
  - checks manufacturing rules **before** building;
  - outputs STEP and the flat pattern;
  - **names the important faces** (bolt faces, module mounting face), so analyses set themselves up automatically.
- Templates make every design manufacturable and analyzable, and their knobs are a ready-made ML input.
  They are also where your expertise is stored once and reused.

---

## 7. The problem: templates limit innovation

Templates solve the "random designs are junk" problem, but they create a new one:

- Designs can only be **variations of the shapes we wrote down**.
- A dataset built only from templates is a **dataset of familiar ideas**.
- Models trained on it, and agents using it, can only **reproduce** those ideas. They can never discover a better *kind* of design.
- That contradicts MEKINT's goal of expanding the mechanical and topological complexity that design can reach.

So the core tension is **reliability (manufacturable, analyzable, sensible) vs novelty (genuinely new designs)**.

## 8. The proposed solution

### 8.1 Separate judging from generating
The grader evaluates **any** geometry: STEP file, then mesh, then FEM, with loads and supports found from named
or detected faces. **Evaluation never limits innovation.** Only the generator needs structure, and that structure can loosen step by step.

### 8.2 A ladder of design freedom

| Level | How designs are made | Novelty | Reliability |
|---|---|---|---|
| L1 Fixed templates | Knobs on known families (L, U, Z, hat) | Low | High |
| L2 Feature building blocks | Combine beads, ribs, gussets, flanges, cut-outs and holes anywhere the rules allow, like LEGO pieces rather than fixed models | Medium: combinations nobody drew | High |
| L3 Agent-invented | The agent writes a new feature or template in CAD code. The grader and the manufacturing rules check it. If it passes review, it **joins the library** | High | Medium |
| L4 Topology optimization | Physics decides where material goes, with no template. The result is turned into manufacturable sheet-metal features (beads and ribs where the material wants to be) | Highest | Needs that conversion |

Every dataset record notes which level produced it.

### 8.3 Reward diversity as well as quality
Plain optimization collapses onto one "best" shape, which is boring by construction. We use a **quality-diversity
archive** (MAP-Elites; Mouret & Clune, 2015):

- Divide the space of *design characteristics* into cells, for example
  *mass × first natural frequency × load-path type*.
- **Keep the best design found in every cell.**
- The dataset then spreads across many different kinds of good design instead of piling up around one familiar shape.

### 8.4 The agent as curator and inventor: this is what makes the factory "agentic"
A plain parameter sweep is not agentic. In our factory the agent closes the loop:

1. **Reads the dataset's state:**
   - coverage of requests, performance and design embeddings;
   - empty archive cells;
   - pass rates;
   - recurring failures.
2. **Decides the next batch:**
   - where to sample;
   - which generator level to use;
   - how much of the compute budget to spend at each fidelity level.
3. **Designs into gaps.** When existing templates and features *cannot reach* a region (for example "under 80 g and
   above 400 Hz"), it **invents** a new feature or template (L3).
4. **Diagnoses failures:**
   - meshing errors;
   - invalid geometry;
   - suspicious physics flags.

   It proposes fixes, and any change to library code goes through tests and your review.
5. **Grows the library.** Successful inventions are promoted, so the factory's vocabulary expands over time.

Numbers stay deterministic: the agent decides what to do, and the tested tools compute every result.

### 8.5 Innovation is also strategy, not just shape
When a bracket fails its frequency target, the physics offers different strategies:
- **stiffen** (bead, gusset, thickness);
- **move the mass;**
- **isolate** (soft mounts, so the resonance sits below the input);
- **add damping.**

Choosing the right strategy from the governing parameters is often where real innovation lies. The generator
supports at least **stiffen, relocate and isolate** (isolators modelled as spring-dampers at the bolts). Damping
treatments come later.

### 8.6 Measuring innovation
Using design embeddings:
- **novelty** is the distance from the nearest existing or template design;
- **quality** is the margins and the mass.

The headline metric: **designs that are both novel and better than the best template design**. That turns
"the agent is creative" from a claim into a measured result.

### 8.7 Closing the loop: fine-tuned models back in the factory
The data trains a model, the model runs in the factory, and the factory produces better data. In ML this is called
expert iteration or self-training.

```
 factory, agent v0 (Claude) ──► designs ──► GRADER (physics) ──► dataset
          ▲                                                       │
          │                                                       ▼
 agent v1 (fine-tuned) ◄──── fine-tune on graded successes + recoveries
          │
          └── must beat v0 on held-out benchmark tasks before replacing it
```

The model learns **decisions** (which template, which strategy, which model level, how to repair), not physics.
The tools still compute every number. Four safeguards keep the loop improving instead of drifting:

1. **The grader is the judge.** Without an independent physics judge, training on its own outputs degrades the model ("model collapse").
2. **Protect diversity.** Training on its own best outputs narrows the model. The quality-diversity archive, novelty
   measures and fresh template-level data in every training mix counteract that.
3. **Stop it gaming the grader:**
   - only labels from models used within their validity limits count;
   - record-breaking designs are re-checked at full fidelity;
   - fault injection keeps testing the checks themselves.
4. **Held-out benchmark.** Some tasks are never used for training, and every new version must beat the old one on them.

Practical notes:
- Claude cannot be fine-tuned here, so we use a small open-weight model with LoRA and compare it with the Claude-driven agent.
- It needs **paid cloud GPU time**.
- It overlaps with MEKINT's ML Research Engineer role, which shows we understand how our data gets used.

### 8.8 Guardrails
- **Manufacturability:** every design, whatever its source, must pass sheet-metal rules (including a valid flat
  pattern), or be tagged for another process.
- **Physics validity:** every label records which model produced it and whether that model was valid.
- **Duplicates:** near-identical designs are removed using embeddings.

## 9. How the factory runs

```
            ┌──────────────────── CURATOR AGENT ─────────────────────┐
            │ reads coverage, archive gaps, novelty, failure stats   │
            │ decides where next, which generator, compute budget    │
            └──────┬──────────────────────────────────────▲──────────┘
                   │ batch plan                           │ stats and gaps
                   ▼                                      │
 REQUEST      →  GENERATORS     →  GRADER          →  DATASET        →  LEARNING
 SAMPLER         L1 templates      physics,           geometry in       embeddings,
 realistic       L2 features       criteria,          many forms,       predictors,
 requirement     L3 agent-made     validity,          labels per        pass/fail model,
 sets            L4 topology opt.  margins            model level,      novelty scores
                 + optimizer                          decision logs
```

## 10. What you show Mechanical AI

- **The repo:** grader, tools, generators, design agent, factory, learning and tests, built with Claude Code
  multi-agent workflows (named in the posting).
- **Design agent demo:** a request in plain English becomes a checked bracket, with its STEP file, flat pattern and report,
  including the agent's reasoning about which models were valid and why it chose to stiffen, move the mass or isolate.
- **Factory demo:** the curator agent finds a gap, designs into it, and invents a feature that templates could not produce.
- **A dataset release:**
  - manufacturable brackets, with modal, random-vibration, shock and thermal labels;
  - the CAD program, STEP, flat pattern, mesh, point cloud and embeddings;
  - a dataset card.
- **Learning results:**
  - measured validity maps (e.g. where Miles' equation holds);
  - fast-predictor accuracy;
  - fault-injection detection rates;
  - benchmark scores for the design agent;
  - **novel-and-better designs found by the agent.**
- **A short video** covering the two demos.

Each item maps to a line in the job posting.

## 11. Decisions

**Made (by you):**
- domain: brackets, structural mechanics and NVH;
- scope: **all three capabilities in full**: design agent, agentic data factory, learning;
- **stage 8 approved:** fine-tune a small open model and close the loop (needs paid cloud GPU time);
- quality before speed.

**Proposed by me, awaiting your confirmation:**
1. **Process:** sheet metal first; machined brackets later.
2. **Standard:** ISO 16750-3 (automotive) vibration and shock profiles; aerospace profiles later, as data.
3. **Strategies in scope at first:** stiffen, relocate, isolate. Damping treatments later.
4. **Generator levels in the first release:** L1 and L2, then L3 (agent-invented) as the highlight. L4 (topology optimization) after that.
5. **Tooling:** native Windows, Python 3.12, CadQuery, gmsh, scikit-fem, CalculiX as the independent check, MCP for the tool interface,
   Claude Agent SDK using your Claude Code login.

## 12. Next steps

1. You review this brief.
2. I present the remaining design section by section: architecture and component boundaries, data formats,
   error handling, testing and verification.
3. A written spec goes to `docs/superpowers/specs/`, then the implementation plan, then the build. Each sub-project
   ends in something tested and usable, and each depends on the ones before it:
   1. **Grader:** physics, acceptance criteria, validity limits, checks against exact answers and an independent solver.
   2. **Tool layer:** typed tools with units, physics checks on every run, job running, caching and provenance.
   3. **Generators L1–L2 plus optimizer:** templates and free combinations of features.
   4. **Design agent:** request to checked design and report, plus benchmark tasks.
   5. **Agentic data factory:** curator agent, quality-diversity archive, L3 agent-invented features.
   6. **Learning:** embeddings, fast predictors, validity maps, novelty measures.
   7. **L4 topology optimization, cloud batch runs, dataset release.**
   8. **Closing the loop (fine-tuning):** fine-tune a small open-weight model (LoRA, cloud GPU) on graded designs
      and agent decision logs. It replaces the Claude-driven agent in the factory only after beating it on held-out
      benchmark tasks. See section 8.7.
