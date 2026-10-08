# Contract

The design contract is the question the factory designs to: what must be connected, what loads pass through it, what must hold, and how it is made.

Its typed schema is `HousingDesignSpec`. Every value in it is an entry with four parts:
- a **value**, with its unit;
- a **provenance**: published, standard, measured, derived, an assumption, or the engineer's;
- an **authority**: engineer-locked, agent-bounded with its range, or agent-free;
- a **kind**: hard, soft or derived.

The validator refuses a fault with its rule, the entry and the reason. A frozen contract carries its own hash and is a replayable graded task. The dataset generator, the agent's state, the physics interface and the records all derive from it.

**PBI key:** CON · **State:** CON-1 (contract schema v0) works locally: its checks pass, including the three example contracts. Not committed, and not yet reviewed by the engineer · **Updated:** 2026-10-08 11:48 by Claude
**Code:** `src/zenryx/contract/` (`units.py`, `entry.py`, `model.py`, `canonical.py`, `involute.py`, `validate.py`); checks in `checks/contract/`; example contracts in `checks/data/contracts/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| CON-1 | `HousingDesignSpec` v0: its layers, entries with provenance, authority and kind; units and frames; derived values stamped; the three stages; the validator; the canonical hash | Claude · LAPTOP-IR8VEG53 · `product/end-to-end`, the one branch for now (uncommitted) | 2026-10-08 02:15 | **Done locally, against the spec's §8.** It accepts the three example contracts and refuses more than five broken ones, each with its rule. The hash is stable and changes with any value. The examples are licence-clean. **Left:** the engineer's review of the spec and the code, then the commit |

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
- **The example contracts** (`checks/data/contracts/`, written by `make_examples.py`; see its README):
  - Hofstetter et al. 2018, package style, posed;
  - the agricultural EV gearbox of Kim et al. 2024, gear-train style, posed;
  - a textbook gear between two bearings, derived. Its two bearing designations rest on assumption A2 ("two 6206"). Until 11:45 on 8 October they were marked published, citing "chosen for the example (A2)". The UI's Sources page (PLT-4, the web UI) showed A2 with no entry pointing to it, and they were corrected.
- **The UI shows every contract** through `zenryx.api.snapshot` (PLT-4). Its Sources page is where a slip like the one above shows: a citation that is really an assumption, or an assumption no entry uses.

## Rules in force

- A derived value is stamped with its tool, version and input hash. The agent may ask for it to be computed again, but never writes it.
- Every torque and speed names its shaft and its kind.
- Every value carries its source; every assumption is listed with why.
- A contract holds no answers: extra fields are refused, and results live outside the contract.

## Measured

- The checks pass: units 17, entries 9, model 11, hash 7, involute 3, validator 23, examples 13, with environment 10 beside them (93), and the snapshot's 16 since PLT-4 (109 in all, 1.9 s).
- The agricultural gearbox's published centre distances follow from its published teeth, module, angles and profile shifts: 56.94 mm against 57 mm, and 96.99 mm against 97 mm. This also confirms the subagent's reading of Kim et al. 2024 Table 1, re-read from the PDF.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| Every problem is a replayable graded task | The data record is designed so each root problem can be replayed later as a graded task. The contract is the question, with no answers in it; the deterministic judge, at a frozen version, is the grader. Anyone can attempt it: our agent, another agent, a rule-based method, an optimiser or a person. The same grader version always gives the same grade. The record keeps the references (the bound, the best designs so far with their grades) and every attempt (its trajectory, its design, its grade). It serves our own models and AI labs alike | 2026-10-08 01:25, the engineer |
| What an attempt hands in | **Any geometry**: a STEP file, or a closed surface mesh for printed organic shapes. With it comes a declaration of the process and, for printing, the build direction. Our own recipe (core values plus members) is optional and helps our own learning. The grader checks that the interfaces sit where the contract says, checks the process rules, then meshes, solves and grades. A file that cannot be meshed fails its attempt with a reason; it never breaks the grader. It is the same build, mesh and solve chain fastcae ran | 2026-10-08 01:32, the engineer |
| The first contract and its process | Hofstetter et al. 2018 (Tables 2 and 3); aluminium high-pressure die casting with NADCA's rules; CadQuery for the machined core only, the shell and structure in field space (product page) | 2026-10-08 02:02, the engineer |

## Open

- **The spec and the code await the engineer's review:** [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md).
- **The first contract's assumptions are the engineer's to change:** A1-A8 in `hofstetter2018_posed.json`.
- **The stress safety factor has no source yet.** Stress is recorded, not judged, in v0.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md): the spec of CON-1.
- [2026-10-08-plan-contract-v0-and-first-variant.md](2026-10-08-plan-contract-v0-and-first-variant.md): the implementation plan, Tasks 1-11.
- [requirements-catalogue.md](requirements-catalogue.md): what engineers ask of a housing (15 questions), the inputs a user gives, what the tools derive, the load cases and the gaps, each row with its source.
- The plan of record, section 4 (the contract): [plan.md](../product/plan.md).
