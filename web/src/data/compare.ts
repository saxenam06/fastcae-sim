/**
 * Two contracts compared entry by entry, by path.
 *
 * A counterfactual pair differs in one requirement; two unrelated contracts differ in dozens of
 * entries, and the count of them is the measure of how far apart two tasks are. Values are
 * compared in canonical units where there are any, so the same torque written in N·m and in N·mm
 * counts as the same, and as written otherwise.
 */

import { LAYERS } from "../app/product";
import type { ContractView, EntryView, Layer } from "../records/types";

export type Difference = "same" | "different" | "only_a" | "only_b";

export const DIFFERENCE: Record<Difference, string> = {
  same: "the same value in both",
  different: "in both, with different values",
  only_a: "only in A",
  only_b: "only in B",
};

export interface Compared {
  path: string;
  layer: Layer;
  label: string;
  how: Difference;
  a: EntryView | null;
  b: EntryView | null;
}

const valueOf = (e: EntryView) => e.canonical ?? e.value;

/** Every path in either contract, in layer order, then in the order A and then B write them. */
export function compareContracts(a: ContractView, b: ContractView): Compared[] {
  const inB = new Map(b.entries.map((e) => [e.path, e]));
  const inA = new Set(a.entries.map((e) => e.path));
  const rows: Compared[] = a.entries.map((ea) => {
    const eb = inB.get(ea.path) ?? null;
    const how: Difference = !eb ? "only_a" : valueOf(ea) === valueOf(eb) ? "same" : "different";
    return { path: ea.path, layer: ea.layer, label: ea.label, how, a: ea, b: eb };
  });
  for (const eb of b.entries) {
    if (!inA.has(eb.path)) rows.push({ path: eb.path, layer: eb.layer, label: eb.label, how: "only_b", a: null, b: eb });
  }
  const order = (layer: Layer) => LAYERS.findIndex((l) => l.id === layer);
  // A stable sort keeps each contract's own order within a layer.
  return rows.sort((x, y) => order(x.layer) - order(y.layer));
}

export function countBy(rows: Compared[]): Record<Difference, number> {
  const n: Record<Difference, number> = { same: 0, different: 0, only_a: 0, only_b: 0 };
  for (const r of rows) n[r.how] += 1;
  return n;
}
