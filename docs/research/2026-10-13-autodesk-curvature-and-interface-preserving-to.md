# Autodesk's interface-preserving level-set topology optimisation, read for a curvature penalty

13 October 2026. Read by a research subagent: check before citing.

**Why it was read.** The engineer asked on 13 October at 00:03 how to penalise the rate of change of the surface round the regions that matter (interfaces, a cover's patch, a mount's bracket) so that the optimiser stops wrinkling them. A reviewer proposed a region-weighted curvature penalty on our height field, P = Σᵢ wᵢ (h_xx² + h_yy² + 2 h_xy²), and cited two Autodesk Research items in its support:

1. <https://www.research.autodesk.com/app/uploads/2025/10/MPTOpaper.pdf> (called "MPTO", said to show "how curvature and accessibility constraints can be incorporated into the optimization itself");
2. <https://www.research.autodesk.com/publications/interface-preserving-level-set-update-strategy-topology-optimization-mechanical-assemblies/> (said to "explicitly constrain functional boundary regions while allowing other boundaries to evolve freely").

**How it was read.**

- The publication page was read through a web fetch.
- The PDF was downloaded and its text extracted with pypdf, all 15 pages.
- The result figures (Figs. 4, 5, 8, 9, 12, 13) were extracted as images and looked at; the convergence plots were not.
- A third Autodesk paper, the one the reviewer's second claim most likely meant, was read the same way (arXiv text, figures not seen).

*Verified* below means read in the paper's text. "My reading" and "inference" mark what is mine.

## The two links are one paper

*Verified.* The publication page (link 2) names one PDF, and it is link 1, `MPTOpaper.pdf`. The PDF's metadata and first page give:

- **Authors:** Adrian Humphry, Mehran Ebrahimi (corresponding), Nigel Morris, Adrian Butscher, Autodesk Research, Toronto. The publication page lists only Ebrahimi, Morris and Butscher.
- **Title:** "An interface-preserving level set update strategy for topology optimisation of mechanical assemblies".
- **Venue:** *Computers and Structures* 319 (2025) 107973, doi:10.1016/j.compstruc.2025.107973. Received 2 May 2025, accepted 26 September 2025, online 7 October 2025.

There is no separate "MPTO" paper on manufacturing constraints behind link 1. What "MPTO" stands for is not said anywhere in the PDF.

## Humphry, Ebrahimi, Morris and Butscher 2025: what the paper does

**Representation and update** (*verified*, §2, §3, App. B).

- The shape is the zero sub-level set of a level-set function on a uniform background grid, kept as a signed distance.
- It moves by the linear transport equation ∂F/∂ε + ⟨∇F, Θ⟩ = 0 (Eq. 1), integrated by a first-order upwind finite-difference scheme (Sethian).
- **The update velocity Θ** comes from the shape gradient by the Hilbert space extension (HSE).
  - The inner product is H¹ over a narrowband B of the boundary: ⟨⟨Θ₁,Θ₂⟩⟩ = ∫Θ₁·Θ₂ + γ²∫DΘ₁:DΘ₂ (§2.3).
  - Its strong form is Θ − γ²ΔΘ = G (Eq. 7), which the paper calls "a diffusive smoothing of G where γ can be characterised as a length-scale over which the smoothing takes place".
  - The smoothing acts on the update velocity. It is not a term in the objective.
- **Optimiser:** compliance is minimised under an equality constraint on volume, by an augmented Lagrangian (Nocedal and Wright) (§4.1).
  - A six-step line search starts each inner loop.
  - Later steps reuse the time step, grown a little, and back-track when the Lagrangian rises (§4.3.1).
- **Analysis:** body-fitted, with the mesh rebuilt from the signed distance at every evaluation (§4.3.1):
  - OpenVDB draws the surface;
  - geogram remeshes it, refined at the loads and supports;
  - geogram meshes the volume.

**What is constrained, and how** (*verified*, §3.1-3.4).

- **Interfaces.** Each interface Γ_I⁽ⁿ⁾ has a location p and an orientation Q.
  - Inside a small narrowband N_I⁽ⁿ⁾ round it, the velocity must lie in a finite span of affine fields: translations, rotations and orthotropic scalings aligned with the interface (Eqs. 10-11).
  - The basis has nine fields. A cylinder keeps seven: three translations, two rotations, a scaling along its axis and one uniform scaling across it.
  - So "flat interfaces remain flat, cylindrical interfaces remain cylindrical" (§3.2), while each interface's place, orientation and size are optimised.
- **How it is imposed: a hard linear restriction on the update velocity.** It is not a penalty and has no weight.
  - The paper notes that HSE's velocity is the minimiser of a convex quadratic problem (§3.3).
  - The constrained HSE (C-HSE) minimises ½⟨⟨Θ,Θ⟩⟩_γ − ∫dJ n·Θ subject to Θ = Σ z_s V_s in each N_I (Eq. 12).
  - The constraint enters through Nitsche terms (Eq. 13).
  - In the strong form it becomes Dirichlet conditions on ∂N_I, with the coefficients z found by integral conditions (Eq. 14).
  - −Θ_CHSE is shown to stay a descent direction (Eq. 15).
- **Frozen regions** have zero velocity, a Dirichlet condition on Γ₀ (§2.3). A "keep-out" region the part may not overlap appears in the L-bracket example (§4.3.2).
- **Nothing else is constrained: no curvature, no slope, no least radius, no accessibility, no draft.**
  - A search of the whole text finds neither "curvature" nor "access".
  - Manufacturability appears only in the related work (§1.2). There the paper names others' work on hollow tubes or stamped parts, on least thickness (Allaire et al. 2016) and on overhang (Allaire et al. 2017). The authors say those methods "do not allow for constraining shape updates in specified regions to preserve the geometric nature of an interface".

**The edge between constrained and free regions** (*verified*).

- In the velocity solve, the edge is a Dirichlet condition on ∂N_I. The velocity is continuous across it; its derivative is not.
- For the finite step, a smooth positive cut-off χ_I is 1 on N_I and vanishes "outside a slightly larger narrowband" (Eq. 16). It blends the exact time-dependent rigid-and-scaling motion into the C-HSE velocity. The band's width is not given.
- The introduction claims "smooth transitions to the surrounding geometry" (§1.2).
- **§5 ("Smoothness of the evolving geometry") reports the opposite case:** "It is sometimes possible to observe a kink (a.k.a., discontinuity in the tangent planes) arise and grow in the evolving shape boundary at the location where its constrained regions overlap with its free regions". The cause is that "the C-HSE procedure solves a second-order PDE". The effect is "small and usually most apparent in the earlier iterations".
- **The remedy they propose, untested:** "a second-order smoothing energy that penalises the L² norm of the HSE field along with its first two derivatives". Its fourth-order PDE "allows both the update velocity and its first derivatives to be continuous across the overlap".
  - They point to Stein, Grinspun, Wardetzky and Jacobson, "Natural boundary conditions for smoothing in geometry processing" (ACM TOG 2018), for a lightweight mixed finite element version.
  - That reference was not read here.

**The smoothing length γ** (*verified*, §4.3).

- γ is "the foremost hyperparameter", "selected heuristically", and its effect "depends on the size of the problem".
- **The values used:**
  - γ² = 500 for the L-bracket (characteristic length 140);
  - γ² = 4000 for the cantilever (length 80), set high "to help avoid the uncontrolled hole generation/removal";
  - γ² = 1000 for the rocker (length 175).
- My arithmetic: γ is 0.16, 0.79 and 0.18 of the characteristic length. No units are given.
- Larger γ converges faster; smaller γ gives "slightly lower objective function values". No number is given for this trade.
- One γ is used over the whole domain. An automated γ update is future work.

**Results** (*verified* in the text).

- **Three 3D cases:**
  - an L-bracket with an aperture, at 20 % of the start's volume;
  - a cantilever, at 30 %;
  - a suspension rocker, at 70 %.
- **Shown qualitatively:**
  - the loaded cylindrical face "remained perfectly cylindrical";
  - interfaces translated, scaled and rotated (the rocker's pin region turned to align with its force);
  - the cantilever came out as a simple Michell truss.
- **Not reported:**
  - the only plots are the Lagrangian's convergence;
  - there is no comparison with an unconstrained run or a frozen-interface run, so the constraint's cost in stiffness or mass is unknown;
  - nothing measures the smoothness of the surfaces.
- **The figures, my reading.** Organic free-form members, faceted at the grid's scale. One groove runs along the L-bracket's upright. The constrained regions (flat pads, cylinders) keep crisp primitive forms with sharp edges where they meet the free surface. The figures do not show smooth surfaces under control.

**Limitations they state** (*verified*, §3.5, §4.3, §5).

- **Topology changes.** The transport equation cannot change topology in theory. Holes appear and close anyway, through the first-order scheme's numerical dissipation. That is "uncontrolled" and slows convergence.
- **"Fine control".** A constrained region can merge into the free geometry, or into another constrained region, when the sensitivities push it there.
- **Kinks** at the edge between constrained and free regions (above).
- **Cost.** The C-HSE solve has up to three times the HSE's unknowns, but elasticity stays the bottleneck.
- **Interface sensitivities** come from finite differences.
- **Scope.** One component only; assemblies are future work.
- **Dependence.** Results depend on the start and on γ.

## The paper the second claim probably meant: Morris, Butscher and Iorio 2020

"A subtractive manufacturing constraint for level set topology optimization", Nigel Morris, Adrian Butscher, Francesco Iorio (Autodesk).

- **Venue:** *Structural and Multidisciplinary Optimization*, 2020, per Autodesk's publication page (<https://www.research.autodesk.com/publications/a-subtractive-manufacturing-constraint-for-level-set-topology-optimization/>).
- **Read as:** arXiv:2002.10246v1, title page dated 3 July 2019. Text read in full; figures not seen.

What it says (*verified* in the arXiv text):

- **Method.** Level-set topology optimisation on OpenVDB, by an augmented Lagrangian. The boundary speed is extended along the normals.
- **FE.** Autodesk Nastran on a fixed tet mesh; tets cut by the boundary are weighted by their volume fraction (§4.3).
- **Three conditions, from the user's tool.** The tool is a bit (radius r, length b) and a head (radius h), each a capped cylinder (§2). The conditions (abstract):
  - "surface smoothness such that the radius of curvature of the part does not exceed the milling bit radius";
  - every milled surface visible from an allowed direction;
  - "accessibility such that every surface patch can be reached by the tool bit without interference with the tool or head mount".
- **How they are imposed: a hard multiplicative filter on the boundary speed.** It works like gradient projection.
  - The speed is v_modified = −η dL, with η in [0, 1] (§3.4).
  - η is 0 where the boundary would grow (in the strict variant) or where no direction is accessible. Elsewhere it is max |m_i·n| over the accessible directions (Eq. 5).
  - η "transition[s] smoothly from 0 to 1 in a small 'collar'" round the violating region (§3.4).
  - Descent is kept because η ≥ 0. There are no weights; the parameters are the tool's physical sizes.
- **The curvature bound is implicit.**
  - A point is tested by casting a ray against the part offset by r (§4.1), so a hollow tighter than the bit is not carved.
  - A final morphological closing by r "explicitly enforces fillets and fills any cavities smaller than the tool radius". It is "a very minor cleaning … since the fillets and curvature of cavities are already implicitly controlled by the filter function η" (§4.4).
  - In effect it is a least concave radius, equal to the tool's. It is not a curvature penalty, and no second derivatives of the shape appear.
- **A relaxed variant** puts a positive speed α·v_max where η = 0, so infeasible regions fill in. α from 0.1 to 0.25 "work[s] well"; 0.25 is used in every example (§4.4, §5.2).
- **Load and fixity patches** have zero speed and are added back by a boolean union at every step (§3.1, §5.2).
- **Results:**
  - **TorqueStruct after 40 iterations at about 0.30 volume (Table 1).** Relative compliance is 1.000 (hemisphere search), 0.968 (normal search), 0.901 (heat search) and 0.659 unconstrained. My arithmetic: the constraint costs 1.37-1.52 times the compliance.
  - **SkateTruck** (six load cases and a stress constraint, by a "proprietary method"): the constrained part is "just 8% heavier and 2% stiffer than the unconstrained version".
  - **Tool radius:** a larger tool gives "a smoother result with fewer divots" (Fig. 10 g-i).
  - Two parts were milled on a 5-axis machine.
- **Limitations.**
  - The strict variant forbids growth, which "limits the effectiveness".
  - Its "projected" nature may stop at a worse local optimum.
  - There is no convergence proof.
- **Casting kin, not read here.** It names the closest level-set work for castings: Xia, Shi, Wang and Liu 2010 (SMO 41:735-747) and Wang and Kang 2017 (IJNME 111:1252-1273). Both constrain the level-set velocity for a two-part mould.

## Are the reviewer's two claims right?

1. **"Interface-preserving level-set TO explicitly constrains functional boundary regions while allowing other boundaries to evolve freely": accurate as stated, but it supports less than the proposal needs.** The abstract says the method "enables constrained shape updates along user-specified boundaries while allowing free-form updates elsewhere" (*verified*). But:
   - its constraint is hard and binary: a region is restricted to rigid motions and aligned scalings, or frozen, or free. It has no graded strengths and no weights;
   - it keeps an interface's geometric kind (plane, cylinder, sphere). It does nothing to protect a member's stiffness or section, such as a bracket under its mount loads;
   - its only smoothing is of the update velocity (γ), uniform over the domain;
   - the velocity is only C⁰ across the edge between constrained and free regions, and the authors report kinks there.
2. **"Autodesk's work on manufacturing-constrained optimization shows how curvature and accessibility constraints can be incorporated into the optimization itself": not supported by the cited link.**
   - Link 1 is the same interface-preserving paper. It contains no curvature or accessibility constraint and is not about manufacturing constraints.
   - It does hold related content: the velocity smoothing γ, and the untested suggestion of a second-derivative smoothing energy to remove kinks at region edges.
   - The claim is **partly true of a different Autodesk paper**, Morris, Butscher and Iorio 2020. That paper does build accessibility and a least concave radius into a level-set optimisation. It does so as a hard mask on the boundary speed, sized by a physical tool, for milling. It has no curvature penalty, no weights and no second derivatives.

## What it means for zenryx

1. **Neither paper supports weights.** (paper) Both make a geometric requirement hard: a subspace of allowed motions, zero speed, or a [0, 1] mask sized by a physical tool. Neither has a weighted curvature term, graded strengths, or a rule like "the penalty's share of the gradient". (inference) Weights set by gradient share would be our own tuning, to be justified by our own measurements.
2. **The reviewer's form is the right second-derivative energy, but it does not belong on ribs.**
   - (paper) The interface paper's own remedy for kinks at region edges is an energy on the first two derivatives, untested.
   - (inference) h_xx² + 2h_xy² + h_yy² is the squared Hessian (thin-plate) energy. It is zero exactly on planes, so a patch may slope freely.
   - (inference) The squared Laplacian (h_xx + h_yy)² would leave saddle-shaped waves unpenalised (h = x² − y², h = xy). Use the Hessian form.
   - (inference) In a height field a rib's flank is a step between columns, so the energy there is large by construction. The penalty belongs on patches meant to be surfaces (a cover, a wall), not on the members, which matches the reviewer's "rib networks mostly free".
3. **Constrain the design, not the step.**
   - (paper) HSE's γ smooths the update. It changes the path and the local optimum reached: larger γ is faster but "slightly" worse. The converged shapes still show kinks and facets.
   - (inference) In GCMMA the analogue is filtering the sensitivities, which does not bound the converged shape's curvature. To stop wrinkles at convergence, the curvature measure must be part of the problem itself.
4. **Prefer a bound to a penalty.** (inference, following both papers' hard style)
   - Use one GCMMA constraint per region: the mean or p-norm of the squared curvature of the filtered heights over the region, at most 1/R².
   - R is a least radius with units, read from production castings or the pattern's least fillet, as Morris et al. size theirs by the tool.
   - This replaces "weak, medium, strong" with a number in mm, and GCMMA reports whether it binds. The energy is quadratic in h, so its gradient is a small linear stencil and cheap.
5. **A hard subspace is the interface paper's mechanism, and we already have its height-field form.**
   - (paper) An interface keeps its kind by restricting the update near it to a few affine fields.
   - (inference) For a height field this means a region's columns are driven by a few parameters: one height, a plane a + bx + cy for a cover's patch, or a root and a tip. `topo.volume_map` already does this for volumes.
   - (paper, read across) Expect a crease at such a region's edge unless a C¹ blend or a second-derivative energy spans the edge.
   - (inference) The reviewer's 8-12 mm fade (two or three columns) comes from neither paper. Its width is ours to measure.
6. **Brackets: neither paper helps.** (paper) Constrained and frozen regions keep geometry only, and the interface paper lists the merging of constrained regions into free geometry as a limitation. (inference) Our problem (c), metal taken from a mount's arm, needs a mechanical requirement: each mount's stiffness under its own loads. The reviewer's bracket rule must stand on its own evidence.
7. **Measure the price before adopting it.**
   - (paper) The interface paper reports no cost for its constraints. The milling constraint left compliance 1.37-1.52 times the unconstrained at the same volume (Table 1; my arithmetic).
   - (inference) Any curvature bound should be run against the empty-start baseline `empty1_5.5kg`, with its stiffness, tilts and mass, before it enters the flow.
8. **The level-set machinery does not transfer.** (inference) C-HSE, Nitsche terms and transport-equation updates need a boundary-tracked level set and a body-fitted remesh at every evaluation. Ours are column heights under GCMMA with adjoint sensitivities. Take the ideas (hard subspaces, C¹ blends, bounds sized by the process), not the solver.
