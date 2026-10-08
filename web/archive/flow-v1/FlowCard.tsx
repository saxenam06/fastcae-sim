/**
 * The card on the right: the step in focus, in full - what it is, what makes it and whether that
 * is built, the stages either side of it, and its count contract by contract. A datapoint kind or
 * a cut picked on the campaign diagram shows here as it does on the Data tab, from the same list.
 * With nothing in focus, the factory's totals, a group a section, so the card is never empty.
 */

import { Fragment } from "react";
import { shortTitle } from "../app/product";
import type { Go } from "../app/route";
import type { CardProps } from "../app/tab";
import { CardFrame, Count, Dot, Hash, StageDots } from "../panel/bits";
import { cutOf, kindOf } from "../data/kinds";
import { CutView, KindView } from "../data/views";
import type { Snapshot } from "../records/types";
import {
  GROUPS,
  maker,
  neighbours,
  noun,
  STAGES,
  stageDot,
  stageOf,
  stagesIn,
  stageStatus,
  STATUS_WORDS,
  type FactoryStage,
} from "./stages";
import { citationsOf, tallyContracts, type ContractTally } from "./tally";

export function FlowCard({ snap, route, go, onCollapse }: CardProps) {
  const stage = stageOf(route.focus);
  const kind = kindOf(route.focus);
  const cut = cutOf(route.focus);
  const label = stage ? "step" : kind ? "datapoint kind" : cut ? "cut from a campaign" : "the factory";
  return (
    <CardFrame kind={label} onCollapse={onCollapse}>
      {stage ? (
        <StageView stage={stage} snap={snap} go={go} />
      ) : kind ? (
        <KindView kind={kind} snap={snap} go={go} />
      ) : cut ? (
        <CutView cut={cut} snap={snap} go={go} />
      ) : (
        <FactoryView snap={snap} go={go} />
      )}
    </CardFrame>
  );
}

function StageView({ stage, snap, go }: { stage: FactoryStage; snap: Snapshot; go: Go }) {
  const n = stage.count(snap);
  const status = stageStatus(stage, n);
  const { prev, next } = neighbours(stage);
  const group = GROUPS.find((g) => g.id === stage.group);
  const rows = tallyContracts(snap);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">{group ? group.label : "step"}</span>
          <span className="pill flow-built" data-built={stage.built} title={STATUS_WORDS[status]}>
            <Dot status={stageDot(status)} /> {stage.built ? "built" : "not built"}
          </span>
        </div>
        <h2 className="entity-title">
          {stage.label} <span className="count">{n}</span>
        </h2>
        <p className="step-detail flow-card-what">{stage.what}</p>
        <div className="entity-made">made by {maker(stage, snap)}</div>
      </header>
      <details className="card-section" open>
        <summary>The step</summary>
        <dl className="fields-list">
          <dt>count</dt>
          <dd>
            <Count n={n} /> {noun(stage, n)}
          </dd>
          <dt>made by</dt>
          <dd>{maker(stage, snap)}</dd>
          <dt>built</dt>
          <dd>{stage.built ? "yes" : "not yet"}</dd>
          {stage.detail ? (
            <>
              <dt>note</dt>
              <dd>{stage.detail}</dd>
            </>
          ) : null}
          <dt>in</dt>
          <dd>{prev ? <StageLink stage={prev} snap={snap} go={go} /> : <span className="dim">- the first stage</span>}</dd>
          <dt>out</dt>
          <dd>{next ? <StageLink stage={next} snap={snap} go={go} /> : <span className="dim">- the last stage</span>}</dd>
        </dl>
      </details>
      <details className="card-section" open>
        <summary>
          By contract <span className="count">{rows.length}</span>
        </summary>
        {rows.map((row) => (
          <button
            key={row.contract.id}
            className="io-row"
            onClick={() => go({ view: "contracts", id: row.contract.id })}
            title={`Open ${row.contract.id}`}
          >
            <b className="num">{stage.perContract(row)}</b>
            <span>{shortTitle(row.contract.title)}</span>
            <span className="dim">
              <Aside stage={stage} row={row} />
            </span>
          </button>
        ))}
        {stage.id === "requirement" ? (
          <p className="flow-card-note">A source two contracts cite counts once in the total.</p>
        ) : null}
      </details>
      {stage.id === "requirement" ? <Sources snap={snap} /> : null}
      {stage.id === "posed" ? <Rules snap={snap} /> : null}
    </>
  );
}

function StageLink({ stage, snap, go }: { stage: FactoryStage; snap: Snapshot; go: Go }) {
  const n = stage.count(snap);
  return (
    <>
      <button className="link" onClick={() => go({ focus: stage.id })}>
        {stage.label}
      </button>{" "}
      <span className="dim">
        <span className="num">{n}</span> {noun(stage, n)}
      </span>
    </>
  );
}

/** What the by-contract row says beside its count: the freeze's readiness where that is the stage. */
function Aside({ stage, row }: { stage: FactoryStage; row: ContractTally }) {
  const c = row.contract;
  if (stage.id === "frozen") {
    if (c.frozen_hash) return <Hash value={c.frozen_hash} />;
    return <>{c.freeze.ready ? "ready" : "not ready"}</>;
  }
  return <StageDots stage={c.stage} />;
}

/** Every source the contracts cite, and how many contracts cite it. */
function Sources({ snap }: { snap: Snapshot }) {
  const cited = new Map<string, number>();
  for (const c of snap.contracts) {
    for (const cite of citationsOf(c.entries)) cited.set(cite, (cited.get(cite) ?? 0) + 1);
  }
  const rows = [...cited.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return (
    <details className="card-section">
      <summary>
        The sources <span className="count">{rows.length}</span>
      </summary>
      <div className="flow-sources">
        {rows.map(([cite, n]) => (
          <div key={cite} className="flow-source" title={cite}>
            <span className="num">{n}</span>
            <span>{cite}</span>
          </div>
        ))}
      </div>
    </details>
  );
}

function Rules({ snap }: { snap: Snapshot }) {
  return (
    <details className="card-section">
      <summary>
        The validator's rules <span className="count">{snap.rules.length}</span>
      </summary>
      <dl className="fields-list flow-rules">
        {snap.rules.map((r) => (
          <Fragment key={r.id}>
            <dt className="mono">{r.id}</dt>
            <dd>{r.words}</dd>
          </Fragment>
        ))}
      </dl>
    </details>
  );
}

/** Nothing in focus: the factory's totals, a group a section. */
function FactoryView({ snap, go }: { snap: Snapshot; go: Go }) {
  const built = STAGES.filter((s) => s.built).length;
  const ready = snap.contracts.filter((c) => c.stage !== "frozen" && c.freeze.ready).length;
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">the factory</span>
        </div>
        <h2 className="entity-title">Requirement to datapoint</h2>
        <div className="entity-made">
          {built} of {STAGES.length} stages built; pick a step to see it here
        </div>
      </header>
      {GROUPS.map((g) => {
        const stages = stagesIn(g.id);
        return (
          <details key={g.id} className="card-section" open>
            <summary>
              {g.label}{" "}
              <span className="count">
                {stages.filter((s) => s.built).length}/{stages.length}
              </span>
            </summary>
            <dl className="fields-list">
              {stages.map((s) => {
                const n = s.count(snap);
                return (
                  <Fragment key={s.id}>
                    <dt>
                      <Dot status={stageDot(stageStatus(s, n))} title={STATUS_WORDS[stageStatus(s, n)]} />{" "}
                      <button className="link" onClick={() => go({ focus: s.id })}>
                        {s.label}
                      </button>
                    </dt>
                    <dd>
                      <Count n={n} /> <span className="dim">{noun(s, n)}</span>
                    </dd>
                  </Fragment>
                );
              })}
              {g.id === "task" ? (
                <>
                  <dt>ready to freeze</dt>
                  <dd>
                    <Count n={ready} /> <span className="dim">{ready === 1 ? "contract" : "contracts"}</span>
                  </dd>
                </>
              ) : null}
            </dl>
          </details>
        );
      })}
    </>
  );
}
