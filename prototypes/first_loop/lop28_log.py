"""PROTOTYPE (LOP-28) - the overnight campaign's decision log for the Campaigns page: data/first_loop/agent/lop28.json,
written whole from the moves below (the account is docs/features/loop/2026-10-13-record-overnight.md). Each move says what
the agent saw, its hypothesis, the lever, what changed, what it expected, its designs, its verdict and the next move. No
number is typed for a result: each move names its designs, and `campaign_export.py lop28` takes their runs' records and
their FE grades; each design's run is read from its own record (`outcome_of`).

Run: .venv/Scripts/python.exe prototypes/first_loop/lop28_log.py, then campaign_export.py lop28"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
SETTINGS = {"voxel_mm": 4, "height_limit_mm": 24, "smoothing_mm": 6, "load_case": "peak drive", "mounts": "held fully", "start": "empty"}


def run_of(design: str) -> str:
    p = OUT / f"{design}.json"
    return json.loads(p.read_text(encoding="utf-8")).get("outcome_of", "") if p.exists() else ""


def move(n, title, at, saw, hypothesis, lever, changed, expected, designs, verdict, nxt, settings=None, kind="rules"):
    return {"n": n, "iteration": n + 1, "kind": kind, "title": title, "at": at, "until": None, "by": "the agent", "saw": saw,
            "hypothesis": hypothesis, "lever": lever, "settings": {**SETTINGS, **(settings or {})}, "changed": list(changed), "not_pulled": [],
            "expected": expected, "budget": "", "acceptance": "every graded line by FE (the worst seat, the tilt, the orders), at most "
            "7.73 kg, oil-tight; the look against production's", "rollback": "the best validated design so far",
            "space": {"name": "the empty start's", "changed": False, "file": None, "words": "fixed (D16)"}, "pictures": [],
            "results": [{"label": label, "run": run_of(d), "design": d} for label, d in designs], "verdict": verdict, "next": nxt}  # fmt: skip


LEAST = {"objective": "the least metal, every tilt and bed held at 1/1.25 of its line"}
MOVES = [
    move(0, "The reference: the empty start", "2026-10-12T20:40", "No fixed shell; one field for the whole housing.",
         "The reference every rule is judged against.", "`topo_free.py --empty`", [], "", [("the reference", "empty1_5.5kg")],
         "Every line passes; lumps where the loads meet.", "The semantic rules.",
         {"objective": "the stiffest at 5.5 kg, every tilt and bed held at 1/1.15"}, kind="space"),
    move(1, "The semantic rules", "2026-10-13T00:31",
         "Lumps on the bridges between the bearings, bumpy collars round the bosses, wrinkled panels; case 3's web took a fifth of a bracket.",
         "Bounding each region's own roughness, with the brackets' metal held, cleans the look at a small cost.",
         "`--bending s1_regions.npz --brackets s1_brackets.npz`",
         ["the bridges' bending at most 0.3 × the reference's", "the rings' and panels' double curvature at most 0.5 ×",
          "each bracket's metal at least the reference's"], "calmer bridges and rounder collars, the seats a few percent softer",
         [("the semantic rules", "sem1_5.5kg")],
         "Every region at its bound, yet the look barely changed (the engineer, 00:50: 'I don't think there is an improvement').",
         "Protect the functional geometry first (the engineer, 00:50).", {"objective": "the stiffest at 5.5 kg, 1/1.15"}),
    move(2, "The protected interfaces, fused as CAD", "2026-10-13T00:56",
         "The bosses round the bearings and the sealing flange were the optimiser's lumpy voxel metal.",
         "With the functional geometry fixed, the field adds only ribs and transitions round it.",
         "`--protect` (fused exact solids)", ["each bearing's boss, the sealing land, the bolts' bosses and the lugs fixed"],
         "the interfaces read as designed", [("the protected interfaces", "prot1_5.5kg")],
         "The bosses overhung the lobes (undercut 3.8 / 5.7 %) and the tilt failed; the engineer (01:28): all protected regions in the "
         "field only.", "The bosses as castable towers, drawn in the field.", {"objective": "the stiffest at 5.5 kg, 1/1.15"}),
    move(3, "The functional package at the least mass, in the field", "2026-10-13T01:32",
         "Fused CAD mixed two worlds, overhung, leaked and meshed past FE's memory.",
         "The same features as densities from their exact shapes, contoured once with the rest, mesh and cast cleanly.",
         "`outcome_cad.py` with `exact_walls.interface_density`; `--objective mass_tilt --safety 1.25`",
         ["the interfaces in the field", "the least mass with every line held"], "oil-tight, castable, an ordinary size for FE",
         [("drawn in the field", "prot3f")], "Oil-tight and castable, but the cover's input seat failed its tilt: its boss had shrunk to a 4 mm "
         "tube where the seat stands past its room.", "Each boss a castable tower from its seat to the split.", LEAST),
    move(4, "The bosses as castable towers", "2026-10-13T01:45", "Clipped to the lobes, a boss became a tube.",
         "A tower from a wall past the seat down to the split stands as a cast boss does.", "`topo_free.build_free(protect=True)`",
         ["each boss a tower from a wall past its seat to the split"], "the seats' tilt back within its line",
         [("the towers", "prot4_least")], "The tilt at 1.036 ×: the model flatters one seat.", "Read which seat, from FE.", LEAST),
    move(5, "A seat's own factor of safety, learned from FE", "2026-10-13T01:48",
         "The model's misalignment is lower than FE's at one seat more than the rest.",
         "Holding that seat at a tighter factor closes the gap (`seat_ratios.py`: the motor side's intermediate seat, 1.29-1.40 ×).",
         "`LOOP_SAFETY_SEATS`", ["the input seat at 1/1.4 (P5), then the motor side's intermediate seat at 1/1.4 (P6)"],
         "the tilt within its line", [("the input seat at 1/1.4", "prot5_least"), ("the intermediate seat at 1/1.4", "prot6_least")],
         "P6 holds the tilt (0.961 ×); a mode in s1's band remains.", "Production's rules against ours.", LEAST),
    move(6, "Production's plain walls", "2026-10-13T02:05", "The engineer (01:54): the walls between the ribs are plain.",
         "A wall either bare at its least or carrying a member at least 6 mm tall.", "`LOOP_WALL_GATE=6`", ["the wall gate"],
         "calmer walls", [("plain walls", "rule1_wall")],
         "No look change (the drawing already drops thin paint); the seats 31 % softer. Dropped.", "One-way curvature.", LEAST),
    move(7, "One-way curvature everywhere", "2026-10-13T02:12",
         "Production's castings curve one way at a time; double curvature reads as organic.",
         "Bounding the double curvature everywhere calms the shapes.", "`--bending dev1_regions.npz`",
         ["the double curvature at most half P5's, every column"], "calmer shapes at no cost", [("one-way curvature", "rule2_dev")],
         "The limits bind at no cost, but the look is P6's: what reads as loops is the members' layout in plan.",
         "A rule on the plan.", LEAST),
    move(8, "Thin, spaced members", "2026-10-13T02:15", "Loops and blobs are the members' layout in plan.",
         "Members at most 8 mm wide and 20 mm apart read as production's ribs.", "`--plan-gap 20 --plan-width 8`",
         ["the plan rule"], "rib-like members", [],
         "Infeasible on this layout: the plan share stalled at 0.65 against 0.5, every line at its bound (stopped at iteration 55, "
         "also with 0.4 kg more). The bridges and arms need wider members.", "A floor on the bridge for the mode.", LEAST),
    move(9, "The mode: a floor on the cover's bridge", "2026-10-13T02:25", "Mode 8 sits in s1's band: the cover's panel between "
         "its output and intermediate bosses.", "More metal on that bridge stiffens it out of the band.",
         "`LOOP_FLOORS=cover:intermediate:output:100`", ["at least 100 cm³ on the bridge"], "the mode +3 %",
         [("the bridge's floor", "final1")], "The mode moved 10 Hz of the 77 needed.", "Production's panel spokes.", LEAST),
    move(10, "Production's panel spokes, drawn", "2026-10-13T02:35", "Production stiffens such panels with radial ribs.",
         "Spokes every 30° from each boss across the end walls lift the panel's modes.", "`LOOP_PANEL_SPOKES=30:6:10` (drawn only)",
         ["the spokes drawn on P6's run"], "the mode out of the band", [("spokes drawn", "p6spk")],
         "The mode +1.4 %, but the tilt 1.19 ×: spokes the optimiser did not know stiffen one side more.",
         "Fix the spokes in the optimisation.", LEAST),
    move(11, "The cover's spokes fixed in the optimisation", "2026-10-13T02:41",
         "Spokes must be known to the optimiser so it sizes the rest round them.", "Fixed spokes keep the tilt and look like production.",
         "`LOOP_PANEL_SPOKES=30:6:12 LOOP_SPOKE_HALVES=cover` with `--protect`", ["the cover's spokes fixed", "the intermediate seat at 1/1.5"],
         "production's look, every line but the mode", [("the cover's spokes", "final2"), ("the spokes 14 mm tall", "final3")],
         "The cover carries production's wheel of spokes; every line holds but mode 8 (2440 Hz), whatever the spokes' height.",
         "The modes' last moves.", LEAST),
    move(12, "The modes' last moves", "2026-10-13T02:53", "Mode 8: the motor side's input bore 21 %, the cover's bores, mount-3 11 %.",
         "Spokes on both halves, a lighter housing, or mount-3's bracket as a tuning mass moves it.",
         "`LOOP_SPOKE_HALVES`, `--safety`, `--brackets floors:...`",
         ["spokes on both halves", "every line at 1/1.2", "mount-3's bracket at 70, 110, 150 cm³"], "one of them clears the band",
         [("spokes on both halves", "final4"), ("every line at 1/1.2", "final5"), ("mount-3 at 70 cm³", "final6"),
          ("mount-3 at 110 cm³", "final7"), ("mount-3 at 150 cm³", "final8")],
         "Mount-3 at 110 cm³ (final7) passes every graded line: the first. At 150 a mode falls into s2's band: a narrow window.",
         "The hand-over of final7; then the lumps at the junctions.", LEAST),
    move(13, "No lump at the junctions", "2026-10-13T03:33", "Final7's members bunch where the loads meet (`ball_shares.py`).",
         "The note's cap on local accumulation, not yet tried with the height field, thins the junctions.",
         "`--max-member 16`, then read near its worst ball (`LOOP_MEMBER_P=40`)", ["the greatest member, 16 mm"],
         "thinner junctions at the same lines", [("the cap at p 12", "final9"), ("the cap at p 40", "final10")],
         "At p 12 it never bound, and its near-identical field put mode 8 in s1's band (the margin is within the noise). At p 40 it held at no "
         "cost: final10 passes every line with smaller lumps and less undercut. It is the hand-over.",
         "Test whether the designer's reading holds the lines.", LEAST),
    move(14, "Is the designer's reading safe to draw?", "2026-10-13T04:02",
         "The hand-over reads each member as straight runs; a designer will draw them so.",
         "Put back into the field and judged, the reading shows which simplifications keep the lines.",
         "`reading_field.py final10 [--keep ...] [--deep]`", ["the members' metal replaced by the reading's runs"],
         "the reading near final10's numbers",
         [("all as runs, median heights", "final10r"), ("the arms kept", "final10ra"), ("the arms and networks kept", "final10rn"),
          ("every member kept", "final10rz"), ("ribs at their deep heights", "final10rp"), ("all at their deep heights", "final10rd")],
         "At their median heights the ribs lose a third of the stiffness (a rib's depth peaks near the bosses); at their deep heights, "
         "with the arms and networks as the field, every static line holds for 0.3 kg. The drawing rule goes on the page.",
         "The thinner drawing, and the margins.", {"objective": "none: final10's field, redrawn"}, kind="space"),
    move(15, "The margins: a thinner drawing, then every line held tighter", "2026-10-13T04:36",
         "Final10 passes, but its tilt (4.6 %) and s1 (0.2 % past the band's edge) margins are thin.",
         "Drawn thinner (member level 0.5) the same field shows what its thin members carry; holding every line tighter buys margin.",
         "`LOOP_MEMBER_LEVEL=0.5`; `--safety 1.3`, `1.45`; mount-3's floor", ["the member level", "every line at 1/1.3, 1/1.45",
          "mount-3's floor back at 50.6 cm³"], "margins past what the thin members carry",
         [("final10 drawn at 0.5", "final10_l50"), ("every line at 1/1.3", "final11"), ("every line at 1/1.45", "final12"),
          ("1/1.45, mount-3 at 50.6 cm³", "final13")],
         "Drawn thinner, the tilt reads 6 % higher and the modes 1 % lower. Stiffer lifts every mode: mode 8 leaves s1's band as mode 4 enters "
         "s2's; clearing both with margin costs mass up to the 7.73 kg line. Without its floor mount-3's bracket fails (58 µm, 372 Hz). "
         "Final10 stays the hand-over; final12 is the stiffer alternative.",
         "Production's gusseted lugs in place of the floors.",
         {"objective": "the least metal, every line at 1/1.3 or 1/1.45"}),
    move(16, "Production's gusseted lugs", "2026-10-13T05:02",
         "The brackets were the motor side's least production-like part, and their floor is structural.",
         "Two webs from each lug to its room's wall, over the lug's length, carry the mount as production's lugs do, cleanly.",
         "`LOOP_LUG_WEBS=8:25` (`exact_walls.lug_webs`), the floors dropped; then the seat's factor and every line at 1/1.3",
         ["the gusseted lugs fixed in the field", "the intermediate seat at 1/1.65", "every line at 1/1.3"],
         "production's brackets; the static lines held",
         [("the gusseted lugs", "final14"), ("the intermediate seat at 1/1.65", "final15"), ("every line at 1/1.3", "final16"),
          ("final16 drawn at 0.5", "final16_l50"), ("the drawing rule on its field", "final16rp"),
          ("every line at 1/1.35", "final17"), ("final17 drawn at 0.5", "final17_l50"),
          ("a floor on the input-intermediate bridge", "final18"), ("final18 drawn at 0.5", "final18_l50")],
         "The lugs lifted every mode (first 868-883 Hz) and cleared both orders by 12 % and more: the modes chased all night were "
         "the brackets' softness. Final16 passes every line (7.50 kg, tilt 0.963 ×) and is the hand-over, its tilt "
         "leaning on thin members; at 1/1.35 (final17) the tilt still reads its line drawn thinner, and a floor on the motor side's input-intermediate bridge (final18) holds it at 0.917 × for 0.11 kg.", "The morning's review.", {"objective": "the least metal, every line at 1/1.25 or 1/1.3"}),
]


def write(moves=MOVES):
    log = {"id": "lop28", "title": "Region-aware rules, then one clean housing for a CAD engineer", "contract": "EV two-stage reducer",
           "driver": "agent", "agent": "Claude (Opus 5.5), acting as the runtime agent in the session (the engineer away, 13 October 00:16)",
           "started": "2026-10-13T00:20",
           "goal": "a housing a CAD engineer can start from: every graded line by FE at no more than 7.73 kg, oil-tight, castable, calm "
                   "panels, clear ribs, whole brackets, at the least mass that keeps all of it",
           "baseline": "empty1_5.5kg", "log": "docs/features/loop/2026-10-13-record-overnight.md", "moves": moves}  # fmt: skip
    (OUT / "agent").mkdir(parents=True, exist_ok=True)
    (OUT / "agent" / "lop28.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    missing = [r["design"] for m in moves for r in m["results"] if not r["run"]]
    print(OUT / "agent" / "lop28.json", len(moves), "moves", f"(no run found for {missing})" if missing else "")


if __name__ == "__main__":
    write()
