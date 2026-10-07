# Gearbox-housing design discovery: the plan

**Date.** 6-7 October 2026. Drafted from 23:30 on 6 October; completed on 7 October once the five research reports were in.

**Status.** The plan of record. All its decisions were taken by the engineer on 7 October 2026: D1 at 11:03, D2-D13 and the changes from the engineer's Q&A record at 11:41 (section 15, [decisions.md](decisions.md)). Nothing is built yet. The engineer will put a few more questions before P0 starts.

**What it converges.**
- The engineer's two plan documents of 6 October: [From Rib Placement to an Agentic Gearbox-Housing Design Platform](../../../../fastcae/docs/From%20Rib%20Placement%20to%20an%20Agentic%20Gearbox-Housing%20Design%20Platform.md) ("From Rib Placement" below) and [Agentic Mechanical Design Platform: Final Implementation Plan](../../../../fastcae/docs/Agentic_Mechanical_Design_Final_Implementation_Plan.md) ("the Final Implementation Plan").
- A reviewer's suggestions, pasted by the engineer on 6 October 23:08.
- Tonight's discussion: the level question, on the [product page](../../../../fastcae/docs/features/product/status.md).
- fastcae-sim's plan of 5 October (`C:\Work\fastcae-sim\docs\plan_gearbox.md`).
- The [recipes design](../../../../fastcae/docs/features/product/2026-10-05-recipes-not-a-menu-design.md) and the [audit](../../../../fastcae/docs/features/product/2026-10-04-fastcae-audit-for-mekint.md).
- Five research reports of 6 October in [docs/research/](../../../../fastcae/docs/research/README.md), listed in section 17.

**Where it lives.** Here, in `fastcae-sim`, the new product's repository (the engineer, 7 October 11:03). It moved here from fastcae's product folder. The research and inputs it cites stay in fastcae's library, and its links point there.

---

## 0. The plan on one page

**The product.**
- **What it does:** given a gearbox's functional interfaces, loads, package, targets and one manufacturing process, the platform builds the design problem and runs a design campaign that chooses and revises its structural hypotheses.
- **What comes back:** housings that are FE-proven and pass the process's rules, with the whole trajectory kept as data.
- **The level:** it starts at the functional interfaces. The MVP is L1 (fixed interfaces), the dataset spans L1 to L2 (bounded layout), and the platform releases L2. Gear-train and vehicle levels are upstream adapters, never the core (section 2).

**Why an agent.** The structural hypothesis is not known in advance (section 3).
- **What it does:** optimisers search within a formulation. The agent puts a **hypothesis**, a physical reason, in front of each formulation. It edits and abandons hypotheses by evidence that code keeps (a budget and a status each), and says when the design space is exhausted.
- **When to stop:** the test is a relaxed topology bound. If the best structure the whole domain allows misses the goal, no strategy inside the contract can meet it.
- **What it never does:** derive physics or judge. Which candidates get an FE proof is chosen in code: LLMs ignore numeric feedback.

**What it is built on, each from the research of 6-7 October.**
- **Geometry (5):**
  - an exact CadQuery core;
  - an **explicit member grammar** as the editable, learnable recipe;
  - voxel SIMP only to discover, bound and seed;
  - realised as B-rep (proven in fastcae) or as SDF (for printing), with a P1 gate between the two.
- **Physics (6):**
  - judged **at the bearing seats in µm and mrad**: misalignment per face width, bearing tilt, centre distance, ovalisation;
  - modes by a Campbell check, and fits under temperature;
  - never by peak displacement or global strain energy.
- **Process (7):**
  - LPBF AlSi10Mg with machined interfaces;
  - overhang, least member, no enclosed voids and the build volume enforced inside the optimisation and checked on the built part;
  - every design carries its **rung** on a qualification ladder, and the platform reaches "process-rule-feasible" on its own.
- **Compute (5.3):** this laptop proves about 410k TET10 elements. So the least member is about 4 mm here, lattices and thin walls wait for cloud GPUs, and the 1,000-problem dataset is a cloud job.
- **Learning (10), deterministic first:**
  - then a calibrated scalar model that also ranks candidates (30-100 proofs a family);
  - then a field surrogate, and action ranking based on the models;
  - a trained policy only at about 10⁴ tasks;
  - peak stress stays with FE, and mass is computed.
- **Data (9):**
  - a tree: root problem → campaign → episode → candidate → evaluation, with failures kept;
  - 1,000 root problems in five cohorts, split by family.
- **Benchmark (11):**
  - four arms at equal budget: a fixed workflow, an expert heuristic, an optimiser and the agent;
  - three repeats, and a pass mark registered beforehand;
  - shuffled-result and reflection controls;
  - **the kill criterion:** if the agent does not beat the adaptive rule-based arm, it is not fundamental;
  - the demo: three counterfactual pairs, the same function with one requirement changed, each design different for a stated physical reason.

**The phases (12).** Each ends on a measured gate. No new plan until P1's gate is measured.
- P0: the judge and the contract, about 1 week.
- P1: one requirement end to end, with the route gate, about 3 weeks.
- P2: the arms, the demo and a mini-benchmark, about 4 weeks.
- P3: the dataset factory and the first models, about 6 weeks.
- P4: the L2 platform, thermal, other processes, a prototype.

**Decided (15):** D1-D13, all taken by the engineer on 7 October. The four that weigh most:
- D1, the repository: fastcae-sim.
- D2-D3, the family and process: EV two-stage, LPBF.
- D4, "field geometry never makes data" re-taken for printed regions.
- D6b, the verdict's measures.

---

## 1. Why this, and what changed

**The loop worked; the design space was the limit.** fastcae's agent was given a fixed housing, fixed design volumes and predefined rib families. It could find only different arrangements of known ribs. On 20 % less metal, four of round 3's five finals share 64-89 % of their metal in the same place: one problem from one menu gives one answer ([agent page](../../../../fastcae/docs/features/agent/status.md)).

**The precedents, read honestly.**
- **Jäger & Linde 2025** ([WEVJ 16(10):552](https://www.mdpi.com/2032-6653/16/10/552)), from its full text: a concept, simulated only.
  - **The part:** a housing of a **planetary** gearbox that carries two ring gears, at 150 kW and up to 2,400 Nm at the output. There are two static load cases, forward and reverse, with eight-fold cyclic symmetry.
  - **The method:** SIMP in ANSYS minimised mass under a torsional-stiffness constraint, with the mounting faces as non-design regions and no overhang or support constraints. The X it found puts the ring-gear mounts at the X's tips: the answer to reaction torque.
  - **Then explicit members:** a parametric X-rib design, refined over **13 variants** of rib width and height, turned-part and flange thickness. Density discovered the layout; explicit members made the design (section 5).
  - **The results:** about 21 % less mass, with about 5 % more torsional deformation. The first mode is near 1,330-1,410 Hz across the material variants. Validation was plausibility checks only, with no experiments.
  - **The cost** (quotes, up to 100 units):
    - casting about 0.20 EUR/cm³ at 100 units;
    - SLM under 1.0 EUR/cm³ from the best provider, with quotes down about 28 % in two years;
    - the hybrid LMD route the dearest.
- **Porsche 2020** ([newsroom](https://newsroom.porsche.com/en/2020/innovation/porsche-protoype-small-production-electric-drive-housing-3d-printer-23235.html)): an LPBF e-drive housing, built and tested. Housing parts about 40 % lighter, 1.5 mm walls, the stiffness between motor and gearbox doubled.
- **A 2019 study** (Forschung im Ingenieurwesen, [doi 10.1007/s10010-019-00374-1](https://colab.ws/articles/10.1007%2Fs10010-019-00374-1)): an AlSi10Mg SLM housing with oil channels and a scraper built in, finish-machined, assembled and given short functional checks (From Rib Placement; see section 7).

**What printing changes.** It does not remove manufacturing rules; it swaps them.
- Draft, tooling access and rib rules give way to build orientation, least feature size, supports and powder removal, distortion, surface finish, machining stock, inspection access and qualification.
- So "manufacturable" is a predicate, not a property of a shape: `Manufacturable(design, process, machine, material state, orientation, post-processing, inspection plan, volume)`.

**What changes for the product.** The aim moves from parameter optimisation inside a solution family a designer set, to discovering structural embodiments while the interfaces and the function are kept.

## 2. The product boundary

| Level | The agent is given | The agent designs | Role in this plan |
|---|---|---|---|
| L0 Feature tuning | A fixed housing and its interfaces | Rib choice, placement, sizes | fastcae today, on the GRC housing: the evidence so far and a baseline |
| L1 Free structure | Fixed bores, mounts, envelope, loads | Shell, bosses, free topology, printed reinforcement | **MVP and benchmark** |
| L2 Bounded layout | A gearbox layout family with a load model; bores and mounts move within zones | The functional core's placement within bounds, plus free topology | **The dataset spans L1 → L2; L2 is the platform release** |
| L3 Gear-train synthesis | A motor or load spectrum and a package | Ratios, gears, shafts, bearings, layout | An upstream adapter: deterministic tools that write L2 contracts |
| L4 Vehicle mission | Vehicle performance and duty | The whole e-drive | The long-term vision |

The table is From Rib Placement's. The reviewer's point is taken: the MVP proves L1, the first dataset spans L1 to bounded L2, and the platform releases L2. These are three phases; no single demonstrator has to prove all of them.

**Why not start higher.** Above L2 the platform must also prove gear rating, bearing life, shaft deflection, contact, lubrication and efficiency. The search grows with every one of them, and it becomes hard to tell where the design intelligence comes from. Vehicle words still work as a front door (section 4.4): a few vehicle scenarios run through deterministic ratio, gear and bearing tools give different L2 contracts. Autonomy is claimed and judged at L1-L2.

**A general core, a gearbox module.** The engineer's standing rule is no part-specific code: name things by geometric kind, never by domain role ([plans lessons](../../../../fastcae/docs/research/2026-10-06-plans-lessons.md), decisions 1-2).
- The core knows a cylindrical seat, a planar face, a fastener circle, a sweep envelope, a design domain, a load case.
- The gearbox module is data plus its own front-end tools. It gives roles (input bearing, intermediate seat) to those kinds, and derives the loads.
- A bracket or a knuckle is another module over the same core.

**Who owns what** (the reviewer's contract, adopted):

| Owner | Owns | Examples |
|---|---|---|
| The engineer | Functional truth | Bearing seats and their tolerances, the mount faces, the envelope, the process, the hard limits |
| Deterministic tools | Every derived quantity, and every check and verdict | Gear forces, bearing reactions, mesh orders, keep-outs, DfAM checks, KPIs, PASS/FAIL |
| The agent | Design decisions within the freedom delegated to it | The structural hypothesis, its formulation, local edits, when to switch, when to stop |
| The solver | Physical truth | Fields, modes, margins |

## 3. Why there is an agent

**Not because of natural language.** The UI captures what is deterministic: torque, envelope, interfaces, limits, process. Words carry only the soft intent no field can hold, such as "prioritise bearing alignment over a small mass saving" (the Final Implementation Plan, section 4). Turning fields into a contract is ordinary software.

**Because the structural hypothesis is not predetermined.** The reviewer's five levels:

| Level | Question | Answered by |
|---|---|---|
| 1 | What problem am I solving? | The engineer, with the product context |
| 2 | What is allowed to change? | The design contract |
| 3 | What structural hypothesis should I test? | **The agent** |
| 4 | How do I optimise that hypothesis? | Optimisers and numerical methods |
| 5 | Is the result physically valid? | Physics and deterministic checks |

An optimiser searches *within* a formulation: variables, bounds, objective, constraints. The agent decides *which formulation to search*, and when to abandon it.

**Two kinds of decision.**

| Campaign-level (the real agency) | Design-level |
|---|---|
| Keep exploring this hypothesis, or drop it? | Move a feature within its zone |
| Change the representation (free density, shell plus reinforcement, struts, lattice infill)? | Change a local thickness |
| Change the formulation (objective, load-case weights, a misalignment constraint in place of compliance)? | Redistribute material |
| Change the design domain (open or close a region, move a keep-out within authority)? | Change the topology locally (bridge, split, merge) |
| Add or remove a constraint, or relax a soft target? | Change a lattice's density |
| Ask for higher fidelity (a refined mesh, a load case added, thermal)? | |
| Declare the design space exhausted, and say what would open it? | |

A library of fixed strategies would make the agent a selector among predefined optimisers; the reviewer warned against this. Here a strategy is instead a **formulation**: representation, domain edits, objective, constraints, optimiser and fidelity, each a typed, editable field. V1 ships a few named starting formulations (section 8.3) as seeds. The agent composes and edits them; how far its formulations move from the seeds is measured.

**The hypothesis: a reason in front of each formulation, and its bookkeeping** (adopted by the engineer, 7 October, from the engineer's Q&A record). The agent's unit of work is a hypothesis.
- **The reason:** a physical claim the agent writes about this problem. For example: "bearing A tilts because its path to the left mount is soft; a bridge there will cut the tilt more per kilogram than thicker walls."
- **The formulation** that tests it, as above.
- **The expected effect**, and **what result would prove it wrong**.
- **A budget:** FE proofs, optimiser steps, wall-clock time.
- **A status, computed by code from evidence, never by the agent:** untested, under-explored, promising, or explored and poor. The agent's own stated confidence is recorded beside it, but the status ignores it (LLMs do not use numbers reliably, AI report).

**Telling a bad candidate from a bad hypothesis** (deterministic tests):
1. Optimise deeper within the hypothesis.
2. Read the hypothesis's own bound and its mass-against-stiffness trade-off on the screen.
3. Compare it with other hypotheses at a fair budget.

A hypothesis is set aside only when these say so, which gives the agent its role of allocating the FE budget across hypotheses.

**Where the reasons come from.** The LLM's own reasoning writes them. A structured ontology of textbook regimes is **not built now**: it comes in only if the LLM's reasoning stops producing good designs (the engineer, 7 October). The same goes for sensitivity records and a learned hypothesis prior: later, if useful. The physical evidence the agent reads (which limit binds, where the strain energy sits, how close the modes are to gear orders) is already its structured observation (8.1).

**A bound before a search: when the design space is exhausted.** The reviewer left open how to tell that the current design space is exhausted. Physics answers part of it:
- Topology optimisation over the whole design domain, with the process rules relaxed, bounds what any structure in that domain can reach. That holds for stiffness-type goals under linear elasticity, within the method's own approximations.
- If even that relaxed optimum misses the goal, no strategy inside this contract can meet it. The agent must then say so, and say what would open the space: more domain, a looser limit, or another process.
- fastcae measured exactly this on the GRC housing: the relaxed topology optimum reached 87.9 % of the goal before repair, legal roundings 70.1-85.8 %, and the solved design 85.7 %. So rules and rounding cost about two points ([optimize page](../../../../fastcae/docs/features/optimize/status.md), 2 October).

So every campaign starts with the bound. It gives the agent a stop rule, gives the engineer the "price of the process", and labels infeasible root problems in the dataset.

**What the agent never does.** It never derives a physics quantity. Bearing reactions, mesh frequencies, margins and verdicts come from versioned deterministic tools; the agent reasons about what to do with them. It never decides PASS or FAIL.

**The evidence so far, and what is still to prove.** In fastcae, the agent's departures from the fixed rule gained in rounds 1-3. It learned where the cheap model errs ("the FE values ring ribs about five times more than the cube"). It met production's limits in 2 FE solves against the fixed workflow's 6. These are single, uncontrolled runs ([audit](../../../../fastcae/docs/features/product/2026-10-04-fastcae-audit-for-mekint.md), section 5). The new platform must prove the agent's value at equal budget, with repeats, against a fixed workflow, an expert heuristic and an optimiser (section 11).

## 4. The design contract

The contract is the central artifact. The dataset generator, the agent's state, the simulation interface, the training records and the runtime product all derive from it (the Final Implementation Plan, section 47). It is the first thing built.

### 4.1 Inputs

- **Structured context, from the UI:** application, architecture, torque and speed, duty cycle, envelope, known interfaces, material and process, load cases, safety factors, targets, and allowed and forbidden features.
- **Soft intent, in words:** priorities, preferences, how aggressive to be, preferred complexity. The agent turns these into soft objectives and shows them back for confirmation before the campaign starts.

### 4.2 The layers of `HousingDesignSpec`

These are From Rib Placement's six layers. Every entity carries an **authority** (`engineer_locked`, `agent_bounded` with its allowed range, `agent_free`) and a **kind** (`hard`, `soft`, `derived`).

| Layer | Holds | Typical authority | Kind |
|---|---|---|---|
| Product intent | Family and topology id, duty-cycle id, priority statement, validation tier required | Engineer | Hard, or soft for priorities |
| Functional interfaces | Bearing-seat frames, diameters, widths, fits; gear and shaft envelopes; motor, differential, chassis and cover interfaces; mounts, bolt preloads, datums; seals, oil ports, vents | Engineer locked (L1); agent bounded within zones (L2) | Hard |
| Physics cases | Bearing reactions and moments per operating case; bolt preload; mount stiffness; gravity and shock; thermal case; excitation orders | **Derived** by tools from the product context | Derived |
| Design limits | Mass; relative bore translation and rotation (not only peak displacement); stress and fatigue; modal separation; temperatures; package and access | Engineer | Hard, or soft for preferences |
| Manufacturing profile | Process, machine envelope, alloy property card, orientation rules, least wall, strut and hole sizes, overhang policy, supports, powder removal, machining stock, finish, heat treatment, inspection | Engineer picks the profile; its values come from the profile's version | Hard |
| Optimisation policy | Objective (scalar, lexicographic, Pareto); hard against soft; permitted actions; FE budget and fidelity; stop rules; required baselines | Engineer sets the budget; agent free within it | Mixed |

**Rule:** a derived quantity is computed by a deterministic, versioned tool and stamped with that tool's version. The agent may ask for it to be computed again with a changed input it has authority over. It may never write the value.

### 4.3 The deterministic derivations

| Derived | From | Tool |
|---|---|---|
| Gear mesh forces per stage and case | Torque, pitch diameters, pressure angle, helix angle | `Ft = 2T/d`, `Fr = Ft·tan(αn)/cos(β)`, `Fa = Ft·tan(β)` (section 6 confirms the conventions) |
| Bearing reactions per case | Mesh forces with the moment `Fa·d/2`, gear positions on each shaft, the bearings' effective load centres, the axial forces tapered and angular-contact bearings induce | Shaft statics, two bearings a shaft (6.2) |
| Mount reactions | All loads, the mount scheme and stiffness | The FE itself (supports) |
| Mesh frequencies and orders, the Campbell lines | Speeds over the band, tooth counts (`z·n/60`) | Arithmetic |
| Fit loss with temperature | Seat diameters, the two materials' expansion, the temperatures | Arithmetic, then the uniform-temperature case in FE |
| Keep-outs | Gear tip circles and faces plus clearance, shafts, bearings, tool access, assembly sweeps | Geometry from the layout |
| Design domain | Envelope less keep-outs, plus preserve regions around interfaces | Geometry |
| The bound (section 3) | Domain, loads, limits | Topology optimisation with relaxed rules |

**The load front-end is validated before its loads are trusted.** agenticCAE's gear-statics code reproduced its deck's total load to 1.4 % while getting the directions wrong ([plans lessons](../../../../fastcae/docs/research/2026-10-06-plans-lessons.md), pitfall 8). So the front-end passes three checks before any campaign uses it:
1. a textbook worked example, to the digit;
2. the GRC deck's own bearing loads (directions and magnitudes) from the GRC gear data, within a stated tolerance. This is an internal check, never published;
3. fault injection: a flipped hand of helix, a reversed torque, a swapped bearing. Each must change the reactions as statics says it should.

Each result is reported with its load case named. Where a direction is not fixed, such as a rotor's bending or a mount's preload, the targets are robust: the worst case over a band. Of 29 GRC designs scored under 12 load cases, none beat production under all of them (pitfall 9).

### 4.4 The root-problem generator

This is the deterministic factory that writes contracts. It follows the Final Implementation Plan's section 36:
- Pick an archetype: an EV two-stage parallel-axis reducer in V1.
- Draw a physically consistent operating point: torque, speed, ratio, split, within the archetype's ranges (6.7). Each torque and speed names its shaft and its kind.
- Size gears and bearings by textbook rules, then lay out the shafts. At L1 the layout is fixed; at L2 it varies within its family's zones.
- Make the load cases, the package and the interfaces.
- Pick the process profile.
- Write the contract.

The vehicle front door (L3/L4 phrasing) sits on top. A vehicle scenario becomes duty numbers by two formulas (ratio from top speed, motor speed and wheel radius; torque from wheel torque), then goes through the same generator.

### 4.5 Contract checks before any campaign

- **Schema:** units, frames, bounds, contradictions.
- **Consistency:** gear diameters against centre distances, bearings against shafts, keep-outs against the envelope.
- **The bound (section 3):** a root problem infeasible at the bound is labelled so. It goes to the "infeasible" cohort and is not run as a design campaign.

### 4.6 The Final Implementation Plan's eleven questions, answered

| # | Question | Answer |
|---|---|---|
| 1 | What can the engineer enter? | The structured context (4.1), the targets, the process profile, soft intent in words |
| 2 | What is hard against soft? | Each entity's `kind` (4.2): interfaces, process and limits are hard; priorities and preferences soft |
| 3 | What does the UI capture deterministically? | Everything but soft intent |
| 4 | What is derived from the product context? | The table in 4.3, by versioned tools |
| 5 | What is locked? | `engineer_locked` entities: at L1 every interface; at L2 the interfaces' kind and size, with their position bounded |
| 6 | What is the design domain? | Envelope less keep-outs, less preserve regions; voxels and SDF (section 5) |
| 7 | What can the agent change? | `agent_free` and `agent_bounded` entities; the formulation (section 3); the design-level edits |
| 8 | Which strategies can it select? | Any formulation built from the typed fields; the V1 seeds in 8.3 |
| 9 | What makes a design valid? | Every hard limit met on the TET10 proof, every process rule passed, interfaces untouched; labelled on the ladder (section 7) |
| 10 | What lets the agent declare success? | The contract's verdict, by the deterministic evaluator, never by the agent |
| 11 | What means the design space is exhausted? | The relaxed bound misses the goal (section 3); or every hypothesis within authority has been set aside by its tests (section 3, 8.5) |

## 5. Geometry: representations and the stack

The evidence for this section is [the geometry-technology lessons](../../../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md) (6 October): 15 technologies, 26 rules the engineer set from experience, and 18 contradictions between documents. Its lessons are cited as "lesson n".

### 5.1 Four geometry classes, not one solid

From Rib Placement's split, adopted:

| Class | What it is | Representation |
|---|---|---|
| Functional core | Bearing seats with shoulders and machining stock, seal lands, split faces, motor, cover and mount interfaces, bolt patterns, datums, oil ports | Exact parametric B-rep; every face named when it is made |
| Keep-outs | Gear and shaft sweeps with clearance, bearings, tool and assembly access, oil paths, sensors | Exact B-rep where available, plus a conservative SDF for optimisation and collision tests |
| Structural design domain | The continuous region connecting the interfaces, where material may go | A voxel grid and SDF over the envelope, less keep-outs and preserve regions |
| Manufacturing state | Build orientation, supports, machining allowance, datums, powder paths, heat treatment, inspection regions | Typed data on the candidate, checked by the process profile (section 7) |

Additive structure never alters a functional face without an explicit, authorised interface action.

### 5.2 The stack, layer by layer

| Layer | Main choice | Alternatives | Why (evidence) | Risks |
|---|---|---|---|---|
| **Functional core** | Parametric templates in **CadQuery**, on the OCP 7.9.3.1.1 bindings fastcae already pins. Typed, bounded parameters; a build check that refuses with where and why; faces named when made and carried to the mesh as groups; the core's own fillets drawn inside the template | **FreeCAD** (feature tree, TechDraw and GD&T; the tool the labs and MEKINT name); build123d (OCP 8, its own environment) | Exact faces are not negotiable (lesson 1). fastcae's extraction, geometry service and rules all sit on OpenCascade. A housing family is estimated at 2-4 days, plus 1-2 for robustness | OpenCascade's weak spots: fillets where a boss meets a wall, and shelling. Automated parametric sweeps fail 70-80 % in nTop's account. Face numbers change after booleans, so use names or geometric signatures |
| **Discovery and the bound** | **GPU voxel SIMP** with adjoints and multigrid over the design domain (5 s a step measured on the cube model). Run with the rules relaxed, it gives the bound (section 3); with the process filters on, it gives the price of the process. It seeds member layouts. **Its fields never become data** | Diffusion or one-shot topology priors as proposers on simple domains, later | Cubes read 1.0-2.4× stiffer than the mesh, and voxel FE was 14-17 % off on tilt (lesson 5). Free-density layouts lost their metal when made into parts: BESO plates kept 51-70 % (lesson 6) | Holding casting rules inside topology cost 11 % on displacement and 25 % on strain energy. The cost of printing rules is unmeasured |
| **Structure representation (the recipe)** | An **explicit member grammar** in the MMC and force-flow style: struts, webs, plates, shells and nodes. Each is drawn from its own numbers, giving both its voxel density (with derivatives, for the screen and for shape gradients) and its exact geometry for the proof. Members go anywhere the domain allows; there is no library. This is the recipes design's idea, widened from rib families to printed members | Density-to-SDF extraction for free-form printed concepts; lattices only as infill where the process allows | Drawn for the kernel, members fuse cleanly (lesson 3); projected and voxel layouts did not (lessons 2, 6). Parametric families are learnable: 1.75-3.9 % field error, against about 30 % on topologically diverse designs (lesson 10). The vocabulary sets the ceiling (lesson 8) | No attempt has yet held all three corners at once: manufacturable, carries load, differentiable. Each new member kind needs its gate |
| **Realisation** | **Two routes from the same recipe, gated in P1:**<br>**Route B (B-rep):** draw each member long and square, cut it by half-spaces, trim it to the core, fuse the batch. A failed fuse rejects the design; nothing is filleted after the union; fillets are rolled onto the mesh.<br>**Route S (SDF):** the members as SDF primitives with radius-controlled smooth unions on a sparse narrow band, joined to the core's crisp face-by-face surface mesh by an exact mesh boolean (manifold3d, Apache-2.0) | A local implicit band at the interfaces only | Route B is fastcae's measured winner: trim-then-fuse joined every rib in 14-42 s where the old route took up to 13 min. Route S is fastcae's "option 2" of 25 September, chosen but never built. Printed regions need no exact B-rep: only the machined faces must stay exact (Inferred; section 7) | Route B: seam slivers, and OCC fillets fail on fused seams (0 of 42), so fillets go on the mesh, at 4.6 min and 13.2 GB. Route S: untested; contoured SDF surfaces can cross themselves (2,333 faces once) |
| **Mesh** | gmsh face by face to TET10: size fields from the rules, the core's face names as groups, unloaded tiny features defeatured, gates (mesh again once if the metal is far off, then warn; the tet cap) | For Route S: gmsh HXT filling the joined surface (9 s measured on one design); TetGen on a marked surface (AGPL); fTetWild only as a flagged fallback | 55 of 55 sharp designs meshed; re-mesh noise 0.98 % on displacement and 1.32 % on strain energy | Fillet bands dominate time and memory. 19 first meshes in round 3 came out 3 % or more over their CAD's metal. Thin printed walls multiply the element count (5.3) |
| **Solve** | **cuDSS**, a single-precision factor refined to double (2.18 M unknowns in 15 s), with Code_Aster re-solving a sample as the audit | CalculiX as the open cross-check (the labs name it); JAX-FEM where gradients are wanted | It matches Code_Aster to 3·10⁻¹⁰, 4.3× faster; each further load case costs 0.04 s | **There is no eigen-solver yet**, and a housing needs its modes: shift-invert Lanczos on the cuDSS factor is a P1 task. How the part is held moved the worst tilt by 40 %, more than any solver |
| **Data** | **The recipe is the record and the agent's handle:** core template and values, member graph with numbers, process profile, the rules' hash. Beside it, regenerated: STEP, mesh, nodal fields in Zarr, metrics in Parquet, a fixed-grid SDF, a manifest | B-rep face graphs for learning geometry; surface point clouds for field surrogates | A design that is its recipe rebuilds bit for bit; CP-SAT with one worker gave 4 of 4 identical repeats | When topology changes, neighbours' meshes no longer match, so there is no training on derivatives across them |

**Why one recipe, two realisations.** The recipe gives the agent an editable handle (thicken this strut, add a path from this seat to that mount). It gives the networks a compact, learnable form, and it gives one judge for both processes. Route B is the proven path, for cast-like and conservative structure. Route S is the natural path for printed structure: organic nodes, smooth junctions, booleans that cannot fail. The machined faces are never in the SDF. Which route a design takes is part of its manufacturing state.

### 5.3 The compute budget on this laptop

The card's measured ceiling is 412,667 TET10, 2.18 M unknowns, in single precision ([simulate page](../../../../fastcae/docs/features/simulate/status.md)). Against a printed aluminium housing (AlSi10Mg, 2.67 g/cm³), computed 6 October:

| Case | TET10 needed | Against the card |
|---|---:|---:|
| A 6 kg housing at the card's budget | 0.41 M (mean edge 3.6 mm) | ×1.0 |
| Every wall meshed at 4 mm | 0.30 M | ×0.7 |
| ... at 3 mm | 0.71 M | ×1.7 |
| ... at 2 mm | 2.38 M | ×5.8 |
| ... at 1.5 mm (Porsche's walls) | 5.65 M | ×13.7 |

So on this laptop:
- the **least member is about 4 mm**: set by the FE budget, not the printer;
- **lattices are homogenised**: an effective material in the voxel model and in the FE, with unit-cell checks;
- **thin walls and real lattices wait for cloud GPUs.** 40-80 GB cards raise the ceiling roughly 5-10× (estimated; to measure);
- **the 1,000-root dataset is a cloud job** (sections 9 and 12).

The voxel grid for discovery: 3 mm voxels over a 420 × 280 × 260 mm envelope give 1.13 M voxels and 3.4 M DOF, matrix-free with multigrid.

**Those voxels cannot resolve 4 mm members** (D7): a feature needs about three voxels across (geometry lesson 7). Resolving them would need about 1.5 mm voxels, some 9 M voxels and 27 M DOF, too heavy here. So the roles are fixed:
- **the voxels discover the layout** at coarse scale;
- **the explicit members carry the fine sizes** in their own numbers, sized by gradients through their projected density;
- **the TET10 proof judges.**

### 5.4 Rules carried over

The engineer's own rules from experience, dated in the geometry report's section 3:
- **Exactness:**
  - exact interfaces meshed face by face, never from a field;
  - shapes drawn from their parameters, never traced;
  - every check on the CAD by one judge;
  - metal judged on the CAD.
- **Joining:** trim then fuse; a failed fuse rejects the design; no fillets after the union.
- **Data:**
  - cubes never produce data;
  - one case end to end, then the batch;
  - the dataset made fresh by a frozen pipeline.
- **The machine:** the factor single precision on purpose; heavy work one job at a time, with the laptop idle and 9 GB free, under the guard.

### 5.5 What P1 proves first

1. One core template swept across its bounds: how many build, and every refusal named.
2. One member of each kind joined, meshed and solved by Route B, then by Route S on the same designs.
3. Route S gated by the field-meshing gate's method before any of its data counts: compare it with Route B, and mesh it again for the noise.
4. Ten designs per member kind: all solved, metal within 1 % of the CAD, under the tet cap, no crash.
5. The noise read at two mesh sizes. A verdict inside the noise is no verdict.

## 6. Physics and the verdict

The evidence for this section is [the gearbox-housing engineering report](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md) (6-7 October, 67 sources; each claim is tagged with its confidence there).

### 6.1 What a housing is judged on

**At its bearing seats, in micrometres, not by peak displacement.**
- The relative skew of two shafts drives the gear's face load factor KHβ (ISO 6336-1; its Annex E follows AGMA 927).
- At ISO grade 6 (gears of 50-125 mm, 20-40 mm wide), the axes may be out of parallel by 6 µm out of plane and 12 µm in plane per face width, and the centre distance may vary by ±20-26 µm (JGMA, via KHK). On the report's arithmetic, 10 µm of misalignment raises KHβ by about 0.3.
- The gear is less forgiving than its bearings:

  | | Allowed slope |
  |---|---|
  | An uncrowned gear | 0.5 mrad (Shigley) |
  | Tapered roller bearings | 0.5-1.2 mrad |
  | Cylindrical roller bearings | 0.8-1.2 mrad |
  | Deep-groove ball bearings | 1-3 mrad |

So the governing measures are per shaft and per stage:
- the tilt of the shaft's two seats against each other, projected into the plane of action and across it, per face width;
- the change in centre distance;
- each seat's ovalisation against its roundness tolerance (about 8-18 µm for 50-180 mm bores).

**Global strain energy and peak displacement are not requirements.** fastcae's industry research said so on 30 September, and fastcae ranked by them anyway. The new verdict ranks by the interface measures.

**Temperature changes the fits.** A steel bearing in an aluminium bore loses interference as both warm. On the report's arithmetic, a 72 mm seat warmed by 80 K loses about 66 µm, more than the whole mechanical tolerance budget. JTEKT asks for more interference in light-alloy housings, and Eaton reports bearing creep. So a uniform-temperature case belongs early (6.3), not with "thermal later".

**NVH in an EV is tonal, and no engine masks it.**
- A first-stage mesh order of 23 puts the mesh at about 6.1 kHz at 16,000 rpm, so not every housing mode can sit above it.
- Practice uses a Campbell diagram: motor and gear orders are kept at least 3 % away from the modes across the speed band, with a limit on the equivalent radiated power. The mount-support bending modes come first.
- Public first modes are 238-719 Hz for an e-axle on its mounts, and about 1.3-1.4 kHz for a stiff housing alone; Jäger & Linde's housing had 1,330-1,410 Hz.

**How the housing is modelled moves the answer.** Against measurements on a hypoid axle, the model's error was:
- 26.6 % with a rigid housing;
- 17.8 % with stiffness at the bore centres only;
- 11.7 % with eight points per seat that carry no tension (TU Munich, 2022).

So bearing loads go onto the seat as a distributed load, never onto a rigid centre (D6a):
- **in P1,** a linear cosine distribution over each seat's loaded half;
- **in P0,** the sensitivity against a compression-only iteration on the same factor is measured once;
- **later,** that iteration is added. Margins must cover the 10-25 % model-to-test differences measured.

### 6.2 The derivations, completed

The front-end's formulas are confirmed (JTEKT): `Ft = 2T/d`, `Fr = Ft·tan(αn)/cos(β)`, `Fa = Ft·tan(β)`. Three additions are required for the bearing reactions:
1. the moment `Fa·d/2` that the axial force makes about the gear's centre;
2. spans measured to the bearings' **effective load centres**, not their mid-widths;
3. the **induced axial forces** of tapered-roller and angular-contact bearings.

Mesh frequencies are `z·n/60` per stage, and the Campbell lines are drawn from them.

**Torque and speed must say where they are measured, and of what kind.** The Final Implementation Plan's example gives "1200 Nm at 6500 rpm". At the motor that would be 817 kW; as output torque it implies a top speed near 89 km/h. Every torque and speed in a contract states its shaft and whether it is peak, continuous or maximum.

### 6.3 Load cases

| Case | What | From | Phase |
|---|---|---|---|
| Peak drive | Peak motor torque, forward, through both stages | The front-end | P1 |
| Peak regen or coast | The reversed torque | The front-end | P1 |
| Continuous | The continuous torque: the reference for fatigue | The front-end | P1 (recorded); fatigue checked in P4 |
| Modes, as mounted | The mounts' stiffness stated; free-free kept as a check | The contract | P1 |
| **Uniform temperature** | A uniform temperature rise: bore growth and fit loss against the steel bearings. A thermo-elastic load on the same mesh, with no conduction solve | The contract's temperatures | **P2** |
| Park-lock holding | Holding the vehicle on a grade. The US rule (FMVSS 114) allows at most 150 mm of movement on a 10 % grade; the load comes from vehicle mass, grade and wheel radius | The front-end, when the archetype has a park lock | P2 |
| Assembly state | Bolt preload, press fits, bearing preload | The contract | P4 (finalists) |
| Forced response, park-lock abuse, fatigue under the duty cycle, bolted joints (VDI 2230: no opening, no slip, bolt fatigue) | - | The contract | P4 (finalists) |

### 6.4 The verdict's measures

The deterministic evaluator reads these from the TET10 proof. **The limits are the engineer's** (`engineer_locked`). The values below are typical, to seed the generator's ranges, not defaults to trust.

| Measure | Definition | Typical limit (report) |
|---|---|---|
| Mesh misalignment from the housing, each stage | The relative tilt of the shaft's two seats, in the plane of action and across it, per face width | An agreed share of the grade's parallelism (6 / 12 µm per face width at grade 6). No public source gives the share; the gear engineer sets it |
| Bearing tilt, each seat | The seat axis's rotation | 0.5-1.2 mrad (tapered), 0.8-1.2 (cylindrical), 1-3 (ball) |
| Centre-distance change, each stage | The seats' relative translation along the centre line | A share of ±20-40 µm |
| Seat ovalisation | Out-of-roundness under load | A share of the 8-18 µm roundness tolerance |
| Fit kept warm (P2) | The interference left at the hot case | Positive at every seat |
| Modes | The Campbell check: no strong order within ±3 % of a mode across the speed band; a floor on the first mounted mode | Set by the contract; the radiated-power limit is later |
| Stress | The static peak against allowable ÷ safety factor, read on a refined mesh for finalists; fatigue later | From the material card |
| Mass | From the geometry, never the mesh | The contract's cap |

**Margins.** A design passes only with margin beyond the declared model allowance. The engineer sets it: 10-25 % was measured model to test. The bearing coupling's sensitivity is measured once in P0: rigid against distributed against compression-only multi-point.

### 6.5 The judge, verified before it judges

There is no reference deck for a sampled requirement (plans lesson 1). So:
- **Analytic cases:** a thick cylinder under pressure (Lamé), a cantilever, the first frequencies of a cantilever and a free ring, and a uniform-temperature ring for the fit check.
- **Code_Aster** re-solving a sample.
- **Every solve:** reaction balance and the energy check.
- **Fault injection:** a missing support, a reversed load, a swapped bearing, a flipped hand of helix. Each must be caught.
- **The noise** at two mesh sizes, and **the coupling sensitivity** above.

### 6.6 Corrections to the example contract in the Final Implementation Plan

| Its value | Verdict | Use instead |
|---|---|---|
| `max_displacement: 0.40 mm` | The wrong criterion: 10-100× too coarse | The interface measures in µm and mrad (6.4) |
| `min_first_mode: 900 Hz` | Unsupported | A Campbell check against the stated orders, with the mounting stated |
| `1200 Nm` at `6500 rpm` | Inconsistent (817 kW at the motor) | Torque and speed with their shaft and kind |
| `max_stress: 120 MPa` | Not enough | Static strength with its factor, plus fatigue under the duty cycle (finalists) |
| "Coaxiality 0.015-0.025 mm" (the pasted research notes) | The order of magnitude is right; no source found | Derived per seat from the gear's budget, the bore size and the bearing type |

### 6.7 Typical EV archetype values, for the generator's ranges

- **The unit:** single-speed, two-stage helical, with the differential integrated.
- **Ratio:** about 8-13.
- **Motor:** 10,000-20,000 rpm (up to 30,000 in premium units), 163-650 N·m.
- **Mass:** integrated units weigh 91-113 kg, for the whole drive.
- **Ownership:** published gearbox optimisers leave housing deformation, lubrication, NVH and the park lock to a later expert step. That step is where this platform sits.

## 7. Manufacturing profiles and the label ladder

The evidence for this section is [the AM report](../../../../fastcae/docs/research/2026-10-06-am-housings-rules-and-cases.md) (6-7 October). Three of its five research threads finished. The gaps it names are listed in 7.6.

### 7.1 The first profile: LPBF, AlSi10Mg, machined interfaces

A process profile is one versioned record: one rules record for the process, read by every tool. Its values are **specific to the machine, the alloy and the parameters**; none is a universal constant. The table holds the values found and where each rule is enforced.

| Rule | Value found | Inside the optimisation | Checked on the built geometry |
|---|---|---|---|
| Least wall or strut | 0.4 mm on an EOS M 290 (about 0.1 mm in research). **The design floor on this laptop is 4 mm, set by the FE budget (5.3)** | The length-scale filter | A thickness map (distance transform) |
| Overhang | Downskin faces at less than 45° to the plate normally need supports | An overhang filter for the chosen build direction (Langelaar's method; OptiStruct and Ansys support kinds of it) | A downskin map with the support area |
| Holes and channels | Horizontal channels unsupported up to about 8 mm | - | Each opening's size against its orientation |
| Powder removal | No enclosed voids; escape channels of 1-3 mm | A no-enclosed-void constraint | A flood fill from outside |
| Machining stock | 0.5-2 mm on every machined face | Drawn in the core template | Present on every functional face |
| As-built surface | Rz 30-140 µm | - | Functional faces machined; fatigue knocked down elsewhere |
| Fatigue | 110 MPa at 2×10⁷ cycles fully reversed, on turned specimens; as-built "significantly reduced". NASA's low-demand line is 60 % of the fatigue limit for as-built surfaces, 80 % for improved | - | The stress verdict uses an allowable for each surface state (finalists) |
| Static strength | About 460 MPa UTS for LPBF AlSi10Mg; anisotropy noted on the property card | - | The verdict |
| Build volume | Machine-specific. A 420 mm envelope does not lie flat in a 400 mm EOS M 400-4; Porsche's housing (590 × 560 × 367 mm) was built in 21 h on an SLM NXG XII 600 | The domain must fit the machine in the chosen orientation | The fit in that orientation |
| Supports, distortion, overheating | ISO/ASTM 52911-1: relying on supports raises waste and the risk of a failed build. Constraints on distortion are still research | Orientation chosen as a discrete variable (CP-SAT) | **Process simulation for finalists, later** |

**The build orientation is a design variable.** It sets the overhang map, the supports and the fit in the machine. It is chosen, like any discrete choice, with the rest of the formulation. Counterfactual pair C of the demo changes it (11.4).

### 7.2 The label ladder

**Qualification attaches to a process and a part plan, not to a geometry.**
- NASA's MSFC-STD-3716 and MSFC-SPEC-3717 are still active, and NASA-STD-6030 and 6033 (2021) are their successors in practice.
- NASA does not accept verification by analysis alone for the higher part classes.
- In automotive, the top rung is PPAP.

Every design carries its rung. A design is never just `verified: true`.

| Rung | What it needs | Who signs |
|---|---|---|
| Simulation-feasible | The contract's verdict met on the TET10 proof, with margins | The deterministic evaluator |
| Process-rule-feasible | Every rule of the process profile passed on the built geometry | The deterministic checker |
| Process-simulated | Distortion, residual stress and supports simulated for the chosen orientation | A process simulation (later) |
| Prototype-validated | Built, machined, measured against the prediction | A test with a partner |
| Production-qualified | A qualified process, production controls, NDE, acceptance (PPAP) | The customer's quality system |

**The platform reaches the second rung on its own; the rest need partners.** The first two rungs already fix NASA's part class, from the FE margins and an AM-risk score. So the platform can compute it and say what the higher rungs would need: a possible differentiator.

### 7.3 What has been built

Few printed housings have been built: Porsche (2020), SEW-EURODRIVE (2019), an aviation gearbox housing (Magerramova et al.), Rolls-Royce's EBM bearing housing, and REINTJES's WAAM part (still research). A 2019 AlSi10Mg SLM gearbox housing had its oil channels and a scraper built in, then was machined, assembled and given short functional checks (Forschung im Ingenieurwesen). **None publishes a fatigue or endurance test protocol.** Porsche published results, not its protocol: housing parts 40 % lighter, the drive 10 %, stiffness doubled with 1.5 mm walls and lattice, about 40 assembly steps removed.

### 7.4 Cost and volume: what the product may claim

- **Casting wins at volume.**
  - Jäger & Linde: casting about 0.20 EUR/cm³ at 100 units; SLM under 1.0 EUR/cm³ as built; hybrid LMD the dearest. Their LMD figure leaves out the turned core, and the SLM quotes leave out machining and heat treatment.
  - Elsewhere: DMLS beat die casting only below 42 parts, for a small part; printing beat sand casting only for a single part.
- **So printed housings are for prototypes, small series, motorsport and aerospace.** Series housings are cast.
- **This is why "one requirement, several processes, argued" matters** ([differentiators](../../../../fastcae/docs/features/product/differentiators.md)). It is also why the casting profile, fastcae's rules, returns as a contrast in P4.
- **Printing can also improve casting:** SEW's printed die cut a cycle by 11 %.

### 7.5 The hybrid route, for later

The turned-core plus LMD route is the least documented. No open study deposits ribs on a pre-machined aluminium part. LMD AlSi10Mg reaches about 180-220 MPa UTS against about 460 MPa for LPBF, and the interface metallurgy is unstudied. It stays a later profile (D3). If it comes, the fixed-material rule is asked again for a part made of two materials (D11).

### 7.6 Corrections and gaps

- **To From Rib Placement:**
  - Jäger & Linde's optimisation had no AM constraint beyond a least wall; "incomplete" understates it.
  - The standard is MSFC-**SPEC**-3717.
  - NIST's wall rules are illustrative values.
- **To the Final Implementation Plan's contract:**
  - `min_wall: 1.5 mm` is plausible (Porsche used it). But the contract also needs the build direction, the downskin limit, hole sizes, gaps, escape holes, machining stock and the build volume.
  - `max_stress: 120 MPa` must say static or fatigue. As a fatigue limit it exceeds the machined fatigue strength of 110 MPa.
  - `lattice: allowed` needs conditions for depowdering and inspection.
  - Varying material and process in the first dataset conflicts with qualification and with the fixed-material rule: one profile in V1.
  - Name the process (LPBF), not "additive manufacturing".
  - Replace `verified: true` with a rung.
- **Not reached:**
  - the DiVA thesis, MATEC, IJRPR, the patent, IJRASET, the Springer review, the bike stem, UT Austin;
  - housings from GE, Airbus and motorsport;
  - HIP cycles, Scalmalloy fatigue, leak-tightness of thin walls, the largest machines' build volumes.

  To be read before P1's DfAM checks are frozen.

## 8. The agent

### 8.1 State and observation

- **Structured state,** kept by the platform, never inferred by the agent:
  - the contract;
  - the current best design with its KPI vector;
  - the hypothesis in use and every hypothesis tried: its claim, its formulation, the budget spent, and its status as code computed it;
  - violated constraints with margins;
  - the unresolved risks;
  - the budget left, in TET10 proofs and in wall-clock time;
  - the bound.

  This is the Final Implementation Plan's `campaign_state`, extended with hypotheses.
- **Each observation is structured** (From Rib Placement, stage 10):
  - violations with margins;
  - hotspots linked to semantic regions (a bore, a mount path, a panel);
  - each region's share of the strain energy and of the goal;
  - modal participation and how close each mode sits to the excitation orders;
  - DfAM violations and whether each can be repaired;
  - solver-quality flags: mesh check, refinement residual, metal against the design's own volume;
  - the cost and time spent.
- **Pictures as well.** fastcae's `look` showed the agent's reasoning improves when it can see the FE hot spots and the topology's dials (AGT-14).

### 8.2 Actions: typed tools

- **Reading:** `state`, `look`, `bound`, `regions`.
- **Campaign-level:**
  - `hypothesise`: create or edit a hypothesis (its claim, formulation, expected effect, what would prove it wrong, budget);
  - `domain_edit` (open or close a region within authority);
  - `constrain` / `relax_soft`;
  - `escalate_fidelity`;
  - `switch` / `continue_from` / `restart_with_seed`;
  - `declare_exhausted` (with the evidence: the bound, the history).
- **Design-level:** `move_within_zone`, `thicken` / `thin` (a region), `reinforce_path` (between two semantic nodes), `redistribute`, `lattice_density`.
- **Proof:** `screen` (the voxel model: seconds to minutes, free of the budget), `solve` (TET10 cuDSS: counted against the budget), `reflect`.

Every action goes through the same deterministic tools the fixed workflow uses. fastcae's lesson holds: both benchmark arms run on the same tools.

**Which candidates get a proof is chosen in code, not by the agent** (10.3). The agent decides the formulation, the strategy and when to stop. A deterministic acquisition rule picks the candidates of a batch to prove.
- The evidence: LLM agents ignored permuted outcome labels in experimental design.
- This also keeps the arms comparable: the fixed workflow uses the same acquisition.

**Typed tools and repair from feedback carry most of an agent's gain.** In published CAE work, typed tools took end-to-end success from 22 % to 83 %, and repair from execution feedback from 72 % to 96 %; "scripted reflection adds nothing" in one ablation. So:
- every tool returns typed failures with the rule and the place;
- fastcae's per-solve reflection is kept, and is ablated once in P2 to see whether it pays.

### 8.3 The V1 starting points (seeds)

Each seed is a formulation the agent may start a hypothesis from. The claim in front of it is the agent's own, written for the problem at hand.

| Seed | Representation | Objective and constraints | When it suits |
|---|---|---|---|
| Free density | SIMP density over the whole domain, with length-scale and overhang control | Least compliance-weighted interface motion at the mass cap; misalignment and modal constraints | The default; also the bound |
| Shell plus reinforcement | A wall of set thickness on the domain's outer skin, with free density inside | As above | Oil-tight shells; NVH-driven panels |
| Bridge-first | Paths reserved between bearing seats and mounts, then free density | Bore-to-bore and bore-to-mount stiffness | Misalignment-governed cases |
| Struts | A skeleton of members between interfaces, sized by optimisation | As above | Low mass fractions; the X-type torsion paths |
| Lattice infill (after the MVP, D7) | Homogenised lattice in eligible regions, with solid skins; on this laptop for screening only | Stiffness and mass | Thick, lightly loaded regions; NVH damping |
| Ribs on a shell | Parametric webs on a fixed shell (CadQuery) | As above | The conventional reference; a cast-like baseline |

A seed is only a starting point. The agent edits any field of a formulation, and the trajectory records every edit.

### 8.4 The run discipline carried from fastcae

- A hypothesis and its risk are stated before every proof, and a reflection written after (brief v3).
- Multi-step planning on the cheap model before a proof (AGT-22).
- A clean run folder, an allow-list, a guard before every call, transcripts, an FE budget.
- Nothing an agent reads may hold a result, a lesson or advice from another run (CLAUDE.md). Every brief is checked before a benchmark freeze. The audit found that briefs v2-v4 carried process advice from earlier rounds; that must not happen again.
- Fairness: a new tool goes to both arms, with the fixed workflow's rule for it.
- One agent with structured reflection, not a separate critic agent (the engineer, 3 October).
- The brief holds rules that always hold, never an example or a number. There are a few general tools, one job each.
- The cheap model's error is part of the game. The agent decides under it; it is not handed a correction.

### 8.5 Stop rules

- The contract's verdict is met.
- The bound says the space is exhausted.
- The budget is spent.
- Every hypothesis within authority has been set aside by its tests (section 3): no gain beyond the noise after deeper optimisation, or a worse trade-off than another hypothesis at a fair budget.

The agent may stop early only with a stated reason, which is itself a recorded decision.

## 9. Data

### 9.1 The tree (the reviewer's hierarchy)

```text
ROOT PROBLEM (contract + product context)        root_problem_id, family, cohort
  └─ CAMPAIGN (a run of the agent, or of a fixed workflow, with its budget and seed)
      └─ EPISODE (one hypothesis explored: claim, formulation, edits, budget, status, optimiser history)
          └─ CANDIDATE (one geometry: core + structure, its manufacturing state)
              └─ EVALUATION (one fidelity: screen, TET10 static per case, modal, thermal; DfAM)
```

Every node keeps its parent, its tool versions and its hashes. Training reads `state → action → consequence`, not only `problem → answer`.

### 9.2 What each node records

| Node | Records |
|---|---|
| Root problem | Structured intent, soft intent in words, the contract with authority and kind on every entity, the product context (gears, shafts, bearings, reactions per case, frames, keep-outs), the bound and its outcome |
| Campaign | The arm (agent, fixed workflow, heuristic), the model and brief version, the budget, the seeds, the transcript, the final verdict and why it stopped |
| Episode | The formulation, every edit with its reason, the optimiser's history (density checkpoints), the outcome |
| Candidate | The functional B-rep and its feature graph, the structure (density field, SDF, surface mesh), the representation crosswalk, the manufacturing state, the DfAM report |
| Evaluation | Mesh statistics and quality, solver settings and residuals, fields at nodes and at fixed sample points, interface KPIs, modes, margins, the verdict, the failure type if any |

**The crosswalk:** `brep_face_id ↔ surface_patch_id ↔ volume_element_set ↔ sdf_region_id ↔ functional_interface_id ↔ manufacturing_feature_id` (From Rib Placement). Without it, a hotspot cannot be tied back to an editable region.

**Failures are data.** CAD failures, failed reconstructions, mesh failures, stalled solves, DfAM refusals, infeasible problems and dead-end campaigns are all kept, with a failure taxonomy.

**Guards learned the hard way** ([plans lessons](../../../../fastcae/docs/research/2026-10-06-plans-lessons.md), pitfalls 6, 7, 17, 22, 24, 28, 33):
- **Counting:** every run counts what each generator offered and what each check refused, with reasons. A design space must never shrink silently, as fastcae's library once did. A changed setting gets a dry count before any campaign.
- **Geometry and mesh:** volume and interfaces are checked after every geometry operation. A mesh is checked against its geometry's volume before it is solved, so a failed build costs no FE solve.
- **Field format:** geometry-agnostic. Fields are kept at the mesh's nodes, on the interfaces, and as surface point clouds in the part's normalised frame. Fixed points on an unchanged part do not exist when the part changes with each requirement.
- **Records:** append-only, so stopping a campaign never overwrites a failure. Tests are tracked and in CI from step 0.
- **References:** each benchmark's reference and the grader's version are fixed beforehand. References are graded again whenever the grader changes. Production's metal read three ways as fastcae's mesher and rules changed.

### 9.3 Reproducibility

- Datasets come from a frozen pipeline: one commit, one rules and profile version, one tool version per derivation. One command and a config regenerate them. A dataset run refuses a dirty tree.
- CP-SAT, where used, runs with one worker and a **deterministic** limit (`max_deterministic_time`), not a wall-clock one. A solve cut off by wall time returns whatever it held at that moment, which depends on the machine's load. Each solve logs OPTIMAL or FEASIBLE, and ties are broken explicitly. Every random draw has a stored seed.
- Agent campaigns are reproducible as a procedure: the same brief, tools and budget in a clean session, with repeats and their spread reported.

### 9.4 The 1,000 root problems

The cohorts are From Rib Placement's:

| Cohort | Roots | Purpose |
|---|---:|---|
| Core coverage | 500 | Sobol or Latin-hypercube sampling of loads, bounded layout, envelope and targets, then a feasibility filter |
| Counterfactual pairs | 200 | One requirement changed at a time (mass, bore stiffness, modal band, orientation): this teaches cause |
| Pareto sets | 150 | One physical problem re-solved under different priorities |
| Infeasible and boundary | 100 | Taught by the bound: spec repair, impossibility, safe failure |
| Held-out family | 50 | A new mount pattern or bore-layout region, never trained on |

- **Splits** are by layout family and root problem, never by mesh. A root problem's descendants never cross a split.
- **Coverage is counted by governing regime,** not by N: torsion or bending, stiffness or frequency, mounted on the motor or on bushings. The process is held to one profile in V1 (7.6), and becomes an axis only when a second profile exists. The sampler fills the regime grid evenly. Once a surrogate exists, a curator picks the next roots where the regimes are thin and the surrogate is least sure (section 10).
- **Phasing:** 10 roots by hand → 100 (L1) → 1,000 (L1 → bounded L2).

## 10. Learning

The evidence for this section is [the AI-technology report](../../../../fastcae/docs/research/2026-10-06-ai-technology-for-the-platform.md) (6 October). The rule is the engineer's: a learned model is a screen, never the judge. It earns its place by saving TET10 proofs or screen readings, or by preventing failed ones.

### 10.1 What can be learned at this data scale

| Target | Learnable? | Evidence |
|---|---|---|
| Global scalars: interface motion, stiffness, strain energy, largest displacement | **Yes**, from a few hundred designs | PhysicsBench: displacement R² 0.93-0.98 at 200 designs; BMO-GNN and DeepJEB R² 0.96-0.99 from 700-1,700 |
| Natural frequencies (as scalars) | **Yes** | DeepJEB: the first two frequencies at R² 0.988-0.990 (MAPE 2.9-4.1 %) from about 1,710 designs. 4 % of a 900 Hz mode is 36 Hz, so designs near a modal limit still need FE |
| Mode shapes (as fields) | **Not yet** | Every model R² < 0 on DeepJEB's mode-shape fields (PhysicsBench) |
| Stress fields | Partly, within a family | R² 0.76-0.83 at 200 designs |
| **Peak stress at fillets** | **No**; it stays with FE | No published model found; meshing the same part twice already moves element stresses about 18 % |
| Mass | **Never learned**: it is computed exactly | - |

### 10.2 The order

| # | Component | Replaces | Built from | Data it needs | Switched on when |
|---|---|---|---|---|---|
| 0 | The deterministic tools (exact mass, unit-load superposition, the voxel screen with adjoints, CP-SAT legality, the rules) | - | Exists | - | Always |
| 1 | **A calibrated scalar KPI model, which is also the candidate ranker.** It learns the gap between the TET10 result and the scaled screen | Screen readings at pool scale (milliseconds instead of about 41 s); proofs wasted on poor candidates | A Gaussian process (BoTorch), with gradient-boosted trees and TabPFN v2 as challengers, and split-conformal intervals | 30-100 proofs per family; every proof adds a pair | It beats the scaled screen on rank correlation and regret on held-out proofs. A warning applies: agenticCAE's 250-design surrogate ranked only 2.4 % better than random |
| 2 | A failure and cost predictor (optional) | Failed or dangerous proofs: meshes past memory, stalled solves | A deterministic estimate first (elements from the size field), then a small classifier | Every attempt, failures included | Failures cost more than about one proof in twenty |
| 3 | **A field surrogate** for displacement and strain-energy density | Proofs during screening. It tells the agent where the compliance sits | A Transolver-family model (GeoTransolver in PhysicsNeMo, Apache-2.0) on points sampled from the TET10 mesh, each tagged with its region (bore A, mount 2, structure); OODGuard; an uncertainty head | Hundreds to low thousands of proofs across root problems | The scalar model's errors show that the field carries information the scalars lack |
| 4 | **Action ranking:** (a) model-based, scoring each move by component 1's or 3's prediction and uncertainty; (b) later, a value model learned from the campaign tree | Proofs and agent turns spent on moves that do not pay | (a) No new data. (b) Digi-Q style | (b) thousands of logged transitions | (a) once 1 is on; (b) at thousands of transitions |
| 5 | A trained policy: SFT, then GRPO with the FE as verifier | The frontier model, if cost or privacy demands it | A small open model | About 10⁴ templated tasks and a multi-GPU node: COSMO-Agent needed 20,000 tasks and 16 H200s to go from 26 % to 74.5 % | It beats the frontier agent on held-out families at lower cost |
| Not now | A learned topology initialiser (the evidence is 2D only: OAT fails on 39 % of random problems); B-rep or "shared embedding" encoders; learned checks of exact rules; mode-shape fields; a learned hypothesis prior and sensitivity records (the engineer, 7 October: later) | - | - | - | Only when a measurement shows the deterministic route is the bottleneck |

**Two corrections to the input plans.**
- A learned feasibility classifier does not come first: where a process rule is exact, its check is cheap and right already. Learn only the failures that are expensive to discover (component 2).
- Vanilla MeshGraphNets are not the backbone for statics. On static elasticity they had 0.63 relative error against 0.04 for a long-range GNN, and they needed 12.5 GB at 16,000 nodes. Global attention on sampled points fits the 8 GB card.

### 10.3 Where the selection lives: in code, not in the LLM

LLM agents in a Bayesian-optimisation study did no worse when their observed outcomes were randomly permuted; Gaussian processes beat them (EMNLP 2025). So:
- **the agent chooses formulations, strategies and when to stop;**
- **deterministic acquisition chooses which candidates get a TET10 proof:** a calibrated model's upper-confidence or expected-improvement rule, plus a feasibility probability near the limits, with at least a quarter of each batch random.

That is the reviewer's five levels, held exactly: the agent at level 3, the optimiser at level 4.

The published evidence for the loop: an LLM motor-design system that evaluated on its surrogate and called FEA only where unsure did up to 44 % better than FEA-only search at an equal FEA budget. Search by the AI alone ended at false optima.

### 10.4 The active-learning loop (the reviewer's loop)

1. Every campaign adds labelled pairs: screen against proof, by region and by kind of move.
2. Component 1 learns them.
3. It ranks the legal pool.
4. Proofs are spent where the model is unsure, or where it predicts that a move matters.
5. New campaigns add new pairs.

The curator (section 9.4) uses the same uncertainty to pick the next root problems.

### 10.5 One scorecard for every learned model

- **The test set** is split by root problem and family, fixed before any active learning, and never used to choose batches.
- **Errors** are always set beside the FE's own re-mesh noise.
- **Decisions, not means:** rank correlation, top-k recall, and the FE regret of the model's pick.
- **Safety:** the false-pass rate (proposed at most 1 %) and interval coverage.
- **Out of distribution:** error against distance to the nearest training design. PhysicsX measured errors growing from 15 % to 39 % with that distance.
- **In the benchmark,** learned models enter only as the declared fourth arm. A model trained on earlier runs carries their lessons, which the no-leak rule forbids for the other arms.

### 10.6 Licences, before any model is chosen

- **Usable:** Transolver (MIT), PhysicsNeMo (Apache-2.0), UV-Net, DeepSDF and BrepMFR (MIT), dl4to (Apache-2.0), TabPFN v2 weights (Apache 2.0 with attribution), OpenEvolve and ShinkaEvolve (Apache-2.0).
- **Not for the product:** BRepNet, BrepGen, Text2CAD, CAD-Recode, the TabPFN 2.5 and 3.5 weights (non-commercial). MeshSDF and TopoDiff (no licence at all).
- **Copyleft:** FEniTop, TOuNN, EngiBench (GPL-3.0).

## 11. Benchmark and demo

### 11.1 The arms, at equal budget

1. A fixed free-topology workflow: the free-density seed, then a fixed rule for what comes next. Like fastcae's look-ahead, it screens the same moves the agent can make, and it is made as strong as a fixed rule fairly can be before the agent is judged.
2. An expert heuristic: a hand-written adaptive rule set.
3. **An optimiser arm:** Bayesian optimisation over the seed formulations' continuous fields and their choice. The engineer asked for it on 1 October ("against the strongest optimisers at the same budget"), and it is still owed.
4. The agent.
5. Later: the agent with a learned surrogate (section 10).

**The kill criterion** (adopted by the engineer, 7 October). If the agent does not beat the adaptive rule-based arm (arm 2) at equal budget in P2's benchmark, the agent is not fundamental. P3's data then runs on the rule-based arm, and the agent thesis is revisited.

On fastcae's GRC housing, L0 (the rib workflow and its agent) stays as published evidence. It is not an arm on the new family.

### 11.2 Protocol

- One frozen commit and the same checks for every arm.
- **The pass mark is registered before any run.** It was never decided in fastcae, and the budget drifted between 16 and about 200 solves. Proposed: the arm that meets the contract in fewer proofs wins; else the one nearer on its weakest measure. One verdict rule for every arm: better only when the worst excess falls and the sum of excesses does not rise.
- **Three or more repeats** per arm and problem, with the spread reported. Two fastcae runs from one start ended 2.1 points apart, more than any agent-against-fixed gap (≤ 1.5). A difference inside the measured mesh noise is a tie.
- Held-out root problems, and several requirements at once. The agent's edge shows where the options outrun the FE budget, not on one library and one objective (the engineer, 1 October).
- **The budget** is counted in TET10 proofs and in wall-clock time; voxel screens are counted separately. In fastcae's fixed run of 1 October the FE took 10 of 312 minutes: proposing took 212 and meshing 71.

### 11.3 Measures

- The feasible-design rate.
- Proofs and wall-clock to the first feasible design.
- The worst normalised margin, and hypervolume under equal budget.
- Failure and recovery rates.
- Strategy switches that gained.
- Requirement coverage, and whether assumptions were right.
- Novelty: the share of material in place against the nearest design of other arms and of training. This generalises fastcae's `designs_apart`.
- Human interventions per campaign.
- **Two controls on the agent:**
  - **Shuffled FE results.** The agent's arm is run once with its FE readings permuted. If it does as well, its reasoning is not using the physics.
  - **Reflection ablated.** The same agent without its per-solve reflection, to see whether that reflection pays.

### 11.4 The demo that proves intent-conditioning

The reviewer's and From Rib Placement's experiment: **the same gearbox function, three counterfactual pairs, one requirement changed in each.**

| Pair | Changed | Expected physical reason the design differs |
|---|---|---|
| A | The mass cap is tightened | Material leaves the panels for the load paths; struts replace walls |
| B | A modal band is forbidden | Panels are stiffened or curved; mass moves to raise the first modes |
| C | The build orientation changes | Overhang control re-routes members; support-free angles appear |

For each pair, the system shows the two designs, the fields, the trajectory, and the stated reason checked against the FE. "Beautiful shapes" and "fewer solves" come second.

## 12. The build plan

**The principles** come from the engineer's rules and the plans lessons:
- One case end to end, then the batch.
- The judge is built and verified before anything it judges.
- No design freedom beyond what the checks and the provenance can carry.
- No new plan until the current phase's gate is measured. Twenty plans arrived in ten days, and the fastCAD plans reported no measured number.

Durations are estimates of working days with Claude writing most of the code and the engineer reviewing the physics and results.

### P0: Foundations, the judge and the contract (about 1 week)

- **The repository.** `fastcae-sim`, package `zenryx`, holding only what the new application needs, with nothing imported from fastcae (D1). It has:
  - a CLAUDE.md carrying this machine's pitfalls;
  - a board and features;
  - tests tracked, and CI;
  - no dependency outside the repository: fastcae (`../fastcae`, tag `fastcae-v1`) is read and copied from, never imported.
- **fastcae's parts copied in, with a parity test each** (section 13):
  - the cuDSS solve, to 10⁻¹⁰ against fastcae on a reference mesh;
  - the mesher pieces;
  - the runner and guards;
  - the harness.
- **The judge, verified independently** (plans lesson 1). Sampled requirements come with no reference deck, so:
  - analytic cases: a thick cylinder under pressure (Lamé), a cantilever, a cantilever's and a free ring's first frequencies;
  - Code_Aster re-solving two meshes;
  - reaction balance on every solve;
  - fault injection: a missing support and a reversed load must be caught;
  - a mesh-convergence protocol: the noise at two sizes.
- **The contract**, `HousingDesignSpec` v0: the schema with authority and kind on every entity, a validator, and the derived-quantity stamps.

**Done when:**
- A clean clone runs the tests and one reference solve.
- Every analytic case lies within its stated tolerance.
- The validator accepts three hand-written contracts and refuses five broken ones, each with its reason.

### P1: One requirement end to end (about 3 weeks)

- **The gearbox module v0:**
  - the EV two-stage archetype;
  - the front-end: ratio split, textbook gear sizing, shaft statics giving the reactions per case;
  - validated by the three checks of section 4.3.
- **The core template v0** in CadQuery:
  - bearing seats with shoulders and stock, the split flange with its bolt circle, three mounts, a cover opening, the oil drain;
  - every face named;
  - a sweep of its bounds: how many build, and every refusal named.
- **The domain and keep-outs:** a 3 mm voxel grid with an SDF.
- **Discovery:**
  - GPU voxel SIMP, from the cube model, with length-scale control (least member 4 mm) and an overhang filter for one build direction;
  - the bound, and the price of the process.
- **The member grammar v0:**
  - struts, plates and webs, shell patches, nodes;
  - seeded from the density by its skeleton;
  - sized by the members' own gradients.
- **Realisation:** Route B in full. Route S as a spike, the same designs both ways (5.2).
- **Proof:**
  - gmsh TET10, then cuDSS statics for every load case;
  - bearing loads as a cosine distribution over each seat's loaded half (6.1, D6a);
  - **modal**: shift-invert Lanczos on the cuDSS factor, the one new solver piece, with the Campbell check;
  - the interface measures (6.4), and the deterministic verdict.
- **DfAM checks v0** on the built geometry (section 7): least thickness, overhang map, trapped volumes, build envelope, machining stock.

**Done when:**
- One root problem gives a design that meets its contract on the TET10 proof and passes DfAM. Every number comes from the deterministic tools.
- The noise is measured at two mesh sizes.
- The gain lost from optimum to built design is measured; fastcae's plates lost most of theirs.
- Route B against Route S is decided on ten designs.
- **Gate:** if no route keeps at least most of the optimised gain on the built geometry, stop. Rethink the representation before P2.

### P2: The campaign, the arms and the demo (about 4 weeks)

- **The campaign controller:**
  - a deterministic state machine for the fixed workflow, made as strong as a fixed rule can be (with look-ahead screening);
  - the expert heuristic;
  - the optimiser arm (Bayesian optimisation).
- **The agent:** its harness and typed tools (section 8.2), and a brief of rules only.
- **The physics, widened:** the uniform-temperature case (fits and bore growth, as a thermo-elastic load on the same mesh) and park-lock holding (6.3).
- **The counterfactual demo** (11.4): one function, three pairs, the reasons checked against FE.
- **A pre-registered mini-benchmark:** three root problems × four arms × three repeats at equal budget. That is about 36 campaigns, about 36-50 hours of machine time on the laptop (estimated), run nights under the guards.

**Done when:**
- The demo's three pairs differ for the stated reasons, and FE confirms each reason.
- The mini-benchmark is read against its registered pass mark, whichever way it falls.

### P3: The dataset factory and the first models (about 6 weeks)

- **The frozen pipeline,** with the root generator: Sobol sampling, a feasibility filter, the bound, the cohorts.
  - 100 roots at L1 on the laptop, over nights.
  - Then 1,000 roots from L1 to bounded L2 on cloud GPUs, in containers. agenticCAE ran this pattern on GCP: 490 designs, no failures.
- **Campaigns:** the fixed workflow on every root; the agent on a subset of 100-200 roots, for trajectories.
- **The first learned models** (section 10), each judged against FE on held-out families.

**Done when:**
- 1,000 roots carry full records, split by family.
- The models' scores are recorded against the voxel screen and against Sobol at equal solves, whichever way they fall.

### P4: The L2 platform, and breadth (after P3)

- The L2 release: bounded layouts in the contract, the product UI (requirement → campaign → evidence).
- Steady thermal: bore growth, and the oil's heat.
- The turned-core + DED profile, and casting as the contrast profile.
- The L3 adapter: vehicle scenarios written as contracts.
- With a partner: one printed prototype, measured against its prediction. That is the ladder's "prototype-validated".

### The first PBIs (P0)

| PBI | Done when |
|---|---|
| Repository, CLAUDE.md, CI | A clean clone runs the tests |
| Solver and mesher copied in, with parity tests | 10⁻¹⁰ parity on the reference mesh |
| The analytic verification set and fault injection | Every case within tolerance; every fault caught |
| `HousingDesignSpec` v0 and its validator | 3 accepted, 5 refused with reasons |

## 13. From fastcae: what comes, and what stays

| Brought in, with a parity test each | Left in fastcae |
|---|---|
| The cuDSS static solve and its unit load cases; the deck writer, for Code_Aster cross-checks | The GRC part, its deck and every GRC-derived file |
| The face-by-face TET10 mesher pieces that apply to a surface mesh (sizing, quality checks, provenance), with agenticCAE's `surface.py` brought in | The rib library, its families and patterns |
| The cube model's voxel FE with adjoints: the seed of the topology engine and the screen | CP-SAT rib repair. CP-SAT itself stays, for discrete choices (orientation, features) |
| The rules framework's shape (FAST, EXACT, refusals with rule and place), which becomes the process profiles | The design volumes picked by hand |
| The agent harness: clean folder, allow-list, guard, transcripts, budgets, `look` pictures, hypothesis and reflection | The 143 analysis tools (their catalogue stays as a reference) |
| The runner (jobs, cancels, heartbeat, one runner), manifests and lineage, `heavy_guard`, `away_only` | The UI's GRC-shaped pages |
| The UI's 3D viewer, contour and section views, iteration pages ("what changed and why") | |

fastcae stays as it is: the GRC study, private, and the source of the L0 evidence.

## 14. Risks

| Risk | Why it is real | How it is handled |
|---|---|---|
| The optimised gain is lost when the structure is built | fastcae: 25 of 30 projected plates lost at the fuse; BESO plates kept 51-70 % of the optimised metal | A member grammar drawn for the kernel; Route S for printed structure; the gain measured on the built geometry; the P1 gate |
| Organic structure will not mesh, or exceeds the card | Thin walls need 5.8-13.7× the card (5.3); about 1 mesh in 10 crashed before SIM-12; fillet bands peak at 13.2 GB | Least member 4 mm on the laptop; the route gate; HXT and TetGen as fallbacks; the tet cap; cloud GPUs for the dataset |
| The load front-end is wrong | agenticCAE's gear statics got the directions wrong | Three checks before use (4.3) |
| The agent shows no edge at equal budget | Single runs so far; run-to-run spread larger than the gap | Problems where the options outrun the budget; strong arms; repeats; reported either way. The bound and the formulation edits are the agent's ground |
| The cheap model misleads exactly where it matters | Cubes 1.0-2.4× stiffer; restarts off by up to 19 %; the error depends on the kind of move | A validity map by move kind; the screen never decides alone; the TET10 proof decides |
| The plan drifts | Twenty plans in ten days; goals moved, so plans moved | This plan's gates. One family, one process, statics plus modal first. No new plan until P1's gate is measured |
| The laptop crashes, or blocks the work | Two blue screens on 2 October; 16 GB RAM, an 8 GB card | One heavy job at a time, with the guards; detached runners; the dataset on the cloud |
| There is no eigen-solver | A housing needs its modes; none exists in fastcae | Built in P1 on the cuDSS factor, checked against analytic and Code_Aster modes |
| The DfAM rules are not validated by a process partner | The rules come from standards and papers (section 7) | Claims stop at "process-rule-feasible"; the label ladder; a partner in P4 |
| Benchmark contamination | Briefs v2-v4 carried earlier rounds' advice | Clean runs; every brief checked before each freeze |
| Agent runs cost time and money | $1.27-16.39 a run in fastcae; 4-5 hours a 16-proof run | Agents on a subset; the deterministic factory for coverage; voxel screens inside the loop |
| The licence | GRC data is NLR's | The new family is synthetic and publishable; GRC is used only for the internal load check |
| The CAD templates are fragile | nTop reports 70-80 % of automated parametric sweeps fail; OpenCascade's weak spots | Bounded templates; refusals named; P1's sweep counts what builds |

## 15. Decisions

All taken by the engineer on 7 October 2026: D1 at 11:03, the rest at 11:41, each as recommended. The options, the evidence and what each sets downstream are in [decisions.md](decisions.md). A decision can be revisited with its reasons there.

| # | Decision | Decided | Not taken |
|---|---|---|---|
| D1 | Where the product lives | **Decided (the engineer, 7 October 11:03):** the repository `fastcae-sim` (`C:\Work\fastcae-sim`), the package `zenryx`. It is independent of fastcae: nothing imported, code copied from fastcae's tag `fastcae-v1` with a parity test each. fastcae stays the rib application, frozen | (A long-lived branch in fastcae: weighed and not taken, because independence holds by construction only in a separate repository) |
| D2 | The first family | **An EV single-speed two-stage parallel-axis reducer housing** | A coaxial planetary, the paper's round housing, as the second family |
| D2b | The housing's two parts | **Both parts designed (main housing and cover, or two halves); tied at the flange in V1's FE, each with its own build orientation**; the bolted joint checked with the finalists (VDI 2230) | One bonded body only |
| D3 | The first process | **LPBF, AlSi10Mg, with machined interfaces.** Its guidance and qualification are the most formalised (section 7) | Turned core plus DED (the paper's route: deposition on a surface, interface metallurgy, the dearest in its own costing); casting as a contrast profile in P4 |
| D4 | **Re-take the 18 September rule for printed regions.** The rule today: "voxel, shell or field geometry never produces training data". Proposed: the watertight surface made from the members' SDF is a printed region's own geometry, since it is what the printer builds. Machined faces stay exact B-rep, meshed face by face | **Yes**, gated by P1's Route S check | Keep the rule: Route B only, with every structure an exact B-rep |
| D5 | The CAD for the core | **CadQuery** (code-first, headless, on the OCP fastcae already pins) | FreeCAD (feature tree, TechDraw; named by the labs and by MEKINT); both later through the same templates |
| D6 | The physics of the MVP | **Statics for every load case plus modal in P1; a uniform-temperature case (fit loss, bore growth) and park-lock holding in P2.** A 72 mm aluminium seat warmed by 80 K loses about 66 µm of interference, more than the whole mechanical budget (6.1) | Steady conduction with oil heat in P2 rather than P4 |
| D6a | How bearing loads enter the model | **A linear cosine distribution over each seat's loaded half in P1**; the compression-only iteration measured in P0 and added later | A rigid centre (26.6 % error against test) |
| D6b | The verdict's measures and limits | **Interface measures in µm and mrad (6.4), with the limits set by the engineer per archetype**: global strain energy and peak displacement recorded, not ranked | fastcae's three measures (displacement, strain energy, metal) |
| D7 | The least member on this laptop | **4 mm**, set by the FE budget; lattices out of the MVP (homogenised only for screening). The voxels discover; the members carry the sizes (5.3) | 3 mm (does not fit the card); thin walls only on cloud GPUs |
| D8 | The benchmark protocol | **Section 11:** four arms, a pass mark registered beforehand, proofs and wall-clock as the budget, three repeats | Fewer arms for the first round |
| D9 | Where the dataset runs | **This laptop for P1-P2 and the first 100 roots; cloud GPUs for the 1,000** | The laptop only: about 100 designs a day, so weeks |
| D10 | The agent's model | **Claude Code, headless, as today**, with the model kept replaceable | Another model behind the same harness |
| D11 | The material rule for a two-process part | Ask only when the hybrid profile comes (P4) | - |
| D12 | When to show the work outside (MEKINT) | **After P1**, or earlier if the role has a deadline; from a clean repository | After P2 (the strongest demo, but later); now (fastcae's evidence only) |
| D13 | The topology-optimisation engine | **fastcae's cube model extended**: voxel FE with adjoints and GPU multigrid; dl4to as a cross-check if needed | dl4to as the engine; FEniTop or TOuNN (GPL); a commercial optimiser |
| Q&A | The engineer's Q&A record | **Adopted:** the hypothesis as the agent's unit of work, with its bookkeeping (section 3), and the kill criterion (11.1). **Accepted:** the seven corrections. **Not now:** the ontology (LLM reasoning first), sensitivity records, a learned hypothesis prior | - |

## 16. Not frozen yet

These are the reviewer's list. Each one is decided by measurement in the phases, not now.
- **The exact action space.** It starts from section 8.2, and grows or shrinks by what gains in P2.
- **How much freedom L1 gives:** a free domain at L1, and authority over positions at L2.
- **Seeds against open-ended discovery:** the seeds are starting points for hypotheses; the edits beyond them are measured.
- **Whether the agent needs textbook knowledge** (an ontology of regimes): not now. It comes in if the LLM's own reasoning stops producing good designs (the engineer, 7 October).
- **The structural representation:** explicit members, realised by Route B or Route S, decided at P1's gate. Free density-to-SDF is the fallback if the member grammar cannot reach the layouts the bound finds (section 5).
- **Which learned models are needed:** decided after the first data (section 10).
- **What counts as a novel design:** the novelty measure in 11.3, to be calibrated.
- **When the design space is exhausted:** the bound plus the hypothesis tests (section 3), to be checked against the engineer's judgement on the first ten roots.

## 17. Sources

**The research of 6-7 October.** Each report lists its sources with the date read, and tags every claim High, Medium or Low:
- [Geometry and CAD technologies: what fastcae learned, measured and read](../../../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md).
- [Lessons from the plans](../../../../fastcae/docs/research/2026-10-06-plans-lessons.md).
- [Gearbox-housing engineering](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md).
- [AM for metal housings: rules, standards and cases](../../../../fastcae/docs/research/2026-10-06-am-housings-rules-and-cases.md).
- [AI technology for the platform](../../../../fastcae/docs/research/2026-10-06-ai-technology-for-the-platform.md).

**The inputs.**
- [From Rib Placement to an Agentic Gearbox-Housing Design Platform](../../../../fastcae/docs/From%20Rib%20Placement%20to%20an%20Agentic%20Gearbox-Housing%20Design%20Platform.md) and [Agentic Mechanical Design Platform: Final Implementation Plan](../../../../fastcae/docs/Agentic_Mechanical_Design_Final_Implementation_Plan.md): the engineer's documents of 6 October.
- [A reviewer's suggestions and the researched links](../../../../fastcae/docs/inputs/plans/2026-10-06-reviewer-suggestions-and-links.md), pasted by the engineer on 6 October at 23:08 and kept verbatim. Their substance is in sections 2, 3, 9, 10.4, 11 and 16.
- The level question and its answer of 6 October: the [product page](../../../../fastcae/docs/features/product/status.md), Open.
- fastcae-sim's plan of 5 October: `C:\Work\fastcae-sim\docs\plan_gearbox.md`.
- The [recipes design](../../../../fastcae/docs/features/product/2026-10-05-recipes-not-a-menu-design.md), the [audit](../../../../fastcae/docs/features/product/2026-10-04-fastcae-audit-for-mekint.md), [MEKINT](../../../../fastcae/docs/research/2026-10-04-mekint.md), the [differentiators](../../../../fastcae/docs/features/product/differentiators.md).

**fastcae's own record.** The [agent](../../../../fastcae/docs/features/agent/status.md), [optimize](../../../../fastcae/docs/features/optimize/status.md) and [simulate](../../../../fastcae/docs/features/simulate/status.md) pages; the board, [status.md](../../../../fastcae/docs/status.md).

**Primary sources read directly for this plan.**
- Jäger & Linde, "Design and Cost Evaluation of Additively Manufactured Electric Vehicle Gearbox Housings", World Electric Vehicle Journal 16(10):552, 25 September 2025, [doi 10.3390/wevj16100552](https://www.mdpi.com/2032-6653/16/10/552). Its full text was read on 7 October.
- Porsche newsroom, ["Prototype for small-series production: electric drive housing from a 3D printer"](https://newsroom.porsche.com/en/2020/innovation/porsche-protoype-small-production-electric-drive-housing-3d-printer-23235.html), December 2020, read through search results on 6 October.
