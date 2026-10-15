"""PROTOTYPE (LOP-29) - one design's three steps, each half from outside along its pull with the same camera in every row (the
engineer, 13 October 23:40: "show me picture after every step: optimization, drawing and then FE... what geometry is coming
out of optimization, then drawing and then FE"):
1. the optimisation: the run's cubes, the fixed ones grey (the interfaces, the shell), the metal it placed orange;
2. the drawing: the drawn halves (the field mesh FE meshes);
3. FE: each half's displacement under peak drive (µm), on FE's own mesh (`fe_<design>.npz`).
Each row's numbers from the records: the run's own check (`<run>.json`'s binary), the drawing's (`<design>.json`), FE's grade
(`flow_<design>.json`). The steps done so far are drawn, so it can run after each (the optimisation's stem read from
`optimise_<design>.log` before the drawing names it); a step not yet done is a grey band. Writes data/first_loop/steps_<design>.png.

Run: .venv/Scripts/python.exe prototypes/first_loop/steps_view.py <design>"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "first_loop"
HALVES = ("cover", "motor_side")  # the cover left, as the face pictures


def camera(pl, half: str, bounds) -> None:
    """From outside along the pull, a little off it (the motor side from below, the cover from above), y down the page."""
    c = np.array([(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2])
    look = np.array([0.22, 0.30, -1.0 if half == "motor_side" else 1.0])
    pl.camera.focal_point = tuple(c)
    pl.camera.position = tuple(c + 900.0 * look / np.linalg.norm(look))
    pl.camera.up = (0.0, -1.0, 0.0)
    pl.reset_camera(bounds=bounds)
    pl.camera.zoom(1.15)


def shot(meshes, half: str, bounds, scalars=None, clim=None, size=(800, 760)):
    import pyvista as pv

    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    for m, kw in meshes:
        pl.add_mesh(m, **kw)
    camera(pl, half, bounds)
    img = pl.screenshot(return_img=True)
    pl.close()
    return img


def run_of(design: str) -> str | None:
    """The design's optimisation: the drawing's record names it; before the drawing, the optimisation's log's last line."""
    rec_path = OUT / f"{design}.json"
    if rec_path.exists():
        return json.loads(rec_path.read_text(encoding="utf-8")).get("outcome_of")
    log = OUT / f"optimise_{design}.log"
    if log.exists():
        done = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if "done in" in ln]
        if done:
            return done[-1].rsplit("; ", 1)[-1].strip()
    return None


def main(design: str) -> None:
    import pyvista as pv
    from PIL import Image, ImageDraw, ImageFont

    run = run_of(design)
    if not run or not (OUT / f"{run}.npz").exists():
        raise SystemExit(f"{design}: its optimisation has not ended yet")
    rec_path = OUT / f"{design}.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else None
    if rec is not None and not all((OUT / rec.get("files", {}).get(hf, "-")).exists() for hf in HALVES):
        rec = None  # drawn only in part
    rr = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
    flow_path = OUT / f"flow_{design}.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8")) if flow_path.exists() else {}
    grade = flow.get("grade") or {}
    judged = (OUT / f"fe_{design}.npz").exists() and rec is not None
    z = np.load(OUT / f"{run}.npz")
    n, lo, h, ks = z["n"].astype(int), np.asarray(z["lo"], float), float(z["h"]), int(z["k_split"])
    cells = np.zeros(int(np.prod(n)), np.int8)
    elem, free_e, frozen = z["elem"], z["free_e"], z["frozen"].astype(bool)
    cells[elem[frozen]] = 1
    cells[elem[free_e][np.asarray(z["phys"], float) >= 0.5]] = 2
    cells = cells.reshape(tuple(n))
    fe = np.load(OUT / f"fe_{design}.npz") if judged else None
    u = fe["u"][:, 0] if judged else None
    rows = {"field": {}, "drawing": {}, "fe": {}}
    umax = 0.0
    surf_fe = {}
    for half in HALVES:
        c_half = cells.copy()
        if half == "motor_side":
            c_half[:, :, ks:] = 0
        else:
            c_half[:, :, :ks] = 0
        grid = pv.ImageData(dimensions=tuple(int(v) for v in n + 1), spacing=(h, h, h), origin=tuple(lo))
        grid.cell_data["k"] = c_half.ravel(order="F")
        fixed = grid.threshold([0.5, 1.5], scalars="k").extract_surface(algorithm="dataset_surface")
        placed = grid.threshold([1.5, 2.5], scalars="k").extract_surface(algorithm="dataset_surface")
        drawn = pv.read(str(OUT / rec["files"][half])) if rec is not None else None
        bounds = drawn.bounds if drawn is not None else fixed.merge(placed).bounds if placed.n_points else fixed.bounds
        rows["field"][half] = shot([(fixed, {"color": "#b8bec7", "opacity": 0.35}), (placed, {"color": "#e08a2c", "smooth_shading": False})], half, bounds)
        if drawn is not None:
            rows["drawing"][half] = shot([(drawn, {"color": "#c9ced6", "smooth_shading": True, "specular": 0.3})], half, bounds)
        if not judged:
            surf_fe[half] = (None, bounds)
            continue
        nodes, tets, off = fe[f"{half}_nodes"], fe[f"{half}_tets"], int(fe[f"{half}_offset"])
        disp = 1000.0 * np.linalg.norm(u[off : off + 3 * len(nodes)].reshape(-1, 3), axis=1)  # µm
        ug = pv.UnstructuredGrid(np.hstack([np.full((len(tets), 1), 4), tets[:, :4]]).ravel(), np.full(len(tets), pv.CellType.TETRA, dtype=np.uint8), nodes)
        ug.point_data["um"] = disp
        surf_fe[half] = (ug.extract_surface(algorithm="dataset_surface"), bounds)
        umax = max(umax, float(disp.max()))
    for half in HALVES:
        s, bounds = surf_fe[half]
        if s is None:
            continue
        rows["fe"][half] = shot([(s, {"scalars": "um", "cmap": "turbo", "clim": (0.0, umax), "show_scalar_bar": half == "motor_side",
                                      "scalar_bar_args": {"title": "µm, peak drive", "color": "black", "vertical": True}})], half, bounds)  # fmt: skip
    b = rr.get("binary") or {}
    drawn_kg = rec.get("mass_kg") if rec is not None else None
    drawn_kg = float(drawn_kg.get("total", sum(v for v in drawn_kg.values() if isinstance(v, (int, float))))) if isinstance(drawn_kg, dict) else float(drawn_kg or "nan")
    g = grade.get("lines") or {}
    disp_ = (g.get("displacement, peak drive") or {}).get("value_um")
    tilt_ = (g.get("misalignment (worst seat against its line)") or {}).get("ratio")
    clashes = (g.get("orders") or {}).get("clashes") or []
    texts = {
        "field": "1  The optimisation: the fixed cubes grey (interfaces, the 4 mm shell), the metal it placed orange. "
                 + (f"Its own check: {b.get('mass_kg', float('nan')):.2f} kg placed, the worst line {b.get('worst', float('nan')):.3f} of its held limit"
                    if b else ""),
        "drawing": f"2  The drawing (the field mesh): {drawn_kg:.2f} kg; every cube kept, walls exact" if rec is not None else "2  The drawing: not yet",
        "fe": (f"3  FE (rigid couplings): {grade.get('mass_kg', float('nan')):.2f} kg; worst seat {disp_:.1f} µm (to beat 52.2); tilt {tilt_:.2f} (line 1.0); "
               f"first mode {grade.get('first_mode_hz') or float('nan'):.0f} Hz; " + ("orders clear" if not clashes else f"{len(clashes)} mode(s) in an order's band")
               + ("; PASSES" if grade.get("pass") else "; fails")) if disp_ is not None else ("3  FE: judged, its grade follows" if judged else "3  FE: not yet"),
    }
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    w1, h1 = 800, 760
    band = 44
    sheet = Image.new("RGB", (2 * w1, 3 * (h1 + band)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, key in enumerate(("field", "drawing", "fe")):
        y = r * (h1 + band)
        draw.rectangle([0, y, 2 * w1, y + band], fill=(232, 236, 240))
        draw.text((12, y + 10), texts[key], fill="black", font=font)
        for c, half in enumerate(HALVES):
            if half not in rows[key]:
                draw.rectangle([c * w1, y + band, (c + 1) * w1, y + band + h1], fill=(244, 245, 247))
                continue
            sheet.paste(Image.fromarray(rows[key][half]), (c * w1, y + band))
            draw.text((c * w1 + 12, y + band + 8), "the cover, from outside" if half == "cover" else "the motor side, from outside", fill=(90, 90, 90), font=font)
    path = OUT / f"steps_{design}.png"
    sheet.save(path)
    print(path)


if __name__ == "__main__":
    main(sys.argv[1])
