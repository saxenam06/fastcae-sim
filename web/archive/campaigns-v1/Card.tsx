/**
 * The step card: one decision record in full, in its three parts - what the agent saw, what it
 * decided and why, what happened - and the next step (data design §5, §7). A hypothesis in focus
 * shows that idea and the steps that tested it; with nothing in focus, the campaign in view.
 *
 * Before any campaign the card keeps the record's shape: each part with one dim line of what it
 * will hold, so the card says what a step is before there is one to show.
 */

import { shortTitle } from "../app/product";
import type { CardProps } from "../app/tab";
import { CardFrame, Count, Dot, Hash } from "../panel/bits";
import type { Campaign, ContractView, DecisionRecord, Episode, Snapshot } from "../records/types";
import { Grade, Holds, Part, StatusPill } from "./bits";
import { candidateById, candidatesOf, episodeById, episodesOf, inView, stepsOf, toolRuns } from "./records";
import { ARM, RECORD_PARTS, STOP } from "./words";

type Go = CardProps["go"];

export function StepCard({ snap, route, go, onCollapse }: CardProps) {
  const { campaign, contract } = inView(snap, route);
  const step = campaign ? (stepsOf(snap, campaign.id).find((s) => s.id === route.focus) ?? null) : null;
  const episode = campaign && !step ? (episodesOf(snap, campaign.id).find((e) => e.id === route.focus) ?? null) : null;
  if (step)
    return (
      <CardFrame kind="the step" onCollapse={onCollapse}>
        <StepBody snap={snap} step={step} go={go} />
      </CardFrame>
    );
  if (campaign && episode)
    return (
      <CardFrame kind="the hypothesis" onCollapse={onCollapse}>
        <HypothesisBody snap={snap} episode={episode} go={go} />
      </CardFrame>
    );
  if (campaign)
    return (
      <CardFrame kind="the campaign" onCollapse={onCollapse}>
        <CampaignBody snap={snap} campaign={campaign} contract={contract} go={go} />
      </CardFrame>
    );
  return (
    <CardFrame kind="the step" onCollapse={onCollapse}>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">step</span>
          <Dot status="blank" title="Not built yet: AGT-1" />
        </div>
        <h2 className="entity-title">No campaign</h2>
        <div className="entity-made">
          {contract ? `${shortTitle(contract.title)} · ` : ""}a step's card is its decision record
        </div>
      </header>
      {RECORD_PARTS.map((p) => (
        <Part key={p.id} title={p.title}>
          <Holds>{p.holds}</Holds>
        </Part>
      ))}
    </CardFrame>
  );
}

function StepBody({ snap, step, go }: { snap: Snapshot; step: DecisionRecord; go: Go }) {
  const episode = episodeById(snap, step.episode);
  const design = candidateById(snap, step.candidate);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">step {step.step}</span>
          <StatusPill status={step.status} />
        </div>
        <h2 className="entity-title">{episode?.claim ?? step.decided}</h2>
        <div className="entity-made mono">{step.campaign}</div>
      </header>
      <Part title={RECORD_PARTS[0].title}>
        <p className="cmp-text">{step.saw}</p>
      </Part>
      <Part title={RECORD_PARTS[1].title}>
        <p className="cmp-text">{step.decided}</p>
        {episode ? <EpisodeFields episode={episode} /> : null}
      </Part>
      <Part title={RECORD_PARTS[2].title}>
        <p className="cmp-text">{step.happened}</p>
        <dl className="fields-list">
          <dt>tools</dt>
          <dd className="mono">{step.tools.length ? toolRuns(step.tools) : "—"}</dd>
          <dt>design</dt>
          <dd>
            {design ? (
              <button className="link mono" onClick={() => go({ view: "designs", id: design.id })}>
                {design.id}
              </button>
            ) : (
              "—"
            )}
          </dd>
          <dt>grade</dt>
          <dd>{design ? <Grade design={design} /> : "—"}</dd>
          <dt>status</dt>
          <dd>
            <StatusPill status={step.status} /> <span className="dim">by code</span>
          </dd>
        </dl>
      </Part>
      <Part title={RECORD_PARTS[3].title}>
        <p className="cmp-text">{step.next}</p>
      </Part>
    </>
  );
}

function EpisodeFields({ episode }: { episode: Episode }) {
  return (
    <dl className="fields-list">
      <dt>claim</dt>
      <dd>{episode.claim}</dd>
      <dt>reason</dt>
      <dd>{episode.reason}</dd>
      <dt>expected</dt>
      <dd>{episode.expected}</dd>
      <dt>wrong if</dt>
      <dd>{episode.wrong_if}</dd>
      <dt>seed</dt>
      <dd>{episode.seed ?? "none"}</dd>
      <dt>budget</dt>
      <dd className="num">{episode.budget_fe_proofs} FE proofs</dd>
    </dl>
  );
}

function HypothesisBody({ snap, episode, go }: { snap: Snapshot; episode: Episode; go: Go }) {
  const steps = stepsOf(snap, episode.campaign).filter((s) => s.episode === episode.id);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">hypothesis</span>
          <StatusPill status={episode.status} />
        </div>
        <h2 className="entity-title">{episode.claim}</h2>
        <div className="entity-made mono">{episode.campaign}</div>
      </header>
      <Part title="The idea">
        <EpisodeFields episode={episode} />
      </Part>
      <Part title="Its steps" count={steps.length}>
        {steps.length ? (
          <dl className="fields-list">
            {steps.map((s) => (
              <StepLink key={s.id} step={s} go={go} />
            ))}
          </dl>
        ) : (
          <Holds>no step has tested it yet</Holds>
        )}
      </Part>
    </>
  );
}

function StepLink({ step, go }: { step: DecisionRecord; go: Go }) {
  return (
    <>
      <dt>
        <button className="link" onClick={() => go({ page: "steps", focus: step.id })}>
          step {step.step}
        </button>
      </dt>
      <dd>
        <StatusPill status={step.status} /> <span className="dim">{step.happened}</span>
      </dd>
    </>
  );
}

function CampaignBody({
  snap,
  campaign,
  contract,
  go,
}: {
  snap: Snapshot;
  campaign: Campaign;
  contract: ContractView | null;
  go: Go;
}) {
  const steps = stepsOf(snap, campaign.id);
  const best = candidateById(snap, campaign.best_design);
  const stop = campaign.stop ? STOP[campaign.stop] : null;
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">campaign</span>
          <span className="pill" title={ARM[campaign.arm].words}>
            {ARM[campaign.arm].label}
          </span>
        </div>
        <h2 className="entity-title mono">{campaign.id}</h2>
        <div className="entity-made">{contract ? shortTitle(contract.title) : campaign.contract}</div>
      </header>
      <Part title="The attempt">
        <dl className="fields-list">
          <dt>task</dt>
          <dd>
            {contract ? (
              <button className="link" onClick={() => go({ view: "contracts", id: contract.id })}>
                {shortTitle(contract.title)}
              </button>
            ) : (
              <span className="mono">{campaign.contract}</span>
            )}{" "}
            <Hash value={campaign.task_hash} />
          </dd>
          <dt>who</dt>
          <dd>{ARM[campaign.arm].label}</dd>
          <dt>model</dt>
          <dd className="mono">{campaign.model ?? "—"}</dd>
          <dt>brief</dt>
          <dd className="mono">{campaign.brief_version ?? "—"}</dd>
          <dt>budget</dt>
          <dd className="num">
            {campaign.spent_fe_proofs} of {campaign.budget_fe_proofs} FE proofs
          </dd>
          <dt>started</dt>
          <dd className="num">{campaign.started}</dd>
          <dt>ended</dt>
          <dd className="num">{campaign.ended ?? "running"}</dd>
          <dt>stop</dt>
          <dd title={stop?.words}>
            {stop ? stop.label : "—"}
            {campaign.stop_reason ? <div className="dim">{campaign.stop_reason}</div> : null}
          </dd>
          <dt>best design</dt>
          <dd>
            {best ? (
              <button className="link mono" onClick={() => go({ view: "designs", id: best.id })}>
                {best.id}
              </button>
            ) : (
              "—"
            )}
          </dd>
        </dl>
      </Part>
      <Part title="Steps" count={steps.length}>
        <Holds>
          {steps.length ? (
            <>
              <Count n={episodesOf(snap, campaign.id).length} /> hypotheses ·{" "}
              <Count n={candidatesOf(snap, campaign.id).length} /> designs · a click on a step opens its record
            </>
          ) : (
            "no step recorded yet"
          )}
        </Holds>
      </Part>
    </>
  );
}
