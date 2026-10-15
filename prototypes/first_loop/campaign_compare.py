"""PROTOTYPE (LOP-28) - one iteration of the overnight campaign judged against the reference, the same way every time: the
grade's numbers (mass, the worst seat, the tilt, the first mode, the clashes), oil-tightness, castability (undercut, the
members' largest section against the 16 mm lump gate), each semantic region's measure on both runs' own heights (the
regions file's: the bending or the double curvature, 1/m), the brackets' metal, where the metal moved (by bore, mount,
flange and walls), and a sheet of both designs' faces along the pull with their numbers.

Run: .venv/Scripts/python.exe prototypes/first_loop/campaign_compare.py <reference design> <design> [--regions s1_regions.npz]
Writes data/first_loop/compare_<design>.png and prints the table."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import metal_by_part  # noqa: E402
import roughness  # noqa: E402
import topo  # noqa: E402

OUT = topo.OUT


def grade_of(design: str) -> dict:
    g = {x["stem"]: x for x in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))}.get(design)
    if g is None:
        return {}
    lines = g["lines"]
    return {"kg": g["mass_kg"], "seat_um": lines["displacement, peak drive"]["value_um"],
            "tilt": lines["misalignment (worst seat against its line)"]["ratio"], "mode1_hz": g.get("first_mode_hz"),
            "clashes": len(lines["orders"]["clashes"]), "pass": g["pass"]}  # fmt: skip


def cast_of(design: str) -> dict:
    out = {}
    p = OUT / f"castable_{design}.json"
    if p.exists():
        c = json.loads(p.read_text(encoding="utf-8"))
        out["undercut_pct"] = [round(100 * hh["undercut_share"], 2) for hh in c["halves"]]
        out["members_mm"] = [hh.get("largest_section_members_mm") for hh in c["halves"]]
    p = OUT / f"oiltight_{design}.json"
    if p.exists():
        out["oiltight"] = json.loads(p.read_text(encoding="utf-8")).get("tight")
    return out


def regions_of(run: str, regions: Path) -> tuple[list[str], np.ndarray]:
    zr = np.load(regions)
    f = roughness.tops(run)
    op = topo.bending_operator(f["height"], f["ijk_free"], zr["weights"])
    kinds = zr["kinds"] if "kinds" in zr.files else np.zeros(len(zr["names"]), int)
    b, _ = topo.bending_value(op, f["t"], kinds)
    return [str(v) for v in zr["names"]], topo.bending_rms(b, kinds, f["h"])


def main(ref: str, design: str, regions: str) -> None:
    runs = {d: json.loads((OUT / f"{d}.json").read_text(encoding="utf-8"))["outcome_of"] for d in (ref, design)}
    rows = {d: {**grade_of(d), **cast_of(d)} for d in (ref, design)}
    print(f"{'':24s} {'kg':>6s} {'seat µm':>8s} {'tilt':>6s} {'mode1':>6s} {'clash':>5s} {'pass':>5s}  undercut %   members mm  oil-tight")
    for d, r in rows.items():
        print(f"{d:24s} {r.get('kg', float('nan')):6.2f} {r.get('seat_um', float('nan')):8.1f} {r.get('tilt', float('nan')):6.3f} "
              f"{r.get('mode1_hz') or float('nan'):6.0f} {r.get('clashes', -1):5d} {str(r.get('pass')):>5s}  {r.get('undercut_pct')}  {r.get('members_mm')}  {r.get('oiltight')}")  # fmt: skip
    rp = Path(regions)
    rp = rp if rp.is_absolute() or rp.exists() else OUT / rp
    try:  # a regions file is per column: one made for another set-up (the panel spokes fix 58 columns) does not fit
        names, ref_v = regions_of(runs[ref], rp) if rp.exists() else (None, None)
        _, des_v = regions_of(runs[design], rp) if rp.exists() else (None, None)
    except ValueError as e:
        print(f"\nthe regions ({rp.name}) do not fit these runs' columns ({e}); their bending is not read")
        names = None
    if names is not None:
        bounds = np.load(rp)["rms_per_m"]
        print(f"\n{'region (the optimiser’s heights, 1/m)':40s} {ref:>16s} {design:>16s} {'bound':>8s}")
        for nm, a, b, bd in zip(names, ref_v, des_v, bounds, strict=True):
            print(f"{nm:40s} {a:16.0f} {b:16.0f} {bd:8.0f}  ({100 * (b / a - 1):+.0f} %)")
    print()
    metal_by_part.main(runs[ref], runs[design], ref, design)
    try:  # the faces, one row each, with their numbers
        from PIL import Image, ImageDraw, ImageFont

        ims, labels = [], []
        for d in (ref, design):
            p = OUT / f"look_face_{d}.png"
            if p.exists():
                ims.append(Image.open(p).convert("RGB"))
                r = rows[d]
                labels.append(f"{d}: {r.get('kg', 0):.2f} kg · {r.get('seat_um', 0):.1f} µm · tilt {r.get('tilt', 0):.3f} × · "
                              f"{r.get('mode1_hz') or 0:.0f} Hz · {r.get('clashes', 0)} clash(es) · {'PASS' if r.get('pass') else 'fail'}")  # fmt: skip
        if ims:
            band = 60
            w = max(im.width for im in ims)
            sheet = Image.new("RGB", (w, sum(im.height + band for im in ims)), "white")
            draw = ImageDraw.Draw(sheet)
            font = ImageFont.truetype("arial.ttf", 30)
            y = 0
            for im, lab in zip(ims, labels, strict=True):
                draw.rectangle([0, y, w, y + band], fill=(235, 235, 235))
                draw.text((16, y + 14), lab, fill="black", font=font)
                sheet.paste(im, (0, y + band))
                y += im.height + band
            sheet = sheet.resize((sheet.width // 2, sheet.height // 2))
            sheet.save(OUT / f"compare_{design}.png")
            print(OUT / f"compare_{design}.png")
    except Exception as exc:  # the sheet is for looking only
        print(f"(no sheet: {exc})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="One campaign iteration against the reference (LOP-28).")
    ap.add_argument("ref")
    ap.add_argument("design")
    ap.add_argument("--regions", default="s1_regions.npz")
    a = ap.parse_args()
    main(a.ref, a.design, a.regions)
