/**
 * The small pieces every tab uses: provenance, stage and status marks, a block, a blank, a card's
 * frame, a hash. Each carries its meaning by shape as well as colour, as fastcae's marks do.
 */

import type { ReactNode } from "react";
import { PROVENANCE, STAGES } from "../app/product";
import type { ProvenanceKind, Stage } from "../records/types";

/** Where a value came from, as a pill: its colour and its underline - solid, dotted or dashed. */
export function Prov({ kind }: { kind: ProvenanceKind }) {
  const p = PROVENANCE[kind];
  return (
    <span className="prov" data-prov={kind} title={p.words}>
      {p.label}
    </span>
  );
}

/** The same, as a dot for a row. */
export function ProvDot({ kind }: { kind: ProvenanceKind }) {
  return <i className="prov-dot" data-prov={kind} title={PROVENANCE[kind].words} />;
}

/** A contract's three stages as dots: filled up to the one it has reached. */
export function StageDots({ stage }: { stage: Stage }) {
  const reached = STAGES.findIndex((s) => s.id === stage);
  return (
    <span className="stage-dots" title={`${stage}: ${STAGES[reached].words}`}>
      {STAGES.map((s, i) => (
        <i key={s.id} data-reached={i <= reached} data-stage={s.id} />
      ))}
    </span>
  );
}

export type Status = "done" | "running" | "failed" | "pending" | "skipped" | "blank";

/** A status dot: green done, pulsing ochre running, red failed, hollow to do, dashed not built. */
export function Dot({ status, title }: { status: Status; title?: string }) {
  return <i className="sdot" data-status={status} title={title} />;
}

/** A titled block of a page. */
export function Block({
  title,
  count,
  aside,
  children,
}: {
  title: ReactNode;
  count?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="block">
      <h2>
        {title}
        {count !== undefined ? <span className="count"> {count}</span> : null}
        {aside ? <span className="block-aside">{aside}</span> : null}
      </h2>
      {children}
    </section>
  );
}

/**
 * What a page shows before anything fills it: what will be here, and what makes it. Kept to a few
 * words - the page's layout around it says the rest.
 */
export function Blank({ title, waits, children }: { title: string; waits: string; children?: ReactNode }) {
  return (
    <div className="blank">
      <h3>{title}</h3>
      {children ? <div className="blank-body">{children}</div> : null}
      <p className="blank-waits">
        <Dot status="blank" /> {waits}
      </p>
    </div>
  );
}

/** The right-hand card's frame: its kind on the bar, a fold button, a scrolling body. */
export function CardFrame({
  kind,
  onCollapse,
  children,
}: {
  kind: string;
  onCollapse: () => void;
  children: ReactNode;
}) {
  return (
    <div className="entity-card">
      <div className="entity-card-bar">
        <span className="dim">{kind}</span>
        <button className="icon" onClick={onCollapse} title="Fold the card away">
          ›
        </button>
      </div>
      <div className="entity-card-scroll">{children}</div>
    </div>
  );
}

/** A hash, shortened, the whole of it selectable and on hover. */
export function Hash({ value }: { value: string | null }) {
  if (!value) return <span className="dim">-</span>;
  const [algo, digest] = value.includes(":") ? value.split(":") : ["", value];
  return (
    <span className="hash mono" title={value}>
      {algo ? `${algo}:` : ""}
      {digest.slice(0, 12)}
    </span>
  );
}

/** A count that reads as none when it is zero. */
export function Count({ n }: { n: number }) {
  return (
    <span className="num" data-zero={n === 0}>
      {n.toLocaleString("en-GB")}
    </span>
  );
}
