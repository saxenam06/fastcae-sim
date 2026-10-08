# What engineers ask of a gearbox housing: the requirements the contract takes

**Date.** 8 October 2026, 00:20.

**For.** CON-1 (contract schema v0). The engineer asked on 8 October for the realistic requirements a user brings:
- meaningful, and industry practice;
- the questions gearbox CAE and design engineers ask every day;
- each one taken from the research already done, with its evidence, and nothing invented.

**The rule of this page.**
- Every row names its source, and keeps the confidence tag the source report gave it:
  - **High:** a primary page or paper was read.
  - **Medium:** a secondary source, or a listing only.
  - **Low:** one weak source.
  - **Inferred:** arithmetic or reasoning in the report.
  - **gap:** searched for and not found.
- Section 6 is a proposal, and says so.

**Sources, by short name.**

| Short name | Document | What it is |
|---|---|---|
| GHE | [fastcae: Gearbox-housing engineering](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md) | 6-7 Oct; 67 sources; standards, bearing and gear makers, papers, OEM releases |
| PAINS | [fastcae: How industry designs a casting, and where it hurts](../../../../fastcae/docs/research/2026-09-30-industry-design-pains.md) | 30 Sept; practice knowledge plus the library's sourced reports |
| AM | [fastcae: AM for metal housings](../../../../fastcae/docs/research/2026-10-06-am-housings-rules-and-cases.md) | 6-7 Oct; LPBF rules, standards, printed housings |
| PAPERS | [Housing papers read for the contract](../../research/2026-10-07-housing-papers-for-the-contract.md) | 7 Oct; Hofstetter 2018, the agricultural EV gearbox (Kim 2024, Son 2019/2020), Jäger & Linde 2025, Cognitive Design Systems. The agricultural-gearbox numbers were read by subagents and are not re-checked |

---

## 1. The questions engineers ask of every housing design

These are the checks a gearbox engineer signs off on (PAINS §2; GHE "Verdict checks"). Each becomes a measure the deterministic judge computes, and a target in the contract.

| # | The question | What answers it | Typical value or target | Source | Confidence |
|---|---|---|---|---|---|
| 1 | **Will the gears stay aligned under load?** | Per-mesh misalignment, in the plane of the axes and normal to it, per face width; then KHβ | A share, agreed with the gear engineer, of the parallelism tolerance. For example, grade N6, d 50-125 mm, b 20-40 mm: 6.0 µm out of plane and 12 µm in plane per face width, manufacturing included. About 10 µm of misalignment raises KHβ by about 0.3 | GHE §1.1-1.2 (JGMA 1102-01 via KHK; ISO 6336-1; Kissling 2014). PAINS §2: "the gear meshes' alignment is the requirement that matters most" (for the GRC) | High for the tolerances; Inferred for the share and the KHβ step |
| 2 | **Will a bearing tilt beyond its allowance?** | The tilt of each seat: the rotation of a single pad, i.e. the axial-displacement difference across the bore divided by its diameter | 0.5-1.2 mrad tapered roller; 0.8-1.2 mrad cylindrical roller; 1-3 mrad deep-groove ball; under 0.5 mrad at an uncrowned spur gear | GHE §1.2 (Shigley, Table 7-2: "rough guideline"); KPI extraction after Honeywell (Das 2011), GHE §6.3 | High |
| 3 | **Will the centre distance hold, loaded and hot (the backlash)?** | Change of each stage's centre distance under load and temperature | Manufacturing tolerance ±20 µm (50-125 mm) or ±26 µm (125-280 mm) at N5-N6. An aluminium housing at +80 K grows a 165 mm centre distance about 0.15 mm more than the steel gears | GHE §1.3-1.4 (JGMA 1101-01 via KHK) | High for the tolerance; Inferred for the growth |
| 4 | **Will the bearing seats stay round?** | Ovalisation of each seat under load | Roundness and cylindricity IT4-IT5, about 8-18 µm for 50-180 mm bores. A seat model that carries no tension captures ovalisation | GHE §1.3 (JTEKT Table 14-1; ISO 286-1); GHE §6.3 (FZG 2022) | High / Medium |
| 5 | **Will the bearing fit hold when it is hot (creep)?** | Interference left at the hottest case; or an anti-creep feature | Aluminium needs "relatively greater than normal interference". Creep is "more severe in aluminum enclosures"; O-rings are proposed. A 72 mm seat warmed by 80 K loses about 66 µm of interference, more than the 30 µm IT7 band | GHE §1.4 (JTEKT; Eaton SAE 2026-26-0598; Timken SAE 910799) | High; Eaton and Timken abstract only; Inferred for 66 µm |
| 6 | **Will it whine or resonate?** | The Campbell map: modes against mesh and motor orders over the speed range. Then the forced response (ERP or surface velocity) | Orders kept at least 3 % apart. The supports' bending modes come first. ERP at most the baseline's. No public OEM rule of the form "first mode at least X Hz" | GHE §1.5 (Marano et al. 2021) | High for the rules; gap for an OEM modal target |
| 7 | **Will the bearings last?** | Bearing life with the seat's tilt and deformation | "The elastic adjacent construction has an influence on the distribution of bearing load and thus on the rating life" | GHE §5.1 (Schaeffler 2020); ISO 281 named, not read | High (the influence) |
| 8 | **Is it strong enough, and will it survive fatigue?** | Static stress against allowable over safety factor; fatigue at ribs, fillets and bolt holes | LPBF AlSi10Mg: 110 MPa at 2·10⁷ cycles fully reversed, turned specimens; as-built "significantly reduced". Cast parts are checked against the FKM guideline | AM lines 67, 189 (EOS data sheet); PAINS §1 (FKM named) | High for EOS; Low for FKM (not read) |
| 9 | **Will the joints hold and the housing stay sealed?** | Per bolted joint: no opening, no slip, bolt fatigue, surface pressure. At the sealing line: no opening; gap change and sliding within the sealant's capability | As-cast faces are not flat enough to seal, so sealing faces are machined. The machined flatness value comes from the sealant supplier and the OEM drawing | GHE §1.6 (VDI 2230 scope; ThreeBond TN107; NADCA 2015) | High for the criteria; gap for the flatness value |
| 10 | **Does it hold the park lock?** | Stress and deflection at the pawl pivot, the actuator bosses and the park gear's seats | US rule: at most 150 mm of movement on a 10 % grade. The OEM's own grade and the abusive-engagement loads come from the engineer | GHE §1.8 (FMVSS 114) | High for the rule; gap for the OEM values |
| 11 | **Do the mounts carry the reaction?** | Stress and stiffness of the mount bosses and supports under torque reaction plus vehicle accelerations | With the motor in the same housing, the mounts react about i·T_motor. ZF: 380 N·m × 9.6 = 3,648 N·m against its quoted 3,500 N·m axle torque | GHE §1.9 (ZF release; Marano et al.) | High for the data; Inferred for the statics |
| 12 | **Does it fit the package?** | Violating volume against the installation space | "The package integration of the gearbox is then quantified by a specific" violating-volume measure | Hofstetter et al. 2018 (PAPERS; GHE §3) | High |
| 13 | **Can it be made?** | The process's rules checked on the built geometry | **Die casting:** draft 2° inside, 1° outside for features at least 1 in deep; walls about 1-5 mm; at least 0.25 mm machining stock. **LPBF:** least wall 0.4 mm (AlSi10Mg, EOS M 290); downskin under 45° needs supports; horizontal channels self-supporting to about 8 mm; powder escape 1-3 mm; machining stock 0.5-2 mm; Rz 30-140 µm as built | GHE §5.3 (NADCA 2015; ISO/ASTM 52911-1); AM lines 58-65, 153-179 | High (NADCA, EOS); Medium (IWU17 values) |
| 14 | **How much lighter or cheaper, at equal performance?** | Mass, computed from the geometry; cost | "A 5-15 % mass cut at equal bearing-seat stiffness and stress is the usual industrial win" (practice knowledge). Jäger & Linde: about 21 % lighter at about 5 % more torsional deformation. Cost: casting about 0.20 EUR/cm³ at 100 units, SLM under 1.0 | PAINS §4; Jäger & Linde 2025 (PAPERS) | Practice knowledge (unsourced); High (Jäger & Linde) |
| 15 | **Can I trust the FE answer?** | Margins over the model's uncertainty; the seat model stated | A good housing model is still 10-25 % from test: 11.5 % RMS detailed, 25.2 % simple, on a wind gearbox. The seat model moved the error from 26.6 % (rigid housing) to 11.7 % (eight points per seat, no tension) | GHE §4 (Gutierrez Santiago et al. 2023); GHE §1 item 5 (FZG 2022) | High for the evidence; Inferred for the margin size |

---

## 2. What the engineer gives: the contract's inputs

**Two ways a requirement arrives.**
1. **Package-level, as in Hofstetter et al. 2018.** The inputs are "a. transmission ratio, b. (range of) offset between input- and output shaft, c. load spectrum and service life ..., d. desired installation space" (GHE §3; High). The front-end then derives the gear train. The answer is not unique: "deduction of component requirements is not unique" (GHE item 9; High).
2. **A given gear train, as in the agricultural EV gearbox** (Kim 2024, Table 1): tooth numbers, normal module, pressure angle, helix angle, face widths, centre distances, profile shifts (PAPERS; read by a subagent). The front-end then derives only the seats and the loads.

**The fields.** The groups and fields are GHE's "Requirement fields a housing problem needs". The typical values are each source's own.

| Group | Fields the engineer gives | Typical EV values | Source | Confidence |
|---|---|---|---|---|
| **Duty** | Motor torque-speed envelope in both directions, peak and continuous, with the point of measurement (motor or wheel); maximum and base speed; regeneration torque; duty spectrum (load collective with times); temperatures (oil, housing, ambient, cold start) | Motors 10,000-20,000 rpm, up to 30,000 in premium units (AVL). Single motors 163-650 N·m and 74-360 kW. Magna: 366 N·m nominal input, 15,000 rpm, 944 h service life. VW MEB: 310 N·m, 150 kW, 16,000 rpm. ZF: 380 N·m, about 13,000 rpm | GHE "Requirement fields"; GHE §2 (AVL SAE 2020-01-1501; University West 2024; Hofstetter 2018; VW; ZF) | High; Medium for University West |
| **Vehicle** (optional, upstream) | Mass, rolling radius, top speed, gradeability, acceleration, drive cycle; park-lock holding grade and engagement-speed limit | Gradeability bounds the highest ratio: γ1·γfd ≥ g·r_w·m_v·(c_r·cos β_max + sin β_max)/T_m,max, with β_max = 7.5° in that study | GHE "Requirement fields"; GHE §3 (Borsboom et al. 2022) | Medium |
| **Gear train** (way 2), or ratio and offset (way 1) | Topology (stages, axis layout, differential), stage ratios, macro-geometry (z, mn, αn, β, helix hands, b, x), quality grades, micro-geometry, park-gear location | Single-speed two-stage helical with integrated differential is the common topology. Ratio about 8-13 (Magna 9.32 ± 1 %, ZF 9.6). Magna's total centre distance 165 mm. Face width for smooth running from overlap ratio 2: b = εβ·π·mn/sin β | GHE item 8 and §2, §6.1 (Hofstetter 2018; ZF) | High |
| **Bearings** | Type and arrangement per seat (X or O, locating and floating), effective load centres, setting or preload, fits, outer-ring anti-rotation | Magna: deep-groove ball and cylindrical roller on the input, a tapered pair on the intermediate shaft, deep-groove balls on the differential. Housing fits: H7 for a stationary outer-ring load; JS7, K7, M7 as loads become indeterminate or heavier | GHE §2 (Hofstetter 2018); GHE §1.4 (JTEKT) | Medium (Magna's bearing table); High (JTEKT) |
| **Interfaces** (the exact core; fixed at L1 (fixed interfaces)) | Bore frames, diameters, widths, shoulders; position, coaxiality, parallelism and form tolerances; machining stock and datums; split and cover faces with bolt pattern and sealing line; mounts (positions, mount stiffness); motor flange; park-lock pawl pivot and actuator; oil, breather, drain and fill ports | Tolerances as in questions 1-4 | GHE "Requirement fields" | High (the field list); values as cited above |
| **Package** | The installation space the housing must stay inside | Hofstetter's demonstration gearbox is fitted into a given space and scored by violating volume | Hofstetter 2018 (PAPERS) | High |
| **Targets** | Per-mesh misalignment (µm per face width, in and out of the plane of the axes) or KHβ; bearing tilt; seat ovalisation; centre-distance change; bearing life; stress and fatigue safety factors; bolt and flange criteria; order-separation and response targets with their boundary conditions; mass; cost | As in section 1 | GHE "Requirement fields" | as section 1 |
| **Manufacturing profile** | Process (die casting, sand casting, AM, hybrid); alloy with a property card (E, ν, ρ, CTE, fatigue); draft; minimum and maximum wall; as-cast flatness; minimum stock | As in question 13. Series e-drive housings "are often made of cast aluminium alloys". Which die-casting alloys are used was not confirmed | GHE "Requirement fields"; GHE §2 (Schweigert et al. 2022) | High; Low for the alloys |

---

## 3. What the tools derive: never typed by the engineer, never written by the agent

GHE, "Derived quantities a deterministic model must compute (never the agent)" (items 1-10; High where the method is from a primary source):
1. Unit, frame and sign consistency, and the checks P = T·ω and v = ω·r/i. VW's "10x" implies about 12.4 at 160 km/h and 16,000 rpm (GHE §2, Inferred).
2. The ratio split and, per stage and per load case, the mesh forces: Ft = 2T/d, Fr = Ft·tan αn/cos β, Fa = Ft·tan β (JTEKT eqs. 5-14, 5-16, 5-22).
3. The bearing reactions per load case. These include the moment of the axial force, spans measured to the effective load centres, and the induced axial forces of tapered pairs (JTEKT eq. 5-29), plus the preload and the axial load share.
4. The torque reaction into the mounts or the motor flange, and the park-lock torque at the park gear.
5. Thermal growth: the fit change at every seat, the change in preload, and the growth of every centre distance and its backlash.
6. Mesh and motor orders and their frequencies over the speed range, with the Campbell crossings and the separation between orders.
7. From each FE solve:
   - per bore: the centre's translation and tilt, the ovalisation, the shaft misalignment and the pad rotation;
   - per mesh: the misalignment in and out of the plane of the axes, then KHβ.
8. Bearing life with seat tilt and deformation.
9. Bolt and flange quantities by VDI 2230.
10. Mass, centre of gravity and inertia.

---

## 4. The load cases engineers run

GHE, "Load cases to include", with each case's basis:

| # | Case | Why | Basis |
|---|---|---|---|
| 1 | Drive, forward, at peak motor torque | maximum mesh and bearing forces | Hofstetter; Jäger & Linde (forward) |
| 2 | Coast or regeneration at peak regenerative torque | Fa reverses and the axial-force moment swaps bearings | FZG; GHE §6.2 |
| 3 | Drive, reverse | Ft reverses | Jäger & Linde (reverse) |
| 4 | Duty spectrum | bearing, gear and housing fatigue life | Hofstetter (load spectrum) |
| 5 | Rated torque at high speed | the NVH and thermal operating point | Marano; Inferred |
| 6 | Park lock: holding, then abusive engagement | pawl pivot, actuator bosses, the park gear's seats | FMVSS 114; the abuse loads are a gap |
| 7 | Mount loads: torque reaction plus vehicle accelerations | mount bosses and supports | GHE §1.9; Honeywell analogue |
| 8 | Assembly state: bolt preload, bearing press fits, preload | the pre-stress the operating cases sit on | Schaeffler; VDI 2230 |
| 9 | Thermal: uniform heating and gradients, hot and cold | fits, preload, centre distance, flange movement | JTEKT; SAE 910799; ThreeBond |
| 10 | Modal (on mounts and as bolted) and forced response | whine, whistle, radiation | Marano; Souza |
| 11 | Misuse torque spikes (wheel slip and regrip, potholes) | peak strength | none confirmed (Low) |
| 12 | Gravity | small, but always present | Inferred |

For noise, the agricultural EV gearbox studies add (PAPERS, read by subagents):
- both rotation directions as separate cases (Son 2020);
- excitation by the mesh-order transmission error (Kim 2024).

---

## 5. What the research could not confirm

The engineer supplies these, or the contract marks them as assumptions:
- An OEM limit for housing-induced misalignment. None is public; the share of the tolerance is agreed with the gear engineer (GHE §1.2).
- An OEM modal target of the form "first mode at least X Hz". None is public (GHE §1.5).
- The park-lock holding grade beyond the US 10 % rule, the engagement speed and the abuse loads (GHE §1.8).
- The machined sealing-face flatness (GHE §1.6).
- The fatigue guideline for cast housings (FKM): named, not read (GHE §5.1).
- Oil level, churning share and dry-sump practice in EVs (GHE §1.7).
- The die-casting alloys of e-drive housings (GHE §2).
- The mass of a two-stage housing alone (GHE §2). One data point since: the agricultural 7 kW housing at 4.836 kg (PAPERS).
- How ZF, GKN, Bosch, Ricardo and FEV verify their housings: not reached (GHE §5.1).

---

## 6. Proposal for CON-1 (contract schema v0): what L1 needs first

*This is a proposal, not evidence.* It follows D6 (MVP physics): statics and modes in P1 (one requirement end to end), then a uniform temperature and the park lock in P2.

| Part of the contract | In v0 | Answers questions |
|---|---|---|
| Duty: peak drive, peak regeneration, reverse; the speed range | yes | 1-6, 11 |
| The requirement, in either way: Hofstetter's four inputs, or a given gear train | yes | all |
| Bearing type and arrangement per seat | yes | 2, 7 |
| Interfaces: seat frames and sizes, the split face and its bolts, mounts, the motor flange | yes | 1-4, 9, 11 |
| Package (installation space) | yes | 12 |
| Targets for questions 1-4, 6, 12-14 | yes | as listed |
| One manufacturing profile, with its property card | yes | 13 |
| Temperatures and the fit check | P2 | 3, 5 |
| Park-lock grade and abuse case | P2 | 10 |
| Duty spectrum, life and fatigue; bolts and sealing | finalists, later | 7-9 |
| Forced response (ERP) | later | 6 |
