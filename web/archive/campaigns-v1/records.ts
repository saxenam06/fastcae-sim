/**
 * Lookups over the snapshot's records, for the Campaigns and Designs tabs.
 *
 * Every number either tab draws is computed here from the records - a tally of tool calls, the
 * proofs a step spent, the best margin so far - never typed into a page, so no page can show a
 * figure the records do not hold. Today every record list is empty and each lookup answers with
 * nothing; the pages draw their blanks from that answer, and their rows from the same code once
 * the agent and the judge write records.
 */

import type { Route } from "../app/route";
import type {
  Campaign,
  Candidate,
  ContractView,
  DecisionRecord,
  Episode,
  Evaluation,
  Snapshot,
  ToolCall,
} from "../records/types";
import { PROOF_TOOL } from "./words";

// --- one record by id ------------------------------------------------------------------------

export function contractById(snap: Snapshot, id: string | null): ContractView | null {
  return id ? (snap.contracts.find((c) => c.id === id) ?? null) : null;
}

export function campaignById(snap: Snapshot, id: string | null): Campaign | null {
  return id ? (snap.records.campaigns.find((c) => c.id === id) ?? null) : null;
}

export function episodeById(snap: Snapshot, id: string | null): Episode | null {
  return id ? (snap.records.episodes.find((e) => e.id === id) ?? null) : null;
}

export function candidateById(snap: Snapshot, id: string | null): Candidate | null {
  return id ? (snap.records.candidates.find((c) => c.id === id) ?? null) : null;
}

// --- a record's children ---------------------------------------------------------------------

export function campaignsOf(snap: Snapshot, contract: string): Campaign[] {
  return snap.records.campaigns.filter((c) => c.contract === contract);
}

/** A campaign's steps in the order they were taken. */
export function stepsOf(snap: Snapshot, campaign: string): DecisionRecord[] {
  return snap.records.decisions.filter((d) => d.campaign === campaign).sort((a, b) => a.step - b.step);
}

export function episodesOf(snap: Snapshot, campaign: string): Episode[] {
  return snap.records.episodes.filter((e) => e.campaign === campaign);
}

export function candidatesOf(snap: Snapshot, campaign: string): Candidate[] {
  return snap.records.candidates.filter((c) => c.campaign === campaign);
}

export function evaluationsOf(snap: Snapshot, candidate: string): Evaluation[] {
  return snap.records.evaluations.filter((e) => e.candidate === candidate);
}

/**
 * What the route has in view on Campaigns: a campaign and the contract it attempts. A link that
 * names a contract instead (from Flow, say) keeps that contract in view with no campaign.
 */
export function inView(snap: Snapshot, route: Route): { campaign: Campaign | null; contract: ContractView | null } {
  const campaign = campaignById(snap, route.id);
  if (campaign) return { campaign, contract: contractById(snap, campaign.contract) };
  return { campaign: null, contract: contractById(snap, route.id) };
}

// --- the contracts a campaign may attempt -----------------------------------------------------

/** A campaign attempts a frozen contract only: its hash is the task's identity. */
export function frozen(snap: Snapshot): ContractView[] {
  return snap.contracts.filter((c) => c.stage === "frozen");
}

/** Not frozen yet, but the validator would accept it frozen now. */
export function readyToFreeze(snap: Snapshot): ContractView[] {
  return snap.contracts.filter((c) => c.stage !== "frozen" && c.freeze.ready);
}

// --- tallies, computed -----------------------------------------------------------------------

/** Tool calls in order, a run of the same tool counted once: `hypothesise, reinforce_path, solve ×2`. */
export function toolRuns(tools: ToolCall[]): string {
  const runs: { tool: string; n: number }[] = [];
  for (const call of tools) {
    const last = runs[runs.length - 1];
    if (last && last.tool === call.tool) last.n += 1;
    else runs.push({ tool: call.tool, n: 1 });
  }
  return runs.map((r) => (r.n > 1 ? `${r.tool} ×${r.n}` : r.tool)).join(", ");
}

/** Evaluations counted by kind, in the order the kinds first appear: `3 static, 2 modal`. */
export function kindTally(evaluations: Evaluation[]): string {
  const counts = new Map<string, number>();
  for (const e of evaluations) counts.set(e.kind, (counts.get(e.kind) ?? 0) + 1);
  return [...counts].map(([kind, n]) => `${n} ${kind}`).join(", ");
}

/** The FE proofs a list of calls spent: one a `solve` (plan §8.2). */
export function proofsIn(tools: ToolCall[]): number {
  return tools.filter((t) => t.tool === PROOF_TOOL).length;
}

/**
 * A campaign's course, step by step: the FE proofs spent so far and the best worst-margin among
 * the designs made so far. Read from the trace and the designs; nothing is stored twice.
 */
export function course(snap: Snapshot, campaign: string): { step: number; proofs: number; best: number | null }[] {
  let proofs = 0;
  let best: number | null = null;
  return stepsOf(snap, campaign).map((s) => {
    proofs += proofsIn(s.tools);
    const margin = candidateById(snap, s.candidate)?.worst_margin ?? null;
    if (margin !== null && (best === null || margin > best)) best = margin;
    return { step: s.step, proofs, best };
  });
}

/** The best design a campaign made: the one with the largest worst-margin. */
export function bestOf(designs: Candidate[]): Candidate | null {
  let best: Candidate | null = null;
  for (const d of designs) {
    if (d.worst_margin === null) continue;
    if (!best || best.worst_margin === null || d.worst_margin > best.worst_margin) best = d;
  }
  return best;
}

/**
 * The span a margin axis shows: always both sides of the zero line, at least ±10 %, and a tenth of
 * the span beyond the extremes so no point sits on the frame.
 */
export function marginRange(margins: number[]): [number, number] {
  const lo = Math.min(-0.1, ...margins);
  const hi = Math.max(0.1, ...margins);
  const pad = (hi - lo) * 0.1;
  return [lo - pad, hi + pad];
}

// --- how a quantity is written --------------------------------------------------------------

/** A margin as a share of its limit, signed: `+12 %`, `−3 %`. */
export function pct(share: number | null): string {
  if (share === null) return "—";
  const v = Math.round(share * 100);
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)} %`;
}

export function kg(mass: number | null): string {
  return mass === null ? "—" : `${mass.toFixed(2)} kg`;
}

export function duration(seconds: number): string {
  if (seconds < 60) return `${seconds < 10 ? seconds.toFixed(1) : Math.round(seconds)} s`;
  return `${Math.floor(seconds / 60)} min ${Math.round(seconds % 60)} s`;
}
