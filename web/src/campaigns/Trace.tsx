/**
 * Trace: every tool call of the campaign, in order, as the trace keeps it - the tool, its version,
 * the hashes of what went in and what came out, how long it took, whether it ran, and the typed
 * failure when it did not. Calls are grouped under the step that made them; a group's head opens
 * that step in the card.
 *
 * Under the table, the agent's whole tool set as the plan groups it (§8.2), so the trace's names
 * can be read against the list of what exists. The closing line is the plan's rule that keeps the
 * proof budget out of the agent's hands.
 */

import type { TabProps } from "../app/tab";
import { Blank, Block, Hash } from "../panel/bits";
import type { DecisionRecord } from "../records/types";
import type { Column } from "./bits";
import { TableHead, TemplateRow } from "./bits";
import { CampaignHead } from "./Head";
import { duration, episodeById, inView, stepsOf } from "./records";
import { TOOL_GROUPS } from "./words";

const COLUMNS: Column[] = [
  { id: "n", label: "#", template: "in order", kind: "narrow", min: 64 },
  { id: "tool", label: "Tool", template: "the typed tool called", min: 100 },
  { id: "version", label: "Version", template: "the tool's version", min: 80 },
  { id: "input", label: "Input hash", template: "what it was given", min: 100 },
  { id: "output", label: "Output hash", template: "what it returned", min: 100 },
  { id: "time", label: "Time", template: "how long it took", kind: "num", min: 70 },
  { id: "ok", label: "OK", template: "whether it ran", min: 60 },
  { id: "note", label: "Note", template: "on a failure, the rule and the place", kind: "wide", min: 150 },
];

const TOOLS = TOOL_GROUPS.reduce((n, g) => n + g.tools.length, 0);

const WHY_CODE_PICKS =
  "The agent decides the formulation, the strategy and when to stop; a deterministic acquisition rule " +
  "picks the candidates of a batch to prove, and the fixed workflow uses the same rule (plan §8.2, §10.3)";

export function TracePage(props: TabProps) {
  const { snap, route, go } = props;
  const { campaign } = inView(snap, route);
  const steps = campaign ? stepsOf(snap, campaign.id) : [];
  const calls = steps.reduce((n, s) => n + s.tools.length, 0);
  return (
    <div className="stage-scroll cmp-page">
      <CampaignHead {...props} />

      <Block title="Trace" count={calls} aside="every call, in order, with its version and hashes">
        <div className="tbl-wrap">
          <table className="tbl cmp-trace">
            <TableHead columns={COLUMNS} />
            <tbody>
              {calls ? (
                <Calls
                  steps={steps}
                  focus={route.focus}
                  onStep={(id) => go({ focus: id })}
                  claimOf={(id) => episodeById(snap, id)?.claim ?? null}
                />
              ) : (
                <TemplateRow columns={COLUMNS} />
              )}
            </tbody>
          </table>
        </div>
      </Block>

      <Block title="The agent's tools" count={TOOLS} aside="the same tools for every arm">
        <dl className="cmp-tools">
          {TOOL_GROUPS.map((g) => (
            <div key={g.group} className="cmp-tool-group">
              <dt title={g.words}>{g.group}</dt>
              <dd className="pills">
                {g.tools.map((t) => (
                  <span key={t.name} className="pill cmp-tool" title={t.words}>
                    {t.name}
                  </span>
                ))}
              </dd>
            </div>
          ))}
        </dl>
        <p className="cmp-rule" title={WHY_CODE_PICKS}>
          Which candidates get a proof is chosen in code, not by the agent
        </p>
      </Block>

      {snap.records.campaigns.length === 0 ? (
        <Blank title="Not built yet" waits="the agent's tools and their trace (AGT-1)" />
      ) : null}
    </div>
  );
}

/** The calls, a group a step: the step's head row, then its calls numbered across the campaign. */
function Calls({
  steps,
  focus,
  onStep,
  claimOf,
}: {
  steps: DecisionRecord[];
  focus: string | null;
  onStep: (id: string) => void;
  claimOf: (episode: string | null) => string | null;
}) {
  // Where each step's calls start in the campaign's numbering.
  const first: number[] = [];
  for (let i = 0; i < steps.length; i++) first.push(i === 0 ? 1 : first[i - 1] + steps[i - 1].tools.length);
  return (
    <>
      {steps.map((s, i) => (
        <StepCalls
          key={s.id}
          step={s}
          first={first[i]}
          focused={focus === s.id}
          onStep={() => onStep(s.id)}
          claim={claimOf(s.episode)}
        />
      ))}
    </>
  );
}

function StepCalls({
  step,
  first,
  focused,
  onStep,
  claim,
}: {
  step: DecisionRecord;
  first: number;
  focused: boolean;
  onStep: () => void;
  claim: string | null;
}) {
  return (
    <>
      <tr className="cmp-step-row" data-click="true" data-focus={focused} onClick={onStep}>
        <td colSpan={COLUMNS.length}>
          <b>step {step.step}</b> <span className="dim">{claim ?? step.decided}</span>
        </td>
      </tr>
      {step.tools.map((t, i) => (
        <tr key={i} data-ok={t.ok}>
          <td className="num cmp-narrow">{first + i}</td>
          <td className="mono">{t.tool}</td>
          <td className="mono">{t.version}</td>
          <td>
            <Hash value={t.input_hash} />
          </td>
          <td>
            <Hash value={t.output_hash} />
          </td>
          <td className="num">{duration(t.seconds)}</td>
          <td>{t.ok ? "✓" : <span className="cmp-bad">✗</span>}</td>
          <td className="cmp-wide">{t.note || <span className="dim">—</span>}</td>
        </tr>
      ))}
    </>
  );
}
