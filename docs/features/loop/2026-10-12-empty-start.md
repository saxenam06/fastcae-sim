# The empty start (LOP-27): implementation plan

> Executed by Claude in this session (the engineer, 12 October 20:22: "Do an empty start"); the loop page's LOP-27 row says where it stands.

**Goal:** a housing from an empty design space. No fixed shell: the walls, bosses, ribs and brackets are one field the optimiser sizes, oil-tight by rule, drawn as one body, exact only where a machine cuts.

**Architecture:**
- The height field's columns stay as they are (castable by construction), without the frozen skin and the flange's land:
  - over the inside (the cup's rooms), a column's metal grows from the room's far face;
  - elsewhere it grows from the split.
- The oil-tightness is each column's **least height**, an offset inside the height chain, so the walls are the same smooth field as everything else:
  - the end walls;
  - the plate over the other half's wider opening;
  - the side wall with the sealing land;
  - each seal's seat.
- Fixed: only the interfaces (the seats' rings, the mounts' lugs, the bolts' bosses).
- Drawn: from the field alone, with the inside, the bores, the exits and the holes cut exact.

**Tech stack:** `topo_free.py` and `topo.py` (numpy, CuPy, GCMMA), `outcome_cad.py` (manifold3d), `fe.py`, `castable.py`, `grade.py`, `propose.py`.

**Spec:** the engineer's direction of 19:30-20:22 and [the reading of the reviewer's direction and five papers](../../research/2026-10-12-reviewer-direction-and-five-papers.md) §3-4.

## Global constraints

- The design space is fixed in every iteration (D16).
- No fixed shell (20:22).
- The contract's rules:
  - `min_wall` 4 mm;
  - the joint (A26): a sealing land 10 mm wide, 9 mm each half, M8 bolts in Ø20 bosses;
  - each sealed exit's seat, 11 mm behind its bearing (A16-A17).
- Peak drive alone.
- The factor of safety 1.15.
- One heavy job at a time, with free memory checked first.
- Nothing committed without the engineer's word.

## The first comparison

`it1_free_5.5kg` is the benchmark: 5.63 kg, beds 36.8 µm, tilt 0.93 ×, 773 Hz, no clash. The empty start keeps everything else the same, so that only "shell fixed" against "shell free" changes:
- 4 mm voxels and 5.5 kg in all;
- `compliance_tilt --beds`, peak drive, `--route split --settle 0.02 --every 25 --beta-most 32 --fast`;
- `--height-field 6 --safety 1.15`;
- the same design space: the 24 mm band off the old shell's place, which is 28 mm off the inside, the mounts' regions open.

The band then lapses as a separate, single change, if the engineer wants it.

## Files

- `prototypes/first_loop/topo_free.py`:
  - `build_free(..., empty=True)`: the set-up without the shell, and each run's least height (`model["height_min"]`);
  - `--empty`: the stem tagged `empty`, and the record saying `"empty": true`.
- `prototypes/first_loop/topo.py`: `Voxels`' height field takes the least heights as an offset, never gated by the least member.
- `prototypes/first_loop/topo_gradcheck.py`: `--empty` checks the chain's derivatives on the empty set-up's height field.
- `prototypes/first_loop/outcome_cad.py`: an empty run drawn without the exact shell, its interfaces at full size on the grid.
- `prototypes/first_loop/oiltight.py` (new): both drawn halves voxelised and flood-filled from the inside with the seals in place; a leak names where.
- `prototypes/first_loop/propose.py`: flow E, "the empty start", from an empty run's record.

## Tasks

1. **The set-up without the shell** (`build_free(empty=True)`).
   - **Frozen:** the seats' rings (the voxel layer round each bearing, along it, whole), the mounts, and the bolts' bosses (the flange's share for the bosses alone).
   - **The skin:** still found, for the band and the mounts' reach, but free.
   - **Least heights, in voxels of the run's own free metal:**
     - a run standing on a room: `min_wall`;
     - a run at the split over the other half's room: `min_wall`;
     - a run in the land, within 10 mm of either half's inside at the split: the flange's 9 mm;
     - the first ring round the inside: the deepest own room beside it plus `min_wall`, at least 9 mm;
     - the first ring round each seal's exit: 11 mm.
   - **Check:** the set-up's counts (frozen kg, free voxels, the walls' least mass against the budget).
2. **The offset in the height chain** (`topo.Voxels`): `t = t_min + M x L` on a wall's column, with no gate; the least member gates only the columns with no least height.
   - **Check:** `topo_gradcheck.py 10 4 2 --empty` passes (central differences, relative 1e-3).
3. **`topo_free.py --empty`:** the flag, the tag and the record.
   - **Check:** a 6 mm smoke run, 20 iterations, finishing without error.
4. **The drawing** (`outcome_cad.py`, an empty run):
   - no exact shell, and no buried parts;
   - the bolts' bosses and the mounts on the grid at full size;
   - the land and the plate the field's;
   - the cuts as today.
   - **Check:** both halves watertight, and the bolts and the mounts held.
5. **The oil-tight gate** (`oiltight.py <design>`).
   - **Check:** `it1_free_5.5kg` reads tight; the same with one wall cell opened reads a leak.
6. **Flow E in `propose.py`** (its set-up note, its name).
   - **Check:** `process_export.py` writes its tabs.
7. **The run:** 4 mm, the first comparison's settings with `--empty`. Then FE, castability, the grade, the pictures, the oil-tight gate, against `it1_free_5.5kg`.
8. **Records:**
   - the loop page (LOP-27; the decision "no fixed shell");
   - CLAUDE.md's lines;
   - the README's rows;
   - the memory.

## Review focus

1. **A seat's nodes:** each bearing's ring must hold more than 8 nodes on its bore (`topo.Voxels` asserts it). With no skin, the ring is the only metal there.
2. **The joint:** where the halves' insides differ, the plate over the other half's opening must close it, or oil leaks at the split. The oil-tight gate checks it on the drawing.
3. **The least member:** its gate must never empty a wall's column (Task 2's exemption). A run with `LOOP_LEAST_MEMBER` set must still keep every wall.
4. **The drawing's 4 mm walls** are two cells of its 2 mm grid. The blur and the contour must not open them; the oil-tight gate and watertightness say so.
5. **The budget:** the walls' least metal must leave the optimiser room. The set-up prints the walls' least mass beside the budget, and stops if it exceeds it.
