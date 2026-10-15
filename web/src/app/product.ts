/**
 * The product, its tabs, and the words it uses for what it shows.
 *
 * From fastcae-v1:ui/src/app/product.ts: the vendor and the art kept; the product, its tabs and
 * their pages are zenryx's own, and the words for provenance, authority and stages are new.
 *
 * The tabs come in the order the work happens: the contract, the campaigns that attempt it, the
 * designs they make, the data the record becomes, then Flow, the factory at a glance. Every
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

/**
 * The tabs in the order the work happens (the engineer, 8 Oct 20:35): the contract you give, the
 * campaigns the agent runs on it, the designs they make and their grades, the data it all becomes,
 * and Flow, where the whole factory stands. One page each, no rail, no card.
 */
export const VIEWS: ViewSpec[] = [
  {
    id: "contracts",
    label: "Contract",
    summary: "Your inputs, what the tools calculate from them, and what a design must meet",
    ready: true,
    pages: [{ id: "contract", label: "Contract", summary: "Inputs, calculations, pass criteria, the design to beat" }],
  },
  {
    id: "campaigns",
    label: "Campaigns",
    summary: "The agent's attempts at the contract: each step, what it tried and why, what happened",
    ready: false,
    pages: [{ id: "campaign", label: "Campaigns", summary: "A new campaign, and its steps" }],
  },
  {
    id: "designs",
    label: "Designs",
    summary: "Every housing a campaign makes: its stages, its grade, its rung, against the design to beat",
    ready: false,
    pages: [
      { id: "designs", label: "Designs", summary: "Every design, grouped by the flow that made it, and its process step by step" },
      { id: "optimisation", label: "Optimisation", summary: "Topology optimisation runs in 3D: what was frozen, what was placed" },
    ],
  },
  {
    id: "data",
    label: "Data",
    summary: "What the record becomes: datapoints, and the tasks cut from them",
    ready: true,
    pages: [{ id: "data", label: "Data", summary: "Datapoints and tasks" }],
  },
  {
    id: "flow",
    label: "Flow",
    summary: "Where the whole factory stands, from the contract to the data",
    ready: true,
    pages: [{ id: "flow", label: "Flow", summary: "The factory, step by step" }],
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
  derived: { label: "calculated", words: "Calculated by a versioned tool from the entries above it" },
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
  derived: { label: "calculated", words: "Calculated, never typed; it follows from the hard entries" },
};

export const STAGES: { id: Stage; label: string; words: string }[] = [
  { id: "posed", label: "posed", words: "The requirement stated, every value sourced" },
  { id: "completed", label: "completed", words: "The interfaces and physics calculated by the tools and written in" },
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
