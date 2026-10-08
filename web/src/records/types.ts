/**
 * The snapshot: what the UI reads, as `zenryx.api.snapshot` writes it.
 *
 * The contract side mirrors the Python payload exactly. The records side - campaigns, episodes,
 * candidates, evaluations, decisions, the engineer's choices, pairs - is empty today, and its shapes
 * here are provisional: they follow the plan's record tree (plan §9.1-9.2) and the data design
 * (docs/features/data, §2-§5 and §7) until the record schema (DAT-1) is agreed.
 */

export type Stage = "posed" | "derived" | "frozen";
export type ProvenanceKind = "published" | "standard" | "measured" | "derived" | "assumption" | "engineer";
export type Authority = "engineer_locked" | "agent_bounded" | "agent_free";
export type EntryKind = "hard" | "soft" | "derived";
export type Layer = "requirement" | "interfaces" | "physics" | "limits" | "manufacturing";

export interface Refusal {
  rule: string;
  entry: string;
  reason: string;
}

export interface Provenance {
  kind: ProvenanceKind;
  citation?: string;
  tool?: string;
  tool_version?: string;
  input_hash?: string;
  assumption_id?: string;
  who?: string;
  when?: string;
  note?: string;
}

/** One value of a contract, in words, with where it came from. */
export interface EntryView {
  /** The dotted path in the contract, e.g. `requirement.torques[0].torque`. */
  path: string;
  layer: Layer;
  /** Where it sits on the sheet: `torques`, `bearings`, `the housing's shares` … */
  group: string;
  /** The field in words, with the list item it belongs to: `torque · peak drive, input shaft`. */
  label: string;
  /** As written: `366 N·m`, `(0, 0, 1)`, `6206`. */
  value: string;
  /** In canonical units (`366000 N*mm`), or null when not a quantity. */
  canonical: string | null;
  provenance: Provenance;
  authority: Authority;
  kind: EntryKind;
  bounds: [string, string] | null;
}

/** A named thing a design must keep or carry: a torque, a gear stage, a bearing, a seat … */
export interface Item {
  kind: string;
  name: string;
  path: string;
  detail: string;
}

/** A test a design of this contract will be judged under, as the contract implies it. */
export interface Scenario {
  kind: "static" | "orders" | "modal";
  name: string;
  /** The entry it comes from. */
  from: string;
}

export interface Assumption {
  id: string;
  what: string;
  value: string;
  why: string;
  varied: boolean;
}

/** A published value kept as a plausibility band, never as a limit. */
export interface Reference {
  source: string;
  quantity: string;
  value: string;
  conditions: string;
  confidence: string;
}

// --- the contract page (zenryx.api.contract_page) -----------------------------------------------

/** Where a value came from, in two words, with the full text for the hover. */
export interface Sourced {
  /** A short label: "Ivanov 2018", "Shigley", "assumed", "you", "calculated". */
  source: string;
  /** The provenance kind, for the label's style; empty where none applies. */
  kind: ProvenanceKind | "";
  title: string;
}

export interface InputRow extends Sourced {
  label: string;
  value: string;
  path: string;
  /** For a choice (the process): what could be chosen instead. */
  options?: string[];
  /** What comes with the value rather than apart from it: a material's properties. */
  detail?: string;
}

export interface InputCell extends Sourced {
  value: string;
  /** True where the cell's source differs from its column's: only then is it marked. */
  own: boolean;
}

export interface InputGroup {
  group: string;
  rows: InputRow[];
  /** The gear train's stages, a column each, each column with where it comes from. */
  table?: { columns: string[]; sources: Sourced[]; rows: { label: string; cells: InputCell[] }[] } | null;
}

/** What a step takes in: an input from the Inputs section, or another step's output. */
export interface StepInput {
  name: string;
  /** The step whose output it is; null for an input. */
  step: number | null;
}

/** What a step gave: a row a quantity, a column a stage where it has one (else one cell). */
export interface StepTable {
  columns: string[];
  rows: { label: string; cells: string[] }[];
}

/** A step of the calculation chain (docs/features/product/2026-10-08-the-calculation-chain.md). */
export interface Calculation {
  step: number;
  quantity: string;
  method: string;
  /** The standard or the authors the method follows. */
  by: string;
  /** The function that computes it, or the tool that will. */
  function: string;
  status: "computed" | "planned";
  takes_in: StepInput[];
  /** What it gives, in words. */
  gives: string;
  /** What it gave; null while planned. */
  table: StepTable | null;
  /** While planned: the PBI that builds it, or what it still needs. */
  plan: string;
}

export interface Criterion extends Sourced {
  label: string;
  value: string;
}

export interface ToBeat {
  quantity: string;
  value: string;
  source: string;
  title: string;
  /** A computed remark, such as a published mode sitting on a mesh frequency. */
  note: string;
}

export interface ContractPage {
  inputs: InputGroup[];
  calculations: Calculation[];
  criteria: Criterion[];
  to_beat: ToBeat[];
}

export interface ContractView {
  id: string;
  /** The JSON file it was read from, relative to the repository. */
  file: string;
  /** False when the file does not load: then only `refusals` and `json` are set. */
  loaded: boolean;
  title: string;
  family: string;
  level: string;
  priorities: string[];
  budget_fe_proofs: number;
  budget_hours: number;
  stage: Stage;
  style: "package" | "gear_train";
  process: string;
  material: string;
  space: "box" | "layout_envelope";
  verdict_rule_version: string;
  objective: string;
  stress: string;
  /** The hash of the content as it is now. */
  hash: string;
  /** Set only on a frozen contract: the task's identity. */
  frozen_hash: string | null;
  refusals: Refusal[];
  /** What the validator would say of the contract frozen now. */
  freeze: { ready: boolean; refusals: Refusal[] };
  entries: EntryView[];
  items: Item[];
  scenarios: Scenario[];
  assumptions: Assumption[];
  references: Reference[];
  /** The contract page's view: inputs, calculations, criteria, the design to beat. */
  page: ContractPage;
  /** The file as written, indented. */
  json: string;
}

export interface Rule {
  id: string;
  words: string;
}

// --- the records: provisional until DAT-1 (the record schema) -----------------------------------

/** Who attempts a task: the plan's benchmark arms (plan §11.1). */
export type Arm = "agent" | "rule_based" | "optimiser" | "person";

/** The hypothesis status code computes; the agent never sets it (plan §8.1). */
export type HypothesisStatus = "open" | "promising" | "poor" | "met" | "set_aside";

/** The stop rules (plan §8.5). */
export type StopRule = "verdict_met" | "bound_exhausted" | "budget_spent" | "all_set_aside" | "stopped_with_reason";

/** The rungs of the label ladder (plan §7.2). A design is never just "verified". */
export type Rung =
  | "none"
  | "simulation_feasible"
  | "process_rule_feasible"
  | "process_simulated"
  | "prototype_validated"
  | "production_qualified";

/** One attempt at one frozen contract by one solver, with a budget. */
export interface Campaign {
  id: string;
  /** The frozen contract's id: the task. */
  contract: string;
  /** The frozen hash it ran against. */
  task_hash: string;
  arm: Arm;
  model?: string;
  brief_version?: string;
  budget_fe_proofs: number;
  spent_fe_proofs: number;
  started: string;
  ended: string | null;
  stop: StopRule | null;
  stop_reason: string | null;
  best_design: string | null;
}

/** One hypothesis explored within a campaign: the plan's episode. */
export interface Episode {
  id: string;
  campaign: string;
  claim: string;
  reason: string;
  expected: string;
  /** What result would prove it wrong. */
  wrong_if: string;
  seed: string | null;
  budget_fe_proofs: number;
  status: HypothesisStatus;
}

/** One tool call, as the trace keeps it. */
export interface ToolCall {
  tool: string;
  version: string;
  input_hash: string;
  output_hash: string;
  seconds: number;
  ok: boolean;
  note: string;
}

/** One step of a campaign: what the agent saw, what it decided and why, what happened. */
export interface DecisionRecord {
  id: string;
  campaign: string;
  step: number;
  episode: string | null;
  saw: string;
  decided: string;
  tools: ToolCall[];
  candidate: string | null;
  happened: string;
  status: HypothesisStatus;
  next: string;
}

/** One geometry: the machined core and the structure joined, with its manufacturing state. */
export interface Candidate {
  id: string;
  campaign: string;
  episode: string | null;
  mass_kg: number | null;
  rung: Rung;
  /** The worst verdict margin over every check, as a share of its limit; negative fails. */
  worst_margin: number | null;
  passed: boolean | null;
  failure: string | null;
}

/** One test of one candidate under one scenario. */
export interface Evaluation {
  id: string;
  candidate: string;
  scenario: string;
  kind: "static" | "orders" | "modal" | "thermal" | "process" | "screen";
  fidelity: "screen" | "full";
  results: { name: string; value: number; unit: string; limit: number | null; passed: boolean | null }[];
}

/** The engineer's accept or reject, with the reason (DAT-3, proposed). */
export interface EngineerChoice {
  id: string;
  candidate: string;
  contract: string;
  accepted: boolean;
  reason: string;
  who: string;
  when: string;
}

/** Two contracts identical but for one requirement, and how the design changed. */
export interface CounterfactualPair {
  id: string;
  a: string;
  b: string;
  changed: string;
  effect: string;
}

/** A campaign step frozen as a replayable task, holding only what was known then (DAT-2). */
export interface SnapshotTask {
  id: string;
  decision: string;
  task_type: number;
  given: string;
  hand_in: string;
}

/** In the same situation, step A graded better than step B. */
export interface PreferencePair {
  id: string;
  better: string;
  worse: string;
  why: string;
}

export interface Records {
  campaigns: Campaign[];
  episodes: Episode[];
  candidates: Candidate[];
  evaluations: Evaluation[];
  decisions: DecisionRecord[];
  choices: EngineerChoice[];
  pairs: CounterfactualPair[];
  snapshot_tasks: SnapshotTask[];
  preference_pairs: PreferencePair[];
}

export interface Snapshot {
  schema: string;
  zenryx: string;
  contract_schema: string;
  rules: Rule[];
  contracts: ContractView[];
  records: Records;
  hash: string;
}
