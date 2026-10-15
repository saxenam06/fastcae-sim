"""The final designs side by side with their numbers (LOP-34; a prototype): one row a design, its
end faces (`look_face_<design>.png`) beside its four views (`look_<design>.png`), under its numbers
from its own records (the grade in the folder's `grades.json`, castability in
`castable_<design>.json`, the oil-tight gate in `judged_<design>.json`).
`sheet.py <out.png> <folder>:<design>[:<title>] ...` (out relative to `data/rib_housing`); the
layout as `prototypes/first_loop/compare_sheet.py`'s."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "rib_housing"


def numbers(folder: Path, d: str) -> list[str]:
    grades = folder / "grades.json"
    g = next((r for r in json.loads(grades.read_text(encoding="utf-8")) if r.get("stem") == d), {}) if grades.exists() else {}
    lines = g.get("lines") or {}
    disp = next((v.get("value_um") for k, v in lines.items() if k.startswith("displacement")), None)
    tilt = (lines.get("misalignment (worst seat against its line)") or {}).get("ratio")
    clashes = (lines.get("orders") or {}).get("clashes") or []
    first = g.get("first_mode_hz")
    judged = folder / f"judged_{d}.json"
    tight = json.loads(judged.read_text(encoding="utf-8")).get("oiltight") if judged.exists() else None
    fe = (
        f"{g.get('mass_kg', float('nan')):.2f} kg (7.73 to beat); worst seat {disp:.1f} µm (52.2 to beat); "
        f"tilt {tilt:.2f} of its line; first mode {first or 0:.0f} Hz (500); "
        + ("orders clear" if not clashes else f"{len(clashes)} order clash(es)")
        + ("; every FE line PASSES" if g.get("pass") else "; FE fails a line")
        + ("" if tight is None else ("; oil-tight" if tight else "; NOT oil-tight"))
        if disp is not None
        else "FE: not judged"
    )
    cast = folder / f"castable_{d}.json"
    if not cast.exists():
        return [fe, "castability: not judged"]
    by = {h["half"]: h for h in json.loads(cast.read_text(encoding="utf-8"))["halves"]}
    under = " / ".join(f"{by[h]['undercut_cm2']:.0f}" for h in ("cover", "motor_side") if h in by)
    thin = " / ".join(f"{by[h]['thinner_than_least_wall_cm2']:.0f}" for h in ("cover", "motor_side") if h in by)
    big = max(by[h]["largest_section_members_mm"] for h in by)
    return [fe, f"castability (cover / motor side): overhangs {under} cm²; thinner than 4 mm {thin} cm²; "
                f"thickest member {big:.0f} mm"]


def main(out: str, items: list[str]) -> None:
    rows = []
    for it in items:
        parts = it.split(":")
        folder, d = Path(parts[0]), parts[1]
        rows.append((folder if folder.is_absolute() else ROOT / folder, d, parts[2] if len(parts) > 2 else d))
    try:
        font_t = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font_t = font = ImageFont.load_default()
    face_w, face_h, look_w, band = 2000, 1000, 1200, 120
    sheet = Image.new("RGB", (face_w + look_w, len(rows) * (face_h + band)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (folder, d, title) in enumerate(rows):
        y = i * (face_h + band)
        draw.rectangle([0, y, sheet.width, y + band], fill=(232, 236, 240))
        draw.text((16, y + 8), title, fill="black", font=font_t)
        for k, line in enumerate(numbers(folder, d)):
            draw.text((16, y + 50 + 30 * k), line, fill=(40, 40, 40), font=font)
        face = folder / f"look_face_{d}.png"
        if face.exists():
            sheet.paste(Image.open(face).convert("RGB").resize((face_w, face_h)), (0, y + band))
        look = folder / f"look_{d}.png"
        if look.exists():
            im = Image.open(look).convert("RGB")
            sheet.paste(im.resize((look_w, int(im.height * look_w / im.width))).crop((0, 0, look_w, face_h)),
                        (face_w, y + band))
    sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
    path = OUT / out
    sheet.save(path)
    print(path, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
