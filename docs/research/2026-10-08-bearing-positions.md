# How the bearings' positions along the shafts are set

**Date.** 8 October 2026, 23:29; corrected 23:48 after a review the engineer sent. **Asked by** the engineer (23:23): is a bearing's position an input or calculated, what are "the gaps", and can the bearing life set the bearing width? **Read** in the main session from the sources of 7-8 October (copies in the session scratchpad, out of git), plus one targeted web search.

## The answer

- **Across the housing,** a bearing sits on its shaft's axis. Step 3 (where the shafts sit) places the axes from the working centre distances and the packaging offset. Calculated today.
- **Along the shaft, two decisions are made.**
  - **The layout is chosen:** the order of the gears and bearings, their rough spacing, the bearing arrangement (how the shaft is held axially), and room for assembly. This is engineering design. No source derives it from the gear data, and no unique position follows from the ratio or the diameters.
  - **The coordinates are calculated** from the chosen layout: the components' real widths, the clearances, and a datum.
- **Static equilibrium does not place the bearings.** For positions already chosen, it gives the reactions. The layout is then judged against shaft strength and stiffness, bearing loads and life, gear alignment, packaging and assembly, and changed if needed. For one gear load F at a between supports at 0 and L: R_A = F(L−a)/L, R_B = Fa/L, and the moment at the gear is Fa(L−a)/L. Moving the gear towards a bearing loads that bearing more, the other less, and lowers that peak moment.
- **Two ways to state a chosen layout.** Both describe the same geometry; never give both for the same dimension.
  - **Gap-driven:** the gaps are given, and the coordinates follow from a datum and the widths.
  - **Coordinate-driven:** the positions are given, and the gaps follow.
  - An optimiser or agent can also take the coordinates as its variables and hold the gaps as minimum clearances.
- **A stack-up names its reference.** With centres measured from a datum and a face-to-face gap g, a gear after a bearing sits at x_G = x_B + B_B/2 + g + B_G/2, where B_B and B_G are the bearing's and the gear's widths.
- **The bearing arrangement is a separate choice from the placement.** One locating bearing and one floating is common. An adjusted pair of opposing angular-contact or tapered bearings is just as valid: Ivanov's intermediate shaft takes a tapered pair (A8). Do not hard-code either.
- **The life and the loads constrain the bearing's selection; they do not fix its width alone.** The other criteria are a bore that fits the shaft, radial and axial capacity, the arrangement, and the shaft's deflection. The chosen catalogue bearing then supplies its bore, width and outside diameter, and a tapered one its load-centre offset. "The smallest bearing that meets the life" means nothing until "smallest" and the other constraints are defined.
- **The loop:** the layout needs the bearings' widths; the loads need the layout; the shaft sections need the loads; the bearings need the loads and the shaft's diameter.
  - Shigley starts from guessed widths and finds the selected bearings "close to the original estimates … no redesign should be necessary".
  - Once the layout is chosen, the tool can calculate the coordinates and iterate, until the layout and the components agree.

## Source by source

| Source | What it says about the positions | How it was read |
|---|---|---|
| Shigley, *Mechanical Engineering Design*, Ch. 18 (McGraw-Hill free chapter), §18-4 and Fig. 18-2 | "A free-body force analysis … can not be performed without knowing axial distances between gears and bearings. It is extremely important to keep axial distances small." Gear widths are known, and "bearing widths are guessed, allowing a little more space for larger bearings on the intermediate shaft". "Small allotments are given for the retaining rings, and for space behind the bearings". In the case study "only one bearing on each shaft is axially fixed in the housing". Fig. 18-2, the intermediate shaft, in inches: | The rendered page, read in the main session |
| | ¼ behind the bearing, 1 bearing, ¾ gap, 1½ gear 3, 4 between the gears, 2 gear 4, ¾ gap, 1 bearing, ¼ behind; 11.5 in all | |
| | The 4 in is ½ gap, ¾ bearing, 1½ inner wall, ¾ bearing, ½ gap. That leaves room for the input and output shafts' bearings and the wall between them | |
| Shigley Ch. 18, §18-9 (bearing selection) | Life 12,000 h at 99 % reliability and 389 rpm give L_D = 2.8·10⁸ rev, and so the C required. A catalogue bearing then gives C, ID, OD and W. A ball bearing could not carry the load at a bore near 1 in, so the text takes a cylindrical roller: the selection weighs type and bore, not life alone. "The bearing widths are close to the original estimates … No redesign should be necessary" | The text |
| Maciejczyk & Zdziennicki, *Design Basic of Industrial Gear Boxes* (TU Łódź 2011), Ch. 3 | The worked reducer's bearing distances come from its sketch (Fig. 3.1). The moment equations use arms of 0.11, 0.09 and 0.18 m: the pulley 110 mm outside bearing B, the pinion 90 mm from B, a 180 mm span, so the pinion sits centred. They are not derived | The text's equations |
| The same, Ch. 2 | Helical gears on one shaft are handed so that their thrusts oppose. On an overhung pinion, "the centre distance of the bearings should be at least three times" the overhang | The text |
| The same, Ch. 9 and Fig. 9.1 (gear case) | To draw the case one needs the centre distance A, the bearing bores D (the bearings' outside diameters) and the pinion's face width. The wall is δ = 0.025A + 1 ≥ 7.5 mm; the radial gap from the gear tip to the wall is (1.1-1.2)δ; the boss is E = 1.2D. There is no axial-gap rule | The text and the rendered figure |
| Ivanov 2018 (KTH thesis for AVL; the Scribd copy) | The bearing slots (Fig. 27) are those of AVL's existing gearbox. Their forces come from AVL's KISSsoft model (reverse, 2,000 rpm, 150 N·m) and from EXCITE, so the housing designer received the positions as given | Medium: a garbled copy |
| 1.5 kW gearbox student report (Scribd 499747356) | An assumed bearing arrangement (its Fig. 2.1), approximate bearing loads, then bearings selected by required rated capacity | Medium |
| fastcae research, 2026-10-06 gearbox-housing engineering, after JTEKT eq. 5-29 | A span runs between the bearings' effective load centres. A tapered or angular-contact bearing's centre is offset from its face by the catalogue's a | fastcae's report |
| Kongsberg Maritime, problem proposal 2 for MiMM 2021 (Karlstad University) | Automatic placement of radial bearings on propeller shaft lines by rules: span over diameter between 10 and 25; no component obstructed, each with its dismounting space; no-go zones. Another domain, the same kind of rule-based placement | The text |
| A targeted web search for a published axial-gap rule (for example a cube-root rule) | No primary source was found, and nothing was used | - |
| A review the engineer sent (8 October, 23:39) | It corrected this note: the layout is chosen and the coordinates follow; two ways to state it; arrangement and placement are separate choices; life is one selection criterion among several; the shaft sections need stiffness as well as strength; a stack-up names its reference | Taken in above |

## What it means for the chain

The steps, as the calculation chain now numbers them:

- **Step 5, the layout along each shaft, is gap-driven** (the engineer, 9 Oct 00:06). Its inputs are the face widths, the bearing arrangement and the gaps; the bearing widths come from step 8, a first guess at first. It gives each gear's and bearing's centre from the datum. The Ivanov contract assumes Shigley's Fig. 18-2 gaps (A13-A15): 12.7 mm (½ in) between a bearing and its gear, 6.35 mm (¼ in) behind each bearing, and 12.7 mm between two gears on one shaft (no source).
- **Step 7, the shaft sections.** They are sized for strength in bending and torsion, and for stiffness: deflection and slope at the gears and bearings (Shigley Ch. 7; Łódź Ch. 3). Each bearing's bore must fit its shaft section.
- **Step 8, the bearing selection.** It takes the life with the loads, the bore, the radial and axial capacity, and the arrangement. It needs a bearing table: ISO 15 dimensions, public, and a maker's dynamic ratings C, cited.
- **Steps 5 to 8 go round** until the layout and the selected bearings agree.
- **A product idea.** An agent that formulates the bearing layout as a hypothesis of its own, beside the housing structure, could co-design the two. That changes the transmission's interfaces, so it belongs to a contract level above L1 (fixed interfaces). Not now.

## Sources

- Shigley Ch. 18: https://highered.mheducation.com/sites/dl/free/0073398209/1036702/Chapter18.pdf
- Maciejczyk & Zdziennicki 2011: https://cad-lab.github.io/cadlab_data/files/design_basic_gear_boxes.pdf
- Ivanov 2018 (Scribd copy): https://www.scribd.com/document/514058589
- Student report (Scribd): https://www.scribd.com/document/499747356
- Kongsberg Maritime / Karlstad University, MiMM 2021 problem 2: https://www.kau.se/files/2021-11/Problem_2_Kongsberg_0.pdf
- fastcae: `../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md`
