/**
 * Steps: fastcae's campaign grid turned to the agent. A step a row, read left to right as a
 * decision record runs: what the agent saw, the idea it tried, the tools it called, the design that
 * came of it, the tests and the grade, the status code gave the idea, and the next step. A click
 * opens the step's whole record in the card.
 *
 * Before any campaign the table holds one template row, in words, of what each cell will hold.
 * Under it, the plan's stop rules and the arms that may attempt a task: the one that applies to the
 * campaign in view is marked, and none is marked before a campaign exists.
 */

import type { TabProps } from "../app/tab";
import { Blank, Block } from "../panel/bits";
import type { DecisionRecord, Snapshot } from "../records/types";
import type { Column } from "./bits";
import { Clamp, Grade, StatusPill, TableHead, TemplateRow } from "./bits";
import { CampaignHead } from "./Head";
import { candidateById, episodeById, evaluationsOf, inView, kindTally, stepsOf, toolRuns } from "./records";
import { ARM, ARM_ORDER, STOP, STOP_ORDER } from "./words";

const COLUMNS: Column[] = [
  { id: "step", label: "Step", template: "in order", kind: "narrow" },
  {
    id: "saw",
    label: "Saw",
    template: "what the agent saw: the best design so far, its margins, where the strain energy sits, the budget left",
    kind: "wide",
    min: 140,
  },
  {
    id: "hypothesis",
    label: "Hypothesis",
    template: "the idea, its reason, what it expects, what would prove it wrong",
    kind: "wide",
    min: 130,
  },
  { id: "tools", label: "Tools", template: "the typed tools it called, in order", min: 84 },
  { id: "design", label: "Design", template: "the design it made", min: 64 },
  { id: "evaluations", label: "Evaluations", template: "the tests it was graded under" },
  { id: "grade", label: "Grade", template: "the verdict, the worst margin, the mass", min: 84 },
  {
    id: "status",
    label: "Status (code)",
    template: "the idea's status, from the evidence",
    title: "Computed by code from the evidence; the agent never sets it",
  },
  { id: "next", label: "Next", template: "the next step, or the stop rule that fired", min: 84 },
];

export function StepsPage(props: TabProps) {
  const { snap, route, go } = props;
  const { campaign } = inView(snap, route);
  const steps = campaign ? stepsOf(snap, campaign.id) : [];
  return (
    <div className="stage-scroll cmp-page">
      <CampaignHead {...props} />

      <Block title="Steps" count={steps.length} aside="a step a row · a click opens its record">
        <div className="tbl-wrap">
          <table className="tbl cmp-steps">
            <TableHead columns={COLUMNS} />
            <tbody>
              {steps.length ? (
                steps.map((s) => (
                  <StepRow
                    key={s.id}
                    snap={snap}
                    step={s}
                    focused={route.focus === s.id}
                    onFocus={() => go({ focus: s.id })}
                    onDesign={(id) => go({ view: "designs", id })}
                  />
                ))
              ) : (
                <TemplateRow columns={COLUMNS} />
              )}
            </tbody>
          </table>
        </div>
      </Block>

      <Block title="Stop rules" aside={campaign?.stop ? "the one that fired is marked" : "a campaign stops on one"}>
        <div className="pills">
          {STOP_ORDER.map((id) => (
            <span key={id} className="pill cmp-pill" data-on={campaign?.stop === id} title={STOP[id].words}>
              {STOP[id].label}
            </span>
          ))}
        </div>
        {campaign?.stop_reason ? <p className="cmp-reason">{campaign.stop_reason}</p> : null}
      </Block>

      <Block title="Who attempts" aside="every arm on the same tools, at equal budget">
        <div className="pills">
          {ARM_ORDER.map((id) => (
            <span key={id} className="pill cmp-pill" data-on={campaign?.arm === id} title={ARM[id].words}>
              {ARM[id].label}
            </span>
          ))}
        </div>
      </Block>

      {snap.records.campaigns.length === 0 ? (
        <Blank title="Not built yet" waits="the agent and its campaign state (AGT-1)" />
      ) : null}
    </div>
  );
}

/** One step, its cells read from its decision record and the records it points at. */
function StepRow({
  snap,
  step,
  focused,
  onFocus,
  onDesign,
}: {
  snap: Snapshot;
  step: DecisionRecord;
  focused: boolean;
  onFocus: () => void;
  onDesign: (id: string) => void;
}) {
  const episode = episodeById(snap, step.episode);
  const design = candidateById(snap, step.candidate);
  const evaluations = design ? evaluationsOf(snap, design.id) : [];
  return (
    <tr data-click="true" data-focus={focused} onClick={onFocus}>
      <td className="num cmp-narrow">{step.step}</td>
      <td className="cmp-wide">
        <Clamp text={step.saw} />
      </td>
      <td className="cmp-wide">
        <Clamp text={episode?.claim ?? step.decided} title={step.decided} />
      </td>
      <td className="mono">{step.tools.length ? toolRuns(step.tools) : "—"}</td>
      <td className="mono">
        {design ? (
          <button
            className="link"
            onClick={(e) => {
              e.stopPropagation();
              onDesign(design.id);
            }}
            title="Open the design"
          >
            {design.id}
          </button>
        ) : (
          "—"
        )}
      </td>
      <td>{evaluations.length ? kindTally(evaluations) : "—"}</td>
      <td>{design ? <Grade design={design} /> : "—"}</td>
      <td>
        <StatusPill status={step.status} />
      </td>
      <td>
        <Clamp text={step.next} />
      </td>
    </tr>
  );
}
