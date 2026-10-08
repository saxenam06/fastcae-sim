/**
 * A datapoint kind, a cut from a campaign and a task type, each as the card shows it in full.
 *
 * Shared by the Data tab's card and the Flow tab's, so that a kind picked on the campaign diagram
 * reads exactly as it does here. Each view ends with its count contract by contract, because a
 * kind is only ever as full as the contracts it comes from; where the count is 0 a blank names
 * what will fill it.
 */

import { Fragment } from "react";
import { shortTitle } from "../app/product";
import type { Go } from "../app/route";
import { Blank, Count, Dot, StageDots } from "../panel/bits";
import { tallyContracts, type ContractTally } from "../flow/tally";
import type { Snapshot } from "../records/types";
import { CUTS, KINDS, MAKING, type Cut, type DatapointKind, type Making } from "./kinds";
import { GRADER_STATUS, graderOf, TASK_NOTE, type TaskType } from "./taskTypes";

export function MakingPill({ making }: { making: Making }) {
  return (
    <span className="pill data-making" data-making={making} title={MAKING[making]}>
      <Dot status={making === "built" ? "pending" : "blank"} /> {making}
    </span>
  );
}

export function KindView({ kind, snap, go }: { kind: DatapointKind; snap: Snapshot; go: Go }) {
  const n = kind.count(snap);
  const cut = CUTS.find((c) => c.kind === kind.letter);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">kind {kind.letter}</span>
          <MakingPill making={kind.making} />
        </div>
        <h2 className="entity-title">
          {kind.letter}. {kind.name} <span className="count">{n}</span>
        </h2>
        <p className="step-detail data-card-what">{kind.what}</p>
        <div className="entity-made">made by {kind.madeBy}</div>
      </header>
      <details className="card-section" open>
        <summary>The kind</summary>
        <dl className="fields-list">
          <dt>count now</dt>
          <dd>
            <Count n={n} />
          </dd>
          <dt>trains</dt>
          <dd>{kind.trains}</dd>
          <dt>learning</dt>
          <dd>{kind.learning}</dd>
          <dt>how</dt>
          <dd>{kind.uses}</dd>
          <dt>made by</dt>
          <dd>{kind.madeBy}</dd>
          <dt>status</dt>
          <dd>{MAKING[kind.making]}</dd>
          {cut ? (
            <>
              <dt>cut as</dt>
              <dd>
                <button className="link" onClick={() => go({ focus: `cut:${cut.id}` })}>
                  {cut.name.toLowerCase()}
                </button>
                , from {cut.from}
              </dd>
            </>
          ) : null}
        </dl>
      </details>
      <ByContract snap={snap} go={go} count={kind.perContract} aside={kind.letter === "A" ? freezeWords : undefined} />
      {n === 0 ? (
        <div className="card-pad">
          <Blank title={kind.none} waits={kind.waits(snap)} />
        </div>
      ) : null}
    </>
  );
}

export function CutView({ cut, snap, go }: { cut: Cut; snap: Snapshot; go: Go }) {
  const n = cut.count(snap);
  const kind = KINDS.find((k) => k.letter === cut.kind);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">cut</span>
          <MakingPill making={cut.making} />
        </div>
        <h2 className="entity-title">
          {cut.name} <span className="count">{n}</span>
        </h2>
        <p className="step-detail data-card-what">{cut.words}</p>
        <div className="entity-made">made by {cut.madeBy}</div>
      </header>
      <details className="card-section" open>
        <summary>The cut</summary>
        <dl className="fields-list">
          <dt>count now</dt>
          <dd>
            <Count n={n} />
          </dd>
          <dt>cut from</dt>
          <dd>{cut.from}</dd>
          <dt>what</dt>
          <dd>{cut.what}</dd>
          <dt>trains</dt>
          <dd>{cut.learning}</dd>
          <dt>made by</dt>
          <dd>{cut.madeBy}</dd>
          {kind ? (
            <>
              <dt>kind</dt>
              <dd>
                <button className="link" onClick={() => go({ focus: `kind:${kind.letter}` })}>
                  {kind.letter}. {kind.name.toLowerCase()}
                </button>
              </dd>
            </>
          ) : null}
        </dl>
      </details>
      <ByContract snap={snap} go={go} count={cut.perContract} />
      {n === 0 ? (
        <div className="card-pad">
          <Blank title={`No ${cut.name.toLowerCase()} yet`} waits={`Waits for ${cut.madeBy}, and a campaign (AGT)`} />
        </div>
      ) : null}
    </>
  );
}

export function TaskView({ task, snap }: { task: TaskType; snap: Snapshot }) {
  const grader = graderOf(task);
  const status = GRADER_STATUS[grader.status];
  const instances = snap.records.snapshot_tasks.filter((s) => s.task_type === task.n).length;
  const rules =
    grader.rules === "all"
      ? snap.rules
      : snap.rules.filter((r) => (grader.rules ?? []).includes(r.id));
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">task type {task.n}</span>
          <GraderPill task={task} />
        </div>
        <h2 className="entity-title">{task.task}</h2>
        <div className="entity-made">graded by {grader.label}</div>
      </header>
      <details className="card-section" open>
        <summary>The task</summary>
        <dl className="fields-list">
          <dt>given</dt>
          <dd>{task.given}</dd>
          <dt>hand in</dt>
          <dd>{task.handIn}</dd>
          <dt>graded by</dt>
          <dd>{task.gradedBy}</dd>
          <dt>grader</dt>
          <dd>
            <Dot status={status.dot} /> {grader.label}: {status.words.toLowerCase()}
          </dd>
          <dt>used for</dt>
          <dd>{task.usedFor}</dd>
          <dt>instances</dt>
          <dd>
            <Count n={instances} />
          </dd>
        </dl>
        <p className="data-card-note">{TASK_NOTE}</p>
      </details>
      {rules.length ? (
        <details className="card-section" open={rules.length <= 4}>
          <summary>
            The rules that grade it <span className="count">{rules.length}</span>
          </summary>
          <dl className="fields-list data-rules">
            {rules.map((r) => (
              <Fragment key={r.id}>
                <dt className="mono">{r.id}</dt>
                <dd>{r.words}</dd>
              </Fragment>
            ))}
          </dl>
        </details>
      ) : null}
      {instances === 0 ? (
        <div className="card-pad">
          <Blank
            title="No instances yet"
            waits={
              grader.status === "exists"
                ? "Gradable now; instances are cut from campaigns (DAT-2)"
                : `Waits for ${grader.label}, and snapshot tasks (DAT-2)`
            }
          />
        </div>
      ) : null}
    </>
  );
}

export function GraderPill({ task }: { task: TaskType }) {
  const grader = graderOf(task);
  const status = GRADER_STATUS[grader.status];
  return (
    <span className="pill data-grader" data-status={grader.status} title={`${grader.label}: ${status.words}`}>
      <Dot status={status.dot} /> {status.label}
    </span>
  );
}

/** A kind's count, contract by contract, each row opening its contract. */
function ByContract({
  snap,
  go,
  count,
  aside,
}: {
  snap: Snapshot;
  go: Go;
  count: (t: ContractTally) => number;
  aside?: (t: ContractTally) => string;
}) {
  const rows = tallyContracts(snap);
  return (
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
          <b className="num">{count(row)}</b>
          <span>{shortTitle(row.contract.title)}</span>
          <span className="dim">{aside ? aside(row) : <StageDots stage={row.contract.stage} />}</span>
        </button>
      ))}
    </details>
  );
}

function freezeWords(t: ContractTally): string {
  const c = t.contract;
  if (c.stage === "frozen") return "frozen";
  return c.freeze.ready ? "ready to freeze" : `${c.stage}, not ready`;
}
