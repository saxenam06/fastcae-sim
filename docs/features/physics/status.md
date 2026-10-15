# Physics and the judge

The deterministic judge every design passes through:
- the TET10 mesh;
- statics for every load case, modes, and a uniform-temperature case;
- the interface measures at the bearing seats;
- the verdict against the contract's limits.

It is verified independently before it judges anything, with analytic cases, a second solver and fault injection. Every other feature trusts its numbers, and no agent ever writes one.

**PBI key:** PHY · **State:** nothing built in `src/`. Decided: the FE model's practice (supports, joints and bearing loads by distributing couplings, 02:15), the 25 % model margin read strictly (09:09), and the misalignment measure (09:57). The loop's prototype judge (`prototypes/first_loop/fe.py`) has proven what PHY-1 and PHY-5 take (Rules in force, Measured) · **Updated:** 2026-10-09 12:47 by Claude
**Code:** to come: `src/zenryx/physics/`, its checks in `checks/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| PHY-1 | The cuDSS static solve, copied from fastcae `fastcae-v1:src/fastcae/simulate/`, with its unit load cases. The couplings are eliminated exactly, and one single-precision factor serves every load case and the modes, as in the loop's prototype | Parity with fastcae within 10⁻¹⁰ on a reference mesh; reaction balance on every solve; the loop's `box1_fl`, on the prototype's mesh, within 0.1 % of the prototype's numbers |
| PHY-5 | The mesh: fastcae's face-by-face mesher (`fastcae-v1:src/fastcae/simulate/face_mesh.py`), with the CAD hygiene the loop learned. No hairline faces: outlines kept off cylinders, near-coincident planes snapped, small faces healed, a heal kept only when its surface test mesh passes | The loop's three designs that cannot be solved today (`boxint1`, `boxint2`, `box1_sw`) mesh, and solve in single precision in under 10 refining steps |
| PHY-2 | The verification set: analytic cases (a thick cylinder under pressure, a cantilever, a cantilever's and a free ring's first frequencies, a uniform-temperature ring), fault injection (a missing support, a reversed load, a swapped bearing), and the noise protocol at two mesh sizes | Every case within its stated tolerance; every fault caught; the noise recorded |
| PHY-3 | Modes: the mass matrix and shift-invert Lanczos on the cuDSS factor (the prototype's start: a lumped mass, Lanczos about zero on the single factor, its inner solves refined to 10⁻⁷) | The analytic modes, and Code_Aster's, within tolerance |
| PHY-4 | Each bearing's loads by a distributing coupling over its whole seat, from the bearing's load centre (02:15), with the bearing's own stiffness (00:57). The interface measures: the bearing's misalignment (the seat's tilt against its shaft's line plus the shaft's own bend, 09:57), the centre-distance change, the seat's ovalisation | Measures correct on an analytic two-seat case; the coupling's sensitivity recorded |

## What runs

Nothing in the product yet. The loop's prototype judge runs outside `src/`: `prototypes/first_loop/fe.py` (the [loop's page](../loop/status.md)).

## Rules in force

- **Single precision on purpose:** the factor is single precision so it fits the 8 GB card; never a double factor.
- **Couplings exact, never penalties:** each coupling (a mount held, the halves tied at a bolt) is eliminated from the stiffness (T'KT, the slaves chosen by a pivoted QR). A penalty caps any factor's accuracy near a relative residual of 2-5·10⁻⁸, above the refinement's line. That cap is what pushed the night's prototype into a double factor.
- **One single-precision factor per design** serves every load case and the modes. Conjugate gradients refine to 10⁻¹⁰; GMRES on the same factor takes over when they stall. A solve that does not refine is a fault to diagnose, never a reason for a double factor.
- **A stall points at the CAD first:** faces narrower than about 0.5 mm (width = 2·area/perimeter) make the stiffness unsolvable in single precision. They are cured in the CAD.
- **One heavy job at a time,** with memory checked first.
- **No verdict inside the measured noise.**

## Measured

From the loop's prototype judge (9 October), not yet the product's:
- **Exact couplings change nothing but the accuracy:** `lobed_e10`'s seat motions and modes came within 0.3 % of the night's penalty model, at a residual of 7.9·10⁻¹¹.
- **Clean designs refine in 4-7 steps,** to residuals of 4·10⁻¹² to 10⁻¹⁰, with twelve modes in 20-35 s.
- **Hairline faces stalled the solves:** faces 0.02-0.03 mm wide, where a polygon outline ran along a true cylinder. Those designs took 34-60 steps or never refined. Cured in the CAD, `hyb3` went from 34 steps to 4, and its modes from 111 s to 21.
- **The unscaled stiffness's factor took over 10 minutes;** scaling by the diagonal is kept.
- **GMRES on the single factor converges, slowly:** `hyb3` reached 1.2·10⁻⁸ after 517 steps before its CAD was cured.
- **Three designs still cannot be solved** (`boxint1`, `boxint2`, `box1_sw`): ribs inside the housing meet its walls on narrow lands. PHY-5's mesher is the cure to try.

The full account: [the record, night to noon](../loop/2026-10-09-record-night-to-noon.md), sections 3.1 and 8.1.

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| The FE model follows industry practice | Bolted joints by distributed couplings; bearing loads spread over each seat, with the bearing's own stiffness (the seat model that cut the model-to-test error from 26.6 % to 11.7 % in FZG 2022), not point loads. The casting's own variation and the simplifications that remain are what the model margin covers | 2026-10-09 00:57, the engineer |
| **Supports, joints and bearing loads in the FE** | The housing's mount bosses are held fixed through distributing couplings. The two halves (split across the shafts) are joined at each bolt by distributing couplings. Each bearing's loads enter through a distributing coupling from a reference point at the bearing's centre (a tapered bearing's load centre) to every node of its seat face, so the load spreads over the whole seat's mesh | 2026-10-09 02:12-02:15, the engineer |
| **The model margin stays 25 %** | The judge keeps a 25 % margin between the FE value and each limit, a factor of safety for what the model leaves out (the casting's variation, the simplifications that remain). It costs some metal. Tying it to the model's level, folding in the measured mesh noise and recalibrating it against tests come later | 2026-10-09 01:06, the engineer |
| **The margin read strictly** | A design passes a limit when its FE value is at most 0.75 × the limit: a tapered seat, 0.375 of its 0.5 mrad. The limit is never relaxed to make a design pass | 2026-10-09 09:09 (confirmed as already agreed) and 09:29 ("keep it strict"), the engineer |
| **The bearing's misalignment** | The seat's tilt against its shaft's line (from the FE), plus the shaft's own bend at that bearing (from the load tool), per load case as a vector, against the bearing's line. One limit, not split between the housing and the shaft | 2026-10-09 09:57, the engineer |

## Open

- The physics of the MVP (D6, D6a, D6b in the [decisions](../product/decisions.md)) is not yet decided.
- **The gear mesh misalignment** (each mesh's lead slope, the measure Hexagon and GRM optimise a housing for) is not measured yet; the bearings' misalignment stands in for it.
- **Later, agreed in principle (01:06):** a margin per model level (a finer model earns a smaller one); the mesh-convergence noise measured on each design (PHY-2's protocol) and added to the margin; the margin recalibrated when test or published measurements of a housing are at hand.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- The plan, sections 5.2 (the solve), 6 (physics and the verdict) and 12 (P0-P1): [plan.md](../product/plan.md).
- What the loop's prototype taught the judge: [the record, night to noon](../loop/2026-10-09-record-night-to-noon.md).
- The evidence: fastcae's [gearbox-housing engineering report](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md), and fastcae's [solver choice](../../../../fastcae/docs/research/solver-choice.md).
