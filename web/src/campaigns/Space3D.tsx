/**
 * A move's design space in 3D (LOP-24; the engineer, 12 October 00:04: "I want to see design spaces in
 * 3D on UI and each iteration on UI"), as the Contract page draws what the optimiser is given
 * (`../contracts/Volumes.tsx`): the contract's gear train, bores and mounts exact, from the Contract
 * page's own `../records/volumes.json`, and the run's own voxels as layers, from
 * `../records/campaigns/space3d/<campaign>.json` (`prototypes/first_loop/campaign_export.py`, git-ignored),
 * each drawn as a volume, a smooth see-through surface of the run's own cells (the engineer, 12 October
 * 01:02: "I want to see the design volumes as volumes and not as voxels"): the metal held fixed, where the
 * optimiser may place metal, the regions the agent chose (on each bore's boss, strips and wedges between the
 * hard points), for a move on one area its volumes, features and what it holds empty, and the metal the run
 * placed. Each chip shows or hides its layer. Camera: drag to turn, shift-drag or the middle button to pan,
 * the wheel to zoom.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { Ghost } from "../render/renderer";
import { Renderer } from "../render/renderer";
import type { Mesh } from "../render/mesh";
import { meshFromBase64 } from "../render/mesh";

interface Layer3D {
  id: string;
  key: string;
  label: string;
  kind: string;
  colour: [number, number, number];
  alpha: number;
  cells: number;
  note: string;
}
interface Space3DFile {
  voxel_mm: number;
  grid: { size: number; shape: [number, number, number]; origin: [number, number, number] };
  layers: Record<string, { mesh: string | null; cells: number; litres: number }>;
  context: Layer3D[];
  moves: Record<string, Layer3D[]>;
  /** Where a move with an area of its own opens: the area's box and the side its half faces (the viewer's frame). */
  focus?: Record<string, { bbox: number[]; from: number[] }>;
}
interface PartsLayer {
  id: string;
  label: string;
  colour: [number, number, number];
  faces: number[];
}
interface PartsFile {
  meshes: Record<string, string>;
  layers: PartsLayer[];
  bbox: number[];
  faces: number;
}

// Optional, as the Contract page's setup.json: absent in a fresh clone and in CI.
const FILES = import.meta.glob("../records/campaigns/space3d/*.json");
/** The contract's solids drawn exactly beside the voxels. */
const PARTS = new Set(["gear", "shaft", "bearing", "carrier", "mount"]);
/** Off when the view opens: the fixed metal veils the rest; the free space too where the move has an area of its own. */
const OFF_AT_OPEN = new Set(["fixed"]);
const AREA = new Set(["volumes", "features", "empty", "region_boss", "region_strip", "region_wedge"]);

export function Space3D({ campaign, move }: { campaign: string; move: number }) {
  const [file, setFile] = useState<Space3DFile | null>(null);
  const [parts, setParts] = useState<PartsFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    const load = FILES[`../records/campaigns/space3d/${campaign}.json`];
    if (!load) {
      setFailed("No 3D record for this campaign yet: campaign_export.py writes it.");
      return;
    }
    load()
      .then((m) => setFile((m as { default: Space3DFile }).default))
      .catch((e: unknown) => setFailed(String(e)));
    import("../records/volumes.json")
      .then((m) => setParts(m.default as unknown as PartsFile))
      .catch((e: unknown) => setFailed(String(e)));
  }, [campaign]);
  if (failed) return <div className="vol-empty">{failed}</div>;
  if (!file || !parts) return <div className="vol-empty">drawing the design space…</div>;
  const rows = file.moves[String(move)];
  if (!rows) return <div className="vol-empty">This move ran no optimisation: no design space to draw.</div>;
  return <Space3DStage file={file} parts={parts} rows={rows} focus={file.focus?.[String(move)] ?? null} />;
}

function Space3DStage({ file, parts, rows, focus }: { file: Space3DFile; parts: PartsFile; rows: Layer3D[]; focus: { bbox: number[]; from: number[] } | null }) {
  const layers = useMemo(() => [...file.context, ...rows], [file, rows]);
  const mesh = useMemo<Mesh>(() => meshFromBase64(parts.meshes.parts), [parts]);
  const [shown, setShown] = useState<Record<string, boolean>>({});
  const hasArea = rows.some((l) => AREA.has(l.id) || l.id.startsWith("domain_") || l.id.startsWith("volumes_"));
  const on = (l: Layer3D) => shown[l.id] ?? !(OFF_AT_OPEN.has(l.id) || (l.id === "space" && hasArea));
  const [partsOn, setPartsOn] = useState(true);
  const [opacity, setOpacity] = useState(1);
  // Each layer's surface decoded once (the renderer keeps an upload per mesh object).
  const volumes = useMemo(() => {
    const out: Record<string, Mesh> = {};
    for (const l of layers) {
      const src = file.layers[l.key];
      if (src?.mesh && !out[l.key]) out[l.key] = meshFromBase64(src.mesh);
    }
    return out;
  }, [file, layers]);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const dirtyRef = useRef(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const renderer = new Renderer(canvas, mesh, parts.faces);
    const paint = new Map<number, [number, number, number]>();
    for (const layer of parts.layers) for (const f of layer.faces) paint.set(f, layer.colour);
    renderer.setFacePaint(paint);
    renderer.colourMode = "paint";
    renderer.setFaceState({ selected: new Set(), hovered: null, frozen: new Set(), exterior: new Set() });
    renderer.frame(parts.bbox);
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
  }, [mesh, parts]);

  // A move with an area of its own is looked at there, from the side its half faces.
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.frame(parts.bbox);
    if (focus) renderer.focusBox(focus.bbox, focus.from);
    dirtyRef.current = true;
  }, [focus, parts]);

  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    const hidden = new Set<number>();
    for (const layer of parts.layers) if (!partsOn || !PARTS.has(layer.id)) for (const f of layer.faces) hidden.add(f);
    renderer.setHidden(hidden);
    const ghosts: Ghost[] = [];
    for (const l of layers) {
      if (on(l) && volumes[l.key]) ghosts.push({ mesh: volumes[l.key], tint: l.colour, alpha: Math.min(1, l.alpha * opacity) });
    }
    renderer.setGhosts(ghosts);
    dirtyRef.current = true;
  }, [shown, partsOn, layers, volumes, opacity, parts]); // `on` reads `shown`

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

  const rgb = (c: [number, number, number]) => `rgb(${c.map((v) => Math.round(v * 255)).join(",")})`;
  const litres = (l: Layer3D) => `${(file.layers[l.key]?.litres ?? 0).toFixed(2)} L`;
  return (
    <div className="vol cg-3d">
      <div className="vol-stage">
        <canvas ref={canvasRef} />
      </div>
      <div className="vol-side">
        <div className="vol-group" data-first={true}>
          <div className="vol-group-head">
            <span className="vol-group-title">The design space, as volumes</span>
            <span className="vol-group-sub">what it holds, the regions it may place metal in, and what it placed (from its {file.voxel_mm} mm cells)</span>
          </div>
          <div className="vol-chips">
            <button type="button" className="vol-chip" data-on={partsOn} title="the contract's gears, shafts, bearing bores and mounts, exact" onClick={() => setPartsOn(!partsOn)}>
              <span className="vol-swatch" style={{ background: "rgb(150,150,160)" }} />
              <span className="vol-label">Gear train, bores, mounts</span>
              <span className="vol-litres mono">exact</span>
            </button>
            {layers.map((l) => (
              <button key={l.id} type="button" className="vol-chip" data-on={on(l)} title={l.note} onClick={() => setShown({ ...shown, [l.id]: !on(l) })}>
                <span className="vol-swatch" style={{ background: rgb(l.colour) }} data-ghost={l.alpha < 0.5} />
                <span className="vol-label">{l.label}</span>
                <span className="vol-litres mono">{litres(l)}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="vol-actions">
          {focus ? (
            <button
              type="button"
              onClick={() => {
                rendererRef.current?.focusBox(focus.bbox, focus.from);
                dirtyRef.current = true;
              }}
            >
              The area
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              rendererRef.current?.frame(parts.bbox);
              dirtyRef.current = true;
            }}
          >
            The whole housing
          </button>
        </div>
        <label className="vol-opacity">
          <span>See-through</span>
          <input type="range" min={0.1} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
          <span className="mono">{Math.round(opacity * 100)}%</span>
        </label>
        <div className="vol-help">Drag to turn · shift-drag to pan · wheel to zoom · a chip shows or hides its layer</div>
      </div>
    </div>
  );
}
