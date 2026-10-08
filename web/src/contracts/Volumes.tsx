/**
 * The contract's result: the volumes it fixes, and the design space they leave (PLT-8).
 *
 * `zenryx.api.volumes` writes them beside the snapshot: the parts (gears, shafts, bearings, the
 * differential) as one mesh with a face id per part, and the packaging space and the design space
 * as meshes of their own. They are drawn by fastcae's WebGL2 renderer (copied, `../render`): the
 * parts solid, each in its layer's colour; the two spaces see-through. Every layer's chip shows
 * or hides it, so the design space can be seen alone or with everything it was cut from.
 *
 * Camera: drag to turn, shift-drag or the middle button to pan, the wheel to zoom (as fastcae's
 * stage, `ui/src/stage/Stage.tsx`).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { Ghost } from "../render/renderer";
import { Renderer } from "../render/renderer";
import type { Mesh } from "../render/mesh";
import { meshFromBase64 } from "../render/mesh";

interface Layer {
  id: string;
  label: string;
  colour: [number, number, number];
  draw: "solid" | "ghost";
  faces: number[];
  names: string[];
  litres: number;
}

interface VolumesFile {
  contract: string;
  layers: Layer[];
  meshes: Record<string, string>;
  bbox: number[];
  faces: number;
  incomplete: string[];
}

/** How see-through each space is drawn. */
const ALPHA: Record<string, number> = { packaging: 0.1, design_space: 0.32 };

export function Volumes() {
  const [data, setData] = useState<VolumesFile | null>(null);
  const [failed, setFailed] = useState("");
  useEffect(() => {
    import("../records/volumes.json")
      .then((m) => setData(m.default as unknown as VolumesFile))
      .catch((e: unknown) => setFailed(String(e)));
  }, []);
  if (failed) return <div className="vol-empty">the volumes could not be read: {failed}</div>;
  if (!data) return <div className="vol-empty">drawing the volumes…</div>;
  return <VolumesStage data={data} />;
}

function VolumesStage({ data }: { data: VolumesFile }) {
  const meshes = useMemo(() => {
    const out: Record<string, Mesh> = {};
    for (const [k, v] of Object.entries(data.meshes)) out[k] = meshFromBase64(v);
    return out;
  }, [data]);
  const [shown, setShown] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(data.layers.map((l) => [l.id, l.id !== "packaging"])),
  );

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const dirtyRef = useRef(true);

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

  // What is shown: solid layers by hiding their faces, the spaces as ghosts.
  useEffect(() => {
    const renderer = rendererRef.current;
    if (!renderer) return;
    const hidden = new Set<number>();
    const ghosts: Ghost[] = [];
    for (const layer of data.layers) {
      if (layer.draw === "solid") {
        if (!shown[layer.id]) for (const f of layer.faces) hidden.add(f);
      } else if (shown[layer.id]) {
        ghosts.push({ mesh: meshes[layer.id], tint: layer.colour, alpha: ALPHA[layer.id] ?? 0.25 });
      }
    }
    renderer.setHidden(hidden);
    renderer.setGhosts(ghosts);
    dirtyRef.current = true;
  }, [shown, data, meshes]);

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

  const only = (id: string) => setShown(Object.fromEntries(data.layers.map((l) => [l.id, l.id === id])));
  const all = () => setShown(Object.fromEntries(data.layers.map((l) => [l.id, true])));
  const rgb = (c: [number, number, number]) => `rgb(${c.map((v) => Math.round(v * 255)).join(",")})`;

  return (
    <div className="vol">
      <div className="vol-stage">
        <canvas ref={canvasRef} />
      </div>
      <div className="vol-side">
        <div className="vol-chips">
          {data.layers.map((l) => (
            <button
              key={l.id}
              type="button"
              className="vol-chip"
              data-on={shown[l.id]}
              title={l.names.join(" · ")}
              onClick={() => setShown({ ...shown, [l.id]: !shown[l.id] })}
            >
              <span className="vol-swatch" style={{ background: rgb(l.colour) }} data-ghost={l.draw === "ghost"} />
              <span className="vol-label">{l.label}</span>
              <span className="vol-litres mono">{l.litres.toFixed(2)} L</span>
            </button>
          ))}
        </div>
        <div className="vol-actions">
          <button type="button" onClick={() => only("design_space")}>
            Design space only
          </button>
          <button type="button" onClick={all}>
            All
          </button>
        </div>
        {data.incomplete.length ? (
          <div className="vol-warn">
            Drawn with a guessed bearing where none is selected yet: {data.incomplete.join("; ")}
          </div>
        ) : null}
        <div className="vol-help">Drag to turn · shift-drag to pan · wheel to zoom</div>
      </div>
    </div>
  );
}
