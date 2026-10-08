/**
 * The twenty task types of the data design (§6), each with the grader that marks it and whether
 * that grader exists in zenryx today.
 *
 * Worded for any contract, without the design document's illustrative numbers: a product page
 * shows the shape of a task, and a number in it would read as a result. The document keeps its
 * own examples.
 *
 * The grader's status is the honest column. Two task types can be graded now, because the
 * validator's rules exist; two have a closed form that nobody has written as a grader yet; the
 * rest wait for the load tool, the judge, the casting checker or the bound.
 */

import type { Status } from "../panel/bits";

export type GraderStatus = "exists" | "formula" | "not built";

export const GRADER_STATUS: Record<GraderStatus, { label: string; words: string; dot: Status }> = {
  exists: { label: "ready", words: "Code in zenryx today", dot: "done" },
  formula: { label: "formula", words: "A closed form, not yet written as a grader", dot: "pending" },
  "not built": { label: "not built", words: "Waits for the tool that will grade it", dot: "blank" },
};

export type GraderKey =
  | "load_tool"
  | "arithmetic"
  | "validator_ratio_offset"
  | "thermal"
  | "validator_refusals"
  | "frozen_judge"
  | "judge_runs"
  | "casting_checker"
  | "judge"
  | "fe_fix"
  | "bound"
  | "precomputed_fe"
  | "fe_estimate";

export interface Grader {
  label: string;
  status: GraderStatus;
}

export const GRADERS: Record<GraderKey, Grader> = {
  load_tool: { label: "the load tool (GBX-1)", status: "not built" },
  arithmetic: { label: "exact arithmetic", status: "formula" },
  validator_ratio_offset: { label: "the validator's ratio and offset rules", status: "exists" },
  thermal: { label: "thermal arithmetic", status: "formula" },
  validator_refusals: { label: "the validator's refusals", status: "exists" },
  frozen_judge: { label: "the frozen judge (PHY-1, PHY-3)", status: "not built" },
  judge_runs: { label: "the judge's runs", status: "not built" },
  casting_checker: { label: "the casting checker (PRC)", status: "not built" },
  judge: { label: "the judge", status: "not built" },
  fe_fix: { label: "an FE run of the fix", status: "not built" },
  bound: { label: "the bound (OPT)", status: "not built" },
  precomputed_fe: { label: "pre-computed FE of each idea", status: "not built" },
  fe_estimate: { label: "FE, against the estimate", status: "not built" },
};

export interface TaskType {
  n: number;
  task: string;
  given: string;
  handIn: string;
  gradedBy: GraderKey;
  usedFor: string;
}

export const TASK_TYPES: TaskType[] = [
  { n: 1, task: "The bearing-seat loads", given: "the contract's gear train, torques and seats", handIn: "a force vector per seat", gradedBy: "load_tool", usedFor: "imitation, test" },
  { n: 2, task: "Mesh frequencies, and where an order meets a mode", given: "tooth counts, a speed range, a mode", handIn: "the frequencies and the crossing speed", gradedBy: "arithmetic", usedFor: "imitation, test" },
  { n: 3, task: "Place the intermediate shaft", given: "a ratio with its tolerance, an offset", handIn: "the gears and the shaft's position", gradedBy: "validator_ratio_offset", usedFor: "imitation, test" },
  { n: 4, task: "Fit lost when hot", given: "a seat, its bearing, a temperature rise", handIn: "the interference lost", gradedBy: "thermal", usedFor: "test" },
  { n: 5, task: "Find the errors in a contract", given: "a contract with hidden faults", handIn: "each error and why", gradedBy: "validator_refusals", usedFor: "imitation, test" },
  { n: 6, task: "Static FE under every load case", given: "the contract and a housing", handIn: "misalignment per mesh, tilt per seat", gradedBy: "frozen_judge", usedFor: "test" },
  { n: 7, task: "Free-free modes", given: "a housing", handIn: "its first modes", gradedBy: "frozen_judge", usedFor: "test" },
  { n: 8, task: "Mesh convergence", given: "a design, two mesh sizes", handIn: "the change", gradedBy: "judge_runs", usedFor: "test" },
  { n: 9, task: "How bearing loads are applied", given: "rigid against distributed seat loads", handIn: "the change in tilt", gradedBy: "judge_runs", usedFor: "test" },
  { n: 10, task: "Castability", given: "a housing and its process", handIn: "where it breaks the casting rules", gradedBy: "casting_checker", usedFor: "test" },
  { n: 11, task: "The lightest passing housing", given: "the contract", handIn: "a housing, as STEP or mesh", gradedBy: "judge", usedFor: "reinforcement learning, benchmark" },
  { n: 12, task: "Make a passing design lighter", given: "the design and a target", handIn: "the lighter design", gradedBy: "judge", usedFor: "reinforcement learning" },
  { n: 13, task: "Move a mode off a gear order", given: "the failing design, a mass allowance", handIn: "the fix", gradedBy: "judge", usedFor: "imitation, reinforcement learning" },
  { n: 14, task: "Make it castable, keeping its stiffness", given: "a design with casting faults", handIn: "the castable design", gradedBy: "judge", usedFor: "reinforcement learning" },
  { n: 15, task: "The same housing for a changed requirement", given: "the contract with one input changed", handIn: "the design and the reason for each change", gradedBy: "judge", usedFor: "preference, test" },
  { n: 16, task: "Re-route for moved mounts", given: "a variant with its mounts moved", handIn: "the design", gradedBy: "judge", usedFor: "reinforcement learning" },
  { n: 17, task: "Diagnose the soft load path and propose a fix", given: "an FE result", handIn: "the diagnosis, the fix, the expected gain", gradedBy: "fe_fix", usedFor: "preference" },
  { n: 18, task: "Stop or continue?", given: "a bound that misses the target", handIn: "the decision, and what would open the space", gradedBy: "bound", usedFor: "imitation, test" },
  { n: 19, task: "Rank ideas by gain per kilogram", given: "the evidence and several hypotheses", handIn: "the ranking", gradedBy: "precomputed_fe", usedFor: "preference" },
  { n: 20, task: "Estimate seat tilt by hand", given: "a simple housing", handIn: "the estimate and its governing parameter", gradedBy: "fe_estimate", usedFor: "test" },
];

export function graderOf(task: TaskType): Grader {
  return GRADERS[task.gradedBy];
}

export function gradableNow(): TaskType[] {
  return TASK_TYPES.filter((t) => graderOf(t).status === "exists");
}
