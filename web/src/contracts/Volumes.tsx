/**
 * The contract's result in 3D, in three groups, each derived from those above it (the engineer,
 * 10 October 14:00; PLT-8, GBX-5):
 * - **the contract:** the gears, shafts, bearing bores, the differential and the mounts, which the
 *   design space keeps out of, and the packaging space;
 * - **what the agent decides,** its first hypothesis: the split flange at the split's place (a
 *   plane where the contract has no joint rules), the shell (the inside and its wall) and the
 *   bolts, with the hypothesis in words;
 * - **what the optimiser is given:** the design space, the packaging space less all of the above.
 *
 * `zenryx.api.volumes` writes them beside the snapshot: the solid elements as one mesh with a face
 * id per solid, and each see-through volume as a mesh of its own. They are drawn by fastcae's
 * WebGL2 renderer (copied, `../render`). Every chip shows or hides its element.
 *
 * Exact or voxels: when `../records/setup.json` exists (written by
 * `prototypes/first_loop/setup_export.py` from the same definitions, git-ignored), a switch shows
 * the optimiser's own 6 mm voxels in place of the exact volumes, element by element: what it holds
 * fixed, what it keeps out of, and where it is free. The gear train is the same in both. Without
 * the file the page shows the exact volumes alone (CI, a fresh clone).
 *
 * Camera: drag to turn, shift-drag or the middle button to pan, the wheel to zoom (as fastcae's
 * stage, `ui/src/stage/Stage.tsx`).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { Ghost, VoxelLayer } from "../render/renderer";
import { Renderer } from "../render/renderer";
import type { Mesh, VoxelCells } from "../render/mesh";
import { meshFromBase64 } from "../render/mesh";
import { SectionControl, useSection } from "../render/Section";
import { outlineOf, planeOf } from "../render/sectionPlane";

interface Layer {
  id: string;
  group: string;
  label: string;
  colour: [number, number, number];
  /** Its solids in the parts mesh. */
  faces: number[];
  /** Its see-through meshes, by key into `meshes`. */
  ghosts: string[];
  names: string[];
  litres: number;
  note: string;
  /** The split drawn as a plane (a contract without joint rules); with them it is the flange. */
  plane?: boolean;
}

interface Group {
  id: string;
  label: string;
  sub: string;
}

interface Row {
  label: string;
  value: string;
}

interface VolumesFile {
  contract: string;
  groups: Group[];
  hypothesis: Row[];
  layers: Layer[];
  meshes: Record<string, string>;
  bbox: number[];
  faces: number;
  incomplete: string[];
}

/** How see-through each see-through mesh is drawn. */
const ALPHA: Record<string, number> = {
  packaging: 0.08,
  design_space: 0.26,
  shell: 0.22,
  split: 0.35,
  shaft_reach: 0.2,
  mount_reach: 0.2,
};

/** Off when the page opens: the two spaces veil what they are cut from (their chips, or a group's
 * title, show them). */
const OFF_AT_OPEN = new Set(["packaging", "design_space"]);

/** The gear train: drawn exactly in both views (the optimiser holds it as the inside). */
const ALWAYS_EXACT = new Set(["gear", "shaft", "bearing", "carrier"]);

/** One mask of the optimiser's voxel model, as the boundary faces of its cells, and the chip it
 * belongs to. */
interface SetupLayer {
  id: string;
  chip: string;
  /** Metal held fixed, a room kept out, the free space, or a plane. */
  kind: "fixed" | "kept_out" | "free" | "plane";
  label: string;
  colour: [number, number, number];
  alpha: number;
  faces: string;
  cells: number;
  litres: number;
  note: string;
}

interface SetupFile {
  source: string;
  voxel_mm: number;
  grid: { size: number; shape: [number, number, number]; origin: [number, number, number] };
  layers: SetupLayer[];
  hypothesis?: Row[];
}

// Optional: absent in a fresh clone and in CI, where the page shows the exact volumes only.
const SETUP_FILES = import.meta.glob("../records/setup.json");

function uint32FromBase64(text: string): Uint32Array {
  const raw = atob(text);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return new Uint32Array(bytes.buffer);
}

/** `voxels`: open on the optimiser's voxels (the Designs page's Set-up step) rather than the exact volumes. */
export function Volumes({ voxels = false }: { voxels?: boolean } = {}) {
  const [data, setData] = useState<VolumesFile | null>(null);
  const [setup, setSetup] = useState<SetupFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    import("../records/volumes.json")
      .then((m) => setData(m.default as unknown as VolumesFile))
      .catch((e: unknown) => setFailed(String(e)));
    const load = SETUP_FILES["../records/setup.json"];
    if (load) {
      load()
        .then((m) => setSetup((m as { default: SetupFile }).default))
        .catch(() => setSetup(null));
    }
  }, []);
  if (failed) return <div className="vol-empty">the volumes could not be read: {failed}</div>;
  if (!data) return <div className="vol-empty">drawing the volumes…</div>;
  return <VolumesStage data={data} setup={setup} startVoxels={voxels} />;
}

function VolumesStage({ data, setup, startVoxels }: { data: VolumesFile; setup: SetupFile | null; startVoxels: boolean }) {
  const meshes = useMemo(() => {
    const out: Record<string, Mesh> = {};
    for (const [k, v] of Object.entries(data.meshes)) out[k] = meshFromBase64(v);
    return out;
  }, [data]);
  const [shown, setShown] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(data.layers.map((l) => [l.id, !OFF_AT_OPEN.has(l.id)])),
  );
  const [voxels, setVoxels] = useState(startVoxels);
  // The optimiser's voxels, each layer's cells decoded once (the renderer keeps an upload per cells object).
  const setupCells = useMemo(() => {
    const out: Record<string, VoxelCells> = {};
    if (!setup) return out;
    for (const l of setup.layers) {
      out[l.id] = { faces: uint32FromBase64(l.faces), size: setup.grid.size, shape: setup.grid.shape, origin: setup.grid.origin };
    }
    return out;
  }, [setup]);
  const twins = useMemo(() => {
    const out: Record<string, SetupLayer[]> = {};
    for (const l of setup?.layers ?? []) (out[l.chip] ??= []).push(l);
    return out;
  }, [setup]);
  const [opacity, setOpacity] = useState(1);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const dirtyRef = useRef(true);
  // The cut section every 3D view shares (render/Section.tsx, fastcae's): kept on the side `n . x <= d`.
  const { section } = useSection();
  const plane = useMemo(() => planeOf(section, data.bbox), [section, data.bbox]);
  const planeRef = useRef(plane);
  planeRef.current = plane;

  // The renderer, once per mesh; what is shown reaches it through explicit calls.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const renderer = new Renderer(canvas, meshes.parts, data.faces);
    const paint = new Map<number, [number, number, number]>();
    for (const layer of data.layers) for (const f of layer.faces) paint.set(f, layer.colour);
    renderer.setFacePaint(paint);
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
  }, [meshes, data]);

  // What is shown. In the voxel view an element with voxels shows them in place of its exact
  // volumes; the gear train keeps its exact solids.
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    const hidden = new Set<number>();
    const ghosts: Ghost[] = [];
    const cells: VoxelLayer[] = [];
    for (const layer of data.layers) {
      const on = Boolean(shown[layer.id]);
      const twin = voxels ? twins[layer.id] : undefined;
      const exactSolids = on && (!twin || ALWAYS_EXACT.has(layer.id));
      if (!exactSolids) for (const f of layer.faces) hidden.add(f);
      if (!on) continue;
      if (twin) {
        for (const l of twin) {
          if (setupCells[l.id]) cells.push({ key: l.id, cells: setupCells[l.id], tint: l.colour, alpha: Math.min(1, l.alpha * opacity) });
        }
      } else {
        for (const key of layer.ghosts) {
          if (meshes[key]) ghosts.push({ mesh: meshes[key], tint: layer.colour, alpha: ALPHA[key] ?? 0.25 });
        }
      }
    }
    renderer.setHidden(hidden);
    renderer.setGhosts(ghosts);
    renderer.setVoxelLayers(cells);
    dirtyRef.current = true;
  }, [shown, data, meshes, voxels, twins, setupCells, opacity]);

  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    renderer.setSection(plane, plane ? outlineOf(plane, data.bbox) : null);
    dirtyRef.current = true;
  }, [plane, data.bbox]);

  // Camera input, as fastcae's stage: drag turns, shift or the middle button pans, the wheel zooms.
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

  const only = (ids: string[]) => setShown(Object.fromEntries(data.layers.map((l) => [l.id, ids.includes(l.id)])));
  const group = (g: string) => data.layers.filter((l) => l.group === g);
  // A group's title: the group with what it derives from (the groups above it), the packaging
  // space left out unless it is the group's own.
  const upTo = (g: string) => {
    const order = data.groups.map((x) => x.id);
    const last = order.indexOf(g);
    only(data.layers.filter((l) => order.indexOf(l.group) <= last && (l.id !== "packaging" || l.group === g)).map((l) => l.id));
  };
  const rgb = (c: [number, number, number]) => `rgb(${c.map((v) => Math.round(v * 255)).join(",")})`;
  // A chip's litres: its metal (or the free space), never the rooms it keeps out of.
  const litres = (l: Layer) => {
    const twin = voxels ? twins[l.id] : undefined;
    if (twin && !ALWAYS_EXACT.has(l.id)) {
      const counted = twin.filter((t) => t.kind === "fixed" || t.kind === "free");
      return counted.length ? `${counted.reduce((s, t) => s + t.litres, 0).toFixed(2)} L` : "plane";
    }
    return l.plane ? "plane" : `${l.litres.toFixed(2)} L`;
  };

  return (
    <div className="vol">
      <div className="vol-stage">
        <canvas ref={canvasRef} />
        <SectionControl bbox={data.bbox} facing={() => rendererRef.current?.facing() ?? null} />
      </div>
      <div className="vol-side">
        {setup ? (
          <div className="vol-mode">
            <span className="segmented">
              <button type="button" data-active={!voxels} onClick={() => setVoxels(false)}>
                Exact
              </button>
              <button type="button" data-active={voxels} onClick={() => setVoxels(true)}>
                The optimiser's {setup.voxel_mm} mm voxels
              </button>
            </span>
          </div>
        ) : null}
        {data.groups.map((g, i) => (
          <div key={g.id} className="vol-group" data-first={i === 0}>
            <button type="button" className="vol-group-head" title="Show this and what it derives from" onClick={() => upTo(g.id)}>
              <span className="vol-group-title">{g.label}</span>
              <span className="vol-group-sub">{g.sub}</span>
            </button>
            <div className="vol-chips">
              {group(g.id).map((l) => (
                <button
                  key={l.id}
                  type="button"
                  className="vol-chip"
                  data-on={Boolean(shown[l.id])}
                  title={l.note}
                  onClick={() => setShown({ ...shown, [l.id]: !shown[l.id] })}
                >
                  <span className="vol-swatch" style={{ background: rgb(l.colour) }} data-ghost={l.faces.length === 0} />
                  <span className="vol-label">{l.label}</span>
                  <span className="vol-litres mono">{litres(l)}</span>
                </button>
              ))}
            </div>
            {g.id === "hypothesis" ? (
              <dl className="vol-rows">
                {[...data.hypothesis, ...(setup?.hypothesis ?? [])].map((r) => (
                  <div key={r.label} className="vol-row">
                    <dt>{r.label}</dt>
                    <dd>{r.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
        ))}
        {voxels ? (
          <label className="vol-opacity">
            <span>See-through</span>
            <input type="range" min={0.1} max={1} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
            <span className="mono">{Math.round(opacity * 100)}%</span>
          </label>
        ) : null}
        <div className="vol-actions">
          <button type="button" onClick={() => only(["design_space"])}>
            Design space only
          </button>
          <button type="button" onClick={() => setShown(Object.fromEntries(data.layers.map((l) => [l.id, true])))}>
            All
          </button>
        </div>
        {data.incomplete.length ? (
          <div className="vol-warn">
            Drawn with a guessed bearing where none is selected yet: {data.incomplete.join("; ")}
          </div>
        ) : null}
        <div className="vol-help">Drag to turn · shift-drag to pan · wheel to zoom · a group's title shows it with what it derives from</div>
      </div>
    </div>
  );
}
