/**
 * The design's process (LOP-21; the engineer, 10 October 23:47, 11 October 00:01 and 02:08): the
 * designs on the left, the chosen design's flow step by step in the centre, the step's card on the
 * right. Every flow tried keeps its own tabs, named by what it did: flow A, the CAD route, drew the
 * housing in OCC right after the optimisation; flow B, the mesh route, does the booleans on meshes
 * and FE straight from them. A step's view is the one its kind needs: the contract's volumes (and
 * the optimiser's voxels), a run's field, a design's body, FE's mesh and its results.
 *
 * The data: `../records/process/<design>.json` (`prototypes/first_loop/process_export.py`): the flow,
 * each step's name, method, time, view and card. The numbers on a design's card come from the
 * designs' index (`names.py`'s summary).
 */

import type { CardProps, TabProps } from "../app/tab";
import { Volumes } from "../contracts/Volumes";
import { DesignMesh } from "./DesignView";
import { FeView } from "./FeView";
import { RunView } from "./Optimisation";

/** A grade's line: what, the design's value, the limit, whether it holds. */
type GradeRow = [string, string, string, boolean];

interface Step {
  id: string;
  label: string;
  method: string;
  /** Its time; null on the second tab of a stage drawn as two (`of` names the first), and on a
   * stage run beside another (`beside` names it). */
  seconds?: number | null;
  of?: string;
  beside?: string;
  ok?: boolean;
  note?: string;
  view: {
    kind: "volumes" | "field" | "design" | "fe" | "grade" | "image" | "none";
    voxels?: boolean;
    run?: string;
    stem?: string;
    field?: string | null;
    rows?: GradeRow[];
    verdict?: boolean | null;
    /** a picture beside the records (`process_export.py` copies it): a field's reading in plan */
    src?: string;
  };
  card: [string, string][];
}

interface ProcessFile {
  design: string;
  flow: { id: string; name: string; words: string };
  steps: Step[];
  seconds: number;
}

interface Summary {
  cad_kg?: number | null;
  drive_um?: number;
  tilt?: number;
  mode_hz?: number | null;
  clashes?: number;
  castable?: boolean;
  undercut?: number;
  passes?: { beds: boolean; tilt: boolean; mode: boolean; mass: boolean };
}

const PROCESS = import.meta.glob(["../records/process/*.json", "!../records/process/*_fe.json"], { eager: true }) as Record<string, { default: ProcessFile }>;
const IMAGES = import.meta.glob("../records/process/*.png", { eager: true, query: "?url", import: "default" }) as Record<string, string>;
const INDEX_FILES = import.meta.glob("../records/designs/_index.json", { eager: true }) as Record<
  string,
  { default: Record<string, { title: string; time?: number; summary?: Summary | null }> }
>;
const INDEX = Object.values(INDEX_FILES)[0]?.default ?? {};

// Newest first (the engineer, 11 October 13:49: "the last run should not land anywhere"): each
// design by when it was drawn (the designs' index, `names.py`), each flow placed by its newest
const madeAt = (design: string) => INDEX[design]?.time ?? 0;
const RECORDS: ProcessFile[] = Object.values(PROCESS)
  .map((m) => m.default)
  .sort((a, b) => madeAt(b.design) - madeAt(a.design) || a.design.localeCompare(b.design));
const FLOWS = [...new Map(RECORDS.map((r) => [r.flow.id, r.flow])).values()];

function chosen(route: TabProps["route"]): ProcessFile | null {
  return RECORDS.find((r) => r.design === route.id) ?? RECORDS[0] ?? null;
}

// A design opens on its own body, shaded (the engineer, 11 October 14:28: the FE mesh's triangles are
// not the design): the machined housing, else its drawn body, else the flow's first step
function stepOf(rec: ProcessFile, route: TabProps["route"]): Step | null {
  const body = rec.steps.find((s) => s.id === "machined") ?? rec.steps.find((s) => s.id === "body");
  return rec.steps.find((s) => s.id === route.focus) ?? body ?? rec.steps[0] ?? null;
}

const time = (s?: number | null) => (s == null ? "" : s >= 90 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(0)} s`);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** When a design was drawn, local time ("11 Oct 13:29"); "" when its index has no time. */
const when = (t: number) => {
  if (!t) return "";
  const d = new Date(t * 1000);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")} · `;
};
const mark = (ok?: boolean) => (ok == null ? undefined : ok ? "pass" : "fail");
const titleOf = (design: string) => INDEX[design]?.title ?? design;

export function ProcessRail({ route, go }: TabProps) {
  const current = chosen(route);
  if (!RECORDS.length) {
    return <div className="rail-note">No design's process exported yet: run prototypes/first_loop/process_export.py.</div>;
  }
  return (
    <nav className="pr-rail">
      {FLOWS.map((flow) => (
        <section key={flow.id} className="pr-flow">
          <header className="pr-flow-head" title={flow.words}>
            <span className="pr-flow-id">Flow {flow.id}</span> {flow.name}
          </header>
          {RECORDS.filter((r) => r.flow.id === flow.id).map((r) => {
            const s = INDEX[r.design]?.summary ?? {};
            return (
              <button
                key={r.design}
                type="button"
                className="pr-design"
                data-on={current?.design === r.design}
                onClick={() => go({ id: r.design, focus: null })}
                title={r.design}
              >
                <span className="pr-design-id mono">{r.design}</span>
                <span className="pr-design-name">{titleOf(r.design)}</span>
                <span className="pr-design-time mono">
                  {when(madeAt(r.design))}
                  {time(r.seconds)} end to end
                </span>
                <span className="pr-pills">
                  <span className="pr-pill mono" data-mark={mark(s.passes?.mass)}>{s.cad_kg != null ? `${s.cad_kg.toFixed(2)} kg` : "- kg"}</span>
                  <span className="pr-pill mono" data-mark={mark(s.passes?.beds)}>{s.drive_um != null ? `beds ${s.drive_um.toFixed(0)} µm` : "beds -"}</span>
                  <span className="pr-pill mono" data-mark={mark(s.passes?.tilt)}>{s.tilt != null ? `tilt ${s.tilt.toFixed(2)}×` : "tilt -"}</span>
                  <span className="pr-pill mono" data-mark={mark(s.passes?.mode)}>
                    {s.mode_hz ? `${s.mode_hz.toFixed(0)} Hz${s.clashes ? `, ${s.clashes} clash` : ""}` : "modes -"}
                  </span>
                  <span className="pr-pill mono" data-mark={mark(s.castable)}>{s.undercut != null ? `undercut ${(100 * s.undercut).toFixed(1)} %` : "cast -"}</span>
                </span>
                <span className="pr-dots">
                  {r.steps.map((st) => (
                    <i key={st.id} data-ok={st.ok !== false} title={`${st.label}${st.seconds ? `: ${time(st.seconds)}` : ""}`} />
                  ))}
                </span>
              </button>
            );
          })}
        </section>
      ))}
      <section className="pr-flow">
        <header className="pr-flow-head">The design to beat</header>
        <div className="pr-design pr-reference">
          <span className="pr-design-name">The reference housing</span>
          <span className="pr-pills">
            <span className="pr-pill mono">7.73 kg</span>
            <span className="pr-pill mono">beds 52 µm</span>
          </span>
        </div>
      </section>
    </nav>
  );
}

export function ProcessStage({ route, go }: TabProps) {
  const rec = chosen(route);
  if (!rec) {
    return (
      <div className="stage-scroll">
        <div className="vol-empty">No design's process exported yet: run prototypes/first_loop/process_export.py &lt;design&gt;.</div>
      </div>
    );
  }
  const step = stepOf(rec, route);
  return (
    <div className="stage-scroll pr-stage">
      <header className="pr-head">
        <div className="pr-head-kicker">
          Flow {rec.flow.id} · {rec.flow.name} · {time(rec.seconds)} end to end
        </div>
        <h2 className="pr-head-title">{titleOf(rec.design)}</h2>
        <p className="pr-head-words">{rec.flow.words}</p>
      </header>
      <nav className="pr-steps" aria-label="the design's steps">
        {rec.steps.map((s, i) => (
          <button
            key={s.id}
            type="button"
            className="pr-step"
            data-on={step?.id === s.id}
            data-ok={s.ok !== false}
            onClick={() => go({ id: rec.design, focus: s.id })}
            title={s.method}
          >
            <span className="pr-step-n mono">{i + 1}</span> {s.label}
            {s.seconds ? <span className="pr-step-t mono">{time(s.seconds)}</span> : null}
            {s.beside ? <span className="pr-step-t mono">∥ {rec.steps.find((o) => o.id === s.beside)?.label ?? s.beside}</span> : null}
          </button>
        ))}
      </nav>
      <div className="pr-view">{step ? <StepView rec={rec} step={step} /> : null}</div>
    </div>
  );
}

function StepView({ rec, step }: { rec: ProcessFile; step: Step }) {
  const v = step.view;
  if (v.kind === "volumes") return <Volumes key={v.voxels ? "voxels" : "exact"} voxels={v.voxels} />;
  if (v.kind === "field" && v.run) return <RunView key={v.run} stem={v.run} />;
  if (v.kind === "design" && v.stem) return <DesignMesh key={v.stem} stem={v.stem} />;
  if (v.kind === "fe") return <FeView key={`${rec.design}-${v.field ?? "mesh"}`} design={rec.design} field={v.field ?? null} />;
  if (v.kind === "grade") return <GradeView rows={v.rows ?? []} verdict={v.verdict ?? null} />;
  if (v.kind === "image" && v.src) {
    const url = IMAGES[`../records/process/${v.src}`];
    return url ? <img className="pr-image" src={url} alt={step.label} /> : <div className="vol-empty">No picture exported ({v.src}).</div>;
  }
  return <div className="vol-empty">This step has no picture.</div>;
}

/** The grade: every line of the contract the design is judged on, its value, its limit, its verdict. */
function GradeView({ rows, verdict }: { rows: GradeRow[]; verdict: boolean | null }) {
  if (!rows.length) return <div className="vol-empty">Not graded yet (prototypes/first_loop/grade.py).</div>;
  const held = rows.filter((r) => r[3]).length;
  return (
    <div className="pr-grade">
      <div className="pr-grade-verdict" data-mark={verdict ? "pass" : "fail"}>
        {verdict ? `Passes all ${rows.length} lines` : `Fails ${rows.length - held} of ${rows.length} lines`}
      </div>
      <table className="pr-grade-table">
        <thead>
          <tr>
            <th>Line</th>
            <th>The design</th>
            <th>The limit</th>
            <th>Verdict</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([what, value, limit, ok]) => (
            <tr key={what}>
              <td>{what}</td>
              <td className="mono">{value}</td>
              <td className="dim">{limit}</td>
              <td>
                <span className="pr-pill mono" data-mark={ok ? "pass" : "fail"}>
                  {ok ? "pass" : "fail"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProcessCard({ route, onCollapse }: CardProps) {
  const rec = chosen(route);
  const step = rec ? stepOf(rec, route) : null;
  return (
    <div className="entity-card">
      <div className="entity-card-bar">
        <span className="dim">the step</span>
        <button className="icon" type="button" onClick={onCollapse} title="Fold the card away">
          ›
        </button>
      </div>
      <div className="entity-card-scroll">
        {!rec || !step ? (
          <div className="dim card-pad">Pick a design.</div>
        ) : (
          <div className="pr-card">
            <div className="pr-card-kicker">
              Flow {rec.flow.id} · step {rec.steps.indexOf(step) + 1} of {rec.steps.length}
            </div>
            <h3 className="pr-card-title">{step.label}</h3>
            <p className="pr-card-method">{step.method}</p>
            <dl className="pr-card-facts">
              {step.seconds ? (
                <>
                  <dt>Time</dt>
                  <dd className="mono">{time(step.seconds)}</dd>
                </>
              ) : null}
              {step.of || step.beside ? (
                <>
                  <dt>Time</dt>
                  <dd>
                    {step.of ? "the same stage as " : "beside "}
                    {rec.steps.find((o) => o.id === (step.of ?? step.beside))?.label ?? ""}
                  </dd>
                </>
              ) : null}
              {step.ok === false ? (
                <>
                  <dt>Outcome</dt>
                  <dd className="pr-fail">failed</dd>
                </>
              ) : null}
              {step.note ? (
                <>
                  <dt>Note</dt>
                  <dd>{step.note}</dd>
                </>
              ) : null}
              {step.card.map(([k, val]) => (
                <span key={k} className="pr-card-row">
                  <dt>{k}</dt>
                  <dd className="mono">{val}</dd>
                </span>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
