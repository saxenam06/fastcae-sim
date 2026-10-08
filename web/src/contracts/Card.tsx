/**
 * The card: whatever is in focus, in full - an entry, an assumption, or the contract itself.
 *
 * An entry's card answers, in order, the questions an engineer asks of a value: what is it, what is
 * it in the units the tools compute in, where did it come from, who may change it, how does it bind,
 * and does any rule refuse it. Each answer is a section, folded open, so a long one can be put away.
 * An assumption's card lists every entry that takes its value from it. With nothing in focus the
 * card is the contract's own (./ContractCard.tsx).
 */

import { useMemo } from "react";
import { AUTHORITY, KIND, PROVENANCE } from "../app/product";
import type { CardProps } from "../app/tab";
import { CardFrame, Dot, Hash, Prov } from "../panel/bits";
import { Metric } from "../panel/cards";
import type { Assumption, ContractView, EntryView } from "../records/types";
import { ContractCard } from "./ContractCard";
import { assumptionFocus, contractIn, focusIn, itemOf, layerSpec, refusalsOn } from "./model";
import { EntryRow } from "./parts";

type OnFocus = (focus: string | null) => void;

export function Card({ snap, route, go, onCollapse }: CardProps) {
  const c = contractIn(snap, route.id);
  if (!c) {
    return (
      <CardFrame kind="the contract" onCollapse={onCollapse}>
        <div className="card-pad dim">No contract in the snapshot.</div>
      </CardFrame>
    );
  }
  const focus = focusIn(c, route.focus);
  const onFocus: OnFocus = (next) => go({ id: c.id, focus: next });
  if (focus.kind === "entry") {
    return (
      <CardFrame kind="the entry" onCollapse={onCollapse}>
        <EntryCard key={focus.entry.path} c={c} e={focus.entry} onFocus={onFocus} />
      </CardFrame>
    );
  }
  if (focus.kind === "assumption") {
    return (
      <CardFrame kind="the assumption" onCollapse={onCollapse}>
        <AssumptionCard c={c} id={focus.id} a={focus.assumption} onFocus={onFocus} />
      </CardFrame>
    );
  }
  return (
    <CardFrame kind="the contract" onCollapse={onCollapse}>
      <ContractCard snap={snap} c={c} missing={focus.missing} />
    </CardFrame>
  );
}

// --- an entry ---------------------------------------------------------------------------------

function EntryCard({ c, e, onFocus }: { c: ContractView; e: EntryView; onFocus: OnFocus }) {
  const layer = layerSpec(e.layer);
  const item = useMemo(() => itemOf(e.path, c.items), [e, c.items]);
  const beside = useMemo(
    () => (item ? c.entries.filter((x) => x.path !== e.path && itemOf(x.path, c.items)?.path === item.path) : []),
    [c, e, item],
  );
  const refusals = refusalsOn(e.path, c.refusals);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip" title={layer.words}>
            {layer.label}
          </span>
          <Prov kind={e.provenance.kind} />
        </div>
        <h2 className="entity-title">{e.label}</h2>
        <div className="entity-id mono ct-wrap">{e.path}</div>
        <div className="entity-made">
          {e.group}
          {item?.detail ? (
            <span className="dim">
              {" "}
              · {item.name} · {item.detail}
            </span>
          ) : null}
        </div>
      </header>
      <div className="card-pad">
        <div className="metrics">
          <Metric label="as written" value={e.value} />
          {e.canonical !== null ? <Metric label="canonical" value={e.canonical} /> : null}
        </div>
      </div>
      <details className="card-section" open>
        <summary>Where it came from</summary>
        <div className="proofs">
          <Origin c={c} e={e} onFocus={onFocus} />
        </div>
      </details>
      <details className="card-section" open>
        <summary>Who may change it</summary>
        <dl className="fields-list">
          <dt>{AUTHORITY[e.authority].label}</dt>
          <dd>{AUTHORITY[e.authority].words}</dd>
          {e.bounds ? (
            <>
              <dt>bounds</dt>
              <dd className="mono">
                {e.bounds[0]} to {e.bounds[1]}
              </dd>
            </>
          ) : null}
        </dl>
      </details>
      <details className="card-section" open>
        <summary>How it binds</summary>
        <dl className="fields-list">
          <dt>{KIND[e.kind].label}</dt>
          <dd>{KIND[e.kind].words}</dd>
        </dl>
      </details>
      <details className="card-section" open>
        <summary>
          Refused by <span className="count">{refusals.length}</span>
        </summary>
        {refusals.length ? (
          <div className="proofs">
            {refusals.map((r, i) => (
              <div key={i} className="proof ct-proof" data-source="refusal">
                <span className="proof-source mono">{r.rule}</span>
                <span>{r.reason}</span>
                {r.entry !== e.path ? <span className="dim mono">on {r.entry}</span> : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="ct-card-line">
            <Dot status="done" /> no rule refuses it
          </p>
        )}
      </details>
      {item && beside.length ? (
        <details className="card-section" open>
          <summary>
            Beside it, in {item.kind} {item.name} <span className="count">{beside.length}</span>
          </summary>
          <div className="tie-group">
            <div className="ties">
              {beside.map((x) => (
                <button key={x.path} className="tie" onClick={() => onFocus(x.path)} title={`${x.label}\n${x.path}`}>
                  <span className="tie-kind">{x.label.split(" · ")[0]}</span>
                  <span className="mono">{x.value}</span>
                </button>
              ))}
            </div>
          </div>
        </details>
      ) : null}
    </>
  );
}

/** Where an entry's value came from, as fastcae's evidence: a rule in its provenance's line. */
function Origin({ c, e, onFocus }: { c: ContractView; e: EntryView; onFocus: OnFocus }) {
  const p = e.provenance;
  const note = p.note ? <span className="ct-proof-note">{p.note}</span> : null;
  const head = <span className="proof-source">{PROVENANCE[p.kind].label}</span>;
  if (p.kind === "derived") {
    return (
      <div className="proof ct-proof" data-source="derived">
        {head}
        <span>
          tool <span className="mono">{p.tool ?? "?"}</span> · version <span className="mono">{p.tool_version ?? "?"}</span>
        </span>
        <span>
          input <Hash value={p.input_hash ?? null} />
        </span>
        {note}
      </div>
    );
  }
  if (p.kind === "assumption") {
    const id = p.assumption_id ?? "";
    const a: Assumption | undefined = c.assumptions.find((x) => x.id === id);
    return (
      <div className="proof ct-proof" data-source="assumption">
        {head}
        <span>
          <button className="link mono" onClick={() => onFocus(assumptionFocus(id))} title="Open the assumption">
            {id || "?"}
          </button>{" "}
          {a ? a.what : <span className="dim">not in the assumptions list</span>}
        </span>
        {a ? (
          <dl className="ct-proof-fields">
            <dt>taken as</dt>
            <dd>{a.value}</dd>
            <dt>why</dt>
            <dd>{a.why}</dd>
          </dl>
        ) : null}
        {a?.varied ? <span className="pill ct-varied">varied later</span> : null}
        {note}
      </div>
    );
  }
  if (p.kind === "engineer") {
    return (
      <div className="proof ct-proof" data-source="engineer">
        {head}
        <span>
          {p.who ?? "?"} · <span className="mono">{p.when ?? "?"}</span>
        </span>
        {note}
      </div>
    );
  }
  return (
    <div className="proof ct-proof" data-source={p.kind}>
      {head}
      <span>{p.citation ?? <span className="dim">no citation</span>}</span>
      {note}
    </div>
  );
}

// --- an assumption ----------------------------------------------------------------------------

function AssumptionCard({
  c,
  id,
  a,
  onFocus,
}: {
  c: ContractView;
  id: string;
  a: Assumption | null;
  onFocus: OnFocus;
}) {
  const entries = useMemo(() => c.entries.filter((e) => e.provenance.assumption_id === id), [c, id]);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">assumption</span>
          {a?.varied ? (
            <span className="pill ct-varied" title="The dataset may vary it to make variants">
              varied later
            </span>
          ) : null}
        </div>
        <h2 className="entity-title">{a ? a.what : `${id} is not in this contract`}</h2>
        <div className="entity-id mono ct-wrap">{id}</div>
      </header>
      {a ? (
        <dl className="fields-list ct-card-fields">
          <dt>taken as</dt>
          <dd>{a.value}</dd>
          <dt>why</dt>
          <dd>{a.why}</dd>
          <dt>varied later</dt>
          <dd>{a.varied ? "yes: the dataset may vary it to make variants" : "no"}</dd>
        </dl>
      ) : null}
      <details className="card-section" open>
        <summary>
          Entries it sets <span className="count">{entries.length}</span>
        </summary>
        {entries.length ? (
          <div className="ct-rows ct-card-rows">
            {entries.map((e) => (
              <EntryRow key={e.path} row={{ entry: e, label: e.label }} focus={null} onFocus={onFocus} prov={false} />
            ))}
          </div>
        ) : (
          <p className="ct-card-line dim">no entry takes its value from it</p>
        )}
      </details>
    </>
  );
}
