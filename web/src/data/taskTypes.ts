/**
 * The twenty task types of the data design (§6), copied exactly, each with the grader that marks
 * it and whether that grader exists in zenryx today.
 *
 * The grader's status is the honest column. Two task types can be graded now, because the
 * validator's rules exist; two have a closed form that nobody has written as a grader yet; the
 * rest wait for the load tool, the judge, the casting checker or the bound. A task type with no
 * grader is still listed: it is the shape of a task the factory will make, and the gap says what
 * has to be built before it can.
 */

import type { Status } from "../panel/bits";

export type GraderStatus = "exists" | "formula" | "not built";

export const GRADER_STATUS: Record<GraderStatus, { label: string; words: string; dot: Status }> = {
  exists: { label: "exists", words: "Code in zenryx today", dot: "done" },
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
  /** Where the grader is the validator: the rules it runs, by id, or every rule. */
  rules?: string[] | "all";
}

export const GRADERS: Record<GraderKey, Grader> = {
  load_tool: { label: "the load tool (GBX-1)", status: "not built" },
  arithmetic: { label: "exact arithmetic", status: "formula" },
  validator_ratio_offset: {
    label: "the validator's ratio and offset rules",
    status: "exists",
    rules: ["consistency.ratio", "consistency.offset"],
  },
  thermal: { label: "thermal arithmetic", status: "formula" },
  validator_refusals: { label: "the validator's refusals", status: "exists", rules: "all" },
  frozen_judge: { label: "the frozen judge (PHY-1, PHY-3)", status: "not built" },
  judge_runs: { label: "the judge's runs", status: "not built" },
  casting_checker: { label: "the casting checker (PRC)", status: "not built" },
  judge: { label: "the judge", status: "not built" },
  fe_fix: { label: "an FE run of the fix", status: "not built" },
  bound: { label: "the bound (OPT)", status: "not built" },
  precomputed_fe: { label: "pre-computed FE", status: "not built" },
  fe_estimate: { label: "FE, to compare the estimate against", status: "not built" },
};

export interface TaskType {
  n: number;
  task: string;
  given: string;
  handIn: string;
  gradedBy: string;
  usedFor: string;
  grader: GraderKey;
}

/** The §6 table's own note on its abbreviations and numbers. */
export const TASK_NOTE = "H is Hofstetter's EV reducer; AG is the agricultural EV gearbox; the numbers are illustrative";

export const TASK_TYPES: TaskType[] = [
  {
    n: 1,
    task: "The six bearing-seat loads",
    given: "H's gear train, torque, seat positions",
    handIn: "Force vector per seat",
    gradedBy: "The load tool, within 1 %, directions included",
    usedFor: "Imitation, test",
    grader: "load_tool",
  },
  {
    n: 2,
    task: "Gear-mesh frequencies; the speed where an order meets a 1,350 Hz mode",
    given: "Tooth counts, speed range",
    handIn: "Frequencies, crossing speed",
    gradedBy: "Exact arithmetic",
    usedFor: "Imitation, test",
    grader: "arithmetic",
  },
  {
    n: 3,
    task: "Place the intermediate shaft",
    given: "Ratio 9.32 ± 1 %, offset 165 mm",
    handIn: "Gears and shaft position",
    gradedBy: "The validator's ratio and offset rules",
    usedFor: "Imitation, test",
    grader: "validator_ratio_offset",
  },
  {
    n: 4,
    task: "Fit loss when hot",
    given: "Ø72 aluminium seat, steel bearing, +80 K",
    handIn: "µm lost",
    gradedBy: "Thermal arithmetic (about 66 µm)",
    usedFor: "Test",
    grader: "thermal",
  },
  {
    n: 5,
    task: "Find the errors in a contract",
    given: "A contract with three hidden faults",
    handIn: "Each error and why",
    gradedBy: "The validator's refusals",
    usedFor: "Imitation, test",
    grader: "validator_refusals",
  },
  {
    n: 6,
    task: "Static FE under every load case",
    given: "H contract, housing STEP",
    handIn: "Misalignment per mesh, tilt per seat",
    gradedBy: "The frozen judge, within mesh noise",
    usedFor: "Test",
    grader: "frozen_judge",
  },
  {
    n: 7,
    task: "Free-free modes against the measured band",
    given: "AG housing proxy",
    handIn: "First six modes",
    gradedBy: "The judge, and the published 1,352.7 Hz",
    usedFor: "Test",
    grader: "frozen_judge",
  },
  {
    n: 8,
    task: "Mesh convergence",
    given: "A design, two mesh sizes",
    handIn: "The change",
    gradedBy: "The judge's noise measure",
    usedFor: "Test",
    grader: "judge_runs",
  },
  {
    n: 9,
    task: "How bearing loads are applied",
    given: "Rigid against distributed seat loads",
    handIn: "The change in tilt",
    gradedBy: "The judge's two runs",
    usedFor: "Test",
    grader: "judge_runs",
  },
  {
    n: 10,
    task: "Castability",
    given: "A mesh, a pull direction",
    handIn: "Share under 1° of draft; least wall",
    gradedBy: "The casting checker",
    usedFor: "Test",
    grader: "casting_checker",
  },
  {
    n: 11,
    task: "The lightest passing housing",
    given: "H contract",
    handIn: "A housing, STEP or mesh",
    gradedBy: "The judge (pass, then mass)",
    usedFor: "Reinforcement learning, benchmark",
    grader: "judge",
  },
  {
    n: 12,
    task: "Make a 3.6 kg passing design ≥ 5 % lighter",
    given: "The design",
    handIn: "The modified design",
    gradedBy: "The judge",
    usedFor: "Reinforcement learning",
    grader: "judge",
  },
  {
    n: 13,
    task: "Fix a mode 2 % from a gear order, ≤ +0.2 kg",
    given: "The failing design",
    handIn: "The fix",
    gradedBy: "The judge",
    usedFor: "Imitation, reinforcement learning",
    grader: "judge",
  },
  {
    n: 14,
    task: "Make it castable, ≤ 2 % stiffness lost",
    given: "A design with a draft fault and a void",
    handIn: "The castable design",
    gradedBy: "The checker and the judge",
    usedFor: "Reinforcement learning",
    grader: "judge",
  },
  {
    n: 15,
    task: "The same housing for +20 % torque",
    given: "H contract, changed",
    handIn: "Design plus the reason per change",
    gradedBy: "The judge, and the stated reason checked",
    usedFor: "Preference, test",
    grader: "judge",
  },
  {
    n: 16,
    task: "Re-route for moved mounts",
    given: "The F1 variant",
    handIn: "The design",
    gradedBy: "The judge",
    usedFor: "Reinforcement learning",
    grader: "judge",
  },
  {
    n: 17,
    task: "Diagnose the soft load path; propose a fix with its effect",
    given: "An FE result",
    handIn: "Diagnosis, fix, expected gain",
    gradedBy: "An FE run of the fix: did it gain as claimed?",
    usedFor: "Preference",
    grader: "fe_fix",
  },
  {
    n: 18,
    task: "Stop or continue?",
    given: "The bound misses the target by 15 %",
    handIn: "The decision, and what would open the space",
    gradedBy: "Correct stop; valid options",
    usedFor: "Imitation, test",
    grader: "bound",
  },
  {
    n: 19,
    task: "Rank three ideas by gain per kilogram",
    given: "Evidence, three hypotheses",
    handIn: "The ranking",
    gradedBy: "Pre-computed FE of all three",
    usedFor: "Preference",
    grader: "precomputed_fe",
  },
  {
    n: 20,
    task: "Estimate seat tilt by hand before FE",
    given: "A simple housing",
    handIn: "The estimate and its governing parameter",
    gradedBy: "Within 30 % of FE; parameter named",
    usedFor: "Test (the reduced-order skill)",
    grader: "fe_estimate",
  },
];

export function graderOf(task: TaskType): Grader {
  return GRADERS[task.grader];
}

export function gradableNow(): TaskType[] {
  return TASK_TYPES.filter((t) => graderOf(t).status === "exists");
}

export function taskOf(focus: string | null): TaskType | undefined {
  return TASK_TYPES.find((t) => focus === `task:${t.n}`);
}
