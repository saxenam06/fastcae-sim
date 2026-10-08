/**
 * Campaigns: the agent's attempts at the contract.
 *
 * A campaign starts from the frozen contract with a solver and a budget. It then runs in steps:
 * the agent reads the evidence, writes a hypothesis with its reason and what would prove it wrong,
 * calls the tools, sees the result, and decides the next step, until a stop rule fires. Each step
 * is a row, and each row becomes a decision record (C) in Data.
 *
 * Nothing runs yet: the agent (AGT-1) is not built, and the contract must be frozen first. So the
 * form is shown with its choices made, and the steps table shows the shape of a row in words.
 * The first version (a page per view, a rail of campaigns) is archived in
 * `archive/web/campaigns-v1/`.
 */

import { shortTitle } from "../app/product";
import type { Tab, TabProps } from "../app/tab";
import { Dot } from "../panel/bits";
import { Badge, PageHead, Section, Value } from "../panel/page";
import { ARM, ARM_ORDER, STOP, STOP_ORDER } from "../words/campaign";

/** The parts of one step, in the order a row reads; the template row says what each will hold. */
const COLUMNS: { head: string; holds: string }[] = [
  { head: "Step", holds: "1, 2, 3 …" },
  { head: "Saw", holds: "the evidence: the margins, where the housing is soft, the budget left" },
  { head: "Tried, and why", holds: "the hypothesis: what to change, why, the gain expected, what would prove it wrong" },
  { head: "Tools", holds: "geometry, FE" },
  { head: "Design", holds: "the housing it made" },
  { head: "Grade", holds: "pass or fail, the mass, the worst margin" },
  { head: "Next", holds: "the next step, or stop" },
];

function Stage({ snap, go }: TabProps) {
  const contract = snap.contracts[0];
  if (!contract) return <div className="stage-scroll" />;
  const campaigns = snap.records.campaigns.filter((c) => c.contract === contract.id);
  const steps = snap.records.decisions.filter((d) => campaigns.some((c) => c.id === d.campaign));
  const frozen = contract.stage === "frozen";
  const blocked = !frozen
    ? "Needs the contract frozen: the load tool (GBX-1) derives it first"
    : "Needs the agent (AGT-1)";
  return (
    <div className="stage-scroll cp-scroll">
      <div className="cp-page">
        <PageHead
          kicker="Campaigns"
          title={shortTitle(contract.title)}
          sub="The agent's attempts at the contract: each step, what it tried and why, what happened"
          side={
            <div className="cp-badges">
              <Badge>{campaigns.length === 1 ? "1 campaign" : `${campaigns.length} campaigns`}</Badge>
              <Badge tone="wait">{blocked}</Badge>
            </div>
          }
        />

        <Section title="New campaign">
          <div className="cp-card cp-form">
            <table className="cp-inputs">
              <tbody>
                <tr>
                  <th>Contract</th>
                  <td>
                    <button className="cp-link" onClick={() => go({ view: "contracts" })}>
                      <Value value={`${shortTitle(contract.title)} · ${contract.stage}`} />
                    </button>
                  </td>
                </tr>
                <tr>
                  <th>Solver</th>
                  <td>
                    <Value value={cap(ARM.agent.label)} options={ARM_ORDER.map((a) => cap(ARM[a].label))} />
                  </td>
                </tr>
                <tr>
                  <th>Budget</th>
                  <td>
                    <Value value={`${contract.budget_fe_proofs} FE runs · ${contract.budget_hours} h`} />
                  </td>
                </tr>
                <tr>
                  <th>Stops when</th>
                  <td className="cp-stops">
                    {STOP_ORDER.map((s) => (
                      <span key={s} className="pill" title={STOP[s].words}>
                        {STOP[s].short}
                      </span>
                    ))}
                  </td>
                </tr>
              </tbody>
            </table>
            <div className="cp-actions">
              <button className="cp-start" disabled title={blocked}>
                Start campaign
              </button>
              <span className="dim">{blocked}</span>
            </div>
          </div>
        </Section>

        <Section title="Steps" aside={steps.length ? `${steps.length} steps` : "none yet"}>
          <table className="cp-table cp-steps">
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.head}>{c.head}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {steps.length ? (
                steps.map((d) => (
                  <tr key={d.id}>
                    <td className="mono">{d.step}</td>
                    <td>{d.saw}</td>
                    <td>{d.decided}</td>
                    <td className="mono">{d.tools.map((t) => t.tool).join(", ")}</td>
                    <td className="mono">{d.candidate ?? "-"}</td>
                    <td>{d.happened}</td>
                    <td>{d.next}</td>
                  </tr>
                ))
              ) : (
                <tr className="cp-template">
                  {COLUMNS.map((c) => (
                    <td key={c.head}>{c.holds}</td>
                  ))}
                </tr>
              )}
            </tbody>
            <caption>
              <Dot status="blank" /> Every step becomes a decision record (C) in Data
            </caption>
          </table>
        </Section>
      </div>
    </div>
  );
}

function cap(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const campaignsTab: Tab = { Stage, cardName: "" };
