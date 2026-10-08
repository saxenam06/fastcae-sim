/**
 * The product, its tabs, and the words it uses for what it shows.
 *
 * From fastcae-v1:ui/src/app/product.ts: the vendor and the art kept; the product, its tabs and
 * their pages are zenryx's own, and the words for provenance, authority and stages are new.
 *
 * The tabs come in the order the work happens: the contract, the campaigns that attempt it, the
 * designs they make, the data the record becomes - with Flow first, the factory at a glance. Every
 * tab is shown whether or not what fills it is built yet. A shell that hides its unbuilt stages
 * describes a tool; one that shows them describes a product, and tells anyone looking where what
 * they are doing now leads.
 */

import type { Authority, EntryKind, Layer, ProvenanceKind, Stage } from "../records/types";

export const VENDOR = {
  name: "ZenryxAI",
  tagline: "Generate. Learn. Optimize.",
} as const;

export const PRODUCT = {
  name: "zenryx",
  tagline: "housings from requirements",
} as const;

export const ART = {
  /** The crane, cropped out of the full lockup. Used in the bar and as the favicon. */
  mark: "./zenryx-mark.png",
  /** The full stacked lockup. Kept for anywhere it can be shown at size. */
  lockup: "./zenryx-logo.png",
} as const;

export type View = "flow" | "contracts" | "campaigns" | "designs" | "data";

export interface Page {
  id: string;
  label: string;
  summary: string;
}

export interface ViewSpec {
  id: View;
  label: string;
  summary: string;
  /** Whether anything fills it yet. A tab not ready still opens, and says what it waits for. */
  ready: boolean;
  /** Its pages, as tabs above the stage. */
  pages: Page[];
}

export const VIEWS: ViewSpec[] = [
  {
    id: "flow",
    label: "Flow",
    summary: "The factory end to end: each contract on its way through campaigns, designs and grades into data",
    ready: true,
    pages: [
      { id: "contracts", label: "Contracts through the factory", summary: "A contract a row, a stage of the factory a column" },
      { id: "campaign", label: "A campaign into data", summary: "How one campaign's steps become datapoints and tasks" },
    ],
  },
  {
    id: "contracts",
    label: "Contracts",
    summary: "The tasks: what a design must meet, every value with where it came from",
    ready: true,
    pages: [
      { id: "binding", label: "Binding", summary: "What binds a design: the duty, the interfaces, the verdict, the process, the agent's authority, the assumptions" },
      { id: "sheet", label: "Sheet", summary: "Every entry by layer, with its provenance, authority and kind" },
      { id: "check", label: "Check", summary: "The stage ladder and every validator rule" },
      { id: "sources", label: "Sources", summary: "Every source and the entries it supports; the published values kept as a band" },
      { id: "json", label: "JSON", summary: "The contract as written, with its hash" },
    ],
  },
  {
    id: "campaigns",
    label: "Campaigns",
    summary: "Attempts at a task: each hypothesis, the design it made, its grade, the reasoning and the next step",
    ready: false,
    pages: [
      { id: "steps", label: "Steps", summary: "A step a row: what the agent saw, the hypothesis, the tools, the design, its grade, the next step" },
      { id: "hypotheses", label: "Hypotheses", summary: "Every idea tried, with its reason, its test and the status code gave it" },
      { id: "trace", label: "Trace", summary: "Every tool call, in order, with its version and hashes" },
      { id: "budget", label: "Budget", summary: "FE proofs spent, and the best design so far" },
    ],
  },
  {
    id: "designs",
    label: "Designs",
    summary: "Every design a campaign made: its geometry, how it was tested, its grade and its rung",
    ready: false,
    pages: [
      { id: "grid", label: "Grid", summary: "A design a row, a stage a column" },
      { id: "tradeoff", label: "Trade-off", summary: "Mass against the worst margin, every design" },
      { id: "evaluations", label: "Evaluations", summary: "Every test of every design, by scenario" },
    ],
  },
  {
    id: "data",
    label: "Data",
    summary: "What the record becomes: datapoints, tasks cut from campaigns, the sets they train",
    ready: true,
    pages: [
      { id: "axes", label: "Axes", summary: "Task, attempt, evaluation, result: what sits on each" },
      { id: "datapoints", label: "Datapoints", summary: "The kinds A-E: what each is, what it trains, how many exist" },
      { id: "tasks", label: "Tasks", summary: "The 20 task types, each with its grader and whether it exists yet" },
      { id: "pairs", label: "Pairs", summary: "Counterfactual pairs, and any two contracts compared entry by entry" },
    ],
  },
];

export function viewSpec(view: View): ViewSpec {
  return VIEWS.find((v) => v.id === view) ?? VIEWS[0];
}

// --- the words --------------------------------------------------------------------------------

export const PROVENANCE: Record<ProvenanceKind, { label: string; words: string }> = {
  published: { label: "published", words: "From a published paper, cited" },
  standard: { label: "standard", words: "From a standard or a design guideline, cited" },
  measured: { label: "measured", words: "Measured, with its source cited" },
  derived: { label: "derived", words: "Computed by a versioned tool from the entries above it" },
  assumption: { label: "assumption", words: "An assumption, listed with its reason, for the engineer to confirm" },
  engineer: { label: "engineer", words: "Set by the engineer, with who and when" },
};

export const PROVENANCE_ORDER: ProvenanceKind[] = [
  "published",
  "standard",
  "measured",
  "derived",
  "assumption",
  "engineer",
];

export const AUTHORITY: Record<Authority, { label: string; words: string }> = {
  engineer_locked: { label: "locked", words: "Only the engineer may change it; the agent cannot" },
  agent_bounded: { label: "agent, bounded", words: "The agent may move it within its bounds" },
  agent_free: { label: "agent, free", words: "The agent may set it" },
};

export const KIND: Record<EntryKind, { label: string; words: string }> = {
  hard: { label: "hard", words: "Must hold: a design that breaks it fails" },
  soft: { label: "soft", words: "Preferred: may be traded, with the trade recorded" },
  derived: { label: "derived", words: "Computed, never typed; it follows from the hard entries" },
};

export const STAGES: { id: Stage; label: string; words: string }[] = [
  { id: "posed", label: "posed", words: "The requirement stated, every value sourced" },
  { id: "derived", label: "derived", words: "Interfaces and physics computed by the tools" },
  { id: "frozen", label: "frozen", words: "Hashed: the hash is the task's identity, and nothing in it changes" },
];

export const LAYERS: { id: Layer; label: string; words: string }[] = [
  { id: "requirement", label: "Requirement", words: "The duty and the package: torques, speeds, ratio, gears, bearings, space" },
  { id: "interfaces", label: "Interfaces", words: "What a design must keep: seats, split faces, mounts, flanges, ports" },
  { id: "physics", label: "Physics", words: "The load cases and mesh orders, derived" },
  { id: "limits", label: "Limits", words: "The verdict: what a design must meet" },
  { id: "manufacturing", label: "Manufacturing", words: "The process and its rules, and the material" },
];

export const PROCESS: Record<string, string> = {
  high_pressure_die_casting: "aluminium high-pressure die casting",
  sand_casting: "sand casting",
  laser_powder_bed_fusion: "laser powder-bed fusion",
};

export const OBJECTIVE: Record<string, string> = {
  least_mass: "least mass among passing designs",
};

/** A contract's title is a sentence; the rail and the bar want its first few words. */
export function shortTitle(title: string): string {
  const cut = title.split(/[:(]/)[0].trim();
  return cut.length > 48 ? `${cut.slice(0, 46)}…` : cut;
}
