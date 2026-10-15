# Decisions for the new platform: options, evidence, consequences

**Date.** 7 October 2026.

**Status.** **Decided.** The engineer accepted the recommended option for every decision, D2-D13, on 7 October 2026 at 11:41 (D1 at 11:03). The record keeps, for each, the options considered, the reasons, the evidence from the research already done, what each option sets downstream (libraries, methods, technology), and what is gained and lost, so any decision can be revisited with its reasons. It answers the engineer's request of 09:39.

**The engineer's Q&A record, decided the same day:**
- **Adopted:** the hypothesis as the agent's unit of work (a reason in front of each formulation), with its bookkeeping by code; the kill criterion.
- **Accepted:** the seven corrections.
- **Not now:** the ontology (LLM reasoning first; textbook knowledge only if that reasoning stops producing good designs), sensitivity records, a learned hypothesis prior.

The plan's sections 3, 8, 11, 15 and 16 say how.

**Evidence used.**
- The five reports of 6-7 October, cited by short name:
  - [geometry](../../../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md);
  - [plans](../../../../fastcae/docs/research/2026-10-06-plans-lessons.md);
  - [gearbox](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md);
  - [AM](../../../../fastcae/docs/research/2026-10-06-am-housings-rules-and-cases.md);
  - [AI](../../../../fastcae/docs/research/2026-10-06-ai-technology-for-the-platform.md).
- fastcae's own measurements: its pages and the [plan](plan.md)'s section 5.3.
- Numbers are quoted as the reports give them. A judgement without a measurement says so.

**Already decided.** D1 (the engineer, 7 October 09:11-11:03):
- the repository `fastcae-sim` (`C:\Work\fastcae-sim`), the package `zenryx`;
- **independent of fastcae**: nothing imported, code copied from fastcae's tag `fastcae-v1` where needed with a parity test each, the rest built from scratch;
- fastcae stays the rib application, tagged `fastcae-v1`, frozen except for fixes.

A long-lived branch in fastcae was weighed and not taken: independence holds by construction only in a separate repository.

---

## D2. The first product family

| Option | What it means |
|---|---|
| **A. EV single-speed two-stage parallel-axis reducer** | Three shafts: input, intermediate, output with the differential. Helical gears |
| B. Coaxial planetary | Jäger & Linde's round housing carrying ring gears |
| C. A GRC-like wind-turbine housing, made parametric | The housing fastcae knows, rebuilt as a family |
| D. A bracket (the GE jet-engine bracket problem) | No gearbox: interfaces, loads and a design space |

**Recommended: A.**

**Evidence.**
- **Gearbox:** the typical EV unit is a single-speed two-stage helical reducer with an integrated differential: ratio about 8-13, motors at 10,000-20,000 rpm, 163-650 N·m. Published gearbox optimisers leave housing deformation, NVH and the park lock to a later expert step. That step is where the platform sits.
- **AM:** Porsche printed and tested a two-stage e-drive housing (LPBF). So A has a built precedent.
- **Jäger & Linde's housing (B)** is planetary. Torsion from the ring gears governs, so its answer is an X. That is one regime, and little variety for a dataset (inferred from the paper's own result).
- **C** is NLR's data, and a 1-2 m cast-iron housing does not fit a printer's build volume (AM: 400-600 mm machines).
- **D** is licence-clean and has public comparison data (SimJEB, 381 designs, in the earlier research). But it has no gearbox physics, and the engineer's and MEKINT's domain is transmissions.

**Downstream of A.**
- **The front-end:** helical forces, shaft statics with the moment `Fa·d/2`, effective load centres and induced axial forces (gearbox).
- **Keep-outs:** three gear sweeps.
- **Interfaces:** six bearing seats, mounts, the motor flange.
- **Physics:** misalignment per stage, and a Campbell check over two mesh orders.

**Gained:** the most common EV layout; the richest load paths (three bores, axial loads, several mount schemes), so the most regimes and the most variety; a printed precedent; every number of the gearbox report applies.

**Lost:** the paper's round-housing picture (B comes second); a validation deck (C); the simplest first build (D).

### D2b. One body or two (a new point, from engineering reality)

A reducer is assembled: shafts and bearings go in, so the housing is split, either a main housing and a cover or two halves bolted on a flange. **Recommended:** design both parts. In V1's FE the two are tied at the flange (one bonded body); each part has its own build orientation; the bolted joint is checked with the finalists (VDI 2230, gearbox). Joining them by bonding is an assumption and is stated as one.

---

## D3. The first manufacturing process

| Option | |
|---|---|
| **A. LPBF, AlSi10Mg, machined interfaces** | The whole part printed, functional faces machined |
| B. A turned core plus DED (LMD) structure | The paper's route |
| C. Casting | fastcae's rules record: draft, pull, sand |
| D. No process rules | Physics only |

**Re-taken on 8 October 2026, 02:02, by the engineer: C, aluminium high-pressure die casting, with NADCA's rules.** Casting is the series process for e-drive housings, and the competitor in sight (Cognitive Design Systems) works in it. Printing stays a possible later profile. D4 is widened at the same time: field-built cast surfaces count too, since only machined faces must be exact. See the product page. The text below is the original recommendation of 7 October.

**Recommended (7 October): A; C returns as a contrast profile in P4.**

**Evidence.**
- **The rules exist only for A** (AM): ISO/ASTM 52911-1 is the design standard for LPBF of metals, and NASA MSFC-STD-3716 / MSFC-SPEC-3717 cover qualification.
- **A's values:** least wall 0.4 mm (EOS M 290); downskin under 45° needs supports; horizontal channels unsupported to about 8 mm; powder escape 1-3 mm; machining stock 0.5-2 mm; fatigue 110 MPa machined.
- **B is the least documented** (AM). No open study deposits ribs on a pre-machined aluminium part. LMD AlSi10Mg reaches about 180-220 MPa UTS against about 460 for LPBF. It was the dearest route in Jäger & Linde's own costing.
- **C is cheaper at volume:** casting about 0.20 EUR/cm³ at 100 units, against under 1.0 for SLM (Jäger & Linde). But it puts the product back in fastcae's space.
- **D** cannot be called manufacturable at all.

**Downstream of A.**
- **Topology optimisation:** an overhang filter for the build direction (Langelaar's method), a length-scale filter, a no-enclosed-void constraint.
- **Choices:** the build orientation as a discrete variable (CP-SAT); the machine envelope in the profile.
- **Checks on the built part:** a thickness map, a downskin map, a flood fill.
- **Stress:** knocked down by surface state (NASA's 60 % as built, 80 % improved).
- **Route S (SDF)** is natural, because the printer builds from a surface mesh.

**Gained:** formal rules and a qualification ladder; a built precedent; organic structure is allowed.

**Lost:** volume economics, where casting wins, so the platform's claims for A are prototypes, small series, motorsport and aerospace; the paper's hybrid story; fastcae's measured casting rules (until P4).

---

## D4. Do printed regions built through an SDF count as real geometry? (re-taking the rule of 18 September)

The rule today: "Voxel, shell or field geometry never produces training data." The engineer set it because field meshing rounded bores and edges (25 September).

| Option | |
|---|---|
| **A. Yes, for printed regions only:** the watertight surface made from the members' SDF is a printed region's own geometry. Machined faces stay exact B-rep, meshed face by face | Route S allowed for data |
| B. Keep the rule: every structure an exact B-rep | Route B only |
| C. Let voxel or field results be data, labelled | - |

**Recommended: A, gated in P1.** Route S must match Route B on the same designs within the re-mesh noise before any of its data counts.

**Widened on 8 October 2026, 02:02, by the engineer, with D3's re-take to die casting.**
- Field-built (SDF) surfaces count for **cast** regions too. The same argument holds: as-cast surfaces have tolerances of tenths of a millimetre (NADCA), and only machined faces must be exact. Machined faces stay exact B-rep, built in CadQuery.
- The gate is unchanged: Route S against Route B on the same designs in P1.
- A foundry will later need the cast shape as CAD; the conversion from field to B-rep is later work.

**Evidence.**
- **Why the rule exists** (geometry): field meshing rounds bores and edges, and a seat's shoulder was missed by up to 15.6 mm until the edge lines were spaced right. That concerns *machined, functional* faces, and A keeps those exact.
- **Why B is a risk:** B-rep booleans killed the gains before. Geometry projection gained 58 %, then 25 of 30 plates failed at the fuse on sliver faces (geometry). Trim-then-fuse works for prismatic members (14-42 s), but organic nodes cannot be drawn that way.
- **Why A is sound for printing:**
  - the printer builds from a surface mesh, and its as-built surface is Rz 30-140 µm (AM), coarser than a well-resolved SDF's error (inferred);
  - implicit geometry never fails a boolean;
  - mesh booleans (manifold3d, Apache-2.0) were chosen as fastcae's "option 2" on 25 September, but never built.
- **Why not C:** voxel FE was 14-17 % off on tilt, and the cube model reads 1.0-2.4× stiffer than the mesh (geometry).

**Downstream of A.**
- **Route S:** a sparse narrow-band SDF (OpenVDB, NanoVDB or Warp, all Apache-2.0); smooth unions with radius control; manifold3d to join with the core's crisp surface mesh; gmsh HXT to fill the volume; TetGen or fTetWild as fallbacks.
- **Data:** the record keeps the surface mesh as the printed geometry.

**Gained:** organic, print-native structure; booleans that cannot fail; no sliver faces.

**Lost:** an untested route (the risk is in P1); the comfort of one exact B-rep for everything. Contoured SDF surfaces can cross themselves (2,333 faces once), so a check is needed.

**Downstream of B:** every member must be a clean B-rep solid (cylinders, swept profiles, plates), with fillets rolled onto the mesh (4.6 min, peaking at 13.2 GB). It is proven, but cannot do organic shapes.

---

## D5. The CAD for the functional core

| Option | |
|---|---|
| **A. CadQuery** on the OCP 7.9.3.1.1 that fastcae pins | Code-first, headless |
| B. FreeCAD | A feature tree, TechDraw drawings, GD&T |
| C. build123d | Needs OCP 8: another environment |
| D. Raw OCP calls | No layer |

**Recommended: A, with FreeCAD later for engineering drawings and export.**

**Evidence.**
- **Geometry:** CadQuery runs on the OpenCascade fastcae's extraction, geometry service and rules already use, and a housing family is estimated at 2-4 days plus 1-2 for robustness. build123d needs OCP 8.
- **AI:**
  - The published CAD-CAE agent trained with an FE verifier, COSMO-Agent, used CadQuery templates with Gmsh and CalculiX.
  - Editing CAD passes far more often than generating it (CADEngBench: 1,071 against 231 items).
  - LLM-written code is executable 56-81 % of the time (RealCADBench, geometry).

  So templates with typed parameters, which the agent edits, never free code.
- **FreeCAD** is what the labs and MEKINT name. fastcae-sim's Windows-tooling research flagged a heavier install on this machine.

**Downstream of A:** CadQuery in the new virtual environment, templates by geometric kind, faces named when made (and carried through booleans by OpenCascade's history, AI), exact queries reusing the geometry service.

**Gained:** one kernel version for the whole stack; fast, testable templates; code the agent can edit.

**Lost:** an engineer-facing feature tree and drawings until FreeCAD is added; the "FreeCAD" line on a MEKINT application.

---

## D6. The physics of the MVP

| Option | |
|---|---|
| **A. Statics for every load case and modes in P1; a uniform-temperature case and park-lock holding in P2** | |
| B. Statics only in P1 | |
| C. Statics, modes and steady thermal conduction in P1 | |
| D. Fatigue early as well | |

**Recommended: A.**

**Evidence.**
- **Gearbox:**
  - A 72 mm aluminium seat warmed 80 K loses about 66 µm of interference (the report's arithmetic), more than the whole mechanical budget. So temperature cannot wait for "thermal later", but a uniform temperature captures it without a conduction solve.
  - EV noise is tonal: Campbell checks against mesh orders are standard, so modes belong in the MVP.
  - The park lock is a real load case: FMVSS 114 allows at most 150 mm of movement on a 10 % grade.
- **Geometry:** there is no eigen-solver in fastcae yet.

**Downstream of A.**
- **Modes:** a mass matrix, and shift-invert Lanczos with the cuDSS factor as the solve operator (estimated 1.5-2 days in the MEKINT research). Checked against analytic modes and Code_Aster.
- **The uniform-temperature case:** thermal strain as an initial-strain load on the same mesh, and the steel bearings' expansion for the fit check.
- **The park lock:** vehicle mass, grade and wheel radius into the front-end. Only when the archetype has a park lock.

**Gained:** the three things a gearbox engineer checks first (alignment, modes, fits); the platform's credibility with them.

**Lost:** about 3 days more in P1-P2 than statics alone. Fatigue and forced response wait for P4.

### D6a. How bearing loads enter the housing model (a new point)

The gearbox report: against measurements on a hypoid axle, the error was 26.6 % with a rigid housing and 11.7 % with eight compression-only points per seat (TU Munich 2022). A compression-only coupling is nonlinear.

**Recommended:** in P1, a **linear cosine-distributed load** over the loaded half of each seat, the common practice. Its sensitivity against a compression-only iteration on the same factor is measured once in P0.

**Lost:** some accuracy until the iteration is added.

---

## D6b. What the verdict measures

| Option | |
|---|---|
| **A. Interface measures:** per stage, the relative tilt of each shaft's two seats per face width and the centre-distance change; per seat, its tilt and ovalisation; then modes, stress and mass | |
| B. fastcae's three: peak displacement, strain energy, metal | |
| C. Compliance only | |

**Recommended: A.**

**Evidence.**
- **Gearbox:**
  - The relative skew of two shafts drives KHβ (ISO 6336-1, AGMA 927).
  - At grade 6, parallelism is 6 µm out of plane and 12 µm in plane per face width.
  - Bearing slope limits are 0.5-1.2 mrad (tapered) and 0.5 mrad for an uncrowned gear.
  - Seat roundness is 8-18 µm.
- **Plans:** fastcae's industry research (30 September) said "Global strain energy is not among the requirements". fastcae ranked by it anyway.
- **AI:** interface scalars are learnable at a few hundred designs.

**Downstream of A.**
- **KPI extraction:** each seat's face group (from the crosswalk) gives its node set, then a least-squares axis, then relative tilts and translations.
- **The optimiser's objective:** interface motion, not compliance. Its adjoint is one extra solve.
- **The contract** needs the limits: **the housing's share of each budget is not published anywhere** (gearbox), so the engineer sets it.

**Gained:** a verdict a gearbox engineer accepts.

**Lost:** simplicity. Each archetype needs the engineer's limits before P1's verdict means anything.

---

## D7. The least member on this laptop, and what the voxels can resolve

| Option | |
|---|---|
| **A. 4 mm least member, set by the FE budget**; lattices out of the MVP | |
| B. 3 mm | |
| C. The process's own least wall (0.4-1.5 mm), on cloud GPUs | |
| D. Shell elements for thin walls | |

**Recommended: A.**

**Evidence.**
- **The card's ceiling** is 412,667 TET10 (2.18 M unknowns) in single precision (simulate page). A 6 kg aluminium housing at that budget means a mean element edge of about 3.6 mm (plan 5.3).
- **The alternatives do not fit:**
  - walls at 3 mm need about 0.71 M TET10 (×1.7 the card), so **B does not fit at all**;
  - 2 mm needs ×5.8, and 1.5 mm (Porsche's walls) ×13.7.
- **Memory is the other limit:** meshes peak at 9.5-13 GB of 16, and the laptop blue-screened twice.

**A finding while writing this.** The plan pairs 3 mm voxels with 4 mm members. But a feature needs about three voxels across (geometry lesson 7), so **the voxel grid cannot resolve 4 mm members**. Resolving them would take about 1.5 mm voxels: about 9 M voxels and 27 M DOF over the envelope, too heavy here. This settles the roles:
- the voxels discover the layout at coarse scale;
- **the explicit members carry the fine sizes in their own numbers**, sized by gradients through their projected density;
- the TET10 proof judges.

It is one more reason the member grammar is needed (section 5 of the plan is to say so).

**Downstream of A.** The length-scale filter at the voxel stage is coarse; member sizing is resolution-free; the 1,000-root dataset is a cloud job.

**Gained:** fits the machine; honest proofs.

**Lost:** Porsche-like 1.5 mm walls and real lattices until cloud GPUs. Those GPUs raise the ceiling roughly 5-10× (estimated, to measure). D (shells) would need a new element type and mixed meshes: weeks.

---

## D8. The benchmark protocol

| Option | |
|---|---|
| **A. Four arms at equal budget:** a fixed workflow, a rule-based adaptive heuristic, an optimiser (Bayesian optimisation), the agent. A registered pass mark, three repeats, a shuffled-FE control | |
| B. Two arms (fixed and agent), as in fastcae | |
| C. The agent alone, with ablations | |

**Recommended: A.**

**Evidence.**
- **Plans:**
  - fastcae's comparisons were single runs.
  - Two runs from one start ended 2.1 points apart, more than any agent-against-fixed gap (≤ 1.5).
  - No pass mark was ever decided, and the FE budget drifted between 16 and about 200.
  - The engineer asked on 1 October for "the strongest optimisers at the same budget".
- **AI:**
  - LLM agents ignored permuted outcome labels (EMNLP 2025), hence the shuffled control.
  - "Scripted reflection adds nothing" in one ablation, hence a reflection ablation.

**Downstream of A.**
- **Code:** Bayesian optimisation (BoTorch or Ax) over the seed formulations' parameters; the heuristic arm's rules written out (or the ontology, if adopted).
- **Machine time:** about 36 campaigns of 10-16 proofs: 36-50 hours on the laptop (estimated).
- **Cost:** agent campaigns at fastcae's $1.27-16.39 a run, and plan usage limits. The session limit stopped work last night.

**Gained:** a claim that survives review, either way.

**Lost:** about a week of machine time and the optimiser arm's build (1-2 days, MEKINT research estimate).

---

## D9. Where the work runs

| Option | |
|---|---|
| **A. This laptop for P0-P2 and the first 100 roots; cloud GPUs for the 1,000** | |
| B. The laptop only | |
| C. Cloud from the start | |

**Recommended: A.**

**Evidence.**
- **The laptop:** about 100 designs a day here (plan estimate), and it blue-screens under heavy GPU and memory load (CLAUDE.md).
- **agenticCAE on GCP:** a Slurm cluster ran 490 designs with none failing, 29 in 36 minutes at 14 at once, about ₹2.5 a design (MEKINT research).

**Downstream of A:** a container image with gmsh, OpenCascade and CadQuery, the solver and cuDSS; batch jobs; data sync. The pattern exists in agenticCAE.

**Gained:** speed when it matters, at known cost.

**Lost:** a few days of container work before P3. B would mean weeks for 1,000 roots. C spends cloud money on debugging.

---

## D10. The agent's model and how it is driven

| Option | |
|---|---|
| **A. Claude Code, headless, through fastcae's harness, with tools kept model-agnostic (a command line now, MCP later)** | |
| B. The Claude API with the Agent SDK | |
| C. An open model (for example Qwen) | |
| D. LangGraph with another provider | fastcae's chat agent used OpenRouter |

**Recommended: A for P2; consider B for P3's scale; C only for a policy, if ever.**

**Evidence.**
- **Plans:** the harness is proven: a clean folder, a guard, transcripts and budgets, six finished runs.
- **AI:**
  - Typed tools matter more than the model (StructureClaw: 22 % to 83 %).
  - A single agent matched or beat multi-agent systems (FoamBench).
  - A small model trained with GRPO beat Claude Sonnet 4.5 on its own templated tasks (COSMO-Agent: 74.5 % against 36 %). But it took 20,000 tasks and 16 H200s.
- **This session:** the usage limit stopped three agents overnight. Scale needs either a plan that allows it or the API.

**Downstream of A:** no new framework; tools stay plain commands any model can call.

**Gained:** the fastest start, on proven ground.

**Lost:** at scale, session limits. B costs per token, but runs campaigns in parallel without session limits.

---

## D11. The material rule for a part of two materials

**Recommended: defer to P4,** when the hybrid route comes. The engineer's rule today is one material per part. The AM report found the interface metallurgy of deposition on a machined aluminium part unstudied. Nothing in P0-P3 needs it.

---

## D12. When to show the work outside (MEKINT)

| Option | What is shown |
|---|---|
| A. Now | fastcae's evidence, framed honestly, plus this plan |
| **B. After P1 (about 4 weeks)** | The above, plus one requirement end to end on the new platform |
| C. After P2 (about 8 weeks) | The counterfactual demo and the mini-benchmark |

**Recommended: B, and earlier if the role has a deadline.**

**Evidence.**
- **MEKINT research:** the company's bottleneck is its data engine and its own models, and the founder screens for governing parameters and reduced models.
- **The audit:** fastcae's "beats production" is a tie inside mesh noise, and its comparisons are single runs. So what fastcae can claim honestly is limited.
- **Plans:** claims beyond the evidence are a recorded pitfall.

**Downstream.** Anything shared outside needs a clean repository: this one holds GRC-derived results and the MEKINT research. Extracting `<app>` and the engine modules it imports takes about a day.

**Gained by B:** a working new-platform case beside real evidence.

**Lost against C:** the strongest demo (intent-conditioned designs) comes later. Against A: time, if the role closes.

---

## D13. The topology-optimisation engine (a new decision the plan had folded in)

| Option | |
|---|---|
| **A. Extend fastcae's cube model:** voxel FE with adjoints, GPU multigrid at 5 s a step | |
| B. dl4to (PyTorch 3D SIMP, Apache-2.0) | |
| C. FEniTop or TOuNN | GPL-3.0 |
| D. A commercial optimiser (OptiStruct, Ansys) | |

**Recommended: A, with B as a cross-check if needed.**

**Evidence.**
- **Geometry:** the cube model already gives adjoints, and member densities with derivatives by every number. One drawing serves the screen, the member gradients and the bound.
- **AI:** deterministic 3D SIMP on a GPU is mature: one GPU solved 65.5 M-element problems in about 2 hours. dl4to is Apache-2.0; FEniTop and TOuNN are GPL-3.0. Learned topology optimisation is still 2D.
- **Plans:** the engineer's rule is one judge, one geometry service.

**Downstream of A:**
- a finer grid with per-voxel densities;
- the overhang and length-scale filters;
- an objective on interface motion (D6b);
- the bound.

**Gained:** one physics model across screen, gradients and bound, plus fastcae's measured screen-to-FE scaling (about 2 % on strain energy once scaled).

**Lost:** a ready optimiser's features: B has them, but would be a second, separate physics model to keep consistent.

---

## D14. What a design is delivered as (11 October 2026)

**The engineer, 14:13:** "how about we change the product direction that it won't deliver the editable CAD... just provide creative designs, plausible designs, realistic designs... and once the innovation is unleashed then human gets an editable CAD build from the selected design". **And at 14:38:** "We have skipped the CAD build but not the quality of design that we can get and good looking designs without constraining creativity and innovation."

**Decided:**
- Each design is delivered as an FE-proven, castable mesh with its evidence: the grade, castability, mass, pictures and settings. It is not delivered as editable CAD.
- Editable CAD is built later, only for a design the engineer selects.
- The design's quality and looks are kept. The optimisation stays free, with no patterns (13:07). How metal may stand (the casting rules, the members' plan rule) and how each member is drawn are the tools for clean, attractive designs.

**Evidence:**
- Every exact-CAD reading of a free field failed somewhere: 58-73 % of the metal kept, slivers, refused booleans ([CAD from a free optimisation](2026-10-11-cad-from-a-free-optimisation.md)).
- The mesh route built every field, and FE judged it in minutes.
- The three outside proposals reviewed at 14:02-14:16 agreed.
- Generative design is used the same way: the tool proposes, and a designer rebuilds the chosen design.

**Consequences:**
- D5 (CadQuery) stays, for the exact shell and the hand-over.
- The relief route (flow D) becomes the hand-over's helper for a selected design, not part of the loop.
- An evidence pack and a clarity score become part of every design.

---

## D15. Designs come from a chain of optimisations (11 October 2026)

**The engineer, 18:00:** "someone should really recreate the identified features/pattern again and fuse with existing CAD and add fillets and then deliver... otherwise it looks like someone has spilled a thick paint on the housing". **And at 18:24:** "it should be agentic which should chain multiple optimizations to iteratively derive the design... ultimately the designs should come from optimization only but as per the patterns and features of the production manufacturable CADs"; a designer reading the result afterwards loses performance, an agent can add the constraints inside the loop.

**Decided:**
- A design comes from a chain of optimisations, never from a reading made after one. The first runs free; the agent reads its patterns and a concept (how each mount is carried, how each bore is held); each next optimisation places and sizes production's features inside that concept, and each step adds manufacturing-grade features and rules.
- The first optimisation stays free (13:07, revised): patterns enter only as the agent reads them from it.
- Each optimisation is fast, so that a concept is tried in minutes.

**Evidence:** every reading after an optimisation lost performance when measured (flow C's ribs: tilt 1.20 × against the organic drawing's 0.70 ×; clean ribs: beds 84.5 µm against 42.4; exact readings kept 58-73 % of the metal); production's styles placed without an optimiser were 1.7-2.2 × too soft at the beds; production's network placed by the optimiser passed every line (`outcome_ribsfieldfins24_6.7kg`: 7.27 kg, 37.6 µm, 0.77 ×).

**Consequences:**
- The method, for review: [the chained optimisation](2026-10-11-chained-optimisation.md) (LOP-24).
- D14 may be revised: the chain's last step is exact CAD by construction, so every design could be delivered as exact CAD. That is the engineer's to decide.

---

## D16. The design space is fixed in every iteration (12 October 2026)

**The engineer, 19:30:** "I don't want iterate changes in the design space → that will remain fixed in all the iterations… and that will be between the shell and the packaging space".

**Decided:**
- One design space for a whole campaign: the room between the shell's outer face and the packaging space, less what the contract keeps clear. This is the contract's own definition of what the optimiser is given ("the packaging less all of the above"). The shell is fixed with it.
- No iteration redraws the design space from a run's metal: no masks, regions, strips or held-empty volumes.

**Revises:** D15's chain, in that its iterations no longer narrow the design space ([the chained optimisation](2026-10-11-chained-optimisation.md) §4c and §4e), and the agent's role in [the plan of 11 October](2026-10-11-the-plan-agents-and-structural-design.md) (choosing where the next design space goes).

**Open:**
- What an iteration may change instead: the engineer's next instruction.
- Whether the 24 mm height envelope (11 October 13:21) stays inside the space.

**Evidence (Claude's, from the trials; the engineer gave the rule without a reason):** two days of iterated spaces (11-12 October) left the designs organic inside them, whether each space was traced from the last run's metal, drawn as regions round the hard points, or cut into sections ([the chained optimisation](2026-10-11-chained-optimisation.md) §4c-§4e; the loop's [record of the night of 12 October](../loop/2026-10-12-record-night.md)).

## D17. Patterns from a library, every parameter from the optimiser (13 October 2026)

**The engineer, 17:45:** "I am ok to keep a pattern library -> but the dimensions orientations, placement, thickness, height its parameters etc should be derived from optimization and not guessed by you... I am ok to have a workflow where you do a free optimization and then identify patterns and then choose a relevant pattern from library and let the optimize size it, decide the number of members it needs and its parameters etc.. but I am not ok agent choosing some nice guess of parameters values that just happened to work.." Also: modes far from the gear orders may be kept in the optimisation; keep margins; and a good result (straight brackets) must be a result, not an ask: when the optimiser is asked for that result's performance, does it deliver the straight bracket?

**Decided:**
- A library of production patterns is allowed (spokes, gusseted lugs, bridges, collars, ribs).
- The flow: a free optimisation first; the agent identifies the patterns in it and picks the relevant family from the library; the optimiser sizes it: the number of members, their placement, orientation, thickness, height and every other parameter.
- The agent never sets a pattern's parameter values. A fixed pattern whose values the agent chose is not a result.
- The modes may enter the optimisation (held clear of the gear orders), with margins on every line.
- A result found by hand becomes a test: asked for its performance, can the optimiser deliver it?

**Revises:** the overnight campaign's last designs (LOP-28, `final14`-`final18`): their cover spokes (every 30°, 6 x 12 mm) and gusseted lugs (two 8 mm webs, 25 mm apart at the wall) were fixed with values the agent chose. They stand as a reference of what is reachable (`final16`: the modes 12-14 % from the orders), not as a result.

**Evidence:** `final16`'s brackets lifted every mode and cleared both orders by 12 % and more, but their form and sizes were a guess checked after; a runtime agent guessing so on any other geometry would need luck (the engineer, 10:07 and 17:09).

---

## The decisions at a glance

| # | Decided (7 October) | The deciding evidence |
|---|---|---|
| D2 | EV two-stage reducer; both housing parts designed, tied in V1's FE | Typical EV unit; Porsche's printed precedent; the most regimes |
| D3 | LPBF AlSi10Mg; casting as a contrast in P4 | ISO/ASTM 52911-1, NASA 3716/3717; DED undocumented and dearest |
| D4 | SDF-built printed regions count, machined faces exact; gated in P1 | Fuses killed the gains (25/30 slivers); printers build from meshes |
| D5 | CadQuery; FreeCAD later for drawings | One kernel; COSMO-Agent; editing beats generating |
| D6 | Statics and modes in P1; uniform temperature and park lock in P2; cosine seat loads | 66 µm fit loss at +80 K; tonal EV NVH; no eigen-solver yet |
| D6b | Interface measures in µm and mrad | KHβ, 6/12 µm per face width; strain energy is not a requirement |
| D7 | 4 mm least member; voxels discover, members carry sizes | The card's ceiling; three voxels a feature |
| D8 | Four arms, a registered pass mark, three repeats, a shuffled control | 2.1-point run spread; LLMs ignore numeric feedback |
| D9 | Laptop to 100 roots, cloud for 1,000 | 100 designs a day; agenticCAE's GCP pattern |
| D10 | Claude Code now, tools model-agnostic | The proven harness; typed tools matter more than the model |
| D11 | Defer | Not needed before P4 |
| D12 | Show after P1, or earlier for a deadline | Honest claims; a clean repository first |
| D13 | Extend the cube model; dl4to as a check | One judge; adjoints and derivatives exist |
| D14 (11 October) | Designs delivered as FE-proven meshes with their evidence; editable CAD only for a selected design, later; quality and looks kept, the optimisation free | Every exact reading of a free field failed somewhere; the mesh route builds every field |
| D15 (11 October) | Designs come from a chain of optimisations: free first, then optimisations constrained to production's features as the agent reads them, concept by concept | Readings after an optimisation always lost performance; production's network placed by the optimiser passed |
| D16 (12 October) | The design space is fixed in every iteration: between the shell and the packaging space, never redrawn from a run's metal | The engineer's rule (19:30); iterated spaces left the designs organic inside them |
| D17 (13 October) | Patterns from a library, every parameter (count, placement, orientation, thickness, height) from the optimiser after a free run; the agent picks the family only; modes may be in the optimisation; margins kept | The engineer's rule (17:45); the overnight's lugs and spokes were the agent's guessed values |
