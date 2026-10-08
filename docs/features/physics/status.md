# Physics and the judge

The deterministic judge every design passes through:
- the TET10 mesh;
- statics for every load case, modes, and a uniform-temperature case;
- the interface measures at the bearing seats;
- the verdict against the contract's limits.

It is verified independently before it judges anything, with analytic cases, a second solver and fault injection. Every other feature trusts its numbers, and no agent ever writes one.

**PBI key:** PHY · **State:** nothing built; the FE model's practice is decided (supports, joints and bearing loads by distributing couplings, 02:15), and the model margin stays 25 % for now (Decisions) · **Updated:** 2026-10-09 02:16 by Claude
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
| The FE model follows industry practice | Bolted joints by distributed couplings; bearing loads spread over each seat, with the bearing's own stiffness (the seat model that cut the model-to-test error from 26.6 % to 11.7 % in FZG 2022), not point loads. The casting's own variation and the simplifications that remain are what the model margin covers | 2026-10-09 00:57, the engineer |
| **Supports, joints and bearing loads in the FE** | The housing's mount bosses are held fixed through distributing couplings. The two halves (split across the shafts) are joined at each bolt by distributing couplings. Each bearing's loads enter through a distributing coupling from a reference point at the bearing's centre (a tapered bearing's load centre) to every node of its seat face, so the load spreads over the whole seat's mesh | 2026-10-09 02:12-02:15, the engineer |
| **The model margin stays 25 %** | The judge keeps a 25 % margin between the FE value and each limit, a factor of safety for what the model leaves out (the casting's variation, the simplifications that remain). It costs some metal. Tying it to the model's level, folding in the measured mesh noise and recalibrating it against tests come later | 2026-10-09 01:06, the engineer |

## Open

- The physics of the MVP (D6, D6a, D6b in the [decisions](../product/decisions.md)) is not yet decided.
- **How the 25 % applies, proposed:** a design passes a limit when its FE value is at most 0.75 × the limit. The other reading, 1.25 × the value within the limit, allows 0.8 × the limit.
- **Later, agreed in principle (01:06):** a margin per model level (a finer model earns a smaller one); the mesh-convergence noise measured on each design (PHY-2's protocol) and added to the margin; the margin recalibrated when test or published measurements of a housing are at hand.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- The plan, sections 5.2 (the solve), 6 (physics and the verdict) and 12 (P0-P1): [plan.md](../product/plan.md).
- The evidence: fastcae's [gearbox-housing engineering report](../../../../fastcae/docs/research/2026-10-06-gearbox-housing-engineering.md), and fastcae's [solver choice](../../../../fastcae/docs/research/solver-choice.md).
