# Smooth geometry from a SIMP field (Ježek et al. 2025, rho2sdf): what it does, and what it can do for us

**12 October 2026, 19:25.** The engineer sent the paper (arXiv 2512.06976) and asked three things: how I read our current problem, how I read the paper, and how it can solve our problem. It was listed once before, on 9 October, as source 21 of [housing topology optimisation in practice](2026-10-09-housing-topology-optimisation-practice.md) ("meshable, not semantic CAD"). Our smoothed drawing (`LOOP_SDF`, `mesh_route.contour_sdf`) cites it.

How it was read: the PDF in full (pdftotext), and its result figures pulled out of the PDF and viewed (the beam, Fig. 9; the gripper, Fig. 12). The PDF stays in the session's scratchpad, out of git.

## 1. In short

- **What it is:** a post-processing method. It turns a density field into a smooth surface, keeps the volume, and keeps the field's members and holes.
- **It can fix our drawing.** Our smoothed drawing cost 18 % of the beds' stiffness on a 7 kg design and 73 % on a lean one, and lost 2.5-3.6 % of the mass. The paper's version costs about 8 % at the same volume. It differs from ours in two places: it interpolates the distance where we blur it, and it shifts the surface until the volume is back.
- **It cannot fix the look.** It keeps the layout by design. A clean truss comes out a smooth clean truss (the beam). An organic field comes out a smooth organic body (the gripper). Our paint would come out smooth paint, as `outcome_hfsdf_4mm_7.0kg` already showed.
- **Its own limit names our gap.** The authors write that an optimisation on a genuinely finer mesh "would potentially reveal additional structural features such as thin membranes and ribs". Production's ribs are 4-6 mm thick. Our optimiser works on 4 mm voxels, and its members are 13-14 mm wide at the median. No extraction makes ribs the optimisation could not hold.
- **Where it can lead.** Its future work is a level-set (shape) optimisation started from its smooth shape. That is the engineer's generator C. It is also today's lesson: a design is only as regular as what the optimiser itself sizes.

## 2. The paper

Ježek O., Kopačka J., Isoz M., Gabriel D., Šotola M., Maršálek P., Rybanský D., Halama R. (Institute of Thermomechanics CAS; CTU Prague; VSB Ostrava): *Smooth geometry extraction from SIMP topology optimization: signed distance function approach with volume preservation*. arXiv 2512.06976v1, 7 December 2025, submitted to *Advances in Engineering Software*. Code: `kopacja/rho2sdf.jl` v0.1.0 (Julia, MIT).

**The method, in five steps:**
1. The elements' densities go to the nodes by a local linear least-squares fit, which keeps the shape on irregular meshes better than averaging.
2. The boundary is the isocontour where the shape functions' interpolated density equals the threshold.
3. A signed distance to that isocontour is computed at the nodes of a regular grid:
   - the exact projection inside each element, solved by SLSQP (NLopt);
   - distances to the design domain's outer faces where elements are solid;
   - the sign from the interpolated density at the node.
4. The distance is made smooth by Gaussian radial basis functions, one at every grid node, their width the grid spacing.
   - The interpolation is exact at the nodes: it is not a blur.
   - A uniform shift of the distance, found by iteration, brings the enclosed volume back to the optimisation's.
   - The RBFs are global, so the matrix is dense; local ones are left to future work.
5. The surface is drawn by marching cubes or dual contouring. Tets come by isosurface stuffing (Labelle and Shewchuk 2007), which bounds the dihedral angles.

**Grid spacing:**
- The grid spacing sets the smoothing.
- The best spacing is about the optimisation's element size.
- 3.3 times coarser loses features.
- 8 times finer reproduces each element's facets.
- On a sphere the volume converges at order 1.94.

**Results:**

| Case | Measure | Raw SIMP | Plain contour | SDF |
|---|---|---|---|---|
| Cantilever (20 mm, 1 mm hexes, 40 %) | volume fraction | 0.4007 | 0.4017 | 0.3942 |
| | deformation energy (J) | 3.411 | 2.832 | 3.075 |
| | greatest equivalent stress (MPa) | - | 0.3010 | 0.2543 |
| Robot gripper (printed ABS, 16,490 hexes, 30 %) | volume fraction | 0.3000 | 0.3001 | 0.3001 |
| | deformation energy (kJ) | 115.6 | 94.8 | 102.1 |

**How to read the results:**
- **Smoothing costs stiffness.** Against the plain contour, the smooth body is 7.7 % softer on the gripper at the same volume, and 8.6 % softer on the beam, where it also has 1.9 % less volume.
- **"Stiffer than raw SIMP" is not a gain of the method.** Raw SIMP counts its grey elements at the penalty 3, so any black-and-white body of the same volume reads stiffer.
- **The stress claim.** The abstract's "18 % reduction in maximum equivalent stress" is the inverse ratio (0.3010/0.2543). The reduction is 15.5 %, as the body says.

**What the paper does not do:**
- no casting rules (no pull direction, draft or undercut); its real case is a printed plastic part;
- no control of the members' length scale;
- no features and no B-rep;
- one load case in each example.

The authors flag one more limit: the smoothing rounds the faces where loads and supports act. We already avoid it: our exact shell and exact cuts are added after the smooth members, which stand 2 mm under the exact faces.

## 3. Our smoothed drawing against the paper's

| | Ours (`LOOP_SDF=3`, `outcome_cad.py`, `mesh_route.contour_sdf`) | The paper's |
|---|---|---|
| The boundary | The metal read at 0.5 on the 2 mm grid: binary, nothing between cells | The density's own isocontour, between nodes |
| Thin parts | An opening takes out webs under about two cells (4 mm) and pinholes. It was added because FE's coarsening folded the thinned webs | Kept |
| Smoothing | The distance blurred (Gaussian, 3 mm) on the 2 mm grid. A blur moves the surface: it rounds edges and thins members | Exact RBF interpolation of distances sampled at the element size: smooth between the samples, unmoved at them |
| Volume | Not restored (`keep_mass_level` is off) | A uniform shift until the volume matches |

**What ours measured** (FE, peak drive; the records of 11 October):

| Field | Drawn plainly | Drawn smooth (`LOOP_SDF=3`) |
|---|---|---|
| Height field, 7.0 kg (`outcome_hf6_4mm_7.0kg`, then `outcome_hfsdf_4mm_7.0kg`) | 7.07 kg, beds 26.0 µm, tilt 0.89 ×, 754 Hz, no clash | 6.89 kg (−2.5 %), 30.7 µm (+18 %), 0.88 ×, 656 Hz, one clash |
| Least metal, 4.6 kg (`it1_leastmetal_plain_4.6kg`, then `it1_leastmetal_4.6kg`) | 4.71 kg, 69.0 µm, 1.02 ×, 516 Hz | 4.54 kg (−3.6 %), 119.2 µm (+73 %), 1.06 ×, 393 Hz |

The paper's own cost, about 8 % at the same volume, is the measure our next smooth drawing should meet.

## 4. What it can and cannot do for us

**It can:**
- **Draw the optimiser's field faithfully and smoothly.**
  - It keeps the mass.
  - It keeps thin members, so lean designs need not be drawn plainly (terraced) to keep their arms.
  - That narrows the drawing's part of the gap between the optimiser and FE, which the factors of safety (1.15 on the tilt, 1.35-1.5 on the beds) partly pay for today.
- **Make generator A's alternatives principled** (the plan's "vary thresholds, smoothing scales"). The sampling grid is the smoothing scale: at the voxel size it keeps every member, and at twice the voxel it should take out bumps and frayed edges under about 8 mm (inferred from the paper's grid study, not measured on ours). The volume stays the same either way.
- **Possibly mesh straight from the implicit** (isosurface stuffing). That would avoid our surface coarsening, TetGen's refusals and self-crossings. Our exact cuts (bores, faces, holes) would have to be in the same implicit, and stuffing rounds sharp edges at its cell size, so this is an option to test only if the meshing keeps failing.

**It cannot:**
- **Change the layout.**
  - The broad, low members over 42-48 % of each shell (the 7 kg height-field design; production's ribs cover 10-25 % of a face) stay.
  - So do the knots where bundles cross and the wavy sides.
  - The figures show it: the beam's smooth result is clean because its field was a clean truss; the gripper's is as organic as its field.
  - The engineer's plan says the same (§1, §10: "Smoothing is not reconstruction").
- **Keep a casting castable.** A 3D smoothing rounds members across the pull: `outcome_hfsdf`'s undercut came out 1.5 % against the plain drawing's 1.2 %.
- **Make features or a B-rep.**

## 5. How it would enter our flow

1. **As the drawing: generator A, done as the paper does it.**
   - The steps:
     - the boundary from the field's continuous values, not the 0.5 set;
     - distances sampled at the voxel size (4 mm);
     - Gaussian RBF interpolation;
     - the shift to the optimiser's mass;
     - then the exact shell and cuts as now.
   - The computation is cheap on our grid. A Gaussian on a regular grid is separable, so the interpolation is three banded one-dimensional solves (condition number about 200), not the paper's dense matrix.
   - The risk: thin webs kept may fold under FE's coarsening again.
   - The test: `p40_free` and the least-metal field redrawn, each judged by FE against its plain and `LOOP_SDF=3` drawings.
2. **For castings, in plan.**
   - Draw each half's members as an outline in plan (a 2D signed distance, smoothed and shifted to its area) and a smooth top height.
   - Their sides then run along the pull: castable by construction, and closer to a cast rib's form than a member rounded in 3D.
   - Our earlier height-field drawing (`LOOP_HEIGHT_FIELD=1`) tore at the footprints' edges. A smooth outline is what it lacked.
3. **As the start of generator C** (the paper's future work).
   - The smooth shape it returns is a sum of Gaussians on a grid, Σ αᵢ φ(‖x − xᵢ‖). That is exactly the design variable of the parametric RBF level-set method, which it cites as ref. 36 (Wang and Wang 2006).
   - The weights could be handed back to our own GCMMA and adjoint as a smooth height field ("the height field on a coarse smooth basis", [the sources of 12 October](2026-10-12-generative-manufacturable-agentic-design.md) §3).
   - The rules would be held on the smooth shape:
     - the greatest and least thickness, from the distance;
     - the fairness of outlines;
     - the pull.
   - Then the optimiser sizes a shape that is already smooth, and nothing is cleaned after the run.
   - Two limits remain:
     - a level-set keeps its start's topology unless holes are seeded;
     - at 4 mm voxels the model still cannot hold a 4-6 mm rib accurately, so production's ribs need the shape stage on FE's own mesh, or finer voxels.

## 6. Sources

- Ježek O. et al.: Smooth geometry extraction from SIMP topology optimization: Signed distance function approach with volume preservation. arXiv 2512.06976v1 (2025): https://arxiv.org/abs/2512.06976. Code: https://github.com/kopacja/rho2sdf.jl
- Labelle F., Shewchuk J. R.: Isosurface stuffing: fast tetrahedral meshes with good dihedral angles. ACM TOG 26 (2007), doi 10.1145/1276377.1276448 (the paper's ref. 17; not read here).
- Wang S. Y., Wang M. Y.: Radial basis functions and level set method for structural topology optimization. IJNME 65 (2006) 2060-2090, doi 10.1002/nme.1536 (the paper's ref. 36; not read here).
