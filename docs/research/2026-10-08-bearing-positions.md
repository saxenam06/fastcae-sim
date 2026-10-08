# How the bearings' positions along the shafts are set

**Date.** 8 October 2026, 23:29. **Asked by** the engineer (23:23): is a bearing's position an input or calculated, what are "the gaps", and can the bearing life set the bearing width? **Read** in the main session from the sources of 7-8 October (copies in the session scratchpad, out of git), plus one targeted web search.

## The answer

- **Across the housing,** a bearing sits on its shaft's axis. Step 3 (where the shafts sit) places the axes from the working centre distances and the packaging offset. Calculated today.
- **Along the shaft,** no source derives the positions from the gear data by a formula. Every source lays them out as a **stack of known widths plus gaps**, under a few rules:
  - keep the spans short (moment arms, and deflection grows with span³);
  - each gear lines up with its mate on the next shaft;
  - leave room for shoulders and retaining rings, for the housing behind each bearing, and for a puller to reach the back of the bearing;
  - fix one bearing per shaft axially in the housing, and let the other float for thermal growth.
- **The bearing width is calculated:** the life (944 h), the seat loads and the shaft speed give the required dynamic rating C. The smallest catalogue bearing of the chosen type that carries C and fits the shaft gives the width, the outside diameter and, for a tapered or angular-contact bearing, its load-centre offset.
- **The loop:** the widths set the spacing, the spacing sets the loads, and the loads set the widths. Shigley starts from guessed widths and finds the selected bearings "close to the original estimates … no redesign should be necessary".
- **So the free inputs are the gaps, and the positions are calculated** (or, as in Ivanov's AVL case, the transmission designer gives the positions directly, and then the gaps are not inputs).

## Source by source

| Source | What it says about the positions | Confidence |
|---|---|---|
| Shigley, *Mechanical Engineering Design*, Ch. 18 (McGraw-Hill free chapter), §18-4 and Fig. 18-2 | "A free-body force analysis … can not be performed without knowing axial distances between gears and bearings. It is extremely important to keep axial distances small." Gear widths known; "bearing widths are guessed, allowing a little more space for larger bearings on the intermediate shaft"; "small allotments are given for the retaining rings, and for space behind the bearings". Fig. 18-2, the intermediate shaft, in inches: ¼ behind the bearing, 1 bearing, ¾ gap, 1½ gear, 4 between the gears, 2 gear, ¾ gap, 1 bearing, ¼ behind: 11.5 in. The 4 in is ½ gap, ¾ bearing, 1½ inner wall, ¾ bearing, ½ gap, which leaves room for the input and output shafts' bearings and the wall between them. "Only one bearing on each shaft is axially fixed in the housing" | High (read from the rendered figure) |
| Shigley Ch. 18, §18-9 (bearing selection) | Life 12,000 h at 99 % reliability, speed 389 rpm → L_D = 2.8·10⁸ rev → required C → a catalogue bearing (C, ID, OD, W). "The bearing widths are close to the original estimates. Slight adjustments should be made … No redesign should be necessary" | High |
| Maciejczyk & Zdziennicki, *Design Basic of Industrial Gear Boxes* (TU Łódź 2011), Ch. 3 | The worked reducer's bearing distances are taken from its sketch (Fig. 3.1): the pinion centred between the bearings, 90 + 90 mm for a 90 mm pinion, the pulley 110 mm outside. They are not derived | High |
| The same, Ch. 2 | Helical gears on one shaft are handed so that their thrusts oppose. On an overhung pinion, "the centre distance of the bearings should be at least three times" the overhang | High |
| The same, Ch. 9 and Fig. 9.1 (gear case) | To draw the case one needs the centre distance A, the bearing bores D (the bearings' outside diameters) and the pinion's face width. Wall δ = 0.025A + 1 ≥ 7.5 mm; the radial gap from gear tip to wall (1.1-1.2)δ; boss E = 1.2D. No axial-gap rule in the text | High (figure rendered) |
| Ivanov 2018 (KTH thesis for AVL, read from the Scribd copy) | The bearing slots (Fig. 27) are AVL's, from the existing gearbox. Their forces come from AVL's KISSsoft model (reverse, 2,000 rpm, 150 N·m) and EXCITE. The positions were the housing designer's inputs | Medium (garbled copy) |
| 1.5 kW gearbox student report (Scribd 499747356) | An assumed bearing arrangement (its Fig. 2.1), approximate bearing loads, then bearings selected by required rated capacity | Medium |
| fastcae research, 2026-10-06 gearbox-housing engineering, after JTEKT eq. 5-29 | A span runs between the bearings' effective load centres; a tapered or angular-contact bearing's centre is offset from its face by the catalogue's a | High |
| Kongsberg Maritime, problem proposal 2 for MiMM 2021 (Karlstad University) | Automatic placement of radial bearings on propeller shaft lines by rules: span over diameter 10-25; no component obstructed, each with its dismounting space; no-go zones. Another domain, the same kind of rule-based placement | High (read) |
| Targeted web search for a published axial-gap rule (for example a cube-root rule) | No primary source found; nothing used | - |

## What it means for the chain

- **Step 5 (spacing along each shaft)** stacks, per shaft: the space behind the bearing, the bearing width (step 7), the gap, the gear face widths, the gap between gears where a shaft carries two, the gap, the bearing, the space behind. The gears on adjacent shafts line up.
- **Its free inputs are the gaps.** Defaults could come from Shigley's case (¼ in behind a bearing, ½-¾ in between bearing and gear), stated as assumptions until the engineer sets them. A user who brings the positions themselves gives no gaps.
- **Step 7 needs each seat's shaft diameter** (the bearing's bore must fit it). That comes from a shaft-strength sizing (Shigley Ch. 7; Łódź Ch. 3-4), which the chain does not have yet.
- **Step 7 needs a bearing table:** dimensions (ISO 15, public) and dynamic ratings C from a maker's catalogue, cited.

## Sources

- Shigley Ch. 18: https://highered.mheducation.com/sites/dl/free/0073398209/1036702/Chapter18.pdf
- Maciejczyk & Zdziennicki 2011: https://cad-lab.github.io/cadlab_data/files/design_basic_gear_boxes.pdf
- Ivanov 2018 (Scribd copy): https://www.scribd.com/document/514058589
- Student report (Scribd): https://www.scribd.com/document/499747356
- Kongsberg Maritime / Karlstad University, MiMM 2021 problem 2: https://www.kau.se/files/2021-11/Problem_2_Kongsberg_0.pdf
- fastcae: `../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md`
