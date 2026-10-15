/**
 * Optimisation runs in 3D (PLT-10): what a topology optimisation froze, the material it placed and
 * its grey zone, with the contract's parts inside for scale, toggled and see-through as a design is
 * (PLT-9's stage). Beside them, the run's settings, its objective's history and its worst seat.
 *
 * The runs come from `prototypes/first_loop/topo_export.py`, one file per run in
 * `../records/optimisations/` (git ignores the folder; the runs live in data/). A run is a
 * hypothesis: its voxel model ranks, it never judges. The CAD drawn from it, meshed and solved, is
 * the judge.
 */

import { useEffect, useState } from "react";
import type { Part, StageAction, StageData } from "./DesignView";
import { PartsStage } from "./DesignView";

interface RunFile extends StageData {
  title: string;
  run: {
    objective: string | null;
    budget_kg: number | null;
    frozen_kg: number | null;
    placed_kg: number;
    grey_kg: number;
    voxel_mm: number;
    iterations: number;
    unknowns: number | null;
    seconds: number;
    element: string;
    factor: string;
    casting: string;
    worst_ratio: number | null;
    worst_seat: string | null;
    converged: boolean;
  };
  history: { it: number; objective: number; worst: number | null }[];
}

const FILES = import.meta.glob("../records/optimisations/*.json");
/** Each run's name (`prototypes/first_loop/names.py` writes `_index.json`): what was varied, its
 * mass, its method; the designs drawn from it carry the same name with "· CAD". Newest first. */
const INDEX_FILES = import.meta.glob("../records/optimisations/_index.json", { eager: true }) as Record<string, { default: Record<string, { title: string }> }>;
const INDEX: Record<string, { title: string }> = Object.values(INDEX_FILES)[0]?.default ?? {};
const order = (s: string) => {
  const i = Object.keys(INDEX).indexOf(s);
  return i < 0 ? Number.MAX_SAFE_INTEGER : i;
};
const STEMS = Object.keys(FILES)
  .map((p) => p.replace(/^.*\/(.*)\.json$/, "$1"))
  .filter((s) => !s.startsWith("_"))
  .sort((a, b) => order(a) - order(b) || a.localeCompare(b));

const GROUPS: [string, string][] = [
  ["frozen", "Frozen"],
  ["placed", "Material placed"],
  ["grey", "Grey zone"],
  ["gears", "Gears"],
  ["shafts", "Shafts"],
  ["bearings", "Bearings"],
  ["differential", "Differential"],
  ["motor", "Motor"],
];

const look = (shown: boolean, opacity = 100) => ({ shown, opacity });

const ACTIONS: StageAction[] = [
  { label: "See inside", pick: (p) => (p.group === "frozen" ? look(true, 25) : p.group === "grey" ? look(true, 35) : p.group === "motor" ? look(false) : look(true)) },
  { label: "Placed only", pick: (p) => look(p.group === "placed") },
  { label: "Solid", pick: (p) => (p.group === "motor" || p.group === "grey" ? look(false) : look(true)) },
];

const INITIAL = (p: Part) => (p.group === "frozen" ? look(true, 25) : p.group === "grey" || p.group === "motor" ? look(false) : look(true));

/** "intermediate +z case 1" -> "intermediate +z, reverse" (case 0 drives, case 1 reverses). */
function seatWords(seat: string | null): string {
  if (!seat) return "-";
  return seat.replace(/ case 0$/, ", peak drive").replace(/ case 1$/, ", peak reverse");
}

function title(stem: string): string {
  return INDEX[stem]?.title ?? stem.replace(/^topo_/, "").replace(/_/g, " ");
}

export function OptimisationView() {
  const [stem, setStem] = useState(STEMS[0] ?? "");
  const [data, setData] = useState<RunFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    if (!stem) return;
    setData(null);
    FILES[`../records/optimisations/${stem}.json`]()
      .then((m) => setData((m as { default: RunFile }).default))
      .catch((e: unknown) => setFailed(String(e)));
  }, [stem]);
  if (!STEMS.length) {
    return (
      <div className="vol-empty">
        No optimisation exported yet: run <span className="mono">prototypes/first_loop/topo_export.py</span>.
      </div>
    );
  }
  return (
    <div className="dv">
      <div className="dv-pick">
        {STEMS.map((s) => (
          <button key={s} type="button" className="dv-pick-b" data-on={s === stem} onClick={() => setStem(s)}>
            {title(s)}
          </button>
        ))}
      </div>
      {failed ? <div className="vol-empty">the run could not be read: {failed}</div> : null}
      {data ? (
        <PartsStage key={data.stem} data={data} groups={GROUPS} actions={ACTIONS} initial={INITIAL}>
          <RunFacts data={data} />
        </PartsStage>
      ) : (
        <div className="vol-empty">drawing the run…</div>
      )}
    </div>
  );
}

/** One run in 3D (LOP-21: a flow's optimisation step): what was frozen and what was placed. */
export function RunView({ stem }: { stem: string }) {
  const [data, setData] = useState<RunFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    setData(null);
    setFailed("");
    const load = FILES[`../records/optimisations/${stem}.json`];
    if (!load) {
      setFailed(`the run ${stem} is not exported (prototypes/first_loop/topo_export.py)`);
      return;
    }
    load()
      .then((m) => setData((m as { default: RunFile }).default))
      .catch((e: unknown) => setFailed(String(e)));
  }, [stem]);
  if (failed) return <div className="vol-empty">{failed}</div>;
  if (!data) return <div className="vol-empty">drawing the run…</div>;
  return (
    <PartsStage key={data.stem} data={data} groups={GROUPS} actions={ACTIONS} initial={INITIAL}>
      <RunFacts data={data} />
    </PartsStage>
  );
}

function RunFacts({ data }: { data: RunFile }) {
  const r = data.run;
  const against = r.factor.includes("against");
  const rows: [string, string][] = [
    ["objective", r.objective ?? "-"],
    ["mass", r.budget_kg !== null && r.frozen_kg !== null ? `${r.budget_kg} kg: ${r.frozen_kg.toFixed(2)} frozen, ${r.placed_kg.toFixed(2)} placed` : `${r.placed_kg.toFixed(2)} kg placed`],
    ["worst seat", r.worst_ratio !== null ? `${r.worst_ratio.toFixed(2)} × its line, ${seatWords(r.worst_seat)}` : "-"],
    ["iterations", `${r.iterations}${r.converged ? ", converged" : ", not converged"}`],
    ["voxels", `${r.voxel_mm} mm, ${r.unknowns ? r.unknowns.toLocaleString("en-GB") : "-"} unknowns, ${r.seconds} s`],
    ["element", r.element],
    ["casting", r.casting],
  ];
  return (
    <div className="dv-facts">
      <div className="dv-fact ov-title">{data.title}</div>
      {rows.map(([k, v]) => (
        <div key={k} className="dv-fact">
          <span>{k}</span>
          <span className="mono">{v}</span>
        </div>
      ))}
      <div className="dv-fact" data-warn={against}>
        <span>factor</span>
        <span className="mono">{r.factor}</span>
      </div>
      <History history={data.history} />
      <div className="dv-fact dim">The voxel model ranks; it never judges. The CAD drawn from it, meshed and solved, is the judge.</div>
    </div>
  );
}

/** The objective over the iterations, and the worst seat's ratio where the run logged it. */
function History({ history }: { history: RunFile["history"] }) {
  if (history.length < 2) return null;
  const w = 260;
  const h = 96;
  const pad = { l: 6, r: 6, t: 8, b: 16 };
  const last = history[history.length - 1].it;
  const x = (it: number) => pad.l + ((it - history[0].it) / Math.max(1, last - history[0].it)) * (w - pad.l - pad.r);
  const line = (vals: number[]) => {
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const y = (v: number) => pad.t + (hi === lo ? 0.5 : (hi - v) / (hi - lo)) * (h - pad.t - pad.b);
    return vals.map((v, i) => `${x(history[i].it).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  };
  const worst = history.every((e) => e.worst !== null) ? history.map((e) => e.worst as number) : null;
  return (
    <svg className="ov-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="the objective over the iterations">
      <rect x={pad.l} y={pad.t} width={w - pad.l - pad.r} height={h - pad.t - pad.b} className="cp-chart-frame" />
      <polyline points={line(history.map((e) => e.objective))} className="ov-line" />
      {worst ? <polyline points={line(worst)} className="ov-line ov-line-worst" /> : null}
      <text x={pad.l} y={h - 3} className="cp-chart-tick">
        1
      </text>
      <text x={w - pad.r} y={h - 3} textAnchor="end" className="cp-chart-tick">
        {last}
      </text>
      <text x={w / 2} y={h - 3} textAnchor="middle" className="cp-chart-tick">
        objective{worst ? " · worst seat (dashed)" : ""}, by iteration
      </text>
    </svg>
  );
}
