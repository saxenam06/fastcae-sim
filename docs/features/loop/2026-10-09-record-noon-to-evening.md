# The first loop, noon to evening: production housings, the trade's grammar, and the product's reach

**What this is.** A record of 9 October 2026, 12:32 to 19:55, for review, following [the record, night to noon](2026-10-09-record-night-to-noon.md). It covers:
- what was built and measured;
- every failure met, with its cause and its cure;
- the engineer's questions and the answers given;
- the decisions taken, and what is still open.

The [loop's page](status.md) says what is true now; this page says how we got there.

**Status words.** *Solved*: the cause found and the cure measured. *Worked round*: understood, the proper cure a later PBI. *Open*: not solved.

## 1. In short

1. **None of our 43 housings could be cast as the contract says.** The engineer saw it first, on `box1_fl`'s picture: "I have never seen the housing like this." A new check measured it on the CAD (`castable.py`):
   - no design passed the contract's own hard pull rule or its 4 mm least wall;
   - the best one, `box1_fl`, was 17-25 % undercut, with 22 closed voids.

   The search had graded physics only, and the generator spoke no housing grammar.
2. **The engineer's 36 pictures of production housings share one grammar,** written up in [the study](../../research/2026-10-09-production-housings-against-ours.md) as eleven rules: one silhouette, one thin shell, hard points first, ribs between hard points, wheels and grids, gussets, fillets, everything drawn along the pull. The trade's rule values, with sources, came from two research subagents.
3. **The reference shapes are the requirement** (the engineer, 13:29). A new generator, `grammar.py`, draws the housing in the trade's grammar, castable by construction. Its baseline, `grammar4`:
   - 7.50 kg, against the reference's 7.73;
   - reads as a production housing;
   - is castable at the check's resolution (0.8 cm² undercut per half);
   - is judged by FE: 162/192 µm, misalignment 6.36 × its line.

   It is softer than the old lobed shells at the same mass, for causes understood (section 6).
4. **The engineer then asked how far the product can go:** every style in the pictures, fitted to a requirement, or adapted from a new photograph. The answer is [every style, fitted to the requirement](../../research/2026-10-09-every-style-fitted-to-the-requirement.md): yes, in the design phase, through a recipe with style presets, picture reading, agent-written features and an exploring agent. The neural CAD methods help; the deterministic tools judge.
5. **Now building:** LOP-12, the recipe and its six style presets as a gallery. Then LOP-13, LOP-14 and PLT-9 (the 3D viewer).

Nothing since 04:49 is committed (the engineer, 09:57: "later we commit"). Nothing is pushed.

## 2. Timeline

| Time | The engineer | What was done | Where |
|---|---|---|---|
| 12:32 | Document everything since last night | The record, night to noon; the pages | [the record](2026-10-09-record-night-to-noon.md) |
| 12:48 | "Is this housing manufacturable? … I have never seen the housing like this": 36 pictures; find the missing criteria; study the trade; decide | Two research subagents sent; `castable.py` written; all 43 designs measured; the study written | §3, §4 |
| 13:10 | | Decided, at the engineer's request: the casting rules into the grade (LOP-8), a generator in the trade's grammar (LOP-9), its baseline before A8 (LOP-10), the loop on it (LOP-11) | §4 |
| 13:29 | "Why this is still a question on me … I already provided you reference shapes" | No more questions on the process. The generator follows production casting rules, stricter than the contract's floor | §4 |
| 13:31 | | The session's usage limit stopped both research subagents | §5 |
| 18:41 | "continue" | The generator's design fixed from the layout; `grammar.py` written | §6 |
| 18:42-18:43 | "Can we take the result of agents whatever they have done so far … why they are not copied in docs" | Both partial reports saved into `docs/research/`; their values into the study (§5.4); the rule changed: agents write to the docs | §5 |
| 18:58-19:24 | | `grammar0` to `grammar4` built; each fault the check found was fixed; the check's own three faults were fixed | §6, §8 |
| 18:59 | Are the motor and the differential inside? What is a "generator"? | Answered | §7 |
| 19:25 | | `grammar4` judged by FE | §6 |
| 19:39 | Twenty questions: the differential's bearings and seals; the motor's mass; the generator, the split, the mounts, the fixed points, bosses; one generator, one design?; industry practice; topology optimisation's reach; a 3D viewer with parts, colours, toggles and transparency | Answered; PLT-9 planned | §7 |
| 19:45 | Housings in every picture's style, fitted to my requirement? bunnysocrazy.com; a Mercedes photo, adapted? How far can the product go today? | Read the site (Awesome Neural CAD, about 150 papers); the answer written | §7; [the note](../../research/2026-10-09-every-style-fitted-to-the-requirement.md) |
| 19:54 | "Document the current status, state of our discussions and start building" | This record, the pages; LOP-12 started | |

## 3. Can our housings be cast? (12:48-13:10)

- **The check** (`prototypes/first_loop/castable.py`) works on each half's CAD and needs no FE. It tests the contract's rules:
  - **the pull direction,** by two-sided visibility along each half's pull, rays cast through VTK. A closed void counts as an undercut.
  - **the 4 mm least wall,** by a ray along each face's inward normal.
  - **the largest section,** reported from a 1 mm distance map.
- **The result:** none of the 43 designs passed either rule.
  - The boxes, `box1_fl` among them, were 17-30 % undercut, with 22-26 closed voids of about 330 cm³: the cells of their cored double walls.
  - The inward-thickened walls and inner lattices left 60-120 cm² of wedges under 4 mm.
  - Even the plain shells failed, on two details every design inherited: the motor's flange plate overhanging the split flange, and 1 mm membranes at the motor bolt holes.
- **What it meant:** the best line readings came only from designs that fail by their structure. The search bought stiffness the process forbids. Every row is in the study's section 3.

## 4. The study and the decisions (12:48-13:29)

**[Production housings against ours](../../research/2026-10-09-production-housings-against-ours.md)** covers:
- the 36 pictures, by family: the AVL housing's figures; the agricultural gearbox; Avtec, Kalyani, Punch, Rawsuns, Magna, Batom; ZF's rail drives;
- the grammar they share, in eleven rules;
- our designs, measured;
- the criteria we miss: process, function, form, and the search itself;
- how engineers make these shapes;
- the trade's rule values with their sources (§5.4).

**Decided:**

| Decision | Choice | When, by whom |
|---|---|---|
| A housing in the trade's grammar, castable by construction | No more stiffness forms on the lobed pods. The casting rules join the grade (LOP-8); a new generator in the grammar (LOP-9); its baseline graded before A8 (LOP-10); then the loop on it (LOP-11) | 13:10, Claude, at the engineer's request (12:48) |
| The reference shapes are the requirement | The generator follows production casting's rules (demouldable along the pull without cores, drafted, filleted, one wall thickness, ribs between hard points). These are stricter than the contract's floor, so the contract does not change (A11's 0° stays) | 13:29, the engineer |

## 5. The research subagents (12:58-18:43)

- **Two subagents were sent** for the rule values: casting rules (sand, printed moulds, die casting), and the housing trade's form rules.
- **Both stopped at the session's usage limit** at 13:24-13:31, with 58 KB written, but into the session's scratchpad, on my instruction.
- **The engineer asked** "why they are not copied in docs". The reports were saved as written:
  - [casting rules for the checker](../../research/2026-10-09-casting-rules-for-the-checker.md), complete in its three topics;
  - [the housing's form rules](../../research/2026-10-09-housing-form-rules.md), two of four topics: EV practice and sealing were never researched.

  Their values are in the study's §5.4. Among them:
  - ribs 0.8 × the wall;
  - Campbell's thermal rule: a leg as thick as its wall is a hot spot;
  - fillets by junction (NADCA 2021);
  - bosses 1.25·D + 10 mm, their faces in one plane, 0.5·δ proud;
  - bolts as close to the bearings as possible;
  - printed moulds need no draft.
- **The rule changed:** research subagents now write straight into `docs/research/`, marked as unchecked, so a stop loses nothing (the memory note on the research library).

## 6. The generator in the trade's grammar (LOP-9, 18:41-19:25)

**What it builds** (`prototypes/first_loop/grammar.py`, about 8 s a design):

| Feature | How it is built |
|---|---|
| The silhouette | The exact convex hull of the gear rooms' circles grown by the wall, in arcs and tangent lines. The input's circle is grown to hold the motor's ring (r 90), so nothing overhangs the split flange |
| The motor side | One cup, drafted 1.5°, to one flat motor face at the deepest stack's end; fillets of 6 mm inside and 12 outside at the corner. The motor's ring (A25) is built up into the corner, with an eight-spoke wheel inside it |
| The cover | A drum over stage 2, its inside face the axial clearance past the gears. A bearing bridge (the hull of the intermediate's and output's bosses) rises to the stacks' ends |
| Bosses | 1.25·D + 10 mm, hanging inside to each bearing. Pads stand 0.5·δ proud outside |
| The flange | An 8 mm lip, with Ø20 bolt bosses at about 80 mm (14 bolts) |
| Mounts (A20) | Columns from the motor face to the flange |
| Ribs | 5 mm thick, 15 mm off an end face and 10 off a side wall. Each spoke turns at the corner: over the end face from the nearest boss to the wall under a bolt, then square down the side to the bolt's boss. Plus boss-to-boss ribs and ear-to-boss ribs |
| Clearances and meshing | Every boss kept out of the moving parts' rooms and of the other bearings' fitting paths, and every fitting path cut clear at the end. Each half kept as built when gmsh meshes it, healed otherwise |

The record and face names are the same as `lobed.py`'s, so `fe.py`, `grade.py`, `castable.py` and `poster.py` read it unchanged. `look.py` shows a design as the trade's pictures do.

**The builds:**

| Build | kg | What changed | Castability (undercut per half) |
|---|---|---|---|
| `grammar0` | 7.63 | The first | 80 / 49 cm² read (most of it the check's own fault, §8); one tiny closed void |
| `grammar1` | 7.59 | The motor ring built up into the corner; spokes from each pad's edge | No voids |
| `grammar2` | 7.60 | The bridge's hollow stops at other bosses; tubes kept out of fitting paths | 11.5 / 1.3 cm² (the check now honest) |
| `grammar3` | 7.51 | Fitting paths cut clear; side ribs at 10 mm | 0.2 / 0.0 cm²; the cover did not mesh for FE (§8) |
| **`grammar4`** | **7.50** | Spokes turn at the corner; the mesh test and heal step | **0.8 / 0.8 cm²**, no voids, 0.1-1.5 cm² of specks under 4 mm; both halves mesh |

**`grammar4` judged** (8 mm mesh, 49 s; single precision, 4 refining steps, residual 4·10⁻¹²):

| | `grammar4` | The reference |
|---|---|---|
| Bearing beds, drive / reverse | 162 / 192 µm | 52 / 138 µm |
| Misalignment against the shaft, +shaft | 6.36 × its line (housing alone 6.54) | Not graded |
| First mode | 927 Hz; one clash, 1,099 Hz within 3 % of stage 2's 1,127 Hz | |

`lobed_e10s`, at the same mass, reads 102/139 µm and 3.29.

**Why the baseline is soft** (the causes are understood):
- **The flat motor face** sits at the deepest stack's end, so the intermediate's and output's bearings hang on tubes 14 and 9 mm off the wall.
- **The end walls are 6 mm,** against `lobed_e10s`' 10.

**The levers next** (LOP-11): each bearing's wall drawn to its own depth, or gussets inside at the tubes; deeper ribs where the motor leaves room; the end walls' thickness.

## 7. The engineer's questions, and the answers given

| Question | Answer |
|---|---|
| Are the motor and the differential inside the housing? (18:59) | The differential is: it sits in the output gear (the contract's carrier, A23). The motor bolts on outside, to the motor face's ring of 6 bolts (A25); its body (Ø204) sits against that face |
| What is the "generator"? (18:59, 19:39) | The program that draws the housing's CAD. It is a parametric feature program, like an Onshape FeatureScript or a SolidWorks macro with a design table, in Python on OpenCascade (CadQuery): features in order, each computed from data, deterministic |
| How are both output bores "sealed" if the half-shafts come out? Is the bearing between the differential and the housing? Is it in the papers? (19:39) | The output bearings (6309, 6209, 45 mm bore) are the differential case's bearings, on its hubs, 96 mm apart (A23). No bearing touches a half-shaft. Each half-shaft passes through a case hub, is splined to a side gear in the cage, and leaves through a lip seal in the output bore, outboard of the bearing. "Sealed" means that seal. The bores look small because the case body (Ø105) is wider than its hub bearings, and the visible bore is the seal's (Ø65). Our gear train is parallel-axis: the "crown" is the 198 mm helical output gear on the case. Simplified: the seal runs on 45 mm (the hub), and the case's insides are not modelled. Sources: Ivanov ("integrated with the crown and cage of an incorporated differential mechanism"; a bearing cap takes its axial force), Schaeffler 2010, Hofstetter 2018 |
| Do we consider the motor's mass and size in the calculations? How do the papers do it? (19:39) | Today the motor enters only as its reaction torque on the flange bolts (Ivanov's Fig. 36) and as space no rib may enter. No paper we hold includes its mass: Ivanov judges static torque and the housing's free modes; Son and Kim add the gears and shafts as substructures. Proposed: the motor's mass and centre of gravity as contract inputs, plus acceleration load cases, with the motor in the FE as a lumped mass. A load-case change, so **the engineer's decision** (Open) |
| Who defines the split? The bolts, the mounts and the motor interface are not in the contract (19:39) | The split's type is the engineer's decision of 02:12; its place is computed by the generator (z = 14.35). The mounts (A20) and the motor flange (A25) are placed by the prototype and are not yet in the contract: GBX-5 puts them there as the vehicle's and the motor's interfaces. The flange bolts come from rules (Łódź, Henkel). The wall, draft, fillets, rib sizes and which points the ribs join are design choices |
| What are the "fixed points" the ribs join, and the options? (19:39) | Hard points, where load enters or leaves: bearing bosses (gear loads in), the motor's ring (its torque), mount bosses (the vehicle's reactions), bolt bosses (the joint). The options are which pairs are joined (boss–bolt, boss–boss, mount–boss, mount–bolt, ring–boss) and the pattern (spokes, a wheel, triangles, a grid, gussets) |
| What is a boss? The motor ring, the wheel, the scalloped flange? (19:39) | A boss is a local, usually round, thickening that gives a hole or a seat its metal: a bearing boss round a seat, a bolt boss round a bolt hole with a face for its head, a mount boss round a vehicle bolt. The motor ring is the raised ring with 6 holes on the motor face. The wheel is the 8 spokes inside it. The scalloped flange is the round bumps along the split line, one per bolt |
| With one generator, only one possibility? Am I doing something wrong? How does industry do it? Can topology optimisation replace the feature program? (19:39) | Not wrong: the generator's choices were hard-coded, so it makes one family. They must become the agent's: a recipe of choices plus a growing vocabulary of feature types. Industry starts from a previous product or a company template (parametric layouts with user-defined features and rules in CATIA or NX), then refines by FE and topology optimisation. Topology optimisation cannot replace the feature program. It says where material helps, in a space round a design, and someone reads it into features |
| I want to see the generated CAD in the UI, every part in its own colour, toggled, with transparency; where? (19:39) | The Designs tab. Both halves and every part inside, each its own colour, with show/hide chips and opacity sliders, and orbit, pan and zoom. The design's recipe, castability and grade sit beside it. It extends the Contract page's renderer (PLT-8): **PLT-9** |
| Can you create housings in all the pictures' styles, fitted to my requirements? How can we use bunnysocrazy.com's methods? Will a Mercedes photo be adapted? How far can the product go today? (19:45) | Yes, in the design phase: [every style, fitted to the requirement](../../research/2026-10-09-every-style-fitted-to-the-requirement.md). It takes a recipe with style presets (six families from the pictures), a vision-language model reading a picture into a recipe (style only, the dimensions from the contract), agent-written features admitted by tests, and an agent that composes, builds, judges and shows a gallery. Awesome Neural CAD (about 150 papers in six sections) strengthens each step; none replaces the deterministic tools. A photo gives a concept in its design language, exact to the user's interfaces and judged: not a copy, not production-ready, its principles rather than its protected design |

## 8. Failures, causes and cures

| Failure | Cause | Cure | Status |
|---|---|---|---|
| All 43 designs uncastable | The grade measured physics only; the generator had no housing grammar; the contract's casting rules were never measured | `castable.py`; a new generator in the trade's grammar | **Solved** for the baseline (`grammar4`); LOP-8 puts the check into the grade |
| I asked the engineer which process to design for, after 36 reference pictures | I treated a question the pictures already answered as open | Production casting rules adopted, stricter than the contract's floor; no question back | **Solved**; a lesson kept |
| The research subagents' results stranded in the scratchpad | I pointed them at the scratchpad "to check first", and the usage limit stopped them | Reports saved to `docs/research/`; agents write to the docs from now on | **Solved** |
| The check read 1.5-1.8 % undercut on drafted walls | Facet normals on 1.5°-drafted faces flip sign | Each face's exact normal (`exact_normals`) | **Solved** |
| The check still read 1.5 % | A ray along a drafted face re-crosses its own facets | Rays start 0.3 mm off the face, and a drafted cone, cylinder or plane's own crossings are left out | **Solved** |
| Projecting rays' starts onto the true surface made it worse (4.4 %) | CadQuery tessellates relative to each face's size, about 1 mm on big walls, so a ray from the true surface began behind the facets | The half meshed first to an absolute 0.1 mm (`BRepMesh_IncrementalMesh(shape, 0.1, False, 0.25)`); the projection dropped | **Solved**; a CLAUDE.md pitfall |
| The motor ring's back hid under the cup's rounded corner | The ring sat partly on the fillet | The ring built up into the corner, and the cavity cut takes back what lies inside | **Solved** |
| Thin wedges where the output's spokes met, and a tiny closed void | All spokes started at the axis | Spokes start inside their boss's pad | **Solved** |
| A pocket over the input's boss in the cover | The bridge's hollow opened the drum's end wall over the boss | The hollow stops at other bosses | **Solved** |
| The intermediate's boss overhung the input bearing's seat by 0.5 mm, which would block its fitting | The bosses overlap at 83 mm centres | Every boss is cut by the other bearings' fitting paths | **Solved** |
| A lump of the bridge in the intermediate's fitting path | The first cure's ring round the input's boss was 6 mm too wide | Narrowed; every fitting path cut clear at the end | **Solved** |
| `grammar3`'s cover did not mesh ("two exactly self-intersecting facets") | Slivers where straight spokes crossed the side walls aslant | Spokes turn at the corner; a mesh test and heal step (`meshable`) | **Solved** (`grammar4` meshes as built) |
| The baseline is about 2× softer than the lobed shell at equal mass | The flat motor face's long tubes; 6 mm end walls | The levers listed in §6 (LOP-11) | **Open** |
| A mode within 3 % of stage 2's mesh frequency | Not yet studied | To be designed out with the stiffness | **Open** |

## 9. What is open, and for whom

**For the engineer:**
1. Whether the motor's mass and centre of gravity, and acceleration load cases, enter the contract (§7).
2. A8, the intermediate's bearing arrangement, after LOP-10 grades a castable housing.
3. When to commit, and when to push.

**Mine, in order:**
1. LOP-12, the recipe and its six style presets as a gallery on the contract, each castable and judged. **Building now.**
2. PLT-9, the 3D viewer.
3. LOP-13, the pictures read into recipes.
4. LOP-14, agent-written features.
5. LOP-11's stiffness levers.
6. LOP-8, the castability check in the grade.
7. GBX-5, the mounts and the motor's interface into the contract.

## 10. Where the numbers live

The CAD records, STEP and BREP files, castability records (`castable_<stem>.json` and `.png`), FE answers and pictures (`look_<stem>.png`) are in `data/first_loop/`, which git ignores. The numbers that matter are copied here and on the loop's page.
