# Designs from a chain of optimisations

**The engineer's idea of 11 October, 18:00-18:24, developed for review** (LOP-24). It was revised after the three outside reviews the engineer passed on at 19:18-19:22. The evidence is the loop's day: [the afternoon's record](../loop/2026-10-11-record-afternoon.md) and [the morning's](../loop/2026-10-11-record-morning.md). **Updated:** 2026-10-11 23:03 by Claude.

## 1. The idea

In the engineer's words (18:24), the loop should be agentic and chain several optimisations:
- The first runs free, to see where the material wants to go.
- The agent then looks at the patterns and picks the one that stands out. The next optimisation runs with that pattern, so it only has to work out where and how big the pattern should be to reach the goal.
- Concepts drive the result. If a mount is carried by the flange's bolts, the bearing bores need less structure. If it is carried by a bearing bore, the bore needs a different structure, and the design turns out different.
- For each concept, every iteration adds production-grade features and more constraints: on how the material flows, in what patterns and in what features. The end is a well-defined shape that looks like a real housing and is verified against the goal.
- "Ultimately the designs should come from optimization only, but as per the patterns and features of the production manufacturable CADs."
- A human used to interpret the result in between, and lost performance. An agent can add the constraints step by step, from what the previous solution showed (§11 says what that requires).
- Each optimisation must be fast, so that trying a concept is fast.

## 2. What the runs show

| Finding | Measured |
|---|---|
| A free optimisation finds load paths that pass every line | `outcome_hf6_4mm_7.0kg` (the height field, 4 mm, within 24 mm of the shell): 7.07 kg, bearing beds 26.0 µm (the reference 52.2), tilt 0.89 × its line, first mode 754 Hz, no clash; the optimisation took 168 s |
| ... but it does not look like a housing | Its members cover 42-48 % of each half's shell in plan. They are 13-14 mm wide at the median, and up to 34-41 mm. Production's ribs are 4-6 mm thick, cover about 10-25 % of a face, and each ends on a boss, a ring or the rim. The engineer: "like someone has spilled a thick paint on the housing" |
| Every reading made after the optimisation changed the structure | Flow C's ribs on a 6 mm field: tilt 1.20 ×, where the same field's organic drawing held 0.70 × (with 0.7 kg more metal). Clean ribs fitted to a 4 mm field: beds 84.5 µm against the field's own drawing's 42.4 (the cover's output seat kept 30 % of its metal). Production's network field read into exact CAD: 61.2 µm and 1.65 ×, against 42.0 µm and 0.83 × for its mesh drawing (both by FE; the exact CAD 0.6 kg lighter). The exact readings kept 58-73 % of the field's metal |
| Production's patterns placed without an optimiser are soft | LOP-12's styles (ZF, Kalyani, AVL), placed by the generator on the set-up of 9 October: beds 1.7-2.2 × the reference's, misalignment 4-5 × its line |
| Production's patterns placed by the optimiser pass | `outcome_ribsfieldfins24_6.7kg` (6 mm; the design space only production's network, side fins and a free run's lines): 7.27 kg, beds 37.6 µm, tilt 0.77 ×, 746 Hz. The free design of the same mass (`outcome_env24f_6.5kg`, 7.24 kg) read 33.5 µm and 0.71 ×. The network cost about 12 % of the beds' stiffness and still passed |
| Rules laid over a free field make artefacts, not features | The members' 3D rule grew a lattice (54 % of the gaps 8 mm or less). The plan gap rule broke ribs into dashes and was not met (0.61 against 0.5): beds 53.6 µm, tilt 1.30 × |
| One smooth height a column gives continuous, pull-compatible members, fast | The height field: about 10,000 design variables in place of 96,000, one run of metal per column along the pull, 168 s at 4 mm |
| The optimiser's own model flatters FE | At 4 mm by about 11-15 %: production's network read tilt 0.999 × in the model and 1.11 × by FE. The gap-rule design read 30 % better in the model. So there is no single correction |
| How a mount is carried changes the design | With each mount's region open, the arms became wide thin plates and the first mode fell to 169-230 Hz. With each mount tied straight to the nearest wall it was 733 Hz, and with the height field's arms hanging from the split, 754 Hz. The engineer's pictures of 18:24 show the same three mounts attached differently in each design |
| Half the designs clash with a gear order | 28 of the 56 designs judged on the contract's set-up hold a mode within 3 % of a gear-mesh frequency, 18 of them near stage 2's 1,127 Hz (1,094-1,154 Hz). The budget does not move it. `outcome_hf6_4mm_7.0kg` and the 6 mm envelope designs have none |

## 3. Three problems, and the one that bites first

The task is not to make a topology result look like a gearbox housing. It is three coupled problems:
1. **The architecture:** how the gears' loads get from the bearing seats to the mounts, and how the seats hold each other in line.
2. **The manufacturing geometry:** which rings, ribs, gussets, walls and junctions can express that architecture in the contract's process.
3. **The representation:** whether the optimiser's geometry, the CAD and FE's mesh are the same structure.

The third bites first. Every reading of a field changed the structure it read, so a failed reading does not show that its concept was bad. The first goal is therefore **one geometry definition that drives both the optimiser's model and the CAD.**

## 4. The method: a search that can go back

```
explore freely  →  propose concepts and feature networks  →  size them (the optimiser)
      ↑                                                              ↓
revise the sizes, the families, the network or the concept  ←  verify the exact geometry (FE, castability)
```

- **Any earlier decision can be reopened.** That includes a removed connection, a family, a mount's concept, or the vocabulary itself. A one-way chain would grow cleaner-looking while it grew structurally worse.
- **Several branches stay alive:** the free design, at least one hybrid, and each concept worth keeping. The best verified design is the incumbent. A low-fidelity score never replaces it.
- **Who does what:**

| Who | Does |
|---|---|
| The agent | Proposes alternatives, chooses each experiment, explains trade-offs, diagnoses failures; may say the evidence is not enough to choose |
| The optimiser | Computes the feasible sizes (and later the positions) of a given network |
| The geometry tools | Build the specified shape, the same for analysis and CAD |
| The judges | FE on the exact geometry, castability and the grade: every number and every verdict |
| The engineer | Approves the loads, the limits and the process's assumptions |

The agent never turns a failed verification into a pass by reinterpreting it.

- **The agent's moves are testable hypotheses.** For example: the exact design fails the tilt. Then the agent asks which explanation fits:
  - the ring is too soft;
  - a mount's connection twists the ring;
  - the wall lets the seat rotate;
  - the fast model misread a junction.

  It picks the experiment that tells them apart, such as a taller ring against a different mount path at equal mass. The answer keeps or drops the hypothesis. "The picture looks weak near the output bore" is not a move.

## 4c. The design space drawn in CAD, refined iteration by iteration

The engineer, 20:16: the agent uses CadQuery to draw each iteration's design space from what the last optimisation showed, so that the material's flow is constrained more each time while every step is proven against the goal.

| Iteration | The design space (CadQuery, from the last result) | What the optimiser does |
|---|---|---|
| 1 | Everything within the height envelope: free | Shows where the metal wants to go (the mass sweep) |
| 2 | Main regions only: round each bore the metal favoured, round each mount's arm, along the main webs; their outlines loose, no bores or bolt holes drawn yet | Places metal inside them |
| 3 | The regions sharpened into features: rings at the bores, the bolt bosses, the brackets, rib strips where ribs now show clearly | The same |
| n | Until the features are nearly filled | |

- **When to stop:** every feature is filled by the optimiser to a high share (little of the design space left empty), no feature is pressed full against its own outline (a sign it wants to grow), and the lines pass. The agent reasons from those numbers that the design space now is the design.
- **The fill only means something when the metal is not forced.** At a fixed budget the optimiser must spend all of it, so a design space the size of the budget is filled whatever the physics says. The runs that measure the fill therefore use the least-metal objective (`mass_tilt`: every line met with the factor of safety, the least metal, the budget only a ceiling).
- **The final design is the last design space itself:** its CadQuery features, each exact with its own rounded top and root fillets, joined in mesh (manifold3d's booleans with the exact shell), not fused in CAD. FE judges it. Nothing is read or redrawn after the optimisation, so nothing is lost.
- **Creativity stays in iteration 1;** each later space only narrows what the optimiser itself showed.

## 4d. The levers that reveal the pattern, graded run by run

The engineer, 20:21: the free run's settings are one set of levers. The agent grades each result and decides the next pull from it, to drive the optimisation until it reveals the pattern. No lever's result is known before it runs, so the decision is made in real time, run by run (about 3 minutes a run at 4 mm).

**The grade of a free run**, measured by tools on its field:
- **Its lines:** every tilt and bed in the optimiser's metal-or-air check, with the factor of safety. A run that misses them is not kept.
- **The paint:** the share of the shell's plan under members (production about 10-25 %).
- **The widths:** the members' median width on their centre-lines.
- **The continuity:** the separate pieces of metal on each half (few is continuous).
- **The recurrence:** whether the members stand in the neighbouring runs too.
- **The metal placed.**

**The levers:**

| Lever | Pull it when the grade shows | What it should change | Its risk |
|---|---|---|---|
| The mass (a sweep) | Always first | The core load paths at the least mass, and less paint | Below some mass the lines can't be met |
| Least metal (`mass_tilt`) | Paint with stiffness to spare | No surplus metal: the optimiser stops once the lines are met | The metal thinned evenly rather than gathered |
| A coverage limit (members on at most a share of the shell) | Still more than about 30 % covered | Fewer, taller members: ribs, with bare wall between | The bare panels soften, so watch the modes |
| The plan smoothing (6 → 5 mm) | Members still broad | Narrower members | Below about 5 mm at 4 mm voxels, noise |
| The factor of safety | The model and FE measured apart | The margin the lines are held with | More metal |
| The mounts' paths (open, or closed to a concept) | Plate-like arms, or concepts to compare | Another bracket concept | Arms that hang off as plates |

Shape rules laid over the free run (the gap rule, the 3D member rule) are not levers: they made dashes and lattices. The 24 mm height limit is the engineer's.

## 4e. The design space iterated; primitives only where a clear shape has emerged (agreed 23:03)

The engineer, 22:35-23:02, after iterations 2-4: a design space shrink-wrapped round the metal found keeps that metal's irregular outline; it must be regular, and chosen intelligently, iteration by iteration. Agreed:

**The optimiser stays general.** It knows physics and general process rules only (the pull, the height limit, the factor of safety); nothing about bores, bearings or gearboxes, so the same tool designs a bracket or a knuckle. No part-specific constraint goes into it (a coverage limit round bearing bores was proposed and dropped).

**1. The design space is iterated, with a check on it each time.**
- **A spill** is a broad patch the optimiser filled almost completely: several rib widths wide and nearly full. It is measured, on any part, wherever it is (on a seat, a face, beside a lug).
- **For each spill the agent tries another space next time:** its middle hollowed out (a narrow band kept next to the hard point); the patch cut into strips at several angles, so that the strips the optimiser fills show the directions it needs; or a lower height allowed there.
- **Each change is compared with the last:** the lines by FE, the mass, and the clarity of the pattern (fewer, narrower members, fewer separate pieces). What worked is kept; where the lines fail, the space removed was needed and part of it goes back (as strips rather than a patch).
- Which change works on a new part is not known beforehand: it is decided at runtime, and every try is on the Campaigns page with its space and its result.

**2. Standard primitives are fitted only where a clear shape of that kind has emerged.**
- **The library is general, by geometric kind:** a ring round a cylindrical seat or hole; ribs radiating from a ring; a rib between two hard points; a gusset where a lug meets a face; a pad on a flat face; fins along a wall. What is particular to a family (the trade's boss size round a bearing seat, a preference for spokes there) is data in its domain module.
- **A fitting tool** fits a primitive's parameters to a zone's metal (a rib's path between its anchors, its width rounded to 4, 6 or 8 mm, its height), with a score: the metal it captures, the space it adds, the rules it keeps.
- **A zone becomes a primitive only when the fit is clear:** its score above a threshold (most of the metal captured with little added space). Until then the zone stays free and its design space keeps being iterated (step 1); a zone no primitive ever fits stays free to the end.
- **Choosing the set:** where several zones turn into primitives together, a selection solver (an integer program: scipy's HiGHS, already used by `tobs.py`; or CP-SAT) picks the set that captures the most metal with the fewest features under the rules (ribs at least the sand gap apart, crossings at 60° or more, even spokes, every hole held, every mount joined).

**3. The optimiser fills the chosen space, FE judges, the agent revises:** primitives left empty dropped, half-used ones refitted, a failing line answered by a change to the space; until every primitive is mostly filled and FE passes. The final design is the primitives drawn exact with fillets, and the zones still free drawn as they are, joined in mesh.

## 5. One geometry: the feature network

**The network is read from where the free optimiser put its metal, never from a library of patterns** (the engineer, 19:36: "if the placed material is like ribs then we place ribs, but again optimally"; scattering rib patterns everywhere for the optimiser to pick from is what fastcae did). Each member the free run made becomes the matching feature, at its own place and in its own direction:
- a long narrow member becomes a rib along its centre-line, ending on the boss, bolt or ring it reaches;
- metal round a bore becomes a ring;
- a broad web becomes a web, or ribs of production's thickness carrying the same section, if FE agrees;
- each mount's arm becomes its bracket along the arm's path.

The optimiser then sizes those features again, and shifts their ends: that is the "again optimally". The CAD is built from the same list. The clean ribs of 15:28 were read the same way but never optimised again, which is why a seat kept the reading's error and lost 70 % of its metal. If a design still misses, a free run in the space the features leave shows where metal is still wanted, and that place becomes the next feature. Variety comes from several free runs (other budgets, each mount held to a different attachment), not from candidates the optimiser never placed.

The design is a small graph, and both the optimiser's model and the CAD come from it.
- **Nodes** are the structural attachment places: the bearing rings, the bolt bosses, the mount roots, flange segments and junctions.
- **Edges** are the connections: ribs, webs, gussets and fins, straight or one arc.
- **Each edge's attributes:** whether it is active, its family, its thickness, its height along it, and the rules it must keep.

**In the optimiser:** each edge covers the plan columns under its thickness, and each column's height is its edge's height there. This is a linear map from the network's few parameters to the columns. It replaces the free height field's plan filter, so the existing height-field machinery (`topo.Voxels`' height mode, its derivatives, GCMMA) runs a network unchanged, with tens of variables in place of 10,000.
- The thicknesses are fixed per family in the first version, and the heights are continuous.
- The rib's fully rounded top and its root fillets are allowed for in the heights, so that both models carry the same metal.

**In the CAD:** each edge is an exact plate of that thickness along its line, with its top at the same heights, fully rounded, filleted at its root. Each node is a boss or a ring. Draft (0°), fillets, overlaps and the contract's cuts are either in both models or accounted for in both.

**Junctions are first-class.**
- An edge stands no higher than the node it meets (a linear constraint).
- Where three or more edges meet, the node is a boss of bounded size, so that it does not become a hot spot.
- Every edge is connected at both ends.
- The fillets at a junction are drawn, not left to chance.

**Families from the start, not as a clean-up afterwards:**
- a few families, each with one thickness and one height law, with a limited deviation per feature;
- tightened where verification shows margin, split where a family's uniformity causes a verified failure.

**Freedom in levels:**
1. presence and size (first);
2. position and curvature: feature mapping, where each feature's position, angle and size are variables projected onto the analysis grid with their derivatives ([Wein, Dunning & Norato 2020](https://doi.org/10.1007/s00158-020-02649-6));
3. a small free region at a critical joint, when the vocabulary cannot pass there (the height field's own columns).

**A feature the optimiser drives to nothing is removed by an edit,** and the next run sizes the network without it. No remnant is ever drawn. Each feature's least length and its connectivity are checked.

## 6. Concepts: how the mounts join the housing

| Concept | How the mounts are carried | What it asks of the bores | The risk to measure |
|---|---|---|---|
| A. By the flange | Each lug tied by a pair of gussets to its two nearest bolt bosses, with a rim rib along the flange | Rings and spokes for the gears' loads only | The flange's compliance, a longer path |
| B. By a bore | Each lug tied by a strut to the nearest bearing bore's ring | Heavier rings and spokes on the mounts' side | The seat distorted by the mount's reaction |
| C. By the wall | Each lug on a pad with a fan of gussets into the nearest wall | Ribs across the end faces' panels | Soft panels, plate-like arms, low modes |
| D. Free or hybrid | The free run's arms closed, or the concepts mixed | Whatever the optimiser finds | More complex geometry |

**How the agent steers a joint:** it never draws the bracket. It changes where the next run may put metal, and the optimiser grows the joint.
- **Open a path:** the arm may grow only in the concept's strip (`mount_reach`: "corridor" is concept C's path and "disc" is free; A and B are the same kind of strip to another anchor).
- **Close a path:** the free run's own arms are closed, so the optimiser must find its next-best joint.
- **Later, if needed:** "be different" (at most a share of the last design's arm metal; fastcae ran free load paths this way on 19 September) and regional budgets.

**The three mounts' 27 mixes are screened cheaply** (the 6 mm height field, about a minute each), with the free and a hybrid beside them, rather than swapping one mount at a time: the mounts interact through the shell. The best and the most distinct go to 4 mm and exact FE. Whether 6 mm ranks the concepts as FE does is checked on each screen.

**The reading is mechanical, not only geometric:**
- **First clue, geometric only** (`prototypes/first_loop/mount_concepts.py`; `data/first_loop/mount_concepts_hf6_4mm_7.0kg.png`):
  - the free run's arm metal nearest each path: mount-1, 91 % along the path to its nearest flange bolt;
  - mount-2, 55 % to two bolts, 28 % to the wall and 18 % to the output bore;
  - mount-3, 54 % to the output bore and 38 % to the bolts, as a closed loop.

  Nearness to a path is not load carried.
- **The evidence:** for each candidate connection,
  - its share of the strain energy;
  - the force through a section across it;
  - a knock-out: the connection removed, the optimiser's model solved again (about a second at 4 mm), and the change in the beds and the tilt read off.
- **Across runs:** what recurs over a few free runs with different levers.
- **Beyond one free run:** what the first run did not place is looked for by other free runs (each mount held to another attachment, another budget) and by a free run in the space the features leave, never by a library of candidates.

## 7. What counts as success

- **A design passes** when FE on its exact geometry meets every graded line, at no more metal than the reference's 7.73 kg, and castability gives its rung. The lines are:
  - the bearing beds stiffer than the reference's 52.2 µm;
  - every seat's tilt within its line (against the shaft's line, the shaft's own lean included);
  - no mode within 3 % of a gear-mesh frequency.

  This is the engineer's rule: lower displacement than production, with no more metal. The judged case is peak drive, as the engineer set on 10 October.
- **The mass is a ceiling, not a target.** Among the designs that pass, the result is a Pareto set over the beds, the tilt margin, the modal separation, the mass and the geometric complexity, with the trade-offs explained. It is not one score.
- **Every run says what it optimises.** Today that is the least compliance at a set budget, with the tilt held; the budget is swept to find where designs pass.
- **Model quality and acceptance are separate questions.** The optimiser's error is measured per metric and per kind of design, and each run aims inside its lines by that error (for example the tilt at 0.85 × the line). The margin is updated from each verification. Only exact FE accepts.
- **Before anything is optimised:**
  - the optimiser's model, the FE model and the exact CAD carry the same loads, material and supports;
  - the critical outputs pass a mesh-sensitivity check.
- **Three kinds of requirement are kept apart:**
  - mandatory: the interfaces, the lines and the process's rules, as constraints;
  - structural preferences: shorter paths, balanced bores, as hypotheses;
  - presentation: families, fewer features, coverage, as measured trade-offs.

  Looking like production is never a substitute for being feasible.

## 8. The modes, in the first proof

- **The rule is the contract's:** every mode at least 3 % from the gear-mesh frequencies at the rated speed (1,127 Hz for stage 2, 2,500 Hz for stage 1).
- **What it does not cover:** a speed range, the mode's participation at the seats and mounts, or a forced response. Each would be a change to the contract, and so the engineer's.
- **To build first:**
  - FE keeps the mode shapes (it keeps none today);
  - the clashing mode is identified (what moves) and tracked from design to design by its shape (MAC), since modes change order;
  - then a constraint keeps every mode out of the band round each order. This is frequency-gap optimisation ([Du & Olhoff 2007](https://www.doi.org/10.1007/S00158-006-0088-9)), with multiple eigenvalues handled.
- **A first-mode floor would not fix a mode at 1.1 kHz.**

## 9. Manufacturing claims

- **The contract's process:** sand casting in EN AC-42100 T6 (AlSi7Mg0.3). The draft is 0° (A11: "printed sand moulds need no pattern draft; to confirm against a public rule").
- **The features are pull-compatible by construction under these assumptions.** That is not "castable". A design carries its rung (simulation-feasible, process-rule-feasible), and production approval needs a foundry.
- **Checks on the final, filleted geometry:**
  - pull accessibility, undercuts and closed voids (`castable.py`);
  - the least wall;
  - the sand's width everywhere: every pocket and every throat, not one circle per pocket;
  - the largest section (hot spots);
  - a way out for the sand.
- **The values are the process's or the engineer's:** the ribs' 4-8 mm and the least sand width. The proof spaces its candidates at least 20 mm apart, and that is an agent's assumption, labelled as one.

## 10. The order of work

| # | Build or test | Done when |
|---|---|---|
| 1 | **Diagnose the known losses** with the tools that exist (`voxel_vs_fe.py` splits a gap into the model's flattery and the drawing's change), on `outcome_prod24m_4mm_7.0kg` (model 0.999 ×, FE 1.11 ×) and `outcome_hf6_4mm_7.0kg`; the three models' loads, material and supports compared | The dominant source of each gap is known, and an exact evaluation repeats |
| 2 | **The feature network as one geometry:** the network read from `outcome_hf6_4mm_7.0kg`'s own members (§5: each member the matching feature, at its place) **and each mount's bracket** (the lug a node, its gussets or strut edges, in the concept the free run leans to: mount-1 gussets to its nearest flange bolts, mount-2 gussets to two bolts and a web to the wall, mount-3 a strut to the output bore's ring with gussets to two bolts), with the optimiser's model and the exact geometry both built from its parameters | Both built from one record |
| 3 | **Test A, representation:** the network at several sizes, the optimiser's model against FE on its exact geometry (beds, tilt, modes, mass, each junction connected), and one rib at 0°, 22.5° and 45° on the 4 mm grid | Each metric's discrepancy known, with its cause |
| 4 | **Test B, does optimising help:** the network sized by hand, the same network optimised, and the optimised network's exact FE; beside the free design and a hybrid | At least one feature-only exact design passes every line, with nothing destroyed after the optimisation |
| 5 | **Families and junctions** in the sizing | The same, with families and junction rules |
| 6 | **The modes:** shapes kept, the clash identified and tracked, then the frequency-gap constraint | The shortlist clear of the orders |
| 7 | **The mount concepts and the brackets' forms:** the 27 mixes screened, the shortlist at 4 mm and exact FE, knock-outs for attribution; for each attachment, its form compared (a pair of gussets, a strut with a rib, a V of two struts, a pad with a fan of gussets), each sized by the optimiser, the first mode watched (open plate-like arms read 169-230 Hz) | The concepts differ in measured responses, not only in looks |
| 8 | **The agent's search:** network edits chosen by the agent (add or remove a connection, change an anchor, split or merge a family, a ring segment), the incumbent kept | Every edit recorded with its hypothesis, prediction and result |
| 9 | **Test C, does the agent add value:** the same contract, tools and FE budget for a fixed chain, an adaptive algorithm and the agent | The agent against the adaptive algorithm (§11) |
| 10 | **Later:** moving features (level 2), "be different", regional budgets | When the network's freedom is shown to be short |

The 15-25 minutes a concept stays a target, but not ahead of correct decisions. Screening and parallel concepts bring the time down once the loop is trustworthy.

## 11. What agents add

The engineer's point: the next optimisation must come from the feedback of the previous one. Feedback decisions come in three kinds:

| Kind | Example | Who handles it |
|---|---|---|
| Change the sizes | Beds too soft: taller ribs | The optimiser, by its gradients |
| Choose the next experiment among known ones | Test concept B before committing to A | A design of experiments or Bayesian optimisation; no agent needed |
| **Decide what problem to solve next** | Neither concept holds the tilt, so the vocabulary may be wrong: add a loop across the bores, or ask whether the gap is the model's | **The agent:** the formulation itself changes, from mixed evidence (fields, mode shapes, castability maps, CAD failures) that no list of branches anticipates for every contract |

**Today's record shows the third kind at work.** Each change of formulation came from a result, not from a branch coded in advance:
- the height envelope, after ribs stood 63 mm proud;
- the height field, after the gap rule broke ribs into dashes;
- the smoothed drawing, after TetGen refused thin webs;
- the mounts' regions opened, after a review found the corridors steering the arms;
- the plan rule dropped, after it was measured to cap metal per disc.

**An agent can lose performance too.** The clean ribs lost 70 % of a seat's metal, and the gap rule broke ribs. What protects performance is one geometry for analysis and CAD, decisions that can be reversed, and verification after every meaningful change.

**The claim to make now:** agents automate the adaptive reasoning between engineering optimisations, rather than every branch being coded by hand. Whether they are irreplaceable is what Test C measures. The decisive comparison is the agent against a good adaptive algorithm with the same tools and FE budget, not against a fixed chain, so that the gains of adaptive search are not credited to the agent. It is measured by:
- the verified feasible designs found, and their quality and diversity;
- the FE runs used;
- the time to the first pass;
- the recovery from failures;
- a second contract run without rewriting the controller.

## 12. The product: explore, then engineer

D14 stands: exploration delivers FE-proven designs, each labelled with its rung. The feature network's exact CAD is the engineering step for the designs selected, and it is now reliable because the CAD is the optimised network itself. Finer voxels are not a cleaner design: they give the optimiser more freedom, not production's vocabulary.

## 13. For the engineer

1. **The success rule** (§7): the lines at no more than 7.73 kg, then a Pareto set. As written?
2. **The clash rule:** one rated speed, as now, or a speed range or a forced response. That is a contract change.
3. **The least sand width:** a value of the process.
4. **The load cases:** peak drive alone, as set on 10 October. The reviewers ask for every relevant case; reverse stays out unless the engineer says otherwise.
5. **Step 1 of §10, to start.**

## Sources

- Wein, F., Dunning, P. D. & Norato, J. A. (2020). A review on feature-mapping methods for structural optimization. *Structural and Multidisciplinary Optimization* 62(4), 1597-1638. https://doi.org/10.1007/s00158-020-02649-6 (open preprint: https://ar5iv.labs.arxiv.org/html/1910.10770).
- Du, J. & Olhoff, N. (2007). Topological design of freely vibrating continuum structures for maximum values of simple and multiple eigenfrequencies and frequency gaps. *Structural and Multidisciplinary Optimization* 34(2), 91-110. https://www.doi.org/10.1007/S00158-006-0088-9.
- Altair OptiStruct 2025, "Pattern Grouping" (pattern constraints set before a run): https://2025.help.altair.com/2025/hwsolvers/altair_help/topics/solvers/os/topology_opt_pattern_grouping_r.htm.
- The trade's rules and their sources: [production housings against ours](../../research/2026-10-09-production-housings-against-ours.md), §5.4.
- The three outside reviews of 19:18-19:22 are the engineer's inputs; they are not kept in the repository.
