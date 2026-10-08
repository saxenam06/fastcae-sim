/**
 * The kinds of datapoint the factory records (the data design, §4), each with an example from the
 * contract in words, never numbers: nothing is recorded yet, and an invented number would read as
 * a result.
 *
 * Replaces the first version's kinds (archived in `archive/web/data-v1/kinds.ts`), which were
 * tied to the old Flow tab's counts.
 */

import type { Snapshot } from "../records/types";

export interface DatapointKind {
  letter: "A" | "B" | "C" | "D" | "E";
  name: string;
  what: string;
  /** An example, in words, from the first contract. */
  example: string;
  trains: string;
  count: (snap: Snapshot) => number;
}

export const KINDS: DatapointKind[] = [
  {
    letter: "A",
    name: "Contract",
    what: "The question, once frozen",
    example: "the EV reducer at 165 mm, sand cast",
    trains: "the task set; reinforcement learning with the judge as grader",
    count: (snap) => snap.contracts.filter((c) => c.stage === "frozen").length,
  },
  {
    letter: "B",
    name: "Graded design",
    what: "One housing, its FE results under each load case, pass or fail",
    example: "a design from a campaign on the EV reducer: its mass, its modes, its verdict",
    trains: "the physics models: design to results",
    count: (snap) => snap.records.candidates.filter((d) => d.passed !== null).length,
  },
  {
    letter: "C",
    name: "Decision",
    what: "One step of the agent: what it saw, what it tried and why, what happened",
    example: "the mode sits on the mesh frequency, so stiffen the back panel; the mode moves",
    trains: "the agent: imitation of the steps that worked",
    count: (snap) => snap.records.decisions.length,
  },
  {
    letter: "D",
    name: "Your choice",
    what: "You accept or reject a design, with the reason",
    example: "rejected: the rib blocks the drain plug",
    trains: "preference: what engineers want",
    count: (snap) => snap.records.choices.length,
  },
  {
    letter: "E",
    name: "Counterfactual pair",
    what: "Two contracts one input apart, and how the best design changed",
    example: "the EV reducer at 165 mm against 130 mm packaging",
    trains: "cause and effect",
    count: (snap) => snap.records.pairs.length,
  },
];

/** What is cut from a campaign, beside its datapoints (the data design, §5). */
export const CUTS: { name: string; what: string; count: (snap: Snapshot) => number }[] = [
  {
    name: "Decision records",
    what: "every step, as it happened",
    count: (snap) => snap.records.decisions.length,
  },
  {
    name: "Snapshot tasks",
    what: "a decisive step frozen as a task, holding only what was known then",
    count: (snap) => snap.records.snapshot_tasks.length,
  },
  {
    name: "Preference pairs",
    what: "two steps from one state: the better and the worse",
    count: (snap) => snap.records.preference_pairs.length,
  },
];

/** Every datapoint recorded, kind by kind. The title block counts the same way. */
export function datapoints(snap: Snapshot): number {
  return KINDS.reduce((n, k) => n + k.count(snap), 0);
}
