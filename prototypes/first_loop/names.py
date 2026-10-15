"""PROTOTYPE (LOP-17) - one name for each optimisation run, and the same name on every design drawn
from it, so the Designs page's two tabs read alike (the engineer, 10 October 12:20: "optimization
based designs should have the same name as the optimization based designs in the designs tab maybe
added by a short suffix highlighting the method").

A run's name is what was varied, its mass, and its method: "Split robust β32 · 7.73 kg · GCMMA".
A design drawn from a run is the run's name with "· CAD" (and "redrawn" for a second drawing of
the same run). A design from the generator keeps its own name, and is listed as parametric.

`write_indexes()` writes `_index.json` beside the Designs page's records
(`web/src/records/designs/`) and the Optimisation tab's (`web/src/records/optimisations/`): each
record's name, its kind and, for a design, the run it was drawn from, newest first. view_export.py
and topo_export.py call it after each export.

Run: .venv/Scripts/python.exe prototypes/first_loop/names.py   (rebuilds both indexes)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "first_loop"
RECORDS = ROOT / "web" / "src" / "records"


def method_of(stem: str) -> str:
    if stem.startswith("tobs_"):
        return "TOBS"
    if "_bound_" in stem or "_pnorm_" in stem or "_compliance_gcmma_" in stem or "_compliance_tilt_" in stem:
        return "GCMMA"
    return "OC"  # the optimality-criteria runs (LOP-3, LOP-16's runs 1-3)


def _record(stem: str) -> dict:
    try:
        return json.loads((OUT / f"{stem}.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def run_title(stem: str) -> str:
    """A run's short name: what was varied, its mass, its method."""
    kg = re.search(r"_(\d+(?:\.\d+)?)kg", stem)
    mass = f"{kg.group(1)} kg" if kg else ""
    method = method_of(stem)
    if stem.startswith("topo_"):  # LOP-3, round a frozen shell
        what = "Lobed shell, tilt" if "tilt" in stem else "Shell, compliance"
    elif "_bound_" in stem or "_pnorm_" in stem or "_compliance_gcmma_" in stem or "_compliance_tilt_" in stem or stem.startswith("tobs_"):
        # the model's choices follow the joint and the skin's wall ("_bolts_skin4_"); a run whose voxel
        # is the wall itself (4 mm, LOP-23) has no skin in its stem
        joint = re.search(r"_(?:bolts|glued)(?:_skin\d+(?:\.\d+)?)?(?=_|$)", stem)
        tail = stem[joint.end():] if joint else ""
        parts = [p for p in tail.split("_") if p]
        route = next((p for p in parts if p in ("split", "free")), "cast")
        what = route.capitalize()
        beta = next((p for p in parts if re.fullmatch(r"b\d+", p)), None)
        if any(p.startswith("robust") for p in parts):
            what += " robust"
        if beta:
            what += f" β{beta[1:]}"
        # LOP-19's one weighted objective, a run on one load case, and a voxel other than 6 mm
        if "_pnorm_" in stem:
            what += ", p-norm"
        if "_compliance_gcmma_" in stem:
            what += ", compliance"
        if "_compliance_tilt_" in stem:  # LOP-20: the stiffness, every bearing's tilt held under its line
            # 11 October: the beds held too (--beds), and the whole problem in one run rather than a
            # second stage started from a stiff run's design (the record's "start")
            what += ", compliance, tilt" + (" and beds" if "beds" in parts else "") + " held"
            what += ", from a stiff run" if _record(stem).get("start") else ", one run"
        if "_mass_tilt_" in stem:  # LOP-24: the least metal holding every bearing's tilt and bed
            what += ", least metal, tilt" + (" and beds" if "beds" in parts else "") + " held"
        if "drive" not in parts and "reverse" not in parts and ("_compliance_" in stem):
            what += ", both cases"
        if "drive" in parts and "reverse" not in parts:
            what += ", peak drive"
        voxel = re.search(r"_(\d+(?:\.\d+)?)mm_", stem)
        if voxel and voxel.group(1) != "6":
            what += f", {voxel.group(1)} mm voxels"
        member = next((p for p in parts if re.fullmatch(r"max\d+(?:\.\d+)?", p)), None)
        if member:  # LOP-20's greatest member
            what += f", members ≤ {member[3:]} mm"
        plan = next((re.fullmatch(r"plan(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", p) for p in parts if re.fullmatch(r"plan\d+(?:\.\d+)?x\d+(?:\.\d+)?", p)), None)
        if plan:  # LOP-23's members' plan rule: at most a width wide, a gap apart
            what += f", in plan members ≤ {plan.group(1)} mm wide, {plan.group(2)} mm gap"
        safety = next((p for p in parts if re.fullmatch(r"sf\d+(?:\.\d+)?", p)), None)
        if safety:  # LOP-24: the optimiser's factor of safety on every tilt and bed
            what += f", safety factor {safety[2:]}"
        safety_b = next((p for p in parts if re.fullmatch(r"sfb\d+(?:\.\d+)?", p)), None)
        if safety_b:  # the beds' own factor
            what += f" (beds {safety_b[3:]})"
        band = re.search(r"_band(\d+(?:\.\d+)?)_", stem)
        if band:  # the height envelope (11 October): metal only within it of the shell
            what += f", within {band.group(1)} mm of the shell"
        # LOP-23: only on production's rib network, with a free run's members' centre-lines, with fins
        rib_word = next((p for p in parts if p in ("ribs", "ribsfield", "ribsfins", "ribsfieldfins")), None)
        if rib_word:
            what += ", on the rib network" + (" and a free run's lines" if "field" in rib_word else "") + (", side fins" if "fins" in rib_word else "")
    elif "band" in stem:
        band = re.search(r"band(\d+)", stem)
        what = f"Run 3, band {band.group(1)} mm" if band else "Run 3"
    elif "projected" in stem:
        what = "Run 2, solid and void"
    else:
        what = "Run 1, grey"
    return " · ".join(p for p in (what, mass, method) if p)


def summary_of(stem: str, run: str | None, body: dict, grades: dict) -> dict | None:
    """A design's row in the Designs page's comparison (LOP-20; the engineer, 10 October 19:33:
    "compare that with the previous iteration on the UI"): the optimiser's budget, what its set-up
    held fixed and what it placed (its metal-or-air check), the drawn CAD's mass, FE's bearing
    beds, worst tilt and first mode (grade.py's), and castability. None for a design not drawn
    from a run and never graded (a parametric design's row has no budget)."""
    if not run and stem not in grades:
        return None
    row = {"cad_kg": (body.get("mass_kg") or {}).get("total")}
    rec = OUT / f"{run}.json" if run else None
    if rec is not None and rec.exists():
        r = json.loads(rec.read_text(encoding="utf-8"))
        row.update(budget_kg=r.get("budget_kg"), fixed_kg=r.get("frozen_kg"), placed_kg=(r.get("binary") or {}).get("mass_kg"))
    g = grades.get(stem)
    if g:
        lines = g["lines"]
        # peak drive alone since 11 October (grade.GRADED_CASES; the engineer: reverse is not in the checks)
        drive = lines["displacement, peak drive"]
        tilt, orders, mass = lines["misalignment (worst seat against its line)"], lines["orders"], lines["mass"]
        row.update(drive_um=drive["value_um"], tilt=tilt["ratio"], mode_hz=g.get("first_mode_hz"),
                   clashes=len(orders["clashes"]),
                   passes={"beds": drive["pass"], "tilt": tilt["pass"], "mode": orders["pass"], "mass": mass["pass"]},
                   to_beat={"kg": mass["to_beat_kg"], "drive_um": drive["to_beat_um"]})  # fmt: skip
    cast = OUT / f"castable_{stem}.json"
    if cast.exists():
        halves = json.loads(cast.read_text(encoding="utf-8"))
        halves = halves if isinstance(halves, list) else halves.get("halves", [halves])
        row["castable"] = all(h.get("pull_rule") == "PASS" and h.get("least_wall_rule") == "PASS" for h in halves)
        row["undercut"] = max(h.get("undercut_share", 0.0) for h in halves)
    return row


def design_title(stem: str, run: str | None, redrawn: bool, route: str | None = None, drawing: str | None = None) -> str:
    """The run's name with what the drawing made: "CAD" (OCC's B-rep), "mesh" for the mesh route
    (11 October: the booleans on watertight meshes, `outcome_cad.build_mesh`), or "ribbed CAD"
    (the field read as ribs and pads, exact, `ribbed_cad.py`)."""
    if not run:
        return stem.replace("style_", "")
    kind = "ribbed CAD" if drawing == "ribs" else "mesh" if route == "mesh" else "CAD"
    return f"{run_title(run)} · {kind}" + (", redrawn" if redrawn else "")


def write_indexes() -> None:
    runs = {}
    for f in sorted((RECORDS / "optimisations").glob("*.json")):
        if f.name.startswith("_"):
            continue
        src = OUT / f.name
        runs[f.stem] = {"title": run_title(f.stem), "method": method_of(f.stem), "time": (src if src.exists() else f).stat().st_mtime}
    designs = {}
    seen: dict[str, int] = {}
    graded = OUT / "grades.json"
    grades = {g["stem"]: g for g in json.loads(graded.read_text(encoding="utf-8"))} if graded.exists() else {}
    files = [f for f in (RECORDS / "designs").glob("*.json") if not f.name.startswith("_")]
    for f in sorted(files, key=lambda p: (OUT / p.name).stat().st_mtime if (OUT / p.name).exists() else p.stat().st_mtime):
        rec = OUT / f.name
        run, form, drawing, body = None, None, None, {}
        if rec.exists():
            try:
                body = json.loads(rec.read_text(encoding="utf-8"))
                run, form, drawing = body.get("outcome_of"), body.get("form"), body.get("drawing")
            except (json.JSONDecodeError, OSError):
                run = None
        # LOP-20's skin drawing: the cup's exact wall and the field's members; the first one also drew
        # the trade's bearing bosses (its record predates the flag)
        skin = (", skin drawing" + (" with the trade's bosses" if body.get("skin_bosses", True) else "")) if drawing == "skin" else ""
        if isinstance(body.get("skin"), dict) and body["skin"].get("clean_members"):  # LOP-23: each member drawn clean
            skin += ", members drawn clean"
        if isinstance(body.get("skin"), dict) and body["skin"].get("smooth_passes"):  # LOP-23: the members' surface smoothed
            skin += ", smoothed"
        if form == "organic":  # the organic shape alone, before its CAD (outcome_cad.py)
            body_name = "ribbed body, before its cuts" if drawing == "ribs" else f"organic shape{skin}"
            title = f"{run_title(run)} · {body_name}" if run else f.stem
        else:
            redrawn = bool(run) and seen.get(run, 0) > 0 and not skin and drawing != "ribs"
            if run:
                seen[run] = seen.get(run, 0) + 1
            title = design_title(f.stem, run, redrawn, body.get("route"), drawing) + skin
            if body.get("strengthened"):  # a design agent's move on a failing seat (`ribbed_cad.py --strengthen`)
                st = body["strengthened"]
                title += f", the {st['shaft']} {st['side']} seat strengthened"
        designs[f.stem] = {"title": title, "source": "optimisation" if run else "parametric",
                           "run": run, "time": (rec if rec.exists() else f).stat().st_mtime,
                           "summary": summary_of(f.stem, run, body, grades) if form != "organic" else None}  # fmt: skip
    for folder, index in (("optimisations", runs), ("designs", designs)):
        ordered = dict(sorted(index.items(), key=lambda kv: -kv[1]["time"]))
        (RECORDS / folder / "_index.json").write_text(json.dumps(ordered, indent=1), encoding="utf-8")
        print(f"{folder}/_index.json: {len(ordered)}")
        for k, v in ordered.items():
            print(f"  {k}: {v['title']}".encode("ascii", "backslashreplace").decode("ascii"))


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the names hold β and ·
    write_indexes()
