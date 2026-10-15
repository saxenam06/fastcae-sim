# The rib-direction field on our housing (LOP-34, a prototype)

The toy's method (`prototypes/rib_field/`, [the method](../../docs/features/loop/2026-10-16-rib-direction-field.md))
carried to the housing, in this folder only, so the running pipeline in `src/` is not touched (the
engineer, 16 October). **Where the work stands and what is next:
[the housing's page](../../docs/features/loop/2026-10-16-rib-field-housing.md).** Outputs in `data/rib_housing/`.

Run with the product on the path and, in the cloud container, the GPU stand-ins:
`PYTHONPATH=checks/support/gpu_on_cpu:src python prototypes/rib_housing/<script>`.

| Script | What it does |
|---|---|
| `housing.py` | The set-up from the contract by the product's own stages: the layout record (`housing.layout.write`), the voxel model (`setup.build`, `voxels.Voxels`) with the final recipe's arguments; the column groups (a half's run of columns along the pull) |
| `ribmodel.py` | The product's model with every free cube a rib cube (the toy's laminate, plain hexahedra in the product's corner order); the fixed cubes the product's element, assembled once; PARDISO; every seat's tilt and bed (the product's measures) and their derivatives by every rib cube's stiffness |
| `field.py` | The rib-direction field over the columns: per group two families (thickness and height shares as B-splines), the directions a smooth turn from the strains' start; thickness by place at the hard points (bores with their rings, bolts' bosses, mounts' lugs); fastcae's rules (`prototypes/rib_field/rules.py`) per group with the housing's anchors |
| `optimise.py <label> [iterations] [--voxel=<mm>] [--start=<npz>]` | The product's problem (least placed metal, every tilt and bed at 1/1.5 of its line, the peak drive) with the rules, by MMA; state every 5 iterations |
| `gradcheck.py [voxel mm] [--solid]` | The derivatives against central differences (5 mm by default; `--solid` a solid zone's variables only) |
| `drawrib.py <label> [<design>] [--voxel=<mm>]` | The state drawn by the product's drawing: written as a run of the product's format (`rib_<label>`), the members' signed distance replaced by the ribs' (stripes per group and family) and the solid zones' columns |
| `setup_probe.py`, `model_probe.py` | The set-up's size; one analysis's time and memory |
| `parity_probe.py` | The rib model against the product's on the reference's own field (`ref/lop33`'s `baseline2_lw8`): within 1-4 % |
| `boss_probe.py [voxel mm]` | What the solid zones (bosses and mounts' corridors) buy: the lines with ribs alone, ribs and full zones, the zones alone, every cube solid |
