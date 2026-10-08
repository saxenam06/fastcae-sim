/**
 * What the Designs tab reads from the records: designs grouped by the campaign that made them, the
 * state of each of a design's stages, and the verdict of one evaluation.
 *
 * A stage reads only what the records say. The provisional Candidate (records/types.ts) is the
 * joined geometry and carries no stage states of its own, so the geometry stages read "made" when
 * the design is recorded without a failure; the stages the judge runs read from the evaluations of
 * their kind. When the record schema (DAT-1) gives a design its stages, this is the one place that
 * changes.
 */

import type { Status } from "../panel/bits";
import type { Candidate, Evaluation, Snapshot } from "../records/types";
import { evaluationsOf } from "../campaigns/records";
import type { DesignStage } from "./words";

/** Designs by the campaign that made them, campaigns in the order they first appear. */
export function byCampaign(designs: Candidate[]): { campaign: string; designs: Candidate[] }[] {
  const groups = new Map<string, Candidate[]>();
  for (const d of designs) groups.set(d.campaign, [...(groups.get(d.campaign) ?? []), d]);
  return [...groups].map(([campaign, list]) => ({ campaign, designs: list }));
}

export interface StageState {
  status: Status;
  text: string;
  title: string;
}

/** Which evaluations each judged stage reads. */
const JUDGED: Partial<Record<DesignStage, (e: Evaluation) => boolean>> = {
  castability: (e) => e.kind === "process",
  mesh: (e) => e.fidelity === "full",
  statics: (e) => e.kind === "static",
  modes: (e) => e.kind === "modal" || e.kind === "orders",
};

export function stageState(snap: Snapshot, design: Candidate, stage: DesignStage): StageState {
  const pick = JUDGED[stage];
  if (!pick) {
    // A geometry stage: the record is the joined geometry, unless it records a failure.
    if (!design.failure) return { status: "done", text: "made", title: "recorded as made" };
    return {
      status: "pending",
      text: "not recorded",
      title: `${design.failure}: which stage failed is not in the record yet (DAT-1)`,
    };
  }
  const runs = evaluationsOf(snap, design.id).filter(pick);
  if (!runs.length) return { status: "pending", text: "not run", title: "no evaluation of this kind yet" };
  if (stage === "mesh") return { status: "done", text: `${runs.length} solved`, title: "solved on the full mesh" };
  const checks = judged(runs.flatMap((e) => e.results));
  const failed = checks.filter((r) => r.passed === false).length;
  const scenarios = runs.map((e) => e.scenario).join("\n");
  if (failed) return { status: "failed", text: `${failed} of ${checks.length} fail`, title: scenarios };
  const text = `${plural(runs.length, "run")} · ${plural(checks.length, "check")}`;
  return { status: "done", text, title: scenarios };
}

/**
 * One evaluation's verdict, from its judged results only - a result with no limit (stress, say) is
 * recorded, not judged: fail if any judged result fails, pass if there are some and all pass.
 */
export function evaluationVerdict(e: Evaluation): boolean | null {
  const checks = judged(e.results);
  if (checks.some((r) => r.passed === false)) return false;
  return checks.length ? true : null;
}

function judged(results: Evaluation["results"]): Evaluation["results"] {
  return results.filter((r) => r.passed !== null);
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** A result as it reads in a row: `tilt 0.31 / 0.5 mrad`. */
export function resultWords(r: Evaluation["results"][number]): string {
  const limit = r.limit === null ? "" : ` / ${r.limit}`;
  return `${r.name} ${r.value}${limit} ${r.unit}`.trim();
}
