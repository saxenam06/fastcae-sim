# Contract

The design contract: what must be true, and what may change. Its typed schema, `HousingDesignSpec`, has six layers: product intent, functional interfaces, physics cases, design limits, the manufacturing profile, and the optimisation policy. Every entity carries:
- an **authority**: engineer-locked, agent-bounded with its range, or agent-free;
- a **kind**: hard, soft or derived.

A validator checks units, frames, bounds and contradictions. The dataset generator, the agent's state, the physics interface and the records all derive from this contract.

**PBI key:** CON · **State:** nothing built · **Updated:** 2026-10-07 11:15 by Claude
**Code:** to come: `src/zenryx/contract/`

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| CON-1 | `HousingDesignSpec` v0: the six layers, authority and kind on every entity, units and frames, stamps on derived values (the tool and its version), the validator | It accepts three hand-written contracts and refuses five broken ones, each with its reason |

## What runs

Nothing yet.

## Rules in force

- A derived quantity is stamped with the tool and version that computed it. The agent may ask for it to be computed again, but never writes it.
- Every torque and speed names its shaft and its kind (peak, continuous, maximum).

## Measured

-

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|

## Open

- The engineer's limits for the first archetype are needed before P1 (product page, Open).

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- The plan, section 4 (the contract): [plan.md](../product/plan.md).
