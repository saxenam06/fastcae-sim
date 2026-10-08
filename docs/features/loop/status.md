# The first loop, start to end

One housing taken all the way, once: from the completed contract to a plain shell and wall, topology optimisation, ribs, the CAD joined, meshed, coupled, loaded, solved and graded against the contract. It is a prototype (`prototypes/first_loop/`), built to learn what the product's tools must be and where the agent's judgement belongs, before any agent is built (the engineer, 9 October 01:54).

**PBI key:** LOP · **State:** planned; it waits on the completed contract (GBX-1 to GBX-4). Two reviews run first: the spaces inside a reducer, and how housing topology optimisation is iterated · **Updated:** 2026-10-09 02:28 by Claude
**Code:** `prototypes/first_loop/` (a prototype: nothing in `src/` imports it; its outputs go to `data/first_loop/`, which git ignores)

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

| PBI | Goal | Done when |
|---|---|---|
| LOP-1 | The design space and the plain shell and wall: from the completed contract (seats, gears, shafts, packaging, mounts), the two halves split across the shafts, the bearing bosses, the split flange with its bolts, the mount bosses; every face named by its role (bearing seat, shaft hole, wall, flange, bolt, mount) | A watertight solid per half; its mass; its named faces listed; a picture of it |
| LOP-2 | The plain housing judged: a TET10 mesh; distributing couplings over each whole bearing seat, at each bolt between the halves, and at each mount (held fixed); the contract's seat loads in every case; the solve; the grade against the contract | The grade, with the weakest places named |
| LOP-3 | Topology optimisation in the design space: on the whole space first, then on sub-spaces at the weak places; every iteration's settings and result kept | A density field and its picture per iteration, and what changed between them |
| LOP-4 | Ribs from the optimisation's result, joined to the shell; meshed, solved and graded again; iterated until the contract is met or the budget ends | A graded design and the record of its iterations |
| LOP-5 | What the loop teaches: how many iterations, what changed, which strategies worked; the tools the product needs (shell and wall, design space, optimisation, interpretation, ribs, mesh and couplings, judge) and where the agent's judgement belongs | The write-up in this folder, and the next PBIs on the board |

## What runs

Nothing yet.

## Rules in force

- The pass lines are the contract's: the housing's share of the gear tolerances, the bearing tilt limits, the order separation at the rated 6,000 rpm, the 25 % model margin; least mass among passing designs.
- **The machine:** one heavy job at a time; the GPU kept at most about 6 GB of its 8 (checked with `nvidia-smi` first); at least 4 GB of RAM free before a mesh or a solve; meshes well under the card's ceiling of about 412,667 TET10. VS Code must stay open (the engineer, 9 October 02:12).

## Measured

-

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| One loop, start to end, before the agent | Complete the whole flow once in a prototype; learn from it how the agent should work and where its judgement belongs. Do not build the agent yet | 2026-10-09 01:54, the engineer |
| The two halves split across the shafts | One plane square to the shafts; each shaft has a bearing in each half | 2026-10-09 02:12, the engineer |
| Supports and joints | The mount bosses held fixed through distributing couplings; the halves joined at each bolt by distributing couplings; each bearing's loads through a distributing coupling over its whole seat (Physics) | 2026-10-09 02:12-02:15, the engineer |
| The mounts are an input | Their positions come from the vehicle (its mounting system's hardpoints) and are given in the contract. The example gives none, so three are assumed and labelled | 2026-10-09 02:16, the engineer |

## Open

- The reviews under way: `docs/research/2026-10-09-spaces-inside-a-reducer.md` and `docs/research/2026-10-09-housing-topology-optimisation-practice.md`.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- The engineer's brief of 9 October 01:54 is this page's Decisions and Next.
