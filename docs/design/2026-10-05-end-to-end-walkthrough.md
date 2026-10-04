# End-to-end walkthrough: dataset → training → runtime

*Draft, 2026-10-05. Shows how the system operates, with many examples, because the data factory's job is to produce
thousands of data points, not one.*

*Related documents:*
- *`2026-10-05-problem-statement.md`: the problem;*
- *`2026-10-04-agentic-data-factory-brief.md`: the reasoning so far.*

***All numbers are illustrative.***

```
 PHASE 1: CREATE DATASET (batch, no human)           PHASE 2: TRAIN (offline)
 requests → curator agent → generators → grader ──►  embeddings · fast predictors ·
            (plans batches) (operations)  (physics)   validity maps · fine-tuned LLM
                  ▲                                          │ become new tools
                  │                                          ▼
                  └──── runs fed back ─────  PHASE 3: RUNTIME (user in the UI)
                                             request + CAD → spec → explore → candidates → export
```

**Reading guide.** Phase 1 shows the factory at three scales:
1. one request becomes many designs;
2. one batch produces thousands of designs;
3. the curator agent steers batch after batch.

Phase 2 shows what is trained on those records. Phase 3 shows three different user requests at runtime.

---

## Phase 1: Creating the dataset

### 1.1 Many requests

The request sampler draws realistic requirement sets across the whole space, in the same typed format the UI
produces. Here are six of the 500 requests in batch 1:

| ID | Payload | Mounting | Vibration input | Requirements |
|---|---|---|---|---|
| R-001 | 1.2 kg control module, 15 W | Vertical body rail, 2 × M6 | ISO 16750-3, body | f1 ≥ 200 Hz; base ≤ 85 °C at 65 °C ambient |
| R-002 | 0.3 kg camera module, 3 W | Overhang from a crossmember, 120 mm reach | ISO 16750-3, body | f1 ≥ 150 Hz |
| R-003 | 3.5 kg power-electronics controller, 40 W | Spans two floor rails, 200 mm apart | ISO 16750-3, body | f1 ≥ 250 Hz; base ≤ 90 °C |
| R-004 | 0.8 kg sensor ECU, 5 W | Engine block | ISO 16750-3, engine (much more severe) | f1 ≥ 400 Hz |
| R-005 | 0.6 kg inertial sensor (IMU), 2 W | Wall, 3 × M5 | ISO 16750-3, body | Cut vibration above 100 Hz by ≥ 70 %; sway ≤ 3 mm |
| R-006 | 1.2 kg control module, 15 W | Vertical body rail | ISO 16750-3, body | Base ≤ 70 °C at 65 °C ambient |

Every request also carries the payload's footprint and centre of gravity, the allowed envelope and the keep-out zones.
The mix is deliberate:
- easy and hard;
- light and heavy;
- driven by stiffness (R-001) or by isolation (R-005);
- one that is impossible (R-006).

### 1.2 One request, many designs

Several sources generate designs for every request. In batch 1, an average request gets:

| Source | Designs | Why |
|---|---|---|
| Hand-formula first guess | 1 | The engineer's starting point: required stiffness k = m(2πf)², which sets the section and thickness |
| Systematic variations (templates and feature combinations) | 24 | Cover the space around the first guess, good designs and bad |
| Optimizer runs | 8 | Push towards the best mass-versus-margin trade-off; intermediate steps are kept |
| Agent | 3 | The agent works on about one request in seven, producing about 20 designs each, with full logs |
| **Total** | **≈ 36** | |

Some of the designs for R-001. f1 is the first natural frequency from L1 analysis. Fatigue damage must stay ≤ 0.5.

| Design | Made by | Concept | Sheet | Mass | f1 | Fatigue damage | Base temp. | Rules | Result |
|---|---|---|---|---|---|---|---|---|---|
| D-0001 | First guess | Channel L-bracket | 2.0 mm Al | 68 g | 184 Hz | 0.62 | 81 °C | Hole too close to bend | **FAIL**: f1 −8 %, fatigue, rule |
| D-0002 | Variation | Channel + diagonal bead, holes moved | 2.0 mm Al | 69 g | 212 Hz | 0.31 | 81 °C | ok | **PASS**, +6 % |
| D-0003 | Variation | Channel, thinner | 1.6 mm Al | 56 g | 163 Hz | 1.4 | 82 °C | ok | **FAIL**: f1 −19 %, fatigue |
| D-0004 | Variation | Channel, thicker | 2.5 mm Al | 84 g | 221 Hz | 0.18 | 80 °C | ok | **PASS**, but heavy |
| D-0005 | Optimizer | Channel + 2 beads + 2 lightening holes | 1.8 mm Al | 55 g | 205 Hz | 0.42 | 82 °C | ok | **PASS**, +2.5 % |
| D-0006 | Agent | Closed box, spot-welded seam | 1.2 mm Al | 49 g | 218 Hz | 0.29 | 83 °C | ok | **PASS**, +9 % |
| D-0007 | Agent-invented feature | Channel + bead that follows the mode-1 bending | 1.6 mm Al | 52 g | 214 Hz | 0.33 | 82 °C | ok | **PASS**, +7 %, novel |
| D-0008 | Variation | Bead across a bend line | — | — | — | — | — | Bead crosses bend | **REJECTED** before analysis |

**Failures are kept, and reused.** D-0003 fails R-001, but it is a correct answer to "the same module with f1 ≥ 160 Hz".
So it is also stored as that request–design pair. This is **relabelling**: every graded design yields at least one
valid example.

**The best design, and even the strategy, differs from request to request:**

| Request | Best design | Concept | Mass | Key result |
|---|---|---|---|---|
| R-001 | D-0006 | Closed box, 1.2 mm Al | 49 g | f1 218 Hz (+9 %) |
| R-002 | D-0131 | Tapered hat section, 1.5 mm Al | 31 g | f1 162 Hz (+8 %) |
| R-003 | D-0420 | Hat-section bridge between the rails, 2.0 mm steel | 410 g | f1 268 Hz (+7 %), base 86 °C |
| R-004 | D-0733 | Short box, 2.0 mm steel | 140 g | f1 431 Hz (+8 %) |
| R-005 | D-0912 | Plate on 3 elastomer isolators, isolating at ≈ 45 Hz | 38 g + isolators | 78 % cut above 100 Hz; sway 2.1 mm |
| R-006 | — | No feasible design | — | Thermal limit; see record D below |

R-001 to R-004 are solved by **stiffening**. R-005 is solved by **isolating**, the opposite strategy.

### 1.3 A whole batch

Batch 1, by the numbers:

```
500 requests × ≈ 36 designs     = 18,000 designs
manufacturing check               2,700 rejected (15 %), reason logged, not analysed
L0 hand models                   15,300 designs   milliseconds each
L1 finite elements                6,100 designs   seconds each: L0 near-passes, plus a random 10 % of the rest
                                                  so that failures are represented
L2 full 3D FEM                      450 designs   minutes each: random sample, record-breakers, novel designs
quarantined                          19 runs      failed a physics invariant check
passing (of L1-graded)               37 %
```

**Why the 19 runs were quarantined.**
- **Symptom:** the free-free check found 12 zero-frequency modes instead of 6, so the module was not connected to the
  bracket. The mass check flagged the same runs.
- **Cause:** a variation step had moved the bracket's module holes away from the module's bolts.
- **Response:** the curator agent traced the cause and proposed a fix. The fix goes through tests and your review
  before the 19 designs are re-run.

Without the check, 19 wrong labels would have entered the dataset silently.

### 1.4 The curator steers the next batch

After each batch, the curator agent reads the dataset's state. Passing designs per cell after batch 1:

```
                      f1 target →  150–200   200–300   300–400   400+ Hz
module 0.3–1 kg                      412       388       201       64
module 1–2 kg                        355       297        96       11
module 2–3.5 kg                      190       121        14        0
module 3.5–5 kg                       88        37         0        0
```

Its plan for batch 2:

```
focus     heavy modules (2–5 kg) with f1 ≥ 300 Hz: four cells nearly empty
methods   feature combinations and box sections; about 70 requests designed by the agent,
          all in the focus cells; 10 attempts to invent a new feature
sampling  extra designs near the pass/fail boundary in the 200–300 Hz cells,
          where the pass/fail model is least certain
budget    70 % of L1 time on the focus cells
fix       re-run the 19 quarantined designs once the interface fix is approved
```

After batch 2, the bottom two rows read:

```
module 2–3.5 kg                      190       160        88       19
module 3.5–5 kg                       88        91        42        6
```

The 3.5–5 kg, 400+ Hz cell is still thin. It has 6 passing designs, but most of its requests remain unsolved, with
the best attempts falling up to 9 % short. Existing features cannot reach those requests within the envelope, so the
agent invented one: a **double-wall box with an internal stiffening tab**. It passed the manufacturing rules and the
grader, you approved it, and it joined the library as a new operation. Batch 3 uses it.

**The archive keeps the dataset diverse.** It stores the best design of each kind in every cell. For example, in the
cell "1–2 kg, 200–300 Hz":

```
best channel     55 g   (D-0005)
best box         49 g   (D-0006)
best invented    52 g   (D-0007)
best isolated    —      (isolation cannot meet a frequency floor: empty by design)
```

After batch 2 the concept mix is roughly: channel 52 %, box 21 %, hat 11 %, isolated 9 %, invented 7 %.

### 1.5 What the records look like

**A. A passing design from the optimizer**
```
record   D-0005                          request R-001
made by  optimizer, starting from D-0002
design   base → side_flanges(18) → bend(90°) → upright → bead(diagonal) → bead(diagonal)
         → lightening_holes(2 × Ø14) → holes(2 × M6)          5052-H32, 1.8 mm, 55 g
forms    feature list · CadQuery code · STEP · flat pattern · mesh · point cloud
labels   f1: L0 219 · L1 205 · L2 207 Hz | Grms 10.4 g | damage 0.42 | shock 128 MPa | base 82 °C
checks   all pass · smallest margin +2.5 % (f1)
fields   mode shapes 1–6 · modal strain energy · RMS stress
```

**B. An agent design, with its reasoning log**
```
record   D-0006                          request R-001
made by  agent, starting from D-0001
log      1 characterize: mode 1 is upright bending with twist; 71 % of strain energy at the upright root
         2 decide: twist matters, so a closed section beats beads
         3 add closed_section(seam = spot weld, pitch 25 mm) → rules ok
         4 grade (L1): f1 236 Hz, damage 0.21 → pass
         5 optimize for mass → 1.2 mm, 49 g
labels   f1: L1 218 · L2 216 Hz | damage 0.29 | base 83 °C
checks   all pass · smallest margin +9 % (f1)
```

**C. A rejected design**
```
record   D-0008                          request R-001
made by  variation
status   REJECTED before building: bead crosses a bend line (sheet-metal rule)
labels   none; kept as a negative example for the agent
```

**D. An impossible request**
```
request  R-006: 1.2 kg, 15 W module; base ≤ 70 °C at 65 °C ambient (only a 5 K rise allowed)
result   NO FEASIBLE DESIGN (412 designs tried)
bound    the best heat path the process allows (3 mm sheet, full 50 mm interface, shortest route)
         is ≈ 1 K/W, so it carries ≈ 5 W at a 5 K rise; the module's own surfaces shed ≈ 2 W;
         15 W must go → impossible for any bracket (rail treated as a heat sink at ambient)
nearest  base ≤ 80 °C is feasible (best found: 78 °C) → stored as a relabelled request → design pair
```

### 1.6 Splitting for honest tests

- The test sets hold out **whole kinds of request**, not random designs. For example, every two-rail request (like
  R-003) and every engine-mounted request (like R-004) goes into the test set only.
- Models must then handle these without having seen a single one, which is exactly what happens at runtime.
- A dataset card records the generator mix, pass rates, distributions and limits (simulation only; damping assumed).

---

## Phase 2: Training on the dataset

### 2A. Physics AI models

**Fast predictors** learn from thousands of graded records like these:

| Record | Input | Targets |
|---|---|---|
| D-0001 | Point cloud + 1.2 kg module, CG 35 mm, body profile | f1 184 Hz, damage 0.62, base 81 °C, pass = 0 |
| D-0005 | Point cloud + 1.2 kg module, CG 35 mm, body profile | f1 205 Hz, damage 0.42, base 82 °C, pass = 1 |
| D-0131 | Point cloud + 0.3 kg module, 120 mm reach, body profile | f1 162 Hz, damage 0.21, pass = 1 |
| D-0912 | Point cloud + isolators + 0.6 kg module, body profile | isolation at 45 Hz, 78 % cut above 100 Hz, sway 2.1 mm, pass = 1 |
| … | About 6,000 L1-graded records per batch | |

- **Models.** A baseline of gradient-boosted trees on the feature list, and a main point-cloud or mesh network
  (Transolver- or MeshGraphNet-style) that works on any geometry. An ensemble of models gives the uncertainty.
- **Fields.** They also predict mode shapes and strain energy on the mesh. Between similar designs, modes swap order
  and flip sign, so the training loss must match modes first (MAC-based matching).

**Embeddings and novelty.** The encoder places every design in a vector space. The distance to the nearest existing
design measures novelty:

| Design | Nearest existing design | Distance (novelty) | Novel *and* better? |
|---|---|---|---|
| D-0002, channel + bead | D-0001 | 0.08, low | No: a small variation |
| D-0006, closed box | Other box designs | 0.19, moderate | No: the box is a known family |
| D-0007, mode-following bead | D-0002 | 0.47, high | **Yes**: 52 g at +7 %, versus the best channel at 55 g and +2.5 % |

The same distance flags **unfamiliar** designs at runtime (Phase 3, example B).

**Validity maps.** Comparing L0 with L1 across the 6,100 L1-graded designs of batch 1 gives evidence-based rules:

| Mode-1 effective mass | Bolt spacing ÷ flange width | L0 frequency error (median / 95th percentile) | Rule learned |
|---|---|---|---|
| ≥ 85 % | ≥ 0.6 | 4 % / 9 % | L0 is fine for screening |
| ≥ 85 % | < 0.6 | 12 % / 27 % | L0 over-predicts (joint flexibility): use L1 |
| < 85 % | any | 18 % / 44 % | L1 required |

D-0001 is a typical case from the second row: L0 said 205 Hz (pass), and L1 said 184 Hz (fail).

**Acceptance gate.**
- A predictor may screen designs only if its false-pass rate on the held-out sets is below a 1 % limit.
- Example: predictor v3 has 0.4 % false passes on held-out engine-mounted designs and is accepted. v2 has 3.1 % and is rejected.
- Even an accepted predictor only screens. It never signs a design off.

### 2B. Fine-tuning an LLM (stage 8; needs a paid cloud GPU)

The factory's logs supply three kinds of training example.

**1. Imitating a good session** (from D-0006's log):
```
input    R-001 specification + D-0001's result (f1 −8 %, fatigue fail)
target   characterize → "upright bends and twists" → add closed_section → grade → optimize → pass
```

**2. Learning from a mistake and its recovery** (from an R-002 session):
```
1 add lightening holes near the root to save mass   → grade: fatigue damage 1.8 ✗
2 read the strain-energy field: the holes sit in the highest-strain zone
3 move the holes to the low-strain tip region        → grade: damage 0.40 ✓, 3 g lighter than the start
lesson   lightening holes go where strain energy is low
```

**3. Reinforcement learning on a task never seen in training:**
```
task R-014: 2.2 kg module, f1 ≥ 260 Hz
attempt A   4 rounds → pass, 88 g       reward 0.81
attempt B   9 rounds → fail, f1 −4 %    reward 0.12
attempt C   3 rounds → pass, 79 g       reward 0.90
→ the model is updated towards attempt C's choices (box section early, no creeping thickness increases)
```
- **Reward.** It requires a pass, and favours lower mass and fewer rounds.
- **Guarding against gaming.** Only labels from models used within their validity limits count, and winning designs
  are re-checked with full 3D FEM.

**Evaluation.**
- Held-out tasks compare three set-ups:
  - the Claude-driven agent;
  - the fine-tuned small model;
  - the small model with hard requests escalated to Claude.
- The measures are success rate, rounds to pass and cost per design.
- Realistic expectation: the small model is cheaper and faster on routine requests, and hard ones still go to Claude.

### 2C. Back into the toolbox

- The trained models become new tools: `find_similar_designs`, `predict_performance` (with uncertainty) and
  `propose_design`.
- Validity maps update the rules for when to move to a fuller model.
- The physics tools still have the final word.

---

## Phase 3: Runtime, with a user in the UI

### Example A: a familiar request

*Screen-by-screen version: `2026-10-05-ui-flow.md`.*

*"Mount a 1.2 kg, 15 W control module to a vertical body rail. ISO 16750-3. First mode ≥ 200 Hz, module base ≤ 85 °C.
Sheet metal, lightest possible."* The user also attaches CAD of the rail, the module and the allowed envelope.

1. **Brief check.**
   - Claude shows the specification and its assumptions:
     - damping 2–5 %, swept;
     - module treated as rigid, to be checked;
     - 5052-H32 from the company list.
   - It asks only blocking questions: *"Body-mounted or engine-mounted profile?"* and *"The rail has 3 holes but you
     mentioned 2 × M6. Use all 3?"*
2. **Plan.** *"Three concepts: channel with bead, closed box, hat section. Isolation is ruled out: it cannot meet a
   frequency floor."* The user can approve, edit, or let it run.
3. **Explore.** *"6 similar past designs found (nearest at distance 0.05). 400 variants screened by the fast predictor
   in 3 s; 25 sent to FEM."*
4. **Results.**
   - Ranked candidates on a mass-versus-margin chart: box 49 g (+9 %), invented-bead channel 52 g (+7 %), channel
     55 g (+2.5 %).
   - Each comes with its 3D model, mode-shape animation, margins, validity flags and novelty.
   - The finalists are re-checked with full 3D FEM.
5. **Refine.** *"Lighter, and no spot welds: our line can't weld aluminium."* The agent switches the box seam to
   clinching, re-optimizes and re-verifies.
6. **Deliver.**
   - STEP file, flat pattern, report and decision log.
   - With the user's consent, the run and the engineer's chosen candidate go back into the dataset.

### Example B: an unfamiliar request

*"6.5 kg pump controller bolted to a compressor housing. Engine-type vibration. First mode ≥ 450 Hz. Steel allowed."*

- **Unfamiliar.** The dataset only covers payloads up to 5 kg, and the nearest past design is at distance 0.62
  (familiar requests are below 0.3). The fast predictor is switched off for this request, and every candidate goes
  to FEM.
- **More rounds.** The agent needs 14 rounds instead of about 5:
  - a channel fails;
  - a box falls short;
  - the double-wall box with internal tab, invented in batch 3, passes: 2.5 mm steel, 620 g, f1 468 Hz (+4 %).
- **Slower, but correct.** The session's designs then extend the dataset beyond 5 kg.

### Example C: an impossible request

*"Same 1.2 kg, 15 W module, but base ≤ 70 °C at 65 °C ambient."*

- **It says no, with physics.** The agent doesn't return a bad design. It reports: *"Not achievable with a sheet-metal
  bracket in this space. At a 5 K rise, the best heat path the process allows carries about 5 W, and the module's own
  surfaces shed about 2 W. 15 W must go."*
- **It offers options, with evidence:**
  - accept ≤ 80 °C (best design 78 °C);
  - allow a machined or thicker bracket, which is outside the current process;
  - add a heat path to the chassis, which needs a packaging change.

---

## The loop

- Runtime sessions and factory batches both feed the dataset.
- The dataset improves the models and the rules, which make the runtime faster and the factory smarter.
- The grader anchors all of it.

---

## Appendix A: from attached CAD to boundary conditions (Example A)

Tools recognize the interfaces in the CAD, and Claude confirms anything ambiguous with the user. Because the bracket
is built by our own operations, its contact and load regions are named when they are created. Boundary conditions
are then applied by rule and checked automatically.

### A.1 Read and align (tool)
- Import the three STEP files (rail, module, envelope) with OpenCascade.
- Check units and solid validity, and keep the parts in their exported positions.
- The vibration axes come from the file's coordinate frame, so the files should be in vehicle coordinates. If they
  are not, Claude asks which directions are up and forward.

### A.2 Recognize interface features (tool)
STEP files carry shapes but no meaning, so the meaning is inferred:
- **Rail holes.** Cylindrical through-faces. Ø 6.6 mm is an M6 clearance hole (ISO 273). Holes are grouped into
  patterns, and only holes facing the envelope count.
- **Rail contact land.** The planar face around those holes. Its normal fixes the orientation of the bracket's flange.
- **Module mounting points.** Threaded holes appear as plain cylinders at tap-drill size (Ø 5.0 = M6, Ø 4.2 = M5),
  or as bosses. They are grouped into a pattern.
- **Module base.** The largest planar face of the module facing the bracket. This is the face the heat comes through.
- **Clearances.** The offset and alignment between the rail land and the module's mounting plane.

### A.3 Confirm (Claude and the user)
- Claude compares what the tools found with the text and asks only about conflicts, for example:
  - *"The rail has 3 holes but you mentioned 2 × M6. Use all 3?"*
  - *"Module centre of gravity: the CAD centroid, which assumes uniform density, or the datasheet value?"*
- **Mass comes from the text**, because module CAD is usually a simplified solid without real density. Inertia comes
  from the CAD shape scaled to that mass, and is flagged as an assumption.

### A.4 Build the bracket with named regions (tool)
- The operations place the bracket's holes on the recognized rail and module patterns, so every face is **tagged
  when it is created**:
  - rail contact;
  - rail holes;
  - module contact;
  - module holes;
  - free surfaces.
- CAD kernels renumber faces after each operation (the *topological naming* problem). Tags are therefore re-found by
  geometric signature (position, normal, adjacency) after every operation, and checked to resolve to the expected faces.

### A.5 Map regions to the model

| Region | Becomes |
|---|---|
| **Clamped zone at each rail bolt.** Washer footprint (Ø 12 mm for M6) plus the VDI 2230 compression cone through the flange | Fixed support, and where the base excitation enters. **Not the whole flange face.** Clamping the whole flange over-predicts f1, the same effect behind D-0001's L0 205 Hz versus L1 184 Hz |
| **Module bolt footprints on the bracket** | Rigid (RBE2-type) coupling to the module's centre of gravity: 1.2 kg plus inertia. If the module housing is not stiff (octave rule fails), switch to an RBE3-type coupling, which adds no stiffness |
| **Module-to-bracket contact patch** | 15 W heat input, with contact conductance (with or without a thermal pad) |
| **Rail contact land** | Heat sink at ambient temperature through contact conductance (a flagged assumption) |
| **All other bracket faces** | Natural convection and radiation to 65 °C ambient |
| **Bends, hole edges, seams** | Stress read-out regions for fatigue. Points at rigid couplings are excluded (singular) |
| **Envelope, keep-outs, and a generated socket-access cylinder on every bolt axis** | Geometric limits on the bracket, so the bolts can actually be tightened |

**Loads.**
- The ISO 16750-3 body-profile random PSD as base excitation, one vehicle axis at a time.
- The standard's shock pulse.
- Gravity.

**Rail stiffness is a modelling choice on the ladder.**
- L1 assumes the rail is rigid at the clamped zones.
- If the rail's local stiffness is not well above the bracket's (for example 10×), the result is flagged.
- L2 then models a patch of the rail, or uses the rail's measured drive-point FRF if the user has one.

### A.6 Check the boundary conditions automatically (tool)
- **Free-free:** exactly 6 rigid-body modes. The module is attached and nothing is loose.
- **Constrained:** zero rigid-body modes. The model is not under-constrained.
- **Reactions:** under 1 g they equal the total weight, which catches missing mass and unit errors.
- **Effective masses:** they sum to the total mass.
- **Tags:** every tag is found, with the expected area.

### A.7 Preview (UI)
Before running, the 3D viewer highlights the fixed zones, the mass coupling, the heat input and the keep-outs. The
user can catch a wrong boundary condition in seconds.

### In the data factory
- This step is easier there: the request sampler generates the rail, module and envelope itself, so the interfaces
  are known exactly.
- Recognition is needed only when a user brings their own CAD.
- The factory's own geometry, exported as plain STEP files with the tags removed, is a ready-made test set for the
  recognition step.
