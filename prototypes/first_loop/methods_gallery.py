"""PROTOTYPE (LOP-25) - the methods gallery: each method's housing, whole and along the pull, with its set-up (what is
fixed, the design space, what changes, the objective, the limits, the shape rules, the drawing) and what FE and the
castability check found, as one HTML file with its pictures inside (the engineer, 12 October 16:43-17:37).

    python prototypes/first_loop/methods_gallery.py      ->  data/first_loop/methods_gallery.html

Every number comes from a design's own records: its run's record (`topofree_*.json`), its flow (`flow_<design>.json`,
else its FE record and its row in the grade's table), its castability log, and its pictures: the whole housing
(`look_<design>.png`, from `look.py <design>`) and each half along the pull (`look_face_<design>.png`, from `look.py
<design> face`). The words on each card describe the method."""

import base64
import html
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "first_loop"
PAGE = OUT / "methods_gallery.html"
FROZEN_KG = 2.93  # the contract's fixed metal in the optimiser's model (contract_layout.py's fixed_exact_kg)
LUMP_MM = 16.0  # castable.py's lump gate: a member's largest section
E = html.escape

GROUPS = [
    ("free", "The free optimisation", "The reference: the optimiser free in the whole design space."),
    ("spaces", "Free optimisation in a chosen design space", "The agent restricts where metal may go; the optimiser stays free inside."),
    ("forms", "Production forms sized by the optimiser", "Production's forms laid where the free run's flow runs; the optimiser sizes them."),
    ("a2", "Approach 2: the first generators", "The plan's generators: C re-optimises under a rule, B rebuilds the members along their skeleton."),
    ("parts", "Production parts as the optimiser's variables", "Straight plates and rings at points the optimiser moves; it sizes and places them."),
    ("rules", "Shape rules inside the free optimisation", "The optimiser free, with rules against paint, lumps, worms and knots."),
    ("clean", "Cleaning the members after the run", "The plan's generator B done properly, on a member-like run."),
    ("cad9", "Parametric CAD built in CadQuery alone: the trade's grammar (9 October)",
     "A whole housing drawn in CadQuery from one recipe (`grammar.py <stem> <preset>`), with no optimiser: the massing (the "
     "outline, the motor side's levels, the cover) and the ribs, one preset a style, after six families of production "
     "housings. The grammar's sizes: one 6 mm wall, 1.5° draft, corners R6 inside and R12 outside, ribs 5 mm thick and 15 mm "
     "high (10 mm off a side wall) unless a preset says otherwise, bearing bosses 1.25·D + 10 standing 3 mm proud, a split "
     "flange 24 mm wide and 9 mm thick with M8 bolts every 80 mm, mounts Ø36. Every style has an ear rib from each mount to "
     "its nearest boss and a wheel of spokes inside the motor's ring. This is 9 October's set-up, before the contract's of "
     "10 October: it carries the motor's flange on the motor side. FE at 8 mm; graded today on peak drive, as every card."),
    ("cad", "Parametric CAD built in CadQuery alone: production's features (12 October)",
     "Production's features drawn as exact CAD from a recipe (flow D, `param_cad.py`) on the contract's exact shell: no "
     "optimisation sizes them; their sizes are the recipe's, the ribs' heights read from the production-forms run."),
]

RECIPE = "a recipe of production's features; its ribs' heights read from the production-forms run (`ln_6`, as `prod9_asis`)"
GRAMMAR = "a recipe of the trade's grammar, one style's preset (`grammar.py`)"
GRAMMAR_RULES = ("The grammar's: one 6 mm wall, ribs on the end faces only, where they come out of the mould (a pattern that "
                 "would run across the pull on a side wall is put on the end faces).")
GRAMMAR_DRAWING = "OCC exact B-rep (STEP) in CadQuery: the drafted shell with its corner fillets, bosses, flange and mounts, the ribs fused on."

D = {
    "it1_free_5.5kg": dict(group="free", title="The free height field (the benchmark)",
        method="One optimisation over the whole design space: every column of metal its own height, the stiffness maximised "
               "with every bearing's tilt and bed held.",
        space="Every free voxel within 24 mm of the shell (96,197 voxels of 4 mm); each column one run of metal from its wall or the split.",
        changes="Every column's height (one variable a column), smoothed over 6 mm in plan.",
        rules="None beyond the band and the height field (castable along the pull by construction).",
        drawing="The mesh route, drawn plainly: the field's surface by marching cubes on the exact shell, every exact cut.",
        seen="Passes every graded line. Thick paint spread over the walls and blobs round the seats: no foundry's shape."),
    "hp2_5.9kg": dict(group="spaces", title="Design volumes from the hard points (approach 1)",
        method="74 candidate regions from the hard points (a boss on each seat; strips 48 mm wide along the shortest path round "
               "the shell between two hard points); a selection (HiGHS) chose 35 of them, holding 84 % of the free run's metal; "
               "the optimiser free inside them, the least metal.",
        space="Only the 35 regions' cells (56 % of the free voxels; `hp1.npz`), each mount's and seat's own room always kept.",
        changes="Every column's height inside the regions.",
        rules="None beyond the regions, the band and the height field.",
        drawing="The mesh route, drawn plainly.",
        seen="Passes every graded line, 0.55 kg over the best; organic, every region filled to its edges."),
    "bore_ties_5.6kg": dict(group="spaces", title="Features sized round one bearing (the bore experiment)",
        method="The motor side's intermediate bore's region (within 77.5 mm of its axis, nearer its boss than any other's) "
               "given to explicit features the optimiser sizes: a cap (to 26 mm), the boss ring (26-37.5 mm), and four straight "
               "ties 8 mm wide out to 77.5 mm, towards the input bore, the output bore and mounts 1 and 2; the rest of the housing free.",
        space="The whole design space; in the bore's region only the features' columns, every other column there empty.",
        changes="The free columns' heights, and each feature's parameters (a ring's height; a tie's root and tip heights).",
        rules="In the region, only those features; elsewhere none beyond the band.",
        drawing="The mesh route, drawn plainly.",
        seen="Passes every graded line: one bore's patch regular and parametric, 0.29 kg over the free form; the rest organic."),
    "sf3_ribs_6.6kg": dict(group="forms", title="Ribs along the flow's own lines",
        method="The free run's skeleton across each half read as 107 straight ribs (8-24 mm wide), the bosses' rings and each "
               "section's thickness: 237 parameters the optimiser sizes.",
        space="The columns of those ribs, rings and sections (`sf2_cols.npz`); every other column empty.",
        changes="Each rib's root and tip heights, each ring's height, each section's thickness.",
        rules="Only those forms.",
        drawing="The mesh route, drawn plainly.",
        seen="Passes every graded line at 6.86 kg; lumpy (drawn from the 4 mm voxels)."),
    "prod9_asis": dict(group="forms", title="Production forms with free heights, drawn smooth",
        method="Production's forms laid where the free run's flow runs: a bridge between each pair of seats, straight ribs from "
               "the seats to the bolts and mounts, an annulus round each bore, radial gussets beside the side walls; within "
               "each form every column its own height.",
        space="Only the forms' columns (`ln6_cols.npz`); every other column held empty.",
        changes="Each form column's height.",
        rules="Only those forms; a column outside them holds nothing.",
        drawing="One smooth signed-distance body (`implicit_draw.py`): the exact, filleted shell, the forms as the optimiser "
                "left them, gusseted lugs at the mounts.",
        seen="A production-like layout, but the tops torn (each column its own height); one mode inside its 3 % band."),
    "prod19_asis": dict(group="forms", title="The same forms with production's panel ribs",
        method="As above, with radial ribs 6 mm thick, every 30°, 10 mm high, from each boss across the end walls' bare "
               "panels (production's panel rule).",
        space="As above (`ln6_cols.npz`).",
        changes="As above; the panel ribs are drawn, not sized.",
        rules="As above.",
        drawing="As above, with the panel ribs (`LOOP_PANEL_RIBS=1`).",
        seen="The panel ribs moved the cover's mode by the stage-2 order out of its band (1,149 to 1,206 Hz); the tilt 1.07 "
             "and a mode by stage 1's order remain."),
    "a2_c1": dict(group="a2", title="Generator C: the least member",
        method="The free height field again, with one rule: a column under 8 mm holds nothing, so thin layers of paint cost "
               "nothing and hold nothing.",
        space="The whole design space (as the benchmark).",
        changes="Every column's height.",
        rules="Least member 8 mm.",
        drawing="A smooth signed-distance surface (3 mm) on the exact, filleted shell (`LOOP_SDF=3`).",
        seen="No paint; passes the stiffness and the tilt; the metal gathered into lumps up to 38 mm thick, and a mode by "
             "stage 1's order."),
    "a2_b1": dict(group="a2", title="Generator B: the members along their skeleton",
        source="a reading of the benchmark's field (`it1_free_5.5kg`)",
        method="The benchmark's members thinned to their skeleton and rebuilt as round struts along it, each as wide as the "
               "field there (capped at 16 mm), twigs under 20 mm pruned.",
        space="No optimisation: the benchmark's field read.",
        changes="Nothing; a reading.",
        rules="Struts only.",
        drawing="Struts along the skeleton (`LOOP_SKELETON=1.0:20:16`) on the exact shell.",
        seen="Clean, sparse struts on bare walls, 3.3 times too soft: the load the paint carried went to no member."),
    "a2_bc": dict(group="a2", title="B then C: the optimiser inside B's members",
        method="Generator B's members (grown by one voxel) as the design space, re-optimised with the least member.",
        space="Only the cells of B's members, grown one voxel (`a2_bspace.npz`, 58,865 cells).",
        changes="Every column's height inside that space.",
        rules="Least member 8 mm.",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="Modes clear; the optimiser filled B's space back into lumps (37 mm); 19 % too soft."),
    "rf1_parts_6.4kg": dict(group="parts", title="Production parts, moved and sized (Refine)",
        method="The least-member run's members rebuilt as production parts: 84 members (straight plates 8 mm wide between two "
               "points: 20 ribs, 16 spokes, 14 belts, 13 fins, 7 links, 7 gussets, 4 arms, 3 ties) and 8 rings (3 bosses round "
               "the seats, at most the handbook's 1.25·D + 10 across, 3 towers, 2 seal bosses round the exits). The optimiser "
               "moves the points and sizes every part.",
        space="Only the parts' footprints: a column no part covers holds nothing.",
        changes="352 numbers: every point's place (sliding round a boss, along the outline, or free within 15 mm at an end "
                "and 12 mm at a knot), every member's root and tip heights, every ring's radius and height.",
        rules="Only production's parts; a part under 8 mm tall vanishes; where parts cross, the taller one sets the height.",
        drawing="The parts as plates with rounded tops and rings, on the exact, filleted shell (`LOOP_PARTS`).",
        seen="The most regular design that passes the stiffness and the tilt; one mode by stage 1's order; sparse beside production."),
    "rg20b_parts": dict(group="parts", title="Parts read from the gap-rule run",
        method="The 20 mm-gap free run's members read as parts (119 members: 40 belts, 20 fins, 16 spokes, 16 gussets, 15 "
               "ribs, 6 arms, 4 links, a tie and a rim; 7 rings), moved and sized as above; each part's own least height.",
        space="Only the parts' footprints.",
        changes="510 numbers: the points' places, the members' heights, the rings' radii and heights.",
        rules="As above.",
        drawing="As above (`LOOP_PARTS`).",
        seen="The reading kept the layout but lost stiffness: tilt 1.22 and two modes in their bands."),
    "rg20_free": dict(group="rules", title="Members a set width and gap apart (20 mm)",
        method="The free height field with the members' plan rule: in plan, no member wider than 8 mm and none closer than "
               "20 mm to the next; and the least member.",
        space="The whole design space.",
        changes="Every column's height.",
        rules="Least member 8 mm; plan width 8 mm, gap 20 mm (the rule's share 0.705 at the end, over its 0.5).",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="A production-like pattern (spokes round the cover's output bearing, links, rim ribs), drawn as wormy members; "
             "a loose piece at 142 Hz."),
    "mm12_free": dict(group="rules", title="Members between 8 and 12 mm thick",
        method="The free height field with both thickness rules: a column under 8 mm holds nothing, and in a ball of 14 mm "
               "round any metal at most 60 % is metal (no member thicker than about 12 mm).",
        space="The whole design space.",
        changes="Every column's height.",
        rules="Least member 8 mm; greatest member 12 mm, held on the metal's p-mean (p 12).",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="Continuous, branching members merged into the shell, no paint, no big lumps; organic; the worst seat 10 % over in FE."),
    "ol_free": dict(group="rules", title="+ a limit on the members' outline",
        method="As above, with the members' outline in plan at most 6,750 mm (0.8 of the last run's), so that dashes and "
               "worms, with their many ends, cost too much.",
        space="The whole design space.",
        changes="Every column's height.",
        rules="Least member 8 mm; greatest member 12 mm; outline at most 6,750 mm (7,229 mm at the end).",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="The outline 14 % shorter, the look nearly the same."),
    "p40_free": dict(group="rules", title="+ the thickness rule held near its worst spot",
        method="As the 8-12 mm run, with the thickness rule's mean read near its worst ball (p 40), so a knot where members "
               "cross cannot hide in the average.",
        space="The whole design space.",
        changes="Every column's height.",
        rules="Least member 8 mm; greatest member 12 mm (p 40).",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="Stiffer in FE (39.4 µm), the tilt 2 % over, two modes in their bands; still irregular, knots of 25-26 mm."),
    "webcap_free": dict(group="rules", title="+ flat webs between the bearings",
        method="As the 8-12 mm run, with room for a flat plate between the bearings: over the hull of every two of a half's "
               "seats' bosses, metal only within 12 mm of the wall.",
        space="The whole design space, but between the bosses only 12 mm off the wall (`web12.npz`: 8,509 cells taken out).",
        changes="Every column's height.",
        rules="Least member 8 mm; greatest member 12 mm; webs at most 12 mm between the bearings.",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="Worse: the webs could not hold the seats' tilt (1.28) and the lumps grew to 35 mm."),
    "web_free": dict(group="rules", title="All the rules at once",
        method="Every rule together: least member, greatest member near its worst spot, the webs, and the beds held with a "
               "larger margin (1.35).",
        space="As the webs' run.",
        changes="Every column's height.",
        rules="Least member 8 mm; greatest member 12 mm (p 40); webs at most 12 mm; beds at most 52.2/1.35 µm.",
        drawing="A smooth signed-distance surface (3 mm).",
        seen="Too many limits at once at 5.5 kg: the run broke its budget and the thickness rule; broad, melted forms."),
    "p40_clean": dict(group="clean", title="Clean members after the run (generator B done properly)",
        source="a reading of the p 40 run's field (`p40_free`)",
        method="The p 40 run's metal thinned to its skeleton; each branch's path smoothed or straightened, its width (8-16 mm) "
               "and height the run's own, gently varying; each seat's boss a ring.",
        space="No optimisation: the p 40 run read.",
        changes="Nothing; a reading.",
        rules="Members and rings only.",
        drawing="Each member a plate along its path on the exact, filleted shell, joints filleted (`LOOP_CLEAN=1`).",
        seen="Smoother but beaded, and twice as soft as the field it came from."),
    "style_zf": dict(group="cad9", title="ZF's style: lobes, drums, towers and crossed ribs",
        source=GRAMMAR,
        method="The outline lobed (30 mm blends, each gear's drum showing); the motor side in drums (a base at the shallowest "
               "shaft's end, a drum down to each deeper shaft's own end); the cover a tower over each bearing; on the end "
               "faces crossed ribs at ±45°, 60 mm apart, ending on a rim; delta ribs boss to boss along the lines of centres; "
               "side ribs every 34 mm; the ribs 26 mm high and 6 mm thick, 12 mm off the side walls.",
        space="No optimisation: the whole housing from the preset `zf`.",
        changes="Nothing in an optimisation; the preset's choices.",
        rules=GRAMMAR_RULES,
        drawing=GRAMMAR_DRAWING,
        seen="The best of the grammar: the massing (lobes, drums, towers braced by tall crossed ribs and a rim) moved the "
             "stiffness far more than the ribs did; still 1.6 times too soft at the worst seat, and 1.4 kg over the mass."),
    "style_kalyani": dict(group="cad9", title="Kalyani's style: fans round two bearings, clean ribs by rule",
        source=GRAMMAR,
        method="The outline lobed (45 mm blends); drums; the cover a bridge over stage 2's bearings; on the end faces fans of "
               "12 curved ribs round the output and the intermediate bearings (bent 40°), a rim, the motor's ring scalloped "
               "(a boss round each of its bolts); the ribs 22 mm high, 6 mm thick. Rebuilt at 23:11 with fastcae's clean-rib "
               "rules (LOP-15): every rib ends on a hard point, arrives at 45° or more, crosses at 60° or more and bends no "
               "tighter than 8 times its thickness; the rules kept 15 of 47 candidate ribs.",
        space="No optimisation: the whole housing from the preset `kalyani`.",
        changes="Nothing in an optimisation; the preset's choices.",
        rules="The grammar's, and fastcae's clean-rib rules (`ribrules.py`): R3 root fillets, an end's top 3 mm under what it "
              "meets, least height 6 mm, ends 11 mm apart, 6 mm face to face, ribs meeting the wall between the bolts.",
        drawing="OCC exact B-rep (STEP) in CadQuery: each rib one sweep of a section with a semicircular top (no fillet "
                "operation), fused rib by rib, any rib that breaks the solid left out.",
        seen="Clean, castable and meshing, but softer than its first, unruly version: a style's rib pattern drawn by hand "
             "does not fit clean rules in this layout."),
    "style_avl": dict(group="cad9", title="AVL's style: a hull, a truss of spokes and a wheel",
        source=GRAMMAR,
        method="The outline the hull round the gears; the motor side one flat face; the cover a bridge; spokes as a truss (two "
               "from each boss to the walls under the bolts); delta ribs boss to boss along the lines of centres; an 8-spoke "
               "wheel inside the motor's ring; the grammar's ribs (5 mm thick, 15 mm high).",
        space="No optimisation: the whole housing from the preset `avl`.",
        changes="Nothing in an optimisation; the preset's choices.",
        rules=GRAMMAR_RULES,
        drawing=GRAMMAR_DRAWING,
        seen="Over twice too soft at the worst seat: its flat motor side and bridge hold the seats less than drums and "
             "towers, and its ribs left the most undercut of the six."),
    "style_punch": dict(group="cad9", title="Punch's style: deep lobes and five sweeping curves",
        source=GRAMMAR,
        method="The outline lobed with 90 mm blends; drums; the cover a bridge; five curved fan ribs round the intermediate and "
               "the output bearings (bent 85°); low ribs, 12 mm high and 6 mm off the side walls.",
        space="No optimisation: the whole housing from the preset `punch`.",
        changes="Nothing in an optimisation; the preset's choices.",
        rules=GRAMMAR_RULES,
        drawing=GRAMMAR_DRAWING,
        seen="Light and clean to cast, but soft: its few low sweeping ribs hold little."),
    "style_avtec": dict(group="cad9", title="Avtec's style: a rounded box with a square grid",
        source=GRAMMAR,
        method="The outline a box round all the gears with 50 mm corners; the motor side flat; the cover flat; a square grid "
               "of ribs (0° and 90°, 48 mm apart) on the end faces, ending on a rim; side ribs every 40 mm; the ribs 18 mm high.",
        space="No optimisation: the whole housing from the preset `avtec`.",
        changes="Nothing in an optimisation; the preset's choices.",
        rules=GRAMMAR_RULES,
        drawing=GRAMMAR_DRAWING + " Its mesh held one flat tet, cured by Netgen's optimiser (`fe.py`).",
        seen="The heaviest and among the softest: its big flat faces give the first mode at 622 Hz."),
    "style_batom": dict(group="cad9", title="Batom's style: a hull, drums, towers and a 12-spoke wheel",
        source=GRAMMAR,
        method="The outline the hull; drums; the cover a tower over each bearing; a spoke from each boss to the nearest wall "
               "under a bolt; a 12-spoke wheel with an inner ring inside the motor's ring; the ribs 20 mm high.",
        space="No optimisation: the whole housing from the preset `batom`.",
        changes="Nothing in an optimisation; the preset's choices.",
        rules=GRAMMAR_RULES,
        drawing=GRAMMAR_DRAWING,
        seen="Its free-standing towers are soft: the cover's seats moved and tilted 2.5-3 times ZF's, whose towers are "
             "braced by crossed ribs, side ribs and a rim."),
    "param3": dict(group="cad", title="The production-features recipe, drawn in CadQuery",
        source=RECIPE,
        method="The production-forms layout rebuilt as exact parametric CAD from a recipe (`param_cad.py`, CadQuery on OCC): "
               "each seat's boss a collar 12 mm wide and 8 mm high; a bridge 10 mm thick and 18 mm high between each pair of "
               "seats; straight ribs 5 mm thick with full-round tops, their root and tip heights the optimiser's along its form; "
               "spokes every 30° (5 mm thick, 14 mm high at the boss falling to 8); a gusset 5 mm thick and 18 mm high at each "
               "flange bolt; an arm 25 mm wide to each mount. Motor side: 3 bosses, 2 bridges, 3 ribs, 5 spokes, 8 gussets, "
               "3 arms; cover: 3 bosses, 1 bridge, 5 ribs, 9 spokes, 5 gussets.",
        space="No optimisation: every feature's size is the recipe's (`param3_recipe.json`).",
        changes="Nothing in an optimisation; the recipe's numbers.",
        rules="The recipe's features only, on the contract's exact shell.",
        drawing="OCC exact B-rep (STEP): fillets of 3 mm on the rims (the motor side's 25 refused by OCC and left sharp, the "
                "cover's 12 all made) and at the roots (61 of 131 and 65 of 115 edges made, the rest refused), 2 mm on the "
                "bosses' edges; every exact cut. Built in 188 s.",
        seen="Clean, regular CAD, a foundry's look, but 5.2 times too soft (273 µm), the tilt 4.9 times its line, three "
             "modes in their bands: the recipe's features left out the metal that held the seats in the run."),
    "param5": dict(group="cad", title="The recipe with fins, slimmer collars and taller webs",
        source=RECIPE,
        method="As param3, with fins every 30° round each room (6 mm thick, 20 mm deep, 6 mm at the tip; 42 on the motor side, "
               "33 on the cover), the collars 8 mm wide reaching 8 mm below, the bridges and gussets 24 mm high, the cover's "
               "spokes 11; the features fused to one another first, then onto the shell.",
        space="No optimisation: every feature's size is the recipe's (`param5_recipe.json`).",
        changes="Nothing in an optimisation; the recipe's numbers.",
        rules="The recipe's features only, on the contract's exact shell.",
        drawing="OCC exact B-rep (STEP): the rims filleted at 3 mm (all made), 2 mm on the bosses' edges; every exact cut. "
                "OCC called the motor side's B-rep invalid (38 faces under 0.5 mm wide); FE's mesh of it was watertight. Built in 47 s.",
        seen="The fins and taller webs recovered little (239 µm, tilt 4.6): the cover's seats stand on tubes, and the "
             "features left out the metal that held them in the run."),
}

OBJECTIVE = {
    "compliance_tilt": "Maximise the stiffness (least compliance) under peak drive",
    "mass_tilt": "The least metal under peak drive (the mass a ceiling only)",
}
KEYS = ("objective", "budget_kg", "safety", "safety_beds", "least_height_mm", "max_member", "plan_rule", "perimeter_mm",
        "space", "parts_read", "height_volumes", "height_features")  # fmt: skip


CAST_KEYS = ("undercut_cm2", "undercut_share", "largest_section_mm", "largest_section_members_mm")


def castable(d: str) -> dict:
    """Each half's castability: from its log's JSON lines, else from its record's halves (castable.py's older output)."""
    out = {}
    p = OUT / f"castable_{d}.log"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            i = line.find(": {")
            if i < 0:
                continue
            try:
                r = json.loads(line[i + 2 :])
            except json.JSONDecodeError:
                continue
            if r.get("half") in ("cover", "motor_side"):
                out[r["half"]] = {k: r.get(k) for k in CAST_KEYS}
    rec = OUT / f"castable_{d}.json"
    if not out and rec.exists():
        for h in json.loads(rec.read_text(encoding="utf-8")).get("halves", []):
            out[h["half"]] = {k: h.get(k) for k in CAST_KEYS}
    return out


def grade_row(d: str) -> dict:
    """A design graded before its flow record existed: its FE record, and its row in the grade's table (design, kg,
    drive µm, reverse µm, the tilt of its own housing, of the housing, against the shaft, mode 1, orders, verdict),
    from its own grade log, else the newest that holds it."""
    fe = json.loads((OUT / f"fe_{d}.json").read_text(encoding="utf-8"))
    own = OUT / f"grade_{d}.log"
    logs = ([own] if own.exists() else []) + sorted(OUT.glob("grade_*.log"), key=lambda q: q.stat().st_mtime, reverse=True)
    for log in logs:
        rows = log.read_text(encoding="utf-8", errors="replace").splitlines()
        row = next((s.split() for s in rows if s.split()[:1] == [d]), None)
        if row:
            break
    else:
        raise SystemExit(f"{d}: no row in any grade log")
    return {"mass_kg": fe["mass_kg"], "first_mode_hz": fe["modes_hz"][0], "seat_um": float(row[2]), "tilt": float(row[6]),
            "clashes": fe.get("order_clashes") or [], "pass": row[-1] == "PASS"}  # fmt: skip


def record(d: str) -> dict:
    """A design's run settings, its run's metal-or-air check, its FE grade and its castability."""
    flow_p = OUT / f"flow_{d}.json"
    flow = json.loads(flow_p.read_text(encoding="utf-8")) if flow_p.exists() else {}
    run = next((str(o) for s in flow.get("steps", []) for o in (s.get("outputs") or []) if str(o).startswith("topofree_")), None)
    rec_p = OUT / f"{run}.json" if run else None
    rec = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p and rec_p.exists() else {}
    if flow.get("grade"):
        g = flow["grade"]
        lines = g.get("lines") or {}
        grade = {"mass_kg": g.get("mass_kg"), "first_mode_hz": g.get("first_mode_hz"),
                 "seat_um": (lines.get("displacement, peak drive") or {}).get("value_um"),
                 "tilt": (lines.get("misalignment (worst seat against its line)") or {}).get("ratio"),
                 "clashes": (lines.get("orders") or {}).get("clashes") or [], "pass": g.get("pass")}  # fmt: skip
    else:
        grade = grade_row(d)
    b = rec.get("binary")
    keep = ("worst", "bed_worst", "mass_kg", "greatest_share", "plan_share", "outline_mm")
    return {"run": run, "settings": {k: rec.get(k) for k in KEYS if rec.get(k) not in (None, False, "")},
            "binary": {k: b.get(k) for k in keep} if b else None, "grade": grade, "castable": castable(d)}  # fmt: skip


def limits(s: dict) -> str:
    """The run's limits: its mass, every bearing's tilt and bed (each with the optimiser's factor of safety)."""
    out = []
    b = s.get("budget_kg")
    if b:
        word = "Mass at most" if s.get("objective") == "compliance_tilt" else "Mass ceiling"
        out.append(f"{word} {b:g} kg ({b - FROZEN_KG:.2f} kg to place on the {FROZEN_KG:.2f} kg fixed)")
    sf = s.get("safety", 1.0)
    out.append(f"every bearing's tilt at most 1/{sf:g} of its line")
    sb = s.get("safety_beds", sf)
    out.append(f"every bearing's bed at most 52.2 µm / {sb:g} = {52.2 / sb:.1f} µm")
    return "; ".join(out)


def thickest(r: dict) -> float | None:
    """The members' thickest section (the lump gate's measure: the seats' bosses and the mounts' eyes left out), where measured."""
    vals = [v["largest_section_members_mm"] for v in r["castable"].values() if v and v.get("largest_section_members_mm") is not None]
    return max(vals) if vals else None


def chips(r: dict) -> str:
    g = r["grade"]
    clashes = g["clashes"]
    items = [
        ("mass", f"{g['mass_kg']:.2f} kg", g["mass_kg"] <= 7.732),
        ("seat", f"{g['seat_um']:.1f} µm", g["seat_um"] <= 52.2),
        ("tilt", f"{g['tilt']:.2f}", g["tilt"] <= 1.0),
        ("modes", "clear" if not clashes else f"{len(clashes)} clash" + ("es" if len(clashes) > 1 else ""), not clashes),
    ]
    t = thickest(r)
    if t is not None:
        items.append(("thickest member", f"{t:.0f} mm", t <= LUMP_MM))
    return "".join(f'<span class="chip {"ok" if ok else "bad"}"><span class="k">{E(k)}</span>{E(v)}</span>' for k, v, ok in items)


def results(r: dict, sourced: bool) -> str:
    g, c, s = r["grade"], r["castable"], r["settings"]
    clashes = g["clashes"]
    lines = [
        f"FE on the drawn geometry: {g['mass_kg']:.2f} kg; the worst bearing seat {g['seat_um']:.1f} µm (52.2 to beat); "
        f"the worst tilt {g['tilt']:.2f} of its line; the first mode {g['first_mode_hz']:.0f} Hz; "
        + ("no mode within 3 % of the gear orders" if not clashes else "; ".join(clashes))
    ]
    parts = []
    for half, name in (("cover", "cover"), ("motor_side", "motor side")):
        v = c.get(half)
        if not v:
            parts.append(f"{name}: not judged" + (" (the check failed on its surface)" if c else ""))
            continue
        if v.get("undercut_cm2") is not None:
            under = f"undercut {v['undercut_cm2']:.1f} cm²"
        else:
            under = f"undercut {100 * v['undercut_share']:.1f} %"
        if v.get("largest_section_members_mm") is not None:
            sec = f", thickest member section {v['largest_section_members_mm']:.0f} mm"
        elif v.get("largest_section_mm") is not None:
            sec = f", thickest section anywhere, the bosses included, {v['largest_section_mm']:.0f} mm (judged before the members' gate)"
        else:
            sec = ""
        parts.append(f"{name}: {under}{sec}")
    lines.append("Castability: " + "; ".join(parts))
    b = r.get("binary")
    if b and not sourced and b.get("worst") is not None:
        extra = [f"the worst tilt {b['worst']:.3f}" + (f" and the worst bed {b['bed_worst']:.3f}" if b.get("bed_worst") is not None else "")
                 + " of their held limits"]  # fmt: skip
        if b.get("greatest_share") is not None:
            extra.append(f"the thickness rule's share {b['greatest_share']:.3f} (at most 0.6)")
        if b.get("plan_share") is not None:
            extra.append(f"the plan rule's share {b['plan_share']:.3f} (at most 0.5)")
        if b.get("outline_mm") is not None:
            extra.append(f"the outline {b['outline_mm']:,.0f} mm")
        total = b["mass_kg"] + FROZEN_KG
        over = ""
        if s.get("objective") == "compliance_tilt" and s.get("budget_kg") and total > s["budget_kg"] + 0.02:
            over = f", over its {s['budget_kg']:g} kg budget"
        lines.append(f"The optimiser's own check (its design read as metal or air, in its voxel model): {', '.join(extra)}; {total:.2f} kg{over}")
    return "".join(f"<p>{E(x)}</p>" for x in lines)


def image(stem: str) -> str:
    """A picture (`look_<design>`: the whole housing; `look_face_<design>`: each half along the pull) as an embedded JPEG."""
    im = Image.open(OUT / f"{stem}.png").convert("RGB")
    w, h = im.size
    im = im.resize((1400, round(1400 * h / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


CSS = """
:root {
  --bg: #eef1f4; --surface: #ffffff; --ink: #18222d; --muted: #5a6776; --line: #d3dae2; --accent: #1d5c86;
  --ok: #1d7445; --ok-bg: #e3f2e9; --bad: #a8321f; --bad-bg: #f8e5e1;
  --display: "Barlow Semi Condensed", "Arial Narrow", Arial, sans-serif;
  --body: "Public Sans", "Segoe UI", Roboto, Arial, sans-serif;
  --mono: "IBM Plex Mono", Consolas, "Courier New", monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #10161c; --surface: #18212b; --ink: #e4ebf2; --muted: #9aa8b6; --line: #2b3846; --accent: #77b6e3;
  --ok: #5cc98a; --ok-bg: #173226; --bad: #ff8b78; --bad-bg: #3a1f1b; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #10161c; --surface: #18212b; --ink: #e4ebf2; --muted: #9aa8b6; --line: #2b3846; --accent: #77b6e3;
  --ok: #5cc98a; --ok-bg: #173226; --bad: #ff8b78; --bad-bg: #3a1f1b; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body); }
.wrap { max-width: 1120px; margin: 0 auto; padding: 28px 16px 64px; display: grid; gap: 28px; }
.wrap, .group, .stack, .card { grid-template-columns: minmax(0, 1fr); }
.stack { display: grid; gap: 10px; }
h1, h2, h3 { font-family: var(--display); text-wrap: balance; margin: 0; letter-spacing: 0.01em; }
h1 { font-size: clamp(30px, 5vw, 44px); line-height: 1.05; }
h2 { font-size: 26px; color: var(--accent); }
h3 { font-size: 21px; line-height: 1.2; }
h4 { margin: 0 0 6px; font: 600 12px/1 var(--body); text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
p { margin: 0; max-width: 78ch; }
.lede { color: var(--muted); font-size: 16px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 18px 20px; display: grid; gap: 12px; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
.cols > div { min-width: 0; display: grid; gap: 6px; align-content: start; }
.cols ul { margin: 0; padding-left: 18px; display: grid; gap: 3px; }
.code, td, .chip { font-variant-numeric: tabular-nums; }
.code { margin-top: 2px; font: 12px/1.4 var(--mono); color: var(--muted); word-break: break-all; }
.table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }
table { border-collapse: collapse; width: 100%; min-width: 780px; font-size: 14px; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { font: 600 12px/1.2 var(--body); text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
td.ok { color: var(--ok); font-family: var(--mono); }
td.bad { color: var(--bad); font-family: var(--mono); }
td.na { color: var(--muted); font-family: var(--mono); }
td.grp { color: var(--muted); font-size: 13px; }
td a { color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--line); }
td a:hover, td a:focus-visible { border-bottom-color: var(--accent); outline: none; }
.group { display: grid; gap: 16px; }
.blurb { color: var(--muted); margin-top: -8px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; display: grid; }
.card figure { margin: 0; background: #ffffff; border-bottom: 1px solid var(--line); }
.card figcaption { padding: 10px 14px 0; font: 600 11px/1.3 var(--body); text-transform: uppercase; letter-spacing: 0.08em; color: #5a6776; }
.card img { display: block; width: 100%; height: auto; }
.card-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 10px 18px; padding: 16px 20px 6px; }
.card-head > div { min-width: 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; gap: 6px; align-items: baseline; padding: 3px 9px; border-radius: 999px; font: 500 13px/1.4 var(--mono); }
.chip .k { font: 600 10px/1 var(--body); text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.8; }
.chip.ok { background: var(--ok-bg); color: var(--ok); }
.chip.bad { background: var(--bad-bg); color: var(--bad); }
.spec { display: grid; grid-template-columns: 150px 1fr; gap: 6px 16px; margin: 0; padding: 10px 20px 4px; }
.spec dt { font: 600 12px/1.5 var(--body); text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); padding-top: 2px; }
.spec dd { margin: 0; min-width: 0; }
.res { padding: 12px 20px 18px; display: grid; gap: 6px; border-top: 1px dashed var(--line); margin-top: 10px; }
.res p { font-size: 14px; }
.seen { margin-top: 4px; }
@media (max-width: 640px) {
  .spec { grid-template-columns: 1fr; gap: 2px; } .spec dd { margin-bottom: 8px; }
  .card-head, .spec, .res { padding-inline: 14px; }
}
"""

COMMON = """
<section class="panel">
  <h4>The same in every design since 11 October (the 9 October styles had the generator's own set-up, given in their section)</h4>
  <div class="cols">
    <div><b>Fixed: the contract</b><ul>
      <li>The 4 mm shell: each gear room's cup and its end walls</li>
      <li>Six bearing seats (three a half), their bores and the paths in</li>
      <li>The split flange's land: 10 mm wide, 9 mm a half</li>
      <li>13 bolt bosses, Ø20, on the land</li>
      <li>3 mounts on the motor side (Ø36 eyes)</li>
      <li>The shafts' exits and every kept-clear room</li>
      <li>2.93 kg of fixed metal in the optimiser's model</li></ul></div>
    <div><b>Targets (beat the reference)</b><ul>
      <li>Mass at most 7.73 kg</li>
      <li>The worst bearing seat at most 52.2 µm, peak drive</li>
      <li>Every bearing's tilt at most its line (ratio ≤ 1.00)</li>
      <li>No mode within 3 % of the gear orders: 1,127 Hz (stage 2), 2,500 Hz (stage 1)</li>
      <li>Castable: one pull a half, no thin lips, no lumps (members' sections ≤ 16 mm)</li></ul></div>
    <div><b>The optimiser and the judges</b><ul>
      <li>4 mm voxels, 96,197 free, within a 24 mm band off the shell (each mount's region reaches its eye)</li>
      <li>The height field: each column one run of metal, smoothed over 6 mm in plan, castable along the pull by construction</li>
      <li>GCMMA; one load case, peak drive; every tilt and bed held with a factor of safety (1.15 unless a card says otherwise)</li>
      <li>FE: quadratic tetrahedra (TetGen) on the drawn surface, the single-precision factor on the GPU (cuDSS), 12 modes</li>
      <li>Castability: rays along the pull, the least wall, the largest ball in the metal</li></ul></div>
  </div>
</section>
"""


def build() -> Path:
    data = {d: record(d) for d in D}
    cards, rows = {}, []
    for key, name, _ in GROUPS:
        for d, t in D.items():
            if t["group"] != key:
                continue
            r, s, src = data[d], data[d]["settings"], t.get("source")
            spec = [
                ("How it works", t["method"]),
                ("Design space", t["space"]),
                ("What changes", t["changes"]),
                ("Objective", f"None of its own: {src}" if src else OBJECTIVE.get(s.get("objective"), "–") + "; load case: peak drive"),
                ("Limits", "None of its own (only the targets judge it)" if src else limits(s)),
                ("Shape rules", t["rules"]),
                ("Drawing", t["drawing"]),
            ]
            dl = "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in spec)
            cards.setdefault(key, []).append(f"""
<article class="card" id="{E(d)}">
  <figure><figcaption>The whole housing: each half from outside, and the two together from the cover's side and the motor's</figcaption>
    <img src="{image(f"look_{d}")}" alt="{E(t["title"])}: the whole housing from four cameras" width="1400" height="1167"></figure>
  <figure><figcaption>Each half's outside along the pull: the cover (left), the motor side (right)</figcaption>
    <img src="{image(f"look_face_{d}")}" alt="{E(t["title"])}: the cover (left) and the motor side (right), seen along the pull" width="1400" height="700"></figure>
  <header class="card-head"><div><h3>{E(t["title"])}</h3><p class="code">{E(d)}</p></div><div class="chips">{chips(r)}</div></header>
  <dl class="spec">{dl}</dl>
  <section class="res"><h4>Results</h4>{results(r, bool(src))}<p class="seen"><b>Seen:</b> {E(t["seen"])}</p></section>
</article>""")
            g, th = r["grade"], thickest(r)

            def cell(ok: bool, text: str) -> str:
                return f'<td class="{"ok" if ok else "bad"}">{E(text)}</td>'

            rows.append(
                f'<tr><td><a href="#{E(d)}">{E(t["title"])}</a></td><td class="grp">{E(name)}</td>'
                + cell(g["mass_kg"] <= 7.732, f"{g['mass_kg']:.2f}")
                + cell(g["seat_um"] <= 52.2, f"{g['seat_um']:.1f}")
                + cell(g["tilt"] <= 1.0, f"{g['tilt']:.2f}")
                + cell(not g["clashes"], "clear" if not g["clashes"] else str(len(g["clashes"])))
                + (cell(th <= LUMP_MM, f"{th:.0f}") if th is not None else '<td class="na">–</td>')
                + "</tr>"
            )
    sections = "".join(
        f'<section class="group"><h2>{E(name)}</h2><p class="blurb">{E(blurb)}</p>{"".join(cards[key])}</section>'
        for key, name, blurb in GROUPS
        if key in cards
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Housing Methods Gallery</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@600;700&family=Public+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header class="stack">
  <h1>Housing methods gallery</h1>
  <p class="lede">The EV two-stage reducer housing from each method tried on 9, 11 and 12 October, seen along the pull (the cover on
  the left, the motor side on the right), with what was fixed, what could change, the objective, the limits and shape rules,
  how it was drawn, and what FE and the castability check found. Every number comes from the design's own records.</p>
</header>
{COMMON}
<section class="stack">
  <h2>Summary</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Design</th><th>Method</th><th>Mass kg</th><th>Seat µm</th><th>Tilt</th><th>Modes</th><th>Thickest member mm</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
  <p class="lede">Green meets the target, red misses it: mass ≤ 7.73 kg, the worst seat ≤ 52.2 µm, the tilt ≤ 1.00 of its line,
  no mode within 3 % of an order, the thickest member section ≤ 16 mm (the lump gate, the seats' bosses and the mounts' eyes
  left out; "–" where a design was judged before the gate: its card gives the thickest section anywhere).</p>
</section>
{sections}
</div>
</body>
</html>
"""
    PAGE.write_text(page, encoding="utf-8")
    return PAGE


if __name__ == "__main__":
    p = build()
    print(p, f"{p.stat().st_size / 1e6:.1f} MB,", len(D), "designs")
