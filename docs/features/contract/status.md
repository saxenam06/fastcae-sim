# Contract

The design contract is the question the factory designs to: what must be connected, what loads pass through it, what must hold, and how it is made.

Its typed schema is `HousingDesignSpec`. Every value in it is an entry with four parts:
- a **value**, with its unit;
- a **provenance**: published, standard, measured, derived, an assumption, or the engineer's;
- an **authority**: engineer-locked, agent-bounded with its range, or agent-free;
- a **kind**: hard, soft or derived.

The validator refuses a fault with its rule, the entry and the reason. A frozen contract carries its own hash and is a replayable graded task. The dataset generator, the agent's state, the physics interface and the records all derive from it.

**PBI key:** CON · **State:** CON-1 (contract schema v0) works locally: its checks pass, including the example contracts. Committed in f51aba1. CON-3 (the Ivanov 2018 contract) is written and posed: the product's one contract. Committed in 840c486 and 9acf466. All on `product/end-to-end`, not pushed, and not yet reviewed by the engineer. The involute module gives the whole mesh geometry since 22:46 (PLT-7, uncommitted). Since 22:57 an input is only what can be chosen freely (Decisions). The helix angles stay 30° (23:23). Proposed, waiting on the engineer: the paper's figures out of the contract and the validator (Open) · **Updated:** 2026-10-08 23:29 by Claude
**Code:** `src/zenryx/contract/` (`units.py`, `entry.py`, `model.py`, `canonical.py`, `involute.py`, `train.py`, `validate.py`); checks in `checks/contract/`; example contracts in `checks/data/contracts/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| CON-1 | `HousingDesignSpec` v0: its layers, entries with provenance, authority and kind; units and frames; derived values stamped; the three stages; the validator; the canonical hash | Claude · LAPTOP-IR8VEG53 · `product/end-to-end`, the one branch for now | 2026-10-08 02:15 | **Done locally, against the spec's §8.** It accepts the three example contracts and refuses more than five broken ones, each with its rule. The hash is stable and changes with any value. The examples are licence-clean. **Committed in f51aba1** (not pushed). **Left:** the engineer's review of the spec and the code |
| CON-3 | The Ivanov 2018 contract, posed: Ivanov's gear train and duty, the gaps filled from the best sources, each labelled. Plan: [2026-10-08-plan-ivanov2018-contract.md](2026-10-08-plan-ivanov2018-contract.md). Done when the validator accepts `ivanov2018_posed.json`, every value has its source, its assumptions are listed, and the snapshot and the UI show it | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-08 19:37 | **Done locally, 20:00.** `checks/data/contracts/ivanov2018_posed.json`: the validator accepts it, the centre distances check at a 30° helix, its assumptions are A1-A12, and it is the UI's one contract. **Committed in 840c486 (the gear-train kinematics) and 9acf466 (the contract and its page)**, not pushed. **Left, the engineer's:** the process (A10, sand casting proposed) and the first packaging (A9, 165 mm proposed); both show on the page as pre-selected inputs. Deriving and freezing it is GBX-4 |

## Next

| PBI | Goal | Done when |
|---|---|---|
| CON-2 | Check the example contracts' open points: (1) the bearings' ISO 15 dimensions against a maker's catalogue; (2) Hofstetter's "Total center distance" read as the offset, against the paper's Fig. 4; (3) A8, which bearing sits in the main housing | Each is confirmed or corrected, with its source |

## What runs

- **Load and validate:** `zenryx.contract.validate.load_and_validate(path_or_json_or_dict)` returns `(spec, refusals)`. Each `Refusal` has a `rule`, an `entry` (the dotted path) and a `reason`. The rules:
  - **`schema`:** pydantic's errors. Units are from the fixed list; extra fields are refused, so no answers can be smuggled in; a bare number is not a value; a torque must name its shaft and kind.
  - **`provenance.assumption_listed`.**
  - **`stage.posed`, `stage.derived_needs_physics`, `stage.physics_is_derived`, `stage.frozen_hash`.**
  - **`consistency.*`:**
    - `dimension`: every entry in its quantity's unit;
    - `shape`: positions, directions and forces are vectors; every other quantity is a single value;
    - `ratio`: the stages' tooth ratios give the total ratio, within its tolerance;
    - `centre_distance`: the working centre distance with profile shift, within 0.1 mm;
    - `offset`: |a1 − a2| ≤ offset ≤ a1 + a2;
    - `seat_inside_space`;
    - `power`: P = T·ω within 2 %;
    - `unique_names`;
    - `seat_reference`;
    - `unit_vector`;
    - `bearing_seat`: the bearing's outside diameter against its seat;
    - `tilt_limit`: every bearing type in the contract has a tilt limit, since the judge needs one per seat.
- **Units** (`units.py`):
  - Every quantity is kept as written and read in canonical units (mm, N, N*mm, s, MPa, t/mm3, rad, rad/s, Hz, W, kg, 1/K, 1).
  - One alias table: Nm, N*m, um, kg/m3, um/(m.K) and so on.
  - Anything else is refused, with the list of allowed units.
- **The hash** (`canonical.py`):
  - SHA-256 over canonical JSON: sorted keys, canonical units, 12 significant digits, the hash excluded.
  - `freeze()` sets the stage to frozen and stamps the hash.
  - A posed contract cannot be frozen into a valid task until it has been derived.
- **The mesh geometry** (`involute.py`, since 22:46 with PLT-7): `mesh_geometry()` gives a shifted helical pair's transverse and working pressure angles, its reference, base and working pitch diameters, and the working centre distance. The validator's centre-distance rule and the contract page's step 1 both use it; GBX-1's forces will start from it.
- **The gear train** (`train.py`): the total ratio, the shaft speeds, each mesh's frequency (teeth × rpm / 60), and the angle between the two stages that a packaging offset fixes (law of cosines; an offset out of reach is refused).
- **The example contracts** (`checks/data/contracts/`, written by `make_examples.py`; see its README):
  - **Ivanov 2018, gear-train style, posed: the first contract** (CON-3). Its gear train and duty as published; the gaps filled from the best sources, each labelled; assumptions A1-A12;
  - Hofstetter et al. 2018, package style, posed: the second;
  - the agricultural EV gearbox of Kim et al. 2024, gear-train style, posed;
  - a textbook gear between two bearings, derived. Its two bearing designations rest on assumption A2 ("two 6206"). Until 11:45 on 8 October they were marked published, citing "chosen for the example (A2)". The UI's Sources page (PLT-4, the web UI) showed A2 with no entry pointing to it, and they were corrected.
- **The UI shows one contract, Ivanov 2018,** through `zenryx.api.snapshot` and its page model `zenryx.api.contract_page` (PLT-6). The other three stay as examples for the checks. Each input's short source is shown beside it, which is where a slip like the one above shows: a citation that is really an assumption, or an assumption no entry uses.

## Rules in force

- A derived value is stamped with its tool, version and input hash. The agent may ask for it to be computed again, but never writes it.
- Every torque and speed names its shaft and its kind.
- Every value carries its source; every assumption is listed with why.
- A contract holds no answers: extra fields are refused, and results live outside the contract.

## Measured

- The checks pass: units 17, entries 9, model 11, hash 7, involute 8, train 9, validator 23, examples 17 (101 for the contract), with environment 10 and the snapshot's 22 beside them (133 in all, 1.9 s; 8 October 22:46).
- Ivanov's mesh geometry: working pressure angles 23.566° (stage 1) and 22.824° (stage 2), from the 18° normal pressure angle, the 30° helix and the profile shifts.
- Ivanov's published centre distances follow from its teeth, modules, pressure angle and profile shifts at a 30° helix: 82.917 mm against 83 mm, and 125.04 mm against 125 mm, both within the validator's 0.1 mm.
- The agricultural gearbox's published centre distances follow from its published teeth, module, angles and profile shifts: 56.94 mm against 57 mm, and 96.99 mm against 97 mm. This also confirms the subagent's reading of Kim et al. 2024 Table 1, re-read from the PDF.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| Every problem is a replayable graded task | The data record is designed so each root problem can be replayed later as a graded task. The contract is the question, with no answers in it; the deterministic judge, at a frozen version, is the grader. Anyone can attempt it: our agent, another agent, a rule-based method, an optimiser or a person. The same grader version always gives the same grade. The record keeps the references (the bound, the best designs so far with their grades) and every attempt (its trajectory, its design, its grade). It serves our own models and AI labs alike | 2026-10-08 01:25, the engineer |
| What an attempt hands in | **Any geometry**: a STEP file, or a closed surface mesh for printed organic shapes. With it comes a declaration of the process and, for printing, the build direction. Our own recipe (core values plus members) is optional and helps our own learning. The grader checks that the interfaces sit where the contract says, checks the process rules, then meshes, solves and grades. A file that cannot be meshed fails its attempt with a reason; it never breaks the grader. It is the same build, mesh and solve chain fastcae ran | 2026-10-08 01:32, the engineer |
| The first contract and its process | Hofstetter et al. 2018 (Tables 2 and 3); aluminium high-pressure die casting with NADCA's rules; CadQuery for the machined core only, the shell and structure in field space (product page). **The first contract is replaced at 19:37 (below). The process is being taken again with the product's other decisions (the engineer, 19:43); A10 proposes sand casting** | 2026-10-08 02:02, the engineer |
| **The first contract: Ivanov 2018** | Ivanov's gear train and duty as published (KTH thesis for AVL); the gaps filled from the best sources, each labelled ([plan](2026-10-08-plan-ivanov2018-contract.md)). Hofstetter 2018 becomes the second contract | 2026-10-08 19:37, the engineer |
| The maximum input speed | From a vehicle top speed on Ivanov's 245/45 R19 tyre: 160 km/h, about 8,670 rpm, as proposed (B3) | 2026-10-08 19:37, the engineer |
| **Packaging is the user's input** | The input-output offset (motor shaft to axle) is a packaging input the engineer gives, not our assumption. With Ivanov's two centre distances (83 and 125 mm) it fixes the shafts' angle. Each packaging choice is its own contract, so a set of them shows how the structure follows the package. The validator already checks that an offset is reachable (consistency.offset) | 2026-10-08 19:43, the engineer |
| Working without the originals | The engineer cannot get Ivanov's original or Brauer 2017. The contract is written from the copy read, with moderate confidence. Stage 2's helix angle stays as recovered (30°, B6) and the bearing sizes come from our life calculation (B7) | 2026-10-08 19:43, the engineer |
| **An input is only what can be chosen freely** | Anything the other inputs fix is a step's output, not an input: the centre distance (fixed by the teeth, module, pressure angle, helix angle and profile shifts) and the ratio (fixed by the teeth). A published figure for it stays in the contract only for the validator's check (Ivanov's 83 / 125 mm and 7.184), off the page: the page shows what the user brings and what the tools work out (the engineer, 23:15). A material's properties come with the material. Shown so on the contract page (PLT-7) | 2026-10-08 22:57 and 23:15, the engineer |
| The helix angles | 30° on both stages, as read (stage 2's is A7). The housing's centre distances are therefore the calculated 82.917 and 125.037 mm | 2026-10-08 23:23, the engineer |
| Values borrowed from Hofstetter 2018 | Its bearing arrangement as a pattern (B7: ball + cylindrical roller on the input, a tapered pair on the intermediate, a ball pair on the output; sizes chosen from Ivanov's own loads) and its 944 h service life (B4), each labelled as borrowed | 2026-10-08 19:37, the engineer |

## Open

- **The spec and the code await the engineer's review:** [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md).
- **The first contract's assumptions are the engineer's to change:** A1-A12 in `ivanov2018_posed.json`, the packaging (A9) and the process (A10) first. The second contract's are A1-A8 in `hofstetter2018_posed.json`.
- **A paper's figures out of the contract, proposed** (the engineer, 23:23: users bring their own requirements, and no paper will exist for most of them).
  - The paper's numbers verify the tools once, in `checks/`: Ivanov's 83 / 125 mm in `test_involute.py`. Not in every contract.
  - So: drop the centre distances and the ratio from the gear-train contracts (Ivanov, Kim). The ratio stays only where it is the requirement, with no teeth given (Hofstetter's package style); `total_ratio` becomes optional.
  - Replace the validator's paper-agreement rules (`consistency.centre_distance`, `consistency.ratio`) with one that refuses a redundant input: a centre distance the gear data fix, or a ratio the teeth fix. `consistency.offset` stays, since it checks whether the user's packaging can be reached.
  - A contract-format change: waiting on the engineer's word.
- **The order-check speeds copy the duty's speeds.** `limits.order_check_speeds` holds 6,000 and 8,673 rpm again, apart from the rated and maximum input speeds. A changed maximum speed would leave the criterion behind. Proposed: the criterion names the duty's speeds instead of copying them (a contract-format change, so the engineer's).
- **The stress safety factor has no source yet.** Stress is recorded, not judged, in v0.
- **The rule-based arm, proposed** (plan §11.1): Maciejczyk and Zdziennicki's gear-case rules (TU Łódź 2011, Chapter 9).
  - They give the walls, bosses, flanges and bolts from the centre distance and the bearing bores, so they are the conventional design the agent must beat.
  - Their 7.5 mm floor is for sand casting. Under die casting, the contract's least wall would replace it.
  - Not built.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md): the spec of CON-1.
- [2026-10-08-plan-contract-v0-and-first-variant.md](2026-10-08-plan-contract-v0-and-first-variant.md): the implementation plan, Tasks 1-11.
- [requirements-catalogue.md](requirements-catalogue.md): what engineers ask of a housing (15 questions), the inputs a user gives, what the tools derive, the load cases and the gaps, each row with its source.
- The plan of record, section 4 (the contract): [plan.md](../product/plan.md).
