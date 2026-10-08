/**
 * Flow: where the whole factory stands, from the contract to the data.
 *
 * One strip of steps, in the order the work runs. Each step shows its count, whether what makes it
 * is built, and what it waits for; a click opens its tab. Under the strip are the tools still to
 * build, in order, each with what it unlocks. The first version (a contract-by-stage table and a
 * campaign diagram) is archived in `archive/web/flow-v1/`.
 */

import type { View } from "../app/product";
import type { Tab, TabProps } from "../app/tab";
import { Dot } from "../panel/bits";
import { PageHead, Section } from "../panel/page";
import type { Snapshot } from "../records/types";
import { datapoints } from "../words/kinds";
import { gradableNow, TASK_TYPES } from "../words/taskTypes";

interface Step {
  label: string;
  count: (snap: Snapshot) => string;
  /** What makes it, or what it waits for. */
  by: string;
  built: (snap: Snapshot) => boolean;
  view: View;
}

const STEPS: Step[] = [
  {
    label: "Contract",
    count: (s) => `${s.contracts.length} · ${s.contracts[0]?.stage ?? "-"}`,
    by: "you, checked by the validator",
    built: () => true,
    view: "contracts",
  },
  {
    label: "Derived",
    count: (s) => String(s.contracts.filter((c) => c.stage !== "posed").length),
    by: "the load tool (GBX-1)",
    built: () => false,
    view: "contracts",
  },
  {
    label: "Frozen task",
    count: (s) => String(s.contracts.filter((c) => c.stage === "frozen").length),
    by: "freeze, once derived",
    built: () => true,
    view: "contracts",
  },
  {
    label: "Campaigns",
    count: (s) => String(s.records.campaigns.length),
    by: "the agent (AGT-1)",
    built: () => false,
    view: "campaigns",
  },
  {
    label: "Designs",
    count: (s) => String(s.records.candidates.length),
    by: "geometry (GEO-1)",
    built: () => false,
    view: "designs",
  },
  {
    label: "Grades",
    count: (s) => String(s.records.candidates.filter((d) => d.passed !== null).length),
    by: "the judge (PHY-1)",
    built: () => false,
    view: "designs",
  },
  {
    label: "Datapoints",
    count: (s) => String(datapoints(s)),
    by: "recorded as the steps run",
    built: () => true,
    view: "data",
  },
  {
    label: "Tasks",
    count: () => `${TASK_TYPES.length} types`,
    by: `${gradableNow().length} gradable now`,
    built: () => true,
    view: "data",
  },
];

/** The tools still to build, in order, and what each unlocks. */
const NEXT: { tool: string; what: string; unlocks: string }[] = [
  { tool: "GBX-1", what: "the load tool: gear forces, the shaft spacing, bearing loads and sizes", unlocks: "the contract derived, then frozen" },
  { tool: "PHY-1", what: "the judge's FE solve: statics, then modes", unlocks: "grades" },
  { tool: "GEO-1", what: "geometry: the CadQuery core and the grown structure", unlocks: "designs" },
  { tool: "AGT-1", what: "the agent: hypotheses, tools, steps", unlocks: "campaigns, and the data they make" },
];

function Stage({ snap, go }: TabProps) {
  return (
    <div className="stage-scroll cp-scroll">
      <div className="cp-page">
        <PageHead kicker="Flow" title="Where the factory stands" sub="From the contract to the data, step by step" />

        <Section title="The factory">
          <ol className="cp-strip">
            {STEPS.map((s) => {
              const built = s.built(snap);
              return (
                <li key={s.label}>
                  <button className="cp-step" data-built={built} onClick={() => go({ view: s.view })} title={`Open ${s.view}`}>
                    <span className="cp-step-label">{s.label}</span>
                    <span className="cp-step-count mono">{s.count(snap)}</span>
                    <span className="cp-step-by">
                      <Dot status={built ? "done" : "blank"} /> {s.by}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </Section>

        <Section title="Next to build" aside="in order">
          <table className="cp-table">
            <tbody>
              {NEXT.map((n) => (
                <tr key={n.tool}>
                  <th className="mono">{n.tool}</th>
                  <td>{n.what}</td>
                  <td className="dim">unlocks {n.unlocks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      </div>
    </div>
  );
}

export const flowTab: Tab = { Stage, cardName: "" };
