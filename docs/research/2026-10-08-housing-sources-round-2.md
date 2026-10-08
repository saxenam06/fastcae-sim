# Housing sources, round 2: the seven the engineer sent on 8 October

**Date.** 8 October 2026, 19:04. All seven were fetched and read in the main session (*verified*). The PDFs and texts stay out of git, in the session scratchpad (`cadlab/`, `kit-nvh/`, `scribd/`, `shigley/`, `springer/`). Each is cited by its URL below, so it can be fetched again.

**The engineer's question:** which of these holds the key binding inputs, and derives everything else from them by equations, so that the housing design is completely described?

## The answer: Maciejczyk and Zdziennicki, TU Łódź, 2011

**"Design Basic of Industrial Gear Boxes: Calculation and Design Case Example"** is the one. It is 84 pages from the Technical University of Łódź (Department of Vehicles and Fundamentals of Machine Design).

**It is one worked case, a one-stage spur reducer, carried from its binding inputs to the gear case.**

1. **The binding inputs:**
   - the motor: 22 kW at 1,465 rpm;
   - the ratios: belt 2.4, gears 3.95;
   - the conditions: uniform input, moderate shock at the output, 3 hours a day.
2. **The size:** the output torque with its service factors, Tout = 30·P/(π·nm)·ub·ug·ka·kt, is 1.445 kN·m. Its chart then gives a centre distance of 166-184 mm; the case takes 178.5 mm.
3. **The gears:** ratios, teeth and pitch, module, face widths.
4. **The shaft loads:**
   - the belt force: 3.42 kN, with Fmax = 5·Fmin;
   - the pinion forces: Wt = 9.556 kN and Wr = 3.478 kN at 20°.
   - Then the free-body diagrams, bending and torsion, the critical sections, the bearing loads and the least shaft diameters.
5. **The bearings:** deep-groove ball bearings selected by life.
6. **The rest of the drive:** seals (ISO 6194), the V-belt drive (PN-M-85203, PN-ISO 4184) and the keys.
7. **Chapter 9, the gear case.** It is derived by its equations from three inputs: the centre distance A, the bearing bores D (the bearings' outside diameters) and the pinion's face width.
   - **Walls:** case δ = 0.025·A + 1 ≥ 7.5 mm, top δ₁ = 0.02·A + 1 ≥ 7.5 mm, height H = A.
   - **Bosses:** E = 1.2·D.
   - **Bolts:** foundation bolts d₁ = 12 + 0.036·A, housing bolts d₂ = 0.75·d₁, cap bolts d₄ = 0.08·D.
   - **Flange:** thickness 2.35·δ, width K₁ + 1.5·δ.
   - **Tables:** each bolt size's flange width K, wall-to-axis distance C, hole and spotface (Table 9.1), and the bearing caps by bore (Table 9.2).
   - **For A = 178.5 mm:** δ computes to 5.46 mm and is raised to the 8 mm floor; the bolts are M18 and M14; the flange is 20 mm thick and 58 mm wide.

**Its limits, as zenryx would use it:**
- **The rules are approximate.** The authors say so: "All formulae used here possess an approximate character only."
- **They size a sand-cast iron case for strength and castability.** Nothing in them checks stiffness, misalignment at the meshes, or modes. That is the judge's work.
- **The 7.5 mm floor is a sand-casting floor.** Die-cast aluminium walls are thinner (NADCA), and the contract's 4 mm least wall (D7) comes from the FE budget.
- **It is one stage, belt-driven and industrial.** It is not an EV reducer.

**What it gives zenryx:**
- **The rule-based arm.** Plan §11.1 names a fixed rule-based arm that the agent must beat at equal budget. Chapter 9's rules, fed by the load tool's centre distances and bearings, are that arm: deterministic, cited, and the conventional design an engineer would draw first.
- **A starting core.** The bosses (E = 1.2·D), the flange and the bolt sizes can seed the CadQuery core before the field-space structure is grown.

**The other two worth keeping:**
- **Shigley, Chapter 18, for the load chain.** It derives every step by numbered equations for a two-stage reducer, including the slopes at the bearings, and it stops at the housing. It is the template for GBX-1 (the load tool). Łódź's Chapter 9 takes over where it stops.
- **Ivanov 2018 (KTH, for AVL), for EV data.** It is the source with an EV reducer's real data: the full gear geometry, the torques and speeds, the housing's material and mass, the FE setup and results. Its bearing loads come from simulation, and its housing is AVL's.

## The seven, one by one

| Source | What it is | Binding inputs it gives | Derived by equations | The housing | Licence | For zenryx |
|---|---|---|---|---|---|---|
| **Maciejczyk, A., Zdziennicki, Z., "Design Basic of Industrial Gear Boxes: Calculation and Design Case Example"**, Technical University of Łódź, 2011 (84 pages; read from cad-lab.github.io) | A teaching handbook: one worked one-stage spur reducer with a V-belt drive | 22 kW; 1,465 rpm; belt 2.4; gears 3.95; uniform input, moderate shock at the output; 3 h/day | Everything, from the service factors and centre distance through the gears, shaft loads, shaft diameters, bearings, seals, belt and keys | **Derived:** walls, height, bosses, flanges, bolts and caps from A, D and the face width (Chapter 9) | University teaching material, licence not stated: its equations can be implemented with citation, the PDF never enters git | **The answer to the question.** The rule-based baseline arm, and seeds for the core |

| Source | What it is | Binding inputs it gives | Derived by equations | The housing | Licence | For zenryx |
|---|---|---|---|---|---|---|
| **Shigley, *Mechanical Engineering Design*, 10th ed., Ch. 18** (Budynas and Nisbett; McGraw-Hill's free sample chapter) | The textbook's power-transmission case study: a two-stage compound reverted spur reducer | 20 hp; 1,750 rpm in, 82-88 rpm out; low shock, occasional moderate; shafts 4 in outside; envelope 14 × 14 in base, 22 in high; input and output in line; gears and bearings > 12,000 h, shafts infinite life | All of it, chapter by chapter: tooth counts 16/72 (86.42 rpm out); torques 60, 270 and 1,215 lbf·ft; the least diametral pitch from the envelope height (P ≥ 5.76, so 6); transmitted loads 540 and 2,431 lbf; AGMA bending and contact (safety ≥ 1.2); shaft layout; force analysis; Goodman fatigue; slopes and deflections at the gears and bearings; bearing selection for the life; keys and retaining rings | Not designed: the envelope, and where the bearings sit | Copyrighted textbook; its equations can be cited, the chapter never enters git | **The template for GBX-1's chain**, from requirement to the seats' loads and slopes. The contract already cites its Table 7-2 for the tilt limits |
| **Ivanov, D., "Gearbox Housing Design – Topology Optimization through Generative Design"**, MSc thesis, KTH Machine Design, TRITA-ITM-EX 2018:724; commissioned by AVL Sweden. Read as the Scribd copy (document 514058589) | An EV two-stage helical reducer housing, redesigned by topology optimisation (Abaqus, Tosca, CATIA) | **The gear train:** 3 shafts and 4 helical gears, the output gear carrying the differential; ratio 7.184.<br>- Stage 1: 25/51 teeth, mn 1.85 mm, αn 18°, a 83 mm, x 0.43672 / 0.57200, b 16.5 / 15.5 mm.<br>- Stage 2: 23/81 teeth, mn 2.05 mm, αn 18°, a 125 mm, x 0.431143 / 0.568577, b 25.625 / 22.25 mm.<br>- Gears in SS 2511 steel.<br>**The duty:** 150 N·m maximum (AVL); the motor curve reaches 165 N·m; forward 150 N·m at 6,000 rpm, reverse 150 N·m at 2,000 rpm; cruise 110 km/h on a 245/45 R19 tyre, about 6,000 rpm.<br>**The housing:** EN 1706 AC-42100 T6, sand cast, three parts (flange, motor side, back side); E 69 GPa, ν 0.33, yield 230 MPa, UTS 290 MPa; **7.732 kg** (CAD, at 2.6 g/cm³) | Gear forces from torque (§2.2); Miner's rule. **Bearing loads come from simulation:** AVL EXCITE (multibody) for forward, KISSsoft for reverse | Given (AVL's design), then topology-optimised. **The FE setup:** mounts fixed at the bosses; the motor's 150 N·m reaction through the flange alone. **Pass lines:** 230 MPa, 0.2 mm. **Free modes:** the first at 1,127 Hz; mode 13 at 2,851 Hz; mode 16 at 3,159 Hz | A KTH thesis: public, rights with the author. The official copy is on KTH's DiVA, not located in this session | **A strong fourth contract, gear-train style, EV:** the gear data are complete and self-consistent (below). Missing: the bearings' designations and positions, the housing's geometry, the mounts' positions. Its band: 7.7 kg sand cast; first free mode about 1.13 kHz |
| **Farshi Ghodsi, K., Petersen, M., Colangeli, C., Cuenca, J., Kucukcoskun, K., Ott, S., "Effect of Lightweight Design on the NVH Behavior of an Electric Vehicle Gearbox Housing"**, DAGA 2024; replication dataset doi 10.35097/svJLbovVnTFAbJQV (KIT IPEK with Siemens; EU ECODRIVE, GA 858018) | An NVH study of rib arrangements on an EV gearbox housing, numerical | The housing as a mesh, and three cases: the original; A, the wheel-side housing with all ribs; B, ribs at the wheel bearings | None. The decks are Simcenter Nastran SOL 111: 183,449 grids and 287,166 CTETRA; aluminium E 70 GPa, ν 0.3, ρ 2,700 kg/m³; one harmonic force; frequency response 100-5,000 Hz in 10 Hz steps, modes to 5 kHz; air (MAT10) for the radiated sound. Acoustic power and pressure at four points, at 1,560, 1,980 and 2,010 Hz | A real EV housing's geometry, as a mesh only | **CC BY-NC-ND 4.0: no commercial use, no derivatives.** Not for zenryx's product or its repository; reading only | A possible NVH verification case for the judge (PHY), **only with the authors' written permission** (contact: K. Farshi, KIT) |
| **Dhumal, A., Abdullah, M., Ambhore, N., Jadhav, T., Kulkarni, A., "Integrated finite element and experimental vibration analysis for reliable electric vehicle gearbox design"**, *Discover Mechanical Engineering*, 2026, doi 10.1007/s44245-026-00376-8 | The spur-gear gearbox of an E-Baja student vehicle, driven by chain | Vehicle data (its Table 1, on a separate page) and a market motor | The vehicle front end: drag 155.8 N, rolling 467.9 N, grade 1,490.4 N, traction 1,958.4 N, wheel torque 501.4 N·m. Then Lewis bending, AGMA contact, shaft stress, bearing L10, the gear-mesh frequency | Analysed, not designed. FE with fixed mounts and a 2 mm mesh; a one-accelerometer FFT test, within ±3 % of the FE modes; MAC only between FE models | CC BY-NC-ND 4.0 | Low. Its vehicle-to-wheel-torque front end could later give a requirement style that starts from the vehicle |
| **Stadtfeld, H. J., "Introduction to Electric Vehicle Transmissions"**, Gleason, 2020; on KISSsoft's site (9 pages) | An overview of EV transmission concepts | Typical numbers: single-speed two-stage ratios of about 12.5 (up to 18 in three stages); 3 shafts and 6 bearings, tapered roller or angular ball; motors at 10,000 rpm, rising to 20,000-30,000 rpm by 2030 | One equation, wheel speed from vehicle speed | A word on NVH: the housing must not carry the smallest vibration into noise | Copyrighted brochure | Band values only |
| **"Advanced Machine Design Assignment" (Scribd 499747356)** | A student report, 45 pages | 1.5 kW; about 140 rpm out; base mounted with bolts; gears keyed and press-fitted; 5 years at 8 h a day and 5 days a week; 1 % failures | Gears from KHK's catalogue, shaft loads, shaft diameters, bearings, keys, fits | The casing is sized from the countershaft length, the centre distances and a clearance, with four base bolts | Unknown provenance and licence | Not used |

## Ivanov's gear data check out

Our own involute geometry (`zenryx.contract.involute`) recovers the helix angles from the published teeth, module, pressure angle, profile shifts and centre distances. The copy read garbles those two cells ("30 mm" and "0000").
- Stage 1 needs 30.10° and stage 2 29.97°, so both stages are 30°.
- At exactly 30° the stages run at 82.917 mm and 125.037 mm, within 0.083 mm and 0.037 mm of the published 83 and 125 mm. That is inside the validator's 0.1 mm tolerance.
- The ratio checks: (51/25)·(81/23) = 7.184.
- The output speed checks: 6,000 / 7.184 = 835.2 rpm, as the thesis says (835.19).

The student report's table of contents (Gear Mesh, then Counter Shaft Load, and so on) follows the Łódź handbook's.

## Sources

- Maciejczyk and Zdziennicki 2011: https://cad-lab.github.io/cadlab_data/files/design_basic_gear_boxes.pdf
- Shigley Ch. 18: https://highered.mheducation.com/sites/dl/free/0073398209/1036702/Chapter18.pdf
- Ivanov 2018, as read: https://www.scribd.com/document/514058589/Gearbox-Housing-Design
- The DAGA 2024 dataset: doi 10.35097/svJLbovVnTFAbJQV (RADAR4KIT; the engineer's download in `Downloads\10.35097-svJLbovVnTFAbJQV`)
- Dhumal et al. 2026: https://link.springer.com/article/10.1007/s44245-026-00376-8
- Stadtfeld 2020: https://www.kisssoft.com/en/products/publications/brochures/introduction-to-electric-vehicle-transmissions
- The student report: https://www.scribd.com/document/499747356/Advanced-Machine-Design-Assign
