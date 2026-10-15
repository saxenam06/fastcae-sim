# Structural parts designed from requirements, with agents: the problem, the approach, where we are

**Written** 11 October 2026, 23:10, by Claude with the engineer, from the day's work (LOP-23, LOP-24); **revised 23:21** after an outside review, agreed by the engineer (the features' own parameters optimised once a region holds features; the solver for admissibility; the stopping rule on verified geometry; the modes and one bearing bore first). The evidence behind each number: [the agent's log](../loop/2026-10-11-agent-log.md), [the afternoon's record](../loop/2026-10-11-record-afternoon.md), [the chained optimisation](2026-10-11-chained-optimisation.md) (the method in detail, revised after three outside reviews), the Campaigns page.

## In short

- **The product:** an engineer states what a structural part must do: where it connects, what loads it carries, how much room it has, what it must achieve, how it will be made. zenryx designs the part. Every design is proven by finite-element analysis (FE), and every decision is recorded. The first part family is the housing of an electric car's two-stage gearbox; brackets, mounts and other structural parts come next.
- **The problem:** optimisation finds strong shapes, but they look nothing like parts a foundry makes. When a designer redraws them into proper features afterwards, much of the performance is lost. When a designer starts from experience instead, the parts look right but are far from optimal.
- **Where we are:** the whole flow runs on one laptop in minutes per design. A design 27 % lighter than the reference passes every requirement, verified against the specified FE model and load case. An agent loop (Claude driving the optimiser move by move, every decision shown on the UI) is narrowing the design space toward production's features, and the shape is converging.
- **The bottleneck:** the design spaces are still traced from the optimiser's own blobs, so the result keeps their irregular, "spilled paint" look, worst on the bearing bores. Nothing yet turns them into the regular features a designer would draw.
- **The proposal:** let free optimisation discover the architecture; then represent each region by explicit, parametric features from a general library (rings, ribs, gussets, pads) and **optimise those features' own sizes and shapes** against the requirements, rather than letting a density field fill a feature-shaped envelope. Two loops: the optimiser sizes and shapes the current features; the agent changes which features exist, where they connect, which family to try, or reopens a region. Verified as drawn, by FE and the casting checks.
- **The role of agents:** the decisions between optimisations (where to put the next design space, which experiment to try, when a shape has emerged, why a run failed) depend on evidence that differs for every part. A fixed workflow cannot anticipate them. An agent can: it looks at the pictures, reads the measurements, decides, logs why, and talks with the engineer in plain language. The tools compute every number and give every verdict.

## 1. The product

**What the engineer gives:** a contract, in the engineer's own terms:
- the part's functional interfaces: bearing seats, bolt circles, mounting points;
- the loads and the load cases;
- the package it must fit in;
- the targets: stiffness, alignment, natural frequencies, mass;
- one manufacturing process, for example sand casting in EN AC-42100 T6 with its rules.

Everything that can be calculated from these (forces, reactions, gear-mesh frequencies) is calculated by a tool, never typed in.

**What zenryx returns:** designs that meet the contract, each one:
- **verified by FE** against the contract's model and load cases: stiffness, alignment, natural frequencies and mass judged against its lines;
- **shaped for the process,** passing its encoded casting checks (undercuts, wall thickness, sand access; more rules as they are encoded);
- **with its evidence:** the grade, the pictures, the settings, and the record of every decision that led to it;
- **with editable CAD** for the design the engineer selects (decision D14).

**Who uses it:** design engineers who know their part and its requirements, not optimisation specialists.

**What it is not:** a tool for one part. The core knows geometric kinds (a cylindrical seat, a fastener circle, a flat face) and physics; what is particular to a family (a gearbox's bearings, a bracket's lugs) lives as data. The gearbox housing is the first family because it is hard: alignment, stiffness, noise and castability all at once.

## 2. Why it matters

Today a structural part is designed in one of two ways, and both lose something.

1. **Optimisation, then a designer.** An analyst runs topology optimisation, a method that places material where the loads need it. It returns an organic shape. A designer then redraws it as ribs, rings and walls a foundry can cast. That redrawing takes days. It needs expertise. And it **loses performance:**
   - our own readings lost 30-70 % of the stiffness;
   - one redrawn design's bearing deflection doubled, from 42 µm to 84 µm;
   - another's alignment went from 0.70 to 1.20 of its limit;
   - the exact-CAD readings kept only 58-73 % of the optimiser's metal.
2. **A designer from experience.** The parts look right, but they are not optimal. Production-style ribbing placed by rule, without optimisation, was 1.7-2.2 × too soft at the bearings on our housing.

Commercial optimisers can impose patterns (symmetry, cyclic patterns, a draw direction), but a specialist must choose them before the run, and cannot revise them from what the run shows.

**What closes the gap:** the step between optimisation and design is a chain of judgements made on evidence: what the result shows, which feature expresses it, what to try next. It can happen inside the loop, many times, with each choice proven by the optimiser and FE. When we let the optimiser itself place production's rib network, the design passed every requirement and gave up only about 12 % of the stiffness of a free shape.

## 3. The problem, precisely

Three problems are coupled:

| Problem | The question | How it shows on our housing |
|---|---|---|
| **The architecture** | How do the loads travel from the bearing seats to the mounts, and how are the seats kept in line? | Where the optimiser puts its arms and webs; how each mount joins the housing |
| **The manufacturing geometry** | Which features (rings, ribs, gussets, pads) express that architecture, castably? | Production uses thin ribs between hard points; the optimiser makes broad patches |
| **The representation** | Are the optimiser's geometry, the CAD and the FE mesh the same structure? | Every redrawing changed the structure; the optimiser's coarse model overrates thin members by 11-30 % |

**The gearbox's requirements** (the contract's lines, judged by FE):
- bearing beds stiffer than the reference's 52.2 µm;
- every bearing's tilt within its line;
- every natural frequency at least 3 % from the gear-mesh frequencies;
- mass no more than the reference's 7.73 kg;
- castable in a two-part sand mould: along the pull, the least wall 4 mm.

## 4. Where we are

**The flow, end to end, on one laptop (an 8 GB GPU):**
1. **The contract:** validated; the loads and frequencies derived by tools.
2. **Optimisation:** a "height field" optimiser on 4 mm voxels, with one height per point of the part's plan. It places metal that comes out of the mould by construction. It holds every requirement as a constraint, with a safety factor for its own optimism. About 2-4 minutes.
3. **Drawing:** the result drawn as a watertight mesh on the exact shell; seconds.
4. **FE:** quadratic tetrahedra solved on the GPU; about 2-3 minutes. Castability is checked beside it.
5. **Grade and UI:** the Designs page shows every design's process step by step. The Campaigns page shows the agent's moves, each with its decision, design space and results.

**Results, judged by FE:**

| Design | Mass | Beds (≤ 52.2 µm) | Tilt (≤ 1.0) | Modes | Verdict |
|---|---|---|---|---|---|
| The reference | 7.73 kg | 52.2 µm | - | - | the design to beat |
| The baseline: free optimisation, smoothed | 6.89 kg | 30.7 µm | 0.88 | one clash | fails one line; looks like spilled paint |
| **`it1_free_5.5kg`: less metal** | **5.63 kg** | **36.8 µm** | **0.93** | **clear** | **passes every line, 27 % lighter than the reference** |
| `it4_refined_5.8kg`: production-shaped design space, 4th iteration | 5.92 kg | 39.4 µm | 0.98 | one clash | passes beds and tilt; one mode 2 % from a gear order |

**What the day established:**
1. **The "spilled paint" was surplus metal, not structure.** Asked to spend 7 kg, the optimiser spread the spare metal over the shell. Asked for the least metal that meets the requirements, it kept the load paths and dropped the paint: about 1.5 kg less.
2. **The same load paths recur at every mass:** webs between the bores, rings round them, arms to the three mounts, spokes on the cover. They are real, not accidents of one run.
3. **The design-space iteration converges.** Three times the design space was cut down to what the optimiser used, shaped toward production's features. In the fourth iteration, 29 of 47 features are 70-95 % filled, and beds and tilt pass by FE.
4. **The optimiser's model must be trusted per measure, with margins learned from FE.** The tilt needs a factor of 1.25 on lean, feature-shaped designs; the beds 1.5. The margins were set from the measured gaps, move by move.
5. **The agent loop works as a loop.** Nine moves, each logged with what it saw, its hypothesis, its lever, what changed, what it expected and what came back. The engineer can see each one on the UI.

## 5. The bottleneck

**The design spaces are still traced from the optimiser's own blobs.** Each iteration's space was the metal found, slightly grown. So it inherits that metal's irregular outline, and the result still looks organic, not like a production housing.

**The worst case is the bearing bores.** Every load enters there, and stiffness and alignment are measured there. So the optimiser piles solid metal round each bore, as high as it may. A production housing instead has a short boss round each bore with ribs radiating from it. That holds the bearing almost as well with much less metal, and avoids a thick lump that would cast porous beside the seat.

**Two further gaps:**
- **The modes:** every lean design so far has put one natural frequency near a gear order, and nothing in the optimiser steers the modes yet.
- **The look of the final drawing:** members are drawn from the optimiser's coarse voxels, so even the right features come out rough.

## 6. The proposal

**6.1 The optimiser stays general.** It knows physics and general process rules (the pull direction, the height limit, the safety factor). Nothing in it knows what a bearing or a bore is, so the same optimiser designs a bracket or a knuckle.

**6.2 Free optimisation discovers the architecture; it does not dictate the shapes.** The free run (and a few with other settings) shows where the metal wants to go: the recurring paths between the seats, the mounts and the shell, and the response fields that carry the load. An unrestricted reference is always kept, and design spaces may grow again as well as shrink, so a useful path removed by one choice can come back.

**6.3 Two linked representations.**
- **A structural graph for the architecture:** nodes are the functional interfaces and the main junctions (seats, mounts, flange regions, shell junctions); edges are the candidate connections (ribs, webs, gussets). The free runs suggest edges; they do not fix their exact outlines.
- **A parametric geometry model for the realisation:** each chosen connection is an explicit feature attached to the part's faces, from a general library by geometric kind (a ring round a cylindrical seat or hole, ribs radiating from it, a rib between two hard points, a gusset where a lug meets a face, a pad on a flat face, fins along a wall; fastcae's parametric rib is the start). **One feature definition drives the optimiser's geometry, the drawn geometry FE verifies, and the editable CAD:** its thicknesses, paths, heights and transitions are never re-read at a later stage. What is particular to a family (the gearbox's boss size round a bearing seat) is data.

**6.4 Once a region holds features, it is optimised as features: two loops.**

| Loop | What changes | Who |
|---|---|---|
| **Inner** | The current features' sizes and shapes: a boss's height and extent; each rib's thickness, height profile, position, angle, curvature within its limits, root blends; whether a feature exists | The optimiser, by gradients |
| **Outer** | Which features exist, where they connect, which family to try; whether a region is reopened for free optimisation | The agent, between runs |

Features are a current hypothesis, never a fixed architecture. The conversion happens region by region: a clear rib becomes an explicit rib, a clear boss an explicit boss, an ambiguous junction stays free and is marked as unresolved geometry.

**6.5 Competing families early, committed when verified.** Where the evidence supports several forms (a boss with spokes, a boss with a partial ring web, a boss tied straight to its neighbours), the agent offers them as branches from the start, with comparable budgets, and commits a region to the family that wins by FE. Ambiguous regions stay free.

**6.6 A solver for what is allowed, not what is best.** A selection solver (an integer program: scipy's HiGHS; or CP-SAT) answers the discrete questions: which candidate features can coexist, which combinations break spacing, access or casting rules, which arrangements join every required interface, which deserve continuous optimisation. Covering the free run's metal generates candidates; it never ranks them. Performance is ranked by the optimisation and by FE: redrawn geometry that kept most of the metal still lost stiffness (§2).

**6.7 The stopping rule.** A design is done when its geometry, as drawn, passes FE and the casting checks, and further iterations improve it by less than a set amount. How full a design space was is a diagnostic, not a goal.

**6.8 The modes from the first proof.** The meaning of the rule is settled first (one operating point, a speed range, or a forced response: the engineer's call); until then the contract's rule is optimised, without wider claims. The modes' shapes are identified and tracked by shape as the geometry changes (MAC), clustered modes looked at together; candidates are screened for the modes before expensive verification; and the agreed frequency constraint enters the feature optimisation (Du & Olhoff 2007).

**6.9 The agent's experiments, each with six fields:** a hypothesis; one primary intervention; the expected, measurable effect; a run budget; an acceptance criterion; a rollback target. Logged move by move and shown on the Campaigns page. Typical moves, each a hypothesis to test, never an automatic diagnosis:

| Evidence | The agent's test |
|---|---|
| Beds pass, a seat's tilt fails | Another boss support or connection layout at that seat |
| The static lines pass, a mode clashes | A change round the mode's deforming region |
| The optimisation passes, the drawn geometry fails | The representation checked before any metal is added |
| A rib passes, its junction fails a casting check | The junction or the arrangement changed |
| A feature family keeps losing to free geometry | Another family, or the region reopened |

**6.10 Concepts as branches.** Structural alternatives, such as a mount carried by the flange's bolts against one carried by a bore, run side by side and are compared on FE.

## 7. The role of agents

**Who does what:**

| Who | Does |
|---|---|
| **The tools** (deterministic) | Every number and every verdict: the loads, the optimisation, the drawing, FE, castability, the fill, the fit scores, the selection solver |
| **The agent** | The decisions between runs: where the next design space goes, which experiment to try on a spill, when a shape has clearly emerged, which features to offer, why a run failed (the space, the margin, the drawing or the concept), when to stop; and the explanation of each |
| **The engineer** | The requirements and the process; the direction and the ideas; what "good" means; the decisions that change the contract, the process values or the load cases |

**Why an agent, and not a fixed workflow.** Inside a fixed formulation, feedback is handled well by numerical methods. An optimiser follows its gradients, and Bayesian optimisation picks the next experiment from earlier ones. Our problem needs more: the feedback changes the formulation itself.
- the design space, its faces and its regions;
- the vocabulary offered;
- which experiment to run;
- whether a failure belongs to the concept, the space, the margin or the drawing.

These choices are made on mixed evidence: fields, pictures, fill measures, FE results, mode shapes, castability maps. And they differ for every part and every requirement. In principle any one choice could be written as a rule. In practice, enumerating them for every part, every process and every surprise is not feasible: a new bracket, a softer load case or a different gear train would need the workflow rewritten. An agent handles the unforeseen case, because it reasons about the evidence rather than following a branch.

**Why multimodal.** A designer spots a pattern by looking: spokes forming round a bore, an arm shaped like a wedge, a spill. The agent is given the same pictures each iteration (the field on each face, the design space in 3D with its fill shaded, the spills marked) beside the tools' numbers. The pictures are for spotting and for hypotheses; the numbers are for decisions. Every decision rests on a measurement a tool can check.

**What the agent may not do:** write a derived number, declare a pass, or change the contract's limits, the process's values or the load cases. Those belong to the tools and the engineer.

**How the claim will be proven.** "Agents automate the adaptive reasoning between engineering optimisations, instead of every branch being coded by hand." It will be tested by giving the same contract, tools and FE budget to an adaptive algorithm and to the agent (Test C). The measures:
- how many verified designs each finds, and their quality;
- the FE runs used;
- the time to the first pass;
- recovery from failures;
- a second part family run without rewriting the controller.

## 8. The human, the agent, and plain language

The engineer and the agent work in natural language, and that is the product's interface, not a convenience.

- **The engineer says what and why, in their own words:** "this looks like someone has spilled thick paint on the housing"; "the mount could hang from the flange's bolts instead of the bore"; "the design space should be a parametrised feature from a library, not fitted exactly to the material"; "it must iterate on the design space, and put standard primitives only when clear shapes emerge". Each of these changed the method within the hour.
- **The agent turns intent into levers and experiments,** reports back plainly (what it tried, what happened, what it learned), and says when a decision is the engineer's.
- **Ideas from outside enter the same way.** Three outside reviews of the method arrived as text. Their sound points were adopted within the hour: one geometry for analysis and CAD, a search that can go back, families early, the modes in the first proof. The points that went too far were answered.
- **One record serves both:** the decision log, shown on the Campaigns page, is what the engineer reads to follow and correct the agent. It is also what a runtime agent learns from, and what Test C measures.

So plain language connects the engineer's intent to a deterministic engineering stack. The engineer sets the goal and the judgement of what "good" looks like. The agent decides how to get there and tries it. The tools compute and judge. And the engineer can step in at any move.

## 9. The plan

Ordered to retire the hardest uncertainty first: can regular, parametric features keep the performance once drawn?

| Step | What | Done when |
|---|---|---|
| 1 | **The verification baseline:** the passing free-form design (`it1_free_5.5kg`), its exact geometry and its analysis settings kept as the reference | Reproducible from its record |
| 2 | **One bearing bore as explicit features:** the protected seat, the reinforcement as parameters (boss, ribs, partial ring web, ties to neighbours), a small free region only if needed; four branches (boss with radial ribs; boss with a partial ring web and ribs; boss tied to the neighbouring bores or mounts; the free-form reference) at comparable mass; each branch's feature parameters optimised, drawn as features, judged by FE with the modes | One problematic bore patch replaced by regular, parametric reinforcement that passes as drawn, its mass and performance against the free form known |
| 3 | **The modes in that experiment:** the modes' shapes identified and tracked, candidates screened | The clashing mode located and steered on the bore's branches |
| 4 | **One shared feature definition** for the optimiser, the drawing and FE; the remaining discrepancy measured | The model and FE agree within the margins on the features |
| 5 | **Extended** to the web between the bores and one mount's connection | The representation holds beyond one bore |
| 6 | **The admissibility solver** (HiGHS) generating admissible layouts | Layouts that keep every rule, ranked by the optimisation |
| 7 | **The runtime agent** over these tested operations (as fastcae-agent was built), and **the design space in 3D** on the Campaigns page | The agent runs a campaign end to end, every move on the page |
| 8 | **A bracket** on the same tools, then **Test C**: the agent against an adaptive algorithm, the same budget | A bracket designed without changing the core; the agent's value measured |

## 10. Risks and open questions

- **Regular features cost some stiffness:** about 12 % with production's network today. The bore experiment measures it region by region, and a region that needs freedom keeps it, marked as unresolved.
- **The 4 mm model overrates thin features.** Margins per measure, calibrated from each verification, cover it for now; one shared feature definition (step 4) and later feature mapping at finer resolution shrink it.
- **One GPU, one heavy job at a time.** Branches run in sequence, about 10-15 minutes each.
- **The GPU's Cholesky factorisation hung on restricted design spaces;** those runs now take the pivoting symmetric one.
- **The claims, at this stage:** "verified against the specified FE model and load case", "passes the encoded casting-design checks" (the pull, the least wall; section transitions, draft, cores, radii and heavy sections are not yet all encoded), "editable CAD demonstrated for the supported feature families" once the final assembly produces it. The reported numbers are this repository's records.
- **Open, the engineer's:** the minimum sand gap's value; whether the mode rule covers a speed range or a forced response; whether peak drive stays the only load case; archiving the older web records (the bundle needs a 6 GB heap).

## Sources

- Wein, F., Dunning, P. D. & Norato, J. A. (2020). A review on feature-mapping methods for structural optimization. *Structural and Multidisciplinary Optimization* 62(4), 1597-1638. https://doi.org/10.1007/s00158-020-02649-6.
- Du, J. & Olhoff, N. (2007). Topological design of freely vibrating continuum structures for maximum values of simple and multiple eigenfrequencies and frequency gaps. *Structural and Multidisciplinary Optimization* 34(2), 91-110. https://www.doi.org/10.1007/S00158-006-0088-9.
- Altair OptiStruct 2025, "Pattern Grouping": https://2025.help.altair.com/2025/hwsolvers/altair_help/topics/solvers/os/topology_opt_pattern_grouping_r.htm.
- The trade's rules for cast housings and their sources: [production housings against ours](../../research/2026-10-09-production-housings-against-ours.md), §5.4.
