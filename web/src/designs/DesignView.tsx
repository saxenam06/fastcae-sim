/**
 * A design in 3D (PLT-9): both halves of the housing and every part inside, each solid in its
 * own colour, each with a show/hide toggle and an opacity slider. A part below full opacity is
 * drawn see-through, so with the housing at 20 % the gears, shafts, bearings and the
 * differential's case show working inside it.
 *
 * The designs come from `prototypes/first_loop/view_export.py`, one file per design in
 * `../records/designs/` (git ignores the folder; the designs live in data/). Each file holds one
 * mesh whose face id is the part's index, the parts' names and colours, the design's recipe, its
 * mass, its castability and its grade. The renderer is the Contract page's (fastcae's WebGL2,
 * PLT-8): parts at full opacity are painted on the one mesh; parts below it are hidden there and
 * drawn as ghosts, each from its own share of the mesh.
 *
 * Camera: drag to turn, shift-drag or the middle button to pan, the wheel to zoom.
 */

import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Ghost } from "../render/renderer";
import { Renderer } from "../render/renderer";
import type { Mesh } from "../render/mesh";
import { meshFromBase64 } from "../render/mesh";
import { SectionControl, useSection } from "../render/Section";
import { outlineOf, planeOf } from "../render/sectionPlane";

export interface Part {
  id: string;
  label: string;
  kind: string;
  group: string;
  colour: [number, number, number];
}

/** What the stage draws: one mesh whose face id is the part's index, and the parts. */
export interface StageData {
  stem: string;
  parts: Part[];
  mesh: string;
  bbox: number[];
  faces: number;
}

interface DesignFile extends StageData {
  recipe: Record<string, unknown> | null;
  mass_kg: { motor_side: number; cover: number; total: number };
  castable: { half: string; undercut_cm2: number; closed_voids: number; thin_cm2: number }[] | null;
  /** Graded in peak drive alone (the engineer's one load case). */
  grade: { drive_um: number; misalignment: number; first_mode_hz: number | null; clashes: string[] } | null;
}

export interface Look {
  shown: boolean;
  opacity: number; // 0-100
}

/** A button over the parts: each part's look, or null to leave it as it is. */
export interface StageAction {
  label: string;
  pick: (p: Part) => Look | null;
}

const FILES = import.meta.glob("../records/designs/*.json");

/** Each design's name and kind (`prototypes/first_loop/names.py` writes `_index.json`): a design
 * drawn from an optimisation run carries the run's name with "· CAD", as the Optimisation tab
 * names the run; one from the generator is parametric. Newest first. */
interface DesignEntry {
  title: string;
  source: "optimisation" | "parametric";
  run: string | null;
  summary?: Summary | null;
}

/** A design's comparison row (`names.py`'s `summary_of`, LOP-20): what the optimiser was given
 * (its budget, the set-up's fixed metal and what it placed), the drawn CAD's mass, FE's bearing
 * beds, worst tilt and first mode with the grade's verdicts, and castability. */
interface Summary {
  cad_kg?: number | null;
  budget_kg?: number | null;
  fixed_kg?: number | null;
  placed_kg?: number | null;
  drive_um?: number;
  tilt?: number;
  mode_hz?: number | null;
  clashes?: number;
  castable?: boolean;
  undercut?: number;
  passes?: { beds: boolean; tilt: boolean; mode: boolean; mass: boolean };
  to_beat?: { kg: number; drive_um: number };
}
const INDEX_FILES = import.meta.glob("../records/designs/_index.json", { eager: true }) as Record<string, { default: Record<string, DesignEntry> }>;
const INDEX: Record<string, DesignEntry> = Object.values(INDEX_FILES)[0]?.default ?? {};

const ALL = Object.keys(FILES)
  .map((p) => p.replace(/^.*\/(.*)\.json$/, "$1"))
  .filter((s) => !s.startsWith("_"));
const order = (s: string) => {
  const i = Object.keys(INDEX).indexOf(s);
  return i < 0 ? Number.MAX_SAFE_INTEGER : i;
};
const STEMS = ALL.sort((a, b) => order(a) - order(b) || a.localeCompare(b));
const kindOf = (s: string): DesignEntry["source"] => INDEX[s]?.source ?? (s.startsWith("outcome_") ? "optimisation" : "parametric");
const nameOf = (s: string) => INDEX[s]?.title ?? s.replace(/^style_/, "");

const KINDS: { id: DesignEntry["source"]; label: string; hint: string }[] = [
  { id: "optimisation", label: "From topology optimisation", hint: "a run's field drawn as organic CAD; named after its run" },
  { id: "parametric", label: "Parametric", hint: "the generator's recipes: the style presets and grammar4" },
];

const GROUPS: [string, string][] = [
  ["housing", "Housing"],
  ["gears", "Gears"],
  ["shafts", "Shafts"],
  ["bearings", "Bearings"],
  ["differential", "Differential"],
  ["motor", "Motor"],
];

export function DesignView() {
  const [kind, setKind] = useState<DesignEntry["source"]>(STEMS.some((s) => kindOf(s) === "optimisation") ? "optimisation" : "parametric");
  const [stem, setStem] = useState(STEMS.find((s) => kindOf(s) === kind) ?? STEMS[0] ?? "");
  const pick = (k: DesignEntry["source"]) => {
    setKind(k);
    const first = STEMS.find((s) => kindOf(s) === k);
    if (first) setStem(first);
  };
  const [data, setData] = useState<DesignFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    if (!stem) return;
    setData(null);
    const load = FILES[`../records/designs/${stem}.json`];
    load()
      .then((m) => setData((m as { default: DesignFile }).default))
      .catch((e: unknown) => setFailed(String(e)));
  }, [stem]);
  if (!STEMS.length) {
    return (
      <div className="vol-empty">
        No design exported yet: run <span className="mono">prototypes/first_loop/view_export.py &lt;stem&gt;</span>.
      </div>
    );
  }
  return (
    <div className="dv">
      <div className="dv-kinds">
        {KINDS.map((k) => (
          <button key={k.id} type="button" className="dv-kind" data-on={k.id === kind} title={k.hint} onClick={() => pick(k.id)}>
            {k.label} <span className="dv-kind-n mono">{STEMS.filter((s) => kindOf(s) === k.id).length}</span>
          </button>
        ))}
      </div>
      <Compare stems={STEMS.filter((s) => kindOf(s) === kind)} stem={stem} pick={setStem} />
      <div className="dv-pick">
        {STEMS.filter((s) => kindOf(s) === kind).map((s) => (
          <button key={s} type="button" className="dv-pick-b" data-on={s === stem} title={s} onClick={() => setStem(s)}>
            {nameOf(s)}
          </button>
        ))}
      </div>
      {failed ? <div className="vol-empty">the design could not be read: {failed}</div> : null}
      {data ? <DesignStage key={data.stem} data={data} /> : <div className="vol-empty">drawing the design…</div>}
    </div>
  );
}

/** One design in 3D (LOP-21: a flow's body, machined and castability steps), by its stem. */
export function DesignMesh({ stem }: { stem: string }) {
  const [data, setData] = useState<DesignFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    setData(null);
    setFailed("");
    const load = FILES[`../records/designs/${stem}.json`];
    if (!load) {
      setFailed(`the design ${stem} is not exported (prototypes/first_loop/view_export.py)`);
      return;
    }
    load()
      .then((m) => setData((m as { default: DesignFile }).default))
      .catch((e: unknown) => setFailed(String(e)));
  }, [stem]);
  if (failed) return <div className="vol-empty">{failed}</div>;
  return data ? <DesignStage key={data.stem} data={data} /> : <div className="vol-empty">drawing the design…</div>;
}

/** The optimisation designs side by side (LOP-20; the engineer, 10 October 19:33: "how much
 * weight the optimisation gets, and compare that with the previous iteration on the UI"): what
 * the optimiser was given and placed, what the drawing weighs, FE's verdicts. A row opens its
 * design; the reference housing closes the table. */
function Compare({ stems, stem, pick }: { stems: string[]; stem: string; pick: (s: string) => void }) {
  const rows = stems.filter((s) => INDEX[s]?.summary);
  if (!rows.length) return null;
  const ref = rows.map((s) => INDEX[s].summary?.to_beat).find(Boolean);
  const kg = (v?: number | null) => (v == null ? "-" : v.toFixed(2));
  const mark = (ok?: boolean) => (ok == null ? undefined : ok ? "pass" : "fail");
  return (
    <div className="dv-compare">
      <table className="cp-table">
        <thead>
          <tr>
            <th>Design</th>
            <th>
              Optimiser's budget, <span className="dv-unit">kg</span>
            </th>
            <th>
              Drawn, <span className="dv-unit">kg</span>
            </th>
            <th>
              Bearing beds, peak drive, <span className="dv-unit">µm</span>
            </th>
            <th>Worst tilt, peak drive</th>
            <th>First mode</th>
            <th>Castable</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => {
            const r = INDEX[s].summary as Summary;
            return (
              <tr key={s} data-on={s === stem} onClick={() => pick(s)}>
                <th title={s}>{nameOf(s)}</th>
                <td className="mono">{r.budget_kg == null ? "-" : `${kg(r.budget_kg)}: ${kg(r.fixed_kg)} fixed, ${kg(r.placed_kg)} placed`}</td>
                <td className="mono" data-mark={mark(r.passes?.mass)}>{kg(r.cad_kg)}</td>
                <td className="mono" data-mark={mark(r.passes?.beds)} title="the worst bearing seat's displacement in peak drive">
                  {r.drive_um == null ? "-" : r.drive_um.toFixed(0)}
                </td>
                <td className="mono" data-mark={mark(r.passes?.tilt)} title="the worst seat's tilt over its line in peak drive">
                  {r.tilt == null ? "-" : `${r.tilt.toFixed(2)} ×`}
                </td>
                <td className="mono" data-mark={mark(r.passes?.mode)}>
                  {r.mode_hz ? `${r.mode_hz.toFixed(0)} Hz` + (r.clashes ? `, ${r.clashes} clash${r.clashes > 1 ? "es" : ""}` : "") : "-"}
                </td>
                <td className="mono" data-mark={mark(r.castable)}>
                  {r.castable == null ? "-" : r.castable ? "yes" : `no, undercut ${(100 * (r.undercut ?? 0)).toFixed(1)} %`}
                </td>
              </tr>
            );
          })}
          {ref ? (
            <tr className="dv-compare-ref">
              <th>The reference housing</th>
              <td className="mono">-</td>
              <td className="mono">{ref.kg.toFixed(2)}</td>
              <td className="mono">{ref.drive_um.toFixed(0)}</td>
              <td className="mono">-</td>
              <td className="mono">-</td>
              <td className="mono">-</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

/** One part's share of the mesh, for drawing it see-through on its own. */
function subMesh(mesh: Mesh, id: number): Mesh {
  const map = new Int32Array(mesh.vertexCount).fill(-1);
  const indices: number[] = [];
  let count = 0;
  for (let t = 0; t < mesh.indexCount; t += 3) {
    if (mesh.faceIds[mesh.indices[t]] !== id) continue;
    for (let k = 0; k < 3; k++) {
      const v = mesh.indices[t + k];
      if (map[v] < 0) map[v] = count++;
      indices.push(map[v]);
    }
  }
  const positions = new Float32Array(count * 3);
  const normals = new Int8Array(count * 4);
  const faceIds = new Uint32Array(count).fill(id);
  for (let v = 0; v < mesh.vertexCount; v++) {
    const m = map[v];
    if (m < 0) continue;
    positions.set(mesh.positions.subarray(3 * v, 3 * v + 3), 3 * m);
    normals.set(mesh.normals.subarray(4 * v, 4 * v + 4), 4 * m);
  }
  return { positions, normals, faceIds, indices: Uint32Array.from(indices), vertexCount: count, indexCount: indices.length };
}

const DESIGN_ACTIONS: StageAction[] = [
  { label: "See inside", pick: (p) => (p.group === "housing" ? { shown: true, opacity: 20 } : p.group === "motor" ? null : { shown: true, opacity: 100 }) },
  { label: "Solid", pick: (p) => (p.group === "motor" ? null : { shown: true, opacity: 100 }) },
  { label: "Parts only", pick: (p) => (p.group === "housing" ? { shown: false, opacity: 100 } : p.group === "motor" ? null : { shown: true, opacity: 100 }) },
];

function DesignStage({ data }: { data: DesignFile }) {
  return (
    <PartsStage data={data} groups={GROUPS} actions={DESIGN_ACTIONS} initial={(p) => ({ shown: p.group !== "motor", opacity: 100 })}>
      <Facts data={data} />
    </PartsStage>
  );
}

/**
 * Parts in 3D: the stage, then the parts in their groups, each a toggle swatch and an opacity
 * slider, the buttons over them, and what the caller puts below (the facts).
 */
export function PartsStage({
  data,
  groups,
  actions,
  initial,
  children,
}: {
  data: StageData;
  groups: [string, string][];
  actions: StageAction[];
  initial: (p: Part) => Look;
  children?: ReactNode;
}) {
  const mesh = useMemo(() => meshFromBase64(data.mesh), [data]);
  const subs = useMemo(() => data.parts.map((_, i) => subMesh(mesh, i)), [mesh, data]);
  const [looks, setLooks] = useState<Look[]>(() => data.parts.map(initial));

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const dirtyRef = useRef(true);
  // The cut section every 3D view shares (render/Section.tsx, fastcae's).
  const { section } = useSection();
  const plane = useMemo(() => planeOf(section, data.bbox), [section, data.bbox]);
  const planeRef = useRef(plane);
  planeRef.current = plane;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const renderer = new Renderer(canvas, mesh, data.faces);
    renderer.setFacePaint(new Map(data.parts.map((p, i) => [i, p.colour])));
    renderer.colourMode = "paint";
    renderer.setFaceState({ selected: new Set(), hovered: null, frozen: new Set(), exterior: new Set() });
    renderer.frame(data.bbox);
    renderer.setSection(planeRef.current, planeRef.current ? outlineOf(planeRef.current, data.bbox) : null);
    rendererRef.current = renderer;
    dirtyRef.current = true;
    let frame = 0;
    const loop = () => {
      if (dirtyRef.current) {
        dirtyRef.current = false;
        renderer.render();
      }
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    const sized = new ResizeObserver(() => {
      dirtyRef.current = true;
    });
    sized.observe(canvas);
    return () => {
      cancelAnimationFrame(frame);
      sized.disconnect();
      renderer.dispose();
      rendererRef.current = null;
    };
  }, [mesh, data]);

  // Full opacity: painted on the one mesh. Below it: hidden there, drawn as a ghost of its own.
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    const hidden = new Set<number>();
    const ghosts: Ghost[] = [];
    looks.forEach((look, i) => {
      if (!look.shown || look.opacity <= 0) hidden.add(i);
      else if (look.opacity < 100) {
        hidden.add(i);
        ghosts.push({ mesh: subs[i], tint: data.parts[i].colour, alpha: look.opacity / 100 });
      }
    });
    renderer.setHidden(hidden);
    renderer.setGhosts(ghosts);
    dirtyRef.current = true;
  }, [looks, subs, data]);

  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.setSection(plane, plane ? outlineOf(plane, data.bbox) : null);
    dirtyRef.current = true;
  }, [plane, data.bbox]);

  // Camera input, as the Contract page's: drag turns, shift or the middle button pans, the wheel zooms.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let dragging: "orbit" | "pan" | null = null;
    let lastX = 0;
    let lastY = 0;
    const down = (e: PointerEvent) => {
      canvas.setPointerCapture(e.pointerId);
      dragging = e.button === 1 || e.shiftKey ? "pan" : "orbit";
      lastX = e.clientX;
      lastY = e.clientY;
    };
    const move = (e: PointerEvent) => {
      const renderer = rendererRef.current;
      if (!renderer || !dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      if (dragging === "orbit") renderer.orbit(dx, dy);
      else renderer.pan(dx, dy);
      dirtyRef.current = true;
    };
    const up = (e: PointerEvent) => {
      canvas.releasePointerCapture(e.pointerId);
      dragging = null;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      rendererRef.current?.zoom(e.deltaY);
      dirtyRef.current = true;
    };
    const menu = (e: Event) => e.preventDefault();
    canvas.addEventListener("pointerdown", down);
    canvas.addEventListener("pointermove", move);
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("wheel", wheel, { passive: false });
    canvas.addEventListener("contextmenu", menu);
    return () => {
      canvas.removeEventListener("pointerdown", down);
      canvas.removeEventListener("pointermove", move);
      canvas.removeEventListener("pointerup", up);
      canvas.removeEventListener("wheel", wheel);
      canvas.removeEventListener("contextmenu", menu);
    };
  }, []);

  const set = (i: number, look: Partial<Look>) => setLooks(looks.map((l, k) => (k === i ? { ...l, ...look } : l)));
  const where = (pick: (p: Part) => Look | null) => setLooks(data.parts.map((p, i) => pick(p) ?? looks[i]));
  const rgb = (c: [number, number, number]) => `rgb(${c.map((v) => Math.round(v * 255)).join(",")})`;

  return (
    <div className="vol dv-vol">
      <div className="vol-stage dv-stage">
        <canvas ref={canvasRef} />
        <SectionControl bbox={data.bbox} facing={() => rendererRef.current?.facing() ?? null} />
      </div>
      <div className="vol-side dv-side">
        <div className="vol-actions dv-actions">
          {actions.map((a) => (
            <button key={a.label} type="button" onClick={() => where(a.pick)}>
              {a.label}
            </button>
          ))}
        </div>
        <div className="dv-parts">
          {groups.map(([g, title]) => {
            const members = data.parts.map((p, i) => [p, i] as const).filter(([p]) => p.group === g);
            if (!members.length) return null;
            return (
              <div key={g} className="dv-group">
                <div className="dv-group-h">{title}</div>
                {members.map(([p, i]) => (
                  <div key={p.id} className="dv-row" data-on={looks[i].shown}>
                    <button type="button" className="dv-toggle" title={looks[i].shown ? "hide" : "show"} onClick={() => set(i, { shown: !looks[i].shown })}>
                      <span className="vol-swatch" style={{ background: rgb(p.colour) }} />
                    </button>
                    <span className="dv-label" title={p.label}>
                      {p.label}
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={5}
                      value={looks[i].opacity}
                      aria-label={`${p.label} opacity`}
                      onChange={(e) => set(i, { opacity: Number(e.target.value), shown: true })}
                    />
                    <span className="dv-pct mono">{looks[i].opacity}%</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
        {children}
        <div className="vol-help">Drag to turn · shift-drag to pan · wheel to zoom</div>
      </div>
    </div>
  );
}

function Facts({ data }: { data: DesignFile }) {
  const recipe = data.recipe ?? {};
  const words = (v: unknown) => (typeof v === "object" && v !== null ? JSON.stringify(v).replace(/[{}"]/g, "").replace(/,/g, ", ") : String(v));
  const under = data.castable ? data.castable.reduce((s, h) => s + h.undercut_cm2, 0) : null;
  const voids = data.castable ? data.castable.reduce((s, h) => s + h.closed_voids, 0) : null;
  return (
    <div className="dv-facts">
      <div className="dv-fact">
        <span>mass</span>
        <span className="mono">{data.mass_kg.total.toFixed(2)} kg</span>
      </div>
      {under !== null ? (
        <div className="dv-fact">
          <span>castable</span>
          <span className="mono">
            {under.toFixed(1)} cm² undercut, {voids} voids
          </span>
        </div>
      ) : null}
      {data.grade ? (
        <>
          <div className="dv-fact">
            <span>bearing beds, peak drive</span>
            <span className="mono">{data.grade.drive_um.toFixed(0)} µm</span>
          </div>
          <div className="dv-fact">
            <span>misalignment</span>
            <span className="mono">{data.grade.misalignment.toFixed(2)} × its line</span>
          </div>
          <div className="dv-fact">
            <span>first mode</span>
            <span className="mono">{data.grade.first_mode_hz ? `${data.grade.first_mode_hz.toFixed(0)} Hz` : "-"}</span>
          </div>
        </>
      ) : (
        <div className="dv-fact dim">not judged yet</div>
      )}
      <details className="dv-recipe">
        <summary>Recipe</summary>
        {Object.entries(recipe).map(([k, v]) => (
          <div key={k} className="dv-fact">
            <span>{k}</span>
            <span className="mono">{words(v)}</span>
          </div>
        ))}
      </details>
    </div>
  );
}
