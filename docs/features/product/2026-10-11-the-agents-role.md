# The agents' role, from the first end-to-end runs

**Date.** 11 October 2026, written 05:20-06:00 while the night's last runs ran. **Asked by the engineer** (01:26-01:38): once the pipeline runs end to end and its robustness, its failures and the cases needing a person are known, decide how agents become native to the process. Agents should take manual work off people, help them reason beyond their first ideas, and turn every run into data for training agents. Re-read beside the original vision (the MechanicalAI and micro1 posts).

**Read with:** [the night's record](../loop/2026-10-11-record-night.md) (every trial, failure and fix), [the plan of record](plan.md) §3 and §8-11 (the agent, the data, the learning, the benchmark), [the two job descriptions read against zenryx](../../research/2026-10-08-job-descriptions-against-zenryx.md), [the differentiators](differentiators.md).

## 1. The view as of now

1. **The pipeline now runs end to end, fast enough for a loop.** A judged design in about 5 minutes (flow B), or exact CAD in about 9 (flow C), against about 50 the evening before. That is a dozen judged hypotheses an hour. Until tonight the agent's role was a hypothesis about a pipeline that did not exist; now it is a question about this one.
2. **The tools compute and judge; that holds.** Every number on the grade came from a versioned tool. Nothing tonight needed an agent to derive physics, and nothing should.
3. **What tonight's course changes were made of: decisions no tool makes.**
   - the formulation (one run or two stages, the beds held or not);
   - the drawing's route (OCC, meshes or ribs);
   - how a field is read into a part;
   - what to do about a line that fails;
   - how to cure a tool run that breaks;
   - when to stop and what to tell the engineer.

   These are the agents' work: the plan's level 3 (which hypothesis to test), extended to the reading and the repair.
4. **The engineer's part is clear from what they corrected.** Ten of the course's turning points were the engineer's word:
   - the load cases;
   - the wall and the flange as the contract's;
   - no three robust versions;
   - stopping when settled;
   - one run, not stages;
   - speed first;
   - read the field like a designer;
   - fix the inputs before optimising;
   - the UI;
   - ask plainly.

   They are functional truth, cost against benefit, taste and communication. Each became a rule or a default. That kind of decision stays the engineer's, and the agent's job is to bring it to them early and plainly.
5. **Agents become native at five seams** (section 5): the formulation, the reading, the response to a failed line, the repair of a broken run, and the conversation with the engineer. Each already has typed inputs and measured outputs in the pipeline as it stands.
6. **Creativity, concretely:** widen what the engineer sees, each option judged in minutes, never claimed without a judge. Tonight the Designs page shows every flow tried, with its own tabs. That page is where the engineer and the agent meet.
7. **The data is the trajectory, the repairs and the corrections.** MEKINT's synthetic sets have the trajectories but not the corrections; micro1's hand-made tasks have neither repairs nor corrections. Every run tonight recorded each step, its time and its outcome. Adding typed failures and the engineer's corrections to those records makes the data neither has.

## 2. The pipeline the agents work on (as it runs at 05:15)

| Step | Tool | Time | What it settles |
|---|---|---|---|
| The contract | the engineer, the validator | - | the requirement: interfaces, loads, limits, process |
| The set-up | `topo_free.build_free` (from `spaces`) | 3 s | what is fixed, kept out and free (the exact wall, the flange, the bosses, the mounts) |
| The optimisation | `topo_free.py`: GCMMA, MMA's dual, stopping once settled | 3.4 min | where the metal goes, within one formulation |
| The drawing | flow B, the mesh route; or flow C, the ribbed CAD (`ribbed_cad.py`) | 12 s; 2.8 min | the part's shape and representation |
| FE | TetGen, cuDSS TET10, peak drive and 12 modes | 1-2 min | the physics at the seats |
| Castability | rays along the pull | 1 min | undercut, voids, thin sections |
| The grade | `grade.py` | 1 s | each line's verdict |
| The page | `process_export.py`, the Designs page | seconds | what the engineer sees: every flow, every step |

## 3. What failed tonight, and who cured it

Every failure was found by a measurement (a volume, a face's width, a count of crossing faces, a memory request), not by a look. "Who" says who could have cured it.
- **tool:** cured now by a rule or a ladder in the code;
- **coding agent:** a change to the code, admitted by checks and the judges;
- **design agent:** a choice of formulation or reading;
- **engineer:** a decision that is theirs.

| Step | Failure | Cause found | Cure | Who |
|---|---|---|---|---|
| Optimisation | the tilt held from iteration 1 floated the core (10 Oct) | a relative tilt can't see a rigid swing | hold the bearing beds too | design agent |
| Optimisation | two stages took the time of one and gave the softer design | habit | one run, the beds and tilt held from the start | design agent, the engineer's push |
| Optimisation | runs ran their full count | no stop rule | settle stop (0.2 % over 5 iterations) | tool |
| Drawing, OCC | not watertight on thin members; 114,000 faces, 10 min; faces 0.000 mm wide | smoothing folds thin members; sewn facets | the mesh route (10 s) | coding agent |
| FE meshing | gmsh refused or crawled on the mesh route's surface | its reparametrisation | TetGen | coding agent |
| FE meshing | TetGen: "self-intersections" | the decimation folded bare 4 mm walls | decimate again with the faces near crossings kept out | tool, since 03:58 |
| FE meshing | TetGen: "repair_tet", "recoversubfaces"; flat tets | features under 0.1 mm from exact parts meeting | FE's body filled on a 1.5 mm grid, the machined faces exact | coding agent |
| FE | 2.8 M unknowns, past the factor | thin ribs force small tets | TetGen's quality relaxed past the ceiling | tool |
| FE | 18 GB asked at 1.68 M unknowns | eliminating a coupling filled the stiffness densely over finely meshed holes | each coupled set spread to 300 nodes | tool |
| Drawing, OCC (flow C) | the cover lost, called valid | a fuse of several parts sharing the joint's plane | fused a pair at a time, checked by volume | tool |
| Drawing (flow C) | the mounts left loose | a centre-line stops half a member short | free ends carried on; a strut into each mount | coding agent |
| Drawing (flow C) | slivers 0.002-0.08 mm | parts' faces tangent to cylinders, tops grazing faces | kept 1.5 mm off; ribs only 3 mm proud; posts 1 mm proud | coding agent |
| Reading (flow C) | tilt 1.30 × | the pad over the output lobe's end wall dropped (its outline crossed itself) | pads as polygons: 1.13 × | coding agent |
| Reading (flow C) | still softer: 1.20 × at the intermediate seat | uniform ribs on centre-lines don't carry what the organic members carry there | **open: an agent's move** (section 6) | design agent |
| FE meshing | the 10 mm scout's motor side refused by TetGen at 9, 7 and 5 mm triangles | not found: pymeshlab sees no crossing, no non-manifold vertex or edge, one watertight body | **open:** TetGen's own intersection report next | repair agent |
| Grade | a mode within 3 % of stage 2's order in every flow B design (1,123-1,149 Hz, at five budgets and members) | the optimiser never sees the modes; the budget doesn't move this one | **open: a mode margin in the formulation** | design agent |
| Grade | mass 0.24-0.3 kg over (flows A, B) | the drawing adds metal round the field | **open**; flow C is under the mass | design agent |
| Page | Edge's screenshot showed placeholders | it captures before the lazy views load | `web/tools/shot.mjs` | coding agent |
| Notes | the load case changed unasked (10 Oct) | my default, not the engineer's | the contract's load cases are locked | the engineer's |

**What it shows.**
- **Robustness:** the pipeline's tool failures are many, but each was found by a measurement within minutes and is now cured by a ladder rung or a rule. A broken run should cost minutes, not a person.
- **What remains open:** the physical failures: a tilt at one seat, a mode near an order, the mass. Those are decisions about the design, and they are the design agent's work.

## 4. The cases that need the engineer

| The engineer's word (this session) | Its kind | What it became |
|---|---|---|
| One load case, peak drive, in the optimiser and the checks | functional truth | locked in the contract; the agent may propose a case, never add one |
| The 4 mm wall drawn exact; the split flange the contract's | functional truth | contract entries (`JointRules.land_width`), the exact shell |
| No three robust versions: "are they really helping?" | cost against benefit | a method is kept only with its measured gain |
| Stop the run when the result stops changing | efficiency | the settle stop, the default |
| One run, not stages "unnecessarily" | simplicity of the formulation | the one-run formulation (measured better and faster) |
| "If each end-to-end process takes 50 mins it's the end of the story" | the product's priority | 5 minutes a design, the pipeline's target |
| Read the field like a designer; the readings were "nowhere close" (10 Oct) | taste, realism | the reading as a hypothesis, judged (flow C) |
| Mounts realistic, decided once before a run (10 Oct) | inputs | inputs fixed before optimising |
| The Designs page's layout, every flow with its tabs | presentation | LOP-21 |
| Ask plainly, one decision at a time, name things exactly | communication | the dialogue agent's rule |

**When the agent must bring something to the engineer:**
- a contract entry it would change (a limit, a load case, an interface, the process);
- a trade between lines (mass against tilt);
- a method whose cost isn't yet shown to pay;
- a design it calls ready, for acceptance;
- any judge it would change.

Everything else (formulations, readings, repairs, variations) it may do inside its budget, and it reports with the evidence.

## 5. Where the agents become native

| Seam | The agent decides | Its tools (typed) | Measured by | Tonight's evidence |
|---|---|---|---|---|
| **The formulation** (the plan's level 3) | the hypothesis and its formulation: objective, constraints (tilt, beds, member size, a mode margin), route, budget, voxel size; when to drop it | `topo_free.py` (its arguments are the formulation's fields), a 10 mm scout and a 6 mm finalist, the binary check | the grade's lines, minutes per hypothesis | the floating core falsified and cured; two stages against one run; the settle stop |
| **The reading** (the field into a part) | which members become ribs, pads or organic, their sizes, which rules; where a reading lost what the field had | `ribbed_cad.py` and its settings, the mesh route, `field_and_cad.py`, `voxel_vs_fe.py` | the loss against the field: mass, tilt, beds | flow C: the pads dropped cost the tilt (1.30 → 1.13 ×); uniform ribs lose the intermediate seat (1.20 ×) |
| **The failed line** | the change that fixes it, where, at what cost | thicken or add a rib at a seat, a local re-optimisation, a mode margin | the line's verdict, the mass spent | the third mode's clash; the intermediate seat |
| **The broken run** | the diagnosis and the cure; a cure kept as code only when the checks and the judges admit it | the typed failures, the cures' ladders, the measurements (volumes, face widths, crossings), a coding agent with tests | minutes to recovery, the failures' recurrence | about 15 cures tonight, each now a rule or a rung |
| **The engineer** | what to show, what to ask, which single decision to bring | the Designs page (every flow, every step), the records, plain summaries | decisions per hour, corrections needed | ten corrections, each now a rule |

Two plan rules stay as they are:
- **the agent never derives physics or judges;**
- **which candidates get a proof is chosen in code**, not by the agent (plan §10.3).

## 6. Thinking beyond: the moves an agent would put to the engineer now

Each move is a hypothesis with its reason, its expected effect and what would prove it wrong, costing 5-9 minutes a try.

| Hypothesis | Reason | Expected | Wrong if |
|---|---|---|---|
| Strengthen the ribs round the intermediate −z seat (flow C; **run, 05:37**) | the seat that fails is the one whose organic members the ribs replaced | tilt ≤ 1 × at +0.2-0.4 kg, still under 7.73 | the tilt does not fall per gram as the field's members did. **Result: falsified.** The ribs within 60 mm of the seat at 12 mm and 6 mm higher gave tilt 1.192 × against 1.195, for +0.10 kg and a new clash at 2,432 Hz. The cause is not those ribs; next, compare the field and the CAD along the seat's load paths before strengthening |
| Keep the organic members within about 40 mm of each seat, ribs elsewhere | the seats need the optimiser's exact shapes; the panels don't | flow B's tilt near flow C's mass | the mass rises past 7.73 |
| A mode margin in the optimiser (no mode within 3 % of an order) | the clash is the one line the optimiser does not hold | the clash gone at a small compliance cost | the compliance rises past the beds' line |
| A lighter budget, 7.2 kg (**run, 05:21**) | flow B's drawing adds about 0.3 kg | a design under 7.73 with the lines held | the tilt or the beds fail. **Result: 7.45 kg, beds 28.2 µm, tilt 0.77 ×: three lines pass; a mode at 1,149 Hz sits 1.95 % from stage 2's order (3 % needed).** The next move is a small budget sweep, or a mode margin |
| A 10 mm scout (**run, 05:24**) | hypotheses screened in about 2 minutes, 6 mm for finalists | the same ranking at a third of the time | the scout's ranking differs from the finalist's. **Result: 175 s end to end (the optimisation 71 s); its FE stopped on a surface TetGen refused, now cured (coarsened again finer), FE again** |
| Thinner members, 9 mm (**run, 05:31**) | the trade's ribs are thinner than 12 | more, thinner members, as cast housings have | stiffness falls more than mass. **Result: beds 21.6 µm, tilt 0.70 ×, but 8.15 kg and two clashes: no lighter** |

| Budgets 7.0 and 7.4 kg (**run, 05:42-05:47**) | if the clash moves with the mass, a budget clears it | a budget where no mode is within 3 % of an order | the mode stays near the order. **Result: it stays.** 7.21 and 7.63 kg drawn, beds and tilt pass, modes at 1,148 and 1,145 Hz |

**What the moves taught, beyond each one:** across five budgets and members (7.0-7.73 kg, 9 and 12 mm), every flow B design has a mode within 3 % of stage 2's order (1,123-1,149 Hz). The budget moves the mass but not that mode, and the optimiser never sees the modes. The ribbed CAD's modes straddle the order (1,087 and 1,176 Hz). An agent reads that pattern across runs; a single run cannot. So the next formulation carries a mode margin (the eigenvalue's derivative as a constraint), or the next reading is checked against the orders before FE is spent on it.

**And how the moves were recorded:** each move above has its reason, its expected effect and what would prove it wrong, written before it ran; its result decides. One was falsified within 5 minutes; that is the plan's hypothesis bookkeeping (§3) running on real tools.
| The split plane as a hypothesis | the split decides each half's pull and its walls | another split may cast with less undercut | the bearings' bores cross the split |

## 7. Agentic data generation

**What each run already records:**
- the flow, each step's name, method, time, view and card;
- the design with its grade, castability and pictures;
- the optimisation's history and its metal-or-air check;
- the night's account of every failure with its cause and cure.

**Four datasets, from the same runs:**
1. **Graded tasks** (the micro1 kind, made by the factory, not by hand): the frozen contract as the question, the frozen judge as the grader. Any attempt, by an agent, a method or a person, can be graded.
2. **Campaign trajectories** (MEKINT's "agent trajectories"): state → action (a formulation, a reading, a fix) → consequence (the grade's lines). For example, two stages (197 s, compliance 793.1 N·mm, tilt 0.998 ×) → one run (231 s, then 194 s with every gradient row back in one pass; 789.8 N·mm, 0.926 ×).
3. **Repair trajectories** (new): a typed failure → its measured diagnosis → the cure → the checks that admitted it. Tonight gave about 15; they teach tool-using agents what MEKINT's and micro1's data do not.
4. **The engineer's corrections** (new): each correction with its context and the rule it became. They align an agent with how this engineer works, and they are what "work more efficiently with humans" means in data.

**To add to the records** (proposals):
- a typed failure code on every step's outcome (`not_watertight`, `self_intersecting`, `past_ceiling`, `host_memory`, `sliver`, `loose_part`, ...) with its measurement;
- the reason for every choice, as the plan's hypothesis record holds it;
- the engineer's corrections as records beside the campaign;
- the human interventions per campaign (the plan's measure, §11.3).

## 8. What this changes in the plan (proposals, for the engineer)

1. **The reading becomes a hypothesis type** beside the formulation. A field's reading into a part has its own claim, its own budget and its own measured loss against the field, the "interpretation penalty" of the differentiators.
2. **Repair becomes a product capability.** The pipeline returns typed failures (the plan's §8.2 asks for this), known cures are ladders in code, and a coding agent proposes new cures, admitted by checks and the judges.
3. **The engineer's corrections become first-class records,** and "human interventions per campaign" is reported with every campaign.
4. **The unit of the loop is the 5-minute design.** The benchmark's budget (plan §11.2) is counted in minutes as well as in proofs: speed is what lets the agent try options on purpose.
5. **The Designs page's flows are the seam between engineer and agent:** every flow tried is visible with its steps, and the engineer can see where a reading or a route lost.

What stays: the tools compute and judge; the agent works at level 3; deterministic acquisition picks the proofs; the kill criterion (the agent must beat the adaptive rule-based arm at equal budget).

## 9. The levers a campaign varies, once the flow is fixed

**The engineer, 11 October 13:31:** once the flow is fixed, these give the variations, beside the agent's hypotheses and the investigations a user directs in plain language ("what if the mounts were softer?", "show me designs with box sections"), towards more interesting designs. Each lever is one of the optimiser's settings or assumptions. Each variant is a hypothesis with its reason, run in 2-7 minutes and graded. A lever that changes a contract limit, the process, a load case or the FE budget needs the engineer's word (CLAUDE.md); in the product, the user's query is that word.

| Lever | Today | Varied, it opens | Built |
|---|---|---|---|
| **Undercuts** | none: each half cast along the shafts, every column one piece from the split (`--route split`, the contract's pull directions) | hollow box sections, bridges and arches, overhanging ribs, side bosses on cores, as printed sand moulds (A11) allow | no: a route with cores, and a castability check that judges trapped sand and core prints instead of the pull |
| **The members' greatest thickness** | 8 mm at 4 mm voxels, 12 at 6 (`--max-member`) | thick solid bosses and pads, or thinner and more members | yes |
| **The resolution** | 4 mm voxels; 6 mm, and a 10 mm scout | finer members and smoother slopes, for more time; the FE ceiling bounds it | yes (`--voxel`) |
| **Several designs of equal merit** | one run, one design: a local optimiser from an even start | other topologies: other starts, or deflation (each run pushed away from the designs found) | no |
| **How much metal** | a fixed budget, all of it spent (`--budget`) | the lightest design that meets every line (the mass as the objective) | the budget yes, the lightest no |
| **The objective and constraints** | stiffness, every seat's tilt and bed held (`compliance_tilt --beds`) | a mode margin (no mode within 3 % of an order), the misalignment as the objective, the design held eroded and dilated (`--robust`) | all but the mode margin |
| **The height envelope** | 24 mm (the engineer, 13:21) | taller or lower ribs | yes (`--band`); the engineer's to change |
| **The inside** | a cup round each gear's room, open to the split | another inner wall (each room its own, a fairer lobed inside) | `--cavity cup` or `rooms` |
| **The load cases** | peak drive alone | both peaks, more cases | yes (`--cases`); a new case is the engineer's |
| **The mounts' support** | held rigid | compliant bushings | no |
| **The inputs the agent set** | the 3 mounts' places, 13 bolts, the split's height | other places, counts and heights, each an agent's hypothesis | the split as a hypothesis (`spaces`); the mounts and bolts from the layout |
