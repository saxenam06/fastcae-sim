# CAD generation approaches and bracket datasets

Researched 2026-10-05 for the bracket direction. Items marked *verified* were fetched and read in the main session.
The others come from search-result summaries or subagent notes and must be checked before they are cited publicly.

## 1. Bracket datasets

| Dataset | Designs | How they were made | Labels | Formats | License | Status |
|---|---|---|---|---|---|---|
| **SimJEB** (2021) | 381 | Human designs from the GrabCAD *GE Jet Engine Bracket Challenge* (700+ entries, 320 designers, 56 countries), cleaned and categorised | 4 static load cases; per load case, displacement X/Y/Z, magnitude and von Mises stress at the vertices | CAD, tetrahedral mesh, surface mesh, results | Dataset CC0, but the **CAD files are licensed for non-commercial use by GrabCAD** | *verified* (abstract and search summary) |
| **DeepJEB** (2024) | 2,138 | SDF auto-decoder (8 × 512 layers, 128-d latent) trained on 263 SimJEB seeds: 4,833 generated → 2,737 well-formed → 2,138 after outlier removal | 4 static cases (35.6 kN vertical, 37.8 kN horizontal, 42.3 kN diagonal, 565 kN·mm torsion); free-free modes 1–2; max displacement and stress; Ti-6Al-4V; TET10, about 2 mm | STL, VTK, STEP, FEM deck, CSV, H5, 26 PNG views, JSON | Open Data Commons Attribution | *verified* (paper HTML) |
| **DeepJEB++** (June 2026) | 15,360 | Fewer than 400 seeds → 2D latent-diffusion fine-tuning, latent interpolation, VLM quality filter, image-to-3D foundation model, automated FE labelling | Mass, stress, displacement | 3D meshes (plus 2D renders) | "Will be made publicly available" | *verified* (abstract) |

**The common origin: the GE Jet Engine Bracket Challenge (2013).**
- **Interfaces:** a 0.75 in clevis pin (rigid) plus 4 × 0.375-24 bolts (rigid).
- **Loads:** 8,000 lbf vertical, 8,500 lbf horizontal, 9,500 lbf at 42°, and 5,000 lbf·in torsion.
- **Material:** Ti-6Al-4V, with a minimum wall of 0.050 in. The top ten designs were additively manufactured and tested.
- The **fixed bolt and load locations** form part of the specification, and only the shape in between varies.

Sources: GrabCAD challenge page (search summary).

**What none of these datasets has:**
- sheet metal (bends, flat patterns, press-brake rules);
- random vibration or fatigue beyond the first two free-free modes;
- thermal labels;
- natural-language intents;
- editable feature programs;
- agent decision logs;
- requirement-specific pass/fail.

All three are additive-style titanium brackets with static loads.

**A possible use for us:** DeepJEB ships FE decks and results under an attribution licence. Re-solving a sample with
our grader would be an independent cross-solver check against Altair's results.

## 2. Ways to generate CAD

| Approach | Examples | Output | Strengths | Limits for us |
|---|---|---|---|---|
| Parametric CAD scripting (templates, features) | FreeCAD PartDesign + SheetMetal workbench; CadQuery; NX Open | Editable feature models | Deterministic; manufacturable by construction; editable | Limited by the feature vocabulary |
| Generative design: topology optimisation | Altair Inspire/OptiStruct, Autodesk Fusion, nTop | Density field → organic shape | Physics-driven | Organic shapes suit additive or casting, not sheet metal |
| Generative design: **topography optimisation** | OptiStruct, Inspire | **Bead patterns on sheet** | Maximises stiffness and eigenfrequency **without adding mass**. The classic sheet-metal method | Gives a bead field that must be turned into formable beads (wider beads form more easily but stiffen less) |
| Deep generative shape models | DeepCAD, BrepGen, SDF auto-decoders (DeepJEB), diffusion + VLM (DeepJEB++) | Meshes, SDFs, CAD sequences | Many novel shapes for expanding a dataset | Not aware of physics or manufacturing; mostly not editable features |
| LLM text-to-CAD code | CAD-Recode, CAD-Coder, Text-to-CadQuery, Zoo | CAD code | General shapes from text | **RealCADBench (Sept 2026):** 12,632 industrial design-intent tasks with FreeCAD-API code. Across 9 frontier models, executability 0.565–0.812, solid IoU 0.28–0.54; failures: missing fine structures, loss of part identity |
| Agentic CAD with feedback | FreeCAD MCP servers (render or screenshot after each step), gencad (headless FreeCAD over MCP), CADDesigner | Editable FreeCAD models | Iterates on what it sees | Geometry only: no physics or manufacturing verification |

**Implication for us:**
- Use **agentic parametric generation with physics in the loop.** The design is a typed sheet-metal feature program in
  FreeCAD, edited through typed tools and judged by FE and manufacturing rules.
- Other approaches **propose** designs:
  - space-filling sweeps;
  - an optimiser;
  - **topography-style sensitivities for bead placement**;
  - agent concept edits;
  - invented features through a gate;
  - later, a learned generator trained on our own data that outputs **feature programs, not meshes**.

## Sources

- SimJEB: https://arxiv.org/abs/2105.03534 · https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/XFUWJG
- DeepJEB: https://arxiv.org/abs/2406.09047 (HTML: https://arxiv.org/html/2406.09047) · https://www.narnia.ai/dataset
- DeepJEB++: https://arxiv.org/abs/2606.12994
- GE Jet Engine Bracket Challenge: https://grabcad.com/challenges/ge-jet-engine-bracket-challenge
- RealCADBench: https://arxiv.org/abs/2609.03773
- gencad (headless FreeCAD over MCP): https://github.com/gurul/gencad
- FreeCAD MCP guide: https://mcp.directory/blog/freecad-mcp-complete-guide-2026
- CADDesigner: https://arxiv.org/pdf/2508.01031
- Topography optimisation: https://help.altair.com/inspire/en_us/topics/inspire/tutorials/tut_opti_topography_c.htm ·
  https://altair.com/optistruct/capabilities
- Bead patterns: https://doi.org/10.18311/jmmf/2025/47429 ·
  https://www.sciencedirect.com/science/article/abs/pii/S0965997812001731
