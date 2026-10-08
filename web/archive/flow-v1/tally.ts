/**
 * The records counted by contract.
 *
 * A campaign names its contract; everything below it - hypothesis, design, evaluation, decision -
 * reaches the contract through its campaign, as the record tree does (plan §9.1). The walk is
 * done once here so that the matrix, the rail and the card read the same numbers and cannot
 * disagree. A record whose parent is missing counts for no contract: the walk follows the links as
 * they are and never guesses one.
 */

import type { ContractView, EntryView, Snapshot } from "../records/types";

/** The provenance kinds that cite a source outside zenryx: a paper, a standard, a measurement. */
const CITED = new Set(["published", "standard", "measured"]);

/** The sources a contract's values cite, each once. */
export function citationsOf(entries: EntryView[]): Set<string> {
  const found = new Set<string>();
  for (const e of entries) {
    if (CITED.has(e.provenance.kind) && e.provenance.citation) found.add(e.provenance.citation);
  }
  return found;
}

/** Every distinct source cited across the contracts: the requirement stage's count. */
export function allCitations(snap: Snapshot): Set<string> {
  const found = new Set<string>();
  for (const c of snap.contracts) for (const cite of citationsOf(c.entries)) found.add(cite);
  return found;
}

export interface ContractTally {
  contract: ContractView;
  citations: number;
  campaigns: number;
  episodes: number;
  candidates: number;
  evaluations: number;
  /** Designs the verdict has graded: `passed` is set, true or false. */
  graded: number;
  decisions: number;
  choices: number;
  /** Counterfactual pairs this contract is either side of. */
  pairs: number;
  snapshotTasks: number;
  preferencePairs: number;
}

// The snapshot is read once and never changes while the page is open, so its tally is kept
// against it rather than recomputed by every cell that asks.
const kept = new WeakMap<Snapshot, ContractTally[]>();

export function tallyContracts(snap: Snapshot): ContractTally[] {
  const found = kept.get(snap);
  if (found) return found;
  const r = snap.records;
  const campaignOf = new Map(r.campaigns.map((c) => [c.id, c.contract]));
  const candidateOf = new Map(r.candidates.map((c) => [c.id, campaignOf.get(c.campaign)]));
  const decisionOf = new Map(r.decisions.map((d) => [d.id, campaignOf.get(d.campaign)]));
  const count = <T>(items: T[], contractOf: (item: T) => string | undefined, id: string) =>
    items.filter((item) => contractOf(item) === id).length;

  const rows = snap.contracts.map((contract): ContractTally => {
    const id = contract.id;
    return {
      contract,
      citations: citationsOf(contract.entries).size,
      campaigns: count(r.campaigns, (c) => c.contract, id),
      episodes: count(r.episodes, (e) => campaignOf.get(e.campaign), id),
      candidates: count(r.candidates, (c) => campaignOf.get(c.campaign), id),
      evaluations: count(r.evaluations, (e) => candidateOf.get(e.candidate), id),
      graded: count(
        r.candidates.filter((c) => c.passed !== null),
        (c) => campaignOf.get(c.campaign),
        id,
      ),
      decisions: count(r.decisions, (d) => campaignOf.get(d.campaign), id),
      choices: count(r.choices, (c) => c.contract, id),
      pairs: r.pairs.filter((p) => p.a === id || p.b === id).length,
      snapshotTasks: count(r.snapshot_tasks, (s) => decisionOf.get(s.decision), id),
      preferencePairs: count(r.preference_pairs, (p) => decisionOf.get(p.better), id),
    };
  });
  kept.set(snap, rows);
  return rows;
}
