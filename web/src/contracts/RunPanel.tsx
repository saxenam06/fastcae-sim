/**
 * The Run button (PLT-5; the engineer, 15 October: "I already need a run button on the UI on the
 * contract page"). It asks the API (`zenryx.api.server`, port 8030, proxied as /api) to run the final
 * workflow on this contract: the optimisation (on RunPod or here, the API's setting), the drawing,
 * FE, castability and the grade. While a run goes, its stages, time and log's last lines show here;
 * when it ends, its verdict and a link to the new design on the Designs tab.
 *
 * Nothing is shown that the API did not say: with no API running, the panel says how to start it.
 */

import { useCallback, useEffect, useState } from "react";

type Last = {
  design: string;
  verdict: string;
  time: string;
  version: number;
  numbers: {
    mass_kg: number | null;
    worst_seat_um: number | null;
    tilt: number | null;
    first_mode_hz: number | null;
    clashes: string[] | null;
  };
};
type Workflow = {
  recipe: { name: string; version: number };
  last: Last | null;
  changed: { contract: boolean; recipe: boolean };
  running: string | null;
};
type Stage = { stage: string; started: string; ended?: string };
type Run = {
  id: string;
  design: string;
  status: "running" | "done" | "failed" | "cancelled";
  started: string;
  ended?: string;
  stage: string | null;
  stages: Stage[];
  stages_all: string[];
  log: string[];
  error?: string;
  result?: Last;
};

const LABEL: Record<string, string> = {
  layout: "Layout",
  optimise: "Optimisation",
  draw: "Drawing",
  oiltight: "Oil-tight",
  judge: "FE · castability",
  grade: "Grade",
  records: "Records",
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, init);
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 300)}`);
  return (await r.json()) as T;
}

function minutes(from: string, to?: string): string {
  const ms = (to ? Date.parse(to) : Date.now()) - Date.parse(from);
  return `${Math.max(0, ms / 60000).toFixed(1)} min`;
}

export function RunPanel() {
  const [wf, setWf] = useState<Workflow | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [down, setDown] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const w = await api<Workflow>("/workflow");
      setWf(w);
      setDown(false);
      const id = w.running ?? run?.id;
      if (id) setRun(await api<Run>(`/runs/${id}`));
    } catch {
      setDown(true);
    }
  }, [run?.id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const going = run?.status === "running";
  useEffect(() => {
    if (!going) return;
    const t = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(t);
  }, [going, refresh]);

  const start = async () => {
    setError("");
    try {
      setRun(await api<Run>("/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }));
      void refresh();
    } catch (e) {
      setError(String(e));
    }
  };
  const cancel = async () => {
    if (!run) return;
    try {
      await api(`/runs/${run.id}/cancel`, { method: "POST" });
      void refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  if (down) {
    return (
      <div className="run-panel" data-state="down">
        <p>
          The API is not running. Start it on this machine, then reload:{" "}
          <code>.venv/Scripts/python.exe prototypes/first_loop/serve.py</code>
        </p>
      </div>
    );
  }
  if (!wf) return <div className="run-panel vol-empty">Asking the API…</div>;

  const shown = going ? run : null;
  const last = wf.last;
  const changed = wf.changed.contract || wf.changed.recipe;
  return (
    <div className="run-panel" data-state={going ? "running" : "idle"}>
      <div className="run-head">
        <div>
          <div className="run-recipe">
            recipe <b>{wf.recipe.name}</b> v{wf.recipe.version}
          </div>
          {changed ? (
            <span className="cp-badge" data-tone="next">
              {wf.last ? "the contract or the recipe changed since the last run" : "never run"}
            </span>
          ) : (
            <span className="cp-badge" data-ok>
              up to date with the last run
            </span>
          )}
        </div>
        <div className="run-actions">
          {going ? (
            <button type="button" className="run-btn" data-kind="cancel" onClick={() => void cancel()}>
              Cancel
            </button>
          ) : (
            <button type="button" className="run-btn" onClick={() => void start()}>
              Run the final workflow
            </button>
          )}
        </div>
      </div>

      {shown ? (
        <div className="run-live">
          <ol className="run-stages">
            {shown.stages_all.map((s) => {
              const st = shown.stages.find((x) => x.stage === s);
              const state = !st ? "todo" : shown.stage === s ? "now" : "done";
              return (
                <li key={s} data-state={state}>
                  <i />
                  {LABEL[s] ?? s}
                  {st ? <span className="mono">{minutes(st.started, st.ended)}</span> : null}
                </li>
              );
            })}
          </ol>
          <div className="run-meta mono">
            {shown.design} · {minutes(shown.started)} so far
          </div>
          {shown.log.length ? <pre className="run-log">{shown.log.slice(-8).join("\n")}</pre> : null}
        </div>
      ) : null}

      {run && !going && run.status !== "done" ? (
        <p className="run-error">
          The last run {run.status}
          {run.error ? `: ${run.error}` : ""}
        </p>
      ) : null}
      {error ? <p className="run-error">{error}</p> : null}

      {last && !going ? (
        <div className="run-last">
          <div>
            <div className="run-label">last design</div>
            <a href={`#/designs/${last.design}`} className="mono">
              {last.design}
            </a>
            <div className="run-when">{last.time}</div>
          </div>
          <div>
            <div className="run-label">verdict</div>
            <div data-pass={last.verdict === "passes every line"}>{last.verdict}</div>
          </div>
          <Num label="mass" v={last.numbers.mass_kg} unit="kg" digits={2} />
          <Num label="worst seat" v={last.numbers.worst_seat_um} unit="µm" digits={1} />
          <Num label="tilt" v={last.numbers.tilt} unit="× line" digits={2} />
          <Num label="first mode" v={last.numbers.first_mode_hz} unit="Hz" digits={0} />
        </div>
      ) : null}
    </div>
  );
}

function Num({ label, v, unit, digits }: { label: string; v: number | null; unit: string; digits: number }) {
  return (
    <div>
      <div className="run-label">{label}</div>
      <div className="mono">{v === null || v === undefined ? "-" : `${v.toFixed(digits)} ${unit}`}</div>
    </div>
  );
}
