Researched on 9 October 2026 for LOP-16.

# Topology optimisation in practice: iterations, interpretation, castings

## 1. Is topology optimisation iterative in practice, not one-shot?

Yes. In practice, topology optimisation (TO) is usually part of an **iterative design loop**, not a one-shot path straight to production CAD. The common industrial pattern is: define a broad design space, run TO to reveal load paths, interpret the result into a manufacturable CAD concept, reanalyse that CAD, then either optimize feature dimensions or run a second optimisation in a reduced design space.[cite:297][cite:348][cite:351]

This workflow appears under several overlapping names in literature and software practice: sequential topology–shape optimisation, topology-to-size/shape chains, progressive design-space refinement, and reconstruction plus re-optimisation. Academic work on sequential optimisation explicitly combines topology and later geometric refinement, while vendor workflows document a post-TO CAD fitting and verification loop rather than direct release of the raw field result.[cite:302][cite:348][cite:351]

The strongest practical evidence is not that everyone uses a single formal term, but that many published case studies separate the **concept-generating stage** from the **engineering-detail stage**. In gearbox and housing work, authors often use TO to determine rib trajectories or reinforcement zones, then redesign those zones into walls and ribs with manufacturable thicknesses, fillets, and draft, and finally reassess structural or acoustic performance.[cite:297][cite:310]

A useful caution comes from a cast two-stage reducer housing study by Slavov and Konsulova-Bakalova in *Machines* (2019), where the topology result suggested a much larger mass reduction than the final manufacturable CAD. The paper reported a 28.65% reduction for the smoothed topology-inspired concept, but only 7.33% once the manufacturable cast design was reconstructed, which is direct evidence that interpretation and redesign materially change the result.[cite:348]

### Practical names you can use internally

- Multi-stage TO.
- Sequential or progressive refinement.
- TO → CAD reconstruction → verification → local re-optimisation.
- TO → rib layout synthesis → size/shape optimisation.
- TO → topography/shape/size chain, when the follow-on stages truly are those methods.[cite:302][cite:348][cite:351]

### What is confirmed, and what is not

Confirmed: iterative reinterpretation and verification are routine in practice, and published gearbox/housing studies do use staged flows.[cite:297][cite:348]

Not firmly confirmed from the sources reviewed: a single universally accepted label for “run SIMP, rebuild CAD, freeze accepted material, shrink the domain, and rerun SIMP.” That pattern is technically credible and aligned with practice, but the naming is fragmented across subfields and vendor workflows.[cite:302][cite:310]

## 2. How topology results become designs, especially castings

### Manual interpretation remains standard

The dominant real-world route is still manual or semi-manual interpretation by an engineer. The engineer reads the density field as a **load-path map**, keeps the persistent branches that survive across load cases or parameter settings, and converts those into a controlled network of ribs, webs, walls, bosses, and junctions tied back into the frozen interfaces such as bearing seats, flanges, mounts, and split lines.[cite:297][cite:310]

For castings, this interpretation stage is where the “organic” topology output is turned into production logic: constant or slowly varying wall thickness, filleted rib roots, smooth blending into bosses, symmetry where functionally justified, machining stock, draft, and a parting strategy that avoids impossible undercuts.[cite:313][cite:314][cite:355]

### Altair Inspire and PolyNURBS

Altair documents a workflow in which the user first inspects the optimisation result, applies thresholding and smoothing, and then fits a PolyNURBS surface/body to the generated shape. The fitted PolyNURBS can then be intersected or combined with the original package geometry and re-analysed as ordinary CAD, which is a formalised version of the interpretation-and-verify loop.[cite:348][cite:351][cite:352]

This is useful because PolyNURBS provides smooth, editable geometry rather than a raw faceted isosurface. However, it still does not remove the need for engineering judgement; it mainly accelerates the creation of a smooth starting point for a controlled CAD rebuild.[cite:348][cite:351]

### nTop and implicit/SDF-style reconstruction

nTop’s documented workflow treats topology-optimised results as implicit geometry that can be smoothed, blended, thickened, combined with other bodies, and then exported. Its support articles describe conversion of topology-optimised or implicit models into CAD-compatible geometry, including STEP and Parasolid export paths.[cite:363][cite:364]

This is strong for rapid post-processing and complex smooth geometry handling, especially when the result will stay within an implicit workflow for a while. But nTop also notes that conversion quality and downstream usability depend on geometry complexity, so a very intricate topology result may still need simplification before it becomes robust production CAD.[cite:363][cite:364][cite:366]

### Autodesk Fusion generative design and casting constraints

Autodesk positions Fusion generative design as a workflow that generates manufacturing-aware design options and evaluates multiple outcomes against selected manufacturing methods. Autodesk’s material emphasises that the process can consider manufacturing constraints early, which is valuable for casting-oriented concept generation, although the reviewed public sources were less explicit than Altair’s solver documentation about the exact mathematical enforcement of casting rules.[cite:375][cite:377]

This means Fusion can be useful at the concept phase, but for a cast gearbox housing the engineering team still needs an explicit review of draw directions, wall strategy, machining, sealing interfaces, and local bearing-seat stiffness before trusting a concept for production release.[cite:375][cite:377]

### Feature-based reconstruction

Feature-based reconstruction means rebuilding the topology result as explicit CAD features: rib sketches, shell offsets, boss pads, gussets, web cut-outs, blend radii, and split-plane logic. This route is slower than automatic fitting, but it is usually the most robust option for cast housings because every critical design choice stays editable and measurable in terms familiar to casting, machining, and validation teams.[cite:310][cite:313]

For a reducer housing, this is usually the best path once the load paths are understood: use TO to answer “where should structure exist?” and feature-based CAD to answer “what exact wall, rib, and boss geometry should be manufactured?”[cite:297][cite:310]

### CAD-ready or explicit TO families

A different branch of the field aims to produce more CAD-ready results directly by representing geometry explicitly rather than as a free density field. Relevant families include moving morphable components (MMC), moving morphable voids (MMV), geometry projection methods, and mixed projection/explicit approaches that reduce the gap between optimisation variables and manufacturable members.[cite:322][cite:305]

These methods are attractive because they can embed interpretable components or voids and make reconstruction easier. Their trade-off is that they usually restrict design freedom more than unconstrained density-based TO, so they are often best viewed as complementary tools for later-stage refinement or for problems where clear member-based geometry is desired from the start.[cite:322][cite:305]

## 3. Manufacturing constraints for castings in TO

Topology optimisation for castings typically needs more than a mass constraint plus a draw direction. The major constraint classes are draw or molding direction, split-draw or parting logic, minimum member size, minimum void size, symmetry, pattern repetition, and sometimes extrusion or rotational constraints where the manufacturing route or design architecture requires them.[cite:353][cite:355][cite:356]

### Draw, extrusion, and split-draw

Altair/OptiStruct documents draw direction constraints as a way to ensure the die or mold can move in a specified direction without geometric lock. Inspire also documents split-draw constraints for cases where the parting plane lies inside the design space and both mold halves pull away from the part.[cite:353][cite:355][cite:362]

OptiStruct’s `DTPL` design-variable definition includes manufacturing controls such as `DRAW`, `EXTR`, `SINGLE`, `SPLIT`, and pattern/repetition-related options. The documentation also states that minimum dimension controls should be at least three times the average element size when draw, extrusion, pattern grouping, or similar manufacturing constraints are used, which matters directly for voxel-based SIMP workflows.[cite:356][cite:362]

### Academic foundations for casting constraints

The literature on manufacturing-aware TO is well established. Gersborg-Hansen and Andreasen proposed an explicit castability parameterisation intended to eliminate internal voids and undercuts and demonstrated 2D and 3D castable designs.[cite:316]

Vatanabe and co-authors presented a projection-based framework for a broad family of manufacturing constraints, including minimum and maximum member size, minimum hole size, symmetry, extrusion, pattern repetition, rotational manufacture, casting, forging, and rolling. That work is important because it showed that many manufacturing rules can be handled in a single projection-based framework rather than as isolated ad hoc tricks.[cite:331]

Allaire and collaborators developed molding-direction constraints within level-set based shape and topology optimisation, using geometric constraints defined along rays. This is especially relevant when the question is not merely “does the result look castable?” but “can castability be enforced mathematically during optimisation?”[cite:346][cite:343]

### Minimum length scale

Minimum feature control deserves special attention because density filtering and projection can be misunderstood. Recent work from the University of Liège group showed that, in density-based robust formulations, the minimum sizes of solid and void phases are tied to the filter and Heaviside parameters, and that careful three-field formulations are needed for simultaneous control of both phases.[cite:318][cite:321]

In practical terms, this means your current filter plus Heaviside continuation is a good foundation, but it should not be assumed to guarantee both rib thickness and removable pocket size unless those relationships are calibrated or independently checked. For a cast housing, both matter.[cite:318][cite:321][cite:323]

### Symmetry and repetition

Symmetry constraints are commonly used in housings to keep balanced load paths, consistent styling, and manufacturing simplicity when the physics allows it. Repetition or pattern constraints are useful where repeated ribs, bolt pads, or repeated substructures improve castability or assembly consistency, though they can suppress asymmetric solutions that may be structurally superior under real multi-load operation.[cite:331][cite:356]

## 4. Gearbox, EV reducer, and e-axle housing examples

### Kim, Han, Chung, Park (2024), *Scientific Reports*

Kim, Han, Chung, and Park published “Optimization of gearbox housing shape for agricultural UTV using structural–acoustic coupled analysis” in *Scientific Reports* in 2024. The gearbox was a two-stage helical gearbox for an electric agricultural utility vehicle, and the optimization targeted radiated noise using structural–acoustic coupling rather than only static stiffness.[cite:297]

The paper cites three especially relevant prior gearbox-housing works: Ogata, Suzuki, and Hiraoka’s 2005 SAE technical paper on transmission housing weight reduction by topology optimisation; Ide, Otomori, Leiva, and Watson’s 2014 *Structural and Multidisciplinary Optimization* paper on structural optimization methods for light, efficient automatic transmissions with low radiated noise; and Son, Kim, Cho, and Park’s 2020 *Applied Sciences* paper on gearbox-housing shape optimisation for radiated-noise reduction.[cite:297]

Kim et al. used the acoustic response as the optimisation target and reported that the optimised housing reduced radiated noise by 3.46 dB(A) in the principal operating range and by 2.43 dB(A) overall while keeping mass essentially unchanged, within about 0.2%. The important practical point is that the topology/shape ideas were translated into manufacturable housing geometry rather than left as a raw optimisation field.[cite:297]

### Eyckens et al. (2021), Resource Efficient Vehicles Conference

Eyckens, Naets, Deckers, Rosseel, Schuette, Koutla, Diltoer, Lopez, and Duysinx presented a gearbox-housing study in the 2021 Resource Efficient Vehicles Conference under the CAMEDO project. Their use case was an EV gearbox housing with a multi-material design goal, and they explicitly framed the work around manufacturing-informed design and optimisation.[cite:290]

They used topology optimisation under realistic loading, examined material-fraction constraints and mesh sensitivity, and then discussed design-for-manufacturing rules needed to reach a manufacturable CAD design. That paper is useful here because it treats optimisation output as one stage inside a broader manufacturability workflow rather than as an endpoint.[cite:290]

### Reducer-housing weight optimisation in *Machines* (2019)

A 2019 *Machines* paper hosted by SolidWorks describes weight optimisation of a two-stage reduction gearbox housing used in conveyor-belt service. The optimisation considered casting-oriented constraints, symmetry, preserved bearing and mounting regions, and a manufacturable redesign stage.[cite:348]

Its practical lesson is particularly important for LOP-16: the raw topology result and the finished manufacturable design can differ dramatically in realised benefit. That paper therefore supports an internal KPI such as “interpretation penalty” or “manufacturing translation loss,” measured between the thresholded TO concept and the verified cast CAD.[cite:348]

### What is directly confirmed for bearing-seat stiffness and misalignment

The reviewed search set gave strong confirmation that gearbox and transmission housing optimisation often targets weight, static stiffness, modes, or radiated noise, and that bearing-hole or shaft-hole regions are typically protected as non-design interfaces.[cite:290][cite:297][cite:348]

What was **not fully confirmed** in the reviewed sources is a large open literature set using your exact objective phrasing of “bearing-seat tilt against the shaft line” for cast EV two-stage reducer housings. However, related transmission-housing work does model housing stiffness around bearings as important to gear-mesh alignment and NVH, which supports the engineering validity of your metric.[cite:293][cite:294]

## 5. How humans design the “amazing shapes” after optimisation

The visually compelling final parts are not simply the optimisation iso-surface with fillets added. Designers use the topology result as a **load-path sketch**, then apply product architecture, casting knowledge, brand or design language, and inspection of multiple load cases to decide which branches become primary ribs, which become secondary gussets, and which are discarded as optimisation noise.[cite:310][cite:313]

In cast housings, this often means flowing ribs into bosses and flanges with controlled rhythm and symmetry, merging nearby branches into one stronger wall, choosing constant or stepped rib thicknesses that the foundry can fill reliably, and aligning the geometry with split lines, seals, bolts, machining datums, and assembly clearances.[cite:313][cite:314][cite:355]

That is why celebrated optimised parts in automotive and aerospace usually look cleaner than the underlying optimisation field. The “beauty” comes from a human-led abstraction of persistent force flow into a coherent manufacturable language, followed by repeated analysis to ensure that the aesthetic simplification did not destroy the mechanical benefit.[cite:348][cite:351]

## What this means for our loop

For a cast aluminium EV two-stage reducer housing, the next practical loop should be staged rather than monolithic.[cite:297][cite:348]

1. Keep the current broad design space with bearing seats, mounts, motor flange, and enclosure skin frozen, because the literature supports protecting interfaces and closed-wall functions during TO.[cite:290][cite:297][cite:348]
2. Run the density-based TO across several mass budgets and at least two mesh levels so persistent load paths can be separated from mesh artefacts.[cite:290][cite:318]
3. Interpret only the persistent paths into a feature model: outer shell, bearing-boss bridges, mount towers, axial and circumferential ribs, local gussets, and wall transitions.[cite:310][cite:348]
4. Enforce casting logic explicitly in CAD even if a draw filter already exists in TO: split-draw feasibility, draft, minimum wall and pocket size, root radii, thickness transitions, core strategy, and machining access.[cite:353][cite:355][cite:356]
5. Reanalyse the reconstructed CAD with the original bearing-seat misalignment objective plus modal/NVH checks, because gearbox-housing literature shows static and acoustic goals can diverge.[cite:297][cite:293]
6. Add a second stage of optimisation on rib heights, thicknesses, and junction positions, or rerun TO locally inside selected rib envelopes while freezing the accepted CAD structure.[cite:302][cite:348]
7. Track the gap between raw TO and reconstructed CAD as an explicit metric, since published gearbox housing examples show this gap can be large.[cite:348]

## Sources

- [Optimization of gearbox housing shape for agricultural UTV using structural–acoustic coupled analysis](https://www.nature.com/articles/s41598-024-54606-8) — primary gearbox-housing paper with authors, year, venue, and references to earlier gearbox topology/shape optimisation work.[cite:297]
- [A generic approach to capitalize manufacturing experience in design and optimization](https://orbi.uliege.be/bitstream/2268/268634/1/rev2021-043(1).pdf) — EV gearbox housing case study framed around manufacturing-informed optimisation and DfM integration.[cite:290]
- [Tutorial: Generating CAD from Optimization Results](https://help.altair.com/inspire/en_us/topics/inspire/tutorials/tut_analyzingshape_c.htm) — Altair workflow for thresholding/smoothing results and fitting PolyNURBS to TO output.[cite:348]
- [Fit PolyNURBS to the Generated Shape](https://help.altair.com/inspire/en_us/topics/inspire/structure/fit_polynurbs_c.htm) — concise vendor documentation for PolyNURBS-based reconstruction.[cite:351]
- [Split Draw](https://2025.help.altair.com/2025/inspire/en_us/topics/inspire/structure/draw_split_draw_c.htm) — practical explanation of split-draw manufacturing constraints in Inspire.[cite:357]
- [Draw Direction Constraints](https://2025.help.altair.com/2025/hwsolvers/altair_help/topics/solvers/os/mfg_topology_draw_direction_constraints_r.htm) — OptiStruct manufacturing-constraint documentation for draw-direction feasibility.[cite:362]
- [DTPL bulk data entry](https://2022.help.altair.com/2022.3/hwsolvers/os/topics/solvers/os/dtpl_bulk_r.htm) — explicit solver-level parameters for draw, extrusion, split, and pattern options.[cite:356]
- [How to export geometry as a CAD part (STEP or Parasolid)](https://support.ntop.com/hc/en-us/articles/7323484481555-How-to-export-geometry-as-a-CAD-part-STEP-or-Parasolid) — nTop documentation for converting implicit or topology-optimised bodies into CAD output.[cite:364]
- [How to export geometry: Overview of export workflows](https://support.ntop.com/hc/en-us/articles/360048784874-How-to-export-geometry-Overview-of-export-workflows) — broader nTop export guidance and limitations.[cite:363]
- [Analytical relationships for imposing minimum length scale in topology optimization](https://orbi.uliege.be/handle/2268/261997) — clarifies how filter/projection parameters relate to minimum feature size in density-based TO.[cite:321]
- [Autodesk Fusion generative design overview](https://www.autodesk.com/products/fusion-360/blog/unlocking-innovative-solutions-with-generative-design/) — current Autodesk positioning of manufacturing-aware generative design.[cite:375]
