/**
 * Sheet: every entry of the contract as one table, by layer and then by group.
 *
 * The filters come first because the question this page answers is usually "show me the
 * assumptions" or "what is in the limits": a chip a provenance kind, each hiding or showing its
 * entries (the legend rule: every chip toggles its category), and the layers as one segmented
 * control. The columns are the four things every entry has - value, provenance, authority, kind -
 * with the value both as written and in the canonical units the tools compute in.
 */

import { Fragment, useMemo, useState } from "react";
import { AUTHORITY, KIND, LAYERS, PROVENANCE } from "../app/product";
import { Prov, ProvDot } from "../panel/bits";
import type { EntryView, Layer, ProvenanceKind } from "../records/types";
import { DERIVES_THEM, assumptionIn, provenanceMix } from "./model";
import { Unloaded, clickable, useRevealFocus, type PageProps } from "./parts";

/** A layer the table shows, with its entries by group. */
interface Section {
  layer: (typeof LAYERS)[number];
  total: number;
  groups: { name: string; entries: EntryView[] }[];
}

export function Sheet({ c, focus, go }: PageProps) {
  const [hidden, setHidden] = useState<ReadonlySet<ProvenanceKind>>(() => new Set());
  const [layer, setLayer] = useState<Layer | "all">("all");

  const all = useMemo(() => (c.loaded ? c.entries : []), [c]);
  const inLayer = useMemo(() => all.filter((e) => layer === "all" || e.layer === layer), [all, layer]);
  const mix = useMemo(() => provenanceMix(inLayer), [inLayer]);
  const shown = useMemo(() => inLayer.filter((e) => !hidden.has(e.provenance.kind)), [inLayer, hidden]);
  const sections = useMemo<Section[]>(
    () =>
      LAYERS.filter((l) => layer === "all" || l.id === layer).map((l) => {
        const groups = new Map<string, EntryView[]>();
        for (const e of shown) {
          if (e.layer !== l.id) continue;
          const list = groups.get(e.group);
          if (list) list.push(e);
          else groups.set(e.group, [e]);
        }
        return {
          layer: l,
          total: all.filter((e) => e.layer === l.id).length,
          groups: [...groups].map(([name, entries]) => ({ name, entries })),
        };
      }),
    [all, shown, layer],
  );

  const scroller = useRevealFocus(focus, c.id);

  if (!c.loaded) return <Unloaded c={c} />;

  const filtered = hidden.size > 0;
  const toggle = (kind: ProvenanceKind) =>
    setHidden((was) => {
      const next = new Set(was);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  const onFocus = (path: string) => go({ id: c.id, focus: path });
  const shownMix = provenanceMix(shown).filter((m) => m.n > 0);
  const assumption = assumptionIn(focus);

  return (
    <div className="stage-scroll ct-page" ref={scroller}>
      <div className="ct-filters">
        <div className="pills">
          {mix.map(({ kind, n }) => {
            const on = !hidden.has(kind);
            return (
              <button
                key={kind}
                className="pill ct-chip"
                data-active={on}
                data-zero={n === 0}
                disabled={n === 0}
                onClick={() => toggle(kind)}
                title={`${PROVENANCE[kind].words}. Click to ${on ? "hide" : "show"} them.`}
              >
                <ProvDot kind={kind} /> {PROVENANCE[kind].label} <span className="num">{n}</span>
              </button>
            );
          })}
          {filtered ? (
            <button className="link ct-show-all" onClick={() => setHidden(new Set())}>
              show all
            </button>
          ) : null}
        </div>
        <div className="segmented">
          <button data-active={layer === "all"} onClick={() => setLayer("all")}>
            all <span className="num dim">{all.length}</span>
          </button>
          {LAYERS.map((l) => (
            <button key={l.id} data-active={layer === l.id} onClick={() => setLayer(l.id)} title={l.words}>
              {l.label} <span className="num dim">{all.filter((e) => e.layer === l.id).length}</span>
            </button>
          ))}
        </div>
      </div>

      <p className="ct-count-line">
        <span className="num">{shown.length}</span> {shown.length === 1 ? "entry" : "entries"}
        {shown.length !== all.length ? (
          <>
            {" "}
            of <span className="num">{all.length}</span>
          </>
        ) : null}
        {shownMix.map((m) => (
          <span key={m.kind}>
            {" · "}
            <span className="num">{m.n}</span> {PROVENANCE[m.kind].label}
          </span>
        ))}
      </p>

      <div className="tbl-wrap">
        <table className="tbl ct-sheet">
          <thead>
            <tr>
              <th>what</th>
              <th>value</th>
              <th>canonical</th>
              <th>provenance</th>
              <th>authority</th>
              <th>kind</th>
            </tr>
          </thead>
          {sections.map(({ layer: l, total, groups }) => {
            // A layer with nothing in it is drawn while nothing is filtered out, so the posed
            // contract's empty interfaces and physics read as places still to fill.
            if (!groups.length && (total > 0 || filtered)) return null;
            return (
              <tbody key={l.id}>
                <tr className="ct-layer-row">
                  <th colSpan={6} title={l.words}>
                    {l.label} <span className="count">{groups.reduce((n, g) => n + g.entries.length, 0)}</span>
                    <span className="ct-layer-words">{l.words}</span>
                  </th>
                </tr>
                {groups.length === 0 ? (
                  <tr className="template">
                    <td colSpan={6}>
                      {l.id === "interfaces" || l.id === "physics" ? `none yet: ${DERIVES_THEM}` : "none"}
                    </td>
                  </tr>
                ) : (
                  groups.map((g) => (
                    <Fragment key={g.name}>
                      <tr className="ct-group-row">
                        <td colSpan={6}>
                          {g.name} <span className="count">{g.entries.length}</span>
                        </td>
                      </tr>
                      {g.entries.map((e) => (
                        <tr
                          key={e.path}
                          {...clickable(() => onFocus(e.path))}
                          data-focus={focus === e.path}
                          data-related={assumption !== null && e.provenance.assumption_id === assumption}
                          title={e.path}
                        >
                          <td className="ct-sheet-what">{e.label}</td>
                          <td className="mono">{e.value}</td>
                          <td className="mono dim">{e.canonical ?? ""}</td>
                          <td>
                            <Prov kind={e.provenance.kind} />
                          </td>
                          <td title={AUTHORITY[e.authority].words}>
                            {AUTHORITY[e.authority].label}
                            {e.bounds ? (
                              <div className="mono dim">
                                {e.bounds[0]} to {e.bounds[1]}
                              </div>
                            ) : null}
                          </td>
                          <td title={KIND[e.kind].words}>{KIND[e.kind].label}</td>
                        </tr>
                      ))}
                    </Fragment>
                  ))
                )}
              </tbody>
            );
          })}
          {shown.length === 0 && filtered ? (
            <tbody>
              <tr className="template">
                <td colSpan={6}>nothing shown: the chips above hide every entry here</td>
              </tr>
            </tbody>
          ) : null}
        </table>
      </div>
    </div>
  );
}
