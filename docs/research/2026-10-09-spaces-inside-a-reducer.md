# What else the housing must hold: the spaces inside a reducer

**Date.** 9 October 2026, 02:38. **Asked by** the engineer: besides the gears, shafts and bearings, everything else inside or on the housing needs its space, or the housing will look unrealistic to a gearbox engineer. Do the layout's allowances (`requirement.shaft_layout`, A13-A19) roughly cover it, and what is missing?

**How it was read.** A research subagent read local copies of the sources of 7-8 October (Shigley Ch. 18, Łódź, Ivanov, Hofstetter), fastcae's housing report, and the pages found by a targeted web search. The copies stay out of git, in the session scratchpad. The values were not re-read in the main session, so check each one against its source before citing it anywhere public. Each value is marked high, medium or low confidence.

## 1. Verdict

**Along each shaft, roughly yes. Across the rest of the housing, no.**

What the allowances cover:
- A13 has room for a shoulder, a DIN 471 ring and a puller.
- A14 has room for the wall or cover behind the bearing, and for the tapered pair's shim.
- A16 holds an ISO 6194 seal up to 10 mm wide in its 10.3 mm seat.
- A19 is Łódź's own rule.

Where they fall short:
- A15 and A18 still have no source.
- A14 is too short wherever a lock nut holds a bearing.

**What is missing is everything that is not a gear, a shaft or a bearing.**
- **The differential, the biggest item.** The output gear is carried on a differential case, and the case's type sets the space it takes.
  - A spur-gear differential can stay within the final drive's width: Schaeffler's volume-production targets put its bearings 26-33 mm apart.
  - A conventional bevel unit of the 2,100 N·m class has its bearings 96 mm apart and a case body about 100 mm across.
  - Our stack spaces the output bearings 64-68 mm apart. It silently assumes the compact case.
- **The oil.** Nothing sets the oil level, a sump, the drain, the fill, the breather or the oil catchers, although stage 1 runs above splash speed at cruise.
- **The split flange:** its sealing land, bolts, bosses and dowels. A3's envelope (the gears plus 20 mm) cannot even hold the flange: the tip clearance (8.25 mm), the wall (δ = 7.5 mm) and an M8 flange (24 mm) reach 39.75 mm beyond the tips.
- **The park lock** on the intermediate shaft.
- **The outside:** the motor flange, the vehicle mounts, a sensor port, and tool access to every bore.

Without these, a housing drawn from today's contract is a tight shell round three bare shafts, with no differential bulge, no flange, no sump and no bosses. That is what makes it look unrealistic.

## 2. Item by item

| Item | What it needs | Covered by | Source |
|---|---|---|---|
| Shoulder, retaining ring, puller room | A DIN 471 ring for a 40 mm shaft is 1.75 mm thick (high). The ring's catalogue gives an edge margin from the groove (§18-10) | A13 (12.7 mm), with room to spare | [1] §18-10 and Fig. 18-2; [2] |
| Shim or spacer for the tapered pair | Setting by a measured shim or spacer, or by an adjusting nut (high); the shim pack's thickness is a few mm (low) | A14 (6.35 mm) behind the cup | [3]; [4] §1.4 |
| Lock nut, if one holds a bearing | KM 6 (M30×1.5): 7 mm wide, Ø45 mm. KM 8 (M40×1.5): 9 mm wide, Ø58 mm. Plus a lock washer (medium) | **Not covered** behind a bearing: A14 is 6.35 mm | [5] |
| Radial shaft seals | ISO 6194 widths are 7, 8 or 10 mm for 25-50 mm shafts. The housing bore is b + 0.3 mm deep, H8, Ra 1.6-6.3 µm (high) | A16 (11 mm), for seals up to 10 mm; A17 names the sealed ends | [6] Ch. 6 |
| Bearing cap | In Ivanov's housing, a bolted cap holds one output bearing and takes the gear's axial force (medium). Łódź sizes caps by the bore D: bolts d4 = 0.08·D, Table 9.2 (medium) | **Not covered.** A14 is a wall, not a cap with its bolt circle | [7]; [6] Ch. 9 |
| **Differential** (case, side gears and pinions; the output gear on the case; bearings on its hubs) | Hofstetter: the output shaft's contour includes the differential, "selected off-the-shelf depending on the required transmittable torque" (high).<br>Schaeffler, Figs. 13-14, bevel units:<br>- 2,100 N·m axle torque: final drive 171.5 mm, bearing spacing B 96 mm, 5.5 kg with the final drive;<br>- 5,500 N·m: 195.1 mm, 128 mm, 8.95 kg (high).<br>Schaeffler's spur differential, volume-production targets: B 26.3-32.6 mm; its type 2 stays within the final drive's width (high).<br>Eaton, compact EV bevel unit: hub span 46 % smaller and diameter 6 % smaller than a standard one (medium).<br>Read off Fig. 14: the case body is about 0.6·D_f (about 103 mm), and the final drive sits beside one bearing (low).<br>Ours carries about 1,080 N·m (150 × 7.184) | **Not covered.** The stack spaces the output bearings 64-68 mm apart (16-20 mm balls) and gives the case no diameter | [8]; [9]; [10]; [7] |
| **Park lock** | The park gear sits on the intermediate shaft (Ivanov; medium). Chalmers names the parts: a pawl, a cone or roller actuator with its rod and springs, a return spring, and a park gear "on either one of the shafts in an EV transmission".<br>An electric actuator goes outside, for example 133 × 124 × 64 mm and 1.63 kg (Nidec; high).<br>On the intermediate shaft, anything over Ø51.9 mm overlaps the output gear end-on, so A18 applies.<br>Holding the vehicle on a 10-30 % grade puts about 199-582 N·m on that shaft (2,200 kg vehicle assumed; low) | **Not covered** | [7]; [11]; [12]; [4] §1.8 |
| **Oil level** | The lowest gear, usually the output gear, dips 1h-3h. That is 4.6-13.8 mm here (KHK Table 13.2; high).<br>FZG compared lower levels with oil up to the centreline:<br>- a 3·m dip cut the pitting endurance limit by 8 %;<br>- a 1·m dip cut it by 23 %;<br>- the no-load losses fell (high) | **Not covered** | [13]; [14] |
| **Sump below the lowest gear** | Łódź Fig. 9.1: H = A, from the wheel's axis to the case's inner floor. For stage 2 that leaves about 26 mm under the output gear's tips (low to medium: a one-stage industrial rule). A19's 8.25 mm at the floor would leave about a third of that | **Not covered** | [6] Fig. 9.1 |
| **Oil catchers, channels, pump** | KHK puts splash lubrication at about 3-15 m/s. Stage 1 here runs 16.8 m/s at cruise and 24.3 m/s at 8,673 rpm. So the input mesh and bearings need catch pockets and channels, or a pump (medium).<br>Ivanov kept design-space blocks for "oil ports, pump and frame mounts". SAE 2026-26-0064 uses baffles, return channels and an accumulation cavity to keep the breather dry (abstract only) | **Not covered** | [13]; [7]; [15] |
| Breather, drain, fill | The breather sits above the oil level (Gore) and is shielded from the splash [15]. The drain sits at the lowest point and the fill at the highest accessible point (Ivanov; Łódź's Fig. 9.1 draws the drain plug at the floor) (medium). A magnetic drain plug is usual; no source read gives one | **Not covered** | [16]; [7]; [6] |
| **Split flange** | Łódź Table 9.1 gives the flange width K and the bolt axis C from the wall: M8 24 / 13 mm, M10 28 / 15 mm. At the split, two flanges of 1.5·δ each, 11.25 mm at δ = 7.5 mm (medium).<br>Henkel, anaerobic FIPG (high):<br>- machined faces, Ra 0.8-3.2 µm, flatness 0.1 mm over 400 mm;<br>- at least 5 mm of sealing overlap, and 3 mm round each bolt;<br>- gaps 0.1-0.25 mm; at least 2.5 MPa contact pressure.<br>Bolt pitch by Rötscher's cones: about dK + 2h, and between dK + h and dK + 2h for highly stressed joints (medium). ThreeBond: liquid gaskets in EV transmission cases | **Not covered.** A3 is an envelope, not a flange, and too small for one | [6]; [17]; [18] |
| Dowels | Henkel: two alignment dowels per joint, so the sealant is not smeared and the halves sit in place (high). SPIROL: hollow dowels of 6-16 mm OD align within 20 µm; a 16 mm one locates a transmission to its engine (medium) | **Not covered** | [17]; [19] |
| Bolt bosses and threads | Thread engagement in aluminium is 1.6·d, plus 20 % under dynamic load: about 13-15 mm for M8 (Henkel; medium). The spotface per bolt size is in Łódź Table 9.1 | **Not covered** | [17]; [6] |
| Motor interface | A flange joins the motor to the housing; Ivanov 2018 assumes the whole counter-torque passes through it. The rotor drives the input through a spline, usually greased; its clearance and misalignment amplify rattle (SAE 2023-01-7019, abstract). The spigot's diameter and depth and the bolt circle are the motor's data (low) | Only the seal (A16). The flange is **not covered** | [7]; [20] |
| Vehicle mounts | Frame-mount bosses are the FE's fixed points (Ivanov). A separate gearbox reacts about (i − 1)·T_in = 928 N·m (fastcae; inferred) | **Not covered** | [7]; [4] §1.9 |
| Speed sensor, if fitted | A Hall sensor: Ø11.8 mm bore, 30 mm deep, one M6 screw, 0.4-1.0 mm air gap to a toothed target (Bosch HA-D 90; medium) | **Not covered** | [21] |
| Machining and assembly access | MAPAL: a bearing in a separate part is positioned by position bores or fitting surfaces, and one clamping helps coaxiality (high, for motor housings). SEW, for a split along the axes: the raw castings are pinned and screwed together before the bores are machined (high, for that case).<br>For our split, square to the shafts, each shaft's two bores lie in different halves, so the dowels become the datum (inferred). Every bore needs a tool's approach. Shafts whose parts overlap end-on (the stage-1 and output gears) go in together (inferred) | **Not covered** | [22]; [23] |

## 3. Recommended additions to the contract

Most important first. Each is labelled an assumption until the engineer confirms it.

1. **`differential`: the output shaft's carrier, stated by type and dimensions.**
   - *What it holds:* its type (bevel, compact bevel or spur), its case diameter, its bearing spacing, its hub diameters (for the bearings and seals) and the final drive's offset along it. In Hofstetter et al. 2018 the differential is selected off the shelf by torque [9].
   - *Default until a unit is chosen:* Schaeffler's 2,100 N·m bevel unit [8]. Bearing spacing 96 mm (high, for that unit); case Ø ≈ 105 mm (low).
   - *In the chain:* step 5 builds the output shaft from the differential, not from A13.
   - *In the clearance check:* step 3 takes the case's contour too. A Ø103 mm case clears the stage-1 gear's tip circle by 16 mm radially; above Ø135 mm it overlaps that gear end-on.
2. **`oil`: the level and the sump.**
   - `oil_level`: the lowest gear's dip, 1h-3h [13]. The engineer chooses within it; [14] shows what the low end costs in pitting life.
   - `sump_depth`: the floor below the lowest gear's tips, about 26 mm by Łódź's H = A [6] (low to medium). It replaces A19 at the floor.
   - The oil volume then follows by calculation and is never typed.
3. **`split_flange`.**
   - *Inputs:* the bolt size (M8 assumed; low) and the sealant type.
   - *From the bolt size:* flange width and bolt axis per Łódź Table 9.1 (24 / 13 mm for M8), and 1.5·δ thick per half [6].
   - *Sealing land:* at least 5 mm, and 3 mm round each bolt [17].
   - *Derived:* the pitch, by Rötscher's cones [17].
   - *Dowels:* two, as far apart as the flange allows [17], [19].
   - *Knock-on:* A3 must grow to hold the flange, or the flange's lobes must be allowed outside it.
4. **`park_lock`.**
   - *Its shaft:* the intermediate one [7].
   - *The park gear's diameter and width:* no public size was found, so this is the engineer's or a supplier's value.
   - *On the housing:* a boss for the pawl's pivot, and a pad outside for the actuator (envelope 133 × 124 × 64 mm [12]).
   - *Load:* a holding case [4] §1.8.
   - *In step 5:* one more part on the intermediate shaft, with A18 against the output gear. If it sits between that shaft's two gears, A15 grows by its width.
5. **`motor_flange` and `mounts`: the outside interfaces.** The motor gives its spigot's diameter and depth, its bolt circle and its bolt count. The vehicle gives the mounts' positions, bolt sizes and pad sizes. These are inputs, not calculations. Their bosses are sized from the bolt: Łódź Table 9.1 [6], and 1.6·d of thread in aluminium [17].
6. **`oil_ports`: keep-outs in the exact core** that the structure may not fill [4] §1.7.
   - the drain at the lowest point;
   - the fill at the oil level;
   - the breather on top, behind a catcher [15], [16];
   - catch pockets and channels to the input bearings, since stage 1 runs above splash speed at cruise [13].
7. **A tool-access check on every machined bore and face,** with the dowels as the datum for both halves [22], [23]. A bore no tool can reach is refused, like a clearance breach.
8. **Smaller corrections.**
   - A14 grows to the nut's width wherever a nut holds a bearing: KM 6 7 mm, KM 8 9 mm, plus the washer [5].
   - A17's sealed input end assumes a dry motor interface, with a greased spline and a seal. A wet interface, sharing the gear oil, needs no seal there (inferred from [20]).
   - A speed sensor, if fitted, needs a Ø11.8 mm bore and an M6 boss, within 0.4-1.0 mm of a toothed wheel [21].

## 4. Sources

1. Shigley, *Mechanical Engineering Design*, 10th ed., Ch. 18 (McGraw-Hill free chapter): https://highered.mheducation.com/sites/dl/free/0073398209/1036702/Chapter18.pdf
2. Lemu, DIN 471 retaining ring A 40: https://www.lemu.dk/en/product/a-40-plain-retaining-ring-din-471-id-2471040000
3. Springer and Corneliussen (Timken), "Setting techniques for tapered roller bearings", *Machine Design*, 2000: https://www.machinedesign.com/motors-drives/article/21831685/setting-techniques-for-tapered-roller-bearings
4. fastcae research, "Gearbox-housing engineering", 6-7 October 2026, §1.4 and §1.7-1.9: [../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md](../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md)
5. SKF KM lock nuts, as listed by a reseller: https://www.qualitybearingsonline.ca/km8-skf-lock-nut-50x58x9mm/ and https://qualitybearingsonline.ca/km6-skf-lock-nut-38x45x7mm
6. Maciejczyk and Zdziennicki, *Design Basic of Industrial Gear Boxes*, TU Łódź, 2011, Ch. 6 and Ch. 9: https://cad-lab.github.io/cadlab_data/files/design_basic_gear_boxes.pdf
7. Ivanov, *Gearbox Housing Design*, KTH MSc thesis for AVL, 2018 (Scribd copy, partly garbled; medium): https://www.scribd.com/document/514058589
8. Schaeffler Symposium 2010, the lightweight differential (Figs. 13-14): https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/symposia_1/downloads_11/Schaeffler_Kolloquium_2010_06_en.pdf
9. Hofstetter et al., *Forschung im Ingenieurwesen*, 2018 (read from a local copy): https://link.springer.com/article/10.1007/s10010-018-0278-9
10. Eaton, EV differentials (percentages only): https://www.eaton.com.cn/cn/en-us/catalog/differentials/eaton-open-differential.html
11. Swami Narayan, *Park Lock Development: Parametrising the Park Lock Mechanism*, Chalmers MSc thesis with AVL Vicura, 2020 (open access): https://odr.chalmers.se/handle/20.500.12380/300916
12. Nidec Powertrain Systems, park lock actuator D1L2C1: https://www.nidec.com/en/nidec-powertrainsystems/product/search/category/B105/M100/S121/NPSC-GY_actr
13. KHK, Gear Technical Reference, "Lubrication of gears" (Tables 13.1 and 13.2): https://khkgears.net/new/gear_knowledge/gear_technical_reference/lubrication-of-gears.html
14. Höhn, Michaelis and Otto (FZG), "Flank Load Carrying Capacity and Power Loss Reduction by Minimized Lubrication", *Gear Technology*, May 2011: https://ik.imagekit.io/agmamedia/gt/issues/0511x/hoehn.pdf
15. Ekshinge et al., "Oil Channelization for EV Transmission", SAE 2026-26-0064 (paywalled; abstract only): https://saemobilus.sae.org/papers/oil-channelization-ev-transmission-2026-26-0064
16. Gore, protective vents for gearboxes: https://gore.com/products/venting/protective-vents-for-gearboxes
17. Henkel (Loctite), *Liquid Gasketing Design Guide*: https://dm.henkel-dam.com/is/content/henkel/Gasketing%20Design%20Guide-Final_LR
18. ThreeBond, Technical News 107, July 2026 (via [4]): https://www.threebond.co.jp/en/technical/technicalnews/docs/TechnicalNews107_EN.pdf
19. SPIROL, ground hollow dowels GD100: https://www.spirol.com/assets/files/bush-ground-hollow-dowels-gd100-us.pdf
20. Wang, Zhang and Yang, "Analysis and Control of Gear Rattle Noise for E-Axle", SAE 2023-01-7019 (paywalled; abstract only): https://saemobilus.sae.org/papers/analysis-control-gear-rattle-noise-e-axle-2023-01-7019
21. Bosch Motorsport, Hall-effect speed sensor HA-D 90, datasheet: https://www.bosch-motorsport.com/content/downloads/Raceparts/Resources/pdf/Data%20Sheet_69813003_Speed_Sensor_Hall-Effect_HA-D_90.pdf
22. MAPAL, "Bearing and position bores": https://mapal.com/en-int/sectors-solutions/automotive/toolsolutions-electrified-mobility/electrified-drives/bearing-and-position-bores
23. SEW-Eurodrive, US 11,767,906 B2, "Transmission and method for producing a transmission having a housing": https://patents.google.com/patent/US11767906B2/en

**Not found in a public source:** the park gear's size, a sump depth made for EV units, the spigot sizes of an EV motor flange, and a magnetic drain plug's size.
