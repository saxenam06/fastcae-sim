/**
 * The Data tab's card: the kind, the cut or the task type in focus, in full; with nothing in focus,
 * the record's totals - what exists, what is cut, what can be graded - so the card says how far
 * the record is from being training data before anything is picked.
 */

import { Fragment } from "react";
import type { Go } from "../app/route";
import type { CardProps } from "../app/tab";
import { CardFrame, Count, Dot } from "../panel/bits";
import type { Snapshot } from "../records/types";
import { CUTS, cutOf, datapoints, KINDS, kindOf } from "./kinds";
import { GRADER_STATUS, graderOf, TASK_TYPES, taskOf, type GraderStatus } from "./taskTypes";
import { CutView, KindView, TaskView } from "./views";

export function DataCard({ snap, route, go, onCollapse }: CardProps) {
  const kind = kindOf(route.focus);
  const cut = cutOf(route.focus);
  const task = taskOf(route.focus);
  const label = kind ? "datapoint kind" : cut ? "cut from a campaign" : task ? "task type" : "the record";
  return (
    <CardFrame kind={label} onCollapse={onCollapse}>
      {kind ? (
        <KindView kind={kind} snap={snap} go={go} />
      ) : cut ? (
        <CutView cut={cut} snap={snap} go={go} />
      ) : task ? (
        <TaskView task={task} snap={snap} />
      ) : (
        <RecordView snap={snap} go={go} />
      )}
    </CardFrame>
  );
}

function RecordView({ snap, go }: { snap: Snapshot; go: Go }) {
  const frozen = snap.contracts.filter((c) => c.stage === "frozen").length;
  const families = new Set(snap.contracts.map((c) => c.family)).size;
  const scenarios = snap.contracts.reduce((n, c) => n + c.scenarios.length, 0);
  const byStatus = (s: GraderStatus) => TASK_TYPES.filter((t) => graderOf(t).status === s).length;
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">the record</span>
        </div>
        <h2 className="entity-title">
          Datapoints <span className="count">{datapoints(snap)}</span>
        </h2>
        <div className="entity-made">pick a kind, a cut or a task type to see it here</div>
      </header>

      <details className="card-section" open>
        <summary>
          The kinds <span className="count">{KINDS.length}</span>
        </summary>
        <dl className="fields-list">
          {KINDS.map((k) => (
            <Fragment key={k.letter}>
              <dt>
                <button className="link" onClick={() => go({ page: "datapoints", focus: `kind:${k.letter}` })}>
                  {k.letter}. {k.name.toLowerCase()}
                </button>
              </dt>
              <dd>
                <Count n={k.count(snap)} /> <span className="dim">{k.making}</span>
              </dd>
            </Fragment>
          ))}
        </dl>
      </details>

      <details className="card-section" open>
        <summary>
          Cut from campaigns <span className="count">{CUTS.length}</span>
        </summary>
        <dl className="fields-list">
          {CUTS.map((c) => (
            <Fragment key={c.id}>
              <dt>
                <button className="link" onClick={() => go({ page: "datapoints", focus: `cut:${c.id}` })}>
                  {c.name.toLowerCase()}
                </button>
              </dt>
              <dd>
                <Count n={c.count(snap)} /> <span className="dim">{c.making}</span>
              </dd>
            </Fragment>
          ))}
        </dl>
      </details>

      <details className="card-section" open>
        <summary>
          Task types <span className="count">{TASK_TYPES.length}</span>
        </summary>
        <dl className="fields-list">
          {(["exists", "formula", "not built"] as const).map((s) => (
            <Fragment key={s}>
              <dt>
                <Dot status={GRADER_STATUS[s].dot} /> grader {GRADER_STATUS[s].label}
              </dt>
              <dd>
                <Count n={byStatus(s)} />
              </dd>
            </Fragment>
          ))}
          <dt>instances</dt>
          <dd>
            <Count n={snap.records.snapshot_tasks.length} />
          </dd>
        </dl>
      </details>

      <details className="card-section" open>
        <summary>The contracts</summary>
        <dl className="fields-list">
          <dt>contracts</dt>
          <dd>
            <Count n={snap.contracts.length} />
          </dd>
          <dt>frozen</dt>
          <dd>
            <Count n={frozen} /> <span className="dim">a contract becomes a task once frozen</span>
          </dd>
          <dt>families</dt>
          <dd>
            <Count n={families} />
          </dd>
          <dt>scenarios</dt>
          <dd>
            <Count n={scenarios} /> <span className="dim">implied, across the contracts</span>
          </dd>
        </dl>
      </details>
    </>
  );
}
