/**
 * Trade-off: every graded design as a point, mass along and the worst margin up, in the style of
 * fastcae's TradeOff. The contract's objective is least mass among passing designs, so the designs
 * worth looking at sit above the dashed zero-margin line and as far left as they go. A click on a
 * point opens the design.
 *
 * Empty, it is the frame and the pass line; it never draws a point the records do not hold. A
 * design's mass is always computed, its margin always the judge's.
 */

import type { TabProps } from "../app/tab";
import { Blank, Block } from "../panel/bits";
import type { Candidate } from "../records/types";
import { kg, marginRange, pct } from "../campaigns/records";
import { DesignsHead } from "./bits";

type Graded = Candidate & { mass_kg: number; worst_margin: number };

export function TradeOffPage({ snap, route, go }: TabProps) {
  const graded = snap.records.candidates.filter(
    (d): d is Graded => d.mass_kg !== null && d.worst_margin !== null,
  );
  return (
    <div className="stage-scroll dsg-page">
      <DesignsHead snap={snap} />
      <Block title="Mass against the worst margin" count={graded.length} aside="lighter is left, more margin is up">
        <figure className="dsg-chart">
          <Scatter designs={graded} focus={route.id} onOpen={(id) => go({ id })} />
        </figure>
      </Block>
      {snap.records.candidates.length === 0 ? (
        <Blank title="Not built yet" waits="designs and their grades (GEO-1, PHY-1)" />
      ) : null}
    </div>
  );
}

const W = 560;
const H = 300;
const LEFT = 56;
const RIGHT = 18;
const TOP = 16;
const BOTTOM = 42;
const AXIS = { stroke: "currentColor", strokeOpacity: 0.35 } as const;
const LABEL = { fontSize: 10, fill: "currentColor" } as const;

function Scatter({
  designs,
  focus,
  onOpen,
}: {
  designs: Graded[];
  focus: string | null;
  onOpen: (id: string) => void;
}) {
  const masses = designs.map((d) => d.mass_kg);
  const kgLo = designs.length ? Math.min(...masses) * 0.95 : 0;
  const kgHi = designs.length ? Math.max(...masses) * 1.05 : 1;
  const [lo, hi] = marginRange(designs.map((d) => d.worst_margin));
  const x = (m: number) => LEFT + ((m - kgLo) / Math.max(kgHi - kgLo, 1e-9)) * (W - LEFT - RIGHT);
  // Before any point the scale has nothing to say; the pass line sits where the frame puts it.
  const y = (s: number) =>
    designs.length ? TOP + ((hi - s) / (hi - lo)) * (H - TOP - BOTTOM) : TOP + 0.45 * (H - TOP - BOTTOM);
  const midY = (TOP + H - BOTTOM) / 2;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Mass against the worst margin, a point a design">
      <line x1={LEFT} y1={H - BOTTOM} x2={W - RIGHT} y2={H - BOTTOM} {...AXIS} />
      <line x1={LEFT} y1={TOP} x2={LEFT} y2={H - BOTTOM} {...AXIS} />
      <line x1={LEFT} y1={y(0)} x2={W - RIGHT} y2={y(0)} {...AXIS} strokeOpacity={0.55} strokeDasharray="4 3" />
      <text x={LEFT - 6} y={y(0) + 3} textAnchor="end" {...LABEL}>
        0 %
      </text>
      <text x={W - RIGHT} y={y(0) - 5} textAnchor="end" fontWeight="600" {...LABEL} fontSize={10.5}>
        pass
      </text>
      <text x={(LEFT + W - RIGHT) / 2} y={H - 10} textAnchor="middle" {...LABEL} fontSize={10.5}>
        mass (kg)
      </text>
      <text x={14} y={midY} textAnchor="middle" transform={`rotate(-90 14 ${midY})`} {...LABEL} fontSize={10.5}>
        worst margin (%)
      </text>
      {designs.length ? (
        <>
          <text x={LEFT} y={H - BOTTOM + 14} {...LABEL}>
            {kgLo.toFixed(1)}
          </text>
          <text x={W - RIGHT} y={H - BOTTOM + 14} textAnchor="end" {...LABEL}>
            {kgHi.toFixed(1)}
          </text>
          <text x={LEFT - 6} y={y(hi) + 3} textAnchor="end" {...LABEL}>
            {pct(hi)}
          </text>
          <text x={LEFT - 6} y={y(lo) + 3} textAnchor="end" {...LABEL}>
            {pct(lo)}
          </text>
        </>
      ) : null}
      {designs.map((d) => {
        const px = x(d.mass_kg);
        const py = y(d.worst_margin);
        // Named on the side with room: left of a point near the right edge.
        const right = px > 0.6 * W;
        return (
          <g
            key={d.id}
            className="dsg-point"
            data-pass={d.worst_margin >= 0}
            data-focus={focus === d.id}
            onClick={() => onOpen(d.id)}
          >
            <circle cx={px} cy={py} r="5" />
            <text x={px + (right ? -8 : 8)} y={py + 4} textAnchor={right ? "end" : "start"} {...LABEL} fontSize={10.5}>
              {d.id}
            </text>
            <title>{`${d.id}: ${kg(d.mass_kg)}, worst margin ${pct(d.worst_margin)}`}</title>
          </g>
        );
      })}
    </svg>
  );
}
