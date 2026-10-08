# The contract, v0: design

**Date.** 8 October 2026, 02:10.

**Status.** For the engineer's review. Nothing is built.

**For.** CON-1 (contract schema v0). It follows the decisions on the [product page](../product/status.md), Decisions, first two rows, and on the [contract page](status.md), Decisions.

**Evidence.**
- The [requirements catalogue](requirements-catalogue.md), each row cited.
- The [housing papers note](../../research/2026-10-07-housing-papers-for-the-contract.md).
- The plan, sections 4 and 9.

---

## 1. What the contract is for

- **The question the factory designs to.** One housing design problem at L1 (fixed interfaces): what must be connected, what loads pass through, what must hold, how it is made. Every value carries where it came from.
- **A replayable graded task.**
  - The contract is the question, and it holds no answers.
  - The deterministic judge, at a frozen version, is the grader.
  - Anyone may attempt it: our agent, another agent, a rule-based method, an optimiser or a person.
  - An attempt hands in any geometry: STEP, or a closed surface mesh, with the process declared.
- **Judged by standards, compared with the literature.** Pass or fail comes from standards and guidelines. Published values form a plausibility band; a design inside the published range is the achievement.
- **Two entry points, one form.**
  - A requirement (package-level, or a given gear train).
  - Later, an existing part whose interfaces are measured.
  - Only the provenance of the values differs.

The first instance is Hofstetter et al. 2018's demonstration gearbox, made by aluminium high-pressure die casting. CadQuery builds only the machined core; the shell and the structure are generated in field space.

## 2. Scope of v0

| In v0 | Not in v0 (owner) |
|---|---|
| The schema below: every entry with its provenance, authority and kind | The load front-end that computes the derived values (GBX, gearbox domain) |
| Units and frames | The core template, the design domain and keep-outs (GEO, geometry) |
| The contract's three stages: posed, derived, frozen | The judge and the verdict's computation (PHY, physics and the judge) |
| The validator, refusing with the rule and the entry | The task and attempt store; recording the engineer's accept and reject choices (DAT, data) |
| Canonical serialisation and its hash | The bound, which needs topology optimisation (OPT) |
| Example contracts as checks: three accepted, five or more refused | Fatigue, bolted joints, sealing, thermal, park lock, forced response (later phases) |

**Dependency:** PLT-2 (Python project, venv, checks, CI) comes first. CON-1 is the first code in it.

## 3. Every entry: value, provenance, authority, kind

Every value in the contract is an entry with four things.

| Field | Values | Meaning |
|---|---|---|
| **Value** | a quantity with its unit, a choice, or a reference | units from a fixed list, converted on read (§5) |
| **Provenance** | `published` (citation: document, table or page) · `standard` (standard and clause) · `measured` (a part and a face; for the later entry point) · `derived` (tool, tool version, input hash) · `assumption` (its entry in the assumptions list) · `engineer` (who, when) | where the value came from. Nothing is entered without one |
| **Authority** | `engineer_locked` · `agent_bounded` (with its range) · `agent_free` | who may change it. At L1 every interface is engineer-locked |
| **Kind** | `hard` · `soft` · `derived` | hard must hold; soft is a preference; derived is computed, never typed |

**The rule:** a `derived` value is written only by its versioned tool. A person or an agent may ask for a re-derivation with a changed input they have authority over, but never writes the value.

## 4. The layers

### 4.1 Task

| Entry | v0 content |
|---|---|
| Task id and title | e.g. `hofstetter2018-l1-hpdc` |
| Family | "two-stage parallel-axis helical reducer with integrated differential" (Hofstetter 2018) |
| Level | L1 (fixed interfaces) |
| Requirement style | `package` (ratio, offset, duty, life, package) or `gear_train` (given) |
| Priorities, in words | e.g. "alignment before a small mass saving", turned into soft objectives and confirmed by the engineer |
| Budget | FE proofs and wall-clock time per attempt |
| Verdict rule version | the rule set and scoring rule this task is graded with, fixed before any attempt (plan §11.2) |

### 4.2 Requirement (the engineer's input)

| Entry | Hofstetter 2018 (first instance) | Provenance |
|---|---|---|
| Total centre distance (input to output) | 165 mm | published, Table 2 ("Total center distance"). Read as the straight-line offset between the input and output axes: the paper's requirement b, "(range of) offset between input- and output shaft", with the intermediate shaft off that line. This reading is to be checked against the paper's Fig. 4 before the first derivation |
| Total ratio | 9.32 ± 1 % | published, Table 2 |
| Input torque | 366 N·m, **nominal**, at the input shaft | published, Table 2 |
| Peak drive, peak regeneration and reverse torques | 366 N·m each; regeneration and reverse with reversed sign | **assumption A1**: the paper gives only the nominal torque |
| Maximum input speed | 15,000 rpm | published, Table 2 |
| Service life, load spectrum | 944 h; the spectrum itself is not published | published, Table 2; the spectrum is not needed in v0 |
| Gear and shaft material | 20MnCr5 | published, Table 2 |
| Bearings | Benchmark set: input 6206 and NU205-E; intermediate 32010 pair; differential 6012 and 6011 | published, Table 3. The row alignment of the extracted table is to be checked against the PDF before use |
| Gear quality grade | N6 | **assumption A2** |
| Installation space | The layout's envelope grown by a clearance of 20 mm | **assumption A3**: the paper shows the space only as a figure |
| Process | aluminium high-pressure die casting | engineer, 8 Oct (D3 re-taken) |

**Which torque and which speed.** Every torque and speed names its shaft and its kind (peak, nominal, continuous, maximum). The validator refuses one without them.

**The second style.** A `gear_train` contract (way 2, as in the agricultural EV gearbox) also gives the tooth numbers, modules, pressure and helix angles, helix hands, face widths, profile shifts and centre distances. These are taken as given rather than derived.

### 4.3 Functional interfaces (fixed at L1)

The machined core that CadQuery builds. In the `package` style, the front-end derives the positions from the layout; they are then locked. Kinds are named by geometry, and domain roles live in data (CLAUDE.md).

| Interface kind | Entries |
|---|---|
| Cylindrical seat | frame (origin and axis), diameter, width, shoulder side, machining stock, fit and form tolerances, the bearing it hosts |
| Split face | plane; the bolt pattern (pitch circle or point list, count, hole diameter); the sealing line |
| Mount pad | position, normal, bolt pattern, the stated mount stiffness or "fixed" |
| Motor flange | spigot diameter, face, bolt pattern |
| Port | position, axis, diameter, role (fill, drain, breather) |

**Supports for the verdict, assumption A4.** The motor flange is clamped, and one torque-reaction mount pad is fixed. That follows GHE §1.9's case of a gearbox bolted to its motor. Hofstetter's unit integrates the motor, so the real mount scheme is not published.

### 4.4 Physics cases (derived, stamped)

Written by the front-end (GBX), each with its tool, version and input hash.
- **Load cases:** peak drive, peak regeneration, reverse. For each:
  - the force vector at every seat, in the contract's frame;
  - the reactions the supports carry.
- **Excitation:** gear-mesh orders and frequencies from the tooth counts over 0-15,000 rpm input. The order-separation check uses check speeds of 7,500 and 15,000 rpm input (**assumption A5**: half and full of the maximum, since no duty spectrum is published). All crossings are reported over the full range.

### 4.5 Limits and the verdict rule

The defaults come from the requirements catalogue (§1), each labelled. The engineer may override any of them.

| Check | v0 default | Source |
|---|---|---|
| Per-mesh misalignment from the housing, in and out of the plane of the axes, per face width | **Half** of the JGMA 1102-01 parallelism tolerance for the grade and the derived gear size. For N6, d 50-125 mm, b 20-40 mm: 3.0 µm out of plane, 6.0 µm in plane | standard (JGMA via KHK); the half is **assumption A6** |
| Bearing tilt, per seat | The lower end of Shigley's ranges, by bearing type: tapered 0.5 mrad, cylindrical 0.8 mrad, deep-groove ball 1.0 mrad | guideline (Shigley Table 7-2), lower end chosen |
| Centre-distance change, per stage | Half of ±fa: ±10 µm (50-125 mm) or ±13 µm (125-280 mm) at N5-N6 | standard (JGMA 1101-01); the half is A6 |
| Seat ovalisation | Half of IT5 for the bore size | standard (ISO 286-1 via JTEKT); the half is A6 |
| Order separation | Every housing mode at least 3 % from every gear-mesh order at the check speeds; the supports' boundary conditions stated | guideline (Marano et al. 2021) |
| Model margin | Every hard limit met with 25 % to spare | evidence: model to test 10-25 % (Gutierrez Santiago 2023; FZG 2022); 25 % is the top of the range |
| Manufacturing | The profile's rules pass on the built geometry (§4.6) | standard (NADCA 2015) |
| Package | No violating volume | Hofstetter 2018's measure |
| Mass | Computed from the geometry; the objective is the least mass among passing designs | - |
| Stress | Recorded, not judged in v0, until the engineer sets the safety factor (no source yet) | - |

**The tolerance tables.**
- GHE quotes only two N6 rows of JGMA 1102-01 (via KHK) and the ±fa rows of JGMA 1101-01.
- The full tables are read from KHK's page before the limits code is written, so that any derived gear size finds its row.
- A size outside the tables is refused, not extrapolated.

**The scoring rule, fixed before any attempt.** An attempt passes when every hard check passes with the margin. Among passing attempts, less mass is better. A difference inside the measured mesh noise is a tie (plan §11.2).

### 4.6 Manufacturing profile: aluminium high-pressure die casting

| Rule | v0 value | Source |
|---|---|---|
| Pull direction | Normal to the split face, one per housing part (main housing, cover) | **assumption A7** |
| Draft | At least 2° on inside surfaces and 1° on outside surfaces, for features at least 25.4 mm deep | standard (NADCA 2015, §4A) |
| No undercuts | Every surface reachable along its part's pull direction | follows from the pull direction |
| Minimum wall | 4 mm | D7 (least member): the FE budget on this laptop. NADCA allows thinner |
| Maximum wall | Not enforced in v0. The thickness map is recorded | no sourced value yet |
| Machining stock | At least 0.25 mm on every machined face | standard (NADCA 2015: "normal minimum machining allowance") |
| As-cast faces | Sealing faces and bores machined | standard (NADCA as-cast flatness 0.20 mm plus 0.08 mm per extra 25.4 mm) |
| Alloy property card | E 70.93 GPa, ν 0.3135, ρ 2,660 kg/m³ | published: Kim et al. 2024, Table 3, an aluminium gearbox housing's card updated against a modal test. The die-casting alloy of e-drive housings is not confirmed (GHE §2) |

### 4.7 Published reference band

Each entry holds the source, the quantity, its value or range, the conditions it was measured or computed under, and its confidence. These are not limits. Each defines a **comparison case** the judge can run under the paper's conditions.

| Source | Quantity | Value | Conditions | Status |
|---|---|---|---|---|
| Kim 2024; Son 2019 | Housing mass; housing modes | 4.836 kg; 1,352.7-2,939.0 Hz | 7 kW, ratio 12.4, two-stage; modal test, free-free | read by subagents |
| Jäger & Linde 2025 | Mass; rotational deformation; first mode | 8.41 kg; 9.34 µm; 1,294-1,408 Hz | planetary, 150 kW; fixed on one side, torque at the other | read |
| Marano et al. 2021 | First ten modes | 238-719 Hz | two-stage e-axle on its mountings | via GHE |
| Jixie chuandong 2021 | Bearing-hole displacement | 0.085 mm before, 0.07 mm after | two-speed EV housing | abstract only |

### 4.8 The assumptions list

Every value without a published or standard source is listed here, with its value, its reason and how the dataset may vary it. For the first instance:

| Id | Assumption | Value | Why | Varied later? |
|---|---|---|---|---|
| A1 | Peak drive, regeneration and reverse torques | = the nominal 366 N·m | only the nominal torque is published | yes |
| A2 | Gear quality grade | N6 | the grade sets the misalignment budget; none is published | yes |
| A3 | Installation space | the layout's envelope grown by 20 mm | the space is a figure only | yes |
| A4 | Supports | motor flange clamped, one torque-reaction pad fixed | the mount scheme is not published | yes |
| A5 | Order-check speeds | 7,500 and 15,000 rpm input | no duty spectrum is published | yes |
| A6 | The housing's share of each tolerance | half | no public source gives a share (GHE §1.2) | yes |
| A7 | Pull direction | normal to the split face | a two-part housing drawn from its split | yes |

## 5. Units and frames

- **Units.** Each quantity carries a unit from a fixed list (mm, m; N, kN; N·m, N·mm; rpm, rad/s; MPa, GPa; kg, g, kg/m³; µm; mrad, deg; h, s; Hz). It is converted on read to the canonical set: mm, N, s, MPa, tonne. A value without a unit is refused.
- **Frame.** One right-handed frame per contract, stated in it. The default origin is the input shaft's axis on the split face, with +z along the input shaft, pointing away from the motor.

## 6. The three stages of a contract

1. **Posed:** the task, the requirement, the process and the limits are filled. In the `package` style the interfaces and physics cases are empty.
2. **Derived:** the front-end has filled the interfaces (for `package`) and the physics cases, each stamped.
3. **Frozen:** validated, serialised canonically and hashed. Only a frozen contract is a task. A changed value gives a new contract with a new hash.

## 7. The validator

Each refusal names its rule and the entry, and gives the reason.

1. **Schema:** required entries; types; units from the list; bounds (diameters and lengths positive, a ratio above 1, angles in range).
2. **Provenance:**
   - every entry has one;
   - a `derived` entry has a tool, a version and an input hash;
   - an `assumption` entry points into the assumptions list;
   - no entry is both hard and derived-without-stamp.
3. **Consistency:**
   - P = T·ω where a power is given;
   - the product of the stage ratios against the total ratio, within its tolerance;
   - each stage's centre distance against its gears' pitch diameters and profile shift;
   - the two stages able to reach the input-to-output offset: |a1 − a2| ≤ offset ≤ a1 + a2;
   - each bearing's outside diameter against its seat;
   - every seat and port inside the installation space;
   - interfaces not overlapping;
   - frames orthonormal;
   - tooth numbers present wherever orders are asked for.
4. **Task hygiene:**
   - no result, design or reference inside the contract (answers forbidden);
   - the verdict rule version present;
   - the stage stated, and a frozen contract's hash matching its content.

Not in v0: the bound (needs OPT, topology optimisation); checks on a design (the judge's).

## 8. Checks that say v0 is done

- **Accepted (3):**
  1. **Hofstetter 2018, `package` style, posed.**
  2. **The agricultural EV gearbox, `gear_train` style, posed.** Values from Kim 2024 Table 1; the assumptions are listed.
  3. **A small textbook case, derived.** JTEKT's worked example: one gear between two bearings, the derived seat loads entered with a `manual-1` tool stamp. This exercises the derived stage.
- **Refused, each with its reason (5 or more):**
  - a quantity without a unit;
  - a torque without its shaft or kind;
  - a total ratio that the stages do not give;
  - a seat outside the installation space;
  - a derived value without a tool stamp;
  - a contract carrying a result field.
- **Stable hash:** a frozen contract's hash is unchanged by re-serialisation, and changes with any value.
- **Clean data:** the example files are licence-clean: published values with their citations, assumptions labelled, nothing from GRC.

## 9. Building it (for the implementation plan)

- **Code:**
  - `src/zenryx/contract/`: the models in pydantic v2, as fastcae's typed entities were;
  - the unit table and converter;
  - the validator;
  - canonical JSON and its SHA-256 hash.
- **Checks:** `checks/contract/`, with the example contracts in `checks/data/contracts/`.
- **Order:** PLT-2 (Python project, venv, checks, CI), then CON-1. The front-end (GBX) and the core template (GEO) come next and fill the derived stage.
