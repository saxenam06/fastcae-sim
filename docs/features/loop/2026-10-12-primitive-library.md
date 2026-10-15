# Designs built only from production's parts: the library and the Refine method

**12 October 2026, 11:05, for the engineer's review (LOP-26).**

The engineer's requests, 10:31 to 11:01:
- 10:31: "Want all families of primitives production housing build and how can we make optimization only build features with those primitive in the library… this will kill unwanted shapes like paint";
- 10:46, on a fixed menu of candidates: "this constraints creativity and innovation";
- 11:01: the layout by **Refine**.

## 1. In short

- **The problem.** Left free, the optimiser makes shapes no foundry would make: paint (thin layers spread over the walls) and lumps (thick pads). Redrawn afterwards as production features, the designs lost their stiffness: this morning's parametric CAD was 4.6-5 times too soft.
- **The rule.** The optimiser builds only with production's parts. **What** a member can be is fixed: production's families (§2). **Where** members go, how many there are, which way they run and how they join stays the optimiser's.
- **The method, Refine (§3).**
  1. A free optimisation lays out the members where the load asks. It uses the least member, so it makes no paint.
  2. Each of its members is rebuilt as the production part it looks like.
  3. The optimiser then moves, turns, stretches, resizes or removes those parts.
  4. The parts that survive are the recipe for the exact CAD. The CAD is the optimised design; nothing is read again.
- **Why it can work.**
  - The free run needs no paint: `a2_c1` met the stiffness and the tilt without it at 5.49 kg.
  - Sized production parts can pass: the bore experiment's ties passed every graded line at 5.73 kg.
- **What is asked:** a review of this design. Then step 1 (§5), which shows the free run's members turned into parts, pictured beside production's photos, before any optimisation.

## 2. The library: what production housings are built from

The families come from the 36 + 17 production pictures and the trade's rules already in the research library:
- [the trade's vocabulary](../../research/2026-10-09-the-trade-and-art-of-housing-design.md) §3.5;
- [the grammar production housings share](../../research/2026-10-09-production-housings-against-ours.md) §2.5, and [their rules with sources](../../research/2026-10-09-production-housings-against-ours.md) §5.4;
- [four production EV housings](../../research/2026-10-11-production-ev-housings-against-the-ribbed-cad.md);
- [fastcae's rib rules](../../research/2026-10-09-fastcae-rib-rules.md).

Parts of those notes came from research subagents: check a value against its source before citing it in public.

### 2.1 Three kinds of family

- **Fixed by the contract:** always there, never chosen. Bolt bosses (Ø20 on the land, A26), mount eyes, the 4 mm skin, and the machined pads.
- **Tied to a hard point:** each family's place follows from what it holds. The optimiser sizes each one, or removes it.
  - bearing bosses, and towers where a seat stands on a tube;
  - gussets under the bolts, round tall bosses, and under the mounts;
  - mount arms.
- **Free:** spokes, links, ties, ring ribs, rims, grids, fins and belts. The optimiser chooses where they go, which way they run, how many there are and how big they are.

### 2.2 The families

| Family | Kind | What it is | What it does | Where production puts it |
|---|---|---|---|---|
| Bearing boss | Tied | A ring round a seat, standing proud of the end wall | Takes the bearing's load into the wall; the hub the ribs end on | Every seat |
| Tower | Tied | A collar down the tube a seat stands on, with fins | Holds a seat that stands off its end wall | Seats on tubes (our cover's three) |
| Bolt boss | Contract | A cylinder round a flange bolt | Clamps the joint; a rib's end | On the flange at an even pitch |
| Mount eye | Contract | A boss round a mount's bolt | Where every load leaves the housing | The mounts |
| Port boss | Contract (none yet) | A boss round a drain, fill, breather or sensor port | Function | The drain lowest, the fill and breather on top |
| Spoke | Free | A rib from a bearing boss out to a rim | The hub's moment reaches the rim as in-plane forces, so the end wall stops bending | Round faces: a wheel of 6-12, straight or a fan |
| Link | Free | A rib or a web between two bearing bosses | Carries the gears' separating force directly | Between the seats on one wall |
| Tie to a mount | Free | A rib from a mount to a bearing boss | The straight path from the bearing to the ground | Every mount |
| Tie to a bolt | Free | A rib from a bearing boss to flange bolts | Takes the boss's load to the joint | Round each boss |
| Ring rib, rim | Free | A circle round a boss; a rib along the end face's edge | Something stiff for the spokes to end on | Round wheels; along the flange |
| Grid | Free | Crossed ribs in triangles on a bare panel | Keeps a panel's bending stiffness and its modes up | Large flat panels |
| Fin | Free | A rib along the pull on a side wall or down a tube | Stiffens a side wall or a tube in bending | At bolts, round each room |
| Belt | Free | A rib round the side walls, parallel to the flange | A continuous rim beside the joint | Along the flange |
| Flange gusset | Tied | A triangle under a bolt boss, flange to side wall | The boss stops bending at its root | Under every bolt boss |
| Boss-root gusset | Tied | Small triangles round a tall boss's root | The same for a bearing boss on a tube | Round tall bosses |
| Mount gusset | Tied | Two webs under a mount's eye | Braces the mount | Every mount |
| Arm | Tied | A plate from the shell to a mount's eye, with webs | Carries the mount's load into the shell | Mounts standing off the shell |
| Skin | Contract | One thickness, following the gears | Closes the housing; the mass belongs in the ribs and bosses | Everywhere (4 mm) |
| Machined pad | Contract | A local thickening where a face is machined | Function | The land, mount faces, boss faces |

Every part also gets draft, a root fillet, a rounded top, and cores in thick sections. These are drawn, not sized.

### 2.3 The rules every part keeps, on our grid (4 mm voxels, a 4 mm wall)

| Rule | Production's value | Here |
|---|---|---|
| Rib thickness | 0.8-1.0 × the wall | **8 mm, two voxels.** A rib of one voxel is not honest at 4 mm: FE reads such members 11-30 % softer than the model. 8 mm is twice the wall, a hot spot by the thermal rule, so it is drawn with draft and revisited on a finer grid (3.5 mm is the finest that fits the card) |
| Rib height | At most 5 × the thickness | At most the band (24 mm; for a mount, its own reach); **at least 8 mm**: a column under 8 mm holds nothing, so there is no paint |
| Every rib ends on something | A boss, a rim, another rib | Every member ends at a node: a hard point, the face's edge, or a junction with other members. An end left alone when its partners vanish is flagged, and the agent removes or extends it |
| Crossings | Nodes at bosses; 60° or more | Members meet at nodes. Where parts overlap, a column takes the tallest (a smooth maximum), never the sum, so a node is no hot spot |
| Regularity | One depth and one thickness per family | One thickness per family. The heights are per part, a root and a tip: one height for a whole form cost twice the metal |
| Bearing bosses | Ø 1.25·D + 10 mm, standing 0.5·δ proud | The ring's radius within a range round it |
| Fillets | A T-junction's R = 1-1.25 × the thinner leg | Drawn (4 mm roots), not sized |
| Draft | ¼-1° a side (die casting); 2° (the reducer handbooks) | The height field casts along the pull; the draft is drawn |
| Lumps | One thin skin; no lumps | Each family's width is fixed, so a lump can only be a boss or a node |

## 3. The Refine method

### 3.1 Two shapes carry every family

In the height field, each column holds metal of one height off its face: off an end wall, or off the split beside a side wall. Every family above is then one of two shapes, with a family's label and rules:
- **a member:** a straight plate between two nodes, as wide as its family, its height running from a root value at one end to a tip value at the other. Spokes, links, ties, rims, grids, fins, belts, gussets and arms are members. On the end walls they stand off the wall; beside the side walls they stand off the split, so a gusset is a member whose height falls from the wall to its bolt.
- **a ring:** an annulus round an axis, with an inner and an outer radius and a height. Bearing bosses, ring ribs and towers are rings: a tower is a ring beside a seat's tube, standing off the split.

**Nodes** are where members end:
- **fixed:** a bolt or a mount;
- **sliding:** round a boss's rim, or along the face's edge, one number each;
- **free:** a junction in the open, two numbers.

The layout is a graph: nodes joined by members, with rings at the seats.

### 3.2 Step A: the free run lays out the members

The optimisation is the free one with the least member (8 mm), as `a2_c1`:
- 4 mm voxels, peak drive, the band 24 mm;
- the compliance, with every tilt and bed held at 1/1.15 of its line;
- 5.5 kg.

Its members are where the load wants metal. Nobody draws them. The first one exists already: `topofree_compliance_tilt_5.5kg_4mm_..._c1_hf6_single_flange_beds_lm8_sf1.15` (202 s).

### 3.3 Step B: each member becomes the part it looks like

The conversion follows the trade's reading:
- **Tied first.** Metal round a seat becomes its boss: the ring's outer radius is where that metal ends, within the boss's range, and its height is the metal's. Metal beside a seat's tube becomes a tower, and its ridges along the tube become fins. Metal beside a side wall at a bolt becomes the bolt's gusset. Metal reaching a mount becomes its arm, or its gusset webs.
- **Free next.** The rest of each face's metal is thinned to its skeleton (`section_forms.flow_ribs`). Junctions become free nodes, ends at bosses, bolts, mounts or the edge become sliding or fixed nodes, and each branch, cut into straight runs, becomes members. Each member takes its family from what it joins: boss to boss is a link, boss to bolt or mount a tie, boss to the edge a spoke, along the edge a rim.
- **Broad metal becomes a grid, never one wide part.** Where the free run spread metal much wider than a rib (wider than about 20 mm), it becomes several members: parallel ribs along a strip, or triangles over a panel (Hexagon's reading: "bulk reinforcement material translated to a cross-hatched lattice of ribs").
- **Each part's start size** is fitted to the metal it replaces. The members' root and tip heights come from the free run's columns at their ends.

### 3.4 Step C: the optimiser moves and sizes the parts

The variables:
- every free node's two coordinates and every sliding node's one;
- every member's root and tip heights;
- every ring's radius and height.

That is about a thousand numbers, where the free run has about a hundred thousand columns. The map from parts to columns:
- each part covers the columns within its width, with a soft edge of about 1.5 mm, so a moving part changes the columns smoothly;
- a column's height is the tallest part over it (a smooth maximum);
- a column covered by no part holds nothing;
- a column under 8 mm holds nothing (the least member).

From the columns on, the chain is today's: the casting filter, the voxels, the model, GCMMA, and the binary check at the end. The objective and constraints are those of step A.

What the optimiser can do:
- slide or shift a part;
- turn it, as its nodes move;
- stretch it;
- grow it, or shrink it until it vanishes.

It cannot change which nodes a member joins. That move, like adding a member, is the agent's (§3.6).

The bounds:
- a node moves at most about 30 mm from its start in a run, and stays on its face;
- the heights stay within the family's range;
- the rings' radii stay within their range.

### 3.5 Step D: the recipe, the CAD and FE

The parts that survive, with their sizes, are the recipe, written in `param_cad.py`'s form:
- each member a plate with a rounded top, from its root height to its tip height;
- each ring a collar.

From the same recipe:
- FE judges the mesh drawing: the parts as rounded plates and collars on the exact, filleted shell, the drawing that meshed in the night;
- `param_cad.py` builds the STEP, with its fillets and draft.

The two masses are checked to agree within 2 %. Then come the grade, castability, the pictures beside production's photos, and the Designs page as a new flow ("E: parts refined from the free run").

### 3.6 What the agent decides between runs

After each run the agent reads:
- which parts vanished, moved or grew;
- which hit their bounds (a part at full height where a line binds needs a partner);
- the lines that bind;
- the modes.

Its moves, each logged (campaign `lop26` on the Campaigns page):
- a member added between two nodes, or split at a new node;
- a grid swapped for a wheel on a panel;
- a family's thickness changed;
- a free run at another budget, read again.

Different free runs and different readings give different designs: approach 2's diverse population.

## 4. The evidence, and the risks

- **The free run needs no paint.** With the least member, `a2_c1` met the stiffness and the tilt at 5.49 kg (39.0 µm, tilt 0.90 ×). It made lumps instead, and the lumps sit where bosses, links and towers belong.
- **Sized production parts pass.**
  - The bore experiment's ties: 5.73 kg, every graded line.
  - `ln_6` (production's forms with free heights, drawn `prod9_asis`): 7.71 kg, 41.8 µm, tilt 0.81 ×; one mode 0.4 Hz inside the 3 % band of s1's order.
- **The night's nearest try failed, for reasons Refine removes.** Ribs and rings read from a painted free run's skeleton, sized in height only, could not hold the cover's seats (`sf_5`: the beds 1.40 × their line at 7.79 kg). Three things differ now:
  - the free run has no paint, so its skeleton is of real members;
  - the parts move;
  - towers and fins hold the seats on their tubes.
- **One height for a whole form cost twice the metal** (`ln_5`: 9.25 kg). So every member has a root and a tip height, and broad metal becomes several members.
- **Moving parts and the model.** fastcae's moving plates (20 September) were shelved for two reasons. Moved plates could not be built as CAD. And the voxel model overrated them: it claimed 56-58 % gains, while built and solved, one was better, three worse and one unbuildable. Here every position is castable (the height field) and drawable (plates and collars), but the overrating can remain. The factor of safety stays, the binary check closes every run, and FE judges every design.
- **The grid limits the rib** to 8 mm (§2.3).
- **The modes stay open.** Every design so far has a mode by s1's order. FE reports them after each run, and the agent steers.

## 5. The steps (LOP-26), each with its check

1. **The part model, `parts.py`.** Nodes (fixed, sliding round a circle or along an edge, free), members, rings; the map onto the height field's columns, with the soft edge, the smooth maximum and its derivatives. **Check:** the derivatives against central differences (10⁻⁶), on positions and heights; a synthetic layout pictured.
2. **The reading, `refine_read.py`:** the free run's members into parts (§3.3). **Check:** the parts hold at least 90 % of the free run's metal on each face and its mass within 10 %. They are pictured on each half, in plan (the free run's heights under the parts, coloured by family) and in 3D, beside production's photos. **This is the first thing the engineer sees, before any optimisation.**
3. **The optimiser over parts** (`topo_free.py --parts <file>`, `topo.Voxels`' height mode taking the parts' map): one run from `c1`'s reading at 5.5 kg. **Check:** it settles; its binary check is within 10 % of its lines; the parts that moved, grew and vanished are pictured.
4. **The drawing and the judgement:** the recipe drawn as a mesh for FE and by `param_cad.py` as a STEP. **Check:** the masses agree within 2 %; FE, the grade, castability, and the pictures beside production's; the Designs page.
5. **The agent's moves** on the result, logged as `lop26`.

Steps 1-4 take about a day, with a picture after steps 2, 3 and 4. I build them in this session, one heavy job at a time.

## 6. Kept for later

- **Grow:** ribs added step by step from the hard points, where they help most.
- **Shuffle:** many parts scattered and moved from scratch.

Both build only from the same library and could follow Refine as a second source of layouts.
