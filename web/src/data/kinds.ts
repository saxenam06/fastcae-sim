/**
 * What the record becomes: the five kinds of datapoint (data design §4), the three cuts made from
 * a campaign (§5) and the four rules those cuts keep.
 *
 * One list, read by the Data tab's rail, pages and card and by the Flow tab's campaign diagram, so
 * that a kind is described in one place. Each says what makes it and whether that exists, and
 * counts itself from the snapshot. Only kind A has a maker today - freezing a contract - and it
 * reads 0 until a contract is frozen; the rest wait for what is named in their brackets.
 */

import type { ContractTally } from "../flow/tally";
import type { Snapshot } from "../records/types";

export type KindLetter = "A" | "B" | "C" | "D" | "E";

/** Whether what makes a datapoint exists: built, not built, or proposed and awaiting the engineer. */
export type Making = "built" | "not built" | "proposed";

export const MAKING: Record<Making, string> = {
  built: "What makes it is built",
  "not built": "What makes it is not built yet",
  proposed: "Proposed, awaiting the engineer's yes",
};

export interface DatapointKind {
  letter: KindLetter;
  name: string;
  /** What one is, as the data design's §4 says it. */
  what: string;
  /** What it trains, as §4 says it. */
  trains: string;
  /** The learning that uses it, in a word or two (§7 for the agent, §8 for the physics models). */
  learning: string;
  /** How that learning uses it, for the card. */
  uses: string;
  madeBy: string;
  making: Making;
  /** What the card's blank says while there are none, and what they wait for. */
  none: string;
  waits: (snap: Snapshot) => string;
  count: (snap: Snapshot) => number;
  perContract: (t: ContractTally) => number;
}

const readyToFreeze = (snap: Snapshot) => {
  const n = snap.contracts.filter((c) => c.stage !== "frozen" && c.freeze.ready).length;
  return `Freezing is built (CON-1); ${n} ${n === 1 ? "contract is" : "contracts are"} ready to freeze`;
};

export const KINDS: DatapointKind[] = [
  {
    letter: "A",
    name: "Contract",
    what: "A requirement: the question",
    trains: "The task set",
    learning: "reinforcement learning",
    uses: "A frozen contract is a replayable task: the model attempts it whole and the frozen judge's grade is the reward; the benchmark runs on the same tasks",
    madeBy: "freeze: the canonical hash (CON-1)",
    making: "built",
    none: "No contract frozen yet",
    waits: readyToFreeze,
    count: (snap) => snap.contracts.filter((c) => c.stage === "frozen").length,
    perContract: (t) => (t.contract.stage === "frozen" ? 1 : 0),
  },
  {
    letter: "B",
    name: "Graded design",
    what: "A geometry plus its FE results under each scenario, failures included",
    trains: "The physics models",
    learning: "the physics models",
    uses: "(design, scenario) → results: a scalar predictor first, then a failure predictor, then a field model; a screen, never the judge",
    madeBy: "the geometry (GEO-1) and the judge (PHY-1)",
    making: "not built",
    none: "No graded design yet",
    waits: () => "Waits for the geometry (GEO-1) and the judge (PHY-1)",
    count: (snap) => snap.records.candidates.filter((c) => c.passed !== null).length,
    perContract: (t) => t.graded,
  },
  {
    letter: "C",
    name: "Decision",
    what: "What the agent saw, the idea it tried and why, and what happened",
    trains: "The agent (the LLM)",
    learning: "imitation",
    uses: "Situation → the good next step: the hypothesis, its reason, the tool call, from campaigns that went well",
    madeBy: "the record (DAT-1), from the agent's campaigns (AGT)",
    making: "not built",
    none: "No decision recorded yet",
    waits: () => "Waits for the record (DAT-1) and a campaign of the agent (AGT)",
    count: (snap) => snap.records.decisions.length,
    perContract: (t) => t.decisions,
  },
  {
    letter: "D",
    name: "Engineer's choice",
    what: "Which design was accepted or rejected, and why",
    trains: "Preference: what engineers want",
    learning: "preference",
    uses: "The engineer's accept and reject choices with their reasons, beside the judge's better-against-worse pairs",
    madeBy: "the engineer (DAT-3, proposed)",
    making: "proposed",
    none: "No engineer's choice yet",
    waits: () => "Waits for the engineer's yes to recording choices (DAT-3, proposed)",
    count: (snap) => snap.records.choices.length,
    perContract: (t) => t.choices,
  },
  {
    letter: "E",
    name: "Counterfactual pair",
    what: "Two contracts differing in one requirement, and how the design changed",
    trains: "Cause and effect",
    learning: "cause and effect",
    uses: "One requirement changed at a time, and what that did to the design: this teaches cause (plan §9.4)",
    madeBy: "the generator, recorded (DAT-1)",
    making: "not built",
    none: "No counterfactual pair yet",
    waits: () => "Not built yet: counterfactual contracts are written by the generator and recorded (DAT-1)",
    count: (snap) => snap.records.pairs.length,
    perContract: (t) => t.pairs,
  },
];

export function kindOf(focus: string | null): DatapointKind | undefined {
  return KINDS.find((k) => focus === `kind:${k.letter}`);
}

export function datapoints(snap: Snapshot): number {
  return KINDS.reduce((n, k) => n + k.count(snap), 0);
}

// --- cut from a campaign ---------------------------------------------------------------------------

export type CutId = "decisions" | "snapshots" | "preferences";

export interface Cut {
  id: CutId;
  name: string;
  /** The datapoint kind it is, where it is one. */
  kind: KindLetter | null;
  /** Which steps it is cut from, in a few words: the connector's label on the diagram. */
  from: string;
  what: string;
  learning: string;
  /** The longer words, for the card and the hover. */
  words: string;
  madeBy: string;
  making: Making;
  count: (snap: Snapshot) => number;
  perContract: (t: ContractTally) => number;
}

export const CUTS: Cut[] = [
  {
    id: "decisions",
    name: "Decision records",
    kind: "C",
    from: "every step",
    what: "the situation, the idea and its reason, the result",
    learning: "imitation",
    words: "Every step, logged with what the agent saw then - the contract, the design, the FE results, the tool versions, the budget spent - each by reference and hash; the idea and its reason; the outcome; the status code computed",
    madeBy: "the record (DAT-1)",
    making: "not built",
    count: (snap) => snap.records.decisions.length,
    perContract: (t) => t.decisions,
  },
  {
    id: "snapshots",
    name: "Snapshot tasks",
    kind: null,
    from: "a decisive step, frozen",
    what: "a replayable task, holding only what was known then",
    learning: "test, reinforcement learning",
    words: "A decisive step - a large gain, a clear failure, a switch of approach, a correct stop - frozen as a stand-alone task; the grader runs the attempt's fix through the frozen judge",
    madeBy: "snapshot tasks (DAT-2)",
    making: "not built",
    count: (snap) => snap.records.snapshot_tasks.length,
    perContract: (t) => t.snapshotTasks,
  },
  {
    id: "preferences",
    name: "Preference pairs",
    kind: null,
    from: "two steps from one state",
    what: "the better step and the worse, by the judge's grades",
    learning: "preference",
    words: "In the same situation, step A graded better than step B; the failed idea is kept as the worse half",
    madeBy: "the judge's grades, recorded (DAT-1)",
    making: "not built",
    count: (snap) => snap.records.preference_pairs.length,
    perContract: (t) => t.preferencePairs,
  },
];

export function cutOf(focus: string | null): Cut | undefined {
  return CUTS.find((c) => focus === `cut:${c.id}`);
}

/** The four rules a cut keeps (data design §5). */
export const CUT_RULES: { label: string; words: string }[] = [
  {
    label: "a frozen step holds only what was known then",
    words: "A frozen step holds only what was known at that moment: no later step, no outcome",
  },
  {
    label: "failed ideas are kept",
    words: "Failed ideas are kept: the worse half of preference pairs, and tasks of their own (\"why did this fix not work?\")",
  },
  {
    label: "branch at revealing moments",
    words: "Branch at revealing moments: try three ideas from the same state and grade all three. That is how ranking tasks are made",
  },
  {
    label: "the same split",
    words: "Same split: every step from one contract or family stays on the same side of the train/test split",
  },
];
