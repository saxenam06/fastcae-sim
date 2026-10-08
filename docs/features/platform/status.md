# Platform

The repository and what every other feature runs on: the Python project and its own virtual environment, the checks and CI, the runner and its guards, the API and the web UI.

**PBI key:** PLT · **State:**
- PLT-2 (Python project, venv, checks, CI) works locally.
- PLT-4 (the web UI) works locally: the product's flow from the contract to the datapoints, asked for by the engineer at 10:38. It shows the three contracts in full, and lays out everything downstream of them blank.
- Committed on `product/end-to-end`, not pushed: PLT-2 in feca5c1, PLT-4 in ca44539. A fresh clone of the branch passes every check and builds the UI.

**Updated:** 2026-10-08 18:38 by Claude
**Code:** `pyproject.toml`, `uv.lock`, `src/zenryx/` (with `src/zenryx/api/`), `checks/`, `web/`, `.github/workflows/checks.yml`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| PLT-2 | The Python project: `pyproject.toml` (package `zenryx`), its own `.venv` (CadQuery and the solver's needs), `checks/` tracked with pytest pointed there, ruff, CI | Claude · LAPTOP-IR8VEG53 · `product/end-to-end`, the one branch for now | 2026-10-08 02:12 | Locally done: `uv sync --all-extras` builds the venv from `uv.lock`; the checks pass; ruff check and format are clean. **Committed in feca5c1** (not pushed). **Left:** the first CI run, once the branch is pushed |
| PLT-4 | The web UI (`web/`), built as the product rather than a viewer of prototypes: the contract, the campaigns made from it, their hypotheses, designs and grades, and the datapoints they become. What exists now (the contracts, their checks and sources) is shown; the rest is laid out and left blank. fastcae's sheet design copied. Design: [2026-10-08-ui-design.md](2026-10-08-ui-design.md) | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` (from `main` at 640a0f7, 8 Oct 18:18) | 2026-10-08 10:38 | **Done locally.** Five tabs: Flow, Contracts, Campaigns, Designs, Data. `npm run build` passes; the snapshot's 16 checks pass; every view was looked at in a screenshot of the built page (headless Edge, no server). **Committed in ca44539** (not pushed). **Left:** the engineer opens it (in PowerShell: `cd web`, then `npm.cmd run dev`, then http://localhost:5190) and says what to change; CI's first run of the web job once pushed |

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
  - It reads every contract in `checks/data/contracts/`. For each one it records: the entries in words, each with its provenance, authority and kind; the validator's 18 rules and its refusals; what freezing it now would say; the items to keep; the scenarios it implies.
  - It keeps the records the agent and the judge will make, which are empty today.
  - It is deterministic (no timestamp), and `checks/api/test_snapshot.py` fails when the committed copy is stale. `--check` says the same from the command line.
- **The web UI** (`web/`):
  - React 19.3, Vite 7.3 and TypeScript 5.9, with no other dependency.
  - `npm ci`, then `npm run build` (types and bundle) or `npm run dev` (port 5190, a server: on the engineer's word).
  - In PowerShell, type `npm.cmd` for `npm`: its default execution policy refuses the `npm.ps1` wrapper. The engineer met this at 18:14 on 8 October.
  - It bundles the snapshot; nothing on screen comes from anywhere else.
  - The tabs:
    - **Flow:** the factory's 11 stages with counts, and a contract a row through every stage; how one campaign is cut into datapoints.
    - **Contracts:** what binds a design (six boxes), every entry with its provenance, the validator's rules, the sources, the JSON; the entry or assumption card.
    - **Campaigns:** the steps table (the decision record), hypotheses, the tool trace and the budget, laid out blank; the stop rules, arms, seeds and tools.
    - **Designs:** the grid (a design a row, a stage a column), the trade-off and the evaluations, laid out blank; the verdict each contract sets, the rungs.
    - **Data:** the four axes with the scenarios each contract implies, the kinds A-E, the 20 task types with their graders' state, the counterfactual pairs, and a comparison of any two contracts.
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

- **The checks:** `uv run pytest checks -q` gives 109 passed in 1.9 s. The snapshot adds 16 of them.
- **The UI's build:** 1.2 s, after `tsc -b`.
  - The bundle: 391 kB of script (113 kB gzipped), 63 kB of styles, and a 141 kB snapshot chunk (14 kB gzipped).
  - The snapshot file is 152 kB for three contracts.
- **What the UI shows today:** 3 contracts (2 posed, 1 derived, 1 ready to freeze, 0 frozen), 17 cited sources and 18 validator rules, all passed. Every record downstream is 0.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| The repository | This one (`fastcae-sim`), package `zenryx`; see the product page | 2026-10-07, the engineer |
| The UI | Built as the end-to-end product, starting from the contract; fastcae's UI copied for its design; a prototype's trials are not part of it; what does not exist yet stays blank | 2026-10-08 10:38, the engineer |
| One branch for now | Every PBI's work goes on `product/end-to-end` until the workflow runs end to end; branches per PBI come back after that | 2026-10-08 18:20, the engineer |

## Open

- The remote is `github.com/saxenam06/fastcae-sim` (private). A rename to `zenryx` can come at any time; GitHub keeps redirects. The local folder keeps its name, because Claude's memory for this repository is tied to the folder's path.
- **The UI's words for the agent and the record** (the stop rules, statuses, seeds, tools, rungs and stages) sit in each tab's own `words.ts`. They move into `app/product.ts` when a second tab needs the same word.
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
