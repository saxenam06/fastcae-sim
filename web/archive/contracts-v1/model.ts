/**
 * The Contracts tab's reading of the snapshot: the contract in view, what is in focus, and the
 * groupings its pages lay out.
 *
 * Pure functions over the snapshot. A page memoises them on the contract, which never changes under
 * it; and since every number they return is counted or looked up, none of them can invent one.
 */

import { LAYERS, PROVENANCE_ORDER } from "../app/product";
import type {
  Assumption,
  ContractView,
  EntryView,
  Item,
  Layer,
  Provenance,
  ProvenanceKind,
  Refusal,
  Rule,
  Scenario,
  Snapshot,
  Stage,
} from "../records/types";

// --- the words this tab adds ------------------------------------------------------------------

export const LEVEL: Record<string, string> = { L1: "fixed interfaces" };

export const STYLE: Record<string, string> = {
  package: "the package: ratio, offset, duty, life",
  gear_train: "a given gear train",
};

export const STRESS: Record<string, string> = { recorded: "recorded, not judged" };

/** What each stage still needs before the next. Frozen needs nothing: its hash is shown instead. */
export const NEXT_STEP: Record<Stage, string> = {
  posed: "derive the interfaces and the physics: the load tool (GBX-1), not built",
  derived: "freeze it",
  frozen: "",
};

/** What fills the derived layers, said wherever they are still empty. */
export const DERIVES_THEM = "the load tool (GBX-1) derives them, not built";

/** The stages as the rail lists them: the tasks first, the requirements still being worked last. */
export const RAIL_ORDER: Stage[] = ["frozen", "derived", "posed"];

export function layerSpec(layer: Layer) {
  return LAYERS.find((l) => l.id === layer) ?? LAYERS[0];
}

// --- the contract in view, and the focus ------------------------------------------------------

export function contractIn(snap: Snapshot, id: string | null): ContractView | null {
  return snap.contracts.find((c) => c.id === id) ?? snap.contracts[0] ?? null;
}

const ASSUMPTION = "assumption:";

export function assumptionFocus(id: string): string {
  return `${ASSUMPTION}${id}`;
}

/** The assumption a focus names, when it names one. */
export function assumptionIn(focus: string | null): string | null {
  return focus?.startsWith(ASSUMPTION) ? focus.slice(ASSUMPTION.length) : null;
}

export type Focus =
  | { kind: "entry"; entry: EntryView }
  | { kind: "assumption"; id: string; assumption: Assumption | null }
  | { kind: "contract"; missing: string | null };

/** What the route's focus names in this contract; a focus it does not hold falls back to the contract. */
export function focusIn(c: ContractView, focus: string | null): Focus {
  if (!focus) return { kind: "contract", missing: null };
  if (!c.loaded) return { kind: "contract", missing: focus };
  if (focus.startsWith(ASSUMPTION)) {
    const id = focus.slice(ASSUMPTION.length);
    return { kind: "assumption", id, assumption: c.assumptions.find((a) => a.id === id) ?? null };
  }
  const entry = c.entries.find((e) => e.path === focus);
  return entry ? { kind: "entry", entry } : { kind: "contract", missing: focus };
}

/** Whether a focus means something in another contract. The rail keeps it when it does, so the same
 * entry can be read across contracts; one that does not resolve would only say "not here". */
export function resolves(c: ContractView, focus: string | null): boolean {
  const f = focusIn(c, focus);
  return f.kind === "entry" || (f.kind === "assumption" && f.assumption !== null);
}

export function verdictOf(c: ContractView): { words: string; outcome: "pass" | "reject" } {
  if (!c.loaded) return { words: "does not load", outcome: "reject" };
  const n = c.refusals.length;
  return n ? { words: `${n} refused`, outcome: "reject" } : { words: "accepted", outcome: "pass" };
}

// --- entries in groups ------------------------------------------------------------------------

/** The item an entry belongs to: the deepest item whose path its own path continues. */
export function itemOf(path: string, items: Item[]): Item | null {
  let best: Item | null = null;
  for (const item of items) {
    const under = path.startsWith(`${item.path}.`) || path.startsWith(`${item.path}[`);
    if (under && (!best || item.path.length > best.path.length)) best = item;
  }
  return best;
}

export interface Row {
  entry: EntryView;
  /** The label as the row shows it: without the tag its item's head already says. */
  label: string;
}

/** Entries of one item under its head, or loose entries (item null) as rows of their own. */
export interface Bunch {
  item: Item | null;
  rows: Row[];
}

export interface Group {
  name: string;
  count: number;
  bunches: Bunch[];
}

/** Entries by their group in the order they come, and within a group by the item they belong to. */
export function groupsOf(entries: EntryView[], items: Item[]): Group[] {
  const groups = new Map<string, EntryView[]>();
  for (const e of entries) {
    const list = groups.get(e.group);
    if (list) list.push(e);
    else groups.set(e.group, [e]);
  }
  return [...groups].map(([name, list]) => ({ name, count: list.length, bunches: bunchesOf(list, items) }));
}

function bunchesOf(entries: EntryView[], items: Item[]): Bunch[] {
  const out: { item: Item | null; entries: EntryView[] }[] = [];
  const open = new Map<string, EntryView[]>();
  for (const e of entries) {
    const item = itemOf(e.path, items);
    const list = item ? open.get(item.path) : undefined;
    if (list) {
      list.push(e);
    } else {
      const fresh = [e];
      if (item) open.set(item.path, fresh);
      out.push({ item, entries: fresh });
    }
  }
  // An item with one entry reads better as that entry's own row than as a head over one line.
  return out.flatMap(({ item, entries: list }): Bunch[] =>
    item && list.length > 1
      ? [{ item, rows: rowsUnder(item, list) }]
      : list.map((entry) => ({ item: null, rows: [{ entry, label: entry.label }] })),
  );
}

/**
 * An entry's label is `field · tag of each list item above it` (snapshot.py). Under its item's head
 * the item's own tag is said already, so it is dropped - but only when every entry of the item
 * carries the same tag there, so a label that does not follow the pattern is shown whole.
 */
function rowsUnder(item: Item, entries: EntryView[]): Row[] {
  const depth = item.path.split("[").length - 1;
  const parts = entries.map((e) => e.label.split(" · "));
  const tag = parts[0][depth];
  const shared = depth > 0 && tag !== undefined && parts.every((p) => p[depth] === tag);
  return entries.map((entry, i) => ({
    entry,
    label: shared ? parts[i].filter((_, j) => j !== depth).join(" · ") : entry.label,
  }));
}

/** A bearing item's detail reads `<type> at <seat>`, as the snapshot writes it. */
export function bearingParts(item: Item): { type: string; seat: string } {
  const at = item.detail.indexOf(" at ");
  return at < 0 ? { type: item.detail, seat: "" } : { type: item.detail.slice(0, at), seat: item.detail.slice(at + 4) };
}

// --- counts -----------------------------------------------------------------------------------

export function provenanceMix(entries: EntryView[]): { kind: ProvenanceKind; n: number }[] {
  return PROVENANCE_ORDER.map((kind) => ({ kind, n: entries.filter((e) => e.provenance.kind === kind).length }));
}

export function judgedUnder(scenarios: Scenario[]): string {
  const n = (kind: Scenario["kind"]) => scenarios.filter((s) => s.kind === kind).length;
  const [s, o, m] = [n("static"), n("orders"), n("modal")];
  return `judged under: ${s} static ${s === 1 ? "case" : "cases"} · orders at ${o} ${o === 1 ? "speed" : "speeds"} · ${m} modal`;
}

// --- refusals and rules -----------------------------------------------------------------------

/** The refusals that name this entry, or an item or layer it sits in. */
export function refusalsOn(path: string, refusals: Refusal[]): Refusal[] {
  return refusals.filter(
    (r) => r.entry !== "" && (r.entry === path || path.startsWith(`${r.entry}.`) || path.startsWith(`${r.entry}[`)),
  );
}

export interface RuleRow {
  rule: Rule;
  refusals: Refusal[];
}

/** Every rule the validator runs with the refusals it gave; a refusal from a rule not listed comes last. */
export function ruleRows(rules: Rule[], refusals: Refusal[]): RuleRow[] {
  const known = new Set(rules.map((r) => r.id));
  const strays = [...new Set(refusals.map((r) => r.rule).filter((id) => !known.has(id)))];
  return [...rules, ...strays.map((id) => ({ id, words: "" }))].map((rule) => ({
    rule,
    refusals: refusals.filter((r) => r.rule === rule.id),
  }));
}

// --- sources ----------------------------------------------------------------------------------

/** One place values came from: a citation, a tool run, an assumption, or the engineer at a time. */
export interface Source {
  key: string;
  kind: ProvenanceKind;
  /** The first entry's provenance: every entry of a source shares the fields that name it. */
  provenance: Provenance | null;
  assumption: Assumption | null;
  entries: EntryView[];
}

function sourceKey(p: Provenance): string {
  switch (p.kind) {
    case "derived":
      return `${p.tool ?? ""}|${p.tool_version ?? ""}|${p.input_hash ?? ""}`;
    case "assumption":
      return p.assumption_id ?? "";
    case "engineer":
      return `${p.who ?? ""}|${p.when ?? ""}`;
    default:
      return p.citation ?? "";
  }
}

/** The entries by where they came from, a list of sources a provenance kind. Every listed assumption
 * is a source, whether or not an entry points to it yet. */
export function sourcesOf(c: ContractView): Map<ProvenanceKind, Source[]> {
  const out = new Map<ProvenanceKind, Source[]>(PROVENANCE_ORDER.map((k) => [k, []]));
  const index = new Map<string, Source>();
  const add = (source: Source) => {
    index.set(`${source.kind}|${source.key}`, source);
    out.get(source.kind)?.push(source);
  };
  for (const a of c.assumptions) add({ key: a.id, kind: "assumption", provenance: null, assumption: a, entries: [] });
  for (const e of c.entries) {
    const p = e.provenance;
    const key = sourceKey(p);
    const found = index.get(`${p.kind}|${key}`);
    if (found) {
      found.entries.push(e);
      found.provenance ??= p;
    } else {
      add({ key, kind: p.kind, provenance: p, assumption: null, entries: [e] });
    }
  }
  return out;
}
