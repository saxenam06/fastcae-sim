# The first loop, start to end (PROTOTYPE)

**A prototype, not product code** (CLAUDE.md): nothing in `src/` imports it, and its outputs go to `data/first_loop/`, which git ignores. It is the LOP feature's work (`docs/features/loop/status.md`): one housing for the EV two-stage reducer taken from the completed contract through a plain shell and wall, its FE judgement, topology optimisation, ribs, and the FE judgement again, to learn which tools the product needs and where an agent's judgement belongs (the engineer, 9 October 01:54). What it taught: `docs/features/loop/2026-10-09-first-loop-what-it-teaches.md`.

| Step | Script | What it makes |
|---|---|---|
| LOP-1 | `shell.py` | The plain convex housing: two halves split across the shafts, its walls round the gears' cavity (with a sump), the bearing bosses and seats, the seal bores, the split flange with its bolts, three mount bosses (A20) and the motor flange (A25); every face named by its role; STEP, the face names, the mass, pictures. `build(stem, ribs, overrides)` adds ribs and changes settings |
| LOP-1 | `lobed.py` | The lobed housing: a pod per shaft, each end wall stepped to its own shaft's length, the motor's flange plate; the same `build(stem, ribs, overrides)` |
| LOP-2 | `fe.py <stem> [size]` | The FE judgement: TET10, the seats' loads over each whole seat (RBE3; `LOOP_LOADS=cosine` for the plan's cosine), the mounts and the bolts by distributing couplings, the motor's torque, statics and modes; `fe_<stem>.json` |
| LOP-2 | `fastcae_fe.py` | fastcae-v1's TET10 stiffness and cuDSS solve, copied verbatim |
| LOP-3 | `topo.py <shell> <compliance\|tilt> <kg> [voxel] [its]` | Voxel SIMP in the packaging space outside the frozen shell; the tilt objective by an adjoint |
| LOP-4 | `read.py <topo> [skeleton <shell>]` | Rib paths from a density field: a scored fan, or the field's skeleton |
| LOP-4 | `hypothesis.py <stem> …` | A designer's radial ribs round chosen bosses, built like any reading |
| LOP-4, LOP-6 | `grade.py` | Every FE result against the contract's lines; the tilt graded is each seat's against its shaft's line, the seat's own rotation printed beside it; `grades.json` |
| | `picture.py`, `deformed.py` | The halves by face role; the displacement on the deformed halves |

Run from the repository's root, e.g. `uv run python prototypes/first_loop/shell.py`. `LOOP_CONTRACT=<path>` runs any script on a what-if variant of the contract. The night's one, `data/first_loop/whatif_same_hand.json`, is the product's contract with `requirement.stages[1].helix_hand_pinion` set to `"right"`, as the checks' `same_hand` fixture builds it (`checks/gearbox/test_complete.py`).

The housing's own choices (its wall, bosses and flange) are the shell-and-wall tool's settings, in `shell.py`'s `SETTINGS`, each with where it comes from. The contract's values (the layout, the bearings, the clearances, the process) are read from the contract and the load tool, never typed here.
