/**
 * A campaign's moves, as its agent made them (LOP-24; the engineer, 11 October 21:37: "I want to see
 * your decisions on the UI for each iteration: what design space you considered and what was the
 * result, if the design space was changed in that iteration... later the same can be used to analyse
 * the runtime agent"). As fastcae's Optimize tab showed an agent's iterations
 * (fastcae-v1:ui/src/optimize/Optimize.tsx): the campaigns on the left; in the centre, the best design
 * so far against the moves, the moves one row each, and the chosen move's decision, design space and
 * results; on the right, the move's settings with what changed marked, and who decided.
 *
 * The data: `../records/campaigns/<campaign>.json` (`prototypes/first_loop/campaign_export.py`, from the
 * campaign's decision log `data/first_loop/agent/<campaign>.json`, which the agent writes move by move;
 * the runtime agent will write the same). Its numbers come from each run's record (the optimiser's own
 * check, against the true lines) and from FE's grades, never from the log.
 */

import { useState } from "react";
import type { CardProps, TabProps } from "../app/tab";
import { Space3D } from "./Space3D";

interface Model {
  done: boolean;
  kg?: number;
  tilt?: number;
  beds_um?: number | null;
  safety?: number;
  safety_beds?: number;
  objective?: string;
  seconds?: number;
  free_voxels?: number | null;
}
interface Fe {
  kg: number;
  beds_um: number;
  beds_ok: boolean;
  tilt: number;
  tilt_ok: boolean;
  first_hz: number | null;
  clashes: string[];
  orders_ok: boolean;
  mass_ok: boolean;
  pass: boolean;
}
interface Result {
  label: string;
  run?: string;
  design?: string;
  model?: Model | null;
  fe?: Fe | null;
  picture?: string | null;
}
type Poly = number[][];
interface Region {
  name: string;
  outline: Poly;
  holes: Poly[];
  /** "empty": a part of a features' region no feature covers, held empty */
  kind?: string;
}
interface Space {
  name: string;
  changed: boolean;
  file?: string | null;
  /** a `--height-features` file: the rest of the part free, the features drawn over it */
  features?: string | null;
  words?: string;
  regions?: Record<string, Region[]>;
  /** the optimiser's fill, region by region (`space_fill.py`), keyed `<half>|<region>` */
  fill?: Record<string, { covered: number; volume: number; height_mm: number }>;
}
interface Move {
  n: number;
  iteration: number;
  kind: string;
  title: string;
  at: string;
  until: string | null;
  by: string;
  saw: string;
  hypothesis: string;
  lever: string;
  settings: Record<string, string | number | null>;
  changed: string[];
  not_pulled: { lever: string; why: string }[];
  expected: string;
  /** an experiment's run budget, acceptance criterion and rollback target (the plan's §6.9) */
  budget?: string;
  acceptance?: string;
  rollback?: string;
  space: Space;
  results: Result[];
  pictures: string[];
  notes?: string[];
  verdict: string | null;
  next: string | null;
}
interface Context {
  halves: Record<string, Poly[]>;
  bores: { shaft: string; side: string; axis: number[]; r: number; boss_r: number }[];
  bolts: number[][];
  mounts: { name: string; centre: number[]; r: number }[];
  box: number[];
}
interface Campaign {
  id: string;
  title: string;
  contract: string;
  driver: string;
  agent: string;
  started: string;
  goal: string;
  baseline: string;
  log: string;
  moves: Move[];
  fe_runs: number;
  best: { design: string; kg: number; move: number } | null;
  context: Context;
}

const FILES = import.meta.glob("../records/campaigns/*.json", { eager: true }) as Record<string, { default: Campaign }>;
const PICTURES = import.meta.glob("../records/campaigns/*.png", { eager: true, query: "?url", import: "default" }) as Record<string, string>;
export const CAMPAIGNS: Campaign[] = Object.values(FILES)
  .map((m) => m.default)
  .sort((a, b) => b.started.localeCompare(a.started));

const REFERENCE_KG = 7.73;
const BASELINE_KG = 6.89;
const picture = (name?: string | null) => (name ? PICTURES[`../records/campaigns/${name}`] : undefined);
const hhmm = (iso: string | null) => (iso ? iso.slice(11, 16) : "");
const kg = (v?: number | null) => (v == null ? "-" : `${v.toFixed(2)} kg`);

/** The log's words, its `backticked` names set as code. */
function Rich({ text }: { text: string }) {
  const parts = text.split("`");
  return (
    <>
      {parts.map((p, i) => (i % 2 ? <span key={i} className="mono cg-code">{p}</span> : <span key={i}>{p}</span>))}
    </>
  );
}

/** A move's state: running, passing (an FE result passes), failing (FE judged, none passes), or the optimiser's alone. */
function stateOf(m: Move): "running" | "pass" | "fail" | "model" {
  if (!m.until && !m.verdict) return "running";
  const fe = m.results.filter((r) => r.fe);
  if (fe.length) return fe.some((r) => r.fe!.pass) ? "pass" : "fail";
  return "model";
}

export function chosenCampaign(route: TabProps["route"]): Campaign | null {
  return CAMPAIGNS.find((c) => c.id === route.id) ?? CAMPAIGNS[0] ?? null;
}

function chosenMove(c: Campaign, route: TabProps["route"]): Move | null {
  const n = route.focus != null ? Number(route.focus) : NaN;
  return c.moves.find((m) => m.n === n) ?? c.moves[c.moves.length - 1] ?? null;
}

export function AgentRail({ route, go }: TabProps) {
  const current = chosenCampaign(route);
  return (
    <nav className="pr-rail">
      <section className="pr-flow">
        <header className="pr-flow-head">Campaigns, newest first</header>
        {CAMPAIGNS.map((c) => (
          <button
            key={c.id}
            type="button"
            className="pr-design"
            data-on={route.id !== "new" && current?.id === c.id}
            onClick={() => go({ id: c.id, focus: null })}
          >
            <span className="pr-design-id mono">{c.id}</span>
            <span className="pr-design-name">{c.title}</span>
            <span className="pr-design-time mono">
              {c.started.slice(0, 10)} {hhmm(c.started)} · driver: {c.driver}
            </span>
            <span className="pr-pills">
              <span className="pr-pill mono">{c.moves.length} moves</span>
              <span className="pr-pill mono">{c.fe_runs} FE runs</span>
              <span className="pr-pill mono" data-mark={c.best ? "pass" : "fail"}>
                {c.best ? `best ${c.best.kg.toFixed(2)} kg` : "nothing passes yet"}
              </span>
            </span>
            <span className="cg-dots">
              {c.moves.map((m) => (
                <i key={m.n} data-state={stateOf(m)} title={`Move ${m.n}: ${m.title}`} />
              ))}
            </span>
          </button>
        ))}
      </section>
      <section className="pr-flow">
        <button type="button" className="pr-design" data-on={route.id === "new"} onClick={() => go({ id: "new", focus: null })}>
          <span className="pr-design-name">New campaign</span>
          <span className="pr-design-time">the product's form: a contract, a solver, a budget, the stop rules</span>
        </button>
      </section>
    </nav>
  );
}

export function AgentStage({ route, go }: TabProps) {
  const c = chosenCampaign(route);
  const [tab, setTab] = useState<"decision" | "space" | "result">("decision");
  if (!c) return <div className="stage-scroll"><div className="vol-empty">No campaign exported yet: run prototypes/first_loop/campaign_export.py &lt;campaign&gt;.</div></div>;
  const move = chosenMove(c, route);
  const prevSpace = move ? [...c.moves].filter((m) => m.n < move.n && m.space).pop()?.space ?? null : null;
  return (
    <div className="stage-scroll pr-stage cg-stage">
      <header className="pr-head">
        <div className="pr-head-kicker">
          Campaign {c.id} · {c.contract} · driver: {c.driver} ({c.agent})
        </div>
        <h2 className="pr-head-title">{c.title}</h2>
        <p className="pr-head-words">
          The goal: {c.goal}. The baseline: <span className="mono">{c.baseline}</span>. The account in words: <span className="mono">{c.log}</span>.
        </p>
        <div className="pr-pills">
          <span className="pr-pill mono">{c.moves.length} moves</span>
          <span className="pr-pill mono">{c.fe_runs} FE runs</span>
          {c.best ? (
            <button type="button" className="pr-pill mono cg-link" data-mark="pass" onClick={() => go({ view: "designs", id: c.best!.design })}>
              best passing: {c.best.design}, {c.best.kg.toFixed(2)} kg (move {c.best.move})
            </button>
          ) : (
            <span className="pr-pill mono" data-mark="fail">nothing passes yet</span>
          )}
        </div>
      </header>
      <Curve c={c} on={move?.n ?? null} pick={(n) => go({ id: c.id, focus: String(n) })} />
      <section className="cg-moves" aria-label="the moves">
        {c.moves.map((m) => (
          <button key={m.n} type="button" className="cg-move" data-on={move?.n === m.n} data-state={stateOf(m)} onClick={() => go({ id: c.id, focus: String(m.n) })}>
            <span className="cg-move-n mono">Move {m.n}</span>
            <span className="cg-move-it mono">it {m.iteration}</span>
            <span className="cg-move-title">{m.title}</span>
            <span className="pr-pill mono" data-mark={m.space.changed ? "change" : undefined}>
              {m.space.changed ? `space changed: ${m.space.name}` : `space: ${m.space.name}`}
            </span>
            <span className="cg-move-result mono">{headline(m)}</span>
          </button>
        ))}
      </section>
      {move ? (
        <section className="cg-detail">
          <nav className="pr-steps">
            {(
              [
                ["decision", "What it saw and decided"],
                ["space", m_space_label(move)],
                ["result", "The result"],
              ] as const
            ).map(([id, label]) => (
              <button key={id} type="button" className="pr-step" data-on={tab === id} onClick={() => setTab(id)}>
                {label}
              </button>
            ))}
          </nav>
          {tab === "decision" ? <Decision m={move} /> : null}
          {tab === "space" ? (
            <>
              <Space3D campaign={c.id} move={move.n} />
              <h3 className="cg-sub">In plan</h3>
              <SpaceView ctx={c.context} space={move.space} prev={move.space.changed ? prevSpace : null} pictures={move.pictures} />
            </>
          ) : null}
          {tab === "result" ? <ResultView m={move} go={go} /> : null}
        </section>
      ) : null}
    </div>
  );
}

const m_space_label = (m: Move) => (m.space.changed ? "The design space (changed)" : "The design space");

/** The move's result in one line: the best FE verdict, else the optimiser's own. */
function headline(m: Move): string {
  const st = stateOf(m);
  if (st === "running") return "running";
  const fe = m.results.filter((r) => r.fe);
  if (fe.length) {
    const r = fe.find((x) => x.fe!.pass) ?? fe[0];
    const f = r.fe!;
    return `FE: ${kg(f.kg)}, beds ${f.beds_um.toFixed(1)} µm, tilt ${f.tilt.toFixed(2)}×, ${f.first_hz?.toFixed(0) ?? "-"} Hz${f.clashes.length ? `, ${f.clashes.length} clash` : ""}: ${f.pass ? "passes" : "fails"}`;
  }
  const ms = m.results.map((r) => r.model).filter((x): x is Model => !!x && x.done);
  if (!ms.length) return "no result";
  const lightest = ms.reduce((a, b) => ((a.kg ?? 99) <= (b.kg ?? 99) ? a : b));
  return `model: ${ms.length > 1 ? `${ms.length} runs, the lightest ` : ""}${kg(lightest.kg)}, tilt ${lightest.tilt?.toFixed(2)}×, beds ${lightest.beds_um?.toFixed(1)} µm`;
}

function Curve({ c, on, pick }: { c: Campaign; on: number | null; pick: (n: number) => void }) {
  const W = 760;
  const H = 190;
  const pad = { l: 46, r: 16, t: 14, b: 30 };
  const n = Math.max(1, c.moves.length - 1);
  const lo = 4;
  const hi = 8;
  const X = (i: number) => pad.l + 16 + ((W - pad.l - pad.r - 32) * i) / n;
  const Y = (v: number) => pad.t + ((H - pad.t - pad.b) * (hi - v)) / (hi - lo);
  const pts: { n: number; kg: number; kind: "pass" | "fail" | "model" }[] = [];
  for (const m of c.moves) {
    for (const r of m.results) {
      if (r.fe) pts.push({ n: m.n, kg: r.fe.kg, kind: r.fe.pass ? "pass" : "fail" });
      else if (r.model?.done && r.model.kg != null) pts.push({ n: m.n, kg: r.model.kg, kind: "model" });
    }
  }
  let best = Infinity;
  const stairs: string[] = [];
  for (const m of c.moves) {
    for (const r of m.results) if (r.fe?.pass) best = Math.min(best, r.fe.kg);
    if (best < Infinity) stairs.push(`${X(m.n)},${Y(best)}`);
  }
  return (
    <figure className="cg-curve">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="the designs' mass move by move">
        {[4, 5, 6, 7, 8].map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={Y(v)} y2={Y(v)} className="cg-grid" />
            <text x={pad.l - 6} y={Y(v) + 4} className="cg-axis" textAnchor="end">
              {v} kg
            </text>
          </g>
        ))}
        <line x1={pad.l} x2={W - pad.r} y1={Y(REFERENCE_KG)} y2={Y(REFERENCE_KG)} className="cg-ref" />
        <text x={W - pad.r} y={Y(REFERENCE_KG) - 4} className="cg-axis" textAnchor="end">
          the reference, 7.73 kg
        </text>
        <line x1={pad.l} x2={W - pad.r} y1={Y(BASELINE_KG)} y2={Y(BASELINE_KG)} className="cg-base" />
        <text x={W - pad.r} y={Y(BASELINE_KG) - 4} className="cg-axis" textAnchor="end">
          the baseline, 6.89 kg
        </text>
        {stairs.length > 1 ? <polyline points={stairs.join(" ")} className="cg-best" /> : null}
        {c.moves.map((m) => (
          <g key={m.n} onClick={() => pick(m.n)} className="cg-col" data-on={on === m.n}>
            <rect x={X(m.n) - 12} y={pad.t} width={24} height={H - pad.t - pad.b} />
            <text x={X(m.n)} y={H - 10} className="cg-axis" textAnchor="middle">
              {m.n}
            </text>
          </g>
        ))}
        {pts.map((p, i) => (
          <circle key={i} cx={X(p.n)} cy={Y(Math.min(hi, Math.max(lo, p.kg)))} r={p.kind === "model" ? 4 : 5.5} className="cg-pt" data-kind={p.kind} onClick={() => pick(p.n)}>
            <title>{`move ${p.n}: ${p.kg.toFixed(2)} kg (${p.kind === "model" ? "the optimiser's model" : `FE, ${p.kind}`})`}</title>
          </circle>
        ))}
      </svg>
      <figcaption className="dim">
        Each move's designs by mass: filled, judged by FE (green passes, red fails); hollow, the optimiser's own check. The line: the lightest passing design so far.
      </figcaption>
    </figure>
  );
}

function Decision({ m }: { m: Move }) {
  return (
    <dl className="cg-decision">
      <dt>Saw</dt>
      <dd>
        <Rich text={m.saw} />
      </dd>
      <dt>Hypothesis</dt>
      <dd>
        <Rich text={m.hypothesis} />
      </dd>
      <dt>Lever</dt>
      <dd>
        <Rich text={m.lever} />
      </dd>
      {m.changed.length ? (
        <>
          <dt>Changed</dt>
          <dd>
            <span className="pr-pills">
              {m.changed.map((x) => (
                <span key={x} className="pr-pill" data-mark="change">
                  {x}
                </span>
              ))}
            </span>
          </dd>
        </>
      ) : null}
      {m.not_pulled.length ? (
        <>
          <dt>Not pulled</dt>
          <dd>
            {m.not_pulled.map((x) => (
              <div key={x.lever}>
                {x.lever}: <span className="dim">{x.why}</span>
              </div>
            ))}
          </dd>
        </>
      ) : null}
      <dt>Expected</dt>
      <dd>
        <Rich text={m.expected} />
      </dd>
      {m.budget ? (
        <>
          <dt>Run budget</dt>
          <dd>
            <Rich text={m.budget} />
          </dd>
        </>
      ) : null}
      {m.acceptance ? (
        <>
          <dt>Accepted if</dt>
          <dd>
            <Rich text={m.acceptance} />
          </dd>
        </>
      ) : null}
      {m.rollback ? (
        <>
          <dt>Rollback to</dt>
          <dd>
            <Rich text={m.rollback} />
          </dd>
        </>
      ) : null}
      {m.notes?.length ? (
        <>
          <dt>On the way</dt>
          <dd>
            {m.notes.map((x) => (
              <div key={x}>
                <Rich text={x} />
              </div>
            ))}
          </dd>
        </>
      ) : null}
      <dt>Verdict</dt>
      <dd>{m.verdict ? <Rich text={m.verdict} /> : <span className="dim">running</span>}</dd>
      <dt>Next</dt>
      <dd>{m.next ? <Rich text={m.next} /> : <span className="dim">to be decided on the result</span>}</dd>
      <dt>Decided by</dt>
      <dd>{m.by}</dd>
    </dl>
  );
}

const HALVES: [string, string, string][] = [
  ["motor_side", "-z", "The motor side"],
  ["cover", "+z", "The cover"],
];

function ringPath(p: Poly): string {
  return p.length ? `M${p.map((q) => `${q[0].toFixed(1)},${q[1].toFixed(1)}`).join("L")}Z` : "";
}

function SpaceView({ ctx, space, prev, pictures }: { ctx: Context; space: Space; prev: Space | null; pictures: string[] }) {
  const [x0, y0, x1, y1] = ctx.box;
  const restricted = !!space.regions && !space.features;
  return (
    <div className="cg-space">
      <p className="cg-space-words">
        {space.changed ? <span className="pr-pill" data-mark="change">changed</span> : <span className="pr-pill">unchanged</span>} <b>{space.name}</b>: {space.words}
        {prev && prev.name !== space.name ? (
          <span className="dim">{prev.regions ? ` · dashed: the space before (${prev.name})` : ` · before: ${prev.name}`}</span>
        ) : null}
        {space.fill && Object.keys(space.fill).length ? <span className="dim"> · each region shaded by how much of its plan the optimiser filled</span> : null}
      </p>
      <div className="cg-space-halves">
        {HALVES.map(([half, side, label]) => (
          <figure key={half}>
            <svg viewBox={`${x0} ${y0} ${x1 - x0} ${y1 - y0}`} role="img" aria-label={`${label}: the design space in plan`}>
              <g transform={`translate(0 ${y0 + y1}) scale(1 -1)`}>
                {(ctx.halves[half] ?? []).map((p, i) => (
                  <path key={`in${i}`} d={ringPath(p)} className={restricted ? "cg-inside" : "cg-inside cg-free"} />
                ))}
                {prev?.regions
                  ? (prev.regions[half] ?? []).map((r, i) => <path key={`pv${i}`} d={[r.outline, ...r.holes].map(ringPath).join("")} className="cg-prev" fillRule="evenodd" />)
                  : null}
                {space.regions
                  ? (space.regions[half] ?? []).map((r, i) => {
                      const f = space.fill?.[`${half}|${r.name}`];
                      return (
                        <path
                          key={`rg${i}`}
                          d={[r.outline, ...r.holes].map(ringPath).join("")}
                          className={r.kind === "empty" ? "cg-region cg-empty" : r.kind === "feature" ? "cg-region cg-feature" : "cg-region"}
                          fillRule="evenodd"
                          style={f ? { fillOpacity: 0.15 + 0.75 * f.covered } : undefined}
                        >
                          <title>
                            {r.kind === "empty"
                              ? `${r.name}: no feature, held empty`
                              : f
                                ? `${r.name}: ${(100 * f.covered).toFixed(0)} % of its plan filled, members ${f.height_mm.toFixed(0)} mm high`
                                : r.name}
                          </title>
                        </path>
                      );
                    })
                  : null}
                {ctx.bores
                  .filter((b) => b.side === side)
                  .map((b) => (
                    <circle key={b.shaft} cx={b.axis[0]} cy={b.axis[1]} r={b.r} className="cg-bore">
                      <title>{`the ${b.shaft} bore`}</title>
                    </circle>
                  ))}
                {ctx.bolts.map((b, i) => (
                  <circle key={`b${i}`} cx={b[0]} cy={b[1]} r={10} className="cg-bolt" />
                ))}
                {half === "motor_side"
                  ? ctx.mounts.map((m) => (
                      <circle key={m.name} cx={m.centre[0]} cy={m.centre[1]} r={m.r} className="cg-mount">
                        <title>{m.name}</title>
                      </circle>
                    ))
                  : null}
              </g>
            </svg>
            <figcaption>{label}</figcaption>
          </figure>
        ))}
      </div>
      {pictures.length ? (
        <div className="cg-pictures">
          {pictures.map((p) => {
            const url = picture(p);
            return url ? (
              <a key={p} href={url} target="_blank" rel="noreferrer" title="the full picture">
                <img src={url} alt={p} />
              </a>
            ) : null;
          })}
        </div>
      ) : null}
    </div>
  );
}

function ResultView({ m, go }: { m: Move; go: TabProps["go"] }) {
  if (!m.results.length) return <div className="vol-empty">This move made no design.</div>;
  return (
    <div className="cg-results">
      <table className="pr-grade-table">
        <thead>
          <tr>
            <th>Result</th>
            <th>The optimiser's own check</th>
            <th>FE, the judge</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody>
          {m.results.map((r, i) => (
            <tr key={`${r.label}|${r.design ?? ""}|${i}`}>
              <td>
                {r.label}
                {r.design ? (
                  <div>
                    <button type="button" className="cg-link mono" onClick={() => go({ view: "designs", id: r.design! })}>
                      {r.design}
                    </button>
                  </div>
                ) : null}
              </td>
              <td className="mono">
                {r.model?.done ? (
                  <>
                    {kg(r.model.kg)} · tilt {r.model.tilt?.toFixed(2)}× · beds {r.model.beds_um?.toFixed(1)} µm
                    <div className="dim">
                      held at 1/{r.model.safety}
                      {r.model.safety_beds !== r.model.safety ? ` (beds 1/${r.model.safety_beds})` : ""}
                      {r.model.free_voxels ? ` · ${r.model.free_voxels.toLocaleString()} free voxels` : ""}
                    </div>
                  </>
                ) : r.model ? (
                  <span className="dim">not finished</span>
                ) : (
                  <span className="dim">-</span>
                )}
              </td>
              <td className="mono">
                {r.fe ? (
                  <>
                    <span className="pr-pill" data-mark={r.fe.mass_ok ? "pass" : "fail"}>{kg(r.fe.kg)}</span>{" "}
                    <span className="pr-pill" data-mark={r.fe.beds_ok ? "pass" : "fail"}>beds {r.fe.beds_um.toFixed(1)} µm</span>{" "}
                    <span className="pr-pill" data-mark={r.fe.tilt_ok ? "pass" : "fail"}>tilt {r.fe.tilt.toFixed(2)}×</span>{" "}
                    <span className="pr-pill" data-mark={r.fe.orders_ok ? "pass" : "fail"}>
                      {r.fe.first_hz?.toFixed(0) ?? "-"} Hz{r.fe.clashes.length ? `, ${r.fe.clashes.length} clash` : ""}
                    </span>
                  </>
                ) : (
                  <span className="dim">not judged</span>
                )}
              </td>
              <td>
                {r.fe ? (
                  <span className="pr-pill mono" data-mark={r.fe.pass ? "pass" : "fail"}>
                    {r.fe.pass ? "passes" : "fails"}
                  </span>
                ) : (
                  <span className="pr-pill mono">model only</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="cg-pictures">
        {m.results
          .filter((r) => r.picture)
          .map((r, i) => {
            const url = picture(r.picture);
            return url ? (
              <button key={`${r.label}|${r.design ?? ""}|${i}`} type="button" className="cg-shot" onClick={() => r.design && go({ view: "designs", id: r.design })} title="open the design">
                <img src={url} alt={r.design ?? r.label} />
                <span className="mono">{r.design}</span>
              </button>
            ) : null;
          })}
      </div>
    </div>
  );
}

const SETTING_NAMES: Record<string, string> = {
  objective: "Objective",
  budget: "Mass",
  voxel_mm: "Voxel, mm",
  height_limit_mm: "Height limit, mm",
  smoothing_mm: "Plan smoothing, mm",
  safety: "Factor of safety",
  safety_beds: "Beds' own factor",
  load_case: "Load case",
  mounts: "Mounts",
  space: "Design space",
  drawing: "Drawing",
};

export function AgentCard({ route, onCollapse }: CardProps) {
  const c = chosenCampaign(route);
  const m = c ? chosenMove(c, route) : null;
  const prev = c && m ? [...c.moves].filter((x) => x.n < m.n).pop() ?? null : null;
  return (
    <div className="entity-card">
      <div className="entity-card-bar">
        <span className="dim">the move</span>
        <button className="icon" type="button" onClick={onCollapse} title="Fold the card away">
          ›
        </button>
      </div>
      <div className="entity-card-scroll">
        {!c || !m ? (
          <div className="dim card-pad">Pick a campaign.</div>
        ) : (
          <div className="pr-card">
            <div className="pr-card-kicker">
              Move {m.n} · iteration {m.iteration} · {m.kind}
            </div>
            <h3 className="pr-card-title">{m.title}</h3>
            <p className="pr-card-method">
              {hhmm(m.at)}
              {m.until ? `-${hhmm(m.until)}` : ", running"} · decided by {m.by}
            </p>
            <dl className="pr-card-facts">
              {Object.entries(m.settings).map(([k, v]) => {
                const was = prev?.settings[k];
                const moved = prev != null && was !== undefined && String(was) !== String(v);
                return (
                  <span key={k} className="pr-card-row" data-moved={moved}>
                    <dt>{SETTING_NAMES[k] ?? k}</dt>
                    <dd className="mono">
                      {v == null ? "-" : String(v)}
                      {moved ? <span className="dim"> (was {was == null ? "-" : String(was)})</span> : null}
                    </dd>
                  </span>
                );
              })}
              {[...new Set(m.results.map((r) => r.run).filter((run): run is string => !!run))].map((run) => (
                <span key={run} className="pr-card-row">
                  <dt>Run</dt>
                  <dd className="mono cg-stem">{run}</dd>
                </span>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
