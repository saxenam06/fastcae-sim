# fastcae and fastcae-agent, audited against the MEKINT Research Engineer post

**Date.** 4 October 2026, 22:50–23:20 IST.

**Scope.** This is a read-only audit of `C:\Work\fastcae` (210 commits, 9 Sep – 3 Oct 2026) and
`C:\Work\fastcae-agent`. It used:
- three code-reading subagents (physics and solver; agent, tools and harness; data engine);
- direct checks in the main session: git, GitHub pages, the docs.

**Not read:** `C:\Work\agenticCAE` (outside scope), `.env`, `results/` binaries. Nothing was run or modified.
The agenticCAE facts below come from fastcae's own `docs/research/agenticcae.md`.

**Tags.**
- **[code]**: read in source.
- **[disk]**: listed or opened under `results/` or `assets/`.
- **[docs]**: stated in docs only.
- **[git]**: checked with git or on GitHub.

Paths are relative to `C:\Work\fastcae`; `S` = `src/fastcae`.

## 1. Public face [git]

- **Both repos are public.**
  - `github.com/saxenam06/fastcae` opens on branch `fea/generate_fullyImplicit_geom` (46 commits pushed). Its README describes the earlier product.
  - All 210 commits of the current branch `ribs/RIB-20-horizontal-ribs` are pushed, but a visitor does not land on them.
  - There is no `main` on the remote.
- **`fastcae-agent`** has 15 PNG renders of the housing committed in its 2 local-only commits, so none are pushed.
  - The fastcae rule "Renders of the housing stay out of git until the dataset contact's written OK" holds today. It would break on the next push.
- **Already public:** one GRC-derived plot, `bench/solvers/results/gate/section_ax2.png` (a bore profile, CAD against mesh).
- **No credentials** in the tracked files of either repo (pattern scan, file names only). `.env` is untracked.
- **Tests are untracked by design** (`.gitignore`: "Tests are the assistant's working checks"). There is no CI.
- **The GitHub profile** (Manasvi Saxena, India) pins MPC and controls repos; fastcae is not pinned.

## 2. Physics and solver

- **Linear static only.**
  - TET10, isotropic: E 169,000 MPa, ν 0.275 (`S/simulate/aster.py:294-297`, `S/simulate/solve.py:265-267`, `assets/.../baseline.comm:20`).
  - No mass matrix, modal, transient, thermal or nonlinear code anywhere, not even stubs. [code]
- **Solver.**
  - Assembly in CuPy, 4-point rule (`S/simulate/solve.py:144-187`).
  - Solved by cuDSS via nvmath: single-precision Cholesky refined by double-precision CG to 1e-10, with fallbacks LDLᵀ then double (`:593-713`). [code]
  - Code_Aster runs only from `bench/` (`bench/solvers/baseline_deck.py:268,294`). [code]
- **Load case.**
  - 25 bolt groups tied to references held in translation; six bearing seats coupled to references by RBE3, loaded by forces only. Net 345.3 kN, one static case (`baseline.comm:29-85`). [disk]
  - The deck is fastcae's own stand-in, written with agenticCAE's loads, not an NREL deck (`docs/research/baseline-deck.md:3-5`). [docs]
- **The three measures** (`S/generate/solve.py:354-367`, `S/simulate/signals.py:193-203,272-287`). [code]
  - Peak = the largest |u| at any node.
  - "Strain energy %" = ½ΣF·u at the six references ÷ the rib-less deck's Code_Aster value (1,063,961 N·mm).
  - Metal is judged on the CAD since 2 Oct (`S/optimize/fe.py:35-50`).
- **Superposition exists but is unused.**
  - `components=True` solves each load component (16) on one factor and returns each seat's 6-DOF motion (`S/simulate/solve.py:256-531`). Nothing in src calls it, and it has no test.
  - There is no condensed seat compliance and no superelement. [code]
- **Agreement with Code_Aster is recorded, not enforced.**
  - On the 209,044-TET10 deck the error was ~1e-11 (`docs/research/baseline-deck.md:37-41`). [docs]
  - That result predates the mixed-precision factor (26 Sep).
  - The current deck (281,132 TET10) has no cuDSS run against Code_Aster, and no design mesh has been solved by Code_Aster.
  - Tests cover a CPU bar only (`tests/test_simulate.py:99-111`).
- **Enforced checks.** [code]
  - Residual ≤ 1e-8 (`S/simulate/solve.py:629-639`).
  - Reaction against load ≤ 2 %, force sum only (`S/generate/build.py:352-360`).
  - Tet quality (`:309-331`).
  - The 3 % metal check has been warn-only since 3 Oct (`S/optimize/__main__.py:241,260`).
- **Noise.**
  - Re-meshing: ≤ 0.98 % displacement, 1.32 % strain energy, 0.82 % metal (`assets/.../qualify/noise.json`, 25 Sep, older route). [disk]
  - Fillet resolution moved designs 4–6 % (`docs/features/simulate/status.md:72`). [docs]
  - No h-refinement study exists.
- **The cube model** (`S/generate/paths.py`, `sizing.py`, `multigrid.py`, `S/space/physics.py`, `S/loop/worth.py`, `relax.py`). [code]
  - 10 mm binary voxels, trilinear HEX8 elasticity, float32 multigrid-CG. "SIMP" acts on rib presences.
  - Adjoint sensitivities; only the rib-drawing gradient has a finite-difference test (`tests/test_fins.py:134`).
  - Boundary conditions: clamped near the bolts (the FE frees rotation there), loads spread uniformly rather than by RBE3.
  - Calibration: two scalars, FE ÷ cube, taken from the parent design's solve (`S/loop/worth.py:468-499`).
  - Error [docs]: the bare part's ratio stands 17–28× off the ribbed designs'. Across ribbed designs the ratio holds within about 2 % (energy) and 3.5 % (peak spots). Production is 10–15 % off.
  - **It is a calibrated coarse-grid surrogate (a low-fidelity screen), not a reduced-order model:** it has no projection basis and no error estimator.
- **Mesh** [data, docs].
  - Mesh with fillets 115–231 s, solve 35–45 s; production end-to-end 380 s.
  - Peaks of 9.5–13.2 GB; two blue screens on 2 Oct.
  - gmsh crashes about 1 in 10 with no retry.
  - **`S/simulate/face_mesh.py:52,134-146` imports a file from `C:\Work\agenticCAE`**, so a fresh clone cannot mesh.
- **Estimated cost to extend** (auditor's estimates).
  - Modal: 2–3 days. Needs consistent mass at a degree-4 rule and an eigensolver; reuses the TET10 loop and the cuDSS factor.
  - Steady heat with Robin boundaries: 2–4 days.
  - Static condensation of the seat compliance: about 1 day, via `components` (36 unit cases; check F = Fᵀ and ½fᵀFf = work).
  - Craig-Bampton: 4–6 days. Needs modal and a seat interface.

## 3. Agent, tools, harness

- **Tools.** `bash optimize.sh <tool>` → `python -m fastcae.optimize agent` (`S/optimize/harness.py:410-419`, `__main__.py:225-229`). [code]
  - `S/optimize/agent.py`: state 423, propose 593, wait 871, solve 928, reflect 986, look 1216, ribs 239. Arguments parsed by argparse (1248-1282).
  - A state machine enforces the budget, at most 3 proposals a step, and reflect before the next propose (615-621, 942-950).
  - Output is JSON on stdout.
  - Typed failures exist (`S/generate/records.py:187-197`) but never reach the agent (`agent.py:849-868`).
  - **No schema per tool, no MCP:** the contract is prose in the brief (`harness.py:124-385`).
- **Harness** (`harness.py:35-36, 437-480`). [code]
  - Launch: `claude -p --model claude-opus-5-5 --effort max --setting-sources project --strict-mcp-config --no-session-persistence --disable-slash-commands --tools Bash,Read --allowedTools "Bash(bash optimize.sh:*),Read(./pictures/**)" --permission-mode dontAsk --append-system-prompt-file brief.md`.
  - The environment is stripped of CLAUDE* and ANTHROPIC* variables.
  - `guard.py` allows only the 7 tools, with no shell metacharacters, and reads only the run's own pictures. Refusals fire in every transcript. The overflow spool file is blocked too, so oversize answers arrive truncated.
  - No `--max-turns` or `--max-budget-usd`. The resume path has never been exercised.
- **Cost.**
  - $1.27–16.39 per run at API-price equivalents (billing was the subscription), from transcripts only.
  - **6 runs finished**, not 8.
- **Briefs.**
  - v1: `look` with 3 views, family and volume filters.
  - v2: the `ribs` tool and 6 views with sections.
  - v3: hypothesis and risk before each solve, reflection after.
  - v4: chained moves (`--from K`), used for 5 of its 16 solves.
  - Anti-leakage is structural (isolation). Automated checks are thin, and briefs v2–v4 carry process advice drawn from earlier rounds.
- **Results** (verified in `run.json`).

  | Round | Fixed workflow | Agent |
  |---|---|---|
  | R1 | 94.42 % | 94.60 % (neither met the goal) |
  | R2 | met at 8 FE solves | met at 4 |
  | R3, production's limits | met at 6 | met at 2 |
  | R3, 20 % less metal | 98.44 % | 98.74 (v1), 99.92 (v3), 97.85 (v3, paused at 13/16), 98.89 (v4) |

- **The comparison is not yet controlled.**
  - One run per arm per case; the repeats were never run.
  - Two v3 runs from the same first design end 2.1 points apart, more than any gap between agent and fixed workflow (≤ 1.5).
  - In R3, production's limits, the fixed workflow passed by 0.06 % and stood at 99.90 % after solve 5.
  - The arms used different metal checks.
  - Manifests show 2–5 commits inside single runs, and dirty trees in most designs. The benchmark doc's "same commit for every arm" (`docs/features/optimize/benchmark-2026-10-02.md:16`) does not hold.
  - There is no optimiser baseline: no BO or GA code exists. AGT-16 (the frozen 2×2) has not started. [code+disk]
- **Gaps.**
  - The tools are specific to this rib loop; the loop CLI hard-codes the project (`S/loop/__main__.py:37`).
  - CAD operations are not tools the agent can call.
  - Requirements in words → contract (AGT-12) is not built.
  - No subagents: the Agent tool is denied (`harness.py:393`).
  - `S/agent` is a separate read-only chat agent (LangGraph, OpenRouter, deepseek-v4-pro).

## 4. Data engine

- **What a design is.**
  - A CP-SAT-chosen subset of a placed rib library, plus a thickness per member. Each member is a 20-number row with family, kind and volume (`S/generate/fins.py:53-74`, `preview.py:126-143`). [code]
  - Library `b844caed37325549`: 805 laid, 673 placed (430 webs, 109 plates, 38 T, 96 inverted T), 132 refused, 29,832 conflict pairs, about 1.5 h. [disk]
- **Rules on the CAD.**
  - 32 numeric values, checked PASS/FAIL/UNKNOWN per member: form, arrival ≥ 45°, glue, flush, 20 mm clearance, tool access, one solid (`S/rules/member.py:105`, `S/generate/rules.py:32-150`).
  - Pair and pocket rules go to CP-SAT. [code]
- **Build.** OCC fuse → STEP and BREP (`S/generate/cad.py:124`, `fuse.py:36`) → gmsh TET10 → cuDSS. [code]
  - The SDF "field" is no longer the representation; the README is stale.
- **On disk** (`results/GRC_Gearbox_Housing`). [disk]
  - 29 campaigns: 607 records, 308 fused CADs, 235 meshed, **216 solved**.
  - Optimize: 21 runs (12 agent, 9 workflow), **153 solved**, **166 decisions**.
  - **369 FE-solved** is verified.
  - "20,279 rib candidates judged" overstates it: **20,279 laid, 5,666 judged exactly** (4,773 placed, 893 refused).
- **A record** (`campaigns/20261003-015836/02`). [disk]
  - `manifest.json`: sha256 of inputs and outputs, commit with dirty flag, package versions.
  - `design.json`: members, seed, stage times, mesh, checks, headline, verdict.
  - zarr `u[10,4096,3]`: displacement at 4,096 surface points.
  - Formats: json, STEP, BREP, npz, zarr.
- **Representations.**
  - Exist: member rows, STEP and BREP, tessellations, TET10 meshes with nodal fields, the 4,096-point field.
  - Absent: per-design SDF or voxels, point clouds with normals, POD, a table with splits.
  - **No ML model has ever been trained:** no torch, sklearn, xgboost, jax or physicsnemo imports. [code]
- **Reproducibility.**
  - The campaign sampler runs **8 CP-SAT workers**, so it is non-deterministic (`S/pipeline/sample.py:98,211`). One worker holds for the agent's tools only.
  - 399 of 460 manifests are dirty.
  - Manifests hold digests, not settings.
  - There is no config-plus-command regeneration.
  - The external agenticCAE import (section 2).
- **Generality.**
  - General: solver, mesher, fuse, CP-SAT, lineage.
  - Rib-specific: members, rules, placement.
  - Gearbox-specific: the objective.
  - One part has been run.
- **DAT-1..5** are all Next; no export, table or split code exists.
- **agenticCAE** (from `docs/research/agenticcae.md:6-12, 87-111`):
  - 490 designs solved on a GCP Slurm cluster (Cluster Toolkit, Terraform, Apptainer with Code_Aster, `sbatch` arrays).
  - 29 designs in 36 min at 14 at once; about ₹2.5 a design.
  - Datasets stored in PhysicsNeMo's Zarr layout.

## 5. Claims to correct before anyone outside reads them

| As written | What the evidence supports |
|---|---|
| A rule-valid design "beats production on all three measures" | Strain energy −0.51 % is inside the 1.32 % re-meshing noise, so by the plan's own rule (`docs/data-engine-plan.md:148-150`) it is a tie. Peak displacement −1.25 % is just outside the 0.98 % noise. Rib metal is −3.2 % on the CAD. **Say:** "matched production's stiffness within mesh noise with 3.2 % less rib metal". Re-measure the noise under today's mesher |
| "The agent met the goal in 2 FE solves, the fixed workflow in 6" | Single runs, code changing mid-run, different metal checks. A controlled benchmark (frozen commit, repeats, an optimiser arm) must come first |
| "The cube model is a reduced-order model" | It is a ratio-calibrated coarse-grid screen. The true ROM is still to build: condensed seat compliance, then Craig-Bampton |
| "20,279 rib candidates judged on the CAD" | 20,279 laid, 5,666 judged exactly |
| "Eight agent runs" | Six finished runs |
| "Checked against Code_Aster" | True to ~1e-11 on the earlier deck mesh, before the mixed-precision factor. Re-check on today's deck and two or three design meshes, as a test |
| "The engineer's FE deck" | fastcae's own deck with GRC loads (via agenticCAE) |
| "Manufacturing-grade" | Rule-valid: 32 geometric casting rules on the CAD; no foundry review |

## 6. Against the post

| The post asks | Verified today | Gap |
|---|---|---|
| Manufacturing-grade synthetic designs | Rule-valid rib variants, CP-SAT, OCC, TET10, cuDSS; 369 solved | One part; rib variants only |
| Agentic data generation | The agent's designs leave records | The agent does not steer generation toward what the data lacks |
| Embedding-friendly representations | Member tokens, STEP/BREP, meshes and fields, the 4,096-point field | No table, splits, point clouds or POD; no model trained |
| Modular tools and execution protocols | 7 JSON tools, state machine, guard, per-run isolation, manifests | No schema or MCP; failures untyped to the agent; statics only; CAD not a tool |
| Structural / fluid / heat / aerothermal | Linear statics | Modal, thermal, fluid |
| Build and train design agents | Claude Code agent with harness, briefs v1–v4 | Uncontrolled benchmark; nothing trained |
| Characterising physics and governing principles | Peak spots, FE pictures, FE÷cube ratio | Superposition code dormant; no condensed compliance; no "characterize" step |
| Governing parameters and ROMs (must) | Career: MSc in model-order reduction, SIMPACK flexible bodies | Not yet shown in fastcae |
| First principles across thermal, fluid, structural, dynamic (must) | Career: NVH, multibody, 0-D/1-D thermal | fastcae shows one physics |
| Speed, Python (must) | 210 commits in 25 days, about 40k lines in `src` | – |
| Claude Code multi-agent development | Board, PBIs, hooks, worktrees, subagents | Undocumented |
| Cloud batch (GCP) | agenticCAE on Slurm | Not on the résumé |

## 7. Proposed order (pending the engineer's choice)

1. **Front door and claims** (1–2 days).
   - Vendor the agenticCAE mesher file into the repo.
   - Track a curated test suite with CI; include cuDSS against Code_Aster on today's deck.
   - Make `main` the default branch and rewrite the README.
   - Apply the corrections in section 5.
   - Send PRD-2 (the NLR written OK); keep the `fastcae-agent` renders unpushed until it arrives.
2. **Tool contracts as an MCP server** (2–3 days).
   - Typed schemas, with the brief generated from them.
   - Structured errors that carry the typed failures.
   - Physics postconditions: 6-component equilibrium, residual, metal, mesh quality.
   - A fault-injection suite: unit slip, dropped support, flipped load, coarse mesh.
3. **Condensed seat compliance and a `characterize` tool** (1–2 days).
   - The 36 unit cases on one factor, with symmetry and work checks.
   - Load-component shares of the goal.
   - The agent states what governs the goal before its first move.
4. **Modal analysis** (2–3 days): consistent mass and shift-invert eigenmodes on the cuDSS factor, MAC against Code_Aster, frequency limits in the contract (gear-mesh orders).
5. **Steady heat** (2–4 days).
   - Bearing losses in, natural convection out by correlation (Churchill–Chu, valid range in Rayleigh number).
   - Ribs as fins, governed by the fin parameter mL.
6. **Controlled benchmark** (AGT-16): frozen commit, clean tree, same checks, ≥ 3 repeats; arms are random, the fixed workflow, BO or GA, and the agent with and without `characterize`.
7. **Frozen dataset and first models.**
   - One command plus a config, with one CP-SAT worker.
   - Aligned records with point clouds and POD.
   - A feasibility classifier on the 5,666 exactly judged candidates, then a member-set surrogate, with splits by run.
8. **Requirements in words → contract** (AGT-12), judged on 10–20 briefs.
9. **Craig-Bampton** at the bearing seats (4–6 days, after modal).
10. **Evidence package:** a 3–4 page note, a 2-minute video, the résumé entry.
