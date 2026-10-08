/**
 * The Designs rail: designs grouped by the campaign that made them, a row each with a dot a stage,
 * its verdict and its rung - fastcae's design rail, with the rung added because a design is always
 * labelled with it.
 *
 * Before any design, the rail says what a design is and lists the stages every row will carry,
 * each with what builds it, so the dots of the rows to come can be read before they exist.
 */

import type { TabProps } from "../app/tab";
import { Dot } from "../panel/bits";
import type { Candidate } from "../records/types";
import { Verdict } from "../campaigns/bits";
import { campaignById, pct } from "../campaigns/records";
import { ARM } from "../campaigns/words";
import { RungPill } from "./bits";
import { byCampaign, stageState } from "./records";
import { STAGES } from "./words";

export function DesignsRail({ snap, route, go }: TabProps) {
  const designs = snap.records.candidates;
  return (
    <nav className="dsg-rail">
      {designs.length ? (
        byCampaign(designs).map((g) => {
          const c = campaignById(snap, g.campaign);
          return (
            <section key={g.campaign} className="rail-group">
              <header>
                <button
                  className="link mono"
                  onClick={() => go({ view: "campaigns", id: g.campaign })}
                  title="Open the campaign"
                >
                  {g.campaign}
                </button>
                {c ? <span className="dim">{ARM[c.arm].label}</span> : null}
                <span className="count">{g.designs.length}</span>
              </header>
              {g.designs.map((d) => (
                <DesignRow key={d.id} snap={snap} route={route} go={go} design={d} />
              ))}
            </section>
          );
        })
      ) : (
        <>
          <div className="dsg-none">No design yet</div>
          <div className="rail-note">
            A design is one housing a hypothesis produced: the machined core and the structure joined
          </div>
        </>
      )}
      <section className="rail-group dsg-legend">
        <header>
          Each design's stages <span className="count">{STAGES.length}</span>
        </header>
        <ol>
          {STAGES.map((s) => (
            <li key={s.id} title={s.words}>
              <Dot status={designs.length ? "pending" : "blank"} />
              <span>
                {s.label}
                {s.method ? <span className="dim"> ({s.method})</span> : null}
              </span>
              <span className="dim mono">{s.builds}</span>
            </li>
          ))}
        </ol>
      </section>
    </nav>
  );
}

function DesignRow({ snap, route, go, design }: Pick<TabProps, "snap" | "route" | "go"> & { design: Candidate }) {
  return (
    <button className="design-row" data-active={route.id === design.id} onClick={() => go({ id: design.id })}>
      <span className="dsg-row-head">
        <b className="mono">{design.id}</b>
        <RungPill rung={design.rung} />
      </span>
      <span className="design-stages">
        {STAGES.map((s) => {
          const st = stageState(snap, design, s.id);
          return <i key={s.id} data-status={st.status} title={`${s.label}: ${st.text}`} />;
        })}
      </span>
      <span className="dsg-verdict">
        <Verdict passed={design.passed} failure={design.failure} />
        {design.worst_margin !== null ? <span className="num dim">{pct(design.worst_margin)}</span> : null}
      </span>
      {design.failure ? <span className="design-failed">{design.failure}</span> : null}
    </button>
  );
}
