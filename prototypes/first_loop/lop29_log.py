"""PROTOTYPE (LOP-29) - the campaign's decision log for the Campaigns page: data/first_loop/agent/lop29.json, written whole
from the moves below (the account: the loop page's LOP-29 row and decisions; D17). Each move names its designs; the
numbers come from their runs' records and FE's grades (`campaign_export.py lop29`), never typed here.

Run: .venv/Scripts/python.exe prototypes/first_loop/lop29_log.py, then campaign_export.py lop29"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "first_loop"
SETTINGS = {"voxel_mm": 4, "height_limit_mm": 24, "smoothing_mm": 6, "load_case": "peak drive", "mounts": "held fully",
            "start": "empty", "fixed": "the contract's interfaces: bearing towers, the 8 mm sealing land, the bolts' bosses, the lugs",
            "patterns": "none (D17)", "max_member_mm": 16, "objective": "the least metal, every tilt and bed at 1/1.25, the "
            "intermediate seat at 1/1.5"}  # fmt: skip


def run_of(design: str) -> str:
    p = OUT / f"{design}.json"
    return json.loads(p.read_text(encoding="utf-8")).get("outcome_of", "") if p.exists() else ""


def move(n, title, at, saw, hypothesis, lever, changed, expected, designs, verdict, nxt, settings=None, kind="rules"):
    return {"n": n, "iteration": n + 1, "kind": kind, "title": title, "at": at, "until": None, "by": "the agent", "saw": saw,
            "hypothesis": hypothesis, "lever": lever, "settings": {**SETTINGS, **(settings or {})}, "changed": list(changed), "not_pulled": [],
            "expected": expected, "budget": "", "acceptance": "every graded line by FE (the worst seat, the tilt, the orders), at most "
            "7.73 kg, oil-tight; the model's modes beside FE's", "rollback": "final16 (a reference: its lugs and spokes were set by hand)",
            "space": {"name": "the empty start's", "changed": False, "file": None, "words": "fixed (D16)"}, "pictures": [],
            "results": [{"label": label, "run": run_of(d), "design": d} for label, d in designs], "verdict": verdict, "next": nxt}  # fmt: skip


MOVES = [
    move(0, "The set-up made honest: the flange 8 mm, every fixed cube whole", "2026-10-13T18:42",
         "The model's own modes were flaps of the split flange's partly filled cubes (150-330 Hz against FE's 700-3,000): a "
         "cube the flange filled in part had the cube of its share as stiffness but its share as mass.",
         "Whole cubes, as the mounts are, leave no cube soft for its mass; a flange two whole cubes deep matches the real one.",
         "The contract's A26 (the engineer: 9 → 8 mm); `build_free(..., flange_whole=True)`",
         ["the flange 8 mm deep each side (A26)", "every cube whose centre lies in the flange or a bolt boss fixed whole"],
         "no partly filled fixed cube; the model's modes near FE's", [],
         "Every one of the 22,032 fixed cubes whole; the contract, the UI's records and the layout written again; 216 checks pass.",
         "The modes into the optimiser.", kind="space"),
    move(1, "The modes in the optimiser, asked for final16's clearance", "2026-10-13T19:37",
         "final16 cleared both gear orders by 12 % and more, but its brackets were a pattern I set (D17: not a result).",
         "Asked for the same clearance with free brackets, the optimiser stiffens the mounting by itself.",
         "`--modes 0.12` (`topo.mode_gaps`: the mode just below each order at least 12 % under it, the one above 12 % over)",
         ["the lowest 14 modes read each step on the step's own factor", "the gap round each order a constraint"],
         "every graded line, the modes 12 % clear, the brackets the optimiser's own", [("the modes held", "lop29_modes")],
         "In the model every line and both gaps held (2.30 kg placed); in FE it fails: the seats 84 µm, the tilt 1.08, modes at 1107 and "
         "2459 Hz, the brackets thin struts. The model is fair (on the drawing voxelised it reads FE's numbers, model_vs_fe.py); the "
         "drawing lost 10 % of the field's metal, half of it members one voxel wide, 449 voxels at the brackets.",
         "A drawing that keeps every voxel of the field, tested on this run.", {"modes_margin": 0.12}),
    move(2, "The drawing keeps the optimiser's field, checked before FE", "2026-10-13T20:26",
         "The drawing lost a tenth of the field's metal: its blur thinned members one cube wide and dropped lone cubes.",
         "Held at every cube the optimiser placed, the drawing is the field, and FE reads what the model read.",
         "`mesh_route.contour(..., keep=)`; `outcome_cad.cube_fidelity` (the engineer, 20:12: \"Yes do option 1\")",
         ["every metal cube of the field held by the contour", "each cube's centre tested inside the drawing before FE"],
         "FE near the model's 41.8 µm and tilt 0.81", [("the field kept", "lop29_keep")],
         "The drawing now loses 6 of the 6,957 cubes; 472 stood where the drawing keeps clear (351 in the bolts' sockets, which the "
         "set-up did not know; 61 in the bolts' holes; 60 in the mounts' rooms). FE: 53.1 µm, tilt 1.05, 579 Hz, 2522 Hz in s1's band. "
         "The model on this drawing reads FE's numbers: the tilt is the drawing's. Only the metal added between the motor side's "
         "intermediate seat and the split moves it (0.66 → 1.11 in the model): that gear room's floor, drawn 4.9 mm where the "
         "optimiser has 4.", "Draw the walls at their true thickness.", {"modes_margin": 0.12}, kind="drawing"),
    move(3, "The walls drawn at their true thickness", "2026-10-13T20:50",
         "A 4 mm least wall came out 3-5 mm on the drawing's 2 mm cells (each face on a cell's face); 4.9 mm under the "
         "intermediate gear room stiffened that seat's split-side end and tipped it.",
         "With each face at its true place the seats keep the balance the optimiser gave them.",
         "`exact_walls.ramp`: the faces of the least walls and the protected interfaces as a ramp in the one field",
         ["the least walls and the interfaces drawn with their faces where they are (4.0 mm measured under that room)"],
         "the tilt back under its line", [("the walls at 4 mm", "lop29_exact")],
         "Tilt 0.89 and no mode in an order's band now; the worst seat 55.4 µm against 52.2 to beat (6 % over). The model on the "
         "drawing is within 10 % of FE; the rest of the gap is the metal the optimiser put where the drawing keeps clear (the "
         "field 41.8 µm, the drawing 50.5 in the model).", "The set-up keeps clear what the drawing keeps clear.",
         {"modes_margin": 0.12}, kind="drawing"),
    move(4, "The set-up keeps clear what the drawing keeps clear; the mounts' rooms as tall as the mount", "2026-10-13T20:56",
         "The optimiser filled the bolts' holes and sockets and the margins round kept-clear spaces, and its towers were 2 mm "
         "thinner than the drawn ones; the room over each lug ran up the whole housing.",
         "On one description of what is kept clear, the optimiser counts only metal that is drawn, and FE reads its numbers.",
         "`build_free(..., drawing_clear=True)`; the contract's A20 (the engineer, 20:31: \"Keep clear is just the mount height and "
         "not any higher\")",
         ["each bolt's hole and its head's socket (Ø16 × 25 mm) void", "every kept-clear space 2 mm wider, as the drawing's",
          "each tower by the whole-cube rule", "each mount's bracket room 30 mm beyond each face, no higher"],
         "every graded line by FE, the brackets the optimiser's own", [("the set-up aligned", "lop29_clear")],
         "The drawing holds 7,814 of the 7,836 cubes and none stands where it keeps clear: the field is drawn. But the optimiser "
         "starved two brackets (mount-1 23.6 → 2.5 cm³, mount-2 40.4 → 19.3) and FE fails: 74.2 µm, tilt 0.90, the first mode 175 Hz "
         "(the whole housing swinging on its mounts; the model's own 199 Hz, far from both orders, so no gap held it). The model reads "
         "the drawing as its field (44.3 µm against 43.9) but FE 1.7 times softer: the model holds each lug's core clamped and glues "
         "the flanges over each bolt's patch, where FE holds each hole's mean motion, so two mounts look enough to it.",
         "Hold the mounts and join the halves in the model as FE does.", {"modes_margin": 0.12}, kind="set-up"),
]


def write(moves=MOVES):
    log = {"id": "lop29", "title": "The modes in the optimiser: asked for final16's performance with free brackets",
           "contract": "EV two-stage reducer", "driver": "agent", "agent": "Claude (Opus 5.5), in the session with the engineer",
           "started": "2026-10-13T18:42",
           "goal": "the engineer's test (17:45): asked for final16's performance (every line with margins, the modes 12 % from the "
                   "gear orders), does the optimiser deliver straight brackets by itself?",
           "baseline": "final16", "log": "docs/features/loop/status.md (LOP-29)", "moves": moves}  # fmt: skip
    (OUT / "agent").mkdir(parents=True, exist_ok=True)
    (OUT / "agent" / "lop29.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    print(OUT / "agent" / "lop29.json", len(moves), "moves")


if __name__ == "__main__":
    write()
