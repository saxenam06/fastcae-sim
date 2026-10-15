# The rib-direction field on our housing: the plan, the state, the learnings (LOP-34)

**Read this first after a compaction or in a new session.** It is the working memory of this job.

**The engineer's brief (16 October, before leaving for the day):** "Once you are done with this test model, apply the same for our housing, and run the entire workflow from contract to optimization to drawing, and then to FE, and then to solve, and then prepare a picture with the final designs, and do that in the prototype folder so that we do not disturb the current pipeline ... Once we agree, then we will plug this into the running pipeline ... transferring the entire thought process from this test model with the rules to our production housing ... Once one entire workflow is complete, then you are done. Keep documenting the status and the learnings as you move forward."

**Updated:** 2026-10-16 02:30 (IST) by Claude, cloud session, branch `product/end-to-end`.

## 1. Where things stand (rewrite at every milestone)

- **The toy** (`prototypes/rib_field/`, [the method](2026-10-16-rib-direction-field.md)): built, judged by FE, fastcae's rules in and checked. Two rule fixes found on it (§3); the check run `f6` (every rule, the share-based end rule) running beside the housing.
- **The housing** (`prototypes/rib_housing/`, its README):
  - **Done:** the set-up from the contract by the product's own stages (`housing.py`: the layout record, then `setup.build` and `Voxels` with the final recipe's arguments; 111,482 cubes, 19,959 fixed (3.32 kg), 91,523 free, 400,176 unknowns, 9,587 columns in 4 groups: `motor_side_run1` 4,880, `cover_run1` 4,377, two small run-2 groups); the rib model (`ribmodel.py`: the fixed cubes the product's element, the free cubes rib cubes, PARDISO; one analysis with its 12 adjoints about 60 s at 4 mm, 13 s at 5 mm, 8 GB); the field (`field.py`); the optimiser (`optimise.py`). **Derivatives checked at 5 mm** (`gradcheck.py 5`): a tilt, a bed and the mass by a thickness, a height and a turn variable, and every rule: worst 7·10⁻⁶.
  - **Now: the run `h1`** (`optimise.py h1 80`, 4 mm, the cloud container, started 16 October ~03:40 IST, about 1.5 h; log `data/rib_housing/h1.log`, state saved every 5 iterations to `h1.npz`/`h1.json`; resume with `--start=data/rib_housing/h1.npz`).
  - **Next:** the drawing through the product's (`draw.members_sdf` replaced by the ribs' signed distance and tops, §2 step 5), then oil-tight, FE (CPU), castability, grade, pictures beside `baseline2_lw8_smooth`.

## 2. The plan for the housing (in `prototypes/rib_housing/`; nothing in `src/` changes)

1. **Set-up from the product, unchanged:** `zenryx.domains.gearbox.housing.layout.write` (the contract to `contract.json`), `setup.build` and `voxels.Voxels` (4 mm cubes, the fixed shell and interfaces, the design space as columns along the pull, the rigid couplings, the loads, every seat's tilt and bed measure with its line, the safety). The recipe's own settings (`src/zenryx/workflow/recipes/final.json`): budget 7.73 kg, band 24 mm, `--empty --protect --shell-fixed --no-towers`, safety 1.5, peak drive.
2. **The model:** the fixed cubes keep the product's element (Wilson's incompatible modes, isotropic); every free cube becomes a rib cube: the toy's laminate (thin plates along the pull, running along theta in plan, share rho), times its share of its column's height (the toy's `model.py`, plain hexahedra: the toy's model read 12 % stiffer than FE of its drawing). Assembled each step as K_fixed + K_ribs(x); solved by PARDISO (double, CPU).
3. **The fields:** per group of columns (half x the product's column layer), two families at right angles, each with a thickness share and a height share as cubic B-splines on 16 mm knots, and the directions a smooth B-spline turn from where the strains first put them (the toy's `Field`); thickness by place and fastcae's rules (`rules.py`) with the housing's hard points (the bearings' bosses, the bolts' bosses, the mounts' lugs) and anchors (the shell's walls: a column's base).
4. **The problem:** the product's `mass_tilt`: the least placed metal with every seat's tilt and bed held at 1/1.5 of its line in the peak drive; MMA. **The modes are not held in this run** (the CPU's time); FE reads them after.
5. **The drawing:** the ribs from the stripes on a fine plan grid per group, as an implicit solid (draft, rounded tops, root fillets) united with the product's exact shell and interfaces, cut by the product's kept-clear spaces; a mesh per half as the product's drawing writes it, so the product's FE, oil-tight check, castability, grade and pictures read it unchanged.
6. **FE:** the product's `fe.judge` on the CPU (the GPU stand-ins of `checks/support/gpu_on_cpu`, PARDISO double); the container has 15 GB, so FE's surface and tets coarser than the laptop's (judge the reference `baseline2_lw8_smooth` the same way, like for like).
7. **The pictures:** each half from the product's cameras and along the pull, beside the reference, with the numbers.

## 3. Learnings carried from the toy (each measured, the method page §6)

- The strains' best direction flips one-way-stiff ribs every step: the directions must be the optimiser's own variables (a smooth B-spline turn from the strains' start), with the exact derivative.
- Two families at right angles, not one (several load cases).
- The smeared model reads ~12 % stiffer than FE of its drawing: fair.
- Thickness by place beats one cap: thin ribs alone are 1.9 x softer than free metal at equal mass, by place 1.75 x.
- The end rule (thickness constant along a rib away from the anchors) works: free ends 29 → 19 a metre; the drawing's gate (loose pieces, ribs under 20 mm) takes it to 13.
- 8 mm cubes lose a 4 mm wall: use 4 mm. The container ran out of memory on a 2.3 M-unknown FE mesh: keep FE under ~1.2 M unknowns here.
- Plain MMA (no inner loop) settles in 60-100 steps on the toy.
- **The bend rule read at every point at p 8 is infeasible** where the start's directions converge (at the bosses): the toy's `f4` emptied its ribs (0.06 kg) trying. Read away from the anchors at p 4, radius 30 mm (`rules.P_BEND`, `R_BEND`): held.
- **The end rule must read a rib's share of its local cap, not its thickness:** with thickness by place, a thick-rooted rib's taper broke it, and the toy's `f5` placed half its budget (0.12 of 0.25 kg). Read on the share (`rules.transport`'s `ds`), a rib tapers with its cap from a thick root: production's tapered rib.
- **PARDISO through pypardiso factorises on every `solve` unless `factorize` was called first** (it records only what `factorize` factorised): call it once, then solve the cases and the adjoints (112 → about 60 s an analysis at 4 mm).
- **Rib cubes need a floor of isotropic stiffness** (1e-4): their plates take nothing across, and with 1e-6 a central difference on the housing came out wrong (the analytic derivative was right: checked at 5 mm with the floor).
- At 8 mm cubes the product's least width (8 mm, two cubes) refuses to build: check at 5 mm.

## 4. How to resume

- The toy: `prototypes/rib_field/README.md`.
- The housing: this page's §1 says which step runs; its scripts' README (`prototypes/rib_housing/README.md`) says the commands.
- The cloud session's Python: the scratchpad venv (`<scratchpad>/venv/bin/python`); a new session builds one with `uv sync --all-extras` and `pypardiso`, and puts `checks/support/gpu_on_cpu` on `PYTHONPATH` for the product's FE and optimiser on the CPU.
