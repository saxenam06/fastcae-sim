# GenTO, renamed TOM (Radler et al. 2025): several designs from one neural field

12 October 2026, 19:52. Read for the reviewer's proposal: a smooth 3D implicit field over the permitted volume, shape and casting rules inside the loop, the optimised solid kept as the design. It checks and corrects §2.1 of [our note of 13:42](../2026-10-12-generative-manufacturable-agentic-design.md).

## 1. Citation and reading

Radler A., Volkmann E., Brandstetter J., Berzins A. (JKU Linz; Emmi AI). *Diverse Topology Optimization using Modulated Neural Fields*. arXiv 2502.13174 v2, 17 June 2025, CC BY 4.0; a poster at the NeurIPS 2025 workshop "AI for Science". No journal version found. Version 1 (17 February 2025) was titled *Generative Topology Optimization: Exploring Diverse Solutions in Structural Design* and named the method GenTO. Version 2 renamed it TOM and changed the sampling, the settings and the numbers.

**Read:** the v2 PDF and the v1 and v2 arXiv HTML, as text, tables cell by cell; the released code's configurations and FE files (read, not run); the repository's result images.

**What our note of 13:42 got wrong** (it read v1 through a summariser):
- **Its numbers are v1's MBB beam** (9 shapes in 4 min, mean compliance +1.5 %, diversity +57 %). In v2 the mean compliance is above plain SIMP's single design by 10 % (MBB), 17 % (cantilever) and 32 % (3D bracket). So its "about 1.5 % performance" (§3) is wrong too.
- **"Smooth by construction" and "the network's frequency is the length scale" are wrong.** The authors chose a network biased to high frequencies and blame it for their undulations. No length scale is defined or measured.
- **"β from 0 to 400" is wrong:** [0, 400] is the iteration window; the released configurations raise β from 1 to 100 over it.
- **One 3D case,** not several.
- **Right:** the architecture, the diversity term, the augmented Lagrangian, p = 1.5 in 3D, the 3D grid, floaters, undulations, cost.

## 2. The representation and the FE coupling

- **Network:** a conditional WIRE. Input: the point x joined to a 2D code z. Three hidden layers (32 wide in 2D, 64 in 3D) of real Gabor wavelets, cos(ω₀a)·exp(−s₀b²), first-layer ω₀ 9-18; a sigmoid gives a density in (0, 1).
- **Shapes:** each z gives one shape, where ρ > 0.5. v2 samples z on a circle of radius r (1.2, 0.6, 0.02).
- **FE:** FEniCSx through FeniTop, on a fixed structured grid of bilinear quadrilaterals (2D) or trilinear hexahedra (3D). The density is the network's value at each node, through a Heaviside step; E = (10⁻⁶ + (1 − 10⁻⁶)ρᵖ)·E₀. PETSc conjugate gradients with algebraic multigrid, on the CPU, one process per shape.
- **Gradients:** the adjoint gives dC/dρ at the nodes; PyTorch chains it to the weights; Adam updates them. An adaptive augmented Lagrangian balances volume, diversity and geometric terms.
- **Interfaces and design region:** soft penalties on the continuous field at sampled points (f = 0.5 and matching normals on the interfaces, f < 0.5 outside the region).

It is SIMP with a neural parameterisation, not a level-set or SDF method. The FE never sees a boundary.

## 3. Smoothness, length scale and manufacturing rules

- **What sets the form:** WIRE's ω₀ and s₀, the FE grid, the β ramp, the penalty p. There is no density filter in the loop: Algorithm 1 has only the Heaviside step, and every released configuration sets `use_filters: False`.
- **The undulations are the method's.** The authors chose WIRE for its "inductive bias towards high-frequencies" and "attribute the undulations to the wavelet activation". TOM's shapes are "wavier than DB or TopoDiff" and can hold floaters, which they remove after the run.
- **Not controlled:** least or greatest member, wall thickness, junction size, curvature, draft, pull direction, parting line, any casting rule, stress, any displacement. The shared GINN code has curvature and connectedness losses; TOM's configurations set both weights to 0.
- **My reading:** the FE sees the field only at the grid's nodes, and in 3D the shape is extracted on a finer grid (128 per axis in the code). Wiggles between nodes cost nothing in the physics, which may explain the undulations and part of the 3D gap.

## 4. Diversity

δ = (Σⱼ (minₖ≠ⱼ d(Ωⱼ, Ωₖ))^½)² ≥ δ* (0.3, 0.4, 0.13), with d a one-sided chamfer distance between boundary points, differentiated through the level-set equation. Without it the 3D shapes collapsed into one; in 3D it had to start at iteration 350 of 1,000, or it broke the shapes. Their diversity score misjudges: a collapsed ablation scored higher than the base model.

## 5. Scale and cost

| Problem | TOM's FE grid | Elements | Iterations | FE solves | Time |
|---|---|---|---|---|---|
| MBB beam, 2D (half) | 180 × 60 | 10,800 | 400 | 10,000 (25 shapes) | 6.1 min |
| Cantilever, 2D | 150 × 100 | 15,000 | 1,000 | 25,000 (25 shapes) | 29 min |
| Jet-engine bracket, 3D | 26 × 43 × 15 | 16,770 | 1,000 | 9,000 (9 shapes) | 47 min |

SIMP (FeniTop, 400 iterations) took 2, 4 and 187 min, its bracket on 1.07 M elements (64 times TOM's grid), so the 3D time comparison is uneven. The deflated-barrier method (DB) took 55.5 and 123 min for 2 shapes each. Hardware: one Titan V (12 GB), a 36-core Xeon, 384 GB RAM; under 2 GB of GPU memory.

## 6. Results (v2)

Compliance against SIMP's single design, on one fine evaluation mesh:

| Problem | Mean | Best | Worst | Volume (target) | Diversity E(W₁), TOM / DB |
|---|---|---|---|---|---|
| MBB | +10 % | −3 % | +22 % | 55.1 % (53.5 %) | 4.23 / 1.36 (×10⁻²) |
| Cantilever | +17 % | +8 % | +115 % | 49.2 % (50.0 %) | 2.42 / 1.01 |
| Bracket | +32 % | +8 % | +56 % | 6.86 % (7.00 %; SIMP 7.16 %) | 0.15 / no DB |

- On the cantilever 8 % of TOM's samples missed a load and were dropped (TopoDiff: 87 %).
- Between versions the bracket's mean moved from 2 % better than SIMP (v1: 0.97 against 0.99 ×10⁻³) to 32 % worse (v2: 1.31), on the same grid and iteration count.
- **Inconsistencies:** the Figure 6 caption still calls the brackets' compliance "similar" to SIMP's; the bracket's ±0.01 cannot hold with a 1.07-1.54 range; in Table 4 the 3D run with p = 3, which the text calls an "undesired local minimum", reports a lower compliance than the base (0.09 against 0.13 ×10⁻², at a higher volume).

## 7. Limitations

**Stated:** floaters and undulations; a one-dimensional modulation manifold; the diversity measures; many solver calls; sensitivity to p and r.

**Seen:** compliance only; a soft volume (MBB 3 % over); interfaces as penalties, and in the code the bracket's loads and supports sit on the grid's outer faces nearest each interface, not on its holes; one 3D case at 16,770 elements; numbers that changed between versions.

## 8. Code and licence

The repository the paper names (MIT) holds only a README and images. The code is in `ml-jku/GINNs-Geometry-informed-Neural-Networks` (MIT; PyTorch, FEniCSx). Its TOM configurations are v1's runs (9 shapes, z on a grid or uniform); I found none for v2's circle.

## 9. For our problem

- **Our irregular shapes:** nothing here fixes them. The field is smooth as a function, but its frequency bias is one global setting: a bias high enough for 4-6 mm ribs on a housing several hundred millimetres across applies everywhere, and that makes waves. Flat walls with thin ribs need explicit features or thickness constraints.
- **Stiffness:** 10-32 % worse mean compliance than plain SIMP (best sample −3 % to +8 %). Nothing shows it beats our filters.
- **Tilt and bed constraints:** possible in principle: any quantity with an adjoint dX/dρ chains through the network, so our adjoints carry over. Not shown: Adam with an augmented Lagrangian left even the MBB's one volume constraint 3 % over. For twenty or more hard lines we would keep GCMMA on the weights (about 17,000 for 3 × 64): untried, and MMA's separable approximations may suit weights poorly.
- **300 k-1 M voxels on the 8 GB card:** the network is cheap (my estimate: 4 GB of activations for a 3 × 64 WIRE at 1 M points in one pass, 0.4 GB in chunks of 100,000). The FE stays the cost: 400-1,000 Adam iterations where SIMP took 400, and K shapes cost K solves and their adjoints an iteration. The paper's 3D grid is 18 times smaller than our 300 k voxels.
- **The engineer's "no fixed shell":** the bracket is that set-up (an empty envelope, interfaces imposed). Its answer, in the repository's image, is organic, dimpled plates and arms, with no flat walls or ribs.
- **The reviewer's proposal, in part.** Supported: a neural field can drive SIMP in 3D, change topology freely, hold interfaces finer than the FE grid and give several designs per run. Not supported: curvature, thickness, junction or casting rules in the loop; none is used. Contradicted: keeping the solid as the design; the authors clean it and propose classical refinement.
- **The first small test:** our height field is already a 2D function over the plan. Replace the column heights by a small neural field h(x, y) (3 × 64, low-frequency bias) inside our GCMMA loop, on `it1_free_5.5kg`'s set-up (peak drive, tilts and beds held at 1.15) at 10 mm voxels. Compare with the plain height field smoothed over 6, 12 and 18 mm at equal mass: graded lines, `member_census.py`'s widths and heights, pictures, then FE on each best drawing. Keep it only if it removes lumps for under 5 % of stiffness. Diversity, the paper's real contribution, is a separate test (our note's §4), priced at +10-32 % mean.

## 10. Sources

- https://arxiv.org/abs/2502.13174 (versions, licence); https://arxiv.org/pdf/2502.13174 (v2 PDF)
- https://arxiv.org/html/2502.13174v2 and https://arxiv.org/html/2502.13174v1
- https://neurips.cc/virtual/2025/126034 (the workshop poster)
- https://github.com/ml-jku/Topology-Optimization-Modulated-Neural-Fields (README, images)
- https://github.com/ml-jku/GINNs-Geometry-informed-Neural-Networks: `configs/TOM/*.yml`, `GINN/fenitop/{fem, feni_configs, fenitop_mp, fenitop_single_process, simjeb_bc}.py`, `models/wire.py`
