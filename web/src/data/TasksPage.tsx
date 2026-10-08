/**
 * Tasks: the twenty task types of the data design (§6), each with what it gives, what it asks back,
 * how it is graded, and whether that grader exists in zenryx yet.
 *
 * A table rather than cards, because the columns are the point: read down "graded by" and the
 * gaps show what must be built before a task type can be set. The filter keeps only the task types
 * gradable now. The instance counts are the record's snapshot tasks of each type, 0 until a
 * campaign is cut into them (DAT-2).
 */

import { useEffect, useRef, useState } from "react";
import type { TabProps } from "../app/tab";
import { Blank, Block, Count } from "../panel/bits";
import { gradableNow, TASK_NOTE, TASK_TYPES } from "./taskTypes";
import { GraderPill } from "./views";

type Filter = "all" | "now";

export function TasksPage({ snap, route, go }: TabProps) {
  const [filter, setFilter] = useState<Filter>("all");
  const now = gradableNow();
  const shown = filter === "all" ? TASK_TYPES : now;
  const focus = route.focus;
  const rows = useRef(new Map<string, HTMLTableRowElement>());

  // A task type picked in the rail may sit below the fold; bring its row into view.
  useEffect(() => {
    if (focus) rows.current.get(focus)?.scrollIntoView({ block: "nearest" });
  }, [focus, filter]);

  const instances = (n: number) => snap.records.snapshot_tasks.filter((s) => s.task_type === n).length;

  return (
    <Block title="Task types" count={TASK_TYPES.length} aside={`${now.length} gradable now`}>
      <div className="data-filter">
        <div className="segmented">
          <button data-active={filter === "all"} onClick={() => setFilter("all")}>
            all <span className="num">{TASK_TYPES.length}</span>
          </button>
          <button data-active={filter === "now"} onClick={() => setFilter("now")} title="Their grader exists">
            gradable now <span className="num">{now.length}</span>
          </button>
        </div>
        <span className="data-note" title={TASK_NOTE}>
          H: Hofstetter's EV reducer · AG: the agricultural EV gearbox · numbers illustrative
        </span>
      </div>
      <div className="tbl-wrap">
        <table className="tbl data-table data-tasks">
          <thead>
            <tr>
              <th className="data-right">#</th>
              <th>Task</th>
              <th>Given</th>
              <th>Hand in</th>
              <th>Graded by</th>
              <th>Used for</th>
              <th className="data-right">Instances</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((t) => {
              const key = `task:${t.n}`;
              return (
                <tr
                  key={t.n}
                  ref={(el) => {
                    if (el) rows.current.set(key, el);
                    else rows.current.delete(key);
                  }}
                  data-click="true"
                  data-focus={focus === key}
                  onClick={() => go({ focus: key })}
                >
                  <td className="num">{t.n}</td>
                  <td className="data-name">{t.task}</td>
                  <td>{t.given}</td>
                  <td>{t.handIn}</td>
                  <td>
                    <div>{t.gradedBy}</div>
                    <GraderPill task={t} />
                  </td>
                  <td>{t.usedFor}</td>
                  <td className="num">
                    <Count n={instances(t.n)} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="data-gap">
        <Blank
          title="No task instances yet"
          waits="Instances are cut from campaigns as snapshot tasks (DAT-2) and exported with their grader (DAT-4)"
        />
      </div>
    </Block>
  );
}
