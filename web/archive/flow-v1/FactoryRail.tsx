/**
 * The factory on the left, drawn as fastcae's pipeline rail (fastcae-v1:ui/src/pipeline/
 * PipelineRail.tsx): every stage from a requirement to a datapoint, in the order the work happens,
 * grouped into the task, the attempt, the judgement and the data.
 *
 * A stage's dot says whether its maker is built - dashed when it is not - and its count says what
 * it has made. A stage opens to what it is, what makes it, and the stages either side of it; as in
 * fastcae, opening one also puts it in the card, and whatever the focus moves to from elsewhere is
 * opened here, so the rail always shows where the card's step sits in the line.
 */

import { useEffect, useState } from "react";
import type { TabProps } from "../app/tab";
import { Count, Dot } from "../panel/bits";
import type { Snapshot } from "../records/types";
import {
  GROUPS,
  maker,
  neighbours,
  noun,
  STAGES,
  stagesIn,
  stageStatus,
  STATUS_WORDS,
  type FactoryStage,
} from "./stages";

export function FactoryRail({ snap, route, go }: TabProps) {
  const focus = route.focus;
  const [open, setOpen] = useState<Set<string>>(() => new Set(focus ? [focus] : []));

  useEffect(() => {
    if (focus && STAGES.some((s) => s.id === focus)) {
      setOpen((was) => (was.has(focus) ? was : new Set(was).add(focus)));
    }
  }, [focus]);

  const toggle = (stage: FactoryStage) => {
    // Opening a step shows it in the card; closing one only closes it.
    if (!open.has(stage.id)) go({ focus: stage.id });
    setOpen((was) => {
      const next = new Set(was);
      if (next.has(stage.id)) next.delete(stage.id);
      else next.add(stage.id);
      return next;
    });
  };

  return (
    <nav className="pipeline flow-rail">
      <header className="pipeline-head">
        <span>The factory</span>
      </header>
      {GROUPS.map((group) => {
        const steps = stagesIn(group.id);
        const built = steps.filter((s) => s.built).length;
        return (
          <section key={group.id} className="pipeline-stage">
            <header title={group.words}>
              <span>{group.label}</span>
              <span className="count" title={`${built} of ${steps.length} built`}>
                {built}/{steps.length}
              </span>
            </header>
            {steps.map((stage) => (
              <StepRow
                key={stage.id}
                stage={stage}
                snap={snap}
                open={open.has(stage.id)}
                focused={focus === stage.id}
                onToggle={() => toggle(stage)}
                onFocus={(id) => go({ focus: id })}
              />
            ))}
          </section>
        );
      })}
      <div className="flow-legend">
        <span>
          <Dot status="done" /> made some
        </span>
        <span>
          <Dot status="pending" /> built, none yet
        </span>
        <span>
          <Dot status="blank" /> not built
        </span>
      </div>
    </nav>
  );
}

function StepRow(props: {
  stage: FactoryStage;
  snap: Snapshot;
  open: boolean;
  focused: boolean;
  onToggle: () => void;
  onFocus: (id: string) => void;
}) {
  const { stage, snap } = props;
  const n = stage.count(snap);
  const status = stageStatus(stage, n);
  const madeBy = stage.madeBy(snap);
  const { prev, next } = neighbours(stage);
  return (
    <div className="step" data-status={status} data-open={props.open} data-focus={props.focused}>
      <button className="step-head" onClick={props.onToggle} title={`${stage.label}: ${stage.what}`}>
        <i className="dot" title={STATUS_WORDS[status]} />
        <span className="step-label">{stage.label}</span>
        <span className="step-time" title={`${n} ${noun(stage, n)}`}>
          <Count n={n} />
        </span>
      </button>
      {!props.open ? (
        <div className="step-line" title={madeBy}>
          {madeBy}
        </div>
      ) : (
        <div className="step-body">
          <div className="step-detail">
            {stage.what}
            {stage.detail ? `; ${stage.detail}` : ""}
          </div>
          <div className="io">
            <span className="io-tag">by</span>
            <span className="flow-by">
              {maker(stage, snap)}
              {stage.built ? null : <span className="dim"> · not built</span>}
            </span>
          </div>
          {prev ? <Neighbour tag="in" stage={prev} snap={snap} onFocus={props.onFocus} /> : null}
          {next ? <Neighbour tag="out" stage={next} snap={snap} onFocus={props.onFocus} /> : null}
        </div>
      )}
    </div>
  );
}

function Neighbour({
  tag,
  stage,
  snap,
  onFocus,
}: {
  tag: "in" | "out";
  stage: FactoryStage;
  snap: Snapshot;
  onFocus: (id: string) => void;
}) {
  const n = stage.count(snap);
  return (
    <div className="io">
      <span className="io-tag">{tag}</span>
      <div className="io-chips">
        <button
          className="chip-in"
          data-empty={n === 0}
          title={`${tag === "in" ? "from" : "into"} ${stage.label}: ${n} ${noun(stage, n)}`}
          onClick={() => onFocus(stage.id)}
        >
          <b>{n.toLocaleString("en-GB")}</b> {stage.label.toLowerCase()}
        </button>
      </div>
    </div>
  );
}
