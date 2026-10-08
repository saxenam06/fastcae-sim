/**
 * Designs: every housing a campaign makes, how far it got, and how it graded.
 *
 * A design passes through its stages in order: the machined core, the grown structure, the join,
 * castability, the mesh, statics, modes, and the verdict. Each design is a row with a dot per
 * stage, its mass, its grade and its rung. The design to beat (the published housing) sits on top,
 * and the chart puts every design against it: mass across, the worst margin up.
 *
 * Nothing is made yet: geometry (GEO-1) and the judge (PHY-1) are not built. The published
 * design's mass is real, so it is drawn; the rest is the frame. The first version is archived
 * in `archive/web/designs-v1/`.
 */

import { shortTitle } from "../app/product";
import type { Tab, TabProps } from "../app/tab";
import { Dot } from "../panel/bits";
import { Badge, PageHead, Section } from "../panel/page";
import { RUNG, RUNG_ORDER, STAGES } from "../words/stages";

function Stage({ snap }: TabProps) {
  const contract = snap.contracts[0];
  if (!contract) return <div className="stage-scroll" />;
  const campaigns = new Set(snap.records.campaigns.filter((c) => c.contract === contract.id).map((c) => c.id));
  const designs = snap.records.candidates.filter((d) => campaigns.has(d.campaign));
  const beat = contract.page.to_beat;
  const mass = parseMass(beat.find((b) => b.quantity.includes("mass"))?.value ?? "");
  const rungs = RUNG_ORDER.filter((r) => r !== "none");
  return (
    <div className="stage-scroll cp-scroll">
      <div className="cp-page">
        <PageHead
          kicker="Designs"
          title={shortTitle(contract.title)}
          sub="Every housing a campaign makes: its stages, its grade, its rung"
          side={
            <div className="cp-badges">
              <Badge>{designs.length === 1 ? "1 design" : `${designs.length} designs`}</Badge>
              <Badge tone="wait">Needs geometry (GEO-1) and the judge (PHY-1)</Badge>
            </div>
          }
        />

        <Section title="The design to beat" aside="published">
          <div className="cp-beat cp-beat-row">
            {beat.map((b) => (
              <div key={b.quantity} className="cp-beat-item" data-warn={b.note !== ""}>
                <div className="cp-beat-q">{b.quantity}</div>
                <div className="cp-beat-v mono">{b.value}</div>
                {b.note ? <div className="cp-beat-note">⚠ {b.note}</div> : null}
                <span className="prov" data-prov="published" title={b.title}>
                  {b.source}
                </span>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Designs" aside={designs.length ? `${designs.length}` : "none yet"}>
          <table className="cp-table cp-designs">
            <thead>
              <tr>
                <th>Design</th>
                {STAGES.map((s) => (
                  <th key={s.id} title={`${s.words} (${s.builds})`}>
                    {s.label}
                  </th>
                ))}
                <th>Verdict</th>
                <th>Mass</th>
                <th>Rung</th>
              </tr>
            </thead>
            <tbody>
              {designs.length ? (
                designs.map((d) => (
                  <tr key={d.id}>
                    <td className="mono">{d.id}</td>
                    {STAGES.map((s) => (
                      <td key={s.id}>
                        <Dot status={d.failure ? "failed" : "done"} />
                      </td>
                    ))}
                    <td>{d.passed === null ? "-" : d.passed ? "pass" : "fail"}</td>
                    <td className="mono">{d.mass_kg === null ? "-" : `${d.mass_kg.toFixed(2)} kg`}</td>
                    <td>{RUNG[d.rung].label}</td>
                  </tr>
                ))
              ) : (
                <tr className="cp-template">
                  <td>each design, by its step</td>
                  {STAGES.map((s) => (
                    <td key={s.id} title={s.template}>
                      <Dot status="blank" />
                    </td>
                  ))}
                  <td>pass or fail</td>
                  <td>kg</td>
                  <td>its rung</td>
                </tr>
              )}
            </tbody>
          </table>
        </Section>

        <div className="cp-pair">
          <Section title="Mass against margin">
            <div className="cp-card">
              <Chart mass={mass} />
            </div>
          </Section>
          <Section title="Rungs" aside="a design is labelled with its rung">
            <div className="cp-card">
              <ol className="cp-rungs">
                {rungs.map((r) => (
                  <li key={r} title={`${RUNG[r].needs} · signed by ${RUNG[r].signs}`} data-own={RUNG[r].own}>
                    {RUNG[r].label}
                  </li>
                ))}
              </ol>
              <p className="dim cp-rungs-note">The first two the platform reaches on its own; the rest need partners.</p>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}

/** "7.732 kg" to 7.732; null if no mass is published. */
function parseMass(text: string): number | null {
  const found = /(\d+(?:\.\d+)?)\s*kg/.exec(text);
  return found ? Number(found[1]) : null;
}

/**
 * The frame every design will sit in: mass across (0-10 kg), the worst margin up (-50 % to 50 %).
 * The pass line is at a margin of zero, and the published design's mass is a line to come in under.
 */
function Chart({ mass }: { mass: number | null }) {
  const w = 460;
  const h = 230;
  const pad = { l: 46, r: 14, t: 12, b: 34 };
  const x = (kg: number) => pad.l + (kg / 10) * (w - pad.l - pad.r);
  const y = (pct: number) => pad.t + ((50 - pct) / 100) * (h - pad.t - pad.b);
  return (
    <svg className="cp-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="mass against margin">
      <rect x={pad.l} y={pad.t} width={w - pad.l - pad.r} height={h - pad.t - pad.b} className="cp-chart-frame" />
      {[0, 2, 4, 6, 8, 10].map((kg) => (
        <text key={kg} x={x(kg)} y={h - pad.b + 14} textAnchor="middle" className="cp-chart-tick">
          {kg}
        </text>
      ))}
      {[-50, 0, 50].map((p) => (
        <text key={p} x={pad.l - 6} y={y(p) + 3} textAnchor="end" className="cp-chart-tick">
          {p}
        </text>
      ))}
      <line x1={pad.l} x2={w - pad.r} y1={y(0)} y2={y(0)} className="cp-chart-pass" />
      <text x={w - pad.r - 4} y={y(0) - 5} textAnchor="end" className="cp-chart-label">
        pass
      </text>
      {mass !== null ? (
        <>
          <line x1={x(mass)} x2={x(mass)} y1={pad.t} y2={h - pad.b} className="cp-chart-beat" />
          <text x={x(mass) - 5} y={pad.t + 12} textAnchor="end" className="cp-chart-label cp-chart-beat-label">
            to beat: {mass} kg
          </text>
        </>
      ) : null}
      <text x={(pad.l + w - pad.r) / 2} y={h - 4} textAnchor="middle" className="cp-chart-axis">
        mass (kg)
      </text>
      <text x={12} y={(pad.t + h - pad.b) / 2} textAnchor="middle" className="cp-chart-axis" transform={`rotate(-90 12 ${(pad.t + h - pad.b) / 2})`}>
        worst margin (%)
      </text>
    </svg>
  );
}

export const designsTab: Tab = { Stage, cardName: "" };
