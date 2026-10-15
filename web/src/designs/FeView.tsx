/**
 * FE's mesh and its results on a design (LOP-21): the outer surface of the design's TET10 mesh, the
 * two halves as patches with their element edges, or a field in peak drive (the displacement, the
 * von Mises stress) as banded contours, on the shape deformed as many times as chosen. Drawn by
 * fastcae-v1's FE renderer (`../render/fe.ts`, copied) with its legend (`Legend.tsx`, copied).
 *
 * The data: `../records/process/<design>_fe.json`, written by `prototypes/first_loop/process_export.py`
 * from the design's FE result (each outer face of the mesh, a value per node). Loaded only when shown.
 *
 * Camera: drag to turn, shift-drag to pan, the wheel to zoom.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { Skin } from "../render/fe";
import { FeRenderer, newCamera } from "../render/fe";
import { Legend } from "./Legend";

const FE_FILES = import.meta.glob("../records/process/*_fe.json");

interface Field {
  unit: string;
  label: string;
  values: string;
}

interface FeFile {
  design: string;
  skin: { positions: string; triangles: string; groups: string; nodes: string; groupNames: string[] };
  fields: Record<string, Field>;
  vectors: string;
  bbox: number[];
  mesh: { unknowns: number | null; modes_hz: number[] | null; clashes: string[] | null };
}

function bytes(text: string): ArrayBuffer {
  const raw = atob(text);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out.buffer;
}

const HALF_COLOURS: [number, number, number][] = [
  [178, 186, 199],
  [168, 199, 182],
];
const DEFORMS = [0, 300, 1000, 3000];

export function FeView({ design, field }: { design: string; field: string | null }) {
  const [data, setData] = useState<FeFile | null>(null);
  const [failed, setFailed] = useState("");
  const [which, setWhich] = useState<string | null>(field);
  const [deform, setDeform] = useState(field ? 1000 : 0);
  useEffect(() => setWhich(field), [field]);
  useEffect(() => {
    setData(null);
    setFailed("");
    const load = FE_FILES[`../records/process/${design}_fe.json`];
    if (!load) {
      setFailed(`no FE result exported for ${design} (prototypes/first_loop/process_export.py)`);
      return;
    }
    load()
      .then((m) => setData((m as { default: FeFile }).default))
      .catch((e: unknown) => setFailed(String(e)));
  }, [design]);

  const decoded = useMemo(() => {
    if (!data) return null;
    const skin: Skin = {
      positions: new Float32Array(bytes(data.skin.positions)),
      triangles: new Uint32Array(bytes(data.skin.triangles)),
      groups: new Uint16Array(bytes(data.skin.groups)),
      nodes: new Uint32Array(bytes(data.skin.nodes)),
      groupNames: data.skin.groupNames,
    };
    const fields: Record<string, { field: Field; values: Float32Array; range: [number, number] }> = {};
    for (const [name, f] of Object.entries(data.fields)) {
      const values = new Float32Array(bytes(f.values));
      let lo = Infinity;
      let hi = -Infinity;
      for (const v of values) {
        if (Number.isFinite(v)) {
          lo = Math.min(lo, v);
          hi = Math.max(hi, v);
        }
      }
      fields[name] = { field: f, values, range: [lo, hi] };
    }
    return { skin, fields, vectors: new Float32Array(bytes(data.vectors)) };
  }, [data]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rendererRef = useRef<FeRenderer | null>(null);
  const [range, setRange] = useState<[number, number] | null>(null);
  const current = which && decoded ? decoded.fields[which] : null;
  useEffect(() => setRange(current ? current.range : null), [which, decoded]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !decoded || !data) return;
    const r = new FeRenderer(canvas, newCamera());
    rendererRef.current = r;
    r.setSkin(decoded.skin);
    r.setGroupColours(HALF_COLOURS);
    r.frame(data.bbox);
    r.render();
    let drag: { x: number; y: number; pan: boolean } | null = null;
    const down = (e: PointerEvent) => {
      drag = { x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button === 1 };
      canvas.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!drag) return;
      const dx = e.clientX - drag.x;
      const dy = e.clientY - drag.y;
      drag.x = e.clientX;
      drag.y = e.clientY;
      if (drag.pan) r.pan(dx, dy);
      else r.orbit(dx, dy);
      r.render();
    };
    const up = () => {
      drag = null;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      r.zoom(e.deltaY);
      r.render();
    };
    const resize = new ResizeObserver(() => r.render());
    resize.observe(canvas);
    canvas.addEventListener("pointerdown", down);
    canvas.addEventListener("pointermove", move);
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("wheel", wheel, { passive: false });
    return () => {
      resize.disconnect();
      canvas.removeEventListener("pointerdown", down);
      canvas.removeEventListener("pointermove", move);
      canvas.removeEventListener("pointerup", up);
      canvas.removeEventListener("wheel", wheel);
      r.dispose();
      rendererRef.current = null;
    };
  }, [decoded, data]);

  useEffect(() => {
    const r = rendererRef.current;
    if (!r || !decoded) return;
    if (current && range) {
      r.mode = "contour";
      r.range = range;
      r.edges = false;
      r.deform = deform;
      r.setValues(current.values, decoded.vectors);
    } else {
      r.mode = "patches";
      r.edges = true;
      r.deform = 0;
      r.setValues(null, null);
    }
    r.render();
  }, [current, range, deform, decoded]);

  if (failed) return <div className="vol-empty">{failed}</div>;
  if (!data || !decoded) return <div className="vol-empty">loading FE's mesh and results…</div>;
  const names = Object.keys(decoded.fields);
  return (
    <div className="fe-view">
      <div className="fe-view-bar">
        <button type="button" className="dv-pick-b" data-on={!which} onClick={() => setWhich(null)}>
          The mesh
        </button>
        {names.map((n) => (
          <button key={n} type="button" className="dv-pick-b" data-on={which === n} onClick={() => setWhich(n)}>
            {decoded.fields[n].field.label}
          </button>
        ))}
        {which ? (
          <span className="fe-view-deform">
            deformed ×
            {DEFORMS.map((d) => (
              <button key={d} type="button" className="dv-pick-b" data-on={deform === d} onClick={() => setDeform(d)}>
                {d}
              </button>
            ))}
          </span>
        ) : null}
      </div>
      <div className="fe-view-stage">
        <canvas ref={canvasRef} className="fe-view-canvas" />
        {current && range ? (
          <Legend title={current.field.label} unit={current.field.unit} range={range} data={current.range} bands={12} onRange={setRange} />
        ) : null}
        <div className="hint">drag to turn · shift-drag to pan · wheel to zoom</div>
      </div>
    </div>
  );
}
