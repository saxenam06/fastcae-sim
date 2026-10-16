# The rib field on the walls: the plan and the state (LOP-34, the restart)

**Read this first after a compaction or in a new session.** It is the working memory of this job.

**The engineer's goal (16 October, ~10:00 IST):** "beat every line of production housing and provide a plausible realistic and production quality design", by the rib field on the walls (chosen over feature families from a library and over redrawing a passing design). The mass line is the production housing's, 7.73 kg: our optimised designs pass at 4.5-5 kg, so up to about 2.5-3 kg is there to buy a clean, production-like form.

**Updated:** 2026-10-16 10:20 (IST) by Claude, cloud session, branch `product/end-to-end`. Code in `prototypes/rib_walls/`; outputs in `data/rib_walls/`.

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
| 2. The field and features in the model, derivatives checked | next |
| 3. A 5 mm trial, the field pictured on the walls | |
| 4. The 4 mm run | |
| 5. The drawing, pictured before FE | |
| 6. FE, castability, the grade, the sheet beside the reference | |

## How to resume

Python: the scratchpad venv; `PYTHONPATH=checks/support/gpu_on_cpu:src`. Start every long job detached (`setsid nohup`): the session's worker restarted twice on 16 October and took foreground jobs with it.
