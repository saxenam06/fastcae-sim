/**
 * Hypotheses: every idea a campaign tried, as the plan states one (§3) - the claim, the physical
 * reason in front of it, the effect expected, what result would prove it wrong, the seed it started
 * from, its budget, and the status code computed for it.
 *
 * The status column sits last and apart because it is the only one the agent did not write: code
 * computes it from the evidence. The legend under the table says what each status means, and the
 * seeds the plan offers (§8.3) follow, with the one deferred past the MVP marked.
 */

import type { TabProps } from "../app/tab";
import { Blank, Block } from "../panel/bits";
import type { Column } from "./bits";
import { Clamp, StatusPill, TableHead, TemplateRow } from "./bits";
import { CampaignHead } from "./Head";
import { episodesOf, inView, stepsOf } from "./records";
import { SEEDS, STATUS, STATUS_ORDER } from "./words";

const COLUMNS: Column[] = [
  { id: "claim", label: "Hypothesis (claim)", template: "the idea, in the agent's own words", kind: "wide", min: 150 },
  { id: "reason", label: "Reason", template: "the physical reason it should work", kind: "wide", min: 150 },
  { id: "expected", label: "Expected", template: "the effect it should have, and at what cost", min: 110 },
  { id: "wrong_if", label: "Wrong if", template: "the result that would prove it wrong", min: 110 },
  { id: "seed", label: "Seed", template: "the formulation it started from", min: 100 },
  { id: "budget", label: "Budget", template: "the FE proofs it may spend", kind: "num", min: 80 },
  {
    id: "status",
    label: "Status",
    template: "as code computes it from the evidence",
    title: "Computed by code from the evidence; the agent never sets it",
    min: 96,
  },
];

export function HypothesesPage(props: TabProps) {
  const { snap, route, go } = props;
  const { campaign } = inView(snap, route);
  const episodes = campaign ? episodesOf(snap, campaign.id) : [];
  const steps = campaign ? stepsOf(snap, campaign.id) : [];
  return (
    <div className="stage-scroll cmp-page">
      <CampaignHead {...props} />

      <Block title="Hypotheses" count={episodes.length} aside="an idea a row, with its own test">
        <div className="tbl-wrap">
          <table className="tbl cmp-hyps">
            <TableHead columns={COLUMNS} />
            <tbody>
              {episodes.length ? (
                episodes.map((h) => (
                  <tr
                    key={h.id}
                    data-click="true"
                    data-focus={route.focus === h.id}
                    onClick={() => go({ focus: h.id })}
                    title={`${steps.filter((s) => s.episode === h.id).length} steps · a click opens it`}
                  >
                    <td className="cmp-wide">
                      <Clamp text={h.claim} />
                    </td>
                    <td className="cmp-wide">
                      <Clamp text={h.reason} />
                    </td>
                    <td>
                      <Clamp text={h.expected} />
                    </td>
                    <td>
                      <Clamp text={h.wrong_if} />
                    </td>
                    <td>{h.seed ?? <span className="dim">none</span>}</td>
                    <td className="num">{h.budget_fe_proofs}</td>
                    <td>
                      <StatusPill status={h.status} />
                    </td>
                  </tr>
                ))
              ) : (
                <TemplateRow columns={COLUMNS} />
              )}
            </tbody>
          </table>
        </div>
      </Block>

      <Block title="Status, as code computes it" aside="the agent never sets it">
        <div className="cmp-gloss">
          {STATUS_ORDER.map((s) => (
            <span key={s} title={STATUS[s].words}>
              <StatusPill status={s} />
              <span className="dim">{STATUS[s].short}</span>
            </span>
          ))}
        </div>
      </Block>

      <Block title="Seeds" count={SEEDS.length} aside="where a hypothesis may start; the claim is the agent's">
        <div className="pills">
          {SEEDS.map((s) => (
            <span
              key={s.name}
              className="pill cmp-seed"
              data-later={Boolean(s.later)}
              title={`${s.representation}\nSuits: ${s.suits}${s.later ? `\n${s.later}` : ""}`}
            >
              {s.name}
              {s.later ? <span className="cmp-later">{s.later}</span> : null}
            </span>
          ))}
        </div>
      </Block>

      {snap.records.campaigns.length === 0 ? (
        <Blank title="Not built yet" waits="hypotheses and the code that grades them (AGT-1)" />
      ) : null}
    </div>
  );
}
