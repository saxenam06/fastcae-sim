# Solving the Verified Bracket Design Problem

## Executive answer

The problem is solvable, but not as a single end-to-end generative model. The most credible architecture is a **verified design compiler**: natural-language requirements are compiled into a typed engineering contract; several process-specific parametric CAD generators produce candidates; deterministic geometry, manufacturing, and physics checkers reject invalid candidates; multi-fidelity optimization allocates simulation budget; and only an independent high-fidelity verification pipeline can issue a pass. Learning models should accelerate search and rank candidates, never be the authority that signs them off.

The highest-value initial product is narrower than the full vision: **single-piece brackets carrying a rigid payload, with fixed mounting and payload interfaces, linear structural dynamics, random vibration fatigue, shock/static strength, and optional steady conduction**. Start with two manufacturing families—bent sheet metal and machined plate or 2.5D extrusion—and add additive/casting only after the verification core is stable. Sheet metal and machined designs provide editable parameters, strong manufacturability rules, low-cost prototypes, and sharply different cost-volume trade-offs; they therefore test the core thesis better than an additive-only demonstrator.

The central research contribution should not be “AI makes bracket shapes.” It should be **an auditable closed loop that knows what was specified, what remains unknown, why each model is valid, what uncertainty changes the verdict, and when to abstain**. Recent engineering-agent benchmarks reinforce this framing: attractive or executable CAD is not equivalent to correct engineering, and solver completion is not evidence of physical validity.[^1][^2][^3]

## Reframe the goal

The product should return a **set of defensible decisions**, not merely geometry. For each process family it should answer: Is there a feasible concept? What requirements bind? What assumptions dominate? What is the estimated unit cost at the requested volume? Which evidence supports each claim? What is the residual risk? If the request is incomplete, the correct output is a minimal set of questions; if no design survives robust verification, the correct output is an infeasibility certificate and the smallest requirement relaxations that restore feasibility.

A useful formalization is a mixed discrete-continuous, multi-objective, robust design problem. Discrete variables select the process, material, concept grammar, joint model, and optional thermal path; continuous variables govern thicknesses, bend positions, rib dimensions, hole offsets, fillets, and local features. Objectives are mass, recurring cost, non-recurring tooling cost, lead time, and risk. Constraints cover static stress, displacement, modal separation, random-vibration fatigue, shock, joint slip/separation, temperature, envelope, tool access, and process rules. Uncertain variables include damping, joint stiffness, contact conductance, thickness/material scatter, and load-spectrum scaling.

This decomposition avoids a common category error: process selection is not a late manufacturability filter. The process changes the allowable design representation, cost model, material state, tolerances, feature rules, and physics. It must therefore sit at the root of a branching search graph.

## Recommended architecture

| Layer | Responsibility | Recommended implementation | Hard rule |
|---|---|---|---|
| Requirement compiler | Convert language into a typed, unit-safe contract; detect omissions and contradictions | JSON Schema/Pydantic, Pint units, retrieval from controlled standards and material records | No unspecified load or qualification may be silently inferred |
| Concept portfolio | Select several genuinely different process/concept families | Rule-based portfolio plus diversity-aware bandit | Do not let one globally trained generator collapse all processes into one shape style |
| Process CAD compilers | Generate editable designs and manufacturing metadata | build123d/CadQuery/FreeCAD Python; one grammar per process | Native parameters and semantic face selectors are source of truth, not tessellated meshes |
| Geometry/DFM verifier | Check topology, envelope, clearances, tool access, minimum features, process rules | OCCT checks, voxel/ray queries, exact B-Rep measurements, process-specific rule engine | Reject before meshing when possible |
| Analysis compiler | Create solver-neutral analysis intent, then solver decks | Typed intermediate representation, deterministic templates, unit tests | LLM does not write unrestricted solver input directly |
| Simulation ladder | Run analytic, coarse FE, refined FE, and independent confirmation | Gmsh/Netgen/SALOME; CalculiX and Code_Aster or commercial reference | Every fidelity has a declared applicability domain |
| Optimizer | Choose parameters, concepts, fidelity, and next experiments | BoTorch/Ax, pymoo, OpenMDAO, Dakota | Optimize probability of feasible improvement, not an unpenalized surrogate score |
| Evidence ledger | Store inputs, artifacts, hashes, solver versions, diagnostics, margins, provenance | PostgreSQL + object store + immutable manifests | A result without complete lineage cannot support a verification claim |
| Independent verifier | Rebuild and audit from the engineering contract | Separate read-only process or agent using fresh meshes/checks | Generator cannot grade itself |
| Learning system | Train surrogates, failure classifiers, policies, and retrieval | PyTorch/PyG/NeuralOperator plus calibrated UQ | Surrogate can guide; only verified solvers/tests can sign off |

A solver-neutral **engineering intermediate representation (EIR)** is the architectural keystone. It should contain dimensional quantities, coordinate frames, interfaces, payload rigid-body properties, load spectra, thermal sources/sinks, required outputs, uncertainty distributions, candidate process/material sets, manufacturing rules, and evidence thresholds. The EIR should be compiled into CAD, mesh-control, solver, cost, and report artifacts. This makes every translation testable and prevents conversational context from becoming an invisible model input.

The analysis compiler should use deterministic, versioned templates rather than free-form input generation. New agentic FEA systems show that execution feedback, task decomposition, and iterative checking improve success, but published benchmarks still show large gaps between runnable code and correct physics. A 2026 comparative study further suggests that equal access to tools and repair budget can matter more than elaborate multi-agent role structures, so the system should start with a simple orchestrator and invest first in checkers, contracts, and feedback quality.[^4][^5][^6]

## Requirement compiler

Create a domain-specific language with four states for every requirement: **specified**, **derived by an approved rule**, **assumed with explicit approval**, or **unknown/blocking**. Values require units, reference frames, tolerances or distributions, provenance, and an applicability interval. Standards should be retrieved into structured clauses, but licensed text should not be reproduced into the dataset; store clause identifiers and organization-owned interpretations.

The compiler should perform dimensional checks, coordinate-frame closure, load-case completeness, interface consistency, and feasibility screening. Examples include a thermal lower bound based on required conductance, a modal upper-bound estimate based on available stiffness and payload mass, gross-section stress bounds, minimum fastener count and edge-distance rules, and a cost floor. These checks can reject impossible or underspecified requests before CAD generation.

For automotive vibration, the mounting configuration must be represented explicitly. ISO 16750-3 warns that a support bracket can amplify or attenuate the test load and requires the transfer function and control strategy to be considered when a bracket is unavoidable; it also identifies fatigue-related breakage as a central purpose of the vibration test. Thus, “ISO 16750-3 body vibration” is not a sufficient scalar input: the mounting location, relevant profile, axes, duration, DUT/bracket test configuration, and transfer-function interpretation must be resolved.[^7]

## Geometry representation

Use **process-specific parametric programs over exact B-Reps**, not a universal latent shape as the primary representation. A design should consist of a concept-grammar identifier, a compact parameter vector, construction history, semantic interface entities, keep-out/tool-access metadata, and generated manufacturing artifacts. Meshes, signed-distance fields, point clouds, and graphs are derived views for simulation and learning.

For the first release, implement these grammars:

- **Bent sheet metal:** one or two planar webs, flange graph, bends, hems/gussets, holes/slots, stamped beads, embosses, local doublers, and optional captive hardware. Parameters include gauge, bend radius, bend angle, flange width, reliefs, bead paths/width/depth, and hole-to-edge distances.
- **Machined plate or extrusion:** stock envelope, 2.5D pockets, through-holes, ribs left by pocketing, chamfers/fillets, datum faces, tool approach directions, and setups.
- **Later casting:** parting direction, draft, cores, uniform-wall targets, ribs/bosses, machining allowances, and porosity-sensitive zones.
- **Later additive:** build orientation, support accessibility, minimum wall/strut size, trapped-volume prevention, machining stock, and anisotropic material allowables.

build123d is a Python parametric B-Rep framework built on Open Cascade and targets CNC, laser cutting, and 3D printing workflows; CadQuery supports STEP/DXF import-export but preserves full parametricity in its Python source rather than neutral STEP. That makes the source program plus parameter manifest the editable master, while STEP is the exchange artifact. Semantic selection must avoid brittle “face number 12” references: interfaces should be created as named construction objects and recovered with geometric predicates if topology changes.[^8][^9]

A process grammar gives stronger validity guarantees than unrestricted text-to-CAD and makes optimization tractable. It may reduce novelty within one grammar, so novelty should come from a **portfolio of grammars**, grammar composition, new feature placement, and occasional topology-derived concept discovery—not from removing all constraints.

## Candidate generation

Use four complementary generators rather than betting on one method:

| Generator | Best use | Strength | Limitation |
|---|---|---|---|
| Parametric grammar + optimization | Production designs in known process families | Editable, DFM-safe, data-efficient | Novelty bounded by grammar |
| Topography/free-form shape optimization | Sheet beads and rib patterns | Excellent stiffness/frequency gain with little mass | CAD reconstruction and stamping limits need checking |
| Density/topology optimization | Load-path discovery for casting/additive/machined ribs | Finds non-obvious paths | Raw density fields are not manufacturing-ready CAD |
| Retrieval and mutation | Seed concepts from validated prior designs | Fast, interpretable, low failure rate | Can narrow diversity and repeat historical bias |

For thin sheet brackets, topography optimization deserves first-class status. It modifies surface geometry with beads/embossments while largely retaining material distribution, and studies report its use to raise natural frequency and improve sheet-metal stiffness without simply thickening the part. A recent method combines vertex morphing with grayscale morphological operations to generate engineering-like bead patterns, suggesting a route to differentiable bead discovery that can later be projected into explicit CAD features.[^10][^11][^12]

For solid concepts, use topology optimization mainly as a **teacher and proposal mechanism**. Open-source implementations exist using FEniCS, dolfin-adjoint and IPOPT for 2D/3D SIMP optimization with adjoint sensitivities. FEniTop brings topology optimization to FEniCSx and parallel computing, while TopOpt.jl supports multiple material models, 2D/3D domains, unstructured meshes, automatic differentiation, and several optimizers. However, none replaces the process-specific CAD reconstruction and DFM verification layer.[^13][^14][^15][^16]

Generate diversity deliberately. Maintain separate archives indexed by process, concept grammar, load-path signature, and performance. Use quality-diversity search such as MAP-Elites or a process-conditioned novelty archive, with feasibility as a gate and objective quality inside each cell. Distinctness should be measured by both geometry and engineering behavior: feature grammar, load path, modal strain-energy distribution, active constraints, process plan, and cost breakdown.

## Physics ladder

Each requirement needs a ladder from cheap screening to sign-off. The system should record which rung produced each value and why that rung is valid.

| Requirement | Search model | Intermediate model | Sign-off model |
|---|---|---|---|
| Static strength | beam/plate bounds, section properties | linear shell/solid FE | converged solid or shell FE with justified joints/contact; nonlinear if needed |
| First modes | lumped payload + beam/plate model | shell or coarse solid eigenanalysis | refined prestressed/contact-aware modal model where preload affects stiffness |
| Harmonic response | modal participation estimate | modal FRF | converged frequency response with damping uncertainty |
| Random vibration | modal response + PSD moments | FE transfer functions and stress PSD | refined modal random response plus fatigue method and sensitivity |
| Shock | static equivalent acceleration initially | response spectrum/modal transient | time-domain transient when nonlinear contact, yielding, or pulse details matter |
| Fatigue | hotspot screening | spectral fatigue | verified S-N data, mean-stress/notch corrections, uncertainty and critical-location convergence |
| Joint integrity | bolt-group statics | connector/preload model | contact/preload model with slip/separation checks where required |
| Temperature | resistance network | shell/solid conduction | contact-aware conduction with radiation/convection assumptions and uncertainty |

For random vibration fatigue, calculate transfer functions from base acceleration to stress, combine them with the input PSD to obtain stress PSDs, and use a spectral cycle method such as Dirlik for stationary Gaussian broadband screening. Dirlik is widely used because it usually approximates time-domain rainflow better than narrow-band Rayleigh assumptions, but broadband/non-Gaussian, multiaxial, or nonstationary cases require escalation or cross-checking.[^17][^18][^19]

Bolted interfaces are likely to dominate prediction uncertainty. Literature shows that boundary contact stiffness cannot simply be ignored when accurate modal prediction is required; tangential stiffness is especially important for torsional behavior. Connector-based models such as six-degree-of-freedom CBUSH equivalents can be useful, but their stiffness should be calibrated or represented probabilistically rather than treated as universal constants.[^20][^21][^22][^23]

Thermal analysis must include the module-to-bracket and bracket-to-rail contact resistances. A design that satisfies conduction only under perfect contact should fail robust verification. If the bracket is the sole heat path, the pre-CAD feasibility check should compare required thermal resistance, available footprint, material conductivity, plausible contact conductance, and geometric path length.

## Meshing and solvers

A practical open toolchain is:

- **Geometry:** build123d or CadQuery over OCCT; FreeCAD for inspection and interoperability.
- **Meshing:** Gmsh Python API as the default; SALOME/SMESH for shell workflows, groups, alternative algorithms, or complex hybrid meshes; Netgen as a second mesher.
- **Structural solve:** CalculiX for reproducible linear static, modal, and harmonic workflows; Code_Aster for richer structural dynamics/contact/fatigue capabilities; one commercial solver for periodic cross-validation if available.
- **Post-processing:** meshio, PyVista, ParaView, NumPy/SciPy, and custom result validators.
- **Optimization/UQ:** BoTorch/Ax, pymoo, OpenMDAO, Dakota, IPOPT/NLopt.
- **Workflow:** Python, Prefect or Dagster, containerized workers, PostgreSQL, object storage, and MLflow or an equivalent lineage layer.

Gmsh provides C/C++/Python/Julia APIs and OpenCASCADE integration. SALOME SMESH can combine meshing algorithms, retain geometric groups, run through Python for reproducibility, and provides mesh-quality controls; its HOMARD module supports local adaptation. This supports an important anti-correlation tactic: remesh final candidates with a second algorithm and compare key outputs rather than relying on one mesh generator.[^24][^25]

CalculiX supports modal-basis steady-state dynamics, recovering eigenfrequencies, mode shapes, stiffness, and mass from a prior frequency step. It is suitable for an MVP but should not be assumed to cover every random-vibration, contact, or fatigue workflow natively. Implement spectral post-processing as a tested library, and use Code_Aster or a commercial reference for challenging sign-off cases.[^26]

## Automatic verification

A successful solver exit code is only one check. Recent CAD–CAE evaluation found many candidates that reached the solver yet violated limits or disagreed physically; validity across a single nominal parameter state also missed failures exposed by parameter changes. Automatic verification should therefore operate at five levels:[^1]

1. **Contract checks:** units, coordinate frames, required load cases, standards interpretation, payload inertia, and uncertainty definitions.
2. **Model-construction checks:** material coverage, orphan nodes/elements, element normals, shell thickness, disconnected regions, duplicate constraints, load/resultant balance, mass and center-of-gravity reconciliation, and semantic boundary-condition coverage.
3. **Numerical checks:** mesh-quality limits, rigid-body modes, energy/reaction balance, residuals, modal effective mass, eigenvalue ordering, contact status, time-step/frequency resolution, and mesh convergence.
4. **Physics checks:** hand-calculation bounds, monotonic perturbation tests, symmetry expectations, limit cases, and comparison against an independent solver/model.
5. **Decision checks:** margins use the correct allowable, uncertainty is propagated, fatigue duration matches the specification, and no claim exceeds the evidence.

Treat each checker as code with unit tests and adversarial fixtures. NASA guidance calls for verifying geometry, material data, units, boundary conditions, solution procedures, mesh refinement, element sensitivity, and comparison to analytic or independent solutions where available. ASME V&V 10 frames verification, validation, and uncertainty quantification as distinct credibility activities and emphasizes intended use.[^27][^28][^29]

The independent verifier should consume only the EIR and candidate master CAD, not the generator’s intermediate reasoning. It should rebuild meshes, re-identify interfaces, recompute properties, and rerun essential analyses. This information barrier prevents shared mistakes from passing because both “designer” and “reviewer” copied the same assumption.

## Robust design and UQ

Separate uncertainty into **aleatory variability**, **epistemic/model uncertainty**, and **specification uncertainty**. Examples are material scatter and assembly torque (aleatory), uncertain contact model or damping law (epistemic), and missing vibration axis or unclear thermal boundary (specification). The last category cannot be repaired by Monte Carlo sampling; it requires a question or explicit program decision.

Use a staged UQ plan:

- Run global sensitivity screening with Morris or Sobol methods on simplified models.
- Retain dominant uncertain parameters for Latin hypercube or polynomial-chaos studies.
- Optimize robust metrics such as upper quantiles of stress/damage/temperature and lower quantiles of frequency/margin.
- Report probability of feasibility only when input distributions are defensible; otherwise report bounded scenario robustness.
- Require final candidates to remain feasible across specified tolerances and credible interface-property ranges.

Dakota already supports optimization, UQ, parameter estimation, sensitivity analysis, surrogate-based optimization, mixed-integer methods, and optimization under uncertainty through a solver-agnostic interface. OpenMDAO is stronger when analytic derivatives and tightly coupled models matter; it supports decomposition, parallel methods, and large gradient-based design spaces.[^30][^31][^32]

## Multi-fidelity optimization

Use a **portfolio scheduler** rather than one monolithic optimizer. Each process/concept branch has a local optimizer; a top-level bandit allocates evaluation budget according to expected feasible Pareto improvement, information gain, diversity deficit, and branch maturity. Failed jobs remain valuable if the failure is classified precisely.

For compact continuous parameterizations, constrained multi-objective Bayesian optimization is a strong default. BoTorch/Ax supports noisy constrained multi-objective acquisition functions such as qNEHVI/qLogNEHVI and represents solutions as a Pareto front rather than forcing one arbitrary scalar score. For high-dimensional bead fields or topology variables, use adjoint gradients or quality-diversity/evolutionary methods; Bayesian optimization should then operate on lower-dimensional concept and process parameters.[^33][^34]

A useful evaluation policy is:

1. Screen every candidate with exact geometry/DFM and analytic bounds.
2. Run coarse models for candidates with plausible feasibility.
3. Use surrogates to rank uncertainty-aware expected improvement.
4. Promote candidates near constraints, outside the training domain, or likely to change the Pareto front.
5. Run refined, independently meshed models only on promoted candidates.
6. Reserve physical tests for uncertainty reduction, model discrepancy estimation, and final validation—not merely for confirming easy cases.

Active learning should choose data that improves **decisions**, not global average field error. Prioritize candidates near pass/fail boundaries, regions where models disagree, unseen concept/process cells, and parameters with high expected value of information. Compare this policy against fixed Latin-hypercube and random sampling at equal compute, as required by the brief.

## Surrogate strategy

Do not begin with a universal geometry-to-all-physics foundation model. Initial data will be too small, process distributions too different, and the false-pass cost too high. Start with modular surrogates:

- Scalar feasibility/ranking models for mass, first frequency, peak stress, temperature, and cost.
- Modal reduced-order models that predict eigenvalues and mode-subspace quantities, not raw mode index alone.
- Graph or mesh neural networks for stress/temperature fields only after stable mesh correspondence or operator representations exist.
- Residual models that correct a cheap physics model rather than replacing it.
- Failure classifiers for CAD, mesh, solver, and model-validity states.

Mode tracking requires the Modal Assurance Criterion or subspace correlation because modes can cross and exchange order as geometry changes. Train against invariant quantities such as clustered eigenvalue subspaces, modal effective mass, strain-energy localization, and transfer functions. For random vibration, predicting the stress PSD or reduced transfer function is often more reusable than directly predicting fatigue life, because life depends heavily on material S-N assumptions and exposure duration.

Uncertainty should combine ensembles or probabilistic surrogates, OOD detection, and post-hoc calibration. NeuralUQ documents Bayesian and deterministic approaches and notes that deep ensembles can provide useful model uncertainty for neural PDE/operator models. However, studies find that some neural-operator UQ methods fail under even moderate distribution shift, while ensembles correlate better with high-error regions. Conformal calibration can add finite-sample coverage under exchangeability, but coverage does not automatically survive distribution shift, so an explicit abstention/OOD gate remains mandatory.[^35][^36][^37][^38]

Use three gates before accepting a surrogate-assisted pass: the candidate is inside the validated applicability domain; calibrated uncertainty is below a requirement-specific threshold; and a physics residual or independent cheap model is consistent. Otherwise promote to FE. Track the most safety-relevant metric: **false pass rate on unseen requirement families**, not only RMSE.

## Manufacturing and cost

Cross-process comparison requires a process plan and a cost model, not mass multiplied by a rate. For each candidate estimate material and scrap, purchased hardware, setup, cycle time, machine/labor rates, tooling and amortization, inspection, finishing, yield/scrap, and logistics. Report recurring unit cost, non-recurring cost, and uncertainty separately.

The generic unit-cost structure is:

\[
C_{unit}=C_{material}+C_{process}+C_{labor}+C_{tooling}/N+C_{setup}/N+C_{inspection}+C_{finish}+C_{scrap}+C_{overhead}
\]

where batch volume \(N\) changes the ranking. Process-based cost models map physical design parameters to cycle times, resources, yields, and facility needs before converting resources to cost. Published bracket process-selection work likewise shows that volume can move the break-even point between alternatives, so the platform must expose the crossing volumes rather than announce one timeless “cheapest process.”[^39][^40][^41]

Use interval estimates early and calibrated estimates later. A relative ranking can be useful before a detailed route exists, but the system should label its maturity. Seed machine rates, material prices, bend/pierce times, tooling models, and scrap factors from local suppliers; generic public databases will not produce defensible Bengaluru or supplier-specific quotes without calibration.

## Dataset design

Existing bracket data are useful pretraining material but not a sufficient benchmark. SimJEB contains 381 cleaned, simulated human designs from the GE challenge under four linear-static load cases. DeepJEB expands this to 2,138 synthetic designs with B-Reps, second-order volume meshes, field/scalar results, and modal data. DeepJEB++ reports 15,360 simulation-labelled designs, but it remains derived from the same GE-style interface and linear-elastic problem family.[^42][^43][^44]

Build a new dataset around **programs and evidence**, not only shapes. Each record should include:

- Requirement EIR and original controlled-language request.
- Process/material choice and concept grammar.
- Parametric source CAD, parameter history, semantic interfaces, and manufacturing artifacts.
- Every mesh and solver deck, model version, diagnostics, and convergence record.
- Scalar and field outputs at all fidelities.
- Uncertainty samples and robust verdict.
- Cost model inputs and process route.
- Failure taxonomy and repair actions.
- Agent decisions, retrieved evidence, and human interventions.
- Physical-test setup, raw data, uncertainty, and model-update record when available.

Split by **requirement family, interface topology, process, concept grammar, and load regime**, not random designs. A random split over mutations of the same seed geometry will substantially overstate generalization. Keep a sealed physical-validation set and a challenge set authored after system development.

The failure taxonomy should distinguish requirement, geometry-kernel, manufacturability, meshing, boundary-condition, material, solver, numerical-convergence, post-processing, model-validity, and true physical infeasibility failures. Preserve invalid candidates and near misses. They are essential for training rejection models and preventing repeated mistakes.

## Agent design

Use the LLM for planning, requirement dialogue, tool selection, diagnosis, and explanation—not numerical authority. All numeric claims should be read from typed tool outputs. Give the agent callable operations such as `compile_requirement`, `generate_sheet_concept`, `check_dfm`, `run_modal`, `run_random_vibration`, `estimate_cost`, and `verify_candidate`, each with strict input/output schemas.

Adopt a state machine:

1. Parse and normalize.
2. Ask blocking questions.
3. Generate a process portfolio.
4. Create and validate geometry.
5. Run physics ladder.
6. Optimize and promote candidates.
7. Independently verify.
8. Produce evidence-backed explanations.
9. Escalate unresolved uncertainty to the engineer.

Do not train the agent initially with reward equal to “solver succeeded” or “mass minimized.” Those rewards invite evaluator exploitation. Reward a vector: contract completeness, verified feasibility, independent-verifier agreement, diversity, compute cost, correct abstention, and calibrated risk. Current strict engineering benchmarks show that feedback loops improve results but remain far from reliable autonomy, supporting an engineer-sign-off and constrained-tool approach.[^2][^45]

## Evaluation protocol

Evaluate the system at the artifact and decision levels, over repeated runs. Recommended top-level metrics are:

| Dimension | Metric |
|---|---|
| Intent | Blocking omission recall; unnecessary-question rate; unit/frame error rate |
| Geometry | Valid B-Rep rate; editable-parameter rate; semantic-interface recovery rate |
| Manufacturing | Rule-pass rate; expert DFM pass rate; generated artifact completeness |
| Physics | Solver completion; independent-verifier agreement; mesh-converged result rate |
| Safety | False-pass rate; false-impossibility rate; calibrated coverage; abstention quality |
| Optimization | Verified Pareto hypervolume per compute-hour; time/cost per verified design |
| Diversity | Process/concept coverage; behavioral novelty; duplicate rate |
| Agent reliability | Pass@k, pass-all-k, median repair count, failure-stage distribution |
| Realism | Test/simulation discrepancy with uncertainty; supplier cost-quote error |
| Learning | Improvement over frozen baseline at equal cumulative compute |

Use mutation tests to ensure checkers detect injected faults: wrong units, inverted normals, missing density, underconstrained rigid modes, duplicated loads, lost mesh groups, incorrect PSD duration, wrong material curve, insufficient frequency truncation, and unconverged hotspot stress. This is the engineering equivalent of adversarial security testing.

Creativity should be measured only among feasible designs. A candidate is useful-novel if it occupies a new concept/load-path/process cell and improves the verified Pareto archive or opens a requirement region that previous designs could not satisfy. Visual dissimilarity alone should carry little weight.

## Physical validation

Start with tap/impact modal tests on 6–12 simple brackets, then random-vibration or sine-sweep tests on a smaller subset. Use a rigid dummy payload with measured mass, center of gravity, and inertia. Record bolt torque, surface condition, accelerometer mass/loading, fixture modes, temperature, and assembly repetitions.

Repeat assembly/disassembly to estimate joint variability. Published stochastic joint work used repeated reassembly plus Latin hypercube variation of connector stiffness, illustrating how assembly scatter can be turned into a calibration distribution rather than hidden as analyst error. Update joint stiffness/damping from measured frequencies and FRFs, but retain a separate validation set so calibration is not mistaken for prediction.[^21]

Follow a hierarchical V&V plan: coupons/materials, isolated joints, simple bracket, then coupled bracket-payload system. ASME guidance states that verification should precede validation and that validation is specific to model and intended use. The physical test report should include measurement uncertainty and compare prediction intervals, not only nominal frequencies.[^28]

## Fast implementation plan

### Weeks 1–2: contract and baseline

- Define EIR v0.1, units, frames, requirement states, evidence schema, and failure taxonomy.
- Implement one controlled-language request and explicit question generation.
- Create one baseline L-bracket family in build123d/CadQuery with named interfaces.
- Build Gmsh-to-CalculiX static/modal pipeline and core automated checks.
- Reproduce analytic cantilever/plate benchmarks and perform mesh-convergence tests.

### Weeks 3–4: two process families

- Add sheet-metal grammar with flat pattern and bend/feature checks.
- Add machined-plate grammar with stock, pocket, tool-access, and setup metadata.
- Implement deterministic mass and early cost models with volume amortization.
- Run constrained multi-objective optimization over 10–25 parameters.
- Store all artifacts and lineage in the evidence ledger.

### Weeks 5–6: dynamics and robustness

- Add payload mass/inertia, modal effective mass, mode tracking, harmonic transfer functions, PSD propagation, and Dirlik fatigue screening.
- Add joint-stiffness and damping uncertainty sweeps.
- Implement independent remeshing and verifier process.
- Build fault-injection tests for units, boundary conditions, mesh groups, and modal truncation.

### Weeks 7–8: data engine and physical test

- Add active-learning scheduler and simple scalar ensemble surrogates.
- Compare active learning against fixed Latin-hypercube sampling at equal compute.
- Manufacture several sheet and machined brackets; perform impact modal tests with repeated assembly.
- Update joint priors and report prediction-versus-test intervals.

### Weeks 9–12: demonstrator

- Add steady thermal conduction and contact-conductance uncertainty.
- Add bead-feature optimization or a restricted topography method.
- Evaluate 20–50 held-out requirement programs with repeated agent attempts.
- Produce three verified candidates per feasible request, an impossibility/clarification pathway, and full evidence reports.

The first public milestone should not claim general autonomous bracket design. A defensible claim is: **from a typed or controlled-language request, the system generates and independently verifies multiple editable sheet-metal and machined bracket candidates for a defined linear thermo-structural domain, reports uncertainty and cost-volume trade-offs, and demonstrates modal agreement on physical prototypes**.

## Tool choices

| Need | Primary choice | Alternative | Recommendation |
|---|---|---|---|
| Parametric CAD | build123d | CadQuery, FreeCAD Python | build123d for new grammars; FreeCAD for engineer inspection |
| Exact geometry kernel | OCCT/OCP | FreeCAD Part API | Keep kernel operations behind a tested geometry service |
| Meshing | Gmsh | Netgen, SALOME SMESH | Gmsh default; second mesher for confirmation |
| Open structural solver | CalculiX | Code_Aster | CalculiX MVP; Code_Aster for richer confirmation |
| PDE/topology research | FEniCSx/FEniTop | TopOpt.jl, PETSc TopOpt | Research branch, not critical path for MVP |
| Multiobjective BO | Ax + BoTorch | Optuna, SMAC | qLogNEHVI-style constrained search for compact spaces |
| Evolutionary/QD | pymoo + custom MAP-Elites | Nevergrad | Use for mixed/discrete portfolios and novelty archives |
| MDO integration | OpenMDAO | custom DAG | Add when coupled derivatives become valuable |
| UQ | Dakota, SALib | UQpy, Chaospy | Dakota for mature orchestration; SALib for quick screening |
| Mesh/results | meshio + PyVista | ParaView | Keep numerical extraction headless and deterministic |
| Workflow/data | Prefect/Dagster + Postgres + object store | Celery/Ray | Start simple; store immutable manifests and hashes |
| Surrogates | PyTorch/PyG | JAX, NeuralOperator | Begin with scalar ensembles, then field/operator models |

## Highest-risk assumptions

The largest technical risk is not geometry generation; it is whether the verification pipeline can produce trustworthy dynamics and fatigue verdicts under uncertain joints and damping. Address this before large-scale surrogate training.

The second risk is semantic robustness across CAD edits. If named interfaces and manufacturability intent are lost whenever geometry changes, downstream automation will remain fragile. The process-

---

## References

1. [CADEngBench: It Looks Like CAD, but Does It Work? ...](https://arxiv.org/html/2608.09296v1)

2. [Self-Improving CAD Generation Agents with Finite Element ...](https://arxiv.org/html/2605.17448v2) - These benchmarks reward geometric resemblance, while engineering use requires parts that satisfy phy...

3. [EngiWorld: What Can Frontier Agents Deliver in Professional ...](https://huggingface.co/papers/2609.37686) - Join the discussion on this paper page

4. [MOOSEAGENT: A LLM BASED MULTI-AGENT FRAMEWORK](https://taozhan18.github.io/files/mooseagent.pdf)

5. [ALL–FEM: Agentic Large Language models Fine-tuned for Finite ...](https://arxiv.org/html/2603.21011v2)

6. [What Do CAE Simulation Agents Really Need Beyond a Generic ...](https://arxiv.org/html/2609.03718v1)

7. [INTERNATIONAL ISO STANDARD 16750-3](https://cdn.standards.iteh.ai/samples/77579/c438a2f8976e4088873fb2b6b918a821/ISO-16750-3-2023.pdf)

8. [Importing and Exporting Files - CadQuery Documentation](https://cadquery.readthedocs.io/en/latest/importexport.html)

9. [build123d.readthedocs.io › enAbout — build123d 0.13.1.dev133+g12b4fbe55 documentation](https://build123d.readthedocs.io/en/latest/index.html)

10. [ISSN: 2315-4462](https://www.joace.org/uploadfile/2014/0930/20140930102305328.pdf)

11. [Uludağ University Journal of The Faculty of Engineering, Vol. 27, No. 3, 2022                         RESEARCH](https://dergipark.org.tr/en/download/article-file/2655080)

12. [Engineering features in free-form shape optimization using ...](https://link.springer.com/article/10.1007/s00158-026-04367-x?error=cookies_not_supported&code=5934722c-6295-4503-a170-7ea894d282f2)

13. [A Simple and Efficient Structural Topology Optimization ...](https://www.techscience.com/CMES/v136n2/51579/html) - This work analyzes the implementation of a continuous method of structural topology optimization (ST...

14. [dolfin-adjoint about](https://dolfin-adjoint.github.io/dolfin-adjoint/)

15. [TopOpt.jl - Julia Packages](https://www.juliapackages.com/p/topopt) - A package for binary and continuous, single and multi-material, truss and continuum, 2D and 3D topol...

16. [GitHub - missionlab/fenitop: FEniCSx-based topology optimization supporting parallel computing](https://github.com/missionlab/fenitop) - FEniCSx-based topology optimization supporting parallel computing - missionlab/fenitop

17. [Research on Multiaxial Random Vibration Fatigue ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13075063/) - At present, most of the research methods for vibration fatigue of welded structures mainly focus on ...

18. [[PDF] Frequency analysis of random fatigue - ARPI - UNIPI](https://arpi.unipi.it/bitstream/11568/1162030.9/2/Applied%20Research%20-%202022%20-%20Sgamma%20-%20Frequency%20analysis%20of%20random%20fatigue%20%20setup%20for%20an%20experimental%20study.pdf)

19. [[PDF] Random Vibration Fatigue Life Analysis of Aeroengine Bolts Using ...](https://yadda.icm.edu.pl/baztech/element/bwmeta1.element.baztech-106dbf3c-4746-4a68-a1e4-915e6ab7dd57/c/Tian_Random_FAS_2024.pdf)

20. [[PDF] Application of computer simulation technology in modal analysis of ...](https://pdfs.semanticscholar.org/25f3/cc343d07647fffa9de2913780013b6377afd.pdf)

21. [Stochastic Model Updating of Bolt-Jointed Structure for ...](https://journal.ump.edu.my/index.php/ijame/article/download/5692/1399/23520)

22. [6th European Conference on Computational Mechanics (ECCM 6)](https://congress.cimne.com/eccm_ecfd2018/admin/files/fileabstract/a1520.pdf)

23. [Modal testing and modelling the dynamic characteristics of ...](https://journal.ump.edu.my/jmes/article/download/6081/1667/27068)

24. [Gmsh - Open CASCADE Technology](https://dev.opencascade.org/project/gmsh) - Gmsh is a 3D finite element mesh generator with built-in pre- and post-processing facilities. Its de...

25. [Meshing with SMESH - SALOME PLATFORM](https://www.salome-platform.org/?page_id=374) - SMESH — Salome MESH — is the mesh module of SALOME that provides a wide range of meshing algorithms ...

26. [*STEADY STATE DYNAMICS](https://web.mit.edu/calculix_v2.7/CalculiX/ccx_2.7/doc/ccx/node244.html) - *STEADY STATE DYNAMICS

27. [Standard for Verification and Validation in Computational ...](https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics) - Understand verification and validation , V V 10 in engineering and software: learn differences, prac...

28. [An overview of the PTC 60/V&V 10: guide for verification and validation in computational solid mechanics - Engineering with Computers](https://link.springer.com/article/10.1007/s00366-007-0072-z) - Engineering with Computers -

29. [NASA Technical Memorandum 0000](https://ntrs.nasa.gov/api/citations/20140002412/downloads/20140002412.pdf)

30. [OpenMDAO repository.](https://github.com/OpenMDAO/OpenMDAO) - OpenMDAO repository. . Contribute to OpenMDAO/OpenMDAO development by creating an account on GitHub.

31. [About Dakota](https://snl-dakota.github.io/docs/6.18.0/users/usingdakota/introduction/aboutdakota.html) - The Dakota project delivers both state-of-the-art research and robust, usable software for optimizat...

32. [OpenMDAO: An open-source framework for multidisciplinary ...](https://openmdao.org/pubs/openmdao_overview_2019.pdf)

33. [BoTorch · Bayesian Optimization in PyTorch](https://botorch.org/tutorials/constrained_multi_objective_bo) - Bayesian Optimization in PyTorch

34. [Multi-Objective Bayesian Optimization - BoTorch](https://botorch.org/docs/multi_objective) - BoTorch provides first-class support for Multi-Objective (MO) Bayesian

35. [NeuralUQ: A comprehensive library for uncertainty quantification in neural differential equations and operators](https://ar5iv.labs.arxiv.org/html/2208.11866) - Uncertainty quantification (UQ) in machine learning is currently drawing increasing research interes...

36. [Conformal Uncertainty Quantification Guarantees for Neural Operators](https://arxiv.org/pdf/2608.28515.pdf)

37. [A Conformal Prediction Framework for Uncertainty Quantification in Physics-Informed Neural Networks](https://ar5iv.labs.arxiv.org/html/2509.13717) - Physics-Informed Neural Networks (PINNs) have emerged as a powerful framework for solving PDEs, yet ...

38. [ICML Poster Using Uncertainty Quantification to Characterize and ...](https://icml.cc/virtual/2024/poster/33787)

39. [Development of a Life Cycle Engineering Model for Technology Selection                                                             Djordjevic, N.](https://fenix.tecnico.ulisboa.pt/downloadFile/1689244997262837/ExtendedAbstract_81993_NatalijaDjordjevic.pdf)

40. [Computer-aided design for manufacturing process selection](https://link.springer.com/article/10.1007/BF00123964)

41. [Metal additive manufacturing](https://pure.tue.nl/ws/portalfiles/portal/120332611/manu_139_08_081010.pdf)

42. [SimJEB: Simulated Jet Engine Bracket Dataset - arXiv](https://arxiv.org/html/2105.03534v2)

43. [DeepJEB: 3D Deep Learning-based Synthetic Jet Engine ...](https://arxiv.org/html/2406.09047v2)

44. [DeepJEB++: Foundation Model-Driven Large-Scale 3D Engineering ...](https://arxiv.org/html/2606.12994v2)

45. [Benchmarking the Engineering Design Capabilities of LLMs - arXiv](https://arxiv.org/html/2509.16204v2)

