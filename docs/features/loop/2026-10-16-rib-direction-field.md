# The rib-direction field: ribs and brackets from the load, without a library (LOP-34)

**The engineer, 16 October 00:50 (IST): "lets build this".** Agreed in conversation from 15 October 22:00: the members' shapes (wobbly, uneven, stretched, the screenshots of `baseline2_lw8` drawn smooth) are not cured by another representation of metal-or-not (cubes, B-splines, NURBS) or by smoothing afterwards; nothing in such an optimisation rewards order. fastcae's way (patterns drew candidate ribs, CP-SAT chose which stand) and Refine's (LOP-26: straight parts read from a free run) are libraries, which the engineer refuses: "we came to this repo to unleash creativity and innovation".

**Updated:** 2026-10-16 00:58 by Claude

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
| The field, ribs up to 12 mm | (running) | | | |

- **The method works end to end:** the field draws ribs (spokes from the bearing's boss to the bolts and the lug, a second family crossing them), nobody laid them; the derivatives agree with central differences within 3·10⁻⁶ (`gradcheck.py`).
- **The smeared model is fair:** it reads 12 % stiffer than FE of its own drawing, as it does for the free columns (12 %).
- **At the same mass the ribs are 1.9 times softer than the free columns** (tilt 1.6 times). The free columns pile metal into full-height stepped wings from the boss to the three nearest bolts (the lumpy look); both rib families sit at their 7 mm cap round the boss, so the field wants more metal there than thin ribs hold, and spreads it.
- **What the drawing still lacks:** ribs end in the open, short fragments stand alone, and some branch; the end rules (an end on a wall or a boss, steeply) and a least length are not in yet.
- **Learned on the way:** the strains' best direction flips ribs stiff one way only (stiffened along it, the strain moves across), so 95-99 % of the directions turned their full step every iteration; as MMA's own variables (a smooth B-spline turn from the strains' start) they settle (median turn 0.4° at the end). One family alone is far worse than two (two load cases). At 8 mm cubes the 4 mm wall rounds to no layer: judge 4 mm runs only. The 0.5 mm drawing's FE mesh (2.3 M unknowns) ran the container's 15 GB out; judge at 1 mm.
