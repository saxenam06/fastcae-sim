# Gearbox domain

The gearbox's physics before any housing exists. From a contract's gear train, torques and packaging it works out:
- the forces at each mesh;
- the spacing along each shaft;
- the loads each bearing puts into its seat, for every load case;
- the bearing sizes, and the mesh orders.

It turns a posed contract into a derived one that can be frozen. The judge applies these seat loads to every design.

**PBI key:** GBX · **State:** planned. The load tool's plan is written (equations, sources, checks); nothing is built yet. The gear-train kinematics it builds on exist in `zenryx.contract.train` and `zenryx.contract.involute` · **Updated:** 2026-10-08 21:01 by Claude
**Code:** to come, under `src/zenryx/domains/` (CLAUDE.md: domain roles live in a domain module)

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| GBX-1 | Mesh geometry and forces for helical, profile-shifted gears, with their directions in each load case ([plan](2026-10-08-load-tool-plan.md)) | The invariants hold; the forms agree at zero shift; Shigley's and Łódź's force numbers are reproduced |
| GBX-2 | Spacing along the shafts and the bearing reactions, axial moments included | The textbook example's seat loads and Shigley's and Łódź's reactions are reproduced; an FE beam agrees; injected faults are caught |
| GBX-3 | Bearing sizes by L10 life | Łódź Ch. 5's and Shigley's worked selections are reproduced |
| GBX-4 | Derive the Ivanov contract: seats and load cases stamped; the validator accepts it as derived; it freezes | The contract freezes, and the UI's planned calculations show their results |

## What runs

- Nothing of the load tool yet.
- What it builds on:
  - `zenryx.contract.involute`: the working centre distance with profile shift;
  - `zenryx.contract.train`: the ratio, shaft speeds, mesh frequencies, and the shaft angle from the packaging offset.

## Rules in force

- Derived physics is computed, never typed: every value the tool writes is stamped with the tool, its version and the input hash (CLAUDE.md).
- Paid standards (ISO 6336, ISO 281) never enter the repository. Their public formulas are taken from textbooks and catalogues.

## Measured

- **Profile shift matters for Ivanov:** at 150 N·m the radial mesh force is +13.8 % (stage 1) and +10.4 % (stage 2) above the textbook formula; tangential −2.1 % and −1.6 %; axial unchanged.
  - The torque check (Ft × working radius) holds exactly.
  - Source: scratchpad `helical_forces.py` with `zenryx.contract.involute`, 8 October 21:00.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| How sources are combined | Each step from the source that gives it best and still holds for helical gears, starting from what all sources agree on, each step with its confidence | 2026-10-08 20:59, the engineer |
| Where confidence is low, search | A targeted web search for that point only, the finding recorded with its source. Helical gearboxes are a proven trade, so the information exists. Done for the shifted-gear convention and the tapered pair (plan §3a) | 2026-10-08 21:02, the engineer |

## Open

- The convention for shifted gears: the base-circle form is proposed (the plan's §4).
- The duty for bearing life: the drive case for all 944 h is proposed.
- The spacing along the shafts, and which bearings locate axially: assumptions, after the A8 pattern.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- [2026-10-08-load-tool-plan.md](2026-10-08-load-tool-plan.md): the load tool's equations, sources and checks.
