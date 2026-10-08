# zenryx - how we work in this repository

zenryx designs housings from requirements. The engineer states a gearbox's functional interfaces, loads, package, targets and one manufacturing process. Agents run design campaigns over deterministic tools: they choose and revise the structural hypotheses, while the tools compute every derived quantity and give every verdict. Each design is FE-proven, and every decision and its consequence is kept as data. It is a general platform; the EV two-stage reducer housing is its first family. This page is read by every Claude session and every person who clones the repo: how the work is organised, where its state is kept, and what to watch for.

## Where things are

- **[docs/status.md](docs/status.md) - the board.** Every feature, its state, who works on it, what comes next. Start here.
- **`docs/features/<feature>/status.md` - each feature's page:** what runs, the rules in force, what is measured, the decisions, what is open, and its PBIs (Now, Next, Done). The feature's design documents sit beside it in its folder.
- **The plan of record:** [docs/features/product/plan.md](docs/features/product/plan.md). **The decisions, with their evidence:** [docs/features/product/decisions.md](docs/features/product/decisions.md).
- **Research:**
  - This repository's notes: [docs/research/](docs/research/README.md).
  - fastcae's research library at `../fastcae/docs/research/`. Its five reports of 6-7 October (geometry, plans, gearbox engineering, AM, AI) are the evidence the plan rests on.
  - Read the indexes before researching anything again.
- **Inputs from outside:** fastcae's `../fastcae/docs/inputs/`. It holds the engineer's plans of 6 October, the reviewer's suggestions and the Q&A record.
- **The archive:** [docs/archive/](docs/archive/). This repository's earlier gearbox and bracket plans, superseded by the plan.
- **fastcae** (`C:\Work\fastcae`, tag `fastcae-v1`) is the earlier rib application, frozen. It is a reference to read and copy from, never a dependency.
- **Session scratchpads are temporary.** Anything worth keeping is copied into the repo the same day.

## Independence from fastcae

- **Nothing in this repository imports fastcae.** When new code needs something fastcae has proven, it is copied from the tag `fastcae-v1`, only when it is needed. Read it with `git -C ../fastcae show fastcae-v1:<path>`, or from the folder itself.
- **Every copied file is traceable.** It starts with a header naming its origin (`fastcae-v1:<path>`) and what was changed. A parity test in `checks/` shows it gives the original's result, for example the cuDSS solve within 10⁻¹⁰ on a reference mesh.
- **fastcae's untracked data is never touched:** `assets/`, `results/` and its `.venv`. Its GRC files never come here.

## How the work is organised: features and PBIs

1. **Every piece of work belongs to a feature.** The features are the rows of the board. A request that fits no feature starts a new one before the work starts: copy [docs/features/_template.md](docs/features/_template.md) to `docs/features/<name>/status.md`, give it a PBI key of three capitals, fill its header, and add its row to the board.
2. **Work is done in PBIs.** A PBI is a piece of work one person can finish in a day or two, with a check that says it is done. Its id is `<KEY>-<n>`. It moves **Next** (in order; the top one is taken next) → **Now** → **Done** on its feature's page.
3. **Claim before starting.** Move the PBI to Now with your name, laptop and branch, and push that change.
4. **Rewrite the feature's page at every milestone:** a run launched, a result measured, a root cause found, a decision taken with the engineer, a commit made. Rewrite what changed and stamp the date and time in the header. The page says what is true now; it never grows a log - the history is git's. A shared hook reminds a Claude session when no status page has been rewritten for 20 minutes of work.
5. **Runs.** A run you launch goes in Now: what it is, its id, whose laptop, when it started, when it should end, where its results land. When it ends, its numbers go to Measured. `data/` is not in git, so a number not written there is lost to everyone else.
6. **Done means done everywhere.** A PBI is done when its code, its checks and its feature page go in together: the Done row with its commits, What runs, Rules in force and Measured brought up to date, Next re-ordered.
7. **Before stopping**, the feature page says exactly where each PBI in Now stands and its next step.
8. **Branches.** Each PBI on its own branch, `<feature>/<KEY>-<n>-<few-words>`, taken from `main` and merged back when it is done.
   - **For now, one branch for everything** (the engineer, 8 October 18:20). Until the workflow runs end to end, every PBI's work goes on `product/end-to-end`. A PBI's page still names its PBI, so the commits say which PBI they serve. Branches per PBI come back after that.
9. **Decisions.** A decision taken with the engineer goes into the feature's Decisions table with its date and who took it. One that changes the product goes into the product page as well.

## Working here

- **Build and check.** `uv sync --all-extras` builds `.venv` from `uv.lock` (Python 3.12; cadquery 2.8.0 on cadquery-ocp 7.9.3.1.1). Then:
  - `uv run pytest checks -q`;
  - `uv run ruff check src checks`;
  - `uv run ruff format --check src checks`.

  CI runs the same (`.github/workflows/checks.yml`).
- **Example contracts** are written by `checks/data/contracts/make_examples.py`. Run it after any change; the checks fail when a file is stale.
  - `ivanov2018_posed.json` is the product's one contract, the first (the engineer, 8 October). It is the only one the UI shows (`zenryx.api.snapshot.CONTRACTS`).
  - The other three are the validator's fixtures.
- **The web UI** (`web/`, PLT-4): React 19 + Vite 7 + TypeScript, no other dependency; its design is `docs/features/platform/2026-10-08-ui-design.md`.
  - It shows the product's flow (contract → campaign → hypothesis → design → grade → datapoints), never a prototype's output. What is not built yet is drawn blank, never filled with example numbers.
  - It reads `web/src/records/snapshot.json`, written by `uv run python -m zenryx.api.snapshot`. Run that after any contract change; a check fails when the snapshot is stale.
  - Check: in `web/`, `npm ci` then `npm run build` (types and bundle). CI runs the same. In PowerShell, type `npm.cmd` for `npm` (see the pitfalls).
  - `npm run dev` serves it on port 5190: a server, so only on the engineer's word. To look at it without one, screenshot `web/dist/index.html` with headless Edge and `--allow-file-access-from-files`.
- **Prototypes** live in `prototypes/`, labelled as prototypes. Nothing in `src/` imports them, and their outputs go to `data/` (gitignored).
- Claude commits, pushes and starts servers only when the person it works for says so.
- Ask the engineer before changing a limit in a contract, a process profile's value, a load case or the FE budget.
- **Derived physics is computed, never written.** Every derived quantity (forces, reactions, mesh orders, margins) comes from a deterministic, versioned tool. The agent never writes one. The deterministic evaluator decides PASS or FAIL.
- **No part-specific code in the core.** Things are named by geometric kind (a cylindrical seat, a fastener circle). Domain roles live in data, under a domain module (`src/zenryx/domains/<family>/`).
- **Nothing an agent reads in a benchmark run may hold a result, a lesson or advice from another run.** Agent runs happen in clean folders outside this repository (`../fastcae-agent/runs/<run>/`).
- **Licences:**
  - No third-party part data (CAD, drawings, decks) in git, and no paid standards (AGMA, ISO, IEC files).
  - GRC data is not used by zenryx, not even for checks (the engineer, 8 October). It never enters this repository (NLR's licence). zenryx works from published requirements and standards.
- **Claims.** A design is labelled with its rung (simulation-feasible, process-rule-feasible, …), never "production-ready". A difference inside the measured mesh noise is a tie.
- Keep this page current: a new feature, tool family, doc, agreed working rule or pitfall gets its line here the same day.

## Pitfalls on this machine (learned in fastcae; they hold here)

- **Encoding:** never rewrite a source with PowerShell's Get-Content or Set-Content; it double-encodes ·, ← and ×.
- **npm in PowerShell:**
  - The execution policy is Windows' default ("Restricted", every scope Undefined), so PowerShell refuses `npm.ps1`. Type `npm.cmd` instead, e.g. `npm.cmd run dev`, or use Git Bash or cmd.
  - Windows PowerShell 5.1 has no `&&`: run the commands one by one, or join them with `;`.
  - Setting `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` would remove the npm problem; that is the engineer's choice, never Claude's.
- **Heredocs:** never patch files through a Bash heredoc. Quotes break, and `\\` collapses so that `\f` becomes a form feed (it did on 7 October). Write the script to a file, then run it.
- **Servers:**
  - Run the API without uvicorn's `--reload`. On Windows its reload sends `CTRL_C_EVENT` to every process on the console, the UI's dev server included.
  - zenryx's API and UI use their own ports, not fastcae's 8021 and 5183: the UI 5190, the API 8030.
- **Heavy jobs:**
  - A mesh, a topology optimisation or a dataset run takes the machine: run one heavy job at a time, with nothing heavy beside it.
  - Check the free memory first: meshes have peaked near 13 GB of 16. The laptop blue-screened twice on 2 October (bug check 0x116) while heavy GPU and memory work ran beside the engineer's.
  - Ask before heavy work while the engineer is at the laptop.
- **The FE ceiling:** the 8 GB card's single-precision cuDSS factor holds about 412,667 TET10 (2.18 M unknowns). The factor is single precision on purpose; never add a double factor. On this laptop the least member is therefore about 4 mm (plan, section 5.3).
- **Efficiency cores:** Windows may run a windowless background process on the efficiency cores at their low clock. A long-running process of ours asks for full speed (fastcae's `runner.full_speed()` shows how), and a timing measured without that can mislead.
- **Runners** (when one is copied here):
  - Start one heavy job, see it running, then the next. Two jobs submitted within seconds once started two runners.
  - Stopping a watcher with `taskkill /T` kills its child agent session.
- **CP-SAT repeatability:** one search worker and a deterministic limit (`max_deterministic_time`), not a wall-clock one. Log OPTIMAL or FEASIBLE, and break ties explicitly.
- **Ignore rules are anchored:** `/data/`, `/assets/` and `/results/`, never a bare `data/`. A bare `data/` also hides `checks/data/` (the example contracts) and `web/src/data/` (the UI's Data tab). It did until 8 October, so a commit would have left them out.
- **Unusual paths:** never hand an unusual path (`\\?\`, relative, empty) to a call that deletes or overwrites. Stage in a short temp folder and check the path first.
- **Usage limits:** a Claude session limit can stop long agent work mid-way. On 6 October it stopped three research agents. Give long work a resume path, and write results to files as they come.
