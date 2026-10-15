# The rib-direction field's toy (LOP-34, a prototype)

Ribs and brackets from the load, without a library: at every column the optimiser chooses which way
the ribs run, how much rib metal and how tall; the ribs are drawn along the directions at one
spacing. [The method](../../docs/features/loop/2026-10-16-rib-direction-field.md). Nothing in `src/`
imports this folder; its outputs go to `data/rib_field/` (git ignores it). It runs on the CPU (the
cloud session's venv: numpy, scipy, pypardiso, scikit-image, pymeshlab, manifold3d, tetgen,
pyvista), and imports `zenryx` from `src/` for the material, the rigid couplings, the lump rule, the
MMA step and FE's meshing and TET10.

| Script | What it does |
|---|---|
| `model.py` | The hexahedra, a cube's stiffness from 36 basis matrices, the rib's laminate stiffness turned to its direction (and its derivative), each cube's energy tensor |
| `toy.py [iterations] [families] [label] [--voxel=<mm>] [--no-columns] [--no-lump]` | The toy (a flat 4 mm wall, 200 x 160 mm, a bearing's boss, 7 bolts and a lug held, two load cases at the bearing's centre) and its two runs at one mass: the field (`Field`: rho and the height's share per family as B-splines, the directions the strains' best at the start then MMA's own variables as a smooth turn) and today's free columns (`Columns`, with our optimiser's lump rule); MMA (our GCMMA's step) for both. `RIB_T_MOST`, `RIB_SPACING` set the thickest rib and the spacing |
| `rules.py` | The rib rules held while the field is found (`toy.py ... --by-place --ends`): thickness by place (12 mm at a boss's, a bolt's or the lug's edge to 6 mm 30 mm away) and the end rules (a rib's thickness and height nearly constant along it, except within 12 mm of a hard point or the plate's edge: two GCMMA constraints) |
| `gradcheck.py [voxel mm] [--rules --by-place --ends]` | The derivatives against central differences (compliance and mass by rho, height share and direction; the columns' compliance; with `--rules`, thickness by place and both end rules) |
| `draw.py` | The de-homogenisation: a stripe pattern along the directions (the smallest eigenvector of a connection energy on the 0.5 or 1 mm plan grid), each rib rho x spacing thick and h tall; the free columns as left; both as height maps and watertight meshes |
| `judge.py <label> field\|columns [--fine=<mm>] [--gate]` | FE of a drawing: our FE's meshing ladder (`fe.mesh_tetgen`), TET10, the bore rigid with the bearing's centre, bolts and lug held, PARDISO in double precision; `<label>_<kind>_fe.json`, with the ribs' census (free ends: a rib's end over 3 mm from a hard point or the edge) and, with `--gate`, the drawing's gate (pieces touching no hard point or edge, and ribs under 20 mm, not drawn) |
| `fields_view.py <label> [<columns label>]` | A run's fields in plan: each family's thickness and direction, its height; the free columns' heights |
| `pictures.py <name> ... \| --sheet <out> <title>:<name> ...` | A drawing seen along the pull and from an oblique camera; a sheet of designs with their FE numbers |

The 4 mm run of both: `toy.py 80 2 v4f2` (about 8 minutes), then `judge.py v4f2 field --fine=1.0` and
`judge.py v4f2 columns --fine=1.0` (2-3 minutes each; the 0.5 mm drawing's mesh, 2.3 M unknowns, ran
the cloud container's 15 GB out of memory). At 8 mm the 4 mm wall rounds to no layer: judge 4 mm runs
only.
