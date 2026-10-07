# Physics and the judge

The deterministic judge every design passes through:
- the TET10 mesh;
- statics for every load case, modes, and a uniform-temperature case;
- the interface measures at the bearing seats;
- the verdict against the contract's limits.

It is verified independently before it judges anything, with analytic cases, a second solver and fault injection. Every other feature trusts its numbers, and no agent ever writes one.

**PBI key:** PHY · **State:** nothing built · **Updated:** 2026-10-07 11:15 by Claude
**Code:** to come: `src/zenryx/physics/`, its checks in `checks/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| PHY-1 | The cuDSS static solve, copied from fastcae `fastcae-v1:src/fastcae/simulate/`, with its unit load cases | Parity with fastcae within 10⁻¹⁰ on a reference mesh; reaction balance on every solve |
| PHY-2 | The verification set: analytic cases (a thick cylinder under pressure, a cantilever, a cantilever's and a free ring's first frequencies, a uniform-temperature ring), fault injection (a missing support, a reversed load, a swapped bearing), and the noise protocol at two mesh sizes | Every case within its stated tolerance; every fault caught; the noise recorded |
| PHY-3 | Modes: the mass matrix and shift-invert Lanczos on the cuDSS factor | The analytic modes, and Code_Aster's, within tolerance |
| PHY-4 | Bearing loads as a cosine distribution over each seat's loaded half; the interface measures (relative seat tilt per face width, centre-distance change, seat tilt and ovalisation) | Measures correct on an analytic two-seat case; the coupling's sensitivity recorded |

## What runs

Nothing yet.

## Rules in force

- **Single precision on purpose:** the factor is single precision so it fits the 8 GB card; never a double factor.
- **One heavy job at a time,** with memory checked first.
- **No verdict inside the measured noise.**

## Measured

-

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|

## Open

- The physics of the MVP (D6, D6a, D6b in the [decisions](../product/decisions.md)) is not yet decided.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- The plan, sections 5.2 (the solve), 6 (physics and the verdict) and 12 (P0-P1): [plan.md](../product/plan.md).
- The evidence: fastcae's [gearbox-housing engineering report](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md), and fastcae's [solver choice](../../../../fastcae/docs/research/solver-choice.md).
