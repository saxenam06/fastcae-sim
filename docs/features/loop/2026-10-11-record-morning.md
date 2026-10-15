# The loop's record: the morning of 11 October

Every trial toward a production-like housing that passes, written as it happens. The loop's page ([status.md](status.md), LOP-23) holds the state; this page holds the account. The night before: [2026-10-11-record-night.md](2026-10-11-record-night.md).

## Where it stands (09:47)

- **Designs that pass every graded line** (the beds against the reference's 52.2 µm, the tilt against its line, the orders, the mass under 7.73 kg). FE on 7 mm triangles; all at 6 mm voxels inside a height envelope (`topo_free.py --band`):

  | Design | Design space | kg | Beds µm | Tilt × | First mode |
  |---|---|---|---|---|---|
  | `outcome_env24f_6.5kg` | free within 24 mm of the shell; 4 mm root fillets | 7.24 | 33.5 | 0.71 | 772 Hz |
  | `outcome_ribsfieldfins24_6.3kg` | **production's rib network** (wheels of spokes, rings, links, fins and a free run's lines) within 24 mm; fillets | 6.83 | 42.0 | 0.83 | 724 Hz |
  | `outcome_ribsfieldfins24_6.7kg` | the same at 6.7 kg | 7.28 | 37.6 | 0.77 | 746 Hz |
  | `outcome_env24_6.5kg` | free within 24 mm | 6.98 | 33.1 | 0.70 | 764 Hz |
  | `outcome_env18_6.0kg` | free within 18 mm | 6.48 | 44.2 | 0.64 | 719 Hz |
  | `outcome_env18_6.5kg` | free within 18 mm | 7.14 | 41.3 | 0.68 | 752 Hz |

- **Not yet:** castability by the strict rule (undercut 0.4-1.1 % of each half's surface): drawn as a height field the body is castable (0.03 %), but the mounts' lugs, with a bracket's room above and below, are not as the set-up has them. And production's crisp ribs. The form is right in its grammar: rings round the bosses, a wheel of spokes, links. But the members are voxel-lumpy at their edges (`data/first_loop/compare_production_faces.png`, face-on beside the production photos).
- **The judge corrected:** FE's surface is 7 mm, not 9 (for the engineer's review).
- **Tried and set aside, each with its numbers below:** 4 mm voxels (the model flatters FE), the rib filter (grey groups), flow C's reading of a field within a band, the clean network drawing.

## The engineer's words (07:32-07:46)

- 07:32: "compare the pictures of CAD with the pictures of ribs I gave you of production housing... what issues do you see? No fillets? Or production ribs are that high? The CAD still looks very odd... what are we missing? What further constraints can we bring into the optimisation?"
- 07:33 and 07:40: search for photos of production EV gearbox housings on the web, and compare them, as with the engineer's own pictures.
- 07:43: "Don't have to wait for my word... find pictures of production housing, compare, find the gaps and try more until we achieve..."
- 07:46: "There is no better proof than reality... we have to achieve the reality without me being the blocker in between."

So the goal is a housing that looks like the production ones and passes every line, tried without waiting for the engineer. Heavy runs go one at a time, and nothing is committed or served without their word.

## The comparison (07:33-07:40)

Written up in [production EV housings against the ribbed CAD](../../research/2026-10-11-production-ev-housings-against-the-ribbed-cad.md), with the side-by-side sheet `data/first_loop/compare_production_housings.png`.

| | Ours (the night's designs) | Production |
|---|---|---|
| Rib height | median 63 mm, up to 105 mm | low: 10-25 mm |
| Rib thickness | 12 mm, 3 × the wall | the wall's or thinner |
| Rib ends | often in the open | always on something |
| Hard points | none | a boss at every bore, bolt bosses at a pitch, gussets |
| Fillets, draft | none | everywhere |

Also compared since then: Aichi Kikai's photos of the cases it casts for Nissan's BEV reducer (two stages, like ours; `scratchpad/web_housings/aichi/`). Round each bearing's boss there is a wheel: radial spokes at an even pitch out to an outer ring, inside a perimeter flange with bolt bosses.

**Why ours look odd:** the design space reached about 100 mm past the end walls. A member's bending stiffness grows with the cube of its depth, so under a mass budget the optimum is a few deep webs. Nothing in the set-up said what production's rule says: a rib stands no higher than the bosses it meets.

## The first move: the height envelope (LOP-23)

`topo_free.py --band <mm>` lets metal sit only within that distance of the shell, plus a corridor out to each mount. It was stage 2's band of 9 October (then a 30 mm band drew a wheel round the output's bearing), now given as an option. It needs no contract change.

| When | Design | Set-up | Result | What it taught |
|---|---|---|---|---|
| 07:48-07:50 | `outcome_band18` | 7.73 kg, an 18 mm band, 6 mm voxels; otherwise the night's method (compliance, tilt and beds held, peak drive, one run) | optimised in **43 s**, judged in 119 s. Beds **35.5 µm** (to beat: 52.2), tilt **0.68 ×**, **no order clash** (first mode 749 Hz); **8.67 kg** (0.94 over) | the first compact shell: no tall webs, the mounts on short arms, a ring round the output's bore. **Every unbanded flow B design had a mode within 3 % of stage 2's order; this one has none.** But the surface is lumpy: 4.8 kg to place in an 18 mm band nearly fills it, and the greatest member's limit breaks that layer into lumps and holes. The drawing adds 0.94 kg because each member is drawn with its whole 6 mm skin voxel under it, where the model counts 4 mm |
| 07:53-07:57 | `outcome_env18_6.0kg` (`envelope_sweep.sh`) | 6.0 kg, 18 mm | **passes every graded line:** 6.48 kg, beds 46.4 µm, tilt 0.66 ×, no clash (721 Hz); 195 s. Castability fails by the strict rule: undercut 0.79 % and 0.23 %, 67 and 36 cm² under 4 mm | **the first design to pass the grade.** Its form is still lumpy shell thickening, not ribs. The undercut is small spots where the mount arms join and beside bolt bosses. Some of the "thin" area is on the exact 4 mm walls: the coarsened mesh's noise against a 0.1 mm tolerance (open) |
| 07:57-08:00 | `outcome_env18_6.5kg` | 6.5 kg, 18 mm | **passes:** 7.14 kg, beds 42.3 µm, tilt 0.64 ×, no clash (744 Hz); undercut 0.91 % and 0.27 % | |
| 08:00-08:02 | `outcome_env18_7.0kg` | 7.0 kg, 18 mm | 7.78 kg (0.05 over), beds 38.4 µm, tilt 0.60 ×, no clash (752 Hz) | the drawing adds 0.48, 0.64, 0.78 and 0.94 kg at 6.0, 6.5, 7.0 and 7.73 kg: it grows with the metal placed (the 6 mm skin voxel under each member) |
| 08:02-08:05 | `outcome_env12_6.5kg` | 6.5 kg, 12 mm | **a failed optimisation:** metal or air 7.1 × the tilt line, 372 × the beds; drawn with 1 of 3 mounts, first mode 33 Hz | the mounts' corridors are as wide as the band: at 12 mm they are two 6 mm voxels across, and two mounts never joined. `propose.py` drew and judged it regardless; it now stops a run whose metal-or-air check misses its own lines by more than 10 % (`FEASIBLE`), as the engineer's rule says: a failed optimisation stops the campaign |
| 08:05-08:07 | `outcome_env24_6.5kg` | 6.5 kg, 24 mm | **passes, the best so far:** 6.98 kg, beds **32.8 µm**, tilt 0.73 ×, no clash (770 Hz); 139 s. Undercut 0.91 % and 0.37 % | taller members make it lighter and stiffer than at 18 mm (7.14 kg, 42.3 µm). More of the end walls is bare exact shell, with the metal in bands round the bores and along the waists, but still organic, not ribs |
| 08:08-08:13 | `outcome_env20_4mm_6.0kg` | 4 mm voxels, a 20 mm band, 6.0 kg, members at most 8 mm | passed just on 9 mm triangles: 6.30 kg, beds 51.8 µm (52.2), tilt 0.99 ×, no clash (615 Hz); on 7 mm (below) the tilt is 1.02 ×. 306 s (the optimisation 228 s, about 3 s an iteration). Undercut 0.88 % and 0.19 % | **the first rib-like members:** on the cover, a ring of short spokes round the intermediate's boss and a fan over the output's end face. The drawing adds only 0.3 kg (the skin voxel is the wall). The 4 mm model flatters: its beds read 0.83 ×, FE's 0.96 × (at 6 mm 0.98 × against FE's 0.85 ×) |
| 08:13-08:20 | `outcome_ribs20_4mm_6.0kg`, `_6.5kg`, `_7.0kg` | the same on production's rib network (`--ribs`, no greatest member): 39,061 free voxels, 6.5 kg if all metal | **failed optimisations:** the beds 1.36, 1.25 and 1.20 × in the voxel model, mostly at the intermediate's +z seat (the plain band: 0.83 ×); stopped before drawing | more metal hardly helps (compliance 1,970 → 1,865 N·mm): the network lacks a load path. Against the plain field (`scratchpad/field_vs_net.py`), about 1 kg of its metal lies off the network |
| 08:20-08:23 | `outcome_ribsfield20_4mm_6.0kg` | the network and the plain run's members' centre-lines (`--ribs-from <run>`, the interpreted design optimised again: the engineer's idea of 9 October 22:51) | feasible in the model (1.00, 1.00), but FE: 5.95 kg, beds **56.0 µm**, tilt **1.12 ×** | still 0.71 kg of the plain field's metal off it, nearly all side-wall plates from the flange up (`scratchpad/off_net.py`), which thinning to lines takes away. The cover's boss discs fill as lumps: per-voxel freedom gives no production regularity |
| 08:27-08:30 | `outcome_ribsfieldfins20_4mm_6.0kg` | the same and fins up the side walls every 24 mm of the inside's outline (`--fins`; 44,587 free voxels) | 5.98 kg, beds 54.2 µm, tilt 1.13 ×; fails | the fins help a little (compliance 1,585 → 1,520 N·mm) |
| 08:31-08:35 | `outcome_ribsfieldfinsuni20_4mm_7.0kg` | the same at 7.0 kg with **the rib filter** (`--rib-filter`: each piece of the network at each height off the shell one group, its voxels one density: 2,068 groups; `topo.Voxels` takes a group's mean as a voxel's filtered density) | drawn 7.48 kg, beds 57.6 µm, tilt 1.16 ×, a mode clash (570 Hz); fails | **the form is cleaner:** flat-topped bosses of the trade's size (the cover's intermediate boss a plateau about 120 mm across), even fins at the output's rim. **But it is softer** than the unfiltered network at 6.0 kg: one height for each 40 mm piece costs stiffness |
| 08:35-08:38 | `outcome_ribsfieldfins20_4mm_7.0kg` | the unfiltered network at 7.0 kg, to part the filter's cost from the network's | 6.96 kg, beds **63.5 µm**, tilt 1.11 × on FE's 9 mm triangles: worse than at 6.0 kg, though the model met its beds | more metal and worse FE: the model and FE disagreed more the thinner the members. Was it the model or the judge? |

## The judge was too coarse for thin ribs (08:39-08:45)

FE coarsens each drawn half to triangles of about 9 mm (`mesh_route.coarse`, quadric decimation) before TetGen fills it. The decimation keeps the mass, but a 4 mm rib cannot keep its section at 9 mm. The same design, judged on three surfaces (`LOOP_SURFACE_EDGE`):

| Design | Surface | Unknowns | Worst bed | Tilt (with the shaft) |
|---|---|---|---|---|
| `outcome_ribsfieldfins20_4mm_7.0kg` (4 mm ribs) | 9 mm | 0.85 M | 63.5 µm | 1.11 × |
| | 7 mm | 1.42 M | 51.3 µm | |
| | 6 mm | 2.01 M (quality relaxed to 3, 10°) | 50.1 µm | 1.02 × |
| `outcome_env24_6.5kg` (6 mm members) | 9 mm | 1.04 M | 32.8 µm | 0.73 × |
| | 7 mm | 1.58 M | 33.1 µm | |

- **On that design the coarse surface judged the ribs 27 % too soft.** It is not general (below): there the decimation spoiled the section near the critical seat.
- Thick members (6 mm voxels) are judged the same on both surfaces.
- **7 mm is FE's surface from now on** (`fe.SURFACE_EDGE`). It is within 2.3 % of 6 mm, about 1.4-1.8 M unknowns (the factor holds 2.18 M), about 70 s a design.
- On 7 mm triangles, one motor side held a flat tet (shape 0), which stops the single factor. A flat tet now moves the surface to the next rung (7.49, 6.51, 5 mm), as a refusal by TetGen does.

**Every design since 07:48 judged again at 7 mm** (`rejudge.sh`, 08:47-09:00):

| Design | kg | Beds, µm (9 → 7 mm) | Tilt × (7 mm) | First mode | Verdict |
|---|---|---|---|---|---|
| `outcome_env24_6.5kg` | 6.98 | 32.8 → 33.1 | 0.70 | 764 Hz | **passes** |
| `outcome_env18_6.0kg` | 6.48 | 46.4 → 44.2 | 0.64 | 719 Hz | **passes** |
| `outcome_env18_6.5kg` | 7.14 | 42.3 → 41.3 | 0.68 | 752 Hz | **passes** |
| `outcome_env18_7.0kg` | 7.78 | 38.4 → 38.3 | 0.60 | 752 Hz | mass (0.05 over) |
| `outcome_env20_4mm_6.0kg` | 6.30 | 51.8 → 50.3 | **1.02** | 616 Hz | the tilt, by 2 % (passed at 9 mm by 1 %) |
| `outcome_ribsfieldfins20_4mm_7.0kg` | 6.96 | 63.5 → 51.3 | 1.03 | 641 Hz | the tilt, by 3 % |
| `outcome_ribsfieldfins20_4mm_6.0kg` | 5.98 | 54.2 → 53.7 | 1.17 | 607 Hz | beds, tilt |
| `outcome_ribsfield20_4mm_6.0kg` | 5.95 | 56.0 → 56.2 | 1.13 | 594 Hz | beds, tilt |
| `outcome_ribsfieldfinsuni20_4mm_7.0kg` | 7.48 | 57.6 → 56.9 | 1.13 | 568 Hz | beds, tilt (no clash at 7 mm) |

- **Only one design moved much; the rest moved 3 % or less.** So the 4 mm model does flatter FE, by about 13-15 % (its beds 0.83 × against FE's 0.96 ×), and the 6 mm model is conservative (0.98 × against 0.85 ×).
- **The likely cause is the bolted joint:** the halves join at the voxel nodes within each bolt's boss (`topo.released_at_split`). At 4 mm, many more nodes fall within each boss than at 6 mm, so the joint is stiffer, and the failing tilt is the input's, whose two seats are in different halves.
- The 6 mm designs keep their margins: they are the ones that pass.

## Production's network at 6 mm, and a designer's reading (09:01-)

| When | Design | Set-up | Result | What it taught |
|---|---|---|---|---|
| 09:01-09:05 | `outcome_ribsfieldfinsuni24_6.5kg` | 6 mm voxels, a 24 mm band, 6.5 kg: the network, the 24 mm run's lines, fins, the rib filter (16,785 free voxels, 1,572 groups) | **unsound:** its metal-or-air check placed 4.46 kg where the budget gave 3.57; drawn 7.70 kg; beds 61.8 µm, tilt 0.66 ×, a clash, the first mode 365 Hz | with the filter each group is a large piece, and the optimiser holds many near the threshold as a stand-in for a thinner rib; at 0.5 they all read as metal. A grouped design needs its groups driven to metal or air (or its pieces sized by a thickness, not a density) before it can be trusted |
| 09:05-09:09 | `outcome_ribsfieldfinsuni24_7.0kg` | the same at 7.0 kg | unsound again: placed 4.46 kg (the budget 4.07); FE 156 µm, the first mode 299 Hz | the rib filter is set aside until its groups go to metal or air |
| 09:09-09:12 | `outcome_ribsfieldfins24_6.5kg` | the network unfiltered at 6.5 kg: 6 mm voxels, a 24 mm band, the 24 mm run's lines, fins | **every line but one:** 6.78 kg, beds 45.4 µm, tilt 0.85 ×; one clash, a mode at 2,560 Hz within 3 % of stage 1's 2,500 Hz order (first mode 704 Hz) | **the most production-like yet** (face-on, `look_face_outcome_ribsfieldfins24_6.5kg.png`): a wheel of short spokes round the cover's output boss, a ring round the intermediate's, straighter links along the network's lines |
| 09:12-09:17 | `outcome_c_env24_6.5kg` | **a designer's reading of the best field** (flow C, `ribbed_cad.py`): ribs along the members' centre-lines, exact; its depth for a rib 8 mm (`LOOP_RIB_DEEP`; 18 mm read a field within a band as pads) | 5.46 kg, beds **111 µm**, tilt **5.05 ×**; fails | the reading threw away the field's load paths: 1.5 kg of its metal lost. Flow C's reading is not fit for a field within a band |
| 09:17-09:19 | `outcome_env24f_6.5kg` | the best field redrawn by the mesh route with **root fillets** of 4 mm (`LOOP_ROOT_FILLET`: a ball rolled over each half) | **passes:** 7.24 kg (+0.26), beds 33.5 µm, tilt 0.71 ×, no clash (772 Hz) | the members blend into the wall as a casting's do, at no cost in stiffness. **4 mm root fillets are the drawing's default from 09:20** (`outcome_cad.ROOT_FILLET`; `LOOP_ROOT_FILLET=0` redraws as before) |
| 09:19-09:25 | `outcome_ribsfieldfins24_6.3kg`, `_6.7kg` | the network design at 6.3 and 6.7 kg (drawn with the fillets), to move its clashing mode | **both pass every graded line:** 6.83 kg, beds 42.0 µm, tilt 0.83 ×, 724 Hz; and 7.28 kg, 37.6 µm, 0.77 ×, 746 Hz. Undercut 1.05 / 0.37 % and 1.13 / 0.51 % | **production's network as the design space passes.** The clash at 6.5 kg was one mode meeting stage 1's order: the mass moves it. Face-on (`look_face_outcome_ribsfieldfins24_6.3kg.png`): a wheel of short spokes round the cover's output boss, a ring round the intermediate's, a long link; the members still voxel-lumpy at their edges |
| 09:27 | castability of the passing designs | where the undercut is | on the motor side, on the flange's underside (z 5.3 mm, facing the pull) above each mount arm; elsewhere tenths of a cm² at the members' junctions | the drawing's, not the design's: the field is cast along the pull, but the blurred grid's contour bulges sideways at a step between columns. A drawing of each half's outside as a height field over the plan would be castable by construction (open) |
| 09:48-09:58 | `outcome_ribshf24_6.3kg` | **each half's outside drawn as a height field along its pull** (`outcome_cad.height_field`, `LOOP_HEIGHT_FIELD=1`): each column's depth off the split smoothed in plan, the surface the zero of a field linear along the pull, so no overhang by construction | first: **undercut 0.03 % a half (0.9 cm²)**, against 1.05 and 0.37 %, but all three mounts came off; then the mounts' lugs drawn apart: the mounts held, 6.81 kg, but undercut 1.43 % at the lugs' junctions (faces leaning 1-3°) and FE's coarsening folded the surface | the body can be drawn castable. **The mounts' lugs cannot, as the set-up has them:** a bracket's room above and below each lug makes its columns a run that never reaches the split, and the split route's filter asks every run to reach it. The lugs want their own castable form (open). Off by default |
| 09:31-09:46 | `outcome_ribsclean24_6.3kg` | **the network design drawn clean** (`network_draw.py`): each piece with metal along its own line, one section, its height the field's | first 8.21 kg (each piece drawn whole), then 8.54 (every piece through a column drew it), then **7.03 kg, its mass the optimiser's** (one piece a column, the nearest column's height, the skin's voxel taken from under it: within 3 % of the field's 1,278 cm³), **but beds 131 µm, tilt 1.66 ×, 478 Hz** | **a failed attempt:** the overlapping pieces (the free run's lines over the spokes, the ridges, the arcs) still fused into masses under the blur and the fillets, and the mount arms, drawn from the corridors' own metal, came out thin at their roots. Off by default (`LOOP_NETWORK_DRAW=1` to try it). A clean drawing wants a network whose pieces do not overlap, and the arms drawn as pieces too |

Pictures face-on (`look.py <design> face`, new) compare a design's end faces with the production photos. Shaded with normals split at creases (`look.py`, 09:05), a mesh's flat end wall no longer looks like a cone.
