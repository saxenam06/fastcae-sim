# Handover to the cloud session, 15 October 2026

**Read this first, then [CLAUDE.md](../../../CLAUDE.md), the board ([docs/status.md](../../status.md)) and the loop's page
([status.md](status.md)).** The engineer moves from the laptop's Claude Code to a Claude cloud session (their weekly limit).
This page holds what the laptop's session knew that the repository did not: where the work stands, the final workflow and
how to run it, what a cloud session can and cannot do, the engineer's working rules, and what is open.

## 1. Where the work stands

- **The product:** zenryx designs housings from requirements. The first family is the EV two-stage reducer housing
  (the contract `checks/data/contracts/ev_reducer_posed.json`). The UI (`web/`) shows the contract, the optimisations and the
  designs; the optimisation workflow is a prototype pipeline in `prototypes/first_loop/`.
- **The engineer's choice (14-15 October):** the design to build on is **`baseline2_lw8`**, the agreed baseline with the
  least member width in plan of 8 mm (clear rib patterns), **drawn smooth from its own field with no new optimisation**.
  Not the spline runs (`spl8f6`: smooth but members a CAD designer would not accept). Not worried for now about the
  optimiser not holding the modes in FE's terms.
- **On the Designs tab:** `baseline2_lw8_smooth` (4.52 kg, worst seat 49.5 um against 52.2, tilt 0.80, first mode 514 Hz,
  but a mode at 2506 Hz within 3 % of the first gear order: fails that line). The cube drawing of the same field,
  `baseline2_lw8`, passes every line (4.94 kg, 34.4 um, tilt 0.69, 678 Hz): **the smooth drawing reads 44 % softer**, and
  where it loses the stiffness is not yet found (section 5).
- **The final workflow is wired end to end (LOP-31):** one recipe and one command (section 2). Proved on the laptop at 15:03-15:14: `run_final.py --run <baseline2_lw8's run>` rebuilt the layout from the contract (identical to the one the run was optimised on), drew and judged `final_1015_1503` (the same numbers as `baseline2_lw8_smooth`), wrote the Designs tab's records and `final_state.json`; called again, it said "up to date".
- **Committed on `product/end-to-end`:** `c5cde98` docs, `42ec2c5` UI, `b322b53` product code and checks, `3b08850` the
  workflow, and the wiring's commit after them. The engineer pushes it (or says to) before the cloud session starts: a cloud
  session sees only what is on GitHub. **Open the cloud session on the branch `product/end-to-end`**, not `main`: `main`
  (8 October) is 39 commits behind; per CLAUDE.md every PBI goes on `product/end-to-end` until the workflow runs end to end.

## 2. The final workflow

- **The recipe:** `src/zenryx/workflow/recipes/final.json` (moved there by LOP-33; the workflow itself is `zenryx.workflow`), versioned: the optimiser's arguments (the agreed baseline of
  `fm500_run.sh` with `--least-width 8`) and the drawing's settings (`LOOP_VOXEL_SMOOTH=3`, `LOOP_DRAW_SMOOTH=6`,
  `LOOP_DRAW_SMOOTH_RANGE=15`, `LOOP_DRAW_FINE=1`: `baseline2_lw8_smooth`'s drawing; the fairing is out until mount-1 holds,
  section 5). A change of setting is a change of this file, with a new version and the engineer's word (rule 3 below).
  `checks/loop/test_final_recipe.py` checks its shape.
- **The command:** `.venv/Scripts/python.exe -m zenryx.workflow.run` (on the laptop; `run_final.py` until LOP-33 moved every stage into `src/zenryx`). It fingerprints the
  contract and the recipe; rebuilds the layout from the contract when the contract changed (`contract_layout.py`,
  `setup_export.py`); runs `campaign_run.sh` (the optimisation, the drawing, FE, castability, oil-tightness, the grade and
  the Designs tab's records, under the memory guard); writes the outcome to `data/first_loop/final_state.json`. Nothing
  runs when neither the contract nor the recipe changed (`--force`). `--run <stem>` draws and judges an existing
  optimisation again (a drawing change); `--dry-run` prints the stages. About 25 minutes with the optimisation.
- **What the drawing does** (`outcome_cad.py`; [the loop page](status.md) and CLAUDE.md say more): each 4 mm column's
  height from the optimiser's cubes (half a cube or more is metal); the plan outline where columns hold metal, blurred over
  3 mm and read at its middle; the tops on one scale from the split, smoothed over 6 mm edge-preservingly (heights within
  about 15 mm of each other averaged, real steps kept); free edges rounded 3 mm, roots filleted 4 mm; the exact shell and
  interfaces in the same field; on a 1 mm grid; FE judges what is drawn. The fairing (`voxel_fair.py`: the outline as a
  signed distance smoothed along each member, the tops along their contours) is built but out of the recipe.

## 3. What a cloud session can and cannot do

- **Can:** read and change the code and the docs; run the checks (`uv sync --all-extras`, `uv run pytest checks -q`,
  `uv run ruff check src checks`, `uv run ruff format --check src checks`), the UI's `npm ci` and `npm run typecheck`;
  plan, review and write new code (the next steps in section 5 are mostly code).
- **Cannot:** run an optimisation or FE (they need the laptop's 8 GB GPU: cupy, nvmath's cuDSS; single precision on
  purpose); see `data/` (every run, field, mesh and judgement is git-ignored, on the laptop only); see the Designs tab's
  designs (their records, `web/src/records/{designs,process,optimisations,campaigns}`, are generated from `data/` and
  git-ignored). `tetgen` and `pymeshlab` are installed into the laptop's `.venv` outside `uv.lock`.
- **So:** a change that needs a run is prepared in the cloud, committed and pushed; the engineer pulls it on the laptop and
  runs `run_final.py` (the laptop's Claude session, or by hand), and its numbers come back through the docs.

## 4. The engineer's working rules (from the laptop's memory, which a cloud session does not have)

1. **The state lives in the repo:** every piece of work belongs to a feature and a PBI; the board and each feature's page
   say what is true now (not a log; the history is git's). The board, the features, the keys and the PBIs' order are
   Claude's to decide and record, never a question for the engineer.
2. **Commit, push and start servers only on the engineer's word,** each time.
3. **Ask before adding any setting to the baseline** (14 October 12:35). A run that passes only with an unagreed setting
   has not passed on the baseline.
4. **Explain plainly** (asked many times): where we are in two or three lines, then one decision with its options; name
   things exactly (the split flange, the bearing bosses), give each id a short name in brackets ("D2 (first product family)").
5. **Show pictures of geometry:** a picture for every try, looked at before it is shown.
6. **Never add or propose a double-precision factor;** cure the conditioning instead (slivers, flat tets).
7. **One heavy job at a time on the laptop,** free memory and the GPU checked first (two blue screens on 2 October); ask
   before heavy work while the engineer is at the laptop.
8. **Never patch files through a Bash heredoc;** write a script, then run it. Never rewrite a source with PowerShell's
   Get-Content/Set-Content.
9. **No GRC data, no paid standards, no third-party part data in git; no part-specific code in the core** (geometric kinds
   in code, domain roles in data).
10. **Derived physics is computed by a tool, never written;** a difference inside the mesh noise is a tie; a design is
    labelled with its rung (simulation-feasible, ...), never "production-ready".
11. **Search the web only where not confident,** one primary source, recorded; the research library is `docs/research/`
    (read its README first).
12. **Write findings into the repo as they happen** (the feature page, the dated record): a session can end without warning.
13. **Fast turnaround:** the peak drive case only; no extra solves without a measured need; never add a load case unasked.
14. **Keep CLAUDE.md current:** a new tool, rule or pitfall gets its line the same day.

## 5. What is open, in order

1. **The final drawing's stiffness.** `baseline2_lw8_smooth` reads 44 % softer than the cube drawing of the same field and
   its first mode 24 % lower, though it keeps the optimiser's metal (1.62 kg of its 1.63). Find where:
   `model_vs_fe.py <design>` (the optimiser's model on the drawing against FE), `lost_cubes.py <run> <design> <png>` (the
   optimiser's cubes outside the drawing, by place), `drawing_attrib.py`. Suspects: the 3 mm rounding of every free edge,
   the 2 mm kept round each mount's room (a 3 mm plate above each lug is lost), the arms' contact with the lugs. Then
   adjust the drawing only (a new recipe version) and judge again.
2. **The fairing parts mount-1 from its arm.** The faired drawing (`LOOP_VOXEL_FAIR=8:2:2.5[:1]` with `LOOP_SMOOTH=10`)
   looks much cleaner in close-up (`data/first_loop/zoom_fairz_cover_se.png`: the corrugated cliff faces and saw-teeth
   gone), but `propose.py`'s mount check stopped it twice: `baseline2_lw8_fair` (the outline 2.5 mm inward) and `final_lw8`
   (1 mm inward). So the outline's band is not the cause alone: suspect the tops smoothed along their contours
   (`voxel_fair.fair_tops`, always on with `LOOP_VOXEL_FAIR`) raising the arm's deep end at the lug, or Taubin's passes
   thinning the neck. Bisect on the laptop: draw with each part alone (give `fair_tops` its own switch), then
   `lug_probe.py <run> <design> mount-1` and `lost_cubes.py`. Until then the recipe leaves the fairing out.
3. **Wiring, step 2** (LOP-33, under way: the workflow, its gates, its state and the grade are in `src/zenryx/workflow` with parity checks; the heavy stages next): move the final workflow's stable parts from `prototypes/` into `src/zenryx` (the optimiser, the
   drawing, FE, the grade), each with a check that it gives the prototype's result; then an API call and a button on the
   UI that runs it, and a mark on the Designs tab when the contract changed since the last run.
4. **Housekeeping:** the loop page's Now cell has grown into a log (280 KB); rewrite it to the current state, the history
   left to git and the dated records.

## 6. Where things are

- The latest record: [2026-10-15-record-night.md](2026-10-15-record-night.md) (the spline runs, `spl8f6`, the model against
  FE). The decisions: the loop page's Decisions table.
- The runs and designs: `data/first_loop/` on the laptop (`flow_<design>.json`, `fe_<design>.json`, `grades.json`,
  pictures `look_<design>.png`, `closeups_<design>.png`).
- The UI: `npm run dev` on port 5190 (only on the engineer's word); its Designs tab reads `web/src/records/`.
