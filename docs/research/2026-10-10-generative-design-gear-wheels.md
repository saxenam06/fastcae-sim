# Generative design of gear bodies, read for our housing

*2026-10-10, for LOP-17 (the generative campaign). The engineer brought the paper at 02:07: "They have not done it for housing … they have used some generative design optimization … They were able to see very interesting designs … Now I want to design something which is physics aware."*

**The paper:** Virostko M., Maláková S., Kopas M., Mantič M., Kuľka J., Krenický T., Lopot F., Petr K., *A Case Study of Applying Generative Design to Gear Wheels*, Materials (Basel) 19(3):565, 1 February 2026. Open access: <https://pmc.ncbi.nlm.nih.gov/articles/PMC12898024/>. Read through the page's text on 10 October; the figures were not seen.

## What they did

- **The part:** a spur gear body (71 teeth, module 2.5, 20°, face 50 mm, bore 55 mm). The teeth themselves were kept unchanged.
- **The tool:** Autodesk Fusion 360's generative design, with FE inside the loop, and a separate FEM check of each chosen design afterwards.
- **Preserved geometry:** the hub round the bore, the rim under the teeth (at least 3.5 × the module thick), the tooth profiles, a least hub thickness.
- **Obstacle geometry:** where no material may go (assembly, function). **Starting shape:** the solid blank.
- **Loads:** three strategies compared:
  - one tooth at 1,000 N, each tooth in turn;
  - the torque shared among the teeth in mesh;
  - every tooth loaded at once.

  Each force is normal to the flank at the contact. The bore's faces are held. They found the single-tooth case alone not enough. Either every tooth at once, or a study per tooth, is needed.
- **Objective and constraints:** least mass, under a safety factor, a largest displacement, modal frequencies and the teeth's deflection. A tooth's stiffness is force over deflection at its tip.
- **The manufacturing route is a design variable.** Each route is a set of constraints, not a step after:
  - **Additive** (PA12-GF30, CF-PA, POM): organic, rib-like structures along the load paths; the most mass taken out (37.5-45.7 % against the solid body), but more deflection.
  - **Machining** (3-axis and 5-axis; S45C, SUS420J2, SCr415, 7075): thicker webs, round lightening holes; stiffer. The two machining routes gave nearly the same result, so the dearer 5-axis bought little.
  - **Casting** (S45C, SCr415, 7075): metal kept round openings, least walls, "more conservative geometries with locally reinforced regions" and smooth transitions.
- **Variants within a route:** 10 or 6 lightening holes, with or without preserved material round them. Without it they did better, because preserved material "limited the optimisation space without a proportional increase in stiffness".
- **Many outcomes, then filtered:** the tool gives many designs, some unusable. They dropped the asymmetric, single-axis-symmetric and impractical ones, and kept those that are manufacturable, mechanically feasible and economical.
- **Then rebuilt and proved:** the kept outcomes were redrawn as parametric CAD and checked again by FEM. They were compared on volume (% of solid), the largest tooth deflection, tooth stiffness and safety factor. The worst case is a tooth over a lightening segment.
- **Limits they state:** numerical only, no tests; static only, no fatigue or dynamics; cost not counted; the materials are typical of each route, not the best match.

## What it means for the housing

The interesting shapes came from the route, the loads and the variants fed to one physics-driven generator. Nobody drew them. That is the step we skipped tonight: we drew shapes (the style presets: varied, but not physics-aware), then read one field mechanically.

| The paper | Our housing (LOP-16, LOP-17) |
|---|---|
| Preserved: hub, rim, teeth | Frozen: each bearing's seat ring, the cavity's skin (one cup per half), the motor's ring, the mounts (`topo_free.py`) |
| Obstacles | Kept clear: the gears' rooms with their clearances, the motor beyond its flange, the half-shafts' joints, the mounts' bolts |
| Starting shape: the blank | The packaging space (PLT-8) |
| Loads: one tooth, the torque, all teeth | Peak drive and peak reverse through the bearings (the chain's reactions); the motor's mass and accelerations are still to come from the engineer |
| Least mass under safety, deflection, modes | The worst seat's misalignment over its line at a given mass, by GCMMA (`misalignment_bound`); stepping the mass (6, 7.73, 9 kg) traces the least mass that meets the line |
| Route as a variable: additive, machining, casting | `--route cast` (a two-part mould split at the joint: each half's columns one interval along the pull) against `--route free` (additive) |
| Variants: holes, preserved material | Budgets; a stage-2 band; the skin's thickness; joint glued or bolted |
| Filter the outcomes | Keep those that settle black and white and meet the line; drop those that hang a seat on a strut, or are lopsided |
| Rebuild as CAD, then FEM | Read each kept field like a designer, from views, into castable features; FE (`fe.py`, TET10) and the castability check on the CAD |

**Our first campaign** (LOP-17, launched 02:11 on 10 October, `prototypes/first_loop/generative_queue.sh`) has five runs in turn: cast 7.73 kg, free 7.73, cast 6, cast 9, free 6. Each runs 200 iterations at 6 mm.

**Two lessons carry over directly:**
- the single-load lesson: all the cases at once, every seat in both cases, as the bound formulation already does;
- preserved material costs optimisation room: freeze only what the contract fixes.
