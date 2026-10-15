# Topology optimisation in practice: cast-aluminium EV reducer housings

**Research date:** 9 October 2026  
**Scope:** Two-stage EV reducer/gearbox housing; bearing-seat angular misalignment relative to the shaft line; density-based SIMP with filtering/projection and casting constraints; interpretation into manufacturable CAD.

## Executive findings

1. **Staged design is established practice.** A common practical route is topology optimisation for a concept, engineering interpretation/reconstruction, then size and shape optimisation, followed by independent FEA and validation. The automotive-engine-cradle industrial case study by Li, Kim and Jeswiet is a clear example. It reduced the mass of the initial design domain from 82.6 kg to 26.7 kg at concept stage, then to 21.4 kg after shape and size optimisation. A recent EV reduction-gearbox housing article by Jing Pu (2026) also reports multi-stage density-based topology optimisation followed by interpretation, rib/wall size and shape optimisation, and static/modal/harmonic validation.
2. **A repeated topology run is not automatically an improvement.** “Topology → CAD → topology again” is a valid engineering experiment, but it is not a universally prescribed recipe. A second run is useful when the design problem has changed for a reason: a clearer load case, a new manufacturing constraint, a deliberate frozen feature, a smaller local design domain, or a refined mesh. Freezing an arbitrary interpreted layout can lock in a poor load path or remove useful alternatives.
3. **CAD reconstruction is a design task, not just smoothing.** Manual rib interpretation remains common. PolyNURBS/subdivision, implicit/SDF-based smoothing, automated skeleton-and-loft reconstruction, and NURBS/B-rep reconstruction are all documented methods. Automatic CAD reconstruction is advancing, but a smooth surface is not the same thing as a robust, editable, cast-ready feature tree.
4. **Casting constraints are available within optimisation algorithms, but have a specific scope.** Draw/split-draw, minimum member size, symmetry, pattern repetition and projection-based manufacturing constraints can suppress important classes of unmanufacturable topology. They do not fully solve die design, coring, parting-line engineering, draft on every final face, wall-thickness transitions, porosity, fill/solidification or machining access.
5. **The closest direct gearbox evidence supports stiffness, bearing-hole displacement and NVH-driven rib development.** A 2015 EV two-stage reducer study uses dynamic bearing-seat loads and frequency-response analysis; a 2021 EV two-speed housing study reports reduced bearing-hole displacement and raised natural frequencies; a 2019 agricultural-EV gearbox study uses experimental modal correlation and strain-guided parameterised ribs. A 2012 bearing-housing study explicitly optimises bearing contact misalignment, though it is not a full EV gearbox housing.
6. **The well-known “organic” parts are often additively manufactured.** GM’s seat bracket, Airbus’s bionic partition and Porsche’s EV drive housing demonstrate the potential of generative/optimised structures, but they do not prove that those geometries can simply be transferred to high-volume die casting. For a cast housing, the designer usually translates force flow into tapered ribs, gussets, bosses and smoothly joined wall structures that the selected mould and core strategy can produce.

---

## 1. Is topology optimisation iterative in practice?

### 1.1 The normal industrial sequence

A defensible industry workflow is:

1. **Concept topology:** establish loads, supports, package, non-design interfaces, mass limits and manufacturing restrictions; run topology optimisation to discover likely material paths.
2. **Interpretation and design review:** identify meaningful paths, remove weak/disconnected branches, decide which members should be ribs or walls, add casting draft/fillets and transition geometry, preserve interfaces, and make the geometry editable.
3. **Re-analysis:** run the reconstructed geometry through the same relevant FE model and compare the actual performance—not just the optimiser's density field—with the original and the idealised topology result.
4. **Detailed optimisation:** size rib thickness/height/width, local wall thickness, boss transitions and selected shape variables; include mass, stress, displacement, modes and NVH targets.
5. **Validation:** evaluate the complete assembled boundary conditions, realistic load combinations, fatigue and manufacturing constraints; correlate the model to tests where possible.

**Direct evidence:** Chao Li, Il Yong Kim and Jack Jeswiet, “Conceptual and detailed design of an automotive engine cradle by using topology, shape, and size optimization,” *Structural and Multidisciplinary Optimization*, 51 (2015), 547–564. DOI: [10.1007/s00158-014-1151-6](https://doi.org/10.1007/s00158-014-1151-6). They report a design review and geometry revision after topology optimisation, followed by shape and size optimisation and durability validation. The initial 82.6 kg design domain became a 26.7 kg concept and then a 21.4 kg detailed design. It is a genuine automotive industrial workflow, although the component is an engine cradle rather than a gearbox housing.

**Direct gearbox evidence:** Jing Pu, “Lightweight Design and Topology Optimization of an Electric Vehicle Reduction Gearbox Housing,” *Journal of Engineering Research and Applications* (JERA), 10(2), 123–131, published 3 April 2026. [Article and DOI](https://doi.org/10.26689/jera.v10i2.14378). The article reports a multi-stage density-based process, interpretation into a smooth geometry, parametric rib-network and wall-thickness optimisation, then static, modal and harmonic-response analysis. Reported outcomes are 34.2% lower mass, 12.7% higher torsional stiffness and 15.3% higher first natural frequency. This is especially relevant by subject, but it studies a **single-stage** reducer, is very recent, and the details available in the article abstract do not establish that it used your exact seat-tilt objective or a validated high-volume cast-aluminium process.

**Another relevant gearbox case:** Steffen Jäger and Tilmann Linde, “Design and Cost Evaluation of Additively Manufactured Electric Vehicle Gearbox Housings,” *World Electric Vehicle Journal*, 16(10), 552 (2025). [Article](https://doi.org/10.3390/wevj16100552). A topology result suggested an X-shaped load path; the authors then varied rib width/height and turned-part, flange and wall thicknesses across 13 variants. That is a clear topology-to-interpreted-layout-to-parametric-refinement process. Its manufacturing proposal is hybrid laser metal deposition on a pre-machined turned part—not conventional die casting—so transfer its optimisation workflow, not its manufacturing assumptions.

### 1.2 What should we call the process?

Terminology varies by author and software. The following distinctions are useful:

- **Topology optimisation followed by shape and size optimisation:** the clearest name for the widely used concept-to-detail workflow.
- **Sequential or multi-stage optimisation:** describes separate optimisation stages with different variables, constraints or model representations. It does not, by itself, mean “run SIMP twice.”
- **Design-space refinement / local re-optimisation:** a reasonable description when the interpreted design becomes part of the fixed geometry and only selected remaining regions are optimised. Treat this as a project-specific workflow, not a universally standardised named algorithm.
- **Topology-to-topography-to-size-to-shape:** a possible chain for some parts, but **not a standard mandatory sequence**. Topography optimisation is principally useful for bead/stiffener patterns on relatively thin surfaces or sheet-like components; for a substantial gearbox housing, topology → CAD interpretation → rib/wall size and shape optimisation is usually the more relevant route.
- **Two-stage topology optimisation:** ambiguous. In the research literature it can denote a formal two-stage mathematical method for a particular objective, rather than the everyday practice of reconstructing CAD and starting another study.

A separate, genuine two-stage algorithm is described in “Density-based shape optimization for fail-safe design,” *Journal of Computational Design and Engineering* (2020). It combines an initial topology optimisation with a second density-based shape optimisation that changes the outline to seek fail-safe performance. This confirms that sequential optimisation stages are an active research theme, but it is a different objective from gearbox-rib refinement. [Paper](https://academic.oup.com/jcde/article/7/5/615/5849132).

### 1.3 When is a second topology run worth doing?

Run a second topology study when it answers a new engineering question, for example:

- The first run reveals the main load paths; the second tests a revised casting draw/split strategy or stricter member-size constraint.
- The reconstructed design changes the stiffness/load path materially; the next study tests where remaining material can be removed.
- The first study uses an intentionally broad design envelope; the next focuses on a region with known load-path opportunities, with interfaces and confirmed structural members treated as fixed.
- A finer mesh is needed to check whether important paths persist. This is a **mesh-sensitivity/refinement check**, not necessarily a new design stage.
- You want to compare mass–misalignment trade-offs across several material budgets and manufacturing assumptions.

Do **not** blindly freeze every visible branch from the first SIMP run. That can preserve density artefacts, overpopulate the housing with ribs, and prevent the solver from finding a better alternative. Keep a candidate branch only when design review and re-analysis support it. Compare each new candidate to the baseline and the prior candidate under identical load cases.

---

## 2. Translating the optimisation into CAD

### 2.1 Manual engineering interpretation

For a gearbox housing, interpretation should translate the density pattern into a recognisable cast structure:

- Identify paths from bearing seats and gear-load introduction regions to the motor flange, mount pads, joint flanges and other supports.
- Separate truly necessary **load-carrying ribs** from low-density whiskers, isolated islands and mesh-sensitive branches.
- Turn a broad material web into a wall or gusset only if the load path and casting process justify it.
- Merge rib ends into bearing bosses and mounting pads with adequate section transitions; avoid abrupt rib terminations at highly loaded bosses.
- Prefer a coherent family of rib sections and transitions that can be cast, inspected, machined and dimensioned over a literal copy of every irregular density contour.
- Preserve the exact bearing-seat and gear-room interfaces. Recheck bearing-axis position, angular alignment and relative seat displacement on the **reconstructed CAD**, not the density mesh.

This interpretation is informed by FE results but is not fully specified by the optimiser's scalar objective. A visually beautiful density iso-surface may have thin ligaments, awkward junctions, poor local thickness or surfaces that are expensive to machine or inspect.

### 2.2 PolyNURBS / subdivision-style fitting (Altair Inspire)

Altair documents a workflow that smooths a topology result and fits a PolyNURBS surface over it. The workflow includes threshold exploration, analysis of the candidate shape, smoothing, fitting, and re-analysis. The documentation explicitly notes that overly detailed fits can result in irregular members and many faces, while smoothing can simplify those details; intersecting with the original design space can preserve the design envelope but introduce sharp features that need subsequent edits.

- **Useful for:** quickly creating a smooth concept surface that follows the broad topology; design review; generating a model that can be sent back through FE analysis.
- **Limitations:** PolyNURBS surfaces are not automatically a well-structured, feature-based casting model. The designer may still need to simplify the surface, make deliberate rib sections, add fillets/draft, repair junctions and create a stable parametric feature history.
- **Official source:** [Altair Inspire — Generating CAD from Optimization Results](https://help.altair.com/inspire/en_us/topics/inspire/tutorials/tut_analyzingshape_c.htm).

### 2.3 Implicit / signed-distance-field (SDF) workflows (nTop)

nTop's documented workflow converts the topology result into an implicit body, smooths or refines the result, unions it with preserved interface geometry, blends the interfaces, then intersects against the original design-space boundary. The resulting implicit body can be meshed or reconstructed as a B-rep/STEP/Parasolid CAD part depending on complexity.

- **Useful for:** smooth blends and Boolean operations, complex geometry, field-driven constraints, repeatable parametric workflows, preserving interface regions, and experiments with geometry-based constraints.
- **Limitations:** implicit smoothness is not the same as foundry readiness. B-rep conversion can require mesh refinement, quadrangulation, face fitting and simplification; the resulting model may not have the semantic feature tree a gearbox designer wants. The workflow must still be checked for manufacturable local thickness, ribs/boss transitions, draft, cores and machining.
- **Official sources:** [nTop — How to run a topology optimization](https://support.ntop.com/hc/en-us/articles/360044051214-How-to-run-a-topology-optimization); [nTop — Export geometry as STEP or Parasolid](https://support.ntop.com/hc/en-us/articles/7323484481555-How-to-export-geometry-as-a-CAD-part-STEP-or-Parasolid); [nTop — Remap Constraint for topology optimisation](https://support.ntop.com/hc/en-us/articles/14262495285651-How-do-I-use-the-Remap-Constraint-for-Topology-Optimization).

### 2.4 Autodesk Fusion Generative Design and casting constraints

Fusion's Generative Design interface allows casting outcomes to be defined with parameters such as ejection direction, minimum draft angle and minimum thickness. The documented casting process also describes thickness and draft requirements above/below the parting plane. Multiple manufacturing methods can be run to compare constrained outcomes against an unrestricted alternative.

- **Useful for:** exploring a concept with draft/ejection/minimum-thickness constraints included from the outset.
- **Important caveat:** a generic “casting” outcome is not automatically a validated production die-casting tool design. The real process must specify the parting plane, side cores/slides, the cavity geometry, rib and wall rules for the selected casting process, machining stock and access, and foundry limitations.
- **Official sources:** [Autodesk — Casting parameters](https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-CASTING-REF.htm); [Autodesk — Specify manufacturing methods](https://help.autodesk.com/view/fusion360/ENU/?contextId=GD-SPECIFY-MFG-METHOD).

### 2.5 Feature-based and automated CAD reconstruction

There is a substantial research literature on reconstructing usable CAD models from topology results:

- **Ming-Hsiu Hsu and Yeh-Liang Hsu (2005), “Interpreting three-dimensional structural topology optimization results,” *Computers & Structures*, 83, 327–337.** An automated process to translate 3D topology output into smooth CAD representation. [DOI](https://doi.org/10.1016/j.compstruc.2004.09.005).
- **Thomas Stangl and Sandro Wartzack (2015), “Feature Based Interpretation and Reconstruction of Structural Topology Optimization Results,” ICED 2015.** A semi-automatic reconstruction approach that produces a parametric feature-based CAD solid; demonstrated on a motorcycle swing arm. [Design Society record](https://nordic.designsociety.org/publication/37838/FEATURE%2BBASED%2BINTERPRETATION%2BAND%2BRECONSTRUCTION%2BOF%2BSTRUCTURAL%2BTOPOLOGY%2BOPTIMIZATION%2BRESULTS).
- **Abdennour Amroune, Jean-Christophe Cuillière and Vincent François (2022), “Automated Lofting-Based Reconstruction of CAD Models from 3D Topology Optimization Results,” *Computer-Aided Design*, 145, 103183.** Uses curve-skeletonisation, fitted B-spline cross-sections and lofting of branches/junctions; FEA is used to validate the rebuilt CAD. It targets beam-like outputs. [DOI](https://doi.org/10.1016/j.cad.2021.103183).
- **Hongyuan Ren et al. (2025), “AMRTO: Automated CAD model reconstruction of topology optimization result,” *Computer Methods in Applied Mechanics and Engineering*, 435, 117673.** A general reconstruction pipeline using mesh processing, sparse quad layout, harmonic mapping and adaptive NURBS fitting, with a multi-resolution strategy to reduce patch/control-point counts. The authors state that the method and test models are available in [PYTOCAD / AMRTO on GitHub](https://github.com/rhy-thu/AMRTO). [DOI](https://doi.org/10.1016/j.cma.2024.117673).

These methods reduce the cost of converting an irregular mesh into a solid or B-rep. But a generic NURBS reconstruction is not necessarily the best output for a die-cast housing: a small number of deliberate wall, boss, rib and fillet features are often easier to edit, dimension, inspect and reuse across variants than hundreds of freeform faces.

---

## 3. Explicit topology optimisation: MMC, MMV and projection methods

Density-based SIMP describes material with element-wise or field-wise pseudo-density. Explicit methods instead use geometric primitives or boundary descriptions as the design variables. They are particularly relevant if the intended design language is a set of ribs/walls rather than an arbitrary continuum.

### Moving Morphable Components (MMC)

- **Xu Guo, Weisheng Zhang and Wenliang Zhong (2014), “Doing Topology Optimization Explicitly and Geometrically—A New Moving Morphable Components Based Framework,” *Journal of Applied Mechanics*, 81(8), 081009.** The topology is formed by moving, changing and adding/removing parameterised components rather than relying only on a pixel/voxel density field. [DOI](https://doi.org/10.1115/1.4027609).
- **Weisheng Zhang, Dong Li, Jian Zhang and Xu Guo (2016), “Minimum length scale control in structural topology optimization based on the Moving Morphable Components (MMC) approach,” *Computer Methods in Applied Mechanics and Engineering*, 311, 327–355.** Explicit minimum length-scale control. [DOI](https://doi.org/10.1016/j.cma.2016.08.022).
- **Xu Guo et al. (2016), “Explicit structural topology optimization based on moving morphable components (MMC) with curved skeletons,” *Computer Methods in Applied Mechanics and Engineering*, 310, 711–748.** Extends component descriptions to curved centre-lines. [DOI](https://doi.org/10.1016/j.cma.2016.07.018).

**Why it matters for the reducer:** each member can be represented by parameters such as centre-line/ends, height, thickness/width, curvature and orientation. This is much closer to a rib design space. Component-based methods may make it easier to apply a minimum rib size and to create a geometry that is explainable and CAD-aligned.

**Limitation:** a parameterised member formulation needs a suitable component family, initial members or topology representation, and junction treatment. It does not automatically infer the right gearbox load paths or solve all casting constraints. Components can be trapped by parameterisation choices, and a rib-only design family may exclude helpful web or wall solutions.

### Moving Morphable Voids (MMV)

MMV methods optimise explicitly described voids; the solid structure is the remaining domain. They can yield explicit boundaries and smooth parameterised curves/surfaces. A key reference is **Weisheng Zhang et al. (2017), “Explicit three dimensional topology optimization via Moving Morphable Void (MMV) approach,” *Computer Methods in Applied Mechanics and Engineering*, 322, 590–614**, [DOI](https://doi.org/10.1016/j.cma.2017.05.002). A follow-up on stress constraints is **Zhang et al. (2018), “A Moving Morphable Void (MMV)-based explicit approach for topology optimization considering stress constraints,” *Computer Methods in Applied Mechanics and Engineering*, 334, 381–413**, [DOI](https://doi.org/10.1016/j.cma.2018.01.050).

MMV is attractive where holes/void boundaries are a convenient design description. It can provide clearer boundaries and fewer design variables than a voxel field, but the ability to encode casting, rib junctions, minimum wall thickness and interfaces still depends on the specific formulation.

### Projection-based manufacturing constraints

**Sandro L. Vatanabe, Tiago N. Lippi, Cícero R. de Lima, Glaucio H. Paulino and Emílio C. N. Silva (2016), “Topology optimization with manufacturing constraints: A unified projection-based approach,” *Advances in Engineering Software*, 100, 97–112.** This formulation describes manufacturing constraints by mapping/projecting design variables into pseudo-densities; the paper covers minimum member and hole sizes, symmetry, extrusion, pattern repetition, turning, casting, forging and rolling. [DOI](https://doi.org/10.1016/j.advengsoft.2016.07.002).

This family of methods is relevant if you want to retain SIMP-like density optimisation but encode more manufacturing-aware geometry behavior within the optimisation rather than relying on downstream repair alone.

---

## 4. Casting constraints: what they actually guarantee

### 4.1 Draw, split-draw and extrusion

- **Single draw:** assumes a defined pull direction and one main die/pull strategy. It discourages geometry that would trap the die in that direction.
- **Split draw:** allows two die halves to separate along a draw direction, with the parting plane determined by the optimiser in the documented Altair Inspire implementation.
- **No-hole options:** in some formulations prevent through-holes or enclosed features along the draw direction; this can make the density evolution more restrictive.
- **Extrusion:** imposes approximately constant cross-section along a specified axis. This is useful for extruded profiles or deliberately prismatic members, but it should not be confused with a general casting rule.
- **Minimum member size:** suppresses very thin members and mesh-scale features. It is a geometric length-scale control, not a complete casting rule for minimum wall thickness or foundry fillability.
- **Symmetry and pattern repetition:** can impose repeatability and regularity, valuable for a visually coherent and serviceable casting but potentially detrimental if the true loads or packaging are asymmetric.

Altair's documentation states that `SINGLE` assumes one die sliding in the chosen direction, while `SPLIT` allows two dies and optimises their splitting surface; its `NO HOLE` option limits holes in the draw direction. See [OptiStruct manufacturability documentation](https://help.altair.com/hwsolvers/os/topics/solvers/os/mfg_topology_opt_intro_c.htm) and [Altair Inspire split-draw constraint](https://help.altair.com/inspire/en_us/topics/inspire/structure/draw_split_draw_c.htm). Altair's official example shows minimum member size and draw constraints applied together with symmetry: [OptiStruct example](https://www.help.altair.com/2021/hwsolvers/os/topics/solvers/os/symmetry_and_draw_direction_constraints_applied_simultaneously_r.htm).

**Reducer-specific caution:** choose the pull direction from the real housing and tooling architecture, not an arbitrary global axis. If the housing is split into mating cast halves, the die-pull direction and parting plane have to work with the cavity, bearing bosses, rib walls and machining. Internal cavities may require cores, slides or side actions that a simple single-draw model does not represent. A thin non-design skin around the gear room keeps the design domain closed, but does not prove the rib network is removable from the chosen tooling.

### 4.2 What the papers contribute

- **Allan Roulund Gersborg and Casper Schousboe Andreasen (2011), “An explicit parameterization for casting constraints in gradient driven topology optimization,” *Structural and Multidisciplinary Optimization*, 44(6), 875–881.** Uses a Heaviside parameterisation along a specified casting direction; the height of each column determines the solid/void interface, reducing independent design variables and enforcing castable directional geometry. [DTU record and DOI](https://orbit.dtu.dk/en/publications/an-explicit-parameterization-for-casting-constraints-in-gradient-/).
- **Grégoire Allaire, François Jouve and Georgios Michailidis (2013/2016 chapter), “Casting/Molding Direction Constraints in Structural Optimization via a Level-Set Method.”** Formulates molding constraints using boundary geometry and penalisation, including thickness restrictions. A key benefit claimed is that the initial shape need not already be moldable, while the method guides it toward a castable shape. [Open manuscript](https://hal.science/hal-01242945/file/Allaire_Jouve_Michailidis_molding.pdf); [chapter DOI](https://doi.org/10.1007/978-3-319-45680-5_1).
- **Yaguang Wang and Zhan Kang (2017), “Structural shape and topology optimization of cast parts using level set method,” *International Journal for Numerical Methods in Engineering*, 111(13), 1252–1273.** Integrates a casting constraint into level-set shape/topology optimisation with a material-volume constraint. [DOI](https://doi.org/10.1002/nme.5503).
- **Quhao Li, Wenjiong Chen, Shutian Liu and Huiru Fan (2018), “Topology optimization design of cast parts based on virtual temperature method,” *Computer-Aided Design*, 94, 28–40.** Uses a fictitious thermal diffusion field to enforce unidirectional or multidirectional casting constraints. [DOI](https://doi.org/10.1016/j.cad.2017.08.002).
- **Vatanabe et al. (2016), unified projection method**, described above, combines casting with a broader suite of manufacturing restrictions.
- **Eric A. Nelson (2003), “Draw Direction Constraints in Topology Optimization—A Practical Example,” SAE 2003 World Congress, 2003-01-1306.** An automotive lower-control-arm application of draw-direction constraints in OptiStruct. [SAE paper](https://doi.org/10.4271/2003-01-1306).

### 4.3 What still needs a foundry review

Do not assume density filters, Heaviside projection, draw-direction constraints, and a mass budget cover every casting issue. Separately review:

- the actual parting line and core/slide pull directions;
- draft angles on all final cast surfaces, including rib side faces and pockets;
- minimum/maximum local wall thickness and abrupt section transitions;
- rib thickness relative to supporting wall thickness, rib spacing and junction radii;
- shrinkage/feeding, porosity, hot spots, filling and solidification for the chosen casting route;
- machining stock and access to bearing seats, bolt faces and flange interfaces;
- dimensional tolerances, distortion, clamping/joint preload and inspection access.

Fusion's official casting parameters explicitly name ejection direction, minimum draft and minimum thickness, and warn that process-dependent wall thickness varies with size, process, material and configuration. [Autodesk casting parameters](https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-CASTING-REF.htm). These are useful baseline controls, not substitutes for foundry process simulation or a casting supplier's rules.

---

## 5. Evidence specific to gearbox and EV reducer housings

### 5.1 Direct studies and what they actually optimise

| Reference | Performance target and approach | Reported result / relevance | Limitation for this project |
|---|---|---|---|
| **Wang Haoran, Fang Yuan & Zhang Tong (2015), “Vibration Analysis and Topology Optimization of Gearbox of Electric Vehicle,” *Journal of Mechanical Transmission*, 39(11), 128–131.** [Article](https://www.jxcd.net.cn/zh/article/doi/10.16578/j.issn.1004.2539.2015.11.031/) | Models a two-stage EV gear transmission in ADAMS, extracts bearing-seat dynamic loads, carries out housing modal and frequency-response analysis, and uses topology optimisation. | Reports reduced housing-surface vibration response amplitudes after optimisation. | Abstract-level source; does not confirm the same casting constraints or bearing-seat-tilt objective. |
| **Peng Xianchang, Cai Wenqi, Lin Zhibin & Gao Bingzhao (2021), “Static and Dynamic Analysis and Topological Optimization of Gearbox Housing in Electric Vehicle,” *Journal of Mechanical Transmission*, 45(7), 74–81.** [Article and DOI](https://doi.org/10.16578/j.issn.1004.2539.2021.07.011) | Two-speed EV transmission; baseline FE verified against constrained modal test; static and dynamic multi-objective topology optimisation. | Bearing-hole-area maximum displacement reportedly fell from 0.085 mm to 0.070 mm; first two natural frequencies rose by 24.8 Hz and 50.2 Hz; mass fell 7.5%. | Reports bearing-hole displacement, not a quantified angular seat-to-shaft alignment objective. |
| **Mingxuan Liang, Jianhong Hu, Shuqing Li & Zhigao Chen (2018), “Topology optimization of transmission gearbox under multiple working loads,” *Advances in Mechanical Engineering*.** [DOI](https://doi.org/10.1177/1687814018813454) | Variable-density topology optimisation under multiple bearing reaction load cases; modal dynamics and frequency-response model is checked against test data. | Reported mass reduced by 7.6%; first and second natural frequencies increased about 4.1% and 5.0%; stiffness/strength maintained. | Not necessarily an EV-specific casting example; objective is dynamic performance under multiple loads. |
| **Gwan-Hee Son, Seung-Je Cho & Young-Jun Park (2019), “Rib Design for Improving the Local Stiffness of Gearbox Housing for Agricultural Electric Vehicles,” *Applied Sciences*, 9(21), 4571.** [Open access](https://doi.org/10.3390/app9214571) | Experimentally updates the FE model; evaluates local stiffness in the frequency range of interest; uses strain analysis to locate ribs; parameterises rib width, length and height and compares patterns. | Demonstrates frequency-targeted, mass-aware, manufacturing-aware rib design rather than blind shape copying. | It is a rib-design/parameter study, not a SIMP TO paper; agricultural EV is not identical to a passenger-car reducer. |
| **Steffen Jäger & Tilmann Linde (2025), “Design and Cost Evaluation of Additively Manufactured Electric Vehicle Gearbox Housings,” *World Electric Vehicle Journal*, 16(10), 552.** [Open access](https://doi.org/10.3390/wevj16100552) | Topology suggests X-shaped load path; parameter optimisation then varies rib width/height, flange and turned-part thickness. | Thirteen design variants compare mass and torsional deformation; shows topology-to-parametric-refinement workflow on a real gearbox housing. | Hybrid additive manufacturing, not a conventional cast-aluminium design; do not directly copy geometry or manufacturing assumptions. |
| **Jing Pu (2026), “Lightweight Design and Topology Optimization of an Electric Vehicle Reduction Gearbox Housing,” *JERA*, 10(2), 123–131.** [Article](https://doi.org/10.26689/jera.v10i2.14378) | Reports multistage TO, interpreted CAD, rib and wall shape/size optimisation, static/modal/harmonic validation. | Reports 34.2% mass reduction, 12.7% higher torsional stiffness, 15.3% higher first natural frequency and lower operating-band vibration response. | Single-stage reducer; very recent publication. The accessible abstract does not establish exact bearing-tilt objectives or foundry validation. |

### 5.2 Direct evidence for optimising misalignment

**Simon Kabus and Claus B. W. Pedersen (2012), “Optimal Bearing Housing Designing Using Topology Optimization,” *Journal of Tribology*, 134(2), 021102.** [DOI](https://doi.org/10.1115/1.4005951). This is highly relevant to the mechanics, though not a complete automotive gearbox housing. The authors represent a cylindrical roller bearing with nonlinear springs, include bearing-load distribution in the optimisation constraints, and demonstrate reduced housing mass and roller contact misalignment with improved bearing fatigue life. The study explicitly recognises that housing stiffness can change roller load distribution and contact misalignment.

This supports the principle that **bearing alignment/contact metrics can be engineering optimisation targets**, not merely secondary outputs. But be careful when mapping the paper to your objective: roller/raceway contact misalignment is not identical to the tilt of a bearing-seat axis relative to a shaft centreline. The latter should be carefully defined from FE displacements and, for the most physically representative model, evaluated in a coupled shaft–bearing–housing system.

Other relevant gear-case literature includes **Zhang Xiqing, Xiang Changle and Liu Hui (2011), “Topology Optimization Design of Gearbox Housing under Multiple Loading Cases,” *China Mechanical Engineering*, 22(15), 1779–1783**, which optimises the first mode frequency with global stress, displacement and volume constraints; and several gearbox studies listed in the references of Peng et al. (2021), including 2013 automobile gearbox housing topology optimisation and 2012 static-dynamic multi-load optimisation.

### 5.3 What is not confirmed

I did **not** find a fully verifiable peer-reviewed example that matches every condition in the brief simultaneously: a **two-stage EV reducer**, cast-aluminium housing, fixed gear-room skin and bearing/motor/mount interfaces, density-based SIMP with draw-direction constraints, and an objective defined exactly as the bearings' seat-axis tilt relative to the shaft line.

That is not evidence the method is invalid. It means the practical proposal should combine: (a) gearbox-housing TO/NVH evidence, (b) the bearing-misalignment optimisation literature, and (c) casting-manufacturability literature, then validate the exact formulation on the target reducer.

---

## 6. Why the final optimised shapes look “designed”

A solver is optimising the performance metrics encoded in its model. It is not automatically optimising visual rhythm, brand style, draft practicality, assembly serviceability, machining access, or the ease of dimensioning a family of parts. An experienced engineer interprets the load paths and deliberately shapes the final members.

For a housing, this often means:

- **Load-path sketching:** trace forces from bearing bosses and gear reactions to the motor flange, mounts and case joint.
- **Flowing ribs into bosses:** merge the rib into a thicker, round-ended boss or a gradual gusset so the force transfer and local stress flow are credible; avoid an abrupt thin rib meeting a thick boss.
- **Rib hierarchy:** use a few primary ribs to carry long-range loads and secondary ribs to support local wall panels or control vibration.
- **Rhythm and symmetry:** align repeated ribs with credible load directions and packaging; preserve symmetry where the loading and mounting architecture justify it, not merely for appearance.
- **Section discipline:** set manufacturable thicknesses, taper, draft and transition radii; reduce abrupt thickness changes; keep ribs accessible to core-making and inspectable.
- **NVH judgement:** use the FE mode shapes and operating excitation orders to decide where a rib should support a wall and where added stiffness might shift a resonance toward an excitation frequency.

These steps are engineering interpretation rather than a hidden capability of SIMP. Son et al. (2019) are especially relevant: they used modal-test correlation, local-stiffness and strain information, and then compared parameterised rib patterns with manufacturing in mind. Jäger and Linde (2025) similarly converted an X-shaped topology into a family of parameterised geometry variants before selecting a trade-off.

### Celebrated examples—and their manufacturing caveat

- **GM seat-belt/seat bracket (Autodesk + General Motors, 2018):** a generatively designed component consolidated eight parts into one 3D-printed stainless-steel part; Autodesk/GM report 40% lower mass and 20% greater strength than the original assembly. [GM case study](https://www.autodesk.com/customer-stories/general-motors-generative-design). **This is additive manufacturing, not a cast-aluminium production housing.**
- **Airbus bionic cabin partition (2016):** the Airbus/Autodesk/APWorks project reports a 45% weight reduction for the partition design, using an aluminium-magnesium-scandium alloy and additive manufacturing. [Airbus announcement](https://www.airbus.com/en/newsroom/news/2016-03-pioneering-bionic-3d-printing). Again, its geometry freedoms are specific to additive manufacturing.
- **Porsche electric-drive housing prototype (2020):** Porsche reports that topology optimisation and function integration reduced the mass of housing parts by about 40%, corresponding to about 10% of the full drive's mass. A lattice structure increased stiffness between motor and gearbox by 100% despite 1.5 mm wall thickness and also improved acoustics. It was made by laser-fusion additive manufacturing for small series/motorsport, not conventional die casting. [Porsche Newsroom](https://newsroom.porsche.com/en_US/technology/porsche-protoype-small-production-electric-drive-housing-3d-printer-23277.html).

These cases are evidence of optimisation-led design, not proof that organic struts or lattices are appropriate for a cast reducer. A casting's “beautiful” solution usually comes from an engineer reducing the computational result to a coherent family of castable ribs, walls and bosses while retaining its important load paths.

---

## 7. Recommended plan for the two-stage reducer

### Stage A — verify the objective before changing the optimiser

1. **Define seat tilt unambiguously.** For each bearing seat, estimate its loaded axis from the FE displacement field at two or more axial slices through the bore. For small angles, the transverse slope can be approximated by the difference in bore-centre displacement divided by axial separation. Compare that seat axis with the shaft centreline under the same operating condition. Track both angular error and centre offset; they are related but not interchangeable.
2. **Use coupled or consistent support modelling.** Gear forces, shaft bending, bearing compliance, bearing reaction forces, housing/mount stiffness, flange bolts and joint preload affect the relative shaft–seat angle. A rigid shaft reference line may be a useful early approximation, but confirm the preferred design in the coupled shaft–bearing–housing model.
3. **Optimise multiple operating cases.** Include forward torque, regenerative/braking or reverse torque as relevant, realistic gear-mesh reaction directions, motor and chassis mount excitations, and thermal/preload cases if they influence alignment. Use a weighted objective and/or a worst-case limit rather than a single convenient load case.
4. **Pair the objective with guardrails.** Keep mass, local stress, maximum bore displacement/centre offset, modal-frequency or operating-band response, minimum member size, and manufacturing constraints explicit. Otherwise the optimiser may find a design that improves a narrowly defined seat tilt while being unacceptable in another respect.

### Stage B — make the first topology study robust

- Keep bearing seats, mount pads, motor flange and essential joint/machining interfaces non-design.
- Preserve the skin surrounding gear volumes, but inspect whether it is thick/stiff enough and whether the optimizer can connect ribs to it appropriately.
- Use a mesh resolution and length-scale constraint that can represent meaningful cast ribs; avoid treating every fine density feature as a member worth preserving.
- Run more than one mass budget. Build a curve of mass versus worst-case relative bearing-seat tilt, and record stress, bore offset, modes and manufacturing violations at every point. One mass target cannot reveal the trade-off curve.
- Compare at least a baseline/unrestricted run with the casting-constrained run. A large performance penalty from the casting constraint is useful design information, not a reason to remove it from the final design.

### Stage C — interpret and test, rather than freeze blindly

1. Extract two or three candidate load-path layouts from the topology results.
2. Rebuild each in editable CAD as a deliberate rib/wall/boss architecture. Apply draft, thickness discipline, junction radii and the real split/core strategy.
3. Re-run the FE analysis on those CAD versions and compare performance with the baseline and density field. A geometry that looks smooth but loses the seat-tilt benefit should be rejected or revised.
4. Parameterise the important features: rib centre-line/end points, rib width and height, wall thickness, local gusset extent, boss transition shape and selected fillets. Optimise those variables with a size/shape stage.
5. If the CAD version reveals a better design region or invalidates a key path, perform a new topology run with a revised domain/constraint—not simply a finer replay of the same problem. Freeze only geometry whose status as required structure is supported by engineering evidence.
6. Validate the selected design with realistic assembly stiffness, joint/contact assumptions, static torque cases, modal and harmonic/gear-order response, and fatigue checks. Correlate the modal model against test results if a prototype exists. Get the casting supplier to review draft, core pulls, section transitions, local thickness and casting simulation before calling it production-ready.

### Stage D — decide whether to stay with SIMP or test explicit ribs

Given that your conceptual design is a cast housing with a thin skin and known non-design interfaces, I would **keep SIMP as the broad concept-discovery stage**. Then compare the engineering value of:

- a conventional parametric rib/wall CAD model refined by size/shape optimisation;
- an MMC-style explicit rib network with controlled centre-lines, endpoints, width/thickness, height and curvature;
- a hybrid method where a topology result identifies load paths and an engineer/algorithm fits manufacturable rib candidates to those paths.

The hybrid approach is a pragmatic compromise: it keeps the broad design freedom of the density field without requiring the final geometry to copy the density iso-surface. Explicit MMC methods are worth a research prototype if repeated reconstruction is the main cost or if you need hundreds of consistent variants; they are not automatically superior for a single industrial housing.

### Proposed decision rule

**Do a new topology run only when you can name the new question it answers.** Otherwise, put effort into improving the CAD interpretation and parametric refinement stage, and prove the design with the target bearing-alignment metric. For this application, a measured Pareto curve of housing mass versus worst-case bearing-seat tilt—subject to static strength, minimum feature size, draw/split-draw, modes and castability—is likely to be more useful than chasing a single visually dramatic topology result.

---

## Sources and confidence notes

### Highest-value primary/official sources

1. Li, C.; Kim, I. Y.; Jeswiet, J. (2015), automotive engine-cradle concept-to-detail optimisation, *Structural and Multidisciplinary Optimization*. [DOI](https://doi.org/10.1007/s00158-014-1151-6).
2. Kabus, S.; Pedersen, C. B. W. (2012), bearing housing topology optimisation and contact misalignment, *Journal of Tribology*. [DOI](https://doi.org/10.1115/1.4005951).
3. Son, G.-H.; Cho, S.-J.; Park, Y.-J. (2019), local-stiffness-guided gearbox rib design, *Applied Sciences*. [DOI](https://doi.org/10.3390/app9214571).
4. Wang, H.; Fang, Y.; Zhang, T. (2015), EV two-stage reducer vibration/TO study, *Journal of Mechanical Transmission*. [Journal record](https://www.jxcd.net.cn/zh/article/doi/10.16578/j.issn.1004.2539.2015.11.031/).
5. Peng, X. et al. (2021), EV two-speed gearbox housing static/dynamic TO, *Journal of Mechanical Transmission*. [DOI](https://doi.org/10.16578/j.issn.1004.2539.2021.07.011).
6. Jäger, S.; Linde, T. (2025), EV gearbox housing for hybrid additive manufacturing, *World Electric Vehicle Journal*. [DOI](https://doi.org/10.3390/wevj16100552).
7. Pu, J. (2026), EV reduction gearbox housing multistage optimisation, *JERA*. [DOI](https://doi.org/10.26689/jera.v10i2.14378).
8. Gersborg, A. R.; Andreasen, C. S. (2011), explicit casting-direction parameterisation, *Structural and Multidisciplinary Optimization*. [DTU record](https://orbit.dtu.dk/en/publications/an-explicit-parameterization-for-casting-constraints-in-gradient-/).
9. Allaire, G.; Jouve, F.; Michailidis, G. (2016 chapter / earlier manuscript), level-set molding constraints. [Open manuscript](https://hal.science/hal-01242945/file/Allaire_Jouve_Michailidis_molding.pdf).
10. Vatanabe, S. L. et al. (2016), unified projection-based manufacturing constraints, *Advances in Engineering Software*. [DOI](https://doi.org/10.1016/j.advengsoft.2016.07.002).
11. Wang, Y.; Kang, Z. (2017), level-set optimisation of cast parts, *International Journal for Numerical Methods in Engineering*. [DOI](https://doi.org/10.1002/nme.5503).
12. Li, Q. et al. (2018), virtual-temperature molding constraint, *Computer-Aided Design*. [DOI](https://doi.org/10.1016/j.cad.2017.08.002).
13. Guo, X.; Zhang, W.; Zhong, W. (2014), MMC, *Journal of Applied Mechanics*. [DOI](https://doi.org/10.1115/1.4027609).
14. Zhang, W. et al. (2017), MMV, *Computer Methods in Applied Mechanics and Engineering*. [DOI](https://doi.org/10.1016/j.cma.2017.05.002).
15. Altair official: [OptiStruct manufacturability](https://help.altair.com/hwsolvers/os/topics/solvers/os/mfg_topology_opt_intro_c.htm), [PolyNURBS reconstruction tutorial](https://help.altair.com/inspire/en_us/topics/inspire/tutorials/tut_analyzingshape_c.htm).
16. Autodesk official: [Fusion casting parameters](https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-CASTING-REF.htm).
17. nTop official: [TO workflow](https://support.ntop.com/hc/en-us/articles/360044051214-How-to-run-a-topology-optimization), [CAD export](https://support.ntop.com/hc/en-us/articles/7323484481555-How-to-export-geometry-as-a-CAD-part-STEP-or-Parasolid).
18. Reconstruction research: [Amroune et al. (2022)](https://doi.org/10.1016/j.cad.2021.103183), [Ren et al. (2025)](https://doi.org/10.1016/j.cma.2024.117673).

### Confidence / verification

- Vendor feature descriptions above are based on official help pages; they describe documented tool capabilities, not independent comparative benchmarks.
- Numerical improvements for the named gearbox studies are the values reported by the papers or their accessible abstracts; they should not be compared as if the models, load cases, materials, manufacturing processes and baselines were identical.
- The 2026 Pu study is recent and its abstract-level information supports the staged workflow and reported performance numbers, but not the detailed castability or bearing-tilt claims in the present brief.
- The GM, Airbus and Porsche examples are manufacturer/vendor case reports. Their reported improvements are useful examples, but all three rely on additive manufacturing freedoms and should not be treated as evidence of a directly castable topology.
