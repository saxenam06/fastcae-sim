# CAD from a free optimisation: the problem, and a proposal

**Date.** 11 October 2026, 13:38, for the engineer's review; the proposal revised at 14:08 after three outside proposals. **Asked by the engineer** (13:28): rewrite the problem without its solution, under two headings, the proposal only under the second. The point that changed it: fastcae could guarantee its CAD because its rib library was built and checked in advance, and a free optimisation has no such library.

**Read with:** [the loop's page](../loop/status.md) (LOP-23), [the morning's record](../loop/2026-10-11-record-morning.md) (every trial with its numbers), [the agents' role](2026-10-11-the-agents-role.md) §9 (the levers a campaign varies).

## Problem

**What zenryx does.** zenryx designs a cast housing from requirements. The engineer gives the gearbox's interfaces, loads, package, targets and one manufacturing process. Here that process is sand casting in a printed mould: each half pulled along the shafts, 0° draft, 4 mm least wall. Tools compute every derived quantity and give every verdict; agents choose the structural hypotheses. The first family is a two-stage EV reducer housing.

**The flow today.** One design takes about 2 minutes at 6 mm voxels and about 6.5 at 4 mm:
1. Set-up: the contract fixes the exact wall, split flange, bolt bosses and mounts.
2. Topology optimisation (GCMMA; 1 minute at 6 mm, 5 at 4 mm). It maximises stiffness with every bearing's tilt and bed held as constraints. It is free, with no patterns put in, and casting rules shape it: each column of metal runs in one piece from the split, members are at most 8 mm thick, and metal stays within 24 mm of the shell.
3. Drawing: the field contoured by marching cubes, then joined to the exact shell and cuts by watertight mesh booleans (12 s).
4. FE on the GPU, with castability checked beside it (1-1.5 minutes).
5. The grade.

**What it achieves.** The optimiser finds clear load paths of its own: rings round the bores, fans of members on the end faces, links between bosses, arms to the mounts. As meshes, its designs pass every graded line. For example, `outcome_env24f_6.5kg` weighs 7.24 kg against the 7.73 kg reference, its bearing beds move 33.5 µm against 52.2, and its worst tilt is 0.71 of its limit.

**Where it breaks: exact, editable CAD.** The passing designs exist only as meshes. They are lumpy at the voxels' scale and have no features to edit, and the mesh drawing adds 0.5-1 kg the optimiser never placed. Every attempt to build them as CAD features has failed somewhere:
- ribs crossing at random angles, running into the floor and walls, or into spaces that must stay clear (the brackets' rooms, the seal exits);
- ribs taller than the bosses they meet;
- slivers where a rib grazes a wall or a cylinder, which FE's single-precision solver refuses;
- outlines crossing themselves, and booleans the kernel (OCC) refuses, so parts drop out silently (once two of the three mounts);
- broad members read as thin ribs, losing up to half the metal;
- a boss dropped because it sat on two floor levels at once.

The best exact CAD kept 58-73 % of the optimiser's metal, and FE failed it where the mesh of the same field passed. Each try costs a 5-10 minute cycle.

**Why it is harder than in fastcae.** fastcae built ribs from a library, and every rib in it had been built and checked before any design used it. The surfaces a rib could stand on, its paths and its patterns were known in advance, and only ribs that built were admitted, so any combination it chose was buildable. The free optimiser has no catalogue. It can return any arrangement: members at any angle and width, merging, branching, fanning, stepping. Each design is a geometry nobody has built before, so there is nothing to check in advance, and a fix that cures one design does not carry to the next.

**What the CAD must do,** for every design the optimiser returns, without a person, in minutes:
- build every time: a valid solid, with no part silently lost;
- keep the optimiser's metal where it put it, so that the stiffness survives;
- hold the rules: exact where the contract fixes it, castable along the pull, walls at least 4 mm, nothing in a kept-clear space, no rib taller than the boss it meets, no slivers;
- look like a production casting: ribs 4-5 mm thick, fillets, clean lines;
- stay editable, so that sizes and shapes can be optimised after.

**The question:** how can the CAD be assured to build for any design the free optimiser produces, when its shapes cannot be known in advance?

## Solutions

**The options, and whether each assures the build:**
1. **Read the field into features and fuse them in the kernel** (flow C; fastcae's builder). Every new arrangement can meet a new kernel failure, and fixes don't carry over: not assured.
2. **Put features into the optimiser** (patterns, or movable components). Buildable by construction, but it constrains the creativity: ruled out (the engineer, 13:07).
3. **Smooth the field and fit surfaces** (subdivision or NURBS). The mesh always builds, but fitting surfaces to a complex topology is fragile, and the result has no features to edit.
4. **Model the solid implicitly** (signed distance fields). It always builds, gives fillets for free and is parametric, but it is not a B-rep, so it is not the exact CAD asked for.

**Proposal: flow D, the relief route. Compile each half from a plan with heights.**

*Why this can be assured.* With 0° draft and each half pulled along the shafts, every face of a half is a wall along the pull or a top across it. Every bore, hole, exit and bracket's room runs along the pull too. The optimiser's casting rule makes each column's metal one run from the split, or from the wall it stands on.

Measured across the 34 fields on today's set-up (14:05), only 98 of 185,845 columns (0.05 %) hold a second run outside the mounts' lugs, at most 0.044 kg in any field. So whatever pattern the optimiser invents, each half is a height map over its plan, with the lugs as the one exception. And any height map can be built:
- its outlines are 2D shapes, and 2D operations in integer arithmetic always compute;
- its solid is vertical walls and flat tops.

fastcae's guarantee came from checking every pattern in advance. Here it comes from a representation in which every admissible design is buildable.

*The steps:*
1. **Certify the field.** Every pull column in each half must hold one run of metal from the split or the wall. The few that don't are filled (the mould needs them filled anyway), or the field is returned with the column and its runs. The mounts' lugs are declared contract geometry.
2. **Three bands from the field:**
   - must-keep: the members shrunk 1 mm a side;
   - may-keep: the members grown 1 mm a side;
   - forbidden: the keep-outs and their clearance.

   The CAD must contain the first and stay inside the second, so it can neither lose a broad member nor add a kilogram unmeasured.
3. **The exact shell, built and checked once per contract and hypothesis:** the wall, flange, bosses, mounts and every cut. It is known before the optimiser runs, as fastcae's anchors were.
4. **The relief in plan.** Each 4 mm height step is one region, faired between the bands, all in one planar arrangement (manifold3d's CrossSection: Clipper2, integer coordinates). The rules act here:
   - members at least the least wall wide;
   - keep-outs clipped with their clearance;
   - round every bore, boss and mount (rule zones, the reviews' "attachment collars"): an outline merges into the circle or keeps 1 mm off it, crosses it at a clear angle, and stays no higher than the boss;
   - each region buried 2 mm into the wall it stands on, and tops kept off the shell's faces.

   The agent reviews any rule that cuts a load path, and records what it decided.
5. **One solid, one join.** The relief is compiled as one solid: each region a flat top, each outline a vertical wall, every shared edge made once. It joins the exact shell in one fuse, whose contacts the rules make clean crossings, and then the exact cuts are made. The shell's walls are true cylinders, which polygon cells cannot share edges with exactly. If the fuse ever fails in the corpus, the shell moves into the same complex.
6. **A certificate on every design:**
   - one solid per half;
   - every protected face present and unchanged;
   - OCC's validity check, and a STEP round trip;
   - the bands held, and the keep-outs empty;
   - single pull runs, and castability;
   - FE on the CAD's own mesh.

   A design that fails is returned with what failed and where, and flow B's mesh judges the field meanwhile. Nothing is dropped silently.
7. **Editable at three levels:**
   - E0, required: a valid STEP.
   - E1, required: the relief's regions and heights as parameters, the input of size and shape optimisation with FE in the loop.
   - E2, best effort: named ribs, pads and bosses read from the relief, with skeleton or loft methods.

*The order of work:*
1. Certification and bands on all 34 fields (about 1 hour; the census is done).
2. The faceted compiler, with flat tops and no fillets, on both halves of `outcome_env24f_6.5kg`, with its certificate and FE (about a day). Then the corpus: the 34 fields and perturbed copies (near-tangent contacts, narrow gaps, many-way junctions), cheap to make in 2D. To pass:
   - no silent failure;
   - every admissible field builds;
   - every rejection names its witness;
   - FE within the mesh noise of flow B.
3. Smooth tops and fillets, built into the height map before compiling (the rolling-ball fillet already works on a depth map), then fitted on the same topology.
4. E1's parameters into size and shape optimisation.
5. Agents on typed operations (certify, regularise, attach, refine, validate), under the certificate.

*For the engineer's word:* what "keeps the optimiser's metal" means in numbers. Proposed:
- must-keep: the members shrunk 1 mm a side, 100 % contained;
- may-keep: the members grown 1 mm a side;
- the mass within ±3 % of the optimiser's;
- FE within about 3 % of flow B on the same field.

*Reviewed against three outside proposals* (the engineer's discussions, 14:02):
- Two of them, an "assured reconstruction" report and its follow-up, reach the same compiler on the same casting invariant. They add the certificate, the bands, the collars, the integer 2D arithmetic and the editability levels, all adopted above.
- The third, a "structural complex" of 3D skeletons, lofted branches and junction patches, is the general route. It does not use the invariant, and its key step, building junction surfaces in general, is still research. Skeleton and loft methods are kept for E2.
- Their citations were not checked; nothing here depends on them.

*What is not known yet:*
- **Fillets and smooth tops** are the only parts that are not prisms, so they are the riskiest for the kernel.
- **Rib thickness.** The field's members are 4-8 mm wide. Ribs at production's 4-5 mm (E2) will give up some metal, which the size and shape optimisation must win back. That loss is measured on each design.
- **Solid collars.** Making the rule zones solid bosses round the bores would change the agreed set-up, so that is the engineer's call.
