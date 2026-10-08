/**
 * The Data tab's rail: what the record becomes, in three lists - the datapoint kinds A-E, the three
 * cuts made from a campaign, and the twenty task types.
 *
 * Every row is the thing itself, and a click opens the page it lives on with it in the card, so the
 * rail doubles as the tab's index. The counts are the record's: 0 today. The task types carry
 * their grader's dot instead of a count, because what a task type lacks now is a grader, not
 * instances.
 */

import type { TabProps } from "../app/tab";
import { Count, Dot } from "../panel/bits";
import { CUTS, datapoints, KINDS } from "./kinds";
import { GRADER_STATUS, gradableNow, graderOf, TASK_TYPES } from "./taskTypes";

export function DataRail({ snap, route, go }: TabProps) {
  const focus = route.focus;
  const cut = CUTS.reduce((n, c) => n + c.count(snap), 0);
  return (
    <nav className="pipeline data-rail">
      <header className="pipeline-head">
        <span>The record</span>
      </header>

      <section className="rail-group">
        <header>
          <span>Datapoints</span>
          <span className="count">{datapoints(snap)}</span>
        </header>
        {KINDS.map((k) => (
          <button
            key={k.letter}
            className="entity-row data-rail-row"
            data-focus={focus === `kind:${k.letter}`}
            onClick={() => go({ page: "datapoints", focus: `kind:${k.letter}` })}
            title={`${k.letter}. ${k.name}: ${k.what}`}
          >
            <span className="data-key">{k.letter}</span>
            <span className="entity-label">{k.name}</span>
            <Count n={k.count(snap)} />
          </button>
        ))}
      </section>

      <section className="rail-group">
        <header>
          <span>Cut from campaigns</span>
          <span className="count">{cut}</span>
        </header>
        {CUTS.map((c) => (
          <button
            key={c.id}
            className="entity-row data-rail-row"
            data-focus={focus === `cut:${c.id}`}
            onClick={() => go({ page: "datapoints", focus: `cut:${c.id}` })}
            title={`${c.name}: ${c.from}, ${c.what}`}
          >
            <span className="data-key data-key-cut" title={c.kind ? `kind ${c.kind}` : "cut from a campaign"}>
              {c.kind ?? "↳"}
            </span>
            <span className="entity-label">{c.name}</span>
            <Count n={c.count(snap)} />
          </button>
        ))}
      </section>

      <section className="rail-group">
        <header>
          <span>Task types</span>
          <span className="count">
            {TASK_TYPES.length} · {gradableNow().length} gradable now
          </span>
        </header>
        {TASK_TYPES.map((t) => {
          const grader = graderOf(t);
          const status = GRADER_STATUS[grader.status];
          return (
            <button
              key={t.n}
              className="entity-row data-rail-row"
              data-focus={focus === `task:${t.n}`}
              onClick={() => go({ page: "tasks", focus: `task:${t.n}` })}
              title={`${t.n}. ${t.task} - graded by ${grader.label} (${status.label})`}
            >
              <span className="data-key data-key-n">{t.n}</span>
              <span className="entity-label">{t.task}</span>
              <Dot status={status.dot} />
            </button>
          );
        })}
      </section>

      <div className="data-legend">
        {(["exists", "formula", "not built"] as const).map((s) => (
          <span key={s} title={GRADER_STATUS[s].words}>
            <Dot status={GRADER_STATUS[s].dot} /> {GRADER_STATUS[s].label}
          </span>
        ))}
      </div>
    </nav>
  );
}
