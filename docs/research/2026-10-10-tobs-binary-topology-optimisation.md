# TOBS: topology optimisation with metal-or-air variables

*2026-10-10, for LOP-17. The engineer, 10:35: "How can we change the optimization algorithm such that it definitely picks either metal or air… otherwise we will never reach the goal on reality". The night had shown why: every density-based run's number rested on grey voxels (split 7.73: 0.087 × its line with them, 5.65 as metal or air; the robust run at β 32, 5 % grey: 0.39 against 1.43). [The night's record](../features/loop/2026-10-10-record-night.md).*

## The method

**TOBS**, *Topology Optimization of Binary Structures* (Sivapuram & Picelli 2018). Every element is metal or air at every iteration, and each step is an integer linear program. Four ingredients:
1. **Sequential linearisation:** the objective and every constraint by first-order Taylor expansion about the current binary design.
2. **Constraint relaxation:** a constraint far from its target may move only a fraction ε of its value per iteration toward it (ε = 0.01 in the 3D examples). Within ε of the target, the step asks for the target exactly.
3. **Sensitivity filtering:** BESO's filter over a radius r_min (1.5 elements), which gives void elements beside metal a sensitivity. Some implementations also average with the previous iteration's sensitivities, as BESO does.
4. **An integer programming solver** for the step: MATLAB's `intlinprog` in the published code, IBM CPLEX recommended.

The subproblem at iteration k (Mamedes, Picelli & Labaki 2023, Eq. 2; as published):

> minimise ∂f(xᵏ)/∂x · Δxᵏ
> subject to ∂gᵢ(xᵏ)/∂x · Δxᵏ ≤ ḡᵢ − gᵢ(xᵏ) := Δgᵢᵏ, i = 1…N_g
> ‖Δxᵏ‖₁ ≤ β N_d
> Δxⱼᵏ ∈ {−xⱼᵏ, 1 − xⱼᵏ}, j = 1…N_d

- **β, the truncation, is the step size:** the largest fraction of the elements that may flip in one iteration (β = 0.05 in their 3D cantilever of 60 × 20 × 10 hexahedra). It keeps the linearisation valid, as a move limit does in MMA.
- **The sensitivities are SIMP's,** at the binary densities. The stiffness is (E_min + xᵖ(E₀ − E_min)) k₀, and the derivative is that of a density method. The design itself never takes a value between 0 and 1.

**Where it has been used:**
- minimum compliance and volume, in 2D and in large 3D hexahedral models (Mamedes et al. 2023);
- microstructures under several non-volume constraints (Sivapuram, Picelli & Xie 2018);
- design-dependent loads: fluid pressure, thermal expansion, fluid-structure interaction;
- fluid flow;
- a body-fitted variant, TOBS-GT (geometry trimming).

The search also reports volume and displacement constraints together. Castability constraints were found only in density-based work, not in TOBS.

## What it means for our optimiser

| TOBS as published | Ours, adapted |
|---|---|
| Binary xⱼ per element | Binary per free voxel. Castable by construction: a voxel may be added only next to metal toward the joint, and removed only at a column's end, so every iterate is one piece from the joint out (the split route's rule, without a filter) |
| One objective and a few constraints | The bound formulation, as now: minimise z with every seat's ratio in both cases ≤ z (12 linearised constraints) and the mass within budget |
| intlinprog or CPLEX | scipy's `milp` (HiGHS, in `.venv`; OR-Tools is not installed here), 15 s a solve, its best found taken: FE checks every step |
| β, ε, r_min | β 1 % of the free voxels, halved when the true FE says a step made things worse (a trust region); ε 0.01 on the mass; r_min 1.5 voxels (our filter's radius) |
| Single elements flip | Per run (a column's stretch along the pull) a length from its end at the split: a step grows or shrinks a run by up to 2 voxels at its far end, one way only. Runs ending at a frozen voxel are metal throughout (2,902 voxels) |
| SIMP derivative at the binary densities | The secant derivative (SIMP's penalty 1 at metal or air): a full flip's first-order change, the same for void and solid voxels; the stiffness at metal or air is penalty 3's |

Built as `prototypes/first_loop/tobs.py` (10 October); its CPU checks pass (`tobs_check.py`): 4,724 runs, no voxel missed or counted twice; the β-32 field at 0.5 is castable as it stands (9,054 voxels, a fixed point of the casting filter); single flips stay castable; a step obeys the flip limit, the mass room and the runs' order.
| SIMP sensitivities | `topo.Voxels.analyse` with adjoints at the binary densities (12 adjoint solves, as now), then the filter |

**What it buys:**
- Every number the optimiser reports is a real shape's number, the one FE will see within the drawing's effects. Last night's robust field showed the metal-or-air number predicts FE within 5 % (1.43 against 1.37).
- Castability holds at every iterate, not just at the end.

**What it does not buy:**
- **Global optimality.** It is a local search from its start, here the robust field at 0.5, which honestly reads 1.43 × its line.
- **A guarantee of meeting the line at 7.73 kg.** It tells us honestly how close a castable housing can come. If that is above 1.0, the levers are the mass, the layout and the mount load cases.

**A risk to test first:** a flip is a large step, not an infinitesimal one, and last night's grey showed a few voxels near a seat move its tilt a great deal. So the trust region, and a check of predicted against true change on a handful of flips, come first.

## Other reading: BESO in an ABAQUS-MATLAB framework (Sun et al. 2025)

The engineer sent it at 10:43 ("not sure if they are useful"). It is the other metal-or-air method, BESO, applied to a heavy casting. Read in full.
- **Method:** BESO, soft-kill. Elements are 1 or 0.001; compliance is minimised toward a volume fraction, removed at an evolutionary rate per iteration (4 %), with SIMP's penalty 3 for the sensitivities. The sensitivity filter is linear, radius r_min; sensitivities are averaged with the previous iteration's. It stops when the compliance over the last 5 iterations changes by less than τ = 0.001.
- **The paper's contribution is software:** MATLAB drives ABAQUS through Python scripts on its CAE and ODB databases, instead of exchanging INP and FIL files.
- **The engineering case:** a hydraulic transmission test bench's adapter support, in grey cast iron HT300, CNC-machined. The design and non-design domains are tied; C3D8 elements of 18 mm (24,016 in the design domain); filter radius 50 mm; volume fraction 30 %; 38 iterations.
  - "Based on the optimized topology, the redesigned structure" weighs 940 kg against 1,362 (−31 %): the result was redesigned by hand.
  - Maximum displacement 0.808 → 0.874 mm, stress 148.2 → 154.6 MPa.
  - Built and run in a 450 kW bench (≥ 9,683 N·m, ≥ 3,590 rpm): no plastic deformation, cracks or fatigue.

**What it gives us:**
- A metal-or-air method's result was turned into a real 3D casting and proved in service.
- **One setting to change:** the filter radius at 2-3 elements, wider still "to avoid generating excessively fine structural features" that complicate manufacture. They used 50 mm on 18 mm elements (2.8). Ours is 1.5 voxels, and the torn fins in our drawings come from members a voxel thick. For the binary runs, r_min of 2.5 voxels (15 mm) is worth a test.

**What it does not give us:**
- An objective other than compliance with a volume target. BESO ranks elements by one sensitivity, so our twelve seat constraints would have to be lumped into one number. TOBS keeps them.
- Any casting or pull-direction rule.
- An automatic drawing: they redrew by hand.
- A housing.

## Sources

1. Sivapuram R., Picelli R. (2018). *Topology optimization of binary structures using Integer Linear Programming.* Finite Elements in Analysis and Design 139, 49-61. (Cited by the authors' repository; not read.)
2. Picelli R., Sivapuram R., Xie Y.M. (2020). *A 101-line MATLAB code for topology optimization using binary variables and integer programming.* Structural and Multidisciplinary Optimization. Code: <https://github.com/renatopicelli/tobs> (the repository's README read: the four ingredients, `intlinprog` by default, CPLEX recommended).
3. Sivapuram R., Picelli R., Xie Y.M. (2018). *Topology optimization of binary microstructures involving various non-volume constraints.* Computational Materials Science 154, 405-425. (Via the repository; not read.)
4. **Mamedes L., Picelli R., Labaki J. (2023).** *An implementation of the TOBS method for topology optimization of large-scale 3D structures.* 27th ABCM International Congress of Mechanical Engineering (COBEM 2023), COB-2023-2372. <https://www.sistema.abcm.org.br/articleFiles/download/38944> (**read, pp. 1-4**: the formulation, Eqs. 1-5; the SIMP sensitivities, Eqs. 6-9; the filter, Eqs. 10-11; the parameters r_min 1.5, ε 0.01, β 0.05).
5. Search results on TOBS's other uses (design-dependent loads, fluid-structure interaction, TOBS-GT, volume with displacement constraints) and on stress-constrained castable design (density-based, NWPU): the result pages' summaries only.
6. **Sun D., Yang X., Liu H., Yang H. (2025).** *BESO Topology Optimization Driven by an ABAQUS-MATLAB Cooperative Framework with Engineering Applications.* Applied Sciences 15(9), 4924. <https://doi.org/10.3390/app15094924> (CC BY; **read in full**: the PDF from MDPI's file server, as the article page refused the fetcher).
