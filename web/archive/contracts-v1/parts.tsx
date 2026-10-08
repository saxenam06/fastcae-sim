/**
 * The pieces the Contracts pages share: an entry as a row, entries in their groups, a box of the
 * Binding page, the verdict chip, a clickable table row, and what a page says of a contract that
 * does not load.
 *
 * An entry is always one row - what, its value, where it came from - and always opens in the card
 * when clicked, whichever page it is on: the card is where an entry is read in full, so every
 * mention of one is a way there.
 */

import { Fragment, type KeyboardEvent, type ReactNode, useEffect, useRef } from "react";
import type { Go } from "../app/route";
import { Dot, Prov } from "../panel/bits";
import type { ContractView, Snapshot } from "../records/types";
import type { Group, Row } from "./model";
import { assumptionIn, verdictOf } from "./model";

/**
 * A ref for a page's scrolling sheet that brings the row in focus into view whenever the focus
 * changes - so an address opened with a focus shows its row - and does not move when the row is
 * in view already, so a click never makes the page jump.
 */
export function useRevealFocus(focus: string | null, contract: string) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const row = ref.current?.querySelector('[data-focus="true"]');
    if (row instanceof HTMLElement) row.scrollIntoView({ block: "nearest" });
  }, [focus, contract]);
  return ref;
}

/** Props that make a table row act as a button: clicked, or Enter or Space when focused. */
export function clickable(act: () => void) {
  return {
    "data-click": true,
    tabIndex: 0,
    onClick: act,
    onKeyDown: (event: KeyboardEvent) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        act();
      }
    },
  };
}

export function VerdictChip({ c }: { c: ContractView }) {
  const v = verdictOf(c);
  return (
    <span className="chip" data-outcome={v.outcome} title={c.loaded ? "What the validator says of it as it is" : undefined}>
      {v.words}
    </span>
  );
}

/** What every page of the tab is given: the snapshot, the contract in view, the focus, a way to move. */
export interface PageProps {
  snap: Snapshot;
  c: ContractView;
  focus: string | null;
  go: Go;
}

/**
 * One entry: its label, its value as written, its provenance. Long labels wrap rather than hide,
 * because a label cut short is the one thing on the row that says what the value is.
 *
 * Given the route's focus, the row marks itself in focus, or - when the focus is an assumption -
 * as one of the entries that assumption sets, so one assumption can be seen across the page.
 */
export function EntryRow({
  row,
  nested = false,
  focus,
  onFocus,
  extra,
  prov = true,
}: {
  row: Row;
  nested?: boolean;
  focus: string | null;
  onFocus: (path: string) => void;
  /** A second line under the label: a note, the bounds. */
  extra?: ReactNode;
  /** Off where the whole list shares one provenance, as a source's entries do. */
  prov?: boolean;
}) {
  const e = row.entry;
  const assumption = assumptionIn(focus);
  return (
    <button
      className="ct-row"
      data-nested={nested}
      data-focus={focus === e.path}
      data-related={assumption !== null && e.provenance.assumption_id === assumption}
      onClick={() => onFocus(e.path)}
      title={`${e.label}\n${e.path}`}
    >
      <span className="ct-row-label">
        {row.label}
        {extra ? <span className="ct-row-extra">{extra}</span> : null}
      </span>
      <span className="ct-row-value mono">{e.value}</span>
      <span className="ct-row-prov">{prov ? <Prov kind={e.provenance.kind} /> : null}</span>
    </button>
  );
}

/** Entries under their group heads, and within a group under the head of the item they belong to. */
export function EntryGroups({
  groups,
  focus,
  onFocus,
}: {
  groups: Group[];
  focus: string | null;
  onFocus: (path: string) => void;
}) {
  return (
    <div className="ct-rows">
      {groups.map((g) => (
        <Fragment key={g.name}>
          <div className="ct-group">
            {g.name} <span className="count">{g.count}</span>
          </div>
          {g.bunches.map((b, i) => (
            <Fragment key={b.item?.path ?? `${g.name}:${i}`}>
              {b.item ? (
                <div className="ct-item" title={b.item.path}>
                  {b.item.name}
                  {b.item.detail ? <span className="dim"> · {b.item.detail}</span> : null}
                </div>
              ) : null}
              {b.rows.map((r) => (
                <EntryRow key={r.entry.path} row={r} nested={b.item !== null} focus={focus} onFocus={onFocus} />
              ))}
            </Fragment>
          ))}
        </Fragment>
      ))}
    </div>
  );
}

/** A box of the Binding page: what binds a design, one kind of binding a box. */
export function Box({
  n,
  title,
  sub,
  count,
  order,
  children,
}: {
  n: number;
  title: string;
  sub: string;
  count?: ReactNode;
  order: number;
  children: ReactNode;
}) {
  return (
    <section className="ct-box" style={{ order }}>
      <header>
        <span className="ct-box-n mono">{n}</span>
        <span className="ct-box-title">{title}</span>
        <span className="ct-box-sub">· {sub}</span>
        {count !== undefined ? <span className="count">{count}</span> : null}
      </header>
      <div className="ct-box-body">{children}</div>
    </section>
  );
}

/** A line inside a box that is not an entry: a fact of the contract, or a place still blank. */
export function Line({ label, children, blank = false }: { label?: string; children: ReactNode; blank?: boolean }) {
  return (
    <div className="ct-line" data-blank={blank}>
      {blank ? <Dot status="blank" title="Not built yet" /> : null}
      {label ? <span className="ct-line-label">{label}</span> : null}
      <span className="ct-line-text">{children}</span>
    </div>
  );
}

/** What a page that reads entries says of a contract that does not load: its refusals, nothing else. */
export function Unloaded({ c }: { c: ContractView }) {
  return (
    <div className="stage-scroll ct-page">
      <header className="page-head">
        <h1 className="mono">{c.id}</h1>
        <span className="chip" data-outcome="reject">
          does not load
        </span>
      </header>
      <div className="blank">
        <h3>The validator refuses it before it reads its entries</h3>
        <div className="blank-body">
          <span className="mono">{c.file}</span>
          {c.refusals.map((r, i) => (
            <div key={i}>
              <span className="mono">{r.rule}</span> · <span className="mono">{r.entry || "-"}</span> · {r.reason}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
