# Platform

The repository and what every other feature runs on: the Python project and its own virtual environment, the checks and CI, the runner and its guards, the API and the web UI.

**PBI key:** PLT · **State:** repository set up (CLAUDE.md, the board, the docs); no code · **Updated:** 2026-10-07 11:15 by Claude
**Code:** none yet (to come: `pyproject.toml`, `src/zenryx/`, `checks/`, `web/`, `scripts/`)

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| PLT-1 | The repository and its context, for the new product: CLAUDE.md, the board, the feature pages, the plan and decisions moved from fastcae, the superseded plans archived, the hooks, Claude's memory for this folder | Claude · LAPTOP-IR8VEG53 · `platform/PLT-1-repo-and-context` | 2026-10-07 11:05 | Written, uncommitted. Next: the engineer's word to commit and to merge into `main` |

## Next

| PBI | Goal | Done when |
|---|---|---|
| PLT-2 | The Python project: `pyproject.toml` (package `zenryx`), its own `.venv` (CadQuery and the solver's needs), `checks/` tracked with pytest pointed there, ruff, CI | A clean clone builds the venv, runs `checks/` green, and CI passes |
| PLT-3 | The runner and its guards copied from fastcae (`runner`, `heavy_guard`, `away_only`), with their parity checks | One job runs and is cancelled; the guard stops a fake heavy job |
| PLT-4 | The API skeleton (FastAPI, its own port, no `--reload`) and the web UI shell (`web/`, its own port), reusing fastcae's 3D viewer components | The UI shows a mesh and its contours from a solved reference case |

## What runs

The repository, its docs and its working rules. No code yet.

## Rules in force

- **Branches:** each PBI on its own branch `<feature>/<KEY>-<n>-<few-words>`, from `main`, merged back when done.
- **Commits and servers:** only on the engineer's word.
- **No imports from fastcae;** copies carry their origin and a parity test.
- **Own state, separate from fastcae's:** ports, venv, data folder, runner state.

## Measured

-

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| The repository | This one (`fastcae-sim`), package `zenryx`; see the product page | 2026-10-07, the engineer |

## Open

- The remote is `github.com/saxenam06/fastcae-sim` (private). A rename to `zenryx` can come at any time; GitHub keeps redirects. The local folder keeps its name, because Claude's memory for this repository is tied to the folder's path.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- [CLAUDE.md](../../../CLAUDE.md): how the work is organised, and this machine's pitfalls.
