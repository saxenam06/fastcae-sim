# fastcae-sim: the plan

**Date:** 5 October 2026.

**Status:** direction agreed; development starts 6 October 2026, with steps 0 and 1.

**Who:** Manasvi Saxena, with Claude.

This is the plan of record. Where another document in this repository disagrees with it, this one holds. The
list of documents is at the end.

---

## 1. Goal

**In one sentence:** a design agent that turns an engineer's requirements into verified, manufacturable
designs.
- The designs are generated as parametric CAD, judged by physics, and recorded, so every iteration becomes
  knowledge.
- It is shown on cast gearbox housings, and the production GRC housing is the benchmark to beat.

**What "solved" means.** All four must hold:

1. **A housing from requirements.**
   - The input is the GRC gearbox's own requirements: bearing layout, bearing loads, mounting interface,
     envelope, gear space, process.
   - From those, the agent generates rule-valid housings, each proven by FE.
   - It reports how close it comes to the production housing, or how far it beats it, with both judged by the
     same grader.
2. **Physics first.** Before designing, the agent states what governs the goal - load path, governing seat,
   mechanism, governing parameters, and a simple model with its error. It then checks those statements against
   FE.
3. **One dataset.**
   - Designs come from several sources: variations, an optimiser, the agent, and features the agent invents.
   - All of them are recorded in one dataset that regenerates from a config, and a first fast model learns from
     it.
4. **Reproducible claims.** Every claim can be rebuilt from a commit and a config.

## 2. Motivation

Mechanical design is mostly iteration: edit the CAD, mesh, solve, check, edit again. Rules of thumb keep each
iteration safe, but they keep the search narrow. Requirements that pull against each other - stiffness, mass,
frequencies, heat, manufacturability - exceed what a person can iterate by hand. Three things change that now:
- **Agents** can drive engineering tools.
- **GPU solvers** prove a design in minutes.
- **Parametric CAD** can be scripted.

### The vision we are building toward

We are building toward the vision Mechanical AI sets out for its design agent, MEKINT, and for the role of
Research Engineer, Mechanical Intelligence.

**The problem**

> "The process in reality, however, often consists of tedious iterations starting from a limited set of
> physical principles and heuristics. This shouldn't be the case. Machines, not humans, should handle these
> repetitive tasks."

**The product**

> "By handling low-level implementations, our AI frees you to focus on high-level innovation, elevating your
> vision beyond the details. Unleash your creativity and insight—without the constraints of complexity."

> "MEKINT autonomously executes iterative design workflows based on user-defined goals and constraints. It
> seamlessly translates human intent into optimized designs, minimizing the need for constant oversight. By
> eliminating the repetitive burden of manual iterations, MEKINT enables engineers to focus on innovation,
> significantly enhancing productivity and creative potential."

**The mission**

> "Our product will unleash creativity and insight, no longer constrained by the complexities of design. The
> upper limit of mechanical, topological, and physical complexity that can be managed by our civilization will
> expand—faster than ever before in human history."

**The work**

> "Build agentic data-generation pipelines for high-fidelity, manufacturing-grade synthetic designs with
> embedding-friendly representations for neural network training."

> "Build modular tool interfaces and execution protocols for agentic design systems, spanning structural, fluid,
> heat-transfer, and aerothermodynamic analysis, as well as synthetic geometry generation through automated CAD
> operations."

> "Build and train state-of-the-art mechanical design agents that translate imagination into real-world designs
> by autonomously characterizing physical elements and governing principles."

**What it takes**

> "First-principles critical thinking across thermal, fluid, structural, and dynamic systems."

> "Demonstrable achievements in characterizing complex physical problems by identifying governing parameters and
> establishing appropriate reduced-order models."

## 3. What we are doing

1. **Generating cast gearbox housings from requirements.** We no longer edit one existing housing.
2. **The housing is a parametric template in FreeCAD:** a feature tree, constraint sketches, and a spreadsheet of
   about 40 named parameters. An engineer can open and edit it.
3. **fastcae's proven tools become the grader:** the STEP reader, the casting checks, the mesher, the GPU FE
   solver and the physics checks.
4. **The agent works on the template:**
   - It first characterises the physics.
   - It then generates designs, from a sweep of the parameters, by editing the feature tree, and by inventing
     new features through a gate.
   - Every design it sends is judged by the grader.
5. **Every design is recorded,** passes and refusals alike, with the agent's reasoning, so the dataset grows
   with each run.

## 4. What fastcae already did

fastcae ([github.com/saxenam06/fastcae](https://github.com/saxenam06/fastcae)) ran from 9 September to 3 October
2026: 210 commits and about 40,000 lines of Python. The figures below were verified in its code and records on
4 October ([the audit](design/2026-10-04-fastcae-audit-for-mekint.md)).

- **The task.** It takes an existing casting - the GRC wind-turbine gearbox rear housing (NREL/NLR) - and its
  FE deck, and adds ribs to make it lighter or stiffer.
- **Checking.**
  - Every rib is checked against the sand-casting rules on the CAD: fast on the GPU, exact on the B-rep.
  - CP-SAT keeps the sets of ribs that are legal together.
- **Proving.**
  - OpenCascade builds each design, and gmsh meshes it in TET10 with the fillets rolled onto the mesh.
  - fastcae's own GPU solver (cuDSS) solves in 35-45 s. It agreed with Code_Aster to about 1e-11 on the earlier
    deck mesh.
  - Every design keeps a manifest.
- **The agent.**
  - Claude Code runs headless in a strict harness and drives seven tools.
  - It states a hypothesis before each FE solve and a reflection after it.
- **The result.** In a single run, the agent's design matched production's stiffness within re-meshing noise,
  with 3.2 % less rib metal on the CAD, at its fourth FE solve. These are single runs, not yet a controlled
  benchmark.
- **The data.** 369 designs solved by FE are on disk. The earlier agenticCAE project solved 490 designs on a
  Google Cloud Slurm cluster.

## 5. Why we are changing the approach

| fastcae's approach | How it limits us |
|---|---|
| **A menu.** 673 ribs pre-built for one housing, about 1.5 h a library; the agent only switches them on and off | It recombines, never invents. A new rib family costs a day or more of engineering |
| **One existing part.** The body is fixed; only ribs change | Intent can only reach the ribs. The walls, bosses, flange and the layout itself cannot change |
| **Data tied to the part.** A design is a list of library ids | Nothing learnt carries over to another housing |
| **One physics.** Linear statics, one load case | The thermal and dynamic requirements a gearbox has cannot be judged |

**Why gearbox housings again, rather than a new part family.** A verified design needs a resolved project
context: the engineer's request, the programme's context and its CAD. A bracket would need all of that rebuilt
from nothing. For the GRC housing it is already worked out: the CAD, the deck's loads and supports, the casting
rules, production as the pass line. So we stay on gearbox housings and change *how* designs are made: generated
from requirements, not edited from one part.

## 6. How the new approach meets the vision better

| The vision's phrase | Before: ribs on the existing casting | Now: parametric housing from requirements |
|---|---|---|
| **Translate human intent into optimized designs** | Intent could only change ribs on a fixed body | Intent sets the whole housing - bearing layout, walls, bosses, flange, ribs. "Move the high-speed shaft 50 mm" becomes possible |
| **Iterative workflows from goals and constraints, minimal oversight** | A fixed optimisation loop, with the goal set by command-line flags | Requirements → a typed brief, confirmed once; then the agent runs alone. It stops only at its boundary: changing a rule, a volume or the budget, or adding a new feature |
| **Mechanical and topological complexity** | Topology fixed apart from ribs | The agent edits the feature tree: it adds or removes webs, rings, walls, whole concepts |
| **Unleash creativity and insight** | The best combination of pre-placed ribs | Concepts (box section against ribbed drum), edits to the tree, invented features - each with the physics reason behind it |
| **Focus on innovation, productivity** | A new part needs volumes picked by hand and a 1.5 h library | A new gearbox goes from requirements to a housing in seconds. The engineer sets goals, judges trade-offs and approves new features |
| **Raise the upper limit** | One part, its data tied to its menu | A family. The factory samples many gearbox layouts, and models trained on parameter vectors and feature trees learn across housings |
| **Governing parameters and reduced-order models** | The "parameters" were thousands of rib on/off choices, and what governed stayed hidden | About 40 named parameters: what governs is measured, and first-principles models are fitted to them (section 7.3) |

**The honest catch.**
- **A template is a menu at a higher level.** It fixes which features exist, and sweeping its numbers alone is
  classic design of experiments and optimisation. The creativity comes from the top of the ladder: the agent
  adding and removing features, and inventing new ones, guided by its physics characterisation.
- **GRC-like, not GRC.** Conclusions hold in the template's world. The acceptance test in step 3 measures how
  far that world is from production.

## 7. How it works

### 7.1 One requirement, end to end

```
1 REQUIREMENTS   bearing layout, bearing loads, mounting interface, envelope, gear space, process, goal
                 (runtime: an engineer gives them · factory: a sampler generates every value)
2 BRIEF          Claude → typed brief, every value with its source; asks only what blocks
3 FIRST GUESS    the template's default instance, sized by rules of thumb
4 CHARACTERISE   what governs on this design (7.3)
5 GENERATE       feature trees from four sources:
                 variations - spread evenly over the parameters (Sobol)
                 optimiser  - over the parameters
                 agent      - edits the tree: adds a web, thickens a wall, adds a gusset
                 invented   - a new feature the agent writes, through the gate (7.4)
6 BUILD          FreeCAD, headless, in its own process: recompute → STEP + .FCStd;
                 a failed recompute is recorded as a typed failure
7 JUDGE          the grader: read the STEP → whole-part casting audit → mesh → loads and supports from
                 the brief → FE on the GPU → physics checks → verdict against the brief
8 RECORD         feature tree + parameters + STEP + results + verdict + reasoning;
                 passes and refusals alike
9 CURATE         the agent sees what the dataset lacks and plans the next batch
```

### 7.2 The template

A FreeCAD feature tree, its sketches driven by a parameter spreadsheet. It has about 10-15 features:
1. the bolted flange, with its bolt circle as a polar pattern;
2. the drum;
3. the main bearing bore and the internal ring;
4. the box section around the parallel shafts;
5. the six bearing bosses;
6. the cover faces with their bolt circles;
7. the windows;
8. the rib patterns;
9. draft.

**Construction rules:**
- **No face references.** Every sketch hangs on a datum plane the spreadsheet positions, never on a face. That
  avoids FreeCAD's topological-naming breakage.
- **Fillets on the mesh.** The 241 fillets of the production casting are rolled onto the mesh, as fastcae does,
  because OpenCascade fillets fail on castings like this.
- **Interfaces read from production.** The GRC instance's interfaces - bore positions and diameters, bolt
  patterns - are filled from fastcae's reading of the production CAD, so they match exactly.
- **Named on creation.** The bearing seats and bolt holes are made by named features, so the grader knows where
  every load and support goes. They are found again by geometry: a bore's axis and radius.

### 7.3 Physics characterisation

Before designing, `characterise(design)` answers *why the design behaves as it does*. An example, with the
numbers illustrative:

```
LOAD PATH        strain energy: box side walls 58 % · bosses 17 % · drum 14 % · flange 11 %
GOVERNING SEAT   seat 4 (high-speed shaft), radial: 71 % of the peak displacement
MECHANISM        box section in torsion
SIMPLE MODEL     closed thin-walled box (Bredt–Batho, stiffness ∝ A²·t / s): 0.31 mm; FE 0.43 mm
PARAMETERS       per mm: box depth −0.9 % displacement · wall thickness −1.1 % · boss OD −0.2 %
BINDING          stiffness binds; metal has 6 % to spare
```

**Governing parameters.**
- Global sensitivity (Sobol indices) over a few hundred evenly spread instances ranks the parameters that drive
  seat stiffness and mass.
- Condensing the FE to the six bearing seats gives their compliance. It is exact for any load at the seats and
  is built from 36 unit cases on one factorisation.
- Superposition gives each load component's share of the goal.

**A ladder of models**, with a measured validity map that says when each can be trusted:

| Level | Model | Good for |
|---|---|---|
| L0 | condensed seat compliance, and first-principles formulas on the named parameters: wall bending D = E·t³ / 12(1−ν²); box torsion ∝ 4A²·t / s; boss ovalisation ∝ R³ / t³ | which seat, load and mechanism govern - in milliseconds |
| L1 | cube model (10 mm voxels, calibrated to FE) | ranking candidates in seconds |
| L2 | full TET10 FE | proof |

The agent uses the cheapest level that is valid for the question. Craig-Bampton reduction at the seats follows,
for dynamics.

### 7.4 How the agent invents, and the gate

A gap between a simple model and FE is itself a finding. In the example above, FE is 39 % softer than the closed
box model. That means the box's cross-section distorts, and the principle that stops distortion is transverse
diaphragms (bulkheads). The template has no diaphragm, so the agent writes one:

```
mechanism → principle → quantity to change → new feature → predicted gain → FE result
distortion  bulkheads    section shape       add_diaphragm    −15 % displ.    −18 %, +3 % metal
```

**The ladder of design freedom:**
1. vary the parameters;
2. add or remove existing features;
3. invent features.

**An invented feature passes a gate** before it joins the feature set:
1. it runs in a sandboxed process;
2. it is tested on a simple block, then on the housing;
3. it passes the whole-part casting audit: draft and undercut along the pull, least wall, keep-outs;
4. the engineer approves it.

**The mechanism library** pairs each mechanism with its principle and feature ideas, for example:
- box distortion → diaphragms;
- wall bending → ribs (∝ h³) or thickness (∝ t³);
- boss ovalisation → collars;
- flange rotation → gussets.

It is written from the engineer's FEA and NVH experience, and FE outcomes confirm or prune each entry.

### 7.5 Principles

- **Verified only inside a resolved project context.** A design is called verified only when the engineer's
  request, the programme's context and its CAD are all present. A concept mode may work from rough numbers; its
  results list their assumptions and are never labelled verified.
- **FE is the judge.** Simple models and fast models propose and rank; FE proves.
- **The agent works through typed tools.** These are `set_param`, `add_rib`, `add_boss`, `thicken_wall` and the
  others. Its own code enters only through the gate.
- **Every claim is reproducible.** One commit, one config, a clean tree, one CP-SAT worker, manifests with
  settings.

## 8. The plan

| # | Step | Done when | Days |
|---|---|---|---|
| 0 | **Repository:** git, uv, Python 3.12, CI, layout, data policy | a clean clone runs the checks in CI | 0.5-1 |
| 1 | **The grader core, from fastcae, with parity:** STEP reader and part model, mesher, cuDSS solver, physics checks, manifests, deck writer | the production housing graded here gives fastcae's results - same mesh, same displacement and strain energy to the solver's tolerance | 3-5 |
| 2 | **FreeCAD spike:** headless FreeCAD inside the repository; a toy template (block + bosses) → STEP → grader | one instance runs end to end; recompute time and failure rate measured | 2-3 |
| 3 | **The GRC-like template v1** | interfaces exact; gear space and keep-outs held; metal within 10 % of production's 121 L; seat stiffness within 15 % (rib-less, same loads); ≥ 95 % of 200 evenly spread parameter sets recompute | 7-10 |
| 4 | **`characterise`:** energy by region, seat compliance, sensitivities, L0 models with their errors | it explains the GRC instance, and each statement is checked against FE | 3-5 |
| 5 | **Generation and a first study:** variations, optimiser, the agent editing the tree through MCP tools; the GRC requirements | a measured answer against production, with at least three repeats of each arm | 6-10, + runs |
| 6 | **Intake, mechanism library, gate for invented features** | the engineer accepts 8 of 10 briefs unchanged; one invented feature passes the gate and FE | 5-7 |
| 7 | **Factory and first model, then modal and thermal** | a dataset regenerates from one config; the model is scored against FE | 6-8, + runs |
| | **Total** | | **about 6-9 weeks** |

**Order of risk.** Step 2 comes early because FreeCAD's headless robustness is the largest unknown. FreeCAD is
not installable with pip, and its recompute speed and failure rate on a part like this are unmeasured.

## 9. From fastcae: what comes, what stays

| Bring, with a parity test each | Leave behind |
|---|---|
| STEP reader and part model (bores, bosses, holes, walls) · mesher, with agenticCAE's `surface.py` brought in · cuDSS solver · physics checks · manifests and lineage · the deck writer, for Code_Aster cross-checks · the agent harness pattern | the rib library and menu · CP-SAT rib repair · the older distance-field code · the 143 analysis tools · the old plans · the UI, for now |

fastcae stays as it is: its history, the GRC redesign work, and the source of production's numbers for the
benchmark.

## 10. Risks

| Risk | How it is handled |
|---|---|
| FreeCAD headless is slow or fragile | Spike first (step 2); datum-based sketches; fillets on the mesh; a typed failure for every failed recompute |
| The template is too far from production | The acceptance test in step 3 measures the gap; the brief states which requirements are covered |
| FE costs minutes per design | Superposition and L0/L1 multiply the labels per solve; cloud batch later |
| Laptop memory: meshes peak at 9.5-13 GB, with blue screens seen | One heavy job at a time, under fastcae's guards |
| GRC data terms | GRC files never enter git; showing GRC-derived results waits for NLR's written OK; synthetic layouts are ours and free to publish |
| The plan drifts again | Each step ends on a measured result; this document is updated at each one |

## 11. Decisions

| Decision | When |
|---|---|
| Gearbox housings; the production GRC housing is the benchmark | 5 Oct 2026 |
| Generate from requirements as parametric CAD in FreeCAD; fastcae's tools are the grader | 5 Oct 2026 |
| A fresh repository; fastcae's parts copied in with parity tests | 5 Oct 2026 |
| Verified designs only inside a resolved project context; concept mode labelled not verified | 5 Oct 2026 |
| Start with steps 0 and 1 on 6 October | 5 Oct 2026 |

**Open:**
- Whether concept mode is in scope now.
- FreeCAD's version and how it is installed (step 2).
- How the factory samples gearbox layouts (step 7).
- Whether the bracket work returns as a second part family.

## 12. Documents in this repository

| Document | Status |
|---|---|
| [plan.md](plan.md) | **This plan - current** |
| [design/2026-10-04-fastcae-audit-for-mekint.md](design/2026-10-04-fastcae-audit-for-mekint.md) | Verified audit of fastcae on 4 October - the claims to correct |
| [design/2026-10-05-recipes-not-a-menu-design.md](design/2026-10-05-recipes-not-a-menu-design.md) | The earlier plan of writing ribs as recipes inside fastcae. Superseded by this plan; its ladder and its judging on demand carry over |
| [design/2026-10-04-agentic-data-factory-brief.md](design/2026-10-04-agentic-data-factory-brief.md), [problem statement](design/2026-10-05-problem-statement.md), [walkthrough](design/2026-10-05-end-to-end-walkthrough.md), [UI flow](design/2026-10-05-ui-flow.md) | The bracket thread. What carries over: the product boundary, the UI flow, the boundary-condition rules and checks, the data scaling |
| [design/bracket_ai_design_system_dataset_physics_ai_llm_runtime.md](design/bracket_ai_design_system_dataset_physics_ai_llm_runtime.md) | Added by the engineer; not yet reviewed for this plan |
| [research/](research/README.md) | The company, the AI-in-CAE landscape, Python tooling on Windows. Only items marked *verified* were checked first-hand |
