/**
 * The contract's own card, shown when nothing in it is in focus: what it is, what its values rest
 * on, what the validator says, and what has been made from it.
 *
 * "What its values rest on" is one thin bar - a segment a provenance kind, its width its share - so
 * how much of a contract is published, and how much is still assumed, reads at a glance. Downstream
 * is drawn whether or not anything is there: today nothing is, and the card says so and names what
 * will fill it, rather than leaving the section out.
 */

import { Fragment, useMemo } from "react";
import { LAYERS, PROVENANCE, STAGES } from "../app/product";
import { Count, Dot, Hash, ProvDot, StageDots } from "../panel/bits";
import type { ContractView, ProvenanceKind, Snapshot } from "../records/types";
import { provenanceMix } from "./model";
import { VerdictChip } from "./parts";

export function ContractCard({ snap, c, missing }: { snap: Snapshot; c: ContractView; missing: string | null }) {
  const mix = useMemo(() => (c.loaded ? provenanceMix(c.entries) : []), [c]);
  const layers = useMemo(
    () => LAYERS.map((l) => ({ l, n: c.loaded ? c.entries.filter((e) => e.layer === l.id).length : 0 })),
    [c],
  );
  const campaigns = snap.records.campaigns.filter((x) => x.contract === c.id);
  const made = new Set(campaigns.map((x) => x.id));
  const designs = snap.records.candidates.filter((d) => made.has(d.campaign));
  const stage = c.loaded ? STAGES.find((s) => s.id === c.stage) : undefined;
  return (
    <>
      {missing ? (
        <p className="ct-card-missing">
          <span className="mono">{missing}</span> is not in this contract
        </p>
      ) : null}
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">contract</span>
          {stage ? (
            <span className="ct-card-stage" title={stage.words}>
              <StageDots stage={stage.id} /> {stage.label}
            </span>
          ) : null}
          <VerdictChip c={c} />
        </div>
        <h2 className="entity-title">{c.loaded ? c.title : c.id}</h2>
        <div className="entity-id mono ct-wrap">{c.id}</div>
        <div className="entity-made mono ct-wrap">{c.file}</div>
      </header>
      {c.loaded ? (
        <>
          <dl className="fields-list ct-card-fields">
            <dt>hash</dt>
            <dd>
              <Hash value={c.hash} />
            </dd>
            <dt>frozen hash</dt>
            <dd>{c.frozen_hash ? <Hash value={c.frozen_hash} /> : <span className="dim">not frozen</span>}</dd>
            <dt>family</dt>
            <dd>{c.family}</dd>
            <dt>level</dt>
            <dd>{c.level}</dd>
          </dl>
          <details className="card-section" open>
            <summary>
              What its values rest on <span className="count">{c.entries.length}</span>
            </summary>
            <Mix mix={mix} />
          </details>
          <details className="card-section" open>
            <summary>By layer</summary>
            <dl className="fields-list">
              {layers.map(({ l, n }) => (
                <Fragment key={l.id}>
                  <dt title={l.words}>{l.label}</dt>
                  <dd>
                    <Count n={n} />
                  </dd>
                </Fragment>
              ))}
            </dl>
          </details>
          <details className="card-section" open>
            <summary>The validator</summary>
            <dl className="fields-list">
              <dt>as it is</dt>
              <dd>{c.refusals.length ? `${c.refusals.length} refused` : "accepted"}</dd>
              <dt>frozen now</dt>
              <dd>
                {c.stage === "frozen"
                  ? "frozen"
                  : c.freeze.ready
                    ? "ready"
                    : `${c.freeze.refusals.length} refused: ${[...new Set(c.freeze.refusals.map((r) => r.entry || r.rule))].join(", ")}`}
              </dd>
            </dl>
          </details>
        </>
      ) : (
        <details className="card-section" open>
          <summary>
            Refusals <span className="count">{c.refusals.length}</span>
          </summary>
          <div className="proofs">
            {c.refusals.map((r, i) => (
              <div key={i} className="proof ct-proof" data-source="refusal">
                <span className="proof-source mono">{r.rule}</span>
                <span>{r.reason}</span>
                {r.entry ? <span className="dim mono">{r.entry}</span> : null}
              </div>
            ))}
          </div>
        </details>
      )}
      <details className="card-section" open>
        <summary>Downstream</summary>
        <dl className="fields-list">
          <dt>campaigns</dt>
          <dd>
            <Count n={campaigns.length} />
          </dd>
          <dt>designs</dt>
          <dd>
            <Count n={designs.length} />
          </dd>
        </dl>
        {campaigns.length ? (
          <div className="ct-card-list">
            {campaigns.map((x) => (
              <div key={x.id}>
                <span className="mono">{x.id}</span>{" "}
                <span className="dim">
                  {x.arm} · {x.spent_fe_proofs} of {x.budget_fe_proofs} FE proofs
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="ct-card-line">
            <Dot status="blank" /> none yet: the agent (AGT-1) is not built
          </p>
        )}
      </details>
    </>
  );
}

/** The provenance mix as one thin bar - a segment a kind, its share its width - and its key. */
function Mix({ mix }: { mix: { kind: ProvenanceKind; n: number }[] }) {
  const total = mix.reduce((n, m) => n + m.n, 0);
  return (
    <div className="card-pad">
      {total ? (
        <div className="ct-mix">
          {mix
            .filter((m) => m.n > 0)
            .map((m) => (
              <i
                key={m.kind}
                data-prov={m.kind}
                style={{ flexGrow: m.n }}
                title={`${m.n} ${PROVENANCE[m.kind].label}, ${Math.round((100 * m.n) / total)} %`}
              />
            ))}
        </div>
      ) : (
        <span className="dim">no entries</span>
      )}
      <div className="ct-mix-key">
        {mix.map((m) => (
          <span key={m.kind} data-zero={m.n === 0}>
            <ProvDot kind={m.kind} /> {PROVENANCE[m.kind].label} <span className="num">{m.n}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
