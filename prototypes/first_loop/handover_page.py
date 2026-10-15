"""PROTOTYPE (LOP-28) - the hand-over page for a CAD designer (the engineer, 13 October 01:30: "a production quality housing
geometry that meets the goal and can be delivered to a cad designer who gets clear direction about the features and members to
be drawn where and in what shape"): one HTML page built from a design's own records, every number from them:
- the graded lines against their targets (the grade), oil-tightness, castability, the mass by half;
- the pictures (each half along the pull; the four views; the members' map), embedded as JPEG;
- the protected features and the members (`member_map.py`'s JSON), as tables;
- the drawing directions, and where the field mesh is on the laptop.

Run: .venv/Scripts/python.exe prototypes/first_loop/handover_page.py <design> [--out <html>]
Writes data/first_loop/handover_<design>.html (or --out)."""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OUT = HERE.parents[1] / "data" / "first_loop"
TARGET_KG = 7.73


def jpeg(path: Path, width: int = 1400) -> str:
    from PIL import Image

    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def esc(v) -> str:
    return html.escape(str(v))


def tower_kg(run: str) -> tuple[float, float]:
    """The run's fixed bearing towers (each boss's cylinder from a wall past its seat to the split, `topo_free --protect`): their
    metal, and the part of it standing between the seats and the split (kg, the run's own voxels at the contract's 2.6 g/cm³)."""
    import numpy as np

    layout = json.loads((OUT / "contract.json").read_text(encoding="utf-8"))
    z = np.load(OUT / f"{run}.npz")
    h, lo = float(z["h"]), z["lo"].astype(float)
    xyz = lo[None, :] + h * (z["ijk"][z["frozen"].astype(bool)] + 0.5)
    kg = h**3 * float(layout["settings"]["density"])
    wall, z_s = float(layout["settings"]["wall"]), float(layout["z"]["split"])
    taken, beyond_all = np.zeros(len(xyz), bool), np.zeros(len(xyz), bool)
    for b in layout["bearings"]:
        r = np.hypot(xyz[:, 0] - b["axis"][0], xyz[:, 1] - b["axis"][1])
        lower = b["side"] == "-z"
        span = ((xyz[:, 2] >= b["z"][0] - wall) & (xyz[:, 2] < z_s)) if lower else ((xyz[:, 2] >= z_s) & (xyz[:, 2] <= b["z"][1] + wall))
        t = (r <= float(b["boss_r"])) & span & ~taken
        taken |= t
        beyond_all |= t & ((xyz[:, 2] > b["z"][1]) if lower else (xyz[:, 2] < b["z"][0]))
    return float(taken.sum() * kg), float(beyond_all.sum() * kg)


def main(design: str, out: Path, look: str = "", record: str = "docs/features/loop/2026-10-13-record-overnight.md") -> None:
    grades = {g["stem"]: g for g in json.loads((OUT / "grades.json").read_text(encoding="utf-8"))}
    g = grades[design]
    rec = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
    cast = json.loads((OUT / f"castable_{design}.json").read_text(encoding="utf-8"))
    tight = json.loads((OUT / f"oiltight_{design}.json").read_text(encoding="utf-8")).get("tight")
    mm = json.loads((OUT / f"member_map_{design}.json").read_text(encoding="utf-8"))
    fe = json.loads((OUT / f"fe_{design}.json").read_text(encoding="utf-8"))
    lines = g["lines"]
    disp = lines["displacement, peak drive"]
    tilt = lines["misalignment (worst seat against its line)"]
    clashes = lines["orders"]["clashes"]
    mass = g["mass_kg"]
    # Each gear order's nearest mode (FE's own modes and mesh frequencies), and how far apart.
    nearest = {name: min(fe["modes_hz"], key=lambda v, hz=hz: abs(v - hz)) for name, hz in fe["mesh_hz"].items()}
    gaps = {name: (nearest[name] - hz) / hz for name, hz in fe["mesh_hz"].items()}
    orders_txt = " or ".join(f"{name} ({hz:.0f} Hz)" for name, hz in fe["mesh_hz"].items())
    thin = [n for n in gaps if abs(gaps[n]) < 0.05]
    thin_txt = (f" The margin{'s' if len(thin) > 1 else ''} on {' and '.join(thin)} {'are' if len(thin) > 1 else 'is'} thin (under 5 %): "
                "the CAD's draft and fillets will move the modes, so judge the CAD's modes again.") if thin else ""  # fmt: skip
    rows = [
        ("Mass", f"{mass:.2f} kg", f"at most {TARGET_KG:g} kg (the reference)", mass <= TARGET_KG),
        ("Worst bearing seat, peak drive", f"{disp['value_um']:.1f} µm", f"at most {disp['to_beat_um']:g} µm", disp["pass"]),
        ("Worst bearing misalignment", f"{tilt['ratio']:.3f} × its line", "at most 1.0 × its line", tilt["pass"]),
        ("Modes against the gear orders", "none within 3 %" if not clashes else "; ".join(clashes), f"no mode within 3 % of {orders_txt}", not clashes),
        ("Oil-tight", "yes" if tight else "no", "the inside sealed, the seals in place", bool(tight)),
    ]
    run = json.loads((OUT / f"{rec['outcome_of']}.json").read_text(encoding="utf-8")) if rec.get("outcome_of") else {}
    towers = tower_kg(rec["outcome_of"]) if run.get("protect") and run.get("towers", True) else None
    spl = run.get("spline") or {}
    # (LOP-30) the design's rung and finish from its own records: simulation-feasible when every graded line passes,
    # process-rule-feasible only when castability's rules pass too; fillets and rounds where the section rule drew them
    cast_ok = all(h_.get("pull_rule", "PASS") == "PASS" and h_.get("least_wall_rule", "PASS") == "PASS" for h_ in cast["halves"])
    rung = ("Simulation-feasible" if g["pass"] else "Not yet simulation-feasible") + (
        " and process-rule-feasible" if cast_ok else "; castability's rules not yet met (below)")
    finish = (f"root fillets {spl['fillet_mm']:g} mm and free edges rounded {spl['round_mm']:g} mm drawn; no draft, not CAD"
              if spl.get("fillet_mm") else "no draft, no fillets, not CAD")  # fmt: skip
    spoke_halves = [half.replace("_", " ") for half, d in mm["halves"].items() if any(f["kind"] == "panel spokes" for f in d["features"])]
    spoke = next((f for d in mm["halves"].values() for f in d["features"] if f["kind"] == "panel spokes"), None)
    spoke_txt = (f", and on the {' and the '.join(spoke_halves)} the panel spokes ({spoke['of']}, {spoke['thickness_mm']:g} mm thick, "
                 f"{spoke['height_mm']:g} mm proud of the wall)") if spoke else ""  # fmt: skip
    webs_f = next((f for d in mm["halves"].values() for f in d["features"] if f["kind"] == "lug webs"), None)
    if webs_f:
        spoke_txt += (f"; and at each lug its two webs ({webs_f['thickness_mm']:g} mm thick, from the lug's far end to the split, "
                      "ending on the room's wall where the map shows them)")  # fmt: skip
    how = []
    if run:
        if run.get("empty") and run.get("shell_fixed"):
            how.append("The 4 mm shell round the gear rooms was fixed, with the sealing land, the bolts' bosses, the bearing seats' "
                       "rings and the mount lugs; the optimiser added members on top of it.")  # fmt: skip
        elif run.get("empty"):
            how.append("It started from no shell: only the bearing seats' rings, the mount lugs and the bolts' bosses were fixed, and every wall round the gear rooms was kept oil-tight by a least height.")
        if spl:
            win = spl.get("window") or {}
            txt = (f"The members are smooth spline fields, an outline in plan ({spl['phi_mm']:g} mm knots) and their heights "
                   f"({spl['h_mm']:g} mm knots): at least {run.get('least_width_mm') or 0:g} mm wide and "
                   f"{spl.get('gap_mm') or 0:g} mm apart, at least {run.get('least_height_mm') or 0:g} mm proud")
            if spl.get("top"):
                txt += ", each member's top one smooth surface"
            if win:
                caps = ", ".join(f"{c:g} mm" for c in win["caps_mm"])
                txt += (f"; on the end walls a member's height capped by its width ({caps} as it widens past "
                        f"{', '.join(f'{w:g}' for w in win['widths_mm'])} mm)")
                if win.get("caps_split_mm"):
                    txt += ", the side walls' gussets thin and deep"
                if win.get("free"):
                    txt += "; no cap in the mounts' reach" + (" and on the bearings' bosses" if "bosses" in win["free"] else "")
            if spl.get("round_mm"):
                txt += f"; free edges rounded {spl['round_mm']:g} mm, roots filleted {spl.get('fillet_mm') or 0:g} mm in the drawing"
            how.append(txt + ".")
            skin = rec.get("skin") or {}
            if skin.get("draw_smooth_mm"):
                how.append(f"The drawing smoothed each member's outline and top over {skin['draw_smooth_mm']:g} mm after the "
                           f"optimiser, on a {skin.get('grid_mm', 2):g} mm grid; FE judged the smoothed shape.")  # fmt: skip
        if run.get("modes"):
            md = run["modes"]
            how.append(f"Its own modes were held {100 * md['margin']:g} % from each gear order and its lowest at least "
                       f"{md.get('first') or 0:g} Hz (its model reads the modes low; FE's are the ones above).")  # fmt: skip
        seats = "; ".join(f"the {'motor side' if k.endswith('-z') else 'cover'}'s {k.split()[0]} seat at 1/{v:g}"
                          for k, v in (run.get("safety_seats") or {}).items())  # fmt: skip
        if run.get("objective") == "mass_tilt":
            how.append(f"It placed the least metal that holds every bearing's misalignment and every bearing bed at 1/{run['safety']:g} of its line"
                       f"{' (' + seats + ', the factor by which FE found the model flattered it)' if seats else ''}, under the {' and '.join(run.get('cases', []))} case.")  # fmt: skip
        held = []
        if run.get("protect"):
            seats_held = "the bearing bosses" if run.get("towers", True) else "the bearing seats' rings"
            held.append(f"the protected interfaces ({seats_held}, the sealing land, the bolts' bosses, the lugs)")
        if run.get("panel_spokes"):
            held.append(f"the panel spokes on the {run['panel_spokes']['halves'].replace(',', ' and ').replace('_', ' ')}")
        if run.get("lug_webs"):
            w_t, w_s = (float(v) for v in run["lug_webs"].split(":"))
            held.append(f"production's gusseted lugs: two webs {w_t:g} mm thick from each lug to its room's wall, from the lug's far end "
                        "to the split")  # fmt: skip
        if run.get("brackets"):
            b = run["brackets"]
            held.append("each bracket's least metal (" + ", ".join(f"{n} {v:g} cm³" for n, v in zip(b["names"], b["least_cm3"], strict=True)) + ")")
        if held:
            how.append("Held fixed in the field: " + "; ".join(held) + ".")
        if run.get("max_member"):
            gm = run["max_member"]
            lump_txt = ""
            lumps_f = OUT / f"lumps_{design}.json"
            if lumps_f.exists():  # (LOP-30) what the drawing measures (`lump_where.py`), beside what the rule aims at
                lw = json.loads(lumps_f.read_text(encoding="utf-8"))
                lump_txt = (" Measured on the drawing, the largest section outside the bearings' bosses and the mounts' eyes is "
                            + ", ".join(f"{v['largest_mm']:.0f} mm on the {k.replace('_', ' ')}" for k, v in lw.items())
                            + ": the rule reads the optimiser's placed metal, not the joins with the land and the arms' roots.")
            how.append(f"No lump: within a ball round each voxel of placed metal at most {gm['alpha']:g} of it is metal, so no member is much "
                       f"over {gm['mm']:g} mm thick (the greatest member{', read near its worst ball' if gm.get('p', 12) > 12 else ''}).{lump_txt}")  # fmt: skip
        if run.get("height_field"):
            how.append(f"The metal is a height off the wall in each {run['voxel_mm']:g} mm column, at most {run['band_mm']:g} mm beyond the wall, so each half casts along its pull by construction.")
    tests_rows = []  # the reading's tests (`reading_field.py`), each row from its design's own grade
    tests_notes = []  # what each test shows, from the tests file
    tests_file = OUT / f"reading_tests_{design}.json"
    if tests_file.exists():
        for t_ in json.loads(tests_file.read_text(encoding="utf-8")):
            gt = grades.get(t_["design"])
            if gt is None:
                continue
            lt = gt["lines"]
            cl = lt["orders"]["clashes"]
            tests_rows.append(
                f'<tr><td>{esc(t_["label"])} <span class="num">({esc(t_["design"])})</span></td><td class="num">{gt["mass_kg"]:.2f} kg</td>'
                f'<td class="num">{lt["displacement, peak drive"]["value_um"]:.1f} µm</td>'
                f'<td class="num">{lt["misalignment (worst seat against its line)"]["ratio"]:.3f} ×</td>'
                f'<td class="num">{gt.get("first_mode_hz") or 0:.0f} Hz</td><td>{esc("; ".join(cl)) if cl else "clear"}</td>'
                f'<td><span class="pill {"ok" if gt["pass"] else "no"}">{"pass" if gt["pass"] else "fail"}</span></td></tr>'
            )
            if t_.get("note"):
                tests_notes.append(f'<li><span class="num">{esc(t_["design"])}</span>: {esc(t_["note"])}</li>')
    und = " / ".join(f"{100 * h_['undercut_share']:.2f} %" for h_ in cast["halves"])
    first_mode = g.get("first_mode_hz") or 0
    pics = {}
    shown = look or design  # (LOP-30) the pictures may be another drawing of the same fields (`--look`, e.g. on 1 mm)
    look_note = ""
    if look:
        lg = grades.get(look)
        lrec = json.loads((OUT / f"{look}.json").read_text(encoding="utf-8"))
        look_note = (f" Drawn here from the same fields on a {(lrec.get('skin') or {}).get('grid_mm', 1):g} mm grid "
                     f"(<code>{esc(look)}</code>, {lrec['mass_kg']['motor_side'] + lrec['mass_kg']['cover']:.2f} kg), "
                     "smoother than the judged drawing's 2 mm cells")
        if lg:
            lcl = lg["lines"]["orders"]["clashes"]
            look_note += (f"; FE on it: {lg['lines']['displacement, peak drive']['value_um']:.1f} µm, tilt "
                          f"{lg['lines']['misalignment (worst seat against its line)']['ratio']:.2f}, first mode "
                          f"{lg.get('first_mode_hz') or 0:.0f} Hz, " + (esc("; ".join(lcl)) if lcl else "the orders clear"))
        look_note += "."
    for key, name in (("faces", f"look_face_{shown}.png"), ("views", f"look_{shown}.png"), ("map", f"member_map_{design}.png"),
                      ("reading", f"member_reading_{design}.png")):  # fmt: skip
        p = OUT / name
        if p.exists():
            pics[key] = jpeg(p, 1800 if key == "reading" else 1600 if key == "map" else 1400)
    files = [f"{rec['files'][h_]}" for h_ in ("cover", "motor_side") if h_ in rec.get("files", {})]
    feat_rows, mem_rows = [], []
    for half, d in mm["halves"].items():
        for f in d["features"]:
            size = ", ".join(f"{k.replace('_mm', '').replace('_', ' ')} {v}" for k, v in f.items() if k.endswith("_mm") and k != "centre_mm")
            kind = f["kind"]
            if kind == "bearing boss" and not towers and run.get("protect"):
                # (LOP-30) no towers: only the seat's 4 mm ring is fixed; the boss round it is the members' metal
                kind = "bearing seat"
                size = (f"bore {f.get('bore_mm')}, its 4 mm ring in the shell, z {f.get('z_mm')}; the boss (up to diameter "
                        f"{f.get('diameter_mm')}) as the members show it")  # fmt: skip
            feat_rows.append((half.replace("_", " "), kind, f.get("of", f.get("count", "")), f.get("centre_mm", ""), size))
        for m_ in d["members"]:
            mem_rows.append((m_["id"], half.replace("_", " "), m_["kind"], f"{m_['from_mm']} → {m_['to_mm']}", m_["length_mm"], m_["width_mm"],
                             f"{m_['height_mm']} / {m_['height_most_mm']}", m_["shape"], ", ".join(m_["meets"])))  # fmt: skip
    status = "Passes every graded line" if g["pass"] else "Passes every line but: " + ", ".join(r[0].lower() for r in rows if not r[3])
    page = f"""<title>Reducer Housing Hand-over</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column of an engineering hand-over sheet, figures full width, tables scroll inside their own frames */
:root {{
  --ground: #f3f5f7; --sheet: #ffffff; --ink: #1c2530; --muted: #5a6876; --rule: #d5dde4;
  --accent: #0e6b74; --pass: #1f7a4c; --fail: #b3541e;
  --display: "Barlow Semi Condensed", "Arial Narrow", Arial, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", Arial, sans-serif;
  --mono: "IBM Plex Mono", Consolas, "Courier New", monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --ground: #11161b; --sheet: #182028; --ink: #e3e9ee; --muted: #9aa8b5; --rule: #2c3842;
  --accent: #4fb3bd; --pass: #5cc48c; --fail: #e8935a; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --ground: #11161b; --sheet: #182028; --ink: #e3e9ee; --muted: #9aa8b5; --rule: #2c3842;
  --accent: #4fb3bd; --pass: #5cc48c; --fail: #e8935a; color-scheme: dark }}
body {{ background: var(--ground); color: var(--ink); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 1080px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px; display: grid; gap: 28px; }}
header {{ display: grid; gap: 10px; }}
.eyebrow {{ font: 500 12px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
h1 {{ font: 600 clamp(28px, 4.2vw, 40px)/1.1 var(--display); margin: 0; text-wrap: balance; }}
h2 {{ font: 600 22px/1.2 var(--display); margin: 0 0 10px; text-wrap: balance; }}
p {{ margin: 0; max-width: 68ch; }}
.status {{ font-weight: 600; color: {"var(--pass)" if g["pass"] else "var(--fail)"}; }}
section {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 6px; padding: 20px; display: grid; gap: 12px; min-width: 0; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
th {{ font: 500 12px/1.3 var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }}
td.num, .num {{ font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
.pill {{ font: 500 12px/1 var(--mono); padding: 4px 8px; border-radius: 999px; border: 1px solid currentColor; white-space: nowrap; }}
.ok {{ color: var(--pass); }} .no {{ color: var(--fail); }}
figure {{ margin: 0; display: grid; gap: 6px; }}
figure img {{ width: 100%; height: auto; border: 1px solid var(--rule); border-radius: 4px; background: #fff; }}
figcaption {{ color: var(--muted); font-size: 13px; }}
ol, ul {{ margin: 0; padding-left: 22px; display: grid; gap: 6px; max-width: 72ch; }}
code {{ font-family: var(--mono); font-size: 13px; overflow-wrap: anywhere; }}
a {{ color: var(--accent); }}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">EV two-stage reducer · housing geometry · {esc(design)}</div>
  <h1>Reducer housing, ready for CAD</h1>
  <p class="status">{esc(status)}.</p>
  <p>The housing's shape as the optimiser found it, drawn as one field mesh: the functional interfaces held exact, the walls at the 4 mm least wall round the gear rooms, and the members the optimiser placed. Judged by FE on that mesh (TET10), checked oil-tight and castable along the pull. {esc(rung)}; not production-ready ({esc(finish)}).</p>
</header>
<section>
  <h2>The lines</h2>
  <div class="scroll"><table>
    <tr><th>Line</th><th>This housing</th><th>Target</th><th></th></tr>
    {"".join(f'<tr><td>{esc(a)}</td><td class="num">{esc(b)}</td><td>{esc(c)}</td><td><span class="pill {"ok" if d else "no"}">{"pass" if d else "fail"}</span></td></tr>' for a, b, c, d in rows)}
  </table></div>
  <p>First mode {first_mode:.0f} Hz. Undercut along the pull {esc(und)} of each half's surface (motor side / cover). Mass by half: motor side {rec['mass_kg']['motor_side']:.2f} kg, cover {rec['mass_kg']['cover']:.2f} kg (the drawn mesh).</p>
  <p>The nearest mode to each gear order: {esc("; ".join(f"{name}'s {hz:.0f} Hz: {nearest[name]:.0f} Hz ({f'{100 * gaps[name]:+.1f}'.replace('-', '−')} %)" for name, hz in fe["mesh_hz"].items()))}.{esc(thin_txt)}</p>
</section>
{f'<section><h2>Each half along its pull</h2><figure><img src="{pics["faces"]}" alt="Both halves seen from outside along the casting pull"><figcaption>The cover (left) and the motor side (right), each from outside along its pull.{look_note}</figcaption></figure></section>' if "faces" in pics else ""}
{f'<section><h2>The whole housing</h2><figure><img src="{pics["views"]}" alt="The housing from four cameras"><figcaption>Both halves from four cameras.{look_note}</figcaption></figure></section>' if "views" in pics else ""}
<section>
  <h2>What to draw, and where</h2>
  {f'<figure><img src="{pics["map"]}" alt="Plan of each half with features and members marked"><figcaption>Each half from outside along its pull. Blue circles: {"the protected bearing bosses" if towers else "each bearing&#39;s boss circle (its seat&#39;s 4 mm ring is fixed; the boss inside the circle is the members&#39; metal)"} (labelled with their diameter); cyan: the bolts&#39; bosses. Coloured lines: the members, by kind; grey: the metal standing beyond the 4 mm wall, in mm.</figcaption></figure>' if "map" in pics else ""}
  {f'<figure><img src="{pics["reading"]}" alt="Each half with its ribs drawn as straight runs labelled width by deep height, and its arms and networks hatched"><figcaption>The members as a designer would draw them. Each centre-line is simplified to straight runs (within 6 mm), each run as wide as the metal nearest it. Coloured: ribs, webs and gussets, each run labelled width × its deep height off the wall in mm (the 90th percentile of its metal&#39;s heights). Hatched: arms and networks, drawn as the field mesh has them. Every run&#39;s ends, width and heights are in <code>member_map_{esc(design)}.json</code> and <code>.md</code>.</figcaption></figure>' if "reading" in pics else ""}
  <h2>Protected features</h2>
  <p>Fixed in the optimisation and held exact in the field. Draw them at these sizes; the bores, holes and the split face are machined.</p>
  {f'<p>The bearing bosses stand as towers from their seats to the split face ({towers[0]:.2f} kg, of it {towers[1]:.2f} kg between the seats and the split), because each half is cast with its parting at the split face. Where a boss is wider than its gear room, the space above it, beside the room&#39;s wall, could only be formed by a die stepping down from the split. With a stepped parting line, or a core from the split side, that metal can be cored out; judge the result again.</p>' if towers else ""}
  <div class="scroll"><table>
    <tr><th>Half</th><th>Feature</th><th>Of</th><th>Centre (mm)</th><th>Size (mm)</th></tr>
    {"".join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td class="num">{esc(d)}</td><td>{esc(e)}</td></tr>' for a, b, c, d, e in feat_rows)}
  </table></div>
  <h2>Members</h2>
  <p>Read from the optimiser's own field: each connected piece of metal standing at least 4 mm beyond the wall, with its main direction, length, width, height off the wall and what it meets. Coordinates are in the housing's frame, in mm, seen along the pull (the intermediate shaft's axis at x = 0, y = 0; the split face at z = {rec["z"]["split"]:.2f}).</p>
  <ul>
    <li><b>Arm:</b> any member that reaches a mount lug; draw it as a bracket of ribs from the lug to what it meets.</li>
    <li><b>Network:</b> a member with three or more ends; draw one rib along each branch of its centre-line (the map's lines).</li>
    <li><b>Rib:</b> at most 14 mm wide and at least 2.5 times as long as wide.</li>
    <li><b>Gusset:</b> shorter than 25 mm, at a boss or a bolt's boss.</li>
    <li><b>Web:</b> wider than a rib; a flat-topped plate.</li>
  </ul>
  <div class="scroll"><table>
    <tr><th>Id</th><th>Half</th><th>Kind</th><th>Along (mm)</th><th>Length</th><th>Width</th><th>Height (median / most)</th><th>Shape</th><th>Meets</th></tr>
    {"".join(f'<tr><td class="num">{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td class="num">{esc(d)}</td><td class="num">{esc(e)}</td><td class="num">{esc(f_)}</td><td class="num">{esc(g_)}</td><td>{esc(h_)}</td><td>{esc(i_)}</td></tr>' for a, b, c, d, e, f_, g_, h_, i_ in mem_rows)}
  </table></div>
</section>
{f'<section><h2>Drawn differently: what holds</h2><p>The same field drawn otherwise (another grid or smoothing), or the reading put back into the field (<code>reading_field.py</code>: under each run&#39;s footprint the metal stands at the run&#39;s height and nowhere else; the walls and the protected features unchanged), each judged by FE as any design.</p><div class="scroll"><table><tr><th>Drawn as</th><th>Mass</th><th>Worst seat</th><th>Tilt</th><th>First mode</th><th>Orders</th><th></th></tr>{"".join(tests_rows)}</table></div><ul>{"".join(tests_notes)}</ul></section>' if tests_rows else ""}
{f'<section><h2>How the shape was found</h2><ul>{"".join(f"<li>{esc(t_)}</li>" for t_ in how)}</ul></section>' if how else ""}
<section>
  <h2>Drawing directions</h2>
  <ol>
    <li>Take the protected features first, at the sizes above: {"the bearing bosses as round towers from their seats down to the split face" if towers else "each bearing seat&#39;s 4 mm ring in the shell (the bosses round them are the members&#39;)"}, the sealing land and the bolts&#39; bosses a flange thick, the mount lugs{spoke_txt}.</li>
    <li>Draw the walls 4 mm thick round each gear room, following the rooms (round lobes, flat end walls), with the sealing land at the split.</li>
    <li>Add the members from the reading and the map, keeping their layout: their positions, directions, widths and heights carry the bearing lines. Draw each rib, web and gusset as straight runs of the listed width at its deep height, joined where the runs meet. Draw each arm and network as the field mesh has it: their depth varies, deepest at the lugs and where the members meet.{" A web from each lug spans the lug&#39;s length." if webs_f else ""}</li>
    <li>Finish for casting: draft along each half&#39;s pull, fillets at every root (about 1 to 1.25 times the thinner leg), rounded rib tops.</li>
    <li>Judge the CAD again by FE against the same lines; the field mesh&#39;s numbers above are the reference to keep.</li>
  </ol>
</section>
<section>
  <h2>Files on the laptop</h2>
  <ul>
    {"".join(f'<li><code>data/first_loop/{esc(f_)}</code> and the indexed <code>.ply</code> beside it</li>' for f_ in files)}
    <li><code>data/first_loop/member_map_{esc(design)}.json</code> and <code>.md</code>: the features and members above</li>
    <li><code>{esc(record)}</code>: how it was made, every iteration with its numbers</li>
  </ul>
</section>
</div>
"""
    out.write_text(page, encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The hand-over page for a CAD designer (LOP-28).")
    ap.add_argument("design")
    ap.add_argument("--out", default="")
    ap.add_argument("--look", default="", help="(LOP-30) the pictures from another drawing of the same fields, e.g. on 1 mm")
    ap.add_argument("--record", default="docs/features/loop/2026-10-13-record-overnight.md", help="the record of how it was made")
    a = ap.parse_args()
    main(a.design, Path(a.out) if a.out else OUT / f"handover_{a.design}.html", a.look, a.record)
