# Production housings against ours: what we miss, and what to do

**Date.** 9 October 2026, 12:48-14:00. **Asked by** the engineer, on seeing the best design of the second round (`box1_fl`, 9.92 kg): "Is this housing manufacturable? Can this be productionized? I have never seen the housing like this. Compare this picture with the housing pictures which I have sent to you and identify what conditions, what criteria we are missing because of which we are creating housings like this, as compared to the housings which engineers create, and how do they nicely create these shapes, what is the trade, what is the art of creating those housings. Study them and then decide what should we do."

**What was read.**
- **36 pictures from the engineer:**
  - Ivanov 2018's figures (Figs 20, 21, 36, 38, 65-71, and two CAD views of the AVL housing);
  - Son 2019, Son 2020 and Kim 2024's figures (the agricultural EV gearbox);
  - product pictures of production units. EV reducers and e-drives: Avtec's 150 N·m single-speed gearbox, Kalyani Technoforge's single-speed gearbox, Punch Powertrain's ET250, Rawsuns' AMTs and EV unit, Magna's eDrive, Batom's EDM1 three-in-one, and one unnamed unit. Rail axle drives: five ZF units and an EMU gearbox (MDPI).

  The pictures were read by me; what is said about a picture is my reading. They stay out of git (third-party images).
- **Our designs, measured on their CAD** by a new check, `prototypes/first_loop/castable.py` (section 3).
- **The rules:** from the research library and two research subagents (section 5), marked where they came from.

## 1. In short

1. **No: `box1_fl` cannot be made as its own contract says, and it is not a design to productionise.** Measured on its CAD:
   - it breaks the contract's hard rule, the pull directions: 25 % of the motor side's surface and 17 % of the cover's are undercut, and the motor side holds 22 closed voids (331 cm³), the cells of its cored double wall;
   - it breaks the 4 mm least wall in about 100 cm² of wedges, where the lattices run into the curved walls;
   - it has no fillet anywhere and sections up to 24 mm beside 4-6 mm walls;
   - it is 28 % heavier than the reference housing (9.92 against 7.73 kg).

   It is a study of where stiffness comes from, not a housing. **None of the 43 designs judged since the night passes either rule.** Even our plainest shell fails the pull rule, where the motor's flange plate overhangs the split flange.
2. **Why ours look like this:**
   - **We graded physics only,** so the search produced physics only. The contract already holds two casting rules (the pull directions and the least wall), and we never measured them on the CAD.
   - **Our generator speaks a stiffness vocabulary,** pods, plates and boxes, not the trade's grammar.
   - **Nothing asked for function or for a production look:** oil, sealing, assembly.
   - **When a line would not pass, the only lever we pulled was the housing's mass.**
3. **The trade designs in a grammar, the same in all 36 pictures** (section 2.5):
   - one silhouette round the gears, and one thin shell;
   - flanges with bolt bosses at an even pitch, and bosses standing proud;
   - ribs drawn between hard points: spokes on round faces, trusses between bosses, grids on flat panels. Every rib ends on something;
   - gussets at every overhang, and fillets everywhere;
   - everything drawn out of the mould along the split.

   The optimiser only corrects a housing already drawn this way (Ivanov's "noribs" runs, Son's gussets).
4. **The decision** (section 7):
   - stop adding stiffness forms to the lobed pods;
   - put the contract's casting rules into the grade (the check exists since 13:00);
   - build a new generator in the trade's grammar, castable by construction;
   - grade its baseline, a housing of the AVL family for our gear train, before deciding A8 (the intermediate's bearings);
   - then run the loop on it.
5. **Settled** (section 8): the engineer's reference shapes are the requirement, so the generator follows production casting's rules. These are stricter than the contract's floor, so the contract does not change. A8 waits for the baseline's number.

## 2. What the pictures show

### 2.1 Ivanov 2018 (KTH, for AVL): the housing our contract's gear train comes from

- **Three parts** (Fig. 20): the motor side, the back side (the cover), and a separate flange plate for the motor.
  - The plate being a part of its own matters for casting. A ring wider than the housing, standing on the motor side's end face, would be an undercut along that half's pull. That is exactly where our plainest shell fails (section 3).
- **The outline** is one smooth closed curve round the three shafts.
  - About twenty bolt bosses sit on it at a near-even pitch.
  - Each boss is a cylinder standing out of the flange, gusseted down the side wall (Fig. 20, the side view; the CAD views).
- **The end faces** are thin walls with bosses standing proud of them:
  - the output bore's boss carries a square, four-bolt bearing cap, which takes the output gear's thrust;
  - the intermediate bore has its own boss;
  - the motor face is a ring with its bolt circle.
- **The ribs** (Figs 20, 21, 71):
  - radially from the output boss to the flange's bolt bosses;
  - a frame round the intermediate boss;
  - diagonals from the top mount ears to the output boss;
  - spokes under the motor face.

  Every rib ends on a boss, an ear, a rim or another rib.
- **The functions show** (Fig. 21):
  - three frame mounts on top, bosses with gussets;
  - the oil inlet and outlet and a pump outlet, each a boss bridged into the wall.
- **The optimisation:**
  - First a solid block: the outline extruded, 279k TET10 (Fig. 38), which the author calls "FEM brainstorming".
  - Then the housing stripped of its ribs ("noribs"), with design-space blocks in the voids between its features. It was run with a demould (pull) control (Fig. 66), and with the bearing centres' displacement as the objective (Fig. 67).
  - The results are patches between the bosses (Figs 65-67).
- **The reading:**
  - what recurs across the runs: "a rib between the fixing ear and bearing hold is suggested in every simulation" (Fig. 68);
  - drawn as straight ribs between features (Fig. 69);
  - exported beside the CAD (Fig. 70);
  - merged by hand (Fig. 71): "most of the design suggestions were respected, except the ones that disturb the functionality of the gearbox features".

### 2.2 The agricultural EV gearbox (Son 2019, Son 2020, Kim 2024)

- **Two castings, 4.84 kg** (Son 2020 Fig. 11):
  - an upper case with a round dish face and a long cylindrical bearing boss;
  - a lower case with an oval pocket and a ribbed bore;
  - ears along the split.
- **The weak place is found by measure first,** then the structure goes there:
  - 65 points of local stiffness (Son 2019 Fig. 8);
  - the first mode's strain at the boss's root (Fig. 10);
  - then eight radial gussets round that root, sized as W × L × H (Fig. 12);
  - the design areas are drawn only on the weak panels (Son 2020 Fig. 16; Kim Fig. 12).
- **What is added is small** (19 g to 0.6 kg), and always from the vocabulary: gussets at a boss's root, ribs across a panel, ribs from a boss to the rim.

### 2.3 Production EV reducers and e-drives

| Unit | What it shows |
|---|---|
| Avtec, 150 N·m single-speed (our torque class) | A compact casting whose walls carry a rectangular grid of ribs; bolts at a close pitch along the split; plugs; an output flange |
| Kalyani Technoforge, single-speed | The motor flange a scalloped ring of twelve bolt lobes; on the gear side, a fan of curved ribs from the large bearing boss to an outer ring; bolt bosses gusseted into the wall |
| Punch Powertrain ET250 | Smooth die-cast shells hugging the gears; curved ribs sweeping across the end face; triangulated ribs at the corners; mount bosses with gussets |
| Rawsuns (two AMTs and an EV unit) | Bell housings with dense radial ribs (wheels of 16-20 spokes); an end face triangulated between the bearing bosses and the bolt bosses |
| Magna eDrive (Jiangxi) | A grid of ribs on the walls; the park-lock actuator on the housing; bearing bosses standing proud |
| Batom EDM1 (three-in-one) | The motor face a wheel: about eight straight spokes from the hub to the rim, and an inner ring |
| Unnamed EV unit | A motor bell with about 16-20 radial spokes to its flange; ribs on the gear housing |

### 2.4 Rail axle drives (ZF; an EMU gearbox)

Large sand castings:
- diagonal ribs crossing in X's over the big gear's side wall;
- ribs round the cylindrical body;
- round bolted covers with radial ribs;
- flanges with many close bolts;
- torque arms on rubber mounts.

The same grammar at a larger scale, with crossing ribs that only a sand mould with cores, or a part drawn across them, can make.

### 2.5 The grammar they share

Every housing in the 36 pictures follows the same rules. They are the trade's art: each gives stiffness and castability, and the look comes from them.

1. **One silhouette.** The split's outline is one closed, smooth curve: arcs round the gears (tip radius + clearance + wall) joined by tangents. The gears can be read from the outside.
2. **One thin skin.** The walls have one thickness and follow the gears at a constant gap. Changes of depth (the differential's drum, the motor's bell) are smooth, drafted steps. Curvature, not thickness, makes the skin stiff: a curved shell carries its load as membrane force.
3. **Hard points first:**
   - bearing bosses stand proud of the end walls;
   - bolt bosses sit on the flange at an even pitch, which makes the scalloped rim;
   - mount ears and ports are bosses too;
   - caps and covers bolt onto round bosses where a thrust goes.
4. **Ribs between hard points:**
   - from each bearing boss straight to the nearest bolt bosses (spokes);
   - between bearing bosses along the line of centres, where the mesh forces act;
   - from each mount ear to the nearest bearing boss.

   The result is a truss drawn on the wall, in triangles, never open quadrilaterals.
5. **Round faces get wheels, flat panels get grids:**
   - spokes from the hub to the rim on a motor face or a cover, straight (Batom) or curved as a fan (Kalyani, Punch);
   - a grid or crossed ribs on a large flat panel with no hard point inside (Avtec, Magna, ZF), to keep its modes up and its radiated noise down.
6. **Every rib ends on something:** a boss, a rim, another rib. The ribs of one family have one depth and one thickness, are drafted, rounded on top and filleted at the root.
7. **Gussets at every overhang:** under each bolt boss and mount ear, and round the root of each tall boss.
8. **The mass is in the ribs and the bosses,** not in the walls. A rib's bending stiffness grows with the cube of its depth.
9. **It comes out of the mould.** What stands on an end face is drawn along the pull, and the ribs on the side walls run along the pull. What cannot be drawn is cored, or made a separate part, like AVL's motor flange plate.
10. **The functions show:** ports and plugs are bosses bridged into the wall; every joint is a flange with bolts; nothing is hidden in a box.
11. **Regularity and economy:** few kinds of element, repeated at an even pitch and angle; symmetry about a shaft where its loads are symmetric; smooth transitions and fillets.

## 3. Ours, measured: can it be cast?

**The check** (`prototypes/first_loop/castable.py`) works on each half's built CAD, with no FE. It takes the rules the contract holds:
- **The pull direction** (hard, engineer-locked, 02:12): each half is drawn along the shafts.
  - A face turned along the pull, or against it, must see free space that way: a ray from the face finds no metal. Otherwise it is an undercut.
  - A face parallel to the pull is formed by either mould part. The contract's draft is 0° (A11).
  - A closed void, a second shell inside the solid, is an undercut by definition.
- **The least wall,** 4 mm (D7): a ray along each face's inward normal.
- **Reported, not judged** (the contract has no rule for it yet): the largest section, the diameter of the largest ball in the metal, from a 1 mm distance map.

The mesh's and the voxels' volumes agree within 0.2-1 %.

| | `box1_fl`, motor side | `box1_fl`, cover | `lobed_e10s`, motor side | `lobed_e10s`, cover |
|---|---|---|---|---|
| Surface undercut along the pull | **25.1 %** (1,490 cm²: walls 1,334, ribs 157) | **17.1 %** (916 cm²) | **7.2 %** (262 cm²) | 0.4 % (12 cm²) |
| Closed voids | **22, 331 cm³** | 0 | 0 | 0 |
| Faces over less than 4 mm of metal | 24 cm² | 76 cm² | 3.7 cm² | 0.3 cm² |
| Largest section | 24 mm | 23 mm | 25 mm | 23 mm |
| Pull rule / least wall | FAIL / FAIL | FAIL / FAIL | FAIL / FAIL | FAIL / FAIL |

Where, from the pictures `data/first_loop/castable_box1_fl.png` and `castable_lobed_e10s.png`:
- **`box1_fl`:**
  - the undercuts are the cells of the lattices under their 4 mm skins: the cored double end walls;
  - the motor side's cells are closed all round (the 22 voids). The cover's are open at their edges but covered from the pull;
  - the thin wedges are where straight lattice ribs run into the pods' curved walls at a shallow angle.
- **`lobed_e10s`:**
  - the motor side's undercut is the underside of the split flange, overhung by the motor's flange plate below it. That is the reason AVL made the plate a third part;
  - the thin places are 1 mm membranes left under the six motor bolt holes, and a 2.4 mm ligament between two bores.

These are CAD details, curable locally. The box design's failures are its structure.

**Every judged design (43, from the night's to this morning's):** none passes the pull rule, and none passes the least wall.
- **Two details fail them all.** Every design inherits them from the generator:
  - the motor's flange plate overhanging the split flange (4-8 % of the motor side);
  - thin membranes at the motor bolt holes and between bores (4-18 cm²).

  Both are curable in the CAD.
- **The ribbed and boxed designs fail through their structure:**
  - the boxes: 17-30 % undercut and 22-26 closed voids of about 330 cm³;
  - the inward-thickened walls and inner lattices: wedges of 60-120 cm² under 4 mm.
- **The best line readings come only from designs that fail by their structure.** That is the search buying stiffness the process forbids.

"1 (0)" is a sealed pocket under 0.5 cm³.

| Design | kg | +shaft | Undercut %, motor side / cover | Closed voids (cm³) | Under 4 mm, cm² | Largest section, mm |
|---|---|---|---|---|---|---|
| `box1_fl` | 9.92 | 1.40 | 25.1 / 17.1 | 22 (331) | 100 | 24 |
| `box1_cm` | 9.55 | 1.41 | 25.0 / 17.4 | 22 (331) | 90 | 24 |
| `box1` | 9.54 | 1.44 | 25.1 / 17.2 | 22 (331) | 90 | 24 |
| `box3` | 11.06 | 1.46 | 29.8 / 24.2 | 26 (322) | 105 | 29 |
| `box2` | 10.29 | 1.52 | 24.4 / 17.2 | 26 (326) | 99 | 29 |
| `pass1` | 11.33 | 1.53 | 9.1 / 0.6 | 0 | 87 | 32 |
| `int2` | 10.77 | 1.54 | 8.3 / 0.4 | 0 | 62 | 34 |
| `int1` | 10.60 | 1.63 | 9.2 / 0.6 | 0 | 87 | 30 |
| `hyb2` | 9.51 | 1.92 | 9.2 / 0.6 | 0 | 123 | 28 |
| `hyb3` | 8.91 | 2.03 | 7.1 / 0.4 | 0 | 65 | 29 |
| `hyb1` | 9.04 | 2.03 | 7.1 / 0.6 | 0 | 75 | 29 |
| `lobed_e10_tilt1` | 7.83 | 2.81 | 6.9 / 0.4 | 0 | 7 | 25 |
| `ing2` | 7.84 | 2.83 | 6.5 / 1.1 | 1 (0) | 15 | 27 |
| `whatif_hand_e10` | 7.50 | 2.98 | 8.8 / 0.5 | 0 | 15 | 27 |
| `lobed_e10_b12` | 8.04 | 3.01 | 6.9 / 0.5 | 0 | 6 | 28 |
| `ing1` | 7.63 | 3.06 | 7.3 / 0.9 | 1 (0) | 14 | 25 |
| `lat1` | 8.18 | 3.22 | 6.2 / 0.3 | 1 (3) | 92 | 24 |
| `lobed_e10s` | 7.63 | 3.29 | 7.2 / 0.4 | 0 | 4 | 25 |
| `wheel6` | 7.95 | 3.33 | 6.5 / 0.3 | 0 | 18 | 24 |
| `hyp_e10` | 7.58 | 3.33 | 7.0 / 0.4 | 0 | 10 | 25 |
| `mounts_cover_e10` | 7.49 | 3.38 | 6.8 / 0.9 | 0 | 6 | 25 |
| `lat2` | 7.98 | 3.39 | 6.2 / 0.3 | 1 (4) | 65 | 22 |
| `lobed_e10` | 7.49 | 3.42 | 7.1 / 0.4 | 0 | 6 | 25 |
| `lobed_e10_m6` | 7.49 | 3.45 | 7.1 / 0.4 | 0 | 6 | 25 |
| `wheel2` | 7.65 | 3.69 | 6.8 / 0.3 | 0 | 12 | 22 |
| `wheel7` | 7.85 | 3.71 | 6.6 / 0.3 | 0 | 18 | 22 |
| `wheel5` | 7.53 | 3.73 | 6.9 / 0.3 | 0 | 18 | 22 |
| `wheel1` | 7.44 | 3.77 | 7.0 / 0.3 | 0 | 12 | 22 |
| `wheel3` | 7.46 | 3.79 | 7.0 / 0.3 | 0 | 14 | 22 |
| `dish1` | 8.66 | 3.98 | 6.3 / 2.0 | 1 (0) | 30 | 22 |
| `end10_fan` | 8.52 | 4.03 | 4.3 / 0.0 | 0 | 9 | 24 |
| `end10` | 8.06 | 4.44 | 4.6 / 0.0 | 0 | 4 | 24 |
| `collar1` | 7.47 | 4.71 | 6.8 / 0.5 | 1 (0) | 7 | 27 |
| `hyp_e6` | 6.75 | 4.92 | 7.7 / 0.4 | 0 | 10 | 22 |
| `ribs2_fan` | 8.16 | 4.95 | 3.9 / 0.0 | 0 | 17 | 21 |
| `fan_tall` | 8.14 | 5.19 | 4.0 / 0.0 | 0 | 14 | 21 |
| `lobed_tilt1` | 6.99 | 5.45 | 7.4 / 0.4 | 0 | 7 | 22 |
| `lobed` | 6.66 | 5.64 | 7.6 / 0.4 | 0 | 6 | 22 |
| `ribs_fan` | 7.68 | 5.98 | 4.2 / 0.0 | 0 | 9 | 21 |
| `ribs_skel` | 7.63 | 6.44 | 4.5 / 0.0 | 0 | 6 | 21 |
| `ribs2_skel` | 8.05 | 6.57 | 4.2 / 0.0 | 0 | 5 | 21 |
| `dish0` | 7.35 | 7.04 | 6.4 / 0.7 | 0 | 13 | 22 |
| `shell` | 7.23 | 10.95 | 4.6 / 0.0 | 0 | 4 | 21 |

**What a printed sand mould could do with `box1_fl`.**
- **A one-off could be printed:** a binder-jetted mould with printed cores for the closed cells, and holes to get the sand out.
- **Its hollow cells could not be cleaned or inspected,** and its sharp junctions and 24 mm sections would shrink and tear.
- **No foundry would quote it for series,** and no die could make it.

**What it lacks beyond the measured rules:**
- fillets;
- bolt bosses, so the bolts are plain holes in a lip;
- standing bearing bosses and caps;
- gussets;
- ports, plugs and a breather;
- mount ribs;
- one outline: it has three cans with stepped discs.

## 4. Side by side

| | The production housings | Ours (`box1_fl`) | What it does to ours |
|---|---|---|---|
| The body | One continuous shell per half, its outline one smooth curve round the gears | Three pods (one per shaft), each a can with its own flat end disc at its own depth | Steps, re-entrant corners and flat annular plates at every pod: weak plates, and the look of stacked cans |
| The walls | One thickness, 4-6 mm, curved, the mass in the ribs | 6 mm walls plus two 4 mm skins over a 35 mm lattice (a sandwich) | Stiff per kilogram in bending, but closed cells, undercuts, 9.9 kg |
| The flange | A band with bolt bosses at an even pitch, each gusseted; dowels | A flat lip with plain holes every 90 mm; 12 mm thick in `box1_fl` | No boss for the bolt's head or spot face, nothing tying the flange to the walls |
| The bearing seats | Bosses standing proud of the end walls; a bolted cap where a thrust goes | Bores through the end walls, bosses buried in the plates | The seat turns with its plate (75-95 % of its rotation, `endwall.py`) |
| The ribs | Between hard points: spokes to bolt bosses, trusses between bosses, ear-to-boss ribs, grids on panels; every rib ends on something | Lattices at a fixed pitch and angle, cut by the gear rooms, under skins; spokes ending on the pods' own rims | Ribs that end in the open or on a free rim do little (the wheels, `wheel1`-`wheel7`, gained almost nothing) |
| The mounts | Ears with gussets and ribs to the bearing bosses | Three bosses on the motor side (A20) | The mount loads enter the plates |
| The functions | Drain at the sump's low point, fill at the oil level, a breather, oil feeds, sensors, the park lock, lifting points | Seal bores only | Not a housing yet; the spaces review lists them |
| The casting | Fillets everywhere, drafted faces, demouldable along the split, no closed cavities | No fillet; undercut 17-25 %; 22 closed voids; wedges under 4 mm; 24 mm sections | Cannot be cast as the contract says (section 3) |
| The mass | The reference, 7.73 kg (AVL, three parts) | 9.92 kg | The search bought stiffness with kilograms |

## 5. The criteria we miss

### 5.1 The process

| Rule | In the contract | Measured on our designs before today | Effect |
|---|---|---|---|
| Demouldable along each half's pull: no undercut, no closed void | **Yes, hard** (the pull directions, 02:12) | **No** | The boxes, skinned lattices and inner lattices were built, judged and ranked first |
| Least wall | Yes, 4 mm (D7) | No | Wedges and membranes |
| Machining stock | Yes, 1.5 mm (A12) | No | The seats are cut to size |
| Draft | 0° (A11, printed moulds) | - | Fine for printed moulds; not for patterns or dies |
| Section uniformity, the largest section beside a wall, hot spots | No | No | 12 mm flanges and 24 mm junctions on 6 mm walls |
| Fillets at every junction | No | No | None anywhere |
| Rib proportions (thickness against the wall, depth, T rather than X junctions in sand) | No | No | Crossing lattices with sharp joints |

### 5.2 Function and assembly

The contract has none of these yet; [the spaces review](2026-10-09-spaces-inside-a-reducer.md) lists them with sources:
- the joint's sealing (the bolt pitch, the flange's width and flatness) and its dowels;
- bolt bosses with tool access;
- bearing retention, and the caps where a thrust goes;
- the oil: the sump's low point and drain, the fill at the oil level, a breather, the feeds to the bearings;
- the park lock, the speed sensor and lifting points;
- the mounts' load paths.

### 5.3 The form

The contract describes the package (the gear rooms, the packaging space, the design space) and the interfaces. Nothing in the contract or the generator says what a housing's form is made of (section 2.5). So our generator made what was easiest to make from the gear rooms: a can round each shaft.

### 5.4 The trade's rules, with their sources

From the two research subagents' reports: [casting rules for the checker](2026-10-09-casting-rules-for-the-checker.md) and [the housing's form rules](2026-10-09-housing-form-rules.md). Both stopped at the usage limit, the second after two of its four topics. Check each value against its source before citing it anywhere public. These are the values the new generator takes (section 7).

| Rule | Value | Source |
|---|---|---|
| The wall | One thickness, with ribs instead of mass; no lumps. The cast-iron formula δ = 1.3·⁴√T gives 7.4 mm at our output torque, an upper reference for aluminium; the least feature in a printed mould for A356 is 4 mm (the contract's least wall too) | ITMO 2014 (Dunaev & Lelikov); ExOne's guidance to UTEP, SFF 2024 |
| A rib's thickness | 0.8 × the wall (0.8-1.0 outside, 0.8-0.9 inside). The thermal rule: a leg as thick as its wall makes a hot spot ("must always be avoided"), half as thick is neutral; a rib under half the wall cools it | ITMO 2014; NNGASU 2010; Giesserei-Lexikon; Campbell & Harding, TALAT 3206; Ciobanu 2010 |
| Ribs on both faces of a wall | Staggered by at most one rib thickness, never opposite | AFS *Casting Source* 2021; Giesserei-Lexikon |
| Where ribs go | From flange to boss, with generous draft and fillets; along the force path, by the shortest way; more ribs rather than one restraining rib on a long expanse; a wheel is a hub, broad thin spokes and rims | NADCA 2015 (Fig. 3.3, pp. 37, 95); Thamm 2000 |
| Fillets | A T-junction R = 1-1.25 × the thinner leg; an L-corner of equal walls R_inside = T, R_outside = R_inside + T; R = (0.5-1.5)·δ in the reducer handbooks; never so large that they make a heavy section | NADCA 2021 G-6-2; NNGASU 2010; AFS 2025 |
| Draft | 2° in the reducer handbooks; ¼-1° per side in die casting; not needed in a printed mould (confirmed) | NNGASU 2010; Dynacast; Woods & Ravi, *Modern Casting* 2015 |
| Bearing bosses | Outside diameter 1.25·D + 10 mm (1.2-1.5·D); all boss faces on one wall in one plane, standing 0.5·δ proud (one machining pass) | ITMO 2014; NPTEL (IIT Madras) L17 |
| The split's bolts | As close to the bearing bores as possible (stiffness and tightness); one bolt type; two dowels as far apart as possible, Ø 0.7-0.8 × the bolt | Dunaev & Lelikov; ITMO 2014; INGGO |
| The flange | Thickness 1.5·δ per half; its width set by the bolt (Łódź Table 9.1 for M8: 24 mm, the bolt 13 mm from the wall) | ITMO 2014; Łódź 2011 |
| Mounts | As far apart as the envelope allows, at the corners; ribs stiffen the housing at the mount points (in an EV drive unit, for the crash load path) | Dunaev; Malm & Wurzinger (Chalmers/Volvo) 2024 |
| Oil | The drain at the lowest point, below the floor, the floor sloped 0.5-1° to it; a fill and inspection hatch at the top, the breather in its cover | Dunaev & Lelikov; ITMO 2014 |
| Lifting | Lugs cast with the housing: a rib with a hole, about 2·δ thick round a hole of about 3·δ | Dunaev Fig. 11.11; ITMO 2014 |
| Noise | A rib is itself a radiator: keep its free area small and its first bending mode off the orders at cruise. The wall panels give most of a compact e-drive's radiated power (2-4 kHz) | Malm & Wurzinger 2024; *Appl. Sci.* 16:3079 (2026) |
| Printed moulds' use | Economic below about 45 castings (simple) to about 1,000 (complex); every cavity needs a way for the sand out | Almaghariz et al., *Int. J. Metalcasting* 2016; Woods & Ravi 2015 |

### 5.5 The search

- **The objective:**
  - The contract's objective is the least mass, and the design to beat weighs 7.73 kg.
  - The second round chased the intermediate's misalignment line with mass: 9.5 to 11.3 kg for no gain past 1.40.
  - A designer stops adding metal when it buys nothing, and pulls the system's levers: the bearing arrangement (A8), the shaft, the joint, the mounts.
- **The rung:**
  - The plan of record labels every design with its rung: simulation-feasible, then process-rule-feasible.
  - Our designs were ranked without any rung. None reaches the first, and the second was never checked.

## 6. The trade: how engineers make these shapes

### 6.1 The process

From Ivanov's thesis, the agricultural studies, the Hexagon deck, and the earlier notes on [the trade and art](2026-10-09-the-trade-and-art-of-housing-design.md) and [topology optimisation practice](2026-10-09-housing-topology-optimisation-practice.md):

1. **The package:** the gear train, bearings, differential, park lock, oil level, the motor interface, the mounts, the split.
2. **The silhouette:**
   - the split's outline drawn round the gear circles with a clearance;
   - the bolts placed along it at the sealing pitch;
   - the motor ring and the mount points.
3. **The shell:** walls of one thickness offset from the gear rooms. Each half is drawn along its pull, with the end walls flat or in drafted steps, and the sump.
4. **The hard points:** bearing bosses, bolt bosses, mount ears, port bosses, caps and covers.
5. **The first ribs, by rule and experience:**
   - from each bearing boss to the nearest bolts and mounts;
   - between the bearing bosses;
   - spokes on round faces;
   - gussets at the roots;
   - ribs on the panels for noise.
6. **The casting detail:** fillets, draft, rib proportions, as few cores as possible.
7. **The FE:**
   - stiffness at the bearings, and the gears' misalignment through a system model (Hexagon);
   - strength;
   - modes and radiated noise.
8. **A local optimisation:**
   - in the voids between the features, with a pull direction and member sizes;
   - read across runs into ribs between features;
   - verified, then sized by a small sweep.
9. **Two or three cycles,** then the detail for machining (datums, stock, tolerances) and a casting simulation with the foundry.

### 6.2 Why our wheels gained almost nothing

**My reading, to be measured on the grammar's baseline:**
- **Our spokes ended on the pods' own rims,** rings on the free edges of thin tubes that ovalise with the lobes (line tilts of 0.77-0.93 on 6 mm walls). The spoke turned with its wall.
- **In the trade's housings the rib network goes on down the side walls** to the flange's bolt bosses. The network closes on the bolted joint, a stiff ring, and the hub is a boss standing proud.
- **The vocabulary without the grammar had no hard points to work between.**

## 7. What we do

**What stops:**
- the stiffness forms on the lobed pods: boxes, skinned lattices, inner lattices, collars and dishes on pods. The contract's own rule refuses them;
- adding metal to pass the intermediate's line.

Their numbers stay, as the study of where a housing's stiffness comes from ([the record](../features/loop/2026-10-09-record-night-to-noon.md)).

**What we keep:**
- the FE judge (exact couplings, single precision);
- the grade (the seat against its shaft plus the shaft's bend);
- the diagnosis (`endwall.py`, the ceilings);
- the castability check;
- the measured mechanics: the end walls bend as plates, the lobes bend sideways, the joint gives nothing, and the intermediate's chord binds.

**The PBIs (the loop's page):**

| PBI | Goal | Done when |
|---|---|---|
| LOP-8 | **The castability judge in the grade.** `castable.py`'s contract rules (the pull directions, the least wall) join `grade.py`, and every design carries its rung. The trade's further rules (section, fillets, ribs) are reported until the engineer adopts their values | Every design so far re-graded with its rung |
| LOP-9 | **The housing in the trade's grammar.** A new builder, `prototypes/first_loop/grammar.py`, castable by construction and proven by `castable.py`. Named by geometric kind (an outline, a shell, a flange, cylindrical bosses, a rib graph); the reducer's roles in data. It builds, in order: (1) the silhouette; (2) one shell of one thickness, drawn along each half's pull; (3) one end wall per half, its steps drafted; (4) standing bearing bosses, with a bolted cap where a thrust goes; (5) the flange with bolt bosses at a pitch, gusseted, and dowels; (6) the mounts as ears with gussets; (7) the ports: drain, fill, breather; (8) a rib graph, its edges between hard points chosen as data, each rib a drafted slab with root fillets; (9) fillets at every root | The EV reducer's baseline builds, passes the contract's casting rules, and its picture reads as a housing beside the trade's |
| LOP-10 | **The baseline graded, then A8.** The grammar's first housing with the trade's default ribs (the AVL family: spokes on the motor face, a triangulated cover, ear-to-boss ribs, gussets), FE-graded at about the reference's mass | Graded and pictured; the intermediate pair's reading in the engineer's hands for the A8 decision |
| LOP-11 | **The loop on the grammar.** The diagnosis; each rib edge's gain per gram; a local optimisation in the voids between the features, with the pull direction and member sizes, read into the graph's edges; a sizing sweep. It takes over the old LOP-8 and LOP-9 | The lightest castable design that passes, or the bound with its reason |

**For the product, once the prototype shows them:**
- **PRC-1:** the process profile and its checker, the contract's rules plus the trade's, sourced;
- **GEO-1:** the housing grammar in `src/`, by geometric kinds.

## 8. Settled with the engineer, and what is left to them

1. **The reference shapes are the requirement** (the engineer, 13:29: "I already provided you reference shapes that I am expecting from you. How best you can achieve that?").
   - The generator follows production casting's rules: demouldable along the pull without cores, drafted, filleted, one wall thickness, ribs between hard points (section 5.4's values).
   - These are stricter than the contract's floor, so the contract does not change: A11's 0° draft, the 4 mm least wall and the 1.5 mm stock stay.
   - A design made this way can be printed for its first parts and drawn in a pattern or a die for series.
2. **A8** (the intermediate's bearings): the engineer decides it after LOP-10, on the number of a housing that can be made.

## 9. Sources

- The engineer's 36 pictures (12:48), from:
  - Ivanov 2018 (Scribd 514058589);
  - Son 2019 (Appl. Sci. 9:4571) and Son 2020 (Appl. Sci. 10:8414);
  - Kim 2024 (Sci. Rep. 14:4145);
  - Google Images listings of ZF, Avtec (IndiaMART), Kalyani Technoforge, Punch Powertrain, Rawsuns (Alibaba), Magna (Jiangxi) and Batom;
  - MDPI (the EMU gearbox).

  Read from the screenshots; not stored.
- This repository:
  - [the trade and art of housing design](2026-10-09-the-trade-and-art-of-housing-design.md);
  - [how housing topology optimisation is practised](2026-10-09-housing-topology-optimisation-practice.md);
  - [the spaces inside a reducer](2026-10-09-spaces-inside-a-reducer.md);
  - [housing sources, round 2](2026-10-08-housing-sources-round-2.md) (the Łódź handbook's Chapter 9);
  - the plan of record, section 7 (process profiles and the label ladder);
  - [the record, night to noon](../features/loop/2026-10-09-record-night-to-noon.md).
- fastcae's [gearbox-housing engineering report](../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md), §5.3 (NADCA 2015's die-casting rules).
