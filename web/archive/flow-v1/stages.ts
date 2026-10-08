/**
 * The factory's stages, in the order the work happens: from a requirement on paper to a datapoint.
 *
 * Each stage says what one of it is, what makes it and whether that is built, and counts itself
 * from the snapshot - so the rail, the chain, the matrix and the card read one list and cannot
 * disagree. A stage whose maker is not built still counts what exists: the textbook case was
 * derived by hand, so "derived" reads 1 while its dashed dot says the load tool does not exist yet.
 */

import type { Status } from "../panel/bits";
import { datapoints, KINDS } from "../data/kinds";
import type { Snapshot } from "../records/types";
import { allCitations, type ContractTally } from "./tally";

export type GroupId = "task" | "attempt" | "judgement" | "data";

export const GROUPS: { id: GroupId; label: string; words: string }[] = [
  { id: "task", label: "The task", words: "What a design must meet, sourced, derived and frozen" },
  { id: "attempt", label: "The attempt", words: "What a solver tries on a frozen task" },
  { id: "judgement", label: "The judgement", words: "How each design is tested, and its verdict" },
  { id: "data", label: "The data", words: "What the record becomes" },
];

export interface FactoryStage {
  id: string;
  group: GroupId;
  label: string;
  /** The matrix's column head. */
  column: string;
  /** What one of it is, in a few words. */
  what: string;
  /** What makes it, with the PBI's short name in brackets. */
  madeBy: (snap: Snapshot) => string;
  built: boolean;
  /** One more line, where the count needs explaining. */
  detail?: string;
  /** Its count's noun: one, many. */
  noun: [string, string];
  count: (snap: Snapshot) => number;
  /** Its count for one contract. */
  perContract: (t: ContractTally) => number;
}

const words = (text: string) => () => text;
const isDerived = (stage: string) => stage === "derived" || stage === "frozen";

export const STAGES: FactoryStage[] = [
  {
    id: "requirement",
    group: "task",
    label: "Requirement",
    column: "Requirement",
    what: "the sources its values cite: papers, standards, measurements",
    madeBy: words("by hand from the paper"),
    built: true,
    noun: ["citation", "citations"],
    count: (snap) => allCitations(snap).size,
    perContract: (t) => t.citations,
  },
  {
    id: "posed",
    group: "task",
    label: "Contract posed",
    column: "Posed",
    what: "the requirement stated, every value sourced",
    madeBy: (snap) => `the validator (zenryx.contract, ${snap.rules.length} rules)`,
    built: true,
    noun: ["contract", "contracts"],
    count: (snap) => snap.contracts.length,
    perContract: () => 1,
  },
  {
    id: "derived",
    group: "task",
    label: "Physics derived",
    column: "Derived",
    what: "interfaces and physics computed from the requirement",
    madeBy: words("the load tool (GBX-1)"),
    built: false,
    detail: "the textbook case was derived by hand",
    noun: ["contract", "contracts"],
    count: (snap) => snap.contracts.filter((c) => isDerived(c.stage)).length,
    perContract: (t) => (isDerived(t.contract.stage) ? 1 : 0),
  },
  {
    id: "frozen",
    group: "task",
    label: "Task frozen",
    column: "Frozen",
    what: "hashed: the hash is the task's identity",
    madeBy: words("freeze: the canonical hash"),
    built: true,
    noun: ["task", "tasks"],
    count: (snap) => snap.contracts.filter((c) => c.stage === "frozen").length,
    perContract: (t) => (t.contract.stage === "frozen" ? 1 : 0),
  },
  {
    id: "campaign",
    group: "attempt",
    label: "Campaign",
    column: "Campaigns",
    what: "one attempt at a frozen task by one solver, with a budget",
    madeBy: words("the agent (AGT), the rule-based workflow, an optimiser, a person"),
    built: false,
    noun: ["campaign", "campaigns"],
    count: (snap) => snap.records.campaigns.length,
    perContract: (t) => t.campaigns,
  },
  {
    id: "hypothesis",
    group: "attempt",
    label: "Hypothesis",
    column: "Hypotheses",
    what: "one idea, its reason, and what would prove it wrong",
    madeBy: words("the agent's ideas (AGT)"),
    built: false,
    noun: ["hypothesis", "hypotheses"],
    count: (snap) => snap.records.episodes.length,
    perContract: (t) => t.episodes,
  },
  {
    id: "design",
    group: "attempt",
    label: "Design",
    column: "Designs",
    what: "one housing an idea produced: the core and its structure",
    madeBy: words("the CadQuery core (GEO-1) and the field-space structure (GEO, OPT)"),
    built: false,
    noun: ["design", "designs"],
    count: (snap) => snap.records.candidates.length,
    perContract: (t) => t.candidates,
  },
  {
    id: "evaluation",
    group: "judgement",
    label: "Evaluation",
    column: "Evaluations",
    what: "one test of one design under one scenario",
    madeBy: words("the judge: statics (PHY-1), modes (PHY-3), process checks (PRC)"),
    built: false,
    noun: ["evaluation", "evaluations"],
    count: (snap) => snap.records.evaluations.length,
    perContract: (t) => t.evaluations,
  },
  {
    id: "grade",
    group: "judgement",
    label: "Grade",
    column: "Grades",
    what: "the verdict on a design: pass or fail, with its margins",
    madeBy: words("the deterministic verdict (PHY)"),
    built: false,
    noun: ["grade", "grades"],
    count: (snap) => snap.records.candidates.filter((c) => c.passed !== null).length,
    perContract: (t) => t.graded,
  },
  {
    id: "decision",
    group: "data",
    label: "Decision",
    column: "Decisions",
    what: "a step: what was seen, decided and why, and what happened",
    madeBy: words("the record (DAT-1)"),
    built: false,
    noun: ["decision", "decisions"],
    count: (snap) => snap.records.decisions.length,
    perContract: (t) => t.decisions,
  },
  {
    id: "datapoints",
    group: "data",
    label: "Datapoints",
    column: "Datapoints",
    what: "the kinds A-E the record becomes",
    madeBy: words("the record and its exports (DAT-1 to DAT-4)"),
    built: false,
    noun: ["datapoint", "datapoints"],
    count: datapoints,
    perContract: (t) => KINDS.reduce((n, k) => n + k.perContract(t), 0),
  },
];

export function stageOf(focus: string | null): FactoryStage | undefined {
  return STAGES.find((s) => s.id === focus);
}

export function stagesIn(group: GroupId): FactoryStage[] {
  return STAGES.filter((s) => s.group === group);
}

/** The stage before and after one, in the factory's order. */
export function neighbours(stage: FactoryStage): { prev?: FactoryStage; next?: FactoryStage } {
  const i = STAGES.indexOf(stage);
  return { prev: STAGES[i - 1], next: STAGES[i + 1] };
}

/**
 * What makes a stage, to follow the words "made by": the requirement's "by hand from the paper"
 * already starts with its "by", which would otherwise read twice.
 */
export function maker(stage: FactoryStage, snap: Snapshot): string {
  return stage.madeBy(snap).replace(/^by /, "");
}

export function noun(stage: FactoryStage, n: number): string {
  return n === 1 ? stage.noun[0] : stage.noun[1];
}

export type StageStatus = "done" | "pending" | "skipped";

/** A stage's dot: green when built and it has made something, hollow when built and empty, dashed when not built. */
export function stageStatus(stage: FactoryStage, n: number): StageStatus {
  if (!stage.built) return "skipped";
  return n > 0 ? "done" : "pending";
}

export const STATUS_WORDS: Record<StageStatus, string> = {
  done: "built, and it has made some",
  pending: "built; nothing made yet",
  skipped: "not built",
};

/** The same, for the shared status dot, whose dashed mark is called `blank`. */
export function stageDot(status: StageStatus): Status {
  return status === "skipped" ? "blank" : status;
}
