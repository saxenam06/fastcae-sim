# Amroune et al. 2022: CAD rebuilt from a topology result by lofting along its skeleton

12 October 2026, 19:55. Read for the reviewer's advice: "keep the optimised solid as the design; do not reconstruct its skeleton as ribs".

## 1. Citation and reading

Amroune A., Cuillière J.-C., François V. (2022). Automated lofting-based reconstruction of CAD models from 3D topology optimization results. *Computer-Aided Design* 145, 103183. doi:10.1016/j.cad.2021.103183. Accepted manuscript (CC BY-NC-ND), UQTR repository.

**Read in full** as text (pdftotext, 33 pages). Tables 1-3 were extracted again in raw mode and their ratios recomputed. Figures not seen, only their captions.

## 2. Problem, input, output

- **Problem:** a 3D SIMP result that "tend[s] towards beam-like structures" turned into a solid CAD model without user interaction.
- **In:** the density field on a tet mesh, thresholded (ρ at least 0.22-0.4, per case) into a triangulated boundary, smoothed (Taubin plus Laplacian).
- **Out:** a closed B-rep (OpenCascade): branches as bicubic B-spline lofts, junctions as lofted and filled patches, united with the untouched non-design solids.
- **The optimisation:** compliance, one load case, penalty 3, volume fraction 3-4 %.

## 3. The method

- **Skeleton:** mean-curvature-flow contraction of the smoothed triangulation (Tagliasacchi et al. 2012), with three parameters.
- **Graph cleaning:** nodes inside non-design regions deleted; each loose end linked to the centroid of the nearest design/non-design interface.
- **Junctions:** cut off at "limit nodes", 1.2-2.0 times the attached branches' mean radius from the junction node.
- **Sections:** 3-4 stations a branch. At each, 6-12 rays at equal angles from the skeleton node, in the plane normal to the skeleton. A closed cubic B-spline goes through the rays' hits on the smoothed boundary; the first ray is carried along the branch so the loft does not twist.
- **Branches:** one loft through each branch's sections and its junction-interface curves.
- **Junction surfaces:** each interface is split into one segment per neighbouring branch, an intermediate segment set between each pair (projection range 80-120°), each pair lofted, the holes filled with B-spline filling surfaces.
- **The solid:** all patches sewn (G1 inside each curve, only G0 between patches), filled, and united with the non-design solid.
- **Nothing idealised:** no straightening, no averaged sections. It re-fits the smoothed shape as it is.

## 4. What it controls, and what it does not

**Controls:** member paths, section outlines at the stations, junction surfaces, links to non-design regions and, through these, the volume (1-6 % off).

**Does not control:**
- **plates and shells:** limited to beam-like results; it "could successfully be applied to simple massive shapes";
- **thickness:** no least or greatest member, no junction size;
- **smoothness:** only the triangulation's smoothing and the spline fits, with creases at every branch-junction seam;
- **manufacturing:** no draft, parting line, undercut or casting rule;
- **stiffness:** checked by FE afterwards, never held;
- **settings:** seven of them, and the density threshold, differ between the four examples; wrong values break the junctions (intersecting sections, overlapping surfaces, openings). "Fully automatic" means no picking by hand, not no tuning.

## 5. Scale and cost

- **The examples:** a bridge, an L-bracket and two cantilevers; E = 69 GPa, ν = 0.33; 10 N or 10 kPa.
- **The optimisations:** 179,167-382,148 linear tets, 21-30 iterations to a 0.5 % change in compliance.
- **The skeletons:** 9-24 branches, 4-14 junctions.
- **Runtime:** none given for any step.

## 6. Results

The smoothed optimised shape ("3D") and the CAD are each solved with the same loads, supports and material, refined adaptively to a strain-energy error "less than 3%" (reported 1.93-3.78 %). From Table 3:

| Case | Volume, 3D / CAD | C_3D / C_CAD | δ_3D / δ_CAD | σ_3D / σ_CAD (junctions) |
|---|---|---|---|---|
| Bridge | 4.08 / 3.85 % | 90 % (372 / 414 J) | 74 % (0.664 / 0.896 mm) | 97 % |
| Cantilever | 3.16 / 3.12 % | 96 % | 96 % | 89 % |
| L-bracket | 2.95 / 3.01 % | 103 % | 101 % | 96 % |
| Cantilever 2 | 3.99 / 3.93 % | 98 % | 97 % | 88 % |

**The authors' words:** cantilever, "the global compliance and the maximum resultant displacement is around 4%"; L-bracket, "3%, 4% and 1%" (compliance, junction stress, displacement); bridge, "slightly more flexible ... maximum resultant displacements are 0.9 and 0.7 mm".

**My reading:**
- **Three cases are ties:** 2-4 % in compliance, the size of the FE's own error estimate.
- **The bridge is the real loss.** Its CAD lost 5.6 % of the volume; compliance rose 11 %, peak displacement 35 %. The local measure moved three times as much as the global one.
- **Junction stresses** are 3-14 % higher in the CAD.
- **The reference is a solid, not the field.** The optimiser's own final compliance is 1.2-5.0 times that solid's (cantilever 2: 1.65·10⁻⁴ against 3.32·10⁻⁵ J).
- **A wrong label:** Table 3's row "f_CAD/f" holds f/f_CAD (bridge: 3.85/4 is 96 %, printed 104 %).

## 7. Limitations

**Stated:** beam-like results only; only G0 between patches; the stress-driven loop (their Fig. 3) not built; other TO methods not tried.

**What I see:**
- four academic cases at 3-4 % volume, one load case each, compliance only;
- editability claimed ("can be easily edited and/or refined by shape optimization"), never shown;
- no rule for choosing the settings;
- every non-design interface is a compact pad: no member runs along a non-design wall;
- **flat sections are lost.** My check: a closed cubic spline through 12 rays' hits from a rectangle's centre, over every orientation of the first ray. A 20 × 20 mm section keeps 96-105 % of its area. A 40 × 8 mm rib keeps 81-94 % of its area and 57-79 % of its bending stiffness about the strong axis; a 60 × 6 mm one 44-78 % and 7-57 %.

## 8. Code and data

**None released:** neither the paper nor the repository record links any. The skeletoniser is in CGAL's Triangulated Surface Mesh Skeletonization package (C++; a closed mesh in one piece). Lofts, fillings and sewing are in OpenCascade (`BRepOffsetAPI_ThruSections`, `BRepOffsetAPI_MakeFilling`, `BRepBuilderAPI_Sewing`); all three import from our cadquery-ocp.

## 9. For our problem

**Why ours lost stiffness:** our two skeleton tries idealised the members; this paper idealises nothing.
- **`a2_b1`** (approach 2's generator B, `skeleton_members.py`):
  - **built from** a 2D skeleton of each half's footprint in plan; half-widths the footprint's distance to its edge, capped at 8 mm; heights the median of nearby column runs; drawn as hulls of vertical cylinders;
  - **graded:** 4.85 kg, 172 µm, tilt 3.40 ×, against its source field drawn as it is (`it1_free_5.5kg`: 5.63 kg, 36.8 µm, tilt 0.93 ×);
  - **so:** 14 % less metal and 4.7 times the displacement. Our record: "round struts on bare walls, the paint's load given to no member".
- **`p40_clean`** (members straightened, widths averaged): 5.70 kg, 82 µm, tilt 2.36, against `p40_free` (5.50 kg, 39 µm, tilt 1.02). It had 4 % more metal and was twice as soft: the metal was moved, not lost.
- **The paper agrees:** stiffness held only where shape and volume held, and a 6 % volume loss cost 35 % in peak displacement. Our graded lines (bed displacement, tilt) are local, the more sensitive kind.

**Would its method avoid the loss? Only for beam-like members.**
- **What it fixes:** sections from the true boundary and explicit junctions would remove generator B's cap, median height and round struts.
- **What it cannot keep:** the paint and the walls. A curve skeleton has no place for plate-like metal, and flat sections sampled by rays lose most of their bending stiffness (section 7).
- **Untested cases:** our members stand on the shell along their whole length; the paper has no such case.
- **No fixed shell:** if the shell goes, the walls become design material, wholly outside the method.

**The reviewer's advice:**
- **Against the general claim:** a faithful skeleton reconstruction of beam-like results stayed within 2-11 % in compliance. A skeleton need not lose stiffness.
- **For the advice, in our case:** a reconstruction keeps stiffness only by reproducing the solid. It gives the same organic shape in B-spline patches, with creases, never production's ribs, walls and bosses. A cleaner look must come from the optimisation.
- **Not tested here:** smoothness, thickness or casting rules inside the loop.

**What is useful:**
- **The validation protocol:** each reconstruction against its source solid, the same loads, the FE error stated, the volume ratio beside the stiffness ratio. Our redrawings should report their mass ratio to the source.
- **A member read-out for the CAD engineer:** the drawn solid's skeleton split into branches and junctions, with each station's section (area, outline). It could extend `member_census.py`; it describes a design, it makes none.
- **Slender parts only** (a mount's arm, a strut): a lofted B-rep, if a STEP of them is needed.

**Effort:** no code to take. A beam-like version needs CGAL called from Python (bindings not checked), ray sections and spline fits (small), and OCC lofts, fillings, sewing and booleans, where our builds already failed on slivers and on several fuses at once. My estimate is one to two weeks, plus tuning for each part. Not worth it for the housing, whose load-bearing metal is mostly plate-like.

## 10. Sources

- The accepted manuscript, read in full: https://depot-e.uqtr.ca/id/eprint/10116/1/CUILLIERE_JC_31_POST.pdf
- The repository record: https://depot-e.uqtr.ca/id/eprint/10116/
- CGAL's skeletonization package: https://doc.cgal.org/latest/Surface_mesh_skeletonization/index.html
- Our numbers: `data/first_loop/grade_a2_b1.log` and the other `grade_*.log` files; `prototypes/first_loop/skeleton_members.py`; `docs/features/loop/status.md` (LOP-25, approach 2).
- The ray-section check: a scratchpad script (`ray_section.py`), not in the repo.
