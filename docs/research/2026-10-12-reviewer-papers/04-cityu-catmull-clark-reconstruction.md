# Wang and Ma 2026: a smooth surface fitted to a topology-optimisation result (Catmull-Clark subdivision)

**12 October 2026.** The reviewer's paper No. 4, read for two questions: does it help our irregular shapes, and does it support the reviewer's proposal?

## 1. Citation, and how it was read

Zhenhan Wang and Weiyin Ma (City University of Hong Kong), "Robust surface reconstruction for topology optimization using Catmull-Clark subdivisions", *Computer Aided Geometric Design* 127 (2026) 102557, DOI [10.1016/j.cagd.2026.102557](https://doi.org/10.1016/j.cagd.2026.102557). It was published online on 14 April 2026, open access.

**It is not the MMC generative-design paper** (Extreme Mechanics Letters 2025) the link was thought to be. It has no generative model and no MMC.

The publisher's PDF (15 pages) was read in full, with every figure viewed. The equations came out as glyphs, so their terms come from the text's definitions.

## 2. The problem and its representation

A thresholded SIMP result is a dense, faceted triangle mesh. The paper fits a smooth, watertight surface with few patches to it, for CAD and simulation. **It is post-processing.** The optimisation is over before it starts, and no step computes mechanics.

The surface is a Catmull-Clark subdivision surface. Its variables are its control vertices (528-1,760), and it is linear in them. It is C2, except C1 at extraordinary vertices. The control mesh's layout comes from the curve skeleton: a tube of quads along each branch and a cube at each junction.

## 3. The method

- The density is thresholded (0.5-0.6), and a skeleton is taken by mean-curvature-flow contraction (Tagliasacchi et al. 2012). Close junctions are merged and short branches dropped.
- At each junction, a cube is turned so that each branch leaves through its own face (Usai et al. 2016). Where two branches share a face, an integer linear program tessellates it.
- A section's radius is the mean hit distance of rays cast in the plane normal to the skeleton. A junction's cube is 1.5-2.0 × its branches' mean radius, a fixed rule.
- The cubes are joined into a closed all-quad mesh, regularised towards right angles and even edges (each vertex within R = 1 or 2, units not given).
- The control points are fitted by linear least squares to the input surface.
- Optional fairing, used on two of the four parts: penalties on Gauss curvature and its variation, plus the fit error (MATLAB SQP).
- The check: FE of the result and of the input, compared by maximum displacement and maximum von Mises stress only.

## 4. What it controls, and what it does not

**It controls:**
- the surface's smoothness;
- G1 blends at junctions, where lofting gives G0 (its claim against Amroune et al. 2022, [note 02](02-amroune-2022-lofting-reconstruction.md));
- the patch count: 50-118 times fewer than the input's triangles.

**It does not control:**
- **stiffness or any mechanics:** the fit is geometry only;
- **member size:** inherited from the optimiser (12, 4 and 8 mm minimum members);
- **casting:** no pull direction, draft, undercut or core rule; the stated target is additive manufacturing;
- **flat faces and sharp edges:** there are no crease rules, so in the figures the two plate-like parts (8 mm and 2-3 mm thick) come out with rounded, tube-like sections;
- **topology:** fixed by the skeleton, and changed unchecked by merging and pruning;
- **the layout:** the fit follows its input, so the drone's irregular branching comes out irregular and smooth (Fig. 15).

## 5. Scale and cost

Four 3D parts, two of them 2.5D plates (8 mm and 2 mm thick). The first quad mesh takes under 30 s, regularisation 101-244 s, least squares a few seconds, and fairing 9-11 min. It runs in MATLAB, on hardware not stated. Nothing is learned: no training data, no GPU. The optimiser and FE solver are not named.

## 6. Results (Table 1)

| Part | Volume fraction, in → out (%) | Max displacement, in → out (mm) | Max von Mises, in → out (MPa) | Patches, in → out |
|---|---|---|---|---|
| Cantilever | 8.42 → 8.52 | 0.0880 → 0.0876 (−0.5 %) | 112 → 101 (Fig. 8 reads 111) | 54,264 → 530 |
| Bridge | 15 → 15.13 | 0.529 → 0.132 (**−75 %**) | 2.7 → 1.8 (−33 %) | 47,768 → 958 |
| Clipper | 20.7 → 21 | 0.169 → 0.182 (+7.7 %) | 271.5 → 270 | 69,102 → 584 |
| Drone | 22.37 → 23.9 (+6.8 % of volume) | 0.781 → 0.772 (−1.2 %) | 13.4 → 13.2 | 110,098 → 1,792 |

The text says displacement and stress "closely matched … across all test cases". **The bridge does not:** its result is four times stiffer by maximum displacement, unexplained.

In the fairing study (Fig. 13), the volume fraction went 21 → 20.5 → 20.79 % as the weights rose (0, 0.1, 2), with no FE. It reports no comparison with another optimiser and no diversity: neither is its subject.

## 7. Limitations

**Stated by the authors:**
- beam-like topologies only, so bulky regions, enclosed cavities and "extensive planar facets" may fail;
- the result depends on the skeleton;
- no stress in the reconstruction;
- slow on large models.

**Seen in reading:**
- **A thin check:** two global maxima a part, one load case, and no mesh study.
- **Inconsistencies:**
  - cantilever stress: 101 MPa in the table, 111 MPa in Fig. 8;
  - bridge input 15 % (table) against 15.23 % (text); clipper 2 mm (text) against 3 mm (Fig. 11);
  - drone: 110,098 triangles on 28,640 vertices does not fit a closed mesh (about two triangles a vertex).
- **No topology check:** nothing checks that holes and branches survive.
- **"Fully automated", yet about ten parameters are set per part** (skeleton weights, merge distance, ray count, junction factor, R, fairing weights).
- **"CAD-compatible B-rep" is asserted, not shown:**
  - no export format or CAD kernel is named;
  - the interfaces (rings, motor pods) stay separate solids, never fused with the surface.

## 8. Code, data and licence

No code or data is released (the data statement specifies none), and one web search found no code.

The skeleton's code exists in MATLAB (Tagliasacchi et al.) and in CGAL (C++). No code was found for Usai et al.'s junction layout.

The article is CC BY-NC-ND 4.0: read and cite it, but keep the PDF and figures out of git.

## 9. For our problem

**The irregular shapes: no.**
- **It keeps the layout:** our paint would come out smooth paint, the verdict already reached for rho2sdf and our `LOOP_SDF` drawing ([rho2sdf](../2026-10-12-smooth-extraction-rho2sdf.md)).
- **It needs a curve skeleton, and our metal has none.** A height-field member stands on the wall along its whole length, a plate on a shell. Without a fixed shell, the optimiser draws the walls too, more of what the paper excludes.
- **Its rounded sections turn flat plates into tubes.** Walls, flanges and machined faces need the crease rules it lacks.

**Stiffness against our seat lines: not known, and probably a loss.**
- The fit has no mechanics. Its evidence is a global maximum displacement: within 8 % on three parts, and four times off on the fourth. Seat tilt and bed displacement are local.
- Our smoothed drawing raised the beds' displacement by 18 % (7 kg design) and 73 % (4.6 kg). Every cleaning after optimisation lost 2-5 times the stiffness.
- Any use needs our FE gate.

**The reviewer's proposal:**
- **In the loop or after it:** the paper argues for after (in-loop rules "can prematurely restrict the design space"), without a comparison. Our measured losses argue the other way.
- **Curvature penalties: partly supported.** Gauss-curvature fairing removed ripples and untangled junctions for a 1-2.4 % change in volume, but it was never judged by FE.
  - *Our inference, untested:* a Gauss-curvature term costs nothing on planes and cylinders, and it charges lumps and saddle-shaped knots. A perimeter term charges every thin plate for its area.
  - That makes Gauss curvature the better candidate smoothness term for a casting.
- **Nothing on:** junction size, local thickness, casting rules, plates or topology changes. It covers only the "branching" half of the adaptive rules, and only for tubes.
- **"Keep the optimised solid":** consistent. The bridge shows that a faithful redraw still needs an FE check.

**What it would take.**
- **Building it:** a Python rewrite of a MATLAB pipeline with no published code, about two to three weeks:
  - the skeleton;
  - the junction ILP (scipy's `milp`, as in TOBS);
  - the subdivision matrices;
  - least squares;
  - fairing.
- **Running it:** minutes a design on the CPU, with no GPU and no training data.
- **Its reach:** tube-like members only, at most free struts to the mounts. Plates and walls would need another method.

**First small test (an hour, CPU, existing meshes).** It tests the one idea worth taking.
- **Measure** Gauss curvature at a 4-6 mm scale (pyvista's `curvature("gaussian")` on smoothed meshes) on four drawings:
  - `outcome_hf6_4mm_7.0kg`;
  - its smooth redraw, `outcome_hfsdf_4mm_7.0kg`;
  - a ribbed CAD (flow C);
  - `param5` (flow D).
- **Then:** if the doubly curved share of each surface ranks the drawings as the engineer's eye does (paint high, ribs low), Gauss curvature is a candidate for the loop's smoothness term. If not, drop the idea.

**Verdict: do not adopt.** It is a careful geometry tool for truss-like parts made by additive manufacturing. It makes a shape smooth, not regular. It cannot represent walls, plates or flat faces, and its stiffness check is thin. Keep Gauss curvature as an idea, to measure first.

## 10. Sources

- The PDF, read in full with its figures: <https://scholars.cityu.edu.hk/ws/portalfiles/portal/490607585/483376819.pdf>.
- The DOI, <https://doi.org/10.1016/j.cagd.2026.102557>: it resolves to Elsevier's article S0167839626000506, but ScienceDirect refused the fetch (403).
- Our smoothing numbers: [2026-10-12-smooth-extraction-rho2sdf.md](../2026-10-12-smooth-extraction-rho2sdf.md).
