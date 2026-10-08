/**
 * The design card: one housing in full - its rung, its mass, its verdict and worst margin, every
 * evaluation it was graded under, and where it came from (the hypothesis, the campaign, the
 * contract). The rung leads, because a design is always labelled with it.
 *
 * Before any design the card shows the ladder a design will be placed on, rung by rung with who
 * signs it, so the label every design carries can be read before there is one.
 */

import { Fragment } from "react";
import { shortTitle } from "../app/product";
import type { CardProps } from "../app/tab";
import { CardFrame, Dot } from "../panel/bits";
import type { Candidate, Snapshot } from "../records/types";
import { Holds, Part, StatusPill, Verdict } from "../campaigns/bits";
import { campaignById, candidateById, contractById, episodeById, evaluationsOf, kg, pct } from "../campaigns/records";
import { ARM } from "../campaigns/words";
import { RungPill } from "./bits";
import { evaluationVerdict, resultWords, stageState } from "./records";
import { RUNG, RUNG_ORDER, STAGES } from "./words";

type Go = CardProps["go"];

export function DesignCard({ snap, route, go, onCollapse }: CardProps) {
  const design = candidateById(snap, route.id);
  return (
    <CardFrame kind="the design" onCollapse={onCollapse}>
      {design ? <DesignBody snap={snap} design={design} go={go} /> : <NoDesign />}
    </CardFrame>
  );
}

function NoDesign() {
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">design</span>
          <Dot status="blank" title="Not built yet: GEO-1, PHY-1" />
        </div>
        <h2 className="entity-title">No design</h2>
        <div className="entity-made">each design is labelled with its rung, never “production-ready”</div>
      </header>
      <Part title="The rungs" count={RUNG_ORDER.length}>
        <dl className="fields-list dsg-ladder">
          {RUNG_ORDER.map((r) => (
            <Fragment key={r}>
              <dt>
                <RungPill rung={r} />
              </dt>
              <dd className={RUNG[r].own ? undefined : "dim"} title={RUNG[r].needs}>
                {RUNG[r].signs}
              </dd>
            </Fragment>
          ))}
        </dl>
        <Holds>the platform reaches the second rung on its own; the rest need partners</Holds>
      </Part>
    </>
  );
}

function DesignBody({ snap, design, go }: { snap: Snapshot; design: Candidate; go: Go }) {
  const episode = episodeById(snap, design.episode);
  const campaign = campaignById(snap, design.campaign);
  const contract = contractById(snap, campaign?.contract ?? null);
  const evaluations = evaluationsOf(snap, design.id);
  return (
    <>
      <header className="entity-head">
        <div className="entity-kind">
          <span className="kind-chip">design</span>
          <RungPill rung={design.rung} />
          <Verdict passed={design.passed} failure={design.failure} />
        </div>
        <h2 className="entity-title mono">{design.id}</h2>
        {episode ? <p className="design-why">{episode.claim}</p> : null}
      </header>

      <Part title="Grade">
        <dl className="fields-list">
          <dt>rung</dt>
          <dd title={RUNG[design.rung].needs}>
            {RUNG[design.rung].label}
            {design.rung !== "none" ? <span className="dim"> · {RUNG[design.rung].signs}</span> : null}
          </dd>
          <dt>verdict</dt>
          <dd>
            <Verdict passed={design.passed} failure={design.failure} />
          </dd>
          <dt>worst margin</dt>
          <dd className="num">{pct(design.worst_margin)}</dd>
          <dt>mass</dt>
          <dd className="num">{kg(design.mass_kg)}</dd>
          {design.failure ? (
            <>
              <dt>failure</dt>
              <dd className="dsg-bad">{design.failure}</dd>
            </>
          ) : null}
        </dl>
      </Part>

      <Part title="Stages" count={STAGES.length}>
        <dl className="fields-list">
          {STAGES.map((s) => {
            const st = stageState(snap, design, s.id);
            return (
              <Fragment key={s.id}>
                <dt title={s.words}>
                  <Dot status={st.status} /> {s.label}
                </dt>
                <dd title={st.title}>{st.text}</dd>
              </Fragment>
            );
          })}
        </dl>
      </Part>

      <Part title="Evaluations" count={evaluations.length}>
        {evaluations.length ? (
          <div className="dsg-card-evals">
            {evaluations.map((e) => (
              <div key={e.id} className="dsg-card-eval">
                <div>
                  <Verdict passed={evaluationVerdict(e)} /> <b>{e.scenario}</b>{" "}
                  <span className="dim">
                    {e.kind} · {e.fidelity}
                  </span>
                </div>
                <div className="dsg-results">
                  {e.results.map((r) => (
                    <span
                      key={r.name}
                      className="vs-pill"
                      data-better={r.passed === true}
                      data-worse={r.passed === false}
                    >
                      {resultWords(r)}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Holds>no evaluation recorded yet</Holds>
        )}
      </Part>

      <Part title="Made by">
        <dl className="fields-list">
          <dt>hypothesis</dt>
          <dd>
            {episode ? (
              <>
                <button
                  className="link"
                  onClick={() => go({ view: "campaigns", id: design.campaign, page: "hypotheses", focus: episode.id })}
                >
                  {episode.claim}
                </button>{" "}
                <StatusPill status={episode.status} />
              </>
            ) : (
              "—"
            )}
          </dd>
          <dt>campaign</dt>
          <dd>
            <button className="link mono" onClick={() => go({ view: "campaigns", id: design.campaign })}>
              {design.campaign}
            </button>
            {campaign ? <span className="dim"> · {ARM[campaign.arm].label}</span> : null}
          </dd>
          <dt>contract</dt>
          <dd>
            {contract ? (
              <button className="link" onClick={() => go({ view: "contracts", id: contract.id })}>
                {shortTitle(contract.title)}
              </button>
            ) : (
              "—"
            )}
          </dd>
        </dl>
      </Part>
    </>
  );
}
