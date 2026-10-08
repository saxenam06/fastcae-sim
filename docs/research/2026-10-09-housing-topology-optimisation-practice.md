# Topology optimisation of gearbox housings: how it is practised

**Date.** 9 October 2026, 02:15-02:50.

**Question.** For the first full loop (a plain shell-and-wall housing, sand cast in aluminium, two halves split across the shafts, a two-stage helical EV reducer → topology optimisation (TO) → ribs → CAD → mesh → couplings, supports and the calculated bearing loads → solve → grade against the contract): do published housing studies read the ribs off one TO, or iterate; how is a density field turned into ribs; how is the problem set up; are sub-spaces used; what do they gain?

**Method and status.**
- *Read in full:* Ivanov 2018 (from the Scribd copy saved in this session's scratchpad on 8 October), Jäger & Linde 2025, Kim 2024, Son 2020, Son 2019, Das 2011, Amaral 2023, Triller et al. 2023.
- *Abstract only:* Ogata 2005 (Honda), Barreiro 2019 (SEW), Klarin 2020 (AVL), Slavov 2019 (two papers), Farshi Ghodsi 2024 (KIT), Liu 2012, Inoue 1992 and 1995 (NASA), and the interpretation papers.
- *Snippet* means seen only as a search result: low confidence.
- What fastcae's library already settles is cited, not researched again. The PDFs stay out of git, in session scratchpads. Each source below has its URL.

## 1. In short

1. **It is not one run, and practice iterates.** The paper the engineer remembers is most likely **Ivanov 2018**, the KTH thesis for AVL that our contract's EV reducer follows. It analysed the original, and the original stripped of its ribs. Then it ran one whole-envelope TO, and at least four TO runs on four blocks conformal to the shell. Between those runs it:
   - tightened the member limits;
   - added a pull direction per block;
   - switched the objective from strain energy to the six seat-centre displacements;
   - piloted an extended space.

   The hand-drawn proposal, a compromise between two result sets, came within 57 g of the original's mass. It deflected more than the original and was discarded. When the reading is not obvious, the thesis calls a second or third cycle, in design spaces shrunk round the first results, "unavoidable". Other multi-loop studies:
   - **Barreiro 2019 (SEW):** an FE check after each loop, comparing safety and weight with the previous version.
   - **Triller 2023 (BMW):** ribs added by hand, with a free-size optimisation re-run "after each of those adaptions", then about 20 sizes optimised.

   Even the single-TO studies add a sizing round: Jäger & Linde ran 13 variants; Honda ran a shape optimisation of the rib thickness after placing the ribs.
2. **What changes between runs:**
   - the design space: whole envelope, then shell-conformal blocks, then a space shrunk round the first result, or the weak areas only;
   - the manufacturing rules: without member limits and a pull direction, the solver thickens walls and makes shapes that cannot be moulded (Ivanov);
   - the objective: compliance, then seat displacement, frequency or radiated power;
   - the material budget;
   - the load cases, their weights, and the loads themselves (Amaral re-derives the bearing loads from the gearbox model after each housing iteration);
   - and every study re-analyses the interpreted CAD.
3. **Interpretation is done by hand in every housing study read.** In each, a designer:
   - thresholds and smooths the field;
   - lays the iso-surface beside the CAD;
   - draws ribs along the paths seat-to-mount, seat-to-seat and mount-to-mount;
   - drops what breaks a function (Ivanov's solver bridged the oil port);
   - then sizes the ribs by a parameter study.

   Tools exist for parts of this: curve and surface skeletons turned into B-rep, casting-aware reconstruction, SDF smoothing, and learned segmentation (2D). None was applied to a housing, and plate-like ribs are their weak case. Judgement decides:
   - which blob is a rib, a thicker wall or an artefact;
   - which load path to keep;
   - junctions, patterns, and conflicts with oil, assembly and tool access.

   A tool can do the rest: thresholds, skeletons, rib candidates with height and width, recurring features across runs (Ivanov's rib "suggested in every simulation"), rule checks, the CAD build and the re-analysis.
4. **The set-up is consistent across studies:**
   - seats, bosses, flanges and mount faces frozen;
   - the gear cavity and the access to bolts and mounts subtracted;
   - bearing loads put in through ring-centre nodes with kinematic or rigid couplings, or through the drivetrain as a reduced substructure, so the loads follow the housing's stiffness;
   - mounts fixed at the bosses (fastcae measured that clamping the bolt holes instead of using couplings moved the worst tilt by 40 %);
   - halves tied, which raises the modes;
   - objectives: compliance in most studies, seat displacement (Ivanov), mass under a stiffness limit (Jäger & Linde), radiated power or sound pressure (Son, Kim);
   - budgets: 8.4 % of the envelope, equal to the original's metal, and 3.5-4.0 % of the shell-conformal blocks (Ivanov); 30 % of the bulk added to the housing (Kim); a 30 % mass-reduction aim (Amaral);
   - casting rules: a pull direction per half, least and largest member, least gap; least member ≥ 3 elements (OptiStruct);
   - results depend on the mesh (Ivanov).

   The alternatives in use:
   - rib layout along the line from the excitation to the support (Inoue; Das);
   - rib sizing (Son 2019; Jäger & Linde);
   - wall-thickness and free-size optimisation (Inoue; Triller; Amaral's modal sizing);
   - topography (beads) for thin walls (OptiStruct);
   - variable-height stiffener TO with a casting filter.
5. **Sub-spaces are used, with costs.**
   - Son 2020 ran the TO only in the weak areas found by radiated power, then the operating shape, then strain energy. It faults earlier studies whose design areas were chosen "based on experience or without clear criteria".
   - Kim 2024 used three separate domains; one did nothing.
   - Son 2019 and KIT 2024 picked weak areas by local stiffness.
   - Inoue 1992 optimised one plate at a time ("the top plate alone is effective").
   - Ivanov recommends a second, narrower cycle.

   **For sub-spaces:** less compute, a finer grid, untouched interfaces, an easier reading, aimed at the measure that binds. **Against:**
   - A local run misses remote load paths, and it cannot question the whole layout. Ivanov's whole-envelope run left out the original's mount-to-mount rib, which flags a missing load case, a model error or a saving.
   - The weak area moves as the design changes.
   - Local fixes interact.
   - Only a whole-domain run gives the bound that tells when to stop.
6. **The gains are modest once interpreted and checked.**
   - Jäger & Linde: −21 % mass for +5 % torsional deflection (concept only).
   - Liu 2012: −5.9 % mass.
   - Amaral: −24 % mass, which halved the first mode (882 → 426 Hz); a plate's thickness was then sized to raise it.
   - Kim: −2.43 dB(A) at +0.2 % mass.
   - Son 2020: radiated power −2.7 to −9.7 dB at +12 % mass.
   - Son 2019: +43 % local stiffness from one rib family.
   - Triller: −25 kg on a mega-casting.
   - Ivanov: none; the proposal was discarded.

   A typical count, read across the table: one whole-domain TO, 1-4 re-runs with changed settings, 1-3 interpret-and-check loops, and a sizing study of about 10-20 variants. The mega-casting took hundreds of samples.
7. **fastcae measured the same.** Its voxel model read 1.0-2.4× stiffer than the mesh. A polish that claimed −56 to −58 % on voxels gave, on the CAD, 1 design better, 3 worse and 1 unbuildable. Holding the casting rules inside TO cost 11 % on displacement. The relaxed bound reached 87.9 % of the goal, the solved design 85.7 % ([geometry lessons](../../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md); [plan](../features/product/plan.md) §3). A TO result is a hypothesis; the CAD, meshed and solved, is the judge.

## 2. The studies

| Reference | Set-up | Iterations and what changed | Into ribs | Gain | URL |
|---|---|---|---|---|---|
| **Ivanov 2018**, KTH MSc for AVL; EV two-stage reducer, sand-cast AC-42100, 7.73 kg *full* | Abaqus + Tosca, TET10. Bearing rings tied to the seats; loads at 6 ring-centre nodes by kinematic couplings; mounts fixed at the bosses (all DOF); 150 N·m motor reaction on the flange's bolt areas; forward and reverse static cases; seats and bosses frozen | (0) original, and "stripped" (−749 g of ribs: over the 0.2 mm limit). (1) Whole envelope minus the gear cavity and the boss access; least strain energy at the original's material (8.4 %); least member 10 mm; 16 iterations, 3 h on 12 CPUs. (2) Four shell-conformal blocks, tied; budget the ribs' volume; member 10-30 mm, gap 5 mm, no pull direction: not manufacturable (without rules the solver thickened the walls or made shapes that cannot be split-moulded). (3) Member 7-15 mm plus a pull direction per block (opposite on the two sides; read as along the shafts). (4) Objective → the six seat-centre displacements; member 10-20 mm. (5) Extended space, no rules (pilot): unrealistic | Iso-surfaces exported to CATIA beside the CAD. A rough proposal by hand (no drafts or fillets), compromising runs 3 and 4; suggestions that broke function dropped | **None.** Within 57 g of the original's mass, it deflected more (seat 6: 0.052 → 0.066 mm forward, 0.138 → 0.163 mm reverse); discarded. Advice: analyse the raw TO result to tell a bad set-up from a bad reading; then a 2nd or 3rd cycle in narrowed spaces, or a sizing sweep | [Scribd copy](https://www.scribd.com/document/514058589/Gearbox-Housing-Design) |
| **Jäger & Linde 2025**, planetary EV housing, 150 kW *full* | ANSYS SIMP (p 3); least mass under torsional-stiffness and volume limits; forward and reverse; 8-fold cyclic symmetry; whole housing except the mounting faces; least wall; no AM rules | One TO, then **13 parameter variants**: rib width and height, turned-part and flange thickness | The X read by hand into parametric X-ribs | −21 % mass, +5 % torsional deformation; first mode 1,294-1,408 Hz; simulated | [WEVJ 16:552](https://www.mdpi.com/2032-6653/16/10/552) |
| **Barreiro et al. 2019**, SEW-EURODRIVE gear unit, SLM AlSi10Mg *abstract* | Not in the abstract | Frame: "an iterative design process"; an FE check "after each loop"; "safety and weight were compared with the previous version". Oil channels separately, by a morphological box | TO "only provides a design draft": redrawn each loop | Built, machined, assembled, short tests passed | [doi](https://doi.org/10.1007/s10010-019-00374-1) |
| **Ogata, Suzuki, Hiraoka 2005**, Honda transmission housing *abstract* | A "double-layered structural mesh" for a sealed housing (read as a closed skin kept, ribs grown from a design layer: *Inferred*) | TO, then ribs placed, then shape optimisation of the rib thickness (as summarised by Kim 2024); TO from the frame-concept stage saved the most | Ribs along "bearing load transmission routes" | Lighter at equal rigidity (no figure) | [SAE 2005-01-1699](https://saemobilus.sae.org/content/2005-01-1699/) |
| **Klarin et al. 2020**, AVL e-drive *abstract* | Concept TO for stiffness and "certain eigenfrequencies" | TO, then multibody over speed and load, operational modal and transfer-path analysis, then a new optimisation loop for noise | - | - | [SAE 2020-01-1578](https://saemobilus.sae.org/content/2020-01-1578) |
| **Kim et al. 2024**, agricultural UTV two-stage helical, Al halves *full* | OptiStruct SIMP (p 2); a bulk shape added to the housing, nodes shared; **3 domains**; volume ≤ 30 % of the design area; min-max sound pressure at the microphone, 0-700 Hz; drivetrain as a Nastran superelement on the ring-centre nodes | One TO; domain 3 had no effect | Threshold, then ribs drawn "to consider the manufacturability and assembly" | −2.43 dB(A); 4.836 → 4.847 kg | [Sci. Rep. 14:4145](https://www.nature.com/articles/s41598-024-54606-8) |
| **Son et al. 2020**, same gearbox *full* | OptiStruct; internals as a reduced substructure (Romax) linked rigidly to the seats, so the bearing forces change with the housing; least radiated power (ERP); both rotation directions | Analysis first: ERP, then the operating shape at the peaks, then the mode's strain energy → **weak areas = the design area** | Left unmanufacturable ("should be designed in detail") | ERP −9.7/−4.2 dB (CW), −2.7/−5.7 dB (CCW); 4.84 → 5.44 kg (+12 %) | [Appl. Sci. 10:8414](https://www.mdpi.com/2076-3417/10/23/8414) |
| **Son, Cho, Park 2019**, same *full* | Local stiffness at 65 points on a model updated to a modal test (2.84 %) | Weak part → rib location from strain → study 1 (width), study 2 (length × height at 4 mm) → stiffness gain per gram | One rib family by hand; length 20 mm, height 25 mm | +43.3 % local stiffness; −1.87 dB peak acceleration | [Appl. Sci. 9:4571](https://www.mdpi.com/2076-3417/9/21/4571) |
| **Amaral 2023**, PhD, Centrale Lyon; steel housing demonstrator *full* | COMSOL, MMA; least strain energy; −30 % mass aim; 12 cases of 1 kN at equal weights; seats and joint face outside the loop | Housing ↔ gearbox model loop to update the bearing loads each iteration (Fig. 2.9); adding seat-displacement and stress limits changed the layout; then a **modal sizing** of the top plate | Openings closed with a 2 mm least wall; walls 6 → 2 mm | 8.92 → 6.81 kg (−24 %); first mode 882 → 426 Hz; the sizing aimed it at 460 Hz (an illustration) | [HAL tel-04478512](https://theses.hal.science/tel-04478512v1) |
| **Triller et al. 2023**, Altair and BMW; mega-casting, not a housing *full* | TO + free-size, > 6 M variables, about 120 linearised cases; draw directions, least and largest member, least gap | Proposals by load-case weights; best picked by hand; ribs added by hand, with free-size re-run "after each of those adaptions" (the count is not given); then 2 response-surface cycles over about 20 sizes | Rib structure transferred to a shell model; ribs added by hand | 25 kg "less than the reference", a classical design that missed the pole-impact requirement | [Sci. Rep. 13:21678](https://pmc.ncbi.nlm.nih.gov/articles/PMC10709356/) |
| **Das 2011**, Honeywell aero accessory gearbox housing *full* | Bearing loads "parabolically distributed" over the pads; mount pads fixed by DOF | Ribs added and removed by hand until the pads' in-plane misalignment (SM) and rotation (SAR), from 8 opposite nodes, met their allowables; gussets iterated for mount strength | By judgement, judged at the seats | "Robust, lightweight" (no figure) | [GT2011-46747](https://torroja.dmt.upm.es/congresos/asme_2011/data/pdfs/trk-26/GT2011-46747.pdf) |
| **Inoue et al. 1992, 1995**, NASA test gearbox *abstract* | Shell FE; vibration energy at the exciting frequency; plate thickness; constant weight | Each surface's share found; plates done one at a time | Thickness, not ribs | Vibration energy 1/5 to 1/30 across beams, plates and the gearbox; "the top plate alone is effective" | [TM-105653](https://ntrs.nasa.gov/citations/19920019233), [TM-106878](https://ntrs.nasa.gov/citations/19960012197) |
| **Others** *abstract or snippet* | Farshi Ghodsi 2024 (KIT): local stiffness by area, then rib arrangements compared for NVH (CC BY-NC-ND). Slavov 2019: SOLIDWORKS thinning by strain energy, and a Taguchi study of the TO's own settings. Liu 2012: static and dynamic TO with stress, displacement, volume and first-mode limits | - | - | Liu: −5.9 % mass, less vibration | [KIT](https://publikationen.bibliothek.kit.edu/1000170585), [Machines 7:9](https://doi.org/10.3390/machines7010009), [MATEC 287:01020](https://doi.org/10.1051/matecconf/201928701020), [Liu](https://pure.bit.edu.cn/en/publications/static-dynamic-combined-topology-optimization-of-gearbox-housing-/) |

**Interpretation methods (none applied to a housing).**
- Amroune, Cuillière & François 2022: curve skeleton → cross-sections → B-spline lofts → solid CAD, then FE on both. Fully automatic, but "beam-like" shapes only.
- Mayer, Völkl & Wartzack 2022 and Mayer & Wartzack 2023: a surface skeleton → editable B-rep for non-beam shapes. A retopology step stays manual.
- A casting-aware variant thickens sections for directed solidification.
- rho2sdf (2025): SDF and RBF smoothing, volume-preserving; meshable, not semantic CAD.
- YOLOv8-TO (2024): learned component detection on 2D density images, +13.8 % Dice against skeletonisation.
- Explicit methods avoid the step: force-flow members, MMC, and variable-height stiffener TO with an anisotropic casting filter. Collected in fastcae's [CAD-light note](../../../fastcae/docs/inputs/research/CAD-Light%20and%20Manufacturing-Ready%20Topology%20Optimization%20%20Recent%20Papers%20and%20a%20Gearbox-Housing%20Research%20Path.md).

**Two modelling lessons from Ivanov.**
- A ring tied to its seat pulls the seat in tension: "bearing beds of the housing cannot be pulled by the bearings". That is the reason for D6a (bearing loads as a cosine over each seat's loaded half; [plan](../features/product/plan.md) §6.1).
- Tied halves give "too high eigenvalues"; bolts and preload matter for the modes.

## 3. What our first loop should do

Each step is marked **[tool]** (deterministic) or **[agent]** (judgement, written as a hypothesis with its reason). Numbers the contract or the process profile owns stay theirs.

**The engineer's FE practice replaces two suggestions in step 1** (9 October 02:12-02:15, recorded on the Physics page):
- the halves are joined at the bolts by **distributing** couplings, not kinematic ones;
- each bearing's loads enter through a distributing coupling over its **whole** seat, not a cosine over the loaded half.

Ivanov's lesson above, that a seat must not be pulled by its bearing, still stands. The first loop therefore runs the engineer's practice and measures the cosine of D6a beside it once, on the baseline.

1. **Baseline proof [tool].**
   - Build the plain shell-and-wall halves at the profile's least wall, with seats, bosses, joint flange and mounts.
   - Mesh TET10. Apply the calculated loads (peak drive and regen) as the cosine over each seat's loaded half (D6a). Mounts through distributing couplings; the halves joined at the bolts by kinematic couplings.
   - Solve statics and modes, and grade.
   - Record what binds, by how much, where the strain energy sits, and which mode sits near which order.

   One FE proof. Every later gain is measured against it at equal mass (Ivanov's lesson).
2. **Whole-domain TO: the bound and the map [tool; the agent sets the formulation].**
   - **The design space:** the envelope minus the swept gears with their clearance, minus the oil zones, minus the access to bolts and mounts. The shell stays frozen at least wall, so structure grows from a closed skin (Honda, Kim; otherwise Amaral had to close the holes afterwards). Seats with a collar, flange, bosses and mount pads are frozen.
   - **The objective:** the measure that binds, the seat-pair tilt per stage by adjoint (Ivanov's "most significant" run was the seat displacements). A compliance run is kept beside it.
   - **Budgets:** 2-3 mass budgets. Each is run relaxed (no casting rules) and constrained (least and largest member, least gap; a pull direction per half along the shafts).
   - **Printed moulds:** printed sand moulds have no pattern to withdraw, so the pull direction is optional there. Imposing it anyway keeps the design castable in conventional sand: the engineer's call (*Inferred*; the printed-mould rules still lack a public source).
   - **The grid:** a third of the least member (OptiStruct's rule), with one finer run to check mesh dependence.
   - The relaxed run at the largest budget is **the bound** (plan §3).
3. **Read the result [tool → agent].**
   - **[tool]** The interpretation tool gives the thresholded field, its surface skeleton on the shell, rib candidates with height and width profiles snapped to the seats, bosses, mounts and bolts, and each candidate's share of the sensitivity. Candidates that recur across the runs of step 2 are marked as robust.
   - **[agent]** The agent writes one or two hypotheses, for example "ribs from seat B to mounts 1-2 carry the regen tilt". It chooses the paths, the count, any pattern or symmetry, and the section bounds within the profile. It drops candidates that break a function and says why.
4. **Build and check [tool].**
   - Parametric ribs rooted on the shell, drafted for their half, with root fillets; trimmed, then fused.
   - The casting check on the CAD: sections, gaps for the sand, draft, undercuts. A broken rule is refused, with where and why.
5. **Prove and measure the reading [tool].**
   - Mesh, couple, solve and grade, with the 25 % model margin and the mass from the CAD.
   - Then compare the interpreted design with the raw TO result on the same voxel model. Comparing on one model is ranking, which a voxel model may do.
   - If the reading lost most of the TO's predicted gain, go back to step 3, not step 2 (Ivanov's split between a bad set-up and a bad reading).
6. **Size [tool; the agent picks the box].** A small study of the chosen family's section parameters: 6-9 proofs (Jäger & Linde's 13 variants; Son's two studies). Keep the lightest design that passes with margin.
7. **One local cycle if a measure still fails [agent picks, tool runs].**
   - **The sub-space:** where the failing measure's adjoint sensitivity per kilogram is highest, plus a band round the first result. For a mode, where its strain energy sits (Son 2020).
   - **The budget:** the mass the contract still allows.
   - Repeat steps 3-6 once.
8. **The stopping rule [tool computes; agent reports].** Stop when the first of these holds:
   - **pass:** every measure passes with margin, and the last cycle saved less mass than the measured mesh noise (a tie);
   - **bound:** the relaxed whole-domain TO misses the goal. Nothing inside this contract can meet it; say what would open it: more envelope, a looser limit, or another process;
   - **reading fails twice:** two readings in a row lose most of the raw TO's gain, or do worse than the baseline at equal mass. The hypothesis is set aside;
   - **budget spent:** about 12-15 FE proofs tonight (1 baseline, 1-2 readings, 6-9 sizing, 1-3 local). Report the best design and its gap.

   Expect one whole-domain round and one local cycle. Run a third only if the second gained beyond the noise.

**Judgement versus tools.**
- **The agent:** the formulation (objective, budgets, which rules relaxed), any design-space edit within authority, what each candidate means, the rib family and its regularisation, where the local cycle goes, and the reasons.
- **The tools:** geometry, loads, couplings, TO, skeletons and candidates, CAD build, rule checks, mesh, solve, measures, verdict, mass, the noise tie, the bound and the hypothesis status.

## 4. Tools this implies

| Tool | In | Out |
|---|---|---|
| Shell-and-wall | Contract layout (seats, bores, joint plane, mounts, envelope); process profile (least wall, draft, fillet) | Two-half B-rep with named faces (crosswalk ids); mass |
| Design space | Envelope, shell, keep-outs (swept gears and clearances, oil zones, bolt and tool access), frozen sets, draw per half, optional sub-space mask | Labelled grid (design, frozen, void); draw per cell; volumes |
| TO | Design grid; load cases with the D6a seat loads; supports and couplings; objective (tilt by adjoint, or compliance); budgets; rules on or off; resolution | Density per run; histories; the relaxed bound; sensitivity maps per measure |
| Interpretation | Densities, thresholds, shell, semantic nodes | Smoothed iso-surface; surface skeleton; rib candidates (path, height, width, ends, share, recurrence); a picture |
| Rib builder | Rib parameters (path, height, thickness, draft, root radius, pattern); shell B-rep | Fused B-rep (trim, then fuse); mass; casting check with refusals by face |
| Mesher and couplings | Named B-rep; load cases | TET10 within the FE budget; seat load sets, mount and bolt couplings; the deck; a volume check |
| Judge | Mesh and deck | cuDSS solve; balance and energy checks; seat tilts per stage, centre-distance change, ovalisation, modes against orders, stress recorded; verdict with margin; the noise tie |

## 5. Sources

1. Ivanov, D., *Gearbox Housing Design - Topology Optimization through Generative Design*, MSc thesis, KTH, TRITA-ITM-EX 2018:724 (for AVL Sweden). Read as https://www.scribd.com/document/514058589/Gearbox-Housing-Design (official copy on KTH's DiVA, unreachable from here).
2. Jäger, Linde 2025, WEVJ 16:552: https://www.mdpi.com/2032-6653/16/10/552
3. Barreiro, Bronner, Hoffmeister, Hermes 2019, Forsch. Ingenieurwes. 83:669-681: https://doi.org/10.1007/s10010-019-00374-1 (abstract: https://colab.ws/articles/10.1007%2Fs10010-019-00374-1)
4. Ogata, Suzuki, Hiraoka 2005, SAE 2005-01-1699: https://saemobilus.sae.org/content/2005-01-1699/
5. Klarin, Resch, Grozdanović, Pevec 2020, SAE 2020-01-1578: https://saemobilus.sae.org/content/2020-01-1578
6. Kim, Han, Chung, Park 2024, Sci. Rep. 14:4145: https://www.nature.com/articles/s41598-024-54606-8
7. Son, Kim, Cho, Park 2020, Appl. Sci. 10:8414: https://www.mdpi.com/2076-3417/10/23/8414
8. Son, Cho, Park 2019, Appl. Sci. 9:4571: https://www.mdpi.com/2076-3417/9/21/4571
9. Amaral 2023, PhD thesis, École Centrale de Lyon, NNT 2023ECDL0046: https://theses.hal.science/tel-04478512v1
10. Triller, Lopez, Nossek, Frenzel 2023, Sci. Rep. 13:21678: https://pmc.ncbi.nlm.nih.gov/articles/PMC10709356/
11. Das 2011, ASME GT2011-46747: https://torroja.dmt.upm.es/congresos/asme_2011/data/pdfs/trk-26/GT2011-46747.pdf
12. Inoue, Townsend, Coy 1992, NASA TM-105653: https://ntrs.nasa.gov/citations/19920019233
13. Inoue, Krantz 1995, NASA TM-106878: https://ntrs.nasa.gov/citations/19960012197
14. Farshi Ghodsi et al. 2024, KIT: https://publikationen.bibliothek.kit.edu/1000170585
15. Slavov, Konsulova-Bakalova 2019, Machines 7:9: https://doi.org/10.3390/machines7010009 and MATEC 287:01020: https://doi.org/10.1051/matecconf/201928701020
16. Liu, Xiang, Zhang 2012, Automotive Engineering: https://pure.bit.edu.cn/en/publications/static-dynamic-combined-topology-optimization-of-gearbox-housing-/
17. Altair OptiStruct, topology manufacturability (least member 3-12 elements; single and split draw): https://help.altair.com/hwsolvers/os/topics/solvers/os/mfg_topology_opt_intro_c.htm; topography: https://2025.help.altair.com/2025.1/hwsolvers/os/topics/solvers/os/topography_opt_intro_c.htm
18. Amroune, Cuillière, François 2022, CAD 145:103183: https://depot-e.uqtr.ca/id/eprint/10116/1/CUILLIERE_JC_31_POST.pdf
19. Mayer, Völkl, Wartzack 2022, DFX 2022: https://www.designsociety.org/publication/45927/Feature-Based+Reconstruction+of+Non-Beam-Like+Topology+Optimization+Design+Proposals+in+Boundary-Representation
20. Casting-aware reconstruction (Design Society proceedings): https://www.cambridge.org/core/journals/proceedings-of-the-design-society/article/reconstruction-of-topology-optimized-geometry-with-casting-constraints-in-a-featurebased-approach/24CABC0E601D57145D8FCF896B4FCB67
21. Smooth SDF extraction from SIMP (rho2sdf), 2025: https://arxiv.org/abs/2512.06976
22. Rochefort-Beaudoin et al. 2024, YOLOv8-TO: https://arxiv.org/abs/2404.18763
23. Variable-height stiffeners with casting constraints, SMO 2022: https://link.springer.com/article/10.1007/s00158-022-03428-1
24. Zimmermann 1993 (ZF), ERF paper M3 (bearings as gap elements, bolts as rods, a redesign read from the deformed shape): https://dspace-erf.nlr.nl/bitstreams/96f04c1f-40b7-465d-94d4-2bd18395134f/download
25. fastcae's own evidence: [geometry lessons](../../../fastcae/docs/research/2026-10-06-geometry-technology-lessons.md), [gearbox-housing engineering](../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md), [industry design pains](../../../fastcae/docs/research/2026-09-30-industry-design-pains.md); this repository's [plan](../features/product/plan.md) and [Ivanov contract plan](../features/contract/2026-10-08-plan-ivanov2018-contract.md)
