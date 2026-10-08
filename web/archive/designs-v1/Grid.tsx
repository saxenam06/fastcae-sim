/**
 * Grid: fastcae's campaign grid, a design a row and a stage a column - the machined core, the
 * structure, their join, the process check, the mesh, the statics and the modes - then the
 * verdict, the mass and the rung. Read across, a row is one housing's way from geometry to grade;
 * read down, a column shows where designs stop. Designs are grouped under the campaign that made
 * them; a click opens one in the card.
 *
 * Before any design the grid holds one template row, in words. Under it, what is real now: the
 * verdict each contract sets, and the rungs a design can be labelled with.
 */

import type { TabProps } from "../app/tab";
import { Block, Dot } from "../panel/bits";
import type { Candidate, Snapshot } from "../records/types";
import { Clamp, Verdict } from "../campaigns/bits";
import { campaignById, episodeById, kg, pct } from "../campaigns/records";
import { ARM } from "../campaigns/words";
import { DesignsHead, RungPill, StageName } from "./bits";
import { byCampaign, stageState } from "./records";
import { Rungs } from "./Rungs";
import { VerdictCards } from "./Verdicts";
import { STAGES } from "./words";

/** The columns either side of the stages, with what the template row says each will hold. */
const BEFORE = [
  { id: "design", label: "Design", template: "each housing made" },
  { id: "hypothesis", label: "Hypothesis", template: "the idea that made it" },
];

const AFTER = [
  { id: "verdict", label: "Verdict", template: "pass or fail, and the worst margin" },
  { id: "mass", label: "Mass", template: "its mass", className: "num" },
  { id: "rung", label: "Rung", template: "the rung it has reached" },
];

const SPAN = BEFORE.length + STAGES.length + AFTER.length;

export function GridPage({ snap, route, go }: TabProps) {
  const designs = snap.records.candidates;
  return (
    <div className="stage-scroll dsg-page">
      <DesignsHead snap={snap} />

      <Block title="Designs" count={designs.length} aside="a design a row, a stage a column · a click opens it">
        <div className="tbl-wrap">
          <table className="tbl dsg-grid">
            <thead>
              <tr>
                {BEFORE.map((c) => (
                  <th key={c.id}>{c.label}</th>
                ))}
                {STAGES.map((s) => (
                  <th key={s.id} title={`${s.words} · built by ${s.builds}`}>
                    <StageName label={s.label} method={s.method} />
                  </th>
                ))}
                {AFTER.map((c) => (
                  <th key={c.id} className={c.className}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {designs.length ? (
                byCampaign(designs).map((g) => (
                  <CampaignRows
                    key={g.campaign}
                    snap={snap}
                    campaign={g.campaign}
                    designs={g.designs}
                    focus={route.id}
                    onOpen={(id) => go({ id })}
                    onCampaign={() => go({ view: "campaigns", id: g.campaign })}
                  />
                ))
              ) : (
                <Template />
              )}
            </tbody>
          </table>
        </div>
      </Block>

      <Block
        title="The verdict each contract sets"
        count={snap.contracts.length}
        aside="the limits a design is graded against"
      >
        <VerdictCards snap={snap} go={go} />
      </Block>

      <Block title="The rungs" aside="a design is labelled with its rung, never “production-ready”">
        <Rungs />
      </Block>
    </div>
  );
}

/** The grid's one row before any design: every cell in words, every stage dashed and named. */
function Template() {
  return (
    <tr className="template">
      {BEFORE.map((c) => (
        <td key={c.id}>{c.template}</td>
      ))}
      {STAGES.map((s) => (
        <td key={s.id} className="stage-cell" title={`Not built yet: ${s.builds}`}>
          <span className="dsg-stage-words">
            <Dot status="blank" />
            <span>{s.template}</span>
          </span>
        </td>
      ))}
      {AFTER.map((c) => (
        <td key={c.id}>{c.template}</td>
      ))}
    </tr>
  );
}

function CampaignRows({
  snap,
  campaign,
  designs,
  focus,
  onOpen,
  onCampaign,
}: {
  snap: Snapshot;
  campaign: string;
  designs: Candidate[];
  focus: string | null;
  onOpen: (id: string) => void;
  onCampaign: () => void;
}) {
  const c = campaignById(snap, campaign);
  return (
    <>
      <tr className="dsg-campaign-row" data-click="true" onClick={onCampaign} title="Open the campaign">
        <td colSpan={SPAN}>
          <b className="mono">{campaign}</b>{" "}
          <span className="dim">
            {c ? `${ARM[c.arm].label} · ` : ""}
            {designs.length} designs
          </span>
        </td>
      </tr>
      {designs.map((d) => (
        <DesignRow key={d.id} snap={snap} design={d} focused={focus === d.id} onOpen={() => onOpen(d.id)} />
      ))}
    </>
  );
}

function DesignRow({
  snap,
  design,
  focused,
  onOpen,
}: {
  snap: Snapshot;
  design: Candidate;
  focused: boolean;
  onOpen: () => void;
}) {
  const episode = episodeById(snap, design.episode);
  return (
    <tr data-click="true" data-focus={focused} onClick={onOpen}>
      <td className="mono">{design.id}</td>
      <td>{episode ? <Clamp text={episode.claim} /> : <span className="dim">—</span>}</td>
      {STAGES.map((s) => {
        const st = stageState(snap, design, s.id);
        return (
          <td key={s.id} className="stage-cell" data-status={st.status} title={st.title}>
            <Dot status={st.status} />
            <span className="stage-cell-text">{st.text}</span>
          </td>
        );
      })}
      <td>
        <span className="dsg-verdict">
          <Verdict passed={design.passed} failure={design.failure} />
          {design.worst_margin !== null ? <span className="num">{pct(design.worst_margin)}</span> : null}
        </span>
      </td>
      <td className="num">{kg(design.mass_kg)}</td>
      <td>
        <RungPill rung={design.rung} />
      </td>
    </tr>
  );
}
