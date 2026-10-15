# The rib-direction field: ribs and brackets from the load, without a library (LOP-34)

**The engineer, 16 October 00:50 (IST): "lets build this".** Agreed in conversation from 15 October 22:00: the members' shapes (wobbly, uneven, stretched, the screenshots of `baseline2_lw8` drawn smooth) are not cured by another representation of metal-or-not (cubes, B-splines, NURBS) or by smoothing afterwards; nothing in such an optimisation rewards order. fastcae's way (patterns drew candidate ribs, CP-SAT chose which stand) and Refine's (LOP-26: straight parts read from a free run) are libraries, which the engineer refuses: "we came to this repo to unleash creativity and innovation".

**Updated:** 2026-10-16 01:50 by Claude

## 1. The idea, plainly

The optimiser stops asking, cube by cube, "metal or not?". At every point of the housing's walls, and of the room round each mount, it answers three questions:

1. **Which way should ribs run here?** A direction, θ.
2. **How much rib metal is needed here?** A share ρ, from 0 (none) through thin ribs and thick ribs to 1 (solid).
3. **How tall should the ribs stand here?** A height h, as the height fields now.

Each is a smooth field (B-splines on coarse knots). The optimiser answers them by the same physics as now: the least metal with the tilt, the beds and the modes held. A rib does most where it lies along the load, so the directions turn to the load's paths, as Nervi's ribbed floors follow their principal moments.

**In the model,** each cube of the rib layer has the stiffness of thin plates standing along the pull and running along θ, at share ρ: stiff along θ and along the pull, nothing across. **In the drawing** (de-homogenisation), ribs are drawn along the directions, evenly spaced (one spacing s, a manufacturing value), each ρ·s thick and h tall; a stripe pattern on a fine plan grid (the phase of a complex field whose stripes follow θ at the spacing; it lets ribs end and branch where the directions converge). The ribs are straight where the load runs straight, of one width where ρ is even, and never wander, because one point has one direction. A rib's thickness is a number, not a count of cubes, so production's 3-6 mm ribs are reachable.

## 2. The patterns come from the load

- round a bearing, the load spreads out: spokes;
- at a mount, the load gathers into the lug: webs fanning into it, ρ solid at its eye (the boss) — **a bracket is where the directions converge on a lug**, and its webs carry on as ribs along the wall;
- between two hard points, the load runs straight: a straight rib;
- a wall loaded two ways: two rib families crossing, a lattice; a third family gives triangles.

## 3. How it differs from fastcae

| | fastcae | the field |
|---|---|---|
| where ribs can be | only on lines our patterns drew | anywhere, at any angle |
| who chose the shapes | us, by writing the patterns | the load |
| what the optimiser does | switches ready-made ribs on or off | sets direction, amount and height everywhere |
| thickness, height | fixed (25 mm), heights by rule | chosen place by place within the rules |
| the rules | a filter on candidates | limits held while the shape is found |
| brackets | not covered | the same field |

The same: fastcae's rules (thickness range, height at most k × thickness, never higher than the wall or boss met, ends meeting walls at 60° or steeper, spacing), and the building block is a plate along the pull plus solid where ρ = 1: a limit on form (no hollow tubes, no bulges), not on layout. The test of a library: can the optimiser make a rib at a place or angle nobody listed? Here, yes.

## 4. Limits, known before building

- **Few ribs per panel** (5-8): the smeared model is approximate; the drawn ribs are judged on a fine grid, and later by FE.
- **Where ribs converge** (a lug, a boss) the stripes pinch: the drawing's hard part.
- **Side walls** need the field on the walls' surfaces, and side-wall ribs that do not run along the pull need a slide: the process profile's choice, the engineer's.
- **Mount loads:** a bracket is as good as its loads; each mount carrying its share (weight, bump, side) is a load-case change, the engineer's.
- **The real optimiser** needs each cube's own direction-dependent stiffness on the GPU (its assembly today is one matrix scaled per cube).

## 5. The toy (LOP-34's first step), CPU only

A flat end wall, 4 mm, 200 × 160 mm, with a bearing's boss (its bore rigid with the bearing's centre, where the load acts, offset from the wall so the wall bends), bolt bosses round the edge held, and a mount lug held at one corner; a band of 24 mm above the wall for the ribs. Two load cases at the bearing. The objective: the least compliance at a given rib mass (the toy's; the product's is the least mass with the lines held). Compared at the same mass with today's method on the same toy (free columns of metal, one height a column).

**Done when:**
1. the model's derivatives agree with central differences (10⁻⁶);
2. pictures: the directions, the ribs drawn, beside the free columns;
3. the drawn ribs and the free columns judged on one finer voxel grid at equal mass: which is stiffer, and by how much; and how far the smeared model was from its drawing.

Then, if the ribs hold their own: the field on a wall's surface (a side wall meeting an end wall at an edge, a lug in its room), then the housing's cover in the real optimiser.

Code: `prototypes/rib_field/` (a prototype: nothing in `src/` imports it; outputs in `data/rib_field/`); its README has the commands.

## 6. The toy, measured (16 October, the cloud session's CPU)

The set-up: 4 mm cubes, 13,104 of them (the wall one layer, the band six), 1,670 design columns, 42,750 unknowns; 0.25 kg of placed metal; the two load cases' compliance minimised by MMA (our GCMMA's step), 80 iterations each.

| Design | The model | FE of the drawing (1 mm, TET10) | Tilt (FE) | Placed metal (drawn) |
|---|---|---|---|---|
| **The field**, two crossing families, ribs at most 7 mm thick, 24 mm apart, at most 4 × their thickness tall | 25.2 N·mm | **28.3 N·mm** | 0.046 mrad | 0.231 kg |
| **Today's free columns**, with our optimiser's lump rule (`--max-member 16`, p 40) | 13.5 N·mm | **15.2 N·mm** | 0.028 mrad | 0.240 kg |
| The field, ribs up to 12 mm (`RIB_T_MOST=12`) | 21.1 N·mm | **22.4 N·mm** | 0.044 mrad | 0.238 kg |
| **Step 2:** thickness by place (12 mm at a boss's, bolt's or the lug's edge to 6 mm 30 mm away; `--by-place`) | 22.7 N·mm | **26.5 N·mm** | 0.049 mrad | 0.221 kg |
| **Steps 1 + 2:** with the end rules (`--by-place --ends`; drawn with the gate) | 26.8 N·mm | (running) | | |

- **The method works end to end:** the field draws ribs (spokes from the bearing's boss to the bolts and the lug, a second family crossing them), nobody laid them; the derivatives agree with central differences within 3·10⁻⁶ (`gradcheck.py`).
- **The smeared model is fair:** it reads 12 % stiffer than FE of its own drawing, as it does for the free columns (12 %).
- **At the same mass the ribs are 1.9 times softer than the free columns** (tilt 1.6 times); **allowed 12 mm, 1.5 times** (tilt 1.6 times): the thin-rib cap costs about a fifth, the rest is open. The free columns pile metal into full-height stepped wings from the boss to the three nearest bolts (the lumpy look); both rib families sit at their 7 mm cap round the boss, so the field wants more metal there than thin ribs hold, and spreads it.
- **What the drawing still lacks:** ribs end in the open, short fragments stand alone, and some branch; the end rules (an end on a wall or a boss, steeply) and a least length are not in yet.
- **Learned on the way:** the strains' best direction flips ribs stiff one way only (stiffened along it, the strain moves across), so 95-99 % of the directions turned their full step every iteration; as MMA's own variables (a smooth B-spline turn from the strains' start) they settle (median turn 0.4° at the end). One family alone is far worse than two (two load cases). At 8 mm cubes the 4 mm wall rounds to no layer: judge 4 mm runs only. The 0.5 mm drawing's FE mesh (2.3 M unknowns) ran the container's 15 GB out; judge at 1 mm.

## 7. fastcae's rules, as this model holds them (the engineer, 16 October: "implement fastcae rules as applicable for this model ... we still should be able to reveal various ribs, patterns, tapered ribs and brackets etc as observed and built by humans in production housing")

`prototypes/rib_field/rules.py`, `toy.py ... --fastcae`; every rule a GCMMA constraint with its derivatives checked (`gradcheck.py 8 --rules --fastcae`: within 5·10⁻⁶), or a rule of the drawing. The values are scaled from fastcae's 25 mm ribs to ours, for the toy; the product's take the engineer's word.

| fastcae's rule | In the field | Value (toy) |
|---|---|---|
| thinnest / thickest | thickness by place: thick at a boss, a bolt or the lug, thin away; thinner not drawn | 12 → 6 mm over 30 mm; 3 mm least |
| tallest_ratio | a rib at most so many times its thickness | 5 |
| never above the boss it grips, flush_mm | the height capped near each hard point under its top; the bolts' bosses a flange's height, so ribs **taper down** to them | 3 mm under; bolts' bosses 12 mm |
| least_end_mm (twice the root fillet) | a rib under it not drawn | 8 mm |
| ends glued to walls | the thickness constant along a rib away from the anchors: ribs start and stop only at a boss, a bolt, the lug or the edge (a housing's side walls) | root mean square slope 0.03 mm a mm, 12 mm reach |
| (no cliffs; tapers allowed) | the height's slope along a rib near its worst: tops slope and taper, never step | 0.5 mm a mm (p-norm 8) |
| arrive_deg | near an anchor, ribs radial (spokes, ends arriving square) or along its face (rings), never oblique; the two families at 90° make a spoke-and-ring pair | 30-60° penalised |
| bend_mm | the rib lines' curvature near its worst: straight ribs unless the load turns | radius 40 mm |
| sand_mm, cross_deg | by construction: one spacing; the families cross at 90° | 24 mm |
| shortest_ratio | the drawing's gate: shorter ribs and pieces touching nothing not drawn | 20 mm |
| draft_deg, tip_mm, fillet_edge_mm, fillet_root_mm | the drawing (`draw.implicit`): one smooth solid, drafted faces, rounded tops, filleted roots | 1°, 2 mm, 3 mm |

**What the rules leave free, so production's variety can appear** (none of it is laid down; each appears where the load calls for it): spokes from a boss and rings round it (the arrival rule's two allowed ways), parallel ribs and grids (one or two families), ties from a bore to a bolt or the lug (the end rule's anchors), tapered ribs (the height cap by place and the slope rule), thick roots (thickness by place), and webs converging on the lug. Not yet: triangles (a third family), brackets standing off the wall and side-wall lattices (the field on a wall's surface, next).

## 8. Next (for the engineer)

1. **A third family** where the load comes from several ways (triangles).
2. **The field on a wall's surface:** a side wall meeting an end wall at an edge, a lug standing off it in its room: brackets as webs from the lug down to the walls, side-wall ribs and lattices (with the process profile's word on slides).
3. **The comparison's fairness:** the free columns keep wide stepped wings under the lump rule (the look the engineer refuses); a fair target for the ribs is their stiffness at the same mass, or the mass at the same stiffness, with the engineer's call on how much stiffness the production look may cost.

