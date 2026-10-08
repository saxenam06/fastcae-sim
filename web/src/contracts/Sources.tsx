/**
 * Sources: the contract read from the other side - not value by value, but source by source.
 *
 * A block a provenance kind, in the order of how firmly a value is held (published, a standard,
 * measured, derived by a tool, assumed, the engineer's), each source a card with its left rule in
 * its kind's line so the page can be scanned for the dashed ones. A source says what it is - the
 * citation, the tool run with its input hash, the assumption with its reason, who and when - and
 * lists the entries it supports. A kind with no source is drawn and says so. The published values
 * kept as a plausibility band close the page, apart, because they are never limits.
 */

import { useMemo } from "react";
import { PROVENANCE, PROVENANCE_ORDER } from "../app/product";
import { Block, Hash, Prov } from "../panel/bits";
import type { ProvenanceKind, Reference } from "../records/types";
import type { Source } from "./model";
import { assumptionFocus, sourcesOf } from "./model";
import { EntryRow, Unloaded, useRevealFocus, type PageProps } from "./parts";

/** What a kind with no source says. Measured values come with the later entry point (an existing part). */
const NONE: Record<ProvenanceKind, string> = {
  published: "none",
  standard: "none",
  measured: "none: measured values come with the later entry point, an existing part",
  derived: "none yet: the load tool (GBX-1) derives the interfaces and the physics, not built",
  assumption: "none",
  engineer: "none",
};

export function Sources({ c, focus, go }: PageProps) {
  const sources = useMemo(() => (c.loaded ? sourcesOf(c) : null), [c]);
  const scroller = useRevealFocus(focus, c.id);
  if (!c.loaded || !sources) return <Unloaded c={c} />;
  const onFocus = (path: string) => go({ id: c.id, focus: path });
  const total = [...sources.values()].reduce((n, list) => n + list.length, 0);

  return (
    <div className="stage-scroll ct-page" ref={scroller}>
      <p className="ct-count-line">
        <span className="num">{c.entries.length}</span> entries from <span className="num">{total}</span> sources
      </p>
      {PROVENANCE_ORDER.map((kind) => {
        const list = sources.get(kind) ?? [];
        const n = list.reduce((sum, s) => sum + s.entries.length, 0);
        return (
          <section key={kind} className="block ct-kind">
            <h2>
              <Prov kind={kind} /> {PROVENANCE[kind].words}
              <span className="count">
                {" "}
                {list.length} {list.length === 1 ? "source" : "sources"} · {n} {n === 1 ? "entry" : "entries"}
              </span>
            </h2>
            {list.length ? (
              <div className="ct-sources">
                {list.map((s) => (
                  <SourceCard key={s.key} s={s} focus={focus} onFocus={onFocus} />
                ))}
              </div>
            ) : (
              <div className="ct-none">{NONE[kind]}</div>
            )}
          </section>
        );
      })}
      <References refs={c.references} />
    </div>
  );
}

function SourceCard({ s, focus, onFocus }: { s: Source; focus: string | null; onFocus: (path: string) => void }) {
  const p = s.provenance;
  const a = s.assumption;
  return (
    <div className="proof ct-proof ct-source" data-source={s.kind}>
      <div className="ct-source-head">
        {s.kind === "assumption" ? (
          <>
            <button
              className="link mono ct-source-id"
              onClick={() => onFocus(assumptionFocus(s.key))}
              title="Open the assumption in the card"
            >
              {s.key}
            </button>
            <span className="ct-source-text">{a ? a.what : "not in the assumptions list"}</span>
            {a?.varied ? <span className="pill ct-varied">varied later</span> : null}
          </>
        ) : s.kind === "derived" ? (
          <span className="ct-source-text">
            <span className="mono">{p?.tool ?? "?"}</span> · version <span className="mono">{p?.tool_version ?? "?"}</span>
          </span>
        ) : s.kind === "engineer" ? (
          <span className="ct-source-text">
            {p?.who ?? "?"} · <span className="mono">{p?.when ?? "?"}</span>
          </span>
        ) : (
          <span className="ct-source-text">{p?.citation ?? <span className="dim">no citation</span>}</span>
        )}
        <span className="count">{s.entries.length}</span>
      </div>
      {s.kind === "derived" && p?.input_hash ? (
        <div className="ct-source-meta">
          input <Hash value={p.input_hash} />
        </div>
      ) : null}
      {a ? (
        <div className="ct-source-meta">
          <span>{a.value}</span>
          <span className="dim"> · why: {a.why}</span>
        </div>
      ) : null}
      {s.entries.length ? (
        <div className="ct-rows ct-source-rows">
          {s.entries.map((e) => (
            <EntryRow
              key={e.path}
              row={{ entry: e, label: e.label }}
              focus={focus}
              onFocus={onFocus}
              prov={false}
              extra={e.provenance.note}
            />
          ))}
        </div>
      ) : (
        <div className="ct-source-meta dim">no entry takes its value from it</div>
      )}
    </div>
  );
}

function References({ refs }: { refs: Reference[] }) {
  return (
    <Block title="References" count={refs.length} aside="published values kept as a plausibility band, never as limits">
      {refs.length ? (
        <div className="tbl-wrap">
          <table className="tbl ct-refs">
            <thead>
              <tr>
                <th>source</th>
                <th>quantity</th>
                <th>value</th>
                <th>conditions</th>
                <th>confidence</th>
              </tr>
            </thead>
            <tbody>
              {refs.map((r, i) => (
                <tr key={i}>
                  <td>{r.source}</td>
                  <td>{r.quantity}</td>
                  <td className="mono">{r.value}</td>
                  <td className="ct-refs-dim">{r.conditions}</td>
                  <td className="ct-refs-dim">{r.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="ct-none">none</div>
      )}
    </Block>
  );
}
