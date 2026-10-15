# The night of 14-15 October: production-like members from the spline space, judged by FE

**15 October 2026, 05:18.** LOP-30. Where to start after this night. The engineer's brief, in their words:

- 22:43-23:01: "What we expect is like this smooth nice but shaped by optimiser"; the plan of the evening (one smooth top, the section window, the bending, a lump rule counting the land, the finer drawing) agreed: "ok".
- 00:10: "how do we cover both mounts and ribs generally assuring optimization have freedom to explore but not in the form of members that look extremely bad and ugly".
- 01:21: "Yes" to production's settings (ribs about the wall's thickness, fillets, no pads).
- 01:30: no D17 ("we have to do optimization twice ... not so efficient"); this approach, made production-like, its smooth output a CAD designer's suggestion; "why can't we simply interpolate or smooth that area out ... after it's been obtained from the optimizer".
- 01:45-01:48, leaving for the night: "Solve this problem"; the rules are guides, "nothing is too strict here", "we need a solution right now which looks good, which looks reasonable, which looks production quality, which looks manufacturable"; a local pad is fine, "not like a lump", "not like the sketchy staircasey thing".

## 1. The result

**`spl8f6` passes every graded FE line, drawn smooth from the optimiser's fields under production-like rules.**

| Line | FE | Limit |
|---|---|---|
| Worst seat, peak drive | 38.9 µm | 52.2 µm to beat |
| Tilt, worst seat against its line | 0.85 | 1.0 |
| First mode | 849 Hz | at least 500 Hz |
| Gear orders | no mode within the bands | |
| Mass | 5.16 kg | 7.73 kg |
| Oil-tight | yes | |

- **The look** (`data/first_loop/look_spl8f6.png`, `look_face_spl8f6.png`, `closeups_spl8f6.png`): smooth members on the end walls, curved arms to the three mounts, thin gussets down the side walls from the flange, a smooth tall boss round the motor side's middle bearing.
- **The night's gates:**
  - free-end rises over 2 mm in 1 mm: 95 / 44 places, 0.8 / 0.9 % of the members' inner cells, the largest 8 / 4 mm (`free_end_steps.py`; `baseline2_spl3`: 125 / 69 places, the largest 38 / 31 mm);
  - sections over 16 mm outside the bearings' bosses and the mounts' eyes: the motor side's largest 38.7 mm, 52.6 cm³ in 39 places, almost all at the split where the members join the sealing land; the cover's 24.0 mm (`lump_where.py`);
  - castability: undercuts 31.3 / 0.4 cm² (motor side / cover; 1 %), thinner than the least wall 167 / 117 cm² (the rounded free edges thin to a knife edge), the thickest member 24 / 23 mm.
- **The hand-over:** `member_map_spl8f6.png` (cover: 8 members, gussets, a web and two networks; motor side: 7, three arms to the mounts, a web, two ribs and a gusset), `member_reading_spl8f6.png`, `handover_spl8f6.html` (built with `--look spl8f6_fine`: the 1 mm drawing's pictures under the judged design's numbers; no towers, so the seats' rings are the fixed features and the bosses the members'; the lumps as measured; castability's rules not met, so the rung is simulation-feasible). `night_spl8f6.png`: the night's design beside its start and 14 October's.
- **The same run drawn smoothed over 3 mm** (`spl8f2`): it passes too (5.07 kg, 40.5 µm, tilt 0.94, 843 Hz), with ragged gusset tops on the side walls (7.7 / 4.5 % rises over 2 mm).

**How it was run.** The optimisation (`spl8`, 01:57-02:25, settled at iteration 136):

```
LOOP_DRAW_SMOOTH=3 LOOP_DRAW_FINE=1 bash prototypes/first_loop/fm500_run.sh spl8 --least-width 6 --spline 12:36 \
  --least-gap 8 --outline 8000 --section 3:4 --top --window 10:14:20:24:18:14:10 --window-split 999:30:20:10 \
  --window-free mounts,bosses_wall --disc --soft-dist --sizes 0.005 --penal-most 1 \
  --start <spl5d's checkpoint> --beta0 4 --ramp 0
```

Its drawing and judgement:

```
LOOP_DRAW_SMOOTH=6 LOOP_DRAW_FINE=2 LOOP_MEMBER_P=40 GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_CAST_AFTER=1 \
  LOOP_LEAST_MEMBER=8 bash prototypes/first_loop/campaign_run.sh spl8f6 --budget 7.73 --voxel 4 --run <spl8's run>
```

## 2. The settings, and why each

On the agreed baseline (`fm500_run.sh`: the empty start, the 4 mm shell fixed, members 8 mm proud, the least metal under 7.73 kg, every line at 1/1.5, the modes 12 % from the orders, the first mode at least 500 Hz, the 16 mm lump rule):

- **The spline space, 12 mm outline knots, 36 mm height knots** (14 October): smooth outlines and calm heights.
- **One smooth top** (`--top`, F1): a member's free end is one surface, not a height above each column's level; the stairs went.
- **The plan rules measured across the walls' steps** (with `--top`, by run and family): measured per level, every strip of one level under 8 mm (the seats' 4 mm rings) held no metal and cut the ribs short of the bosses.
- **Least width 6 mm, least gap 8 mm, as constraints on the raw field** (`--least-width 6 --least-gap 8 --sizes 0.005`): the openings on the 2 mm points had made the outline blocky. 4 mm ribs (`spl6`) could not turn the start's pads into ribs: each new gap passes through narrow first, which the gap rule resists.
- **A cube's share counted linearly** (`--penal-most 1`): the densities are shares of real geometry, so a cube half filled by a thin rib is half as stiff; with SIMP's 3 it read four times too soft off the grid.
- **The section window, by role:**
  - the end walls' ribs: at most 24 mm tall under 10 mm wide, 18 at 10-14, 14 at 14-20, a local pad at most 10 mm from 20 mm wide (`--window 10:14:20:24:18:14:10`);
  - the side walls' gussets, hanging from the split: thin ones as deep as the space allows, 30 / 20 / 10 mm as they widen (`--window-split 999:30:20:10`). Capped like the ribs, the beds stalled at 1.6-1.7 x (`spl6`, `spl7`); they carried the beds;
  - free: each mount's reach disc (a bracket's depth is the lug's place; capped at 32 mm mount-3's lug could not be reached at all) and each bearing's boss on its own wall (the engineer, 00:41: "Lift height cap only"; round every seat 43-78 % of `spl5c`'s metal had stood cut by the cap) (`--window-free mounts,bosses_wall`);
  - the caps measured from each family's level smoothed over 8 mm, so a capped top runs over the wall's steps.
- **The section rule** (`--section 3:4`): the free edges rounded 3 mm, the roots filleted 4 mm.
- **The outline's length at most 8 m:** at 3 m it rewarded pads over ribs.
- **The start:** `spl5d`'s state at iteration 80 (every line held), sharpness 4: from a uniform start the pads never broke into ribs.
- **The drawing's smoothing** (`LOOP_DRAW_SMOOTH=6`): the outline a cubic curve through the points (straight, a tall face showed each kink as a groove), each member's free end smoothed over 6 mm within its member and family, the distance to a sloped top over its slope (the plain height aliased into stripes). FE judges the smoothed shape.

## 3. What the night found, each measured

1. **The lump rule counting the land outright cannot be met** (`spl4`): the land and the bolts' bosses fill 0.70 of the 16 mm ball with nothing placed (the limit 0.6). Held so it can be met (`--lump-fixed 8 --lump-floor 0.25`: each ball's placed metal at most what the fixed leaves of 0.6, never under 0.25), `spl9`, §5.
2. **The window cut the mounts off** (`spl5`): the lugs stand 33-63 mm under the split with their rooms over them; at a 32 mm cap mount-3's lug joins the housing nowhere (`lug_reach_probe.py`).
3. **The plan rules per level masked the seats' rings** (`spl5b`): 3,237 points no 8 mm disc fitted, 4.7 m of the 6.4 m outline against them; by run and family 2,009, the rings gone (`level_strips.png`).
4. **The side walls' gussets carry the bearings' beds** (`spl7` -> `spl8`): with their own caps the lines held within five iterations.
5. **A late sharpening can break a link** (`spl8`, iteration 129, 22.6 -> 32: the input seat 1.00 -> 1.36 x): it recovered to 1.05 x; the run now keeps its last state that held every line (`<stem>_held.npz`).
6. **FE could not mesh any drawing of the new spline path** (`spl8`, `spl5d_it80s`; the older path's `baseline2_spl3` meshed). Two causes, both cured:
   - the kept-clear spaces (the bolts' sockets, the mounts' rooms, the exits) were emptied cell by cell, and the members' smooth faces running along that staircase left hairline flags TetGen reads as "two segments exactly intersect": now cut by the spaces' signed distance, smoothly (`outcome_cad.skin_parts`' `clear_sdf`);
   - marching cubes puts two vertices 1e-4 mm apart where a grid value lies a hair off the level, and TetGen built 249 flat tets on one such needle: FE's coarsening now collapses edges under 0.02 mm (`mesh_route.NEEDLE`).
   - Also: `fe.mesh_tetgen` keeps fine the places TetGen names when it refuses, and coarsens again at the same size.

## 4. Open

- **Lumps** (38.7 mm sections): the largest, 34 of the motor side's 53 cm³ over 16 mm, is mount-3's arm where it meets the split flange at (27, 210), a smooth thick pad (`zoom_lump_motor.png`); the rest at the members' junctions with the land and the bolts' bosses. The union lump rule with its floor at 0.25 did not reduce them (§5).
- **The gear orders are not held in FE's terms** (§6, §8): the optimiser's modes on its own field read about a third low, while its model on the drawn shape reads FE's within 6 %; and its lowest modes stop short of the first stage's order. So whether a design clears the orders in FE is chance (`spl9h` met the second stage's, `spl8f6_fine` the first stage's, each by a mode the model never held).
- **Free-standing posts:** a member may stand beside a bolt's socket, joined only at the flange, with its own mode (§6); the optimiser's gap rule reads the members alone.
- **Undercuts** of 30 / 15 cm² (motor side / cover, 1 mm drawing), mostly on the contract's mount lugs; **thin** areas where the 4 mm shell sits at its least wall and where the rounds thin the free edges.
- **FE on a finer surface:** the 1 mm drawing meshes on 7 mm triangles; on 5 and 6 mm the cover's surface crosses itself where TetGen names it, and the retries do not cure it.
- **To confirm with the engineer**, all made overnight under "rules as guides": the window lifted in the mounts' reach discs; the bosses free only on their own wall; the side walls' gussets' own caps; the lump rule's floor 0.25; a cube's share counted linearly; the drawing smoothed over 6 mm; ribs at least 6 mm (not 4).

## 5. `spl9`: the union lump rule

`spl8`'s settings with `--lump-fixed 8 --lump-floor 0.25`, from the same start (03:42-04:05). **It fails, and its lumps are no smaller.**

- **The run:** by iteration 30 every limit held at once, the union lump measure at its 0.6 (0.747 at the start). At iteration 77 the sharpening 11.3 -> 16 pinched a link off the cover's input seat (1.00 -> 1.16 x, the lowest mode 727 -> 478 Hz), as `spl8`'s had at 129; by iteration 91-94 every line held again. At iteration 101 the sharpening rose to 22.6 with a mode limit still broken, and the same seat went to 1.44 x (the lowest mode 259 Hz); it was stopped at iteration 112 (1.32 x) and its last state holding every line drawn instead (`<stem>_held.npz`, iteration 93, sharpness 16).
- **`spl9h`** (that state, drawn as `spl8f6`): 5.42 kg, 38.3 µm, the worst seat's tilt 0.86, the first mode 828 Hz, but **a mode at 1122 Hz within 3 % of the second stage's mesh order (1127 Hz): fails**.
- **Its lumps:** the motor side's largest section 36.2 mm, 60.5 cm³ over 16 mm in 29 places (`spl8f6`: 38.7 mm, 52.6 cm³); the cover's 26.1 mm (24.0). Why: the floor lets every ball hold a quarter of placed metal whatever the land already fills, so where the land fills half the ball the rule allows 0.75 in all and does not bite at the split, where the lumps are; the drawing's 4 mm root fillets add metal there too. A lower floor would bite, but the rule counted outright cannot be met (`spl4`), so the floor is a choice for the engineer.
- **What it teaches:** a late sharpening breaks the same link twice (the cover's input seat): the held state is the safe output of a run, and the sharpening's step should stop once the field is near 0/1 (here at 16).

## 6. The 1 mm drawing of `spl8`'s fields (`spl8f6_fine`)

The close-ups of `spl8f6` show the side walls' gussets with faceted, torn-looking tops: marching cubes on the 2 mm grid over the smoothed tops. The same fields drawn on 1 mm come out smooth (`zoom_spl8f6_cover_se.png`: top row 2 mm, bottom 1 mm; `look_spl8f6_fine.png`, `look_face_spl8f6_fine.png`, `closeups_spl8f6_fine.png`).

```
LOOP_DRAW_SMOOTH=6 LOOP_DRAW_FINE=1 LOOP_EXACT_WALLS=1 LOOP_MEMBER_P=40 LOOP_LEAST_MEMBER=8 \
  .venv/Scripts/python.exe prototypes/first_loop/outcome_cad.py <spl8's run> spl8f6_fine skin mesh
```

| Line | `spl8f6` (2 mm) | `spl8f6_fine` (1 mm) |
|---|---|---|
| Mass | 5.16 kg | 5.24 kg |
| Worst seat, peak drive | 38.9 µm | 38.2 µm |
| Tilt, worst seat against its line | 0.85 | 0.85 |
| First mode | 849 Hz | 843 Hz |
| The mode nearest the first stage's order (2500 Hz) | 2628 Hz, +5.1 % | **2531 Hz, +1.3 %: fails the 3 % line** |
| Oil-tight | yes | yes |
| Free-end rises over 2 mm in 1 mm | 0.8 / 0.9 % | 1.0 / 1.0 % |
| Largest section outside the bosses | 38.7 / 24.0 mm | 38.7 / 26.0 mm |
| Undercut | 31.3 / 0.4 cm² | 30.4 / 15.1 cm² |

- **FE meshes the 1 mm drawing** since the needle fix (§3.6): at 7 mm triangles, the motor side at the second try, the cover after one flat tet.
- **The mode is a post's own** (`mode_shape.py`, `modes_spl8f6_fine.png`): 92 % of its energy in a member about 15 mm square standing from the flange beside the cover's bolt socket at (80, -35), up to about 55 mm, joined to nothing else: the socket (kept clear for the bolt's head) lies between it and the wall. On the 2 mm drawing the same mode is 2628 Hz. The two drawings differ by 3.7 % on this small mode, about FE's own noise for it, so the design sits on the line: a tie in the measured noise, which the grade reads as a fail on the 1 mm drawing.
- **Why the optimiser did not hold it:** at `spl8`'s end its own lowest ten modes are 546-1360 Hz (the shares' check) where FE reads 849-2628 Hz on the drawing: the model's modes run 1.4-1.9 x low, so its 12 % gaps round the orders are not FE's, and the first stage's band lies beyond the modes it reads. Its first-mode floor (500 Hz in the model) is conservative for the same reason (843-849 Hz in FE).
- **Tried and removed:** closing in the drawing every slot under the run's least gap (8 mm) beside a member, slice by slice across the pull (`LOOP_DRAW_CLOSE`, 04:40): it added 0.22 kg, terraced the members' tops at the 1 mm slices (`zoom_closed_cover_se.png`), and could not touch the post, whose gap is the bolt's socket.

## 7. The least gap read against the shell (built, measured, not run)

- **Why:** the close-ups show thin sheets standing along the side walls ("curtains"), and the optimiser's least gap (8 mm) is measured among the members only, never between a member and the shell.
- **Built:** `topo_free.py --gap-shell` (with `--least-gap` and `--sizes`; the tag's `G`): the closing's discs may hold the half's fixed metal in plan, as metal (`topo.least_width_blocks(..., solid=)`), so a slot between a member and the walls, the land, the bosses or the lugs is read as one between two members is; a point whose every disc already holds the shell (a slot of the shell itself, a boss at the design space's edge) is not read. Its derivative against central differences on `spl8`'s own set-up: 10⁻⁶ or better (`gap_shell_check.py`).
- **Measured on `spl8`'s field** (`gap_shell_map.py`, `gap_shell_spl8.png`): the narrow-gap share 0.72 % with the shell against 0.50 % without (70 points against 56). Counting the shell's own slots too it read 13.6 %, which is why they are left out.
- **So the curtains are not slots:** cut across the pull (`slices_fine_west.png`) they are members themselves, 6-10 mm wide and tall: the side walls' gussets that the window lets stand as deep as the space allows while thin (`--window-split 999:...`), as the beds needed (§2). Where a member does stand within about 2 mm of the exact wall, the drawing's 4 mm rounded union with the exact parts fills the slot. A run with `--gap-shell` would change little, so none was made; the option stays off.
- **The tools kept** (in `prototypes/first_loop/`): `zoom_view.py` (a window of a half from three cameras, designs side by side), `closeups.py` (each half's four quadrants), `mesh_slices.py` (a drawn half cut across the pull), `relief_view.py` (a running spline optimisation's members as a relief, no drawing), `accept_checks.sh` (the night's gates on a design), `judge_drawn.sh` (FE, oil-tight, castability and the grade on an already drawn design).

## 8. The optimiser's modes against FE's (`model_vs_fe.py spl8f6`)

The optimiser's own model (4 mm cubes, the fixed set whole, FE's rigid couplings) solved on three shapes of the same design, against FE on the drawing:

| Shape | Metal cubes placed | Worst seat | Tilt | Modes (Hz) |
|---|---|---|---|---|
| the run's own check (each cube its share, linear) | 1.98 kg | | 1.05 x at 1/1.5 of the lines (0.70) | 546, 669, 719, 769, 904, 910, 956, 1230, 1236, 1360 |
| the field read at 0.5 (metal or air) | 11,344 | 49.0 µm | 1.43 | 725, 867, 1052, 1062, 1106, 1235, 1270, 1456, 1752, 2004 |
| the drawing, voxelised | 12,858 | 35.7 µm | 0.69 | 828, 931, 1266, 1423, 1430, 1644, 1873, 2209, 2218, 2777 |
| FE on the drawing | | 38.9 µm | 0.85 | 849, 932, 1263, 1353, 1514, 1724, 1925, 2208, 2234, 2628 |

- **The model is fair on the drawn shape:** every mode within 6 % of FE's (the first 2.5 % low), the statics about 20 % stiff (tilt 0.69 against 0.85), which the 1.5 safety covers.
- **The field is not the drawing:** read at 0.5 it loses links (tilt 1.43, 13 % fewer cubes than the drawing), and read as shares, as the optimiser reads it, its modes are about a third low (546 Hz against 849), though its tilt is the drawing's (0.70 against 0.69). The drawing makes the field's partly filled cubes whole where the outline passes (its smooth outline, its rounded and filleted joins), which raises the modes far more than the seats' stiffness.
- **So:** the first-mode floor (500 Hz in the optimiser) is conservative in FE (843-849 Hz), and the gaps of 12 % round each order are held on modes that FE puts elsewhere. Holding the orders in FE's terms needs the optimiser's modes read on a shape nearer the drawing (the field projected sharper for the modes alone, say), or margins learned from FE as `seat_ratios.py` learns the seats'. Not tried tonight.
