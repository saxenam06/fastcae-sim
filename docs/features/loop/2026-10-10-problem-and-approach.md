# The problem and how we are solving it

*10 October 2026, for the engineer. Where the work stands; the numbers are FE's unless said.*

## What we want to achieve

A housing for an EV two-stage reducer, designed from your requirements, sand cast in two halves, and proved by FE. It must:
- hold every bearing seat within its misalignment line in peak drive and peak reverse;
- move its bearing beds no more than the reference housing (52 and 138 µm);
- keep its modes 3 % from the gear-mesh orders;
- weigh no more than the reference, 7.73 kg.

The tools compute every derived quantity and give every verdict. The design itself, where the metal goes, is what we are searching for.

## What is fixed before any optimisation

Your requirements fix most of the housing's inside before any shape is drawn:
- **The gear train:** from the gear data, the load tool (GBX) computes the shafts' positions (the centre distances), the ratio, and the shaft diameters.
- **The bearings:** their sizes from their life at peak torque, their positions along the shafts as a stack of widths and gaps, and every bearing's reaction in both load cases.
- **The volumes:** from these come the gears', shafts' and bearings' volumes, each with its clearances (PLT-8), inside your installation envelope.
- **The cavity:** the room each part needs, one cup per half, open toward the joint.
- **The wall:** we fixed the wall round that cavity at the contract's least wall of 4 mm, everywhere, as a skin the optimiser cannot remove.
- **The interfaces, also fixed:**
  - each bearing's seat ring;
  - the seals' bores;
  - the motor's flange (its ring, spigot and six bolts);
  - room kept clear for the motor beyond its flange, for the half-shafts' joints and at the mounts' ends.
- **The split:** the halves part between the two gear stages, at your decision of 9 October. The pull directions run along the shafts, locked by you.

**Three things were placed by our prototype generator** (`grammar4`), not by your requirements or by a tool, and they are assumptions to revisit:
- **the joint's 14 bolts,** along the flange at 80 mm pitch or less;
- **the three mounts:** columns at the outline's far points in three fixed directions (assumption A20);
- **no load through the mounts:** the motor's mass and the vehicle's accelerations are still to come from you.

## What the optimiser decides

Everything else is the optimiser's: where to place 5.17 kg of metal (the 7.73 kg target less the 2.56 kg fixed) among 71,596 free voxels of 6 mm in the package, outside the cavity and the kept-clear spaces. That covers the struts, plates, bridges and thickened walls, and the connections to the seats, bolts and mounts.

**Its objective:** the worst bearing seat's misalignment as the grade measures it, every seat in both load cases. Misalignment here is the seat's tilt against its shaft's line plus the shaft's own lean.

**Its one manufacturing rule:** every column of metal must run in one piece from the joint outward, so that a two-part mould can open.

## How it is solved, and what each step taught

- **The optimiser is our own topology optimisation.** It works on voxels, with the same single-precision GPU solver as the FE judge. It solves with GCMMA, every seat and case its own constraint, with a filter and a projection that drives each voxel toward metal or air.
- **Its first fields promised far too much.** One read 0.087 × the line, but the same field made all metal or air read 5.65. Partly dense voxels had balanced each seat's two ends, which no casting can do.
- **The robust formulation** (the field must work thinned and thickened as well as nominal) and a sharper projection cut that credit. The best honest field now reads **1.43** as metal or air.
- **Its metal-or-air check now predicts FE of the drawn CAD within 5 %.** But sharper projections stopped improving the real shape: as long as a voxel may be partly dense, the optimiser spends it on tuning. So the next optimiser picks only metal or air.
- **That is TOBS** (binary variables, an integer program each step; Sivapuram & Picelli 2018). Its first run, 6 steps in 2½ minutes, took the honest number from **1.43 to 1.19**, castable throughout.
  - Removing single voxels near the seats helped most: one voxel took it from 1.32 to 1.19.
  - It stopped when its step shrank below one voxel. Its linear estimates fail when more than a few voxels change together.
  - **Its gain did not survive the drawing.** The CAD of that field reads 1.39 in FE, the same as the previous best (1.37). The drawing moves every boundary by about a voxel, which wipes out single-voxel tuning.
  - The next step is TOBS that judges every step also with each column a voxel shorter and a voxel longer, so that the drawing's tolerance is priced in.

## How a field becomes CAD, and why organic

Each half's field is turned into a solid in six steps (`outcome_cad.py`):
1. the fixed interfaces made solid, and the kept-clear spaces made empty, a margin past their true size;
2. every column filled from the joint out;
3. the surface smoothed, remeshed into even triangles and sewn into a solid;
4. the machined features cut exactly: the cavity, the bearing bores, the seal bores, the holes, the motor's spigot and the bolt seats;
5. a bolt kept only where the body holds its boss;
6. each half checked as one valid solid that meshes.

**We draw the field as it is because the field is the optimiser's answer.** Every attempt to read it into parametric features lost most of what the optimiser placed:
- choosing the generator's ribs, traced ridges, or terraces on the generator's body;
- those designs scored 6.4-7.1 × the line, and in your words still looked "like the generator";
- the organic drawings score 1.37-1.69.

Generative-design tools hand over organic outcomes too (Fusion turns its level set into smooth T-splines).

**Reading a field into editable features** (ribs, bosses and walls with dimensions) is still done by hand in industry, and every such reading pays a measured penalty (one cast reducer housing: 28.65 % promised, 7.33 % delivered). So the organic CAD comes first, as the honest value of the optimiser's shape. A parametric reading later is to be measured against it.

## Results now

| Design | Mass | Misalignment (× the line) | Castable |
|---|---|---|---|
| `grammar4`, the trade-style baseline | 7.50 kg | 6.36 | yes |
| `box1_fl`, the best hand-made | 9.92 kg | 1.40 | no: 22 closed voids |
| `outcome_robust_7.73c` | 11.53 kg | 1.59 | yes |
| **`outcome_robust_b32`**, the best drawn so far | **11.64 kg** | **1.37** | **yes** |
| `outcome_tobs`, the TOBS field drawn (in the optimiser's model, the field read 1.19) | 11.63 kg | 1.39 | yes |

None passes yet. The best drawn design is the stiffest of the loop and castable. It is still 1.4 times its line, and 3.9 kg over the mass.

## Current issues

1. **Optimisers exploit details finer than the casting.** First partly-dense voxels, then single voxels: TOBS's 1.19 in the voxel model drew as 1.39. The design must hold when its boundary moves by the drawing's voxel. The honest number at 7.73 kg is therefore still about 1.4. If a robust optimiser cannot lower it, the levers are the mass target, the layout and the load cases.
2. **The drawing adds 3.9 kg.** The wall is drawn a full 6 mm voxel where the model counts 4 mm, near-touching plates are merged, and the margins, bolt columns and joint band add more. A mass-faithful drawing is next.
3. **The mounts carry no load,** so the optimiser joins only one or two of the three, and the verdict depends on how many it joins. A load case through the mounts is your decision.
4. **6 mm voxels** (the size that keeps a step to seconds; 4 mm would cost three to four times more) make members at least 6 mm thick. Thin plates leave torn fins in the drawing.
5. **Smaller items:** about 5 % of each half reads undercut, which is the facets' scatter; 70-100 cm² of each half lies under the 4 mm least wall; and one mode sits 3 % from the second mesh's order.
