"""PROTOTYPE (LOP-29) - every design since the empty-start baseline (12 October, LOP-27) in one table, for the engineer's
review (13 October 21:35: "a table of all these runs, starting from the empty start, the baseline which was passing, and then
step by step every iteration that was performed and why it was performed... with a picture of that run"):
- each design's change, why it was run (from the records written as it ran: `2026-10-12-record-evening.md`,
  `2026-10-13-record-overnight.md`, the LOP-29 cell and `lop29_log.py`), and what it showed;
- its FE result from its own records (`flow_<design>.json`'s grade, `oiltight_<design>.json`), never typed here;
- both halves along the pull (`look_face_<design>.png`);
- the engineer's words that turned the campaign, between the runs.
Writes the page (index.html, its pictures in img/) for the Artifact, and the same table as markdown for the loop's records
(`docs/features/loop/2026-10-13-iterations.md`).

Run: .venv/Scripts/python.exe prototypes/first_loop/iterations_page.py <page folder>"""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "first_loop"
DOC = ROOT / "docs" / "features" / "loop" / "2026-10-13-iterations.md"

# ("phase", title, what it was) | ("turn", when, who, words, what followed) | ("run", design, changed, why, showed[, no-FE reason])
ROWS = [
    ("phase", "12 October, evening: the empty start (LOP-27)", "No fixed shell: the optimiser grows the walls and the members from the contract's interfaces."),
    ("turn", "12 Oct 19:30-20:22", "the engineer", "The design space is fixed in every iteration (D16). \"Do an empty start.\"",
     "One world for the whole as-cast housing: no crisp CAD shell with organic metal laid on it."),
    ("run", "empty1_5.5kg",
     "The empty start: only the seats' rings, the mounts and the bolts' bosses fixed; walls at least 4 mm and every member grown by "
     "the optimiser; its plan smoothing 6 mm; drawn plainly.",
     "To remove the two worlds: the optimiser thickens the wall itself where it needs stiffness.",
     "Passes every line. Clear, straight members; octagonal steps; lumps where loads meet. You liked it (22:27): the baseline."),
    ("turn", "12 Oct 21:00", "the engineer", "\"I need to see the smoothing and effect of that as compared to the current.\"",
     "Three smoothings of the same field, after the run."),
    ("run", "empty1_faithful_5.5kg", "The same field drawn smooth but faithful: the surface's distance read at the 4 mm cubes' centres, "
     "interpolated, the volume kept.", "To see the effect of smoothing.",
     "The same stiffness and mass, but the facets stay and ripple into undercuts (4.7 %): smoothing after the run does not fix the look."),
    ("run", "empty1_s8_5.5kg", "The same smoothing from 8 mm samples.", "A smoother surface from coarser samples.",
     "A 4 mm wall opened: the inside leaks.", "not judged: its drawing leaks"),
    ("run", "empty1_r4_5.5kg", "The same smoothing with a damped fit.", "To stop the ripples.",
     "Looks like the plain drawing: nothing gained.", "not judged: it looked as the plain drawing"),
    ("turn", "12 Oct 21:10", "the engineer", "\"First 2 and then 1 on top of it.\"",
     "2: smoothness inside the optimiser (its plan smoothing 12 mm). 1: the least walls drawn exact, in the same field."),
    ("run", "empty2_hf12_5.5kg", "The optimiser's own plan smoothing 12 mm instead of 6.", "Smoothness from the optimiser, not after it.",
     "Neighbouring ribs merged into lumps; the seats a third softer; the tilt fails by 2 %."),
    ("run", "empty2_exact_5.5kg", "On that 12 mm field, the least walls drawn exact: smooth, from the exact inside.",
     "The shell as an exact function in the same field.", "Round lobes and bosses at no stiffness cost: a big gain in look. The tilt still fails (the 12 mm field's)."),
    ("run", "empty1_exact_5.5kg", "The baseline's 6 mm field with the exact walls.", "The exact walls on the field that passed.",
     "Round lobes, but the bearing tubes drawn 4 mm where the optimiser had about 6: the seats 11 % softer, a mode by s1."),
    ("turn", "12 Oct 22:27-23:02", "the engineer and a reviewer", "\"I am liking this baseline.\" The optimiser lays out the members; then passes "
     "clean one area at a time, each form sized by the optimiser.", "Three cases first, each the baseline with one change."),
    ("run", "case1_least_5.5kg", "The least metal that holds every line (and, by mistake, the beds held at 1/1.5: two changes).",
     "Case 1: is the lumps' metal needed?", "Not a clean test: two changes at once. Passes; its members bigger."),
    ("run", "case2_max12_5.5kg", "A cap: no member over 12 mm, read near its worst spot.", "Case 2: does a thickness cap turn lumps into ribs?",
     "The patches 19-34 % smaller, but the lumps become a knotted network with holes. A cap is not a form."),
    ("run", "case3_web_5.5kg", "The cover's patch between the intermediate and output bearings glued into one flat web, its thickness the optimiser's.",
     "Case 3: does a clean form cost stiffness?", "The drawing lost mount-3 (a thin arm read at 0.5), so FE held it on two mounts: "
     "not the design's judgement. A drawing that loses a mount now stops."),
    ("run", "case1b_least_5.5kg", "Case 1 done right: the least metal, the baseline's own factors.", "Case 1 without the mistake.",
     "Lighter (5.37 kg) but fails the tilt and two modes: the lumps' metal is needed."),
    ("run", "empty1_l40_5.5kg", "The baseline drawn with its members read at 0.4.", "A fair comparison with case 3, which needed 0.4 to keep its mount.",
     "Two modes moved into the bands from the drawing alone: a clash within 3 % is the drawing's noise."),
    ("run", "case3_web_l40_5.5kg", "Case 3 drawn at 0.4.", "Case 3 judged on all three mounts.",
     "The patch became one 31 mm slab; the seats 24 % softer, the first mode a third lower; the metal came from the brackets. "
     "A clean form has to follow the load."),
    ("phase", "13 October, night: the overnight campaign (LOP-28)", "A production-quality housing a CAD designer can start from, every line passing."),
    ("turn", "13 Oct 00:16", "the engineer", "\"Go step by step... until we achieve a good production quality shape that we can hand over to CAD engineer.\"",
     "A reviewer's order: region rules first, the least mass with every rule active, one change at a time."),
    ("run", "sem1_5.5kg", "Region rules in the optimiser: each region's bending or curvature bounded (the bridges, the bosses' rings, the panels), "
     "and each bracket's least metal.", "Step 1: calm the lumps and wrinkles region by region.",
     "Almost free (+0.8 % compliance), but the look barely changed: the drawing's 4 mm steps hide the calmer heights."),
    ("run", "empty1h_5.5kg", "The baseline drawn from the optimiser's continuous heights, not whole 4 mm cubes.", "To see the rules' effect without the steps.",
     "No staircase, but cliffs along the rooms' outlines, and the tilt 6 % over: not better."),
    ("run", "sem1h_5.5kg", "sem1 drawn from its continuous heights.", "The same comparison for sem1.",
     "Its drawing leaked and lost mounts (a fault of the height drawing, fixed).", "not judged: its drawing leaked"),
    ("turn", "13 Oct 00:50", "the engineer", "\"I don't think there is an improvement... prevent the optimiser from deforming surfaces that have a "
     "defined engineering purpose.\"", "Protect the functional geometry first; the curvature penalties paused."),
    ("run", "prot1_5.5kg", "The functional geometry protected: the bearing bosses, the sealing land, the bolts' bosses and the lugs fixed, drawn "
     "exact (fused as CAD).", "Seats stay cylindrical, faces flat; the optimiser free round them.",
     "Crisp interfaces, but the bosses overhung the lobes (undercut 3.8 / 5.7 %), it leaked, and the tilt failed."),
    ("run", "prot2_5.5kg", "The bosses clipped to their lobes.", "Stop the overhang.",
     "The drawing lost mount-2 (its bracket starved, 65 → 13 cm³) and leaked: protecting at a fixed budget takes metal from the brackets.",
     "not judged: its drawing lost mount-2"),
    ("run", "prot3_least", "Each bracket's least metal, and the least metal that holds every line (at 1/1.25), together.",
     "P2 could not hold the lines at 5.5 kg; you (00:19): \"minimise mass but without compromising with the objective\".",
     "In the model 5.85 kg with every line held. The CAD-fused parts meshed past FE's memory.", "not judged: FE stopped by the memory guard"),
    ("turn", "13 Oct 01:20-01:30", "the engineer", "\"You should have built it in field only.\" A field-mesh housing, with clear direction to a CAD "
     "designer about the members to draw.", "No CAD fusion: the protected parts become densities in the same field."),
    ("run", "prot3f", "P3's field drawn with the protected parts as densities in the field, the least walls exact.", "Everything in one field.",
     "The most production-like look so far, but the tilt 1.26: the bosses clipped to the lobes had become 4 mm tubes."),
    ("run", "prot3v", "P3 drawn with the optimiser's own voxel walls.", "How much of the tilt the exact walls cost.",
     "Tilt 1.04: the exact walls cost a fifth of that seat's tilt; even the heavier drawing misses."),
    ("run", "prot4_least", "Each boss a castable tower, from past its seat down to the split, in the optimiser and the field.",
     "No more tubes: round bosses standing on the split as cast bosses do.", "The most production-like so far; the tilt 1.04 and two modes in the bands."),
    ("run", "prot5_least", "The cover's input seat held at 1/1.4, its own factor.", "FE read that seat 26-30 % softer than the model.",
     "No change: the seat that governs is the motor side's intermediate seat (`seat_ratios.py`)."),
    ("run", "prot6_least", "The motor side's intermediate seat held at 1/1.4 instead.", "FE reads it 1.3 times softer than the model.",
     "Every static line passes; one mode at 2498 Hz, in s1's band."),
    ("turn", "13 Oct 01:54", "the engineer", "\"Compare the pictures... what are those basic rules which they follow, which ours are not following.\"",
     "Production's rules, each tried as a constraint: plain walls, one-way curvature, thin spaced members."),
    ("run", "rule1_wall", "Plain walls: beyond a wall's least height, either nothing or a member at least 6 mm tall.", "Production's walls are plain between ribs.",
     "The look unchanged, the seats 31 % softer: dropped."),
    ("run", "rule2_dev", "Every surface curving one way at most (its double curvature at most half P5's).", "Production's surfaces curve one way.",
     "Free, but the look nearly the same: the loops and blobs are the members' layout in plan, not their heights."),
    ("run", "rule3_thin", "Thin, spaced members: at most 8 mm wide, 20 mm apart, in plan.", "Production's thin ribs.",
     "Infeasible at the least mass: the members carrying the brackets and bridges need more.", "not judged: the optimisation stopped, infeasible"),
    ("run", "final1", "P6 with a floor of 100 cm³ on the cover's bridge between the intermediate and output bores.",
     "Lift the mode out of s1's band by stiffening the cover between those bores.", "The mode moved 10 Hz of the 77 needed: it is the cover's panel flexing."),
    ("run", "rule3b_thin", "Thin, spaced members again, at a fixed 7.2 kg with room to spare.", "Perhaps thin members fit with spare mass.",
     "Still infeasible on this layout.", "not judged: the optimisation stopped, infeasible"),
    ("run", "p6spk", "P6's field drawn with production's panel spokes on both halves, which the optimiser did not know.",
     "Spokes stiffen panels, and the clashing mode is a panel's.", "The tilt worse (1.19): spokes the optimiser did not know unbalanced the seats. "
     "They must be in the optimisation."),
    ("run", "final2", "Production's spokes fixed on the cover in the optimisation (every 30°, 6 mm thick, 12 mm proud: values I set); the "
     "intermediate seat at 1/1.5.", "The optimiser sizes everything round the spokes.",
     "Production's spoke wheel on the cover; every line passes but one mode, at 2440 Hz."),
    ("run", "final3", "The spokes 14 mm tall.", "Lift that mode.", "The mode did not move: the cover's panel is not where it is decided."),
    ("run", "final4", "The spokes on both halves.", "The motor side's input bore carries a fifth of the mode.", "The mode up 70 Hz, still in the band, for 0.45 kg."),
    ("run", "final5", "Every line at 1/1.2 (lighter).", "Does a lighter housing move the mode?", "No."),
    ("run", "final6", "Mount-3's bracket at least 70 cm³.", "Mount-3 carries 11 % of the mode.", "The mode down 7 Hz: the bracket acts as a tuning mass."),
    ("run", "final7", "Mount-3's bracket at least 110 cm³.", "More tuning mass.", "The first design to pass every line (the mode 3.2 % clear of s1's band)."),
    ("run", "final8", "Mount-3's bracket at least 150 cm³.", "More margin on that mode.", "Another mode fell into s2's band: the window is narrow."),
    ("run", "final9", "The no-lump cap (no section over 16 mm), read as an average.", "Thin the lumps where the members meet.",
     "The cap never bound, and a near-identical field put the mode back in s1's band: final7's margin was the drawing's noise."),
    ("run", "final10", "The cap read near its worst spot.", "Make the cap hold at the junctions.",
     "Passes every line; the junctions thinner; mount-3's floor spread into thin struts."),
    ("run", "final10r", "The designer's reading put back as a design: every member a straight run at its median height.",
     "Is the hand-over's simplified drawing safe to build?", "No: mount-3's bracket lost its depth (151 µm)."),
    ("run", "final10ra", "The reading, the arms to the lugs kept as the field has them.", "Which members can be simplified?", "Still too soft."),
    ("run", "final10rn", "The reading, the arms and the networks kept as the field.", "Which members can be simplified?", "Still too soft."),
    ("run", "final10rz", "Every member kept, only the crumbs gone, a web added at each lug.", "Do the crumbs matter?",
     "Passes: the crumbs do not matter; the members' heights do."),
    ("run", "final10rp", "Ribs, webs and gussets as straight runs at their deep height (90 %), arms and networks as the field.",
     "A drawing rule a designer can follow.", "Every static line holds, for 0.3 kg; a mode by s2."),
    ("run", "final10rd", "Every member at its deep height.", "The same rule for everything.", "Over the reference's mass."),
    ("run", "final10_l50", "final10's own field drawn thinner (members read at 0.5).", "How much margin rests on the thin members?",
     "The tilt and a mode fail: the margins lean on members one cube wide."),
    ("run", "final11", "Every line at 1/1.3.", "More margin.", "One mode clears s1, another falls into s2's band."),
    ("run", "final12", "Every line at 1/1.45.", "More margin.", "s1 clear by 8.7 %; a mode still 0.6 % inside s2's band."),
    ("run", "final13", "final12 with mount-3's floor back at 50.6 cm³.", "Does mount-3 still need its 110 cm³?",
     "58 µm and a 372 Hz mode: the floor is structural, not only a tuning mass."),
    ("run", "final14", "Production's gusseted lugs fixed (two 8 mm webs a lug: values I set), in place of the bracket floors.",
     "The brackets were the least production-like part, and their floors were structural.",
     "Every mode far from the orders (first mode 868 Hz); the tilt 1.03."),
    ("run", "final15", "The intermediate seat at 1/1.65.", "Bring the tilt under its line.", "Tilt 1.003: the seat's own factor alone barely moves FE."),
    ("run", "final16", "Every line at 1/1.3, the intermediate seat at 1/1.65.", "Margin on every line.",
     "The hand-over: every line passes, the modes 12-14 % from the orders."),
    ("run", "final16_l50", "final16's field drawn thinner (0.5).", "How much rests on thin members?", "Tilt 1.018: only the tilt leans on them."),
    ("run", "final16rp", "The drawing rule on final16's field (ribs, webs, gussets at their deep heights).", "The rule on the hand-over.",
     "Every line with margin, at the reference's mass."),
    ("run", "final17", "Every line at 1/1.35.", "More margin on the tilt.", "Each step of the factor buys less."),
    ("run", "final17_l50", "final17 drawn thinner.", "The same check.", "Tilt 1.000."),
    ("run", "final18", "A floor of 60 cm³ on the motor side's bridge between the input and intermediate bores.", "Support that seat directly.",
     "Tilt 0.917 for 0.11 kg."),
    ("run", "final18_l50", "final18 drawn thinner.", "The same check.", "Tilt 1.012: thin members still carry the last margin."),
    ("phase", "13 October, evening: the modes in the optimiser (LOP-29)", "Your test: asked for final16's performance with free brackets, does the optimiser deliver them?"),
    ("turn", "13 Oct 09:33-17:45", "the engineer", "D17: \"the dimensions, orientations, placement, thickness, height... should be derived from "
     "optimization and not guessed by you.\" \"Modes far from the gear orders - you can keep in optimization.\" \"Straight brackets should be a result.\"",
     "final16's spokes and lugs (set by hand) are a reference, not a result."),
    ("turn", "13 Oct 18:38-19:24", "the engineer", "\"I want simple\": the flange 8 mm in the contract, every fixed cube whole. Modes in the optimiser now; "
     "everything visible on the UI.", "The model's own modes had been the flange's partly filled cubes flapping."),
    ("run", "lop29_modes", "The modes held in the optimiser (12 % gap round each gear order); free, no patterns; the contract's interfaces fixed; "
     "the least mass at 1/1.25, the intermediate seat at 1/1.5.", "Your test.",
     "In the model every line held; in FE it fails. The drawing's blur had lost 10 % of the field's metal."),
    ("turn", "13 Oct 20:12", "the engineer", "\"Yes do option 1.\"", "The drawing keeps every metal cube of the field, checked before FE."),
    ("run", "lop29_keep", "The same field drawn keeping every metal cube.", "FE must judge what the optimiser placed.",
     "Far stiffer (53 µm), but the look shows the raw 4 mm cubes; the tilt still fails."),
    ("run", "lop29_exact", "The same field, the walls drawn exactly 4 mm.", "The 2 mm grid had drawn the floor above the motor side's intermediate seat "
     "4.9 mm, which tipped that seat.", "The tilt and the modes pass; the worst seat 6 % over."),
    ("turn", "13 Oct 20:31", "the engineer", "\"Keep clear is just the mount height and not any higher. We can change the contract.\"",
     "Each mount's kept-clear room 30 mm beyond each face, where it had run up the whole housing."),
    ("run", "lop29_clear", "A new run: the optimiser keeps clear what the drawing keeps clear (the bolts' holes and sockets, 2 mm margins), the "
     "towers whole cubes, the mounts' rooms 30 mm.", "6.8 % of the optimiser's metal had stood where the drawing must keep space.",
     "The drawing is now the field, but the optimiser stripped mount-1's bracket (23.6 → 2.5 cm³): the housing swings at 175 Hz. Its model "
     "glues the flanges at the bolts, which FE does not."),
]


def record(d: str) -> dict:
    """The design's numbers from its own records: the grade (flow), oil-tightness, when it was judged."""
    flow, tight, face = OUT / f"flow_{d}.json", OUT / f"oiltight_{d}.json", OUT / f"look_face_{d}.png"
    g = json.loads(flow.read_text(encoding="utf-8")).get("grade") if flow.exists() else None
    t = json.loads(tight.read_text(encoding="utf-8")) if tight.exists() else None
    when = datetime.fromtimestamp((face if face.exists() else flow if flow.exists() else tight).stat().st_mtime) if (face.exists() or flow.exists() or tight.exists()) else None
    if not g:
        return {"graded": False, "tight": None if t is None else bool(t["tight"]), "when": when, "face": face.exists()}
    lines = g["lines"]
    disp, tilt, orders, mass = (lines["displacement, peak drive"], lines["misalignment (worst seat against its line)"], lines["orders"], lines["mass"])  # fmt: skip
    return {"graded": True, "kg": g["mass_kg"], "kg_pass": mass["pass"], "seat": disp["value_um"], "seat_to_beat": disp["to_beat_um"],
            "seat_pass": disp["pass"], "tilt": tilt["ratio"], "tilt_pass": tilt["pass"], "clashes": len(orders["clashes"]),
            "orders_pass": orders["pass"], "mode1": g.get("first_mode_hz"), "pass": bool(g["pass"]) and (t is None or bool(t["tight"])),
            "tight": None if t is None else bool(t["tight"]), "when": when, "face": face.exists()}  # fmt: skip


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def code(s: str) -> str:
    """`x` as <code>x</code>, the rest escaped."""
    parts = s.split("`")
    return "".join(f"<code>{esc(p)}</code>" if i % 2 else esc(p) for i, p in enumerate(parts))


def chip(text: str, ok: bool | None) -> str:
    cls = "chip" + ("" if ok is None else " ok" if ok else " bad")
    return f'<span class="{cls}">{esc(text)}</span>'


def write_page(folder: Path) -> None:
    from PIL import Image

    (folder / "img").mkdir(parents=True, exist_ok=True)
    body, phase_id, n_runs, n_pass, rows_md = [], 0, 0, 0, []
    for row in ROWS:
        kind = row[0]
        if kind == "phase":
            phase_id += 1
            body.append(f'<tbody class="phase" data-phase="p{phase_id}"><tr><th colspan="7" scope="rowgroup"><span class="ph-title">{esc(row[1])}</span>'
                        f'<span class="ph-note">{esc(row[2])}</span></th></tr></tbody><tbody data-phase="p{phase_id}">')  # fmt: skip
            rows_md.append(f"\n## {row[1]}\n\n{row[2]}\n\n| # | Run | What changed | Why | kg | Worst seat µm | Tilt × | First mode Hz | Orders | Oil-tight | Verdict | What it showed |\n|---|---|---|---|---|---|---|---|---|---|---|---|")  # fmt: skip
            continue
        if kind == "turn":
            _, when, who, words, followed = row
            body.append(f'<tr class="turn" data-phase="p{phase_id}"><td class="num"></td><td colspan="6"><span class="t-when">{esc(when)}</span> '
                        f'<span class="t-who">{esc(who)}</span><q>{esc(words)}</q><span class="t-then">{code(followed)}</span></td></tr>')  # fmt: skip
            rows_md.append(f"| | **{when}, {who}** | {words} | {followed} | | | | | | | | |")
            continue
        _, d, changed, why, showed, *rest = row
        no_fe = rest[0] if rest else None
        r = record(d)
        n_runs += 1
        n_pass += int(r.get("pass", False))
        img = ""
        if r["face"]:
            im = Image.open(OUT / f"look_face_{d}.png").convert("RGB")
            im.thumbnail((1200, 600), Image.LANCZOS)
            im.save(folder / "img" / f"{d}.jpg", quality=80, optimize=True)
            img = (f'<button class="pic" type="button" data-full="img/{esc(d)}.jpg" data-cap="{esc(d)}: the cover (left) and the motor side (right), '
                   f'along the pull"><img src="img/{esc(d)}.jpg" alt="{esc(d)}, both halves along the pull" loading="lazy" width="1200" height="600"></button>')  # fmt: skip
        when = r["when"].strftime("%d %b %H:%M") if r["when"] else ""
        if r["graded"]:
            res = " ".join([
                chip(f"{r['kg']:.2f} kg", r["kg_pass"]),
                chip(f"seat {r['seat']:.1f} µm", r["seat_pass"]),
                chip(f"tilt {r['tilt']:.2f}", r["tilt_pass"]),
                chip("orders clear" if r["clashes"] == 0 else f"{r['clashes']} in a band", r["orders_pass"]),
                chip(f"1st mode {r['mode1']:.0f} Hz", None) if r.get("mode1") else "",
                chip("oil-tight" if r["tight"] else "leaks", r["tight"]) if r["tight"] is not None else "",
            ])  # fmt: skip
            verdict = '<span class="verdict pass">passes</span>' if r["pass"] else '<span class="verdict fail">fails</span>'
            md_nums = (f"{r['kg']:.2f} | {r['seat']:.1f} | {r['tilt']:.3f} | {r['mode1']:.0f} | "
                       f"{'clear' if r['clashes'] == 0 else str(r['clashes']) + ' in a band'} | {'yes' if r['tight'] else 'no' if r['tight'] is not None else '-'} | "
                       f"{'passes' if r['pass'] else 'fails'}")  # fmt: skip
        else:
            res = chip(no_fe or "not judged", None) + (" " + chip("oil-tight" if r["tight"] else "leaks", r["tight"]) if r["tight"] is not None else "")
            verdict = '<span class="verdict none">no FE</span>'
            md_nums = f"- | - | - | - | - | {'yes' if r['tight'] else 'no' if r['tight'] is not None else '-'} | {no_fe or 'not judged'}"
        status = "pass" if r.get("pass") else ("none" if not r["graded"] else "fail")
        body.append(f'<tr class="run" data-phase="p{phase_id}" data-status="{status}" id="{esc(d)}"><td class="num">{n_runs}</td>'
                    f'<td class="name"><code>{esc(d)}</code><span class="when">{esc(when)}</span>{verdict}</td>'
                    f"<td>{code(changed)}</td><td>{code(why)}</td><td class=\"res\">{res}</td><td>{code(showed)}</td><td class=\"img\">{img}</td></tr>")  # fmt: skip
        rows_md.append(f"| {n_runs} | `{d}` ({when}) | {changed} | {why} | {md_nums} | {showed} |")
    page = PAGE.replace("{{ROWS}}", "\n".join(body) + "</tbody>").replace("{{N_RUNS}}", str(n_runs)).replace("{{N_PASS}}", str(n_pass))
    (folder / "index.html").write_text(page, encoding="utf-8")
    DOC.write_text(MD_HEAD.format(n_runs=n_runs, n_pass=n_pass) + "\n".join(rows_md) + "\n", encoding="utf-8")
    print(folder / "index.html", n_runs, "designs,", n_pass, "pass every line;", DOC)


MD_HEAD = """# Every design since the empty start, 12-13 October

**13 October 2026, 21:45.** Each design from the empty-start baseline (`empty1_5.5kg`, 12 October) to LOP-29's `lop29_clear`:
what changed, why it was run, FE's result from its own records and what it showed; the engineer's words that turned the
campaign between the runs. {n_runs} designs; {n_pass} pass every graded line (the worst seat at most 52.2 µm, the tilt at most
1.0 × its line, no mode within 3 % of a gear order, at most 7.73 kg, oil-tight). Written by
`prototypes/first_loop/iterations_page.py`, which also writes the page with each design's two halves pictured (an Artifact).
Before it: [the evening's record](2026-10-12-record-evening.md), [the overnight record](2026-10-13-record-overnight.md).
"""

PAGE = """<title>Reducer Housing Iterations</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600&family=IBM+Plex+Mono:wght@400;500&family=Source+Sans+3:wght@400;600&display=swap">
<style>
/* Layout: a drawing-register ledger. A title block on top (the goal's lines and the counts), then one wide table grouped by
   phase, the engineer's words as separator rows, each design's two halves in its last column; chips filter the phases. */
:root {
  --bg: #eef1f4; --sheet: #ffffff; --ink: #1b2430; --muted: #5a6776; --rule: #d3dae2; --rule-strong: #9aa8b7;
  --accent: #245b86; --accent-soft: #e2ecf5; --turn: #f6f1e4; --turn-ink: #5b4a1c;
  --ok: #1d7347; --ok-soft: #e0f1e7; --bad: #a3271f; --bad-soft: #f8e3e1; --none: #6b7480; --none-soft: #eceff2;
  --f-display: "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
  --f-body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --f-data: "IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #11161c; --sheet: #182029; --ink: #e3e9ef; --muted: #9fadbb; --rule: #2b3642; --rule-strong: #4a5868;
  --accent: #8cbbe3; --accent-soft: #1d2d3d; --turn: #2a2618; --turn-ink: #e3d4a5;
  --ok: #7dd3a3; --ok-soft: #173326; --bad: #f19a92; --bad-soft: #3a1f1d; --none: #a7b0ba; --none-soft: #222b34; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #11161c; --sheet: #182029; --ink: #e3e9ef; --muted: #9fadbb; --rule: #2b3642; --rule-strong: #4a5868;
  --accent: #8cbbe3; --accent-soft: #1d2d3d; --turn: #2a2618; --turn-ink: #e3d4a5;
  --ok: #7dd3a3; --ok-soft: #173326; --bad: #f19a92; --bad-soft: #3a1f1d; --none: #a7b0ba; --none-soft: #222b34; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font: 15px/1.45 var(--f-body); }
.wrap { padding-inline: 16px; padding-block: 20px 40px; max-width: 1760px; margin: 0 auto; display: grid; gap: 16px; }
header.block { background: var(--sheet); border: 1px solid var(--rule-strong); display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); }
header.block > div { padding: 14px 18px; min-width: 0; }
header.block > div + div { border-left: 1px solid var(--rule-strong); }
h1 { font: 600 2.1rem/1.05 var(--f-display); letter-spacing: 0.01em; margin: 0 0 6px; text-wrap: balance; }
.sub { color: var(--muted); margin: 0; max-width: 62ch; }
.label { font: 500 0.72rem/1 var(--f-data); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.goal { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px 18px; margin-top: 8px; }
.goal div { display: grid; gap: 3px; }
.goal b { font: 500 1.05rem/1.2 var(--f-data); font-variant-numeric: tabular-nums; }
.counts { margin-top: 12px; color: var(--muted); }
.counts b { color: var(--ink); font-family: var(--f-data); }
.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.filters button { font: 600 0.85rem/1 var(--f-body); border: 1px solid var(--rule-strong); background: var(--sheet); color: var(--ink);
  padding: 7px 12px; border-radius: 999px; cursor: pointer; }
.filters button[aria-pressed="false"] { opacity: 0.45; text-decoration: line-through; }
.filters button:focus-visible, .pic:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.scroller { overflow-x: auto; background: var(--sheet); border: 1px solid var(--rule-strong); }
table { border-collapse: collapse; width: 100%; min-width: 1360px; }
thead th { position: sticky; top: env(safe-area-inset-top, 0px); background: var(--sheet); z-index: 1; text-align: left;
  font: 500 0.72rem/1.2 var(--f-data); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
  padding: 10px 10px; border-bottom: 2px solid var(--rule-strong); }
td { padding: 10px; vertical-align: top; border-bottom: 1px solid var(--rule); }
td.num { font: 500 0.85rem/1.4 var(--f-data); color: var(--muted); width: 2.4em; text-align: right; }
td.name { width: 11em; }
td.name code { display: block; font: 500 0.9rem/1.3 var(--f-data); color: var(--accent); word-break: break-all; }
.when { display: block; font: 400 0.78rem/1.4 var(--f-data); color: var(--muted); margin: 2px 0 6px; }
.verdict { font: 600 0.72rem/1 var(--f-data); letter-spacing: 0.06em; text-transform: uppercase; padding: 4px 7px; border-radius: 3px; display: inline-block; }
.verdict.pass { background: var(--ok-soft); color: var(--ok); }
.verdict.fail { background: var(--bad-soft); color: var(--bad); }
.verdict.none { background: var(--none-soft); color: var(--none); }
td code { font: 0.86em var(--f-data); }
td.res { width: 15em; }
.chip { display: inline-block; font: 500 0.78rem/1.25 var(--f-data); font-variant-numeric: tabular-nums; padding: 3px 6px; margin: 0 4px 4px 0;
  border-radius: 3px; background: var(--none-soft); color: var(--none); white-space: nowrap; }
.chip.ok { background: var(--ok-soft); color: var(--ok); }
.chip.bad { background: var(--bad-soft); color: var(--bad); }
td.img { width: 340px; }
.pic { display: block; padding: 0; border: 1px solid var(--rule); background: #ffffff; cursor: zoom-in; width: 320px; max-width: 100%; }
.pic img { display: block; width: 100%; height: auto; }
tbody.phase th { text-align: left; padding: 18px 10px 10px; border-bottom: 2px solid var(--accent); background: var(--accent-soft); }
.ph-title { display: block; font: 600 1.35rem/1.1 var(--f-display); color: var(--accent); letter-spacing: 0.01em; }
.ph-note { display: block; color: var(--muted); font-weight: 400; margin-top: 3px; }
tr.turn td { background: var(--turn); color: var(--turn-ink); border-bottom: 1px solid var(--rule); }
.t-when { font: 500 0.8rem/1.4 var(--f-data); margin-right: 6px; }
.t-who { font-weight: 600; margin-right: 6px; }
tr.turn q { font-style: italic; }
.t-then { display: block; margin-top: 3px; }
tr[hidden], tbody[hidden] { display: none; }
.lightbox { position: fixed; inset: 0; background: rgba(10, 14, 20, 0.86); display: grid; place-items: center; padding: 16px; z-index: 10; }
.lightbox figure { margin: 0; max-width: min(1400px, 100%); display: grid; gap: 8px; }
.lightbox img { width: 100%; height: auto; background: #ffffff; }
.lightbox figcaption { color: #e3e9ef; font: 500 0.9rem/1.4 var(--f-data); display: flex; justify-content: space-between; gap: 12px; }
.lightbox button { font: 600 0.85rem/1 var(--f-body); background: #e3e9ef; color: #11161c; border: 0; padding: 8px 12px; border-radius: 4px; cursor: pointer; }
@media (max-width: 760px) {
  header.block { grid-template-columns: minmax(0, 1fr); }
  header.block > div + div { border-left: 0; border-top: 1px solid var(--rule-strong); }
  h1 { font-size: 1.7rem; }
}
@media (prefers-reduced-motion: no-preference) { .pic img { transition: opacity 0.2s; } .pic:hover img { opacity: 0.85; } }
</style>
<div class="wrap">
  <header class="block">
    <div>
      <span class="label">EV two-stage reducer housing · LOP-27 to LOP-29</span>
      <h1>Reducer Housing Iterations</h1>
      <p class="sub">Every design from the empty-start baseline you liked (12 October) to the modes in the optimiser (13 October evening):
      what changed, why it was run, FE's result from the design's own records, and both halves along the pull. Your words that turned
      the campaign sit between the runs. Select a picture to enlarge it.</p>
      <p class="counts"><b>{{N_RUNS}}</b> designs · <b>{{N_PASS}}</b> pass every line · the hand-over is <a href="#final16"><code>final16</code></a></p>
    </div>
    <div>
      <span class="label">Every graded line, by FE (peak drive)</span>
      <div class="goal">
        <div><span class="label">Worst seat</span><b>≤ 52.2 µm</b></div>
        <div><span class="label">Tilt</span><b>≤ 1.0 × its line</b></div>
        <div><span class="label">Gear orders</span><b>no mode within 3 %</b><span class="label">s1 2500 Hz · s2 1127 Hz</span></div>
        <div><span class="label">Mass</span><b>≤ 7.73 kg</b></div>
        <div><span class="label">Inside</span><b>oil-tight</b></div>
      </div>
      <p class="sub" style="margin-top:10px">Green passes its line, red fails it, grey is neither (the first mode, or a run that was not judged).
      A design passes only when every line does.</p>
    </div>
  </header>
  <div class="filters" role="group" aria-label="Show or hide">
    <button type="button" id="f-p1" data-phase="p1" aria-pressed="true">12 Oct evening: the empty start</button>
    <button type="button" id="f-p2" data-phase="p2" aria-pressed="true">13 Oct night: the overnight campaign</button>
    <button type="button" id="f-p3" data-phase="p3" aria-pressed="true">13 Oct evening: LOP-29</button>
    <button type="button" id="f-pass" data-status="pass" aria-pressed="true">passes</button>
    <button type="button" id="f-fail" data-status="fail" aria-pressed="true">fails</button>
    <button type="button" id="f-none" data-status="none" aria-pressed="true">not judged</button>
    <button type="button" id="f-turn" data-turn="1" aria-pressed="true">your words</button>
  </div>
  <div class="scroller">
    <table>
      <thead><tr><th>#</th><th>Run</th><th>What changed</th><th>Why</th><th>Result (FE)</th><th>What it showed</th><th>Both halves: cover · motor side</th></tr></thead>
{{ROWS}}
    </table>
  </div>
</div>
<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true" aria-label="Enlarged picture">
  <figure><img id="lb-img" alt=""><figcaption><span id="lb-cap"></span><button type="button" id="lb-close">Close</button></figcaption></figure>
</div>
<script>
(() => {
  const shown = { p1: true, p2: true, p3: true, pass: true, fail: true, none: true, turn: true };
  const apply = () => {
    document.querySelectorAll("tbody.phase").forEach(tb => { tb.hidden = !shown[tb.dataset.phase]; });
    document.querySelectorAll("tr.run").forEach(tr => { tr.hidden = !(shown[tr.dataset.phase] && shown[tr.dataset.status]); });
    document.querySelectorAll("tr.turn").forEach(tr => { tr.hidden = !(shown[tr.dataset.phase] && shown.turn); });
  };
  document.querySelectorAll(".filters button").forEach(b => b.addEventListener("click", () => {
    const key = b.dataset.phase || b.dataset.status || "turn";
    shown[key] = !shown[key];
    b.setAttribute("aria-pressed", String(shown[key]));
    apply();
  }));
  const lb = document.getElementById("lightbox"), img = document.getElementById("lb-img"), cap = document.getElementById("lb-cap");
  let back = null;
  const close = () => { lb.hidden = true; img.removeAttribute("src"); if (back) back.focus(); };
  document.querySelectorAll(".pic").forEach(p => p.addEventListener("click", () => {
    back = p; img.src = p.dataset.full; img.alt = p.dataset.cap; cap.textContent = p.dataset.cap; lb.hidden = false;
    document.getElementById("lb-close").focus();
  }));
  document.getElementById("lb-close").addEventListener("click", close);
  lb.addEventListener("click", e => { if (e.target === lb) close(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !lb.hidden) close(); });
})();
</script>
"""


if __name__ == "__main__":
    write_page(Path(sys.argv[1]))
