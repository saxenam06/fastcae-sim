/**
 * The words the Campaigns tab draws: who attempts a task, how a campaign stops, the status code
 * gives a hypothesis, the seeds a hypothesis may start from, the agent's typed tools, and what each
 * part of a decision record holds. A few words each, with the plan's own sentence kept for the
 * hover (plan §3, §8.2, §8.3, §8.5, §11.1; the data design §5 and §7).
 *
 * Kept as data rather than written into the pages, so each page draws whatever the plan lists and
 * a change to the plan is one edit here. They sit in this folder only while the tabs are built
 * side by side; they belong beside the other words in app/product.ts.
 */

import type { Arm, HypothesisStatus, StopRule } from "../records/types";

/** Who attempts a task: the benchmark's arms, at equal budget, on the same tools (plan §11.1). */
export const ARM: Record<Arm, { label: string; words: string }> = {
  agent: {
    label: "agent",
    words: "The agent: it chooses each hypothesis, its formulation and when to stop; code picks which designs get a proof",
  },
  rule_based: {
    label: "rule-based workflow",
    words: "A fixed workflow, or an expert's adaptive rule set, on the same tools as the agent",
  },
  optimiser: {
    label: "optimiser",
    words: "Bayesian optimisation over the seeds' continuous fields and the choice of seed",
  },
  person: {
    label: "person",
    words: "An engineer attempting the task, with any geometry",
  },
};

export const ARM_ORDER: Arm[] = ["agent", "rule_based", "optimiser", "person"];

/** How a campaign stops (plan §8.5). `short` is for the rail, where a row has one line. */
export const STOP: Record<StopRule, { label: string; short: string; words: string }> = {
  verdict_met: {
    label: "verdict met",
    short: "verdict met",
    words: "The contract's verdict is met.",
  },
  bound_exhausted: {
    label: "the bound says the space is exhausted",
    short: "space exhausted",
    words:
      "The bound says the space is exhausted: the relaxed optimum over the whole domain misses the goal, so no strategy inside this contract can meet it.",
  },
  budget_spent: {
    label: "the budget is spent",
    short: "budget spent",
    words: "The budget is spent: the FE proofs or the hours the contract allows.",
  },
  all_set_aside: {
    label: "every hypothesis set aside",
    short: "all set aside",
    words:
      "Every hypothesis within authority has been set aside by its tests: no gain beyond the noise after deeper optimisation, or a worse trade-off than another hypothesis at a fair budget.",
  },
  stopped_with_reason: {
    label: "stopped early with a stated reason",
    short: "stopped, with reason",
    words: "The agent may stop early only with a stated reason, which is itself a recorded decision.",
  },
};

export const STOP_ORDER: StopRule[] = [
  "verdict_met",
  "bound_exhausted",
  "budget_spent",
  "all_set_aside",
  "stopped_with_reason",
];

/**
 * A hypothesis's status: computed by code from the evidence, never set by the agent (plan §3).
 * `short` is the legend's gloss; `words` the hover's full sentence.
 */
export const STATUS: Record<HypothesisStatus, { label: string; short: string; words: string }> = {
  open: {
    label: "open",
    short: "too little evidence yet",
    words: "Untested or under-explored: too little evidence to judge it yet",
  },
  promising: {
    label: "promising",
    short: "it gains; worth more budget",
    words: "The evidence says it gains: worth more of the budget",
  },
  poor: {
    label: "poor",
    short: "explored; little gain per kilogram",
    words: "Explored and poor: less gain per kilogram than another hypothesis, or none beyond the noise",
  },
  met: {
    label: "met",
    short: "a design from it meets the verdict",
    words: "A design from it meets the contract's verdict",
  },
  set_aside: {
    label: "set aside",
    short: "dropped by its tests",
    words:
      "Set aside by its tests: no gain beyond the noise after deeper optimisation, or a worse trade-off than another hypothesis at a fair budget",
  },
};

export const STATUS_ORDER: HypothesisStatus[] = ["open", "promising", "poor", "met", "set_aside"];

/** The V1 starting formulations (plan §8.3). A seed is a starting point; the claim is the agent's. */
export const SEEDS: { name: string; representation: string; suits: string; later?: string }[] = [
  {
    name: "free density",
    representation: "SIMP density over the whole domain, with length-scale and overhang control",
    suits: "the default; also the bound",
  },
  {
    name: "shell plus reinforcement",
    representation: "a wall of set thickness on the domain's outer skin, with free density inside",
    suits: "oil-tight shells; NVH-driven panels",
  },
  {
    name: "bridge-first",
    representation: "paths reserved between bearing seats and mounts, then free density",
    suits: "misalignment-governed cases",
  },
  {
    name: "struts",
    representation: "a skeleton of members between interfaces, sized by optimisation",
    suits: "low mass fractions; the X-type torsion paths",
  },
  {
    name: "lattice infill",
    representation:
      "homogenised lattice in eligible regions, with solid skins; on this laptop for screening only",
    suits: "thick, lightly loaded regions; NVH damping",
    later: "after the MVP",
  },
  {
    name: "ribs on a shell",
    representation: "parametric webs on a fixed shell (CadQuery)",
    suits: "the conventional reference; a cast-like baseline",
  },
];

/** The agent's typed tools, as the plan groups them (§8.2). Every arm calls the same ones. */
export const TOOL_GROUPS: { group: string; words: string; tools: { name: string; words: string }[] }[] = [
  {
    group: "Reading",
    words: "What the agent reads",
    tools: [
      { name: "state", words: "the campaign's state: the contract, the best design, the hypotheses, the budget left" },
      { name: "look", words: "pictures: the FE hot spots and the topology's dials" },
      { name: "bound", words: "the relaxed optimum: what any structure in the domain can reach" },
      { name: "regions", words: "the semantic regions (bores, mount paths, panels) and their shares of the strain energy" },
    ],
  },
  {
    group: "Campaign",
    words: "The real agency: which formulation to search, and when to stop",
    tools: [
      { name: "hypothesise", words: "create or edit a hypothesis: claim, formulation, expected effect, what would prove it wrong, budget" },
      { name: "domain_edit", words: "open or close a region, within authority" },
      { name: "constrain", words: "add a constraint" },
      { name: "relax_soft", words: "relax a soft target, the trade recorded" },
      { name: "escalate_fidelity", words: "a finer mesh, a load case added, thermal" },
      { name: "switch", words: "move to another hypothesis" },
      { name: "continue_from", words: "carry on from an earlier design" },
      { name: "restart_with_seed", words: "start again from a seed" },
      { name: "declare_exhausted", words: "the space is exhausted, with the evidence: the bound, the history" },
    ],
  },
  {
    group: "Design",
    words: "Edits to one design",
    tools: [
      { name: "move_within_zone", words: "move a feature within its zone" },
      { name: "thicken", words: "thicken a region" },
      { name: "thin", words: "thin a region" },
      { name: "reinforce_path", words: "reinforce the path between two semantic nodes" },
      { name: "redistribute", words: "move material between regions" },
      { name: "lattice_density", words: "change a lattice's density" },
    ],
  },
  {
    group: "Proof",
    words: "The screen is free; each solve counts against the budget",
    tools: [
      { name: "screen", words: "the voxel model: seconds to minutes, free of the budget" },
      { name: "solve", words: "the TET10 proof on cuDSS, counted against the budget" },
      { name: "reflect", words: "a reflection written after each proof" },
    ],
  },
];

/** The tool whose every call spends one FE proof (plan §8.2). */
export const PROOF_TOOL = "solve";

/** One decision record, part by part (data design §5, §7): the card's sections. */
export const RECORD_PARTS: { id: "saw" | "decided" | "happened" | "next"; title: string; holds: string }[] = [
  {
    id: "saw",
    title: "What the agent saw",
    holds: "the contract, the best design so far and its margins, where the strain energy sits, the ideas tried, the budget left",
  },
  {
    id: "decided",
    title: "What it decided, and why",
    holds: "the hypothesis: its claim and reason, what it expects, what would prove it wrong, its budget",
  },
  {
    id: "happened",
    title: "What happened",
    holds: "the tools it called, the design made, its grade, the status code gave the idea",
  },
  {
    id: "next",
    title: "Next",
    holds: "the next step, or the stop rule that fired",
  },
];
