"""PROTOTYPE (LOP-29) - designs side by side, two to a row: each design's face picture (`look_face_<design>.png`, both halves from
outside, as `campaign_run.sh` writes it) under its own numbers from its records (FE's grade in `flow_<design>.json`, castability
in `castable_<design>.json`): mass, the worst seat, tilt, first mode, the orders, the grade, and castability's overhangs, thin
areas and thickest member. The engineer, 14 October 01:14: "compare baseline 1 and baseline 2 side by side with smoothing".

Run: .venv/Scripts/python.exe prototypes/first_loop/compare_sheet.py <out.png> <design>[:<title>] [<design>[:<title>] ...]
(out relative to data/first_loop)"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"


def numbers(d: str) -> list[str]:
    flow = OUT / f"flow_{d}.json"
    g = (json.loads(flow.read_text(encoding="utf-8")).get("grade") or {}) if flow.exists() else {}
    if not g and (OUT / "grades.json").exists():  # (LOP-30) a design judged outside a proposal (`judge_drawn.sh`): the grade's table
        g = next((r for r in json.loads((OUT / "grades.json").read_text(encoding="utf-8")) if r.get("stem") == d), {})
    lines = g.get("lines") or {}
    disp = (lines.get("displacement, peak drive") or {}).get("value_um")
    tilt = (lines.get("misalignment (worst seat against its line)") or {}).get("ratio")
    clashes = (lines.get("orders") or {}).get("clashes") or []
    first = g.get("first_mode_hz")
    fe = (f"{g.get('mass_kg', float('nan')):.2f} kg; worst seat {disp:.1f} µm (52.2 to beat); tilt {tilt:.2f}; first mode {first or 0:.0f} Hz"
          f" (500); " + ("orders clear" if not clashes else clashes[0]) + ("; FE PASSES" if g.get("pass") else "; FE fails")) if disp is not None else "FE: not judged"
    cast = OUT / f"castable_{d}.json"
    if not cast.exists():
        return [fe, "castability: not judged"]
    by = {h["half"]: h for h in json.loads(cast.read_text(encoding="utf-8"))["halves"]}
    under = " / ".join(f"{by[h]['undercut_cm2']:.0f}" for h in ("cover", "motor_side") if h in by)
    thin = " / ".join(f"{by[h]['thinner_than_least_wall_cm2']:.0f}" for h in ("cover", "motor_side") if h in by)
    least = min(by[h]["least_thickness_mm"] for h in by)
    big = max(by[h]["largest_section_members_mm"] for h in by)
    return [fe, f"castability (cover / motor side): overhangs {under} cm²; thinner than 4 mm {thin} cm² (down to {least:.2f} mm); thickest member {big:.0f} mm"]


def main(out: str, items: list[str]) -> None:
    pairs = [(it.split(":", 1) + [it.split(":", 1)[0]])[:2] for it in items]
    try:
        font_t = ImageFont.truetype("arialbd.ttf", 30)
        font = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        font_t = font = ImageFont.load_default()
    cell_w, cell_h, band = 2000, 1000, 130
    rows = (len(pairs) + 1) // 2
    sheet = Image.new("RGB", (2 * cell_w, rows * (cell_h + band)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (d, title) in enumerate(pairs):
        x, y = (i % 2) * cell_w, (i // 2) * (cell_h + band)
        draw.rectangle([x, y, x + cell_w, y + band], fill=(232, 236, 240))
        draw.text((x + 16, y + 10), title, fill="black", font=font_t)
        for k, line in enumerate(numbers(d)):
            draw.text((x + 16, y + 52 + 34 * k), line, fill=(40, 40, 40), font=font)
        face = OUT / f"look_face_{d}.png"
        if face.exists():
            sheet.paste(Image.open(face).convert("RGB").resize((cell_w, cell_h)), (x, y + band))
    draw.line([(cell_w, 0), (cell_w, sheet.height)], fill=(160, 160, 160), width=4)
    sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
    path = OUT / out
    sheet.save(path)
    print(path, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
