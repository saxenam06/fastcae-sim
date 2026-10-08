/**
 * The small pieces the Campaigns and Designs tabs share: the template row a table shows before it
 * has records, a long text cut to a few lines with the whole of it on hover, the status code gave a
 * hypothesis, a design's verdict and grade, and a card's folding section.
 *
 * A template row is drawn faint, italic and dashed (zenryx.css `tr.template`): it is the shape a
 * record will take, written in words, and never an example value that could be read as a result.
 */

import type { ReactNode } from "react";
import type { Candidate, HypothesisStatus } from "../records/types";
import { kg, pct } from "./records";
import { STATUS } from "./words";
// The Designs tab draws these too; their styles come with them, whichever tab loads them first.
import "./campaigns.css";

/** A column of a records table, with what its template cell says will go there. */
export interface Column {
  id: string;
  label: string;
  template: string;
  /**
   * How the column's record cells sit: a long text (`cmp-wide`), a narrow index (`cmp-narrow`), a
   * number (`num`). The head takes the number's alignment; the template row takes none of them.
   */
  kind?: "wide" | "narrow" | "num";
  /** The least width the column keeps, in pixels, so a sheet of many columns stays readable. */
  min?: number;
  /** What the column's head says on hover. */
  title?: string;
}

/**
 * The one row a table shows before it has records: what each cell will hold, in words. Its cells
 * are always words, so they wrap as text whatever the column's records will be.
 */
export function TemplateRow({ columns }: { columns: Column[] }) {
  return (
    <tr className="template">
      {columns.map((c) => (
        <td key={c.id}>{c.template}</td>
      ))}
    </tr>
  );
}

/** A table head drawn from the same columns: each column's least width is kept on its head. */
export function TableHead({ columns }: { columns: Column[] }) {
  return (
    <thead>
      <tr>
        {columns.map((c) => (
          <th
            key={c.id}
            className={c.kind === "num" ? "num" : undefined}
            title={c.title}
            style={c.min ? { minWidth: c.min } : undefined}
          >
            {c.label}
          </th>
        ))}
      </tr>
    </thead>
  );
}

/** A long text kept to three lines in a row, the whole of it on hover. */
export function Clamp({ text, title }: { text: string; title?: string }) {
  return (
    <span className="cmp-clamp" title={title ?? text}>
      {text}
    </span>
  );
}

/** The status code gave a hypothesis. Its line pattern carries it as well as its colour. */
export function StatusPill({ status }: { status: HypothesisStatus }) {
  return (
    <span className="pill cmp-status" data-status={status} title={`${STATUS[status].words} (computed by code)`}>
      {STATUS[status].label}
    </span>
  );
}

/** Pass, fail, or not judged yet: the deterministic evaluator's word, never the agent's. */
export function Verdict({ passed, failure }: { passed: boolean | null; failure?: string | null }) {
  if (passed === null)
    return (
      <span className="pill" title={failure ?? "Not judged yet"}>
        {failure ? "failed" : "not judged"}
      </span>
    );
  return (
    <span className="vs-verdict" data-pass={passed} title={failure ?? undefined}>
      {passed ? "pass" : "fail"}
    </span>
  );
}

/** A design's grade in one line: the verdict, the worst margin, the mass - each only if recorded. */
export function Grade({ design }: { design: Candidate }) {
  return (
    <span className="cmp-grade">
      <Verdict passed={design.passed} failure={design.failure} />
      {design.worst_margin !== null ? (
        <span className="num" title="the worst margin over every check, as a share of its limit">
          {pct(design.worst_margin)}
        </span>
      ) : null}
      {design.mass_kg !== null ? <span className="num dim">{kg(design.mass_kg)}</span> : null}
    </span>
  );
}

/** A section of the right-hand card, open by default, as fastcae's are. */
export function Part({ title, count, children }: { title: string; count?: ReactNode; children: ReactNode }) {
  return (
    <details className="card-section" open>
      <summary>
        {title}
        {count !== undefined ? <span className="count"> {count}</span> : null}
      </summary>
      {children}
    </details>
  );
}

/** The one dim line a card section shows until a record fills it: what it will hold. */
export function Holds({ children }: { children: ReactNode }) {
  return <p className="cmp-holds">{children}</p>;
}
