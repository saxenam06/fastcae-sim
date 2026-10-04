# AI-CAE landscape (2024–2026)

Compiled 2026-10-04 by a web-research subagent. **Not yet independently verified.** Many 2026 items were seen
only at abstract or HTML level. Verify each one before citing it publicly.

## 1. CAE agents, benchmarks, failure modes

### Agents
- [MechAgents '23](https://arxiv.org/abs/2311.08166) (FEniCS)
- [MCP-SIM '26](https://www.nature.com/articles/s44387-025-00057-z) (FEniCS)
- [MooseAgent '25](https://arxiv.org/abs/2504.08621): good on single physics, weak on coupled physics
- [FEABench '25](https://arxiv.org/abs/2504.06260) (COMSOL)
- [Engineering.ai '25](https://arxiv.org/abs/2511.00122) (FreeCAD + Gmsh + CalculiX + OpenFOAM)
- [AbaqusAgent '26](https://arxiv.org/abs/2606.00138): 86% of 50 tasks
- [CAX-Agent '26](https://arxiv.org/abs/2605.15218) (ANSYS APDL)
- [COSMO-Agent '26](https://arxiv.org/abs/2605.20190): RL-trained CAD-CAE loop
- CFD agents:
  - [MetaOpenFOAM '24](https://arxiv.org/abs/2407.21320)
  - [OpenFOAMGPT '25](https://arxiv.org/abs/2501.06327)
  - [Foam-Agent '25](https://arxiv.org/abs/2505.04997) and [Foam-Agent 2.0](https://arxiv.org/abs/2509.18178)
  - [ChatCFD '25](https://arxiv.org/abs/2506.02019)

### Benchmarks
- [FEM-Bench '25](https://arxiv.org/abs/2512.20732)
- [CFDLLMBench '25](https://arxiv.org/abs/2509.20374)
- [EngDesign '25](https://arxiv.org/abs/2509.16204)
- [EngiAI '26](https://arxiv.org/abs/2605.19743)
- [StructureClaw '26](https://arxiv.org/abs/2607.14896)
- [MecEng '26](https://arxiv.org/abs/2608.14615): Exudyn flexible multibody plus Hurty-Craig-Bampton, with eigenfrequency checks
- [VEHBench '26](https://arxiv.org/abs/2607.18181): analytical oracle
- [SimulCost '26](https://arxiv.org/abs/2603.20253)
- [Hephaestus-CCX '26](https://arxiv.org/abs/2605.17448): CadQuery → Gmsh → CalculiX; stress, modal and buckling
- [CADEngBench '26](https://arxiv.org/abs/2608.09296): linear-static only

### What works
- **Retrieval plus repair from execution feedback** makes runs executable: FoamBench 71.8% → 96.4%.
  - A single agent beat a multi-agent setup ([study '26](https://arxiv.org/abs/2609.03718)).
- **Typed, traceable tools**: 22% → 83% end-to-end (StructureClaw).
- **Recovery ladders**: 69% → 93% (CAX-Agent).

### Reported failures
- **Hallucinated or incomplete inputs** (FEABench):
  - hallucinated interfaces: interface factuality 0.54–0.85;
  - wrong boundary-condition dimensionality;
  - low recall of material properties: 0.08–0.32.
- **Workflow mistakes** ([study](https://arxiv.org/abs/2609.03718)):
  - missed hidden boundary conditions;
  - over-trusting tutorials;
  - divergent runs.
- **"It runs" does not mean "the physics is right"**:
  - LLM-judged scores and field-level scores differ by about 20 points.
  - ChatCFD: 82% of runs execute, but only 68% are physically faithful.
  - CADEngBench: 58% of runnable parts violate their specs, and physics agreement is uncorrelated with geometry validity.
- **Silent errors**:
  - [false summit / silent drift](https://arxiv.org/abs/2606.21841);
  - [silent defaults](https://arxiv.org/abs/2603.00214);
  - [Modelica](https://arxiv.org/abs/2608.23653).
- **Flexible multibody**: frame, mass and inertia mistakes (MecEng).
- **Hephaestus-CCX**: zero strict passes on first attempts for GPT-5.5 and Opus 4.7.
- **Unit errors**: none isolated in the sources found (uncertain).
- **Benchmark gaming**: a PhysicsX agent [reverse-engineered PLAID's hidden simulator](https://www.physicsx.ai/newsroom/how-an-ai-agent-cracked-an-industry-benchmark).

## 2. LLM-to-CAD (by CAD kernel)

### CadQuery (dominant)
- [CAD-Recode '25](https://arxiv.org/abs/2412.14042): point cloud → code; 1M synthetic programs
- [CADCodeVerify/CADPrompt '25](https://arxiv.org/abs/2410.05340)
- [CAD-Coder (MIT) '25](https://arxiv.org/abs/2505.14646): 163k pairs
- [CAD-Coder (NeurIPS) '25](https://arxiv.org/abs/2505.19713): GRPO
- [Text-to-CadQuery '25](https://arxiv.org/abs/2505.06507)
- [BenchCAD '26](https://arxiv.org/abs/2605.10865)
- [MUSE '26](https://arxiv.org/abs/2605.28579)
- [Zero-to-CAD '26](https://arxiv.org/abs/2604.24479): 1M programs plus embeddings, no physics

### FreeCAD (tool-using agents)
- [Query2CAD '24](https://arxiv.org/abs/2406.00144): macros, 53.6% first try
- [CAD-Assistant '25](https://arxiv.org/abs/2412.13810)
- [RealCADBench '26](https://arxiv.org/abs/2609.03773)
- [AADvark '26](https://arxiv.org/abs/2604.15184): assemblies

### Other kernels
- **OpenSCAD:** [CADAM](https://github.com/Adam-CAD/CADAM)
- **build123d:** community agents only, e.g. [maker-agent](https://github.com/Anthonyhangprinter/maker-agent). No paper found (uncertain).
- **No kernel:** [Text2CAD '24](https://arxiv.org/abs/2409.17106) uses DeepCAD sketch-extrude sequences.

### Typical failures
Sweeps and lofts get flattened into extrusions, and parts that look valid are not functional (BenchCAD, MUSE).

## 3. Physics-labelled datasets

### Structural
- **[SimJEB '21](https://arxiv.org/abs/2105.03534)**
  - 381 hand-designed brackets; 4 static load cases (OptiStruct).
  - Formats: STEP, tet VTK, OBJ, CSV. **No modal labels.**
- **[DeepJEB '25](https://arxiv.org/abs/2406.09047)**
  - 2,138 designs sampled from an auto-decoder latent space (263 seeds).
  - Labels: static, first two free-free modes, mass properties (Altair solvers).
  - Formats: STL, STEP, VTK, H5, PNG. Licence: CC BY-SA.
- **[DeepJEB++ '26](https://arxiv.org/abs/2606.12994)**
  - 15,360 designs via 2D-latent augmentation.
  - Labels: mass, stress and displacement only. Release promised, not yet out.
- **[SFEM '25](https://huggingface.co/datasets/cmudrc/SFEM)**
  - About 16k BrepGen shapes meshed with Gmsh; static stress.
  - Formats: PyG graphs plus STEP.
- **[Vibrating plates '24](https://arxiv.org/abs/2310.05469):** 12k beaded plates × 300 frequencies.
- **Lattices and heat sinks:** only paper-specific sets, e.g. a heat-sink set in the [operator study](https://arxiv.org/abs/2510.05995).
  No standard open dataset found (uncertain).

### Fluids
- **[DrivAerNet++ '24](https://arxiv.org/abs/2406.09624)**
  - 8k cars by ANSA morphing (26 parameters, LHS); OpenFOAM RANS.
  - Labels: Cd/Cl, Cp, wall shear, volume fields.
  - Formats: STL, parameter CSV, point clouds, VTK. Size: 39 TB.
- **[AirfRANS '22](https://proceedings.neurips.cc/paper_files/paper/2022/file/94ab7b23a345f93333eac8748a66c763-Paper-Datasets_and_Benchmarks.pdf):** 1k parametric NACA RANS cases.
- **[CarBench '25](https://arxiv.org/abs/2512.07847)**

### Dataset infrastructure
- [PLAID '25](https://arxiv.org/abs/2505.02974) (Safran)
- [EngiBench '25](https://arxiv.org/abs/2508.00831)
- [PhysicsBench '26](https://arxiv.org/abs/2608.24056)
- [ChannelFlow-Tools '25](https://arxiv.org/abs/2509.15236): config-driven SDF + LBM pipeline

## 4. Representations

### CAD-native
- [DeepCAD '21](https://arxiv.org/abs/2105.09492) command sequences.
- CadQuery programs.
- B-rep graphs: [UV-Net](https://arxiv.org/abs/2006.10211), [BRepNet](https://arxiv.org/abs/2104.00706).
- [BRepCLIP '26](https://arxiv.org/abs/2606.05515) aligns B-reps with CLIP embeddings.
- **Caveat:** one solid has many valid B-reps, so B-rep encoders are unstable ([2026](https://arxiv.org/abs/2609.11573)).

### For physics regression
Point clouds are the common denominator.
- **[Operator study '25](https://arxiv.org/abs/2510.05995):** 12 neural operators on six 3D datasets, all as point clouds.
  - Transolver is best on cars; DCON on heat sinks and brackets.
  - Freeform JEB brackets are hardest; best error 29.8%.
- **Mesh graphs:** [MeshGraphNets '20](https://arxiv.org/abs/2010.03409); [StructBench '26](https://github.com/qilinli/StructBench) baselines.
- **Grids and SDF:** [FNO '20](https://arxiv.org/abs/2010.08895), [GINO '23](https://arxiv.org/abs/2309.00583).
- **Transformers:** [Transolver '24](https://arxiv.org/abs/2402.02366), [AB-UPT '25](https://arxiv.org/abs/2502.09692),
  [DoMINO '25](https://arxiv.org/abs/2501.13350).
- **B-rep or feature graph → FEA:** only [CarHoods10K '26](https://arxiv.org/abs/2606.06405) (abstract-level).
- **Synthesis:** no CAD-native representation is yet standard for modal regression.

## 5. Structural-dynamics ML

### Surrogates
- [FQ-Operator '24](https://arxiv.org/abs/2310.05469): frequency queries on plates; beats DeepONet and FNO.
- [FE-mesh Graphormer eigen-surrogate '26](https://link.springer.com/article/10.1007/s00366-026-02310-8)
  - Over 99% frequency accuracy, 196× faster.
  - Needs a modal-matching loss (abstract-level).
- [BiW mode-shape classification GNN '26](https://arxiv.org/abs/2604.07781)
- [GNSS '25](https://arxiv.org/abs/2510.25683): impulse dynamics.

### ML plus model-order reduction
- [GNN+ROM on non-parametric geometry '24](https://arxiv.org/abs/2406.02615)
- [ML surrogate elements with SPSD stiffness '23](https://arxiv.org/abs/2307.05434)
- [AE/LSTM MOR '21](https://arxiv.org/abs/2109.11213)
- No paper found that pairs learned geometry embeddings with Craig-Bampton (uncertain).
- [StructBench v0.3](https://github.com/qilinli/StructBench) explicitly excludes modal tasks.

### LLM plus modal
- [Ansys-MCP demo '26](https://github.com/vamshidharre/Modal_Analysis)
- [freecad-fem-mcp](https://github.com/ymiya55/freecad-fem-mcp)
- No agent benchmark for NVH or FRF found (uncertain).

## 6. Commercial players

### AI-assisted CAD
- **[Hestus](https://www.unite.ai/hestus-raises-7-4-million-seed-to-bring-ai-into-mechanical-engineering/):** Fusion sketch autocomplete; $7.4M seed (Oct 2026).
- **[MecAgent](https://mecagent.com/):** natural-language-to-CAD macros inside SolidWorks, CATIA, Inventor and Creo.
- **[Leo AI](https://www.engineering.com/leo-ai-can-now-generate-full-cad-assemblies/):** text-to-assembly with calculations and part search; mates are manual.
- **[Bananaz](https://www.engineering.com/bananaz-launches-ai-design-agent-for-mechanical-engineers/):** DFM and GD&T design-review agent; no simulation.

### Physics-AI platforms
- **[PhysicsX](https://ventureburn.com/physicsx-raises-300m-to-transform-engineering-with-ai/):** $300M Series C (Jun 2026).
- **[Neural Concept](https://www.finsmes.com/2025/12/neural-concept-raises-100m-in-series-c-funding.html):** CAD-native, physics-aware; $100M Series C.
- **[Luminary](https://siliconangle.com/2025/09/15/luminary-cloud-raises-72m-advance-ai-driven-physical-product-design/):** "Physics AI Model Factory".

### Simulation agents and orchestration
- **[Navier AI](https://navier.ai/):** an agent runs CAD → mesh → solve → report across 12+ open solvers, with reviewable plans.
- **[SimScale](https://www.engineering.com/simscale-launches-engineering-ai-agent-within-onshape/):** agent inside Onshape proposes physics and boundary conditions, with human checkpoints.
- **[Synera](https://siliconangle.com/2026/04/14/german-startup-synera-lands-40-million-automate-engineering-workflows-ai-agents/):** orchestration over 80+ CAx tools; $40M Series B.

### Text-to-CAD and incumbents
- **Text-to-CAD:** [Zoo](https://3dprintingindustry.com/news/open-source-ai-text-to-cad-software-by-zoo-unlocks-accessible-3d-design-236964/); Adam (CADAM, above).
- **Siemens:** [Simcenter PhysicsAI + Altair](https://news.siemens.com/en-us/siemens-simcenter-summer-2026/).

## Gaps an open-source project could fill (subagent synthesis)

1. **A benchmark for choosing and escalating reduced-order models.**
   - Nothing found tests whether an agent identifies the governing parameters, picks a model class
     (SDOF, beam, plate, Craig-Bampton-reduced, full FE) and escalates when assumptions break.
   - Near-misses:
     - MecEng prescribes Craig-Bampton and grades only the construction.
     - VEHBench covers one device.
     - SimulCost tunes numerics, not model form.
   - The only escalating multi-fidelity agent found is for power grids ([Grid-Mind '26](https://arxiv.org/abs/2602.20683)).
   - [AnkusDrive '26](https://github.com/gchen19/AnkusDrive) ships hand-calc oracles but does not evaluate the choice.
   - Use parameterized hidden tasks (lesson from the PhysicsX leak) and open solvers.
2. **Physics checks plus fault injection for CAE tool protocols.**
   - Silent failures dominate. StructureClaw's 22% → 83% shows that tool design matters.
   - FreeCAD MCPs already provide tool access (AnkusDrive with 280+ tools, freecad-fem-mcp, Engineering.ai),
     so "another MCP" is *not* a gap.
   - Add invariants:
     - unit consistency;
     - reaction equilibrium;
     - rigid-body-mode count;
     - mass participation;
     - mesh convergence.
   - Inject faults and score whether they are detected:
     - a ×1000 unit slip;
     - a dropped constraint;
     - a wrong boundary-condition dimension.
3. **An open, program-level, multi-label dataset.**
   - Existing datasets fall short:
     - Zero-to-CAD is geometry only.
     - DeepJEB is one family, on commercial solvers, with no parametric intent.
     - SFEM is random BrepGen shapes, static only.
     - SimJEB and CADEngBench are static only.
     - DeepJEB++ has no modal labels and is unreleased.
   - Opportunity: CadQuery families → Gmsh → CalculiX (static, modal, thermal).
     - Ship the program, parameters, STEP, mesh graph, point cloud / SDF and embeddings.
     - Make it PLAID-compatible.
4. **A modal / NVH surrogate benchmark on 3D CAD parts.**
   - StructBench and the six-dataset operator study exclude modal tasks. The only open vibration set is plates.
   - Eigen-surrogates need mode-matching losses.
   - Opportunity:
     - MAC-based metrics and permutation-invariant losses;
     - Craig-Bampton-reduced FRF targets;
     - a loop in which an agent trains a surrogate (shown so far only for [subsurface flow](https://arxiv.org/abs/2604.11945)).
5. **A head-to-head comparison of representations for physics.**
   - Operator benchmarks use only point clouds.
   - B-rep encoders are validated on retrieval and classification, and break under repartitioning.
   - Only CarHoods10K tries feature graphs → FEA.
   - Compare program / feature-graph / B-rep against point cloud / SDF / mesh-graph on static and modal targets.

**Synthesis (inference):** gaps 1 and 2 form the evaluation core; gaps 3 and 4 supply the data.
The company's turbomachinery roots suggest a rotating-machinery modal/thermal case would resonate.
