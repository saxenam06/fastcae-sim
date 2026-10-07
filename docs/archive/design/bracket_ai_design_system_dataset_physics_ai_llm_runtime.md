# Autonomous Mechanical Design System — Dataset Generation, Physics AI, LLM Training, and Runtime

## 1. The system I would actually build

I would solve the bracket problem as a **closed-loop engineering system with three distinct intelligence layers**:

1. **A design generator/search engine** that creates manufacturable bracket variants.
2. **Physics AI** that learns the structural/NVH/thermal response of those variants and becomes the fast evaluator.
3. **An engineering LLM agent** that turns intent into a campaign, selects tools, interprets failures, decides what to try next, and records the engineering reasoning.

The most important architectural decision is:

> **Do not train the LLM to learn physics, and do not ask Physics AI to run the engineering workflow.**  
> Physics AI learns `geometry + loads + BCs → physics response`.  
> The LLM learns `engineering state → next action / diagnosis / decision`.

This separation directly addresses the problem statement's requirements around verified designs, evidence, learning from failures, model validity, and preventing drift. See the uploaded problem statement, particularly the questions around incomplete intent, trustworthy evaluation, simplified-model validity, manufacturable design generation, design representation, and learning without drifting away from physical truth.

---

# 2. Overall architecture

```text
                         OFFLINE LEARNING
                         ===============

      Seed Bracket CAD + Design Rules + Manufacturing Rules
                            │
                            ▼
                   Design Generator
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
       100k cheap designs            Design mutations
             │                             │
             └──────────────┬──────────────┘
                            ▼
                    Geometry Validator
                            │
                    feasible designs
                            ▼
                 Low-Fidelity CAE
                            │
                            ▼
                   High-Fidelity CAE
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
         Static           Modal         NVH/Thermal
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                  VERIFIED DATA LAKE
                            │
                  ┌─────────┴─────────┐
                  ▼                   ▼
             Physics AI         Agent Episodes
                  │                   │
                  ▼                   ▼
          Physics surrogate       LLM SFT/
          + uncertainty           preference tuning
                  │                   │
                  └─────────┬─────────┘
                            ▼

                         RUNTIME
                         =======

 Engineer intent + surrounding CAD
                │
                ▼
        Engineering LLM
                │
       Complete specification
                │
                ▼
        Campaign Planner
                │
                ▼
       Design Generator
                │
                ▼
       Geometry Validator
                │
                ▼
        Physics AI ──────────► thousands of candidates
                │
                ▼
       Search / Optimizer
                │
          top candidates
                ▼
          Full CAE
                │
        ┌───────┴────────┐
        │                │
      PASS              FAIL
        │                │
        ▼                ▼
 Evidence package    Diagnosis Agent
                         │
                         ▼
                    Design mutation
                         │
                         └────────► loop
```

This is fundamentally different from **"LLM generates CAD."**

The actual intelligence is in the **interaction between design representation, physics surrogate, verified CAE, search, and engineering-agent reasoning**.

---

# 3. First solve the data problem

The problem statement identifies a foundational problem: useful design-learning data largely does not exist; industrial data is fragmented; and failed designs and the reasoning behind changes are rarely retained in a consistent, learnable form.

Therefore, the first product is almost secretly a **design-data generation machine**.

The dataset should not simply be:

```text
CAD → Stress = 132 MPa
```

That is far too weak.

Instead capture:

```text
Design
  ↓
How was the design created?
  ↓
What constraints does it satisfy?
  ↓
How was it meshed?
  ↓
How was it solved?
  ↓
Was the solution trustworthy?
  ↓
What happened physically?
  ↓
Why did it fail/pass?
  ↓
What design change caused the next result?
```

That entire lineage becomes part of the proprietary dataset.

---

# 4. Step 1 — Define a machine-readable Design DNA

Before generating thousands of designs, define a representation for a bracket.

This is one of the central research questions in the problem: **how should design be represented so that machine learning can learn from it?**

Use three representations simultaneously.

## 4.1 Representation A — Engineering parameter genome

Example:

```json
{
  "envelope": {
    "x_max": 180,
    "y_max": 120,
    "z_max": 80
  },

  "mounting": {
    "hole_count": 4,
    "hole_diameter": 10,
    "mount_plane": "A"
  },

  "wall": {
    "thickness": 3.0
  },

  "ribs": [
    {
      "type": "gusset",
      "start_anchor": "A12",
      "end_anchor": "B7",
      "height": 35,
      "thickness": 3,
      "angle": 42
    }
  ],

  "fillets": {
    "radius": 5
  },

  "material": "AlSi10Mg",

  "manufacturing": {
    "process": "die_cast",
    "draft": 1.5,
    "min_wall": 2.5,
    "min_rib": 2.0
  }
}
```

This is the **design genome**.

It makes mutations understandable:

```text
increase rib height
move rib endpoint
add gusset
remove rib
increase wall thickness
increase fillet
change section
close open section
etc.
```

---

# 5. Representation B — Actual CAD geometry

The genome generates actual CAD geometry:

```text
genome
   ↓
CAD kernel
   ↓
STEP/BREP
```

The CAD is the source of truth for manufacturability and downstream CAE.

Do not train Physics AI only on the genome. Otherwise the model risks learning your parameterization rather than the actual mechanics.

---

# 6. Representation C — FE mesh graph

The Physics AI should see the actual discretized mechanics.

For example:

```text
Node:
    x,y,z
    material
    BC type
    load
    temperature
    surface type
    interface proximity
    etc.

Edge:
    distance
    element adjacency
    boundary relationship
    material relationship
```

Or, for element-centered approaches:

```text
Element:
    centroid
    volume
    material
    element type
    stress
    strain
    adjacency
```

A mesh/GNN representation is attractive because brackets naturally produce irregular meshes and changing topology.

---

# 7. Step 2 — Do not randomly perturb CAD

A naive dataset generator does:

```text
random hole position
random rib height
random thickness
random fillet
...
```

and produces 100,000 CAD models.

That gives you data volume but potentially poor engineering knowledge.

Instead build a **design grammar**.

## 7.1 Structural operators

```text
add rib
remove rib
move rib
split rib
merge ribs
increase rib height
change rib angle
change rib curvature
add gusset
create closed section
change load path
```

## 7.2 Thickness operators

```text
increase wall
 decrease wall
 increase rib
 decrease rib
 local reinforcement
```

## 7.3 Geometry operators

```text
move hole
change hole diameter
change flange
change bend
add relief
change fillet
```

## 7.4 Manufacturing operators

```text
enforce draft
minimum wall
minimum rib
machining access
tool clearance
pull direction
```

Every operator should have:

```text
operator
preconditions
parameters
constraints
result
```

So a design has a lineage:

```text
D0001
  │
  ├── add_rib(A12,B7)
  │       ↓
  │     D0002
  │
  ├── increase_rib_height(10mm)
  │       ↓
  │     D0003
  │
  └── reduce_wall(0.4mm)
          ↓
        D0004
```

This becomes extremely valuable later because the system learns not just designs, but **design changes**.

---

# 8. Step 3 — Generate the first design population

Use several sampling strategies rather than one.

## 8.1 Population A — DOE / space-filling designs

Use Sobol, Latin Hypercube Sampling, or similar approaches across continuous parameters.

Example ranges:

```text
wall thickness       2–5 mm
rib thickness        1.5–4 mm
rib height            10–50 mm
fillet radius          2–10 mm
rib angle             20–70°
hole diameter          6–14 mm
```

The objective is systematic coverage of the design space.

## 8.2 Population B — Engineering mutations

Start from the baseline and perform meaningful changes:

```text
baseline
   ↓
+ rib
- rib
move rib
thicken wall
thin wall
larger fillet
closed section
etc.
```

## 8.3 Population C — Combinations

Combine operators:

```text
+rib
+fillet
-wall
+gusset
```

and other meaningful combinations.

## 8.4 Population D — Boundary cases

Deliberately generate designs near important boundaries:

```text
minimum manufacturing limit
maximum allowable dimension
near buckling
near resonance
near stress limit
near thermal limit
```

These are valuable because they teach the surrogate about constraint boundaries.

## 8.5 Population E — Negative designs

Deliberately create designs that should fail:

```text
too thin
wrong draft
resonance too close
stress too high
deflection too high
bad mounting configuration
poor thermal path
etc.
```

The objective is not to build a dataset containing only successful designs.

The objective is to **teach the system the shape of both the feasible and infeasible design space**.

The problem statement explicitly treats failures as information.

---

# 9. Step 4 — Geometry validation before CAE

Do not send every generated design to FEA.

Pipeline:

```text
CAD generation
      ↓
B-rep validity
      ↓
interference
      ↓
minimum wall
      ↓
minimum radius
      ↓
manufacturing rules
      ↓
interface constraints
      ↓
packaging
      ↓
meshability
```

A design failing here gets a structured record such as:

```json
{
  "status": "GEOMETRY_INVALID",
  "reason": "rib thickness < manufacturing minimum",
  "failed_constraint": "MFG_MIN_RIB"
}
```

This is training data too.

---

# 10. Step 5 — Automatically generate CAE

Every valid geometry goes through the same standardized CAE pipeline.

```text
CAD
 ↓
material assignment
 ↓
mesh
 ↓
named interfaces
 ↓
BCs
 ↓
load cases
 ↓
solver
 ↓
post-processing
```

Lock down solver reproducibility with a complete provenance record:

```text
solver_version
material_version
mesh_settings
element_type
mesh_quality
BC definition
load definition
units
contact assumptions
convergence tolerance
```

The reason is crucial: a solver can complete successfully while the physical analysis is still wrong. The problem statement calls out unit mistakes, missing/wrong BCs, unconverged meshes, and models used outside their valid ranges.

---

# 11. The dataset should contain four layers of physics

Do not save only the final stress.

## 11.1 Global scalar results

```text
mass
volume
CG
max stress
max displacement
strain energy
reaction forces
factor of safety
```

## 11.2 Modal / NVH results

```text
f1
f2
f3
...
mode shapes
modal participation
effective mass
frequency separation
FRF
PSD response
RMS acceleration
```

## 11.3 Thermal results

```text
Tmax
Tmin
thermal gradient
heat flux
thermal resistance
temperature at interface
```

## 11.4 Full spatial fields

```text
u(x)
σ(x)
ε(x)
T(x)
mode_shape(x)
...
```

This enables the Physics AI eventually to answer not just:

> "Does the design fail?"

but:

> "Where is the problem and what physical pattern explains it?"

---

# 12. The most important dataset: the verification dataset

A core question is:

> How do we know that the physics evaluation itself is trustworthy enough to automate on and learn from?

Create a separate truth/verification layer.

```text
CAE execution
     ↓
Result validator
```

Checks include:

```text
units
BC completeness
load balance
reaction balance
mesh quality
mesh convergence
solver convergence
energy consistency
rigid-body modes
modal consistency
physical sanity
```

Then label each result:

```text
VALID
INVALID
QUESTIONABLE
```

Example:

```json
{
  "physics_result": {
    "max_stress": 142.2,
    "f1": 528
  },

  "verification": {
    "solver_converged": true,
    "mesh_converged": false,
    "reaction_balance": true,
    "energy_balance": true,
    "bc_complete": true
  },

  "trust": "QUESTIONABLE",
  "reason": "mesh sensitivity > allowed tolerance"
}
```

**Never allow an unverified CAE result to become Physics-AI ground truth.**

Otherwise the AI simply learns simulation mistakes at industrial scale.

---

# 13. Multi-fidelity dataset

Do not run the most expensive CAE on every design.

A representative funnel is:

```text
                 DESIGN SPACE

             100,000 designs
                    │
                    ▼
             cheap geometry
                    │
                50,000
                    │
                    ▼
             low-fidelity FEA
                    │
                 10,000
                    │
                    ▼
             medium-fidelity
                    │
                  2,000
                    │
                    ▼
             high-fidelity
                    │
                   500
                    │
                    ▼
                GOLD SET
```

The exact numbers are not sacred; the architecture is.

This is a **multi-fidelity learning problem**. Cheap models provide broad coverage, while expensive simulations provide accurate anchors and gold-standard labels.

---

# 14. Active learning is what makes the approach feasible

Do **not** generate 20,000 expensive simulations up front.

Instead:

```text
Generate initial dataset
        ↓
Train Physics AI v0
        ↓
Use Physics AI to explore
        ↓
Find interesting designs
        ↓
Run real CAE only there
        ↓
Add results
        ↓
Retrain
        ↓
Repeat
```

Select new high-fidelity CAE points because they are:

```text
high uncertainty
OR
near constraint boundary
OR
physically novel
OR
geometrically novel
OR
promising optimum
OR
surrogate disagreement
```

Example:

```text
Design A:
stress = 118 MPa ± 2

Design B:
stress = 141 MPa ± 3

Design C:
stress = 149 MPa ± 27
```

Design C gets high-fidelity CAE because it is precisely where the AI does not know.

This is much more valuable than blindly generating another 1,000 easy designs.

---

# 15. What the Physics AI should actually learn

Build **multiple Physics AI capabilities/heads**, not one monolithic model.

## 15.1 Model 1 — Fast scalar surrogate

Input:

```text
design genome
geometry descriptors
material
loads
BCs
```

Output:

```text
mass
stress
displacement
f1...fN
thermal metrics
fatigue metrics
```

This is the fast screening model.

---

# 16. Model 2 — Mesh-based Physics AI

Input:

```text
FE mesh graph
+
material
+
BCs
+
loads
+
geometry features
```

Output:

```text
nodal displacement
stress
strain
temperature
mode shape
```

A representative architecture is:

```text
FE mesh
   ↓
Graph encoder
   ↓
Message passing
   ↓
Physics-aware processor
   ↓
field decoder
```

A mesh/GNN family such as MeshGraphNet/MPNN is attractive because of irregular meshes and changing topology.

---

# 17. Physics-informed training

Do not train using only:

```text
loss = MSE(predicted, FEA)
```

Use data loss plus physics consistency.

A conceptual objective is:

\[
L =
L_{data}
+ \lambda_1 L_{equilibrium}
+ \lambda_2 L_{BC}
+ \lambda_3 L_{energy}
+ \lambda_4 L_{modal}
+ \lambda_5 L_{thermal}
\]

For static structural mechanics:

\[
Ku=f
\]

so if the model predicts displacement \(u\):

\[
L_{equilibrium}
=
\|Ku_{AI}-f\|
\]

For modal prediction:

\[
K\phi_i = \lambda_i M\phi_i
\]

so the model can be penalized for violating the eigenproblem.

For thermal:

\[
K_TT=q
\]

The Physics AI therefore learns both:

```text
data
+
mechanics
```

rather than merely correlations in simulation outputs.

---

# 18. Train the Physics AI in stages

Do not start with the hardest physics.

## Stage 1 — Static linear elasticity

```text
geometry → displacement/stress
```

## Stage 2 — Modal

```text
geometry + mass + stiffness
        ↓
natural frequencies + mode shapes
```

## Stage 3 — Harmonic / FRF

```text
geometry + excitation
        ↓
FRF / frequency response
```

## Stage 4 — Random vibration

```text
PSD / excitation
       ↓
response / fatigue proxies
```

## Stage 5 — Thermal

```text
geometry + material + BCs + heat load
       ↓
thermal field
```

## Stage 6 — Coupled thermal / structural / NVH

Only after the simpler regimes are reliable.

A curriculum like this also gives you clear model-domain boundaries and easier validation at each stage.

---

# 19. Train on design deltas, not only absolute predictions

This is particularly powerful for design automation.

Suppose:

```text
Parent:
stress = 142 MPa
f1 = 430 Hz
mass = 1.20 kg

Child:
stress = 126 MPa
f1 = 472 Hz
mass = 1.23 kg
```

Calculate:

```text
Δstress = -16 MPa
Δf1 = +42 Hz
Δmass = +0.03 kg
```

Now the AI learns:

> **What did this design change actually do?**

That turns the dataset from a collection of unrelated models into a **design-change dataset**.

This is closer to how engineers actually think.

---

# 20. Build design pairs deliberately

Create the following pair structures.

## Parent → child

```text
D1 → D2
```

## Failed → repaired

```text
FAIL
  ↓
increase gusset
  ↓
PASS
```

## Trade-off pairs

```text
lighter but weaker
vs
heavier but stiffer
```

## Same geometry / different load case

```text
same design
different excitation
```

## Same concept / different manufacturing constraints

```text
same structural concept
different process constraints
```

These pairwise relationships become valuable training data for both Physics AI and the engineering agent.

---

# 21. The LLM dataset is fundamentally different

Do not make the LLM dataset:

```text
CAD → stress → teach LLM
```

The LLM is not the numerical surrogate.

Instead its training examples look like:

```text
Engineering state
        ↓
What should an engineering agent do?
```

Example input:

```text
USER:
Design a bracket for a 3 kg electronics module.
First natural frequency > 500 Hz.
Mass < 1.4 kg.
Die-cast aluminum.
Available envelope ...
```

Desired structured output:

```json
{
  "action": "create_campaign",
  "constraints": {
    "mass_max": 1.4,
    "f1_min": 500
  },
  "physics": [
    "static",
    "modal",
    "random_vibration"
  ],
  "manufacturing": {
    "process": "die_cast_aluminum"
  },
  "missing_information": [
    "shock_load"
  ]
}
```

That becomes one LLM training sample.

---

# 22. Where the LLM training examples come from

This is one of the most important ideas in the system.

The **simulation campaign itself generates the LLM training data**.

Suppose an autonomous campaign executed:

```text
Plan
 ↓
Generate 500 designs
 ↓
Filter 312
 ↓
Run surrogate
 ↓
Select 40
 ↓
Run FEA
 ↓
28 pass
12 fail
 ↓
Diagnose
 ↓
Modify ribs
 ↓
Run 20 more
 ↓
...
```

Every state/action/result becomes an agent trajectory:

```text
state_t
+
available_tools
+
engineering_context
        ↓
expert_action
        ↓
tool_result
        ↓
state_t+1
```

That is your **agent dataset**.

---

# 23. What the LLM should learn

Train it on five main capabilities.

## 23.1 Specification extraction

```text
natural language
        ↓
structured requirements
```

The model should detect missing information rather than silently invent values.

---

## 23.2 Campaign planning

Given:

```text
geometry
constraints
manufacturing
loads
physics
```

the LLM produces:

```text
analysis plan
design variables
constraints
evaluation order
termination criteria
```

For example:

```text
1. Extract interfaces
2. Establish keep-out
3. Identify structural load paths
4. Generate 500 feasible variants
5. Screen static performance
6. Screen modal behavior
7. Run high-fidelity NVH on top 30
8. Independently verify top 5
```

---

# 24. LLM Capability 3 — Tool selection

The agent learns which operation should be executed for a given engineering state:

```text
Need geometry
     ↓
generate_geometry()

Need cheap prediction
     ↓
predict_physics()

Need trustworthy answer
     ↓
run_high_fidelity_fea()

Need failure explanation
     ↓
diagnose_failure()
```

The LLM chooses the next engineering action; the application executes it.

---

# 25. LLM Capability 4 — Engineering diagnosis

Example:

```text
Design fails:
    f1 = 417 Hz
    requirement = 500 Hz

Stress = OK
Mass = OK

Mode shape:
    large deformation around mounting flange
```

Desired diagnosis:

```text
Failure:
insufficient local stiffness near mounting flange

Likely design action:
increase load-path stiffness rather than globally increasing wall thickness

Candidate actions:
1. add gusset
2. shorten unsupported flange
3. connect rib to mounting region
```

Notice:

The LLM does **not** calculate the exact geometric dimensions. It identifies the engineering strategy.

The optimizer determines numeric values.

---

# 26. LLM Capability 5 — Knowing when NOT to trust Physics AI

Suppose Physics AI predicts:

```text
stress = 110 MPa
uncertainty = low
```

but the design is outside the surrogate's validated domain.

The correct action is:

```text
DO NOT ACCEPT

Run high-fidelity CAE.
```

Physics AI therefore becomes:

> **a fast screening model, not the ultimate authority.**

This is central to solving the speed-versus-accuracy problem.

---

# 27. Do not put engineering standards into LLM weights

Rules such as:

```text
manufacturing rules
company standards
material specifications
design guidelines
process capability
CAE modelling rules
```

should generally be accessed through a current knowledge/retrieval layer rather than being treated as immutable model weights.

Fine-tuning teaches:

> **how the agent behaves.**

Retrieval supplies:

> **what the current rule is.**

For example:

```text
LLM
 ↓
"What is the minimum die-cast rib thickness for this process?"
 ↓
Manufacturing knowledge service
 ↓
current approved rule
```

This avoids retraining every time an engineering rule changes.

---

# 28. How I would fine-tune the LLM

Use staged training.

## Stage A — Supervised fine-tuning (SFT)

Train examples of:

```text
intent → specification JSON
state → correct tool
simulation result → diagnosis
failure → recovery strategy
candidate set → next search action
```

The goal is reliable structured engineering behavior.

---

# 29. Stage B — Preference tuning

Now create pairs:

```text
good action
bad action
```

Example:

```text
FAIL:
first frequency 390 Hz

BAD:
increase entire wall thickness by 30%

GOOD:
identify modal deformation region and modify local load path
```

Expert rankings teach the model the difference between:

```text
plausible engineering response
```

and:

```text
good engineering response
```

---

# 30. Stage C — Agent trajectory training

Train sequences of:

```text
observe
→ decide
→ tool call
→ observe result
→ recover
→ continue
→ stop
```

Example:

```text
STATE 1
↓
generate_designs

STATE 2
↓
geometry_validator

STATE 3
↓
Physics AI

STATE 4
↓
uncertainty high
↓
run FEA

STATE 5
↓
failure

STATE 6
↓
diagnose

STATE 7
↓
mutate design
```

This is much more useful than engineering question-answer data alone.

---

# 31. Optional Stage D — Reinforcement learning

Use reinforcement learning only once you have a trustworthy evaluator.

A conceptual reward is:

\[
R =
w_1(\text{constraint satisfaction})
+w_2(\text{mass improvement})
+w_3(\text{novelty})
+w_4(\text{CAE validity})
-w_5(\text{CAE cost})
-w_6(\text{invalid designs})
\]

But one rule is critical:

> **Reward the agent using verified physics, not Physics-AI predictions alone.**

Otherwise the agent can learn to exploit weaknesses in the surrogate.

---

# 32. Runtime — Step 1: Understand engineering intent

Suppose an engineer says:

> Design a lightweight mounting bracket for this module. It must survive the specified vibration environment, remain above the resonance limit, fit this envelope, and be manufacturable.

Runtime starts with:

```text
ENGINEER
    │
    ▼
surrounding CAD
+ natural language
    │
    ▼
ENGINEERING LLM
    │
    ▼
STRUCTURED SPECIFICATION
```

Example:

```json
{
  "payload_mass": 3.0,
  "envelope": "...",
  "f1_min": 500,
  "mass_max": 1.4,
  "manufacturing": "die_cast",
  "physics": [
    "static",
    "modal",
    "random_vibration"
  ]
}
```

---

# 33. Runtime — Step 2: Specification verification

The LLM and validation layer ask:

```text
What is known?
What is missing?
What assumptions are forbidden?
```

For example:

```text
SHOCK LOAD = missing
```

The campaign records:

```text
campaign cannot claim shock qualification
```

The system must not silently invent unknown loads or boundary conditions.

---

# 34. Runtime — Step 3: Campaign creation

The LLM creates a structured campaign:

```text
Design variables:
    rib locations
    rib heights
    wall thickness
    gusset geometry
    fillets

Hard constraints:
    interfaces
    envelope
    manufacturing

Objectives:
    minimize mass
    maximize f1
    minimize stress

Physics:
    static
    modal
    random vibration
```

But the LLM does not directly optimize numerical values.

It calls the design/search engine.

---

# 35. Runtime — Step 4: Generate the initial candidate set

For example:

```text
D001
D002
...
D1000
```

Each remains linked to:

```text
baseline
operator sequence
parameters
design lineage
```

Then geometry validation removes invalid designs.

Example:

```text
1000 generated
↓
733 manufacturable
```

---

# 36. Runtime — Step 5: Physics AI evaluates the 733 candidates

Instead of:

```text
733 × full FEA
```

run:

```text
733 × Physics AI
```

Example result table:

| Design | Mass | Stress | f1 | AI uncertainty |
|---|---:|---:|---:|---:|
| D114 | 1.21 kg | 131 MPa | 563 Hz | low |
| D187 | 1.18 kg | 145 MPa | 522 Hz | low |
| D442 | 1.12 kg | 151 MPa | 604 Hz | high |
| D531 | 1.20 kg | 139 MPa | 579 Hz | low |

---

# 37. Runtime — Step 6: Uncertainty gate

Use a model-domain / uncertainty gate:

```text
AI prediction
      ↓
Is this inside validated model domain?
      │
 ┌────┴─────┐
YES         NO
 │           │
 ▼           ▼
accept     full FEA
```

The surrogate should not be trusted outside its validated operating domain.

---

# 38. Runtime — Step 7: Intelligent candidate selection

Do not simply take the top predicted designs.

Select a mixture of:

```text
best predicted
+
uncertain
+
novel
+
constraint-boundary
+
diverse
```

For example:

```text
10 designs likely best
10 uncertain
5 highly novel
5 near constraints
```

Then run high-fidelity CAE.

---

# 39. Runtime — Step 8: High-fidelity CAE

Suppose:

```text
30 designs
```

are evaluated.

Results:

```text
24 PASS
6 FAIL
```

For each design capture not merely PASS/FAIL, but the failure mechanism and evidence.

---

# 40. Runtime — Step 9: Failure diagnosis

Physics AI and analytics provide field information:

```text
stress field
mode shape
thermal field
```

The diagnostic layer converts these into an engineering state:

```json
{
  "failure": "modal",
  "f1": 438,
  "required": 500,
  "dominant_mode_region": "rear_mount_flange",
  "static_stress": "PASS",
  "mass": "PASS",
  "likely_cause": "local compliance"
}
```

The LLM can reason:

```text
Do not globally thicken bracket.
Try local load-path reinforcement.
```

Then it can call:

```text
mutate_design(
    region="rear_mount_flange",
    strategy="gusset",
    target="increase_local_stiffness"
)
```

---

# 41. Runtime — The optimizer takes over numerical design search

The LLM provides engineering direction:

```text
increase local stiffness
```

The optimizer explores:

```text
rib height
rib thickness
rib position
gusset length
gusset angle
fillet radius
```

Then solve a constrained optimization such as:

\[
\min_x m(x)
\]

subject to:

\[
\sigma_{max}(x) \leq \sigma_{allow}
\]

\[
f_1(x) \geq f_{min}
\]

\[
T_{max}(x) \leq T_{allow}
\]

\[
g_{manufacturing}(x) \leq 0
\]

plus novelty/diversity requirements when relevant.

This numerical optimization does not need an LLM.

Use the LLM to decide **what search strategy or design modification to pursue**, not to replace numerical optimization.

---

# 42. Complete runtime loop

```text
                 ┌──────────────────┐
                 │  Engineering     │
                 │      Intent      │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │       LLM        │
                 │ specification +  │
                 │ campaign planner │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Design Generator │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Geometry / MFG   │
                 │    Validator     │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │   Physics AI     │
                 │ fast evaluation  │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Search / Optimizer│
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ High-Fidelity FEA│
                 └────────┬─────────┘
                          ▼
                    ┌─────┴─────┐
                    │           │
                  PASS         FAIL
                    │           │
                    ▼           ▼
                Verify      Diagnose
                    │           │
                    │           ▼
                    │       Mutate design
                    │           │
                    └───────────┘
```

---

# 43. Every runtime iteration becomes new knowledge

Suppose runtime explored:

```text
D100 → D101 → D102 → D103
```

and discovered:

```text
D100 PASS
D101 FAIL: resonance
D102 FAIL: stress
D103 PASS
```

Store:

```text
D100
D101
failure reason
D102
failure reason
D103
parent-child relationships
LLM decision
optimizer decision
surrogate prediction
CAE ground truth
verification status
```

Now the dataset continuously grows.

---

# 44. Do not immediately train on runtime data

This is one of the most important safeguards.

Runtime produces:

```text
AI prediction
```

and:

```text
CAE result
```

Only the following pipeline should make data eligible for learning:

```text
                  ┌───────────────────────┐
                  │     Runtime result    │
                  └───────────┬───────────┘
                              │
                         High-fidelity
                             CAE
                              │
                         independent
                           validation
                              │
                              ▼
                     TRUSTED NEW DATA
```

Then the trusted sample joins the training pool.

This prevents a dangerous self-training loop where Physics AI predictions become their own labels.

---

# 45. The Physics dataset and the LLM dataset evolve differently

## 45.1 Physics dataset

```text
CAD
+
mesh
+
material
+
BC
+
loads
+
verified solver results
```

This trains:

```text
Physics AI
```

## 45.2 LLM dataset

```text
engineering intent
+
structured state
+
available tools
+
tool result
+
engineering decision
+
failure diagnosis
+
successful outcome
```

This trains:

```text
Engineering Agent
```

---

# 46. The LLM should not receive the million-node FE tensor

Do not send huge raw FE fields directly into the LLM.

Instead the physics/analytics layer converts the simulation into a compact engineering state:

```json
{
  "stress_hotspot": {
    "region": "mounting_boss_2",
    "value": 181.2
  },

  "mode": {
    "frequency": 438,
    "dominant_region": "rear_flange"
  },

  "load_path": {
    "weak_connection": "flange_to_mount"
  }
}
```

Then the LLM reasons over that compact representation.

This makes the architecture scalable and keeps the numerical heavy lifting in the Physics AI/CAE layer.

---

# 47. What to train first

Build this in six practical stages.

## Phase 1 — Design data engine

Before any AI:

```text
CAD
 ↓
parametric design representation
 ↓
design generator
 ↓
geometry validation
 ↓
CAE automation
 ↓
database
```

Goal:

> Automatically produce **verified design records**.

---

## Phase 2 — Physics AI v1

Start with:

```text
static + modal
```

Train:

```text
genome → scalar performance
```

and:

```text
FE mesh → stress/displacement/modal fields
```

Use a mesh/GNN architecture as the main geometry-aware model, with physics losses and uncertainty estimation.

---

## Phase 3 — Active-learning engine

Now:

```text
Physics AI
 ↓
search huge design space
 ↓
uncertainty
 ↓
select CAE points
 ↓
retrain
```

This is where the system begins becoming economically interesting.

---

## Phase 4 — LLM agent

Initially do not fine-tune anything.

Use a strong foundation model with tools:

```text
specification parser
campaign planner
CAD tool
geometry validator
Physics AI
CAE
result analyzer
database
```

Collect trajectories.

---

## Phase 5 — Fine-tune the LLM

Once enough high-quality trajectories exist:

```text
successful trajectories
failed trajectories
recovery trajectories
expert corrections
```

Train:

```text
SFT
   ↓
preference tuning
   ↓
optional RL
```

The resulting model becomes a **specialized engineering workflow agent**.

---

## Phase 6 — Autonomous design discovery

The system can now perform:

```text
Intent
 ↓
Campaign
 ↓
Generate
 ↓
Predict
 ↓
Search
 ↓
Verify
 ↓
Diagnose
 ↓
Mutate
 ↓
Discover
```

and evaluate whether a result is genuinely:

```text
better
AND
valid
AND
manufacturable
AND
novel
```

rather than merely different.

---

# 48. How to measure "new and better"

You need an explicit design-space metric.

## Feasibility

```text
manufacturing = PASS
interfaces = PASS
physics = PASS
verification = PASS
```

## Performance

```text
mass
stress
f1
NVH
thermal
etc.
```

## Novelty

Compare candidates against:

```text
baseline
historical designs
generated population
design embeddings
topological descriptors
```

Example evidence package:

```text
Design X:

mass        -14%
stress       -8%
f1          +17%
manufacturing PASS
verification PASS

geometric novelty = 0.82
```

Then **"new and better"** becomes measurable rather than asserted.

---

# 49. The database becomes more valuable than the model

Structure persistent data around something like:

```text
DESIGN
│
├── design_id
├── parent_id
├── family_id
├── geometry_hash
├── design_genome
├── CAD
├── manufacturing_constraints
│
├── ANALYSIS
│   ├── load_cases
│   ├── BCs
│   ├── mesh
│   ├── solver
│   ├── convergence
│   └── verification
│
├── PHYSICS
│   ├── scalar outputs
│   ├── fields
│   ├── modes
│   └── frequency responses
│
├── VERDICT
│   ├── pass/fail
│   ├── failure mode
│   └── confidence
│
├── LINEAGE
│   ├── operator
│   ├── parameters
│   └── parent results
│
└── AGENT TRACE
    ├── intent
    ├── decision
    ├── tool calls
    ├── diagnosis
    └── next action
```

This becomes the foundation for the entire product.

---

# 50. Recommended implementation architecture

```text
                       ┌─────────────────────┐
                       │ Engineering LLM     │
                       │                     │
                       │ Spec Agent          │
                       │ Campaign Agent      │
                       │ Diagnosis Agent     │
                       │ Evidence Agent      │
                       └──────────┬──────────┘
                                  │
                            Tool / MCP API
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
                 ▼                ▼                ▼
           CAD Generator     Physics AI      CAE Executor
                 │                │                │
                 │                │                │
                 └────────────┬───┴────────────────┘
                              ▼
                       Design Database
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
             Geometry      Physics      Agent traces
              dataset       dataset       dataset
                 │            │            │
                 ▼            ▼            ▼
             Generator     Physics AI      LLM
              learning      training      training
```

---

# 51. The deeper product insight

The obvious pitch is:

> **AI generates mechanical designs.**

The stronger product is:

> **An AI system that builds a continuously expanding, verified map of the mechanical design space.**

The bracket is simply the first domain.

The system is learning:

\[
\boxed{
\text{Design}
\rightarrow
\text{Manufacturability}
\rightarrow
\text{Physics}
\rightarrow
\text{Failure}
\rightarrow
\text{Design Change}
}
\]

That is a much richer asset than CAD generation.

---

# 52. The strongest implementation principle

Do **not** start with generative AI for CAD.

Start with:

```text
PARAMETRIC DESIGN GENERATION
+
AUTOMATED VERIFIED CAE
+
PHYSICS SURROGATE
+
ACTIVE LEARNING
```

Then add:

```text
LLM AGENT
```

Once the system has real engineering tools and a trustworthy physical evaluation layer, the LLM has something meaningful to operate.

Otherwise the risk is building:

```text
LLM
 ↓
"Maybe add a rib here"
 ↓
CAD
 ↓
FEA
```

which can be visually impressive but difficult to make genuinely autonomous and trustworthy.

The stronger architecture is:

```text
                 LLM
                  │
          "what should we do?"
                  │
                  ▼
        Engineering Search
                  │
       "what designs should
             we try?"
                  │
                  ▼
           Physics AI
                  │
        "which are promising?"
                  │
                  ▼
               CAE
                  │
        "what is actually true?"
                  │
                  ▼
             Verifier
                  │
        "can we trust it?"
                  │
                  ▼
               LLM
                  │
       "what did we learn?"
                  │
                  ▼
          Design Generator
```

That is the **self-improving engineering loop**.

---

# 53. End-to-end learning loop

```text
                 ┌────────────────────────────┐
                 │                            │
                 │     VERIFIED EXPERIENCE    │
                 │                            │
                 └─────────────┬──────────────┘
                               │
              ┌────────────────┴─────────────────┐
              │                                  │
              ▼                                  ▼
       Physics training                  LLM training
              │                                  │
              ▼                                  ▼
      Better prediction                  Better decisions
              │                                  │
              └────────────────┬─────────────────┘
                               ▼
                        BETTER RUNTIME
                               │
                               ▼
                     MORE DESIGNS EXPLORED
                               │
                               ▼
                         MORE CAE DATA
                               │
                               └──────────► ...
```

The central rule remains:

> **CAE is the independent physical authority. Physics AI is the fast approximation. The LLM is the campaign and engineering-reasoning layer.**

That separation preserves the core "physics first", "engineers stay in charge", "evidence over assertion", and "failures are information" principles of the problem statement.

---

# 54. Compact mental model

The whole system can be remembered as four nested loops:

```text
LOOP 1 — GEOMETRY
Generate → validate → mutate

LOOP 2 — PHYSICS
Predict → verify → learn

LOOP 3 — SEARCH
Explore → select → optimize

LOOP 4 — ENGINEERING REASONING
Intent → plan → diagnose → decide
```

Together:

```text
                ENGINEER
                    │
                    ▼
                 INTENT
                    │
                    ▼
             ENGINEERING LLM
                    │
                    ▼
               CAMPAIGN
                    │
                    ▼
            DESIGN GENERATOR
                    │
                    ▼
          MANUFACTURABILITY GATE
                    │
                    ▼
              PHYSICS AI
                    │
                    ▼
              SEARCH ENGINE
                    │
                    ▼
               FULL CAE
                    │
                    ▼
               VERIFIER
                    │
           ┌────────┴────────┐
           ▼                 ▼
        EVIDENCE           FAILURE
           │                 │
           │                 ▼
           │             DIAGNOSIS
           │                 │
           │                 ▼
           └──────────► DESIGN CHANGE
                             │
                             └──────► ...
```

This is the architecture I would use as the basis for a production-oriented autonomous structural design system for brackets, with the bracket domain serving as the first complete proof point and later extending to other mechanical part families.

---

# 55. Source basis

The uploaded problem statement establishes the target outcomes and constraints for the system: intent in and verified design out; engineers retaining judgment and sign-off; every iteration becoming knowledge; broader design-space exploration; trustworthy physics evaluation; manufacturability; explicit model validity; failures as information; and learning without drifting from independent physical truth.

Source file: `2026-10-05-problem-statement.md`
