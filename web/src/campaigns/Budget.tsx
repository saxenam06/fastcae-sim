/**
 * Budget: what a campaign spent and what it bought - the FE proofs spent against the best
 * worst-margin reached so far, step by step, read from the trace and the designs. The dashed line
 * at zero is the verdict's own: a negative margin fails. With a campaign in view its budget is
 * drawn as the right-hand limit.
 *
 * Under the chart, each contract's budget as the contract sets it: the one thing on this page that
 * exists before any campaign, and the frame every campaign on that contract spends inside.
 */

import { STAGES, shortTitle } from "../app/product";
import type { TabProps } from "../app/tab";
import { Blank, Block, StageDots } from "../panel/bits";
import { Metric } from "../panel/cards";
import { CampaignHead } from "./Head";
import { bestOf, candidatesOf, course, inView, marginRange, pct, stepsOf } from "./records";

type Point = ReturnType<typeof course>[number];

export function BudgetPage(props: TabProps) {
  const { snap, route, go } = props;
  const { campaign } = inView(snap, route);
  const points = campaign ? course(snap, campaign.id) : [];
  const best = campaign ? bestOf(candidatesOf(snap, campaign.id)) : null;
  const margin = best?.worst_margin ?? null;
  return (
    <div className="stage-scroll cmp-page">
      <CampaignHead {...props} />

      <div className="metrics cmp-metrics">
        <Metric label="FE proofs spent" value={campaign ? campaign.spent_fe_proofs : null} />
        <Metric
          label="FE proofs left"
          value={campaign ? campaign.budget_fe_proofs - campaign.spent_fe_proofs : null}
        />
        <Metric label="steps" value={campaign ? stepsOf(snap, campaign.id).length : null} />
        <Metric
          label="best worst-margin"
          value={margin === null ? null : pct(margin)}
          tone={margin === null ? undefined : margin >= 0 ? "ok" : "bad"}
        />
      </div>

      <Block title="Proofs spent, and the best design so far">
        <figure className="cmp-chart">
          <Course points={points} budget={campaign?.budget_fe_proofs ?? null} />
          {points.length ? null : (
            <Blank title="Not built yet" waits="campaigns, and the FE proofs they spend (AGT-1, PHY-1)" />
          )}
        </figure>
      </Block>

      <Block title="Each contract's budget" count={snap.contracts.length} aside="what one campaign on it may spend">
        <div className="tbl-wrap cmp-budgets">
          <table className="tbl">
            <thead>
              <tr>
                <th>Contract</th>
                <th>Stage</th>
                <th className="num">FE proofs</th>
                <th className="num">Hours</th>
              </tr>
            </thead>
            <tbody>
              {snap.contracts.map((c) => (
                <tr
                  key={c.id}
                  data-click="true"
                  onClick={() => go({ view: "contracts", id: c.id })}
                  title={`${c.title} - open the contract`}
                >
                  <td>{shortTitle(c.title)}</td>
                  <td title={STAGES.find((s) => s.id === c.stage)?.words}>
                    <StageDots stage={c.stage} /> <span className="dim">{c.stage}</span>
                  </td>
                  <td className="num">{c.budget_fe_proofs}</td>
                  <td className="num">{c.budget_hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Block>
    </div>
  );
}

const W = 560;
const H = 250;
const LEFT = 56;
const RIGHT = 18;
const TOP = 16;
const BOTTOM = 40;
const AXIS = { stroke: "currentColor", strokeOpacity: 0.35 } as const;
const LABEL = { fontSize: 10, fill: "currentColor" } as const;

/**
 * The chart: proofs spent along, the best worst-margin up. The best so far only changes when a
 * better design arrives, so it is drawn as steps, never as a slope between two readings. Empty, it
 * is the frame and the pass line; it never draws a point the records do not hold.
 */
function Course({ points, budget }: { points: Point[]; budget: number | null }) {
  const judged = points.filter((p): p is Point & { best: number } => p.best !== null);
  const xMax = Math.max(budget ?? 0, ...points.map((p) => p.proofs), 1);
  const [lo, hi] = marginRange(judged.map((p) => p.best));
  const x = (proofs: number) => LEFT + (proofs / xMax) * (W - LEFT - RIGHT);
  // Before any point the scale has nothing to say; the pass line sits where the frame puts it.
  const y = (m: number) =>
    judged.length ? TOP + ((hi - m) / (hi - lo)) * (H - TOP - BOTTOM) : TOP + 0.42 * (H - TOP - BOTTOM);
  const at = (p: Point & { best: number }) => [x(p.proofs).toFixed(1), y(p.best).toFixed(1)];
  const path = judged
    .map((p, i) => {
      const [px, py] = at(p);
      return i ? `H${px} V${py}` : `M${px},${py}`;
    })
    .join(" ");
  const midY = (TOP + H - BOTTOM) / 2;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="FE proofs spent against the best worst-margin so far">
      <line x1={LEFT} y1={H - BOTTOM} x2={W - RIGHT} y2={H - BOTTOM} {...AXIS} />
      <line x1={LEFT} y1={TOP} x2={LEFT} y2={H - BOTTOM} {...AXIS} />
      <line x1={LEFT} y1={y(0)} x2={W - RIGHT} y2={y(0)} {...AXIS} strokeOpacity={0.55} strokeDasharray="4 3" />
      <text x={LEFT - 6} y={y(0) + 3} textAnchor="end" {...LABEL}>
        0 %
      </text>
      <text x={W - RIGHT} y={y(0) - 5} textAnchor="end" {...LABEL}>
        pass
      </text>
      <text x={(LEFT + W - RIGHT) / 2} y={H - 10} textAnchor="middle" {...LABEL} fontSize={10.5}>
        FE proofs spent
      </text>
      <text x={14} y={midY} textAnchor="middle" transform={`rotate(-90 14 ${midY})`} {...LABEL} fontSize={10.5}>
        best worst-margin
      </text>
      {judged.length ? (
        <>
          <text x={LEFT} y={H - BOTTOM + 14} {...LABEL}>
            0
          </text>
          <text x={W - RIGHT} y={H - BOTTOM + 14} textAnchor="end" {...LABEL}>
            {xMax}
          </text>
          <text x={LEFT - 6} y={y(hi) + 3} textAnchor="end" {...LABEL}>
            {pct(hi)}
          </text>
          <text x={LEFT - 6} y={y(lo) + 3} textAnchor="end" {...LABEL}>
            {pct(lo)}
          </text>
        </>
      ) : null}
      {budget !== null ? (
        <g>
          <line
            x1={x(budget)}
            y1={TOP}
            x2={x(budget)}
            y2={H - BOTTOM}
            {...AXIS}
            strokeOpacity={0.55}
            strokeDasharray="2 3"
          />
          <text x={x(budget) - 4} y={TOP + 10} textAnchor="end" {...LABEL}>
            budget · {budget}
          </text>
        </g>
      ) : null}
      {path ? <path d={path} fill="none" stroke="var(--blue)" strokeWidth="1.5" /> : null}
      {judged.map((p) => (
        <circle
          key={p.step}
          cx={x(p.proofs)}
          cy={y(p.best)}
          r="3.5"
          fill={p.best >= 0 ? "var(--measured)" : "var(--conflict)"}
        >
          <title>{`step ${p.step}: ${p.proofs} proofs, best ${pct(p.best)}`}</title>
        </circle>
      ))}
    </svg>
  );
}
