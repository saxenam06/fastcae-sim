/**
 * Data: what the record becomes.
 *
 * Everything the factory does is kept as datapoints of five kinds: the contract itself (A), each
 * graded design (B), each step of the agent (C), the engineer's accept or reject (D), and pairs of
 * contracts one input apart (E). From campaigns, three more things are cut: decision records,
 * snapshot tasks and preference pairs. And tasks are made from all of it. Each task gives
 * something, asks for something back, and names the grader that marks the answer.
 *
 * The counts are real and zero today; the examples are in words, never numbers. The first
 * version (axes, pairs, a comparison of contracts) is archived in `archive/web/data-v1/`.
 */

import type { Tab, TabProps } from "../app/tab";
import { Dot } from "../panel/bits";
import { Badge, PageHead, Section } from "../panel/page";
import { CUTS, datapoints, KINDS } from "../words/kinds";
import { gradableNow, GRADER_STATUS, graderOf, TASK_TYPES } from "../words/taskTypes";

function Stage({ snap }: TabProps) {
  const total = datapoints(snap);
  const ready = gradableNow().length;
  return (
    <div className="stage-scroll cp-scroll">
      <div className="cp-page">
        <PageHead
          kicker="Data"
          title="What the record becomes"
          sub="Datapoints from every step, and the tasks cut from them"
          side={
            <div className="cp-badges">
              <Badge>{total === 1 ? "1 datapoint" : `${total} datapoints`}</Badge>
              <Badge tone="ok">
                {TASK_TYPES.length} task types · {ready} gradable now
              </Badge>
            </div>
          }
        />

        <Section title="Datapoints" aside="what the factory records">
          <table className="cp-table cp-kinds">
            <thead>
              <tr>
                <th>Kind</th>
                <th>What it is</th>
                <th>Example</th>
                <th>Trains</th>
                <th className="num">Count</th>
              </tr>
            </thead>
            <tbody>
              {KINDS.map((k) => (
                <tr key={k.letter}>
                  <th>
                    <span className="cp-letter">{k.letter}</span> {k.name}
                  </th>
                  <td>{k.what}</td>
                  <td className="dim">{k.example}</td>
                  <td>{k.trains}</td>
                  <td className="num mono">{k.count(snap)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Section title="Cut from campaigns">
          <div className="cp-cuts">
            {CUTS.map((c) => (
              <div key={c.name} className="cp-card">
                <div className="cp-cut-head">
                  <b>{c.name}</b>
                  <span className="mono">{c.count(snap)}</span>
                </div>
                <div className="dim">{c.what}</div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Tasks" aside="given · hand in · graded by">
          <table className="cp-table cp-tasks">
            <thead>
              <tr>
                <th className="num">#</th>
                <th>Task</th>
                <th>Given</th>
                <th>Hand in</th>
                <th>Graded by</th>
                <th>Used for</th>
                <th className="num">Made</th>
              </tr>
            </thead>
            <tbody>
              {TASK_TYPES.map((t) => {
                const grader = graderOf(t);
                const status = GRADER_STATUS[grader.status];
                return (
                  <tr key={t.n} data-ready={grader.status === "exists"}>
                    <td className="num mono">{t.n}</td>
                    <th>{t.task}</th>
                    <td>{t.given}</td>
                    <td>{t.handIn}</td>
                    <td title={status.words}>
                      <Dot status={status.dot} /> {grader.label}
                    </td>
                    <td className="dim">{t.usedFor}</td>
                    <td className="num mono">{snap.records.snapshot_tasks.filter((s) => s.task_type === t.n).length}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Section>
      </div>
    </div>
  );
}

export const dataTab: Tab = { Stage, cardName: "" };
