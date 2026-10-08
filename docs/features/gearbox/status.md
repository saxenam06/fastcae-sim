# Gearbox domain

The gearbox's physics before any housing exists. From a contract's gear train, torques and packaging it works out:
- the forces at each mesh;
- the spacing along each shaft;
- the loads each bearing puts into its seat, for every load case;
- the bearing sizes, and the mesh orders.

It turns a posed contract into a derived one that can be frozen. The judge applies these seat loads to every design.

**PBI key:** GBX · **State:** planned. The load tool's plan is written (equations, sources, checks) and committed in bbcdbac on `product/end-to-end`, not pushed; nothing is built yet. The gear-train kinematics it builds on exist in `zenryx.contract.train` and `zenryx.contract.involute`. Since 01:06 the contract carries what GBX-1 and GBX-2 need from the engineer: one order-check speed (6,000 rpm), the seal allowance per shaft end, and the least clearances for step 5's check (uncommitted) · **Updated:** 2026-10-09 01:22 by Claude
**Code:** to come, under `src/zenryx/domains/` (CLAUDE.md: domain roles live in a domain module)

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|
| GBX-1 | Mesh forces and moments for helical, profile-shifted gears (the base-circle form), with their directions in each load case ([plan](2026-10-08-load-tool-plan.md)). Done when the invariants hold, the forms agree at zero shift, and Shigley's and Łódź's force numbers are reproduced | Claude · LAPTOP-IR8VEG53 · `product/end-to-end` | 2026-10-09 02:28 | Claimed; starting from the prototype `prototypes/helical_forces/forces.py` and the plan's §4 |

## Next

| PBI | Goal | Done when |
|---|---|---|
| GBX-2 | The layout along the shafts (gap-driven or coordinate-driven, centres from a datum) and the bearing reactions, axial moments included: steps 5 and 6 | The textbook example's seat loads and Shigley's and Łódź's reactions are reproduced; an FE beam agrees; injected faults are caught |
| GBX-3 | The shaft sections (strength and stiffness) and the bearing selection (life, bore, capacity, arrangement), iterated with the layout: steps 7 and 8 | Shigley Ch. 7's shaft and Ch. 11's and Łódź Ch. 5's worked selections are reproduced; the loop settles on the textbook example |
| GBX-4 | Derive the Ivanov contract: seats and load cases stamped; the validator accepts it as derived; it freezes | The contract freezes, and the UI's planned calculations show their results |

## What runs

- Nothing of the load tool yet.
- What it builds on:
  - `zenryx.contract.involute.mesh_geometry`: a shifted pair's pressure angles, its reference, base, working pitch and tip diameters, and its working centre distance (committed in e32000d; the tip diameters since 01:06, uncommitted). GBX-1's forces start from its working pressure angle and base diameters;
  - `zenryx.contract.train`: the ratio, shaft speeds, mesh frequencies, and the shaft angle from the packaging offset; since 01:06 the axes' end-view positions (`axis_positions`) and how far two circles on different shafts overlap end-on (`end_view_overlap`), for step 5's clearance check;
  - the contract's `shaft_layout`: the gaps, the seal allowance and the sealed shaft ends, and the least clearances (the contract page lists them).

## Rules in force

- Derived physics is computed, never typed: every value the tool writes is stamped with the tool, its version and the input hash (CLAUDE.md).
- Paid standards (ISO 6336, ISO 281) never enter the repository. Their public formulas are taken from textbooks and catalogues.

## Measured

- **Profile shift matters for Ivanov:** at 150 N·m the radial mesh force is +13.8 % (stage 1) and +10.4 % (stage 2) above the textbook formula; tangential −2.1 % and −1.6 %; axial unchanged.
  - The torque check (Ft × working radius) holds exactly.
  - Source: the prototype `prototypes/helical_forces/forces.py` (on `zenryx.contract.involute`), 8 October 21:00; rerun at 21:30 with the same numbers.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| How sources are combined | Each step from the source that gives it best and still holds for helical gears, starting from what all sources agree on, each step with its confidence | 2026-10-08 20:59, the engineer |
| Mesh forces of shifted gears: the base-circle form | Fbt = 2T/db, then Ft = Fbt·cos αwt, Fr = Fbt·sin αwt, Fa = Fbt·tan βb (plan §4); for Ivanov the radial force is 10-14 % above the textbook form. drivetrainhub confirms it | 2026-10-09 00:57, the engineer |
| Bearing life, shaft material, bearing table | Bearing life 944 h (A4), taken at the drive case throughout. The shaft material is a common gear steel, labelled as an assumption. The bearings come from a maker's public catalogue, cited | 2026-10-09 00:50, the engineer |
| **The layout is gap-driven** | The gaps are the layout's inputs, held in the contract with the bearing arrangement (`requirement.shaft_layout`): bearing to gear, behind each bearing, between two gears on one shaft. Step 5 places the gears and bearings from them, centres from a datum, and the round (steps 5-8) changes only the bearings' widths, so the positions follow | 2026-10-09 00:06, the engineer |
| **One order-check speed: 6,000 rpm** | The mesh orders are checked against the housing's modes at the rated speed alone, the cruise, at least 3 % apart. The criterion names the duty's speed (`order_check_at: rated`) | 2026-10-09 01:06, the engineer |
| **The seal allowance per shaft end; the clearances calculated** | Where a shaft leaves the housing, the bearing has a seal's space behind it (11 mm, A16) on the ends the contract names (input −z, output −z and +z, A17); the intermediate's bores are closed, so its bearings keep the closed-bore space. Step 5 calculates every clearance from the layout: along the shafts between parts on different shafts that overlap end-on (at least A18's 3 mm; Ivanov's stage-1 gear and output gear overlap by 31.4 mm), and from the gear tips to the wall (at least A19's 8.25 mm). Taken before GBX-1 | 2026-10-09 01:06, the engineer |
| Where confidence is low, search | A targeted web search for that point only, the finding recorded with its source. Helical gearboxes are a proven trade, so the information exists. Done for the shifted-gear convention and the tapered pair (plan §3a) | 2026-10-08 21:02, the engineer |

## Open

- **The layout's values, as assumed** (A13-A19 in the Ivanov contract):
  - 12.7 mm between a bearing and its gear and 6.35 mm behind a bearing in a closed bore, both from Shigley's Fig. 18-2, an industrial gearbox, so likely generous;
  - 12.7 mm between the intermediate shaft's two gears, and 3 mm least clearance along the shafts: no source yet;
  - 11 mm behind a bearing where its shaft leaves (an 8 mm radial shaft seal and 3 mm for its seat), and 8.25 mm from the gear tips to the wall (Łódź's (1.1-1.2)·δ).

  Tighter, sourced values for an EV reducer are wanted ([research](../../research/2026-10-08-bearing-positions.md)).
- **Proposed:** the bearings' speed limits checked at the duty's maximum, 8,673 rpm. The order check now uses the rated speed alone, and a bearing must still run at the top speed.
- Equilibrium does not place the bearings; it judges a layout, through its reactions. The bearing arrangement is chosen per shaft: locating and floating, or an adjusted pair like Ivanov's intermediate tapered one. Not one rule for all.
- **Bearing selection needs a bearing table:** ISO 15 dimensions, public, and a maker's dynamic ratings C, cited. The life and loads constrain the choice with the bore, the capacity and the arrangement.
- **The shaft sections are now step 7** (the engineer, 23:37): strength and stiffness; their material is an assumption to add.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- [2026-10-08-load-tool-plan.md](2026-10-08-load-tool-plan.md): the load tool's equations, sources and checks.
- [2026-10-09-gaps-along-a-shaft.html](2026-10-09-gaps-along-a-shaft.html): an interactive explainer of the layout's gaps, made for the engineer (9 Oct 00:22), published privately at https://claude.ai/artifact/QouM3otg2WGmEeJM8LYUDJ. It covers what fills a gap; how the span sets the bending; overhung gears; the seat's material; oil and heat; where the housing puts material; the round of steps 5-8; and (since 01:02) the three shafts. That last section shows Ivanov's end view to scale, where the output wheel overlaps the stage-1 wheel by 31 mm, the side view, and a live clearance check of every pair that overlaps. Its numbers come from simple beam formulas on Ivanov's input shaft, for intuition only.
