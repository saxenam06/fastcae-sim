# Contract

The design contract is the question the factory designs to: what must be connected, what loads pass through it, what must hold, and how it is made.

Its typed schema is `HousingDesignSpec`. Every value in it is an entry with four parts:
- a **value**, with its unit;
- a **provenance**: published, standard, measured, derived, an assumption, or the engineer's;
- an **authority**: engineer-locked, agent-bounded with its range, or agent-free;
- a **kind**: hard, soft or derived.

The validator refuses a fault with its rule, the entry and the reason. A frozen contract carries its own hash and is a replayable graded task. The dataset generator, the agent's state, the physics interface and the records all derive from it.

**PBI key:** CON · **State:** CON-1 (contract schema v0) works locally, committed in f51aba1; the engineer's review is left. The product's contract is the **EV two-stage reducer** (`ev_reducer_posed.json`, CON-3 and CON-4): the engineer's requirements, what they leave open assumed with a reason and a bare reference, and no paper named (9 October 02:25). An input is only what can be chosen freely; papers verify the tools; the shaft layout (A13-A19) and one order-check speed are in. All on `product/end-to-end`, not pushed; committed in 577de20 · **Updated:** 2026-10-09 02:25 by Claude
**Code:** `src/zenryx/contract/` (`units.py`, `entry.py`, `model.py`, `canonical.py`, `involute.py`, `train.py`, `validate.py`); checks in `checks/contract/`; example contracts in `checks/data/contracts/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| CON-1 | `HousingDesignSpec` v0: its layers, entries with provenance, authority and kind; units and frames; derived values stamped; the three stages; the validator; the canonical hash | Claude · LAPTOP-IR8VEG53 · `product/end-to-end`, the one branch for now | 2026-10-08 02:15 | **Done locally, against the spec's §8.** It accepts the three example contracts and refuses more than five broken ones, each with its rule. The hash is stable and changes with any value. The examples are licence-clean. **Committed in f51aba1** (not pushed). **Left:** the engineer's review of the spec and the code |
| CON-3 | The product's first contract, posed: the EV reducer's gear train and duty, the gaps filled from the best sources, each labelled. Plan: [2026-10-08-plan-ivanov2018-contract.md](2026-10-08-plan-ivanov2018-contract.md). Done when the validator accepts the contract (`ev_reducer_posed.json` since CON-4), every value has its source, its assumptions are listed, and the snapshot and the UI show it | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-08 19:37 | **Done locally, 20:00.** `checks/data/contracts/ev_reducer_posed.json`: the validator accepts it, the centre distances check at a 30° helix, its assumptions are A2-A6, A8 and A11-A19 (A1 went with the ratio at 23:37; A7, A9 and A10 became the engineer's at 23:23 and 02:12; A13-A19 are the layout's gaps, sealed ends and least clearances), and it is the UI's one contract. **Committed in 840c486 (the gear-train kinematics) and 9acf466 (the contract and its page)**, not pushed. The process (sand casting) and the first packaging (165 mm) were taken by the engineer on 9 October 02:12. Completing and freezing it is GBX-4 |
| CON-4 | **The product's contract names no paper** (the engineer, 9 October 01:54): named "EV two-stage reducer"; its requirements the engineer's ("you" on the page); each assumption a reason and a bare reference, never a statement about an author; the example's origin in this page only. Done when the contract and its page name no paper, a check says so, and the UI shows it | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-09 02:20 | **Done locally, 02:25.** `make_examples.ev_reducer_posed()` writes `ev_reducer_posed.json` (renamed with `git mv`); `test_the_product_contract_names_no_paper` checks the contract and its page for the source's names and every assumption for pronouns; 151 checks pass; the page looked at in a screenshot (every requirement reads "you"). **Committed in 577de20** |

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
    - `redundant`: no input is one the other inputs fix. Full gear data (teeth, module, pressure angle, helix angle, both shifts) fix a stage's centre distance, so it is refused beside them; the teeth fix the ratio, so it is refused beside them; and a ratio tolerance with no ratio is refused;
    - `ratio`: where the teeth are not given, the ratio is;
    - `offset`: |a1 − a2| ≤ offset ≤ a1 + a2, each centre distance calculated where the gear data fix it;
    - `seat_inside_space`;
    - `power`: P = T·ω within 2 %;
    - `unique_names`;
    - `seat_reference`;
    - `speed_reference`: the order check names a speed kind the duty gives (rated, maximum);
    - `shaft_reference`: each sealed shaft end names a stage's shaft (input, intermediate, output) and a side, −z or +z;
    - `rotation`: the input's sense of rotation in forward drive is +z or −z;
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
  - A posed contract cannot be frozen into a valid task until it has been completed.
- **The mesh geometry** (`involute.py`, since 22:46 with PLT-7): `mesh_geometry()` gives a shifted helical pair's transverse and working pressure angles, its reference, base, working pitch and tip diameters (da = d + 2mn(1 + x)), and the working centre distance. The validator's centre-distance rule and the contract page's steps 1 and 3 use it; GBX-1's forces will start from it.
- **The shaft layout** (`requirement.shaft_layout`, since 9 Oct 00:06; completed 01:06): the inputs from which the load tool places the gears and bearings along each shaft. All lengths are in mm (`consistency.dimension`):
  - the gaps: bearing to gear, behind a bearing in a closed bore, and between two gears on one shaft;
  - the space behind a bearing where its shaft leaves the housing, for a seal and its seat, with the shaft ends that leave (`sealed_ends`: a shaft and a side);
  - the least clearances: along the shafts, between parts on different shafts that overlap seen end-on, and from a gear's tips to the wall.

  The EV reducer's contract assumes them, each labelled: A13 and A14 from Shigley Ch. 18, Fig. 18-2; A15 12.7 mm (no source yet); A16 a radial shaft seal's width; A17 its three sealed ends; A18 3 mm (no source yet); A19 8.25 mm from Maciejczyk & Zdziennicki Ch. 9, Fig. 9.1, (1.1-1.2)·δ.
- **The stages** are posed (the user's requirements), completed (the load tool's results written in, GBX-4) and frozen (hashed: the task). "Completed" replaced "derived" on 9 October 03:05 (the engineer's word, 01:54); a tool's value keeps the provenance kind "derived" and reads "calculated" on the UI. Rule `stage.completed_needs_physics`.
- **New inputs for the load tool and the judge** (9 October): the input's forward rotation (A21); the bearing arrangement bearing by bearing, the side stage 1 meshes on (A22) and a carrier for the differential (A23) in `shaft_layout`; the shafts' steel (A24); the mounts and the motor flange (`requirement.mounts`, `requirement.motor_flange`; their values come with LOP-1). A completed seat names its bearing and type; a load case carries the motor's reaction on its flange (`interface_moments`).
- **The order check** (`limits.order_check_at`, since 9 Oct 01:06): it names one of the duty's speeds by its kind instead of copying its value, so a changed duty speed carries the criterion with it. The EV reducer's is the rated 6,000 rpm (the engineer).
- **The gear train** (`train.py`):
  - the total ratio, the shaft speeds, and each mesh's frequency (teeth × rpm / 60);
  - the angle between the two stages that a packaging offset fixes (law of cosines; an offset out of reach is refused);
  - the axes' positions in the end view (`axis_positions`), and how far two circles on different shafts overlap seen along the shafts (`end_view_overlap`). The EV reducer's stage-1 gear and output gear overlap by 31.4 mm.
- **The example contracts** (`checks/data/contracts/`, written by `make_examples.py`; see its README):
  - **The EV two-stage reducer, gear-train style, posed: the product's contract** (CON-3, CON-4). The engineer's requirements; what they leave open assumed and listed (A2-A6, A8, A11-A19); no paper named;
  - Hofstetter et al. 2018, package style, posed: the second;
  - the agricultural EV gearbox of Kim et al. 2024, gear-train style, posed;
  - a textbook gear between two bearings, derived. Its two bearing designations rest on assumption A2 ("two 6206"). Until 11:45 on 8 October they were marked published, citing "chosen for the example (A2)". The UI's Sources page (PLT-4, the web UI) showed A2 with no entry pointing to it, and they were corrected.
- **The UI shows one contract, the EV two-stage reducer,** through `zenryx.api.snapshot` and its page model `zenryx.api.contract_page` (PLT-6). The other three stay as examples for the checks. Each input's short source is shown beside it, which is where a slip like the one above shows: a citation that is really an assumption, or an assumption no entry uses.

## Rules in force

- A derived value is stamped with its tool, version and input hash. The agent may ask for it to be computed again, but never writes it.
- Every torque and speed names its shaft and its kind.
- Every value carries its source; every assumption is listed with why.
- A contract holds no answers: extra fields are refused, and results live outside the contract.

## Measured

- The checks pass: units 17, entries 9, model 11, hash 7, involute 10, train 12, validator 29, examples 17 (112 for the contract), with environment 10 and the snapshot's 28 beside them (150 in all, 1.9 s; 9 October 01:18).
- The EV reducer's tip diameters: 58.72 / 114.76 mm (stage 1) and 60.31 / 198.17 mm (stage 2). Seen along the shafts, the stage-1 gear (on the intermediate shaft) and the output gear overlap by 31.4 mm, so they must clear each other along the shafts (A18's 3 mm at least).
- The papers verify the tools: Ivanov's 83 / 125 mm and Kim's 57 / 97 mm are met within 0.1 mm by `mesh_geometry`; their ratios 7.184 and 12.37 within 0.1 % by `train.ratio`.
- The EV reducer's mesh geometry: working pressure angles 23.566° (stage 1) and 22.824° (stage 2), from the 18° normal pressure angle, the 30° helix and the profile shifts.
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
| **A paper's figures verify the tools, not each contract** | Users bring their own requirements, and most will have no paper. So the papers check the tools once, in `checks/`: Ivanov's and Kim's centre distances in `test_involute.py`, their ratios in `test_train.py`. The gear-train contracts (Ivanov, Kim, the textbook example) carry no centre distance their gear data fix and no ratio their teeth fix. `total_ratio` is optional and stays only where it is the requirement (Hofstetter's package style). The validator's paper-agreement rules give way to `consistency.redundant`, which refuses such an input | 2026-10-08 23:37, the engineer |
| The helix angles | 30° on both stages, as read (stage 2's is A7). The housing's centre distances are therefore the calculated 82.917 and 125.037 mm | 2026-10-08 23:23, the engineer |
| **One order-check speed: the rated 6,000 rpm** | The gear orders are checked at one speed, the cruise. The criterion names the duty's speed by its kind (`limits.order_check_at: rated`) instead of copying 6,000 and 8,673 rpm, so it follows the duty. The duty's own 8,673 rpm maximum (19:37) is untouched | 2026-10-09 01:06, the engineer |
| **The seal allowance per shaft end, and the clearances calculated** | Before GBX-1 (gear forces): a bearing where its shaft leaves the housing has the seal's space behind it (A16, 11 mm), on the ends the contract names (A17: input −z, output −z and +z); the intermediate's bores are closed. The least clearances are inputs (A18 along the shafts, A19 from the tips to the wall), and step 5 calculates every clearance from the layout and checks it against them, instead of assuming one | 2026-10-09 01:06, the engineer |
| **The product's contract names no paper** | The contract is named for what it is, the "EV two-stage reducer", and its requirements are the engineer's. Standards stay as sources; an assumption that comes from an author gives the reference only (author, year, figure), with no statement about the author. The example's origin is named in the docs, not on the UI. Papers keep verifying the tools in `checks/` | 2026-10-09 01:54, the engineer |
| **The packaging and the process for the first loop** | The 165 mm input-output offset and sand casting in printed sand moulds, taken as the engineer's (they were A9 and A10) | 2026-10-09 02:12, the engineer |
| Values borrowed from Hofstetter 2018 | Its bearing arrangement as a pattern (B7: ball + cylindrical roller on the input, a tapered pair on the intermediate, a ball pair on the output; sizes chosen from Ivanov's own loads) and its 944 h service life (B4), each labelled as borrowed | 2026-10-08 19:37, the engineer |

## Open

- **The spec and the code await the engineer's review:** [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md).
- **The product contract's assumptions are the engineer's to change:** A2-A6, A8 and A11-A19 in `ev_reducer_posed.json`. The second contract's are A1-A8 in `hofstetter2018_posed.json`.
- **Two layout values have no source yet:** A15, the gap between the intermediate's two gears (12.7 mm, taken as the bearing-to-gear gap), and A18, the least clearance along the shafts (3 mm, from the first prototype). Shigley's gaps (A13, A14) are an industrial gearbox's; an EV reducer's are likely tighter.
- **The stress safety factor has no source yet.** Stress is recorded, not judged, in v0.
- **The rule-based arm, proposed** (plan §11.1): Maciejczyk and Zdziennicki's gear-case rules (TU Łódź 2011, Chapter 9).
  - They give the walls, bosses, flanges and bolts from the centre distance and the bearing bores, so they are the conventional design the agent must beat.
  - Their 7.5 mm floor is for sand casting. Under die casting, the contract's least wall would replace it.
  - Not built.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## The example's origin

The product's contract follows an example: Ivanov 2018, *Gearbox Housing Design - Topology Optimization through Generative Design*, MSc thesis, KTH, TRITA-ITM-EX 2018:724, for AVL Sweden, read from a copy.
- The gear train from its Figs. 24 and 25; the duty from §3.3-3.4; the material from Fig. 22.
- The maximum speed of 8,673 rpm from a 160 km/h top speed on its 245/45 R19 tyre (the engineer, 8 October 19:37).
- The reference housing (the design to beat: 7.732 kg, its modes, its bearing-bed displacements, its stress) from §3.1 and §4.1.
- Its 83 / 125 mm centre distances and 7.184 ratio verify the tools in `checks/contract/test_involute.py` and `test_train.py`.

The contract and the UI do not name it (CON-4).

## Docs

- [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md): the spec of CON-1.
- [2026-10-08-plan-contract-v0-and-first-variant.md](2026-10-08-plan-contract-v0-and-first-variant.md): the implementation plan, Tasks 1-11.
- [requirements-catalogue.md](requirements-catalogue.md): what engineers ask of a housing (15 questions), the inputs a user gives, what the tools derive, the load cases and the gaps, each row with its source.
- The plan of record, section 4 (the contract): [plan.md](../product/plan.md).
