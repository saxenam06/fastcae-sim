# Data

The record of everything the factory does, and the tasks made from it.
- **Every problem is a task:** a frozen contract.
- **Every attempt is recorded:** each campaign's hypotheses, designs and graded evaluations, failures included.
- **Each record keeps** its parent, its hashes and its tool versions.

From these records come the physics models' training pairs, the agent's decision records and the replayable tasks that anyone can attempt.

**PBI key:** DAT · **State:** designed in discussion with the engineer (8 October); nothing built · **Updated:** 2026-10-08 09:40 by Claude
**Code:** none yet (to come: `src/zenryx/data/`)

## Now

| PBI | Goal | Who · laptop · branch | Since | Where it stands |
|---|---|---|---|---|

## Next

These are proposals, awaiting the engineer (design §9).

| PBI | Goal | Done when |
|---|---|---|
| DAT-1 | The record schema. Task, campaign, episode, candidate and evaluation, each with its parent, hashes and tool versions; the scenario on every evaluation; failures with a taxonomy; append-only | A recorded campaign rebuilds its tree from the records alone, and a broken parent link is refused |
| DAT-2 | Snapshot tasks: freeze any step as a replayable task, holding only what was known then | A step from a recorded campaign is frozen; replaying the original fix through the judge gives the recorded grade |
| DAT-3 | The engineer's choices: accept or reject, with the reason, tied to the design and the contract | *Awaits the engineer's yes* |
| DAT-4 | The task export: a frozen contract, the grader's version and the references | An outside attempter can take a task with only the exported files |

## What runs

Nothing yet. The contract (CON-1) already gives every task its frozen form and hash.

## Rules in force

- **One contract is one task.** New tasks come only from a changed requirement. Hypotheses and designs are attempts within a task.
- **The four axes:** task, attempt, evaluation (scenarios) and result. One design gives one evaluation record per scenario.
- **Splits are by contract or family,** never by scenario or mesh (plan §9.4). Every step of one campaign stays on one side of the split.
- **A frozen step holds only what was known at that moment.**
- **Failures are kept.**

## Measured

-

## Decisions

| Decision | Choice | When, by whom |
|---|---|---|
| Every problem is a replayable graded task; any geometry may be handed in | See the [contract page](../contract/status.md), Decisions | 2026-10-08 01:25 and 01:32, the engineer |

## Open

See design §10:
- recording the engineer's choices;
- the agent's library of past decisions;
- a hypoid load module;
- how decisive steps are chosen;
- the split policy for a customer with four families.

## Done

| PBI | Delivered | Date | Commits |
|---|---|---|---|

## Docs

- [2026-10-08-data-tasks-and-learning-design.md](2026-10-08-data-tasks-and-learning-design.md). It covers:
  - the framing (a few families, many variants);
  - tasks against attempts, and the four axes;
  - the datapoint kinds, with 23 examples;
  - cutting a campaign into datapoints;
  - 20 task types;
  - LLM fine-tuning and physics AI;
  - the proposed PBIs.
- The plan, §9 (data) and §10 (learning): [plan.md](../product/plan.md).
