# Data, tasks and learning: what the factory records and what it trains

**Date.** 8 October 2026. Written at 09:40 from the discussion with the engineer between 08:43 and 09:37.

**Status.** Design, worked out in discussion. **Nothing here is built.** Two decisions it rests on were taken the night before:
- every problem is a replayable graded task (01:25);
- an attempt hands in any geometry (01:32).

Both are recorded on the [contract page](../contract/status.md). The proposals in §9 await the engineer.

**Builds on:**
- the plan's §9 (data) and §10 (learning): [plan.md](../product/plan.md);
- the contract: [2026-10-08-contract-v0-design.md](../contract/2026-10-08-contract-v0-design.md);
- the requirements catalogue: [requirements-catalogue.md](../contract/requirements-catalogue.md).

---

## 1. The framing: a few families, many variants

- **What industry has:** variants of four or five housing families, not a thousand products. The engineer's example: Mercedes-Benz rear axles HAG 183, 197, 205 and 206, which serve different ratios and vehicles. Helical gearboxes are the same.
- **Where the datapoints come from:** the thousands of datapoints come from the **variants** of a customer's families, and from **every attempt and every decision** made on each variant.
- **This suits learning.** Within one parametric family, field models reach 1.75-3.9 % error, against about 30 % across topologically diverse designs (plan §5.2, geometry lesson 10).
- **A hypothetical customer.** Take a team building rear axles that adopts the product within three months:
  - **Their production CAD and load cases come first.** That is the "existing part" entry point, with their production housings as the designs to beat.
  - **A rear axle has hypoid gears,** so it needs its own load module (hypoid gear forces). The first module is for parallel-axis helical reducers. The core is the same: contract, judge, field-space geometry.

## 2. Tasks, contracts and attempts

**One contract is one task.** A frozen contract is the question, and its hash is its identity.

```
Contract  = the task (the question; fixed, never changed by the agent)
 └─ Campaign      = one attempt at the task by one solver, with a budget
     │              (our agent, a fixed workflow, an optimiser, a person)
     └─ Hypothesis   = one idea with its reason, e.g. "bridge the bearing seats to the mount"
         └─ Design      = one housing that idea produced
             └─ Grade      = the FE result, judged against the same contract
```

**New contracts, and so new tasks, come only from a changed requirement:** a torque, ratio, package, mount position, limit, process, or priority. "Lightest" and "quietest" are two contracts on the same physics. This gives three kinds:
- **variants:** the customer's own;
- **counterfactual pairs:** identical but for one requirement;
- **priority sets:** one physical problem under different priorities.

**The agent cannot change the contract.** When no design in the space can meet it (the bound misses the goal), the agent says what would open the space: more room, a looser limit, another process. The engineer then decides whether to issue a new contract.

## 3. The four axes

| Axis | Answers | Examples | In the data |
|---|---|---|---|
| **Task** (the contract) | What must the design meet? | The required peak torque, ratio, mounts, package, process, limits, priorities | A change gives a **new contract, so a new task** |
| **Attempt** | What was tried? | Campaign → hypothesis → design | Many per contract |
| **Evaluation** (scenarios) | Under which conditions is the design tested? | The load cases (drive, regeneration, reverse, park lock), hot and cold, mounted or free-free, the order-check speeds, screen or full FE, mesh size | **One design, many evaluation records** |
| **Result** | What did the test show? | Displacements, misalignment, tilt, stress, natural frequencies, **mode shapes**, mass, the verdict with margins | What the physics models learn to predict |

**The test for any quantity:** does the engineer *require* it (task), does the judge *test under* it (evaluation), or does it *come out* (result)?

- **Torque sits on two axes.**
  - The required torque is a task input: the best design changes with it.
  - Applying drive, regeneration and reverse at that torque is an evaluation.
  - A robustness sweep of the same design (say 80-120 % of peak) is also an evaluation, and nearly free. In linear statics each design is solved once per unit load per seat direction, and any torque or direction is a re-weighting without a new solve. fastcae and agenticCAE stored their results this way.
- **Mode shapes are results.** They come out of the modal scenario, whose supports (mounted or free-free) sit on the evaluation axis. The modal requirement (at least 3 % from gear orders at the check speeds) is in the contract's limits.

**Example: one design, eight evaluation records.** For contract F1-base and design #12:

| Scenario | Kind |
|---|---|
| Drive, regeneration, reverse | Static |
| +80 K | Thermal (the fits) |
| Mounted modes, free-free modes | Modal |
| Screen, fine mesh | Fidelity |

**Splits are by contract or family, never by scenario** (plan §9.4). Otherwise a model would see the same design under another load case.

## 4. The kinds of datapoint

| Kind | What it is | Trains |
|---|---|---|
| **A. Contract** | A requirement: the question | The task set |
| **B. Graded design** | A geometry plus its FE results under each scenario, failures included | The physics models |
| **C. Decision** | What the agent saw, the idea it tried and why, and what happened | The agent (the LLM) |
| **D. Engineer's choice** | Which design was accepted or rejected, and why | Preference: what engineers want |
| **E. Counterfactual pair** | Two contracts differing in one requirement, and how the design changed | Cause and effect |

**23 examples, for a hypothetical rear-axle team.** F1-F4 stand for its four families; every value is illustrative:

| # | Kind | Family / variant | What is asked or tried | Outcome | What it teaches |
|---|---|---|---|---|---|
| 1 | A | F1 base | Torque, ratio, subframe mounts, package, die casting, limits | (question) | The base task |
| 2 | A | F1, higher ratio | Larger ring gear, more carrier-bearing thrust | (question) | A ratio variant |
| 3 | A | F1, heavier vehicle | Peak torque +20 % | (question) | A vehicle variant |
| 4 | A | F1, new subframe | Mounts moved | (question) | A mount variant |
| 5 | B | F1 base | The customer's production housing, as STEP | Tilt, alignment, first mode, mass | The anchor |
| 6 | C | F1 base | "The pinion seat tilts because its nose is soft; add a ring rib" | Tilt −30 % for +0.2 kg; promising | A good physical idea |
| 7 | C | F1 base | "Thicken the whole wall 1 mm" | Tilt −10 % for +0.6 kg; poor | Worse per kilogram |
| 8 | B | F1, design 12 | Bridges from the carrier bearings to the mounts | Passes; 8 % lighter than production | A winning design |
| 9 | B | F1, design 13 | Wall thinned to 3.5 mm | Fails the casting minimum wall | Failures are data |
| 10 | B | F1, design 15 | Panel ribs removed | First mode on a gear order at cruise | Order crossings |
| 11 | E | F1 base vs +20 % torque | Same function, more torque | Web added at the carrier bearing; +6 % mass | Cause and effect |
| 12 | E | F1 base vs new subframe | Mounts moved | Ribs re-route to the new mounts | Structure follows the load path |
| 13 | C | F2 | The F1 pinion-nose rib idea, reused | Works: tilt −25 % | A lesson that transfers |
| 14 | C | F3 | The same idea | No gain: another bearing arrangement | One that does not |
| 15 | B | F3 | The bound | Misses the alignment target | Says what would open the space |
| 16 | D | F2, design 7 | Accepted | "Keeps our machining fixture" | What engineers value |
| 17 | D | F2, design 9 | Rejected | "The rib blocks drain-plug access" | A requirement the contract lacked |
| 18 | B | F4 | Hot case, +80 K | Interference still positive | The fit check |
| 19 | C | F4 | Switch from shell-and-ribs to struts | −5 % mass at equal tilt | A switch that gained |
| 20 | B | F2 | The same design meshed twice | 1 % apart | The noise level, so ties |
| 21 | B | F1, design 20 | The screen predicted tilt X; FE gave Y | The gap | Trains the fast predictor |
| 22 | A+B | F1 base | The rule-based method and the agent attempt it | 14 against 9 FE runs | Benchmark evidence |
| 23 | E | F1, "lightest" vs "quietest" | Same physics, another priority | Fewer ribs against stiffer panels | The trade-off |

**Scale, roughly, for four families:**
- **Contracts:** 4 families × about 10 real variants, plus 3 one-change counterfactuals each, is **about 160 contracts**.
- **Graded designs:** each contract × 3 approaches × about 20 designs is **about 10,000 graded designs**, each under 3-6 scenarios.
- **Decisions:** about 160 × 3 × 30 steps is **about 14,000 decision records**.
- **Engineer's choices:** tens to hundreds. These are the most valuable per item.

## 5. Cutting a campaign into datapoints and tasks

**Every step is logged with what the agent saw at that moment.** The record holds, each by reference and hash:
- the contract;
- the current design;
- the FE results, the maps and the pictures;
- the tool versions;
- the budget spent.

It also holds the idea and its reason, the outcome, and the hypothesis status that code computed. Plan §9.1 already requires every record to keep its parent, its tool versions and its hashes.

```
Campaign on F1-base (~30 steps)
  step 5  "thicken the wall"              → tilt −10 %, +0.6 kg   (poor)
  step 7  "web: pinion nose → mount 1"     → 2.7 µm, +0.25 kg     (pass)
        ├─ every step     → a decision record (situation → idea + reason → result)
        ├─ step 7 frozen  → a stand-alone task: "design #8 and its FE evidence:
        │                    diagnose and propose a fix"
        └─ steps 5 and 7  → a preference pair (the web gained more per kg)
```

**Rules:**
1. **A frozen step holds only what was known at that moment:** no later step, no outcome.
2. **Failed ideas are kept:** the worse half of preference pairs, and tasks of their own ("why did this fix not work?").
3. **Branch at revealing moments:** try three ideas from the same state and grade all three. That is how ranking tasks are made.
4. **Same split:** every step from one contract or family stays on the same side of the train/test split.

**Not every step is a task.** The decisive ones are: a large gain, a clear failure, a switch of approach, or a correct stop. A 30-step campaign typically gives about 30 decision records, a few preference pairs and a few strong stand-alone tasks.

## 6. Twenty task types

Each task gives a contract (and a geometry where needed), asks for one thing back, and has a fixed grader. H is Hofstetter's EV reducer; AG is the agricultural EV gearbox; the numbers are illustrative.

| # | Task | Given | Hand in | Graded by | Used for |
|---|---|---|---|---|---|
| 1 | The six bearing-seat loads | H's gear train, torque, seat positions | Force vector per seat | The load tool, within 1 %, directions included | Imitation, test |
| 2 | Gear-mesh frequencies; the speed where an order meets a 1,350 Hz mode | Tooth counts, speed range | Frequencies, crossing speed | Exact arithmetic | Imitation, test |
| 3 | Place the intermediate shaft | Ratio 9.32 ± 1 %, offset 165 mm | Gears and shaft position | The validator's ratio and offset rules | Imitation, test |
| 4 | Fit loss when hot | Ø72 aluminium seat, steel bearing, +80 K | µm lost | Thermal arithmetic (about 66 µm) | Test |
| 5 | Find the errors in a contract | A contract with three hidden faults | Each error and why | The validator's refusals | Imitation, test |
| 6 | Static FE under every load case | H contract, housing STEP | Misalignment per mesh, tilt per seat | The frozen judge, within mesh noise | Test |
| 7 | Free-free modes against the measured band | AG housing proxy | First six modes | The judge, and the published 1,352.7 Hz | Test |
| 8 | Mesh convergence | A design, two mesh sizes | The change | The judge's noise measure | Test |
| 9 | How bearing loads are applied | Rigid against distributed seat loads | The change in tilt | The judge's two runs | Test |
| 10 | Castability | A mesh, a pull direction | Share under 1° of draft; least wall | The casting checker | Test |
| 11 | The lightest passing housing | H contract | A housing, STEP or mesh | The judge (pass, then mass) | Reinforcement learning, benchmark |
| 12 | Make a 3.6 kg passing design ≥ 5 % lighter | The design | The modified design | The judge | Reinforcement learning |
| 13 | Fix a mode 2 % from a gear order, ≤ +0.2 kg | The failing design | The fix | The judge | Imitation, reinforcement learning |
| 14 | Make it castable, ≤ 2 % stiffness lost | A design with a draft fault and a void | The castable design | The checker and the judge | Reinforcement learning |
| 15 | The same housing for +20 % torque | H contract, changed | Design plus the reason per change | The judge, and the stated reason checked | Preference, test |
| 16 | Re-route for moved mounts | The F1 variant | The design | The judge | Reinforcement learning |
| 17 | Diagnose the soft load path; propose a fix with its effect | An FE result | Diagnosis, fix, expected gain | An FE run of the fix: did it gain as claimed? | Preference |
| 18 | Stop or continue? | The bound misses the target by 15 % | The decision, and what would open the space | Correct stop; valid options | Imitation, test |
| 19 | Rank three ideas by gain per kilogram | Evidence, three hypotheses | The ranking | Pre-computed FE of all three | Preference |
| 20 | Estimate seat tilt by hand before FE | A simple housing | The estimate and its governing parameter | Within 30 % of FE; parameter named | Test (the reduced-order skill) |

## 7. LLM fine-tuning: the data and the process

**What the LLM learns: how the agent decides.** That is: in this situation, which idea next and why, and when to stop. The physics numbers train the physics models (§8).

**Three kinds of data, in order:**

| Stage | Data | From |
|---|---|---|
| 1. Imitation (supervised fine-tuning) | *situation → the good next step*: the hypothesis, its reason, the tool call | Decision records of campaigns that went well |
| 2. Preference | Pairs: *in the same situation, step A graded better than step B*; the engineer's accept and reject choices with their reasons | The judge's grades on alternatives; the engineer's choices |
| 3. Practice with a grader (reinforcement learning) | The model attempts whole tasks; the frozen judge's score is the reward | The replayable contracts |

**One decision record** (illustrative):

| Part | Example |
|---|---|
| What the agent saw | Contract F1-base. Best so far: misalignment 4.1 µm against a 3.0 µm limit, mass 3.4 kg. 62 % of the strain energy is near the pinion nose. The first mode is 2 % from a gear order at 7,500 rpm. 7 FE runs left. Tried: "thicker wall" (poor), "ring rib" (promising) |
| What it decided | "The pinion seat tilts because the path from its nose to mount 1 is soft; a web there should cut misalignment more per kg than the rib alone. Expect ≤ 3 µm at +0.3 kg. Wrong if misalignment drops less than 10 %. Budget: 3 FE runs." |
| What happened | After 2 runs: 2.7 µm, +0.25 kg, pass. Code marked the idea "met" |

**What is not used** to fine-tune the LLM:
- meshes, stress fields and mode shapes as targets;
- physics numbers as outputs to produce.

The LLM reads numbers the judge computed and never learns to produce them.

**The process:**
1. **Make the tasks:** the factory writes contracts (variants, counterfactual pairs, priorities) and freezes each.
2. **Run attempts:** our agent, the rule-based method, the optimiser and sometimes a person. Every step and the final grade are recorded.
3. **Clean and split:**
   - hold whole families out;
   - check that no task carries an answer;
   - keep the failures.
4. **Imitation:** good steps become *situation → next step* pairs. A small open model is tuned (often with a light method such as LoRA) and tested on held-out tasks.
5. **Preference:** better-against-worse pairs, and the engineer's choices.
6. **Reinforcement learning with the grader:** whole tasks, the judge's grade as the reward (pass, margin, mass, less the FE runs spent). This needs many tasks and GPUs: COSMO-Agent used 20,000 tasks and 16 H200s, going from 26 % to 74.5 % (plan §10.2).
7. **Decide:** the tuned model runs the same benchmark, as a separate arm (plan §10.5). It is kept only if it beats the untuned frontier agent on unseen families at lower cost (plan §10.2).

**Caution: the tools carry most of the gain.** Typed tools took end-to-end success from 22 % to 83 % in published work (plan §8.2).

**For the hypothetical customer:**
- About 160 contracts give about 14,000 decision records. That is enough for a first round of imitation, not for reinforcement learning.
- Until a tuned model earns its place, the same records serve better as **a library the agent consults**: which ideas worked on which family, and why. The engineer deferred that "learned hypothesis prior" on 7 October; bringing it forward is the engineer's call.

## 8. Physics AI, briefly

- **What it learns:** (design, scenario) → results.
  - Scalars: misalignment, tilt, first modes.
  - Fields: displacement, strain energy.
  - Mass is always computed, never learned.
- **The order** (plan §10.2):
  1. A calibrated scalar predictor that also ranks candidates (30-100 FE results a family).
  2. A failure predictor.
  3. A field model on mesh points (hundreds to thousands of results).
  4. Ranking the agent's moves by the models.
- **Its job:** screen candidates in milliseconds and choose, by a fixed acquisition rule, which get a real FE run. **Never the judge.** Peak stress stays with FE.
- **Its scorecard** (plan §10.5):
  - rank correlation, and the regret of its pick;
  - a false-pass rate of at most 1 %;
  - interval coverage;
  - error against the distance to the nearest training design.

## 9. What this asks of the data feature (proposed PBIs)

These are proposals, not yet agreed:
- **DAT-1, the record schema:**
  - task, campaign, episode (hypothesis), candidate, evaluation;
  - each with its parent, its hashes and its tool versions;
  - the scenario on every evaluation;
  - failures with a taxonomy;
  - append-only.
- **DAT-2, snapshot tasks:** freeze any step as a replayable task, holding only what was known then. The grader runs the attempt's fix through the frozen judge.
- **DAT-3, the engineer's choices:** accept or reject, with the reason, tied to the design and the contract. *Proposed on 7-8 October; not yet answered.*
- **DAT-4, the task export:** a frozen contract, the grader's version and the references, so that outside attempters (people, other agents, AI labs) can take a task.

## 10. Open

- Whether to record the engineer's accept and reject choices (DAT-3).
- Whether to bring the agent's library of past decisions (the learned hypothesis prior, deferred on 7 October) forward for a customer.
- A hypoid (bevel) load module for rear axles: not in the plan.
- The rule for choosing the decisive steps that become tasks.
- The split policy when a customer has only four families: one family held out at a time, or held-out variants within a family.
