"""PROTOTYPE - not product code, not the judge.

Plan Part C, Tasks 8-11 in order: front-end sketch (Task 8), the outline for the bolt bosses
(first step of Task 10), the CadQuery core (Task 9), the field shell and structure (Task 10),
the join and exports (Task 11) and the pictures (Task 11); then summary.json.

    uv run python prototypes/first_variant/run.py

Everything lands in data/prototypes/first_variant/ (gitignored).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import core  # noqa: E402
import field  # noqa: E402
import frontend  # noqa: E402
import join  # noqa: E402
import params as P  # noqa: E402
import render  # noqa: E402
from layout import free_memory_mb, peak_memory_mb  # noqa: E402

ASSUMPTIONS = {
    "A1": "peak drive, peak regeneration and reverse torques = the nominal 366 N*m; "
    "regeneration and reverse with the sign reversed (only the nominal is published)",
    "A3": "installation space = the layout's envelope (gears, bearings, motor-flange disc, "
    "mount pad) grown by 20 mm, as a box; it clips the members",
    "A4": "supports: the motor flange clamped and one torque-reaction mount pad fixed; the pad "
    "is placed on the +x end wall near the output axis",
    "A5": "order-check speeds 7,500 and 15,000 rpm input (used only for the mesh-frequency list)",
    "A7": "pull direction normal to the split face, +z for the main housing half",
}

RULES_OF_THUMB = {
    "ratio split": "stage 1 z 25/65 (2.600), stage 2 z 23/82 (3.565); product 9.270",
    "modules": "normal module 2.0 mm (stage 1), 2.5 mm (stage 2)",
    "angles": "helix 20 deg both stages, normal pressure angle 20 deg, no profile shift",
    "face widths": "b = 2 pi mn / sin(beta) (Hofstetter's overlap-ratio rule, eps_beta = 2): "
    "36.74 and 45.93 mm",
    "helix hands": "stage-1 pinion right, stage-2 pinion left (thrusts on the intermediate "
    "shaft partly cancel)",
    "supports": "two supports per shaft at the bearings' mid-widths; thrust to the locating "
    "bearing (6206, 6012; on the intermediate shaft the tapered bearing it pushes "
    "into); tapered bearings' pressure centres and induced thrust ignored",
}

DEVIATIONS = [
    "draft direction: the brief says the offset grows with z; with the pull along +z and the "
    "opening at z = 0 that widens the cavity toward the back wall (an undercut). The offset "
    "grows toward the split face instead (delta = (z_wall_in - z) tan 2 deg), so every side wall "
    "narrows away from the split, as the brief's 'taper away from the split' intends",
    "the cavity is the gears' keep-outs swept to the split face and closed by a flat back, so "
    "the die's core can be drawn; the bearings and the shaft passages are cut out of the solid "
    "as the seats rather than wrapped by the shell",
    "motor flange face raised to z = 130.67 mm: the brief's d150 flange (bolts on d130) reaches "
    "over the intermediate seat, whose bore edge is 55.8 mm from the input axis (the d110 "
    "spigot clears that bore by only 0.8 mm); the face now sits 6 mm above the intermediate "
    "seat ring, and the six holes are turned so the intermediate axis falls between two",
    "bolt hole centres 10 mm outside the wall (not 5) so an M8 head can seat, with a 10 mm "
    "sealing lip carrying the bosses and an r 8 mm head-clearance keep-out above each boss",
    "the installation-space clip (A3) applies to the members only; the shell, lip and bolt "
    "bosses stand where they must, and their volume outside the box is reported",
    "frame: +z points toward the motor (the motor sits on the back wall, as the brief says); "
    "the spec's default frame points +z away from the motor",
    "the back-wall bearings start at the back wall's inner face, 8 mm behind the stage-2 gear "
    "faces (3 mm keep-out clearance + 5 mm shell gap), not 5 mm",
    "derived.json is plain JSON with provenance labels; it is not validated with "
    "zenryx.contract (src/ is separate work tonight and nothing here imports it)",
]

NOT_CHECKED = [
    "the front-end has not passed the plan's three load checks (spec 4.3); sizing is by rule "
    "of thumb, not a gear rating",
    "bearing boundary dimensions (ISO 15 series) are to be checked against a maker's catalogue",
    "no FE yet: no stiffness, misalignment, bearing tilt, modes or stress",
    "the cover half and its three seats are not built",
    "the axial retention at the locating seats (shoulder one way, a retaining ring the other) "
    "is not modelled",
    "bolt head and nut seating, thread engagement and the sealing line are not checked",
    "the d110 spigot leaves only 0.8 mm to the intermediate bore in plan view; the layout "
    "needs a look before any real flange is drawn",
    "machining stock (0.25 mm) is recorded, not modelled; no fill, porosity or parting-line "
    "study; the draft and thickness maps are reported, not enforced",
    "the thickness map is from a 1.0 mm voxel copy (about +-1 mm)",
]


def seat_load_table(derived):
    out = {}
    for case in derived["load_cases"]:
        out[case["name"]] = {
            s["seat"]: {
                "bearing": s["bearing"],
                "force_on_housing_N": s["force_on_housing"]["value"],
                "magnitude_N": s["magnitude"]["value"],
                "radial_N": s["radial"]["value"],
                "axial_N": s["axial"]["value"],
                "provenance": s["force_on_housing"]["provenance"],
            }
            for s in case["seat_loads"]
        }
    return out


def main():
    t0 = time.time()
    times = {}
    free0 = free_memory_mb()

    def step(name, fn):
        t = time.time()
        r = fn()
        times[name] = round(time.time() - t, 1)
        return r

    derived = step("task 8: front-end", frontend.main)
    outline = step("task 10a: outline", field.write_outline)
    core_rep = step("task 9: core", core.main)
    field_rep = step("task 10: field", field.main)
    join_rep = step("task 11: join", join.main)
    pictures = step("task 11: pictures", render.main)

    out = P.OUT
    summary = {
        "PROTOTYPE": (
            "first housing variant, plan Part C (Tasks 8-11): a prototype, not product "
            "code and not the judge; its numbers have not passed the plan's checks"
        ),
        "mass_kg": join_rep["mass_kg"],
        "mass_provenance": "density 2.66 g/cm3: " + P.DENSITY_LABEL,
        "volume_mm3": join_rep["volume_mm3"],
        "bounding_box_mm": join_rep["bounding_box_mm"],
        "triangles": join_rep["triangles"],
        "watertight": join_rep["watertight"],
        "components_as_read": join_rep["components_as_read"],
        "exported_files_read_back": join_rep["exported_files_read_back"],
        "manifold_bodies": join_rep["bodies"],
        "genus": join_rep["genus"],
        "mesh_repair": join_rep["mesh_repair"],
        "closed_except_split_face_and_shaft_passages": join_rep["closed_shell"][
            "closed_except_split_face_and_passages"
        ],
        "keepout_intrusion_mm3": join_rep["keepout_intrusion"],
        "outside_installation_space_mm3": join_rep["outside_installation_space_mm3"],
        "thickness": join_rep["thickness"],
        "draft": join_rep["draft"],
        "enclosed_voids": join_rep["enclosed_voids"],
        "core": {
            "volume_mm3": core_rep["volume_mm3"],
            "solids": core_rep["solids"],
            "step_reimport_relative_difference": core_rep["step_reimport_relative_difference"],
            "step_reimport_ok": core_rep["step_reimport_ok"],
        },
        "field": {
            "voxel_mm": field_rep["voxel_mm"],
            "grid_shape": field_rep["grid_shape"],
            "members": len(field_rep["members"]),
            "triangles": field_rep["field_mesh"]["triangles"],
        },
        "bolt_bosses": {
            "count": outline["boss_count"],
            "pitch_along_outline_mm": outline["boss_pitch_along_outline"],
        },
        "layout": {
            "ratio": derived["ratio_check"]["total_ratio"]["value"],
            "axes_mm": {k: v["value"] for k, v in derived["axes"].items()},
            "L_mm": derived["housing"]["L"]["value"],
            "back_wall_mm": [
                derived["housing"]["back_wall_inner_z"]["value"],
                derived["housing"]["back_wall_outer_z"]["value"],
            ],
            "motor_flange_face_z_mm": derived["interfaces"]["motor_flange"]["centre"]["value"][2],
        },
        "seat_loads": seat_load_table(derived),
        "seat_loads_note": (
            "force the shaft puts on the housing at each seat, global frame, N; "
            "regeneration and reverse give the same quasi-static loads (only "
            "the torque's sign enters); stamp "
            + P.DERIVED
            + ", input hash "
            + derived["stamp"]["input_hash"]
        ),
        "assumptions_used": ASSUMPTIONS,
        "rules_of_thumb": RULES_OF_THUMB,
        "prototype_choices": P.PROVENANCE,
        "bearings": {"source": P.PUB_T3, "dimensions": P.CATALOGUE},
        "deviations_from_the_brief": DEVIATIONS,
        "not_checked": NOT_CHECKED,
        "run": {
            "time_s": times,
            "total_s": round(time.time() - t0, 1),
            "free_memory_mb_at_start": None if free0 is None else round(free0),
            "peak_memory_mb_this_process": peak_memory_mb(),
        },
        "files": {
            "derived": str(out / "derived.json"),
            "outline": str(out / "outline.json"),
            "core_step": str(out / "core.step"),
            "core_stl": str(out / "core.stl"),
            "field_stl": str(out / "field.stl"),
            "housing_stl": str(out / "housing.stl"),
            "housing_glb": str(out / "housing.glb"),
            "pictures": pictures,
        },
    }
    path = out / "summary.json"
    path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print()
    print(f"summary.json -> {path}")
    print(
        f"mass {summary['mass_kg']:.3f} kg; one watertight body as read back: "
        f"{summary['watertight'] and summary['components_as_read'] == 1}; "
        f"thickness min {summary['thickness']['min_mm']} / median "
        f"{summary['thickness']['median_mm']} mm; draft share "
        f"{100 * summary['draft']['share_of_cast_area_below_threshold']:.2f} %; voids "
        f"{summary['enclosed_voids']['mesh_shells_with_negative_volume']}"
    )
    print("pictures:")
    for p_ in pictures:
        print(f"  {p_}")
    print(
        f"total {summary['run']['total_s']} s, peak memory "
        f"{summary['run']['peak_memory_mb_this_process']:.0f} MB"
    )
    return summary


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
