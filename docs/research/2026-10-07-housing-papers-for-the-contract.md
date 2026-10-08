# Gearbox-housing papers read for the contract

**Date.** 7 October 2026, 23:30-23:50.

**Question.** Read for CON-1 (contract schema v0), at the engineer's request. Which published sources can:
- (a) state a requirement the factory designs to;
- (b) give housing numbers to compete with head-to-head;
- (c) give typical values for the plausibility band;
- (d) give measures or methods worth adopting?

The engineer's direction behind it: the factory designs from published requirements and competes with published numbers, both head-to-head and against a plausibility band.

**Method and status.**
- Five PDFs were read in full by research subagents, one each. Their numbers are *not yet re-checked* in the main session; check before citing anywhere public.
- The vendor case study page and the blog were read through a fetch.
- The HAL thesis: only its abstract, through HAL's API. Its PDF sits behind a bot check.
- Jäger & Linde 2025 was read in the main session (*verified*). Hofstetter 2018 was read in part in the main session.
- The PDFs stay out of git, in the session scratchpad. Each source below has its URL, so it can be fetched again.

## Verdicts

| Source | What it is | (a) Requirement | (b) Head-to-head | (c) Band values | (d) Worth adopting |
|---|---|---|---|---|---|
| [Hofstetter et al. 2018](https://link.springer.com/article/10.1007/s10010-018-0278-9), Forsch Ingenieurwes 82:361-370 | Gearbox design synthesis for xEV axle drives under package limits (TU Graz with Magna) | **Yes, package level:** total centre distance 165 mm, ratio 9.32 ± 1 %, 366 N·m nominal input, 15,000 rpm, 944 h with a load spectrum, installation space | No: housing deformation, NVH, lubrication and park lock are out of its scope | - | The front-end's method: gear geometry (DIN 3960), face width from overlap ratio εβ = 2, shaft statics for bearing reactions, bearing life (ISO 281), package check by violating volume |
| [Kim et al. 2024](https://www.nature.com/articles/s41598-024-54606-8), Sci. Rep. 14:4145, CC BY 4.0 | Topology optimisation of an agricultural UTV gearbox housing for radiated noise (coupled structural-acoustic) | **Partly; the gear train is complete:** 7 kW, 2,650 rpm rated; two-stage parallel helical 14/46 and 21/79; mn 1.75; 20°; helix 25°; face widths 16/16 and 18/16 mm; centre distances 57 and 97 mm; profile shifts given. Not given: housing geometry, package, bearings, mounts. The load is ambiguous: "22 Nm" at the output conflicts with "7 kW at 3000 rpm" | Weak: one SPL metric on test-rig conditions, baseline geometry unpublished. Mass 4.836 → 4.847 kg; SPL −3.46 dB(A) RMS at 1,250-2,500 rpm, −2.43 dB(A) overall; simulated only | Aluminium housing in two halves, 4.836 kg, for 7 kW at 12.4:1. Housing modes, test against FE: 1,352.7/1,311.0, 1,720.5/1,696.2, 2,344.8/2,211.4, 2,539.0/2,481.0, 2,688.8/2,580.4 Hz. TE about 1.2 µm peak to peak | Mesh-order TE excitation; the drivetrain as a superelement attached to the seats by spiders; modes checked against a modal test |
| [Son et al. 2020](https://www.mdpi.com/2076-3417/10/23/8414), Appl. Sci. 10:8414, CC BY 4.0 | Same group and same gearbox: topology optimisation for minimum equivalent radiated power (ERP), mass increase capped at 20 % | No: no geometry, materials or torque | Weak, relative only: 4.84 → 5.44 kg (+12 %); ERP at 2,650 rpm −9.7/−4.2 dB (CW), −2.7/−5.7 dB (CCW). Not manufacturable as optimised, never built | FE against modal test about 2.8 %; measured 64-82 dB(A); gear-mesh frequencies 618.3 and 1,236.7 Hz at rated speed | ERP as a cheap noise measure; mesh-order maps; both rotation directions as load cases; a mass cap |
| [Son, Cho, Park 2019](https://www.mdpi.com/2076-3417/9/21/4571), Appl. Sci. 9:4571, CC BY 4.0 | Same housing: ribs for local stiffness, with FE updated against a modal test | No | No: relative gains only, no baseline mass | Modal test 1,352.7-2,939.0 Hz, damping 0.18-0.49 %; FE error −7.5 % raw, ≤ 2.84 % updated; local wall stiffness 2.8·10²-3.2·10³ N/mm | Driving-point stiffness and peak accelerance across the mesh-harmonic band; stiffness gained per gram |
| [Jäger & Linde 2025](https://www.mdpi.com/2032-6653/16/10/552), WEVJ 16:552, CC BY 4.0 | Planetary EV housing carrying two ring gears: SIMP, then X ribs, then a material study | Partly: 150 kW, 2,400 N·m output, forward and reverse, 8-fold cyclic symmetry, at most 300 mm. "Due to industrial confidentiality, the detailed force vectors and constraint definitions cannot be disclosed" | **Yes, on its own numbers** (Table 2, 12 variants). Aluminium design: 8.41 kg, 9.34 µm rotational deformation, first mode 1,382 Hz; about 21 % lighter than the original at about 5 % more deformation. TET10 at 4 mm, fixed on one side; simulated only; no AM constraints in its optimisation | First mode 1,294-1,408 Hz across materials | Rotational deformation, fixed on one side and read at the other end, as a torsional-stiffness measure |
| [Cognitive Design Systems, case study 3](https://www.cognitive-design-systems.com/case-study/accelerating-the-design-of-a-castable-gearbox-housing-for-a-hybrid-vehicle) | Vendor marketing: generative design of a die-castable hybrid gearbox housing | No: inputs are regions already drawn in CAD, plus load cases and casting rules, with no values | No performance numbers. Speed only: "124h" conventional against "12h". 96 of the 124 h are two "back-and-forth" loops; tool time is 28 against 12 h, about 2.3× | - | The step order: envelope, casting rules (draft, minimum wall, no undercuts), thickness from stress, a DFM map, B-rep export. Also hours per step as a speed measure. One design per case study |
| [Amine et al. 2026](https://www.mdpi.com/2227-7080/14/8/466), Technologies 14:466, CC BY | Scoping review of EV gearbox technologies (52 sources) | No: a made-up screening example only (1,800 kg EV, 16,000 rpm, 300 N·m) | No | Drivetrain level only: ratios 6.5-12.1 | Hard constraints before ranking, then a sensitivity check; mesh orders against housing modes. It lists "AI-assisted topology generation" as a direction 5+ years out |
| [Amaral 2023](https://theses.hal.science/tel-04478512v1/document), HAL thesis, abstract only | Lightweight gearbox housings: optimised metal housings, composites, locally resonant metamaterials against noise, with experiments | Not read | Not read | Not read | Worth a read when noise comes in |
| [Gear Technology India blog](https://geartechnologyindia.com/unlocking-efficiency-the-art-of-gearbox-design-for-electric-vehicles/) | Marketing overview | No | No | No numbers | - |

## Cognitive Design Systems: the approach, and its agent

Read 7 October, 23:55, through fetches of the pages below. The claims are the vendor's own and unverified.

- **The platform** ([site](https://www.cognitive-design-systems.com/)): "an on-premise AI-augmented platform that unifies generative design, simulation, and manufacturing constraints in a single concept generation loop". It has:
  - an implicit-modelling geometry kernel, which converts to B-rep for export;
  - generative design and topology optimisation;
  - simulation-driven design, with an embedded meshless FEA that sets thickness from stress;
  - manufacturing-driven design for casting, moulding, machining, AM and forging;
  - multi-objective comparison of cost, weight, CO₂ and lead time;
  - reusable workflows;
  - export to STEP and native CAD; on-premise or private cloud.

  It markets "first optimised concepts within a few hours". It raised €2 million in November 2023 ([3D Printing Industry](https://3dprintingindustry.com/?p=225854)).
- **The agent** ([3D ADEPT, 12 March 2026](https://3dadept.com/?p=78868)): the software is connected to Claude through an on-premise MCP server.
  - **The agent** "independently explores design options, runs simulations, evaluates performance, and refines geometry": variants, meshing, FEA, stress checks, manufacturing constraints.
  - **The engineers** point it at CAD files and set the load cases, materials and targets, then supervise.
  - **The claim:** "50+ fully analyzed variants" where a cycle used to give 3-5 concepts.
  - **The CEO:** "The bottleneck has never been judgment; it has been execution time."
  - No part and no performance numbers are published.
- **Against our plan, from what is public:**
  - **The model is the same family** as D10 (agent's model).
  - **Their starting point** is CAD regions and load cases the engineer already has. Ours is requirements: package, ratio, torque and life, from which the gear train and the bearing loads are derived.
  - **Their agent runs the variant loop.** Ours writes physical hypotheses and chooses formulations. Deterministic tools compute every number, code chooses which candidates get an FE proof, and the bound says when the space is exhausted.
  - **They publish time claims.** We would publish FE-proven numbers against published measurements.
  - **They keep no record of decisions and their consequences**, as far as they say. Ours keeps it as data.

## What follows for the contract

1. **Two kinds of requirement.**
   - A package-level requirement, as in Hofstetter: ratio, offset, torque, speed, life, installation space. The front-end then derives the gear train.
   - A given gear train, as in Kim 2024: teeth, modules, helix, face widths, centre distances. The front-end derives only the seats and loads.

   The contract takes both, with each value's source.
2. **The best head-to-head for a two-stage housing is the agricultural EV gearbox** of Kim 2024 and Son 2019/2020:
   - its gear train is complete;
   - its baseline housing mass (4.836 kg) and its modes are measured;
   - it is two-stage, so it keeps D2 (first product family).

   It has gaps:
   - Its package, bearings and mounts are missing; they become stated assumptions.
   - Its optimised results are noise measures relative to an unpublished baseline.

   So it is compared like for like on the measured, absolute numbers: housing mass, and free-free modes against mesh orders.
3. **Jäger & Linde stays the planetary head-to-head**, if a planetary module is built.
4. **The plausibility band so far** (two-stage and planetary EV housings):
   - Aluminium housings: 4.8 kg (7 kW, 12.4:1) and 8.4 kg (planetary, 150 kW).
   - First free-free housing mode near 1.3-1.4 kHz in both cases.
   - E-axle modes on their mounts: 238-719 Hz (Marano 2021, through the gearbox report).
   - Damping 0.2-0.5 %; FE against modal test within 1.4-7.5 %.
5. **The competitor in sight works in casting.** Cognitive Design Systems embeds casting rules in generative design and quotes about 12 h a design, starting from CAD regions and returning one design. Every housing in these papers is cast aluminium too. That bears on D3 (first process).
