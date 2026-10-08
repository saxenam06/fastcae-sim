/**
 * The pages' small pieces, shared by every tab: the head, a section, a value in its box, a source
 * label, a method shown as a pre-selected choice, a row still to come.
 *
 * Every page opens the same way: what it is, what it is about, where it stands. A source is two
 * words styled by its kind (published, standard, assumed, yours, calculated), with the full
 * citation on hover. A product's form shows where a value came from at a glance; the reader who
 * wants the reference points at it.
 */

import type { ReactNode } from "react";
import type { Sourced } from "../records/types";

/** A page's head: its kind, its title and subject, and on the right where it stands. */
export function PageHead({
  kicker,
  title,
  sub,
  side,
}: {
  kicker: string;
  title: string;
  sub: string;
  side?: ReactNode;
}) {
  return (
    <header className="cp-head">
      <div className="cp-head-main">
        <div className="cp-kicker">{kicker}</div>
        <h1>{title}</h1>
        <div className="cp-sub">{sub}</div>
      </div>
      {side ? <div className="cp-head-side">{side}</div> : null}
    </header>
  );
}

/** A small status label: done (green), waiting (ochre, dashed), or plain. */
export function Badge({ tone, children }: { tone?: "ok" | "wait" | "bad"; children: ReactNode }) {
  const ok = tone === "ok" ? true : tone === "bad" ? false : undefined;
  return (
    <span className="cp-badge" data-ok={ok} data-tone={tone === "wait" ? "next" : undefined}>
      {children}
    </span>
  );
}

export function Section({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="cp-section">
      <header>
        <h2>{title}</h2>
        {aside ? <span className="cp-aside">{aside}</span> : null}
      </header>
      {children}
    </section>
  );
}

/** A value as a form shows it: in its box, numbers in mono. */
export function Value({ value, options }: { value: string; options?: string[] }) {
  if (options && options.length) {
    // A choice already made: shown as a pre-selected drop-down, the others listed on hover.
    return (
      <span className="cp-value cp-choice" title={`Options: ${options.join(" · ")}`}>
        {value}
        <i aria-hidden="true">▾</i>
      </span>
    );
  }
  return <span className="cp-value">{value}</span>;
}

export function Source({ s }: { s: Sourced }) {
  if (!s.source) return null;
  return (
    <span className="prov" data-prov={s.kind || undefined} title={s.title}>
      {s.source}
    </span>
  );
}

/** A method as a pre-selected choice, with its authors or standard in brackets. */
export function Method({ method, by, fn }: { method: string; by: string; fn: string }) {
  return (
    <span className="cp-method" title={`Pre-selected. Calls ${fn}`}>
      {method}
      {by ? <em> ({by})</em> : null}
      <i aria-hidden="true">▾</i>
    </span>
  );
}
