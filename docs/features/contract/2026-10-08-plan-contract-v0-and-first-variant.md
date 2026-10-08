# Contract v0 and the first variant: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three things, overnight on 8 October 2026, at the engineer's request (02:06):
- a working Python environment, PLT-2 (Python project, venv, checks, CI);
- the contract, CON-1 (contract schema v0), test-first;
- one housing variant derived from Hofstetter 2018's contract, to see how the geometry route works and looks. It combines a CadQuery machined core with a shell and structure generated in field space.

**Architecture:**
- `zenryx.contract` is pydantic v2 models plus a unit table, a validator and a canonical hash. It is product code, built with TDD.
- The variant is a **prototype** in `prototypes/first_variant/`, labelled as such: a spike that answers "how does it work, how does it look". It is not product code, and nothing in `src/` imports it.
- Its outputs go to `data/prototypes/first_variant/`, which is gitignored.

**Tech stack:** Python 3.12 with uv. cadquery 2.8.0 on cadquery-ocp 7.9.3.1.1 (the OCP fastcae proved here). pydantic 2.13, numpy 2.5, scipy 1.18, scikit-image 0.26, manifold3d 3.5, trimesh 5.1, pyvista 0.49 with vtk 9.6, gmsh 4.15.2, pypdf 6.19. pytest 9.1 and ruff 0.16. All were resolved together on 8 October.

**Spec:** [2026-10-08-contract-v0-design.md](2026-10-08-contract-v0-design.md).

## Global Constraints

- Python `>=3.12,<3.13`; the venv is `.venv` in the repository root (gitignored); `uv sync` builds it.
- `cadquery==2.8.0` and `cadquery-ocp==7.9.3.1.1`, pinned.
- Nothing imports fastcae. Nothing from GRC enters the repository (CLAUDE.md).
- Canonical units: mm, N, s, MPa, tonne. Every quantity carries a unit from the spec's list (§5). A value without a unit is refused.
- Every value in an example contract carries a provenance (spec §3). Assumptions are A1-A7 (spec §4.8).
- No part-specific names in `src/`: interfaces are named by geometric kind (cylindrical seat, split face, mount pad, motor flange, port).
- **No commits and no pushes** without the engineer's word (CLAUDE.md). Each task ends by leaving its files in place; the commit steps are left for the engineer.
- **Files are written with the Write or Edit tool.** Never patch through a Bash heredoc, and never rewrite sources with PowerShell's Get-Content or Set-Content (CLAUDE.md pitfalls).
- **One heavy job at a time**, with free memory checked first. Nothing in this plan should exceed a few GB.

## Review Focus

1. **Unit spellings.**
   - "Nm", "N*m", "N.m" and "N·m" are the same unit, and so are "um" and "µm". All are accepted, through one alias table.
   - Anything else is refused with the list of allowed units.
   - Test: `test_units.py::test_aliases` and `::test_unknown_unit_is_refused`.
2. **Hash stability.** Key order and re-serialisation must not change the hash, but any value change must. A float that round-trips (0.1 + 0.2) stays stable because it is written with Python's shortest repr after unit conversion. Test: `test_canonical.py`.
3. **Angles.** A helix angle given without a unit is refused, and degrees and radians convert correctly. Test: `test_units.py::test_angles`.
4. **Optional sections absent.** A contract without a vehicle or a load spectrum validates. Test: `test_validate.py::test_minimal_posed_contract_is_accepted`.
5. **The stage rules.**
   - A posed `package` contract with empty interfaces is accepted.
   - A derived contract with an unstamped derived value is refused.
   - A frozen contract whose hash does not match is refused.

   Test: `test_validate.py::test_stage_rules`.

---

## Part A: the environment (PLT-2, Python project, venv, checks, CI)

### Task 1: The Python project, its venv and the first checks

**Files:**
- Create: `pyproject.toml`, `src/zenryx/__init__.py`, `checks/conftest.py`, `checks/test_environment.py`, `.github/workflows/checks.yml`

**Interfaces:**
- Produces: the importable package `zenryx`; `uv run pytest checks -q` and `uv run ruff check src checks` as the two commands every later task runs.

- [x] **Step 1: Write `pyproject.toml`.**
  - Package `zenryx`, built with hatchling from `src/zenryx`.
  - Dependencies: `pydantic>=2.9`, `numpy>=2.1`, `scipy>=1.14`.
  - Optional `geometry`: `cadquery==2.8.0`, `cadquery-ocp==7.9.3.1.1`, `gmsh==4.15.2`, `manifold3d>=3.0`, `scikit-image>=0.24`, `trimesh>=4.5`, `pyvista>=0.44`.
  - Optional `docs`: `pypdf>=5.1`.
  - Optional `dev`: `pytest>=8.3`, `ruff>=0.7`.
  - Ruff: line length 100, rules E, F, I, UP, B, SIM, as fastcae's.
  - Pytest: `testpaths = ["checks"]`.
- [x] **Step 2: Write the failing environment check, `checks/test_environment.py`.**

```python
"""The environment builds what the rest of zenryx relies on."""

import importlib

import pytest


def test_package_imports():
    import zenryx

    assert zenryx.__version__ == "0.1.0"


@pytest.mark.parametrize("name", ["pydantic", "numpy", "scipy"])
def test_core_dependencies_import(name):
    importlib.import_module(name)


def test_cadquery_builds_an_exact_box():
    cq = pytest.importorskip("cadquery")
    box = cq.Workplane("XY").box(10, 20, 30)
    assert box.val().Volume() == pytest.approx(6000.0, rel=1e-9)


@pytest.mark.parametrize("name", ["gmsh", "manifold3d", "skimage", "trimesh", "pyvista"])
def test_geometry_dependencies_import(name):
    pytest.importorskip(name)
```

- [x] **Step 3: Run it to see it fail.** `uv run pytest checks -q` should fail with "No module named zenryx".
- [x] **Step 4: Write `src/zenryx/__init__.py`** with a module docstring and `__version__ = "0.1.0"`. Run `uv sync --all-extras`.
- [x] **Step 5: Run the checks; they pass.** `uv run pytest checks -q` and `uv run ruff check src checks`.
- [x] **Step 6: Write the CI file.** `.github/workflows/checks.yml`: ubuntu-latest, `astral-sh/setup-uv`, `uv sync --all-extras`, `uv run ruff check src checks`, `uv run pytest checks -q`. It is not pushed tonight.
- [ ] **Step 7: Commit, left for the engineer.** `git add pyproject.toml uv.lock src/zenryx/__init__.py checks/ .github/` then `git commit -m "Platform: the Python project, its venv, checks and CI (PLT-2)"`.

## Part B: the contract (CON-1, contract schema v0)

### Task 2: Units

**Files:** Create `src/zenryx/contract/__init__.py`, `src/zenryx/contract/units.py`; test `checks/contract/test_units.py`.

**Interfaces:**
- Produces:
  - `Quantity(BaseModel)`: `value: float` and `unit: str`, frozen;
  - `Quantity.parse(text: str) -> Quantity`;
  - `Quantity.to_canonical() -> tuple[float, str]`;
  - `UNITS: dict[str, tuple[str, float]]`, the unit → (canonical unit, factor) table;
  - `ALIASES: dict[str, str]`;
  - `UnitError(ValueError)`.

Canonical units: `mm`, `N`, `N*mm`, `s`, `MPa`, `t/mm3`, `rad`, `rad/s`, `Hz`, `kg`, `1`. Mass is reported in kg, the unit engineers read. The table: mm 1, m 1000, µm 1e-3; N 1, kN 1e3; N·m → N*mm 1e3, N·mm 1; rpm → rad/s 2π/60, rad/s 1; MPa 1, GPa 1e3; kg/m³ → t/mm3 1e-12; kg 1, g 1e-3; mrad → rad 1e-3, deg → rad π/180, rad 1; h → s 3600, s 1; Hz 1; % → 1 at 0.01; and "1" (dimensionless).

- [x] **Step 1: Write the failing tests.**

```python
import math

import pytest

from zenryx.contract.units import Quantity, UnitError


def test_parse_and_convert_torque():
    q = Quantity.parse("366 N·m")
    assert q.to_canonical() == pytest.approx((366000.0, "N*mm"))


@pytest.mark.parametrize("text", ["366 Nm", "366 N*m", "366 N.m", "366 N m"])
def test_aliases(text):
    assert Quantity.parse(text).to_canonical()[0] == pytest.approx(366000.0)


def test_micrometres_both_spellings():
    assert Quantity.parse("6 µm").to_canonical() == pytest.approx((0.006, "mm"))
    assert Quantity.parse("6 um").to_canonical() == pytest.approx((0.006, "mm"))


def test_speed():
    value, unit = Quantity.parse("15000 rpm").to_canonical()
    assert unit == "rad/s"
    assert value == pytest.approx(15000 * 2 * math.pi / 60)


def test_angles():
    assert Quantity.parse("20 deg").to_canonical()[0] == pytest.approx(math.radians(20))
    assert Quantity.parse("0.5 mrad").to_canonical() == pytest.approx((5e-4, "rad"))
    with pytest.raises(UnitError):
        Quantity.parse("20")


def test_unknown_unit_is_refused():
    with pytest.raises(UnitError, match="allowed units"):
        Quantity.parse("3 furlongs")
```

- [x] **Step 2: Run them to see them fail.** `uv run pytest checks/contract/test_units.py -q` fails with ImportError.
- [x] **Step 3: Implement `units.py`.** The table and aliases above. `parse` splits the number from the unit at the first whitespace, then normalises "·", "*", "." and a space between N and m. An empty unit raises `UnitError("a value needs a unit; allowed units: ...")`.
- [x] **Step 4: Run them; they pass.** Also run ruff.

### Task 3: Entries: value, provenance, authority, kind

**Files:** Create `src/zenryx/contract/entry.py`; test `checks/contract/test_entry.py`.

**Interfaces:**
- Consumes: `Quantity`.
- Produces:
  - `ProvenanceKind = Literal["published", "standard", "measured", "derived", "assumption", "engineer"]`;
  - `Provenance(BaseModel)`, with fields `kind`, `citation: str | None`, `tool: str | None`, `tool_version: str | None`, `input_hash: str | None`, `assumption_id: str | None`, `who: str | None`, `when: str | None`, `note: str | None`;
  - `Authority = Literal["engineer_locked", "agent_bounded", "agent_free"]`;
  - `Kind = Literal["hard", "soft", "derived"]`;
  - `Entry(BaseModel)`, with fields `value: Quantity | str | float | int | bool | list | None`, `provenance`, `authority`, `kind`, `bounds: tuple[Quantity, Quantity] | None`;
  - `Entry.stamped() -> bool`.

All models use `ConfigDict(extra="forbid", frozen=True)`, so unknown fields (an "answer" smuggled in) are refused.

- [x] **Step 1: Write the failing tests.**
  - A `published` entry needs a citation.
  - A `derived` entry needs a tool, version and input hash, so `stamped()` is True only then.
  - An `assumption` entry needs an `assumption_id`.
  - `agent_bounded` needs bounds.
  - An extra field raises a ValidationError.
- [x] **Step 2: Run them to see them fail.**
- [x] **Step 3: Implement with a pydantic `model_validator(mode="after")`.** It enforces the provenance-kind rules and authority bounds, and its messages name the rule ("provenance.derived needs tool, tool_version, input_hash").
- [x] **Step 4: Run them; they pass.**

### Task 4: The layers and the contract

**Files:** Create `src/zenryx/contract/model.py`; test `checks/contract/test_model.py`.

**Interfaces:**
- Consumes: `Entry`, `Quantity`.
- Produces:
  - `Stage = Literal["posed", "derived", "frozen"]`;
  - `RequirementStyle = Literal["package", "gear_train"]`;
  - `TorqueSpec(shaft: str, kind: Literal["peak", "nominal", "continuous", "maximum"], direction: Literal["drive", "regeneration", "reverse"], torque: Entry)`;
  - `SpeedSpec(shaft: str, kind: Literal["maximum", "base", "rated"], speed: Entry)`;
  - `GearStage(name, z_pinion, z_gear, normal_module, pressure_angle, helix_angle, helix_hand_pinion, face_width_pinion, face_width_gear, profile_shift_pinion, profile_shift_gear, centre_distance)`. All are `Entry | None`, so a `package` contract may leave them empty;
  - `BearingSpec(seat: str, designation: Entry, type: Entry)`;
  - `Requirement(style, torques: list[TorqueSpec], speeds: list[SpeedSpec], total_ratio: Entry, ratio_tolerance: Entry | None, input_output_offset: Entry | None, service_life: Entry | None, gear_material: Entry | None, gear_quality: Entry | None, stages: list[GearStage], bearings: list[BearingSpec], installation_space: InstallationSpace)`;
  - `InstallationSpace(kind: Literal["box", "layout_envelope"], size: list[Entry] | None, clearance: Entry | None)`;
  - `Frame(origin: list[float], z_axis: list[float], x_axis: list[float])`;
  - `CylindricalSeat(name, frame, diameter, width, shoulder: Literal["+z", "-z"], stock, hosts)`, `SplitFace(name, origin, normal, bolt_count, bolt_hole_diameter, bolt_pitch_circle | bolt_points)`, `MountPad`, `MotorFlange`, `Port`;
  - `Interfaces(seats, split_faces, mount_pads, motor_flanges, ports)`;
  - `SeatLoad(seat: str, force: list[Entry])`, `LoadCase(name, seat_loads: list[SeatLoad])`;
  - `PhysicsCases(load_cases, mesh_orders: list[Entry])`;
  - `Limits(...)`, one Entry per check in spec §4.5, plus `verdict_rule_version: str`;
  - `ManufacturingProfile(process, pull_directions, draft_inside, draft_outside, min_wall, max_wall: Entry | None, machining_stock, material_E, material_nu, material_rho)`;
  - `ReferenceValue(source, quantity, value_text, conditions, confidence)`;
  - `Assumption(id, what, value_text, why, varied: bool)`;
  - `Task(id, title, family, level: Literal["L1"], priorities: list[str], budget_fe_proofs: int, budget_hours: float)`;
  - `HousingDesignSpec(schema_version: Literal["0.1"], stage, task, requirement, interfaces: Interfaces | None, physics: PhysicsCases | None, limits, manufacturing, references, assumptions, frozen_hash: str | None)`.

- [x] **Step 1: Write the failing test.** Build the Hofstetter posed contract from `checks/data/contracts/hofstetter2018_posed.json` (Task 7 writes it; for this task, a minimal in-test dict) and assert that the model loads it.
- [x] **Step 2: Run it to see it fail.**
- [x] **Step 3: Implement the models.** Each has `extra="forbid"` and is frozen.
- [x] **Step 4: Run it; it passes.**

### Task 5: Canonical serialisation and the hash

**Files:** Create `src/zenryx/contract/canonical.py`; test `checks/contract/test_canonical.py`.

**Interfaces:**
- Produces:
  - `canonical_json(spec: HousingDesignSpec) -> str`. It has sorted keys, compact separators, every Quantity replaced by its canonical (value, unit), and `frozen_hash` excluded;
  - `spec_hash(spec) -> str`: `"sha256:" + hexdigest`;
  - `freeze(spec) -> HousingDesignSpec`, which returns a copy with `stage="frozen"` and `frozen_hash` set.

- [x] **Step 1: Write the failing tests.**
  - The same content in a different key order gives the same hash.
  - A round trip through `model_dump_json` and `model_validate_json` gives the same hash.
  - Changing one torque value changes the hash.
  - "366 N·m" and "366000 N·mm" give the same hash, because the units are canonical.
- [x] **Step 2: Run them to see them fail.**
- [x] **Step 3: Implement.** Use `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, writing floats with Python's repr after conversion.
- [x] **Step 4: Run them; they pass.**

### Task 6: The validator

**Files:** Create `src/zenryx/contract/validate.py`; test `checks/contract/test_validate.py`.

**Interfaces:**
- Consumes: the models, `spec_hash`.
- Produces:
  - `Refusal(BaseModel)`, with fields `rule: str`, `entry: str`, `reason: str`;
  - `validate(spec: HousingDesignSpec) -> list[Refusal]`. An empty list means accepted;
  - `load_and_validate(path) -> tuple[HousingDesignSpec | None, list[Refusal]]`. Pydantic errors become Refusals with rule `schema`.

The rules (spec §7):
- `provenance.*`: an assumption id must exist in `assumptions`.
- `stage.derived_needs_stamps`: in a derived or frozen contract, every entry under `interfaces` and `physics` is stamped.
- `stage.frozen_hash`: the hash matches.
- `consistency.redundant` (since 8 October 23:37, replacing the first plan's `consistency.centre_distance`): no input is one the other inputs fix. A stage whose full gear data are given (teeth, module, pressure angle, helix angle, both profile shifts) carries no centre distance; with αt = atan(tan αn / cos β), inv αw = inv αt + 2(x1 + x2) tan αn / (z1 + z2) and a = (mn (z1 + z2) / (2 cos β)) · cos αt / cos αw, the gear data fix it. With every stage's teeth given, the contract carries no ratio, and no ratio tolerance without a ratio.
- `consistency.ratio`: where the teeth are not given, the ratio is.
- `consistency.offset`: |a1 − a2| ≤ offset ≤ a1 + a2, each centre distance calculated where the gear data fix it.
- `consistency.seat_inside_space`: a seat lies inside the installation space, when it is a box.
- `consistency.power`: P = T·ω, when both are given.
- `hygiene.verdict_rule`: a verdict rule version is present.
- `torque.shaft_and_kind`: enforced by the model; reported as a Refusal.

- [x] **Step 1: Write the failing tests.**
  - The three example contracts are accepted (Task 7's files).
  - Each mutation is refused with its rule: unit removed; torque shaft removed; ratio broken (z changed); seat moved outside the box; stamp removed from a derived value; an extra "result" field; frozen hash tampered.
  - `test_minimal_posed_contract_is_accepted`.
  - `test_stage_rules`.
- [x] **Step 2: Run them to see them fail.**
- [x] **Step 3: Implement**, one function per rule, collecting Refusals.
- [x] **Step 4: Run them; they pass.**

### Task 7: The example contracts

**Files:** Create `checks/data/contracts/hofstetter2018_posed.json`, `checks/data/contracts/agri_ev_gearbox_posed.json`, `checks/data/contracts/textbook_two_bearing_derived.json`, and `checks/data/contracts/README.md` (each file's sources).

- [x] **Step 1: The Hofstetter contract.**
  - From spec §4.2: Table 2's values with `published` citations ("Hofstetter et al. 2018, Forsch Ingenieurwes 82:361-370, Table 2"); Table 3's benchmark bearings.
  - Assumptions A1-A7 with their ids.
  - Limits from spec §4.5; the HPDC profile from spec §4.6; the reference band from spec §4.7.
  - Before entering the Table 3 bearings, re-read them from the paper's text so the row alignment is right.
- [x] **Step 2: The agricultural gearbox, `gear_train` style.**
  - Re-read Kim et al. 2024 Table 1 from its PDF with pypdf, rather than from the subagent's report, and enter the values with citations.
  - The torque is ambiguous in the paper ("22 Nm" at the output against "7 kW"), so the 7 kW at 2,650 rpm input is used and the conflict is recorded as an assumption.
- [x] **Step 3: The textbook case, derived.**
  - GHE §6.2's worked example: T = 300 N·m, d = 60 mm, αn = 20°, β = 25°, a gear centred on a 120 mm span.
  - Its two seat loads (5.07 and 5.92 kN radial) are entered as `derived` with tool `manual-1`, version `1`, and the input hash of the stated inputs.
- [x] **Step 4: Run the whole check suite; it passes.** `uv run pytest checks -q`.

## Part C: the first variant (a prototype, to see how it works and looks)

Labelled throughout as a prototype. Its numbers are not the judge's: the load front-end here is a first sketch, not yet passed through plan §4.3's three checks.

### Task 8: A first front-end sketch: layout and seat loads from Hofstetter's contract

**Files:** Create `prototypes/first_variant/frontend.py`; its output is `data/prototypes/first_variant/derived.json`.

- [x] **Ratio split.** Stage 1 is 25/65 (2.60), stage 2 is 23/82 (3.565); product 9.27, inside 9.32 ± 1 %.
- [x] **Sizing by rule of thumb, labelled.**
  - Normal modules 2.0 and 2.5 mm, helix 20° on both stages, αn 20°, no profile shift. 2.5 mm rather than 3.0 mm, so the output gear (about 218 mm pitch diameter) packs inside the 165 mm offset; changed when the prototype was briefed.
  - Face widths from Hofstetter's overlap-ratio rule: b = εβ·π·mn / sin β with εβ = 2, giving about 36.7 and 45.9 mm.
  - This is not a rating.
- [x] **Layout.**
  - The input axis is at the origin; the output axis is 165 mm along +x (Hofstetter's offset).
  - The intermediate axis sits at the triangle vertex fixed by a1 and a2, on the +y side.
  - Shaft stations come from the face widths and bearing widths, with 5 mm gaps.
- [x] **Bearings from Table 3.**
  - Boundary dimensions from the ISO 15 dimension series as maker catalogues list them: 6206 d30 D62 B16; NU205 d25 D52 B15; 32010 X d50 D80 T20; 6012 d60 D95 B18; 6011 d55 D90 B18.
  - These are to be checked against a maker's catalogue; the morning summary says so.
- [x] **Seat loads** for drive, regeneration and reverse at 366 N·m (A1):
  - Ft = 2T/d, Fr = Ft·tan αn / cos β, Fa = Ft·tan β (JTEKT);
  - two-support statics per shaft, with the axial-force moment Fa·d/2 (JTEKT eq. 5-29);
  - the thrust to the locating bearing.
- [x] **Output:** interfaces and loads written as a `derived` contract, stamped `frontend-prototype` version `0.1`. Validate it with `zenryx.contract.validate`.

### Task 9: The machined core in CadQuery

**Files:** Create `prototypes/first_variant/core.py`; outputs `core.step` and `core.stl`.

- [x] One main-housing half, with the split face at z = 0 and the pull direction +z (A7). The cover is left for later.
- [x] Seat rings on the back wall:
  - bore = the bearing's outside diameter;
  - ring wall 8 mm;
  - ring length = the bearing width plus a 4 mm shoulder;
  - 0.25 mm machining stock modelled as the bore's finish allowance.
- [x] Bolt bosses on the split plane (Ø18 mm, M8 clearance holes Ø9 mm), spaced along the shell's outline at most 80 mm apart.
- [x] A motor-flange ring around the input seat (spigot Ø110 mm), and one mount pad (60 × 40 mm, two Ø11 mm holes) on the output side (A4).
- [x] The prototype's sizes for bosses, pads and flanges (Ø18 mm, 80 mm, Ø110 mm, 60 × 40 mm) are not from the contract and are labelled as such.
- [x] The core's volume and the STEP export are checked: the file re-imports with the same volume.

### Task 10: The shell and structure in field space

**Files:** Create `prototypes/first_variant/field.py`.

- [x] Grid: 1.5 mm voxels over the installation space (the layout's envelope plus 20 mm, A3). Check the free memory first.
- [x] Keep-outs:
  - each gear's tip cylinder plus 5 mm radial and 3 mm axial clearance;
  - each shaft between its seats as a cylinder of the bearing's bore plus 3 mm.
- [x] Shell: the band at distance 5-10 mm from the union of the keep-outs, giving a 5 mm wall above the 4 mm minimum (D7). It is closed at the back wall and cut open at the split plane.
- [x] Draft: the shell's offset grows with z by tan 2° on inside faces, so walls taper away from the split.
- [x] Structure, as distance-field members joined by smooth unions (radius 6 mm), all clipped to the installation space minus the keep-outs:
  - webs from each seat ring to the mount pad;
  - a bridge between the input and intermediate seat rings;
  - a bridge between the intermediate and output seat rings;
  - ribs from the seat rings to the shell.
- [x] Checks reported, not enforced: a wall-thickness map (distance transform, minimum against 4 mm); the share of the cast surface whose slope to the pull direction is under 1° (a draft map); enclosed voids found by flood fill.

### Task 11: Join, export, pictures

**Files:** Create `prototypes/first_variant/join.py`, `prototypes/first_variant/render.py`, `prototypes/first_variant/run.py` (runs Tasks 8-11 in order), and `prototypes/first_variant/README.md` (how it works).

- [x] Marching cubes on the structure field, then a manifold3d union with the core's mesh, then the exact bore cylinders subtracted again so the seats stay clean.
- [x] Export `housing.stl` and `housing.glb`; mass at 2.66 g/cm³ (the card in spec §4.6).
- [x] Pictures with pyvista off screen, as PNGs:
  - an isometric view;
  - the view into the split face;
  - a section through the seats;
  - the wall-thickness map;
  - the draft map.
- [x] `summary.json`: mass, bounding box, thickness statistics, draft share, the voids found, every assumption used, and the run's time.
- [x] Look at every picture before calling the task done (CLAUDE.md, show pictures of geometry).

## After the tasks

- Rewrite the feature pages:
  - Platform: PLT-2 done or where it stands.
  - Contract: CON-1 done or where it stands.
  - The board, with the prototype named as a prototype.
- Rewrite the START HERE memory.
- The morning summary for the engineer covers what runs, where the pictures are, what is not checked, and the commits proposed (one per PBI, on branches `platform/PLT-2-python-project` and `contract/CON-1-contract-v0`, with the prototype separate). Nothing is committed.
