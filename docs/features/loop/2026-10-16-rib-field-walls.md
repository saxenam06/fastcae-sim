# The rib field on the walls: the plan and the state (LOP-34, the restart)

**Read this first after a compaction or in a new session.** It is the working memory of this job.

**The engineer's goal (16 October, ~10:00 IST):** "beat every line of production housing and provide a plausible realistic and production quality design", by the rib field on the walls (chosen over feature families from a library and over redrawing a passing design). The mass line is the production housing's, 7.73 kg: our optimised designs pass at 4.5-5 kg, so up to about 2.5-3 kg is there to buy a clean, production-like form.

**Updated:** 2026-10-16 13:45 (IST) by Claude, cloud session, branch `product/end-to-end`. Code in `prototypes/rib_walls/`; outputs in `data/rib_walls/`.

## Why the first attempt failed (`prototypes/rib_housing/`, [its record](2026-10-16-rib-field-housing.md))

`rib_h3c` passed four lines of five but looked poor and was worse than the reference (7.01 kg and 55 µm against 4.52 kg and 49 µm). The method drifted from the toy's: ribs lived on the plan columns, so a side wall could carry none; "solid zones" of free metal round the bores and mounts held 3.1 of the 4.4 kg (the terraced blobs); one spacing (24 mm) and two families everywhere made a ladder in one corner; and the drawing was patched again and again to get through FE, never looked at until the end. Rules were added without the engineer's word.

## The method

1. **The walls are the surfaces the ribs stand on** (`surface.py`, done): every free cube of the product's model is mapped to the shell beneath it (the contract's exact cup with the plate under the other half's opening): its distance out `d`, the wall's normal `n`, a tangent frame. A rib at angle theta runs along t in the wall's tangent plane, stands along n, and is thick along m = n x t: plates on the end walls, radial fins on the side walls, gussets under the flange, all one field.
2. **The field:** two rib families at right angles, each with a thickness share and a height (cubic B-splines in space, read at each cube's foot on the wall), the directions a smooth turn from where the strains first put them (the toy's, checked). A cube's stiffness is its ribs' laminate turned into its own frame.
3. **Bosses and brackets as production features, sized by the optimiser:** a ring boss round each bearing's seat (its outer radius and height), and each mount's bracket as two gusset webs from the lug to the wall (their thickness and spread), never free blobs.
4. **The problem:** the product's own (`mass_tilt`: least metal, every tilt and bed at 1/1.5 of its line, the peak drive), the budget's remainder a ceiling, with fastcae's rules (thickness constant along a rib, tapered heights).
5. **The drawing, production-quality:** each rib a plate of one thickness along it (draft, rounded top, root fillets, tapered ends), standing on the exact shell; the bosses and webs as their CAD shapes; the product's exact cuts. **Looked at before FE**, each step pictured for the engineer.
6. **Judged** by the product's FE on the CPU (validated on the reference: statics to 1 µm, modes within 0.4 %), castability, oil-tight, the grade.

## Settings (agreed by the engineer, 16 October ~10:25 IST)

| Setting | Agreed | Why |
|---|---|---|
| Least rib thickness | 8 mm | the product's least member width (`--least-width 8`); thinner plates fold FE's 7 mm surface |
| Thickest rib | 12 mm (at a boss), 8-10 away | production's 6-12 mm, thickest at the roots |
| Rib spacing | 40 mm | production's end-wall ribs stand 30-60 mm apart; 24 mm made a ladder |
| Rib height | up to 24 mm off the wall | the recipe's band |
| Families | two, at right angles | radial and ring, or crossing; one family where the other is empty |
| Ring boss | outer radius and height per bearing | production's bosses |
| Mount bracket | two webs per lug, thickness and spread | production's gusseted lugs (`LOOP_LUG_WEBS` of 13 October) |
| The modes | not held in the run (the CPU's time); FE reads them | as before |

## Steps and their state

| Step | State |
|---|---|
| 1. The walls (`surface.py`) | **Done.** 91,523 free cubes mapped: none inside the shell, the distance a true one (its gradient 1.000); motor side 25,181 over faces across the pull and 29,234 beside faces along it, cover 18,577 and 18,531. Distances up to 100 mm only in the mounts' reach (the brackets' room). `data/rib_walls/walls_4.png` |
| 2. The field and features in the model, derivatives checked | **Done** (`wallfield.py`, `wallrules.py`, `gradcheck.py`; 5 mm). The frame against the toy's checked rotation: equal; a plate stores nothing across itself. A tilt, a bed and the mass by every field kind (two thicknesses, two heights, the turn) agree to 10⁻⁶-10⁻⁸; the bosses' radius and height to 10⁻⁵; the rules to 10⁻⁹. Fixed on the way: the shares made smooth (C¹: the linear ones' kinks read 0.3-5 % off), the features joined as a union (1 − Π(1 − v), not a clipped sum), each web's spread kept to the angles whose ray meets the wall (mounts 2 and 3 stand 105 mm off it; their rays miss past 20°, and a web there ran "402 mm" into nothing), and no reach inside a web's share (it jumped where a ray grazed a room). |
| 3. A 5 mm trial, the field pictured on the walls | **Done** (`w5c`, below), and judged by FE: it fails, the drawing losing what the field held (below). Next: the second stage, discrete ribs sized by the model. |
| 4. The 4 mm run | |
| 5. The drawing, pictured before FE | |
| 6. FE, castability, the grade, the sheet beside the reference | |

## What the model holds, beyond the agreed settings (each a castability or a fault the trials showed)

- **Side walls carry fins along the pull only.** On a face along the pull only family 0 stands, at angle 0 (along the pull), its thickness and height read at the split above its foot: a fin of one section from the flange down its wall, as production's side-wall ribs. A rib across the pull on a side wall, or one whose height changed down the wall, is an undercut for the two-part mould. On the end walls both families and their turn stay free (drawn along the pull, any direction casts).
- **A ring boss stands on the wall under it** (`w5b`): a round boss on the bearing's axis from whatever lies under it in its half (a cap on the bore's end wall, a collar down a tall tube to the wall below, or hanging from the split) up to its height past the bearing's outer end. Capped only (`w5a`), the seats at the far ends of the cover's tall tubes (intermediate +z: a 66 mm tube; output +z) held 1.6 and 1.17 x their bed line with every boss at its largest. A collar ending short of the wall below would be an undercut.
- **The webs run from the lug's far end to the split** (`w5c`), joining the flange: production's gusseted lug as the engineer gave it on 13 October (`LOOP_LUG_WEBS`). Over the lug's 30 mm height alone (`w5b`) the webs sat at their 16 mm cap and were among the beds' strongest levers (the bed's derivative by a web's thickness -11 to -16), and the bosses grew into drums instead.

## The trials (5 mm, the product's problem: least metal, every line at 1/1.5, the budget's remainder 3.81 kg)

| Trial | Changed | Placed (kg) | Lines | What it showed |
|---|---|---|---|---|
| `w5a` | (the first) | 4.32 at it 19, still rising | bed intermediate +z 1.63 x, tilt 1.12 x | the bosses capped only cannot hold the tall tubes' seats; stopped |
| `w5b` | bosses standing on the wall under them | 4.71 (ribs 0.66, features 4.05) | all held (1.000, 1.004) | over the budget 23.5 %: 8.63 kg in all; drawn (2 mm) 7.96 kg: the bosses drums (the cover's intermediate one 81 mm in radius), few ribs (`look_walls_w5b.png`) |
| `w5c` | webs from the lug to the split | 2.35 (ribs 0.49, features 1.86) | all held (0.999, 1.007), every rule met | 6.27 kg in all at 5 mm, under production's 7.73; most bosses back at their least; drawn (2 mm) 5.58 kg, 13 of 13 bolts, 2.9 % of the feature cubes lost (`look_walls_w5c.png`): the motor side reads as a casting (compact ring bosses, gusseted lugs to the flange); the cover's intermediate +z tower a plain 76 mm drum, its end-wall ribs scattered short pieces (they live in patches only); being judged by FE |

## `w5c` judged by FE, and why it failed (16 October ~12:50 IST)

FE (the 2 mm drawing, the needles merged, 1.06 M unknowns, residual 1e-11): **5.43 kg, the worst seat 104.8 µm (line 52.2), tilt 1.81 x, first mode 626 Hz, two order clashes: fails.** The model held every line at 1/1.5, so FE reads the design about 3 x softer.

`model_vs_fe.py w5c walls_w5c --voxel=5` splits the gap: the model on the drawing (voxelised onto its cubes) reads tilt 2.76 and bed 2.05 against the field's 1.00 and 1.01, and FE's tilt 2.7 on the same drawing. So the model is fair on what is drawn; **the drawing lost what the field held**:

- the field smears each rib family over its cubes at 40 mm spacing; where a live patch is narrower than that, the drawn stripes may miss it;
- the drawing put fins only outside the plan footprint, while the model has them on every side wall: the tubes standing below a gear room's end face carry fins in the model and none in the drawing (intermediate -z: tilt 1.00 -> 2.76).

**The cure (next): the de-homogenisation's second stage.** Freeze the layout the field found (the end walls' stripes, regular radial fins round every tube), and size those discrete ribs with the model reading them as metal (each cube's share of the drawn ribs), so the model and the drawing are one geometry.

Getting FE to mesh `w5c` taught three things about the judge (prototype only, the product's FE untouched): `judge.py --needles` (`needles.py`) merges the coarsened surface's needles (edges of 1e-4 mm, where the product's collapse falls back) and keeps the surface fine round a flat tet before meshing again (32,000 tets under 1e-5 in one cell had stopped the single factor, residual 30); the members end 5 mm past each bolt's head socket (`SOCKET_CLEAR`: on the boss's edge they made hairlines); a boss under 4 mm proud is drawn flush (`BOSS_SNAP`).

## The engineer's review (16 October ~13:30 IST): stopped

Against the plate's clean result (the toy with fastcae's rules, `prototypes/rib_field/`), the engineer judged `walls_w5c` "noisy sketchy stretchy bad unorganised distorted ribs", and said **"Stop everything"**. Nothing runs. The pictures: [`look_walls_w5c.png`](2026-10-16-rib-field-walls/look_walls_w5c.png), [`look_face_walls_w5c.png`](2026-10-16-rib-field-walls/look_face_walls_w5c.png), [`field_w5c.png`](2026-10-16-rib-field-walls/field_w5c.png) (the field on the walls), [`look_walls_w5b.png`](2026-10-16-rib-field-walls/look_walls_w5b.png) (the drums), [`section_walls_w5c_cover.png`](2026-10-16-rib-field-walls/section_walls_w5c_cover.png) (the land's chamfer where the cover's last flat tets sat).

What was measured, in answer to the review:

- **The rules were thin.** The plate held all of fastcae's rules: ribs end on a boss or an edge, never in air (the arrival rule), the bend rule, a rib no higher than the boss it meets, a least length, and the drawing's gate. The housing held two (constant thickness along a rib, tapered tops), on the end walls only. That is the main reason for the look.
- **The ribs live in patches:** in the converged field 275 and 345 of the 2,291 end-wall points carry a live rib (12-15 %), often in patches narrower than the 40 mm spacing; the drawn stripes are cut at the patches' edges, which makes the stubs.
- **The ribs are low, not sunk:** the model's stand 22 mm (median), the drawn ones 12-18 mm, because the drawing tapers each rib's height to its ends (8 mm plus 1 mm a mm from the end) and most pieces are short. They reach 4 mm into the wall, so they are joined to it; about 9.5 mm thick, the bottom of the agreed 8-12.
- **What was dropped between the field and the drawing:** the fins on the inner side walls (never drawn), patches narrower than the spacing, pieces under 30 mm, 4.6 % of the bosses' and webs' cubes. The model on the drawing reads tilt 2.76 against the field's 1.00.
- **The needles:** where the members meet the product's exact parts at nearly the same place (the flange's top, the land's edge, the bolt sockets), the 2 mm drawing grid and the exact cuts leave vertices 1e-4 mm apart; no rule kept a member clearly into or clearly clear of an exact part. The plate had no such parts, and its judge solved in double precision, which tolerates a flat tet; the housing uses the product's single factor, which one flat tet stops.
- **The needle merge did not change the shape:** 12 of 11,542 triangles removed, vertices moved at most 0.02 mm, FE's mass 5.43 kg against the drawing's 5.42. But a repair is the wrong direction (the engineer: "you must enforce rules such that these issues don't even come").
- **The "wait for rib_h3c's judgement" task** was an idle loop left from the first attempt (a log line that never came); it computed nothing, and ended on its time limit.

## Next, proposed and waiting for the engineer's word: rules upstream, so these issues never arise for any contract

1. **Every wall gets the plate's rules:** a rib ends on a boss, a bolt's boss, a lug or a rim, never in air; a least length and a bend limit; no higher than the boss it meets; at least 8 mm tall or none (no taper to nothing mid-wall).
2. **No near-coincident faces:** a member overlaps an exact part by at least a drawing cell or keeps at least 3 mm clear of it; nothing thinner than two drawing cells; a boss flush or at least 4 mm proud.
3. **The model sizes exactly what is drawn:** the layout frozen (the end walls' stripes, regular fins round every tube, the inner ones too) and its discrete ribs sized as metal, so nothing drops between the two.
4. **A geometry gate before FE** that refuses a drawing with needles, slivers or coincident faces, instead of repairing the mesh.

Each step pictured before any long run. Step 3 alone mends the model's gap to the drawing, not the look: the look needs 1, 2 and 4.

## How to resume

Python: the scratchpad venv; `PYTHONPATH=checks/support/gpu_on_cpu:src`. Start every long job detached (`setsid nohup`): the session's worker restarted twice on 16 October and took foreground jobs with it.
