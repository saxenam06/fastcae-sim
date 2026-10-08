# Platform

The repository and what every other feature runs on: the Python project and its own virtual environment, the checks and CI, the runner and its guards, the API and the web UI.

**PBI key:** PLT · **State:**
- PLT-2 (Python project, venv, checks, CI) works locally.
- PLT-4 (the web UI) works locally: the product's flow from the contract to the datapoints (committed in ca44539).
- **PLT-6 done locally (19:52-20:45):** every tab is one clean product page, asked for by the engineer.
  - The tabs, in the order the work runs: Contract → Campaigns → Designs → Data → Flow.
  - The Contract page shows one contract (Ivanov 2018): its inputs, the calculations with their methods pre-selected, the pass criteria, and the design to beat. The others show their frames, saying what fills them.
  - The old views are archived. Committed: the page model in 9acf466, the UI in 61e51c8 (not pushed).
- **PLT-7 done locally (22:35-23:13), uncommitted:** the Contract page says what is given and what is calculated. Inputs hold only what can be chosen freely (not the ratio or the centre distances, which the gear data fix). The calculations are the chain's nine steps, each naming what it takes in and what it gives out. Step 1 shows the gear geometry per stage: the working pressure angles 23.566° and 22.824°, and the working centre distances 82.917 and 125.037 mm, checked against the published 83 and 125.
- Committed on `product/end-to-end`, not pushed: PLT-2 in feca5c1, PLT-4 in ca44539. A fresh clone of the branch passes every check and builds the UI.

**Updated:** 2026-10-08 23:17 by Claude
**Code:** `pyproject.toml`, `uv.lock`, `src/zenryx/` (with `src/zenryx/api/`), `checks/`, `web/`, `.github/workflows/checks.yml`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| PLT-2 | The Python project: `pyproject.toml` (package `zenryx`), its own `.venv` (CadQuery and the solver's needs), `checks/` tracked with pytest pointed there, ruff, CI | Claude · LAPTOP-IR8VEG53 · `product/end-to-end`, the one branch for now | 2026-10-08 02:12 | Locally done: `uv sync --all-extras` builds the venv from `uv.lock`; the checks pass; ruff check and format are clean. **Committed in feca5c1** (not pushed). **Left:** the first CI run, once the branch is pushed |
| PLT-4 | The web UI (`web/`), built as the product rather than a viewer of prototypes: the contract, the campaigns made from it, their hypotheses, designs and grades, and the datapoints they become. What exists now (the contracts, their checks and sources) is shown; the rest is laid out and left blank. fastcae's sheet design copied. Design: [2026-10-08-ui-design.md](2026-10-08-ui-design.md) | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` (from `main` at 640a0f7, 8 Oct 18:18) | 2026-10-08 10:38 | **Done locally.** Five tabs: Flow, Contracts, Campaigns, Designs, Data. `npm run build` passes; the snapshot's 16 checks pass; every view was looked at in a screenshot of the built page (headless Edge, no server). **Committed in ca44539** (not pushed). **Left:** CI's first run of the web job once pushed |
| PLT-6 | **The contract page, made a product page** (the engineer, 19:52): one contract; clean inputs; calculations with their method pre-selected (authors in brackets); criteria; the design to beat; short source labels; the old long views archived | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-08 19:52 | **Done locally, 20:10.**<br>- The Ivanov contract written (CON-3, posed, validator clean).<br>- `zenryx.contract.train`: ratio, speeds, mesh frequencies, shaft angle; 9 checks.<br>- The page model `zenryx.api.contract_page`: 5 calculations computed, 5 planned.<br>- The page in `web/src/contracts/` (ContractPage, parts, contract.css); a tab may now have no rail or card; the old views archived (now in `archive/web/contracts-v1/`).<br>- 125 checks pass, `npm run build` passes, and the page was looked at in screenshots at 1,600 and 1,280 px.<br>**20:41, the rest made the same way** (the engineer, 20:35: "build it like this").<br>- The tabs, in the order the work runs: Contract → Campaigns → Designs → Data → Flow. One page each, no rail, no card; the contract is the default view.<br>- **Campaigns:** the new-campaign form (contract, solver, budget, stop rules, a Start button that says what it waits for) and the steps table.<br>- **Designs:** the design to beat, the designs table with a dot per stage, mass against margin with the published mass drawn, the rungs.<br>- **Data:** datapoint kinds A-E with examples in words, the cuts from campaigns, the 20 task types worded for any contract with their graders.<br>- **Flow:** the factory as one strip, and what to build next.<br>- The old pages are archived (now in `archive/web/{campaigns,designs,data,flow}-v1/`); their word lists moved to `web/src/words/`.<br>**Done locally, 20:45:** builds, 125 checks pass, every tab looked at in screenshots, the UI design rewritten (§3-8) and the old views described in `docs/archive/2026-10-08-ui-views-v1.md`. **Committed in 9acf466 and 61e51c8** (not pushed); a fresh clone of each passes every check and builds. **Next:** the engineer's look |
| PLT-7 | **The contract page: what is given and what is calculated, step by step** (the engineer, 22:35). Inputs hold only what is given or assumed. The calculations are the chain's steps 1-9, each with what it takes in and what it gives out; step 1 shows the gear geometry per stage (the working pressure angles, the diameters, the working centre distance against the given one) | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-08 22:35 | **Done locally, 22:46.**<br>- `zenryx.contract.involute.mesh_geometry`: the transverse and working pressure angles and the reference, base and working pitch diameters, with the working centre distance from them; 5 new checks (the involute relation, the diameters' identities, the unshifted case, Ivanov's published centre distances).<br>- The page model: the inputs lose the two calculated rows (the shaft angle, the bearing sizes); the gear table names the normal pressure angle and the centre distance given; the calculations are the chain's steps 1-9, each with what it takes in and gives out; the planned ones name GBX-1 to GBX-4 or the judge. 4 new snapshot checks, one replaced.<br>- The UI: the Calculated table (#, step, method, takes in, gives out), step 1's output a column per stage.<br>- **22:54, where the inputs come from** (the engineer, 22:50: "if these are input they are from where?"): each stage's column names its source down to the figure ("Stage 1 · Ivanov 2018, Fig. 24", "Stage 2 · … Fig. 25"); a cell is tagged only where it differs (stage 2's assumed helix angle, A7); the caption "From Ivanov 2018 unless marked" is gone. The page model decides it (`own` on each cell, `sources` on the table).<br>- **23:13, only what can be chosen freely is an input** (the engineer, 22:57-23:05):<br>&nbsp;&nbsp;- the ratio and the centre distances leave the inputs: steps 2 and 1 calculate them, and set them against Ivanov's published 7.184 and 83 / 125 mm;<br>&nbsp;&nbsp;- step 3 places the shafts by the calculated centre distances;<br>&nbsp;&nbsp;- the material's properties sit under the material;<br>&nbsp;&nbsp;- "Takes in" names each quantity, grouped as "Inputs" and "From step n, its name", with no bare ←n.<br>- The same review of the other tabs: the campaign budget is tagged "from the contract"; the load tool reads GBX-1 to GBX-4 wherever it is named (Contract, Campaigns, Flow), and task 1's grader reads GBX-1, GBX-2.<br>- **23:18, the product's view** (the engineer, 23:15: the user brings the requirements, the tools work out the unknowns): the Calculated section shows only what each step works out; the published check row and the ✓ marks are gone; the validator still holds the contract to them (the head's "checks passed"). The sections read "your requirements" and "what zenryx works out from them".<br>- 136 checks pass, ruff is clean, `npm run build` passes, and every tab was looked at in screenshots. **Uncommitted. Next:** the engineer's helix choice (contract page, Open), then the word to commit |

## Next

| PBI | Goal | Done when |
|---|---|---|
| PLT-3 | The runner and its guards copied from fastcae (`runner`, `heavy_guard`, `away_only`), with their parity checks | One job runs and is cancelled; the guard stops a fake heavy job |
| PLT-5 | The API (FastAPI, its own port 8030, no `--reload`) serving the snapshot and the records, and fastcae's 3D viewer copied into the Designs tab (split from PLT-4 on 8 October) | The UI reads the API, and shows a mesh and its contours from a solved reference case |

## What runs

- **The Python project `zenryx`:**
  - Python 3.12, built by uv from `pyproject.toml` and `uv.lock` into `.venv`, which is gitignored.
  - Extras: `geometry` (cadquery 2.8.0 on cadquery-ocp 7.9.3.1.1, the OCP fastcae proved on this laptop; gmsh 4.15.2, manifold3d, scikit-image, trimesh, pyvista), `docs` (pypdf) and `dev` (pytest, ruff).
  - Build: `uv sync --all-extras`.
- **The checks:** `uv run pytest checks -q`. `checks/test_environment.py` checks that the package and every dependency import, and that CadQuery builds an exact box.
- **Lint:** `uv run ruff check src checks` and `uv run ruff format --check src checks`.
- **The snapshot** (`src/zenryx/api/snapshot.py`): `uv run python -m zenryx.api.snapshot` writes `web/src/records/snapshot.json`.
  - It reads the product's contracts, today one: `checks/data/contracts/ivanov2018_posed.json`. For each it records: the entries in words, each with its provenance, authority and kind; the validator's 18 rules and its refusals; what freezing it now would say; the items to keep; the scenarios it implies.
  - With them goes the contract's page (`zenryx.api.contract_page`): the inputs with their short sources, the calculations with their methods, the criteria and the design to beat.
  - It keeps the records the agent and the judge will make, which are empty today.
  - It is deterministic (no timestamp), and `checks/api/test_snapshot.py` fails when the committed copy is stale. `--check` says the same from the command line.
- **The web UI** (`web/`):
  - React 19.3, Vite 7.3 and TypeScript 5.9, with no other dependency.
  - `npm ci`, then `npm run build` (types and bundle) or `npm run dev` (port 5190, a server: on the engineer's word).
  - In PowerShell, type `npm.cmd` for `npm`: its default execution policy refuses the `npm.ps1` wrapper. The engineer met this at 18:14 on 8 October.
  - It bundles the snapshot; nothing on screen comes from anywhere else.
  - The tabs, one clean page each, in the order the work runs (PLT-6):
    - **Contract:** the inputs, only what is given or assumed, with short sources; the calculated steps 1-9 of the chain, each with its method pre-selected, what it takes in and what it gives out (three computed now, six planned); the pass criteria; the design to beat; the assumptions, folded.
    - **Campaigns:** the new-campaign form, whose Start says what it waits for; the steps table.
    - **Designs:** the design to beat; a design a row with a dot per stage; mass against margin; the rungs.
    - **Data:** datapoint kinds A-E with examples in words; the cuts from campaigns; the 20 task types and their graders.
    - **Flow:** the factory as one strip, and what to build next.
  - **The old views** (60 files) are archived in `archive/web/*-v1/` at the repository's top. Git ignores `archive/`, so they are on the engineer's laptop only, outside the build. Git's history also has them at 61e51c8, under `web/archive/*-v1/` (for example `git show 61e51c8:web/archive/flow-v1/README.md`).
- **Copied from fastcae** (`fastcae-v1`, each with its origin header): the design tokens and the shell, rail and campaign styles; the crash screen, the splitter and the metric card; the art. The frame of `App.tsx` and `product.ts` is adapted from fastcae's.
- **CI:** `.github/workflows/checks.yml` builds from the locks on ubuntu. Its first job runs lint, format and checks; the second runs `npm ci` and `npm run build` in `web/`. Neither has run yet.

## Rules in force

- **Branches:** for now one branch, `product/end-to-end`, holds every PBI's work until the workflow runs end to end (the engineer, 8 October 18:20). After that, each PBI goes on its own branch `<feature>/<KEY>-<n>-<few-words>`, from `main`, merged back when done.
- **Commits and servers:** only on the engineer's word. Screenshots of the UI come from headless Edge on the built page, with `--allow-file-access-from-files`, and need no server.
- **No imports from fastcae;** copies carry their origin, and a parity test where they compute.
- **Own state, separate from fastcae's:** ports (the UI 5190, the API 8030), venv, data folder, runner state.
- **Ignore rules are anchored at the root** (`/data/`, `/assets/`, `/results/`), so `checks/data/` (the example contracts) and `web/src/data/` (the Data tab) are tracked. Before 8 October 11:55 a bare `data/` hid both.
- **The UI shows the product's records, never a prototype's output.** What is not built is drawn blank, with words where the records will go and the PBI that fills it; never example numbers.
- **One stylesheet order:** the shared sheets load first (`main.tsx`), and each tab's own sheet, its classes prefixed, refines them.

## Measured

- **The checks:** `uv run pytest checks -q` gives 135 passed in 1.9 s (8 October 23:13). The snapshot's are 24 of them.
- **The UI's build:** 0.9 s, after `tsc -b`.
  - The bundle: 262 kB of script (81 kB gzipped), 39 kB of styles, and an 83 kB snapshot chunk (11 kB gzipped).
  - The snapshot file is 94 kB for one contract.
- **What the UI shows today:** one contract, Ivanov 2018, posed: 29 input values (10 assumed), the chain's steps 1-9 (3 computed, 6 planned), and the validator's 18 rules, all passed. Every record downstream is 0.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| The repository | This one (`fastcae-sim`), package `zenryx`; see the product page | 2026-10-07, the engineer |
| The UI | Built as the end-to-end product, starting from the contract; fastcae's UI copied for its design; a prototype's trials are not part of it; what does not exist yet stays blank | 2026-10-08 10:38, the engineer |
| One branch for now | Every PBI's work goes on `product/end-to-end` until the workflow runs end to end; branches per PBI come back after that | 2026-10-08 18:20, the engineer |
| Archived code is kept, out of git | A top-level `archive/` that git ignores (`/archive/`): `archive/web/` for the UI's old views, `archive/src/` for retired Python. Nothing archived is deleted. Git's history keeps what was committed (the UI's first views at 61e51c8) | 2026-10-08 22:22, the engineer |

## Open

- The remote is `github.com/saxenam06/fastcae-sim` (private). A rename to `zenryx` can come at any time; GitHub keeps redirects. The local folder keeps its name, because Claude's memory for this repository is tied to the folder's path.
- **The UI's words for the agent and the record** (the stop rules, statuses, seeds, tools, rungs, stages, datapoint kinds and task types) sit in `web/src/words/`, shared by every tab (PLT-6).
- **The record's shapes in `web/src/records/types.ts` are provisional** until the record schema (DAT-1) is agreed. Two wishes from building against them:
  - a design's stage states, or a failure that names its stage;
  - a campaign's hours spent.
- **Plan §7.2's third rung, "process-simulated",** still reads as LPBF ("supports simulated for the chosen orientation"). With die casting first, it would be the casting's simulation. The UI shows the plan's words as they are.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|
| PLT-1 | The repository and its context for zenryx: CLAUDE.md, the board, the feature pages, the plan and decisions moved from fastcae (links rewritten), the plans of 4-5 October archived, the notes hook (with `*.sh` kept at LF), Claude's memory for this folder seeded from fastcae's; merged into `main` | 2026-10-07 | bcd86fe, and the commit that records it |

## Docs

- [CLAUDE.md](../../../CLAUDE.md): how the work is organised, and this machine's pitfalls.
- [2026-10-08-ui-design.md](2026-10-08-ui-design.md): the web UI, from the contract to the datapoints.
