# Two job descriptions, read against zenryx

**Date.** 8 October 2026, 09:20-09:40. The engineer pasted both posts in the session.

**The posts:**
- **MEKINT** (Mechanical AI, Inc.), "Research Engineer, Mechanical Intelligence". The company is researched in [2026-10-04-mechanical-ai-company.md](2026-10-04-mechanical-ai-company.md).
- **An AI-training role:** "Mechanical Engineering Expert to contribute to an AI training project". It matches micro1's "simulation AI training" post (role 5) in fastcae's [job-description notes](../../../fastcae/docs/research/2026-10-03-job-descriptions.md). micro1 is an agency that supplies expert-made training data to AI labs.

## 1. What datapoints each creates

| | MEKINT (Research Engineer) | The AI-training role |
|---|---|---|
| **One datapoint** | A synthetic design from their own pipeline: CAD template → sampled parameters → physics labels. It is stored "embedding-friendly" (point clouds, distance fields, graphs) for their networks | One engineering task: a physical requirement, then the expert's whole solution as code (geometry → mesh → materials and boundary conditions → solve → post-process), then the verdict on whether it meets the constraints |
| **For the LLM** | Agent trajectories (goal → tool calls → results → revisions), and reasoning that "characterises physical elements and governing principles": which parameters govern, and which reduced-order model fits | The task used three ways: (a) imitation from the expert's solution; (b) grading ("reviewing and validating") a model's attempt; (c) a practice environment, with the solver as an automatic checker |

Both are close to what the zenryx factory produces on its own:
- a frozen contract plus the judge is a graded task;
- a campaign is a trajectory.

See [the data design](../features/data/2026-10-08-data-tasks-and-learning-design.md). The AI-training role makes such tasks by hand, at $80-150 an hour (fastcae's notes).

## 2. Where zenryx stands, 8 October

✓ done · ◐ partly · ✗ not yet. "fastcae" is the earlier, frozen project; "zenryx" is this repository.

| Requirement (the posts) | Status | Evidence |
|---|---|---|
| Agentic data generation of manufacturing-grade synthetic designs | ◐ | fastcae: agent campaigns and 369 FE-proven designs. zenryx: the contract with provenance and replayable tasks; one die-castable variant checked for draft, wall and voids. No dataset yet |
| Embedding-friendly representations | ◐ | The prototype's distance-field grid (`field.npz`). The recipe and point clouds are planned (plan §9). Nothing trained on them |
| Tool interfaces: structural | ◐ | fastcae: GPU FE (cuDSS, TET10), within 10⁻¹⁰ of Code_Aster. zenryx: not yet copied (PHY-1, the FE solve) |
| Tool interfaces: fluid, heat transfer, aerothermal | ✗ | A uniform-temperature case is planned (P2) |
| Automated CAD operations | ✓ | The prototype's CadQuery core; fastcae's OpenCascade rib geometry |
| Building and training design agents | ◐ / ✗ | fastcae: real agent campaigns against a fixed workflow (single runs). Fine-tuning: none |
| Governing parameters and reduced-order models (MEKINT must-have) | ◐ (a strength not yet presented) | Housings judged by misalignment per face width (about 3 % on KHβ per µm); shafts as two-support beams for the seat loads; the relaxed topology bound; fastcae's screen calibrated against FE; unit-load superposition |
| First principles across thermal, fluid, structural, dynamic | ◐ | Structural ✓; dynamic (modes) planned; thermal by arithmetic (fit loss); fluid ✗ |
| Python, execution speed, coding agents, Claude Code multi-agent work | ✓ | 7-8 October overnight: the environment, the contract (93 checks) and the prototype, about 1.5 h, with subagents in parallel |
| Numerical analysis, design optimisation | ✓ | fastcae: SIMP over a rib library, CP-SAT, the GPU solver |
| Fine-tuning language models, transformers, vision networks | ✗ | Planned only (plan §10) |
| CAD software (CATIA, NX, FreeCAD) | ◐ | CadQuery and OpenCascade only; FreeCAD later (D5, core CAD); no NX or CATIA |
| Cloud batch (GCP, AWS) | ◐ | agenticCAE ran 490 designs on GCP Slurm; zenryx none |
| Geometry, meshes, materials, loads, constraints, solver inputs | ✓ | fastcae: decks, gmsh TET10, couplings. The prototype: core, field, mesh boolean |
| Contacts | ✗ | None |
| Structural, thermal, dynamic, fatigue, buckling, vibration analyses | ◐ | Static ✓; modes planned (PHY-3, modes); thermal planned; fatigue and buckling ✗ |
| CalculiX, Gmsh, Elmer, FEniCSx, CadQuery, OpenSCAD, OpenFOAM | ◐ | Gmsh ✓; CadQuery ✓; CalculiX planned as the open cross-check; the others ✗ |
| Degrees and professional experience | - | Personal to the engineer; not assessed here |

## 3. The fastest ways to close the gaps that matter

1. **PHY-1 (the judge's FE solve), then modes.** zenryx's designs become simulation-proven: structural plus vibration.
2. **A CalculiX cross-check of one design.** Both posts name open tools, and the plan already lists CalculiX as the open check.
3. **Write up the governing-parameter story.** A housing is judged at its bearing seats; here is the reduced model, and here is how it predicts the FE. That is MEKINT's must-have.
4. **Ten replayable tasks with their grader.** What the AI-training role makes by hand, generated by the factory.
5. **Later, a small fine-tuning demonstration on decision records.** The clearest ✗, but sensible only once the agent has run real campaigns.
